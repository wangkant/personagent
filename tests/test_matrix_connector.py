"""The Matrix connector: room events become neutral events, replies and outbox
deliveries go back into the room. matrix-nio is never imported; a fake client
with the same few methods stands in for it, and a fake agent for personagent."""
from __future__ import annotations

import asyncio
import base64
import inspect
import json
import re
import sys
import time
import types
from pathlib import Path

import httpx
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "integrations" / "matrix"))
import matrix_connector as mc  # noqa: E402

BOT = "@nova:example.org"
ALEX = "@alex:example.org"
BRIDGE = "@whatsappbot:example.org"
GROUP = "!group:example.org"
DM = "!dm:example.org"
NOW = 1_790_320_000
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16


def check(name: str, cond: bool, detail: str = "") -> None:
    assert cond, f"{name}: {detail}"


class Obj(types.SimpleNamespace):
    """A nio response or event: attributes only."""


class User:
    def __init__(self, display_name: str = "", invited: bool = False):
        self.display_name = display_name
        self.invited = invited


class Room:
    def __init__(self, room_id: str, members: dict, encrypted: bool = False):
        self.room_id = room_id
        self.users = {uid: User(name) for uid, name in members.items()}
        self.encrypted = encrypted


class Client:
    """The slice of nio.AsyncClient the connector calls."""

    def __init__(self, rooms=()):
        self.user_id = BOT
        self.rooms = {room.room_id: room for room in rooms}
        self.sent: list[tuple[str, dict]] = []
        self.typing: list[tuple[str, bool]] = []
        self.uploads: list[dict] = []
        self.read: list[tuple] = []
        self.joined: list[str] = []
        self.media: dict[str, bytes] = {}
        self.events: dict[str, dict] = {}
        self.direct: dict = {}
        self.refuse_after: int | None = None

    async def room_send(self, room_id, message_type, content, tx_id=None,
                        ignore_unverified_devices=False):
        if self.refuse_after is not None and len(self.sent) >= self.refuse_after:
            return Obj(message="forbidden", status_code="M_FORBIDDEN")
        self.sent.append((room_id, content))
        return Obj(event_id=f"$sent{len(self.sent)}")

    async def room_typing(self, room_id, typing_state=True, timeout=30_000):
        self.typing.append((room_id, typing_state))

    async def upload(self, data_provider, content_type="application/octet-stream",
                     filename=None, encrypt=False, monitor=None, filesize=None):
        self.uploads.append({"data": data_provider.read(), "content_type": content_type,
                             "filename": filename, "encrypt": encrypt, "filesize": filesize})
        keys = {"v": "v2", "key": {"k": "KEY"}, "iv": "IV", "hashes": {"sha256": "SHA"}}
        return Obj(content_uri="mxc://example.org/up1"), (keys if encrypt else None)

    async def download(self, mxc=None, filename=None, allow_remote=True):
        data = self.media.get(mxc)
        return Obj(body=data) if data is not None else Obj(message="not found")

    async def room_get_event(self, room_id, event_id):
        source = self.events.get(event_id)
        return Obj(event=Obj(source=source)) if source else Obj(message="M_NOT_FOUND")

    async def room_read_markers(self, room_id, fully_read_event, read_event=None,
                                private_read_event=None):
        self.read.append((room_id, fully_read_event, read_event))

    async def join(self, room_id):
        self.joined.append(room_id)
        return Obj(room_id=room_id)

    async def list_direct_rooms(self):
        return Obj(rooms=self.direct)


def agent_client(answers: list, seen: list, pulls: list | None = None) -> httpx.AsyncClient:
    """A fake personagent: records each body, answers events and pulls in turn."""
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        seen.append(payload)
        if request.url.path.endswith("/outbox"):
            return httpx.Response(200, json=pulls.pop(0) if pulls else {"deliveries": []})
        answer = answers.pop(0) if answers else {"handled": True, "owned": True, "replies": []}
        return httpx.Response(200, json=answer)
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def settings(**overrides) -> mc.Settings:
    values = {"homeserver": "https://example.org", "user_id": BOT, "access_token": "t",
              "rooms": (GROUP,), "dm_users": (ALEX,), "ignore_users": (BRIDGE,),
              "store_path": Path("unused")}
    values.update(overrides)
    return mc.Settings(**values)


def make(room_list=None, answers=None, seen=None, **overrides):
    room_list = room_list if room_list is not None else [
        Room(GROUP, {BOT: "Nova", ALEX: "Alex", "@bob:example.org": "Bob"}),
        Room(DM, {BOT: "Nova", ALEX: "Alex"}),
    ]
    client = Client(room_list)
    agent = mc.sdk.Connector("http://127.0.0.1:8080/webhook/gateway", forwarder_id="mx1",
                             client=agent_client(answers if answers is not None else [],
                                                 seen if seen is not None else []))
    conn = mc.MatrixConnector(client, settings(**overrides), agent)
    conn.now = lambda: NOW
    conn.pause_s = (0, 0)
    return conn, client


def msg(body: str = "hello", *, sender: str = ALEX, event_id: str = "$e1",
        ts: int = NOW * 1000, event_type: str = "m.room.message", **content) -> dict:
    content = {"msgtype": "m.text", "body": body, **content}
    return {"type": event_type, "sender": sender, "event_id": event_id,
            "origin_server_ts": ts, "content": content}


def build(conn, room_id: str, source: dict):
    return asyncio.run(conn.build_event(conn.client.rooms[room_id], source))


# ---------- settings ----------

def test_settings_come_from_the_file_with_the_environment_on_top(tmp: Path) -> None:
    config = tmp / "matrix.env"
    config.write_text("MATRIX_HOMESERVER=matrix.example.org\nMATRIX_ACCESS_TOKEN=abc\n"
                      "MATRIX_ROOMS=!a:example.org, !b:example.org\n"
                      "MATRIX_DM_USERS=@*:example.org\nMATRIX_E2EE=true\n"
                      "MATRIX_TIMEOUT_S=90\n", encoding="utf-8")
    values = mc.load_env(str(config), environ={"MATRIX_TIMEOUT_S": "600", "HOME": "/x"})
    s = mc.Settings.from_env(values)
    check("scheme added", s.homeserver == "https://matrix.example.org", s.homeserver)
    check("lists split and trimmed", s.rooms == ("!a:example.org", "!b:example.org"),
          repr(s.rooms))
    check("environment wins", s.timeout_s == 600.0, str(s.timeout_s))
    check("flags", s.e2ee and s.outbox and s.read_receipts)
    check("unrelated environment ignored", "HOME" not in values)
    check("token kept out of repr", "abc" not in repr(s))
    with pytest.raises(FileNotFoundError):
        mc.load_env(str(tmp / "missing.env"), environ={})


def test_settings_refuse_what_cannot_work() -> None:
    base = {"MATRIX_HOMESERVER": "https://example.org", "MATRIX_ACCESS_TOKEN": "t"}
    with pytest.raises(ValueError, match="MATRIX_HOMESERVER"):
        mc.Settings.from_env({"MATRIX_ACCESS_TOKEN": "t"})
    with pytest.raises(ValueError, match="MATRIX_ACCESS_TOKEN"):
        mc.Settings.from_env({"MATRIX_HOMESERVER": "https://example.org",
                              "MATRIX_USER_ID": BOT})
    with pytest.raises(ValueError, match="PERSONAGENT_URL"):
        mc.Settings.from_env({**base, "PERSONAGENT_URL": "http://agent.lan:8080/webhook/gateway",
                              "GATEWAY_TOKEN": "g"})
    with pytest.raises(ValueError, match="MATRIX_TIMEOUT_S"):
        mc.Settings.from_env({**base, "MATRIX_TIMEOUT_S": "soon"})
    s = mc.Settings.from_env({**base, "MATRIX_USER_ID": BOT, "MATRIX_PASSWORD": "pw"})
    check("password login is enough too", s.password == "pw" and s.agent_url.startswith(
        "http://127.0.0.1"))
    check("forwarder id is stable per account",
          mc.default_forwarder_id(BOT) == mc.default_forwarder_id(BOT)
          and mc.default_forwarder_id(BOT) != mc.default_forwarder_id(ALEX))


def test_every_setting_is_read_and_documented() -> None:
    source = (ROOT / "integrations" / "matrix" / "matrix_connector.py").read_text(encoding="utf-8")
    named = set(re.findall(r'"((?:MATRIX|PERSONAGENT|GATEWAY)_[A-Z0-9_]+)"', source))
    template = (ROOT / "integrations" / "matrix" / ".env.example").read_text(encoding="utf-8")
    documented = set(re.findall(r"^([A-Z][A-Z0-9_]+)=", template, re.MULTILINE))
    check("every name the code uses passes load_env's filter", named <= set(mc.KNOWN_KEYS),
          repr(named - set(mc.KNOWN_KEYS)))
    check(".env.example lists exactly the known settings", documented == set(mc.KNOWN_KEYS),
          repr(documented ^ set(mc.KNOWN_KEYS)))


# ---------- inbound ----------

def test_a_group_message_becomes_a_neutral_event() -> None:
    conn, _ = make()
    event = build(conn, GROUP, msg("how was your day?"))
    check("event", event is not None)
    expected = {
        "platform": "matrix", "message_type": "group", "conversation_id": GROUP,
        "user_id": ALEX, "sender_name": "Alex", "self_id": BOT, "message_id": "$e1",
        "source_timestamp": NOW, "is_at_me": False, "raw_text": "how was your day?",
        "segments": [{"type": "text", "text": "how was your day?"}],
        "reply_handle": GROUP, "caps": ["outbox", "quote_text"],
    }
    check("fields", event == expected, repr(event))
    conn2, _ = make(outbox=False)
    check("no outbox, no outbox cap", build(conn2, GROUP, msg())["caps"] == ["quote_text"])


def test_direct_rooms_are_private_and_gated_by_the_dm_list() -> None:
    bridged = Room("!wa:example.org", {BOT: "Nova", "@whatsapp_1:example.org": "Kim",
                                       BRIDGE: "WhatsApp bridge bot"})
    flagged = Room("!flag:example.org", {BOT: "Nova", ALEX: "Alex", "@bob:example.org": "Bob"})
    small_group = Room(GROUP, {BOT: "Nova", ALEX: "Alex"})
    conn, client = make([Room(DM, {BOT: "Nova", ALEX: "Alex"}), bridged, flagged,
                         small_group],
                        dm_users=(ALEX, "@whatsapp_*:example.org"))
    event = build(conn, DM, msg())
    check("two members is a DM", event["message_type"] == "private", repr(event))
    check("a DM is keyed by the person", event["conversation_id"] == ALEX)
    check("reply_handle is still the room", event["reply_handle"] == DM)
    wa = build(conn, "!wa:example.org", msg(sender="@whatsapp_1:example.org"))
    check("a bridge bot is not a member", wa and wa["message_type"] == "private", repr(wa))
    check("a room named in MATRIX_ROOMS stays a group",
          build(conn, GROUP, msg())["message_type"] == "group")
    check("a group room not listed is ignored", build(conn, "!flag:example.org", msg()) is None)
    client.direct = {ALEX: ["!flag:example.org"]}
    asyncio.run(conn.refresh_direct_rooms())
    flagged_event = build(conn, "!flag:example.org", msg())
    check("m.direct makes it a DM", flagged_event["message_type"] == "private")
    check("a stranger's DM is ignored",
          build(conn, "!flag:example.org", msg(sender="@bob:example.org")) is None)


def test_is_at_me_follows_mentions_and_replies() -> None:
    conn, client = make()
    at = build(conn, GROUP, msg("Nova: hi", **{"m.mentions": {"user_ids": [BOT]}}))
    check("m.mentions", at["is_at_me"] is True)
    named = build(conn, GROUP, msg("Nova is here", **{"m.mentions": {}}))
    check("a name alone is the agent's call, not a mention", named["is_at_me"] is False)
    pill = build(conn, GROUP, msg(
        "Nova: how was your day?", format="org.matrix.custom.html",
        formatted_body='<a href="https://matrix.to/#/%40nova%3Aexample.org">Nova</a>: '
                       'how was your day?'))
    check("pill without m.mentions", pill["is_at_me"] is True, repr(pill))
    check("pill becomes a mention segment", pill["segments"] == [
        {"type": "mention", "user_id": BOT, "name": "Nova"},
        {"type": "text", "text": ": how was your day?"}], repr(pill["segments"]))
    check("bare user id in an old client's text",
          build(conn, GROUP, msg(f"ping {BOT}"))["is_at_me"] is True)

    conn._remember("$mine", BOT, "it rained")
    reply = build(conn, GROUP, msg("really?", event_id="$e2",
                                   **{"m.relates_to": {"m.in_reply_to": {"event_id": "$mine"}}}))
    check("a reply to the bot", reply["is_at_me"] is True)
    check("the quote carries its text", reply["segments"][0] == {
        "type": "reply", "message_id": "$mine", "sender_id": BOT, "sender_name": "Nova",
        "text": "it rained"}, repr(reply["segments"]))

    client.events["$old"] = msg("from yesterday", sender=BOT, event_id="$old")
    fetched = build(conn, GROUP, msg("still?", event_id="$e3",
                                     **{"m.relates_to": {"m.in_reply_to": {"event_id": "$old"}}}))
    check("a reply to an event fetched from the server", fetched["is_at_me"] is True
          and fetched["segments"][0]["text"] == "from yesterday", repr(fetched["segments"]))

    quoted = build(conn, GROUP, msg(
        f"> <{ALEX}> ask {BOT} later\n\nsure", sender="@bob:example.org", event_id="$e4",
        **{"m.relates_to": {"m.in_reply_to": {"event_id": "$gone"}}}))
    check("a fallback quoting the bot's id is not a mention", quoted["is_at_me"] is False)
    check("the fallback is not the sender's words", quoted["raw_text"] == "sure"
          and quoted["segments"][-1] == {"type": "text", "text": "sure"}, repr(quoted))
    check("an unfetchable quote falls back to the fallback text",
          quoted["segments"][0] == {"type": "reply", "message_id": "$gone",
                                    "text": f"ask {BOT} later"}, repr(quoted["segments"]))


def test_what_is_never_forwarded() -> None:
    conn, _ = make()
    cases = {
        "own message": msg(sender=BOT),
        "bridge bot": msg(sender=BRIDGE),
        "notice": msg(msgtype="m.notice"),
        "edit": msg("fixed", **{"m.new_content": {"body": "fixed"},
                                "m.relates_to": {"rel_type": "m.replace", "event_id": "$e0"}}),
        "backlog": msg(ts=(NOW - 3600) * 1000),
        "no timestamp": {k: v for k, v in msg().items() if k != "origin_server_ts"},
        "reaction": {"type": "m.reaction", "sender": ALEX, "event_id": "$r",
                     "origin_server_ts": NOW * 1000, "content": {}},
    }
    for name, source in cases.items():
        check(name, build(conn, GROUP, source) is None)
    check("unlisted room", asyncio.run(conn.build_event(
        Room("!other:example.org", {BOT: "", ALEX: "", "@b:x": ""}), msg())) is None)

    async def encrypted() -> set:
        conn.on_room_event(conn.client.rooms[GROUP],
                           Obj(source={"type": "m.room.encrypted", "sender": ALEX}))
        return set(conn._tasks)

    check("an undecryptable event starts no turn", asyncio.run(encrypted()) == set())


def test_images_arrive_as_bytes() -> None:
    conn, client = make()
    client.media["mxc://example.org/pic"] = PNG
    image = build(conn, GROUP, msg("cat.png", msgtype="m.image", url="mxc://example.org/pic"))
    check("image inline", image["segments"] == [
        {"type": "image", "b64": base64.b64encode(PNG).decode(), "sticker": False}],
        repr(image["segments"]))
    captioned = build(conn, GROUP, msg("look at this", msgtype="m.image", filename="cat.png",
                                       url="mxc://example.org/pic"))
    check("caption", captioned["segments"][-1] == {"type": "text", "text": "look at this"})
    big = build(conn, GROUP, msg("huge.png", msgtype="m.image", url="mxc://example.org/pic",
                                 info={"size": mc.MAX_IMAGE_BYTES + 1}))
    check("too big is described", big["segments"] == [
        {"type": "text", "text": "(sent an image)"}], repr(big["segments"]))
    sticker = build(conn, GROUP, {"type": "m.sticker", "sender": ALEX, "event_id": "$s",
                                  "origin_server_ts": NOW * 1000,
                                  "content": {"body": "wave", "url": "mxc://example.org/pic"}})
    check("sticker", sticker["segments"][0]["sticker"] is True)
    lost = build(conn, GROUP, {"type": "m.sticker", "sender": ALEX, "event_id": "$s2",
                               "origin_server_ts": NOW * 1000,
                               "content": {"body": "wave", "url": "mxc://example.org/none"}})
    check("unreachable sticker is named", lost["segments"] == [
        {"type": "emoji", "name": "wave"}], repr(lost["segments"]))
    voice = build(conn, GROUP, msg("voice.ogg", msgtype="m.audio",
                                   **{"org.matrix.msc3245.voice": {}}))
    check("voice described", voice["raw_text"] == "(sent a voice message)")
    upload = build(conn, GROUP, msg("deck.pdf", msgtype="m.file"))
    check("file described", upload["raw_text"] == "(sent a file: deck.pdf)")

    calls = []

    def decrypt(data, key, sha256, iv):
        calls.append((data, key, sha256, iv))
        return PNG

    conn.decrypt = decrypt
    client.media["mxc://example.org/enc"] = b"ciphertext"
    secret = build(conn, GROUP, msg("x.png", msgtype="m.image", file={
        "url": "mxc://example.org/enc", "key": {"k": "KEY"}, "iv": "IV",
        "hashes": {"sha256": "SHA"}, "v": "v2"}))
    check("encrypted media is decrypted", calls == [(b"ciphertext", "KEY", "SHA", "IV")]
          and secret["segments"][0]["b64"] == base64.b64encode(PNG).decode())


def test_a_threaded_message_is_answered_in_its_thread() -> None:
    seen: list = []
    conn, client = make(answers=[{"owned": True, "replies": [{"type": "text", "text": "yes"}]}],
                        seen=seen)
    source = msg("in a thread", **{"m.relates_to": {
        "rel_type": "m.thread", "event_id": "$root", "is_falling_back": True,
        "m.in_reply_to": {"event_id": "$prev"}}})
    asyncio.run(conn.handle(client.rooms[GROUP], source))
    check("thread fallback is not a quote", not any(
        s["type"] == "reply" for s in seen[0]["segments"]), repr(seen[0]))
    check("no private field reaches the agent", "_thread_root" not in seen[0])
    relation = client.sent[0][1]["m.relates_to"]
    check("reply in the thread", relation == {
        "rel_type": "m.thread", "event_id": "$root", "is_falling_back": True,
        "m.in_reply_to": {"event_id": "$e1"}}, repr(relation))


# ---------- outbound ----------

def test_a_turn_sends_the_replies_in_order_with_typing() -> None:
    seen: list = []
    answer = {"handled": True, "owned": True, "replies": [
        {"type": "text", "text": "not bad, <rained>", "at_user_id": f"matrix:{ALEX}"},
        {"type": "image", "b64": base64.b64encode(PNG).decode()},
        {"type": "text", "text": "you?", "at_user_id": f"matrix:{BOT}"},
    ]}
    conn, client = make(answers=[answer], seen=seen)
    asyncio.run(conn.handle(client.rooms[GROUP], msg("how was your day?")))
    check("the event reached the agent", seen[0]["forwarder_id"] == "mx1"
          and seen[0]["message_id"] == "$e1")
    check("three messages", len(client.sent) == 3, repr(client.sent))
    first = client.sent[0][1]
    check("mention", first == {
        "msgtype": "m.text", "body": "Alex not bad, <rained>",
        "m.mentions": {"user_ids": [ALEX]}, "format": "org.matrix.custom.html",
        "formatted_body": '<a href="https://matrix.to/#/@alex:example.org">Alex</a> '
                          'not bad, &lt;rained&gt;'}, repr(first))
    image = client.sent[1][1]
    check("image uploaded", image["msgtype"] == "m.image" and image["url"] == "mxc://example.org/up1"
          and image["info"] == {"mimetype": "image/png", "size": len(PNG)}, repr(image))
    check("upload got the bytes", client.uploads[0]["data"] == PNG
          and client.uploads[0]["encrypt"] is False)
    check("the bot never mentions itself", client.sent[2][1] == {
        "msgtype": "m.text", "body": "you?", "m.mentions": {}}, repr(client.sent[2][1]))
    check("typing on first, off last", client.typing[0] == (GROUP, True)
          and client.typing[-1] == (GROUP, False), repr(client.typing))
    check("read receipt for an owned turn", client.read == [(GROUP, "$e1", "$e1")])
    check("typing tasks cleaned up", not conn._typing and not conn._typing_tasks)


def test_a_dm_reply_mentions_nobody_and_an_unowned_turn_is_left_unread() -> None:
    conn, client = make(answers=[
        {"owned": True, "replies": [{"type": "text", "text": "hey", "at_user_id": f"matrix:{ALEX}"}]},
        {"owned": False, "replies": []},
    ])
    asyncio.run(conn.handle(client.rooms[DM], msg()))
    check("no pill in a DM", client.sent == [(DM, {"msgtype": "m.text", "body": "hey",
                                                   "m.mentions": {}})], repr(client.sent))
    asyncio.run(conn.handle(client.rooms[DM], msg(event_id="$e2")))
    check("no receipt when the agent did not take it", client.read == [(DM, "$e1", "$e1")])


def test_encrypted_rooms_need_e2ee() -> None:
    secret = Room("!secret:example.org", {BOT: "Nova", ALEX: "Alex", "@bob:x": "Bob"},
                  encrypted=True)
    reply = {"owned": True, "replies": [{"type": "image", "b64": base64.b64encode(PNG).decode()}]}
    conn, client = make([secret], answers=[reply], e2ee=True, rooms=(secret.room_id,))
    asyncio.run(conn.handle(secret, msg()))
    content = client.sent[0][1]
    check("encrypted upload", client.uploads[0]["encrypt"] is True and "url" not in content
          and content["file"] == {"v": "v2", "key": {"k": "KEY"}, "iv": "IV",
                                  "hashes": {"sha256": "SHA"}, "url": "mxc://example.org/up1"},
          repr(content))
    plain, plain_client = make([secret], rooms=(secret.room_id,))
    status = asyncio.run(plain.deliver({"reply_handle": "!secret:example.org",
                                        "message_type": "group",
                                        "items": [{"type": "text", "text": "hi"}]}))
    check("never plaintext into an encrypted room", status == ("unsupported", 0)
          and plain_client.sent == [], repr(status))


def test_outbox_deliveries_go_to_the_reply_handle() -> None:
    conn, client = make()
    two = [{"type": "text", "text": "anyone up?"}, {"type": "text", "text": "hello?"}]
    check("sent", asyncio.run(conn.deliver({"reply_handle": GROUP, "message_type": "group",
                                            "conversation_id": GROUP, "items": two}))
          == ("sent", 2))
    check("in order", [c["body"] for _, c in client.sent] == ["anyone up?", "hello?"])
    check("dm", asyncio.run(conn.deliver({"reply_handle": DM, "message_type": "private",
                                          "conversation_id": ALEX, "items": two[:1]}))
          == ("sent", 1))
    check("unknown room", asyncio.run(conn.deliver({"reply_handle": "!gone:example.org",
                                                    "items": two})) == ("refused", 0))
    check("no longer allowed", asyncio.run(conn.deliver({
        "reply_handle": DM, "message_type": "private", "conversation_id": "@bob:example.org",
        "items": two})) == ("refused", 0))
    client.refuse_after = len(client.sent) + 1
    check("partial", asyncio.run(conn.deliver({"reply_handle": GROUP, "message_type": "group",
                                               "items": two})) == ("partial", 1))
    check("failed", asyncio.run(conn.deliver({"reply_handle": GROUP, "message_type": "group",
                                              "items": two})) == ("failed", 0))


# ---------- invites ----------

def test_invites_are_accepted_only_when_allowed() -> None:
    conn, client = make(invite_from=(BRIDGE,))

    def invite(room_id: str, sender: str, is_direct: bool = False, target: str = BOT):
        event = Obj(state_key=target, membership="invite", sender=sender,
                    content={"membership": "invite", "is_direct": is_direct})
        asyncio.run(conn.on_invite(Obj(room_id=room_id), event))

    invite(GROUP, "@bob:example.org")
    invite("!portal:example.org", BRIDGE)
    invite("!chat:example.org", ALEX, is_direct=True)
    invite("!spam:example.org", "@spammer:evil.example")
    invite("!group2:example.org", ALEX)
    invite("!notme:example.org", BRIDGE, target=ALEX)
    check("joined", client.joined == [GROUP, "!portal:example.org", "!chat:example.org"],
          repr(client.joined))
    check("a direct invite marks a DM", conn.direct_rooms == {"!chat:example.org"})


# ---------- the matrix-nio wiring ----------

def fake_nio(rooms: list):
    nio = types.ModuleType("nio")

    class Event:
        def __init__(self, source):
            self.source = source

    class RoomMessage(Event):
        pass

    class StickerEvent(Event):
        pass

    class MegolmEvent(Event):
        pass

    class InviteMemberEvent(Event):
        pass

    class AsyncClientConfig:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class AsyncClient(Client):
        instances: list = []

        def __init__(self, homeserver, user="", device_id=None, store_path="", config=None):
            super().__init__(rooms)
            self.user_id = user
            self.homeserver, self.config = homeserver, config
            self.callbacks: list = []
            self.should_upload_keys = False
            self.closed = False
            self.syncs = 0
            AsyncClient.instances.append(self)

        def add_event_callback(self, callback, filter):
            self.callbacks.append((callback, filter))

        async def whoami(self):
            return Obj(user_id=BOT, device_id="DEV")

        def restore_login(self, user_id, device_id, access_token):
            self.user_id, self.device_id, self.access_token = user_id, device_id, access_token

        async def _dispatch(self, events):
            for room_id, event in events:
                for callback, kinds in self.callbacks:
                    if isinstance(event, kinds):
                        result = callback(self.rooms[room_id], event)
                        if inspect.isawaitable(result):
                            await result

        async def sync(self, timeout=0, full_state=None, **_):
            self.syncs += 1
            await self._dispatch(nio.backlog)
            return Obj(next_batch="s1")

        async def sync_forever(self, timeout=None, **_):
            await self._dispatch(nio.live)
            await asyncio.Event().wait()

        async def close(self):
            self.closed = True

    for cls in (RoomMessage, StickerEvent, MegolmEvent, InviteMemberEvent, AsyncClientConfig,
                AsyncClient):
        setattr(nio, cls.__name__, cls)
    return nio


def test_run_skips_the_backlog_and_serves_events_and_the_outbox() -> None:
    rooms = [Room(GROUP, {BOT: "Nova", ALEX: "Alex", "@bob:example.org": "Bob"})]
    fresh = int(time.time()) * 1000
    nio = fake_nio(rooms=rooms)
    nio.backlog = [(GROUP, nio.RoomMessage(msg("old news", event_id="$b", ts=fresh)))]
    nio.live = [(GROUP, nio.RoomMessage(msg("hi Nova", event_id="$l", ts=fresh)))]
    seen: list = []
    pulls = [{"deliveries": [{"delivery_id": "d1", "reply_handle": GROUP,
                              "message_type": "group", "conversation_id": GROUP,
                              "expires_in_s": 300,
                              "items": [{"type": "text", "text": "good morning"}]}]}]
    answers = [{"owned": True, "replies": [{"type": "text", "text": "hi Alex"}]}]
    stop = asyncio.Event()

    async def main() -> None:
        runner = asyncio.ensure_future(mc.run(
            settings(user_id="", device_id=""), nio_module=nio,
            agent_client=agent_client(answers, seen, pulls), stop=stop))
        for _ in range(500):
            client = (nio.AsyncClient.instances or [None])[0]
            acked = any(a.get("delivery_id") == "d1" for p in seen for a in p.get("acks", []))
            if client is not None and len(client.sent) >= 2 and acked:
                break
            await asyncio.sleep(0.01)
        stop.set()
        await asyncio.wait_for(runner, 5)

    asyncio.run(main())
    client = nio.AsyncClient.instances[0]
    events = [p for p in seen if p.get("platform") == "matrix"]
    check("the backlog was not forwarded", [e["message_id"] for e in events] == ["$l"],
          repr(events))
    check("token login learned who it is", events[0]["self_id"] == BOT
          and client.device_id == "DEV")
    check("the default forwarder id", events[0]["forwarder_id"] == mc.default_forwarder_id(BOT))
    bodies = sorted(c["body"] for _, c in client.sent)
    check("reply and outbox delivery sent", bodies == ["good morning", "hi Alex"], repr(bodies))
    check("pulls use the same forwarder id", all(
        p["forwarder_id"] == mc.default_forwarder_id(BOT) for p in seen
        if p.get("kind") == "outbox.pull"))
    check("encryption off unless asked", client.config.kwargs == {
        "encryption_enabled": False, "store_sync_tokens": False})
    check("closed", client.closed)
