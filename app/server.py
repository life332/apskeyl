# -*- coding: utf-8 -*-
"""💎 АПСКЕЙЛ — бекенд (FastAPI на 127.0.0.1:8391).

Окремий процес від вікна: вікно можна закрити, сервер живе (у Етапі 1 задач довших за
пробу немає, але архітектура закладена одразу). Ідентичність — /api/whoami: вікно чіпляється
лише до відповіді {"app":"apskeyl"}, а не до «порт зайнятий» (ці граблі вже стріляли).
Сам гасне після 30 хв без жодного запиту від вікна (щоб не висіти в памʼяті вічно).
"""
from __future__ import annotations
import os, sys, threading, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# Під pythonw stdout/stderr = None, і перший же print/лог убиває процес мовчки.
# Тому без консолі весь вивід — у файл. Якщо тека даних недоступна — падати не можна,
# лог іде у %TEMP% (діагностика «чого не стартує» важливіша за красиве місце).
# Теку даних шукаємо тим самим правилом, що й config (env → apskeyl.json → %LOCALAPPDATA%),
# але без імпорту config: якщо він зламаний, саме це й має потрапити в лог.
def _data_dir_guess() -> Path:
    env = os.getenv("APSK_DATA")
    if env:
        return Path(env)
    try:
        import json
        cfg = json.loads((Path(__file__).resolve().parents[1] / "apskeyl.json").read_text("utf-8"))
        if cfg.get("data_dir"):
            return Path(cfg["data_dir"])
    except Exception:
        pass
    return Path(os.getenv("LOCALAPPDATA") or ".") / "Apskeyl"


if sys.stdout is None or sys.stderr is None:
    try:
        _logdir = _data_dir_guess() / "logs"
        _logdir.mkdir(parents=True, exist_ok=True)
    except OSError:
        _logdir = Path(os.getenv("TEMP", ".")) / "apskeyl"
        _logdir.mkdir(parents=True, exist_ok=True)
    _f = open(_logdir / "server.log", "a", buffering=1, encoding="utf-8", errors="replace")
    sys.stdout = sys.stderr = _f

from uuid import uuid4

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.background import BackgroundTask

import config, db, engine, media, jobs, pool, scout, quality

app = FastAPI(title="apskeyl")
try:
    config.ensure_dirs()
    # прибрати сміття минулих сесій: проби (10-60 МБ кожна) і скрубер-кадри
    import shutil as _sh
    for _p in list(config.TMP.glob("probe*")) + list(config.TMP.glob("clip*")):
        _sh.rmtree(_p, ignore_errors=True)
    for _p in config.TMP.glob("scrub*.jpg"):
        try:
            _p.unlink()
        except OSError:
            pass
except OSError as e:
    print(f"тека даних {config.DATA} недоступна ({e}) — диск не змонтувався?", flush=True)

LAST_SEEN = {"t": time.time()}
IDLE_EXIT_S = 30 * 60


@app.middleware("http")
async def _touch(request, call_next):
    LAST_SEEN["t"] = time.time()
    resp = await call_next(request)
    # сторінка і скрипти — завжди перевіряти свіжість (WebView2 тримає профіль між
    # запусками; застарілий app.js після правки = «виправлено, а не працює»)
    p = request.url.path
    if p == "/" or p.startswith("/static/"):
        resp.headers["Cache-Control"] = "no-cache"
    return resp


@app.get("/api/whoami")
def whoami():
    return {"app": config.APP_NAME, "pid": os.getpid(), "port": config.PORT}


@app.get("/api/health")
def health():
    od = config.out_dir()
    return {"tools_missing": config.check_tools(),
            "free_gb": round(config.disk_free_gb(od), 1),        # диск РЕЗУЛЬТАТІВ (вибір власника)
            "out_drive": od.drive.rstrip(":") or str(od)[:1],
            "tmp_free_gb": round(config.disk_free_gb(config.TMP), 1),
            "tmp_drive": config.TMP.drive.rstrip(":"),
            "gpu_busy_other": engine.gpu_busy_by_other()}


# ── бібліотека ──────────────────────────────────────────────────────────────────
class AddReq(BaseModel):
    paths: list[str]


def _ingest_one(p: Path) -> dict:
    """Один файл → паспорт + превʼю + важка сцена + запис у БД.
    Файл під тим самим шляхом, але з іншим вмістом → ОНОВЛЮЄМО запис (ревізія 28.08:
    інакше перезаписане відео навічно тримало б старий паспорт)."""
    if not p.exists():
        return {"path": str(p), "ok": False, "why": "файл не знайдено"}
    if p.suffix.lower() not in config.VIDEO_EXTS:
        return {"path": str(p), "ok": False, "why": f"не відео ({p.suffix})"}
    try:
        key = media.file_key(p)
        existing = db.get_by_path(p)
        if existing is not None and existing["key"] == key:
            return {"path": str(p), "ok": False, "why": "уже в бібліотеці"}
        info = media.probe(p)
        thumb = media.make_thumb(p, key, info["dur"])
        hard_t = media.hard_scene(p, info["dur"])
        if existing is not None:
            db.refresh(p, key, info, thumb.name, hard_t)
            return {"path": str(p), "ok": True, "id": existing["id"], "refreshed": True}
        item_id = db.add(p, key, info, thumb.name, hard_t)
        if item_id is None:
            return {"path": str(p), "ok": False,
                    "why": "цей самий файл уже в бібліотеці (під іншим імʼям)"}
        return {"path": str(p), "ok": True, "id": item_id}
    except Exception as e:
        return {"path": str(p), "ok": False, "why": str(e)[:200]}


@app.post("/api/add")
def add_files(req: AddReq):
    return {"results": [_ingest_one(Path(p)) for p in req.paths]}


@app.post("/api/scan_inbox")
def scan_inbox():
    """Тека-приймальня <дані>\\inbox — третій, найнадійніший спосіб додати файл.
    Уже відомі шляхи пропускаємо ДО важкого аналізу (превʼю+сцена коштують секунди)."""
    known = db.known_paths()
    found = [p for p in config.INBOX.iterdir()
             if p.is_file() and p.suffix.lower() in config.VIDEO_EXTS]
    fresh = [p for p in found if str(p) not in known]
    return {"results": [_ingest_one(p) for p in fresh],
            "skipped_known": len(found) - len(fresh), "inbox": str(config.INBOX)}


@app.get("/api/library")
def library():
    its = db.items()
    for it in its:
        it["rec"] = media.recommend(it["info"])
    return {"items": its}


@app.delete("/api/item/{item_id}")
def delete_item(item_id: int):
    db.remove(item_id)          # тільки з бібліотеки; сам ФАЙЛ власника не чіпаємо ніколи
    return {"ok": True}


@app.get("/thumb/{name}")
def thumb(name: str):
    p = config.THUMBS / Path(name).name
    if not p.exists():
        return JSONResponse({"error": "нема превʼю"}, status_code=404)
    return FileResponse(p, media_type="image/jpeg")


# ── паспорт, прогноз, проба ────────────────────────────────────────────────────
@app.get("/api/passport/{item_id}")
def passport(item_id: int):
    it = db.get(item_id)
    if it is None:
        return JSONResponse({"error": "нема такого"}, status_code=404)
    it["rec"] = media.recommend(it["info"])
    return it


class EstReq(BaseModel):
    id: int
    target: str = "4k"          # fhd | 2k | 4k
    model: str = engine.DEFAULT_MODEL


@app.post("/api/estimate")
def estimate(req: EstReq):
    it = db.get(req.id)
    if it is None:
        return JSONResponse({"error": "нема такого"}, status_code=404)
    out = {}
    for key in engine.TARGETS:
        out[key] = engine.estimate(it["info"], key, req.model)
    return out


class ProbeReq(BaseModel):
    id: int
    t: float | None = None      # None → найдинамічніша сцена (порада Gemini)
    target: str = "4k"
    model: str = engine.DEFAULT_MODEL
    ops: dict | None = None     # Етап 4: sharpen/grain/denoise/codec


@app.post("/api/probe")
def probe(req: ProbeReq):
    it = db.get(req.id)
    if it is None:
        return JSONResponse({"error": "нема такого"}, status_code=404)
    if not it["exists"]:
        return JSONResponse({"error": "файл зник із диска"}, status_code=410)
    if engine.gpu_busy_by_other() and req.model != "fast":
        return JSONResponse({"error": "GPU зайнятий іншим realesrgan — зачекай або обери "
                                      "⚡ швидкий шлях"}, status_code=423)
    t = req.t if req.t is not None else (it["hard_t"] or it["info"]["dur"] * 0.4)
    return engine.probe_frame(Path(it["path"]), float(t), req.target, req.model, req.id,
                              req.ops)


@app.get("/probe_img/{item_id}/{name}")
def probe_img(item_id: int, name: str):
    p = config.TMP / f"probe{item_id}" / Path(name).name
    if not p.exists():
        return JSONResponse({"error": "нема"}, status_code=404)
    return FileResponse(p, media_type="image/jpeg",
                        headers={"Cache-Control": "no-store"})


# ── Етап 2: проба 10 секунд ────────────────────────────────────────────────────
@app.post("/api/probe_clip")
def probe_clip(req: ProbeReq):
    it = db.get(req.id)
    if it is None:
        return JSONResponse({"error": "нема такого"}, status_code=404)
    if not it["exists"]:
        return JSONResponse({"error": "файл зник із диска"}, status_code=410)
    if engine.gpu_busy_by_other() and req.model != "fast":
        return JSONResponse({"error": "GPU зайнятий іншим realesrgan — зачекай або обери "
                                      "⚡ швидкий шлях"}, status_code=423)
    t = req.t if req.t is not None else (it["hard_t"] or it["info"]["dur"] * 0.4)
    return engine.probe_clip(Path(it["path"]), float(t), req.target, req.model, req.id,
                             it["info"], req.ops)


@app.get("/api/probe_clip_progress")
def probe_clip_progress():
    p = dict(engine.CLIP_PROGRESS)
    p["elapsed"] = round(time.time() - p["t0"], 1) if p["t0"] else 0.0
    p["busy"] = engine.probe_busy()
    return p


@app.post("/api/probe_clip_cancel")
def probe_clip_cancel():
    engine.probe_clip_cancel()
    return {"ok": True}


@app.get("/probe_clip/{item_id}/{name}")
def probe_clip_file(item_id: int, name: str):
    p = config.TMP / f"clip{item_id}" / Path(name).name
    if not p.exists():
        return JSONResponse({"error": "нема"}, status_code=404)
    return FileResponse(p, media_type="video/mp4", headers={"Cache-Control": "no-store"})


@app.get("/api/frame/{item_id}")
def frame_at(item_id: int, t: float = 0.0):
    """Кадр для скрубера. Унікальний файл на запит + перевірка returncode — інакше при
    невдачі ffmpeg віддавався б СТАРИЙ кадр як нібито кадр у t (ревізія 28.08)."""
    it = db.get(item_id)
    if it is None or not it["exists"]:
        return JSONResponse({"error": "нема"}, status_code=404)
    outp = config.TMP / f"scrub{item_id}_{uuid4().hex[:8]}.jpg"
    cp = media.run([config.FFMPEG, "-y", "-v", "error", "-ss", f"{max(0.0, t):.2f}",
                    "-i", it["path"], "-frames:v", "1", "-vf", "scale=-2:360",
                    "-q:v", "4", outp], timeout=30)
    if cp.returncode != 0 or not outp.exists():
        return JSONResponse({"error": "кадр не витягся (за межами відео?)"},
                            status_code=500)
    def _rm(p=outp):
        try:
            p.unlink()
        except OSError:
            pass
    return FileResponse(outp, media_type="image/jpeg",
                        headers={"Cache-Control": "no-store"},
                        background=BackgroundTask(_rm))


# ── Етап 3: черга ──────────────────────────────────────────────────────────────
class JobReq(BaseModel):
    id: int
    target: str = "4k"
    model: str = "fast"
    ops: dict | None = None


@app.get("/api/settings")
def settings_get():
    s = config.load_settings()
    s["models_present"] = sorted(config.models_present())
    s["out_dir_effective"] = str(config.out_dir())
    s["logs_dir"] = str(config.LOGS)
    s["tmp_gb"] = round(sum(f.stat().st_size for f in config.TMP.rglob("*") if f.is_file()) / 1e9, 2) \
        if config.TMP.exists() else 0
    return s


class SettingsReq(BaseModel):
    values: dict


@app.post("/api/settings")
def settings_set(req: SettingsReq):
    v = dict(req.values)
    od = (v.get("out_dir") or "").strip()
    if od:
        p = Path(od)
        try:
            p.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            return JSONResponse({"error": f"тека результатів недоступна: {e}"}, status_code=400)
        if p.drive.upper() == "C:":
            v["_warn"] = "C: — системний диск із 40 ГБ; результати 4K краще на A:"
    s = config.save_settings(v)
    s["out_dir_effective"] = str(config.out_dir())
    if v.get("_warn"):
        s["warn"] = v["_warn"]
    return s


# ── Етап 6 п.4: пул моделей ────────────────────────────────────────────────────
class PoolReq(BaseModel):
    items: list[dict]


class PoolDelReq(BaseModel):
    name: str


@app.get("/api/pool")
def pool_get():
    """Повний пул (і вимкнені, і відсутні) — для налаштувань; меню бере enabled+present."""
    return {"pool": pool.catalog(), "groups": list(pool.GROUPS)}


@app.post("/api/pool")
def pool_set(req: PoolReq):
    return {"pool": pool.save(req.items)}


@app.post("/api/pool/reset")
def pool_reset():
    return {"pool": pool.reset()}


@app.post("/api/pool/delete")
def pool_delete(req: PoolDelReq):
    """Видалити ФАЙЛИ моделі (звільнити місце). Базові копії Автомонтажу не чіпаємо."""
    if db.jobs_active_count() > 0 or engine.probe_busy():
        return JSONResponse({"error": "зараз іде робота — видалення після"}, status_code=409)
    r = pool.remove_files(req.name)
    return JSONResponse(r, status_code=400) if r.get("error") else r


# ── Етап 6 п.1-3: розвідник нових моделей ──────────────────────────────────────
# Власник 08.09: «вкладка, в ній нові моделі рендера, опис, приблизна швидкість і
# можливість її встановити; інфу заносити парсером автономно, пошук раз на 4 дні».
SCOUT_LIST_FIELDS = ("key", "name", "author", "date", "arch", "arch_human", "scale",
                     "purpose", "avail", "type", "size_mb", "sec_per_frame",
                     "hours_10min", "installed", "license", "page", "src")


@app.get("/api/scout")
def scout_list(q: str = "", purpose: str = "", avail: str = "", scale: int = 0,
               only_new: int = 0, only_usable: int = 0, only_installed: int = 0,
               lang: str = "", sort: str = "new", limit: int = 60, offset: int = 0):
    """Список для вкладки. Каталог на 671 модель з описами — це мегабайти, тому назовні
    йде тільки те, що видно на картці; повний опис — окремим запитом на розкриття."""
    d = scout.load()
    models = list((d.get("models") or {}).values())
    new_keys = set(scout.new_keys(d))              # «нове» = за датою, рахується на кожен запит
    # «встановлено» — правда з ПУЛУ зараз, а не прапорець у каталозі: після 🗑 у налаштуваннях
    # каталог не переписується, і модель лишалась би «встановленою» до наступного оновлення
    inst = {i["name"] for i in pool.catalog() if i.get("installed")}
    for m in models:
        m["installed"] = m["key"] in inst
    ql = q.strip().lower()
    if ql:
        # str() навколо всього: у старих каталогах author міг бути списком → 500 на пошуку
        models = [m for m in models if ql in str(m.get("name") or "").lower() or ql in m["key"].lower()
                  or ql in str(m.get("author") or "").lower() or ql in str(m.get("arch") or "")
                  or ql in str(m.get("desc") or "").lower()]
    if purpose:
        models = [m for m in models if any(purpose in p for p in m.get("purpose") or [])]
    if avail:
        models = [m for m in models if m.get("avail") == avail]
    if scale:
        models = [m for m in models if int(m.get("scale") or 0) == scale]
    new_note = None
    if only_new:
        fresh = [m for m in models if m["key"] in new_keys]
        # власник 08.09: «нащо вкладка нові, якщо там нічого нема» — за 30 днів порожньо (найсвіжіший
        # реліз OMDB 2026-08-01), тому добираємо останні релізи за датою до 12 і кажемо про це в стані
        if len(fresh) < 12:
            dated = sorted((m for m in models if m.get("date") and m["key"] not in new_keys),
                           key=lambda m: str(m["date"]), reverse=True)
            fresh += dated[:12 - len(fresh)]
        new_note = {"fresh_30d": sum(1 for m in fresh if m["key"] in new_keys), "shown": len(fresh),
                    "newest": max((str(m.get("date") or "") for m in fresh), default="")}
        models = fresh
    if only_usable:      # те, що реально можна поставити одним кліком
        models = [m for m in models if m.get("avail") in ("direct", "mirror")
                  and m.get("type") in scout.USABLE_TYPES]
    if only_installed:   # власник 08.09: «не зрозуміло, що встановлено, що ні»
        models = [m for m in models if m.get("installed")]
    # сортування (власник 08.09: «градація по качеству»): клас архітектури — проксі, не замір
    if sort == "quality":
        models.sort(key=lambda m: (scout.tier_of(m.get("arch")), str(m.get("date") or "")), reverse=True)
    elif sort == "speed":
        models.sort(key=lambda m: float(m.get("sec_per_frame") or 0))
    elif sort == "name":
        models.sort(key=lambda m: str(m.get("name") or "").lower())
    else:                                                   # new: 🆕 спершу, далі за датою
        models.sort(key=lambda m: (m["key"] in new_keys, str(m.get("date") or "")), reverse=True)
    total = len(models)
    page = models[max(0, offset):max(0, offset) + max(1, min(limit, 200))]
    items = [{k: m.get(k) for k in SCOUT_LIST_FIELDS}
             | {"new": m["key"] in new_keys, "tier": scout.tier_of(m.get("arch")),
                "tier_human": scout.TIER_HUMAN[scout.tier_of(m.get("arch"))]}
             for m in page]
    scout.prefetch_desc([m["key"] for m in page], lang)   # переклади для видимої сторінки — наперед
    st = scout.state()
    st["engine2"] = engine.engine2_ready()
    return {"total": total, "items": items, "state": st, "new_note": new_note,
            "check_every_days": scout.CHECK_EVERY_S // 86400}


@app.get("/api/scout/model/{key}")
def scout_model(key: str):
    m = (scout.load().get("models") or {}).get(key)
    if not m:
        return JSONResponse({"error": "нема такої моделі"}, status_code=404)
    return m


@app.get("/api/scout/desc/{key}")
def scout_desc(key: str, lang: str = "uk"):
    """Опис мовою інтерфейсу (кеш → Ollama → оригінал). Перший переклад моделі триває
    5-20 с — фронт показує «перекладаю…», решту картки малює одразу."""
    r = scout.describe(key, lang)
    return JSONResponse(r, status_code=404) if r.get("error") else r


class ScoutInstallReq(BaseModel):
    key: str


@app.post("/api/scout/refresh")
def scout_refresh():
    """Ручна перевірка «зараз» — сама перевірка все одно йде раз на 4 дні автоматично."""
    if scout._STATE["running"]:
        return JSONResponse({"error": "перевірка вже іде"}, status_code=409)
    threading.Thread(target=lambda: scout.refresh(force=True), daemon=True).start()
    return {"ok": True}


@app.post("/api/scout/install")
def scout_install(req: ScoutInstallReq):
    if db.jobs_active_count() > 0 or engine.probe_busy():
        return JSONResponse({"error": "зараз іде робота — постав модель після"}, status_code=409)
    if not engine.engine2_ready():
        return JSONResponse({"error": "другий рушій (torch) не поставлений — моделі .pth "
                                      "нема чим рахувати"}, status_code=409)
    # скачування йде у фоні (власник 08.09: «немає кнопки скасувати»): тут лише старт,
    # прогрес — /api/scout/install_state, зупинка — /api/scout/install_cancel
    r = scout.start_install(req.key)
    return JSONResponse(r, status_code=400) if r.get("error") else r


@app.get("/api/scout/install_state")
def scout_install_state():
    return scout.install_state()


# ── 📏 проба якості: «⭐ ×N краще за мультяшну» — заміряно LPIPS на кадрах власника ──
@app.get("/api/quality")
def quality_state():
    return quality.state()


class QualityReq(BaseModel):
    model: str | None = None
    force: bool = False


@app.post("/api/quality/run")
def quality_run(req: QualityReq):
    if not quality.ready():
        return JSONResponse({"error": "другий рушій (torch) не поставлений — LPIPS нема чим рахувати"},
                            status_code=409)
    r = quality.request(req.model, req.force)
    return JSONResponse(r, status_code=400) if r.get("error") else r


@app.post("/api/scout/install_cancel")
def scout_install_cancel():
    r = scout.install_cancel()
    return JSONResponse(r, status_code=409) if r.get("error") else r


@app.post("/api/cleanup_tmp")
def cleanup_tmp():
    """Прибрати тимчасові теки (проби/кліпи/сміття) — лише коли черга не працює."""
    if db.jobs_active_count() > 0 or engine.probe_busy():
        return JSONResponse({"error": "зараз іде робота — прибирання після"}, status_code=409)
    import shutil as _sh
    freed = 0
    for p in config.TMP.iterdir():
        try:
            size = sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) if p.is_dir() else p.stat().st_size
            _sh.rmtree(p, ignore_errors=True) if p.is_dir() else p.unlink()
            freed += size
        except OSError:
            pass
    return {"ok": True, "freed_gb": round(freed / 1e9, 2)}


@app.post("/api/jobs")
def job_create(req: JobReq):
    it = db.get(req.id)
    if it is None:
        return JSONResponse({"error": "нема такого"}, status_code=404)
    if not it["exists"]:
        return JSONResponse({"error": "файл зник із диска"}, status_code=410)
    if req.target not in engine.TARGETS:
        return JSONResponse({"error": "невідома ціль"}, status_code=400)
    if req.model != "fast":
        if req.model not in pool.known():
            return JSONResponse({"error": "невідома модель"}, status_code=400)
        if req.model not in {i["name"] for i in pool.catalog() if i["present"]}:
            return JSONResponse({"error": f"файлів моделі {req.model} нема на диску — "
                                          f"обери іншу в меню «ЯК»"}, status_code=409)
    free = config.disk_free_gb()
    if free < config.MIN_FREE_GB_START:
        return JSONResponse({"error": f"мало місця на A: вільно {free:.0f} ГБ, треба "
                                      f"≥{config.MIN_FREE_GB_START} — звільни і повтори"},
                            status_code=409)
    ops = engine.norm_ops(req.ops)
    dup = [j for j in db.jobs_list() if j["item_id"] == req.id and j["state"] in db.ACTIVE
           and j["recipe"].get("target") == req.target and j["recipe"].get("model") == req.model
           and j["recipe"].get("ops") == ops]
    if dup:
        return JSONResponse({"error": "така задача вже в черзі"}, status_code=409)
    jid = db.job_add(req.id, Path(it["path"]),
                     {"target": req.target, "model": req.model, "ops": ops})
    jobs.wake()
    return {"ok": True, "job_id": jid}


@app.get("/api/jobs")
def job_list():
    out = []
    for j in db.jobs_list():
        j["name"] = Path(j["src"]).name
        j["pct"] = round(100 * j["frames_done"] / j["frames_total"], 1) if j["frames_total"] else 0
        j["alive"] = j["state"] in db.RUNNING and time.time() - (j["heartbeat"] or 0) < 60
        out.append(j)
    return {"jobs": out, "active": db.jobs_active_count()}


@app.post("/api/job/{job_id}/{action}")
def job_action(job_id: int, action: str):
    j = db.job_get(job_id)
    if j is None:
        return JSONResponse({"error": "нема"}, status_code=404)
    if action == "cancel":
        if j["state"] in db.RUNNING:
            jobs.control(job_id, "cancel")
        elif j["state"] in ("QUEUED", "PAUSED"):
            db.job_update(job_id, state="CANCELED", reason="скасовано", finished=time.time())
            import shutil as _sh
            _sh.rmtree(config.TMP / f"job{job_id}", ignore_errors=True)
            if j["item_id"]:
                db.library_status(j["item_id"], "new")
    elif action == "pause":
        if j["state"] in db.RUNNING:
            jobs.control(job_id, "pause")
        elif j["state"] == "QUEUED":
            db.job_update(job_id, state="PAUSED", reason="пауза")
    elif action == "resume":
        if j["state"] in ("PAUSED", "FAILED"):
            db.job_update(job_id, state="QUEUED", reason="", pid=0)
            jobs.wake()
    else:
        return JSONResponse({"error": "невідома дія"}, status_code=400)
    return {"ok": True, "job": db.job_get(job_id)}


@app.delete("/api/job/{job_id}")
def job_remove(job_id: int):
    j = db.job_get(job_id)
    if j is None:
        return {"ok": True}
    if j["state"] in db.RUNNING:
        return JSONResponse({"error": "спершу скасуй"}, status_code=409)
    db.job_delete(job_id)                 # ЗАПИС; готовий файл у out\ не чіпаємо
    return {"ok": True}


class PathReq(BaseModel):
    path: str


@app.post("/api/open_folder")
def open_folder(req: PathReq):
    p = Path(req.path)
    if not p.exists():
        return JSONResponse({"error": "файлу вже нема"}, status_code=404)
    import subprocess
    subprocess.Popen(["explorer", "/select,", str(p)])
    return {"ok": True}


class UrlReq(BaseModel):
    url: str


# Відкриваємо ЛИШЕ сторінки каталогу і сховищ моделей. Прога не має ставати кнопкою
# «відкрий що завгодно»: сюди приходить те, що прийшло з мережі, і довіряти йому не можна.
OPEN_URL_HOSTS = ("openmodeldb.info", "huggingface.co", "github.com")


@app.post("/api/open_url")
def open_url(req: UrlReq):
    from urllib.parse import urlparse
    u = urlparse(req.url or "")
    if u.scheme not in ("http", "https"):
        return JSONResponse({"error": "не посилання"}, status_code=400)
    host = (u.netloc or "").lower().split(":")[0]
    if not any(host == h or host.endswith("." + h) for h in OPEN_URL_HOSTS):
        return JSONResponse({"error": f"відкриваю лише {', '.join(OPEN_URL_HOSTS)}"},
                            status_code=400)
    import webbrowser
    webbrowser.open(req.url)
    return {"ok": True}


# ── статика ────────────────────────────────────────────────────────────────────
@app.get("/")
def index():
    return FileResponse(config.WEB / "index.html")


app.mount("/static", StaticFiles(directory=config.WEB), name="static")


def _idle_watch():
    while True:
        time.sleep(60)
        try:
            busy = engine.probe_busy() or db.jobs_active_count() > 0
        except Exception:
            busy = True
        if time.time() - LAST_SEEN["t"] > IDLE_EXIT_S and not busy:
            os._exit(0)          # тихо гаснемо: вікна давно нема, черга порожня


if __name__ == "__main__":
    import uvicorn
    jobs.start()                 # воркер черги + resume задач, що були в роботі
    scout.start_schedule()       # розвідник моделей: сам перевіряє раз на 4 дні
    # фоновий переклад описів через Ollama — лише коли GPU не зайнятий нашою роботою
    scout.start_translate_worker(
        lambda: db.jobs_active_count() > 0 or engine.probe_busy() or scout._INSTALL["running"]
        or quality._STATE["running"])
    # 📏 проба якості моделей (LPIPS на кадрах власника) — теж лише на вільному GPU
    quality.start_worker(
        lambda: db.jobs_active_count() > 0 or engine.probe_busy() or scout._INSTALL["running"]
        or scout._TR_STATE.get("active") or engine.gpu_busy_by_other())
    threading.Thread(target=_idle_watch, daemon=True).start()
    uvicorn.run(app, host="127.0.0.1", port=config.PORT, log_level="warning")
