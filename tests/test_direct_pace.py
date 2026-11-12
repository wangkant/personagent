"""Direct connectors send a reply the way a person does: one message at a
time, each after the time it takes to type, with the typing sign up."""
from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from persona_agent.direct import base, discord, matrix, telegram

pytestmark = pytest.mark.typing_pace


def run(coro):
    return asyncio.run(coro)


def mock(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


class Chat(base.Platform):
    """A platform with a typing sign that logs what it does, in order."""
    kind = "telegram"

    def __init__(self, log: list, typing_fails: bool = False):
        super().__init__({})
        self.bot_id = "7000"
        self.log = log
        self.typing_fails = typing_fails

    async def typing(self, target):
        self.log.append(("typing", target))
        if self.typing_fails:
            raise ConnectionError("no sign today")

    async def send(self, target, items):
        sent = 0
        for item in items:
            await self.pace(target, item)
            self.log.append(("send", target, item.get("text") or item.get("type")))
            sent += 1
        return sent

    def target(self, delivery):
        return delivery["reply_handle"]


class Agent:
    def __init__(self, replies: list, log: list | None = None, takes: float = 0.0):
        self.replies, self.log, self.takes = replies, log, takes

    async def send_event(self, event):
        if self.takes:
            await asyncio.sleep(self.takes)
        if self.log is not None:
            self.log.append(("answered",))
        return {"owned": True, "replies": self.replies}


def bridge(platform, agent, tmp_path, log: list):
    made = base.Bridge(platform, agent, base.Status(tmp_path))

    async def sleep(seconds):
        log.append(("sleep", round(seconds, 2)))
        await asyncio.sleep(0)
    made._sleep = sleep
    return made


def texts(*lines: str) -> list[dict]:
    return [{"type": "text", "text": line} for line in lines]


def test_typing_time_follows_the_length_and_never_passes_seven_seconds(monkeypatch):
    monkeypatch.setattr(base.random, "uniform", lambda low, high: low)
    assert base.typing_delay("ok") == pytest.approx(2 / 6 + 0.4)
    assert base.typing_delay("x" * 30) == pytest.approx(5.4)
    assert base.typing_delay("x" * 500) == 7.0
    assert base.item_delay({"type": "text", "text": "  "}) == 0.0
    assert base.item_delay({"type": "image", "b64": "aGk="}) == pytest.approx(0.6)
    assert base.item_delay({"type": "image"}) == 0.0


def test_a_reply_goes_out_one_message_at_a_time_with_the_sign_up(tmp_path, monkeypatch):
    monkeypatch.setattr(base.random, "uniform", lambda low, high: low)
    log: list = []
    made = bridge(Chat(log), Agent(texts("on my way", "x" * 30)), tmp_path, log)

    async def scenario():
        await made.on_event({"sender_id": "42", "conversation_type": "group", "text": "who is in?"}, "-100")
        await asyncio.gather(*made._tasks)
    run(scenario())
    # 9 characters: 1.9 s. 30 characters: 5.4 s, so the sign is put up again after 4 s.
    assert log == [("typing", "-100"), ("sleep", 1.9), ("send", "-100", "on my way"),
                   ("typing", "-100"), ("sleep", 4.0), ("typing", "-100"), ("sleep", 1.4),
                   ("send", "-100", "x" * 30)]


def test_the_wait_for_the_agent_counts_as_typing_the_first_message(tmp_path, monkeypatch):
    monkeypatch.setattr(base.random, "uniform", lambda low, high: low)
    log: list = []
    made = bridge(Chat(log), None, tmp_path, log)
    assert run(made._send("-100", texts("on my way", "ok"), spent=30.0)) == 2
    assert log[0] == ("send", "-100", "on my way")
    assert log[1:] == [("typing", "-100"), ("sleep", 0.73), ("send", "-100", "ok")]


@pytest.mark.parametrize("event, shown", [
    ({"conversation_type": "dm"}, True),
    ({"conversation_type": "group", "addressed": True}, True),
    ({"conversation_type": "group"}, False),
])
def test_the_sign_goes_up_while_an_answer_to_the_character_is_written(tmp_path, monkeypatch, event, shown):
    monkeypatch.setattr(base.random, "uniform", lambda low, high: low)
    log: list = []
    made = bridge(Chat(log), Agent([], log, takes=0.05), tmp_path, log)

    async def scenario():
        await made.on_event({"sender_id": "42", "text": "hello", **event}, "42")
        await asyncio.gather(*made._tasks)
    run(scenario())
    before = log[:log.index(("answered",))]
    # A moment to read, then the sign, kept up until the agent answers.
    assert (before[:3] == [("sleep", 0.8), ("typing", "42"), ("sleep", 4.0)]) is shown
    assert shown or before == []
    # Nothing follows a silent answer: the sign fades by itself.
    assert log[-1] == ("answered",)


def test_a_typing_sign_that_fails_never_costs_the_reply(tmp_path, monkeypatch):
    monkeypatch.setattr(base.random, "uniform", lambda low, high: low)
    log: list = []
    made = bridge(Chat(log, typing_fails=True), Agent(texts("still here")), tmp_path, log)

    async def scenario():
        await made.on_event({"sender_id": "42", "conversation_type": "dm", "text": "hi"}, "42")
        await asyncio.gather(*made._tasks)
        return await made.deliver({"reply_handle": "42", "items": texts("morning")})
    assert run(scenario()) == ("sent", 1)
    assert [entry[2] for entry in log if entry[0] == "send"] == ["still here", "morning"]


def test_two_replies_to_one_chat_do_not_interleave(tmp_path, monkeypatch):
    monkeypatch.setattr(base.random, "uniform", lambda low, high: low)
    log: list = []
    made = bridge(Chat(log), None, tmp_path, log)

    async def scenario():
        await asyncio.gather(made._send("-100", texts("a1", "a2", "a3")),
                             made._send("-100", texts("b1", "b2", "b3")),
                             made._send("-200", texts("c1", "c2")))
    run(scenario())
    said = [entry[2] for entry in log if entry[0] == "send" and entry[1] == "-100"]
    assert said == ["a1", "a2", "a3", "b1", "b2", "b3"]
    assert [entry[2] for entry in log if entry[0] == "send" and entry[1] == "-200"] == ["c1", "c2"]
    # The other chat was not kept waiting for the first.
    assert log.index(("send", "-200", "c1")) < log.index(("send", "-100", "b1"))
    assert len(made._order) == 0


def test_telegram_shows_typing_before_each_message_in_the_same_topic(tmp_path, monkeypatch):
    monkeypatch.setattr(base.random, "uniform", lambda low, high: low)
    calls = []

    def handler(request):
        calls.append((request.url.path.rsplit("/", 1)[-1], json.loads(request.content or b"{}")))
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 1}})
    bot = telegram.Telegram({"telegram_token": "secret-token"}, client=mock(handler))
    made = bridge(bot, None, tmp_path, [])
    assert run(made.deliver({"reply_handle": "-100/7", "items": texts("one", "two")})) == ("sent", 2)
    assert [name for name, _ in calls] == ["sendChatAction", "sendMessage", "sendChatAction", "sendMessage"]
    assert calls[0][1] == {"chat_id": "-100", "action": "typing", "message_thread_id": 7}
    assert [body["text"] for name, body in calls if name == "sendMessage"] == ["one", "two"]


def test_discord_shows_typing_in_the_channel(tmp_path, monkeypatch):
    monkeypatch.setattr(base.random, "uniform", lambda low, high: low)
    calls = []

    def handler(request):
        calls.append((request.method, request.url.path))
        return httpx.Response(200, json={"id": "2"})
    bot = discord.Discord({"discord_token": "tok"}, client=mock(handler))
    made = bridge(bot, None, tmp_path, [])
    assert run(made.deliver({"reply_handle": "77", "items": texts("ok")})) == ("sent", 1)
    assert [(method, path.split("/channels/", 1)[1]) for method, path in calls] == [
        ("POST", "77/typing"), ("POST", "77/messages")]


def test_matrix_shows_typing_in_the_room_and_orders_by_room(tmp_path, monkeypatch):
    monkeypatch.setattr(base.random, "uniform", lambda low, high: low)
    calls = []

    def handler(request):
        calls.append((request.method, request.url.path, json.loads(request.content or b"{}")))
        return httpx.Response(200, json={"event_id": "$sent"})
    bot = matrix.Matrix({"matrix_homeserver": "https://example.org", "matrix_token": "tok",
                         "matrix_owner": "@kant:example.org"}, client=mock(handler))
    bot.bot_id = "@nova:example.org"
    assert bot.place(("!room:example.org", "", "$m1")) == bot.place("!room:example.org") == "!room:example.org"
    made = bridge(bot, None, tmp_path, [])

    async def scenario():
        return await made._send(("!room:example.org", "", "$m1"), texts("ok"))
    assert run(scenario()) == 1
    kinds = [("typing", body.get("typing")) if "/typing/" in path else ("send", None)
             for _method, path, body in calls]
    assert kinds == [("typing", True), ("send", None), ("typing", False)]
