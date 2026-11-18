"""Connecting a platform personagent serves itself: the sign-in, the check
with the platform and the saving that the local page and
`personagent connect <platform>` share. Each failure is a RuntimeError whose
message is a short code (NAMED_REFUSALS, scan_failed, network_failed,
display_failed, platform_rejected or cancelled), never a credential."""
from __future__ import annotations

import asyncio
import importlib.util
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Callable, Optional

from . import connections as conn
from . import direct
from .astrbot_install import AstrBotInstallation
from .direct import base as direct_base
from .direct import browser as web

# Refusals a direct platform names, which the page and the terminal explain one by one.
NAMED_REFUSALS = {"token_rejected", "app_rejected", "bot_in_use", "message_content_intent_off",
                  "intents_not_allowed", "session_expired", "bot_offline", "bot_banned",
                  "account_deactivated", "insecure_address", "homeserver_invalid", "owner_invalid",
                  "channel_not_found", "nick_in_use", "nick_invalid", "password_rejected",
                  "sasl_required", "long_poll_off", "message_events_off", "token_rights_missing",
                  "not_a_bot", "wrong_bot_type", "not_zulip_site",
                  "need_verifycode", "verify_code_blocked", "binded_redirect", "token_missing",
                  "login_denied", "invalid_intents", "invalid_shard", "sharding_required",
                  "invalid_api_version", "sign_in_expired", "login_rejected", "login_unsupported",
                  "token_short_lived", "sign_in_missing", "invite_declined",
                  # A platform worked through its website (direct.browser).
                  web.VERIFICATION, web.PAGE_CHANGED, web.NO_BROWSER, web.NO_DRIVER, web.DAILY_LIMIT,
                  web.NO_START, "channel_missing",
                  # Still retried, with a cause the page names (direct.base.Status "retrying").
                  "unreachable", "access_denied", "session_paused"}


# How long a direct platform may take to accept a new session.
DIRECT_WINDOW = 40


def verdict(state: dict, running: bool = True) -> str:
    """What one platform's status says of a new session: "connected", "" while
    it is still being decided, or the code of a refusal. The page and the
    terminal both read a connection attempt through this."""
    current = state.get("state")
    if current == "connected":
        return "connected"
    detail = str(state.get("detail") or "")
    if current in ("refused", "error") or not running:
        return detail if detail in NAMED_REFUSALS else "platform_rejected"
    if current == "retrying" and detail == direct_base.ACCESS_DENIED:
        return detail
    return ""


class _NotShown(Exception):
    """The sign-in's `show` failed: the screen, not the platform."""


def stored(home: Path) -> list[str]:
    """The directly connected platforms, in catalog order."""
    saved = direct_base.load_credentials(home)
    return [p.kind for p in conn.PLATFORMS if p.kind in saved]


def check(home: Path, spec: conn.Platform, values: dict, *, session: bool = False,
          window: float = DIRECT_WINDOW) -> dict:
    """Ask the platform whether it accepts `values`; nothing is saved here.
    The values to store, which a sign-in may have changed (Matrix trades a
    password for a token and keeps only the token). With `session`, a
    platform that can still refuse once a session opens (Discord's gateway
    without Message Content Intent) is also given one session, up to
    `window` seconds, and its verdict read as the page reads it."""
    platform = direct.platform_for(spec.kind, values, home)
    state: dict = {}

    async def ask() -> dict:
        try:
            await platform.check()
            keep = getattr(platform, "keep", None)
            kept = keep() if callable(keep) else dict(values)
            if session and getattr(platform, "refuses_in_session", False) is True:
                await _session(platform, state, window)
            return kept
        finally:
            await platform.close()
    try:
        kept = asyncio.run(ask())
    except direct_base.Refused as exc:
        raise RuntimeError(str(exc) if str(exc) in NAMED_REFUSALS else "platform_rejected") from None
    except ConnectionError as exc:
        # A browser that would not start is not the network.
        raise RuntimeError(web.NO_START if str(exc) == web.NO_START else "network_failed") from None
    result = verdict(state)
    if result not in ("", "connected"):
        raise RuntimeError(result)
    return kept


async def _session(platform, state: dict, window: float) -> None:
    """Run `platform` until it accepts a session, refuses it or `window` ends,
    recording what happened in `state` as the status file would."""
    decided = asyncio.Event()

    def connected() -> None:
        state.update(state="connected")
        decided.set()

    async def ignore(event: dict, target) -> None:
        pass

    async def run() -> None:
        try:
            await platform.run(ignore, connected)
        except direct_base.Refused as exc:
            state.update(state="refused", detail=str(exc))
        except Exception as exc:
            state.update(state="error", detail=type(exc).__name__)
        finally:
            decided.set()
    platform.dropped = lambda cause=None: state.update(state="connecting")
    task = asyncio.create_task(run())
    try:
        await asyncio.wait_for(decided.wait(), window)
    except asyncio.TimeoutError:
        pass            # still connecting: kept, as the page keeps it
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)


def sign_in(spec: conn.Platform, values: dict, show: Callable[[str], None],
            should_stop: Callable[[], bool] = lambda: False) -> dict:
    """Run a platform's QR or link login, handing what it shows to `show`;
    the values to store."""
    import httpx

    flow = direct.sign_in_for(spec.kind)
    if flow is None:
        raise RuntimeError("platform_rejected")
    scan, failed = flow

    def shown(content: str) -> None:
        # A screen that cannot draw the code is not a network failure.
        try:
            show(content)
        except Exception as exc:
            raise _NotShown() from exc

    async def login() -> dict:
        async with httpx.AsyncClient() as client:
            task = asyncio.create_task(scan(client, shown, values))
            while not task.done():
                if should_stop():
                    task.cancel()
                    raise RuntimeError("cancelled")
                await asyncio.sleep(0.3)
            return task.result()
    try:
        return asyncio.run(login())
    except _NotShown:
        raise RuntimeError("display_failed") from None
    except failed as exc:
        # A login may name a refusal, such as an app it does not accept.
        raise RuntimeError(str(exc) if str(exc) in NAMED_REFUSALS else "scan_failed") from None
    except (httpx.HTTPError, ValueError):
        raise RuntimeError("network_failed") from None


def connect_plugin(home: Path) -> None:
    """Point the managed AstrBot's plugin at this home's agent."""
    from . import setup_wizard as sw

    data = AstrBotInstallation(home).root / "data"
    values: dict = {}
    # OneBot (NapCat) carries QQ numbers, which the agent reads bare.
    sw.connect_astrbot(home / ".env", values, data_dir=data, qq="aiocqhttp" in conn.connected(data),
                       groups=None, dm_users=None)
    sw.write_env(home / ".env", values)


def astrbot_disconnect(home: Path, spec: conn.Platform) -> None:
    """Take one platform out of the managed AstrBot and close its chats there."""
    from . import setup_wizard as sw

    data = AstrBotInstallation(home).root / "data"
    conn.remove_entry(data, spec.kind)
    connect_plugin(home)
    sw.write_astrbot_config(data, conn.scope(sw.read_astrbot_config(data), spec.kind, allow=False))


def release_from_astrbot(home: Path, spec: conn.Platform) -> bool:
    """One bot cannot be served twice: drop an AstrBot connection of the
    same platform, made before personagent connected it itself. True when
    AstrBot changed and needs a restart."""
    if spec.kind in conn.connected(AstrBotInstallation(home).root / "data"):
        astrbot_disconnect(home, spec)
        return True
    return False


def store(home: Path, spec: conn.Platform, values: dict) -> bool:
    """Save checked values; True when AstrBot gave the platform up."""
    direct_base.save_credentials(home, spec.kind, values)
    return release_from_astrbot(home, spec)


def remove(home: Path, spec: conn.Platform) -> bool:
    """Disconnect; True when AstrBot gave the platform up."""
    direct_base.remove_credentials(home, spec.kind)
    return release_from_astrbot(home, spec)


def clear_state(home: Path, kind: str) -> None:
    """What the ended login kept between runs."""
    direct.state_path(home, kind).unlink(missing_ok=True)


# ---------------------------------------------------------------- a personal account in a browser

#: `open_window(profile, url) -> the window's process or None`: an ordinary
#: browser window for the owner to sign in. Tests sign in on a stand-in site.
open_window: Callable[[Path, str], Optional[subprocess.Popen]] = web.open_sign_in
# How long a window that handed over to another process may take to show it holds the profile.
WINDOW_START_S = 15.0


def is_browser(spec: conn.Platform) -> bool:
    return spec.sign_in == "browser"


def browser_support() -> str:
    """NO_DRIVER or NO_BROWSER when this computer cannot work a website; "" when it can."""
    if importlib.util.find_spec("playwright") is None:
        return web.NO_DRIVER
    if web.find_browser() is None:
        return web.NO_BROWSER
    return ""


def support_command() -> str:
    """The command that adds browser support to this copy of personagent."""
    from .updates import how_to_add_browser_support

    return how_to_add_browser_support()


def profile_open(profile: Path) -> bool:
    """Whether a browser holds `profile`: its lock is taken while one runs."""
    if os.name == "nt":
        lock = profile / "lockfile"
        try:
            lock.unlink()
        except FileNotFoundError:
            return False
        except PermissionError:
            return True
        except OSError:
            return False
        return False
    try:
        target = os.readlink(profile / "SingletonLock")
    except OSError:
        return False
    pid = target.rpartition("-")[2]
    if not pid.isdigit():
        return True
    try:
        os.kill(int(pid), 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def close_window(profile: Path, window: Optional[subprocess.Popen]) -> None:
    """Close the sign-in window as its close button does, so the sign-in
    reaches the disk, then end whatever is left of it."""
    asked = False
    if os.name == "nt":
        # Without /F, taskkill asks a process's windows to close.
        script = ("Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and "
                  "$_.CommandLine.Contains('--user-data-dir') -and "
                  "$_.CommandLine.Contains($env:PERSONAGENT_PROFILE) -and "
                  "-not $_.CommandLine.Contains('--type=') } | ForEach-Object { "
                  "taskkill.exe /PID $_.ProcessId | Out-Null; if ($LASTEXITCODE -eq 0) { 'asked' } }")
        try:
            done = subprocess.run(["powershell", "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", script],
                                  env={**os.environ, "PERSONAGENT_PROFILE": str(profile)},
                                  stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=30)
            asked = "asked" in done.stdout
        except (OSError, subprocess.TimeoutExpired):
            pass
    elif window is not None and window.poll() is None:
        import signal

        try:
            os.killpg(window.pid, signal.SIGTERM)       # a browser closes cleanly on SIGTERM
            asked = True
        except (ProcessLookupError, PermissionError):
            pass
    if asked:
        deadline = time.monotonic() + web.CLOSE_S
        while time.monotonic() < deadline and profile_open(profile):
            time.sleep(0.2)
        # The window is gone a moment before the profile is written out.
        time.sleep(1.0)
    web.end_profile(profile, window)


def browser_sign_in(home: Path, spec: conn.Platform, *, done: Callable[[], bool] = lambda: False,
                    should_stop: Callable[[], bool] = lambda: False,
                    opened: Callable[[], None] = lambda: None,
                    checking: Callable[[], None] = lambda: None) -> dict:
    """Open a window for the owner to sign in, wait until `done()` or the
    window is closed, then read which account is signed in there; the values
    to store. Nothing here sees what the owner types in the window."""
    problem = browser_support()
    if problem:
        raise RuntimeError(problem)
    profile = web.profile_path(home, spec.kind)
    try:
        window = open_window(profile, direct.sign_in_url(spec.kind))
    except direct_base.Refused as exc:
        raise RuntimeError(str(exc) if str(exc) in NAMED_REFUSALS else web.NO_BROWSER) from None
    except OSError:
        raise RuntimeError(web.NO_BROWSER) from None
    opened()
    started, seen = time.monotonic(), False
    try:
        while not done():
            if should_stop():
                raise RuntimeError("cancelled")
            # The first process may hand the window to another and end: the profile's lock says it is open.
            showing = (window is not None and window.poll() is None) or profile_open(profile)
            seen = seen or showing
            if not showing and (seen or window is None or time.monotonic() - started > WINDOW_START_S):
                break
            time.sleep(0.3)
    finally:
        close_window(profile, window)
    checking()
    return check(home, spec, {})


def forget_sign_in(home: Path, kind: str) -> None:
    """A removed browser platform's sign-in (its browser profile) and what was
    learned about its pages. Run while nothing has the profile open."""
    profile = web.profile_path(home, kind)
    web.end_profile(profile)
    shutil.rmtree(profile, ignore_errors=True)
    profile.with_suffix(".learned.json").unlink(missing_ok=True)
