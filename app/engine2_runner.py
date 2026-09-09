# -*- coding: utf-8 -*-
"""🚀 ДРУГИЙ РУШІЙ — PyTorch/CUDA замість ncnn-Vulkan (рішення власника 08.09: «4 онли»).

НАВІЩО. Замір 08.09: ncnn-Vulkan дає 4.6-4.9 с на кадр 1080p для всього ESRGAN-класу
(UltraSharp/Siax/x4plus) = 23 години на 10-хв відео. Vulkan-бекенд ncnn не використовує
тензорні ядра RTX, і це стеля, яку не обійти налаштуваннями (перевірено: потоки, тайли,
пріоритети дали разом ×1.06). PyTorch+cuDNN у fp16 їх використовує.

ДРУГА ПРИЧИНА. Рушій ncnn їсть ЛИШЕ `.param`+`.bin`, а 90% моделей OpenModelDB — `.pth`.
Через spandrel цей рушій вантажить `.pth`/`.safetensors` НАПРЯМУ і розуміє десятки
архітектур (ESRGAN, SPAN, DAT, HAT, OmniSR, Compact…), тобто розблоковує розвідника
(Етап 6 п.1-3) без конвертацій.

ЦЕЙ ФАЙЛ ЖИВЕ В ГІТІ, А ЗАЛЕЖНОСТІ — В ТЕЦІ ДАНИХ. Запускає його ОКРЕМИЙ важкий venv
`<дані>\\engine2\\.venv` (torch+CUDA ~8 ГБ, ставить tools\\setup_engine2.ps1). Тонкий venv
самої проги (fastapi/uvicorn/pywebview) лишається чистим — прога працює й без цього рушія.
Теки моделей і кешу передає викликач через оточення APSK_PTH_DIR / APSK_ENGINE2_DIR.

ІНТЕРФЕЙС НАВМИСНЕ ТАКИЙ САМИЙ, ЯК У БІНАРНИКА ncnn (тека→тека, ті самі ключі):
    python engine2_runner.py -i <тека> -o <тека> -n <модель> -s <масштаб> [-t тайл]
щоб `jobs.py` рахував прогрес тим самим способом (лічильник готових PNG) і вбивав
процес тим самим правилом (тільки свій PID).

Код повернення: 0 — усі кадри готові; 1 — будь-яка біда (з людським текстом у stderr).
"""
from __future__ import annotations
import argparse, os, sys, time
from pathlib import Path

# теки від викликача (engine.py ставить їх з config); дефолт — поруч зі скриптом, щоб
# рушій можна було запустити й руками для перевірки
_HERE = Path(__file__).resolve().parent
PTH_DIR = Path(os.getenv("APSK_PTH_DIR") or _HERE.parent / "models" / "pth")
OVERLAP = 16          # перекриття тайлів у пікселях ВХОДУ: шви ESRGAN ховаються за 8-16 px
ENGINE2_DIR = Path(os.getenv("APSK_ENGINE2_DIR") or _HERE.parent / "engine2")
TRT_CACHE = ENGINE2_DIR / "trt_cache"
ONNX_CACHE = ENGINE2_DIR / "onnx"


def log(msg: str) -> None:
    print(msg, flush=True)


def load_model(name: str, device, want_fp16: bool):
    """spandrel сам упізнає архітектуру по вагах — нам не треба знати, що це за модель."""
    import torch
    from spandrel import ModelLoader

    path = None
    for ext in (".pth", ".safetensors", ".ckpt"):
        p = PTH_DIR / f"{name}{ext}"
        if p.exists():
            path = p
            break
    if path is None:
        raise SystemExit(f"нема файлу моделі {name}.pth у {PTH_DIR}")

    descr = ModelLoader(device=device).load_from_file(str(path))
    model = descr.model.eval().to(device)
    fp16 = want_fp16 and device.type == "cuda" and descr.supports_half
    if fp16:
        model = model.half()
    # channels_last: без нього cuDNN бере звичайні згорткові ядра замість тензорних —
    # на RTX це різниця в рази, і саме вона визначає, чи є сенс у цьому рушії взагалі
    try:
        model = model.to(memory_format=torch.channels_last)
    except Exception:
        pass
    for p in model.parameters():
        p.requires_grad_(False)
    log(f"модель {path.name} · {descr.architecture.name} · ×{descr.scale} · "
        f"{'fp16' if fp16 else 'fp32'} · вхід {descr.input_channels}ch")
    return model, descr, fp16


# ── TensorRT: найшвидший шлях ──────────────────────────────────────────────────
# Заміряно 08.09 (UltraSharp ×4, вхід 1080p, ефір живий):
#   ncnn-Vulkan        4.51 с/кадр
#   torch eager fp16   3.08
#   TensorRT fp16      1.36  ← ×3.3 до ncnn
# Ціна: движок будується під КОНКРЕТНУ роздільну входу (хвилини) і кладеться в кеш —
# другий раз на тій самій роздільній підхоплюється миттєво. Будь-яка невдача = тихий
# відкат на torch, бо працюючий повільний рушій кращий за непрацюючий швидкий.
def _dll_dirs() -> None:
    """ORT/TensorRT самі не бачать cudnn і cublas, що лежать у torch — підкладаємо."""
    import os
    from pathlib import Path as _P
    sp = _P(__file__).parent          # заглушка, реальні шляхи нижче
    venv = ENGINE2_DIR / ".venv" / "Lib" / "site-packages"
    for d in (venv / "torch" / "lib", venv / "tensorrt_libs"):
        if d.exists():
            try:
                os.add_dll_directory(str(d))
            except Exception:
                pass
            os.environ["PATH"] = str(d) + os.pathsep + os.environ.get("PATH", "")


class TrtRunner:
    """Обгортка над зібраним движком: приймає і віддає torch-тензори на GPU."""

    def __init__(self, ctx, engine, trt, out_shape, in_name, out_name):
        self.ctx, self.engine, self.trt = ctx, engine, trt
        self.out_shape, self.in_name, self.out_name = out_shape, in_name, out_name

    def infer(self, x):
        import torch
        # 🚨 NCHW-копію тримаємо у змінній до кінця виклику: `x.contiguous().data_ptr()`
        # віддавав адресу ТИМЧАСОВОГО тензора, який Python звільняв ще до запуску движка —
        # працювало лише тому, що кеш-алокатор torch не встигав віддати блок комусь іншому.
        xc = x.contiguous()
        y = torch.empty(self.out_shape, dtype=torch.float16, device="cuda")
        self.ctx.set_tensor_address(self.in_name, int(xc.data_ptr()))
        self.ctx.set_tensor_address(self.out_name, int(y.data_ptr()))
        ok = self.ctx.execute_async_v3(torch.cuda.current_stream().cuda_stream)
        torch.cuda.synchronize()
        del xc
        if not ok:
            raise RuntimeError("execute_async_v3 повернув False")
        return y


def build_trt(model, name: str, h: int, w: int):
    """Дістає з кешу або будує движок під (модель, роздільна). None = не вийшло."""
    import torch
    _dll_dirs()
    try:
        import tensorrt as trt
    except Exception as e:
        log(f"TensorRT недоступний ({type(e).__name__}) — рахую звичайним torch")
        return None
    TRT_CACHE.mkdir(parents=True, exist_ok=True)
    ONNX_CACHE.mkdir(parents=True, exist_ok=True)
    plan_path = TRT_CACHE / f"{name}_{h}x{w}_fp16.plan"
    logger = trt.Logger(trt.Logger.ERROR)
    try:
        if not plan_path.exists():
            onnx_path = ONNX_CACHE / f"{name}_{h}x{w}_fp16.onnx"
            if not onnx_path.exists():
                log(f"будую движок TensorRT під {w}×{h} (один раз, кілька хвилин)…")
                dummy = torch.randn(1, 3, h, w, device="cuda", dtype=torch.float16)
                with torch.no_grad():
                    torch.onnx.export(model, dummy, str(onnx_path), opset_version=17,
                                      input_names=["x"], output_names=["y"], dynamo=False)
                del dummy
                torch.cuda.empty_cache()
            builder = trt.Builder(logger)
            # 🚨 TensorRT 11 прибрав BuilderFlag.FP16: точність тепер береться з ONNX,
            # тому мережа СТРОГО ТИПІЗОВАНА, а ONNX експортовано вже в half
            net = builder.create_network(
                1 << int(trt.NetworkDefinitionCreationFlag.STRONGLY_TYPED))
            parser = trt.OnnxParser(net, logger)
            if not parser.parse(onnx_path.read_bytes()):
                log("TensorRT: ONNX не розпарсився — відкат на torch")
                return None
            cfg = builder.create_builder_config()
            cfg.set_memory_pool_limit(trt.MemoryPoolType.WORKSPACE, 3 << 30)
            # 🚨 Збірка мовчить хвилинами, а сторож черги (jobs.STALL_S=180) вважає мовчання
            # зависанням і вбиває процес. Тому цокаємо в журнал — це і є ознака життя.
            import threading
            done = threading.Event()

            def _tick():
                t = time.time()
                while not done.wait(25):
                    log(f"  …збираю движок, минуло {int(time.time() - t)} с")

            threading.Thread(target=_tick, daemon=True).start()
            try:
                plan = builder.build_serialized_network(net, cfg)
            finally:
                done.set()
            if plan is None:
                log("TensorRT: движок не зібрався — відкат на torch")
                return None
            plan_path.write_bytes(plan)
            log(f"движок готовий ({plan_path.stat().st_size / 1e6:.0f} МБ), далі з кешу")
        engine = trt.Runtime(logger).deserialize_cuda_engine(plan_path.read_bytes())
        ctx = engine.create_execution_context()
        names = [engine.get_tensor_name(i) for i in range(engine.num_io_tensors)]
        i_name = next(n for n in names if engine.get_tensor_mode(n) == trt.TensorIOMode.INPUT)
        o_name = next(n for n in names if engine.get_tensor_mode(n) == trt.TensorIOMode.OUTPUT)
        return TrtRunner(ctx, engine, trt, tuple(ctx.get_tensor_shape(o_name)), i_name, o_name)
    except Exception as e:
        log(f"TensorRT не пішов ({type(e).__name__}: {str(e)[:120]}) — рахую звичайним torch")
        return None


def _infer(model, x):
    """no_grad, а НЕ inference_mode: у inference_mode результат стає «inference tensor»,
    який не можна ні клампити на місці, ні класти у спільний буфер тайлів
    (RuntimeError: Inplace update to inference tensor…). Швидкість та сама."""
    import torch
    with torch.no_grad():
        return model(x)


def upscale(model, img, scale: int, tile: int):
    """Тайлами з перекриттям — інакше 1080p×4 не влазить у 12 ГБ на важких архітектурах.
    tile=0 → одним куском (швидше, коли пам'яті вистачає)."""
    import torch
    import torch.nn.functional as F

    _, _, h, w = img.shape
    if tile <= 0 or (h <= tile and w <= tile):
        return _infer(model, img)

    out = torch.zeros((1, img.shape[1], h * scale, w * scale),
                      dtype=img.dtype, device=img.device)
    for y0 in range(0, h, tile):
        for x0 in range(0, w, tile):
            y1, x1 = min(y0 + tile, h), min(x0 + tile, w)
            # беремо з полями, рахуємо, і кладемо назад БЕЗ полів — так шва не видно
            py0, px0 = max(0, y0 - OVERLAP), max(0, x0 - OVERLAP)
            py1, px1 = min(h, y1 + OVERLAP), min(w, x1 + OVERLAP)
            piece = _infer(model, img[:, :, py0:py1, px0:px1])
            ty0, tx0 = (y0 - py0) * scale, (x0 - px0) * scale
            out[:, :, y0 * scale:y1 * scale, x0 * scale:x1 * scale] = \
                piece[:, :, ty0:ty0 + (y1 - y0) * scale, tx0:tx0 + (x1 - x0) * scale]
            del piece
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--input", required=True)
    ap.add_argument("-o", "--output", required=True)
    ap.add_argument("-n", "--model", required=True)
    ap.add_argument("-s", "--scale", type=int, default=4)
    ap.add_argument("-t", "--tile", type=int, default=0)
    ap.add_argument("--fp32", action="store_true", help="без half (діагностика)")
    ap.add_argument("--no-trt", action="store_true", help="не вмикати TensorRT (діагностика)")
    a = ap.parse_args()

    import numpy as np
    import torch
    from PIL import Image

    if not torch.cuda.is_available():
        log("CUDA недоступна — цей рушій без відеокарти не має сенсу")
        return 1
    device = torch.device("cuda")
    torch.backends.cudnn.benchmark = True          # розміри кадрів однакові → кеш планів
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True

    src, dst = Path(a.input), Path(a.output)
    dst.mkdir(parents=True, exist_ok=True)
    files = sorted([p for p in src.iterdir() if p.suffix.lower() in (".png", ".jpg", ".jpeg")])
    if not files:
        log(f"у {src} нема кадрів")
        return 1

    model, descr, fp16 = load_model(a.model, device, not a.fp32)
    scale = int(descr.scale or a.scale)
    if a.scale and descr.scale and int(descr.scale) != a.scale:
        log(f"⚠ модель уміє лише ×{descr.scale}, попросили ×{a.scale} — рахую ×{descr.scale}")

    # 🚨 ЗАМІР 08.09: сама модель рахує кадр 1080p за 3.1 с, а перша версія цього рушія
    # видавала 8.6 — 5.5 с з'їдав МІЙ ввід-вивід, поки GPU стояв:
    #   ① з карти тягнувся тензор fp32 (7680×4320×3×4 = 398 МБ) — переводимо в uint8 НА GPU
    #     і веземо 99 МБ замість 398;
    #   ② PNG 33 МБ кодувався в тому ж потоці — виносимо в окремі потоки, щоб кодування
    #     кадру N ішло паралельно з рахунком кадру N+1 (саме так і робить ncnn своїм -j);
    #   ③ читання наступних кадрів теж заздалегідь, з обмеженим запасом (пам'ять не пухне).
    from concurrent.futures import ThreadPoolExecutor
    from collections import deque

    def _read(p: Path):
        return np.asarray(Image.open(p).convert("RGB"), dtype=np.uint8)

    def _write(p: Path, arr):
        # compress_level=3, а не 1: кодування і так іде в окремих потоках паралельно з
        # рахунком наступного кадру (запас великий — GPU зайнятий 3 с на кадр), а от розмір
        # важить: на рівні 1 кадр 4320p виходив 48.5 МБ проти 32.75 у ncnn, і бюджет диска
        # на сегмент (10 ГБ) вигоряв швидше, ніж рахує jobs._seg_len_s
        Image.fromarray(arr).save(p, compress_level=3)

    # TensorRT будується під конкретну роздільну — беремо її з першого кадру
    trt_run, fh, fw = None, 0, 0
    if not a.no_trt and fp16 and a.tile <= 0:
        with Image.open(files[0]) as im:
            fw, fh = im.size
        trt_run = build_trt(model, a.model, fh, fw)
        if trt_run is not None:
            log(f"рахую через TensorRT (вихід {trt_run.out_shape})")

    t0 = time.time()
    readers, writers = ThreadPoolExecutor(2), ThreadPoolExecutor(3)
    prefetch: deque = deque()
    written: deque = deque()
    try:
        for f in files[:3]:
            prefetch.append((f, readers.submit(_read, f)))
        nxt = 3
        for i in range(1, len(files) + 1):
            f, fut = prefetch.popleft()
            if nxt < len(files):
                prefetch.append((files[nxt], readers.submit(_read, files[nxt])))
                nxt += 1
            arr = fut.result()
            x = torch.from_numpy(arr).to(device).permute(2, 0, 1).unsqueeze(0)
            x = (x.half() if fp16 else x.float()).div_(255.0)
            x = x.contiguous(memory_format=torch.channels_last)
            y = None
            # TensorRT лише для half-кадру тієї роздільної, під яку зібрано движок: він
            # читає буфер як half, і fp32-тензор дав би не помилку, а тихе сміття в PNG
            if trt_run is not None and x.dtype == torch.float16 and x.shape[-2:] == (fh, fw):
                try:
                    y = trt_run.infer(x)
                except Exception as e:      # і брак VRAM, і відмова движка → далі звичайним torch
                    torch.cuda.empty_cache()
                    log(f"⚠ TensorRT відмовив на кадрі {i} ({type(e).__name__}) — далі звичайним torch")
                    trt_run = None
            if y is None:
                try:
                    y = upscale(model, x, scale, a.tile)
                except torch.cuda.OutOfMemoryError:
                    torch.cuda.empty_cache()
                    log("⚠ не вистачило VRAM на цілий кадр — перемикаюсь на тайли 512")
                    a.tile, trt_run = 512, None       # TensorRT рахує лише цілий кадр
                    y = upscale(model, x, scale, a.tile)
            # 🚨 fp16 на деяких архітектурах дає NaN — краще перерахувати кадр у fp32,
            # ніж мовчки записати чорний PNG (та сама пастка, що в ncnn при браку VRAM).
            # TensorRT при цьому ВИМИКАЄМО назавжди: його движок зібрано під half.
            if not torch.isfinite(y).all():
                log("⚠ fp16 дав NaN — переганяю в fp32 (далі всі кадри так)")
                model, fp16, trt_run = model.float(), False, None
                x = x.float()
                try:
                    y = upscale(model, x, scale, a.tile)
                except torch.cuda.OutOfMemoryError:
                    torch.cuda.empty_cache()
                    log("⚠ fp32 не влазить у VRAM цілим кадром — тайли 512")
                    a.tile = 512
                    y = upscale(model, x, scale, a.tile)
            # у uint8 ПЕРЕД дорогою через PCIe
            out = (y.clamp(0, 1).mul_(255).round_().to(torch.uint8)
                   .squeeze(0).permute(1, 2, 0).contiguous().cpu().numpy())
            del x, y
            written.append(writers.submit(_write, dst / f"{f.stem}.png", out))
            while len(written) > 3:                 # не даємо черзі запису розповзтись
                written.popleft().result()
            if i % 10 == 0 or i == len(files):
                el = time.time() - t0
                log(f"{i}/{len(files)} · {el / i:.2f} с/кадр")
        for w in written:
            w.result()
    finally:
        readers.shutdown(wait=True)
        writers.shutdown(wait=True)

    el = time.time() - t0
    peak = torch.cuda.max_memory_allocated() / 2**30
    total = torch.cuda.get_device_properties(0).total_memory / 2**30
    log(f"готово: {len(files)} кадрів за {el:.1f} с = {el / len(files):.2f} с/кадр · "
        f"пік VRAM {peak:.2f} / {total:.1f} ГБ")
    if peak > total * 0.75:
        log("⚠ пік близько до межі карти — драйвер міг зливати пам'ять у системну "
            "через PCIe (це не падіння, це просто в рази повільніше). Спробуй менший тайл.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as e:
        log(f"рушій2 впав: {type(e).__name__}: {e}")
        sys.exit(1)
