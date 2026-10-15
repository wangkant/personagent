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
        return Weixin(values, state=home / "platforms" / "direct-state" / "weixin_oc.json")
    if kind == "qq_official":
        from .qq import QQ
        return QQ(values)
    raise ValueError(f"no direct connector for {kind!r}")


#: The catalog ids personagent connects without AstrBot.
KINDS = ("qq_official", "weixin_oc", "telegram", "discord")
