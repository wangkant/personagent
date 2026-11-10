"""Evicting a connector conversation drops it from every per-conversation
table, including the follow-up passes, the opener stamps and the declined
retry stamps.

    python -m pytest tests/test_evict_tables.py
"""
from __future__ import annotations

from pathlib import Path

from persona_agent import channels

from helpers import check, isolated_agent

TABLES = ("_followup_passed", "_opener_sent_at", "_declined_retry_at")


def test_the_tables_exist_from_the_start(tmp: Path) -> None:
    a = isolated_agent(tmp)
    for name in TABLES:
        check(f"{name} is declared", isinstance(vars(a).get(name), dict))
    check("the lazy forms hand back the same tables",
          a._followup_table() is a._followup_passed
          and a._openers() is a._opener_sent_at)


def test_evicting_a_conversation_leaves_nothing_of_it(tmp: Path) -> None:
    a = isolated_agent(tmp)
    room, other = "telegram:-100", "telegram:-200"
    dm = channels.dm_routing_key("telegram:9")
    a._followup_table()[room] = (1.0, {"telegram:5"})
    a._followup_table()[other] = (1.0, {"telegram:6"})
    a._openers()[room] = 1.0
    a._openers()[channels.learning_key(dm)] = 1.0
    check("a declined draft is stamped", a._declined_retry_free(dm))
    a._declined_retry_free(channels.dm_routing_key("telegram:10"))

    a._evict_conversation(room)
    a._evict_conversation(dm)
    for name in TABLES:
        left = [k for k in vars(a)[name] if k in (room, dm, channels.learning_key(dm))]
        check(f"{name}: nothing of the evicted conversations", not left, str(left))
    check("other conversations keep theirs",
          other in a._followup_passed
          and channels.dm_routing_key("telegram:10") in a._declined_retry_at)
