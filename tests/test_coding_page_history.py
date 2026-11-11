"""What the character says through a coding assistant, while no page is open,
is in the page's chat when the page opens next."""
from __future__ import annotations

from pathlib import Path

import pytest

from persona_agent import coding, welcome


@pytest.fixture
def home(tmp_path: Path, monkeypatch) -> Path:
    monkeypatch.setattr(coding, "_page", lambda _home: None)
    monkeypatch.setattr(coding, "_service", lambda _home: "http://127.0.0.1:1")
    return tmp_path


def _replying(monkeypatch, items: list[dict], events: list) -> None:
    class Connector:
        def __init__(self, *args, **kwargs):
            pass

        async def send_event(self, event):
            events.append(event)
            return {"replies": items}

    monkeypatch.setattr(welcome, "_connector_type", lambda: Connector)


def _page_history(home: Path) -> list[dict]:
    return welcome.Workspace(home).history()["messages"]


def test_talk_through_the_service_lands_in_the_page_chat(monkeypatch, home):
    events: list = []
    _replying(monkeypatch, [{"type": "text", "text": "hello back"},
                            {"type": "text", "text": "how is the code?"}], events)
    reply = coding.Character(home).talk("hello")
    assert reply == "hello back\nhow is the code?"
    shown = _page_history(home)
    assert [(m["role"], m["text"]) for m in shown] == [
        ("user", "hello"), ("assistant", "hello back"), ("assistant", "how is the code?")]
    assert all(m.get("via") == "coding" for m in shown)
    assert [m["seq"] for m in shown] == [1, 2, 3]
    assert events[0]["conversation_id"] == welcome.Workspace(home)._conversation


def test_a_stop_hook_remark_lands_without_the_cue(monkeypatch, home):
    _replying(monkeypatch, [{"type": "text", "text": "nice work"}], [])
    coding.Character(home).talk("hi")
    coding._send_to_service(home, "http://127.0.0.1:1", "They are working ...",
                            timeout_s=5, proactive=True)
    shown = _page_history(home)
    assert [(m["role"], m["text"]) for m in shown][-1] == ("assistant", "nice work")
    assert not any("They are working" in m["text"] for m in shown)
    assert [m["seq"] for m in shown] == [1, 2, 3]


def test_a_pass_adds_only_what_was_said(monkeypatch, home):
    _replying(monkeypatch, [], [])
    coding.Character(home).talk("anyone there?")
    assert [(m["role"], m["text"]) for m in _page_history(home)] == [("user", "anyone there?")]
