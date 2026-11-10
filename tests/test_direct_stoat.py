"""Stoat (formerly Revolt) against a stand-in API, file server and events socket."""
from __future__ import annotations

import asyncio
import base64
import json
import logging

import httpx
import pytest

from persona_agent.direct import base, stoat

TOKEN = "SECRET-BOT-TOKEN-123"
API = "https://api.stoat.test"
AUTUMN = "https://cdn.stoat.test"
BOT, OWNER, ALEX, STRANGER = "01BOT", "01OWNER", "01ALEX", "01STRANGER"
# 2026-01-01T00:00:00Z as a ULID time prefix.
MID = "01KDVDNA00" + "0" * 16


def run(coro):
    return asyncio.run(coro)


def root():
    return {"revolt": "0.16.3", "ws": "wss://events.stoat.test",
            "features": {"autumn": {"enabled": True, "url": AUTUMN},
                         "limits": {"default": {"message_length": 2000}}}}


class Server:
    """The REST API and Autumn, recording what was asked of them."""

    def __init__(self, **overrides):
        self.requests: list[httpx.Request] = []
        self.posts: list[dict] = []
        self.overrides = overrides
        self.members = {"S1": {OWNER}, "S2": {STRANGER}}

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path
        if path in self.overrides:
            answer = self.overrides[path]
            return answer(request) if callable(answer) else answer
        if request.url.host == "cdn.stoat.test":
            if request.method == "POST":
                return httpx.Response(200, json={"id": "FILE1"})
            return httpx.Response(200, content=b"\x89PNGpicture")
        if path == "/":
            return httpx.Response(200, json=root())
        if request.headers.get("x-bot-token") != TOKEN:
            return httpx.Response(401, json={"type": "InvalidSession"})
        if path == "/users/@me":
            return httpx.Response(200, json={"_id": BOT, "username": "nova", "display_name": "Nova",
                                             "bot": {"owner": OWNER}})
        if path.startswith("/users/"):
            uid = path.rsplit("/", 1)[1]
            return httpx.Response(200, json={"_id": uid, "username": uid.lower()[2:],
                                             **({"bot": {"owner": "x"}} if uid == "01OTHERBOT" else {})})
        if path.startswith("/servers/"):
            _, _, server, _, member = path.split("/")
            if member in self.members.get(server, set()):
                return httpx.Response(200, json={"_id": {"server": server, "user": member}})
            return httpx.Response(404, json={"type": "NotFound"})
        if path == "/channels/C9/messages/M0":
            return httpx.Response(200, json={"_id": "M0", "author": BOT, "content": "earlier"})
        if path.startswith("/channels/") and path.endswith("/messages") and request.method == "POST":
            self.posts.append(json.loads(request.content))
            return httpx.Response(200, json={"_id": f"SENT{len(self.posts)}", "author": BOT})
        if path.startswith("/channels/"):
            return httpx.Response(404, json={"type": "NotFound"})
        return httpx.Response(404, json={"type": "NotFound"})


def bot_with(server: Server, token: str = TOKEN, connect=None, api: str = API) -> stoat.Stoat:
    return stoat.Stoat({"stoat_token": token, "stoat_api": api},
                       client=httpx.AsyncClient(transport=httpx.MockTransport(server)), connect=connect)


CHANNELS = [{"_id": "C1", "channel_type": "TextChannel", "server": "S1", "name": "general"},
            {"_id": "C2", "channel_type": "TextChannel", "server": "S2", "name": "elsewhere"},
            {"_id": "C9", "channel_type": "TextChannel", "server": "S1", "name": "chat"},
            {"_id": "D1", "channel_type": "DirectMessage", "active": True, "recipients": [BOT, STRANGER]},
            {"_id": "G1", "channel_type": "Group", "name": "pals", "owner": OWNER,
             "recipients": [OWNER, ALEX, BOT]},
            {"_id": "G2", "channel_type": "Group", "name": "strangers", "owner": STRANGER,
             "recipients": [STRANGER, BOT]}]


def ready():
    return {"type": "Ready", "users": [{"_id": ALEX, "username": "alex", "display_name": "Alex"}],
            "channels": [dict(c) for c in CHANNELS], "servers": []}


def message(channel="C1", author=ALEX, content="hello", **fields):
    return {"type": "Message", "_id": MID, "channel": channel, "author": author, "content": content, **fields}


class Socket:
    """An events connection that replays frames, then ends."""

    def __init__(self, frames):
        self.frames = [json.dumps(f) for f in frames]
        self.sent: list[dict] = []
        self.closed = False

    async def send(self, data):
        self.sent.append(json.loads(data))

    async def close(self, code=1000):
        self.closed = True

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self.frames:
            raise StopAsyncIteration
        return self.frames.pop(0)


async def ready_bot(server: Server) -> stoat.Stoat:
    bot = bot_with(server)
    await bot.check()
    await bot._frame(ready(), {"ready": False}, asyncio.Event(), None, lambda: None)
    return bot


# ---------------------------------------------------------------- check

def test_check_proves_the_token_and_learns_the_bot_and_its_owner():
    server = Server()
    bot = bot_with(server)
    assert run(bot.check()) == "Nova"
    assert bot.bot_id == BOT and bot.owner_id == OWNER
    me = next(r for r in server.requests if r.url.path == "/users/@me")
    assert me.headers["x-bot-token"] == TOKEN and TOKEN not in str(me.url)
    # The root it read named the socket: nothing about hosts is hard-coded.
    assert bot.root["ws"] == "wss://events.stoat.test"


def test_check_refuses_a_bad_token_a_person_token_and_a_plain_http_address():
    with pytest.raises(base.Refused, match="token_rejected"):
        run(bot_with(Server(), token="wrong").check())
    person = Server(**{"/users/@me": httpx.Response(200, json={"_id": "01ME", "username": "me"})})
    with pytest.raises(base.Refused, match="token_rejected"):
        run(bot_with(person).check())
    with pytest.raises(base.Refused, match="insecure_address"):
        run(bot_with(Server(), api="http://chat.example.org/api").check())
    # A self-hosted instance on this machine may use plain http.
    assert run(bot_with(Server(), api="http://localhost:14702").check()) == "Nova"


def test_check_reports_an_unreachable_or_wrong_address_as_a_connection_error():
    def down(request):
        raise httpx.ConnectError("no route", request=request)
    with pytest.raises(ConnectionError):
        run(bot_with(down).check())
    with pytest.raises(ConnectionError):
        run(bot_with(Server(**{"/": httpx.Response(200, json={"hello": "not stoat"})})).check())
    with pytest.raises(ConnectionError):
        run(bot_with(Server(**{"/users/@me": httpx.Response(500, json={"type": "InternalError"})})).check())


def test_rest_waits_out_a_429_in_milliseconds(monkeypatch):
    waits = []

    async def record(seconds):
        waits.append(seconds)
    monkeypatch.setattr(stoat.asyncio, "sleep", record)
    answers = iter([httpx.Response(429, json={"retry_after": 1500}),
                    httpx.Response(200, json={"_id": BOT, "username": "nova", "bot": {"owner": OWNER}},
                                   headers={"x-ratelimit-remaining": "0", "x-ratelimit-reset-after": "800"})])
    bot = bot_with(Server(**{"/users/@me": lambda r: next(answers)}))
    assert run(bot.check()) == "nova"
    assert waits == [1.5, 0.8]


# ---------------------------------------------------------------- events

def test_a_group_message_becomes_a_group_event_and_a_mention_addresses_the_bot():
    server = Server()
    bot = run(ready_bot(server))
    event, target = run(bot.event(message()))
    assert event["conversation_type"] == "group" and event["conversation_id"] == "C1"
    assert event["addressed"] is False and event["sender_id"] == ALEX and event["sender_name"] == "Alex"
    assert event["message_id"] == MID and event["reply_handle"] == "C1" and target == f"C1/{MID}"
    assert event["sent_at"] == 1767225600
    assert event["segments"] == [{"type": "text", "text": "hello"}]
    mention, _ = run(bot.event(message(content=f"<@{BOT}> are you there", mentions=[BOT])))
    assert mention["addressed"] is True and mention["text"] == "are you there"
    assert mention["segments"][0] == {"type": "mention", "user_id": BOT, "name": ""}
    called, _ = run(bot.event(message(content="Nova, how was your day?")))
    assert called["addressed"] is True
    novel, _ = run(bot.event(message(content="Novalis wrote poems")))
    assert novel["addressed"] is False


def test_a_dm_is_addressed_and_has_no_conversation_id():
    bot = run(ready_bot(Server()))
    event, target = run(bot.event(message(channel="D1", author=STRANGER, content="hi")))
    assert event["conversation_type"] == "dm" and "conversation_id" not in event
    assert event["addressed"] is True and event["reply_handle"] == "D1" and target == f"D1/{MID}"


def test_a_reply_to_the_bot_is_addressed_and_carries_the_quoted_text():
    bot = run(ready_bot(Server()))
    event, _ = run(bot.event(message(channel="C9", content="why?", replies=["M0"])))
    assert event["addressed"] is True
    assert event["segments"][0] == {"type": "reply", "message_id": "M0", "text": "earlier",
                                    "sender_id": BOT, "sender_name": "Nova"}


def test_its_own_and_other_bots_and_system_messages_are_ignored():
    bot = run(ready_bot(Server()))
    assert run(bot.event(message(author=BOT))) is None
    assert MID in bot.mine
    assert run(bot.event(message(author="01OTHERBOT"))) is None
    assert run(bot.event(message(system={"type": "text", "content": "x"}))) is None
    assert run(bot.event(message(webhook={"name": "hook"}))) is None


def test_rooms_the_owner_is_not_in_are_ignored_so_strangers_cannot_spend_the_budget():
    server = Server()
    bot = run(ready_bot(server))
    assert run(bot.event(message(channel="C2", mentions=[BOT], content=f"<@{BOT}> hi"))) is None
    assert run(bot.event(message(channel="G2", author=STRANGER, mentions=[BOT]))) is None
    group, _ = run(bot.event(message(channel="G1")))
    assert group["conversation_id"] == "G1"
    # The answer is cached, and the owner joining later opens the room.
    asked = sum(r.url.path.startswith("/servers/S2") for r in server.requests)
    run(bot.event(message(channel="C2")))
    assert sum(r.url.path.startswith("/servers/S2") for r in server.requests) == asked
    run(bot._frame({"type": "ServerMemberJoin", "id": "S2", "user": OWNER}, {}, None, None, None))
    assert run(bot.event(message(channel="C2")))[0]["conversation_id"] == "C2"
    run(bot._frame({"type": "ChannelGroupJoin", "id": "G2", "user": OWNER}, {}, None, None, None))
    assert run(bot.event(message(channel="G2", author=STRANGER))) is not None


def test_an_unknown_channel_is_fetched_once_and_cached():
    server = Server(**{"/channels/D7": httpx.Response(200, json={
        "_id": "D7", "channel_type": "DirectMessage", "recipients": [BOT, ALEX]})})
    bot = run(ready_bot(server))
    assert run(bot.event(message(channel="D7")))[0]["conversation_type"] == "dm"
    run(bot.event(message(channel="D7")))
    assert sum(r.url.path == "/channels/D7" for r in server.requests) == 1


def test_images_are_fetched_without_the_token_and_inlined():
    server = Server()
    bot = run(ready_bot(server))
    picture = {"_id": "F1", "tag": "attachments", "filename": "a.png", "content_type": "image/png",
               "size": 11, "metadata": {"type": "Image"}}
    huge = dict(picture, _id="F2", size=base.MAX_INLINE_IMAGE_BYTES + 1)
    doc = {"_id": "F3", "tag": "attachments", "filename": "deck.pdf", "content_type": "application/pdf",
           "size": 10}
    event, _ = run(bot.event(message(content="", attachments=[picture, huge, doc])))
    assert event["segments"] == [
        {"type": "image", "b64": base64.b64encode(b"\x89PNGpicture").decode()},
        {"type": "text", "text": "(sent a photo)"},
        {"type": "text", "text": "(sent a file: deck.pdf)"}]
    fetch = next(r for r in server.requests if r.url.host == "cdn.stoat.test")
    assert str(fetch.url) == f"{AUTUMN}/attachments/F1" and "x-bot-token" not in fetch.headers


# ---------------------------------------------------------------- run

def test_run_authenticates_by_frame_reports_connected_and_hands_messages_over(monkeypatch):
    async def instant(attempt):
        await asyncio.sleep(0)
    monkeypatch.setattr(stoat, "backoff_sleep", instant)
    server = Server()
    sockets = [Socket([{"type": "Authenticated"}, {"type": "Bulk", "v": [ready()]},
                       message(content=f"<@{BOT}> hey", mentions=[BOT]),
                       message(channel="D1", author=STRANGER, content="psst")])]
    urls = []

    async def connect(url):
        urls.append(url)
        if not sockets:
            raise asyncio.CancelledError
        return sockets.pop(0)
    first = sockets[0]
    bot = bot_with(server, connect=connect)
    seen, states = [], []

    async def on_event(event, target):
        seen.append((event, target))
    with pytest.raises(asyncio.CancelledError):
        run(bot.run(on_event, lambda: states.append("connected")))
    assert urls[0] == "wss://events.stoat.test?version=1&format=json" and TOKEN not in urls[0]
    assert first.sent[0] == {"type": "Authenticate", "token": TOKEN}
    assert states == ["connected"]
    assert [e["conversation_type"] for e, _ in seen] == ["group", "dm"]
    assert seen[0][0]["addressed"] and seen[0][1] == f"C1/{MID}"


def test_a_dropped_connection_reconnects_with_dropped_then_connected(monkeypatch):
    async def instant(attempt):
        await asyncio.sleep(0)
    monkeypatch.setattr(stoat, "backoff_sleep", instant)
    sockets = [Socket([ready()]), ConnectionResetError("gone"), Socket([ready()])]

    async def connect(url):
        if not sockets:
            raise asyncio.CancelledError
        nxt = sockets.pop(0)
        if isinstance(nxt, Exception):
            raise nxt
        return nxt
    bot = bot_with(Server(), connect=connect)
    log = []
    bot.dropped = lambda: log.append("dropped")

    async def on_event(event, target):
        pass
    with pytest.raises(asyncio.CancelledError):
        run(bot.run(on_event, lambda: log.append("connected")))
    assert log[:4] == ["connected", "dropped", "dropped", "connected"]


def test_an_invalid_session_or_logout_ends_it_with_token_rejected():
    for frame in ({"type": "Error", "error": "InvalidSession"}, {"type": "Logout"}):
        socket = Socket([frame])

        async def connect(url, socket=socket):
            return socket
        bot = bot_with(Server(), connect=connect)
        with pytest.raises(base.Refused, match="token_rejected"):
            run(bot.run(None, lambda: None))
        assert socket.closed


def test_a_missing_pong_closes_the_connection(monkeypatch):
    monkeypatch.setattr(stoat, "PING_S", 0.01)

    class Quiet(Socket):
        async def __anext__(self):
            while not self.closed:
                await asyncio.sleep(0.005)
            raise StopAsyncIteration
    socket = Quiet([])

    async def connect(url):
        return socket
    bot = bot_with(Server(), connect=connect)
    assert run(asyncio.wait_for(bot._session("wss://x", None, lambda: None), 5)) is False
    assert any(f["type"] == "Ping" for f in socket.sent) and socket.closed


# ---------------------------------------------------------------- send

def test_send_replies_mentions_and_splits_long_text():
    server = Server()
    bot = run(ready_bot(server))
    items = [{"type": "text", "text": "hi", "mention_user_id": f"stoat:{ALEX}"},
             {"type": "text", "text": "word " * 900},
             {"type": "text", "text": "  "}]
    assert run(bot.send(f"C1/{MID}", items)) == 2
    first, *rest = server.posts
    assert first == {"content": f"<@{ALEX}> hi",
                     "replies": [{"id": MID, "mention": False, "fail_if_not_exists": False}]}
    assert len(rest) == 3 and all("replies" not in p for p in rest)
    assert all(len(p["content"]) <= stoat.MAX_TEXT for p in rest)
    assert "SENT1" in bot.mine
    posts = [r for r in server.requests if r.method == "POST"]
    assert all(r.headers.get("idempotency-key") for r in posts)


def test_send_uploads_an_image_to_autumn_first():
    server = Server()
    bot = bot_with(server)
    picture = base64.b64encode(b"\x89PNG\r\n\x1a\nxyz").decode()
    assert run(bot.send("C1", [{"type": "image", "b64": picture}])) == 1
    upload = next(r for r in server.requests if r.url.host == "cdn.stoat.test")
    assert str(upload.url) == f"{AUTUMN}/attachments" and b'name="file"' in upload.content
    assert server.posts == [{"attachments": ["FILE1"]}]


def test_send_skips_images_without_a_file_server_and_stops_on_failure():
    no_files = dict(root(), features={})
    server = Server(**{"/": httpx.Response(200, json=no_files)})
    bot = bot_with(server)
    assert run(bot.send("C1", [{"type": "image", "b64": "aGk="}, {"type": "text", "text": "ok"}])) == 1
    failing = Server(**{"/channels/C1/messages": httpx.Response(403, json={"type": "MissingPermission"})})
    assert run(bot_with(failing).send("C1", [{"type": "text", "text": "a"}, {"type": "text", "text": "b"}])) == 0


def test_target_uses_the_reply_handle():
    bot = bot_with(Server())
    assert bot.target({"reply_handle": "C1"}) == "C1"
    assert bot.target({"conversation_id": "G1"}) == "G1"
    with pytest.raises(base.Unsupported):
        bot.target({})


# ---------------------------------------------------------------- secrecy

def test_no_credential_reaches_an_event_or_a_log(caplog, monkeypatch):
    caplog.set_level(logging.DEBUG)

    async def instant(attempt):
        await asyncio.sleep(0)
    monkeypatch.setattr(stoat, "backoff_sleep", instant)
    picture = {"_id": "F1", "tag": "attachments", "filename": "a.png", "content_type": "image/png", "size": 11}
    sockets = [Socket([ready(), message(content=f"<@{BOT}> hi", mentions=[BOT], attachments=[picture])]),
               OSError("boom")]

    async def connect(url):
        if not sockets:
            raise asyncio.CancelledError
        nxt = sockets.pop(0)
        if isinstance(nxt, Exception):
            raise nxt
        return nxt
    server = Server(**{"/channels/C1/messages": httpx.Response(500, json={"type": "InternalError"})})
    bot = bot_with(server, connect=connect)
    seen = []

    async def on_event(event, target):
        seen.append(event)
        await bot.send(target, [{"type": "text", "text": "reply"}])
    with pytest.raises(asyncio.CancelledError):
        run(bot.run(on_event, lambda: None))
    assert seen and TOKEN not in json.dumps(seen)
    assert caplog.records and all(TOKEN not in r.getMessage() for r in caplog.records)
    assert all(TOKEN not in str(r.url) for r in server.requests)
