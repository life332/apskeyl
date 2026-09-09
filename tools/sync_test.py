# -*- coding: utf-8 -*-
"""🔬 ОБʼЄКТИВНИЙ ТЕСТ СИНХРОНУ ЗВУКУ (28.08, скарга власника «звук відстає від рота»).

Робимо синтетичне відео: раз на секунду БІЛИЙ СПАЛАХ у кадрі і водночас ГУДОК у звуці.
Проганяємо його (а) швидким шляхом — той самий ffmpeg-рядок, що в jobs._run_fast,
(б) сегментним шляхом БЕЗ нейромережі (кадри → «рушій» = копія → збірка → concat → мукс),
тобто перевіряємо саме ТАЙМІНГ конвеєра. Далі знаходимо у виході час спалахів (яскравість
кадру) і гудків (silencedetect) і рахуємо зсув. |зсув| > 40 мс = розсинхрон.

Запуск: .venv\\Scripts\\python.exe -X utf8 tools\\sync_test.py [шлях_до_реального_файлу]
Із реальним файлом додатково звіряє КАДРИ: кадр виходу в момент t має збігатися з кадром
джерела в момент t (SSIM після зведення до 1080p) — якщо ні, відео зсунуте.
"""
from __future__ import annotations
import json, math, re, shutil, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
sys.stdout.reconfigure(encoding="utf-8")
from config import FFMPEG, FFPROBE, TMP
from media import run

W = TMP / "synctest"
shutil.rmtree(W, ignore_errors=True)
W.mkdir(parents=True)
FPS = 29.97
DUR = 12


def make_synthetic() -> Path:
    src = W / "src.mp4"
    # спалах: 3 кадри білого на кожній секунді; гудок 1 кГц 120 мс на кожній секунді
    vf = ("testsrc2=size=1280x720:rate=30000/1001,"
          "drawbox=x=0:y=0:w=iw:h=ih:color=white:t=fill:enable='lt(mod(t\\,1)\\,0.1)'")
    af = "sine=frequency=1000:sample_rate=44100,volume=enable='lt(mod(t\\,1)\\,0.12)':volume=1:eval=frame,volume=enable='gte(mod(t\\,1)\\,0.12)':volume=0:eval=frame"
    cp = run([FFMPEG, "-y", "-v", "error", "-f", "lavfi", "-i", vf, "-f", "lavfi", "-i", af,
              "-t", str(DUR), "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
              "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-shortest", src],
             timeout=300)
    assert cp.returncode == 0, cp.stderr[-400:]
    return src


def flashes(p: Path) -> list[float]:
    cp = run([FFPROBE, "-v", "error", "-f", "lavfi",
              f"movie={str(p).replace(chr(92), '/').replace(':', chr(92) + ':')},signalstats",
              "-show_entries", "frame=pts_time:frame_tags=lavfi.signalstats.YAVG",
              "-of", "csv=p=0"], timeout=600)
    out, prev = [], False
    for line in cp.stdout.splitlines():
        parts = line.split(",")
        if len(parts) < 2:
            continue
        try:
            t, y = float(parts[0]), float(parts[1])
        except ValueError:
            continue
        bright = y > 200
        if bright and not prev:
            out.append(t)
        prev = bright
    return out


def beeps(p: Path) -> list[float]:
    cp = run([FFMPEG, "-v", "info", "-i", p, "-af", "silencedetect=n=-30dB:d=0.3",
              "-f", "null", "-"], timeout=600)
    return [float(m) for m in re.findall(r"silence_end: ([\d.]+)", cp.stderr)]


def offset(p: Path) -> tuple[float, int, int]:
    f, b = flashes(p), beeps(p)
    pairs = []
    for t in f:
        near = min(b, key=lambda x: abs(x - t), default=None)
        if near is not None and abs(near - t) < 0.5:
            pairs.append(near - t)
    return (sum(pairs) / len(pairs) if pairs else float("nan")), len(f), len(b)


def path_fast(src: Path, info: dict) -> Path:
    out = W / "fast.mp4"
    vf = f"fps={FPS},scale=-2:1080:flags=lanczos,cas=0.4,scale=trunc(iw/2)*2:trunc(ih/2)*2"
    cp = run([FFMPEG, "-y", "-v", "error", "-i", src, "-map", "0:v:0", "-map", "0:a?",
              "-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
              "-pix_fmt", "yuv420p", "-c:a", "copy", "-map_metadata", "0",
              "-movflags", "+faststart", out], timeout=600)
    assert cp.returncode == 0, cp.stderr[-400:]
    return out


def path_segments(src: Path, dur: float, seg_len: float = 4.0) -> Path:
    """Той самий таймінг, що в jobs._run_nn / _do_segment, «рушій» = копія PNG."""
    n = math.ceil(dur / seg_len)
    parts = []
    for i in range(n):
        t0, t1 = i * seg_len, min((i + 1) * seg_len, dur)
        f0, f1 = int(round(t0 * FPS)), int(round(t1 * FPS))
        if f1 <= f0:
            continue
        sd = W / f"s{i:03d}"
        (sd / "in").mkdir(parents=True)
        cp = run([FFMPEG, "-y", "-v", "error", "-ss", f"{t0:.3f}", "-t", f"{t1 - t0 + 0.5:.3f}",
                  "-i", src, "-vf", f"fps={FPS}", "-frames:v", str(f1 - f0),
                  sd / "in" / "%06d.png"], timeout=600)
        assert cp.returncode == 0, cp.stderr[-300:]
        seg = W / f"s{i:03d}.mp4"
        cp = run([FFMPEG, "-y", "-v", "error", "-framerate", f"{FPS}", "-i", sd / "in" / "%06d.png",
                  "-vf", "scale=-2:1080:flags=lanczos,scale=trunc(iw/2)*2:trunc(ih/2)*2",
                  "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
                  "-an", seg], timeout=600)
        assert cp.returncode == 0, cp.stderr[-300:]
        shutil.rmtree(sd, ignore_errors=True)
        parts.append(seg)
    (W / "list.txt").write_text("".join(f"file '{p.name}'\n" for p in parts), encoding="utf-8")
    out = W / "segs.mp4"
    cp = subprocess.run([str(FFMPEG), "-y", "-v", "error", "-f", "concat", "-safe", "0",
                         "-i", "list.txt", "-i", str(src), "-map", "0:v:0", "-map", "1:a?",
                         "-c:v", "copy", "-c:a", "copy", "-movflags", "+faststart", "segs.mp4"],
                        cwd=str(W), capture_output=True, text=True, timeout=600,
                        creationflags=0x08000000)
    assert cp.returncode == 0, cp.stderr[-300:]
    return out


def frame_match(src: Path, out: Path, ts: list[float]) -> list[tuple[float, float]]:
    """SSIM між кадром джерела і кадром виходу в той самий момент (обидва → 1080p)."""
    res = []
    for t in ts:
        a, b = W / "fa.png", W / "fb.png"
        run([FFMPEG, "-y", "-v", "error", "-ss", f"{t:.3f}", "-i", src, "-frames:v", "1",
             "-vf", "scale=1920:1080:flags=lanczos", a], timeout=120)
        run([FFMPEG, "-y", "-v", "error", "-ss", f"{t:.3f}", "-i", out, "-frames:v", "1",
             "-vf", "scale=1920:1080:flags=lanczos", b], timeout=120)
        cp = run([FFMPEG, "-v", "info", "-i", a, "-i", b, "-lavfi", "ssim", "-f", "null", "-"],
                 timeout=120)
        m = re.search(r"All:([\d.]+)", cp.stderr)
        res.append((t, float(m.group(1)) if m else float("nan")))
    return res


if __name__ == "__main__":
    src = make_synthetic()
    o0, f0, b0 = offset(src)
    print(f"ДЖЕРЕЛО (синтетика): спалахів {f0}, гудків {b0}, зсув гудок−спалах = {o0*1000:+.0f} мс")
    fast = path_fast(src, {})
    o1, f1, b1 = offset(fast)
    print(f"ШВИДКИЙ ШЛЯХ:        спалахів {f1}, гудків {b1}, зсув = {o1*1000:+.0f} мс  "
          f"→ {'✅ синхрон' if abs(o1 - o0) < 0.04 else '❌ РОЗСИНХРОН'} (Δ проти джерела {(o1-o0)*1000:+.0f} мс)")
    segs = path_segments(src, DUR)
    o2, f2, b2 = offset(segs)
    print(f"СЕГМЕНТНИЙ ШЛЯХ:     спалахів {f2}, гудків {b2}, зсув = {o2*1000:+.0f} мс  "
          f"→ {'✅ синхрон' if abs(o2 - o0) < 0.04 else '❌ РОЗСИНХРОН'} (Δ проти джерела {(o2-o0)*1000:+.0f} мс)")
    if len(sys.argv) > 1:
        real = Path(sys.argv[1])
        print(f"\nРЕАЛЬНИЙ ФАЙЛ {real.name}: звірка кадрів вихід↔джерело у ті самі моменти")
        for out in sys.argv[2:]:
            outp = Path(out)
            mm = frame_match(real, outp, [3.0, 8.0, 15.0])
            print(f"  {outp.name}: " + " · ".join(f"t={t:.0f}с SSIM {s:.3f}" for t, s in mm)
                  + ("  ✅ той самий кадр" if all(s > 0.9 for _, s in mm) else "  ❌ КАДРИ НЕ ТІ — відео зсунуте"))
