# -*- coding: utf-8 -*-
"""Робота з відеофайлом: паспорт (ffprobe), превʼю, пошук «важкої» сцени, рекомендація.

Правила шляхів (уже кусалось у сусідньому проєкті):
 - шлях користувача (кирилиця/пробіли) потрапляє ТІЛЬКИ в -i / -ss аргументи;
 - у filtergraph ЖОДНИХ шляхів;
 - все, що пишемо самі, — в ASCII-теки на A:.
Будь-який subprocess — CREATE_NO_WINDOW (правило власника: ніяких чорних вікон).
"""
from __future__ import annotations
import json, subprocess, hashlib
from pathlib import Path

from config import FFMPEG, FFPROBE, THUMBS

NO_WIN = 0x08000000  # CREATE_NO_WINDOW


def run(cmd: list[str], timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run([str(c) for c in cmd], capture_output=True, text=True,
                          encoding="utf-8", errors="replace",
                          timeout=timeout, creationflags=NO_WIN)


def file_key(p: Path) -> str:
    """Дедуп-ключ: розмір + mtime + sha1 першого мегабайта (швидко навіть для 10 ГБ)."""
    st = p.stat()
    h = hashlib.sha1()
    h.update(f"{st.st_size}:{int(st.st_mtime)}".encode())
    with open(p, "rb") as f:
        h.update(f.read(1024 * 1024))
    return h.hexdigest()


def probe(path: Path) -> dict:
    """Паспорт файлу. VFR-детект: r_frame_rate ≠ avg_frame_rate → звук може поїхати."""
    cp = run([FFPROBE, "-v", "error", "-print_format", "json",
              "-show_format", "-show_streams", "-i", path])
    if cp.returncode != 0:
        raise RuntimeError(f"ffprobe не зміг прочитати файл: {cp.stderr[:300]}")
    j = json.loads(cp.stdout or "{}")
    v = next((s for s in j.get("streams", []) if s.get("codec_type") == "video"), None)
    a = [s for s in j.get("streams", []) if s.get("codec_type") == "audio"]
    if v is None:
        raise RuntimeError("у файлі немає відеопотоку")

    def _fps(s):
        try:
            n, d = (s or "0/1").split("/")
            return float(n) / float(d) if float(d) else 0.0
        except Exception:
            return 0.0

    fps_r, fps_avg = _fps(v.get("r_frame_rate")), _fps(v.get("avg_frame_rate"))
    fmt = j.get("format", {})
    dur = float(fmt.get("duration") or v.get("duration") or 0)
    bitrate = int(fmt.get("bit_rate") or 0)
    w, h = int(v.get("width") or 0), int(v.get("height") or 0)
    pixfmt = v.get("pix_fmt", "")
    hdr = ("smpte2084" in str(v.get("color_transfer", ""))
           or "arib-std-b67" in str(v.get("color_transfer", ""))
           or "10le" in pixfmt or "10be" in pixfmt)
    return {
        "w": w, "h": h, "short": min(w, h) if w and h else 0,
        "fps": round(fps_avg or fps_r, 3), "dur": round(dur, 2),
        "vcodec": v.get("codec_name", "?"),
        "acodec": (a[0].get("codec_name") if a else None),
        "atracks": len(a),
        "bitrate": bitrate,
        "vfr": bool(fps_r and fps_avg and abs(fps_r - fps_avg) / max(fps_avg, 1e-6) > 0.01),
        "hdr": hdr,
        "size": path.stat().st_size,
        "vertical": h > w,
    }


def make_thumb(path: Path, key: str, dur: float) -> Path:
    """Превʼю-кадр ~40 КБ. Беремо 15% тривалості (не перший кадр — там часто чорнота)."""
    out = THUMBS / f"{key}.jpg"
    if out.exists():
        return out
    t = max(0.5, dur * 0.15)
    cp = run([FFMPEG, "-y", "-v", "error", "-ss", f"{t:.2f}", "-i", path,
              "-frames:v", "1", "-vf", "scale=-2:360", "-q:v", "3", out])
    if cp.returncode != 0 or not out.exists():
        # друга спроба з нуля — раптом файл коротший за наш -ss
        run([FFMPEG, "-y", "-v", "error", "-i", path,
             "-frames:v", "1", "-vf", "scale=-2:360", "-q:v", "3", out])
    return out


def extract_frame(path: Path, t: float, out_png: Path) -> bool:
    cp = run([FFMPEG, "-y", "-v", "error", "-ss", f"{max(0.0, t):.3f}", "-i", path,
              "-frames:v", "1", out_png])
    return cp.returncode == 0 and out_png.exists()


def hard_scene(path: Path, dur: float) -> float:
    """Найдинамічніший момент. Порада Gemini: перші секунди — часто статична заставка,
    а артефакти нейромережі вилазять на русі. Дешевий спосіб без декодування: розміри
    пакетів з індексу контейнера — де кадри «важкі», там рух/деталь."""
    try:
        cp = run([FFPROBE, "-v", "error", "-select_streams", "v:0",
                  "-show_entries", "packet=pts_time,size",
                  "-of", "csv=p=0", "-i", path], timeout=60)
        if cp.returncode != 0:
            return dur * 0.4
        pts, sizes = [], []
        for line in cp.stdout.splitlines():
            parts = line.strip().split(",")
            if len(parts) >= 2:
                try:
                    pts.append(float(parts[0])); sizes.append(int(parts[1]))
                except ValueError:
                    continue
        if len(sizes) < 50:
            return dur * 0.4
        # ковзне вікно ~2 секунди за сумою байтів; краї (заставка/титри) відрізаємо
        import bisect
        lo, hi = dur * 0.05, dur * 0.92
        best_t, best_sum = dur * 0.4, -1
        win = 2.0
        for i, t0 in enumerate(pts):
            if t0 < lo or t0 > hi:
                continue
            j = bisect.bisect_right(pts, t0 + win, i)
            s = sum(sizes[i:j])
            if s > best_sum:
                best_sum, best_t = s, t0
        return round(best_t, 2)
    except Exception:
        return dur * 0.4


def recommend(info: dict) -> dict:
    """АВТО-АНАЛІЗ → РЕКОМЕНДАЦІЯ (панель 28.08, обидва ШІ незалежно).
    Програма має ЗАХИЩАТИ від нейромережі там, де вона не дасть нічого, крім гало.
    Етап 1 — груба евристика по паспорту; повний профайлер (блокінг/шум) — Етап 4."""
    short, fps = info["short"], max(info["fps"], 1.0)
    bpp = info["bitrate"] / max(info["w"] * info["h"] * fps, 1)  # біт на піксель
    if short <= 0:
        return {"path": "fast", "text": "Не зміг прочитати роздільну — почни з проби."}
    if short < 900:
        return {"path": "nn",
                "text": f"{short}p — саме для нейромережі: мала роздільна, апскейл дасть "
                        f"видимий приріст. Почни з проби 1 кадра."}
    if bpp < 0.045:
        return {"path": "nn+deblock",
                "text": "1080p, але сильно стиснуте (мало біт на піксель — типово для "
                        "скачаного з YouTube). Нейромережа + прибрати квадрати. Перевір пробою."}
    return {"path": "fast",
            "text": "Джерело чисте: нейромережа дасть ~12% різкості і +22% хибних країв — "
                    "різницю можеш не побачити. Рекомендую швидкий шлях (чистка+різкість), "
                    "а 4K має сенс як вищий тир кодування YouTube."}
