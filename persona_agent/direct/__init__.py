"""Platforms personagent connects to itself, without AstrBot.

Each module speaks one platform's own API, written from that platform's
documentation, and hands messages to the agent through the same connector
protocol every other connector uses (docs/connectors.md). The platforms in
WEB have no bot API for a personal account and are worked through their
websites in a browser the owner signed in to (browser.py). The local page
stores credentials in `<home>/platforms/direct.json` and runs them all in one
process: `python -m persona_agent.direct --home <home>`.
"""
from __future__ import annotations

import importlib
from pathlib import Path
from typing import Awaitable, Callable

from .base import Platform

#: Platforms worked through their website in a browser the owner signed in to:
#: kind -> (module, class). The class is a browser.WebPlatform.
WEB = {"bilibili": ("bilibili", "Bilibili"), "youtube": ("youtube", "YouTube")}


def web_class(kind: str) -> type:
    """The WebPlatform class of a browser-worked platform; importing it starts nothing."""
    module, name = WEB[kind]
    return getattr(importlib.import_module(f".{module}", __name__), name)


def sign_in_url(kind: str) -> str:
    """Where the owner of a browser-worked platform signs in."""
    return web_class(kind).sign_in_url


def platform_for(kind: str, values: dict, home: Path) -> Platform:
    """A live connection for one stored platform."""
    if kind in WEB:
        return web_class(kind)(values, home=home, state=state_path(home, kind))
    if kind == "telegram":
        from .telegram import Telegram
        return Telegram(values, state=state_path(home, kind))
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
    tokens; Telegram: its update offset). It belongs to one login and goes
    when that login does."""
    return home / "platforms" / "direct-state" / f"{kind}.json"


#: The catalog ids personagent connects without AstrBot.
KINDS = ("qq_official", "weixin_oc", "telegram", "discord",
         "matrix", "twitch", "irc", "zulip", "vk", "stoat", *WEB)
