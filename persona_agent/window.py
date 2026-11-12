"""The local page in a window of its own instead of a browser tab.

pywebview draws it: WebView2 on Windows, where it is installed with personagent,
and whatever `personagent[app]` finds on macOS and Linux. Without it, or when no
window opens, `personagent start` falls back to the browser.
"""
from __future__ import annotations

import contextlib
import hmac
import importlib.util
import secrets
import signal
import socket
import sys
import threading
from pathlib import Path
from typing import Callable, Iterator

TITLE = "personagent"
ICON = Path(__file__).with_name("static") / "app"
# Windows files taskbar buttons under this, not under Python.
APP_ID = "wangkant.personagent"
SIZE = (1200, 820)
MIN_SIZE = (400, 560)
# How long the window has to appear before it counts as not opening.
SHOWN_WITHIN = 30
# How long the page has to ask for its title bar before the window takes its own back.
PAGE_WITHIN = 25
# What the page's own title bar may ask of a frameless window.
ACTIONS = ("minimize", "maximize", "restore", "close")


def available() -> bool:
    try:
        return importlib.util.find_spec("webview") is not None
    except (ImportError, ValueError):
        return False


def _toolkit() -> str | None:
    """Which toolkit draws the window; None lets pywebview choose."""
    if sys.platform == "win32":
        return "edgechromium"
    # pywebview tries GTK first and prints a traceback when it is absent,
    # which it is where the app extra installed Qt.
    with contextlib.suppress(ImportError, ValueError):
        if (sys.platform.startswith("linux") and importlib.util.find_spec("gi") is None
                and importlib.util.find_spec("qtpy") is not None):
            return "qt"
    return None


def icon() -> Path:
    return ICON.with_suffix(".ico" if sys.platform == "win32" else ".png")


def alert(text: str) -> None:
    """A sentence for someone who started personagent with no terminal."""
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, text, TITLE, 0x30)


def _text_menus(window) -> bool:
    """pywebview turns right-click off on Windows. Put it back where there is
    text to paste into or to copy: an API key is often pasted that way.
    Also lets the page mark part of itself as the bar the window is moved by;
    True when this WebView2 can do that."""
    from System import Func, Type  # pythonnet, which pywebview has loaded

    form = window.native
    found = {"regions": False}

    def on_menu(sender, args) -> None:
        target = args.ContextMenuTarget
        args.Handled = not (target.IsEditable or target.HasSelection)

    def enable() -> None:
        core = form.browser.webview.CoreWebView2
        core.Settings.AreDefaultContextMenusEnabled = True
        core.ContextMenuRequested += on_menu
        # `app-region: drag` in the page; an older runtime has no such setting.
        with contextlib.suppress(Exception):
            core.Settings.IsNonClientRegionSupportEnabled = True
            found["regions"] = bool(core.Settings.IsNonClientRegionSupportEnabled)

    form.Invoke(Func[Type](enable))
    return found["regions"]


# Window messages and metrics the frameless window handles (winuser.h).
_WM_NCDESTROY, _WM_NCCALCSIZE = 0x0082, 0x0083
_SM_CYSIZEFRAME, _SM_CXPADDEDBORDER = 33, 92
# shellapi.h: is there a taskbar that hides itself at this edge of this screen,
# and how far a maximized page stays from it.
_ABM_GETAUTOHIDEBAREX = 0x0000000B
_HIDDEN_TASKBAR_GAP = 2
# SetWindowPos: keep place, size and order, and work the frame out again.
_FRAME_CHANGED = 0x0001 | 0x0002 | 0x0004 | 0x0010 | 0x0020


def _strip_title_bar(window):
    """Take the title bar off a Windows window and leave everything else the
    system gives one: the resize borders at the sides and the bottom, the
    shadow, snapping and the taskbar entry. The page draws its own bar.

    Returns what must stay referenced while the window lives, or None when
    the title bar is still there."""
    import ctypes
    from ctypes import wintypes

    from System import Func, Type

    form = window.native
    # Libraries of our own: pywebview calls the shared ones with other argument types.
    user32, comctl32, shell32 = ctypes.WinDLL("user32"), ctypes.WinDLL("comctl32"), ctypes.WinDLL("shell32")
    result_t = ctypes.c_ssize_t
    proc_t = ctypes.WINFUNCTYPE(result_t, wintypes.HWND, wintypes.UINT, wintypes.WPARAM,
                                wintypes.LPARAM, ctypes.c_size_t, ctypes.c_size_t)

    class MonitorInfo(ctypes.Structure):
        _fields_ = [("size", wintypes.DWORD), ("monitor", wintypes.RECT), ("work", wintypes.RECT),
                    ("flags", wintypes.DWORD)]

    class AppBar(ctypes.Structure):
        _fields_ = [("size", wintypes.DWORD), ("hwnd", wintypes.HWND), ("message", wintypes.UINT),
                    ("edge", wintypes.UINT), ("rect", wintypes.RECT), ("lparam", wintypes.LPARAM)]

    comctl32.DefSubclassProc.restype = result_t
    comctl32.DefSubclassProc.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    comctl32.SetWindowSubclass.restype = wintypes.BOOL
    comctl32.SetWindowSubclass.argtypes = [wintypes.HWND, proc_t, ctypes.c_size_t, ctypes.c_size_t]
    comctl32.RemoveWindowSubclass.argtypes = [wintypes.HWND, proc_t, ctypes.c_size_t]
    user32.IsZoomed.argtypes = [wintypes.HWND]
    user32.GetDpiForWindow.argtypes = [wintypes.HWND]
    user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
                                    ctypes.c_int, ctypes.c_int, wintypes.UINT]
    user32.MonitorFromWindow.restype = wintypes.HANDLE
    user32.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
    user32.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MonitorInfo)]
    shell32.SHAppBarMessage.restype = ctypes.c_size_t
    shell32.SHAppBarMessage.argtypes = [wintypes.DWORD, ctypes.POINTER(AppBar)]

    def frame_height(hwnd) -> int:
        dpi = user32.GetDpiForWindow(hwnd) or 96
        return (user32.GetSystemMetricsForDpi(_SM_CYSIZEFRAME, dpi)
                + user32.GetSystemMetricsForDpi(_SM_CXPADDEDBORDER, dpi))

    def leave_hidden_taskbar(hwnd, rect) -> None:
        """A page that covers the whole screen counts as full screen, and a
        taskbar set to hide itself would never come back: stop short of its edge."""
        info = MonitorInfo()
        info.size = ctypes.sizeof(MonitorInfo)
        if not user32.GetMonitorInfoW(user32.MonitorFromWindow(hwnd, 2), ctypes.byref(info)):
            return
        for edge, side, step in ((0, "left", 1), (1, "top", 1), (2, "right", -1), (3, "bottom", -1)):
            bar = AppBar()
            bar.size, bar.edge, bar.rect = ctypes.sizeof(AppBar), edge, info.monitor
            if shell32.SHAppBarMessage(_ABM_GETAUTOHIDEBAREX, ctypes.byref(bar)):
                setattr(rect, side, getattr(rect, side) + step * _HIDDEN_TASKBAR_GAP)

    def proc(hwnd, message, wparam, lparam, _subclass, _data):
        if message == _WM_NCCALCSIZE and wparam:
            # The system works out the sides and the bottom; the top stays where
            # the window begins, so there is no title bar. A maximized window
            # reaches past the screen by its frame, and the top comes back in.
            rect = ctypes.cast(ctypes.c_void_p(lparam), ctypes.POINTER(wintypes.RECT))
            top = rect[0].top
            result = comctl32.DefSubclassProc(hwnd, message, wparam, lparam)
            if result == 0:
                with contextlib.suppress(Exception):
                    zoomed = bool(user32.IsZoomed(hwnd))
                    rect[0].top = top + (frame_height(hwnd) if zoomed else 0)
                    if zoomed:
                        leave_hidden_taskbar(hwnd, rect[0])
            return result
        if message == _WM_NCDESTROY:
            comctl32.RemoveWindowSubclass(hwnd, callback, 1)
        return comctl32.DefSubclassProc(hwnd, message, wparam, lparam)

    callback = proc_t(proc)
    done = {"ok": False}

    def install() -> None:
        hwnd = form.Handle.ToInt64()
        if comctl32.SetWindowSubclass(hwnd, callback, 1, 0):
            user32.SetWindowPos(hwnd, None, 0, 0, 0, 0, _FRAME_CHANGED)
            done["ok"] = True

    def undo() -> None:
        """Give the window its title bar back."""
        def remove() -> None:
            hwnd = form.Handle.ToInt64()
            comctl32.RemoveWindowSubclass(hwnd, callback, 1)
            user32.SetWindowPos(hwnd, None, 0, 0, 0, 0, _FRAME_CHANGED)
        form.Invoke(Func[Type](remove))

    # Called from the window's own thread before it shows, so no title bar is ever drawn.
    install()
    return (callback, undo) if done["ok"] else None


@contextlib.contextmanager
def _interrupt(stop: Callable[[], None]) -> Iterator[None]:
    """Ctrl+C calls `stop` at once. The main thread sits in the window's own
    loop, where a Python signal handler would wait for it to come back."""
    if threading.current_thread() is not threading.main_thread():
        yield
        return
    reader, writer = socket.socketpair()
    writer.setblocking(False)

    def wait() -> None:
        with contextlib.suppress(OSError):
            if reader.recv(1):
                stop()

    handler = signal.signal(signal.SIGINT, lambda *_: None)
    wakeup = signal.set_wakeup_fd(writer.fileno(), warn_on_full_buffer=False)
    threading.Thread(target=wait, name="personagent-interrupt", daemon=True).start()
    try:
        yield
    finally:
        signal.set_wakeup_fd(wakeup)
        signal.signal(signal.SIGINT, handler)
        writer.close()
        reader.close()


class AppWindow:
    """One window on `url`. `confirm` returns the question to ask before the
    window closes, or "" to close without asking. While `background` says so,
    closing hides the window behind a notification-area icon instead, where
    the system has one for us (Windows); `words` names that icon's menu."""

    def __init__(self, url: str, *, storage: Path, confirm: Callable[[], str] = lambda: "",
                 background: Callable[[], bool] = lambda: False,
                 words: Callable[[], dict] = lambda: {}, start_hidden: bool = False):
        self.url = url
        self.storage = storage
        self.confirm = confirm
        self.background = background
        self.words = words
        self.start_hidden = start_hidden
        self.opened = False
        # Why no window opened, for the log.
        self.error = ""
        self.hidden = False
        self._window = None
        self._leaving = False
        self._tray = None
        self._told = False
        # A window started for the background is created minimized.
        self._minimized = start_hidden
        #: The window has no title bar of its own: the page draws the bar and its buttons.
        self.frameless = False
        self.maximized = False
        # The frameless window's message handler and how to undo it; .NET holds no reference.
        self._frame = None
        self._frame_seen = threading.Event()
        # Only the page inside this window knows it: a browser tab on the same
        # address neither draws the window's bar nor presses its buttons.
        self.frame_key = secrets.token_urlsafe(16)

    @property
    def can_hide(self) -> bool:
        """Closing can leave personagent running behind an icon."""
        return self._tray is not None

    def show(self) -> bool:
        """Bring the window back in front; False when there is none."""
        if not self.opened or self._leaving:
            return False
        try:
            # Only out of the taskbar: restoring a maximized window would shrink it.
            if self._minimized:
                self._window.restore()
            self._window.show()
            if self.hidden:
                self.hidden = False
                self._on_ui(lambda: setattr(self._tray, "Visible", False))
        except Exception:
            return False
        return True

    def hide(self) -> bool:
        """Leave the window for the notification area; False when it cannot."""
        if self._tray is None or not self.opened or self._leaving:
            return False
        words = {"still": "", **self.words()}

        def away() -> None:
            self._tray.Visible = True
            if not self._told and words["still"]:
                self._told = True
                self._tray.ShowBalloonTip(5000, TITLE, words["still"], self._tray_info)

        try:
            self._window.hide()
            self.hidden = True
            self._on_ui(away)
        except Exception:
            return False
        return True

    def close(self) -> None:
        self._leaving = True
        if self._window is not None:
            with contextlib.suppress(Exception):
                self._window.destroy()

    def _on_ui(self, action: Callable[[], None]) -> None:
        from System import Func, Type

        def run() -> None:
            action()

        self._window.native.Invoke(Func[Type](run))

    def _make_tray(self) -> None:
        """The icon a hidden window is reached through. Its handlers stay
        referenced here, or .NET would lose them."""
        from System.Drawing import Icon
        from System.Windows.Forms import ContextMenuStrip, NotifyIcon, ToolStripMenuItem, ToolTipIcon

        words = {"open": "Open personagent", "quit": "Quit", **self.words()}
        self._tray_info = ToolTipIcon.Info
        self._tray_open = lambda sender, event: self.show()
        self._tray_quit = lambda sender, event: self.close()

        def make() -> None:
            tray = NotifyIcon()
            tray.Icon = Icon(str(icon()))
            tray.Text = TITLE
            menu = ContextMenuStrip()
            for label, handler in ((words["open"], self._tray_open), (words["quit"], self._tray_quit)):
                item = ToolStripMenuItem(label)
                item.Click += handler
                menu.Items.Add(item)
            tray.ContextMenuStrip = menu
            tray.DoubleClick += self._tray_open
            tray.Visible = False
            self._tray = tray

        self._on_ui(make)

    def _closing(self):
        if self._leaving:
            return None
        if self._tray is not None and self.background():
            self.hide()
            return False
        question = self.confirm()
        if question and not self._window.create_confirmation_dialog(TITLE, question):
            return False
        self._leaving = True
        return None

    def _sized(self, minimized: bool, maximized: bool | None = None) -> Callable[[], None]:
        def note() -> None:
            self._minimized = minimized
            if maximized is not None:
                self.maximized = maximized
        return note

    def control(self, action: str) -> bool:
        """What the page's own title bar asks for: one of ACTIONS. False when
        there is no window to do it to."""
        if not self.opened or self._leaving or action not in ACTIONS:
            return False
        try:
            if action == "minimize":
                self._window.minimize()
            elif action == "maximize":
                self._window.maximize()
            elif action == "restore":
                self._window.restore()
            else:
                # As the system's close button: it may hide the window or ask first,
                # so the page is not kept waiting for the answer.
                threading.Thread(target=self._window.destroy, name="personagent-close", daemon=True).start()
        except Exception:
            return False
        return True

    def _before_show(self) -> None:
        with contextlib.suppress(Exception):
            self._frame = _strip_title_bar(self._window)
            self.frameless = self._frame is not None

    @property
    def page_url(self) -> str:
        """The address this window loads: `url` and the key its page shows for the bar."""
        return f"{self.url}{'&' if '#' in self.url else '#'}frame={self.frame_key}"

    def is_own_page(self, key: str) -> bool:
        return hmac.compare_digest(str(key or ""), self.frame_key)

    def frame_seen(self) -> None:
        """The page asked how the window stands, so it draws the bar and the buttons."""
        self._frame_seen.set()

    def _framed_again(self) -> None:
        """The window gets its own title bar back."""
        if self.frameless:
            self.frameless = False
            with contextlib.suppress(Exception):
                self._frame[1]()

    def _unless_seen(self) -> None:
        # A page that never came up draws no buttons: nobody is left with a
        # window that cannot be closed.
        if not self._frame_seen.wait(PAGE_WITHIN) and not self._leaving:
            self._framed_again()

    def run(self) -> bool:
        """Show the window and block until it closes. False when none opened."""
        try:
            import webview
        except Exception as error:
            self.error = repr(error)
            return False
        windows = sys.platform == "win32"
        if windows:
            import ctypes
            with contextlib.suppress(Exception):
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)

        def ready() -> None:
            if not self._window.events.shown.wait(SHOWN_WITHIN):
                self.error = "the window did not appear"
                self.close()
            elif self._leaving:
                # Asked to close before there was a window to close.
                self.close()
            # Without WebView2, Windows offers an engine too old for the page.
            elif windows and webview.renderer != "edgechromium":
                self.error = "the WebView2 runtime is missing"
                self.close()
            else:
                if windows:
                    regions = False
                    with contextlib.suppress(Exception):
                        if self._window.events.loaded.wait(SHOWN_WITHIN):
                            regions = _text_menus(self._window)
                    if not regions:
                        # The page could not be the bar the window is moved by.
                        self._framed_again()
                    with contextlib.suppress(Exception):
                        self._make_tray()
                    self._window.load_url(self.page_url)
                    if self.frameless:
                        threading.Thread(target=self._unless_seen, name="personagent-frame",
                                         daemon=True).start()
                self.opened = True
                if self.start_hidden:
                    self.hide()

        try:
            # WebView2 takes its menu setting from the next load on, so Windows
            # starts on an empty page and `ready` loads the real one after it.
            self._window = webview.create_window(
                TITLE, None if windows else self.page_url, width=SIZE[0], height=SIZE[1],
                min_size=MIN_SIZE, text_select=True, zoomable=True,
                # Started for the background: no window flashes up before it hides.
                minimized=self.start_hidden and windows)
            events = self._window.events
            events.closing += self._closing
            events.minimized += self._sized(True)
            events.restored += self._sized(False, False)
            events.maximized += self._sized(False, True)
            if windows:
                events.before_show += self._before_show
            with _interrupt(self.close):
                # Private: nothing the page stores outlives the window.
                webview.start(ready, gui=_toolkit(), private_mode=True,
                              storage_path=str(self.storage), icon=str(icon()))
        except Exception as error:
            self.error = repr(error)
            return False
        finally:
            if not self.opened:
                # No window after all: the browser that takes over draws no window bar.
                self.frameless = False
            if self._tray is not None:
                with contextlib.suppress(Exception):
                    self._tray.Visible = False
                    self._tray.Dispose()
        return self.opened
