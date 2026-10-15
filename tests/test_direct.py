"""Direct connectors against stand-in platform servers: no network, no accounts."""
from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from persona_agent.direct import base, discord, qq, telegram, weixin


def run(coro):
    return asyncio.run(coro)


def mock(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def test_long_text_is_split_at_a_break_and_never_over_the_limit():
    text = ("word " * 30).strip() + "\n" + "x" * 50
    pieces = base.split_text(text, 40)
    assert all(len(p) <= 40 for p in pieces)
    assert "".join(pieces).replace(" ", "") == text.replace(" ", "").replace("\n", "")
    assert base.split_text("  short  ", 40) == ["short"]
    assert base.raw_id("telegram:42", "telegram") == "42"
    assert base.raw_id("discord:42", "telegram") == ""


def test_credentials_and_status_are_kept_per_platform(tmp_path):
    base.save_credentials(tmp_path, "telegram", {"telegram_token": "a"})
    base.save_credentials(tmp_path, "discord", {"discord_token": "b"})
    base.remove_credentials(tmp_path, "telegram")
    assert base.load_credentials(tmp_path) == {"discord": {"discord_token": "b"}}
    status = base.Status(tmp_path)
    status.set("discord", "connected")
    assert base.read_status(tmp_path)["discord"]["state"] == "connected"


# ---------------------------------------------------------------- telegram

def tg_message(**fields):
    message = {"message_id": 9, "date": 1790000000, "chat": {"id": -100, "type": "supergroup"},
               "from": {"id": 42, "first_name": "Alex"}, "text": "hello"}
    message.update(fields)
    return message


def test_telegram_marks_mentions_replies_and_dms_as_addressed():
    bot = telegram.Telegram({"telegram_token": "t"}, client=mock(lambda r: httpx.Response(500)))
    bot.bot_id, bot.username = "7000", "NovaBot"
    plain = run(bot.event(tg_message()))
    assert plain["conversation_type"] == "group" and plain["conversation_id"] == "-100"
    assert plain["addressed"] is False and plain["reply_handle"] == "-100"
    text = "嗨 @NovaBot 在吗"
    mention = run(bot.event(tg_message(text=text, entities=[
        {"type": "mention", "offset": 2, "length": 8}])))
    assert mention["addressed"] is True
    reply = run(bot.event(tg_message(reply_to_message={"message_id": 3, "text": "earlier",
                                                       "from": {"id": 7000, "is_bot": True}})))
    assert reply["addressed"] is True and reply["segments"][0]["type"] == "reply"
    dm = run(bot.event(tg_message(chat={"id": 42, "type": "private"})))
    assert dm["conversation_type"] == "dm" and "conversation_id" not in dm and dm["addressed"]
    assert run(bot.event(tg_message(**{"from": {"id": 5, "is_bot": True}}))) is None


def test_telegram_sends_mentions_by_entity_and_refuses_a_bad_token():
    calls = []

    def handler(request):
        calls.append((request.url.path, json.loads(request.content or b"{}")))
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 1}})
    bot = telegram.Telegram({"telegram_token": "secret-token"}, client=mock(handler))
    bot.names["42"] = "Alex"
    assert run(bot.send("-100", [{"type": "text", "text": "hi", "mention_user_id": "telegram:42"},
                                 {"type": "text", "text": "  "}])) == 1
    path, payload = calls[0]
    assert path.endswith("/sendMessage")
    assert payload["text"] == "Alex hi"
    assert payload["entities"] == [{"type": "text_mention", "offset": 0, "length": 4, "user": {"id": 42}}]

    refused = telegram.Telegram({"telegram_token": "bad"}, client=mock(
        lambda r: httpx.Response(401, json={"ok": False, "error_code": 401})))
    with pytest.raises(base.Refused, match="token_rejected"):
        run(refused.check())
    busy = telegram.Telegram({"telegram_token": "t"}, client=mock(
        lambda r: httpx.Response(409, json={"ok": False, "error_code": 409})))
    with pytest.raises(base.Refused, match="bot_in_use"):
        run(busy.call("getUpdates"))


# ---------------------------------------------------------------- discord

class Socket:
    """A gateway connection that replays frames, then closes with a code."""

    def __init__(self, frames, close_code=None):
        self.frames = [json.dumps(f) for f in frames]
        self.sent = []
        self.close_code = close_code

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


def test_discord_identifies_then_hands_messages_over():
    message = {"id": "55", "channel_id": "300", "guild_id": "1", "content": "<@900> hey",
               "author": {"id": "42", "username": "alex"}, "mentions": [{"id": "900"}],
               "timestamp": "2026-10-14T10:00:00+00:00"}
    socket = Socket([{"op": 10, "d": {"heartbeat_interval": 45000}},
                     {"op": 0, "t": "READY", "s": 1, "d": {"session_id": "s", "resume_gateway_url": "wss://r",
                                                          "user": {"id": "900"}}},
                     {"op": 0, "t": "MESSAGE_CREATE", "s": 2, "d": message}])

    async def connect(url):
        assert "v=10" in url
        return socket
    bot = discord.Discord({"discord_token": "tok"}, client=mock(discord_rest), connect=connect)
    seen, states = [], []

    async def on_event(event, target):
        seen.append((event, target))
    run(bot._session("wss://gateway.example/?v=10&encoding=json", False, on_event,
                     lambda: states.append("connected")))
    identify = socket.sent[0]
    assert identify["op"] == 2 and identify["d"]["intents"] & (1 << 15)
    assert states == ["connected"] and bot.session_id == "s"
    event, target = seen[0]
    assert target == "300" and event["addressed"] is True and event["text"] == "hey"
    assert event["conversation_id"] == "300" and event["sent_at"] > 0


def test_discord_turns_a_missing_message_content_intent_into_a_named_refusal():
    socket = Socket([{"op": 10, "d": {"heartbeat_interval": 45000}}], close_code=4014)
    bot = discord.Discord({"discord_token": "tok"}, client=mock(discord_rest),
                          connect=lambda url: asyncio.sleep(0, socket))
    with pytest.raises(base.Refused, match="message_content_intent_off"):
        run(bot._session("wss://x", False, None, lambda: None))


def test_discord_skips_bots_and_mentions_people_it_replies_to():
    bot = discord.Discord({"discord_token": "tok"}, client=mock(discord_rest))
    bot.bot_id = "900"
    assert bot.event({"author": {"id": "5", "bot": True}, "content": "x", "channel_id": "1"}) is None
    dm = bot.event({"id": "1", "channel_id": "77", "content": "hi", "author": {"id": "42"},
                    "timestamp": "2026-10-14T10:00:00Z"})
    assert dm["conversation_type"] == "dm" and dm["addressed"]
    posts = []

    def handler(request):
        posts.append(json.loads(request.content))
        return httpx.Response(200, json={"id": "2"})
    bot.client = mock(handler)
    assert run(bot.send("77", [{"type": "text", "text": "ok", "mention_user_id": "discord:42"}])) == 1
    assert posts[0] == {"content": "<@42> ok", "allowed_mentions": {"parse": [], "users": ["42"]}}


# ---------------------------------------------------------------- weixin

def test_weixin_login_shows_the_code_and_returns_the_bot_token():
    statuses = iter([{"status": "wait"}, {"status": "scaned"},
                     {"status": "confirmed", "bot_token": "bt", "ilink_bot_id": "b@im.bot",
                      "baseurl": "https://ilinkai.weixin.qq.com", "ilink_user_id": "u@im.wechat"}])

    def handler(request):
        if request.url.path.endswith("get_bot_qrcode"):
            assert request.method == "POST" and request.headers["AuthorizationType"] == "ilink_bot_token"
            assert "Authorization" not in request.headers
            return httpx.Response(200, json={"qrcode": "q1", "qrcode_img_content": "https://scan.example/q1"})
        assert "Authorization" not in request.headers
        return httpx.Response(200, json=next(statuses))
    shown = []
    weixin.asyncio.sleep, real_sleep = (lambda s: real_sleep(0)), weixin.asyncio.sleep
    try:
        values = run(weixin.login(mock(handler), shown.append))
    finally:
        weixin.asyncio.sleep = real_sleep
    assert shown == ["https://scan.example/q1"]
    assert values["weixin_oc_token"] == "bt" and values["weixin_oc_account_id"] == "b@im.bot"


def test_weixin_keeps_context_tokens_and_echoes_them_when_replying(tmp_path):
    sent = []
    updates = iter([{"ret": 0, "get_updates_buf": "c1", "msgs": [
        {"message_type": 1, "from_user_id": "u@im.wechat", "message_id": 8, "create_time_ms": 1790000000000,
         "context_token": "ctx-1", "item_list": [{"type": 1, "text_item": {"text": "你好"}}]}]}])

    def handler(request):
        body = json.loads(request.content)
        assert request.headers["Authorization"] == "Bearer bt" and body["base_info"]["bot_agent"]
        if request.url.path.endswith("getupdates"):
            try:
                return httpx.Response(200, json=next(updates))
            except StopIteration:
                return httpx.Response(200, json={"ret": -14})
        if request.url.path.endswith("sendmessage"):
            sent.append(body["msg"])
        return httpx.Response(200, json={"ret": 0})
    state = tmp_path / "weixin.json"
    bot = weixin.Weixin({"weixin_oc_token": "bt", "weixin_oc_account_id": "b@im.bot"},
                        state=state, client=mock(handler))
    seen = []

    async def on_event(event, target):
        seen.append((event, target))
    with pytest.raises(base.Refused, match="session_expired"):
        run(bot.run(on_event, lambda: None))
    event, target = seen[0]
    assert event["conversation_type"] == "dm" and event["text"] == "你好" and target == "u@im.wechat"
    assert json.loads(state.read_text(encoding="utf-8")) == {"cursor": "c1", "contexts": {"u@im.wechat": "ctx-1"}}

    again = weixin.Weixin({"weixin_oc_token": "bt"}, state=state, client=mock(handler))
    assert again.target({"reply_handle": "u@im.wechat"}) == "u@im.wechat"
    with pytest.raises(base.Unsupported):
        again.target({"reply_handle": "stranger@im.wechat"})
    assert run(again.send("u@im.wechat", [{"type": "text", "text": "在呢"}, {"type": "image", "b64": "x"}])) == 1
    assert sent[0]["context_token"] == "ctx-1" and sent[0]["item_list"][0]["text_item"]["text"] == "在呢"


# ---------------------------------------------------------------- bridge

class FakePlatform(base.Platform):
    kind = "telegram"

    def __init__(self):
        super().__init__({})
        self.bot_id = "7000"
        self.sent = []

    async def send(self, target, items):
        self.sent.append((target, items))
        return len(items)

    def target(self, delivery):
        if not delivery.get("reply_handle"):
            raise base.Unsupported()
        return delivery["reply_handle"]


class FakeAgent:
    def __init__(self):
        self.events = []

    async def send_event(self, event):
        self.events.append(event)
        return {"owned": True, "replies": [{"type": "text", "text": "hey"}]}


def test_the_bridge_tags_events_and_relays_replies_and_outbox_deliveries(tmp_path):
    platform, agent = FakePlatform(), FakeAgent()
    bridge = base.Bridge(platform, agent, base.Status(tmp_path))

    async def scenario():
        await bridge.on_event({"sender_id": "42", "conversation_type": "dm", "text": "hi"}, "42")
        await bridge.on_event({"sender_id": "7000", "text": "my own echo"}, "42")
        await asyncio.gather(*bridge._tasks)
        return (await bridge.deliver({"reply_handle": "-100", "items": [{"type": "text", "text": "x"}]}),
                await bridge.deliver({"items": [{"type": "text", "text": "x"}]}))
    delivered, unsupported = run(scenario())
    assert len(agent.events) == 1
    assert agent.events[0]["platform"] == "telegram" and agent.events[0]["prefiltered"] is True
    assert agent.events[0]["bot_id"] == "7000" and "outbox" in agent.events[0]["capabilities"]
    assert platform.sent[0] == ("42", [{"type": "text", "text": "hey"}])
    assert delivered == ("sent", 1) and unsupported == ("unsupported", 0)


# ---------------------------------------------------------------- qq

def qq_rest(posts):
    def handler(request):
        if request.url.path.endswith("getAppAccessToken"):
            body = json.loads(request.content)
            if body["clientSecret"] != "good":
                return httpx.Response(200, json={"code": 100016, "message": "invalid appid or secret"})
            return httpx.Response(200, json={"access_token": "qq-token", "expires_in": "7200"})
        assert request.headers["Authorization"] == "QQBot qq-token"
        if request.url.path.endswith("/gateway/bot"):
            return httpx.Response(200, json={"url": "wss://api.bot.qq.com/websocket/"})
        posts.append((request.url.path, json.loads(request.content)))
        return httpx.Response(200, json={"id": "sent"})
    return handler


def test_qq_refuses_a_wrong_secret_from_the_token_body():
    bot = qq.QQ({"appid": "1", "secret": "bad"}, client=mock(qq_rest([])))
    with pytest.raises(base.Refused, match="app_rejected"):
        run(bot.check())


def test_qq_identifies_for_group_and_c2c_and_drops_repeated_pushes():
    group_at = {"id": "m1", "group_openid": "G", "content": " 在吗 ", "timestamp": "2026-10-14T10:00:00+08:00",
                "author": {"member_openid": "U"}}
    socket = Socket([{"op": 10, "d": {"heartbeat_interval": 41250}},
                     {"op": 0, "t": "READY", "s": 1, "d": {"session_id": "s", "user": {"id": "bot"}}},
                     {"op": 0, "t": "GROUP_AT_MESSAGE_CREATE", "s": 2, "d": group_at},
                     {"op": 0, "t": "GROUP_MESSAGE_CREATE", "s": 3, "d": group_at},
                     {"op": 0, "t": "C2C_MESSAGE_CREATE", "s": 4, "d": {
                         "id": "m2", "content": "hi", "timestamp": "2026-10-14T10:01:00+08:00",
                         "author": {"user_openid": "U"}}}])
    bot = qq.QQ({"appid": "1", "secret": "good"}, client=mock(qq_rest([])),
                connect=lambda url: asyncio.sleep(0, socket))
    seen = []

    async def on_event(event, target):
        seen.append((event, target))
    run(bot._session("wss://x", on_event, lambda: None))
    identify = socket.sent[0]["d"]
    assert identify["token"] == "QQBot qq-token" and identify["intents"] == 1 << 25
    assert [t for _, t in seen] == [("group", "G"), ("c2c", "U")]
    group_event = seen[0][0]
    assert group_event["text"] == "在吗" and group_event["addressed"] and group_event["reply_handle"] == "group:G"


def test_qq_replies_passively_while_allowed_then_actively():
    posts = []
    bot = qq.QQ({"appid": "1", "secret": "good"}, client=mock(qq_rest(posts)))
    bot.passive[("group", "G")] = ["m1", qq.time.monotonic(), 0]
    run(bot.send(("group", "G"), [{"type": "text", "text": "a"}, {"type": "text", "text": "b"}]))
    assert [p[1].get("msg_seq") for p in posts] == [1, 2]
    assert all(p[1]["msg_id"] == "m1" and p[0] == "/v2/groups/G/messages" for p in posts)
    bot.passive[("group", "G")][1] -= 6 * 60          # past QQ's five-minute window
    run(bot.send(("group", "G"), [{"type": "text", "text": "c"}]))
    assert "msg_id" not in posts[-1][1]
    assert bot.target({"reply_handle": "c2c:U"}) == ("c2c", "U")
    with pytest.raises(base.Unsupported):
        bot.target({"reply_handle": "elsewhere"})


# ---------------------------------------------------------------- review fixes

def no_wait(monkeypatch):
    async def instant(seconds):
        await asyncio.sleep(0)
    monkeypatch.setattr(base, "backoff_sleep", instant)


def test_a_network_blip_at_startup_is_retried_and_only_a_refusal_ends_it(tmp_path, monkeypatch):
    no_wait(monkeypatch)
    status = base.Status(tmp_path)
    attempts = []

    class Flaky(FakePlatform):
        async def run(self, on_event, connected):
            attempts.append(1)
            if len(attempts) == 1:
                raise ConnectionError("getMe: ConnectTimeout")
            connected()
            self.dropped()
            raise base.Refused("token_rejected")

    class Agent(FakeAgent):
        async def run_outbox(self, deliver, stop=None):
            await stop.wait()
    run(base.Bridge(Flaky(), Agent(), status).run(asyncio.Event()))
    assert len(attempts) == 2
    final = base.read_status(tmp_path)["telegram"]
    assert final["state"] == "refused" and final["detail"] == "token_rejected"


def test_backoff_never_overflows(monkeypatch):
    waits = []

    async def record(seconds):
        waits.append(seconds)
    monkeypatch.setattr(base.asyncio, "sleep", record)
    run(base.backoff_sleep(5000))
    assert waits == [base.RETRY_S[1]]


def test_a_send_that_fails_midway_reports_what_went_out():
    calls = []

    def handler(request):
        calls.append(1)
        if len(calls) == 2:
            return httpx.Response(500, json={"ok": False, "error_code": 500})
        return httpx.Response(200, json={"ok": True, "result": {}})
    bot = telegram.Telegram({"telegram_token": "t"}, client=mock(handler))
    items = [{"type": "text", "text": "one"}, {"type": "text", "text": "two"}, {"type": "text", "text": "three"}]
    assert run(bot.send("-100", items)) == 1


def test_telegram_replies_in_the_forum_topic_and_keeps_long_names_inside_the_limit():
    bot = telegram.Telegram({"telegram_token": "t"}, client=mock(lambda r: httpx.Response(500)))
    bot.bot_id, bot.username = "7000", "NovaBot"
    event = run(bot.event(tg_message(is_topic_message=True, message_thread_id=12)))
    assert event["reply_handle"] == "-100/12"
    sent = []

    def handler(request):
        sent.append(json.loads(request.content))
        return httpx.Response(200, json={"ok": True, "result": {}})
    bot.client = mock(handler)
    bot.names["42"] = "N" * 300
    run(bot.send("-100/12", [{"type": "text", "text": "x" * 5000, "mention_user_id": "telegram:42"}]))
    assert len(sent) == 2
    assert all(p["chat_id"] == "-100" and p["message_thread_id"] == 12 for p in sent)
    assert all(len(p["text"]) <= telegram.MAX_TEXT for p in sent)


def test_discord_keeps_its_session_resumable_and_survives_an_html_429():
    socket = Socket([{"op": 10, "d": {"heartbeat_interval": 45000}}, {"op": 7}])
    closed = []

    async def close(code=1000):
        closed.append(code)
    socket.close = close
    bot = discord.Discord({"discord_token": "tok"}, client=mock(discord_rest),
                          connect=lambda url: asyncio.sleep(0, socket))
    run(bot._session("wss://x", False, None, lambda: None))
    assert closed and not {1000, 1001} & set(closed)

    answers = iter([httpx.Response(429, text="<html>slow down</html>", headers={"retry-after": "0"}),
                    httpx.Response(200, json={"id": "900", "username": "nova"})])
    bot = discord.Discord({"discord_token": "tok"}, client=mock(lambda r: next(answers)))
    assert run(bot.check()) == "nova"


def test_weixin_only_treats_a_long_poll_timeout_as_empty(tmp_path):
    def handler(request):
        raise httpx.ReadTimeout("slow", request=request)
    bot = weixin.Weixin({"weixin_oc_token": "bt"}, state=tmp_path / "s.json", client=mock(handler))
    bot.contexts["u@im.wechat"] = "ctx"
    assert run(bot.call("getupdates", {}, long_poll=True)) == {"ret": 0}
    assert run(bot.send("u@im.wechat", [{"type": "text", "text": "hi"}])) == 0


def test_weixin_reads_the_quoted_message_id_from_the_quoted_item():
    bot = weixin.Weixin({"weixin_oc_token": "bt"}, client=mock(lambda r: httpx.Response(500)))
    event = bot.event({"from_user_id": "u@im.wechat", "message_id": 2, "item_list": [
        {"type": 1, "text_item": {"text": "yes"},
         "ref_msg": {"message_item": {"msg_id": "77", "text_item": {"text": "earlier"}}}}]})
    assert event["segments"][0] == {"type": "reply", "message_id": "77", "text": "earlier",
                                    "sender_id": "", "sender_name": ""}


def test_qq_tells_an_outage_from_wrong_credentials_and_never_resends_after_a_read_timeout():
    bot = qq.QQ({"appid": "1", "secret": "good"}, client=mock(lambda r: httpx.Response(502, json={})))
    with pytest.raises(ConnectionError):
        run(bot.access_token())
    hosts = []

    def handler(request):
        if request.url.path.endswith("getAppAccessToken"):
            return httpx.Response(200, json={"access_token": "qq-token", "expires_in": "7200"})
        hosts.append(request.url.host)
        raise httpx.ReadTimeout("slow", request=request)
    bot = qq.QQ({"appid": "1", "secret": "good"}, client=mock(handler))
    assert run(bot.send(("c2c", "U"), [{"type": "text", "text": "hi"}])) == 0
    assert len(hosts) == 1


def test_qq_starts_a_fresh_session_after_an_invalid_session_close():
    socket = Socket([{"op": 10, "d": {"heartbeat_interval": 41250}}], close_code=4006)
    bot = qq.QQ({"appid": "1", "secret": "good"}, client=mock(qq_rest([])),
                connect=lambda url: asyncio.sleep(0, socket))
    bot.session_id, bot.seq = "old", 9
    run(bot._session("wss://x", None, lambda: None))
    assert socket.sent[0]["op"] == 6 and bot.session_id == "" and bot.seq is None


def test_qq_lets_the_at_copy_of_a_group_message_through_as_addressed(monkeypatch):
    monkeypatch.setattr(qq, "AT_GRACE_S", 0.05)
    bot = qq.QQ({"appid": "1", "secret": "good"}, client=mock(qq_rest([])))
    plain = {"id": "m9", "group_openid": "G", "content": "nova 在吗", "timestamp": "2026-10-14T10:00:00+08:00",
             "author": {"member_openid": "U"}}
    seen = []

    async def on_event(event, target):
        seen.append(event)

    async def scenario():
        await bot._dispatch("GROUP_MESSAGE_CREATE", plain, on_event, lambda: None)
        await bot._dispatch("GROUP_AT_MESSAGE_CREATE", plain, on_event, lambda: None)
        await asyncio.sleep(0.1)
        await bot._dispatch("GROUP_MESSAGE_CREATE", dict(plain, id="m10"), on_event, lambda: None)
        await asyncio.sleep(0.1)
    run(scenario())
    assert [(e["message_id"], e["addressed"]) for e in seen] == [("m9", True), ("m10", False)]


def test_telegram_and_wechat_report_connected_again_after_a_drop(tmp_path, monkeypatch):
    async def instant(seconds):
        await asyncio.sleep(0)
    monkeypatch.setattr(telegram, "backoff_sleep", instant)
    monkeypatch.setattr(weixin, "backoff_sleep", instant)

    tg_answers = iter([{"ok": True, "result": {"id": 7000, "username": "NovaBot"}},   # getMe
                       {"ok": True, "result": True},                                   # deleteWebhook
                       None,                                                           # a drop
                       {"ok": True, "result": []},                                     # recovered
                       {"ok": False, "error_code": 401}])                              # then stop

    def tg(request):
        answer = next(tg_answers)
        if answer is None:
            raise httpx.ConnectError("down", request=request)
        return httpx.Response(200 if answer.get("ok") else 401, json=answer)
    states = []
    bot = telegram.Telegram({"telegram_token": "t"}, client=mock(tg))
    bot.dropped = lambda: states.append("connecting")
    with pytest.raises(base.Refused):
        run(bot.run(None, lambda: states.append("connected")))
    assert states == ["connected", "connecting", "connected"]

    wx_answers = iter([{"ret": 0}, None, {"ret": 0, "msgs": []}, {"ret": -14}])  # notifystart first

    def wx(request):
        answer = next(wx_answers)
        if answer is None:
            raise httpx.ConnectError("down", request=request)
        return httpx.Response(200, json=answer)
    states.clear()
    bot = weixin.Weixin({"weixin_oc_token": "bt"}, state=tmp_path / "s.json", client=mock(wx))
    bot.dropped = lambda: states.append("connecting")
    with pytest.raises(base.Refused):
        run(bot.run(None, lambda: states.append("connected")))
    assert states == ["connecting", "connected"]


def test_qq_lets_held_plain_messages_out_before_a_later_at_message(monkeypatch):
    monkeypatch.setattr(qq, "AT_GRACE_S", 5)
    bot = qq.QQ({"appid": "1", "secret": "good"}, client=mock(qq_rest([])))
    base_message = {"group_openid": "G", "timestamp": "2026-10-14T10:00:00+08:00",
                    "author": {"member_openid": "U"}}
    seen = []

    async def on_event(event, target):
        seen.append(event["message_id"])

    async def scenario():
        await bot._dispatch("GROUP_MESSAGE_CREATE", dict(base_message, id="p1", content="hi"),
                            on_event, lambda: None)
        await bot._dispatch("GROUP_AT_MESSAGE_CREATE", dict(base_message, id="a2", content="nova?"),
                            on_event, lambda: None)
    run(scenario())
    assert seen == ["p1", "a2"]
    assert bot.passive[("group", "G")][0] == "a2" and not bot.held
