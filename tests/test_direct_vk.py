"""The VK direct connector against a stand-in API: no network, no accounts."""
from __future__ import annotations

import asyncio
import base64
import json
import logging
from urllib.parse import parse_qs

import httpx
import pytest

from persona_agent.direct import base, vk

TOKEN = "vk1.a.secret-community-token"
GROUP = {"id": 77, "name": "Nova", "screen_name": "nova_bot"}
PNG = b"\x89PNG\r\n\x1a\n" + b"x" * 64


def run(coro):
    return asyncio.run(coro)


def mock(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def form(request) -> dict:
    return {k: v[0] for k, v in parse_qs(request.content.decode()).items()}


class FakeVK:
    """Answers API methods from a table and the long poll server from a queue."""

    def __init__(self, polls=(), **answers):
        self.answers = {"groups.getById": {"groups": [GROUP]},
                        "groups.getLongPollSettings": {"is_enabled": True, "events": {"message_new": 1}},
                        "groups.getLongPollServer": {"server": "https://lp.vk.test/wh77", "key": "k1", "ts": "10"},
                        "users.get": [{"id": 42, "first_name": "Alex", "last_name": "P"}],
                        "messages.send": 1,
                        "photos.getMessagesUploadServer": {"upload_url": "https://pu.vk.test/upload?sig=s"},
                        "photos.saveMessagesPhoto": [{"id": 5, "owner_id": -77, "access_key": "ak"}],
                        **answers}
        self.polls = list(polls)
        self.calls: list[tuple[str, dict]] = []
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        host = request.url.host
        if host == "api.vk.com":
            method = request.url.path.rsplit("/", 1)[-1]
            body = form(request)
            self.calls.append((method, body))
            answer = self.answers[method]
            if callable(answer):
                answer = answer(body)
            if isinstance(answer, httpx.Response):
                return answer
            if isinstance(answer, dict) and "error" in answer:
                return httpx.Response(200, json=answer)
            return httpx.Response(200, json={"response": answer})
        if host == "lp.vk.test":
            self.calls.append(("poll", dict(request.url.params)))
            answer = self.polls.pop(0) if self.polls else {"failed": 99}
            if answer is None:
                raise httpx.ConnectError("down", request=request)
            return httpx.Response(200, json=answer)
        if host == "pu.vk.test":
            self.calls.append(("upload", {}))
            assert b'name="photo"; filename="image.png"' in request.content
            return httpx.Response(200, json={"server": 1, "photo": "[{...}]", "hash": "h"})
        if host == "sun.userapi.test":
            return httpx.Response(200, content=PNG)
        raise AssertionError(f"unexpected host {host}")

    def sent(self) -> list[dict]:
        return [body for method, body in self.calls if method == "messages.send"]


def error(code, msg="") -> dict:
    return {"error": {"error_code": code, "error_msg": msg}}


def bot_for(fake: FakeVK) -> vk.VK:
    return vk.VK({"vk_token": TOKEN}, client=mock(fake))


def message(**fields) -> dict:
    msg = {"id": 0, "conversation_message_id": 31, "date": 1790000000, "peer_id": 2000000003,
           "from_id": 42, "text": "hello", "attachments": [], "fwd_messages": []}
    msg.update(fields)
    return msg


def update(msg: dict) -> dict:
    return {"type": "message_new", "event_id": "e", "group_id": 77,
            "object": {"message": msg, "client_info": {}}}


@pytest.fixture
def instant(monkeypatch):
    async def no_wait(seconds=0):
        await asyncio.sleep(0)
    real = asyncio.sleep
    monkeypatch.setattr(vk, "backoff_sleep", no_wait)
    monkeypatch.setattr(vk.asyncio, "sleep", lambda s: real(0))


# ---------------------------------------------------------------- check

def test_check_names_the_community_and_sends_the_token_only_in_the_body():
    fake = FakeVK()
    bot = bot_for(fake)
    assert run(bot.check()) == "Nova"
    assert bot.bot_id == "-77" and bot.group_id == 77
    method, body = fake.calls[0]
    assert method == "groups.getById" and body["v"] == vk.VERSION and body["access_token"] == TOKEN
    assert all(TOKEN not in str(r.url) for r in fake.requests)


def test_check_accepts_the_older_list_answer_of_groups_get_by_id():
    bot = bot_for(FakeVK(**{"groups.getById": [GROUP]}))
    assert run(bot.check()) == "Nova"


@pytest.mark.parametrize("answers, code", [
    ({"groups.getById": error(5, "User authorization failed")}, "token_rejected"),
    ({"groups.getById": error(100, "group_ids is undefined")}, "token_rejected"),
    ({"groups.getById": {"groups": [dict(GROUP, deactivated="banned")]}}, "bot_banned"),
    ({"groups.getLongPollSettings": error(15, "Access denied")}, "token_rights_missing"),
    ({"groups.getLongPollSettings": {"is_enabled": False, "events": {}}}, "long_poll_off"),
    ({"groups.getLongPollSettings": {"is_enabled": True, "events": {"message_new": 0}}}, "message_events_off"),
])
def test_check_turns_each_rejection_into_a_named_refusal(answers, code):
    with pytest.raises(base.Refused, match=code):
        run(bot_for(FakeVK(**answers)).check())


def test_check_reports_an_unreachable_or_failing_api_as_a_connection_error(instant):
    def down(request):
        raise httpx.ConnectError("no route", request=request)
    with pytest.raises(ConnectionError):
        run(vk.VK({"vk_token": TOKEN}, client=mock(down)).check())
    with pytest.raises(ConnectionError):
        run(bot_for(FakeVK(**{"groups.getById": httpx.Response(502)})).check())
    with pytest.raises(ConnectionError):
        run(bot_for(FakeVK(**{"groups.getById": error(10, "Internal server error")})).check())


def test_rate_limits_are_waited_out_then_retried(instant):
    answers = iter([error(6, "Too many requests per second"), error(9, "Flood control"), {"groups": [GROUP]}])
    fake = FakeVK(**{"groups.getById": lambda body: next(answers)})
    assert run(bot_for(fake).check()) == "Nova"
    assert [m for m, _ in fake.calls].count("groups.getById") == 3


# ---------------------------------------------------------------- run

def test_run_connects_and_hands_over_group_messages_and_dms(instant):
    mention = message(text="[club77|@nova_bot] как дела?", conversation_message_id=32)
    plain = message(text="just chatting about [id5|Bob]")
    dm = message(id=900, peer_id=42, conversation_message_id=1, text="hi there")
    reply = message(conversation_message_id=33, text="yes",
                    reply_message={"id": 0, "conversation_message_id": 30, "from_id": -77, "text": "ready?"})
    own = message(from_id=-77, text="my own words")
    other_bot = message(from_id=-5, text="another community")
    fake = FakeVK(polls=[{"ts": "11", "updates": [update(m) for m in (mention, plain, dm, reply, own, other_bot)]},
                         {"failed": 99}])
    bot = bot_for(fake)
    seen, states = [], []

    async def on_event(event, target):
        seen.append((event, target))
    with pytest.raises(ConnectionError):
        run(bot.run(on_event, lambda: states.append("connected")))
    assert states == ["connected"]
    poll = [p for m, p in fake.calls if m == "poll"][0]
    assert poll == {"act": "a_check", "key": "k1", "ts": "10", "wait": "25"}
    assert len(seen) == 4

    event, target = seen[0]
    assert target == "2000000003" and event["reply_handle"] == "2000000003"
    assert event["conversation_type"] == "group" and event["conversation_id"] == "2000000003"
    assert event["addressed"] is True and event["text"] == "как дела?"
    assert event["sender_id"] == "42" and event["sender_name"] == "Alex P"
    assert event["message_id"] == "32" and event["sent_at"] == 1790000000
    assert event["segments"] == [{"type": "mention", "user_id": "-77", "name": "nova_bot"},
                                 {"type": "text", "text": "как дела?"}]

    event = seen[1][0]
    assert event["addressed"] is False and event["text"] == "just chatting about @Bob"

    event, target = seen[2]
    assert event["conversation_type"] == "dm" and "conversation_id" not in event
    assert event["addressed"] is True and target == "42" and event["message_id"] == "900"

    event = seen[3][0]
    assert event["addressed"] is True
    assert event["segments"][0] == {"type": "reply", "message_id": "30", "text": "ready?",
                                    "sender_id": "-77", "sender_name": ""}
    # users.get is asked once per person, not once per message.
    assert [m for m, _ in fake.calls].count("users.get") == 1


def test_run_follows_the_failed_answers_of_the_long_poll_server(instant):
    fake = FakeVK(polls=[{"failed": 1, "ts": "20"}, {"ts": "21", "updates": []},
                         {"failed": 2}, {"ts": "22", "updates": []},
                         {"failed": 3}, {"failed": 99}])
    run_until_error(bot_for(fake))
    polls = [p for m, p in fake.calls if m == "poll"]
    # failed 1: new ts; failed 2: new key, same ts; failed 3: new key and ts.
    assert [p["ts"] for p in polls] == ["10", "20", "21", "21", "22", "10"]
    assert [m for m, _ in fake.calls].count("groups.getLongPollServer") == 3


def run_until_error(bot, on_event=None, connected=lambda: None):
    async def ignore(event, target):
        pass
    with pytest.raises(ConnectionError):
        run(bot.run(on_event or ignore, connected))


def test_a_dropped_poll_reports_dropped_then_connected_again(instant):
    fake = FakeVK(polls=[None, None, {"ts": "11", "updates": []}, {"failed": 99}])
    bot = bot_for(fake)
    states = []
    bot.dropped = lambda: states.append("connecting")
    run_until_error(bot, connected=lambda: states.append("connected"))
    assert states == ["connected", "connecting", "connecting", "connected"]


def test_a_revoked_token_or_disabled_long_poll_ends_the_run_with_a_refusal(instant):
    fake = FakeVK(**{"groups.getLongPollServer": error(5, "User authorization failed: invalid access_token")})
    with pytest.raises(base.Refused, match="token_rejected"):
        run(bot_for(fake).run(None, lambda: None))
    fake = FakeVK(**{"groups.getLongPollServer": error(100, "longpoll for this group is not enabled.")})
    with pytest.raises(base.Refused, match="long_poll_off"):
        run(bot_for(fake).run(None, lambda: None))


def test_being_added_to_a_chat_is_not_a_message_and_nothing_is_joined(instant):
    invite = message(text="", action={"type": "chat_invite_user", "member_id": -77})
    fake = FakeVK(polls=[{"ts": "11", "updates": [update(invite)]}, {"failed": 99}])
    seen = []

    async def on_event(event, target):
        seen.append(event)
    run_until_error(bot_for(fake), on_event)
    assert seen == []
    called = {m for m, _ in fake.calls}
    assert called <= {"groups.getById", "groups.getLongPollSettings", "groups.getLongPollServer", "poll"}


def test_photos_are_fetched_and_inlined_and_other_attachments_described():
    fake = FakeVK()
    bot = bot_for(fake)
    bot.group_id, bot.bot_id = 77, "-77"
    photo = {"type": "photo", "photo": {"sizes": [
        {"type": "s", "width": 75, "height": 50, "url": "https://sun.userapi.test/s.jpg"},
        {"type": "x", "width": 604, "height": 403, "url": "https://sun.userapi.test/x.jpg"}]}}
    event = run(bot.event(message(text="", peer_id=42, attachments=[
        photo, {"type": "audio_message"}, {"type": "sticker", "sticker": {"sticker_id": 9}}])))
    assert event["segments"][0] == {"type": "image", "b64": base64.b64encode(PNG).decode()}
    assert event["segments"][1] == {"type": "text", "text": "(sent a voice message)"}
    assert event["segments"][2]["type"] == "emoji"
    fetched = [str(r.url) for r in fake.requests if r.url.host == "sun.userapi.test"]
    assert fetched == ["https://sun.userapi.test/x.jpg"]


def test_a_photo_over_the_cap_is_described_not_inlined(monkeypatch):
    monkeypatch.setattr(vk, "MAX_INLINE_IMAGE_BYTES", 10)
    bot = bot_for(FakeVK())
    bot.group_id, bot.bot_id = 77, "-77"
    event = run(bot.event(message(text="", peer_id=42, attachments=[
        {"type": "photo", "photo": {"sizes": [{"width": 1, "height": 1, "url": "https://sun.userapi.test/a"}]}}])))
    assert event["segments"] == [{"type": "text", "text": "(sent a photo)"}]


# ---------------------------------------------------------------- send

def test_send_text_split_mention_and_image():
    fake = FakeVK()
    bot = bot_for(fake)
    bot.names["42"] = "Alex [P]"
    items = [{"type": "text", "text": "short"},
             {"type": "text", "text": "word " * 2000},
             {"type": "text", "text": "hey", "mention_user_id": "vk:42"},
             {"type": "text", "text": "  "},
             {"type": "image", "b64": base64.b64encode(PNG).decode()}]
    assert run(bot.send("2000000003", items)) == 4
    sent = fake.sent()
    assert sent[0]["message"] == "short" and sent[0]["peer_id"] == "2000000003"
    long_pieces = [s for s in sent if s.get("message", "").startswith("word")]
    assert len(long_pieces) >= 3 and all(len(s["message"]) <= vk.MAX_TEXT for s in long_pieces)
    assert any(s.get("message") == "[id42|Alex P] hey" for s in sent)
    assert sent[-1]["attachment"] == "photo-77_5_ak" and "message" not in sent[-1]
    assert len({s["random_id"] for s in sent}) == len(sent)
    methods = [m for m, _ in fake.calls]
    assert methods.index("photos.getMessagesUploadServer") < methods.index("upload") \
        < methods.index("photos.saveMessagesPhoto")


def test_send_stops_and_counts_when_vk_refuses_a_message():
    answers = iter([1, error(901, "Can't send messages for users without permission")])
    fake = FakeVK(**{"messages.send": lambda body: next(answers)})
    assert run(bot_for(fake).send("42", [{"type": "text", "text": "a"}, {"type": "text", "text": "b"},
                                         {"type": "text", "text": "c"}])) == 1


def test_target_uses_the_reply_handle():
    bot = bot_for(FakeVK())
    assert bot.target({"reply_handle": "2000000003"}) == "2000000003"
    assert bot.target({"reply_handle": "42"}) == "42"
    for bad in ({}, {"reply_handle": "not-a-peer"}):
        with pytest.raises(base.Unsupported):
            bot.target(bad)


# ---------------------------------------------------------------- secrecy

def test_no_credential_reaches_an_event_or_a_log(instant, caplog):
    photo = {"type": "photo", "photo": {"sizes": [{"width": 1, "height": 1, "url": "https://sun.userapi.test/p"}]}}
    fake = FakeVK(polls=[None, {"ts": "11", "updates": [update(message(attachments=[photo]))]}, {"failed": 99}],
                  **{"messages.send": error(902, "privacy")})
    bot = bot_for(fake)
    seen = []

    async def on_event(event, target):
        seen.append((event, target))
    with caplog.at_level(logging.DEBUG):
        run_until_error(bot, on_event)
        run(bot.send("42", [{"type": "text", "text": "x"}]))
    assert seen
    ours = "\n".join(r.getMessage() for r in caplog.records if r.name.startswith("personagent"))
    assert "vk: poll: ConnectError" in ours and "sending stopped" in ours
    dumped = json.dumps(seen, ensure_ascii=False) + caplog.text
    # The API takes the token in the body, so not even httpx's request log carries it.
    assert TOKEN not in dumped and "access_token" not in dumped and "key=k1" not in ours
