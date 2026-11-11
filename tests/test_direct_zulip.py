"""Zulip against a stand-in server: no network, no accounts."""
from __future__ import annotations

import asyncio
import base64
import json
import logging
from urllib.parse import parse_qs

import httpx
import pytest

from persona_agent.direct import base, zulip

SITE = "https://chat.example.org"
KEY = "s3cret-api-key-123"
VALUES = {"zulip_site": SITE + "/", "zulip_email": "nova-bot@chat.example.org", "zulip_api_key": KEY}
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 32


def run(coro):
    return asyncio.run(coro)


def mock(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def ok(**fields) -> httpx.Response:
    return httpx.Response(200, json={"result": "success", "msg": "", **fields})


def error(status: int, code: str, **fields) -> httpx.Response:
    return httpx.Response(status, json={"result": "error", "msg": "no", "code": code, **fields})


def form(request) -> dict:
    return {k: v[0] for k, v in parse_qs(request.content.decode()).items()}


ME = {"user_id": 900, "full_name": "Nova", "email": "nova-bot@chat.example.org", "is_bot": True}


def bot(handler=lambda r: httpx.Response(500)) -> zulip.Zulip:
    platform = zulip.Zulip(VALUES, client=mock(handler))
    platform.bot_id, platform.full_name = "900", "Nova"
    return platform


def channel_message(**fields) -> dict:
    message = {"id": 55, "type": "stream", "stream_id": 12, "subject": "lunch", "sender_id": 42,
               "sender_full_name": "Alex", "sender_email": "alex@x", "timestamp": 1790000000,
               "content": "hello all", "display_recipient": "general"}
    message.update(fields)
    return message


def dm_message(*people, **fields) -> dict:
    message = {"id": 56, "type": "private", "sender_id": 42, "sender_full_name": "Alex",
               "timestamp": 1790000001, "content": "hi there", "subject": "",
               "display_recipient": [{"id": i, "full_name": f"u{i}", "email": f"u{i}@x"}
                                     for i in (people or (42, 900))]}
    message.update(fields)
    return message


# ---------------------------------------------------------------- check

def test_check_proves_the_bot_and_sends_basic_auth_to_the_site():
    seen = []

    def handler(request):
        seen.append(request)
        return ok(**ME)
    platform = zulip.Zulip(VALUES, client=mock(handler))
    assert run(platform.check()) == "Nova"
    assert platform.bot_id == "900"
    request = seen[0]
    assert str(request.url) == SITE + "/api/v1/users/me"
    expected = base64.b64encode(f"{VALUES['zulip_email']}:{KEY}".encode()).decode()
    assert request.headers["Authorization"] == "Basic " + expected
    assert KEY not in str(request.url)


@pytest.mark.parametrize("response, code", [
    (error(401, "UNAUTHORIZED"), "token_rejected"),
    (error(401, "INVALID_API_KEY"), "token_rejected"),
    (error(401, "USER_DEACTIVATED"), "account_deactivated"),
    (error(403, "REALM_DEACTIVATED"), "account_deactivated"),
    (httpx.Response(404, text="<html>not found</html>"), "not_zulip_site"),
    (ok(**dict(ME, is_bot=False)), "not_a_bot"),
])
def test_check_names_each_refusal(response, code):
    platform = zulip.Zulip(VALUES, client=mock(lambda r: response))
    with pytest.raises(base.Refused, match=code):
        run(platform.check())


def test_check_refuses_plain_http_except_on_this_computer():
    asked = []
    remote = zulip.Zulip(dict(VALUES, zulip_site="http://chat.example.org"),
                         client=mock(lambda r: asked.append(r) or ok(**ME)))
    with pytest.raises(base.Refused, match="insecure_address"):
        run(remote.check())
    assert not asked        # the key never left in clear text
    local = zulip.Zulip(dict(VALUES, zulip_site="http://localhost:9991"), client=mock(lambda r: ok(**ME)))
    assert run(local.check()) == "Nova"


def test_check_tells_an_outage_from_a_refusal():
    def down(request):
        raise httpx.ConnectError("down", request=request)
    with pytest.raises(ConnectionError):
        run(zulip.Zulip(VALUES, client=mock(down)).check())
    with pytest.raises(ConnectionError) as caught:
        run(zulip.Zulip(VALUES, client=mock(lambda r: httpx.Response(502, text="bad gateway"))).check())
    assert not isinstance(caught.value, base.Refused)


def test_rate_limits_are_waited_out(monkeypatch):
    waits = []

    async def record(seconds):
        waits.append(seconds)
    monkeypatch.setattr(zulip.asyncio, "sleep", record)
    answers = iter([error(429, "RATE_LIMIT_HIT", **{"retry-after": 2.5}),
                    httpx.Response(429, text="slow down", headers={"Retry-After": "1"}),
                    ok(**ME)])
    assert run(zulip.Zulip(VALUES, client=mock(lambda r: next(answers))).check()) == "Nova"
    assert waits == [2.5, 1.0]


# ---------------------------------------------------------------- events

def test_a_channel_message_is_a_group_event_keyed_by_channel_with_the_topic_in_the_handle():
    platform = bot()
    plain = run(platform.event(channel_message(), []))
    assert plain["conversation_type"] == "group" and plain["conversation_id"] == "12"
    assert plain["addressed"] is False and plain["reply_handle"] == "stream/12/lunch"
    assert plain["sender_id"] == "42" and plain["sender_name"] == "Alex"
    assert plain["message_id"] == "55" and plain["sent_at"] == 1790000000
    assert plain["segments"] == [{"type": "text", "text": "hello all"}]

    mentioned = run(platform.event(channel_message(content="@**Nova|900** how are you"), ["mentioned"]))
    assert mentioned["addressed"] is True and mentioned["text"] == "how are you"
    assert mentioned["segments"][0] == {"type": "mention", "user_id": "900", "name": "Nova"}

    wildcard = run(platform.event(channel_message(content="@**all** lunch?"),
                                  ["wildcard_mentioned", "stream_wildcard_mentioned"]))
    assert wildcard["addressed"] is False


def test_a_quote_of_the_bots_message_is_a_reply_to_it():
    platform = bot()
    content = ("@_**Nova|900** [said](https://chat.example.org/#narrow/channel/12-general/topic/lunch/near/50):\n"
               "```quote\npizza again\n```\nno thanks")
    event = run(platform.event(channel_message(content=content), []))
    assert event["addressed"] is True and event["text"] == "no thanks"
    assert event["segments"][0] == {"type": "reply", "message_id": "50", "text": "pizza again",
                                    "sender_id": "900", "sender_name": "Nova"}
    other = run(platform.event(channel_message(content=content.replace("Nova|900", "Sam|7")), []))
    assert other["addressed"] is False and other["segments"][0]["sender_id"] == "7"


def test_direct_messages_and_group_direct_messages():
    platform = bot()
    dm = run(platform.event(dm_message(), []))
    assert dm["conversation_type"] == "dm" and "conversation_id" not in dm
    assert dm["addressed"] is True and dm["reply_handle"] == "dm/42"
    group = run(platform.event(dm_message(900, 42, 7), []))
    assert group["conversation_type"] == "group" and group["conversation_id"] == "42,7,900"
    assert group["addressed"] is False and group["reply_handle"] == "dm/42,7"
    assert run(platform.event(dm_message(900, 42, 7), ["mentioned"]))["addressed"] is True


def test_the_bots_own_messages_and_empty_ones_are_ignored():
    platform = bot()
    assert run(platform.event(channel_message(sender_id=900), ["mentioned"])) is None
    assert run(platform.event(channel_message(content="   "), [])) is None


def test_uploaded_images_are_inlined_and_their_links_never_passed_on():
    asked = []

    def handler(request):
        asked.append(request)
        if request.url.path == "/api/v1/user_uploads/2/ab/cd/cat.png":
            return ok(url="/user_uploads/temporary/xyz/cat.png")
        if request.url.path == "/user_uploads/temporary/xyz/cat.png":
            return httpx.Response(200, content=PNG)
        return httpx.Response(404)
    platform = bot(handler)
    event = run(platform.event(channel_message(
        content="look [cat.png](/user_uploads/2/ab/cd/cat.png) and [notes.pdf](/user_uploads/2/ef/gh/notes.pdf)"),
        []))
    assert event["text"] == "look and"
    kinds = [s["type"] for s in event["segments"]]
    assert kinds == ["text", "image", "media"]
    assert base64.b64decode(event["segments"][1]["b64"]) == PNG
    assert event["segments"][2] == {"type": "media", "kind": "file", "name": "notes.pdf"}
    assert "user_uploads" not in json.dumps(event)
    # The short-lived link is fetched without the key.
    assert "Authorization" not in asked[1].headers


def test_an_image_too_big_is_described_instead():
    def handler(request):
        if request.url.path.startswith("/api/"):
            return ok(url="/user_uploads/temporary/big.png")
        return httpx.Response(200, content=b"0" * (base.MAX_INLINE_IMAGE_BYTES + 1))
    event = run(bot(handler).event(channel_message(content="[big.png](/user_uploads/2/a/b/big.png)"), []))
    assert event["segments"] == [{"type": "media", "kind": "photo"}]


# ---------------------------------------------------------------- run

class Server:
    """A Zulip that hands out a queue and replays event batches."""

    def __init__(self, batches):
        self.batches = list(batches)
        self.registered = []
        self.polls = []
        self.calls = []

    def __call__(self, request):
        path = request.url.path
        self.calls.append((request.method, path))
        if path.startswith("/api/v1/user_uploads/"):
            return ok(url="/user_uploads/temporary/t/p.png")
        if path.startswith("/user_uploads/temporary/"):
            return httpx.Response(200, content=PNG)
        if path == "/api/v1/users/me":
            return ok(**ME)
        if path == "/api/v1/register":
            self.registered.append(form(request))
            return ok(queue_id=f"q{len(self.registered)}", last_event_id=-1,
                      event_queue_longpoll_timeout_seconds=90, max_message_length=10000,
                      zulip_feature_level=300)
        if path == "/api/v1/events" and request.method == "GET":
            self.polls.append(dict(request.url.params))
            answer = self.batches.pop(0) if self.batches else error(401, "UNAUTHORIZED")
            if callable(answer):
                return answer(request)
            return answer
        if path == "/api/v1/events" and request.method == "DELETE":
            return ok()
        return httpx.Response(404)


def instant(monkeypatch):
    async def no_wait(attempt):
        await asyncio.sleep(0)
    monkeypatch.setattr(zulip, "backoff_sleep", no_wait)


def test_run_registers_for_messages_and_hands_them_over(monkeypatch):
    instant(monkeypatch)
    server = Server([ok(events=[
        {"id": 0, "type": "heartbeat"},
        {"id": 1, "type": "message", "flags": ["mentioned"],
         "message": channel_message(content="@**Nova|900** hi")},
        {"id": 2, "type": "message", "flags": [], "message": channel_message(sender_id=900, content="me")},
        {"id": 3, "type": "message", "flags": ["read"], "message": dm_message()}])])
    platform = zulip.Zulip(VALUES, client=mock(server))
    seen, states = [], []

    async def on_event(event, target):
        seen.append((event, target))
    with pytest.raises(base.Refused, match="token_rejected"):
        run(platform.run(on_event, lambda: states.append("connected")))
    register = server.registered[0]
    assert json.loads(register["event_types"]) == ["message"]
    assert register["all_public_streams"] == "false" and register["apply_markdown"] == "false"
    assert states == ["connected"]
    assert [t for _, t in seen] == ["stream/12/lunch", "dm/42"]
    assert seen[0][0]["addressed"] and seen[1][0]["conversation_type"] == "dm"
    assert server.polls[0] == {"queue_id": "q1", "last_event_id": "-1"}
    assert server.polls[1]["last_event_id"] == "3"


def test_a_lost_queue_is_registered_again_and_a_drop_reconnects(monkeypatch):
    instant(monkeypatch)

    def down(request):
        raise httpx.ConnectError("down", request=request)
    server = Server([error(400, "BAD_EVENT_QUEUE_ID", queue_id="q1"),
                     down,
                     ok(events=[]),
                     error(401, "USER_DEACTIVATED")])
    platform = zulip.Zulip(VALUES, client=mock(server))
    states = []
    platform.dropped = lambda: states.append("connecting")
    with pytest.raises(base.Refused, match="account_deactivated"):
        run(platform.run(None, lambda: states.append("connected")))
    assert len(server.registered) == 2
    assert [p["queue_id"] for p in server.polls] == ["q1", "q2", "q2", "q2"]
    assert states == ["connected", "connecting", "connected"]


def test_a_bot_that_may_not_read_is_a_named_refusal():
    def handler(request):
        if request.url.path.endswith("/users/me"):
            return ok(**ME)
        return error(400, "BAD_REQUEST")
    with pytest.raises(base.Refused, match="wrong_bot_type"):
        run(zulip.Zulip(VALUES, client=mock(handler)).run(None, lambda: None))


def test_the_bot_never_joins_anything_on_its_own(monkeypatch):
    instant(monkeypatch)
    server = Server([ok(events=[{"id": 1, "type": "subscription", "op": "add"}])])
    with pytest.raises(base.Refused):
        run(zulip.Zulip(VALUES, client=mock(server)).run(None, lambda: None))
    # Only reading calls: no subscribe, no message, nothing else.
    assert server.registered[0]["all_public_streams"] == "false"
    assert set(server.calls) == {("GET", "/api/v1/users/me"), ("POST", "/api/v1/register"),
                                 ("GET", "/api/v1/events")}


# ---------------------------------------------------------------- send

def poster(posts, uploads=None):
    def handler(request):
        if request.url.path == "/api/v1/user_uploads":
            uploads.append(request.content)
            return ok(url="/user_uploads/2/zz/image.png", filename="image.png")
        posts.append(form(request))
        return ok(id=1)
    return handler


def test_send_text_to_a_topic_and_mentions_by_name_and_id():
    posts = []
    platform = bot(poster(posts))
    platform.names["42"] = "Alex"
    items = [{"type": "text", "text": "hi", "mention_user_id": "zulip:42"}, {"type": "text", "text": "  "}]
    assert run(platform.send("stream/12/lunch/menu", items)) == 1
    assert posts == [{"type": "stream", "to": "12", "topic": "lunch/menu", "content": "@**Alex|42** hi"}]


def test_send_splits_long_text_and_reaches_direct_messages():
    posts = []
    platform = bot(poster(posts))
    platform.max_text = 500
    assert run(platform.send("dm/42,7", [{"type": "text", "text": "word " * 300}])) == 1
    assert len(posts) > 1 and all(len(p["content"]) <= 500 for p in posts)
    assert all(p["type"] == "direct" and json.loads(p["to"]) == [42, 7] for p in posts)
    platform.feature_level = 100
    run(platform.send("dm/42", [{"type": "text", "text": "old server"}]))
    assert posts[-1]["type"] == "private"


def test_send_uploads_an_image_then_links_it():
    posts, uploads = [], []
    platform = bot(poster(posts, uploads))
    assert run(platform.send("dm/42", [{"type": "image", "b64": base64.b64encode(PNG).decode()}])) == 1
    assert b'name="filename"' in uploads[0] and PNG in uploads[0]
    assert posts[0]["content"] == "[image.png](/user_uploads/2/zz/image.png)"


def test_send_reports_what_went_out_when_it_fails_midway():
    calls = []

    def handler(request):
        calls.append(1)
        return ok(id=1) if len(calls) != 2 else error(400, "STREAM_DOES_NOT_EXIST")
    items = [{"type": "text", "text": t} for t in ("one", "two", "three")]
    assert run(bot(handler).send("stream/12/x", items)) == 1


def test_target_comes_from_the_reply_handle():
    platform = bot()
    assert platform.target({"reply_handle": "stream/12/lunch"}) == "stream/12/lunch"
    assert platform.target({"reply_handle": "dm/42"}) == "dm/42"
    for delivery in ({}, {"reply_handle": "elsewhere"}, {"conversation_id": "12"}):
        with pytest.raises(base.Unsupported):
            platform.target(delivery)


# ---------------------------------------------------------------- secrecy

def test_no_credential_reaches_an_event_or_a_log(monkeypatch, caplog):
    instant(monkeypatch)

    def down(request):
        raise httpx.ConnectError(f"cannot reach {request.url}", request=request)

    server = Server([down, ok(events=[{"id": 1, "type": "message", "flags": [], "message": dm_message(
        content="[p.png](/user_uploads/2/a/b/p.png)")}])])
    seen = []

    async def on_event(event, target):
        seen.append(event)
    caplog.set_level(logging.DEBUG)
    platform = zulip.Zulip(VALUES, client=mock(server))
    with pytest.raises(base.Refused):
        run(platform.run(on_event, lambda: None))
    run(bot(lambda r: error(500, "BAD_REQUEST")).send("dm/42", [{"type": "text", "text": "x"}]))
    assert seen and seen[0]["segments"][0]["type"] == "image"
    secret_forms = (KEY, base64.b64encode(f"{VALUES['zulip_email']}:{KEY}".encode()).decode())
    assert caplog.records
    for secret in secret_forms:
        assert secret not in json.dumps(seen)
        assert secret not in caplog.text
