# -*- coding: utf-8 -*-
"""📏 Метрики якості апскейлу — запускається у ВАЖКОМУ venv рушія 2 (torch + lpips).

    python quality_metrics.py <тека_еталонів> <тека_виходів>
Пари беруться за іменем файлу. На stdout — один JSON:
    {"frames": [{"name", "lpips", "psnr", "ssim"}], "lpips", "psnr", "ssim", "n"}

LPIPS (AlexNet) — перцептивна відстань: менше = ближче до оригіналу НА ОКО. Саме вона, а не
PSNR, бо GAN-моделі (UltraSharp) дають різкішу картинку з гіршим PSNR — і власник обрав їх
оком. PSNR/SSIM рахуємо теж — для запису, не для чіпа.
Ваги AlexNet качаються в TORCH_HOME — викликач (quality.py) ставить його в теку даних,
щоб не засмічувати системний диск; без нього — дефолт torch.
"""
from __future__ import annotations
import json, math, os, sys
from pathlib import Path


def _load(p: Path, device):
    import numpy as np, torch
    from PIL import Image
    arr = np.asarray(Image.open(p).convert("RGB"), dtype=np.uint8)
    x = torch.from_numpy(arr).to(device).permute(2, 0, 1).unsqueeze(0).float().div_(255.0)
    return x                                    # [1,3,H,W] у 0..1


def _ssim(a, b):
    """SSIM по сірому з гаусовим вікном 11 — класична формула, без skimage."""
    import torch, torch.nn.functional as F
    g = lambda x: 0.299 * x[:, 0:1] + 0.587 * x[:, 1:2] + 0.114 * x[:, 2:3]
    a, b = g(a), g(b)
    k = torch.arange(11, dtype=torch.float32, device=a.device) - 5
    k = torch.exp(-k ** 2 / (2 * 1.5 ** 2)); k = (k / k.sum())
    w = (k[:, None] * k[None, :])[None, None]
    mu_a, mu_b = F.conv2d(a, w, padding=5), F.conv2d(b, w, padding=5)
    sa = F.conv2d(a * a, w, padding=5) - mu_a ** 2
    sb = F.conv2d(b * b, w, padding=5) - mu_b ** 2
    sab = F.conv2d(a * b, w, padding=5) - mu_a * mu_b
    c1, c2 = 0.01 ** 2, 0.03 ** 2
    s = ((2 * mu_a * mu_b + c1) * (2 * sab + c2)) / ((mu_a ** 2 + mu_b ** 2 + c1) * (sa + sb + c2))
    return float(s.mean())


def main() -> int:
    import torch
    gt_dir, out_dir = Path(sys.argv[1]), Path(sys.argv[2])
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    import lpips
    net = lpips.LPIPS(net="alex", verbose=False).to(device).eval()
    frames = []
    for gp in sorted(gt_dir.glob("*.png")):
        op = out_dir / gp.name
        if not op.exists():
            continue
        with torch.no_grad():
            a, b = _load(gp, device), _load(op, device)
            if a.shape != b.shape:                        # страховка: розміри мають збігатись
                b = torch.nn.functional.interpolate(b, size=a.shape[-2:], mode="bicubic",
                                                    align_corners=False).clamp_(0, 1)
            mse = float(((a - b) ** 2).mean())
            psnr = 10 * math.log10(1.0 / mse) if mse > 0 else 99.0
            d = float(net(a * 2 - 1, b * 2 - 1))
            s = _ssim(a, b)
        frames.append({"name": gp.name, "lpips": round(d, 4), "psnr": round(psnr, 2), "ssim": round(s, 4)})
        del a, b
        torch.cuda.empty_cache()
    if not frames:
        print(json.dumps({"error": "нема пар кадрів"}, ensure_ascii=False))
        return 1
    n = len(frames)
    agg = {k: round(sum(f[k] for f in frames) / n, 4) for k in ("lpips", "psnr", "ssim")}
    print(json.dumps({"frames": frames, "n": n, **agg}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(json.dumps({"error": f"{type(e).__name__}: {e}"}, ensure_ascii=False))
        sys.exit(1)
