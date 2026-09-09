# -*- coding: utf-8 -*-
"""📏 ПРОБА ЯКОСТІ — чіп «⭐ ×N краще за мультяшну» ВИМІРЯНИЙ, а не вигаданий.

Власник 08.09: голий чіп «×49» він прочитав як «покращує у 49 разів» («обманка»), і попросив:
«давай × від мультяшної — на скільки краще». Єдиний чесний спосіб — заміряти.

ЯК. Беремо ТВОЇ кадри з бібліотеки (короткою стороною ≥2160, найдинамічніші моменти, до 4 кадрів
з 2 відео), робимо з них 1080p (lanczos) і женемо кожну модель ТИМ САМИМ шляхом, що й реальний
рендер 1080p→4K (plan_scale: рідний масштаб моделі, потім зведення до 4K). Результат порівнюємо
з оригінальним 4K-кадром перцептивною відстанню LPIPS (AlexNet): менше = ближче до оригіналу НА ОКО.
PSNR/SSIM теж рахуємо, але для запису: GAN-моделі (UltraSharp) дають різкішу картинку з гіршим
PSNR — і власник обрав їх оком, тому чіп — з LPIPS.
    ⭐ ×1.4 = LPIPS мультяшної / LPIPS моделі = «у 1.4 раза ближче до оригіналу, ніж мультяшна».
    Менше за 1 — чесно «гірше».

МЕЖІ (сказано і в UI): (1) вхід — чистий lanczos-даунскейл, а не YouTube-1080p зі стисненням, тому
моделі, сильні саме на артефактах стиснення (x4v3), тут недооцінені; (2) 3-4 кадри з 1-2 відео —
оцінка порядку, не істина; (3) якщо в бібліотеці нема 4K — задача 540p→1080p (підписано).
Новий набір кадрів (додав 4K у бібліотеку) скидає старі оцінки: порівнювати можна лише на тих самих кадрах.

Фоновий воркер міряє ЛИШЕ коли прога не рендерить, не пробує, не качає і не перекладає (busy_fn):
рушій + Ollama + torch eager HAT разом у 12 ГБ VRAM не влазять.
"""
from __future__ import annotations
import hashlib, json, os, shutil, subprocess, threading, time
from pathlib import Path

from config import FFMPEG, DATA, TMP, ENGINE2_PY
import db, engine, pool
from media import run, extract_frame

QUAL_DIR = DATA / "quality"
QUAL_PATH = DATA / "quality.json"
METRICS_PY = Path(__file__).parent / "quality_metrics.py"
ANCHOR = "realesr-animevideov3"
TARGET = 2160
FRAMES_MAX = 4
_LOCK = threading.Lock()
_QLOCK = threading.Lock()
_QUEUE: list[str] = []
_STATE = {"running": False, "model": "", "phase": "", "last_error": ""}


def load() -> dict:
    try:
        d = json.loads(QUAL_PATH.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _save(d: dict) -> None:
    QUAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    QUAL_PATH.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")


def ready() -> bool:
    return ENGINE2_PY.exists() and METRICS_PY.exists()


# ── еталонний набір кадрів ────────────────────────────────────────────────────
def _pick_sources() -> tuple[list[dict], int]:
    """Кадри-джерела з бібліотеки: ≥2160 → задача 1080p→4K; інакше ≥1080 → 540p→1080p.
    До 2 відео × 2 моменти (найдинамічніший hard_t і ще один далі)."""
    import re
    # 🚨 власні виходи проги («seg10_x4», «…_t10_x2», «…__2160p_…») еталоном бути НЕ можуть:
    # їхня «деталь» намальована моделлю, і замір підіграв би саме їй. Лише нативні записи.
    bad = re.compile(r"(_x[1-8](\.|_)|__\d{3,4}p[_.])", re.I)
    out_dir = str(DATA / "out").lower()
    its = [i for i in db.items() if i.get("exists") and (i.get("info") or {}).get("short")
           and int(i["info"]["short"]) >= 1080
           and not bad.search(Path(i["path"]).name)
           and not str(i["path"]).lower().startswith(out_dir)]
    if not its:
        return [], 0
    # ціль = найбільша нативна коротка сторона (стеля 2160); вхід = ціль ÷ 2.
    # 1440p-записи → задача 720p→1440p: той самий ×2, що і 1080p→4K, лише кадр менший
    its.sort(key=lambda i: (-min(int(i["info"]["short"]), TARGET), -float(i["info"].get("dur") or 0)))
    target = min(int(its[0]["info"]["short"]), TARGET)
    good = [i for i in its if int(i["info"]["short"]) >= target]
    src: list[dict] = []
    for it in good[:2]:
        dur = float(it["info"].get("dur") or 0)
        t1 = float(it.get("hard_t") or dur * 0.4)
        ts = [t1] + ([min(dur - 0.5, t1 + max(2.0, dur * 0.3))] if dur > 4 else [])
        for t in ts:
            if len(src) >= FRAMES_MAX:
                break
            src.append({"id": int(it["id"]), "path": it["path"], "t": round(max(0.0, t), 2),
                        "name": Path(it["path"]).name, "short": int(it["info"]["short"])})
    return src, target


def _set_id(src: list[dict], target: int) -> str:
    return hashlib.md5(json.dumps([(s["id"], s["t"], target) for s in src]).encode()).hexdigest()[:10]


def _ensure_set(d: dict) -> tuple[dict, list[dict], int]:
    """gt/ (кадри цілі) і in/ (ціль ÷ 2) готуються один раз на набір; інший набір скидає оцінки."""
    src, target = _pick_sources()
    if not src:
        raise RuntimeError("у бібліотеці нема відео ≥1080p для еталона — додай хоч одне 4K")
    sid = _set_id(src, target)
    gt, inp = QUAL_DIR / sid / "gt", QUAL_DIR / sid / "in"
    if (d.get("set") or {}).get("id") != sid or len(list(gt.glob("f*.png"))) != len(src):
        shutil.rmtree(QUAL_DIR / sid, ignore_errors=True)
        gt.mkdir(parents=True); inp.mkdir(parents=True)
        for k, s in enumerate(src):
            raw = gt / f"raw{k}.png"
            if not extract_frame(Path(s["path"]), s["t"], raw):
                raise RuntimeError(f"не витяг кадр {s['name']} @ {s['t']} с")
            w, h = engine.png_size(raw)
            g = gt / f"f{k}.png"
            vf = engine.fit_vf(w, h, target)                  # 8K → 4K вниз; 4K лишається як є
            if vf:
                run([FFMPEG, "-y", "-v", "error", "-i", raw, "-vf", vf, g], timeout=180)
                raw.unlink(missing_ok=True)
            else:
                raw.rename(g)
            gw, gh = engine.png_size(g)
            run([FFMPEG, "-y", "-v", "error", "-i", g, "-vf",
                 engine._scale_vf(gw, gh, target // 2) + ":flags=lanczos", inp / f"f{k}.png"], timeout=180)
        d["set"] = {"id": sid, "target": target, "sources": src, "made": time.time()}
        d["models"] = {}
        _save(d)
    return d, src, target


# ── проба однієї моделі ───────────────────────────────────────────────────────
def probe(name: str) -> dict:
    """Рушій ×s на in/ → зведення до цілі → LPIPS/PSNR/SSIM проти gt/. Пише у quality.json."""
    if not ready():
        return {"error": "другий рушій (torch) не поставлений — LPIPS нема чим рахувати"}
    with _LOCK:
        d, src, target = _ensure_set(load())
        sid = d["set"]["id"]
        scales = tuple(pool.scales_for(name) or (4,))
        s = engine.plan_scale(target // 2, target, scales)["s"]
        work = TMP / f"quality_{name}"
        shutil.rmtree(work, ignore_errors=True)
        (work / "in").mkdir(parents=True); (work / "out").mkdir(); (work / "fit").mkdir()
        for p in (QUAL_DIR / sid / "in").glob("*.png"):
            shutil.copy2(p, work / "in" / p.name)
        _STATE.update(model=name, phase=f"рушій ×{s}")
        if not engine._PROBE_LOCK.acquire(timeout=300):
            return {"error": "проба зайнята"}
        try:
            rc, err = engine._run_engine(work / "in", work / "out", name, s)
        finally:
            engine._PROBE_LOCK.release()
        if rc != 0:
            return {"error": f"рушій упав (код {rc}): {(err or '')[-200:]}"}
        blank = engine.blank_output_check(work / "in", work / "out")
        if blank:
            return {"error": blank}
        _STATE["phase"] = "зведення до цілі"
        for p in sorted((work / "out").glob("*.png")):
            w, h = engine.png_size(p)
            vf = engine.fit_vf(w, h, target)
            dst = work / "fit" / p.name
            if vf:
                run([FFMPEG, "-y", "-v", "error", "-i", p, "-vf", vf, dst], timeout=300)
            else:
                shutil.copy2(p, dst)
        _STATE["phase"] = "LPIPS"
        env = dict(os.environ, TORCH_HOME=str(DATA / "engine2" / "torch_home"))
        cp = subprocess.run([str(ENGINE2_PY), str(METRICS_PY), str(QUAL_DIR / sid / "gt"), str(work / "fit")],
                            capture_output=True, text=True, encoding="utf-8", errors="replace",
                            timeout=900, env=env, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        try:
            m = json.loads((cp.stdout or "").strip().splitlines()[-1])
        except Exception:
            return {"error": f"метрика не відповіла: {(cp.stderr or cp.stdout or '')[-200:]}"}
        if m.get("error"):
            return {"error": m["error"]}
        rec = {"lpips": m["lpips"], "psnr": m["psnr"], "ssim": m["ssim"], "n": m["n"], "s": s,
               "frames": m["frames"], "ts": time.time()}
        d = load()
        if (d.get("set") or {}).get("id") != sid:
            return {"error": "набір кадрів змінився під час проби — повтор"}
        d.setdefault("models", {})[name] = rec
        _save(d)
        shutil.rmtree(work, ignore_errors=True)
        return {"ok": True, "model": name, **rec}


# ── оцінки для UI ─────────────────────────────────────────────────────────────
def scores() -> dict:
    d = load()
    ms = d.get("models") or {}
    a = (ms.get(ANCHOR) or {}).get("lpips")
    out = {}
    for name, m in ms.items():
        r = round(a / m["lpips"], 2) if a and m.get("lpips") else None
        out[name] = {"ratio": r, "lpips": m.get("lpips"), "psnr": m.get("psnr"), "ssim": m.get("ssim"),
                     "n": m.get("n"), "s": m.get("s"), "error": m.get("error"), "ts": m.get("ts")}
    st = d.get("set") or {}
    return {"anchor": ANCHOR, "anchor_lpips": a, "target": st.get("target"),
            "sources": [{"name": s["name"], "t": s["t"], "short": s["short"]} for s in st.get("sources") or []],
            "models": out}


def state() -> dict:
    return {"running": _STATE["running"], "model": _STATE["model"], "phase": _STATE["phase"],
            "last_error": _STATE["last_error"], "queue": list(_QUEUE), "ready": ready(), **scores()}


def _present() -> list[str]:
    return [m["name"] for m in pool.catalog() if m.get("present")]


def _missing() -> list[str]:
    have = load().get("models") or {}
    names = [n for n in _present() if n not in have]
    if ANCHOR in names:                                       # точка відліку — перша
        names.remove(ANCHOR); names.insert(0, ANCHOR)
    elif ANCHOR not in have and ANCHOR in _present():
        names.insert(0, ANCHOR)
    return names


def request(model: str | None = None, force: bool = False) -> dict:
    """Ручний запуск із 🛠: одна модель (завжди перемір) або всі (force — і заміряні теж)."""
    with _QLOCK:
        if model:
            if model not in _present():
                return {"error": "модель не поставлена"}
            names = [model]
        else:
            names = _present() if force else _missing()
            if ANCHOR in names:
                names.remove(ANCHOR); names.insert(0, ANCHOR)
        added = [n for n in names if n not in _QUEUE and n != _STATE["model"]]
        _QUEUE.extend(added)
    return {"ok": True, "queued": added, "queue": list(_QUEUE)}


def start_worker(busy_fn) -> None:
    """Фон: черга ручних запитів, а без них — усе поставлене, що ще не заміряно (кожна модель
    один раз). Міряє лише коли busy_fn() каже, що GPU наш і вільний."""
    def loop():
        time.sleep(25)                                        # старт проги — не заважаємо
        while True:
            name = None
            try:
                with _QLOCK:
                    if _QUEUE:
                        name = _QUEUE.pop(0)
                if name is None:
                    auto = _missing()
                    name = auto[0] if auto else None
                if name is None or not ready() or busy_fn():
                    time.sleep(6)
                    continue
                _STATE.update(running=True, model=name, phase="старт")
                r = probe(name)
                if r.get("error"):
                    _STATE["last_error"] = f"{name}: {r['error']}"
                    d = load()
                    d.setdefault("models", {})[name] = {"error": r["error"], "ts": time.time()}
                    _save(d)                                  # не крутити впалу модель по колу
                else:
                    _STATE["last_error"] = ""
            except Exception as e:
                _STATE["last_error"] = f"{type(e).__name__}: {e}"
                time.sleep(300)                               # напр. нема 4K у бібліотеці — не довбати
            finally:
                _STATE.update(running=False, model="", phase="")
            time.sleep(2)

    threading.Thread(target=loop, name="quality", daemon=True).start()
