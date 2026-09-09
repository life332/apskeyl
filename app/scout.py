# -*- coding: utf-8 -*-
"""🧭 РОЗВІДНИК НОВИХ МОДЕЛЕЙ — Етап 6, п.1-3 (замовлення власника 08.09).

«вкладка, в ній нові моделі рендера, опис, приблизна швидкість, і можливість її встановити
в апскейл; інфу туди заносити парсером та скриптами, щоб робило автономно і оновлювало,
робило пошук раз на 4 дні, перевіряло, чи не вийшли нові моделі, чи вони доступні
і чи можна скачать»

ДЖЕРЕЛО. `OpenModelDB/open-model-database` — 671 модель, кожна окремим JSON з готовими
метаданими (архітектура, масштаб, теги, автор, ліцензія, опис, приклади, sha256, посилання).
Тягнемо ОДНИМ архівом (1.2 МБ) замість 671 запиту — раз на 4 дні це майже безкоштовно.

🚨 ГОЛОВНА ПРАВДА, яку показала розвідка 08.09: з 671 моделі прямим лінком лежать лише 164.
Решта — drive.google (290), oracle-сховище (141), mega (122), onedrive, mediafire… Тому
«чи можна скачать» — окреме поле, а не здогад. Для непрямих ще пробуємо ДЗЕРКАЛА на
HuggingFace: перевірено на UltraSharp — OpenModelDB знає лише mega, але файл лежить у
`Kim2091/UltraSharp`, і його sha256 ЗБІГСЯ з тим, що записаний у каталозі. Тобто дзеркало
можна довести, а не просто сподіватись.

ШВИДКІСТЬ — оцінка за архітектурою, відкалібрована на НАШИХ замірах, а не з інтернету.
Вартість кадру ∝ (кількість згорток) × nf². Перевірка формули на двох заміряних точках:
  esrgan 64nf/23nb → 23×15×64² = 1 413 120 умовних → заміряно 4.62 с/кадр 1080p
  compact 64nf/16nc → 16×64²  =    65 536 умовних → формула дає 0.214, ЗАМІРЯНО 0.21 ✅
Тому число на картці — чесна оцінка порядку, а після першої проби воно замінюється
ЗАМІРОМ із `calib.json` (поле `measured`).
"""
from __future__ import annotations
import io, json, re, tarfile, threading, time, urllib.request
from collections import deque
from pathlib import Path
from urllib.parse import urlparse

from config import MODELS_DIR, load_settings
import pool

CATALOG = MODELS_DIR / "catalog.json"
SRC_TARBALL = "https://codeload.github.com/OpenModelDB/open-model-database/tar.gz/refs/heads/main"
PAGE = "https://openmodeldb.info/models/"
UA = {"User-Agent": "apskeyl-scout/1.0 (+local tool)"}
CHECK_EVERY_S = 4 * 24 * 3600          # «раз на 4 дні» — слова власника
HTTP_TIMEOUT = 90
NEW_DAYS = 30                          # власник 08.09: «якщо місяць тому зʼявилось — то нове»
# Додаткові джерела (власник: «за якими ще джерелами дивитись»): збірки на HuggingFace, файли яких
# OpenModelDB не знає. Список можна змінити в settings.json → "scout_sources". Опису й архітектури
# в них нема — картка чесно каже «джерело: HuggingFace», швидкість «?».
DEFAULT_SOURCES = ("uwg/upscaler", "utnah/esrgan")     # Phhofm/models віддає 401 — не публічний

# Хости, з яких файл забирається ОДНИМ GET без браузера і капчі.
DIRECT_HOSTS = ("github.com", "objects.githubusercontent.com", "raw.githubusercontent.com",
                "huggingface.co", "cdn-lfs.huggingface.co", "openmodeldb.info",
                "backblazeb2.com", "oraclecloud.com")
# Дзеркала-збірники: один запит дає сотні файлів (перевірено 08.09: 87 і 117 моделей).
HF_MIRRORS = ("uwg/upscaler", "utnah/esrgan")

# Формати, які вміє наш другий рушій (spandrel): .pth і .safetensors. onnx — ні.
USABLE_TYPES = ("pth", "safetensors")

# ── оцінка вартості кадру ──────────────────────────────────────────────────────
REF_UNITS, REF_SEC = 1_413_120, 4.62      # esrgan 64nf/23nb ↔ заміряно на цій машині
ARCH_UNITS = {          # коли в каталозі нема поля size — типова вага архітектури
    "esrgan": 1_413_120, "compact": 65_536, "span": 50_000, "realplksr": 120_000,
    "ditn": 150_000, "mosr": 150_000, "real-cugan": 300_000, "omnisr": 400_000,
    "rcan": 1_200_000, "swinir": 1_500_000, "srformer": 2_200_000, "rgt": 2_500_000,
    "dat": 2_500_000, "drct": 3_000_000, "atd": 3_000_000, "hat": 4_000_000,
    "sofvsr": 500_000, "codeformer": 800_000, "gfpgan": 800_000,
}
# Клас архітектури — ПРОКСІ очікуваної деталізації для градації каталогу (власник 08.09:
# «градація типу по качеству»). Це НЕ замір: замір (LPIPS) є лише для поставлених — quality.py.
ARCH_TIER = {
    "span": 1, "compact": 1, "realplksr": 1, "mosr": 1, "ditn": 1, "real-cugan": 1,
    "esrgan": 2, "rcan": 2, "omnisr": 2, "swinir": 2, "sofvsr": 2, "codeformer": 2, "gfpgan": 2,
    "srformer": 3, "rgt": 3, "dat": 3, "drct": 3, "atd": 3, "hat": 3,
}
TIER_HUMAN = {1: "легкий клас: швидко, простіша картинка (за архітектурою, не замір)",
              2: "середній клас: класична деталізація (за архітектурою, не замір)",
              3: "важкий клас: найдетальніші й найповільніші (за архітектурою, не замір)"}


def tier_of(arch: str) -> int:
    return ARCH_TIER.get((arch or "").lower(), 2)


ARCH_HUMAN = {
    "esrgan": "ESRGAN — класика, найдетальніша і найповільніша",
    "compact": "Compact — легка згорткова, у рази швидша",
    "span": "SPAN — сучасна легка, майже безкоштовна",
    "dat": "DAT — трансформер, дуже важкий",
    "hat": "HAT — трансформер, найважчий клас",
    "swinir": "SwinIR — трансформер, важкий",
    "omnisr": "OmniSR — середня вага",
    "realplksr": "RealPLKSR — легка, великі ядра",
    "rgt": "RGT — трансформер, важкий",
    "drct": "DRCT — трансформер, важкий",
    "atd": "ATD — трансформер, важкий",
    "srformer": "SRFormer — трансформер, важкий",
    "rcan": "RCAN — глибока згорткова",
    "mosr": "MoSR — легка сучасна",
    "ditn": "DITN — легка",
    "real-cugan": "Real-CUGAN — для мальованого",
}
# теги OpenModelDB → людське призначення
PURPOSE = [
    ("anime", "🎨 мальоване/аніме"), ("cartoon", "🎨 мальоване/аніме"),
    ("faces", "🙂 обличчя"), ("face", "🙂 обличчя"),
    ("text", "🔤 текст і скани"), ("game", "🎮 ігрові текстури"),
    ("compression-removal", "🧹 прибирає стиснення"), ("jpeg", "🧹 прибирає стиснення"),
    ("denoise", "🧼 денойз"), ("dehalo", "🧼 прибирає гало"),
    ("restoration", "🛠 реставрація"), ("photo", "📷 фото"),
    ("realistic", "🎬 реальне відео"), ("general-upscaler", "🎬 універсальна"),
    ("video", "🎬 реальне відео"),
]

_LOCK = threading.Lock()
_STATE = {"running": False, "last_error": "", "phase": ""}


# ── дрібне ─────────────────────────────────────────────────────────────────────
def _get(url: str, timeout: int = HTTP_TIMEOUT) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _units(m: dict) -> int:
    """Умовна вартість кадру. Для esrgan/compact рахуємо з поля size (воно є у 68% моделей),
    інакше — типова вага архітектури. Це ОЦІНКА ПОРЯДКУ, і так і підписано в UI."""
    arch = (m.get("architecture") or "").lower()
    size = m.get("size") or []
    nf = nb = nc = 0
    for s in size:
        if not isinstance(s, str):
            continue
        if (g := re.fullmatch(r"(\d+)nf", s)):
            nf = int(g.group(1))
        elif (g := re.fullmatch(r"(\d+)nb", s)):
            nb = int(g.group(1))
        elif (g := re.fullmatch(r"(\d+)nc", s)):
            nc = int(g.group(1))
    if arch == "esrgan" and nf and nb:
        return nb * 15 * nf * nf          # RRDB: 3 щільні блоки × 5 згорток
    if arch == "compact" and nf and nc:
        return nc * nf * nf
    return ARCH_UNITS.get(arch, 500_000)


def _ref_sec() -> float:
    """Скільки СПРАВДІ коштує еталонний esrgan на цій машині ЗАРАЗ (з calib.json),
    щоб оцінки їхали слідом за реальністю — і за зміною рушія теж."""
    try:
        c = json.loads((MODELS_DIR.parent / "calib.json").read_text(encoding="utf-8"))
    except Exception:
        return REF_SEC
    best = None
    for key in ("4x-UltraSharp-opt-fp16|4", "4x-NMKD-Siax-200k|4", "realesrgan-x4plus|4"):
        v = c.get(key)
        if v:
            best = 2.0736 / float(v)      # мпікс кадру 1080p / (мпікс за секунду)
            break
    return best if best and 0.05 < best < 60 else REF_SEC


def _resources(m: dict) -> tuple[str, dict | None, str]:
    """(як доступна, найкращий ресурс, пряме посилання). Порядок: прямий лінк → дзеркало
    HuggingFace → лише вручну."""
    best_manual = None
    for r in (m.get("resources") or []):
        if r.get("type") not in USABLE_TYPES:
            continue
        for u in r.get("urls") or []:
            host = urlparse(u).netloc.lower()
            if any(host == h or host.endswith("." + h) or h in host for h in DIRECT_HOSTS):
                return "direct", r, u
            best_manual = best_manual or (r, u)
    if best_manual:
        return "manual", best_manual[0], best_manual[1]
    return "none", None, ""


def _hf_index() -> dict[str, str]:
    """Індекс дзеркал: {ім'я файлу в нижньому регістрі: пряме посилання}. Два запити."""
    idx: dict[str, str] = {}
    for repo in HF_MIRRORS:
        try:
            j = json.loads(_get(f"https://huggingface.co/api/models/{repo}", 60))
        except Exception:
            continue
        for s in j.get("siblings") or []:
            f = s.get("rfilename") or ""
            if f.lower().endswith((".pth", ".safetensors")):
                idx.setdefault(f.rsplit("/", 1)[-1].lower(),
                               f"https://huggingface.co/{repo}/resolve/main/{f}")
    return idx


def _clean_desc(s: str) -> str:
    """Опис з OpenModelDB — напівмаркдаун із сирими <br>: у фронті вони показувались літерами
    (власник 08.09). Теги → переноси, зайві порожні рядки — геть."""
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"</?(p|div|ul|ol|li|b|i|strong|em)\b[^>]*>", "\n", s, flags=re.I)
    s = re.sub(r"[ \t]+\n", "\n", s)
    return re.sub(r"\n{3,}", "\n\n", s).strip()


def new_keys(d: dict) -> list[str]:
    """Нові = дата випуску в каталозі за останні NEW_DAYS АБО розвідник уперше побачив за NEW_DAYS
    (але не при найпершому завантаженні каталогу — тоді «новим» було б усе 671)."""
    now = time.time()
    lim = now - NEW_DAYS * 86400
    first_fetch = float(d.get("first_fetch") or 0)
    seen = d.get("first_seen") or {}
    out = []
    for k, m in (d.get("models") or {}).items():
        try:
            ts = time.mktime(time.strptime(str(m.get("date") or "")[:10], "%Y-%m-%d"))
        except Exception:
            ts = 0
        fs = float(seen.get(k) or 0)
        if ts >= lim or (fs >= lim and fs > first_fetch + 3600):
            out.append(k)
    return out


def _hf_sources(existing: dict, omdb: dict) -> dict:
    """Файли .pth/.safetensors зі збірок HuggingFace, яких нема серед ресурсів OpenModelDB.
    sha256 і розмір HF віддає сам (lfs) — тож звірка при встановленні працює і тут."""
    repos = load_settings().get("scout_sources") or list(DEFAULT_SOURCES)
    known: set[str] = set()
    for m in omdb.values():
        for r in m.get("resources") or []:
            for u in r.get("urls") or []:
                known.add(str(u).rsplit("/", 1)[-1].lower())
    add: dict[str, dict] = {}
    for repo in repos:
        try:
            j = json.loads(_get(f"https://huggingface.co/api/models/{repo}?blobs=true", 90))
        except Exception:
            continue
        owner = str(repo).split("/")[0]
        mod = ""      # lastModified — дата ЗБІРКИ, не моделі: інакше всі 100 файлів стали б «новими» разом
        for s in j.get("siblings") or []:
            f = s.get("rfilename") or ""
            base = f.rsplit("/", 1)[-1]
            if not base.lower().endswith((".pth", ".safetensors")) or base.lower() in known:
                continue
            stem = base.rsplit(".", 1)[0]
            key = "hf-" + re.sub(r"[^A-Za-z0-9._-]+", "-", f"{owner}-{stem}")
            if key in existing or key in add:
                continue
            mt = re.search(r"(?:^|[_\-\s])(\d)x(?:[_\-\s.]|$)|x(\d)(?:[_\-\s.]|$)", stem, re.I)
            scale = int(next((g for g in (mt.groups() if mt else ()) if g), 0) or 0)
            lfs = s.get("lfs") or {}
            add[key] = {
                "key": key, "name": stem, "author": owner, "date": mod, "license": "",
                "arch": "", "arch_human": "", "scale": scale, "tags": [], "purpose": [],
                "desc": "", "images": [], "avail": "direct",
                "url": f"https://huggingface.co/{repo}/resolve/main/{f}",
                "page": f"https://huggingface.co/{repo}/blob/main/{f}",
                "type": "safetensors" if base.lower().endswith(".safetensors") else "pth",
                "size_mb": round(float(lfs.get("size") or s.get("size") or 0) / 1e6, 1),
                "sha256": lfs.get("sha256") or "", "units": 0, "sec_per_frame": 0,
                "hours_10min": 0, "first_seen": 0, "installed": False, "src": f"hf:{repo}",
            }
    return add


def _purpose(tags: list) -> list[str]:
    low = {str(t).lower() for t in tags or []}
    out = []
    for key, human in PURPOSE:
        if key in low and human not in out:
            out.append(human)
    return out[:3]


# ── головне: оновлення каталогу ────────────────────────────────────────────────
def refresh(force: bool = False) -> dict:
    """Тягне каталог, класифікує, рахує оцінку швидкості, позначає НОВІ з минулої перевірки."""
    with _LOCK:
        if _STATE["running"]:
            return {"error": "перевірка вже іде"}
        _STATE.update(running=True, last_error="", phase="качаю каталог")
    try:
        prev = load()
        if not force and prev.get("last_check") and \
                time.time() - prev["last_check"] < CHECK_EVERY_S:
            return prev
        raw = _get(SRC_TARBALL, 180)
        models: dict[str, dict] = {}
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as tf:
            for mem in tf.getmembers():
                if "/data/models/" in mem.name and mem.name.endswith(".json"):
                    key = mem.name.rsplit("/", 1)[-1][:-5]
                    try:
                        models[key] = json.loads(tf.extractfile(mem).read().decode("utf-8"))
                    except Exception:
                        pass
        _STATE["phase"] = "шукаю дзеркала"
        mirrors = _hf_index()
        _STATE["phase"] = "класифікую"

        ref_sec, now = _ref_sec(), time.time()
        first_seen = dict(prev.get("first_seen") or {})
        known_before = set(first_seen)
        out = {}
        for key, m in models.items():
            avail, res, url = _resources(m)
            if avail != "direct":
                # OpenModelDB може не знати про дзеркало — питаємо HuggingFace за іменем файлу
                for cand in (f"{key}.pth", f"{key}.safetensors"):
                    if cand.lower() in mirrors:
                        avail, url = "mirror", mirrors[cand.lower()]
                        break
            units = _units(m)
            sec = round(units / REF_UNITS * ref_sec, 3)
            first_seen.setdefault(key, now)
            out[key] = {
                "key": key,
                "name": m.get("name") or key,
                # author у каталозі буває СПИСКОМ (кілька авторів) — пошук по .lower() падав з 500
                "author": ", ".join(str(x) for x in m["author"]) if isinstance(m.get("author"), list)
                          else str(m.get("author") or ""),
                "date": m.get("date") or "",
                "license": m.get("license") or "",
                "arch": (m.get("architecture") or "").lower(),
                "arch_human": ARCH_HUMAN.get((m.get("architecture") or "").lower(), ""),
                "scale": m.get("scale") or 0,
                "tags": m.get("tags") or [],
                "purpose": _purpose(m.get("tags")),
                # повний опис (до 6000): він іде у повноекранну картку, а не в рядок списку
                "desc": _clean_desc(m.get("description") or "")[:6000],
                "images": [i for i in (m.get("images") or []) if isinstance(i, dict)][:3],
                "avail": avail,                       # direct | mirror | manual | none
                "url": url,
                "page": PAGE + key,
                "type": (res or {}).get("type") or "",
                "size_mb": round(((res or {}).get("size") or 0) / 1e6, 1),
                "sha256": (res or {}).get("sha256") or "",
                "units": units,
                "sec_per_frame": sec,
                "hours_10min": round(sec * 18000 / 3600, 2),
                "first_seen": first_seen[key],
                "installed": False,
            }
        # додаткові джерела (HuggingFace-збірки) — те, чого OpenModelDB не знає
        _STATE["phase"] = "додаткові джерела"
        # перше індексування збірки — базова лінія (не «нове»), далі нові файли в ній — нові
        baseline = float(prev.get("first_fetch") or now) if not prev.get("sources_done") else now
        for k, v in _hf_sources(out, models).items():
            first_seen.setdefault(k, baseline)
            v["first_seen"] = first_seen[k]
            out[k] = v
        installed = {i["name"] for i in pool.catalog() if i.get("installed")}
        for k, v in out.items():
            v["installed"] = v["name"] in installed or k in installed

        data = {"fetched": now, "last_check": now,
                "prev_check": prev.get("last_check") or 0,
                "first_fetch": prev.get("first_fetch") or now, "sources_done": True,
                "count": len(out), "ref_sec": ref_sec,
                "models": out, "first_seen": first_seen}
        data["new_keys"] = sorted(new_keys(data))
        CATALOG.parent.mkdir(parents=True, exist_ok=True)
        CATALOG.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return data
    except Exception as e:
        _STATE["last_error"] = f"{type(e).__name__}: {e}"
        return {"error": _STATE["last_error"]}
    finally:
        _STATE.update(running=False, phase="")


def load() -> dict:
    try:
        return json.loads(CATALOG.read_text(encoding="utf-8"))
    except Exception:
        return {}


def state() -> dict:
    d = load()
    return {"running": _STATE["running"], "phase": _STATE["phase"],
            "last_error": _STATE["last_error"],
            "last_check": d.get("last_check", 0), "count": d.get("count", 0),
            "new_count": len(new_keys(d)),
            "sources": ["OpenModelDB"] + [f"HF/{r}" for r in (load_settings().get("scout_sources") or DEFAULT_SOURCES)],
            "next_check": (d.get("last_check", 0) + CHECK_EVERY_S) if d.get("last_check") else 0,
            "install": install_state(), "tr_queue": len(_TR_QUEUE), "tr_error": _TR_STATE["last_error"]}


# ── опис мовою інтерфейсу через Ollama (власник 08.09: «деталі онлі на англійском — надо под
#    язик інтерфейса адаптировать», раніше «може через Ollama підтягувати інфу») ──────────────
# Локально, без інтернету: qwen3:8b уже стоїть. Переклад кешується у desc_i18n.json назавжди
# (опис моделі не міняється), тому GPU платить за кожну модель і мову один раз. Якщо Ollama
# не відповідає — віддаємо оригінал з поміткою, а не помилку.
OLLAMA = "http://127.0.0.1:11434"
OLLAMA_MODEL = "qwen3:8b"
DESC_I18N = MODELS_DIR / "desc_i18n.json"
LANG_HUMAN = {"uk": "українською мовою", "ru": "на русский язык"}
_TR_LOCK = threading.Lock()
_TR_QUEUE: deque = deque()
_TR_STATE = {"last_error": "", "busy_fn": None, "backoff_until": 0.0}


def _tr_load() -> dict:
    try:
        return json.loads(DESC_I18N.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _ollama_translate(text: str, lang: str) -> str:
    system = (f"Ти перекладач технічних описів нейромереж для покращення відео. Переклади текст "
              f"користувача {LANG_HUMAN[lang]}. Збережи структуру: абзаци, списки, позначки ✓ і ✗. "
              "Назви моделей, архітектур і параметрів (ESRGAN, RRDB, DRUNet, tile, denoise, "
              "upscale) лишай як є. Нічого не додавай і не пояснюй — лише переклад.")
    body = {"model": OLLAMA_MODEL, "stream": False, "think": False,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": text}],
            "options": {"temperature": 0.2, "num_predict": 1200}}
    req = urllib.request.Request(OLLAMA + "/api/chat", data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=240) as r:
        j = json.loads(r.read().decode("utf-8"))
    out = ((j.get("message") or {}).get("content") or "")
    out = re.sub(r"<think>.*?</think>", "", out, flags=re.S).strip()   # на випадок увімкненого «думання»
    return out


def describe(key: str, lang: str) -> dict:
    """Опис моделі мовою lang: кеш → Ollama → оригінал (з поміткою, чому)."""
    m = (load().get("models") or {}).get(key)
    if not m:
        return {"error": "нема такої моделі в каталозі"}
    src = m.get("desc") or ""
    if lang not in LANG_HUMAN or not src.strip():
        return {"text": src, "source": "original", "lang": "en"}
    hit = (_tr_load().get(key) or {}).get(lang)
    if hit:
        return {"text": hit, "source": "cache", "lang": lang}
    if time.time() < _TR_STATE["backoff_until"]:
        return {"text": src, "source": "original", "lang": "en", "note": _TR_STATE["last_error"]}
    try:
        out = _ollama_translate(src, lang)
        if len(out) < max(20, len(src) // 4):
            raise RuntimeError("надто коротка відповідь")
    except Exception as e:
        _TR_STATE["last_error"] = f"Ollama ({OLLAMA_MODEL}): {type(e).__name__}: {str(e)[:80]}"
        _TR_STATE["backoff_until"] = time.time() + 60          # не довбати мертвий Ollama щосекунди
        return {"text": src, "source": "original", "lang": "en", "note": _TR_STATE["last_error"]}
    _TR_STATE["last_error"] = ""
    with _TR_LOCK:
        cache = _tr_load()
        cache.setdefault(key, {})[lang] = out
        DESC_I18N.parent.mkdir(parents=True, exist_ok=True)
        DESC_I18N.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    return {"text": out, "source": "ollama", "lang": lang}


def prefetch_desc(keys: list[str], lang: str) -> None:
    """Те, що зараз на екрані, перекладаємо наперед у фоні — щоб відкриття картки було миттєвим."""
    if lang not in LANG_HUMAN:
        return
    cache = _tr_load()
    with _TR_LOCK:
        for k in keys:
            if not (cache.get(k) or {}).get(lang) and (k, lang) not in _TR_QUEUE:
                _TR_QUEUE.append((k, lang))


def start_translate_worker(busy_fn) -> None:
    """Фоновий перекладач: по одній моделі, ЛИШЕ коли прога не рендерить і не пробує
    (busy_fn) — Ollama бере ~5 ГБ VRAM і сповільнила б рушій."""
    _TR_STATE["busy_fn"] = busy_fn

    def loop():
        while True:
            if not _TR_QUEUE or (busy_fn and busy_fn()) or time.time() < _TR_STATE["backoff_until"]:
                time.sleep(3)
                continue
            k, lang = _TR_QUEUE.popleft()
            _TR_STATE["active"] = True                    # проба якості дивиться на це: Ollama + рушій разом не треба
            try:
                describe(k, lang)
            except Exception as e:
                _TR_STATE["last_error"] = f"{type(e).__name__}: {e}"
            finally:
                _TR_STATE["active"] = False

    threading.Thread(target=loop, name="scout-translate", daemon=True).start()


# ── встановлення моделі в апскейл ──────────────────────────────────────────────
# Скачування йде у ФОНОВОМУ потоці (власник 08.09: «немає кнопки скасувати скачування»):
# start_install() лише запускає, install_state() віддає прогрес байтами, install_cancel()
# зупиняє — .part-файл при цьому гине, а в пул нічого не потрапляє.
_INSTALL = {"key": "", "running": False, "done": 0, "total": 0, "phase": "",
            "error": "", "canceled": False, "result": None}
_INSTALL_CANCEL = threading.Event()
_INSTALL_LOCK = threading.Lock()


class _Canceled(Exception):
    pass


def install_state() -> dict:
    s = dict(_INSTALL)
    s["pct"] = int(100 * s["done"] / s["total"]) if s["total"] else 0
    return s


def install_cancel() -> dict:
    if not _INSTALL["running"]:
        return {"error": "зараз нічого не качається"}
    _INSTALL_CANCEL.set()
    return {"ok": True}


def _check_installable(key: str) -> tuple[dict | None, str]:
    m = (load().get("models") or {}).get(key)
    if not m:
        return None, "нема такої моделі в каталозі — онови список"
    if m["avail"] not in ("direct", "mirror"):
        return None, ("цю модель автоматом не скачати (лежить на mega/google-диску) — "
                      f"відкрий сторінку і поклади файл у {PTH_DIR} вручну")
    if m["type"] not in USABLE_TYPES:
        return None, f"формат {m['type'] or '?'} наш рушій не читає (треба pth/safetensors)"
    return m, ""


def start_install(key: str) -> dict:
    """Запускає скачування у фоні. Одне за раз: друге поки перше йде — відмова з поясненням."""
    with _INSTALL_LOCK:
        if _INSTALL["running"]:
            return {"error": f"уже качаю {_INSTALL['key']} — дочекайся або скасуй"}
        m, err = _check_installable(key)
        if err:
            return {"error": err}
        _INSTALL.update(key=key, running=True, done=0, total=int((m.get("size_mb") or 0) * 1e6),
                        phase="качаю", error="", canceled=False, result=None)
        _INSTALL_CANCEL.clear()
    threading.Thread(target=_install_worker, args=(key, m), name="scout-install",
                     daemon=True).start()
    return {"ok": True, "key": key}


def _install_worker(key: str, m: dict) -> None:
    try:
        r = install(key, m)
        if r.get("error"):
            _INSTALL.update(error=r["error"], canceled=bool(r.get("canceled")), phase="")
        else:
            _INSTALL.update(result=r, phase="готово")
    except Exception as e:
        _INSTALL.update(error=f"{type(e).__name__}: {e}", phase="")
    finally:
        _INSTALL["running"] = False


def install(key: str, m: dict | None = None) -> dict:
    """Качає файл шматками (прогрес у _INSTALL, скасування через _INSTALL_CANCEL), звіряє sha256
    з каталогом і кладе модель у пул (група 📦 «Ще»). sha256 звіряємо ЗАВЖДИ, коли він є: саме
    так 08.09 доведено, що дзеркало UltraSharp на HuggingFace — та сама модель, що в каталозі."""
    if m is None:
        m, err = _check_installable(key)
        if err:
            return {"error": err}

    pool.PTH_DIR.mkdir(parents=True, exist_ok=True)
    ext = ".safetensors" if m["type"] == "safetensors" else ".pth"
    dst = pool.PTH_DIR / f"{key}{ext}"
    tmp = dst.with_suffix(dst.suffix + ".part")
    import hashlib
    h, got_bytes = hashlib.sha256(), 0
    try:
        req = urllib.request.Request(m["url"], headers=UA)
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as r, open(tmp, "wb") as f:
            total = int(r.headers.get("Content-Length") or 0)
            if total:
                _INSTALL["total"] = total
            while True:
                if _INSTALL_CANCEL.is_set():
                    raise _Canceled()
                chunk = r.read(1 << 20)
                if not chunk:
                    break
                f.write(chunk)
                h.update(chunk)
                got_bytes += len(chunk)
                _INSTALL["done"] = got_bytes
    except _Canceled:
        tmp.unlink(missing_ok=True)
        return {"error": "скачування скасовано", "canceled": True}
    except Exception as e:
        tmp.unlink(missing_ok=True)
        return {"error": f"не завантажилось: {type(e).__name__}: {e}"}
    if m.get("sha256"):
        got = h.hexdigest()
        if got != m["sha256"]:
            tmp.unlink(missing_ok=True)
            return {"error": f"sha256 не збігся з каталогом ({got[:12]}… проти "
                             f"{m['sha256'][:12]}…) — файлу не вірю, не ставлю"}
    tmp.replace(dst)

    scale = int(m.get("scale") or 4)
    pool.add_installed({
        "name": key, "title": m["name"], "group": "extra", "engine": "torch",
        "desc": (m["arch"].upper() + (" · " + m["purpose"][0] if m["purpose"] else "")).strip(" ·"),
        "scales": [scale], "scale": scale, "enabled": True, "order": 900,
        "arch": m["arch"], "author": m["author"], "license": m["license"], "src": m["page"],
        # оцінка мпікс/с, щоб прогноз часу на кнопці не брехав до першої проби
        "est_mpix_s": round(2.0736 / max(m["sec_per_frame"], 0.001), 3),
    })
    d = load()
    if key in (d.get("models") or {}):
        d["models"][key]["installed"] = True
        CATALOG.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    return {"ok": True, "name": key, "size_mb": round(got_bytes / 1e6, 1),
            "sha_checked": bool(m.get("sha256")), "pool": pool.catalog()}


# ── автономність: перевірка раз на 4 дні ───────────────────────────────────────
def start_schedule() -> None:
    """Фоновий потік: якщо з останньої перевірки минуло 4 дні — оновлює каталог сам.
    Прокидається раз на годину, качає 1.2 МБ — рендерам не заважає."""
    def loop():
        while True:
            try:
                d = load()
                if time.time() - (d.get("last_check") or 0) >= CHECK_EVERY_S:
                    r = refresh()
                    n = len(r.get("new_keys") or [])
                    print(f"розвідник: каталог оновлено, моделей {r.get('count', 0)}"
                          + (f", НОВИХ {n}" if n else ""), flush=True)
            except Exception as e:
                print(f"розвідник: {type(e).__name__}: {e}", flush=True)
            time.sleep(3600)

    threading.Thread(target=loop, name="scout", daemon=True).start()
