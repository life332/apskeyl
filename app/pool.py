# -*- coding: utf-8 -*-
"""🧭 ПУЛ МОДЕЛЕЙ — Етап 6, п.4. Меню «ЯК» будується З ПУЛУ, а не з коду.

Було: список моделей зашитий У ТРЬОХ місцях — `engine.MODEL_SCALES` (валідація задачі),
`web/index.html` (радіокнопки руками) і `app.js` (`MODEL_NAMES` для підписів у черзі).
Додати модель = правити три файли й не забути жодного; вимкнути набридлу = неможливо.

Стало: один список у `<дані>\\models\\pool.json`. Дефолти нижче повторюють меню
станом на 28.08 ОДИН В ОДИН (вердикт власника: UltraSharp топ · Siax гуд · детальна топ ·
мультяшна теж · wdn «херня» · LSDIRplus «потестю пізніше» — під «ще одна модель»),
тому після першого запуску власник не побачить у меню жодної зміни, поки сам не полізе.

Що можна крутити (і що з цього переживає перезапуск): `enabled` (показувати в меню «ЯК»),
`order` (порядок), `group` (🏆 top / ⚖ bal / ⚡ fast / 📦 extra — під «ще одна модель»),
`title` і `desc` (як підписано в меню). Ім'я моделі (`name`) і масштаби (`scales`) — ні:
це властивості файлів рушія, а не смаку.

🚨 ГОЧА, яку видно лише з диска: базові моделі (`realesr-animevideov3`, `realesrgan-x4plus`,
`realesrgan-x4plus-anime`) лежать в архіві рушія (`tools\\bin\\realesrgan\\models`),
а `config.ensure_dirs()` копіює їх до нас ПРИ КОЖНОМУ СТАРТІ. Видалити їхні файли не можна —
воскреснуть. Тому такі позначені `base: true`, кнопка «🗑 файли» їм недоступна, а прибрати
з очей можна лише перемикачем.

🚨 ГОЧА №2: `realesr-animevideov3` не має файлів із таким ім'ям — на диску лежать
`realesr-animevideov3-x2/-x3/-x4`, суфікс дописує сам рушій за `-s`. Тому наявність моделі
перевіряємо і за точним ім'ям, і за суфіксами масштабів.
"""
from __future__ import annotations
import json
from pathlib import Path

from config import (MODELS_DIR, VA_MODELS, DATA, THROUGHPUT_MPIX_S, ENGINE2_PY,
                    load_settings, save_settings)

POOL_PATH = MODELS_DIR / "pool.json"
PTH_DIR = MODELS_DIR / "pth"                 # моделі другого рушія (.pth/.safetensors)
CALIB_PATH = DATA / "calib.json"
GROUPS = ("top", "bal", "fast", "extra")
EDITABLE = ("enabled", "order", "group", "title", "desc")
ANCHOR_MODEL = "realesr-animevideov3"        # «×1» на чіпах — від неї, а не від найшвидшої

# Яким рушієм рахувати модель:
#   ncnn  — realesrgan-ncnn-vulkan, файли .param+.bin (як було з 28.08)
#   torch — engine2_runner.py на важкому venv <дані>\engine2, файли .pth/.safetensors
# Розвідник (Етап 6 п.1-3) кладе нові моделі ЗАВЖДИ як torch: 90% OpenModelDB — .pth,
# а ncnn їх не їсть у принципі.
ENGINES = ("ncnn", "torch")

# Дефолтний пул = меню 28.08 дослівно. Порядок кратний 10 — щоб між рядками можна було
# вставити нову модель, не перенумеровуючи весь список.
#
# `i18n_title`/`i18n_desc` — ключі словника фронта: поки власник не переписав підпис своїми
# словами, RU/EN беруть переклад звідти (у HTML це були data-i18n, і губити їх не можна).
DEFAULTS: list[dict] = [
    {"name": "4x-UltraSharp-opt-fp16", "title": "🔪 UltraSharp", "desc": "топ за твоїм вердиктом",
     "group": "top", "scales": [4], "enabled": True, "order": 10,
     "i18n_title": "", "i18n_desc": "m_ultrasharp_d"},
    {"name": "4x-NMKD-Siax-200k", "title": "🎯 NMKD Siax", "desc": "природна, добра на обличчях",
     "group": "top", "scales": [4], "enabled": True, "order": 20,
     "i18n_title": "", "i18n_desc": "m_siax_d"},
    {"name": "realesrgan-x4plus", "title": "🔬 Детальна", "desc": "x4plus, класика",
     "group": "top", "scales": [4], "enabled": True, "order": 30,
     "i18n_title": "m_x4plus", "i18n_desc": "m_x4plus_d"},
    {"name": "realesr-general-x4v3", "title": "🧠 Реальне відео", "desc": "general-x4v3",
     "group": "bal", "scales": [4], "enabled": True, "order": 40,
     "i18n_title": "m_x4v3", "i18n_desc": ""},
    {"name": "realesr-animevideov3", "title": "🎨 Мультяшна", "desc": "animevideov3, згладжує",
     "group": "fast", "scales": [2, 3, 4], "enabled": True, "order": 50,
     "i18n_title": "m_anime", "i18n_desc": "m_anime_d"},
    {"name": "4xLSDIRplus", "title": "🧬 LSDIRplus", "desc": "новіша реалістична",
     "group": "extra", "scales": [4], "enabled": True, "order": 60,
     "i18n_title": "", "i18n_desc": "m_lsdir_d"},
    # вердикт власника 28.08: «денойз-модель марна» → у пулі є, у меню вимкнена
    {"name": "realesr-general-wdn-x4v3", "title": "🧼 wdn-x4v3", "desc": "з денойзом, для пожатого",
     "group": "extra", "scales": [4], "enabled": False, "order": 70,
     "i18n_title": "", "i18n_desc": ""},
    {"name": "realesrgan-x4plus-anime", "title": "🖌 x4plus-anime", "desc": "для мальованого",
     "group": "extra", "scales": [4], "enabled": False, "order": 80,
     "i18n_title": "", "i18n_desc": ""},
]
_BY_NAME = {d["name"]: d for d in DEFAULTS}


def _files(name: str, scales, engine: str = "ncnn") -> list[Path]:
    """Файли моделі на диску. ncnn — .param+.bin (точне ім'я або суфікси масштабів,
    бо animevideov3 лежить як -x2/-x3/-x4); torch — один .pth/.safetensors у pth\\."""
    if engine == "torch":
        return [p for ext in (".pth", ".safetensors", ".ckpt")
                if (p := PTH_DIR / f"{name}{ext}").exists()]
    out = []
    for stem in [name] + [f"{name}-x{s}" for s in (scales or ())]:
        p, b = MODELS_DIR / f"{stem}.param", MODELS_DIR / f"{stem}.bin"
        if p.exists() and b.exists():
            out += [p, b]
    return out


def _is_base(name: str, scales, engine: str = "ncnn") -> bool:
    """Копія Автомонтажу → ensure_dirs() принесе її назад, видаляти немає сенсу."""
    if engine == "torch":
        return False                       # .pth ніхто нам назад не копіює
    for stem in [name] + [f"{name}-x{s}" for s in (scales or ())]:
        if (VA_MODELS / f"{stem}.param").exists():
            return True
    return False


def _calib() -> dict:
    try:
        return json.loads(CALIB_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def est_speed(name: str) -> float:
    """Оцінка мпікс/с для моделі, яку поставив розвідник (з його формули за архітектурою),
    поки її не заміряли по-справжньому першою пробою."""
    try:
        return float((_load_raw()["installed"].get(name) or {}).get("est_mpix_s") or 0)
    except Exception:
        return 0.0


def _speed(name: str, scales) -> float:
    """Мегапікселі ВХОДУ за секунду на робочому масштабі: спершу ФАКТ (calib.json),
    потім таблиця, потім оцінка розвідника. Робочий масштаб = найменший, який модель уміє
    (для ×4-моделей це 4, для animevideov3 — 2): саме так їх і ганяє plan_scale на 1080p→4K."""
    s = min(scales) if scales else 4
    c = _calib()
    v = c.get(f"{name}|{s}") or THROUGHPUT_MPIX_S.get((name, s))
    if v:
        return float(v)
    same = [x for (m, _), x in THROUGHPUT_MPIX_S.items() if m == name]
    if same:
        return float(min(same))
    return est_speed(name)


def _load_raw() -> dict:
    """Файл пулу: {"overrides": {ім'я: правки}, "installed": {ім'я: повний запис}}.
    Старий плоский формат (лише правки) читається як overrides — щоб оновлення проги
    не стерло те, що власник уже понакручував."""
    try:
        d = json.loads(POOL_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"overrides": {}, "installed": {}}
    if not isinstance(d, dict):
        return {"overrides": {}, "installed": {}}
    if "overrides" not in d and "installed" not in d:
        return {"overrides": d, "installed": {}}
    return {"overrides": d.get("overrides") or {}, "installed": d.get("installed") or {}}


def _save_raw(d: dict) -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    POOL_PATH.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")


def _all_defaults() -> list[dict]:
    """Зашиті вісім + те, що поставив розвідник. Порядок installed — після зашитих."""
    raw = _load_raw()
    out = [dict(d) for d in DEFAULTS]
    known = {d["name"] for d in DEFAULTS}
    for name, e in (raw["installed"] or {}).items():
        if name in known or not isinstance(e, dict):
            continue
        it = {"name": name, "title": e.get("title") or name, "desc": e.get("desc") or "",
              "group": e.get("group") if e.get("group") in GROUPS else "extra",
              "scales": e.get("scales") or [e.get("scale") or 4],
              "enabled": bool(e.get("enabled", True)), "order": int(e.get("order") or 900),
              "i18n_title": "", "i18n_desc": "", "engine": e.get("engine") or "torch",
              "installed": True, "arch": e.get("arch") or "", "author": e.get("author") or "",
              "license": e.get("license") or "", "src": e.get("src") or ""}
        out.append(it)
    return out


def catalog() -> list[dict]:
    """Повний пул: дефолти + встановлені розвідником + правки власника + правда з диска."""
    over = _load_raw()["overrides"]
    items = []
    for d in _all_defaults():
        it = dict(d)
        it.setdefault("engine", "ncnn")
        it.setdefault("installed", False)
        mine = {k: v for k, v in (over.get(d["name"]) or {}).items() if k in EDITABLE}
        it.update(mine)
        it["custom"] = sorted(mine)          # що власник переписав своїми руками → не перекладаємо
        if it.get("group") not in GROUPS:
            it["group"] = d["group"]
        files = _files(it["name"], it["scales"], it["engine"])
        # файл моделі є, але рахувати його нічим (важкий venv не поставлений) — це НЕ
        # «доступна модель»: інакше вибір у меню закінчився б падінням задачі
        it["present"] = bool(files) and (it["engine"] != "torch" or ENGINE2_PY.exists())
        it["size_mb"] = round(sum(f.stat().st_size for f in files) / 1e6, 1)
        it["base"] = _is_base(it["name"], it["scales"], it["engine"])
        it["speed"] = round(_speed(it["name"], it["scales"]), 3)
        it["measured"] = f"{it['name']}|{min(it['scales'])}" in _calib()
        items.append(it)
    # Точка відліку чіпа — ЗАВЖДИ мультяшна (це той «×1», до якого власник звик з 28.08).
    # Якби рахували від найшвидшої в пулі, то кожна нова швидка модель від розвідника
    # зсувала б усі числа (перевірено: поява SPAN перетворила звичні ×17/×2/×1 на ×29/×3/×2).
    anchor = next((i["speed"] for i in items if i["name"] == ANCHOR_MODEL and i["speed"] > 0),
                  max((i["speed"] for i in items if i["speed"] > 0), default=0.0))
    for it in items:
        # чіп рахуємо з ФАКТІВ, а не з рук: 28.08 у HTML стояло ×20/×3/×1, заміри дали ×17/×2/×1
        v = (anchor / it["speed"]) if it["speed"] > 0 and anchor else 0
        it["chip"] = round(v) if v >= 10 else round(v, 1)
    # ⭐ якість — ЛИШЕ заміряна (quality.json від app/quality.py: LPIPS на кадрах власника проти
    # мультяшної). Читаємо файл напряму, бо quality імпортує pool — цикл нам не треба.
    q = _quality()
    qa = (q.get(ANCHOR_MODEL) or {}).get("lpips")
    for it in items:
        m = q.get(it["name"]) or {}
        it["q_lpips"] = m.get("lpips") or 0
        it["q_n"] = m.get("n") or 0
        it["q_ratio"] = round(qa / m["lpips"], 2) if qa and m.get("lpips") else 0
        it["q_anchor"], it["q_anchor_lpips"] = ANCHOR_MODEL, qa or 0
    # Власник 08.09: «×1.5 гірше / ×17 довше — замудрено, зірка не зрозуміла» → дві прості цифри:
    #   якість NN % = схожість з оригіналом (100 − LPIPS·100), місце серед заміряних;
    #   h10 = години на 10 хв відео 1080p (18000 кадрів × 2.07 мпікс) при заміряній швидкості
    measured = sorted((it["q_lpips"], it["name"]) for it in items if it["q_lpips"])
    for it in items:
        it["q_pct"] = round((1 - it["q_lpips"]) * 100) if it["q_lpips"] else 0
        it["q_rank"] = next((i + 1 for i, (_, n) in enumerate(measured) if n == it["name"]), 0)
        it["q_total"] = len(measured)
        it["h10"] = round(18000 * 2.0736 / it["speed"] / 3600, 2) if it["speed"] > 0 else 0
    items.sort(key=lambda x: (GROUPS.index(x["group"]), x["order"]))
    return items


def _quality() -> dict:
    try:
        d = json.loads((DATA / "quality.json").read_text(encoding="utf-8"))
        return d.get("models") or {}
    except Exception:
        return {}


def menu() -> list[dict]:
    """Те, що показуємо в меню «ЯК»: увімкнене І фізично на диску."""
    return [i for i in catalog() if i["enabled"] and i["present"]]


def known() -> dict[str, tuple]:
    """{ім'я: (масштаби)} для валідації задачі — заміна зашитого engine.MODEL_SCALES."""
    return {i["name"]: tuple(i["scales"]) for i in catalog()}


def _entry(name: str) -> dict | None:
    return next((d for d in _all_defaults() if d["name"] == name), None)


def scales_for(name: str) -> tuple | None:
    d = _entry(name)
    return tuple(d["scales"]) if d else None


def engine_of(name: str) -> str:
    """Яким рушієм рахувати цю модель. Невідома → ncnn (як було завжди)."""
    d = _entry(name)
    return (d or {}).get("engine", "ncnn")


def save(items: list[dict]) -> list[dict]:
    """Пише ЛИШЕ редаговані поля і лише для відомих моделей — щоб кривий POST з фронта
    не вигадав неіснуючу модель, яку потім рушій не знайде."""
    raw = _load_raw()
    over, names = raw["overrides"], {d["name"] for d in _all_defaults()}
    for it in items or []:
        name = str(it.get("name") or "")
        if name not in names:
            continue
        cur = dict(over.get(name) or {})
        for k in EDITABLE:
            if k in it:
                cur[k] = (bool(it[k]) if k == "enabled" else
                          int(it[k]) if k == "order" else str(it[k])[:60])
        if cur.get("group") not in GROUPS:
            cur.pop("group", None)
        over[name] = cur
    _save_raw(raw)
    _fix_default_model()
    return catalog()


def add_installed(entry: dict) -> list[dict]:
    """Розвідник поставив модель → вона з'являється в пулі (група 📦 «Ще», щоб не лізти
    в те, що власник відібрав руками) і одразу доступна в меню «ЯК»."""
    raw = _load_raw()
    name = str(entry.get("name") or "").strip()
    if not name:
        return catalog()
    raw["installed"][name] = {k: entry.get(k) for k in
                              ("title", "desc", "group", "scales", "scale", "enabled", "order",
                               "engine", "arch", "author", "license", "src", "est_mpix_s")}
    _save_raw(raw)
    return catalog()


def forget_installed(name: str) -> None:
    raw = _load_raw()
    if raw["installed"].pop(name, None) is not None:
        raw["overrides"].pop(name, None)
        _save_raw(raw)


def reset() -> list[dict]:
    """Скидає ПРАВКИ власника, але НЕ видаляє встановлені моделі — інакше «повернути
    дефолт» тихо викидало б з меню те, що він сам поставив через розвідника."""
    raw = _load_raw()
    _save_raw({"overrides": {}, "installed": raw["installed"]})
    _fix_default_model()
    return catalog()


def remove_files(name: str) -> dict:
    """Видалити файли моделі. Базові (копії Автомонтажу) не чіпаємо — воскреснуть на старті."""
    d = _entry(name)
    if not d:
        return {"error": "невідома модель"}
    eng = d.get("engine", "ncnn")
    if _is_base(name, d["scales"], eng):
        return {"error": "це базова модель з архіву рушія — файли повернуться при старті; "
                         "прибери її з меню перемикачем"}
    files = _files(name, d["scales"], eng)
    if not files:
        return {"error": "файлів і так нема"}
    freed = sum(f.stat().st_size for f in files)
    for f in files:
        try:
            f.unlink()
        except OSError as e:
            return {"error": f"не видалив {f.name}: {e}"}
    if d.get("installed"):
        forget_installed(name)          # поставлену розвідником прибираємо з пулу цілком
    _fix_default_model()
    return {"ok": True, "freed_mb": round(freed / 1e6, 1), "pool": catalog()}


def _fix_default_model() -> None:
    """Дефолтна модель у налаштуваннях зникла з пулу (вимкнули/видалили файли) → мовчазний
    провал задачі при наступному «Покращити». Переставляємо на першу доступну."""
    st = load_settings()
    m = st.get("model")
    ok = {i["name"] for i in menu()}
    if m in ok or m == "fast":
        return
    if ok:
        save_settings({"model": next(i["name"] for i in menu())})
