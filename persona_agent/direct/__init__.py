"""Platforms personagent connects to itself, without AstrBot.

Each module speaks one platform's own API, written from that platform's
documentation, and hands messages to the agent through the same connector
protocol every other connector uses (docs/connectors.md). The local page
stores credentials in `<home>/platforms/direct.json` and runs them all in one
process: `python -m persona_agent.direct --home <home>`.
"""
from __future__ import annotations

from pathlib import Path

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
    raise ValueError(f"no direct connector for {kind!r}")


def state_path(home: Path, kind: str) -> Path:
    """What a platform keeps between runs (WeChat: its cursor and reply
    tokens). It belongs to one login and goes when that login does."""
    return home / "platforms" / "direct-state" / f"{kind}.json"


#: The catalog ids personagent connects without AstrBot.
KINDS = ("qq_official", "weixin_oc", "telegram", "discord")
