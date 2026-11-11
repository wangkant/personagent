"""The Matrix direct connector against a stand-in homeserver: no network, no account."""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import time

import httpx
import pytest

from persona_agent.direct import base, matrix

TOKEN = "syt_secret_token_value"
BOT = "@nova:example.org"
OWNER = "@kant:example.org"
VALUES = {"matrix_homeserver": "https://example.org", "matrix_token": TOKEN, "matrix_owner": OWNER}
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 32
REAL_RETRY_AFTER = matrix._retry_after


def run(coro):
    return asyncio.run(coro)


def now_ms() -> int:
    return int(time.time() * 1000)


def message(event_id, sender, body, **content):
    return {"type": "m.room.message", "event_id": event_id, "sender": sender,
            "origin_server_ts": now_ms(), "content": {"msgtype": "m.text", "body": body, **content}}


class Homeserver:
    """Routes requests by path; `syncs` are answered in order, then 401."""

    def __init__(self, syncs=(), whoami=None):
        self.syncs = list(syncs)
        self.whoami = whoami or (lambda r: httpx.Response(200, json={"user_id": BOT, "device_id": "D"}))
        self.requests: list[httpx.Request] = []
        self.sent: list[tuple[str, dict]] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path
        if path == "/.well-known/matrix/client":
            return httpx.Response(404)
        assert request.headers.get("Authorization") == f"Bearer {TOKEN}"
        assert TOKEN not in str(request.url)
        if path.endswith("/account/whoami"):
            return self.whoami(request)
        if "/profile/" in path:
            return httpx.Response(200, json={"displayname": "Nova"})
        if path.endswith("/sync"):
            if not self.syncs:
                return httpx.Response(401, json={"errcode": "M_UNKNOWN_TOKEN"})
            answer = self.syncs.pop(0)
            if isinstance(answer, Exception):
                raise answer
            return httpx.Response(200, json=answer)
        if "/state/m.room.member/" in path:
            return httpx.Response(200, json={"membership": "join", "displayname": "Alex"})
        if "/send/m.room.message/" in path:
            self.sent.append((path, json.loads(request.content)))
            return httpx.Response(200, json={"event_id": f"$sent{len(self.sent)}"})
        if path.endswith("/_matrix/media/v3/upload"):
            self.sent.append((path, {"type": request.headers["Content-Type"],
                                     "filename": request.url.params.get("filename")}))
            return httpx.Response(200, json={"content_uri": "mxc://example.org/up1"})
        if "/media/download/" in path or "/media/v3/download/" in path:
            return httpx.Response(200, content=PNG)
        if path.endswith(("/join", "/leave")) or "/typing/" in path:
            self.sent.append((path, json.loads(request.content or b"{}")))
            return httpx.Response(200, json={"room_id": "x"} if path.endswith("/join") else {})
        return httpx.Response(404, json={"errcode": "M_UNRECOGNIZED"})


def bot(server, tmp_path=None, **values):
    return matrix.Matrix({**VALUES, **values}, client=httpx.AsyncClient(transport=httpx.MockTransport(server)),
                         state=(tmp_path / "matrix.json") if tmp_path else None)


@pytest.fixture(autouse=True)
def no_waits(monkeypatch):
    async def instant(attempt):
        await asyncio.sleep(0)
    monkeypatch.setattr(matrix, "backoff_sleep", instant)
    monkeypatch.setattr(matrix, "_retry_after", lambda response, body: 0)


# ---------------------------------------------------------------- check

def test_check_learns_the_bot_id_and_name():
    connection = bot(Homeserver())
    assert run(connection.check()) == "Nova"
    assert connection.bot_id == BOT


def test_check_follows_the_servers_well_known_address():
    seen = []

    def handler(request):
        seen.append(str(request.url))
        if request.url.path == "/.well-known/matrix/client":
            return httpx.Response(200, json={"m.homeserver": {"base_url": "https://client.example.org/"}})
        return Homeserver()(request)
    connection = bot(handler)
    run(connection.check())
    assert connection.base == "https://client.example.org"
    assert seen[1].startswith("https://client.example.org/_matrix/client/v3/account/whoami")


@pytest.mark.parametrize("whoami, code", [
    (lambda r: httpx.Response(401, json={"errcode": "M_UNKNOWN_TOKEN", "soft_logout": False}), "token_rejected"),
    (lambda r: httpx.Response(403, json={"errcode": "M_FORBIDDEN"}), "token_rejected"),
    (lambda r: httpx.Response(403, json={"errcode": "M_USER_DEACTIVATED"}), "account_deactivated"),
    (lambda r: httpx.Response(404, text="<html>not here</html>"), "homeserver_invalid"),
    (lambda r: httpx.Response(200, text="<html>a web page</html>"), "homeserver_invalid"),
])
def test_check_names_each_refusal(whoami, code):
    with pytest.raises(base.Refused, match=code):
        run(bot(Homeserver(whoami=whoami)).check())


@pytest.mark.parametrize("values, code", [
    ({"matrix_homeserver": "http://example.org"}, "homeserver_invalid"),
    ({"matrix_owner": "kant"}, "owner_invalid"),
    ({"matrix_owner": BOT}, "owner_invalid"),
])
def test_check_refuses_plain_http_and_a_bad_owner(values, code):
    with pytest.raises(base.Refused, match=code):
        run(bot(Homeserver(), **values).check())


def test_plain_http_is_allowed_to_this_computer_only():
    assert matrix.secure_base("http://localhost:8008") and matrix.secure_base("http://127.0.0.1:8008")
    assert not matrix.secure_base("http://192.168.1.5:8008") and matrix.secure_base("https://matrix.org")


def test_an_unreachable_server_is_a_connection_error():
    def down(request):
        raise httpx.ConnectError("down", request=request)
    with pytest.raises(ConnectionError):
        run(bot(down).check())


def test_a_rate_limit_is_waited_out():
    answers = iter([httpx.Response(429, json={"errcode": "M_LIMIT_EXCEEDED", "retry_after_ms": 10}),
                    httpx.Response(200, json={"user_id": BOT})])
    connection = bot(Homeserver(whoami=lambda r: next(answers)))
    assert run(connection.check()) == "Nova"
    assert REAL_RETRY_AFTER(httpx.Response(429, headers={"Retry-After": "7"}), {"retry_after_ms": 2000}) == 7
    assert REAL_RETRY_AFTER(httpx.Response(429), {"retry_after_ms": 2000}) == 2


# ---------------------------------------------------------------- run

ROOM, DM = "!group:example.org", "!dm:example.org"


def joined(*events, summary=None, state=()):
    return {"timeline": {"events": list(events)}, "state": {"events": list(state)},
            **({"summary": summary} if summary else {})}


def test_run_skips_the_backlog_then_hands_over_group_messages_and_dms(tmp_path, caplog):
    caplog.set_level(logging.DEBUG)
    first = {"next_batch": "s1", "account_data": {"events": [
        {"type": "m.direct", "content": {OWNER: [DM]}}]},
        "rooms": {"join": {ROOM: joined(message("$old", "@alex:example.org", "old news"),
                                        summary={"m.joined_member_count": 5})}}}
    second = {"next_batch": "s2", "rooms": {"join": {
        ROOM: joined(
            message("$1", "@alex:example.org", "just chatting"),
            message("$2", "@alex:example.org", "Nova: hi", **{"m.mentions": {"user_ids": [BOT]},
                    "format": "org.matrix.custom.html",
                    "formatted_body": f'<a href="https://matrix.to/#/{BOT}">Nova</a>: hi'}),
            message("$3", BOT, "my own words"),
            message("$4", "@alex:example.org", "> <@nova:example.org> my own words\n\nreally?",
                    **{"m.relates_to": {"m.in_reply_to": {"event_id": "$3"}}}),
            dict(message("$5", "@bridgebot:example.org", "bridge status"),
                 content={"msgtype": "m.notice", "body": "bridge status"}),
            {"type": "m.room.encrypted", "event_id": "$6", "sender": "@alex:example.org",
             "origin_server_ts": now_ms(), "content": {"algorithm": "m.megolm.v1.aes-sha2"}}),
        DM: joined(message("$7", OWNER, "hello there"))}}}
    server = Homeserver([first, second])
    connection = bot(server, tmp_path)
    seen, states = [], []

    async def on_event(event, target):
        seen.append((event, target))
    connection.dropped = lambda: states.append("connecting")
    with pytest.raises(base.Refused, match="token_rejected"):
        run(connection.run(on_event, lambda: states.append("connected")))
    assert states == ["connected"]
    by_id = {e["message_id"]: (e, t) for e, t in seen}
    assert set(by_id) == {"$1", "$2", "$4", "$7"}   # no backlog, no echo, no notice, nothing encrypted
    plain, target = by_id["$1"]
    assert plain["conversation_type"] == "group" and plain["conversation_id"] == ROOM
    assert plain["addressed"] is False and plain["reply_handle"] == ROOM and target == (ROOM, "", "$1")
    assert plain["sender_id"] == "@alex:example.org" and plain["sender_name"] == "Alex"
    assert plain["segments"] == [{"type": "text", "text": "just chatting"}] and plain["sent_at"] > 0
    mention = by_id["$2"][0]
    assert mention["addressed"] is True
    assert mention["segments"][0] == {"type": "mention", "user_id": BOT, "name": "Nova"}
    reply = by_id["$4"][0]
    assert reply["addressed"] is True and reply["text"] == "really?"
    assert reply["segments"][0] == {"type": "reply", "message_id": "$3", "text": "my own words",
                                    "sender_id": BOT, "sender_name": "Alex"}
    dm = by_id["$7"][0]
    assert dm["conversation_type"] == "dm" and "conversation_id" not in dm and dm["addressed"]
    assert connection.rooms[ROOM]["encrypted"] is True
    saved = json.loads((tmp_path / "matrix.json").read_text(encoding="utf-8"))
    assert saved["since"] == "s2" and saved["user"] == BOT and DM in saved["direct"]
    syncs = [r for r in server.requests if r.url.path.endswith("/sync")]
    assert "since" not in syncs[0].url.params and syncs[0].url.params["timeout"] == "0"
    assert syncs[1].url.params["since"] == "s1"
    typing = [p for p, body in server.sent if "/typing/" in p and body.get("typing")]
    assert typing        # addressed messages show the bot typing
    # The token never reaches an event or a log line.
    assert TOKEN not in json.dumps([e for e, _ in seen])
    assert not any(TOKEN in record.getMessage() for record in caplog.records)


def test_a_restart_resumes_from_the_saved_cursor(tmp_path):
    (tmp_path / "matrix.json").write_text(json.dumps(
        {"user": BOT, "since": "s9", "rooms": {ROOM: {"members": 4, "encrypted": False}}, "direct": []}),
        encoding="utf-8")
    server = Homeserver([{"next_batch": "s10", "rooms": {"join": {
        ROOM: joined(message("$1", "@alex:example.org", "new"))}}}])
    seen = []

    async def on_event(event, target):
        seen.append(event["message_id"])
    with pytest.raises(base.Refused):
        run(bot(server, tmp_path).run(on_event, lambda: None))
    sync = next(r for r in server.requests if r.url.path.endswith("/sync"))
    assert sync.url.params["since"] == "s9" and seen == ["$1"]
    # A cursor saved for another account is not reused.
    (tmp_path / "matrix.json").write_text(json.dumps({"user": "@other:x", "since": "s9"}), encoding="utf-8")
    server = Homeserver([{"next_batch": "a"}])
    with pytest.raises(base.Refused):
        run(bot(server, tmp_path).run(on_event, lambda: None))
    assert "since" not in next(r for r in server.requests if r.url.path.endswith("/sync")).url.params


def test_a_dropped_sync_reports_connecting_then_connected_again(tmp_path):
    server = Homeserver([{"next_batch": "s1"}, httpx.ConnectError("down"), {"next_batch": "s2"}])
    states = []
    connection = bot(server, tmp_path)
    connection.dropped = lambda: states.append("connecting")
    with pytest.raises(base.Refused, match="token_rejected"):
        run(connection.run(None, lambda: states.append("connected")))
    assert states == ["connected", "connecting", "connected"]


def test_old_messages_after_a_long_sleep_are_not_answered(tmp_path):
    connection = bot(Homeserver())
    connection.bot_id = BOT
    stale = message("$1", "@alex:example.org", "hours ago")
    stale["origin_server_ts"] = now_ms() - (matrix.MAX_AGE_S + 60) * 1000
    assert run(connection.event(ROOM, stale)) is None


def test_an_image_is_fetched_with_the_token_and_inlined(tmp_path):
    server = Homeserver()
    connection = bot(server)
    connection.bot_id = BOT
    event = run(connection.event(ROOM, {"type": "m.room.message", "event_id": "$i", "sender": "@alex:example.org",
                                        "origin_server_ts": now_ms(), "content": {
                                            "msgtype": "m.image", "body": "cat.png", "url": "mxc://example.org/abc",
                                            "info": {"size": len(PNG), "mimetype": "image/png"}}}))
    assert event["segments"] == [{"type": "image", "b64": base64.b64encode(PNG).decode()}]
    download = next(r for r in server.requests if "/media/" in r.url.path)
    assert download.url.path == "/_matrix/client/v1/media/download/example.org/abc"
    too_big = run(connection.event(ROOM, {"type": "m.room.message", "event_id": "$j", "sender": "@alex:example.org",
                                          "origin_server_ts": now_ms(), "content": {
                                              "msgtype": "m.image", "body": "big.png", "url": "mxc://example.org/big",
                                              "info": {"size": base.MAX_INLINE_IMAGE_BYTES + 1}}}))
    assert too_big["segments"] == [{"type": "media", "kind": "photo"}]


# ---------------------------------------------------------------- invites

def invite(inviter, *extra, is_direct=False):
    return {"invite_state": {"events": [
        {"type": "m.room.member", "state_key": BOT, "sender": inviter,
         "content": {"membership": "invite", **({"is_direct": True} if is_direct else {})}}, *extra]}}


def test_only_the_owners_invites_are_accepted_and_encrypted_rooms_are_declined(tmp_path):
    rooms = {"!mine:x": invite(OWNER, is_direct=True), "!spam:x": invite("@stranger:evil.org"),
             "!secret:x": invite(OWNER, {"type": "m.room.encryption", "state_key": "",
                                         "content": {"algorithm": "m.megolm.v1.aes-sha2"}})}
    server = Homeserver([{"next_batch": "s1", "rooms": {"invite": rooms}}])
    connection = bot(server, tmp_path)
    with pytest.raises(base.Refused):
        run(connection.run(None, lambda: None))
    calls = {path: body for path, body in server.sent}
    assert "/_matrix/client/v3/rooms/!mine:x/join" in calls
    assert calls["/_matrix/client/v3/rooms/!spam:x/leave"] == {}
    assert "encrypted" in calls["/_matrix/client/v3/rooms/!secret:x/leave"]["reason"]
    assert not any(p.endswith(("spam:x/join", "secret:x/join")) for p in calls)
    assert connection.is_direct("!mine:x")


# ---------------------------------------------------------------- send

def test_send_text_split_mention_image_and_thread():
    server = Homeserver()
    connection = bot(server)
    connection.bot_id = BOT
    connection.rooms[ROOM] = {"members": 5, "encrypted": False}
    long_text = ("word " * 2000).strip()
    items = [{"type": "text", "text": "hi", "mention_user_id": "matrix:@alex:example.org"},
             {"type": "text", "text": long_text},
             {"type": "image", "b64": base64.b64encode(PNG).decode()},
             {"type": "text", "text": "   "}]
    assert run(connection.send((ROOM, "$root", "$last"), items)) == 3
    messages = [body for path, body in server.sent if "/send/m.room.message/" in path]
    first = messages[0]
    assert first["body"] == "Alex hi" and first["m.mentions"] == {"user_ids": ["@alex:example.org"]}
    assert first["formatted_body"] == '<a href="https://matrix.to/#/@alex:example.org">Alex</a> hi'
    assert first["m.relates_to"] == {"rel_type": "m.thread", "event_id": "$root", "is_falling_back": True,
                                     "m.in_reply_to": {"event_id": "$last"}}
    pieces = [m for m in messages if m["msgtype"] == "m.text"][1:]
    assert len(pieces) > 1 and all(len(p["body"]) <= matrix.MAX_TEXT for p in pieces)
    assert all(p["m.mentions"] == {} for p in pieces)
    upload = next(body for path, body in server.sent if path.endswith("/upload"))
    assert upload == {"type": "image/png", "filename": "image.png"}
    image = next(m for m in messages if m["msgtype"] == "m.image")
    assert image["url"] == "mxc://example.org/up1" and image["info"]["mimetype"] == "image/png"
    txns = [path.rsplit("/", 1)[1] for path, _ in server.sent if "/send/" in path]
    assert len(set(txns)) == len(txns)


def test_send_stops_at_a_failure_and_never_writes_into_an_encrypted_room():
    answers = iter([200, 500])

    def handler(request):
        if "/send/" in request.url.path:
            status = next(answers, 500)
            return httpx.Response(status, json={"event_id": "$x"} if status == 200 else {"errcode": "M_UNKNOWN"})
        return httpx.Response(200, json={})
    connection = bot(handler)
    connection.bot_id = BOT
    items = [{"type": "text", "text": "one"}, {"type": "text", "text": "two"}, {"type": "text", "text": "three"}]
    assert run(connection.send(ROOM, items)) == 1
    connection.rooms[ROOM] = {"members": 3, "encrypted": True}
    assert run(connection.send(ROOM, items)) == 0


def test_target_comes_from_the_reply_handle():
    connection = bot(Homeserver())
    assert connection.target({"reply_handle": ROOM}) == (ROOM, "", "")
    with pytest.raises(base.Unsupported):
        connection.target({})
    connection.rooms[ROOM] = {"members": 3, "encrypted": True}
    with pytest.raises(base.Unsupported):
        connection.target({"reply_handle": ROOM})
