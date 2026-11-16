"""What keeps a connected platform working: a failed item does not drop the
rest of a reply, a platform out of reach or refusing says so, the typing sign
shows only where an answer follows, and the fixes per platform. Every
platform is a stand-in: no network, no accounts."""
from __future__ import annotations

import asyncio
import base64
import json
import re
import time
from pathlib import Path

import httpx
import pytest

from persona_agent import connections as conn
from persona_agent import direct, direct_setup, mirrors
from persona_agent import setup_wizard as sw
from persona_agent.direct import base, discord, irc, matrix, qq, stoat, telegram, twitch, vk, weixin, zulip
from test_direct_irc import connector, values as irc_values

PNG = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"0" * 16).decode()
ROOT = Path(__file__).resolve().parents[1]


def run(coro):
    return asyncio.run(coro)


def mock(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


REPLY = [{"type": "image", "b64": PNG}, {"type": "text", "text": "after the picture"}]


# ---------------------------------------------------------------- 1. one failed item

def test_a_failed_picture_is_skipped_and_the_text_still_goes_on_every_platform_that_sends_pictures(caplog):
    texts: dict[str, list[str]] = {}

    def record(kind, text):
        texts.setdefault(kind, []).append(text)

    def tg(request):
        if request.url.path.endswith("/sendPhoto"):
            return httpx.Response(500, json={"ok": False, "error_code": 500})
        record("telegram", json.loads(request.content)["text"])
        return httpx.Response(200, json={"ok": True, "result": {}})

    def dc(request):
        if b"multipart/form-data" in request.headers.get("content-type", "").encode():
            return httpx.Response(500)
        record("discord", json.loads(request.content)["content"])
        return httpx.Response(200, json={"id": "1"})

    def vk_api(request):
        method = request.url.path.rsplit("/", 1)[-1]
        if method == "photos.getMessagesUploadServer":
            return httpx.Response(500)
        if method == "messages.send":
            record("vk", dict(httpx.QueryParams(request.content.decode()))["message"])
            return httpx.Response(200, json={"response": 1})
        raise AssertionError(method)

    def zp(request):
        if request.url.path.endswith("/user_uploads"):
            return httpx.Response(500)
        record("zulip", dict(httpx.QueryParams(request.content.decode()))["content"])
        return httpx.Response(200, json={"result": "success", "id": 1})

    def mx(request):
        if "/media/" in request.url.path:
            return httpx.Response(500, json={})
        if "/send/" in request.url.path:
            record("matrix", json.loads(request.content)["body"])
            return httpx.Response(200, json={"event_id": "$1"})
        return httpx.Response(200, json={})

    def st(request):
        if request.url.host == "cdn.stoat.test":
            return httpx.Response(500, json={})
        if request.url.path == "/":
            return httpx.Response(200, json={"revolt": "0.16", "ws": "wss://e",
                                             "features": {"autumn": {"enabled": True,
                                                                     "url": "https://cdn.stoat.test"}}})
        record("stoat", json.loads(request.content)["content"])
        return httpx.Response(200, json={"_id": "M1"})

    bots = {
        "telegram": telegram.Telegram({"telegram_token": "t"}, client=mock(tg)),
        "discord": discord.Discord({"discord_token": "t"}, client=mock(dc)),
        "vk": vk.VK({"vk_token": "t"}, client=mock(vk_api)),
        "zulip": zulip.Zulip({"zulip_site": "https://z.example", "zulip_email": "b@z", "zulip_api_key": "k"},
                             client=mock(zp)),
        "matrix": matrix.Matrix({"matrix_homeserver": "https://m.example", "matrix_token": "syt_x",
                                 "matrix_owner": "@me:m.example"}, client=mock(mx)),
        "stoat": stoat.Stoat({"stoat_token": "t", "stoat_api": "https://api.stoat.test"}, client=mock(st)),
    }
    bots["matrix"].bot_id = "@nova:m.example"
    targets = {"telegram": "-100", "discord": "300", "vk": "42", "zulip": "stream/12/x",
               "matrix": "!room:m.example", "stoat": "C1"}
    for kind, bot in bots.items():
        assert run(bot.send(targets[kind], REPLY)) == 1, kind
        assert texts.get(kind) == ["after the picture"], (kind, texts.get(kind))
    logged = "\n".join(r.getMessage() for r in caplog.records)
    assert "a picture was not sent" in logged and PNG not in logged


class Writer:
    def __init__(self, fail_first):
        self.lines, self.fail = [], fail_first

    def write(self, data):
        if self.fail:
            self.fail = False
            raise OSError("reset")
        self.lines.append(data.decode().strip())

    async def drain(self):
        pass


def test_a_failed_message_does_not_stop_the_messages_after_it_on_the_text_platforms(monkeypatch):
    items = [{"type": "text", "text": "one"}, {"type": "text", "text": "two"}]
    # WeChat: the first send is answered with an error, the second goes.
    answers = iter([{"ret": 1}, {"ret": 0}])
    wx = weixin.Weixin({"weixin_oc_token": "bt"}, state=Path("unused.json"),
                       client=mock(lambda r: httpx.Response(200, json=next(answers))))
    assert run(wx.send("u@im.wechat", items)) == 1
    # QQ: a 500 for the first message only.
    posts = []

    def qq_api(request):
        posts.append(json.loads(request.content)["content"])
        return httpx.Response(500, json={}) if len(posts) == 1 else httpx.Response(200, json={"id": "m"})
    bot = qq.QQ({"appid": "1", "secret": "s"}, client=mock(qq_api))
    bot.token, bot.token_until = "tok", time.monotonic() + 600
    assert run(bot.send(("c2c", "u1"), items)) == 1 and posts == ["one", "two"]
    # IRC: the first write fails, the next line still goes.
    monkeypatch.setattr(irc, "_pause", lambda seconds: asyncio.sleep(0))
    chat = irc.IRC(irc_values())
    chat._writer = Writer(fail_first=True)
    assert run(chat.send("#room", items)) == 1 and chat._writer.lines == ["PRIVMSG #room :two"]


def test_a_refusal_for_the_chat_still_stops_the_rest():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(403, json={"ok": False, "error_code": 403})
    bot = telegram.Telegram({"telegram_token": "t"}, client=mock(handler))
    assert run(bot.send("-100", [{"type": "text", "text": "a"}, {"type": "text", "text": "b"}])) == 0
    assert len(calls) == 1


# ---------------------------------------------------------------- 2. out of reach, refusing

class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


class Quiet(base.Platform):
    kind = "telegram"


def bridge(tmp_path):
    status = base.Status(tmp_path)
    b = base.Bridge(Quiet({}), agent=None, status=status)
    b._clock = Clock()
    return b, status


def test_a_platform_that_cannot_be_reached_says_so_after_two_minutes_and_recovers(tmp_path):
    b, status = bridge(tmp_path)
    b.failed(ConnectionError("getUpdates: ConnectError"))
    assert status.states["telegram"]["state"] == "connecting"
    b._clock.now += base.UNREACHABLE_S - 1
    b.failed(ConnectionError("getUpdates: ConnectError"))
    assert status.states["telegram"]["state"] == "connecting"
    b._clock.now += 2
    b.failed(ConnectionError("getUpdates: ConnectError"))
    assert status.states["telegram"] == {**status.states["telegram"], "state": "retrying", "detail": "unreachable"}
    assert base.read_status(tmp_path)["telegram"]["detail"] == "unreachable"
    # The next accepted session sets it back by itself.
    b.platform.run = lambda on_event, up: asyncio.sleep(0, up())   # type: ignore[assignment]
    run(b._receive(asyncio.Event()))
    assert status.states["telegram"]["state"] == "connected" and b._down_since is None


def test_repeated_401_or_403_is_named_and_one_alone_is_not(tmp_path):
    b, status = bridge(tmp_path)
    b.failed(ConnectionError("/gateway/bot: 403"))
    b.failed(ConnectionError("/gateway/bot: 403"))
    assert status.states["telegram"]["state"] == "connecting"
    b.failed(ConnectionError("/gateway/bot: 403"))
    assert status.states["telegram"]["detail"] == "access_denied"
    assert base.trouble(ConnectionError("x: 500")) == "" and base.trouble(base.Denied("access_denied"))
    # A pause the platform asked for is named at once.
    b.failed(base.Paused("session_paused"))
    assert status.states["telegram"]["detail"] == "session_paused"


def test_every_named_cause_has_a_sentence_on_the_page_and_in_the_terminal():
    page = (ROOT / "persona_agent/static/welcome/welcome.js").read_text(encoding="utf-8")
    new = ("unreachable", "access_denied", "session_paused", "need_verifycode", "verify_code_blocked",
           "binded_redirect", "token_missing", "login_denied", "invalid_intents", "invalid_shard",
           "sharding_required", "invalid_api_version", "sign_in_expired", "token_short_lived",
           "login_rejected", "login_unsupported", "sign_in_missing", "invite_declined")
    for code in new:
        assert code in direct_setup.NAMED_REFUSALS, code
        assert len(re.findall(rf"^    {code}:", page, re.M)) == 2, code     # en and zh
        assert f"refused_{code}" in sw._TEXT, code
    assert "proxy" in sw._TEXT["refused_unreachable"][0] and "代理" in sw._TEXT["refused_unreachable"][1]
    for word in discord.FATAL.values():
        assert word in direct_setup.NAMED_REFUSALS, word
    for word in qq.FATAL.values():
        assert word in direct_setup.NAMED_REFUSALS, word


def test_the_doctor_says_why_a_platform_is_retrying(monkeypatch):
    from persona_agent import doctor

    mark, words = doctor.direct_row({"running": True, "platforms": [
        {"id": "telegram", "state": "retrying", "detail": "unreachable"}]})
    assert "cannot reach" in words and "proxy" in words


# ---------------------------------------------------------------- 3. proxies

def test_websockets_has_proxy_support_and_no_connector_turns_it_off(monkeypatch):
    # Read as text: tomllib arrived in Python 3.11.
    floor = re.search(r'"(websockets[^"]*)"', (ROOT / "pyproject.toml").read_text(encoding="utf-8")).group(1)
    assert ">=15" in floor
    import websockets

    seen = []

    async def connect(url, **kwargs):
        seen.append(kwargs)
        raise OSError("stand-in")
    monkeypatch.setattr(websockets, "connect", connect)
    platforms = [discord.Discord({"discord_token": "t"}), qq.QQ({"appid": "1", "secret": "s"}),
                 twitch.Twitch({"twitch_client_id": "c", "twitch_channels": "x"}, state=Path("unused.json")),
                 stoat.Stoat({"stoat_token": "t"})]
    for platform in platforms:
        with pytest.raises(OSError):
            run(platform._open("wss://gateway.example"))
    # The default, proxy=True, follows the environment and the system's settings.
    assert len(seen) == 4 and all("proxy" not in kwargs for kwargs in seen)
    for platform in platforms:
        assert platform.client._trust_env


# ---------------------------------------------------------------- 4, 10. named refusals, terminal verdict

class Socket:
    def __init__(self, frames, close_code=None):
        self.frames, self.close_code, self.sent = [json.dumps(f) for f in frames], close_code, []

    async def recv(self):
        return self.frames.pop(0)

    async def send(self, data):
        self.sent.append(json.loads(data))

    async def close(self, code=1000):
        pass

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self.frames:
            raise StopAsyncIteration
        return self.frames.pop(0)


def discord_rest(request):
    if request.url.path.endswith("/users/@me"):
        return httpx.Response(200, json={"id": "900", "username": "nova"})
    if request.url.path.endswith("/gateway/bot"):
        return httpx.Response(200, json={"url": "wss://gateway.example"})
    return httpx.Response(200, json={"id": "1"})


@pytest.mark.parametrize("code,word", [(4013, "invalid_intents"), (4011, "sharding_required"),
                                       (4012, "invalid_api_version"), (4014, "message_content_intent_off")])
def test_the_terminal_waits_for_the_gateway_verdict_as_the_page_does(tmp_path, monkeypatch, capsys, code, word):
    monkeypatch.setenv("AGENT_HOME", str(tmp_path))
    socket = Socket([{"op": 10, "d": {"heartbeat_interval": 45000}}], close_code=code)

    def platform_for(kind, values, home):
        return discord.Discord(values, client=mock(discord_rest), connect=lambda url: asyncio.sleep(0, socket))
    monkeypatch.setattr(direct, "platform_for", platform_for)
    assert sw.connect_main(["discord", "--no-input", "--discord-token", "tok"]) == 1
    err = capsys.readouterr().err
    assert sw._TEXT[f"refused_{word}"][0] in err
    assert base.load_credentials(tmp_path) == {}


def test_a_gateway_that_accepts_is_saved(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENT_HOME", str(tmp_path))
    ready = {"op": 0, "t": "READY", "s": 1, "d": {"session_id": "s", "resume_gateway_url": "wss://r",
                                                  "user": {"id": "900"}}}

    def platform_for(kind, values, home):
        return discord.Discord(values, client=mock(discord_rest),
                               connect=lambda url: asyncio.sleep(0, Socket([{"op": 10, "d": {
                                   "heartbeat_interval": 45000}}, ready])))
    monkeypatch.setattr(direct, "platform_for", platform_for)
    assert sw.connect_main(["discord", "--no-input", "--discord-token", "tok"]) == 0
    assert base.load_credentials(tmp_path) == {"discord": {"discord_token": "tok"}}
    assert direct_setup.verdict({"state": "refused", "detail": "invalid_intents"}) == "invalid_intents"
    assert direct_setup.verdict({"state": "retrying", "detail": "access_denied"}) == "access_denied"
    assert direct_setup.verdict({"state": "retrying", "detail": "unreachable"}) == ""


def test_wechat_scan_results_and_twitch_denial_are_named():
    async def scan(statuses):
        answers = iter([{"qrcode": "q", "qrcode_img_content": "https://qr"}, *statuses])

        def handler(request):
            return httpx.Response(200, json=next(answers))
        async with mock(handler) as client:
            return await weixin.login(client, lambda content: None)
    for status, code in (("need_verifycode", "need_verifycode"),
                         ("confirmed_but_need_verifycode", "need_verifycode"),
                         ("verify_code_blocked", "verify_code_blocked"), ("binded_redirect", "binded_redirect")):
        with pytest.raises(weixin.LoginFailed, match=code):
            run(scan([{"status": status}]))
    with pytest.raises(base.Refused, match="token_missing"):
        run(weixin.Weixin({}, state=Path("unused.json")).check())


# ---------------------------------------------------------------- 5. WeChat

def test_a_wechat_message_without_an_id_gets_the_same_id_each_time_it_arrives():
    bot = weixin.Weixin({"weixin_oc_token": "bt"}, state=Path("unused.json"))
    message = {"message_type": 1, "from_user_id": "u@im.wechat", "create_time_ms": 1790000000000,
               "item_list": [{"type": 1, "text_item": {"text": "hi"}}]}
    first, again = bot.event(dict(message)), bot.event(dict(message))
    assert first["message_id"] == again["message_id"] and first["message_id"].startswith("h")
    other = bot.event({**message, "create_time_ms": 1790000000001})
    assert other["message_id"] != first["message_id"]
    assert bot.event({**message, "client_id": "c-1"})["message_id"] == "c-1"


def test_wechat_minus_14_pauses_the_session_instead_of_ending_the_login(tmp_path, monkeypatch):
    answers = iter([{"ret": 0}, {"ret": -14}, {"ret": 0, "msgs": []}, "stop"])
    states, waits = [], []

    def handler(request):
        answer = next(answers)
        if answer == "stop":
            return httpx.Response(401, json={})
        return httpx.Response(200, json=answer)

    async def pause(seconds):
        waits.append(seconds)
    monkeypatch.setattr(weixin, "_pause", pause)
    bot = weixin.Weixin({"weixin_oc_token": "bt"}, state=tmp_path / "s.json", client=mock(handler))
    bot.dropped = lambda cause=None: states.append(str(cause))
    with pytest.raises(base.Refused, match="session_expired"):
        run(bot.run(None, lambda: states.append("connected")))
    assert waits == [weixin.PAUSE_S] and states == ["session_paused", "connected"]


# ---------------------------------------------------------------- 6. Discord role mentions

def test_a_mention_of_the_bots_own_role_addresses_it():
    bot = discord.Discord({"discord_token": "t"}, client=mock(discord_rest))
    bot.bot_id = "900"
    run(bot._dispatch("GUILD_CREATE", {"roles": [{"id": "R1", "tags": {"bot_id": "900"}},
                                                 {"id": "R2", "tags": {"bot_id": "901"}}, {"id": "R3"}]},
                      None, lambda: None))
    assert bot.own_roles == {"R1"}
    base_message = {"id": "5", "channel_id": "300", "guild_id": "1", "author": {"id": "42", "username": "a"},
                    "timestamp": "2026-11-16T10:00:00Z"}
    own = bot.event({**base_message, "content": "<@&R1> hello", "mention_roles": ["R1"]})
    assert own["addressed"] is True and own["text"] == "hello"
    assert {"type": "mention", "user_id": "900", "name": ""} in own["segments"]
    other = bot.event({**base_message, "content": "<@&R2> hello", "mention_roles": ["R2"]})
    assert other["addressed"] is False


# ---------------------------------------------------------------- 7. Telegram offset

def test_telegram_keeps_its_update_offset_across_a_restart(tmp_path):
    offsets = []
    answers = iter([{"ok": True, "result": {"id": 7, "username": "Nova"}}, {"ok": True, "result": True},
                    {"ok": True, "result": [{"update_id": 41, "message": {
                        "message_id": 1, "date": 1, "chat": {"id": 5, "type": "private"},
                        "from": {"id": 5, "first_name": "A"}, "text": "hi"}}]},
                    {"ok": False, "error_code": 401}])

    def handler(request):
        if request.url.path.endswith("/getUpdates"):
            offsets.append(json.loads(request.content)["offset"])
        return httpx.Response(200, json=next(answers))
    state = direct.state_path(tmp_path, "telegram")
    bot = telegram.Telegram({"telegram_token": "1:a"}, client=mock(handler), state=state)

    async def on_event(event, target):
        pass
    with pytest.raises(base.Refused):
        run(bot.run(on_event, lambda: None))
    assert offsets == [0, 42]
    again = direct.platform_for("telegram", {"telegram_token": "1:a"}, tmp_path)
    assert again.offset == 42
    assert "1:a" not in state.read_text(encoding="utf-8")
    other_bot = telegram.Telegram({"telegram_token": "2:b"}, state=state)
    assert other_bot.offset == 0


# ---------------------------------------------------------------- 8. VK forwards

def test_vk_forwards_are_forward_segments_not_the_senders_words():
    def handler(request):
        method = request.url.path.rsplit("/", 1)[-1]
        assert method == "users.get"
        return httpx.Response(200, json={"response": [{"first_name": "Boris", "last_name": "K"}]})
    bot = vk.VK({"vk_token": "t"}, client=mock(handler))
    bot.group_id, bot.bot_id, bot.names["42"] = 77, "-77", "Alex"
    event = run(bot.event({"id": 3, "date": 1, "peer_id": 42, "from_id": 42, "text": "look",
                           "fwd_messages": [{"from_id": 7, "text": "[club77|Nova] you there?"}]}))
    assert event["segments"] == [{"type": "text", "text": "look"}, {"type": "forward", "name": "Boris K"},
                                 {"type": "text", "text": "you there?"}]
    assert "(forwarded messages)" not in json.dumps(event)
    only = run(bot.event({"id": 4, "date": 1, "peer_id": 2000000001, "from_id": 42, "text": "",
                          "fwd_messages": [{"from_id": 7, "text": "[club77|Nova] hi"}]}))
    assert only["addressed"] is False and only["text"] == "hi"


# ---------------------------------------------------------------- 9. typing sign

class Agent:
    def __init__(self, replies):
        self.replies = replies

    async def send_event(self, event):
        await asyncio.sleep(0.05)
        return {"replies": self.replies}


class Signs(base.Platform):
    kind = "matrix"

    def __init__(self):
        super().__init__({})
        self.signs, self.done = [], []

    async def typing(self, target):
        self.signs.append(target)

    async def typing_done(self, target):
        self.done.append(target)

    async def send(self, target, items):
        return len(items)


@pytest.mark.typing_pace
def test_the_typing_sign_shows_only_where_an_answer_is_expected(tmp_path, monkeypatch):
    monkeypatch.setattr(base, "READ_S", (0.0, 0.0))
    monkeypatch.setattr(base, "item_delay", lambda item: 0.0)

    def turn(event, replies, admits=None):
        platform = Signs()
        b = base.Bridge(platform, Agent(replies), base.Status(tmp_path), admits=admits)

        async def go():
            await b._turn({"platform": "matrix", **event}, "!r")
        run(go())
        return platform
    dm = turn({"conversation_type": "dm"}, [])
    assert dm.signs and dm.done == ["!r"]       # one-to-one as before; a quiet answer takes the sign down
    chatter = turn({"conversation_type": "group", "conversation_id": "!r", "addressed": False}, [])
    assert not chatter.signs
    called = turn({"conversation_type": "group", "conversation_id": "!r", "addressed": True},
                  [{"type": "text", "text": "yes"}])
    assert called.signs and not called.done
    shut = turn({"conversation_type": "group", "conversation_id": "!r", "addressed": True}, [],
                admits=lambda event: False)
    assert not shut.signs


def test_the_settings_decide_which_addressed_groups_are_answered(tmp_path):
    from persona_agent.direct.__main__ import admits

    env = tmp_path / ".env"
    env.write_text("ACCESS_GROUPS=telegram:-100\n", encoding="utf-8")
    answered = admits(tmp_path)
    assert answered({"platform": "telegram", "conversation_id": "-100"})
    assert not answered({"platform": "telegram", "conversation_id": "-200"})
    assert answered({"platform": "discord", "conversation_id": "9"})
    env.write_text("AGENT_ENABLED=false\n", encoding="utf-8")
    import os
    os.utime(env, ns=(time.time_ns() + 10**9, time.time_ns() + 10**9))
    assert not answered({"platform": "discord", "conversation_id": "9"})


def test_matrix_no_longer_types_on_receipt_and_takes_the_sign_down(tmp_path):
    puts = []

    def handler(request):
        puts.append((request.url.path, json.loads(request.content or b"{}")))
        return httpx.Response(200, json={})
    bot = matrix.Matrix({"matrix_homeserver": "https://m.example", "matrix_token": "syt_x",
                         "matrix_owner": "@me:m.example"}, client=mock(handler))
    bot.bot_id = "@nova:m.example"
    run(bot.typing_done("!r:m.example"))
    assert puts and "/typing/" in puts[0][0] and puts[0][1] == {"typing": False}
    assert matrix.TYPING_MS <= 10_000


# ---------------------------------------------------------------- 11. Matrix sign-in

class Homeserver:
    def __init__(self, login_status=200, flows=("m.login.password",)):
        self.login_status, self.flows, self.logins = login_status, flows, []

    def __call__(self, request):
        path = request.url.path
        if path.endswith("/.well-known/matrix/client"):
            return httpx.Response(404)
        if path.endswith("/login") and request.method == "GET":
            return httpx.Response(200, json={"flows": [{"type": f} for f in self.flows]})
        if path.endswith("/login"):
            body = json.loads(request.content)
            self.logins.append(body)
            if self.login_status != 200:
                return httpx.Response(self.login_status, json={"errcode": "M_FORBIDDEN"})
            return httpx.Response(200, json={"access_token": "mct_lasting", "device_id": "DEV1",
                                             "user_id": "@nova:m.example"})
        if path.endswith("/account/whoami"):
            ok = request.headers.get("authorization") in ("Bearer mct_lasting", "Bearer syt_old", "Bearer mat_short")
            return httpx.Response(200 if ok else 401, json={"user_id": "@nova:m.example"} if ok else
                                  {"errcode": "M_UNKNOWN_TOKEN"})
        return httpx.Response(200, json={})


def matrix_values(**extra):
    return {"matrix_homeserver": "https://m.example", "matrix_owner": "@me:m.example", **extra}


def test_matrix_signs_in_with_a_password_once_and_keeps_only_the_token(tmp_path):
    server = Homeserver()
    bot = matrix.Matrix(matrix_values(matrix_user="@nova:m.example", matrix_password="hunter2"),
                        client=mock(server))
    run(bot.check())
    kept = bot.keep()
    assert kept["matrix_token"] == "mct_lasting" and kept["matrix_device_id"] == "DEV1"
    assert "matrix_password" not in kept and "hunter2" not in json.dumps(kept)
    login = server.logins[0]
    assert login["type"] == "m.login.password" and login["identifier"] == {"type": "m.id.user",
                                                                           "user": "@nova:m.example"}
    assert "refresh_token" not in login
    for status, code in ((403, "login_rejected"),):
        with pytest.raises(base.Refused, match=code):
            run(matrix.Matrix(matrix_values(matrix_user="@n:m", matrix_password="x"),
                              client=mock(Homeserver(login_status=status))).check())
    with pytest.raises(base.Refused, match="login_unsupported"):
        run(matrix.Matrix(matrix_values(matrix_user="@n:m", matrix_password="x"),
                          client=mock(Homeserver(flows=("m.login.sso",)))).check())
    with pytest.raises(base.Refused, match="sign_in_missing"):
        run(matrix.Matrix(matrix_values(), client=mock(Homeserver())).check())


def test_a_short_lived_element_token_is_refused_before_saving(tmp_path):
    with pytest.raises(base.Refused, match="token_short_lived"):
        run(matrix.Matrix(matrix_values(matrix_token="mat_short"), client=mock(Homeserver())).check())
    # A token that does not expire, on a homeserver without MAS, is kept as before.
    bot = matrix.Matrix(matrix_values(matrix_token="syt_old"), client=mock(Homeserver()))
    run(bot.check())
    assert bot.keep()["matrix_token"] == "syt_old"


def test_the_page_stores_what_the_password_sign_in_brought(tmp_path, monkeypatch):
    monkeypatch.setattr(direct, "platform_for",
                        lambda kind, values, home: matrix.Matrix(values, client=mock(Homeserver())))
    kept = direct_setup.check(tmp_path, conn.platform("matrix"),
                              matrix_values(matrix_user="@nova:m.example", matrix_password="hunter2",
                                            matrix_token=""))
    assert kept["matrix_token"] == "mct_lasting" and "matrix_password" not in kept


def test_a_declined_invite_from_another_id_is_told(tmp_path, caplog):
    bot = matrix.Matrix(matrix_values(matrix_token="syt_old"), client=mock(lambda r: httpx.Response(200, json={})))
    bot.bot_id = "@nova:m.example"
    notices = []
    bot.notice = notices.append
    invite = {"invite_state": {"events": [{"type": "m.room.member", "state_key": "@nova:m.example",
                                           "sender": "@typo:m.example", "content": {"membership": "invite"}}]}}
    run(bot._invite("!r:m.example", invite))
    assert notices == ["invite_declined"]
    assert "other than the owner" in caplog.text


# ---------------------------------------------------------------- 12. cards

def test_the_cards_carry_the_steps_the_audit_found_missing():
    for kind in ("lark", "dingtalk", "slack", "wecom_ai_bot"):
        assert conn.platform(kind).steps, kind
    discord_steps = " ".join(en for en, _ in conn.platform("discord").steps)
    assert "Public Bot" in discord_steps and "Read Message History" in discord_steps
    number = (1 << 10) | (1 << 11) | (1 << 38) | (1 << 15) | (1 << 16)
    assert f"permissions={number}" in discord_steps
    telegram_steps = " ".join(en for en, _ in conn.platform("telegram").steps)
    assert "/setjoingroups" in telegram_steps and "administrator" in telegram_steps
    assert "mention" not in telegram_steps.split("privacy mode.")[1].split("Disable")[0]
    matrix_card = conn.platform("matrix")
    assert {f.key for f in matrix_card.fields} >= {"matrix_user", "matrix_password", "matrix_token"}
    assert "Start chat" in " ".join(en for en, _ in matrix_card.steps)
    assert "admin" in " ".join(en for en, _ in conn.platform("irc").steps)


# ---------------------------------------------------------------- 13. who the bot answers

def test_each_connected_platform_says_who_it_answers():
    from persona_agent.welcome import reach

    assert reach("telegram", {}) == "all"
    assert reach("telegram", {"ACCESS_GROUPS": "telegram:-1"}) == "groups_listed"
    assert reach("telegram", {"ACCESS_DM_USERS": "telegram:5"}) == "people_listed"
    assert reach("telegram", {"ACCESS_GROUPS": "telegram:-1", "ACCESS_DM_USERS": "telegram:5"}) == "listed"
    assert reach("telegram", {"ACCESS_GROUPS": "discord:1"}) == "all"
    assert reach("weixin_oc", {}) == "dm_all"
    page = (ROOT / "persona_agent/static/welcome/welcome.js").read_text(encoding="utf-8")
    for key in ("reach_all", "reach_groups_listed", "reach_people_listed", "reach_listed", "reach_dm_all",
                "reach_dm_listed", "reach_public_bot", "reachLimit", "reachChange"):
        assert len(re.findall(rf"^    {key}:", page, re.M)) == 2, key


# ---------------------------------------------------------------- 14. the AstrBot download

def test_the_download_uses_mirrors_where_pypi_or_github_cannot_be_reached(tmp_path, monkeypatch):
    from persona_agent import astrbot_install as installer

    monkeypatch.setattr(installer.venv.EnvBuilder, "create", lambda self, path: None)
    installation = installer.AstrBotInstallation(tmp_path)
    calls, steps = [], []

    def finish(argv, **kw):
        calls.append((argv, kw["env"]))
        if "tool" in argv:
            for path in (installation.executable, installation.python):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("", encoding="utf-8")
        elif "init" in argv:
            (installation.root / ".astrbot").write_text("", encoding="utf-8")
        elif "-c" in argv:
            (installation.root / "data").mkdir(parents=True, exist_ok=True)
            (installation.root / "data/cmd_config.json").write_text("{}", encoding="utf-8")

    probed = []
    installer.install_astrbot(tmp_path, run=finish, step=steps.append,
                              probe=lambda url: probed.append(url) or "pypi.org" in url)
    assert probed == [mirrors.PYPI_PROBE, mirrors.GITHUB_PROBE]
    uv = next((argv, env) for argv, env in calls if "tool" in argv)
    assert mirrors.INDEX_MIRRORS[0] not in uv[0]        # PyPI answered
    assert uv[1]["UV_PYTHON_INSTALL_MIRROR"] == mirrors.PYTHON_MIRROR     # GitHub did not
    assert steps[:3] == ["network", "tools", "astrbot"] and steps[-1] == "prepare"


def test_a_failed_plain_download_is_tried_once_more_through_every_mirror(tmp_path, monkeypatch):
    import subprocess

    from persona_agent import astrbot_install as installer

    monkeypatch.setattr(installer.venv.EnvBuilder, "create", lambda self, path: None)
    calls, steps = [], []

    def fail(argv, **kw):
        calls.append((argv, kw["env"]))
        if "tool" in argv:
            raise subprocess.CalledProcessError(1, argv)
    with pytest.raises(subprocess.CalledProcessError):
        installer.install_astrbot(tmp_path, run=fail, step=steps.append, probe=lambda url: True)
    tools = [(argv, env) for argv, env in calls if "tool" in argv]
    pips = [argv for argv, _ in calls if "pip" in argv and "install" in argv]
    assert len(tools) == 2 and "--default-index" not in tools[0][0]
    assert tools[1][0][tools[1][0].index("--default-index") + 1] == mirrors.INDEX_MIRRORS[0]
    assert tools[1][1]["UV_PYTHON_INSTALL_MIRROR"] == mirrors.PYTHON_MIRROR
    assert mirrors.INDEX_MIRRORS[0] in pips[1] and mirrors.INDEX_MIRRORS[0] not in pips[0]
    assert "mirror" in steps
    monkeypatch.setenv("PERSONAGENT_MIRROR", "off")
    assert mirrors.attempts(mirrors.choose(lambda url: False)) == [mirrors.Route()]


def test_a_download_that_makes_no_progress_is_stopped(tmp_path, monkeypatch):
    import sys

    from persona_agent import services as svc
    from persona_agent.astrbot_install import DownloadStalled

    monkeypatch.setattr(svc, "STALL_LOOK_S", 0.2)
    services = svc.Services(tmp_path)
    started = time.monotonic()
    with pytest.raises(DownloadStalled):
        services.run("install", [sys.executable, "-c", "import time; time.sleep(30)"], env=dict(__import__("os").environ),
                     progress=lambda: 0, stall_s=1.0)
    assert time.monotonic() - started < 15 and not services.running("install")
    services.close()


# ---------------------------------------------------------------- 15. IRC

def test_irc_identifies_with_nickserv_before_it_joins(monkeypatch):
    monkeypatch.setattr(irc, "IDENTIFY_WAIT_S", 5)

    def script(server, line):
        if line == "CAP LS 302":
            server.say(":srv CAP * LS :multi-prefix")
        elif line == "CAP END":
            server.say(":srv 001 Nova :Welcome", ":NickServ!NickServ@services.oftc.net NOTICE Nova "
                                                  ":This nickname is registered")
        elif line.startswith("PRIVMSG NickServ :IDENTIFY"):
            server.say(":NickServ!NickServ@services.oftc.net NOTICE Nova :You are successfully identified as Nova")
        elif line.startswith("JOIN "):
            server.hang_up()
    connect = connector(script)
    bot = irc.IRC(irc_values(irc_password="pw"), connect=connect)
    with pytest.raises(ConnectionError):
        run(bot._session(None, lambda: None))
    lines = connect.servers[0].lines
    assert lines.index("PRIVMSG NickServ :IDENTIFY pw") < next(i for i, l in enumerate(lines) if l.startswith("JOIN"))


def test_irc_takes_the_services_account_for_the_sender_where_the_server_tags_it():
    bot = irc.IRC(irc_values())
    bot.bot_id, bot.nick = "nova", "Nova"
    plain = bot.event("kant!~k@host", "#room", "hi")
    assert plain["sender_id"] == "kant"         # no account-tag: the nick, as before
    bot.accounts = True
    who = irc.parse("@account=Kant :someone!~s@host PRIVMSG #room :hi")
    assert irc.tags("@account=Kant;time=x :a PRIVMSG #r :hi") == {"account": "Kant", "time": "x"}
    logged_in = bot.event("someone!~s@host", "#room", "hi", account="Kant")
    impostor = bot.event("kant!~k@host", "#room", "hi", account=None)
    assert logged_in["sender_id"] == "kant" and impostor["sender_id"] == "~kant"
    assert who[1] == "PRIVMSG"
    dm = bot.event("kant!~k@host", "Nova", "hi", account=None)
    assert dm["reply_handle"] == "kant"


def test_irc_asks_for_account_tag_alongside_sasl():
    def script(server, line):
        if line == "CAP LS 302":
            server.say(":srv CAP * LS :sasl=PLAIN account-tag")
        elif line == "CAP REQ :sasl account-tag":
            server.say(":srv CAP * ACK :sasl account-tag")
        elif line == "AUTHENTICATE PLAIN":
            server.say("AUTHENTICATE +")
        elif line.startswith("AUTHENTICATE "):
            server.say(":srv 903 Nova :SASL ok")
        elif line == "CAP END":
            server.say(":srv 001 Nova :Welcome")
    connect = connector(script)
    bot = irc.IRC(irc_values(irc_password="pw"), connect=connect)
    assert run(bot.check()) == "Nova" and bot.accounts is True
