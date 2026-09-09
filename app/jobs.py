# -*- coding: utf-8 -*-
"""⚙️ ДВИГУН ЗАДАЧ (Етап 3): черга → сегменти → збірка. Потік у процесі сервера.

Правила (02_ТЕХПЛАН_ДВИЖОК.md):
 - одночасно РІВНО ОДНА задача (GPU один; поруч живий стрім A1 на тій самій карті);
 - швидкий шлях (дефолт після вердикту власника 28.08) — один прохід ffmpeg, без
   тимчасових кадрів; нейромережа (опція) — СЕГМЕНТАМИ 5-60 с, бо 1 с 4K = ~214 МБ PNG;
 - commit після кожного сегмента → після світла продовжуємо з наступного;
 - прогрес = ГОТОВІ ФАЙЛИ у теці сегмента раз на секунду (рушій нічого не друкує);
 - ETA: спершу з таблиці/калібровки, після першого сегмента — за фактом (EMA);
 - сторожі: диск перед КОЖНИМ сегментом, чужий realesrgan → чекаємо, зависання
   (жодного нового кадру STALL_S) → знімаємо СВІЙ процес і пробуємо сегмент ще раз;
 - скасування вбиває ТІЛЬКИ pid, які самі породили. Ніколи за іменем образу;
 - звук не чіпаємо: фінальний мукс -c:a copy з оригіналу (aac, якщо кодек не лізе в mp4);
 - вихід атомарний: tmp на тому ж томі → os.replace; оригінал не перезаписується ніколи;
 - поки черга не порожня — ПК не спить (екран хай гасне).
"""
from __future__ import annotations
import ctypes, json, math, os, shutil, subprocess, threading, time
from pathlib import Path

import db, engine, media, procs
from config import (FFMPEG, FFPROBE, REALESRGAN, MODELS_DIR, GPU_ID, TMP, OUT,
                    MIN_FREE_GB_START, MIN_FREE_GB_RUN, TMP_GB_PER_SEC_4K, disk_free_gb,
                    load_settings)
from media import run, NO_WIN

YIELD_NAP_S = 8          # 🛡 кодер ефіру просів → рушій спить стільки секунд
YIELD_CHECK_S = 10       # як часто дивимось на ефір
SOFT_AFTER_NAPS = 3      # ≥ стільки поступок за сегмент → наступні сегменти в «м'якому режимі»
_SOFT = {"on": False}    # м'який режим: -j 1:1:1 (один GPU-потік) — менше тисне на кодер ефіру

STALL_S = 180            # рушій мовчить стільки → вважаємо зависанням
SEG_RETRY = 1            # скільки разів переганяти сегмент після зависання/падіння
MP4_AUDIO_OK = {"aac", "mp3", "ac3", "eac3", "alac"}

_WAKE = threading.Event()
_CTRL: dict[int, str] = {}         # job_id → "cancel" | "pause"
_PROC: dict[int, subprocess.Popen] = {}
_started = False


class JobStop(Exception):
    """Скасування або пауза, піднята з середини конвеєра."""


# ── службове ────────────────────────────────────────────────────────────────────
def wake():
    _WAKE.set()


def control(job_id: int, what: str):
    _CTRL[job_id] = what
    p = _PROC.get(job_id)
    if what == "cancel" and p is not None and p.poll() is None:
        try:
            p.kill()                                   # тільки СВІЙ процес
        except Exception:
            pass
    wake()


def _check(jid: int):
    w = _CTRL.get(jid)
    if w:
        raise JobStop(w)


def _sleep_block(on: bool):
    """ES_CONTINUOUS | ES_SYSTEM_REQUIRED без ES_DISPLAY_REQUIRED — екран гасне, ПК ні."""
    try:
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | (0x00000001 if on else 0))
    except Exception:
        pass


def _beep():
    try:
        import winsound
        winsound.MessageBeep(winsound.MB_ICONASTERISK)
    except Exception:
        pass


def _even(n: int) -> int:
    return n if n % 2 == 0 else n - 1


def _probe_out(p: Path) -> dict:
    cp = run([FFPROBE, "-v", "error", "-show_entries",
              "stream=codec_type,width,height,nb_frames:format=duration,size",
              "-of", "json", p], timeout=60)
    try:
        j = json.loads(cp.stdout or "{}")
        v = next((s for s in j.get("streams", []) if s.get("codec_type") == "video"), {})
        a = [s for s in j.get("streams", []) if s.get("codec_type") == "audio"]
        return {"dur": float(j.get("format", {}).get("duration") or 0),
                "size": int(j.get("format", {}).get("size") or 0),
                "w": int(v.get("width") or 0), "h": int(v.get("height") or 0),
                "audio": len(a)}
    except Exception:
        return {"dur": 0, "size": 0, "w": 0, "h": 0, "audio": 0}


def _audio_args(info: dict, exact: bool = False) -> list[str]:
    if not info.get("acodec"):
        return ["-an"]
    if info["acodec"] in MP4_AUDIO_OK and not exact:
        return ["-c:a", "copy"]
    return ["-c:a", "aac", "-b:a", "192k"]      # opus/vorbis/pcm у mp4 не лізуть; exact = точний зріз


def _stream_starts(src: Path) -> tuple[float, float]:
    """start_time відео й аудіо. YouTube/нарізані файли часто мають відео з 0.667 с, а
    аудіо з 0: плеєри, що шанують мітки, грають синхронно, а ті, що ні, — зсувають губи.
    Тому нормалізуємо: обидва потоки починаємо зі СПІЛЬНОЇ точки і пишемо з нуля."""
    cp = run([FFPROBE, "-v", "error", "-show_entries", "stream=codec_type,start_time",
              "-of", "json", src], timeout=60)
    v0 = a0 = 0.0
    try:
        for s in json.loads(cp.stdout or "{}").get("streams", []):
            st = float(s.get("start_time") or 0)
            if s.get("codec_type") == "video":
                v0 = st
            elif s.get("codec_type") == "audio" and a0 == 0.0:
                a0 = st
    except Exception:
        pass
    return v0, a0


def _common_start(src: Path) -> float:
    v0, a0 = _stream_starts(src)
    return max(v0, a0, 0.0) if abs(v0 - a0) > 0.02 else 0.0


def _out_name(src: Path, out_short: int, tag: str) -> Path:
    import config as _cfg
    od = _cfg.out_dir()
    base = od / f"{src.stem}__{out_short}p_{tag}.mp4"
    n = 2
    while base.exists():
        base = od / f"{src.stem}__{out_short}p_{tag}_{n}.mp4"
        n += 1
    return base


def _verify(out: Path, src_dur: float, expect_audio: bool) -> str | None:
    """None = ок, інакше причина провалу. Розсинхрон = критерій ПРОВАЛУ Етапу 3."""
    if not out.exists() or out.stat().st_size < 10_000:
        return "вихідний файл порожній"
    o = _probe_out(out)
    if o["w"] == 0:
        return "вихід не читається ffprobe"
    if src_dur > 1 and abs(o["dur"] - src_dur) > max(0.5, src_dur * 0.002):
        return f"тривалість розійшлась: {o['dur']:.2f} проти {src_dur:.2f} с — розсинхрон"
    if expect_audio and o["audio"] == 0:
        return "звук загубився при муксі"
    return None


# ── воркер ──────────────────────────────────────────────────────────────────────
def _reap_orphans():
    """Після падіння/kill сервера його realesrgan міг лишитись на GPU. Це НАШ процес —
    його pid записаний у jobs.pid — і лише тому його можна зняти (правило: тільки
    породжені нами PID з БД, ніколи за іменем образу). Інакше новий сервер чекав би
    на «чужий» GPU 70 с, як і сталось у тесті 28.08."""
    for j in db.jobs_list():
        pid = int(j.get("pid") or 0)
        if not pid or j["state"] not in db.RUNNING:
            continue
        try:
            cp = run(["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"], timeout=10)
            line = (cp.stdout or "").strip().splitlines()[-1] if cp.stdout else ""
            if not line.startswith(('"realesrgan-ncnn-vulkan.exe"', '"ffmpeg.exe"')):
                continue                                  # pid уже інший або мертвий
            run(["taskkill", "/PID", str(pid), "/F"], timeout=10)
            print(f"черга: знято сирітський процес {pid} задачі {j['id']}", flush=True)
        except Exception:
            pass


def start():
    global _started
    if _started:
        return
    _started = True
    _reap_orphans()
    n = db.recover_after_restart()
    if n:
        print(f"черга: {n} задач(і) продовжено після перезапуску", flush=True)
    threading.Thread(target=_worker, name="jobs", daemon=True).start()


def _worker():
    while True:
        try:
            _auto_resume_paused()
            job = db.next_queued()
            if job is None:
                _sleep_block(False)
                _WAKE.wait(5)
                _WAKE.clear()
                continue
            _sleep_block(True)
            _run_job(job)
        except Exception as e:                        # воркер не сміє померти
            print("воркер:", str(e)[:200], flush=True)
            time.sleep(3)


def _auto_resume_paused():
    """Пауза через диск — сама знімається, коли місце зʼявилось."""
    for j in db.jobs_list():
        if j["state"] == "PAUSED" and j["reason"].startswith("диск") \
                and disk_free_gb() >= MIN_FREE_GB_START:
            db.job_update(j["id"], state="QUEUED", reason="місце зʼявилось — продовжую")


def _run_job(job: dict):
    jid = job["id"]
    _CTRL.pop(jid, None)
    src = Path(job["src"])
    recipe = job["recipe"]
    t_start = time.time()
    prev_elapsed = float(job.get("elapsed_s") or 0)

    def upd(**f):
        db.job_update(jid, heartbeat=time.time(),
                      elapsed_s=prev_elapsed + (time.time() - t_start), **f)

    try:
        if not src.exists():
            raise RuntimeError("файл зник із диска")
        free = disk_free_gb()
        if free < MIN_FREE_GB_START:
            upd(state="PAUSED", reason=f"диск: вільно {free:.0f} ГБ, треба ≥{MIN_FREE_GB_START}")
            return
        info = media.probe(src)
        upd(state="PREPARING", reason="читаю файл",
            started=job["started"] or time.time(), pid=0)
        short = info["short"]
        target = engine.TARGETS.get(recipe.get("target", "4k"), 2160)
        model = recipe.get("model", "fast")
        ops = engine.norm_ops(recipe.get("ops"))
        plan = engine.plan_scale(short, target, engine.model_scales(model))
        fast = model == "fast" or plan["op"] != "nn"
        work = TMP / f"job{jid}"
        work.mkdir(parents=True, exist_ok=True)
        if fast:
            out_short = target                     # fit_vf зводить у ОБИДВА боки
            result = _run_fast(jid, src, info, target, work, upd, ops)
            tag = "fast"
        else:
            out_short = plan["down"] or short * plan["s"]
            result = _run_nn(jid, src, info, plan, model, work, upd, ops)
            tag = {"realesr-animevideov3": "anime", "realesrgan-x4plus": "x4plus",
                   "realesr-general-x4v3": "general", "4x-UltraSharp-opt-fp16": "ultrasharp",
                   "4x-NMKD-Siax-200k": "siax", "4xLSDIRplus": "lsdir"}.get(model, "nn") \
                + f"x{plan['s']}"
        if ops.get("codec") == "hevc_nvenc":
            tag += "_hevc"
        # verify → атомарно у out
        upd(state="VERIFYING", reason="перевіряю вихід")
        why = _verify(result, info["dur"] - _common_start(src), bool(info.get("acodec")))
        if why:
            raise RuntimeError(why)
        out_path = _out_name(src, out_short, tag)
        if out_path.drive.lower() == result.drive.lower():
            os.replace(result, out_path)               # той самий том → атомарно
        else:                                          # інший диск: копія .part + rename
            part = out_path.with_suffix(".part")
            shutil.copy2(result, part)
            os.replace(part, out_path)
            result.unlink(missing_ok=True)
        side = {"src": str(src), "recipe": recipe, "model": model, "plan": plan,
                "frames": db.job_get(jid)["frames_total"], "took_s": round(prev_elapsed +
                time.time() - t_start), "made": time.strftime("%Y-%m-%d %H:%M")}
        out_path.with_suffix(".json").write_text(json.dumps(side, ensure_ascii=False,
                                                            indent=1), encoding="utf-8")
        shutil.rmtree(work, ignore_errors=True)
        upd(state="DONE", reason="", out_path=str(out_path), out_size=out_path.stat().st_size,
            finished=time.time(), pid=0, eta_s=0)
        if job.get("item_id"):
            db.library_status(job["item_id"], "done")
        _beep()
    except JobStop as e:
        _kill_own(jid)
        if str(e) == "cancel":
            shutil.rmtree(TMP / f"job{jid}", ignore_errors=True)
            upd(state="CANCELED", reason="скасовано", finished=time.time(), pid=0)
            if job.get("item_id"):
                db.library_status(job["item_id"], "new")
        else:
            upd(state="PAUSED", reason="пауза", pid=0)
    except Exception as e:
        _kill_own(jid)
        upd(state="FAILED", reason=str(e)[:300], finished=time.time(), pid=0)
        if job.get("item_id"):
            db.library_status(job["item_id"], "error")
    finally:
        _CTRL.pop(jid, None)
        _PROC.pop(jid, None)


def _kill_own(jid: int):
    p = _PROC.get(jid)
    if p is not None and p.poll() is None:
        try:
            p.kill()
            p.wait(timeout=10)
        except Exception:
            pass


# ── швидкий шлях: один прохід ffmpeg ────────────────────────────────────────────
def _run_fast(jid, src: Path, info: dict, target: int, work: Path, upd, ops: dict) -> Path:
    w, h, short = info["w"], info["h"], info["short"]
    fps = round(min(max(float(info["fps"] or 30.0), 1.0), 60.0), 3)
    vf = engine.vf_chain(f"fps={fps}", engine.ops_pre_vf(ops), engine.fit_vf(w, h, target),
                         engine.ops_post_vf(ops) or "cas=0.4",
                         "scale=trunc(iw/2)*2:trunc(ih/2)*2")
    out = work / "out.mp4"
    tc = _common_start(src)            # спільний старт відео/аудіо → без зсуву губ у будь-якому плеєрі
    total = int(round(max(info["dur"] - tc, 0) * fps))
    cmd = [str(FFMPEG), "-y", "-v", "error", "-nostats", "-progress", "pipe:1",
           *engine.ff_threads(),
           *(["-ss", f"{tc:.3f}"] if tc else []),
           "-i", str(src), "-map", "0:v:0", "-map", "0:a?", "-vf", vf,
           *engine.enc_args(ops.get("codec", "libx264")),
           *_audio_args(info, exact=bool(tc)), "-map_metadata", "0",
           "-movflags", "+faststart", str(out)]
    upd(state="ENCODING", reason="швидкий шлях: один прохід", frames_total=total,
        seg_total=1, seg_done=0)
    proc = procs.spawn(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       text=True, encoding="utf-8", errors="replace")
    _PROC[jid] = proc
    upd(pid=proc.pid)
    t0, last, done, speed = time.time(), 0.0, 0, 0.0
    for line in proc.stdout:
        if line.startswith("frame="):
            try:
                done = int(line.split("=")[1])
            except ValueError:
                pass
        if time.time() - last > 2:
            el = max(time.time() - t0, 0.1)
            speed = done / el
            eta = (total - done) / speed if speed > 0 and total else 0
            upd(frames_done=done, speed=round(speed, 2), eta_s=round(eta))
            last = time.time()
            try:
                _check(jid)
            except JobStop:
                proc.kill()
                raise
    proc.wait()
    err = proc.stderr.read()
    if proc.returncode != 0 or not out.exists():
        raise RuntimeError(f"ffmpeg (код {proc.returncode}): {err[-300:]}")
    upd(frames_done=total, seg_done=1, eta_s=0)
    el = time.time() - t0
    if total >= 300 and el > 5:                      # калібрування ETA швидкого шляху за фактом
        engine.calib_update("fast", target, total / el)
    return out


# ── нейромережа: сегментами ─────────────────────────────────────────────────────
def _seg_len_s(out_short: int, src_short: int) -> float:
    # приймання Етапу 3/5: пік диска ≤10 ГБ → бюджет сегмента 10 ГБ (1080p→4K ≈ 36 с)
    budget_gb = min(10.0, disk_free_gb() * 0.15)
    per_sec = TMP_GB_PER_SEC_4K * (out_short / 2160) ** 2 + 0.06 * (src_short / 1080) ** 2
    cap = float(os.getenv("APSK_SEG_MAX_S", "60"))     # тести: маленькі сегменти → resume
    return max(5.0, min(cap, budget_gb / max(per_sec, 0.01)))


def _run_nn(jid, src: Path, info: dict, plan: dict, model: str, work: Path, upd,
            ops: dict) -> Path:
    w, h, short, dur = info["w"], info["h"], info["short"], float(info["dur"])
    fps = round(min(max(float(info["fps"] or 30.0), 1.0), 60.0), 3)
    tc = _common_start(src)            # спільний старт відео/аудіо (див. _stream_starts)
    total = int(round(max(dur - tc, 0) * fps))
    out_short = plan["down"] or short * plan["s"]
    segs = db.seg_list(jid)
    if not segs:                                      # нова задача → нарізаємо
        # 🚨 08.09: бюджет рахувався по ЦІЛІ (out_short), а тимчасові PNG пише РУШІЙ — у
        # своїй роздільній. Для 1080p→4K моделлю ×4 це 4320p: кадр 33-48 МБ замість
        # очікуваних 8, і сегмент на 36 с з'їдав ~36 ГБ замість обіцяних ≤10 (приймання
        # Етапу 3). Для ×2-моделей збігалось, тому й не вилізло раніше.
        seg_len = _seg_len_s(short * plan["s"], short)
        n = max(1, math.ceil((dur - tc) / seg_len))
        plan_segs = []
        for i in range(n):
            t0, t1 = tc + i * seg_len, min(tc + (i + 1) * seg_len, dur)
            f0, f1 = int(round(t0 * fps)), int(round(t1 * fps))   # точні межі в КАДРАХ
            if f1 > f0:
                plan_segs.append((i, round(t0, 3), round(t1, 3), f1 - f0))
        db.seg_init(jid, plan_segs)
        segs = db.seg_list(jid)
    done_frames = sum(s["frames"] for s in segs if s["state"] == "done")
    upd(state="PROCESSING", seg_total=len(segs), seg_done=sum(s["state"] == "done" for s in segs),
        frames_total=total, frames_done=done_frames,
        reason=f"нейромережа {model} ×{plan['s']} · сегментами по ~{segs[0]['t1']-segs[0]['t0']:.0f} с")
    speed_ema = 0.0
    for s in segs:
        if s["state"] == "done" and s["path"] and Path(s["path"]).exists():
            continue
        _check(jid)
        _guards(jid, upd)
        for attempt in range(SEG_RETRY + 1):
            try:
                frames, ms, path, spd, naps = _do_segment(jid, src, s, fps, plan, model, work,
                                                          upd, done_frames, total, speed_ema, ops)
                break
            except JobStop:
                raise
            except Exception as e:
                if attempt >= SEG_RETRY:
                    raise RuntimeError(f"сегмент {s['idx']}: {str(e)[:200]}")
                upd(reason=f"сегмент {s['idx']} впав ({str(e)[:60]}) — пробую ще раз")
                time.sleep(3)
        speed_ema = spd if not speed_ema else speed_ema * 0.6 + spd * 0.4
        if frames >= 60 and naps == 0:                 # калібруємо лише «чисті» сегменти
            engine.calib_update(model, plan["s"], spd * w * h / 1e6)
        # адаптація до ефіру: багато поступок → м'який режим; чистий сегмент у м'якому → назад
        if naps >= SOFT_AFTER_NAPS and not _SOFT["on"]:
            _SOFT["on"] = True
            upd(reason=f"🛡 ефір страждав ({naps} поступок) → м'який режим: один GPU-потік")
        elif naps == 0 and _SOFT["on"]:
            _SOFT["on"] = False
        done_frames += frames
        db.seg_update(jid, s["idx"], state="done", frames=frames, ms=ms, path=str(path))
        eta = (total - done_frames) / speed_ema if speed_ema > 0 else 0
        upd(seg_done=db.job_get(jid)["seg_done"] + 1, frames_done=done_frames,
            speed=round(speed_ema, 2), eta_s=round(eta))
    # фінал: concat -c copy + звук з оригіналу
    _check(jid)
    upd(state="ENCODING", reason="збираю сегменти і звук")
    segs = db.seg_list(jid)
    lst = work / "list.txt"
    lst.write_text("".join(f"file '{Path(s['path']).name}'\n" for s in segs), encoding="utf-8")
    out = work / "out.mp4"
    cmd = [str(FFMPEG), "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", "list.txt",
           *(["-ss", f"{tc:.3f}"] if tc else []), "-i", str(src),
           "-map", "0:v:0", "-map", "1:a?", "-c:v", "copy",
           *_audio_args(info, exact=bool(tc)), "-map_metadata", "1", "-map_chapters", "1",
           "-movflags", "+faststart", "out.mp4"]
    proc = procs.spawn(cmd, cwd=str(work), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       text=True, encoding="utf-8", errors="replace")
    try:
        _, err = proc.communicate(timeout=3600)
    except subprocess.TimeoutExpired:
        proc.kill(); _, err = proc.communicate()
    if proc.returncode != 0 or not out.exists():
        raise RuntimeError(f"збірка: {(err or '')[-300:]}")
    for s in segs:                                     # сегменти більше не потрібні
        try:
            Path(s["path"]).unlink()
        except OSError:
            pass
    return out


def _guards(jid, upd):
    """Диск і GPU перед кожним сегментом. Чекаємо, а не падаємо."""
    waited = False
    while True:
        _check(jid)
        free = disk_free_gb()
        if free < MIN_FREE_GB_RUN:
            upd(state="PAUSED", reason=f"диск: вільно {free:.0f} ГБ (<{MIN_FREE_GB_RUN}) — чекаю")
            raise JobStop("pause")                     # _auto_resume_paused поверне
        if engine.gpu_busy_by_other():
            upd(reason="GPU зайнятий іншим realesrgan — чекаю, не заважаю")
            waited = True
            time.sleep(15)
            continue
        if waited:
            upd(reason="GPU вільний — продовжую")
        return


def _do_segment(jid, src, s, fps, plan, model, work, upd, done_frames, total, speed_ema,
                ops):
    idx, t0, t1, n_plan = s["idx"], s["t0"], s["t1"], s["frames_plan"]
    sdir = work / f"s{idx:03d}"
    sin, sout = sdir / "in", sdir / "out"
    shutil.rmtree(sdir, ignore_errors=True)
    sin.mkdir(parents=True); sout.mkdir(parents=True)
    ts = time.time()
    # 1) кадри: -frames:v = рівно план, інакше межі -t дають ±1 кадр на сегмент і
    #    на 20 сегментах звук поїде на пів секунди. Денойз (якщо є) — тут, ПЕРЕД рушієм.
    #    (08.09 заміряно: 12 кадрів = 0.39 с проти 4.7 с на ОДИН кадр у рушія — ця фаза
    #     не вузьке місце; крутити її стиснення чи пріоритет сенсу не має.)
    cp = procs.run_low([FFMPEG, "-y", "-v", "error", *engine.ff_threads(),
                        *engine.ff_readrate(2.0),          # ≤2× реального часу, поки ефір іде
                        "-ss", f"{t0:.3f}", "-t", f"{t1 - t0 + 0.5:.3f}",
                        "-i", src, "-vf", engine.vf_chain(f"fps={fps}", engine.ops_pre_vf(ops)),
                        "-frames:v", str(n_plan), sin / "%06d.png"], timeout=1800)
    n_in = sum(1 for _ in sin.glob("*.png"))
    if cp.returncode != 0 or n_in == 0:
        raise RuntimeError(f"розкладка кадрів: {(cp.stderr or '')[-200:]}")
    # 2) рушій тека→тека + прогрес по готових файлах + сторож зависання + 🛡 ефір
    yield_on = bool(load_settings().get("yield_to_stream", True))
    naps = 0
    soft = _SOFT["on"] and yield_on
    with open(sdir / "engine.log", "w", encoding="utf-8", errors="replace") as lf:
        proc = procs.spawn(engine.engine_cmd(sin, sout, model, plan["s"],
                                             threads="1:1:1" if soft else None),
                           stdout=lf, stderr=subprocess.STDOUT)
        _PROC[jid] = proc
        engine._OWN_PIDS.add(proc.pid)
        upd(pid=proc.pid, reason=f"сегмент {idx + 1}: нейромережа" + (" (м'який режим)" if soft else ""))
        te, last_n, last_change, last_upd, last_guard = time.time(), 0, time.time(), 0.0, time.time()
        elog, last_esize = sdir / "engine.log", -1
        try:
            while proc.poll() is None:
                time.sleep(1.0)
                n = sum(1 for _ in sout.glob("*.png"))
                # 🚨 «нема нових кадрів» ≠ «завис»: другий рушій перед першим кадром може
                # хвилинами будувати движок TensorRT під цю роздільну (мовчки для теки
                # виходу, але з рядками в журналі). Тому живим вважаємо і того, хто пише в лог.
                try:
                    esize = elog.stat().st_size
                except OSError:
                    esize = last_esize
                if n != last_n or esize != last_esize:
                    last_n, last_esize, last_change = n, esize, time.time()
                elif time.time() - last_change > STALL_S:
                    proc.kill()
                    raise RuntimeError(f"рушій завис ({STALL_S} с без кадрів і без журналу)")
                if yield_on and time.time() - last_guard > YIELD_CHECK_S:
                    last_guard = time.time()
                    strain = procs.stream_strain()
                    if strain:                       # 🛡 ефір просів → рушій спить до відновлення
                        naps += 1
                        upd(reason=f"🛡 ефір просів ({strain}) — поступаюсь (№{naps})")
                        slept = procs.nap_until_recovered(proc, YIELD_NAP_S)
                        last_change = time.time()    # сон — не зависання
                        upd(reason=f"🛡 спав {slept:.0f} с, ефір відновився")
                        upd(reason=f"сегмент {idx + 1}: нейромережа (поступався ефіру ×{naps})")
                if time.time() - last_upd > 2:
                    el = max(time.time() - te, 0.1)
                    spd = n / el
                    eff = speed_ema or spd
                    eta = (total - done_frames - n) / eff if eff > 0 else 0
                    upd(frames_done=done_frames + n, speed=round(eff, 2), eta_s=round(eta))
                    last_upd = time.time()
                try:
                    _check(jid)
                except JobStop:
                    procs.suspend(proc, False)
                    proc.kill()
                    raise
        finally:
            engine._OWN_PIDS.discard(proc.pid)
    n_out = sum(1 for _ in sout.glob("*.png"))
    if proc.returncode != 0 or n_out < n_in:
        raise RuntimeError(f"рушій код {proc.returncode}, кадрів {n_out}/{n_in}")
    blank = engine.blank_output_check(sin, sout)   # кадри є, але порожні — теж провал
    if blank:
        raise RuntimeError(blank)
    spd = n_out / max(time.time() - te, 0.1)
    # 3) збірка сегмента: різкість/зерно ПІСЛЯ рушія → зведення до цілі → кодек
    upd(reason=f"сегмент {idx + 1}: кодую")
    ow, oh = engine.png_size(next(sout.glob("*.png")))
    vf = engine.vf_chain(engine.ops_post_vf(ops),
                         (engine._scale_vf(ow, oh, plan["down"]) + ":flags=lanczos")
                         if plan["down"] else "",
                         "scale=trunc(iw/2)*2:trunc(ih/2)*2")
    seg_mp4 = work / f"s{idx:03d}.mp4"
    cp = procs.run_low([FFMPEG, "-y", "-v", "error", *engine.ff_threads(6),
                        *engine.ff_readrate(1.0),          # збірка — у реальному часі, поки ефір
                        "-framerate", f"{fps}", "-i", sout / "%06d.png",
                        "-vf", vf, *engine.enc_args(ops.get("codec", "libx264")), "-an", seg_mp4],
                       timeout=3600)
    shutil.rmtree(sdir, ignore_errors=True)            # гігабайти кадрів — НЕГАЙНО
    if cp.returncode != 0 or not seg_mp4.exists():
        raise RuntimeError(f"кодування сегмента: {(cp.stderr or '')[-200:]}")
    return n_out, int((time.time() - ts) * 1000), seg_mp4, spd, naps
