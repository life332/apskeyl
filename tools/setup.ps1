# Apskeyl — one-shot setup (Windows 10/11, PowerShell 5.1+ or 7).
#   1) thin Python venv next to the app (fastapi / uvicorn / pywebview)
#   2) ffmpeg + ffprobe              -> tools\bin\ffmpeg\bin\
#   3) realesrgan-ncnn-vulkan + base models -> tools\bin\realesrgan\
# Nothing is written outside the app folder. Re-run any time: existing parts are skipped.
# ASCII-only on purpose: PowerShell 5.1 reads scripts as ANSI unless BOM is present.

param(
    [switch]$SkipTools,     # only the venv (you already have ffmpeg/realesrgan in PATH or APSK_TOOLS)
    [switch]$Force          # re-download tools even if present
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$bin  = Join-Path $root "tools\bin"
Set-Location $root

function Say($m) { Write-Host "  $m" }
function Head($m) { Write-Host ""; Write-Host "== $m ==" -ForegroundColor Cyan }

# ---------- 0. python ----------
Head "python"
$py = $null
foreach ($c in @("py -3.12", "py -3.11", "py -3", "python")) {
    try {
        $v = & cmd /c "$c -c `"import sys;print(sys.version_info[0],sys.version_info[1])`"" 2>$null
        if ($LASTEXITCODE -eq 0 -and $v) {
            $maj, $min = $v.Trim().Split(" ")
            if ([int]$maj -eq 3 -and [int]$min -ge 11) { $py = $c; Say "using $c (3.$min)"; break }
        }
    } catch {}
}
if (-not $py) {
    Write-Host "  Python 3.11+ not found. Install from https://www.python.org/downloads/ (tick 'Add to PATH') and re-run." -ForegroundColor Red
    exit 1
}

# ---------- 1. venv ----------
Head "venv (.venv)"
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    & cmd /c "$py -m venv .venv"
    if ($LASTEXITCODE -ne 0) { Write-Host "  venv failed" -ForegroundColor Red; exit 1 }
    Say "created"
} else { Say "exists" }
& .\.venv\Scripts\python.exe -m pip install --upgrade pip --quiet
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt --quiet
if ($LASTEXITCODE -ne 0) { Write-Host "  pip install failed" -ForegroundColor Red; exit 1 }
Say "requirements ok"

# ---------- 2. tools ----------
if (-not $SkipTools) {
    New-Item -ItemType Directory -Force $bin | Out-Null
    $tmp = Join-Path $env:TEMP "apskeyl_setup"
    New-Item -ItemType Directory -Force $tmp | Out-Null
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

    # -- ffmpeg (gyan.dev essentials, GPL build with x264/NVENC) --
    Head "ffmpeg"
    $ffExe = Join-Path $bin "ffmpeg\bin\ffmpeg.exe"
    if ($Force -or -not (Test-Path $ffExe)) {
        $zip = Join-Path $tmp "ffmpeg.zip"
        Say "downloading (~90 MB) ..."
        Invoke-WebRequest "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip" -OutFile $zip
        $x = Join-Path $tmp "ffx"; if (Test-Path $x) { Remove-Item $x -Recurse -Force }
        Expand-Archive $zip $x
        $inner = Get-ChildItem $x -Directory | Select-Object -First 1
        $dst = Join-Path $bin "ffmpeg"; if (Test-Path $dst) { Remove-Item $dst -Recurse -Force }
        Move-Item $inner.FullName $dst
        Say "ok -> $ffExe"
    } else { Say "exists" }

    # -- realesrgan-ncnn-vulkan (MIT) + base models (BSD) --
    Head "realesrgan-ncnn-vulkan"
    $reExe = Join-Path $bin "realesrgan\realesrgan-ncnn-vulkan.exe"
    if ($Force -or -not (Test-Path $reExe)) {
        $zip = Join-Path $tmp "realesrgan.zip"
        Say "downloading (~40 MB) ..."
        Invoke-WebRequest "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-windows.zip" -OutFile $zip
        $dst = Join-Path $bin "realesrgan"; if (Test-Path $dst) { Remove-Item $dst -Recurse -Force }
        Expand-Archive $zip $dst
        Say "ok -> $reExe"
    } else { Say "exists" }

    # -- realesr-general-x4v3 (BSD, not in the zip above; ~5 MB) --
    Head "extra base model: realesr-general-x4v3"
    $mdir = Join-Path $bin "realesrgan\models"
    foreach ($f in @("realesr-general-x4v3.bin", "realesr-general-x4v3.param")) {
        $p = Join-Path $mdir $f
        if ($Force -or -not (Test-Path $p)) {
            Invoke-WebRequest "https://github.com/TransparentLC/realesrgan-gui/releases/download/additional-models/$f" -OutFile $p
            Say "ok $f"
        } else { Say "exists $f" }
    }
    Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
}

# ---------- 3. check ----------
Head "check"
$env:APSK_TOOLS = $bin
& .\.venv\Scripts\python.exe -c "import sys; sys.path.insert(0,'app'); import config; m=config.check_tools(); print('  tools:', 'ok' if not m else m)"
Write-Host ""
Write-Host "Done. Start the app:  tools\apskeyl.cmd   (or double-click tools\apskeyl.vbs)" -ForegroundColor Green
Write-Host "First start asks where to keep data - pick a big drive, not C:." -ForegroundColor Green
Write-Host "Optional GPU engine 2 (NVIDIA only, ~8 GB):  tools\setup_engine2.ps1"
