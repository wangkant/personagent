"""Whether a newer personagent is on PyPI. Asked at most once a day, in the
background (doctor asks itself when the answer is older), and the request
carries only the version number."""
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
# Generous: through some proxies PyPI's TLS handshake alone takes seconds.
TIMEOUT_S = 15.0

_lock = threading.Lock()
_running: set[Path] = set()
# When each home last started a check, so an unwritable cache cannot turn
# the page's polling into a request every few seconds.
_attempted: dict[Path, float] = {}
_enabled: dict[tuple, bool] = {}


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
    env = home / ".env"
    try:
        stamp = env.stat().st_mtime_ns
    except OSError:
        stamp = None
    # Remembered per .env version, so a bad value warns once, not every poll.
    key = (str(home), stamp, os.environ.get("UPDATE_CHECK_ENABLED"))
    if key not in _enabled:
        from dotenv import dotenv_values

        values = ({k: v for k, v in dotenv_values(env).items() if v is not None}
                  if stamp is not None else {})
        values.update(os.environ)  # the shell wins over .env, as everywhere else
        _enabled[key] = env_bool("UPDATE_CHECK_ENABLED", True, env=values)
    return _enabled[key]


def _cache(home: Path) -> Path:
    return home / "runtime" / "desktop" / "update.json"


def _read(home: Path) -> dict:
    try:
        data = json.loads(_cache(home).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data


def stale(home: Path) -> bool:
    """The last answer is a day old, or an hour old after a failed attempt."""
    last = _read(home)
    checked, wait = last.get("checked"), RETRY_AFTER_S if last.get("failed") else CHECK_EVERY_S
    return checked is None or not 0 <= time.time() - checked < wait


def check(home: Path, timeout: float = TIMEOUT_S) -> str:
    """Ask PyPI now and remember the answer; a failure keeps the last one."""
    import httpx

    latest = ""
    try:
        response = httpx.get(PYPI_URL, timeout=timeout, follow_redirects=True,
                             headers={"User-Agent": f"personagent/{__version__}"})
        response.raise_for_status()
        latest = str(response.json()["info"]["version"])
    except Exception:  # offline, blocked, or an answer of another shape
        pass
    failed = not latest
    latest = latest or str(_read(home).get("latest") or "")
    if home.is_dir():  # doctor may name a home that does not exist yet
        try:
            atomic_write_text(_cache(home), json.dumps(
                {"checked": time.time(), "latest": latest, "failed": failed}), fsync=False)
        except OSError:
            pass
    return latest


def refresh_soon(home: Path) -> None:
    """Ask in the background when the last answer is stale."""
    if not enabled(home) or not stale(home):
        return
    key = home.resolve()
    with _lock:
        now = time.time()
        if key in _running or 0 <= now - _attempted.get(key, 0) < RETRY_AFTER_S:
            return
        _running.add(key)
        _attempted[key] = now

    def run() -> None:
        try:
            check(home)
        finally:
            with _lock:
                _running.discard(key)

    threading.Thread(target=run, name="personagent-update-check", daemon=True).start()


def how_to_update() -> tuple[str, bool]:
    """The command that updates this installation ('' for an unpacked source
    ZIP; a clone's has two lines), and whether it also starts personagent."""
    from .setup_wizard import _program, _quote

    if homes.is_checkout():
        if not (homes.CHECKOUT / ".git").exists():
            return "", False
        root = _quote(str(homes.CHECKOUT))
        # A pull can bring new dependencies.
        return f"git -C {root} pull\n{_program(sys.executable)} -m pip install -e {root}", False
    prefix = Path(sys.prefix)
    if re.search(r"/archive-v\d+/", sys.prefix.replace("\\", "/").lower() + "/"):
        return "uvx personagent@latest", True  # a throwaway environment in uv's cache
    if (prefix / "uv-receipt.toml").is_file():
        return "uv tool upgrade personagent", False
    if (prefix / "pipx_metadata.json").is_file():
        return "pipx upgrade personagent", False
    try:
        config = (prefix / "pyvenv.cfg").read_text(encoding="utf-8")
    except OSError:
        config = ""
    if re.search(r"^uv\s*=", config, re.MULTILINE):  # uv's venvs have no pip
        return f"uv pip install -U personagent --python {_quote(sys.executable)}", False
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


def line(found: dict | None, sub: str = "") -> str:
    """The notice for a terminal, the command last so it copies cleanly;
    `sub` follows a command that starts personagent, such as `up`."""
    if not found:
        return ""
    head = f"personagent {found['version']} is available."
    if not found["command"]:
        return f"{head} Download the new source from {found['url']}"
    if found["opens"]:
        return f"{head} Quit personagent, then start the new version with:\n  {found['command']} {sub}".rstrip()
    commands = "\n  ".join(found["command"].splitlines())
    return f"{head} Quit personagent, run this, then start it again:\n  {commands}"
