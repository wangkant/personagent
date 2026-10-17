"""Whether a newer personagent is on PyPI. Asked at most once a day, never
while anything waits on it, and the request carries only the version number."""
from __future__ import annotations

import json
import os
import re
import sys
import threading
import time
from pathlib import Path

from . import __version__, home as homes
from .config_env import env_bool
from .storage import atomic_write_text

PYPI_URL = "https://pypi.org/pypi/personagent/json"
RELEASE_URL = "https://github.com/wangkant/personagent/releases/tag/v{version}"
CHECK_EVERY_S = 24 * 3600
RETRY_AFTER_S = 3600
# Generous: it runs in the background, and through some proxies PyPI's TLS
# handshake alone takes seconds.
TIMEOUT_S = 15.0

_lock = threading.Lock()
_running: set[Path] = set()


def _release(version: str) -> tuple[int, ...] | None:
    match = re.match(r"(\d+)\.(\d+)\.(\d+)", version or "")
    return tuple(int(n) for n in match.groups()) if match else None


def newer(latest: str, current: str = __version__) -> bool:
    """Only a plain X.Y.Z release counts, so a pre-release is never offered."""
    mine = _release(current)
    if mine is None or not re.fullmatch(r"\d+\.\d+\.\d+", latest or ""):
        return False
    return _release(latest) > mine


def enabled(home: Path) -> bool:
    from dotenv import dotenv_values

    env = home / ".env"
    values = {k: v for k, v in dotenv_values(env).items() if v is not None} if env.is_file() else {}
    values.update(os.environ)  # the shell wins over .env, as everywhere else
    return env_bool("UPDATE_CHECK_ENABLED", True, env=values)


def _cache(home: Path) -> Path:
    return home / "runtime" / "desktop" / "update.json"


def _read(home: Path) -> dict:
    try:
        data = json.loads(_cache(home).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def check(home: Path) -> str:
    """Ask PyPI now and remember the answer; a failure keeps the last one."""
    import httpx

    latest = ""
    try:
        response = httpx.get(PYPI_URL, timeout=TIMEOUT_S, follow_redirects=True,
                             headers={"User-Agent": f"personagent/{__version__}"})
        response.raise_for_status()
        latest = str(response.json()["info"]["version"])
    except Exception:  # offline, blocked, or an answer of another shape
        pass
    failed = not latest
    latest = latest or str(_read(home).get("latest") or "")
    try:
        atomic_write_text(_cache(home), json.dumps({"checked": time.time(), "latest": latest,
                                                    "failed": failed}), fsync=False)
    except OSError:
        pass
    return latest


def refresh_soon(home: Path) -> None:
    """Ask in the background once the last answer is a day old, or an hour
    after a failed attempt."""
    if not enabled(home):
        return
    last = _read(home)
    checked, wait = last.get("checked"), RETRY_AFTER_S if last.get("failed") else CHECK_EVERY_S
    if isinstance(checked, (int, float)) and 0 <= time.time() - checked < wait:
        return
    key = home.resolve()
    with _lock:
        if key in _running:
            return
        _running.add(key)

    def run() -> None:
        try:
            check(home)
        finally:
            with _lock:
                _running.discard(key)

    threading.Thread(target=run, name="personagent-update-check", daemon=True).start()


def how_to_update() -> tuple[str, bool]:
    """The command that updates this installation ('' for an unpacked source
    ZIP), and whether running it also starts personagent."""
    from .setup_wizard import _program, _quote

    if homes.is_checkout():
        if (homes.CHECKOUT / ".git").exists():
            return f"git -C {_quote(str(homes.CHECKOUT))} pull", False
        return "", False
    prefix = sys.prefix.replace("\\", "/").lower()
    if "/archive-v" in prefix:  # uvx: a throwaway environment in uv's cache
        return "uvx personagent@latest", True
    if "/uv/tools/" in prefix:
        return "uv tool upgrade personagent", False
    if "/pipx/venvs/" in prefix:
        return "pipx upgrade personagent", False
    return f"{_program(sys.executable)} -m pip install -U personagent", False


def notice(home: Path, latest: str | None = None) -> dict | None:
    """The newer release the last check found, and how to install it."""
    if not enabled(home):
        return None
    latest = str(_read(home).get("latest") or "") if latest is None else latest
    if not newer(latest):
        return None
    command, opens = how_to_update()
    return {"version": latest, "command": command, "opens": opens,
            "url": RELEASE_URL.format(version=latest)}


def line(found: dict | None) -> str:
    """The notice as one terminal line, '' without one."""
    if not found:
        return ""
    head = f"personagent {found['version']} is available."
    if not found["command"]:
        return f"{head} Download it from {found['url']}"
    if found["opens"]:
        return f"{head} Quit, then start it with: {found['command']}"
    return f"{head} Quit, run: {found['command']}, then start personagent again."
