"""Pictures that reach the character through a connector or a direct platform
are collected as stickers when they came inline or are marked as stickers,
as QQ's always were, and the picture is never fetched a second time."""
from __future__ import annotations

import asyncio
import base64
import json
from pathlib import Path

from persona_agent.agent import Agent
from persona_agent.connector import current_sink

from helpers import check, isolated_agent

PNG = b"\x89PNG\r\n\x1a\n" + bytes(range(256)) * 2


def _agent(tmp: Path) -> tuple[Agent, list]:
    agent = isolated_agent(tmp)
    agent.stickers._llm_caller = None
    fetched: list = []
    real_fetch = agent._fetch_image_bytes

    async def counting_fetch(url: str):
        fetched.append(url)
        return await real_fetch(url)

    async def no_network(*_a, **_kw):
        raise AssertionError("no picture is downloaded in these tests")

    agent._fetch_image_bytes = counting_fetch
    agent._safe_get_bytes = no_network
    return agent, fetched


async def _read(agent: Agent, image: dict) -> str:
    token = current_sink.set(object())
    try:
        text = await agent._extract_text({
            "group_id": "telegram:-100", "user_id": "telegram:5",
            "message": [{"type": "image", "data": image}]})
    finally:
        current_sink.reset(token)
    await asyncio.gather(*list(agent._bg_tasks))
    return text


async def test_an_inline_sticker_from_a_direct_platform_is_collected_once(tmp: Path) -> None:
    agent, fetched = _agent(tmp)
    inline = "base64://" + base64.b64encode(PNG).decode()
    try:
        await _read(agent, {"file": inline, "sticker": True})
        check("one library entry", len(agent.stickers.entries) == 1,
              repr(agent.stickers.entries))
        check("the picture is read once", len(fetched) == 1, repr(len(fetched)))
        logged = [json.loads(line) for line in
                  agent.stickers.unknown_log.read_text(encoding="utf-8").splitlines()]
        check("the unknown-sticker log does not hold the picture itself",
              len(logged) == 1 and len(logged[0]["url"]) < 64, repr(logged)[:200])
    finally:
        await agent.aclose()


async def test_an_inline_picture_read_by_vision_is_not_read_again(tmp: Path) -> None:
    agent, fetched = _agent(tmp)
    inline = "base64://" + base64.b64encode(PNG).decode()

    async def describe_keeping(_url: str):
        return "a cat", PNG

    agent._describe_image_keeping = describe_keeping
    try:
        text = await _read(agent, {"file": inline})
        check("the description reaches the model", "a cat" in text, repr(text))
        check("one library entry", len(agent.stickers.entries) == 1)
        check("the downloaded picture is reused", fetched == [], repr(len(fetched)))
    finally:
        await agent.aclose()


async def test_a_linked_photo_off_qq_is_still_not_collected(tmp: Path) -> None:
    agent, fetched = _agent(tmp)
    try:
        await _read(agent, {"url": "https://cdn.example/photo.jpg"})
        check("no library entry", agent.stickers.entries == {})
        check("nothing fetched for it", fetched == [], repr(fetched))
    finally:
        await agent.aclose()
