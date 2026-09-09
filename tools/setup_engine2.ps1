# Apskeyl — optional ENGINE 2 (PyTorch + CUDA + TensorRT). NVIDIA GPUs only.
# Why: ~2.5x faster than the Vulkan engine on ESRGAN-class models (UltraSharp, Siax, x4plus)
# and it loads .pth/.safetensors directly -> most of OpenModelDB becomes usable.
# Cost: ~8 GB of wheels. Installed into <data dir>\engine2\.venv, NOT next to the app,
# because the data dir is where you have space. Re-run to repair.
# ASCII-only on purpose.

param([string]$DataDir = "")
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

function Say($m) { Write-Host "  $m" }
function Head($m) { Write-Host ""; Write-Host "== $m ==" -ForegroundColor Cyan }

# data dir: argument > APSK_DATA > apskeyl.json
if (-not $DataDir) { $DataDir = $env:APSK_DATA }
if (-not $DataDir -and (Test-Path "apskeyl.json")) {
    $DataDir = (Get-Content apskeyl.json -Raw | ConvertFrom-Json).data_dir
}
if (-not $DataDir) {
    Write-Host "  Data dir unknown. Start the app once (it asks), or run: tools\setup_engine2.ps1 -DataDir D:\apskeyl" -ForegroundColor Red
    exit 1
}
$e2 = Join-Path $DataDir "engine2"
New-Item -ItemType Directory -Force $e2 | Out-Null
Head "engine 2 -> $e2"

# nvidia check (soft): we only warn, the app falls back to engine 1 anyway
try { $g = & nvidia-smi --query-gpu=name --format=csv,noheader 2>$null; if ($g) { Say "GPU: $g" } }
catch { Write-Host "  nvidia-smi not found - engine 2 needs an NVIDIA GPU with a recent driver" -ForegroundColor Yellow }

# python (same rule as setup.ps1)
$py = $null
foreach ($c in @("py -3.12", "py -3.11", "py -3", "python")) {
    try {
        $v = & cmd /c "$c -c `"import sys;print(sys.version_info[1])`"" 2>$null
        if ($LASTEXITCODE -eq 0 -and [int]$v.Trim() -ge 11) { $py = $c; break }
    } catch {}
}
if (-not $py) { Write-Host "  Python 3.11+ not found" -ForegroundColor Red; exit 1 }

$venv = Join-Path $e2 ".venv"
if (-not (Test-Path "$venv\Scripts\python.exe")) { & cmd /c "$py -m venv `"$venv`""; Say "venv created" } else { Say "venv exists" }
$vpy = "$venv\Scripts\python.exe"
& $vpy -m pip install --upgrade pip --quiet

Head "torch + cu128 (~3 GB)"
& $vpy -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
Head "spandrel, onnx, lpips, safetensors"
& $vpy -m pip install "spandrel>=0.4" "onnx>=1.17" "lpips==0.1.4" safetensors scipy pillow numpy tqdm
Head "TensorRT (NVIDIA license; skip = engine 2 still works, just slower)"
& $vpy -m pip install "tensorrt-cu12>=10.9" 2>$null
if ($LASTEXITCODE -ne 0) { Write-Host "  tensorrt wheel failed - continuing without it (torch fp16 path is used)" -ForegroundColor Yellow }

Head "check"
& $vpy -c "import torch, spandrel; print('  torch', torch.__version__, '| cuda', torch.cuda.is_available())"
try { & $vpy -c "import tensorrt; print('  tensorrt', tensorrt.__version__)" } catch { Say "tensorrt: not installed" }
Write-Host ""
Write-Host "Done. Restart the app; .pth models in the catalogue (tab with the compass) become installable." -ForegroundColor Green
