"""Drive the local page inside the real app window, to check that what is on it works.

Windows only: it needs the WebView2 window `personagent start` opens there.

    import sys, pathlib
    sys.path.insert(0, r"<checkout>/tools")
    from window_driver import run

    def steps(d):
        d.configure()                      # a stand-in model, through the page itself
        d.click(".nav[data-view=app]")
        d.check("the App view opens", "app-view" in d.views())

    raise SystemExit(run(pathlib.Path(r"D:/scratch/home"), steps, out=pathlib.Path(r"D:/scratch/out")))

`home` must be a scratch folder, never a home someone uses: the page starts
whatever that home has connected. Clicks and keys go through the browser
engine's own input, so hover, focus and pressed states are the real ones. The
window opens off screen unless `offscreen=False`. Links that would open the
system browser are recorded in `d.links` instead.
"""
from __future__ import annotations

import ctypes
import json
import os
import sys
import threading
import time
import webbrowser
from http.server import ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from package_smoke import FakeModel  # noqa: E402

BUSY = "<<page is busy>>"
VIEWS = ("[...document.querySelectorAll('section')].filter(s => !s.hidden && s.getClientRects().length)"
         ".map(s => s.id)")


class Model(FakeModel):
    """The stand-in model. `fail_until` (a time) makes chat requests fail until then;
    `delay` is how long an answer takes, so a waiting state can be seen."""
    fail_until = 0.0
    delay = 0.6

    def do_POST(self) -> None:
        if time.time() < Model.fail_until and "chat/completions" in self.path:
            self.rfile.read(int(self.headers.get("Content-Length") or 0))
            self.send_response(500)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        time.sleep(Model.delay)
        super().do_POST()


class Driver:
    def __init__(self, home: Path, out: Path, model_url: str) -> None:
        self.home, self.out, self.model_url = home, out, model_url
        self.links: list[str] = []
        self.passed = self.failed = 0
        self.app = None
        self._lines: list[str] = []
        self._shots = 0
        self._core = None

    # -- reporting ----------------------------------------------------------
    def log(self, text: str) -> None:
        self._lines.append(text)
        (self.out / "walk.log").write_text("\n".join(self._lines), encoding="utf-8")

    def check(self, name: str, ok, detail="") -> bool:
        """One thing a control must have done. `detail` is what was seen."""
        if ok:
            self.passed += 1
        else:
            self.failed += 1
        shown = f"  — {json.dumps(detail, ensure_ascii=False)[:300]}" if detail != "" else ""
        self.log(f"{'PASS' if ok else 'FAIL'}  {name}{shown}")
        return bool(ok)

    # -- the engine ---------------------------------------------------------
    def _ui(self, action) -> None:
        from System import Func, Type

        def run_it():
            action()

        self.app._window.native.Invoke(Func[Type](run_it))

    def cdp(self, method: str, **params) -> None:
        """A DevTools protocol call, such as Input.dispatchMouseEvent."""
        if self._core is None:
            held = {}
            self._ui(lambda: held.update(core=self.app._window.native.browser.webview.CoreWebView2))
            self._core = held["core"]
        payload, core = json.dumps(params), self._core
        self._ui(lambda: core.CallDevToolsProtocolMethodAsync(method, payload))

    def js(self, expression: str, timeout: float = 15):
        """The value of a JavaScript expression in the page, or BUSY when the
        page does not answer in time."""
        box = {}

        def ask() -> None:
            try:
                box["value"] = self.app._window.evaluate_js(expression)
            except Exception as error:
                box["value"] = f"<<error: {error}>>"

        worker = threading.Thread(target=ask, daemon=True)
        worker.start()
        worker.join(timeout)
        return BUSY if worker.is_alive() else box.get("value")

    # -- looking ------------------------------------------------------------
    def views(self) -> list:
        return self.js(VIEWS) or []

    def shown(self, selector: str) -> bool:
        return bool(self.js("(s => { const e = document.querySelector(s); return !!e && !e.closest('[hidden]') "
                            "&& e.getClientRects().length > 0; })(%s)" % json.dumps(selector)))

    def text(self, selector: str) -> str:
        return self.js("(s => { const e = document.querySelector(s); return e ? e.textContent.trim().replace(/\\s+/g, ' ') : ''; })(%s)"
                       % json.dumps(selector)) or ""

    def toast(self) -> str:
        return self.js("document.getElementById('toast').hidden ? '' : document.getElementById('toast').textContent") or ""

    def until(self, expression: str, seconds: float = 30):
        """Wait until a JavaScript expression is truthy; its last value."""
        deadline, value = time.time() + seconds, None
        while time.time() < deadline:
            value = self.js(expression)
            if value and value != BUSY and not str(value).startswith("<<error"):
                return value
            time.sleep(0.4)
        return value

    def shot(self, name: str) -> Path:
        """A picture of the window as it is now."""
        from ctypes import wintypes

        from PIL import Image

        self._shots += 1
        user32, gdi32 = ctypes.windll.user32, ctypes.windll.gdi32
        for func in (user32.GetWindowDC, gdi32.CreateCompatibleDC, gdi32.CreateCompatibleBitmap, gdi32.SelectObject):
            func.restype = ctypes.c_void_p
        handle = ctypes.c_void_p(self.app._window.native.Handle.ToInt64())
        rect = wintypes.RECT()
        user32.GetWindowRect(handle, ctypes.byref(rect))
        width, height = rect.right - rect.left, rect.bottom - rect.top
        window_dc = ctypes.c_void_p(user32.GetWindowDC(handle))
        memory = ctypes.c_void_p(gdi32.CreateCompatibleDC(window_dc))
        bitmap = ctypes.c_void_p(gdi32.CreateCompatibleBitmap(window_dc, width, height))
        gdi32.SelectObject(memory, bitmap)
        # 2 = PW_RENDERFULLCONTENT: without it the web view comes out white.
        user32.PrintWindow(handle, memory, 2)
        header = (ctypes.c_uint32 * 10)(40, width, ctypes.c_uint32(-height).value, 1 | (32 << 16), 0, 0, 0, 0, 0, 0)
        pixels = ctypes.create_string_buffer(width * height * 4)
        gdi32.GetDIBits(memory, bitmap, 0, height, pixels, header, 0)
        path = self.out / f"{self._shots:02d}-{name}.png"
        Image.frombuffer("RGB", (width, height), pixels, "raw", "BGRX", 0, 1).save(path)
        gdi32.DeleteObject(bitmap)
        gdi32.DeleteDC(memory)
        user32.ReleaseDC(handle, window_dc)
        return path

    # -- acting -------------------------------------------------------------
    def centre(self, selector: str):
        box = self.js("(() => { const e = document.querySelector(%s); if (!e) return null; e.scrollIntoView({block: 'center'});"
                      " const r = e.getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2, r.width]; })()"
                      % json.dumps(selector))
        return (box[0], box[1]) if isinstance(box, list) and box[2] else None

    def hover(self, selector: str) -> bool:
        at = self.centre(selector)
        if at:
            self.cdp("Input.dispatchMouseEvent", type="mouseMoved", x=at[0], y=at[1])
            time.sleep(0.3)
        return bool(at)

    def click(self, selector: str) -> bool:
        """A real click on the element; False (and a log line) when it is not on screen."""
        at = self.centre(selector)
        if not at:
            self.log(f"      (nothing on screen to click at {selector})")
            return False
        self.cdp("Input.dispatchMouseEvent", type="mouseMoved", x=at[0], y=at[1])
        time.sleep(0.12)
        for kind in ("mousePressed", "mouseReleased"):
            self.cdp("Input.dispatchMouseEvent", type=kind, x=at[0], y=at[1], button="left", buttons=1, clickCount=1)
            time.sleep(0.07)
        time.sleep(0.3)
        return True

    def type_into(self, selector: str, text: str) -> None:
        """Replace what an input holds by typing."""
        self.click(selector)
        self.js("(e => e.select && e.select())(document.querySelector(%s))" % json.dumps(selector))
        self.cdp("Input.insertText", text=text)
        time.sleep(0.2)

    def key(self, name: str, code: int) -> None:
        """Press a key: key("Enter", 13), key("Escape", 27), key("Tab", 9)."""
        for kind in ("keyDown", "keyUp"):
            self.cdp("Input.dispatchKeyEvent", type=kind, key=name, code=name, windowsVirtualKeyCode=code)
            time.sleep(0.05)

    def choose(self, selector: str, value: str) -> None:
        """Pick an option of a <select>: its native list cannot be clicked from here."""
        self.js("(() => { const p = document.querySelector(%s); p.value = %s; p.dispatchEvent(new Event('change', {bubbles: true})); })()"
                % (json.dumps(selector), json.dumps(value)))
        time.sleep(0.4)

    def configure(self) -> bool:
        """First run: point the page at the stand-in model and wait for the chat."""
        self.click(".nav[data-view=settings]")
        self.choose("#provider", "other")
        self.type_into("#base-url", self.model_url)
        self.type_into("#model", "fake-model")
        self.type_into("#api-key", "fake-local-key")
        self.click("#save")
        ready = self.until("(%s).includes('chat-view')" % VIEWS, 60)
        time.sleep(2.5)
        return bool(ready)


def run(home: Path, steps, *, out: Path | None = None, offscreen: bool = True, lang: str = "") -> int:
    """Open the page on the scratch `home`, call `steps(driver)` once the
    window is up, close it. Returns the number of failed checks."""
    if sys.platform != "win32":
        raise SystemExit("window_driver needs the Windows app window")
    home = Path(home).resolve()
    out = Path(out or home / "walk")
    out.mkdir(parents=True, exist_ok=True)
    os.environ["AGENT_HOME"] = str(home)
    os.environ.pop("AGENT_LANG", None)
    if lang:
        os.environ["AGENT_LANG"] = lang

    model = ThreadingHTTPServer(("127.0.0.1", 0), Model)
    threading.Thread(target=model.serve_forever, daemon=True).start()
    driver = Driver(home, out, f"http://127.0.0.1:{model.server_address[1]}/v1")
    webbrowser.open = lambda url, *a, **k: driver.links.append(str(url)) or True

    import webview

    from persona_agent import welcome
    from persona_agent import window as appwindow

    if offscreen:
        create = webview.create_window

        def far_away(*args, **kwargs):
            return create(*args, **{**kwargs, "x": -4000, "y": 60})

        webview.create_window = far_away

    class Watched(appwindow.AppWindow):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            driver.app = self

    welcome.appwindow.AppWindow = Watched

    def walk() -> None:
        for _ in range(300):
            if driver.app and driver.app.opened:
                break
            time.sleep(0.2)
        time.sleep(3)
        try:
            steps(driver)
        except Exception as error:
            import traceback
            driver.failed += 1
            driver.log(f"FAIL  the walk stopped: {error!r}\n{traceback.format_exc()}")
        driver.log(f"== {driver.passed} passed, {driver.failed} failed")
        driver.app.close()

    threading.Thread(target=walk, daemon=True).start()
    welcome.main([])
    # The log has Chinese in it; a legacy console code page must not garble it.
    getattr(sys.stdout, "reconfigure", lambda **_: None)(encoding="utf-8", errors="replace")
    print((out / "walk.log").read_text(encoding="utf-8"))
    return driver.failed
