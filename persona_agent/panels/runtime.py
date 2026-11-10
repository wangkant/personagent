"""The runtime panel: keep running behind the window, and update from inside the app."""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
from pathlib import Path

from fastapi import Request

from .. import __version__, home as homes, updates
from ..storage import atomic_write_text

# Error codes this panel raises as ValueError, which the page may show.
ERRORS: frozenset[str] = frozenset({
    "background_unavailable", "update_none", "update_by_hand", "update_tool_missing",
    "update_clone_changed", "update_not_started"})
LOG_TAIL = 60


def start_update(home: Path, commands: list[list[str]]) -> None:
    """Leave a helper behind that updates once this process has quit, then
    opens personagent again."""
    desktop = home / "runtime" / "desktop"
    desktop.mkdir(parents=True, exist_ok=True)
    # A copy outside the package: the package is what gets replaced.
    helper = desktop / "update_helper.py"
    shutil.copyfile(Path(__file__).resolve().parents[1] / "update_helper.py", helper)
    python = Path(updates._python())
    quiet = python.with_name("pythonw.exe")
    plan = desktop / "update-plan.json"
    atomic_write_text(plan, json.dumps({
        "pid": os.getpid(), "commands": commands, "from": __version__,
        "relaunch": [str(quiet if quiet.is_file() else python), "-m", "persona_agent", "start",
                     "--home", str(home)],
        "log": str(desktop / "update.log"), "result": str(desktop / "update-result.json")}))
    (desktop / "update-result.json").unlink(missing_ok=True)
    # The keys this process read from .env are not the helper's to hold.
    env = {key: value for key, value in os.environ.items() if key not in homes.FROM_ENV_FILE}
    subprocess.Popen(
        [str(python), str(helper), str(plan)], cwd=str(home), env=env, close_fds=True,
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
        | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))


def mount(app, workspace, body) -> None:
    from ..welcome import app_settings, save_app_settings

    desktop = workspace.home / "runtime" / "desktop"

    def last_update() -> dict | None:
        try:
            done = json.loads((desktop / "update-result.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        return {"ok": bool(done.get("ok")), "from": str(done.get("from") or "")}

    def summary() -> dict:
        window = getattr(app.state, "window", None)
        found = updates.notice(workspace.home, always=True)
        kind, commands = updates.plan()
        last = updates._read(workspace.home)
        checked = last.get("checked")
        return {
            "version": __version__,
            "background": bool(app_settings(desktop).get("background")),
            "canHide": bool(window is not None and window.can_hide),
            "update": found and {"version": found["version"], "url": found["url"],
                                 "command": found["command"]},
            "updateBlocked": updates.blocked(kind, commands) if found else "",
            "checked": checked if isinstance(checked, (int, float)) else None,
            # The last attempt did not reach PyPI: "up to date" would be a guess.
            "checkFailed": bool(last.get("failed")),
            "updateKind": kind,
            "lastUpdate": last_update(),
        }

    @app.get("/api/runtime")
    async def runtime():
        return await asyncio.to_thread(summary)

    @app.post("/api/runtime/background")
    async def background(request: Request):
        on = bool((await body(request)).get("on"))
        window = getattr(app.state, "window", None)
        if on and not (window is not None and window.can_hide):
            raise ValueError("background_unavailable")
        save_app_settings(desktop, background=on)
        return await asyncio.to_thread(summary)

    @app.post("/api/runtime/hide")
    async def hide(request: Request):
        await body(request)
        window = getattr(app.state, "window", None)
        if window is None or not await asyncio.to_thread(window.hide):
            raise ValueError("background_unavailable")
        return {"ok": True}

    @app.post("/api/runtime/check")
    async def check(request: Request):
        await body(request)
        await asyncio.to_thread(updates.check, workspace.home, 10.0)
        return await asyncio.to_thread(summary)

    @app.post("/api/runtime/update")
    async def update(request: Request):
        await body(request)
        if not updates.notice(workspace.home, always=True):
            raise ValueError("update_none")
        kind, commands = updates.plan()
        refusal = await asyncio.to_thread(updates.blocked, kind, commands)
        if refusal:
            raise ValueError(refusal)
        # The helper first: if it cannot start, the app must be left as it was.
        try:
            start_update(workspace.home, commands)
        except OSError:
            raise ValueError("update_not_started") from None
        # Everything the app started stops before it quits: the helper replaces the files they hold.
        await asyncio.to_thread(workspace.close)
        callback = getattr(app.state, "shutdown", None)
        if callback:
            callback()
        return {"ok": True}

    @app.get("/api/runtime/update/log")
    async def update_log():
        try:
            lines = (desktop / "update.log").read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            lines = []
        return {"lines": lines[-LOG_TAIL:]}

    @app.post("/api/runtime/update/seen")
    async def seen(request: Request):
        await body(request)
        (desktop / "update-result.json").unlink(missing_ok=True)
        return {"ok": True}
