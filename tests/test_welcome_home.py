"""The home view and Days, read from the page's own files."""
from __future__ import annotations

import re

from persona_agent import welcome


def _js():
    return (welcome.ASSETS / "welcome.js").read_text(encoding="utf-8")


def _body(js, head):
    found = re.search(r"\n" + re.escape(head) + r" \{\n(.*?)\n\}\n", js, re.S)
    assert found, head
    return found.group(1)


def test_the_home_view_keeps_the_chat_nodes_and_adds_the_stage():
    html = (welcome.ASSETS / "index.html").read_text(encoding="utf-8")
    chat = html[html.index('id="chat-view"'):html.index('id="activity-view"')]
    for node in ("messages", "chat-form", "message", "send", "chat-avatar", "forget-chat", "reset-chat",
                 "stage", "stage-avatar", "stage-pat", "stage-bubble", "stage-days", "stage-out", "stage-tell"):
        assert f'id="{node}"' in chat, node
    days = html[html.index('id="activity-view"'):html.index('id="platforms-view"')]
    memory = days[days.index('id="memory-panel"'):]
    assert 'id="learned-root"' in memory and 'id="activity-body"' in memory


def test_a_pat_asks_nothing_of_the_service():
    body = _body(_js(), "function pat()")
    assert "api(" not in body and "fetch(" not in body


def test_only_the_listed_players_are_embedded_and_nothing_is_written_as_html():
    js = _js()
    assert 'new Set(["www.youtube-nocookie.com", "www.youtube.com", "player.bilibili.com"])' in js
    assert 'url.protocol !== "https:"' in _body(js, "function playerUrl(address)")
    card = _body(js, "function contentCard(card)")
    assert "innerHTML" not in card and 'rel = "noopener noreferrer"' in card


def test_every_new_string_is_in_english_and_chinese():
    js = _js()
    zh, en = js.index("\n  zh: {"), js.index("\n  en: {")
    end = js.index("\n};", en)
    keys = set(re.findall(r'\bt\("((?:home|days|card|reader)\w*)"', js))
    keys |= {f"homePat{n}" for n in range(1, 6)}
    keys |= {f"daysKind_{k}" for k in ("saw", "diary", "learned", "remembered", "did", "arrived")}
    keys |= {f"homeWhy_{k}" for k in ("out", "asleep", "recent", "off", "no_model")}
    for key in keys:
        assert f"\n    {key}:" in js[zh:en], key
        assert f"\n    {key}:" in js[en:end], key
