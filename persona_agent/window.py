"""The local page in a window of its own instead of a browser tab.

pywebview draws it: WebView2 on Windows, where it is installed with personagent,
and whatever `personagent[app]` finds on macOS and Linux. Without it, or when no
window opens, `personagent start` falls back to the browser.
"""
from __future__ import annotations

import contextlib
import importlib.util
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


def available() -> bool:
    try:
        return importlib.util.find_spec("webview") is not None
    except (ImportError, ValueError):
        return False


def icon() -> Path:
    return ICON.with_suffix(".ico" if sys.platform == "win32" else ".png")


def alert(text: str) -> None:
    """A sentence for someone who started personagent with no terminal."""
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, text, TITLE, 0x30)


def _text_menus(window) -> None:
    """pywebview turns right-click off on Windows. Put it back where there is
    text to paste into or to copy: an API key is often pasted that way."""
    from System import Func, Type  # pythonnet, which pywebview has loaded

    form = window.native

    def on_menu(sender, args) -> None:
        target = args.ContextMenuTarget
        args.Handled = not (target.IsEditable or target.HasSelection)

    def enable() -> None:
        core = form.browser.webview.CoreWebView2
        core.Settings.AreDefaultContextMenusEnabled = True
        core.ContextMenuRequested += on_menu

    form.Invoke(Func[Type](enable))


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
    window closes, or "" to close without asking."""

    def __init__(self, url: str, *, storage: Path, confirm: Callable[[], str] = lambda: ""):
        self.url = url
        self.storage = storage
        self.confirm = confirm
        self.opened = False
        # Why no window opened, for the log.
        self.error = ""
        self._window = None
        self._leaving = False
        self._minimized = False

    def show(self) -> bool:
        """Bring the window back in front; False when there is none."""
        if not self.opened or self._leaving:
            return False
        try:
            # Only out of the taskbar: restoring a maximized window would shrink it.
            if self._minimized:
                self._window.restore()
            self._window.show()
        except Exception:
            return False
        return True

    def close(self) -> None:
        self._leaving = True
        if self._window is not None:
            with contextlib.suppress(Exception):
                self._window.destroy()

    def _closing(self):
        if self._leaving:
            return None
        question = self.confirm()
        if question and not self._window.create_confirmation_dialog(TITLE, question):
            return False
        self._leaving = True
        return None

    def _sized(self, minimized: bool) -> Callable[[], None]:
        return lambda: setattr(self, "_minimized", minimized)

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
                    with contextlib.suppress(Exception):
                        if self._window.events.loaded.wait(SHOWN_WITHIN):
                            _text_menus(self._window)
                    self._window.load_url(self.url)
                self.opened = True

        try:
            # WebView2 takes its menu setting from the next load on, so Windows
            # starts on an empty page and `ready` loads the real one after it.
            self._window = webview.create_window(
                TITLE, None if windows else self.url, width=SIZE[0], height=SIZE[1],
                min_size=MIN_SIZE, text_select=True, zoomable=True)
            events = self._window.events
            events.closing += self._closing
            events.minimized += self._sized(True)
            events.restored += self._sized(False)
            events.maximized += self._sized(False)
            with _interrupt(self.close):
                # Private: nothing the page stores outlives the window.
                webview.start(ready, gui="edgechromium" if windows else None, private_mode=True,
                              storage_path=str(self.storage), icon=str(icon()))
        except Exception as error:
            self.error = repr(error)
            return False
        return self.opened
