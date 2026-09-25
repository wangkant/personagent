"""Focused contract tests for the bundled AstrBot forwarder plugin."""
from __future__ import annotations

import asyncio
import base64
import enum
import hashlib
import hmac
import importlib.util
import json
import logging
import os
import sys
import types
from datetime import datetime, timezone
from pathlib import Path

import httpx


ROOT = Path(__file__).resolve().parent.parent
PLUGIN_DIR = ROOT / "integrations" / "astrbot" / "astrbot_plugin_llm_persona_gateway"
PLUGIN = PLUGIN_DIR / "main.py"
SDK = ROOT / "integrations" / "sdk" / "personagent_connector.py"
_PACKAGE = "astrbot_gateway_tested"


def _load_plugin_package():
    """Import main.py the way AstrBot does, as a module of the plugin's
    package, so its relative imports resolve."""
    for name in tuple(sys.modules):
        if name == _PACKAGE or name.startswith(_PACKAGE + "."):
            sys.modules.pop(name)
    package = types.ModuleType(_PACKAGE)
    package.__path__ = [str(PLUGIN_DIR)]
    sys.modules[_PACKAGE] = package
    spec = importlib.util.spec_from_file_location(_PACKAGE + ".main", PLUGIN)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _import_plugin():
    def register(name: str) -> types.ModuleType:
        module = types.ModuleType(name)
        sys.modules[name] = module
        return module

    for name in tuple(sys.modules):
        if name == "astrbot" or name.startswith("astrbot."):
            sys.modules.pop(name)

    astrbot = register("astrbot")
    api = register("astrbot.api")
    astrbot.api = api
    api.AstrBotConfig = dict
    api.logger = logging.getLogger("astrbot-plugin-test")
    api.logger.handlers = [logging.NullHandler()]
    api.logger.propagate = False

    event_mod = register("astrbot.api.event")

    class EventMessageType(enum.Flag):
        GROUP_MESSAGE = enum.auto()
        PRIVATE_MESSAGE = enum.auto()
        OTHER_MESSAGE = enum.auto()
        ALL = GROUP_MESSAGE | PRIVATE_MESSAGE | OTHER_MESSAGE

    class Filter:
        @staticmethod
        def event_message_type(_kind):
            return lambda fn: fn

    class MessageChain:
        def __init__(self, chain=None):
            self.chain = list(chain or [])

    Filter.EventMessageType = EventMessageType
    event_mod.AstrMessageEvent = object
    event_mod.MessageChain = MessageChain
    event_mod.filter = Filter

    platform_mod = register("astrbot.api.platform")

    class MessageType(enum.Enum):
        GROUP_MESSAGE = "GroupMessage"
        FRIEND_MESSAGE = "FriendMessage"
        OTHER_MESSAGE = "OtherMessage"

    platform_mod.MessageType = MessageType

    register("astrbot.core")
    register("astrbot.core.platform")
    session_mod = register("astrbot.core.platform.message_session")

    class MessageSession:
        def __init__(self, platform_name, message_type, session_id):
            self.platform_id = platform_name
            self.message_type = message_type
            self.session_id = session_id

        @staticmethod
        def from_str(session_str):
            # AstrBot's own parse, which context.send_message applies.
            platform_id, message_type, session_id = session_str.split(":", 2)
            return MessageSession(platform_id, MessageType(message_type), session_id)

    session_mod.MessageSession = MessageSession

    star_mod = register("astrbot.api.star")

    class Star:
        # AstrBot's plugin store, one per plugin; shared by every instance
        # built from this import, as a reload would see it.
        kv: dict = {}

        def __init__(self, context=None):
            self.context = context

        async def get_kv_data(self, key, default):
            return type(self).kv.get(key, default)

        async def put_kv_data(self, key, value):
            type(self).kv[key] = value

    star_mod.Context = object
    star_mod.Star = Star

    components = register("astrbot.api.message_components")

    class Segment:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class Plain(Segment):
        def __init__(self, text=""):
            super().__init__(text=text)

    class At(Segment):
        pass

    class AtAll(At):
        # AstrBot's AtAll is an At whose qq is "all".
        def __init__(self, **kwargs):
            super().__init__(qq="all", **kwargs)

    class Image(Segment):
        # What AstrBot's download would return, by URL.
        downloads: dict = {}

        def __init__(self, file=None, **kwargs):
            kwargs.setdefault("url", "")
            super().__init__(file=file, **kwargs)

        @classmethod
        def fromBase64(cls, value):
            return cls(file="base64://" + value)

        @classmethod
        def fromFileSystem(cls, path):
            return cls(file="file:///" + os.path.abspath(path), path=path)

        async def convert_to_base64(self):
            src = self.url or self.file or ""
            if src.startswith("base64://"):
                return src[len("base64://"):]
            if src.startswith("file:///"):
                return base64.b64encode(Path(src[len("file:///"):]).read_bytes()).decode()
            if src in Image.downloads:
                return base64.b64encode(Image.downloads[src]).decode()
            raise Exception(f"not a valid file: {src}")

    class Face(Segment):
        pass

    class Reply(Segment):
        pass

    class Video(Segment):
        pass

    class File(Segment):
        pass

    class Record(Segment):
        pass

    components.Plain = Plain
    components.At = At
    components.AtAll = AtAll
    components.Image = Image
    components.Face = Face
    components.Reply = Reply
    components.Video = Video
    components.File = File
    components.Record = Record

    module = _load_plugin_package()
    module.Comp = components
    return module


class _Response:
    def raise_for_status(self):
        return None

    def json(self):
        return {"handled": True, "replies": [{"type": "text", "text": "ok"}]}


class _RecordingClient:
    def __init__(self):
        self.calls = []

    async def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return _Response()

    async def aclose(self):
        return None


class _UnhandledClient(_RecordingClient):
    async def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        response = _Response()
        response.json = lambda: {"handled": False, "replies": []}
        return response


class _SilentButOwnedClient(_RecordingClient):
    """An agent that took the conversation and chose to say nothing."""

    async def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        response = _Response()
        response.json = lambda: {
            "handled": False, "owned": True, "replies": []}
        return response


class _Event:
    def __init__(self, module, *, private: bool, platform: str = "telegram"):
        message_type = (
            module.MessageType.FRIEND_MESSAGE
            if private
            else module.MessageType.GROUP_MESSAGE
        )
        self.message_obj = types.SimpleNamespace(
            type=message_type, message=[], message_id="incoming-1",
            timestamp=1_725_000_000, raw_message=None,
            session_id="user-1" if private else "group-1",
        )
        self.message_str = "hello"
        self._private = private
        self._platform = platform
        self.stopped = False
        self.typing = []
        self.results = []
        self.unified_msg_origin = (
            f"{self.get_platform_id()}:{message_type.value}:"
            f"{self.message_obj.session_id}")

    async def send_typing(self):
        self.typing.append("on")

    async def stop_typing(self):
        self.typing.append("off")

    def get_platform_name(self):
        return self._platform

    def get_platform_id(self):
        return f"my-{self._platform}"

    def get_self_id(self):
        return "bot"

    def get_sender_id(self):
        return "user-1"

    def get_sender_name(self):
        return "Alice"

    def get_group_id(self):
        return "" if self._private else "group-1"

    def is_private_chat(self):
        return self._private

    def chain_result(self, chain):
        return chain

    def stop_event(self):
        self.stopped = True


class _Result(list):
    """A chain_result that records the result flags the plugin sets."""

    def __init__(self, chain):
        super().__init__(chain)
        self.flags = {}

    def use_t2i(self, value):
        self.flags["t2i"] = value
        return self

    def use_markdown(self, value):
        self.flags["markdown"] = value
        return self


class _Inst:
    """A running AstrBot platform adapter instance."""

    def __init__(self, name, pid=None, **attrs):
        self._meta = types.SimpleNamespace(name=name, id=pid or f"my-{name}")
        self.__dict__.update(attrs)

    def meta(self):
        return self._meta


class _Context:
    def __init__(self, *insts, config=None, fail_at=None, refuse=False):
        self.insts = {inst.meta().id: inst for inst in insts}
        self.config = config or {}
        self.sent = []
        self.fail_at = fail_at
        self.refuse = refuse

    def get_platform_inst(self, platform_id):
        return self.insts.get(platform_id)

    def get_config(self, umo=None):
        return self.config

    async def send_message(self, session, chain):
        if self.fail_at is not None and len(self.sent) == self.fail_at:
            raise RuntimeError("platform said no")
        if self.refuse:
            return False
        self.sent.append((session, chain.chain))
        return True


def _plugin_instance(module, config, context=None):
    plugin = module.LLMPersonaGateway(context, config)
    plugin._client = _RecordingClient()
    return plugin


def _run(plugin, event):
    async def collect():
        return [item async for item in plugin.forward_to_agent(event)]
    return asyncio.run(collect())


def _map(plugin, event, platform, self_id="bot"):
    return asyncio.run(plugin._map_segments(event, self_id, platform))


def _names(chain):
    return [type(c).__name__ for c in chain]


async def _no_sleep(_seconds):
    return None


def test_the_vendored_sdk_is_the_sdk():
    """The plugin ships integrations/sdk/personagent_connector.py as a copy
    (AstrBot installs one folder); an edit to either must reach both."""
    vendored = PLUGIN_DIR / "personagent_connector.py"

    def text(path):
        return path.read_bytes().replace(b"\r\n", b"\n")

    assert text(vendored) == text(SDK), (
        "copy integrations/sdk/personagent_connector.py into the plugin folder")


def test_reply_component_preserves_quoted_message_id():
    module = _import_plugin()
    plugin = _plugin_instance(module, {})
    event = _Event(module, private=False, platform="aiocqhttp")
    event.message_obj.message = [module.Comp.Reply(id="quoted-42", sender_id="bot")]

    segments, is_at_me = _map(plugin, event, "")

    assert segments == [{"type": "reply", "message_id": "quoted-42", "sender_id": "bot"}]
    assert is_at_me is True


def test_default_configuration_forwards_neither_groups_nor_private_messages():
    module = _import_plugin()
    plugin = _plugin_instance(module, {})

    assert _run(plugin, _Event(module, private=False)) == []
    assert _run(plugin, _Event(module, private=True)) == []
    assert plugin._client.calls == []


def test_signed_request_uses_canonical_body_and_replay_headers():
    module = _import_plugin()
    plugin = _plugin_instance(
        module,
        {
            "agent_url": "https://agent.example/webhook/gateway",
            "gateway_token": "shared-secret",
        },
    )
    real_time = module.time.time
    real_token_hex = module.sdk.secrets.token_hex
    module.time.time = lambda: 1_725_000_000
    module.sdk.secrets.token_hex = lambda _n: "00112233445566778899aabbccddeeff"
    event = {"z": 1, "message": "你好", "a": [True, None]}
    expected_body = (
        '{"a":[true,null],"message":"你好","z":1}'.encode("utf-8")
    )
    signed = (
        b"1725000000.00112233445566778899aabbccddeeff." + expected_body
    )
    expected_signature = "sha256=" + hmac.new(
        b"shared-secret", signed, hashlib.sha256
    ).hexdigest()

    try:
        delivered, _owned, replies = asyncio.run(plugin._post_to_agent(event))
    finally:
        module.time.time = real_time
        module.sdk.secrets.token_hex = real_token_hex

    assert delivered is True
    assert replies == [{"type": "text", "text": "ok"}]
    assert len(plugin._client.calls) == 1
    url, request = plugin._client.calls[0]
    assert url == "https://agent.example/webhook/gateway"
    assert request["content"] == expected_body
    assert "json" not in request
    assert request["headers"] == {
        "Content-Type": "application/json",
        "X-Gateway-Token": "shared-secret",
        "X-Gateway-Timestamp": "1725000000",
        "X-Gateway-Nonce": "00112233445566778899aabbccddeeff",
        "X-Gateway-Signature": expected_signature,
    }


def test_off_host_endpoint_requires_https_and_a_token():
    module = _import_plugin()

    insecure = _plugin_instance(
        module,
        {
            "agent_url": "http://agent.example/webhook/gateway",
            "gateway_token": "shared-secret",
        },
    )
    no_token = _plugin_instance(
        module, {"agent_url": "https://agent.example/webhook/gateway"}
    )

    assert asyncio.run(
        insecure._post_to_agent({"message": "hello"})) == (False, False, [])
    assert asyncio.run(
        no_token._post_to_agent({"message": "hello"})) == (False, False, [])
    assert insecure._client.calls == []
    assert no_token._client.calls == []


def test_malformed_endpoint_is_rejected_without_a_request():
    module = _import_plugin()
    plugin = _plugin_instance(
        module,
        {
            "agent_url": "http://[broken",
            "gateway_token": "shared-secret",
        },
    )

    assert asyncio.run(
        plugin._post_to_agent({"message": "hello"})) == (False, False, [])
    assert plugin._client.calls == []


_DM_CONFIG = {"private_enabled": True, "private_whitelist": ["user-1"], "block_default": True}


def test_forwarding_failure_does_not_stop_astrbot_fallback():
    module = _import_plugin()
    plugin = _plugin_instance(module, dict(_DM_CONFIG))
    event = _Event(module, private=True)

    async def fail(_neutral_event):
        return False, False, []

    plugin._post_to_agent = fail

    assert _run(plugin, event) == []
    assert event.stopped is False


def test_unhandled_gateway_response_does_not_stop_astrbot_fallback():
    module = _import_plugin()
    plugin = _plugin_instance(module, dict(_DM_CONFIG))
    plugin._client = _UnhandledClient()
    event = _Event(module, private=True)

    assert _run(plugin, event) == []
    assert event.stopped is False


def test_a_silent_but_owned_conversation_blocks_the_fallback():
    """The agent is quiet far more often than it speaks — a PASS, a debounce
    merge, the rhythm gate. Treating that as "not mine" hands the room to
    AstrBot's own model, which answers in it as someone else. The test above
    pins the other direction: an agent too old to send `owned` still falls
    back to `handled`, so nothing changes for it."""
    module = _import_plugin()
    plugin = _plugin_instance(module, dict(_DM_CONFIG))
    plugin._client = _SilentButOwnedClient()
    event = _Event(module, private=True)

    assert _run(plugin, event) == []
    assert event.stopped is True


def test_forwarded_event_carries_source_timestamp_and_success_blocks_fallback():
    module = _import_plugin()
    plugin = _plugin_instance(module, dict(_DM_CONFIG))
    event = _Event(module, private=True)
    captured = {}

    async def succeed(neutral_event):
        captured.update(neutral_event)
        return True, True, []

    plugin._post_to_agent = succeed

    assert _run(plugin, event) == []
    assert captured["source_timestamp"] == 1_725_000_000
    assert event.stopped is True


def test_typing_indicator_brackets_the_round_trip(monkeypatch):
    module = _import_plugin()
    plugin = _plugin_instance(module, {"private_enabled": True, "private_whitelist": ["user-1"]})
    event = _Event(module, private=True)

    async def two_bubbles(_neutral):
        return True, True, [{"type": "text", "text": "a"}, {"type": "text", "text": "b"}]

    plugin._post_to_agent = two_bubbles
    # `module.asyncio` IS the asyncio module, so this has to be undone: a bare
    # assignment left every later test in the run without a real sleep.
    monkeypatch.setattr(module.asyncio, "sleep", _no_sleep)
    out = _run(plugin, event)
    assert len(out) == 2
    # on before the request, on again before the second bubble, off at the end
    assert event.typing == ["on", "on", "off"], event.typing


def test_discord_text_unfolds_mentions_emoji_and_channels():
    module = _import_plugin()
    plugin = _plugin_instance(module, {})
    event = _Event(module, private=False, platform="discord")
    event.message_obj.raw_message = types.SimpleNamespace(
        mentions=[types.SimpleNamespace(id=42, display_name="Bob")],
        role_mentions=[types.SimpleNamespace(id=7, name="mods")],
        channel_mentions=[types.SimpleNamespace(id=9, name="general")],
    )
    event.message_obj.message = [module.Comp.Plain("hey <@42> see <#9> <a:party:1> <@&7> <@!99>")]
    segments, _ = _map(plugin, event, "discord")
    assert segments == [
        {"type": "text", "text": "hey "},
        {"type": "mention", "user_id": "42", "name": "Bob"},
        {"type": "text", "text": " see #general :party: @mods "},
        {"type": "mention", "user_id": "99", "name": ""},
    ], segments


def test_slack_links_are_unfolded_and_mentions_go_out_as_mrkdwn():
    module = _import_plugin()
    plugin = _plugin_instance(module, {})
    event = _Event(module, private=False, platform="slack")
    event.message_obj.message = [module.Comp.Plain("look <https://x.io|the site> &amp; <https://y.io>")]
    segments, _ = _map(plugin, event, "slack")
    assert segments == [{"type": "text", "text": "look the site (https://x.io) & https://y.io"}], segments
    [(chain, _)] = plugin._render(
        [{"type": "text", "text": "hi & bye", "at_user_id": "slack:U1"}], "slack", True, "C1", [])
    assert _names(chain) == ["Plain"], chain
    assert chain[0].text == "<@U1> hi &amp; bye", chain[0].__dict__
    [(chain, _)] = plugin._render(
        [{"type": "text", "text": "hi", "at_user_id": "discord:5"}], "discord", True, "C1", [])
    assert _names(chain) == ["At", "Plain"], chain
    assert chain[1].text == " hi"


def test_media_components_become_notes_the_agent_can_read():
    module = _import_plugin()
    plugin = _plugin_instance(module, {})
    event = _Event(module, private=False)
    event.message_obj.message = [
        module.Comp.Video(file="v.mp4"), module.Comp.File(name="deck.pdf"),
        module.Comp.Record(file="a.ogg"), module.Comp.Plain("thoughts?"),
    ]
    segments, _ = _map(plugin, event, "telegram")
    assert [s["text"] for s in segments] == [
        "(sent a video)", "(sent a file: deck.pdf)", "(sent a voice message)", "thoughts?"], segments


def test_missing_source_timestamp_is_not_forwarded_or_blocked():
    module = _import_plugin()
    plugin = _plugin_instance(module, dict(_DM_CONFIG))
    event = _Event(module, private=True)
    event.message_obj.timestamp = None

    assert _run(plugin, event) == []
    assert plugin._client.calls == []
    assert event.stopped is False


def _group_addressing(module, platform, components, *, wake_flag=False,
                      message_str="hello", raw=None, context=None):
    """Forward one whitelisted group event; return what the agent was sent."""
    plugin = _plugin_instance(module, {"group_whitelist": ["group-1"]}, context)
    event = _Event(module, private=False, platform=platform)
    event.message_obj.message = components
    event.message_obj.raw_message = raw
    event.message_str = message_str
    event.is_at_or_wake_command = wake_flag
    captured = {}

    async def capture(neutral_event):
        captured.update(neutral_event)
        return False, False, []

    plugin._post_to_agent = capture
    _run(plugin, event)
    return captured


def test_an_at_all_announcement_does_not_address_the_persona():
    """AstrBot raises is_at_or_wake_command for every @all (ignore_at_all is
    off by default). Reading that as an @ of the bot made the persona answer
    every group notice and adjudicate it as a reaction to itself."""
    module = _import_plugin()
    sent = _group_addressing(
        module, "aiocqhttp",
        [module.Comp.AtAll(), module.Comp.Plain(" meeting at 8")],
        wake_flag=True, message_str="meeting at 8")
    assert sent["is_at_me"] is False, sent


def test_a_slash_command_does_not_address_the_persona():
    """'/' is AstrBot's default wake prefix, so /help (or another bot's
    Telegram command) sets the wake flag without saying anything to us."""
    module = _import_plugin()
    sent = _group_addressing(
        module, "aiocqhttp", [module.Comp.Plain("/help")],
        wake_flag=True, message_str="/help")
    assert sent["is_at_me"] is False, sent


def test_a_telegram_reply_to_the_bot_addresses_it_and_loses_the_artifact():
    module = _import_plugin()
    for prefix in ("/ ", "/@bot "):
        sent = _group_addressing(
            module, "telegram",
            [module.Comp.Reply(id="77", sender_id="123456"),
             module.Comp.Plain(prefix + "hello")],
            wake_flag=True, message_str=prefix + "hello")
        assert sent["is_at_me"] is True, (prefix, sent)
        assert sent["segments"][1] == {"type": "text", "text": "hello"}, sent
        assert sent["raw_text"] == "hello", sent


def test_a_real_at_of_the_bot_still_addresses_it():
    module = _import_plugin()
    sent = _group_addressing(
        module, "aiocqhttp",
        [module.Comp.At(qq="bot", name="Bot"), module.Comp.Plain(" hi")],
        wake_flag=True)
    assert sent["is_at_me"] is True, sent


class _StatusResponse:
    def __init__(self, status, headers=None):
        self.status_code = status
        self.headers = headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"HTTP {self.status_code}", request=None, response=self)

    def json(self):
        if self.status_code >= 400:
            return {"error": "busy"}
        return {"handled": True, "replies": [{"type": "text", "text": "ok"}]}


class _ScriptedClient(_RecordingClient):
    """Answers each post with the next scripted response."""

    def __init__(self, responses):
        super().__init__()
        self._responses = list(responses)

    async def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self._responses.pop(0)


def _retry_rig(monkeypatch, module, config, responses, *, now=1_725_000_000):
    plugin = _plugin_instance(module, config)
    plugin._client = _ScriptedClient(responses)
    sleeps = []

    async def record_sleep(seconds):
        sleeps.append(seconds)

    monkeypatch.setattr(module.asyncio, "sleep", record_sleep)
    clock = {"now": now}
    monkeypatch.setattr(module.time, "time", lambda: clock["now"])
    return plugin, sleeps, clock


def test_each_attempt_gets_the_full_timeout(monkeypatch):
    """The agent checks the envelope's age on arrival, so there is no reason
    to split timeout_s across attempts — doing so capped every signed request
    at 93 s whatever the operator set."""
    module = _import_plugin()
    for config in ({"gateway_token": "t", "timeout_s": 180}, {"timeout_s": 180}):
        plugin, _sleeps, _clock = _retry_rig(
            monkeypatch, module, config, [_StatusResponse(200)])
        delivered, _owned, _replies = asyncio.run(
            plugin._post_to_agent({"message": "hi"}))
        assert delivered is True
        assert plugin._client.calls[0][1]["timeout"] == 180, config


def test_a_429_is_retried_after_its_retry_after(monkeypatch):
    module = _import_plugin()
    for config in ({"gateway_token": "t"}, {}):
        plugin, sleeps, _clock = _retry_rig(
            monkeypatch, module, config,
            [_StatusResponse(429, {"Retry-After": "3"}), _StatusResponse(200)])
        delivered, _owned, replies = asyncio.run(
            plugin._post_to_agent({"message": "hi"}))
        assert delivered is True, config
        assert replies == [{"type": "text", "text": "ok"}]
        assert sleeps == [3.0], (config, sleeps)
        assert len(plugin._client.calls) == 2


def test_no_retry_once_the_signed_envelope_would_arrive_stale(monkeypatch):
    module = _import_plugin()
    plugin, sleeps, clock = _retry_rig(
        monkeypatch, module, {"gateway_token": "t"},
        [_StatusResponse(500), _StatusResponse(200)])
    real_post = plugin._client.post

    async def slow_post(url, **kwargs):
        response = await real_post(url, **kwargs)
        clock["now"] += 290  # the first attempt failed 290 s after signing
        return response

    plugin._client.post = slow_post
    assert asyncio.run(
        plugin._post_to_agent({"message": "hi"})) == (False, False, [])
    assert len(plugin._client.calls) == 1
    assert sleeps == []


# ---------------------------------------------------------------------------
# Inbound, per platform: what each adapter delivers, read the way people
# meant it (AstrBot 4.25.5)
# ---------------------------------------------------------------------------

def _onebot(messages, **fields):
    """The raw OneBot v11 event the aiocqhttp adapter keeps."""
    raw = {"post_type": "message", "time": 1_700_000_000, "message": messages}
    raw.update(fields)
    return raw


def test_qq_notices_and_requests_are_not_forwarded_as_turns():
    """aiocqhttp types pokes, recalls and friend requests as messages with an
    empty chain; each reached the agent as an empty turn."""
    module = _import_plugin()
    for post_type in ("notice", "request"):
        sent = _group_addressing(module, "aiocqhttp", [], message_str="",
                                 raw={"post_type": post_type, "sub_type": "poke"})
        assert sent == {}, (post_type, sent)
    sent = _group_addressing(module, "aiocqhttp", [module.Comp.Plain("hi")],
                             raw=_onebot([{"type": "text", "data": {"text": "hi"}}]))
    assert sent["segments"] == [{"type": "text", "text": "hi"}]


def test_qq_faces_stickers_and_time_come_from_the_raw_event():
    module = _import_plugin()
    raw = _onebot([
        {"type": "face", "data": {"id": "178", "raw": {"faceText": "/斜眼笑"}}},
        {"type": "image", "data": {"file": "a.gif", "sub_type": 1, "summary": "[动画表情]"}},
        {"type": "mface", "data": {"summary": "[吃瓜]", "emoji_id": "e1"}},
    ], time=1_700_000_123)
    sent = _group_addressing(module, "aiocqhttp", [
        module.Comp.Face(id=178),
        module.Comp.Image(file="a.gif", url="https://multimedia.nt.qq.com.cn/a"),
    ], raw=raw)
    assert sent["segments"] == [
        {"type": "emoji", "name": "斜眼笑", "id": "178"},
        {"type": "image", "url": "https://multimedia.nt.qq.com.cn/a", "sticker": True},
        {"type": "emoji", "name": "吃瓜", "id": "e1"},
    ], sent["segments"]
    assert sent["source_timestamp"] == 1_700_000_123


def test_a_qq_at_the_adapter_could_not_look_up_still_addresses_the_bot():
    module = _import_plugin()
    raw = _onebot([{"type": "at", "data": {"qq": "bot"}}, {"type": "text", "data": {"text": "hi"}}])
    sent = _group_addressing(module, "aiocqhttp", [module.Comp.Plain("hi")], raw=raw)
    assert sent["is_at_me"] is True


def test_a_quote_carries_its_text_and_sender():
    module = _import_plugin()
    quoted = module.Comp.Reply(id="9", sender_id="555", sender_nickname="Bob",
                               message_str="see you at " + "x" * 300)
    sent = _group_addressing(module, "aiocqhttp", [quoted, module.Comp.Plain("ok")],
                             raw=_onebot([]))
    reply = sent["segments"][0]
    assert reply["message_id"] == "9" and reply["sender_id"] == "555"
    assert reply["sender_name"] == "Bob"
    assert reply["text"].startswith("see you at ") and len(reply["text"]) == 201
    assert "quote_text" in sent["caps"]

    plugin = _plugin_instance(module, {"forward_quoted_text": False})
    event = _Event(module, private=False, platform="aiocqhttp")
    event.message_obj.message = [quoted]
    segments, _ = _map(plugin, event, "aiocqhttp")
    assert segments == [{"type": "reply", "message_id": "9"}], segments


def test_a_quoted_photo_without_caption_is_outlined():
    module = _import_plugin()
    quoted = module.Comp.Reply(id="9", sender_id="1", message_str="",
                               chain=[module.Comp.Image(file="https://x/y.jpg")])
    sent = _group_addressing(module, "aiocqhttp", [quoted, module.Comp.Plain("lol")],
                             raw=_onebot([]))
    assert sent["segments"][0]["text"] == "(image)"


def _tg_update(*, text="hi", sticker=None, reply_from=None, date=1_700_000_500):
    user = types.SimpleNamespace(id=4242, username="alice", full_name="Alice A")
    quoted = None
    if reply_from is not None:
        quoted = types.SimpleNamespace(
            message_id=31, text="earlier", caption=None,
            from_user=types.SimpleNamespace(id=1, username=reply_from, full_name=""))
    message = types.SimpleNamespace(
        text=text, sticker=sticker, reply_to_message=quoted, from_user=user,
        date=datetime.fromtimestamp(date, tz=timezone.utc),
        is_topic_message=False, message_thread_id=None)
    return types.SimpleNamespace(message=message)


def test_a_telegram_photo_reply_to_the_bot_addresses_it_without_the_artifact():
    """The adapter's '/@bot' hack exists for text messages only; a photo
    replying to the bot carried no sign of it."""
    module = _import_plugin()
    url = "https://api.telegram.org/file/botTOKEN/p.jpg"
    module.Comp.Image.downloads[url] = b"\xff\xd8jpeg"
    sent = _group_addressing(module, "telegram", [
        module.Comp.Reply(id="31", sender_id="1", sender_nickname="bot", message_str="earlier"),
        module.Comp.Image(file=url, url=url),
    ], raw=_tg_update(text=None, reply_from="Bot"), message_str="")
    assert sent["is_at_me"] is True
    assert sent["source_timestamp"] == 1_700_000_500
    image = sent["segments"][1]
    assert image == {"type": "image", "b64": base64.b64encode(b"\xff\xd8jpeg").decode()}
    assert "api.telegram.org" not in json.dumps(sent), "the bot token left AstrBot"


def test_telegram_files_come_through_the_adapters_own_bot():
    """The adapter's bot carries its proxy settings; AstrBot's generic
    download does not."""
    module = _import_plugin()
    fetched = []

    class _Request:
        async def retrieve(self, url):
            fetched.append(url)
            return bytearray(b"\xff\xd8via-bot")

    raw = _tg_update(text=None)
    raw.message.get_bot = lambda: types.SimpleNamespace(request=_Request())
    url = "https://api.telegram.org/file/botTOKEN/q.jpg"
    sent = _group_addressing(module, "telegram", [module.Comp.Image(file=url, url=url)],
                             raw=raw, message_str="")
    assert fetched == [url]
    assert sent["segments"] == [{"type": "image",
                                 "b64": base64.b64encode(b"\xff\xd8via-bot").decode()}]


def test_a_telegram_sticker_is_an_emoji_and_an_animated_one_has_no_image():
    module = _import_plugin()
    url = "https://api.telegram.org/file/botTOKEN/s.webp"
    module.Comp.Image.downloads[url] = b"RIFF0000WEBPVP8 "
    for animated, expect_image in ((False, True), (True, False)):
        sticker = types.SimpleNamespace(emoji="😀", is_animated=animated, is_video=False)
        sent = _group_addressing(module, "telegram", [
            module.Comp.Image(file=url, url=url), module.Comp.Plain("Sticker: 😀"),
        ], raw=_tg_update(text=None, sticker=sticker), message_str="Sticker: 😀")
        kinds = [s["type"] for s in sent["segments"]]
        assert kinds == (["image", "emoji"] if expect_image else ["emoji"]), sent["segments"]
        assert sent["segments"][-1] == {"type": "emoji", "name": "😀"}
        if expect_image:
            assert sent["segments"][0]["sticker"] is True
        assert sent["raw_text"] == "", "the adapter's 'Sticker:' words are not the person's"


def test_telegram_mentions_by_username_become_the_senders_numeric_id():
    module = _import_plugin()
    plugin = _plugin_instance(module, {"group_whitelist": ["group-1"]})
    first = _Event(module, private=False, platform="telegram")
    first.message_obj.raw_message = _tg_update()  # alice (4242) talks once
    captured = {}

    async def capture(neutral_event):
        captured.update(neutral_event)
        return False, False, []

    plugin._post_to_agent = capture
    _run(plugin, first)
    second = _Event(module, private=False, platform="telegram")
    second.message_obj.message = [module.Comp.At(qq="Alice", name="Alice"), module.Comp.Plain("hi")]
    _run(plugin, second)
    assert captured["segments"][0] == {"type": "mention", "user_id": "4242", "name": "Alice"}


def _discord_message(**fields):
    base = dict(mentions=[], role_mentions=[], channel_mentions=[], stickers=[],
                attachments=[], reference=None, guild=None,
                created_at=datetime.fromtimestamp(1_700_000_900, tz=timezone.utc))
    base.update(fields)
    return types.SimpleNamespace(**base)


def test_a_discord_leading_mention_the_adapter_stripped_still_addresses_the_bot():
    module = _import_plugin()
    bot = types.SimpleNamespace(id="bot", display_name="Nova")
    sent = _group_addressing(module, "discord", [module.Comp.Plain("how was your day")],
                             raw=_discord_message(mentions=[bot]))
    assert sent["is_at_me"] is True
    assert sent["source_timestamp"] == 1_700_000_900

    role = types.SimpleNamespace(id=77, name="bots")
    sent = _group_addressing(module, "discord", [module.Comp.Plain("hey")], raw=_discord_message(
        role_mentions=[role], guild=types.SimpleNamespace(me=types.SimpleNamespace(roles=[role]))))
    assert sent["is_at_me"] is True


def test_a_discord_reply_quotes_the_resolved_message():
    module = _import_plugin()
    resolved = _discord_message(
        content="ask <@42> about it", mentions=[types.SimpleNamespace(id=42, display_name="Bob")],
        author=types.SimpleNamespace(id="bot", display_name="Nova"))
    raw = _discord_message(reference=types.SimpleNamespace(message_id=880, resolved=resolved))
    sent = _group_addressing(module, "discord", [module.Comp.Plain("ok")], raw=raw)
    assert sent["segments"][0] == {"type": "reply", "message_id": "880", "text": "ask @Bob about it",
                                   "sender_id": "bot", "sender_name": "Nova"}, sent["segments"]
    assert sent["is_at_me"] is True


def test_discord_stickers_and_voice_attachments_are_not_lost():
    module = _import_plugin()
    sticker = types.SimpleNamespace(id=5, name="Wumpus wave",
                                    url="https://media.discordapp.net/stickers/5.png",
                                    format=types.SimpleNamespace(name="png"))
    voice = types.SimpleNamespace(url="https://cdn/voice.ogg", filename="voice-message.ogg",
                                  content_type="audio/ogg")
    sent = _group_addressing(module, "discord", [
        module.Comp.File(name="voice-message.ogg", url="https://cdn/voice.ogg"),
    ], raw=_discord_message(stickers=[sticker], attachments=[voice]), message_str="")
    assert sent["segments"] == [
        {"type": "text", "text": "(sent a voice message)"},
        {"type": "emoji", "name": "Wumpus wave", "id": "5"},
        {"type": "image", "url": "https://media.discordapp.net/stickers/5.png", "sticker": True},
    ], sent["segments"]


def test_a_lark_reply_to_the_bot_names_the_app_as_sender():
    module = _import_plugin()
    context = _Context(_Inst("lark", appid="cli_app"))
    sent = _group_addressing(module, "lark", [
        module.Comp.Reply(id="om_1", sender_id="cli_app", sender_nickname="cli_app",
                          message_str="hi"),
        module.Comp.Plain("and you?"),
    ], context=context)
    assert sent["is_at_me"] is True
    assert "sender_name" not in sent["segments"][0], "id[:8] is not a name"


def test_slack_threads_subtypes_and_message_ids():
    module = _import_plugin()
    raw = {"ts": "1700000000.000200", "thread_ts": "1699999999.000100",
           "parent_user_id": "bot", "text": "sure"}
    sent = _group_addressing(module, "slack", [module.Comp.Plain("sure")], raw=raw)
    assert sent["is_at_me"] is True
    assert sent["message_id"] == "1700000000.000200"
    assert sent["segments"][0] == {"type": "reply", "message_id": "1699999999.000100",
                                   "sender_id": "bot"}
    joined = _group_addressing(module, "slack", [module.Comp.Plain("has joined")],
                               raw={"ts": "1.2", "subtype": "channel_join"})
    assert joined == {}


def test_kook_emoji_quotes_and_time():
    module = _import_plugin()
    raw = {"msg_timestamp": 1_700_000_700_123,
           "extra": {"quote": {"id": "q1", "content": "hello (emj)wave(emj)[1/abc]",
                               "author": {"id": "bot", "username": "Nova"}}}}
    sent = _group_addressing(
        module, "kook", [module.Comp.Plain("nice (emj)smile(emj)[2/xyz] \\*wow\\*")], raw=raw)
    assert sent["source_timestamp"] == 1_700_000_700
    assert sent["is_at_me"] is True
    assert sent["segments"] == [
        {"type": "reply", "message_id": "q1", "text": "hello :wave:",
         "sender_id": "bot", "sender_name": "Nova"},
        {"type": "text", "text": "nice "},
        {"type": "emoji", "name": "smile", "id": "2/xyz"},
        {"type": "text", "text": " *wow*"},
    ], sent["segments"]


def test_a_wecom_smart_bot_group_is_a_group_that_addressed_the_bot():
    module = _import_plugin()
    plugin = _plugin_instance(module, {"group_whitelist": ["chat-9"]})
    event = _Event(module, private=False, platform="wecom_ai_bot")
    event.get_group_id = lambda: ""  # the adapter never sets it
    event.message_obj.raw_message = {"message_data": {"chatid": "chat-9", "msgid": "m-7",
                                                      "msgtype": "voice"}}
    event.message_obj.message = [module.Comp.Plain("[voice消息]")]
    event.message_str = "[voice消息]"
    captured = {}

    async def capture(neutral_event):
        captured.update(neutral_event)
        return False, False, []

    plugin._post_to_agent = capture
    _run(plugin, event)
    assert captured["message_type"] == "group" and captured["conversation_id"] == "chat-9"
    assert captured["is_at_me"] is True
    assert captured["message_id"] == "m-7"
    assert captured["segments"] == [{"type": "text", "text": "(sent a voice message)"}]
    assert "outbox" not in captured["caps"]


def test_satori_milliseconds_and_quote_senders():
    module = _import_plugin()
    raw = {"message": {"quote": {"user": {"id": "bot", "nick": "Nova"}}, "content": "ok"}}
    sent = _group_addressing(module, "satori", [
        module.Comp.Reply(id="q", sender_id="", sender_nickname="内容", message_str="earlier"),
        module.Comp.Plain("ok"),
    ], raw=raw)
    assert sent["is_at_me"] is True
    assert sent["segments"][0]["sender_name"] == "Nova"
    # Without a quote author the adapter writes placeholders, not a quote.
    sent = _group_addressing(module, "satori", [
        module.Comp.Reply(id="q", sender_id="", sender_nickname="内容", message_str="[引用消息]",
                          chain=[]),
        module.Comp.Plain("ok"),
    ], raw={"message": {"quote": {"id": "q"}}})
    assert sent["segments"][0] == {"type": "reply", "message_id": "q"}, sent["segments"]

    plugin = _plugin_instance(module, {"group_whitelist": ["group-1"]})
    event = _Event(module, private=False, platform="satori")
    event.message_obj.timestamp = 1_700_000_800_456
    captured = {}

    async def capture(neutral_event):
        captured.update(neutral_event)
        return False, False, []

    plugin._post_to_agent = capture
    _run(plugin, event)
    assert captured["source_timestamp"] == 1_700_000_800


def test_line_stickers_and_self_mentions():
    module = _import_plugin()
    raw = {"message": {"type": "sticker", "stickerId": "52002734", "keywords": ["Hi", "wave"]}}
    sent = _group_addressing(module, "line", [module.Comp.Plain("[sticker]")], raw=raw,
                             message_str="[sticker]")
    assert sent["segments"] == [{"type": "emoji", "name": "Hi", "id": "52002734"}]
    raw = {"message": {"type": "text", "mention": {"mentionees": [{"isSelf": True}]}}}
    sent = _group_addressing(module, "line", [module.Comp.Plain("@Nova hi")], raw=raw)
    assert sent["is_at_me"] is True


def test_qq_official_takes_the_platforms_iso_timestamp():
    module = _import_plugin()
    raw = types.SimpleNamespace(timestamp="2023-11-14T22:13:20+00:00")
    sent = _group_addressing(module, "qq_official",
                             [module.Comp.At(qq="bot"), module.Comp.Plain("hi")], raw=raw)
    assert sent["source_timestamp"] == 1_700_000_000
    assert sent["is_at_me"] is True
    assert "outbox" not in sent["caps"]


def test_local_and_private_images_are_inlined_and_oversized_ones_described(tmp):
    """DingTalk, Mattermost, WebChat and personal WeChat hand over a path on
    the AstrBot host; the agent cannot open it."""
    module = _import_plugin()
    picture = tmp / "p.jpg"
    picture.write_bytes(b"\xff\xd8local")
    plugin = _plugin_instance(module, {"max_inline_image_bytes": 1000})
    event = _Event(module, private=False, platform="dingtalk")
    event.message_obj.message = [
        module.Comp.Image(file="file:///" + str(picture)),
        module.Comp.Image(file="http://127.0.0.1:3000/img.png"),
        module.Comp.Image(file="data:image/png;base64,iVBORw0K"),
        module.Comp.Image(file="https://cdn.example.com/public.png"),
    ]
    module.Comp.Image.downloads["http://127.0.0.1:3000/img.png"] = b"x" * 5000
    segments, _ = _map(plugin, event, "dingtalk")
    assert segments == [
        {"type": "image", "b64": base64.b64encode(b"\xff\xd8local").decode()},
        {"type": "text", "text": "(sent an image)"},
        {"type": "image", "b64": "iVBORw0K"},
        {"type": "image", "url": "https://cdn.example.com/public.png"},
    ], segments


def test_voice_transcripts_ride_along_where_the_platform_has_one():
    module = _import_plugin()
    plugin = _plugin_instance(module, {})
    event = _Event(module, private=True, platform="wecom")
    event.message_obj.raw_message = types.SimpleNamespace(recognition="call me later")
    event.message_obj.message = [module.Comp.Record(file="a.wav")]
    segments, _ = _map(plugin, event, "wecom")
    assert segments == [{"type": "text", "text": "(sent a voice message: call me later)"}]


def test_wecom_customer_service_hears_only_the_customer():
    module = _import_plugin()
    plugin = _plugin_instance(module, dict(_DM_CONFIG))
    for origin, forwarded in ((3, True), (5, False)):
        event = _Event(module, private=True, platform="wecom")
        event.message_obj.raw_message = {"_wechat_kf_flag": None, "origin": origin,
                                         "send_time": 1_700_000_050}
        plugin._client = _RecordingClient()
        _run(plugin, event)
        assert bool(plugin._client.calls) is forwarded, origin


# ---------------------------------------------------------------------------
# Outbound, per platform: each adapter's own mention, length limit and
# formatting
# ---------------------------------------------------------------------------

def _render(plugin, platform, *items, group=True, temps=None):
    return plugin._render(list(items), platform, group, "group-1",
                          [] if temps is None else temps)


def test_qq_mentions_carry_one_space_and_long_text_stays_under_the_forward_card():
    """The aiocqhttp adapter adds its own space after an At, and AstrBot turns
    any reply over forward_threshold into a merged-forward card."""
    module = _import_plugin()
    context = _Context(config={"platform_settings": {"forward_threshold": 120}})
    plugin = _plugin_instance(module, {}, context)
    [(chain, done)] = _render(plugin, "aiocqhttp",
                              {"type": "text", "text": "hi", "at_user_id": "aiocqhttp:42"})
    assert _names(chain) == ["At", "Plain"] and chain[1].text == "hi" and done == 1
    long = " ".join(["this sentence keeps going."] * 20)
    chains = _render(plugin, "aiocqhttp", {"type": "text", "text": long})
    assert len(chains) > 1
    assert all(len(c[0][0].text) <= 120 for c in chains)
    assert " ".join(c[0][0].text for c in chains) == long
    assert {c[1] for c in chains} == {1}


def test_telegram_text_is_shown_as_typed_and_mentions_use_usernames():
    module = _import_plugin()
    plugin = _plugin_instance(module, {})
    [(chain, _)] = _render(plugin, "telegram", {"type": "text", "text": "*sighs* 2*3"})
    assert chain[0].text == "\\*sighs\\* 2\\*3"
    plugin._people.see("telegram", "4242", "alice", "Alice A")
    plugin._people.see("telegram", "77", None, "Bo [x]")
    [(chain, _)] = _render(plugin, "telegram",
                           {"type": "text", "text": "hi", "at_user_id": "telegram:4242"})
    assert _names(chain) == ["At", "Plain"] and chain[0].name == "alice", chain
    [(chain, _)] = _render(plugin, "telegram",
                           {"type": "text", "text": "hi", "at_user_id": "telegram:77"})
    assert chain[0].text == "[Bo \\[x\\]](tg://user?id=77) hi", chain[0].text
    [(chain, _)] = _render(plugin, "telegram",
                           {"type": "text", "text": "hi", "at_user_id": "telegram:99"})
    assert _names(chain) == ["Plain"] and chain[0].text == "hi", "an unknown id is inert"


def test_kook_mentions_inline_and_images_go_through_a_file(tmp):
    module = _import_plugin()
    plugin = _plugin_instance(module, {})
    [(chain, _)] = _render(plugin, "kook",
                           {"type": "text", "text": "hi (met)all(met)", "at_user_id": "kook:9"})
    assert _names(chain) == ["Plain"]
    assert chain[0].text == "(met)9(met) hi \\(met\\)all\\(met\\)", chain[0].text
    temps = []
    png = base64.b64encode(b"\x89PNG\r\n\x1a\nrest").decode()
    [(chain, _)] = _render(plugin, "kook", {"type": "image", "b64": png}, temps=temps)
    assert chain[0].file.startswith("file:///") and temps and temps[0].endswith(".png")
    assert Path(temps[0]).read_bytes().startswith(b"\x89PNG")
    module._remove_files(temps)
    assert not Path(temps[0]).exists()


def test_discord_splits_at_2000_and_keeps_everyone_pings_inert():
    module = _import_plugin()
    plugin = _plugin_instance(module, {})
    chains = _render(plugin, "discord", {"type": "text", "text": "@everyone " + "word " * 600})
    assert len(chains) == 2 and all(len(c[0][0].text) <= 2000 for c in chains)
    assert chains[0][0][0].text.startswith("@​everyone")


def test_platforms_without_mentions_drop_them_cleanly():
    module = _import_plugin()
    plugin = _plugin_instance(module, {})
    for platform in ("qq_official", "dingtalk", "line", "wecom_ai_bot"):
        [(chain, _)] = _render(plugin, platform,
                               {"type": "text", "text": "hi", "at_user_id": f"{platform}:1"})
        assert _names(chain) == ["Plain"] and chain[0].text == "hi", (platform, chain)


def test_qq_official_replies_ask_for_plain_text_and_every_reply_skips_t2i():
    module = _import_plugin()
    plugin = _plugin_instance(module, {"group_whitelist": ["group-1"]})
    event = _Event(module, private=False, platform="qq_official")
    event.chain_result = _Result

    async def reply(_neutral):
        return True, True, [{"type": "text", "text": "**hi**"}]

    plugin._post_to_agent = reply
    [result] = _run(plugin, event)
    assert result.flags == {"t2i": False, "markdown": False}


def test_wecom_splits_by_bytes():
    module = _import_plugin()
    plugin = _plugin_instance(module, {})
    chains = _render(plugin, "wecom", {"type": "text", "text": "好" * 1000}, group=False)
    assert len(chains) == 2
    assert all(len(c[0][0].text.encode("utf-8")) <= 2048 for c in chains)


def test_one_message_platforms_get_the_turn_as_one_and_line_batches():
    module = _import_plugin()
    plugin = _plugin_instance(module, {})
    items = [{"type": "text", "text": "a"}, {"type": "text", "text": "b"},
             {"type": "image", "b64": "AAAA"}]
    [(chain, done)] = _render(plugin, "wecom_ai_bot", *items)
    assert _names(chain) == ["Plain", "Image"] and chain[0].text == "a\nb" and done == 3
    many = [{"type": "text", "text": str(n)} for n in range(7)]
    chains = _render(plugin, "line", *many)
    assert [len(c[0]) for c in chains] == [5, 2] and [c[1] for c in chains] == [5, 7]


# ---------------------------------------------------------------------------
# The connector: forwarder id, reply handle, capabilities, and the outbox
# ---------------------------------------------------------------------------

def _capture_event(plugin, event):
    captured = {}

    async def capture(neutral_event):
        captured.update(neutral_event)
        return False, False, []

    plugin._post_to_agent = capture
    _run(plugin, event)
    return captured


def test_the_forwarder_id_is_made_once_and_kept():
    module = _import_plugin()
    first = _plugin_instance(module, dict(_DM_CONFIG))
    asyncio.run(first._ensure_forwarder_id())
    second = _plugin_instance(module, dict(_DM_CONFIG))  # a reload
    sent = _capture_event(second, _Event(module, private=True))
    assert sent["forwarder_id"] == first._forwarder_id
    assert sent["forwarder_id"].startswith("astrbot-")
    configured = _plugin_instance(module, dict(_DM_CONFIG, forwarder_id="home-bot"))
    assert _capture_event(configured, _Event(module, private=True))["forwarder_id"] == "home-bot"


def test_the_reply_handle_is_the_umo_and_the_group_under_session_isolation():
    module = _import_plugin()
    plugin = _plugin_instance(module, {"group_whitelist": ["group-1"]})
    event = _Event(module, private=False, platform="dingtalk")
    assert _capture_event(plugin, event)["reply_handle"] == "my-dingtalk:GroupMessage:group-1"
    # unique_session points AstrBot's own session at the sender.
    event = _Event(module, private=False, platform="dingtalk")
    event.unified_msg_origin = "my-dingtalk:GroupMessage:user-1"
    assert _capture_event(plugin, event)["reply_handle"] == "my-dingtalk:GroupMessage:group-1"
    # A Discord DM's session is the DM channel, not the user.
    plugin = _plugin_instance(module, dict(_DM_CONFIG))
    event = _Event(module, private=True, platform="discord")
    event.unified_msg_origin = "my-discord:FriendMessage:dm-channel-5"
    sent = _capture_event(plugin, event)
    assert sent["reply_handle"] == "my-discord:FriendMessage:dm-channel-5"
    assert sent["conversation_id"] == "user-1"


def test_outbox_is_claimed_only_where_the_platform_can_speak_first():
    module = _import_plugin()

    async def check():
        results = {}
        for platform in ("aiocqhttp", "telegram", "qq_official", "qq_official_webhook",
                         "weixin_official_account", "wecom_ai_bot", "mystery"):
            plugin = _plugin_instance(module, dict(_DM_CONFIG))
            plugin._outbox_task = asyncio.get_running_loop().create_future()  # a live loop
            captured = {}

            async def capture(neutral_event, captured=captured):
                captured.update(neutral_event)
                return False, False, []

            plugin._post_to_agent = capture
            async for _ in plugin.forward_to_agent(_Event(module, private=True, platform=platform)):
                pass
            results[platform] = "outbox" in captured["caps"]
        return results

    assert asyncio.run(check()) == {
        "aiocqhttp": True, "telegram": True, "qq_official": False,
        "qq_official_webhook": False, "weixin_official_account": False,
        "wecom_ai_bot": False, "mystery": False}
    plugin = _plugin_instance(module, dict(_DM_CONFIG))  # no loop running
    assert "outbox" not in _capture_event(plugin, _Event(module, private=True))["caps"]


def _delivery(**fields):
    base = {"delivery_id": "d_1", "reply_handle": "my-telegram:GroupMessage:group-1",
            "platform": "telegram", "message_type": "group", "conversation_id": "group-1",
            "reason": "proactive", "expires_in_s": 300,
            "items": [{"type": "text", "text": "anyone up?"}, {"type": "text", "text": "hello?"}]}
    base.update(fields)
    return base


def _outbox_rig(monkeypatch, module, *insts, config=None, minted=(_delivery(),),
                **context_kwargs):
    """A plugin with a context, pauses recorded, and the reply handles of
    `minted` taken as if their conversations had written."""
    context = _Context(*insts, **context_kwargs)
    plugin = _plugin_instance(module, config or {"group_whitelist": ["group-1"]}, context)
    for d in minted:
        plugin._handles.mint(d["reply_handle"], d["platform"], d["message_type"],
                             d["conversation_id"])
    pauses = []

    async def pause(seconds):
        pauses.append(seconds)

    monkeypatch.setattr(module.asyncio, "sleep", pause)
    return plugin, context, pauses


def test_a_delivery_goes_out_through_the_reply_handle_in_order(monkeypatch):
    module = _import_plugin()
    plugin, context, pauses = _outbox_rig(monkeypatch, module, _Inst("telegram"))
    assert asyncio.run(plugin._deliver(_delivery())) == ("sent", 2)
    assert [(s, [c.text for c in chain]) for s, chain in context.sent] == [
        ("my-telegram:GroupMessage:group-1", ["anyone up?"]),
        ("my-telegram:GroupMessage:group-1", ["hello?"]),
    ]
    assert len(pauses) == 1 and 0.8 <= pauses[0] <= 1.8


def test_a_delivery_the_lists_no_longer_allow_is_refused(monkeypatch):
    module = _import_plugin()
    for config in ({"group_whitelist": []},
                   {"group_whitelist": ["group-1"], "excluded_platforms": ["telegram"]}):
        plugin, context, _ = _outbox_rig(monkeypatch, module, _Inst("telegram"), config=config)
        assert asyncio.run(plugin._deliver(_delivery())) == ("refused", 0)
        assert context.sent == []
    plugin, context, _ = _outbox_rig(monkeypatch, module, _Inst("telegram"))
    assert asyncio.run(plugin._deliver(_delivery(platform="discord"))) == ("refused", 0)


def _delivery_for(sent, **fields):
    """The delivery the agent hands back for a forwarded event's conversation."""
    private = sent["message_type"] == "private"
    return _delivery(reply_handle=sent["reply_handle"], platform=sent["platform"],
                     message_type=sent["message_type"],
                     conversation_id=sent["user_id" if private else "conversation_id"],
                     **fields)


def test_a_delivery_goes_only_where_the_plugin_took_its_handle_from(monkeypatch):
    """The agent keeps reply_handle as any admitted event spelled it, and a
    local process can post an event without GATEWAY_TOKEN. The allowlists
    name the conversation, but the send goes to the handle."""
    module = _import_plugin()
    config = dict(_DM_CONFIG, group_whitelist=["group-1"])
    plugin, context, _ = _outbox_rig(monkeypatch, module, _Inst("aiocqhttp"),
                                     config=config, minted=())
    plugin._outbox_running = lambda: True
    group = _capture_event(plugin, _Event(module, private=False, platform="aiocqhttp"))
    dm = _capture_event(plugin, _Event(module, private=True, platform="aiocqhttp"))
    # A group message the adapter gave no group id reads as a DM, but its
    # session is still the group's.
    groupless = _Event(module, private=False, platform="aiocqhttp")
    groupless.get_group_id = lambda: ""
    groupless.message_obj.session_id = "group-2"
    groupless = _capture_event(plugin, groupless)
    assert groupless["message_type"] == "private"
    forged = [("my-aiocqhttp:GroupMessage:99999", "group", "group-1"),
              ("my-aiocqhttp:GroupMessage:88888", "private", "user-1"),
              ("my-aiocqhttp:FriendMessage:77777", "private", "user-1"),
              (group["reply_handle"], "private", "user-1"),
              (dm["reply_handle"], "group", "group-1"),
              (groupless["reply_handle"], "private", "user-1")]
    for handle, kind, conversation in forged:
        delivery = _delivery(reply_handle=handle, platform="aiocqhttp",
                             message_type=kind, conversation_id=conversation)
        assert asyncio.run(plugin._deliver(delivery)) == ("refused", 0), (handle, kind)
    assert context.sent == []
    for sent in (group, dm):
        assert asyncio.run(plugin._deliver(_delivery_for(sent))) == ("sent", 2)
    assert [s for s, _ in context.sent] == [group["reply_handle"]] * 2 + [dm["reply_handle"]] * 2


def test_every_platform_that_speaks_first_still_reaches_its_conversations(monkeypatch):
    """Groups, DMs and a group whose session unique_session pointed at one
    member, on every adapter the plugin sends unprompted on, and after a
    reload."""
    module = _import_plugin()
    platforms = sys.modules[_PACKAGE + ".platforms"]
    for name in [p for p, rules in platforms.RULES.items() if rules.outbox]:
        inst = _Inst(name, agent_id="1") if name == "wecom" else _Inst(name)
        plugin, context, _ = _outbox_rig(monkeypatch, module, inst, minted=(),
                                         config=dict(_DM_CONFIG, group_whitelist=["group-1"]))
        plugin._outbox_running = lambda: True
        isolated = _Event(module, private=False, platform=name)
        isolated.unified_msg_origin = f"my-{name}:GroupMessage:user-1"
        events = [_Event(module, private=True, platform=name),
                  _Event(module, private=False, platform=name), isolated]
        for event in events:
            sent = _capture_event(plugin, event)
            assert "outbox" in sent["caps"], name
            context.sent.clear()
            assert asyncio.run(plugin._deliver(_delivery_for(sent))) == ("sent", 2), (
                name, sent["reply_handle"])
            assert {s for s, _ in context.sent} == {sent["reply_handle"]}
        reloaded = _plugin_instance(module, plugin.config, context)
        assert asyncio.run(reloaded._deliver(_delivery_for(sent))) == ("sent", 2), name


def test_platforms_that_cannot_speak_first_answer_unsupported(monkeypatch):
    module = _import_plugin()
    for inst in (_Inst("qq_official"), _Inst("wecom_ai_bot"), _Inst("weixin_official_account"),
                 _Inst("wecom", agent_id="1", client=types.SimpleNamespace(kf_message=object()))):
        name = inst.meta().name
        delivery = _delivery(reply_handle=f"my-{name}:GroupMessage:group-1", platform=name)
        plugin, context, _ = _outbox_rig(monkeypatch, module, inst, minted=(delivery,))
        assert asyncio.run(plugin._deliver(delivery)) == ("unsupported", 0), name
        assert context.sent == []
    # A WeCom app that has not heard from anyone since AstrBot started drops
    # the send and still reports success.
    delivery = _delivery(reply_handle="my-wecom:GroupMessage:group-1", platform="wecom")
    plugin, context, _ = _outbox_rig(
        monkeypatch, module, _Inst("wecom", agent_id=None, client=types.SimpleNamespace()),
        minted=(delivery,))
    assert asyncio.run(plugin._deliver(delivery)) == ("failed", 0)


def test_a_send_that_breaks_midway_is_partial_and_a_refused_one_failed(monkeypatch):
    module = _import_plugin()
    plugin, context, _ = _outbox_rig(monkeypatch, module, _Inst("telegram"), fail_at=1)
    assert asyncio.run(plugin._deliver(_delivery())) == ("partial", 1)
    plugin, context, _ = _outbox_rig(monkeypatch, module, _Inst("telegram"), refuse=True)
    assert asyncio.run(plugin._deliver(_delivery())) == ("failed", 0)


def test_a_platform_still_starting_is_waited_for_then_failed(monkeypatch):
    """AstrBot loads plugins before platforms, so a delivery can arrive
    before its adapter is running."""
    module = _import_plugin()
    for starts_after, expected in ((3, ("sent", 1)), (None, ("failed", 0))):
        plugin, context, pauses = _outbox_rig(monkeypatch, module)

        async def tick(seconds, pauses=pauses, context=context, starts_after=starts_after):
            pauses.append(seconds)
            if len(pauses) == starts_after:
                context.insts["my-telegram"] = _Inst("telegram")

        monkeypatch.setattr(module.asyncio, "sleep", tick)
        delivery = _delivery(items=[{"type": "text", "text": "hi"}])
        assert asyncio.run(plugin._deliver(delivery)) == expected
        assert len(pauses) == (starts_after or module._PLATFORM_WAIT_S)
    # Once AstrBot is up, a platform that is missing is not coming.
    plugin, context, pauses = _outbox_rig(monkeypatch, module)
    plugin._starting_until = module.time.monotonic() - 1
    assert asyncio.run(plugin._deliver(_delivery())) == ("failed", 0)
    assert pauses == []


async def test_the_outbox_loop_pulls_delivers_acks_and_stops(monkeypatch):
    """initialize starts one poller; it signs its pulls like events, sends
    each delivery once through context.send_message, acks it on the next
    pull, and terminate leaves nothing running."""
    module = _import_plugin()
    pulls = []

    def agent(request):
        body = json.loads(request.content)
        pulls.append((request.url.path, body, request.headers.get("X-Gateway-Signature")))
        if len(pulls) == 1:
            return httpx.Response(200, json={"deliveries": [_delivery(), _delivery()],
                                             "next_wait_s": 1})
        return httpx.Response(200, json={"deliveries": [], "next_wait_s": 1})

    real_client = httpx.AsyncClient
    monkeypatch.setattr(module.sdk.httpx, "AsyncClient",
                        lambda *a, **k: real_client(transport=httpx.MockTransport(agent)))
    context = _Context(_Inst("telegram"))
    plugin = module.LLMPersonaGateway(context, {
        "group_whitelist": ["group-1"], "gateway_token": "t",
        "agent_url": "https://agent.example/webhook/gateway"})
    plugin._handles.mint("my-telegram:GroupMessage:group-1", "telegram", "group", "group-1")
    real_sleep = asyncio.sleep
    monkeypatch.setattr(module.random, "uniform", lambda a, b: 0)
    await plugin.initialize()
    first_task = plugin._outbox_task
    await plugin.initialize()
    assert plugin._outbox_task is first_task, "one poller per instance"
    for _ in range(200):
        if len(pulls) >= 2:
            break
        await real_sleep(0.01)
    await plugin.terminate()
    assert first_task.done() and plugin._outbox_task is None
    await plugin.terminate()  # twice is harmless

    assert pulls[0][0] == "/webhook/gateway/outbox" and pulls[0][2].startswith("sha256=")
    assert pulls[0][1]["kind"] == "outbox.pull"
    assert pulls[0][1]["forwarder_id"] == plugin._forwarder_id
    assert [c.text for _s, chain in context.sent for c in chain] == ["anyone up?", "hello?"], \
        "the repeated delivery id went out once"
    assert pulls[1][1]["acks"] == [{"delivery_id": "d_1", "status": "sent", "sent_items": 2}]


async def test_the_outbox_stays_off_when_disabled_or_unsafe():
    module = _import_plugin()
    off = module.LLMPersonaGateway(_Context(), {"outbox_enabled": False})
    await off.initialize()
    assert off._outbox_task is None
    unsafe = module.LLMPersonaGateway(_Context(), {"agent_url": "http://agent.example/webhook/gateway",
                                                   "gateway_token": "t"})
    await unsafe.initialize()
    await asyncio.wait_for(unsafe._outbox_task, 1)
    assert not unsafe._outbox_running()
    await unsafe.terminate()


# ---------------------------------------------------------------------------
# platforms.py: the pure rules
# ---------------------------------------------------------------------------

def test_split_text_prefers_boundaries_and_never_loses_text():
    module = _import_plugin()
    platforms = sys.modules[_PACKAGE + ".platforms"]
    text = "First paragraph here.\n\nSecond one is a bit longer. It has two sentences."
    parts = platforms.split_text(text, 40)
    assert parts == ["First paragraph here.", "Second one is a bit longer.",
                     "It has two sentences."], parts
    assert platforms.split_text("x" * 95, 40) == ["x" * 40, "x" * 40, "x" * 15]
    assert platforms.split_text("", 40) == [] and platforms.split_text("ok", 0) == ["ok"]
    assert module.rules_for("nope") is platforms.DEFAULT_RULES

