"""Twitch chat against a stand-in Twitch: no network, no accounts."""
from __future__ import annotations

import asyncio
import json
import logging
import time
from urllib.parse import parse_qs

import httpx
import pytest

from persona_agent.direct import base, twitch

ACCESS, REFRESH = "access-secret-1", "refresh-secret-1"
VALUES = {"twitch_client_id": "cid", "twitch_channels": "Streamer, https://www.twitch.tv/other/",
          "twitch_access_token": ACCESS, "twitch_refresh_token": REFRESH}


def run(coro):
    return asyncio.run(coro)


def mock(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


class Socket:
    """An EventSub connection that replays frames, then drops."""

    def __init__(self, frames, close_code=None):
        self.frames = [json.dumps(f) for f in frames]
        self.close_code = close_code
        self.closed = False

    async def recv(self):
        if not self.frames:
            raise ConnectionError("socket closed")
        return self.frames.pop(0)

    async def close(self, code=1000):
        self.closed = True


def welcome(session="s1"):
    return {"metadata": {"message_type": "session_welcome"},
            "payload": {"session": {"id": session, "keepalive_timeout_seconds": 10}}}


def chat(mid, text, *, user="42", login="alex", channel="300", fragments=None, reply=None, **extra):
    event = {"broadcaster_user_id": channel, "chatter_user_id": user, "chatter_user_login": login,
             "chatter_user_name": login.title(), "message_id": f"m-{mid}",
             "message": {"text": text, "fragments": fragments or [{"type": "text", "text": text}]}}
    if reply:
        event["reply"] = reply
    event.update(extra)
    return {"metadata": {"message_type": "notification", "message_id": f"n-{mid}",
                         "message_timestamp": "2026-11-10T10:00:00.123456789Z",
                         "subscription_type": "channel.chat.message"},
            "payload": {"subscription": {"type": "channel.chat.message"}, "event": event}}


class Twitch:
    """Stand-in id.twitch.tv and api.twitch.tv; records what was asked."""

    def __init__(self, *, scopes=("user:read:chat", "user:write:chat"), client_id="cid",
                 validate_401=0, refresh_status=200, users=None, subscribe_status=202, send=None):
        self.scopes, self.client_id = list(scopes), client_id
        self.validate_401, self.refresh_status = validate_401, refresh_status
        self.users = users if users is not None else [{"id": "300", "login": "streamer"},
                                                      {"id": "301", "login": "other"}]
        self.subscribe_status = subscribe_status
        self.send = send or (lambda body: httpx.Response(200, json={"data": [
            {"message_id": "x", "is_sent": True, "drop_reason": None}]}))
        self.subscriptions, self.posts, self.refreshes = [], [], []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/oauth2/validate":
            assert request.headers["Authorization"].startswith("OAuth ")
            if self.validate_401:
                self.validate_401 -= 1
                return httpx.Response(401, json={"status": 401, "message": "invalid access token"})
            return httpx.Response(200, json={"client_id": self.client_id, "login": "novabot",
                                             "user_id": "900", "scopes": self.scopes, "expires_in": 14000})
        if path == "/oauth2/token":
            form = parse_qs(request.content.decode())
            assert "client_secret" not in form and form["grant_type"] == ["refresh_token"]
            self.refreshes.append(form["refresh_token"][0])
            if self.refresh_status != 200:
                return httpx.Response(self.refresh_status, json={"status": 400, "message": "Invalid refresh token"})
            n = len(self.refreshes) + 1
            return httpx.Response(200, json={"access_token": f"access-secret-{n}",
                                             "refresh_token": f"refresh-secret-{n}", "expires_in": 14000})
        assert request.headers["Client-Id"] == "cid"
        assert request.headers["Authorization"].startswith("Bearer access-secret-")
        if path == "/helix/users":
            wanted = request.url.params.get_list("login")
            return httpx.Response(200, json={"data": [u for u in self.users if u["login"] in wanted]})
        if path == "/helix/eventsub/subscriptions":
            self.subscriptions.append(json.loads(request.content))
            return httpx.Response(self.subscribe_status, json={})
        if path == "/helix/chat/messages":
            body = json.loads(request.content)
            self.posts.append(body)
            return self.send(body)
        return httpx.Response(404)


@pytest.fixture(autouse=True)
def quick(monkeypatch):
    monkeypatch.setattr(twitch, "CHANNEL_GAP_S", 0.0)
    monkeypatch.setattr(twitch, "RATE_WAIT_S", (0.0, 0.0))

    async def instant(seconds):
        await asyncio.sleep(0)
    monkeypatch.setattr(twitch, "backoff_sleep", instant)


# ---------------------------------------------------------------- check

def test_check_learns_the_bot_and_the_listed_channels():
    server = Twitch()
    bot = twitch.Twitch(VALUES, client=mock(server))
    assert run(bot.check()) == "novabot"
    assert bot.bot_id == "900" and bot.channel_ids == {"300": "streamer", "301": "other"}
    assert bot.channels == ["streamer", "other"]


@pytest.mark.parametrize("server, values, code", [
    (Twitch(validate_401=2, refresh_status=400), VALUES, "session_expired"),
    (Twitch(scopes=["user:read:chat"]), VALUES, "token_rejected"),
    (Twitch(client_id="someone-else"), VALUES, "app_rejected"),
    (Twitch(users=[{"id": "300", "login": "streamer"}]), VALUES, "channel_not_found"),
    (Twitch(), {**VALUES, "twitch_channels": "  ,  "}, "channel_not_found"),
    (Twitch(), {"twitch_client_id": "cid", "twitch_channels": "streamer"}, "session_expired"),
])
def test_check_names_each_refusal(server, values, code):
    with pytest.raises(base.Refused, match=code):
        run(twitch.Twitch(values, client=mock(server)).check())


def test_check_reports_an_unreachable_twitch_as_a_connection_error():
    def down(request):
        raise httpx.ConnectError("down", request=request)
    with pytest.raises(ConnectionError):
        run(twitch.Twitch(VALUES, client=mock(down)).check())


def test_a_refreshed_token_is_kept_in_state_and_a_new_login_replaces_it(tmp_path):
    state = tmp_path / "twitch.json"
    server = Twitch(validate_401=1)
    bot = twitch.Twitch(VALUES, client=mock(server), state=state)
    run(bot.check())
    assert server.refreshes == [REFRESH]
    saved = json.loads(state.read_text(encoding="utf-8"))
    assert saved["refresh_token"] == "refresh-secret-2" and saved["access_token"] == "access-secret-2"
    again = twitch.Twitch(VALUES, client=mock(Twitch()), state=state)
    assert again.refresh_token == "refresh-secret-2"
    relogged = twitch.Twitch({**VALUES, "twitch_refresh_token": "refresh-new"}, client=mock(Twitch()), state=state)
    assert relogged.refresh_token == "refresh-new" and relogged.access == ACCESS


def test_concurrent_401s_spend_the_single_use_refresh_token_once():
    server = Twitch()
    bot = twitch.Twitch(VALUES, client=mock(server))

    async def both():
        stale = bot.access
        await asyncio.gather(bot._refresh(stale), bot._refresh(stale))
    run(both())
    assert server.refreshes == [REFRESH]


# ---------------------------------------------------------------- run

def test_run_subscribes_hands_over_chat_and_reconnects_after_a_drop(caplog):
    caplog.set_level(logging.DEBUG)
    server = Twitch()
    first = Socket([welcome("s1"),
                    chat(1, "hi @NovaBot", fragments=[{"type": "text", "text": "hi "}, {
                        "type": "mention", "text": "@NovaBot",
                        "mention": {"user_id": "900", "user_login": "novabot"}}]),
                    chat(1, "hi @NovaBot"),                                   # a repeated push
                    chat(2, "my own echo", user="900", login="novabot"),
                    chat(3, "just chatting", user="43", login="bea"),
                    chat(4, "yes you", reply={"parent_message_id": "m-0", "parent_message_body": "earlier",
                                              "parent_user_id": "900", "parent_user_login": "novabot"})])
    second = Socket([welcome("s2"), {"metadata": {"message_type": "revocation"},
                                     "payload": {"subscription": {"status": "authorization_revoked"}}}])
    sockets = iter([first, second])

    async def connect(url):
        assert url.startswith("wss://eventsub.wss.twitch.tv/ws")
        return next(sockets)
    bot = twitch.Twitch(VALUES, client=mock(server), connect=connect)
    states, seen = [], []
    bot.dropped = lambda: states.append("connecting")

    async def on_event(event, target):
        seen.append((event, target))
    with pytest.raises(base.Refused, match="session_expired"):
        run(bot.run(on_event, lambda: states.append("connected")))
    assert states == ["connected", "connecting", "connected"]
    assert first.closed and second.closed
    assert [s["transport"]["session_id"] for s in server.subscriptions] == ["s1", "s1", "s2", "s2"]
    assert {s["type"] for s in server.subscriptions} == {"channel.chat.message"}
    assert {s["condition"]["broadcaster_user_id"] for s in server.subscriptions} == {"300", "301"}

    assert [e["message_id"] for e, _ in seen] == ["m-1", "m-3", "m-4"]
    mention, plain, reply = (e for e, _ in seen)
    assert all(t == "300" for _, t in seen)
    assert mention == {"conversation_type": "group", "conversation_id": "300", "sender_id": "42",
                       "sender_name": "Alex", "message_id": "m-1", "sent_at": 1794304800,
                       "addressed": True, "text": "hi @NovaBot",
                       "segments": [{"type": "mention", "user_id": "900", "name": "novabot"},
                                    {"type": "text", "text": "hi @NovaBot"}],
                       "reply_handle": "300"}
    assert plain["addressed"] is False and plain["sender_id"] == "43"
    assert reply["addressed"] is True and reply["segments"][0] == {
        "type": "reply", "message_id": "m-0", "text": "earlier", "sender_id": "900", "sender_name": "novabot"}

    leaked = [r.getMessage() for r in caplog.records] + [json.dumps(e) for e, _ in seen]
    assert not any(secret in line for line in leaked for secret in (ACCESS, REFRESH, "access-secret-2"))


def test_a_session_reconnect_moves_to_the_new_url_without_subscribing_again():
    server = Twitch()
    old = Socket([welcome("s1"), {"metadata": {"message_type": "session_reconnect"}, "payload": {
        "session": {"id": "s1", "reconnect_url": "wss://edge-2.example/ws?id=abc"}}}])
    new = Socket([welcome("s1"), chat(1, "after the move")])
    urls = []

    async def connect(url):
        urls.append(url)
        return old if len(urls) == 1 else new
    bot = twitch.Twitch(VALUES, client=mock(server), connect=connect)
    run(bot.check())
    seen = []

    async def on_event(event, target):
        seen.append(event["text"])
    with pytest.raises(ConnectionError):
        run(bot._session(on_event, lambda: None))
    assert urls[1] == "wss://edge-2.example/ws?id=abc"
    assert old.closed and new.closed and seen == ["after the move"]
    assert len(server.subscriptions) == 2


def test_a_login_without_the_chat_scopes_is_refused_at_subscribe():
    bot = twitch.Twitch(VALUES, client=mock(Twitch(subscribe_status=403)),
                        connect=lambda url: asyncio.sleep(0, Socket([welcome()])))
    with pytest.raises(base.Refused, match="token_rejected"):
        run(bot.run(None, lambda: None))


def test_only_listed_channels_reach_the_character_and_there_are_no_dms():
    bot = twitch.Twitch(VALUES, client=mock(Twitch()))
    run(bot.check())
    listed = bot.event(chat(1, "hello")["payload"]["event"])
    assert listed["conversation_type"] == "group" and listed["conversation_id"] == "300"
    assert bot.event(chat(2, "hello", channel="999")["payload"]["event"]) is None
    shared = chat(3, "from a shared room", source_broadcaster_user_id="555")["payload"]["event"]
    assert bot.event(shared) is None
    own_shared = chat(4, "ours", source_broadcaster_user_id="300")["payload"]["event"]
    assert bot.event(own_shared)["text"] == "ours"


# ---------------------------------------------------------------- send

def test_send_splits_mentions_and_skips_images():
    server = Twitch()
    bot = twitch.Twitch(VALUES, client=mock(server))
    run(bot.check())
    bot.logins["42"] = "alex"
    items = [{"type": "text", "text": "hi", "mention_user_id": "twitch:42"},
             {"type": "text", "text": "word " * 250},
             {"type": "image", "b64": "aGk="},
             {"type": "text", "text": "  "}]
    assert run(bot.send("300", items)) == 2
    assert server.posts[0] == {"broadcaster_id": "300", "sender_id": "900", "message": "@alex hi"}
    long = server.posts[1:]
    assert len(long) >= 3 and all(len(p["message"]) <= twitch.MAX_TEXT for p in long)
    assert all(p["broadcaster_id"] == "300" for p in long)


def test_send_waits_out_a_429_and_stops_on_a_dropped_message():
    answers = iter([httpx.Response(429, headers={"ratelimit-reset": str(int(time.time()))}),
                    httpx.Response(200, json={"data": [{"is_sent": True}]}),
                    httpx.Response(200, json={"data": [{"is_sent": False,
                                                        "drop_reason": {"code": "msg_duplicate"}}]})])
    server = Twitch(send=lambda body: next(answers))
    bot = twitch.Twitch(VALUES, client=mock(server))
    bot.bot_id = "900"
    sent = run(bot.send("300", [{"type": "text", "text": "one"}, {"type": "text", "text": "two"},
                                {"type": "text", "text": "three"}]))
    assert sent == 1 and len(server.posts) == 3


def test_sending_keeps_under_the_chat_rate_limit(monkeypatch):
    monkeypatch.setattr(twitch, "SEND_PER_WINDOW", 2)
    monkeypatch.setattr(twitch, "SEND_WINDOW_S", 0.3)
    bot = twitch.Twitch(VALUES, client=mock(Twitch()))
    bot.bot_id = "900"
    started = time.monotonic()
    assert run(bot.send("300", [{"type": "text", "text": t} for t in ("a", "b", "c")])) == 3
    assert time.monotonic() - started >= 0.25


def test_target_reaches_only_listed_channels():
    bot = twitch.Twitch(VALUES, client=mock(Twitch()))
    run(bot.check())
    assert bot.target({"reply_handle": "300"}) == "300"
    for delivery in ({"reply_handle": "999"}, {}):
        with pytest.raises(base.Unsupported):
            bot.target(delivery)


# ---------------------------------------------------------------- login

def test_login_shows_the_activation_link_and_returns_the_tokens(monkeypatch):
    real_sleep = asyncio.sleep
    monkeypatch.setattr(twitch.asyncio, "sleep", lambda s: real_sleep(0))
    codes = iter(["dev-1", "dev-2"])
    polls = iter([(400, {"status": 400, "message": "authorization_pending"}),
                  (400, {"status": 400, "message": "slow_down"}),
                  (400, {"status": 400, "message": "invalid device code"}),
                  (200, {"access_token": "a1", "refresh_token": "r1", "expires_in": 14000})])

    def handler(request):
        form = parse_qs(request.content.decode())
        assert form["client_id"] == ["cid"] and "client_secret" not in form
        if request.url.path == "/oauth2/device":
            assert form["scopes"] == ["user:read:chat user:write:chat"]
            code = next(codes)
            return httpx.Response(200, json={"device_code": code, "user_code": "ABCD", "expires_in": 1800,
                                             "interval": 5, "verification_uri":
                                             f"https://www.twitch.tv/activate?public=true&device-code={code}"})
        assert form["grant_type"] == [twitch.DEVICE_GRANT]
        status, body = next(polls)
        return httpx.Response(status, json=body)
    shown = []
    values = run(twitch.login(mock(handler), shown.append, {"twitch_client_id": "cid", "twitch_channels": "streamer"}))
    assert [u.rsplit("=", 1)[1] for u in shown] == ["dev-1", "dev-2"]
    assert values == {"twitch_client_id": "cid", "twitch_channels": "streamer",
                      "twitch_access_token": "a1", "twitch_refresh_token": "r1"}


def test_login_refuses_an_unknown_app():
    bad = mock(lambda r: httpx.Response(400, json={"status": 400, "message": "invalid client"}))
    with pytest.raises(twitch.LoginFailed, match="app_rejected"):
        run(twitch.login(bad, lambda uri: None, {"twitch_client_id": "nope"}))
    with pytest.raises(twitch.LoginFailed, match="app_rejected"):
        run(twitch.login(bad, lambda uri: None, {}))
