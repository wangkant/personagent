"""Connecting a platform personagent serves itself: the sign-in, the check
with the platform and the saving that the local page and
`personagent connect <platform>` share. Each failure is a RuntimeError whose
message is a short code (NAMED_REFUSALS, scan_failed, network_failed,
platform_rejected or cancelled), never a credential."""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Callable

from . import connections as conn
from . import direct
from .astrbot_install import AstrBotInstallation
from .direct import base as direct_base

# Refusals a direct platform names, which the page and the terminal explain one by one.
NAMED_REFUSALS = {"token_rejected", "app_rejected", "bot_in_use", "message_content_intent_off",
                  "intents_not_allowed", "session_expired", "bot_offline", "bot_banned",
                  "account_deactivated", "insecure_address", "homeserver_invalid", "owner_invalid",
                  "channel_not_found", "nick_in_use", "nick_invalid", "password_rejected",
                  "sasl_required", "long_poll_off", "message_events_off", "token_rights_missing",
                  "not_a_bot", "wrong_bot_type", "not_zulip_site"}


def stored(home: Path) -> list[str]:
    """The directly connected platforms, in catalog order."""
    saved = direct_base.load_credentials(home)
    return [p.kind for p in conn.PLATFORMS if p.kind in saved]


def check(home: Path, spec: conn.Platform, values: dict) -> None:
    """Ask the platform whether it accepts `values`; nothing is saved here."""
    platform = direct.platform_for(spec.kind, values, home)

    async def ask() -> None:
        try:
            await platform.check()
        finally:
            await platform.close()
    try:
        asyncio.run(ask())
    except direct_base.Refused as exc:
        raise RuntimeError(str(exc) if str(exc) in NAMED_REFUSALS else "platform_rejected") from None
    except ConnectionError:
        raise RuntimeError("network_failed") from None


def sign_in(spec: conn.Platform, values: dict, show: Callable[[str], None],
            should_stop: Callable[[], bool] = lambda: False) -> dict:
    """Run a platform's QR or link login, handing what it shows to `show`;
    the values to store."""
    import httpx

    flow = direct.sign_in_for(spec.kind)
    if flow is None:
        raise RuntimeError("platform_rejected")
    scan, failed = flow

    async def login() -> dict:
        async with httpx.AsyncClient() as client:
            task = asyncio.create_task(scan(client, show, values))
            while not task.done():
                if should_stop():
                    task.cancel()
                    raise RuntimeError("cancelled")
                await asyncio.sleep(0.3)
            return task.result()
    try:
        return asyncio.run(login())
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
