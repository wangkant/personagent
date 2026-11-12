"""The window `personagent start` opens instead of a browser tab, and the
shortcut that opens it. pywebview is stood in for: no window is drawn here."""
from __future__ import annotations

import importlib.util
import json
import re
import signal
import sys
import threading
import time
import types
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from persona_agent import cli, langs, shortcut, welcome, window

TOKEN = "test-local-capability"
HEADERS = {welcome.TOKEN_HEADER: TOKEN}


class _Event:
    def __init__(self) -> None:
        self.handlers: list = []
        self._flag = threading.Event()

    def __iadd__(self, handler):
        self.handlers.append(handler)
        return self

    def set(self) -> None:
        self._flag.set()

    def wait(self, timeout: float | None = None) -> bool:
        return self._flag.wait(timeout)

    def fire(self) -> None:
        for handler in self.handlers:
            handler()


class _Window:
    def __init__(self, gone: threading.Event, url: str | None) -> None:
        self.events = types.SimpleNamespace(**{name: _Event() for name in (
            "closing", "shown", "loaded", "minimized", "restored", "maximized", "before_show")})
        self.url = url
        self.calls: list[str] = []
        self.asked: list[tuple[str, str]] = []
        self.answer = True
        self._gone = gone

    def restore(self) -> None:
        self.calls.append("restore")

    def minimize(self) -> None:
        self.calls.append("minimize")

    def maximize(self) -> None:
        self.calls.append("maximize")

    def show(self) -> None:
        self.calls.append("show")

    def load_url(self, url: str) -> None:
        self.url = url

    def destroy(self) -> None:
        self.calls.append("destroy")
        self._gone.set()

    def create_confirmation_dialog(self, title: str, message: str) -> bool:
        self.asked.append((title, message))
        return self.answer

    def press_close(self) -> bool:
        """The person clicks the X; True when the window went away."""
        if any(handler() is False for handler in self.events.closing.handlers):
            return False
        self._gone.set()
        return True


@pytest.fixture
def webview(monkeypatch):
    """A stand-in pywebview whose `start` blocks until its window is gone.
    `module.person` is what the person does once the window is up."""
    module = types.ModuleType("webview")
    module.renderer = "edgechromium"
    module.shows = True
    module.person = lambda shown: shown.press_close()
    gone = threading.Event()

    def create_window(title, url, **options):
        module.created = (title, options)
        module.window = _Window(gone, url)
        return module.window

    def start(func, **options):
        module.started = options
        # pywebview calls these on the window's own thread, before it shows.
        module.window.events.before_show.fire()
        if module.shows:
            module.window.events.shown.set()
            module.window.events.loaded.set()
        ready = threading.Thread(target=func)
        ready.start()
        if module.shows:
            ready.join()
            module.person(module.window)
        assert gone.wait(5), "the window never closed"
        ready.join()

    module.create_window = create_window
    module.start = start
    monkeypatch.setitem(sys.modules, "webview", module)
    return module


def test_the_page_opens_in_a_private_window_with_the_app_icon(webview, tmp_path) -> None:
    seen = {}

    def person(shown) -> None:
        seen["front"] = app.show()
        seen["url"] = shown.url
        shown.press_close()

    webview.person = person
    app = window.AppWindow("http://127.0.0.1:1/#token=t", storage=tmp_path / "webview")
    assert app.run() is True and app.error == ""
    title, options = webview.created
    # Windows gets there by way of an empty first page; see AppWindow.run.
    assert (title, seen["url"]) == ("personagent", app.page_url)
    # The address, and after it the key only this window's page is given.
    assert app.page_url == f"http://127.0.0.1:1/#token=t&frame={app.frame_key}" and len(app.frame_key) >= 16
    assert app.is_own_page(app.frame_key) and not app.is_own_page("") and not app.is_own_page("guess")
    assert options["text_select"] is True, "a link in the page can be copied"
    assert webview.started["private_mode"] is True
    assert webview.started["storage_path"] == str(tmp_path / "webview")
    assert Path(webview.started["icon"]) == window.icon() and window.icon().is_file()
    assert seen["front"] is True and webview.window.calls == ["show"]
    assert app.show() is False, "nothing to bring forward once it closed"


def test_a_second_start_restores_only_a_minimized_window(webview, tmp_path) -> None:
    def person(shown) -> None:
        shown.events.maximized.fire()
        app.show()
        shown.events.minimized.fire()
        app.show()
        shown.events.restored.fire()
        app.show()
        shown.press_close()

    webview.person = person
    app = window.AppWindow("http://127.0.0.1:1/", storage=tmp_path)
    assert app.run() is True
    assert webview.window.calls == ["show", "restore", "show", "show"], (
        "a maximized window stays maximized")


def test_asked_to_close_before_it_exists_it_closes_once_it_does(webview, tmp_path) -> None:
    """The server died at once, or Ctrl+C came during the toolkit's own start."""
    webview.person = lambda shown: None
    app = window.AppWindow("http://127.0.0.1:1/", storage=tmp_path)
    app.close()
    assert app.run() is False and app.error == ""
    assert webview.window.calls == ["destroy"]


def test_both_icons_ship_with_the_package() -> None:
    for suffix in (".ico", ".png"):
        assert window.ICON.with_suffix(suffix).is_file(), suffix


def test_closing_asks_first_only_when_there_is_a_question(webview, tmp_path) -> None:
    answers = iter(["Close it?", "Close it?"])
    outcomes = []

    def person(shown) -> None:
        shown.answer = False
        outcomes.append(shown.press_close())
        shown.answer = True
        outcomes.append(shown.press_close())

    webview.person = person
    app = window.AppWindow("http://127.0.0.1:1/", storage=tmp_path, confirm=lambda: next(answers))
    assert app.run() is True
    assert outcomes == [False, True], "declined keeps the window, accepted closes it"
    assert webview.window.asked == [("personagent", "Close it?")] * 2


def test_quit_from_the_page_closes_without_asking(webview, tmp_path) -> None:
    webview.person = lambda shown: app.close()
    app = window.AppWindow("http://127.0.0.1:1/", storage=tmp_path, confirm=lambda: "Close it?")
    assert app.run() is True
    assert webview.window.asked == [] and webview.window.calls == ["destroy"]


def test_without_webview2_windows_gets_no_window(webview, tmp_path, monkeypatch) -> None:
    done = _frameless(monkeypatch, regions=True)
    webview.renderer = "mshtml"
    app = window.AppWindow("http://127.0.0.1:1/", storage=tmp_path)
    assert app.run() is False
    # The browser that takes over is told to draw no window bar.
    assert done["stripped"] == 1 and app.frameless is False
    assert "WebView2" in app.error and webview.window.calls == ["destroy"]
    assert webview.started["gui"] == "edgechromium"


def test_a_window_that_never_appears_counts_as_none(webview, tmp_path, monkeypatch) -> None:
    done = _frameless(monkeypatch, regions=True)
    monkeypatch.setattr(window, "SHOWN_WITHIN", 0.05)
    webview.shows = False
    app = window.AppWindow("http://127.0.0.1:1/", storage=tmp_path)
    assert app.run() is False and app.error
    assert done["stripped"] == 1 and app.frameless is False


def test_no_pywebview_means_no_window(tmp_path, monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "webview", None)
    app = window.AppWindow("http://127.0.0.1:1/", storage=tmp_path)
    assert app.run() is False and "webview" in app.error
    monkeypatch.setattr(importlib.util, "find_spec", lambda name: None)
    assert window.available() is False


def test_linux_with_qt_and_no_gtk_asks_for_qt_by_name(monkeypatch) -> None:
    """pywebview tries GTK first and prints a traceback when it is absent."""
    installed = {"qtpy"}
    monkeypatch.setattr(window.importlib.util, "find_spec",
                        lambda name: object() if name in installed else None)
    monkeypatch.setattr(sys, "platform", "linux")
    assert window._toolkit() == "qt"
    installed.add("gi")
    assert window._toolkit() is None
    installed.clear()
    assert window._toolkit() is None
    monkeypatch.setattr(sys, "platform", "darwin")
    installed.add("qtpy")
    assert window._toolkit() is None
    monkeypatch.setattr(sys, "platform", "win32")
    assert window._toolkit() == "edgechromium"


def test_a_toolkit_that_fails_to_start_is_reported_not_raised(webview, tmp_path) -> None:
    def start(func, **options):
        raise RuntimeError("no display")

    webview.start = start
    app = window.AppWindow("http://127.0.0.1:1/", storage=tmp_path)
    assert app.run() is False and "no display" in app.error


def test_ctrl_c_reaches_the_window_while_the_main_thread_is_elsewhere() -> None:
    stopped = threading.Event()
    before = signal.getsignal(signal.SIGINT)
    with window._interrupt(stopped.set):
        signal.raise_signal(signal.SIGINT)
        assert stopped.wait(5)
    assert signal.getsignal(signal.SIGINT) is before


# -- `personagent start` --------------------------------------------------

class _Server:
    """uvicorn's part: serve until told to exit."""

    def __init__(self) -> None:
        self.should_exit = False
        self.ran = threading.Event()

    def run(self, sockets=None) -> None:
        self.ran.set()
        while not self.should_exit:
            time.sleep(0.01)


def _fake_window(monkeypatch, run):
    """AppWindow replaced by one whose `run` is `run(instance)`."""
    made = []

    class Fake:
        def __init__(self, url, *, storage, confirm, **options):
            self.url, self.storage, self.confirm, self.options = url, storage, confirm, options
            self.error = ""
            self.closed = 0
            made.append(self)

        def show(self) -> bool:
            return True

        def close(self) -> None:
            self.closed += 1

        def run(self) -> bool:
            return run(self)

    monkeypatch.setattr(welcome.appwindow, "AppWindow", Fake)
    return made


@pytest.fixture
def page(tmp_path, monkeypatch):
    """A page app with nothing running, and a browser that only takes notes."""
    monkeypatch.setenv("AGENT_LANG", "en")
    workspace = welcome.Workspace(tmp_path)
    app = welcome.create_app(tmp_path, TOKEN, workspace=workspace)
    opened: list[str] = []
    monkeypatch.setattr(welcome.webbrowser, "open", opened.append)
    yield types.SimpleNamespace(app=app, workspace=workspace, opened=opened, home=tmp_path)
    workspace.close()


def test_closing_the_window_stops_the_server_and_opens_no_browser(page, monkeypatch) -> None:
    server = _Server()
    made = _fake_window(monkeypatch, lambda fake: server.ran.wait(5))
    welcome._serve_in_window(page.app, server, None, "http://127.0.0.1:1/#token=t", page.home)
    assert server.should_exit and page.opened == []
    assert made[0].storage == page.home / "webview"
    assert page.app.state.show() is True, "a second start can bring this window forward"


def test_quit_in_the_page_closes_the_window_too(page, monkeypatch) -> None:
    server = _Server()

    def run(fake) -> bool:
        page.app.state.shutdown()
        return True

    made = _fake_window(monkeypatch, run)
    welcome._serve_in_window(page.app, server, None, "http://127.0.0.1:1/", page.home)
    assert server.should_exit and made[0].closed >= 1


def test_no_window_falls_back_to_the_browser_and_keeps_serving(page, monkeypatch, capsys) -> None:
    server = _Server()

    def run(fake) -> bool:
        fake.error = "the WebView2 runtime is missing"
        # The page's Quit button, pressed a moment later in the browser.
        threading.Timer(0.2, page.app.state.shutdown).start()
        return False

    _fake_window(monkeypatch, run)
    welcome._serve_in_window(page.app, server, None, "http://127.0.0.1:1/#token=t", page.home)
    assert page.opened == ["http://127.0.0.1:1/#token=t"]
    assert page.app.state.show is None
    assert "WebView2" in capsys.readouterr().out


def test_ctrl_c_before_or_after_the_window_still_stops_the_server(page, monkeypatch) -> None:
    for outcome in (KeyboardInterrupt, False):
        server = _Server()

        def run(fake, outcome=outcome) -> bool:
            if outcome is KeyboardInterrupt:
                raise KeyboardInterrupt
            return outcome  # closed before it opened: no error, no fallback

        _fake_window(monkeypatch, run)
        welcome._serve_in_window(page.app, server, None, "http://127.0.0.1:1/", page.home)
        assert server.should_exit and page.opened == []


def test_the_window_asks_before_closing_only_while_a_platform_runs(page, monkeypatch) -> None:
    server = _Server()
    made = _fake_window(monkeypatch, lambda fake: True)
    welcome._serve_in_window(page.app, server, None, "http://127.0.0.1:1/", page.home)
    assert made[0].confirm() == ""
    monkeypatch.setattr(page.workspace.services, "running", lambda name: name == "direct")
    assert "out of your chats" in made[0].confirm()


def test_the_window_hides_instead_of_closing_only_when_the_person_chose_that(page, monkeypatch) -> None:
    server = _Server()
    made = _fake_window(monkeypatch, lambda fake: True)
    welcome._serve_in_window(page.app, server, None, "http://127.0.0.1:1/", page.home, hidden=True)
    options = made[0].options
    assert options["background"]() is False and options["start_hidden"] is False
    welcome.save_app_settings(page.home, background=True)
    assert options["background"]() is True, "read at the moment of closing, not at start"
    assert set(options["words"]()) == {"open", "quit", "still"}
    made = _fake_window(monkeypatch, lambda fake: True)
    welcome._serve_in_window(page.app, _Server(), None, "http://127.0.0.1:1/", page.home, hidden=True)
    assert made[0].options["start_hidden"] is True


def test_closing_goes_to_the_background_icon_when_there_is_one(webview, tmp_path) -> None:
    outcomes = []

    def person(shown) -> None:
        app._tray = object()  # the notification-area icon Windows gives
        hidden = []
        app.hide = lambda: hidden.append(True) or True
        outcomes.append(shown.press_close())
        outcomes.append(len(hidden))
        keep["on"] = False
        outcomes.append(shown.press_close())

    keep = {"on": True}
    webview.person = person
    app = window.AppWindow("http://127.0.0.1:1/", storage=tmp_path, background=lambda: keep["on"])
    assert app.run() is True
    assert outcomes == [False, 1, True], "hidden while the switch is on, closed once it is off"


def test_show_needs_the_capability_and_reports_whether_a_window_came_forward(page) -> None:
    with TestClient(page.app, base_url="http://127.0.0.1") as client:
        assert client.post("/api/show", json={}).status_code == 403
        assert client.post("/api/show", json={}, headers=HEADERS).json() == {"ok": True, "window": False}
        page.app.state.show = lambda: True
        assert client.post("/api/show", json={}, headers=HEADERS).json() == {"ok": True, "window": True}


def test_a_second_start_asks_the_first_for_its_window(monkeypatch) -> None:
    asked = {}

    def post(url, **options):
        asked.update(url=url, **options)
        return types.SimpleNamespace(json=lambda: {"ok": True, "window": True})

    monkeypatch.setattr(welcome.httpx, "post", post)
    assert welcome._raise_window("http://127.0.0.1:4321/#token=abc") is True
    assert asked["url"] == "http://127.0.0.1:4321/api/show"
    assert asked["headers"] == {welcome.TOKEN_HEADER: "abc"}
    assert asked["trust_env"] is False, "a system proxy must not get the local token"

    def refused(url, **options):
        raise httpx.ConnectError("gone")

    monkeypatch.setattr(welcome.httpx, "post", refused)
    assert welcome._raise_window("http://127.0.0.1:4321/#token=abc") is False


def _held_start(home: Path, url: str = ""):
    """The lock a running personagent holds, with the link it left."""
    info = home / "runtime" / "desktop" / "welcome.json"
    info.parent.mkdir(parents=True)
    if url:
        info.write_text(json.dumps({"url": url}), encoding="utf-8")
    lock = welcome.FileLock(info.with_suffix(".lock"), timeout=0)
    lock.acquire()
    return lock


@pytest.mark.parametrize("argv, has_window, opens", [
    ([], True, False), ([], False, True), (["--browser"], True, True), (["--no-browser"], False, False)])
def test_starting_twice_reuses_the_running_page(tmp_path, monkeypatch, capsys,
                                                argv, has_window, opens) -> None:
    monkeypatch.setenv("AGENT_HOME", str(tmp_path))
    monkeypatch.setenv("AGENT_LANG", "en")
    url = "http://127.0.0.1:4321/#token=abc"
    lock = _held_start(tmp_path, url)
    opened: list[str] = []
    monkeypatch.setattr(welcome.webbrowser, "open", opened.append)
    monkeypatch.setattr(welcome, "_raise_window", lambda link: has_window)
    try:
        assert welcome.main(argv) == 0
    finally:
        lock.release()
    assert capsys.readouterr().out.strip() == url
    assert opened == ([url] if opens else [])


def test_started_without_a_terminal_it_logs_and_says_refusals_in_a_dialog(
        tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENT_HOME", str(tmp_path))
    monkeypatch.setenv("AGENT_LANG", "en")
    lock = _held_start(tmp_path)
    earlier = tmp_path / "runtime" / "desktop" / "app.log"
    earlier.write_text("what the running one logged\n", encoding="utf-8")
    said: list[str] = []
    monkeypatch.setattr(window, "alert", said.append)
    # pythonw leaves both streams unset.
    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)
    try:
        assert welcome.main([]) == 1
        log = sys.stdout
    finally:
        lock.release()
        monkeypatch.undo()
    log.close()
    assert said == ["personagent is starting. Try again in a moment."]
    written = earlier.read_text(encoding="utf-8")
    assert said[0] in written
    assert written.startswith("what the running one logged"), "its log is not this start's to empty"


def test_an_install_that_does_not_import_says_so_without_a_terminal(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENT_HOME", str(tmp_path))
    monkeypatch.setenv("AGENT_LANG", "en")
    said: list[str] = []
    monkeypatch.setattr(window, "alert", said.append)
    real = cli.importlib.import_module

    def missing(name, *args):
        if name == "persona_agent.welcome":
            raise ImportError("No module named 'fastapi'")
        return real(name, *args)

    monkeypatch.setattr(cli.importlib, "import_module", missing)
    with pytest.raises(ImportError):
        cli.main(["start"])  # a terminal shows the traceback itself
    monkeypatch.setattr(sys, "stderr", None)
    try:
        assert cli.main(["start"]) == 1
    finally:
        monkeypatch.undo()
    log = tmp_path / "runtime" / "desktop" / "app.log"
    assert len(said) == 1 and str(log) in said[0]
    assert "No module named 'fastapi'" in log.read_text(encoding="utf-8")


def test_the_update_command_names_a_python_that_prints(tmp_path, monkeypatch) -> None:
    from persona_agent import updates

    (tmp_path / "python.exe").write_bytes(b"")
    monkeypatch.setattr(sys, "executable", str(tmp_path / "pythonw.exe"))
    assert updates._python() == str(tmp_path / "python.exe")
    monkeypatch.setattr(sys, "executable", str(tmp_path / "python3"))
    assert updates._python() == str(tmp_path / "python3")


def test_a_crash_without_a_terminal_names_the_log(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENT_HOME", str(tmp_path))
    monkeypatch.setenv("AGENT_LANG", "en")
    said: list[str] = []
    monkeypatch.setattr(window, "alert", said.append)

    def broken(args, home, refuse, log=None):
        raise RuntimeError("boom")

    monkeypatch.setattr(welcome, "_start", broken)
    with pytest.raises(RuntimeError):
        welcome.main([])  # with a terminal the traceback is the message
    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)
    try:
        assert welcome.main([]) == 1
        log = sys.stdout
    finally:
        monkeypatch.undo()
    log.close()
    path = tmp_path / "runtime" / "desktop" / "app.log"
    assert len(said) == 1 and str(path) in said[0]
    assert "RuntimeError: boom" in path.read_text(encoding="utf-8")


@pytest.mark.parametrize("argv, available, windowed", [
    ([], True, True), ([], False, False), (["--browser"], True, False), (["--no-browser"], True, False)])
def test_start_opens_the_window_when_it_can(tmp_path, monkeypatch, capsys,
                                            argv, available, windowed) -> None:
    import uvicorn

    monkeypatch.setenv("AGENT_HOME", str(tmp_path))
    monkeypatch.setenv("AGENT_LANG", "en")
    monkeypatch.setattr(welcome.appwindow, "available", lambda: available)
    opened = threading.Event()
    monkeypatch.setattr(welcome.webbrowser, "open", lambda url: opened.set())
    in_window: list[str] = []
    monkeypatch.setattr(welcome, "_serve_in_window",
                        lambda app, server, sock, url, desktop, hidden=False: in_window.append(url))
    monkeypatch.setattr(uvicorn.Server, "run", lambda self, sockets=None: None)
    assert welcome.main(argv) == 0
    out = capsys.readouterr().out
    link = re.search(r"http://127\.0\.0\.1:\d+/#token=\S+", out).group(0)
    assert in_window == ([link] if windowed else [])
    assert ("Close the personagent window to stop." in out) is windowed
    browser = not windowed and argv != ["--no-browser"]
    assert opened.wait(2 if browser else 0.2) is browser
    assert not (tmp_path / "runtime" / "desktop" / "welcome.json").exists()


# -- the shortcut ---------------------------------------------------------

def test_the_shortcut_runs_this_install_on_this_home_with_the_icon(tmp_path) -> None:
    home = tmp_path / "it's home"
    source = shortcut.script(home, folders=[tmp_path / "Desktop"])
    program, arguments = shortcut.target(home)
    assert program.parent == Path(sys.executable).parent
    assert arguments == f'-m persona_agent start --home "{home}"'
    assert "it''s home" in source, "a quote in a path stays inside its PowerShell string"
    assert f"'{window.icon()}'" in source and "personagent.lnk" in source
    assert "GetFolderPath('Desktop')" in shortcut.script(home)
    removal = shortcut.script(home, remove=True, folders=[tmp_path])
    assert "Remove-Item" in removal and "CreateShortcut" not in removal


def test_shortcut_is_a_command(monkeypatch, capsys, tmp_path) -> None:
    module, func, _help = cli.COMMANDS["shortcut"]
    assert (module, func) == ("persona_agent.shortcut", "main")
    monkeypatch.setenv("AGENT_LANG", "en")
    monkeypatch.setenv("AGENT_HOME", str(tmp_path))
    ran = []
    monkeypatch.setattr(shortcut, "run", lambda source: ran.append(source) or "")

    monkeypatch.setattr(shortcut, "WINDOWS", False)
    assert shortcut.main([]) == 1 and "Windows only" in capsys.readouterr().out
    monkeypatch.setattr(shortcut, "WINDOWS", True)
    monkeypatch.setattr(langs, "under_uvx", lambda: True)
    assert shortcut.main([]) == 1 and "uv tool install" in capsys.readouterr().out
    assert ran == [], "nothing is written for a copy that will not stay"

    monkeypatch.setattr(langs, "under_uvx", lambda: False)
    assert shortcut.main([]) == 0 and "desktop" in capsys.readouterr().out
    assert str(tmp_path) in ran[-1] and "CreateShortcut" in ran[-1]
    assert shortcut.main(["--remove"]) == 0 and "gone" in capsys.readouterr().out
    assert "Remove-Item" in ran[-1]
    monkeypatch.setattr(shortcut, "run", lambda source: "access denied")
    assert shortcut.main([]) == 1 and "access denied" in capsys.readouterr().out


@pytest.mark.skipif(not shortcut.WINDOWS, reason="Windows writes .lnk files")
def test_windows_writes_the_link_and_takes_it_away(tmp_path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    folder = tmp_path / "Desktop 桌面"
    folder.mkdir()
    assert shortcut.run(shortcut.script(home, folders=[folder])) == ""
    assert (folder / shortcut.LINK).is_file()
    assert shortcut.run(shortcut.script(home, remove=True, folders=[folder])) == ""
    assert not (folder / shortcut.LINK).exists()
    failed = shortcut.run(shortcut.script(home, folders=[tmp_path / "missing"]))
    assert failed and "CLIXML" not in failed, "the reason is a sentence, not PowerShell's envelope"


# -- the page's own chat ----------------------------------------------------

def test_the_page_names_its_chat_as_the_owners(tmp_path) -> None:
    from persona_agent import access

    workspace = welcome.Workspace(tmp_path)
    try:
        assert access.page_owner(tmp_path / "runtime") == frozenset(), "nothing named before the first save"
        workspace.reset_chat()
        named = access.page_owner(tmp_path / "runtime")
        assert named == {f"browser:{workspace._conversation}"}
        workspace.reset_chat()
        assert access.page_owner(tmp_path / "runtime") == {f"browser:{workspace._conversation}"} != named
        (tmp_path / "runtime" / access.PAGE_OWNER_FILE).write_text("x, qq:1", encoding="utf-8")
        assert access.page_owner(tmp_path / "runtime") == frozenset(), "only one plain id is ever an owner"
    finally:
        workspace.close()


async def test_forgetting_a_chat_asks_the_service_once_then_starts_a_new_one(tmp_path, monkeypatch) -> None:
    workspace = welcome.Workspace(tmp_path)
    before = workspace._conversation
    chat = f"private:browser:{before}"
    calls = []

    async def call(method, path, **options):
        calls.append((method, path, options.get("json") or options.get("params")))
        return {"ok": True, "forgotten": 3}

    monkeypatch.setattr(workspace, "_activity_call", call)
    monkeypatch.setattr(workspace.services, "start_agent", lambda: None)
    try:
        done = await workspace.forget_chat()
    finally:
        workspace.close()
    # Only this chat is forgotten; what other chats remember is kept.
    assert done == {"ok": True, "forgotten": 3}
    assert calls == [("POST", "/api/dashboard/memory/forget_chat", {"conv": chat})]
    assert workspace._conversation != before and workspace._history == []


# ---------------------------------------------------------------- frameless

def _frameless(monkeypatch, *, regions: bool):
    """Windows, with the two native steps stood in for; what they were asked to do."""
    done = {"stripped": 0, "undone": 0}

    def strip(shown):
        done["stripped"] += 1
        return object(), lambda: done.__setitem__("undone", done["undone"] + 1)

    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(window, "_strip_title_bar", strip)
    monkeypatch.setattr(window, "_text_menus", lambda shown: regions)
    return done


def test_on_windows_the_title_bar_goes_before_the_window_shows(webview, tmp_path, monkeypatch) -> None:
    done = _frameless(monkeypatch, regions=True)
    seen = {}

    def person(shown) -> None:
        app.frame_seen()
        seen["frameless"] = app.frameless
        shown.press_close()

    webview.person = person
    app = window.AppWindow("http://127.0.0.1:1/", storage=tmp_path)
    assert app.run() is True
    assert seen == {"frameless": True} and done == {"stripped": 1, "undone": 0}


def test_a_webview_whose_page_cannot_move_the_window_keeps_the_title_bar(webview, tmp_path, monkeypatch) -> None:
    done = _frameless(monkeypatch, regions=False)
    seen = {}

    def person(shown) -> None:
        seen["frameless"] = app.frameless
        shown.press_close()

    webview.person = person
    app = window.AppWindow("http://127.0.0.1:1/", storage=tmp_path)
    assert app.run() is True
    assert seen == {"frameless": False} and done == {"stripped": 1, "undone": 1}


@pytest.mark.parametrize("asks, undone", [(True, 0), (False, 1)])
def test_a_page_that_never_draws_the_bar_gives_the_window_its_own_back(webview, tmp_path, monkeypatch,
                                                                         asks, undone) -> None:
    done = _frameless(monkeypatch, regions=True)
    monkeypatch.setattr(window, "PAGE_WITHIN", 0.1)
    seen = {}

    def person(shown) -> None:
        if asks:
            app.frame_seen()
        time.sleep(1.0)
        seen["frameless"] = app.frameless
        shown.press_close()

    webview.person = person
    app = window.AppWindow("http://127.0.0.1:1/", storage=tmp_path)
    assert app.run() is True
    assert seen == {"frameless": asks} and done["undone"] == undone


def test_elsewhere_the_window_keeps_its_title_bar(webview, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(window, "_strip_title_bar", lambda shown: pytest.fail("only Windows drops the title bar"))
    app = window.AppWindow("http://127.0.0.1:1/", storage=tmp_path)
    assert app.run() is True and app.frameless is False
    assert app.control("minimize") is False, "nothing to do once it closed"


def test_the_pages_buttons_do_what_a_title_bars_do(webview, tmp_path) -> None:
    seen = {}

    def person(shown) -> None:
        seen["before"] = [app.control(action) for action in ("minimize", "maximize", "restore")]
        seen["calls"] = list(shown.calls)
        seen["unknown"] = app.control("format-disk")
        shown.events.maximized.fire()
        seen["maximized"] = app.maximized
        shown.events.restored.fire()
        seen["restored"] = app.maximized
        # Close goes the way the system's button does: here nothing asks, so it closes.
        seen["close"] = app.control("close")

    webview.person = person
    app = window.AppWindow("http://127.0.0.1:1/", storage=tmp_path)
    assert app.control("close") is False, "no window yet"
    assert app.run() is True
    assert seen == {"before": [True, True, True], "calls": ["minimize", "maximize", "restore"],
                    "unknown": False, "maximized": True, "restored": False, "close": True}
    assert webview.window.calls[-1] == "destroy"


def test_a_window_closed_before_its_page_asked_is_left_alone(webview, tmp_path, monkeypatch) -> None:
    done = _frameless(monkeypatch, regions=True)
    monkeypatch.setattr(window, "PAGE_WITHIN", 0.2)
    app = window.AppWindow("http://127.0.0.1:1/", storage=tmp_path)
    assert app.run() is True
    time.sleep(0.5)
    assert done["undone"] == 0, "nothing is done to a window that is gone"

