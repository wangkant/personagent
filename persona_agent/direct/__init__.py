"""Platforms personagent connects to itself, without AstrBot.

Each module speaks one platform's own API, written from that platform's
documentation, and hands messages to the agent through the same connector
protocol every other connector uses (docs/connectors.md). The local page
stores credentials in `<home>/platforms/direct.json` and runs them all in one
process: `python -m persona_agent.direct --home <home>`.
"""
from __future__ import annotations

from pathlib import Path
from typing import Awaitable, Callable

from .base import Platform


def platform_for(kind: str, values: dict, home: Path) -> Platform:
    """A live connection for one stored platform."""
    if kind == "telegram":
        from .telegram import Telegram
        return Telegram(values)
    if kind == "discord":
        from .discord import Discord
        return Discord(values)
    if kind == "weixin_oc":
        from .weixin import Weixin
        return Weixin(values, state=state_path(home, kind))
    if kind == "qq_official":
        from .qq import QQ
        return QQ(values)
    if kind == "matrix":
        from .matrix import Matrix
        return Matrix(values, state=state_path(home, kind))
    if kind == "twitch":
        from .twitch import Twitch
        return Twitch(values, state=state_path(home, kind))
    if kind == "irc":
        from .irc import IRC
        return IRC(values)
    if kind == "zulip":
        from .zulip import Zulip
        return Zulip(values)
    if kind == "vk":
        from .vk import VK
        return VK(values)
    if kind == "stoat":
        from .stoat import Stoat
        return Stoat(values)
    raise ValueError(f"no direct connector for {kind!r}")


#: `sign_in(client, show, values) -> values to store`; `show` gets a QR or link text.
SignIn = Callable[..., Awaitable[dict]]


def sign_in_for(kind: str) -> tuple[SignIn, type[Exception]] | None:
    """The login flow of a platform that signs in by QR code or link, and the
    error it raises when the login does not finish; None for the others."""
    if kind == "qq_official":
        from .qq import BindFailed, bind
        return (lambda client, show, values: bind(client, show)), BindFailed
    if kind == "weixin_oc":
        from .weixin import LoginFailed, login
        return (lambda client, show, values: login(client, show)), LoginFailed
    if kind == "twitch":
        from .twitch import LoginFailed, login
        return login, LoginFailed
    return None


def state_path(home: Path, kind: str) -> Path:
    """What a platform keeps between runs (WeChat: its cursor and reply
    tokens). It belongs to one login and goes when that login does."""
    return home / "platforms" / "direct-state" / f"{kind}.json"


#: The catalog ids personagent connects without AstrBot.
KINDS = ("qq_official", "weixin_oc", "telegram", "discord",
         "matrix", "twitch", "irc", "zulip", "vk", "stoat")
