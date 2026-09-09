# -*- coding: utf-8 -*-
"""Двигун Етапу 1: чесна математика пресетів + проба одного кадра.

Пресети йдуть по КОРОТКІЙ стороні (власник робить і вертикальні шортси 1080×1920) —
тому й масштабування завжди по короткій осі: для вертикального відео scale=W:-2,
для горизонтального scale=-2:H (ревізія 28.08 зловила, що інакше вертикаль бреше).

Рушій уміє лише ×2/×3/×4, і НЕ КОЖНА модель уміє все: animevideov3 — 2/3/4,
x4plus/general-x4v3 — ТІЛЬКИ ×4 (бінарник мовчки зіпсує вихід, якщо дати їм -s 2).

Проба чесна: «до» — той самий кадр, зведений lanczos-ом до тієї ж роздільної, що «після».
Одночасно виконується РІВНО ОДНА проба (_PROBE_LOCK): GPU один, і поруч живий стрім.
"""
from __future__ import annotations
import json, shutil, struct, subprocess, threading, time
from pathlib import Path

from config import (FFMPEG, FFPROBE, REALESRGAN, MODELS_DIR, GPU_ID, TMP, DATA,
                    THROUGHPUT_MPIX_S, FAST_SPEED_X, TMP_GB_PER_SEC_4K,
                    OUT_MB_PER_MIN_4K, disk_free_gb, load_settings,
                    ENGINE2_PY, ENGINE2_TILE, ENGINE2_DIR, PTH_DIR)
from media import run, extract_frame, NO_WIN
import pool
import procs

TARGETS = {"fhd": 1080, "2k": 1440, "4k": 2160}
DEFAULT_MODEL = "realesr-animevideov3"
MODEL_SCALES = {
    "realesr-animevideov3": (2, 3, 4),
    "realesr-general-x4v3": (4,),          # реальне відео, менше «пластиліну» (панель 28.08)
    "realesr-general-wdn-x4v3": (4,),      # те саме + вбудований денойз (для шумного/пожатого)
    "realesrgan-x4plus": (4,),
    "realesrgan-x4plus-anime": (4,),
    # «сильніші» (власник 28.08: детальна — топ, є ще?) — ESRGAN-клас, швидкість як x4plus
    "4x-UltraSharp-opt-fp16": (4,),
    "4x-NMKD-Siax-200k": (4,),
    "4xLSDIRplus": (4,),
}


def model_scales(model: str, default: tuple = (2, 3, 4)) -> tuple:
    """Масштаби моделі. Джерело правди — пул (Етап 6 п.4): моделі, які принесе розвідник,
    почнуть працювати без правок цього файлу. Таблиця вище лишається запасним дном."""
    return pool.scales_for(model) or MODEL_SCALES.get(model, default)


TILE_MAX = 512                      # більше — рушій тихо віддає чорні кадри (див. engine_cmd)

_PROBE_LOCK = threading.Lock()      # одна проба за раз (і server._idle_watch на нього дивиться)
_OWN_PIDS: set[int] = set()         # наші realesrgan-процеси — щоб не плутати з чужими


# ── Етап 4: операції «ЯК ще» + кодек ──────────────────────────────────────────────
# Порядок фільтрів фіксований (техплан): денойз ПЕРЕД нейромережею (інакше множимо шум),
# різкість і зерно — ПІСЛЯ, зведення до цілі — в кінці.
def norm_ops(d: dict | None) -> dict:
    d = d or {}
    st = load_settings()
    return {"sharpen": max(0.0, min(1.0, float(d.get("sharpen", st["sharpen"]) or 0))),
            "grain": bool(d.get("grain", st["grain"])),
            "denoise": bool(d.get("denoise", st["denoise"])),
            "codec": d.get("codec", st["codec"]) if d.get("codec", st["codec"]) in
                     ("libx264", "hevc_nvenc") else "libx264"}


def ops_pre_vf(ops: dict) -> str:
    return "hqdn3d=2:1.5:3:3" if ops.get("denoise") else ""


def ops_post_vf(ops: dict, default_sharpen: float = 0.0) -> str:
    parts = []
    sh = float(ops.get("sharpen", default_sharpen) or 0)
    if sh > 0:
        parts.append(f"cas={min(sh, 1.0):.2f}")
    if ops.get("grain"):
        parts.append("noise=alls=7:allf=t+u")       # дрібне кінозерно, що змінюється в часі
    return ",".join(parts)


def vf_chain(*parts: str) -> str:
    return ",".join(p for p in parts if p)


def _yielding() -> bool:
    return bool(load_settings().get("yield_to_stream", True)) and procs.stream_live()


def ff_threads(n: int = 8) -> list[str]:
    """Провали кодера ефіру (0.47x) давали НАШІ ffmpeg-кроки на всіх 16 P-потоках (розкладка
    PNG, кодування 4K). Поки ефір іде — лишаємо йому половину CPU (кодуванню — ще менше)."""
    return ["-threads", str(n)] if _yielding() else []


def ff_readrate(x: float) -> list[str]:
    """Обмежити швидкість читання входу (вхідна опція, ДО -i): дискові фази (PNG на A:, звідки
    ефір читає музику/озвучку) стають довшими, але плоскими — кодер ефіру не голодує."""
    return ["-readrate", f"{x:.2f}"] if _yielding() else []


def enc_args(codec: str, quality_crf: int = 16) -> list[str]:
    if codec == "hevc_nvenc":
        # NVENC ділиться з ефіром A1, але це ОКРЕМИЙ блок GPU; -cq 19 ≈ crf16 візуально
        return ["-c:v", "hevc_nvenc", "-preset", "p5", "-rc", "vbr", "-cq", "19", "-b:v", "0",
                "-pix_fmt", "yuv420p", "-tag:v", "hvc1"]
    return ["-c:v", "libx264", "-preset", "medium", "-crf", str(quality_crf), "-pix_fmt", "yuv420p"]


def engine2_ready() -> bool:
    """Другий рушій (torch/CUDA) поставлений? Без нього моделі .pth просто не показуються."""
    return ENGINE2_PY.exists() and (Path(__file__).parent / "engine2_runner.py").exists()


def engine_cmd(in_dir: Path, out_dir: Path, model: str, s: int,
               threads: str | None = None) -> list[str]:
    """Рядок рушія з налаштувань: потоки -j і тайл -t (тайл ≥200 — коли шви на небі).
    threads="1:1:1" — «м'який режим», коли ефір страждає (jobs вирішує посегментно).

    Модель сама каже, ЯКИМ рушієм її рахувати (pool.engine_of). Обидва рушії мають
    однаковий інтерфейс «тека→тека», тому jobs.py рахує прогрес і вбиває процес однаково."""
    if pool.engine_of(model) == "torch":
        # теки моделей/кешу рушій бере з оточення — виставляємо їх тут, а не зашиваємо
        # в engine2_runner.py (він запускається в іншому venv і config не бачить)
        import os
        os.environ["APSK_PTH_DIR"] = str(PTH_DIR)
        os.environ["APSK_ENGINE2_DIR"] = str(ENGINE2_DIR)
        return [str(ENGINE2_PY), str(Path(__file__).parent / "engine2_runner.py"),
                "-i", str(in_dir), "-o", str(out_dir), "-n", model,
                "-s", str(s), "-t", str(ENGINE2_TILE)]
    st = load_settings()
    # 🛡 28.08 (контрольований тест): з -j 1:1:1 кодер ефіру тримає 0.995-1.03x, рушій лише
    # −18%; з 1:2:2 — провали до 0.88. Тому поки ефір іде — один GPU-потік автоматично.
    if threads is None and st.get("yield_to_stream", True) and procs.stream_live():
        threads = "1:1:1"
    cmd = [str(REALESRGAN), "-i", str(in_dir), "-o", str(out_dir), "-n", model, "-s", str(s),
           "-g", GPU_ID, "-m", str(MODELS_DIR), "-f", "png",
           "-j", str(threads or st.get("threads") or "1:2:2")]
    try:
        tile = int(st.get("tile") or 0)
    except ValueError:
        tile = 0
    # 🚨 СТЕЛЯ ТАЙЛА (заміряно 08.09 на 3080 Ti з живим ефіром A1, UltraSharp ×4, вхід 1080p):
    #   128…512 — картинка правильна (SSIM 0.997-0.998 до авто, різниця лише на швах тайлів);
    #   ≥640    — рушію не вистачає відеопам'яті, і він НЕ падає, а віддає ЧОРНІ кадри з кодом 0
    #             (PNG 0.1 МБ замість 32.7, SSIM 0.002).
    # Швидкості тайл не додає взагалі (авто 5.22 с/кадр, 256 → 4.99, 512 → 5.03), тож єдине,
    # що тут можна зробити, — не дати вписати в settings.json число, яке тихо вбʼє рендер.
    if tile > TILE_MAX:
        tile = TILE_MAX
    if tile >= 32:
        cmd += ["-t", str(tile)]
    return cmd


def probe_busy() -> bool:
    return _PROBE_LOCK.locked()


def png_size(p: Path) -> tuple[int, int]:
    """Розмір PNG з заголовка — без картинкових бібліотек."""
    try:
        with open(p, "rb") as f:
            head = f.read(32)
    except OSError:
        return 0, 0
    if head[:8] == b"\x89PNG\r\n\x1a\n":
        w, h = struct.unpack(">II", head[16:24])
        return int(w), int(h)
    return 0, 0


def blank_output_check(sin: Path, sout: Path) -> str | None:
    """🚨 Заміряно 08.09: при браку відеопам'яті рушій НЕ падає — він тихо пише ЧОРНИЙ кадр
    і виходить з кодом 0 (тайл 1024 дав PNG на 96 КБ замість 32.7 МБ, SSIM 0.002 до
    правильного). Мовчазне чорне відео після годинного рендера — найгірший з можливих
    результатів, тому звіряємо «байт на піксель» виходу зі входом: справжня картинка після
    апскейлу не може важити в 20 разів менше за джерело. Порожній вхід (чорний кадр у самому
    відео) перевірку не вмикає — інакше ловили б фейди."""
    def bpp(d: Path) -> float:
        tot = px = 0
        for f in sorted(d.glob("*.png"))[:5]:
            w, h = png_size(f)
            if w:
                tot += f.stat().st_size
                px += w * h
        return tot / px if px else 0.0

    bi, bo = bpp(sin), bpp(sout)
    if bi > 0.02 and 0 < bo < bi / 20:
        return (f"рушій віддав порожні кадри ({bo:.4f} байт/піксель проти {bi:.3f} на вході) — "
                f"схоже, не вистачило відеопам'яті на тайл; зменш «тайл» у settings.json")
    return None


def _scale_vf(w: int, h: int, target_short: int) -> str:
    """Масштаб по КОРОТКІЙ стороні: вертикаль → ширина, горизонталь → висота."""
    return f"scale={target_short}:-2" if w < h else f"scale=-2:{target_short}"


def fit_vf(w: int, h: int, target_short: int) -> str:
    """Зведення до цілі В ОБИДВА БОКИ: менше → вгору, більше (8K-джерело при цілі 4K) → вниз.
    Етап 5: раніше «джерело ≥ цілі» лишалось як є — 8K віддавали 8K-ом."""
    short = min(w, h)
    if not short or short == target_short:
        return ""
    return _scale_vf(w, h, target_short) + ":flags=lanczos"


def plan_scale(src_short: int, target_short: int, scales=(2, 3, 4)) -> dict:
    """(масштаб рушія З МОЖЛИВИХ ДЛЯ МОДЕЛІ, чи зводити вниз, людська примітка)."""
    if src_short <= 0:
        return {"op": "none", "s": 1, "down": None, "note": "невідома роздільна"}
    if target_short <= src_short:
        return {"op": "clean", "s": 1, "down": None,
                "note": "це не апскейл — джерело вже таке або більше; тільки чистка й різкість"}
    for s in scales:
        if src_short * s == target_short:
            return {"op": "nn", "s": s, "down": None,
                    "note": f"×{s} рідним масштабом моделі — найдешевший шлях"}
    for s in scales:
        if src_short * s > target_short:
            return {"op": "nn", "s": s, "down": target_short,
                    "note": f"модель уміє лише ×{s} (вийде {src_short*s}p) → зведення вниз до "
                            f"{target_short}p: коштує стільки ж, а картинка менша"}
    s = scales[-1]
    return {"op": "nn", "s": s, "down": None,
            "note": f"максимум моделі ×{s} дає {src_short*s}p — вище не стрибнемо"}


# ── калібрування ETA ЗА ФАКТОМ ────────────────────────────────────────────────
# Таблиця в config.py заміряна 08-19 без живого ефіру; 28.08 поруч крутиться стрім A1
# (NVENC на тій самій карті) — і рушій дав 3.56 кадр/с замість 7.6. Одне красиве число,
# що бреше вдвічі, вбиває довіру, тому кожна NN-проба кліпу оновлює замір (EMA 50/50).
CALIB_PATH = DATA / "calib.json"
_CALIB: dict | None = None


def _calib() -> dict:
    global _CALIB
    if _CALIB is None:
        try:
            _CALIB = json.loads(CALIB_PATH.read_text(encoding="utf-8"))
        except Exception:
            _CALIB = {}
    return _CALIB


def calib_update(model: str, s, mpx_s: float) -> None:
    """Ключ «модель|масштаб» (нейромережа, мегапікселі/с) або «fast|ціль» (кадр/с кодування)."""
    if mpx_s <= 0:
        return
    c = _calib()
    k = f"{model}|{s}"
    c[k] = round(mpx_s if k not in c else c[k] * 0.5 + mpx_s * 0.5, 3)
    try:
        CALIB_PATH.write_text(json.dumps(c, indent=1), encoding="utf-8")
    except OSError:
        pass


def _throughput(model: str, s: int) -> float:
    """Швидкість: спершу ФАКТ із calib.json, далі таблиця БЕЗ крос-модельного фолбека:
    невідомий ключ НЕ сміє підставити найшвидшу модель замість найповільнішої."""
    v = _calib().get(f"{model}|{s}")
    if v:
        return float(v)
    v = THROUGHPUT_MPIX_S.get((model, s))
    if v is not None:
        return v
    same_model = [v for (m, _), v in THROUGHPUT_MPIX_S.items() if m == model]
    if same_model:
        return min(same_model)
    # модель, яку приніс розвідник: беремо ЙОГО оцінку за архітектурою, а не швидкість
    # найшвидшої моделі — інакше прогноз на важкому трансформері збреше в десятки разів
    est = pool.est_speed(model)
    if est > 0:
        return est
    return THROUGHPUT_MPIX_S.get((DEFAULT_MODEL, s), 4.0)


def estimate(info: dict, target_key: str, model: str) -> dict:
    """Прогноз: хвилини (ДІАПАЗОН), пік диска, розмір виходу. dur=0 → чесне «невідомо»."""
    short, dur, fps = info["short"], info["dur"], max(info["fps"], 1.0)
    target = TARGETS.get(target_key, 2160)
    plan = plan_scale(short, target, model_scales(model))
    clip_s = round(clip_eta_s(info, target_key, model))
    if dur <= 0.5:
        return {"plan": plan, "unknown": True, "minutes_lo": 0, "minutes_hi": 0,
                "peak_gb": 0, "out_gb": 0, "free_gb": round(disk_free_gb(), 1), "frames": 0,
                "clip_s": clip_s}
    frames = int(dur * fps)
    if plan["op"] != "nn" or model == "fast":
        # Етап 5: швидкий шлях коштує КАДРІВ ВИХОДУ (120-fps запис → 60 fps = удвічі більше
        # кадрів за 30-fps), а не секунд. Опора — заміряні кадр/с кодування 4K (calib «fast|ціль»),
        # дефолт 35 кадр/с (запис 1440p/120fps: 21000 кадрів за 672 с = 31).
        out_fps = min(fps, 60.0)
        enc_fps = float(_calib().get(f"fast|{target}") or 35.0 * (2160 / target) ** 1.5)
        minutes = dur * out_fps / enc_fps / 60
        lo, hi = minutes * 0.8, minutes * 1.5
        peak_gb = 1.0
    else:
        mpx = info["w"] * info["h"] / 1e6
        sec = frames * mpx / _throughput(model, plan["s"]) * 1.2
        lo, hi = sec / 60 * 0.85, sec / 60 * 1.4
        out_short = plan["down"] or short * plan["s"]
        # пік = один сегмент (бюджет 10 ГБ у jobs._seg_len_s) + збірка; не більше ~11 ГБ
        peak_gb = min(11.0, 10.0 * min(1.0, (out_short / 2160) ** 2 + 0.1) + 1.0)
    out_gb = dur / 60 * OUT_MB_PER_MIN_4K * ((target / 2160) ** 2) / 1000
    return {"plan": plan, "unknown": False,
            "minutes_lo": round(lo, 1), "minutes_hi": round(hi, 1),
            "peak_gb": round(peak_gb, 1), "out_gb": round(max(out_gb, 0.05), 2),
            "free_gb": round(disk_free_gb(), 1), "frames": frames, "clip_s": clip_s}


def gpu_busy_by_other() -> bool:
    """ЧУЖИЙ realesrgan (Автомонтаж) на GPU? Свої PID виключаємо — інакше власна проба
    показувала б «зайнятий Автомонтажем» (ревізія). Чужий процес не чіпаємо ніколи."""
    try:
        cp = run(["tasklist", "/FI", "IMAGENAME eq realesrgan-ncnn-vulkan.exe", "/FO", "CSV"],
                 timeout=10)
        for line in cp.stdout.splitlines():
            if not line.startswith('"realesrgan-ncnn-vulkan.exe"'):
                continue
            try:
                pid = int(line.split('","')[1].strip('"'))
            except (IndexError, ValueError):
                return True          # не розпарсили — вважаємо зайнятим (безпечніше)
            if pid not in _OWN_PIDS:
                return True
        return False
    except Exception:
        return False


def _run_engine(in_dir: Path, out_dir: Path, model: str, s: int) -> tuple[int, str]:
    """realesrgan через Popen — щоб знати СВІЙ pid (для чесного gpu_busy_by_other)."""
    proc = procs.spawn(engine_cmd(in_dir, out_dir, model, s),
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                       encoding="utf-8", errors="replace")
    _OWN_PIDS.add(proc.pid)
    # другий рушій на НОВІЙ роздільній спершу будує движок TensorRT (~2 хв на ESRGAN 1080p,
    # важчі архітектури й більші кадри — довше) + імпорт torch: 300 с для нього замало,
    # і проба брехала б «таймаут» саме там, де вона потрібна найбільше
    limit = 900 if pool.engine_of(model) == "torch" else 300
    try:
        _, err = proc.communicate(timeout=limit)
    except subprocess.TimeoutExpired:
        proc.kill()                 # вбиваємо ТІЛЬКИ власний процес — правило вшите
        return 1, f"таймаут {limit}с"
    finally:
        _OWN_PIDS.discard(proc.pid)
    return proc.returncode, err or ""


def probe_frame(src: Path, t: float, target_key: str, model: str, item_id: int,
                ops: dict | None = None) -> dict:
    """Проба 1 кадра. Серіалізована локом; будь-який збій — читабельна помилка, не 500."""
    if not _PROBE_LOCK.acquire(blocking=False):
        return {"error": "проба вже виконується — зачекай кілька секунд"}
    try:
        return _probe_frame_inner(src, t, target_key, model, item_id, norm_ops(ops))
    except Exception as e:
        return {"error": f"проба впала: {str(e)[:200]}"}
    finally:
        _PROBE_LOCK.release()


def _probe_frame_inner(src: Path, t: float, target_key: str, model: str,
                       item_id: int, ops: dict) -> dict:
    t0 = time.time()
    work = TMP / f"probe{item_id}"
    shutil.rmtree(work, ignore_errors=True)
    (work / "in").mkdir(parents=True, exist_ok=True)
    (work / "out").mkdir(parents=True, exist_ok=True)

    src_png = work / "in" / "f.png"
    if not extract_frame(src, t, src_png):
        return {"error": "не зміг витягти кадр — файл читається?"}
    if ops_pre_vf(ops):                               # денойз ПЕРЕД нейромережею
        den = work / "in" / "f_dn.png"
        run([FFMPEG, "-y", "-v", "error", "-i", src_png, "-vf", ops_pre_vf(ops), den], timeout=60)
        if den.exists():
            src_png.unlink(missing_ok=True)
            den.rename(src_png)
    w, h = png_size(src_png)
    if not w:
        return {"error": "битий кадр"}
    short = min(w, h)
    target = TARGETS.get(target_key, 2160)
    scales = model_scales(model)
    post = ops_post_vf(ops)

    if model == "fast" or plan_scale(short, target, scales)["op"] != "nn":
        after_png = work / "out" / "after.png"
        vf = vf_chain(fit_vf(w, h, target), post or "cas=0.4")
        cp = run([FFMPEG, "-y", "-v", "error", "-i", src_png, "-vf", vf, after_png],
                 timeout=60)
        if cp.returncode != 0 or not after_png.exists():
            return {"error": f"ffmpeg: {(cp.stderr or '')[:200]}"}
        out_png, mode = after_png, "⚡ lanczos+cas"
    else:
        plan = plan_scale(short, target, scales)
        rc, err = _run_engine(work / "in", work / "out", model, plan["s"])
        outs = list((work / "out").glob("*.png"))
        if rc != 0 or not outs:
            return {"error": f"рушій упав (код {rc}): {err[-200:]}"}
        out_png, mode = outs[0], f"🧠 {model} ×{plan['s']}"
        ow2, oh2 = png_size(out_png)
        vf = vf_chain(post, (_scale_vf(ow2 or w, oh2 or h, plan["down"]) + ":flags=lanczos")
                      if plan["down"] else "")
        if vf:                                        # різкість/зерно → зведення до цілі
            posted = work / "out" / "after_post.png"
            run([FFMPEG, "-y", "-v", "error", "-i", out_png, "-vf", vf, posted], timeout=60)
            if posted.exists():
                out_png = posted

    ow, oh = png_size(out_png)
    if not ow:
        ow, oh = w, h
    before_jpg, after_jpg = work / "before.jpg", work / "after.jpg"
    return _finish_probe_frame(src_png, out_png, before_jpg, after_jpg, ow, oh, mode,
                               item_id, t0)


def _finish_probe_frame(src_png, out_png, before_jpg, after_jpg, ow, oh, mode, item_id, t0):
    run([FFMPEG, "-y", "-v", "error", "-i", src_png,
         "-vf", f"scale={ow}:{oh}:flags=lanczos", "-q:v", "2", before_jpg], timeout=60)
    run([FFMPEG, "-y", "-v", "error", "-i", out_png, "-q:v", "2", after_jpg], timeout=60)
    if not (before_jpg.exists() and after_jpg.exists()):
        return {"error": "не зібрав порівняння"}
    return {"before": f"/probe_img/{item_id}/before.jpg",
            "after": f"/probe_img/{item_id}/after.jpg",
            "w": ow, "h": oh, "mode": mode,
            "ms": int((time.time() - t0) * 1000)}


# ── ЕТАП 2: проба 10 секунд ─────────────────────────────────────────────────────
# Мерехтіння між кадрами (flicker) на ОДНОМУ кадрі не видно принципово — а саме воно
# найчастіше псує враження від апскейлу. Тому: 10 с через той самий конвеєр, що буде в
# Етапі 3 (кадри → рушій тека→тека → збірка), два відео однакового розміру і fps.
CLIP_SECS = 10.0
CLIP_PROGRESS = {"phase": "", "done": 0, "total": 0, "t0": 0.0, "fps": 0.0}
_CLIP_CANCEL = threading.Event()


def clip_eta_s(info: dict, target_key: str, model: str, secs: float = CLIP_SECS) -> float:
    """Чесна оцінка тривалості проби-кліпу — для підпису на кнопці (x4plus → десятки хвилин)."""
    fps = min(max(float(info.get("fps") or 30.0), 1.0), 60.0)
    short = int(info.get("short") or 0)
    target = TARGETS.get(target_key, 2160)
    plan = plan_scale(short, target, model_scales(model))
    if model == "fast" or plan["op"] != "nn":
        return 6 + secs * 0.8
    frames = secs * fps
    mpx = int(info["w"]) * int(info["h"]) / 1e6
    return 10 + frames * mpx / _throughput(model, plan["s"]) * 1.15 + frames / 20


def probe_clip_cancel():
    _CLIP_CANCEL.set()


def _video_size(p: Path) -> tuple[int, int]:
    cp = run([FFPROBE, "-v", "error", "-select_streams", "v:0", "-show_entries",
              "stream=width,height", "-of", "csv=p=0", p], timeout=30)
    try:
        w, h = cp.stdout.strip().split(",")[:2]
        return int(w), int(h)
    except Exception:
        return 0, 0


def _run_engine_watched(in_dir: Path, out_dir: Path, model: str, s: int,
                        total: int) -> tuple[int, str]:
    """Як _run_engine, але з лічильником ГОТОВИХ КАДРІВ (файли у вихідній теці раз на
    0.5 с — рушій прогресу не друкує) і скасуванням. stdout/stderr у файл: рушій пише
    рядок на кадр, і 64 КБ pipe-буфера могли б його заблокувати намертво."""
    log = in_dir.parent / "engine.log"
    with open(log, "w", encoding="utf-8", errors="replace") as lf:
        proc = procs.spawn(engine_cmd(in_dir, out_dir, model, s),
                           stdout=lf, stderr=subprocess.STDOUT)
        _OWN_PIDS.add(proc.pid)
        t0 = time.time()
        try:
            while proc.poll() is None:
                time.sleep(0.5)
                done = sum(1 for _ in out_dir.glob("*.png"))
                el = max(time.time() - t0, 0.01)
                CLIP_PROGRESS.update(done=done, total=total, fps=round(done / el, 2))
                if _CLIP_CANCEL.is_set() or el > 3600:
                    proc.kill()                      # ТІЛЬКИ свій pid — правило вшите
                    proc.wait(timeout=10)
                    return 1, "скасовано" if _CLIP_CANCEL.is_set() else "таймаут 1 год"
        finally:
            _OWN_PIDS.discard(proc.pid)
    try:
        err = log.read_text(encoding="utf-8", errors="replace")[-400:]
    except OSError:
        err = ""
    return proc.returncode, err


def probe_clip(src: Path, t: float, target_key: str, model: str, item_id: int,
               info: dict, ops: dict | None = None) -> dict:
    if not _PROBE_LOCK.acquire(blocking=False):
        return {"error": "проба вже виконується — зачекай"}
    _CLIP_CANCEL.clear()
    try:
        return _probe_clip_inner(src, t, target_key, model, item_id, info, norm_ops(ops))
    except Exception as e:
        return {"error": f"проба кліпу впала: {str(e)[:200]}"}
    finally:
        CLIP_PROGRESS.update(phase="", done=0, total=0, t0=0.0, fps=0.0)
        _PROBE_LOCK.release()


def _probe_clip_inner(src: Path, t: float, target_key: str, model: str, item_id: int,
                      info: dict, ops: dict) -> dict:
    t0 = time.time()
    pre, post = ops_pre_vf(ops), ops_post_vf(ops)
    secs = CLIP_SECS
    dur = float(info.get("dur") or 0)
    if dur > 1:                                   # кліп не сміє вилазити за кінець файлу
        t = max(0.0, min(float(t), max(0.0, dur - secs - 0.3)))
        secs = max(1.0, min(secs, dur - t - 0.1))
    fps = round(min(max(float(info.get("fps") or 30.0), 1.0), 60.0), 3)
    if disk_free_gb() < 6:
        return {"error": f"мало місця на A: ({disk_free_gb():.1f} ГБ) — кліп потребує "
                         f"~4 ГБ тимчасово"}
    w, h = int(info["w"]), int(info["h"])
    short = min(w, h)
    target = TARGETS.get(target_key, 2160)
    plan = plan_scale(short, target, model_scales(model))
    work = TMP / f"clip{item_id}"
    shutil.rmtree(work, ignore_errors=True)
    (work / "in").mkdir(parents=True, exist_ok=True)
    (work / "out").mkdir(parents=True, exist_ok=True)
    after, before = work / "after.mp4", work / "before.mp4"
    # -g 15: ключовий кадр кожні пів секунди — сік у плеєрі порівняння дешевий
    enc = ["-c:v", "libx264", "-preset", "fast", "-crf", "16", "-pix_fmt", "yuv420p",
           "-g", "15", "-an", "-movflags", "+faststart"]
    even = "scale=trunc(iw/2)*2:trunc(ih/2)*2"    # yuv420p вимагає парних розмірів
    total = int(round(secs * fps))
    CLIP_PROGRESS.update(phase="розкладаю кадри", done=0, total=total, t0=time.time(), fps=0.0)
    eng_fps = 0.0

    if model == "fast" or plan["op"] != "nn":
        CLIP_PROGRESS["phase"] = "швидкий шлях"
        vf = vf_chain(f"fps={fps}", pre, fit_vf(w, h, target), post or "cas=0.4", even)
        cp = run([FFMPEG, "-y", "-v", "error", "-ss", f"{t:.3f}", "-t", f"{secs:.3f}",
                  "-i", src, "-vf", vf, *enc, after], timeout=900)
        if cp.returncode != 0 or not after.exists():
            return {"error": f"ffmpeg: {(cp.stderr or '')[-200:]}"}
        mode = "⚡ lanczos+cas"
    else:
        cp = run([FFMPEG, "-y", "-v", "error", "-ss", f"{t:.3f}", "-t", f"{secs:.3f}",
                  "-i", src, "-vf", vf_chain(f"fps={fps}", pre),
                  work / "in" / "%06d.png"], timeout=900)
        n_in = sum(1 for _ in (work / "in").glob("*.png"))
        if cp.returncode != 0 or n_in == 0:
            return {"error": f"не розклав кадри: {(cp.stderr or '')[-200:]}"}
        total = n_in
        CLIP_PROGRESS.update(phase="нейромережа", total=n_in, t0=time.time())
        rc, err = _run_engine_watched(work / "in", work / "out", model, plan["s"], n_in)
        if _CLIP_CANCEL.is_set():
            shutil.rmtree(work, ignore_errors=True)
            return {"error": "скасовано", "canceled": True}
        n_out = sum(1 for _ in (work / "out").glob("*.png"))
        if rc != 0 or n_out < n_in:
            return {"error": f"рушій упав (код {rc}, кадрів {n_out}/{n_in}): {err[-200:]}"}
        blank = blank_output_check(work / "in", work / "out")
        if blank:
            return {"error": blank}
        total = n_out
        eng_fps = CLIP_PROGRESS["fps"]
        if n_in >= 60:                                # короткий кліп — шумний замір, не пишемо
            calib_update(model, plan["s"], eng_fps * w * h / 1e6)
        CLIP_PROGRESS["phase"] = "збираю відео"
        ow2, oh2 = png_size(next((work / "out").glob("*.png")))
        vf = vf_chain(post, (_scale_vf(ow2 or w, oh2 or h, plan["down"]) + ":flags=lanczos")
                      if plan["down"] else "", even)
        cp = run([FFMPEG, "-y", "-v", "error", "-framerate", f"{fps}",
                  "-i", work / "out" / "%06d.png", "-vf", vf, *enc, after], timeout=900)
        if cp.returncode != 0 or not after.exists():
            return {"error": f"не зібрав кліп: {(cp.stderr or '')[-200:]}"}
        mode = f"🧠 {model} ×{plan['s']}"

    ow, oh = _video_size(after)
    if not ow:
        return {"error": "вихідний кліп не читається"}
    # «до» — той самий шматок, той самий fps, зведений lanczos-ом до розміру «після»
    CLIP_PROGRESS["phase"] = "готую «до»"
    # -frames:v = стільки ж кадрів, скільки в «після»: інакше межа -t давала 300 проти 301
    # і плеєри розʼїжджались на кадр після кожного кола
    cp = run([FFMPEG, "-y", "-v", "error", "-ss", f"{t:.3f}", "-t", f"{secs + 0.5:.3f}",
              "-i", src, "-vf", f"fps={fps},scale={ow}:{oh}:flags=lanczos",
              "-frames:v", str(total), *enc, before], timeout=900)
    shutil.rmtree(work / "in", ignore_errors=True)      # кадри — гігабайти, чистимо одразу
    shutil.rmtree(work / "out", ignore_errors=True)
    if cp.returncode != 0 or not before.exists():
        return {"error": f"не зібрав «до»: {(cp.stderr or '')[-200:]}"}
    return {"before": f"/probe_clip/{item_id}/before.mp4",
            "after": f"/probe_clip/{item_id}/after.mp4",
            "w": ow, "h": oh, "fps": fps, "secs": round(secs, 2), "t": round(float(t), 2),
            "frames": total, "engine_fps": eng_fps, "mode": mode,
            "ms": int((time.time() - t0) * 1000)}
