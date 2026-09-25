"""The Satori connector: Satori events become neutral events the agent
accepts, replies go back as Satori elements, and outbox deliveries find their
channel through reply_handle. satori-python and the server are faked."""
from __future__ import annotations

import base64
import json
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import ModuleType, SimpleNamespace

import httpx

import main as main_module

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "integrations" / "satori"))
import satori_connector as sc  # noqa: E402


def check(name: str, cond: bool, detail: str = "") -> None:
    assert cond, f"{name}: {detail}" if detail else name


# ---------- fakes for satori-python ----------

class El:
    """Stands in for a satori-python Element: a tag, attributes, children."""

    def __init__(self, tag: str, *children, **attrs):
        self.tag = tag
        self.children = list(children)
        self._attrs = dict(attrs)
        for key, value in attrs.items():
            setattr(self, key, value)


def T(text: str) -> El:
    return El("text", text=text)


class _Rendered:
    def __init__(self, markup: str):
        self.markup = markup

    def __str__(self) -> str:
        return self.markup


class _Image:
    @staticmethod
    def of(raw: bytes, mime=None):
        if mime is None and not raw.startswith(b"\x89PNG"):
            raise ValueError("Cannot detect mime type")
        return _Rendered(f'<img bytes="{len(raw)}" mime="{mime or "image/png"}"/>')


def _parse_message(raw: dict):
    # Quoted content is plain text in these tests.
    return SimpleNamespace(id=raw.get("id"), message=[T(raw.get("content", ""))])


LIB = SimpleNamespace(
    Text=lambda text: _Rendered(text),
    At=lambda id=None: _Rendered(f'<at id="{id}"/>'),
    Image=_Image,
    MessageObject=SimpleNamespace(parse=_parse_message),
)


class FakeProtocol:
    def __init__(self, images=None, fail_on=None):
        self.sent: list[tuple[str, str]] = []
        self.referrers: list = []
        self.images = images or {}
        self.fail_on = fail_on

    async def send_message(self, channel, message, referrer=None):
        markup = "".join(str(m) for m in message)
        if self.fail_on and self.fail_on in markup:
            raise RuntimeError("platform refused")
        self.sent.append((channel, markup))
        self.referrers.append(referrer)
        return []

    async def download(self, url):
        if url not in self.images:
            raise RuntimeError("404")
        return self.images[url]


def account(platform="telegram", self_id="7000", **protocol):
    return SimpleNamespace(platform=platform, self_id=self_id, proxy_urls=[],
                           protocol=FakeProtocol(**protocol),
                           connected=SimpleNamespace(is_set=lambda: True))


NOW_MS = int(time.time() * 1000)


def message_event(elements, *, user="42", channel="-100", guild="-100", channel_type=0,
                  platform="telegram", self_id="7000", raw=None, created_at=NOW_MS,
                  timestamp=None, referrer=None):
    message = SimpleNamespace(id="881", message=elements, _raw_data=raw or {},
                              created_at=created_at)
    return SimpleNamespace(
        type="message-created",
        login=SimpleNamespace(platform=platform, user=SimpleNamespace(id=self_id, name="Nova")),
        user=SimpleNamespace(id=user, name="alex_k", nick=None),
        member=SimpleNamespace(nick="Alex"),
        channel=SimpleNamespace(id=channel, type=channel_type),
        guild=SimpleNamespace(id=guild) if guild else None,
        message=message,
        timestamp=timestamp if timestamp is not None else datetime.now(),
        referrer=referrer,
    )


def config(**overrides) -> sc.Config:
    base = sc.Config.from_env({"SATORI_GROUPS": "-100", "SATORI_DM_USERS": "42"})
    base.reply_gap_s = (0, 0)
    for key, value in overrides.items():
        assert hasattr(base, key), f"Config has no {key}"
        setattr(base, key, value)
    return base


#: The key the default test bridge signs its reply handles with.
KEY = sc.handle_key(config())


def bridge(cfg=None, agent=None, accounts=()) -> sc.SatoriBridge:
    connector = sc.sdk.Connector("http://127.0.0.1:8080", "tok",
                                 connector_id="satori-test", client=agent)

    async def no_sleep(_s):
        return None

    return sc.SatoriBridge(cfg or config(), connector, accounts=lambda: list(accounts),
                           lib=LIB, sleep=no_sleep)


def fake_agent(replies: list, seen: list) -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        return httpx.Response(200, json={"handled": True, "owned": True, "replies": replies})
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


# ---------- inbound ----------

def test_the_module_imports_without_satori_python() -> None:
    check("satori is imported only by serve()", "satori.client" not in sys.modules)


async def test_a_group_message_becomes_an_event_the_agent_accepts() -> None:
    quote = El("quote", El("author", id="7000", name="Nova"), T("it rained"), id="870")
    event = message_event([quote, El("at", id="7000", name="Nova"), T(" how was "),
                           El("b", T("your")), T(" day?")])
    neutral = await bridge().build_event(account(), event)

    check("mapped", neutral is not None)
    check("platform and ids are raw",
          (neutral["platform"], neutral["conversation_id"], neutral["sender_id"],
           neutral["bot_id"], neutral["message_id"]) == ("telegram", "-100", "42", "7000", "881"),
          str(neutral))
    check("group", neutral["conversation_type"] == "group")
    check("member nick is the sender name", neutral["sender_name"] == "Alex")
    check("milliseconds become seconds", neutral["sent_at"] == NOW_MS // 1000,
          str(neutral["sent_at"]))
    check("segments in order", neutral["segments"] == [
        {"type": "reply", "message_id": "870", "sender_id": "7000", "sender_name": "Nova",
         "text": "it rained"},
        {"type": "mention", "user_id": "7000", "name": "Nova"},
        {"type": "text", "text": " how was your day?"},
    ], str(neutral["segments"]))
    check("an @ of the bot addresses it", neutral["addressed"] is True)
    check("raw text", neutral["text"] == "@Nova how was your day?", neutral["text"])
    check("capabilities", neutral["capabilities"] == ["outbox", "quote_text"])
    check("prefiltered by the allowlist", neutral["prefiltered"] is True)
    handle = sc.decode_handle(neutral["reply_handle"])
    check("handle addresses the login and channel",
          handle == {"platform": "telegram", "self_id": "7000", "channel_id": "-100",
                     "guild_id": "-100", "type": "group"}, str(handle))
    check("schema", main_module._validate_event_payload(neutral, connector=True))
    check("fresh", main_module._connector_event_is_fresh(neutral))


async def test_a_reply_to_the_bot_is_read_from_message_quote() -> None:
    raw = {"quote": {"id": "870", "content": "it rained",
                     "user": {"id": "7000", "name": "nova_bot"}, "member": {"nick": "Nova"}}}
    neutral = await bridge().build_event(account(), message_event([T("really?")], raw=raw))
    check("reply segment carries the quoted text and sender",
          neutral["segments"][0] == {"type": "reply", "message_id": "870", "sender_id": "7000",
                                     "sender_name": "Nova", "text": "it rained"},
          str(neutral["segments"]))
    check("replying to the bot addresses it", neutral["addressed"] is True)

    raw["quote"]["user"]["id"] = "55"
    neutral = await bridge().build_event(account(), message_event([T("really?")], raw=raw))
    check("replying to someone else is not", neutral["addressed"] is False)


async def test_a_reply_as_koishi_encodes_it() -> None:
    # Koishi prepends the quoted message as <quote id> holding its <user>,
    # <member> and <channel> resources, then its content.
    quote = El("quote", El("user", id="7000", name="nova_bot"), El("member", nick="Nova"),
               El("channel", id="-100", type="0"), T("it rained "), El("img", src="x"),
               id="870")
    neutral = await bridge().build_event(account(), message_event([quote, T("really?")]))
    check("sender from <user>, name from <member>, resources are not text",
          neutral["segments"] == [
              {"type": "reply", "message_id": "870", "sender_id": "7000", "sender_name": "Nova",
               "text": "it rained [image]"},
              {"type": "text", "text": "really?"}], str(neutral["segments"]))
    check("a reply to the bot addresses it", neutral["addressed"] is True)
    check("the quote is not the person's words", neutral["text"] == "really?")


async def test_mentions_by_name_and_mass_mentions() -> None:
    event = message_event([El("at", name="@nova"), T(" hi "), El("at", type="all"),
                           El("at", id="55", name="Sam")])
    neutral = await bridge().build_event(account(), event)
    check("an id-less @ of the bot's name is the bot",
          neutral["segments"][0] == {"type": "mention", "user_id": "7000", "name": "@nova"},
          str(neutral["segments"]))
    check("@all is text, not a mention of the bot",
          neutral["segments"][1] == {"type": "text", "text": " hi @all"})
    check("others are mentions", neutral["segments"][2]["user_id"] == "55")
    check("addressed", neutral["addressed"] is True)


async def test_direct_messages_and_the_allowlists() -> None:
    dm = message_event([T("hey")], channel="private:42", guild=None, channel_type=1)
    neutral = await bridge().build_event(account(), dm)
    check("a DIRECT channel is a DM", neutral["conversation_type"] == "dm")
    check("a DM's conversation is the person", neutral["conversation_id"] == "42")
    handle = sc.decode_handle(neutral["reply_handle"])
    check("the handle keeps the DM channel",
          handle["channel_id"] == "private:42" and handle["user_id"] == "42", str(handle))

    check("DMs are off by default",
          await bridge(config(dm_users=frozenset())).build_event(account(), dm) is None)
    check("a platform-prefixed entry admits",
          await bridge(config(dm_users=frozenset({"telegram:42"}))).build_event(account(), dm)
          is not None)
    everyone = await bridge(config(dm_users=frozenset({"*"}))).build_event(account(), dm)
    check("'*' forwards and leaves the filtering to the agent",
          everyone["prefiltered"] is False)

    typeless = message_event([T("hey")], guild=None)
    typeless.channel._raw_data = {"id": "-100"}
    neutral = await bridge().build_event(account(), typeless)
    check("no guild and no channel type is a DM", neutral["conversation_type"] == "dm")


async def test_what_is_not_forwarded() -> None:
    b = bridge()
    check("the bot's own message",
          await b.build_event(account(), message_event([T("x")], user="7000")) is None)
    check("an unlisted group",
          await b.build_event(account(), message_event([T("x")], channel="-9", guild="-9"))
          is None)
    check("no group at all while SATORI_GROUPS is empty",
          await bridge(config(groups=frozenset())).build_event(
              account(), message_event([T("x")])) is None)
    anywhere = await bridge(config(groups=frozenset({"*"}))).build_event(
        account(), message_event([T("x")], channel="-9", guild="-9"))
    check("'*' forwards every group, unfiltered",
          anywhere is not None and anywhere["prefiltered"] is False)
    check("a group listed by its guild",
          await bridge(config(groups=frozenset({"discord:g1"}))).build_event(
              account("discord"), message_event([T("x")], channel="c7", guild="g1",
                                                platform="discord")) is not None)
    check("a platform outside SATORI_PLATFORMS",
          await bridge(config(platforms=frozenset({"discord"}))).build_event(
              account(), message_event([T("x")])) is None)
    stale = message_event([T("x")], created_at=5, timestamp=5)
    check("no usable timestamp", await b.build_event(account(), stale) is None)
    seconds = message_event([T("x")], created_at=5, timestamp=int(time.time()))
    check("an implausible created_at falls back to the event time",
          (await b.build_event(account(), seconds))["sent_at"] == seconds.timestamp)

    # satori-python divides by 1000, so an adapter stamping seconds arrives in 1970.
    now_s = int(time.time())
    scaled = message_event([T("x")], created_at=datetime.fromtimestamp(now_s / 1000))
    got = (await b.build_event(account(), scaled))["sent_at"]
    check("seconds read as milliseconds are scaled back", abs(got - now_s) <= 1,
          f"{got} vs {now_s}")


async def test_images_media_and_emoji() -> None:
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 16
    acc = account(images={"internal:telegram/file/1": png,
                          "http://127.0.0.1:5140/satori/v1/assets/2": png})
    event = message_event([
        El("img", src="data:image/jpeg;base64,QUJD"),
        El("img", src="internal:telegram/file/1"),
        El("img", src="https://cdn.example.com/a.png"),
        El("img", src="http://10.0.0.5/b.png"),
        El("img", src="http://127.0.0.1:5140/satori/v1/assets/2"),
        El("img", src="internal:telegram/file/missing"),
        El("audio", src="x"), El("video", src="y"), El("file", src="z", title="deck.pdf"),
        El("emoji", id="123", name="party"), El("face", El("img", src="q"), id="14"),
    ])
    segs = (await bridge().build_event(acc, event))["segments"]
    b64 = base64.b64encode(png).decode()
    check("data: URIs are inlined", segs[0] == {"type": "image", "b64": "QUJD"}, str(segs[0]))
    check("internal: is fetched through the server", segs[1] == {"type": "image", "b64": b64})
    check("a public URL is passed on", segs[2] == {"type": "image",
                                                   "url": "https://cdn.example.com/a.png"})
    check("a private URL the agent cannot fetch is described",
          segs[3] == {"type": "text", "text": "(sent an image)"}, str(segs[3]))
    check("the Satori server's own URL is fetched", segs[4] == {"type": "image", "b64": b64})
    check("a failed fetch is described, and media in words", segs[5] == {
        "type": "text", "text": "(sent an image)(sent a voice message)(sent a video)"
                                "(sent a file: deck.pdf)"}, str(segs[5]))
    check("emoji and QQ faces", segs[6:] == [{"type": "emoji", "name": "party", "id": "123"},
                                             {"type": "emoji", "name": "", "id": "14"}],
          str(segs[6:]))

    inline = await bridge(config(inline_images_enabled=True)).build_event(
        account(images={"https://cdn.example.com/a.png": png}),
        message_event([El("img", src="https://cdn.example.com/a.png")]))
    check("SATORI_INLINE_IMAGES_ENABLED fetches public URLs too",
          inline["segments"] == [{"type": "image", "b64": b64}])


async def test_platform_names_can_be_renamed() -> None:
    cfg = config(platform_names={"qq": "qqbot"}, groups=frozenset({"qqbot:-100"}))
    b = bridge(cfg)
    neutral = await b.build_event(account("qq"), message_event([T("x")], platform="qq"))
    check("the event carries the new name", neutral["platform"] == "qqbot")
    check("the handle keeps the Satori name for sending",
          sc.decode_handle(neutral["reply_handle"])["platform"] == "qq")
    check("mentions resolve under the new name",
          str(b.render({"type": "text", "text": "hi", "mention_user_id": "qqbot:9"}, "qqbot",
                        True)[0]) == '<at id="9"/>')

    default = bridge(config(groups=frozenset({"-100"})))
    neutral = await default.build_event(account("qq"), message_event([T("x")], platform="qq"))
    check("Satori's qq (openids) never claims personagent's bare QQ namespace",
          neutral["platform"] == "qqbot")
    neutral = await default.build_event(account("onebot"),
                                        message_event([T("x")], platform="onebot"))
    check("other platforms keep their Satori name", neutral["platform"] == "onebot")


# ---------- outbound ----------

async def test_replies_go_back_as_satori_elements() -> None:
    png = b"\x89PNG\r\n\x1a\n" + b"1" * 8
    gif = b"GIF89a" + b"2" * 8
    seen: list[dict] = []
    replies = [
        {"type": "text", "text": "not bad", "mention_user_id": "telegram:42"},
        {"type": "text", "text": "rained <all> afternoon", "mention_user_id": "discord:42"},
        {"type": "image", "b64": base64.b64encode(png).decode()},
        {"type": "image", "b64": base64.b64encode(gif).decode(), "mention_user_id": "telegram:42"},
        {"type": "text", "text": ""},
        {"type": "voice"},
    ]
    acc = account()
    b = bridge(agent=fake_agent(replies, seen), accounts=[acc])
    await b.on_message(acc, message_event([T("Nova, how was your day?")],
                                          referrer={"msg_id": "m1"}))

    check("one signed event reached the agent", len(seen) == 1
          and seen[0]["connector_id"] == "satori-test", str(seen))
    check("each reply is its own message, in order", acc.protocol.sent == [
        ("-100", '<at id="42"/> not bad'),
        ("-100", "rained <all> afternoon"),
        ("-100", f'<img bytes="{len(png)}" mime="image/png"/>'),
        ("-100", f'<at id="42"/><img bytes="{len(gif)}" mime="image/png"/>'),
    ], str(acc.protocol.sent))
    check("replies carry the event's referrer, for passive-reply platforms",
          acc.protocol.referrers == [{"msg_id": "m1"}] * 4, str(acc.protocol.referrers))

    dm_acc = account()
    b = bridge(agent=fake_agent(replies[:1], []), accounts=[dm_acc])
    await b.on_message(dm_acc, message_event([T("hey")], channel="private:42", guild=None,
                                             channel_type=1))
    check("a DM reply goes to the DM channel without an @",
          dm_acc.protocol.sent == [("private:42", "not bad")], str(dm_acc.protocol.sent))


async def test_an_agent_error_sends_nothing() -> None:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        if len(calls) == 1:
            return httpx.Response(429, headers={"Retry-After": "0"},
                                  json={"code": "capacity_exceeded"})
        return httpx.Response(403, json={"code": "stale_event",
                                         "error": "stale event"})

    acc = account()
    b = bridge(agent=httpx.AsyncClient(transport=httpx.MockTransport(handler)), accounts=[acc])
    await b.on_message(acc, message_event([T("hi")]))
    check("a 429 is retried once", len(calls) == 2, str(calls))
    check("nothing was sent", acc.protocol.sent == [])


async def test_outbox_deliveries_follow_the_reply_handle() -> None:
    acc = account()
    other = account(self_id="7001")
    b = bridge(accounts=[other, acc])
    handle = sc.encode_handle(key=KEY, platform="telegram", self_id="7000",
                              channel_id="-100", guild_id="-100", type="group")
    delivery = {"delivery_id": "d1", "reply_handle": handle, "conversation_type": "group",
                "items": [{"type": "text", "text": "anyone still up?",
                           "mention_user_id": "telegram:42"},
                          {"type": "text", "text": "second"}]}
    check("sent", await b.deliver(delivery) == ("sent", 2))
    check("through the login in the handle, to its channel",
          acc.protocol.sent == [("-100", '<at id="42"/> anyone still up?'), ("-100", "second")]
          and other.protocol.sent == [], str(acc.protocol.sent))

    flaky = account(fail_on="second")
    check("a failure part-way is partial",
          await bridge(accounts=[flaky]).deliver(delivery) == ("partial", 1))
    check("a failure on the first item is failed",
          await bridge(accounts=[account(fail_on="anyone")]).deliver(delivery) == ("failed", 0))
    check("a login that is gone is failed", await bridge(accounts=[other]).deliver(delivery)
          == ("failed", 0))
    check("a room no longer allowed is refused",
          await bridge(config(groups=frozenset()), accounts=[acc]).deliver(delivery)
          == ("refused", 0))
    check("a handle this connector did not write is unsupported",
          await b.deliver(dict(delivery, reply_handle="tg-bot:GroupMessage:-1")) ==
          ("unsupported", 0))
    # The agent keeps a handle as an event gave it: an allowed DM user paired
    # with a group channel must not reach that channel.
    forged = sc.encode_handle(key=sc.handle_key(config(connector_token="other")),
                              platform="telegram", self_id="7000", channel_id="-999",
                              user_id="42", type="dm")
    sent_before = list(acc.protocol.sent)
    check("a handle signed with another key is refused",
          await b.deliver(dict(delivery, reply_handle=forged)) == ("refused", 0)
          and acc.protocol.sent == sent_before, str(acc.protocol.sent))
    edited = json.loads(handle)
    edited["channel_id"] = "-999"
    check("so is a signed handle with a field changed",
          await b.deliver(dict(delivery, reply_handle=json.dumps(edited))) == ("refused", 0))

    dm = {"delivery_id": "d2", "items": [{"type": "text", "text": "morning"}],
          "reply_handle": sc.encode_handle(key=KEY, platform="telegram", self_id="7000",
                                           channel_id="private:42", user_id="42",
                                           type="dm")}
    dm_acc = account()
    check("a DM delivery", await bridge(accounts=[dm_acc]).deliver(dm) == ("sent", 1))
    check("goes to the DM channel", dm_acc.protocol.sent == [("private:42", "morning")])


async def test_the_sdk_outbox_loop_drives_deliver() -> None:
    import asyncio

    acc = account()
    handle = sc.encode_handle(key=KEY, platform="telegram", self_id="7000",
                              channel_id="-100", guild_id="-100", type="group")
    pulls = [{"deliveries": [{"delivery_id": "d9", "reply_handle": handle, "expires_in_s": 60,
                              "items": [{"type": "text", "text": "hi"}]}]}]
    seen: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        return httpx.Response(200, json=pulls.pop(0) if pulls else {"deliveries": []})

    b = bridge(agent=httpx.AsyncClient(transport=httpx.MockTransport(handler)), accounts=[acc])
    stop = asyncio.Event()

    async def stopper() -> None:
        while len(seen) < 2:
            await asyncio.sleep(0.01)
        stop.set()

    await asyncio.wait_for(asyncio.gather(
        b.connector.run_outbox(b.deliver, wait_s=0, idle_s=0.01, stop=stop), stopper()), 10)
    check("delivered", acc.protocol.sent == [("-100", "hi")])
    check("acked on the next pull",
          {"delivery_id": "d9", "status": "sent", "sent_items": 1} in seen[1]["acks"],
          str(seen))


# ---------- configuration ----------

def test_settings_from_the_environment() -> None:
    cfg = sc.Config.from_env({
        "SATORI_URL": "https://koishi.example.com/satori/v1/",
        "SATORI_TOKEN": "s3cret",
        "SATORI_PLATFORMS": "Telegram, discord",
        "SATORI_PLATFORM_NAMES": "qq=QQBot, bad",
        "SATORI_GROUPS": "-100,\n discord:c7",
        "SATORI_OUTBOX_ENABLED": "off",
        "SATORI_TIMEOUT_S": "90",
    })
    check("endpoint to WebsocketsInfo", cfg.websocket_kwargs() == {
        "host": "koishi.example.com", "port": 443, "path": "/satori", "secure": True,
        "token": "s3cret"}, str(cfg.websocket_kwargs()))
    check("lists", cfg.platforms == {"telegram", "discord"}
          and cfg.groups == {"-100", "discord:c7"} and cfg.dm_users == frozenset())
    check("names", cfg.platform_names == {"qq": "qqbot"}, str(cfg.platform_names))
    check("flags", cfg.outbox_enabled is False and cfg.timeout_s == 90.0)

    default = sc.Config.from_env({})
    check("defaults", default.websocket_kwargs() == {
        "host": "127.0.0.1", "port": 5140, "path": "/satori", "secure": False, "token": None}
          and default.personagent_url == sc.DEFAULT_PERSONAGENT_URL
          and default.outbox_enabled is True)
    check("the connector id is stable per Satori URL",
          default.connector_id == sc.Config.from_env({}).connector_id
          and default.connector_id != cfg.connector_id
          and default.connector_id.startswith("satori-"))


def fake_satori(monkeypatch) -> SimpleNamespace:
    """satori-python's client as serve() uses it. Like the real App, it finds
    the network by the config's exact class, and logs the config as-is when
    the server reports no login."""
    @dataclass
    class WebsocketsInfo:
        host: str = "localhost"
        port: int = 5140
        path: str = ""
        token: str | None = None
        secure: bool = False
        timeout: float | None = None

    class App:
        mapping: dict = {WebsocketsInfo: "WsNetwork"}
        instances: list = []

        @classmethod
        def register_config(cls, tc, tn) -> None:
            cls.mapping[tc] = tn

        def __init__(self, *configs):
            for config in configs:
                if config.__class__ not in self.mapping:
                    raise TypeError(f"Unknown config type: {config}")
            self.configs, self.accounts, self.logged = configs, {}, []
            App.instances.append(self)

        def register_on(self, event_type):
            return lambda func: func

        def lifecycle(self, callback) -> None:
            pass

        async def run_async(self) -> None:
            self.logged.append(f"No account available for {self.configs[0]}")

    fake = SimpleNamespace(App=App, WebsocketsInfo=WebsocketsInfo)
    satori = ModuleType("satori")
    satori.EventType = SimpleNamespace(MESSAGE_CREATED="message-created")
    client = ModuleType("satori.client")
    client.App, client.WebsocketsInfo = App, WebsocketsInfo
    websocket = ModuleType("satori.client.network.websocket")
    websocket.WsNetwork = "WsNetwork"
    for name, module in (("satori", satori), ("satori.client", client),
                         ("satori.client.network", ModuleType("satori.client.network")),
                         ("satori.client.network.websocket", websocket)):
        monkeypatch.setitem(sys.modules, name, module)
    return fake


async def test_the_satori_token_stays_out_of_the_log(monkeypatch) -> None:
    fake = fake_satori(monkeypatch)
    cfg = sc.Config.from_env({"SATORI_TOKEN": "s3cret", "CONNECTOR_TOKEN": "g4te",
                              "SATORI_OUTBOX_ENABLED": "false"})
    await sc.serve(cfg)
    app = fake.App.instances[0]
    check("the network still gets the token", app.configs[0].token == "s3cret"
          and isinstance(app.configs[0], fake.WebsocketsInfo))
    check("the line satori-python logs without a login leaves it out",
          "s3cret" not in app.logged[0] and "127.0.0.1" in app.logged[0], app.logged[0])
    check("so does the connector's own config", "s3cret" not in repr(cfg)
          and "g4te" not in repr(cfg), repr(cfg))


def test_the_default_timeout_outlasts_the_agents_default_turn() -> None:
    from persona_agent.settings import AgentSettings

    agent = AgentSettings.from_env(env={})
    turn = agent.llm_timeout_s * (1 + agent.api_max_retries) + agent.message_debounce_sec
    default = sc.Config.from_env({}).timeout_s
    check("longer than a turn with the agent's defaults", default > turn, f"{default} vs {turn}")
    check("the field agrees", sc.Config().timeout_s == default)
    satori = Path(sc.__file__).parent
    template = (satori / ".env.example").read_text(encoding="utf-8")
    readme = (satori / "README.md").read_text(encoding="utf-8")
    check(".env.example agrees", f"SATORI_TIMEOUT_S={default:.0f}\n" in template)
    check("the README agrees", f"| `SATORI_TIMEOUT_S` | `{default:.0f}` |" in readme)


def test_a_config_file_under_the_environment(tmp: Path, monkeypatch) -> None:
    file = tmp / "satori.env"
    file.write_text("SATORI_URL=http://127.0.0.1:5500\nCONNECTOR_TOKEN=from-file\n",
                    encoding="utf-8")
    env = sc.load_env(str(file), environ={"CONNECTOR_TOKEN": "from-env", "PATH": "x"})
    check("file values, environment wins, unrelated variables ignored",
          env == {"SATORI_URL": "http://127.0.0.1:5500", "CONNECTOR_TOKEN": "from-env"},
          str(env))

    monkeypatch.setitem(sys.modules, "satori", None)  # as if not installed
    check("a missing config file is an error", sc.main(["--config", str(tmp / "no.env")]) == 2)
    unsafe = tmp / "unsafe.env"
    unsafe.write_text("PERSONAGENT_URL=http://agent.example.com\n",
                      encoding="utf-8")
    check("a cleartext off-host agent is refused", sc.main(["--config", str(unsafe)]) == 2)
    check("missing satori-python is reported, not a traceback",
          sc.main(["--config", str(file)]) == 2)
