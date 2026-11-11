"""A conversation whose picture is still being read is not evicted when
other conversations push the connector cap: its line holds its place."""
from __future__ import annotations

import asyncio
from pathlib import Path

from persona_agent import transport

from test_turns import make_agent


async def test_a_conversation_reading_a_picture_survives_the_cap(tmp: Path, monkeypatch) -> None:
    monkeypatch.setattr(transport, "_MAX_CONNECTOR_CONVS", 2)
    agent = make_agent(tmp, message_debounce_sec=0)
    reading, release = asyncio.Event(), asyncio.Event()

    async def describe(url):
        reading.set()
        await release.wait()
        return "a cat on a sofa", None

    async def think(group_id, mode, text="", caller_override=None):
        return "PASS", "chat", ""

    agent._describe_image_keeping, agent._think = describe, think
    event = {"platform": "telegram", "conversation_type": "group", "conversation_id": "c1",
             "sender_id": "5", "sender_name": "Eve", "bot_id": "999000", "message_id": 1,
             "segments": [{"type": "image", "url": "https://img.example/cat.png"}]}
    task = asyncio.create_task(agent.handle_event(event))
    await reading.wait()
    # Its request is no longer counted: only the line keeps it.
    agent._connector_inflight.pop("telegram:c1", None)
    for i in range(5):
        agent._touch_connector_conv(f"telegram:other{i}")
    assert "telegram:c1" in agent._connector_conv_lru
    release.set()
    await task
    lines = [m["text"] for m in agent.buffers["telegram:c1"]]
    assert any("a cat on a sofa" in line for line in lines), lines
