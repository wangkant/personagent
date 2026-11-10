"""A reply that is only a sticker whose tag matches nothing in the library."""
from __future__ import annotations

from pathlib import Path

from helpers import check, isolated_agent

# The smallest GIF.
GIF = b"GIF89a\x01\x00\x01\x00\x00\x00\x00;"


def _library(agent, tags_by_file: dict) -> None:
    agent.stickers.dir.mkdir(parents=True, exist_ok=True)
    for n, (name, (tags, uses)) in enumerate(tags_by_file.items()):
        (agent.stickers.dir / name).write_bytes(GIF + bytes([n]))
        agent.stickers.entries[name] = {
            "md5": f"md5-{n}", "tags": tags, "meaning": "", "auto_tagged": True,
            "use_count": uses}


def _sink(agent) -> list:
    sent: list = []

    async def send(group_id, message):
        sent.append(message)
        return True

    agent._onebot_send_group = send
    return sent


async def test_an_unmatched_sticker_only_reply_sends_the_most_used_one(
        tmp: Path) -> None:
    """It logged "no match, skipping" and the called turn ended in silence."""
    agent = isolated_agent(tmp)
    _library(agent, {"a.gif": (["哈哈"], 3), "b.gif": (["哈哈"], 9),
                     "c.gif": (["哈哈"], 20)})
    agent.stickers.entries["c.gif"]["persona_fit"] = False
    sent = _sink(agent)
    result = await agent._send_group("g1", "[STICKER:smug]")
    check("one sticker goes out, and that is a success",
          result.success is True and len(sent) == 1
          and sent[0][-1]["type"] == "image", repr((result, sent)))
    check("the most used one that may be sent",
          result.sticker_files == ["b.gif"], repr(result.sticker_files))


async def test_a_reply_with_text_or_an_empty_library_sends_no_stand_in(
        tmp: Path) -> None:
    agent = isolated_agent(tmp)
    _library(agent, {"a.gif": (["哈哈"], 3)})
    sent = _sink(agent)
    result = await agent._send_group("g1", "fine [STICKER:smug]")
    check("the text goes out alone", result.success is True
          and sent == ["fine"] and result.sticker_files == [], repr(sent))

    empty = isolated_agent(tmp / "empty")
    sent = _sink(empty)
    result = await empty._send_group("g1", "[STICKER:smug]")
    check("with no tagged sticker nothing is sent", result.success is False
          and sent == [], repr((result, sent)))
