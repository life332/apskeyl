# -*- coding: utf-8 -*-
"""💎 АПСКЕЙЛ — конфіг. Код — у теці програми, ВСІ дані — в окремій теці на великому диску.

Чому дані окремо: одна 4K-задача = десятки ГБ тимчасових кадрів, і класти це поруч із кодом
(зазвичай на системному диску) не можна. Тому тека даних обирається на ПЕРШОМУ запуску
(майстер у desktop.py) і запамʼятовується в `apskeyl.json` поруч із програмою.

Звідки що береться (пріоритет зверху вниз):
  · змінна оточення APSK_DATA / APSK_TOOLS — для скриптів і тестів
  · apskeyl.json поруч із програмою — те, що обрав користувач у майстрі
  · дефолт — %LOCALAPPDATA%\\Apskeyl для даних і tools\\bin для бінарників
Бінарники (ffmpeg, realesrgan-ncnn-vulkan) кладе `tools\\setup.ps1`; на старті перевіряємо,
що вони на місці, і падаємо з ЛЮДСЬКИМ повідомленням, а не трейсбеком.
"""
from __future__ import annotations
import json
import os
import shutil
from pathlib import Path

APP_NAME = "apskeyl"
PORT = int(os.getenv("APSK_PORT", "8391"))

ROOT = Path(__file__).resolve().parents[1]           # тека програми (код)
WEB = ROOT / "web"
CONFIG_FILE = ROOT / "apskeyl.json"                  # локальні налаштування установки (не в git)


def _local_cfg() -> dict:
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def data_configured() -> bool:
    """Чи вже відомо, де тримати дані (інакше desktop.py покаже майстер)."""
    return bool(os.getenv("APSK_DATA") or _local_cfg().get("data_dir"))


def save_data_dir(p: str | Path) -> None:
    cfg = _local_cfg()
    cfg["data_dir"] = str(p)
    CONFIG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=1), encoding="utf-8")


def _data_dir() -> Path:
    env = os.getenv("APSK_DATA")
    if env:
        return Path(env)
    cfg = _local_cfg().get("data_dir")
    if cfg:
        return Path(cfg)
    return Path(os.getenv("LOCALAPPDATA") or ROOT) / "Apskeyl"


DATA = _data_dir()                                   # усі дані
DB_PATH = DATA / "library.db"
THUMBS = DATA / "thumbs"
TMP = DATA / "tmp"                                   # ТІЛЬКИ ASCII-підтеки всередині
OUT = DATA / "out"
LOGS = DATA / "logs"
INBOX = DATA / "inbox"                               # тека-приймальня: кинув файл — підхопимо

# зовнішні бінарники: tools\bin (ставить setup.ps1), інакше — те, що є в PATH
VA_TOOLS = Path(os.getenv("APSK_TOOLS") or _local_cfg().get("tools_dir") or ROOT / "tools" / "bin")


def _find_exe(name: str, *layouts: str) -> Path:
    """Бінарник у теці інструментів (кілька відомих розкладок архівів) або в PATH.
    Якщо нема ніде — повертаємо перший очікуваний шлях, щоб повідомлення було конкретним."""
    for rel in layouts:
        p = VA_TOOLS / rel
        if p.exists():
            return p
    w = shutil.which(name)
    return Path(w) if w else VA_TOOLS / layouts[0]


FFMPEG = _find_exe("ffmpeg", "ffmpeg/bin/ffmpeg.exe", "ffmpeg.exe")
FFPROBE = _find_exe("ffprobe", "ffmpeg/bin/ffprobe.exe", "ffprobe.exe")
REALESRGAN = _find_exe("realesrgan-ncnn-vulkan",
                       "realesrgan/realesrgan-ncnn-vulkan.exe", "realesrgan-ncnn-vulkan.exe")
VA_MODELS = REALESRGAN.parent / "models"             # базові моделі з архіву рушія (лише читаємо)
MODELS_DIR = DATA / "models"                          # НАША тека: копії + докачані моделі

# 🚀 ДРУГИЙ РУШІЙ: torch+CUDA замість ncnn-Vulkan (×2.5 на ESRGAN-класі, читає .pth/.safetensors).
# Важкий venv (~8 ГБ) ставить `tools\setup_engine2.ps1` у теку даних; тонкий venv проги
# не чіпаємо — без цієї теки прога працює як раніше, просто моделі .pth недоступні.
ENGINE2_DIR = DATA / "engine2"
ENGINE2_PY = ENGINE2_DIR / ".venv" / "Scripts" / "python.exe"
PTH_DIR = MODELS_DIR / "pth"                          # моделі другого рушія (.pth/.safetensors)
ENGINE2_TILE = int(os.getenv("APSK_E2_TILE", "0"))    # 0 = цілий кадр; рушій сам впаде на 512 при браку VRAM

GPU_ID = os.getenv("APSK_GPU", "0")                  # Vulkan-пристрій; «auto» може взяти вбудовану Intel!

# Стартові опори швидкості (заміряно на RTX 3080 Ti; після першої проби замінюються
# власним заміром у calib.json). Мегапікселі ВХОДУ за секунду. ETA = mpix_вхід / throughput × 1.2.
THROUGHPUT_MPIX_S = {
    ("realesr-animevideov3", 2): 15.8,
    ("realesr-animevideov3", 3): 7.0,    # інтерполяція між x2 і x4 — уточниться за фактом
    ("realesr-animevideov3", 4): 4.1,
    ("realesr-general-x4v3", 4): 3.5,    # орієнтир до власного заміру
    ("realesr-general-wdn-x4v3", 4): 3.5,
    ("realesrgan-x4plus", 4): 0.32,      # 6.5 с/кадр — ПАСТКА, тільки короткі шматки
    ("4x-UltraSharp-opt-fp16", 4): 0.32, # ESRGAN-клас: та сама ціна, що x4plus
    ("4x-NMKD-Siax-200k", 4): 0.32,
    ("4xLSDIRplus", 4): 0.32,
}
FAST_SPEED_X = 2.5          # швидкий шлях без ШІ ≈ у 2.5 раза швидше за реалтайм (оцінка)
TMP_GB_PER_SEC_4K = 0.214   # 214 МБ тимчасових PNG на секунду відео в 4K (заміряно)
OUT_MB_PER_MIN_4K = 115     # розмір результату crf16

MIN_FREE_GB_START = 25      # менше — задачу не стартуємо
MIN_FREE_GB_RUN = 12        # менше під час роботи — пауза, не падіння

VIDEO_EXTS = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".ts", ".m4v", ".wmv", ".flv"}


def ensure_dirs():
    for d in (DATA, THUMBS, TMP, OUT, LOGS, INBOX, MODELS_DIR):
        d.mkdir(parents=True, exist_ok=True)
    # рушій приймає ОДНУ теку моделей → тримаємо власну, у чужу (Автомонтаж) не пишемо;
    # базові моделі копіюємо один раз (~44 МБ), докачані лягають поруч
    import shutil
    if VA_MODELS.exists():
        for p in VA_MODELS.iterdir():
            if p.suffix in (".bin", ".param") and not (MODELS_DIR / p.name).exists():
                try:
                    shutil.copy2(p, MODELS_DIR / p.name)
                except OSError:
                    pass


def models_present() -> set[str]:
    """Імена моделей, у яких є ОБИДВА файли (.param + .bin)."""
    names = {p.stem for p in MODELS_DIR.glob("*.param")} if MODELS_DIR.exists() else set()
    return {n for n in names if (MODELS_DIR / f"{n}.bin").exists()}


def check_tools() -> list[str]:
    """Людські повідомлення про те, чого бракує, замість трейсбека на першому виклику."""
    missing = []
    hint = " — запусти tools\\setup.ps1"
    if not FFMPEG.exists():
        missing.append(f"ffmpeg не знайдено: {FFMPEG}{hint}")
    if not FFPROBE.exists():
        missing.append(f"ffprobe не знайдено: {FFPROBE}{hint}")
    if not REALESRGAN.exists():
        missing.append(f"realesrgan не знайдено: {REALESRGAN} (нейромережа недоступна){hint}")
    return missing


# ── налаштування користувача (Етап 4) ──────────────────────────────────────────
SETTINGS_PATH = DATA / "settings.json"
DEFAULT_SETTINGS = {
    "model": "4x-UltraSharp-opt-fp16",   # вердикт власника 28.08: «UltraSharp — топ»
    "target": "4k",
    "codec": "libx264",                  # libx264 (якість) | hevc_nvenc (швидко, менший файл)
    "sharpen": 0.0,                      # cas після нейромережі 0..1 (UltraSharp уже різкий)
    "grain": False,                      # кінозерно — маскує «пластилін» (порада панелі)
    "denoise": False,                    # hqdn3d ПЕРЕД нейромережею (для пожатого джерела)
    "threads": "1:2:2",                  # realesrgan -j load:proc:save
    "tile": 0,                           # realesrgan -t (0 = авто; ≥200 якщо шви на небі)
    "lang": "uk",                        # мова інтерфейсу: uk | ru | en
    "out_dir": "",                       # тека результатів; порожньо = <дані>\out
    # 🛡 «ЕФІР МАЄ ПРІОРИТЕТ» — необовʼязковий сторож для тих, хто рендерить під живим
    # стрімом з того самого ПК: низький пріоритет CPU, лише P-ядра, -j 1:1:1, ffmpeg упівсили,
    # сон рушія при просіданні кодера ефіру. Вимкнено; вмикається ключем у settings.json і
    # потребує APSK_STREAM_PROGRESS = шлях до файлу `ffmpeg -progress` вашого стріму.
    "yield_to_stream": False,
}
STREAM_PROGRESS = Path(os.getenv("APSK_STREAM_PROGRESS") or (LOGS / "stream_progress.txt"))
PCORE_MASK = int(os.getenv("APSK_PCORE_MASK", "0xFFFF"), 16)   # 13700K: логічні 0-15 = P-ядра
PCORE_EXPECT_CPUS = int(os.getenv("APSK_PCORE_CPUS", "24"))    # маску вішаємо лише при такій кількості


def load_settings() -> dict:
    import json
    d = dict(DEFAULT_SETTINGS)
    try:
        d.update({k: v for k, v in json.loads(SETTINGS_PATH.read_text(encoding="utf-8")).items()
                  if k in DEFAULT_SETTINGS})
    except Exception:
        pass
    return d


def out_dir() -> Path:
    """Тека результатів із налаштувань (власник може обрати свою); нема/не створюється → OUT."""
    s = load_settings().get("out_dir") or ""
    if s:
        p = Path(s)
        try:
            p.mkdir(parents=True, exist_ok=True)
            return p
        except OSError:
            pass
    OUT.mkdir(parents=True, exist_ok=True)
    return OUT


def save_settings(d: dict) -> dict:
    import json
    cur = load_settings()
    cur.update({k: v for k, v in d.items() if k in DEFAULT_SETTINGS})
    try:
        SETTINGS_PATH.write_text(json.dumps(cur, ensure_ascii=False, indent=1), encoding="utf-8")
    except OSError:
        pass
    return cur


def disk_free_gb(path: Path = DATA) -> float:
    import shutil
    try:
        return shutil.disk_usage(path).free / 1e9
    except Exception:
        return 0.0
