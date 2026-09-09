# -*- coding: utf-8 -*-
"""💎 АПСКЕЙЛ — вікно (pywebview над WebView2).

Порядок: якщо НАШ сервер уже живий (/api/whoami каже apskeyl) — просто відкриваємо вікно.
Інакше стартуємо server.py ОКРЕМИМ відʼєднаним процесом (DETACHED) і чекаємо готовності.
Закриття вікна сервер не вбиває — він сам гасне за 30 хв простою.

js_api: нативний діалог вибору файлів — ЄДИНИЙ гарантований спосіб отримати реальний
шлях із WebView2 (drag&drop там може віддати File без шляху).
"""
from __future__ import annotations
import subprocess, sys, time, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config

# під pythonw stdout/stderr = None → будь-який print валить процес; пишемо у файл.
# Тека даних може бути ще не обрана або диск не змонтований — тоді лог у %TEMP%.
if sys.stdout is None or sys.stderr is None:
    import os as _os
    try:
        config.LOGS.mkdir(parents=True, exist_ok=True)
        _logdir = config.LOGS
    except OSError:
        _logdir = Path(_os.getenv("TEMP", ".")) / "apskeyl"
        _logdir.mkdir(parents=True, exist_ok=True)
    _f = open(_logdir / "desktop.log", "a", buffering=1, encoding="utf-8",
              errors="replace")
    sys.stdout = sys.stderr = _f

URL = f"http://127.0.0.1:{config.PORT}"
DETACHED = 0x00000008 | 0x00000200 | 0x08000000   # DETACHED | NEW_PROCESS_GROUP | NO_WINDOW


def ours_alive() -> bool:
    try:
        with urllib.request.urlopen(f"{URL}/api/whoami", timeout=1.5) as r:
            return b'"apskeyl"' in r.read()
    except Exception:
        return False


def start_server() -> None:
    pyw = config.ROOT / ".venv" / "Scripts" / "pythonw.exe"
    subprocess.Popen([str(pyw), str(config.ROOT / "app" / "server.py")],
                     cwd=str(config.ROOT), creationflags=DETACHED,
                     close_fds=True)


class Api:
    """Місток для фронта: window.pywebview.api.*"""

    def pick_files(self):
        import webview
        res = webview.windows[0].create_file_dialog(
            webview.OPEN_DIALOG, allow_multiple=True,
            file_types=("Відео (*.mp4;*.mkv;*.mov;*.avi;*.webm;*.ts;*.m4v;*.wmv)",
                        "Усі файли (*.*)"))
        return list(res or [])

    def show_in_folder(self, path: str):
        subprocess.Popen(["explorer", "/select,", path])

    def pick_folder(self):
        import webview
        res = webview.windows[0].create_file_dialog(webview.FOLDER_DIALOG)
        return list(res)[0] if res else ""            # скасував діалог → None → порожньо

    # 🚨 ПРАВИЛО (28.08, двічі «Python is not responding»): з методів js_api НЕ чіпати
    # WinForms-обʼєкти напряму (form.WindowState тощо) — вони живуть у UI-потоці, а API
    # виконується в іншому → дедлок. Лише методи pywebview Window.* — вони самі роблять
    # Invoke у UI-потік: minimize/restore/resize/move/destroy.
    _saved_geom = None

    # Геометрія — ТІЛЬКИ через Win32 у ФІЗИЧНИХ пікселях (GetWindowRect/SetWindowPos):
    # pywebview читає x/width з урахуванням DPI-масштабу, а move/resize приймає інші
    # одиниці — на екрані з масштабуванням вікно росло «за межі монітора» (власник 28.08).
    # SetWindowPos з чужого потоку — законний Win32-виклик, Python на UI-потоці не потрібен.
    @staticmethod
    def _hwnd():
        import webview
        return int(webview.windows[0].native.Handle.ToInt64())

    @staticmethod
    def _rect():
        import ctypes
        from ctypes import wintypes
        r = wintypes.RECT()
        ctypes.windll.user32.GetWindowRect(Api._hwnd(), ctypes.byref(r))
        return {"x": r.left, "y": r.top, "w": r.right - r.left, "h": r.bottom - r.top}

    @staticmethod
    def _place(x, y, w, h):
        import ctypes
        ctypes.windll.user32.SetWindowPos(Api._hwnd(), 0, int(x), int(y), int(w), int(h),
                                          0x0004 | 0x0010 | 0x0040)   # NOZORDER|NOACTIVATE|SHOWWINDOW

    def win_min(self):
        import webview
        webview.windows[0].minimize()

    def win_geom(self):
        return Api._rect()

    def win_max(self):
        """«На весь екран» = робоча область (без таскбара) і назад. Без WinForms Maximized:
        безрамкове вікно накривало б таскбар, а стан читати з чужого потоку не можна."""
        import ctypes
        from ctypes import wintypes
        if Api._saved_geom:
            g = Api._saved_geom; Api._saved_geom = None
            Api._place(g["x"], g["y"], g["w"], g["h"])
            return False
        Api._saved_geom = Api._rect()
        r = wintypes.RECT()
        ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(r), 0)   # SPI_GETWORKAREA
        Api._place(r.left, r.top, r.right - r.left, r.bottom - r.top)
        return True

    def win_set(self, x, y, wd, ht):
        """Пряме задання геометрії (фізичні пікселі) — лишено для скриптів/тестів."""
        import ctypes
        dpi = ctypes.windll.user32.GetDpiForWindow(Api._hwnd()) or 96
        min_w, min_h = int(1040 * dpi / 96), int(680 * dpi / 96)
        wd, ht = max(min_w, int(wd)), max(min_h, int(ht))
        Api._place(x, y, wd, ht)
        Api._saved_geom = None
        return Api._rect()

    _HT = {"w": 10, "e": 11, "n": 12, "nw": 13, "ne": 14, "s": 15, "sw": 16, "se": 17}

    def win_size_drag(self, edge: str):
        """НАТИВНЕ розтягування: як звичайне вікно Windows. Сторінка каже, за який край
        натиснуто, ми віддаємо Windows WM_NCLBUTTONDOWN з кодом краю — далі модальний цикл
        розміру веде сама система (правильний курсор, реальна миша, без DPI-математики).
        Так само робить pywebview для перетягування (HTCAPTION). Потрібен WS_THICKFRAME —
        див. _enable_native_resize()."""
        import ctypes
        ht = Api._HT.get(edge)
        if not ht:
            return False
        u32 = ctypes.windll.user32
        u32.ReleaseCapture()
        u32.PostMessageW(Api._hwnd(), 0x00A1, ht, 0)          # WM_NCLBUTTONDOWN
        Api._saved_geom = None
        return True

    def win_close(self):
        import webview
        webview.windows[0].destroy()


# 🚨 ІСТОРІЯ 28.08 (двічі «Python is not responding»): версії розтягування через сабклас
# WndProc із Python-колбеком і через BeginInvoke(FormBorderStyle=Sizable) ВІШАЛИ вікно —
# Python-код на UI-потоці потребує GIL, а API-потік (діалог «Обрати…», win_max) тримав GIL
# і чекав UI → дедлок. Тепер: жодного Python на UI-потоці. Значок — через
# webview.start(icon=…) (pywebview ставить Form.Icon сам при створенні) + WM_SETICON ззовні;
# розтягування — зі сторінки через безпечні Window.move/resize (див. Api.win_set).


def _enable_native_resize():
    """WS_THICKFRAME для безрамкового вікна — щоб DefWindowProc виконував цикл зміни розміру
    (WM_NCLBUTTONDOWN + HT*). Лише Win32-виклики з нашого потоку, без Python на UI-потоці."""
    try:
        import ctypes
        hwnd = Api._hwnd()
        u32 = ctypes.windll.user32
        GWL_STYLE = -16
        style = u32.GetWindowLongPtrW(hwnd, GWL_STYLE)
        u32.SetWindowLongPtrW(hwnd, GWL_STYLE, style | 0x00040000)          # WS_THICKFRAME
        u32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0020 | 0x0002 | 0x0001 | 0x0004)   # FRAMECHANGED
    except Exception as e:
        print("native resize:", str(e)[:120], flush=True)


def _set_taskbar_icon():
    """WM_SETICON через ctypes — це SendMessage з іншого потоку, без Python на UI-потоці."""
    ico = str(config.ROOT / "tools" / "apskeyl.ico")
    try:
        import ctypes, webview
        hwnd = int(webview.windows[0].native.Handle.ToInt64())
        u32 = ctypes.windll.user32
        h = u32.LoadImageW(None, ico, 1, 0, 0, 0x10 | 0x40)      # IMAGE_ICON, LOADFROMFILE|DEFAULTSIZE
        if h:
            u32.SendMessageW(hwnd, 0x80, 0, h)                     # WM_SETICON small
            u32.SendMessageW(hwnd, 0x80, 1, h)                     # WM_SETICON big
    except Exception as e:
        print("значок:", str(e)[:120], flush=True)


def _pick_data_dir() -> str:
    """Майстер першого запуску: де тримати дані. Tkinter — бо він у стандартній бібліотеці
    й не потребує вікна WebView2, якого ще нема."""
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox
    except Exception:
        return ""
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    messagebox.showinfo(
        "💎 Апскейл — перший запуск",
        "Обери теку для даних програми: превʼю, результати і тимчасові кадри.\n\n"
        "Під час рендера в 4K тимчасові кадри займають ДЕСЯТКИ гігабайт — "
        "обирай великий диск, не системний.\n\nЗмінити можна пізніше у файлі apskeyl.json "
        "поруч із програмою.", parent=root)
    d = filedialog.askdirectory(title="Тека даних Апскейлу", parent=root)
    root.destroy()
    return d or ""


def main():
    import ctypes
    global config
    # перший запуск: тека даних ще не обрана → майстер; скасував → просто виходимо
    if not config.data_configured():
        d = _pick_data_dir()
        if not d:
            return
        config.save_data_dir(d)
        import importlib
        config = importlib.reload(config)
    # тека даних доступна? (знімний/мережевий диск після ребута буває не змонтований)
    try:
        config.DATA.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        ctypes.windll.user32.MessageBoxW(
            None, f"Тека даних недоступна: {config.DATA}\n({e})\n\nПідключи диск або зміни "
            f"data_dir у {config.CONFIG_FILE} (видали файл — майстер спитає знову).",
            "💎 Апскейл", 0x10)
        return
    # одне вікно за раз: подвійний клік по ярлику не має плодити копії
    ctypes.windll.kernel32.CreateMutexW(None, False, "Global\\apskeyl_window")
    if ctypes.windll.kernel32.GetLastError() == 183:      # ERROR_ALREADY_EXISTS
        return
    # власний AppUserModelID: панель задач не групує нас із іншими python-вікнами і бере
    # НАШ значок, а не значок pythonw.exe
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Apskeyl.App")
    except Exception:
        pass
    import webview
    if not ours_alive():
        start_server()
        for _ in range(60):
            if ours_alive():
                break
            time.sleep(0.25)
        else:
            import ctypes
            ctypes.windll.user32.MessageBoxW(
                None, "Двигун не відповів на порту "
                f"{config.PORT}.\nПеревір: {config.ROOT}\\app\\server.py "
                "(запусти руками з .venv — побачиш помилку).", "💎 Апскейл", 0x10)
            return
    # автоплей у WebView2 суворіший за Edge: без цього прапорця кліп порівняння міг
    # стояти статикою (скарга 28.08)
    import os
    os.environ.setdefault("WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS",
                          "--autoplay-policy=no-user-gesture-required")
    w = webview.create_window("Апскейл", URL, js_api=Api(),
                              width=1280, height=880, min_size=(1040, 680),
                              background_color="#14161a", frameless=True, easy_drag=False)
    w.events.loaded += _set_taskbar_icon        # _enable_native_resize — не вмикаємо (JS-варіант працює)
    webview.start(private_mode=False, icon=str(config.ROOT / "tools" / "apskeyl.ico"))


if __name__ == "__main__":
    main()
