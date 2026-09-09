# -*- coding: utf-8 -*-
"""🛡 ПРОЦЕСИ, ЩО НЕ ЗАВАЖАЮТЬ ЖИВОМУ СТРІМУ (необовʼязковий сторож).

Для кого: хто рендерить на тому самому ПК, з якого йде ефір. Факт із практики: під
рендером сильними моделями кодер ефіру йшов 0.988x замість 1x, GPU 100%, YouTube скаржився
на «video output low». Тому за увімкненого `yield_to_stream` НАШІ процеси:
  1) стартують з BELOW_NORMAL і прибиті до P-ядер (маска в config) — не лізуть на E-ядра;
  2) якщо кодер ефіру просів — рушій ПРИСИПЛЯЄТЬСЯ (NtSuspendProcess) на кілька секунд.
Стан ефіру читаємо з файлу `ffmpeg -progress` стріму (APSK_STREAM_PROGRESS), лише читання.
Присипляємо ТІЛЬКИ власні процеси (Popen-хендл), ніколи чужі.
"""
from __future__ import annotations
import ctypes, os, re, subprocess, time
from pathlib import Path

from config import STREAM_PROGRESS, PCORE_MASK, PCORE_EXPECT_CPUS, load_settings

NO_WIN = 0x08000000
BELOW_NORMAL = 0x00004000


def throttling() -> bool:
    """Чи тиснемо СЕБЕ заради ефіру просто зараз.

    🚨 08.09: цього питання тут не було — spawn() душив КОЖЕН процес безумовно, хоча
    власник вимкнув `yield_to_stream` 28.08 («модуль зайвий, хай працює на всю»).
    Вимкнений перемикач читали лише ff_threads/ff_readrate/-j 1:1:1, а пріоритет CPU,
    маска P-ядер і I/O Low лишались назавжди — рендери йшли з гальмом, знятим у UI."""
    try:
        return bool(load_settings().get("yield_to_stream", False)) and stream_live()
    except Exception:
        return False


def spawn(cmd: list, throttle: bool | None = None, **kw) -> subprocess.Popen:
    """Popen без вікна. Поступаємось ефіру (низький пріоритет CPU, лише P-ядра, I/O Low)
    ТІЛЬКИ поки увімкнено `yield_to_stream` і ефір справді йде — інакше повна швидкість.
    I/O Low колись лікував провали кодера ефіру (0.19x) від наших дискових фаз (PNG на A:,
    звідки ефір читає музику), але коштує ~третину швидкості дискових фаз, тож вішати його
    при вимкненому сторожі — просто втрата. `throttle=` перекриває рішення (для замірів)."""
    thr = throttling() if throttle is None else bool(throttle)
    kw.setdefault("creationflags", 0)
    kw["creationflags"] |= NO_WIN | (BELOW_NORMAL if thr else 0)
    proc = subprocess.Popen([str(c) for c in cmd], **kw)
    if thr:
        pin_pcores(proc)
        set_io_low(proc)
    return proc


def set_io_low(proc: subprocess.Popen) -> None:
    """ProcessIoPriority = Low (1) через NtSetInformationProcess(…, 33, …)."""
    try:
        val = ctypes.c_ulong(1)
        ctypes.windll.ntdll.NtSetInformationProcess(ctypes.c_void_p(int(proc._handle)), 33,
                                                    ctypes.byref(val), 4)
    except Exception:
        pass


class _Done:
    def __init__(self, rc, out, err):
        self.returncode, self.stdout, self.stderr = rc, out, err


def run_low(cmd: list, timeout: int = 600) -> _Done:
    """Як media.run, але через spawn(): гальмо накидається лише коли ми справді
    поступаємось ефіру (див. throttling()), інакше — повна швидкість."""
    proc = spawn(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                 encoding="utf-8", errors="replace")
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        out, err = proc.communicate()
        return _Done(1, out or "", (err or "") + f"\nтаймаут {timeout} с")
    return _Done(proc.returncode, out or "", err or "")


def pin_pcores(proc: subprocess.Popen) -> None:
    if (os.cpu_count() or 0) != PCORE_EXPECT_CPUS:
        return                                   # інша машина — не вгадуємо ядра
    try:
        ctypes.windll.kernel32.SetProcessAffinityMask(ctypes.c_void_p(int(proc._handle)),
                                                      ctypes.c_size_t(PCORE_MASK))
    except Exception:
        pass


def suspend(proc: subprocess.Popen, on: bool) -> bool:
    try:
        fn = ctypes.windll.ntdll.NtSuspendProcess if on else ctypes.windll.ntdll.NtResumeProcess
        return fn(ctypes.c_void_p(int(proc._handle))) == 0
    except Exception:
        return False


_LAST = {"ot": None, "mt": None, "speed": None}
STRAIN_BELOW = 0.95           # миттєва швидкість кодера ефіру нижче — вважаємо, що просів
RECOVERED_AT = 0.99           # відновився — можна будити рушій
NAP_MAX_S = 40                # довше не спимо: інакше задача ніколи не дорахує
HEALTH_LOG = STREAM_PROGRESS.parent / "health_monitor.log"   # правда від YouTube, раз на 5 хв


def stream_health_bad() -> bool:
    """Наглядач A1 (YouTube health) каже «ПРОБЛЕМА» і запис свіжий (<6 хв)?"""
    try:
        st = HEALTH_LOG.stat()
        if time.time() - st.st_mtime > 360:
            return False
        with open(HEALTH_LOG, "rb") as f:
            f.seek(max(0, st.st_size - 600))
            last = f.read().decode("utf-8", "replace").strip().splitlines()[-1]
        return "ПРОБЛЕМА" in last
    except Exception:
        return False


def stream_live() -> bool:
    """Ефір A1 зараз іде? (файл прогресу кодера свіжіший за 60 с)"""
    try:
        return time.time() - STREAM_PROGRESS.stat().st_mtime < 60
    except OSError:
        return False


def stream_speed() -> float | None:
    """Останній ВІДОМИЙ миттєвий замір швидкості кодера ефіру (оновлюється stream_strain)."""
    stream_strain()
    return _LAST["speed"]


def nap_until_recovered(proc: subprocess.Popen, nap_s: int = 8) -> float:
    """Присипає СВІЙ процес, поки кодер ефіру не відновиться (≥RECOVERED_AT), але не довше
    NAP_MAX_S. Повертає, скільки спав. 28.08: провали були до 0.71x — 8 с не вистачало."""
    if not suspend(proc, True):
        return 0.0
    t0 = time.time()
    try:
        time.sleep(nap_s)
        while time.time() - t0 < NAP_MAX_S:
            sp = stream_speed()
            if sp is not None and sp >= RECOVERED_AT:
                break
            time.sleep(5)
    finally:
        suspend(proc, False)
    return time.time() - t0


def stream_strain() -> str | None:
    """Кодер ефіру просів? Читаємо хвіст ffmpeg_progress.txt ефіру A1 (лише читання).
    🚨 `speed=`/`fps=` у -progress — НАКОПИЧЕНІ середні з моменту старту кодера (після
    ранкового просідання середнє годинами <1 — сторож даремно присипляв би рушій, як і
    сталось 28.08 10:57). Тому міряємо МИТТЄВУ швидкість: Δout_time між двома блоками
    прогресу / Δ часу запису файлу. None = ефір не йде або все добре; рядок = чому просів."""
    try:
        st = STREAM_PROGRESS.stat()
    except OSError:
        return None
    if time.time() - st.st_mtime > 60:
        _LAST.update(ot=None, mt=None)
        return None                                    # ефір не пише → не йде
    try:
        with open(STREAM_PROGRESS, "rb") as f:
            f.seek(max(0, st.st_size - 4000))
            tail = f.read().decode("utf-8", "replace")
    except OSError:
        return None
    ots = re.findall(r"out_time_us=(\d+)", tail)
    if not ots:
        return None
    ot, mt = int(ots[-1]) / 1e6, st.st_mtime
    prev_ot, prev_mt = _LAST["ot"], _LAST["mt"]
    _LAST.update(ot=ot, mt=mt)
    if prev_ot is None or mt <= prev_mt or ot < prev_ot:
        return None                                    # перший замір або кодер перезапустився
    dt = mt - prev_mt
    if dt < 4:
        _LAST.update(ot=prev_ot, mt=prev_mt)           # той самий блок — лишаємо попередню базу
        return None
    inst = (ot - prev_ot) / dt
    _LAST["speed"] = inst
    if inst < STRAIN_BELOW:
        return f"кодер ефіру {inst:.3f}x (миттєво)"
    if inst < 0.985 and stream_health_bad():
        return f"YouTube health «ПРОБЛЕМА», кодер {inst:.3f}x"
    return None
