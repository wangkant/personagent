"""Focused contract tests for the bundled AstrBot forwarder plugin."""
from __future__ import annotations

import asyncio
import enum
import hashlib
import hmac
import importlib.util
import logging
import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PLUGIN = (
    ROOT
    / "integrations"
    / "astrbot"
    / "astrbot_plugin_llm_persona_gateway"
    / "main.py"
)


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

    Filter.EventMessageType = EventMessageType
    event_mod.AstrMessageEvent = object
    event_mod.filter = Filter

    platform_mod = register("astrbot.api.platform")

    class MessageType(enum.Enum):
        GROUP_MESSAGE = "group"
        FRIEND_MESSAGE = "friend"
        OTHER_MESSAGE = "other"

    platform_mod.MessageType = MessageType

    star_mod = register("astrbot.api.star")

    class Star:
        def __init__(self, _context=None):
            pass

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

    class Image(Segment):
        @classmethod
        def fromBase64(cls, value):
            return cls(b64=value)

    class Face(Segment):
        pass

    class Reply(Segment):
        pass

    components.Plain = Plain
    components.At = At
    components.Image = Image
    components.Face = Face
    components.Reply = Reply

    spec = importlib.util.spec_from_file_location("astrbot_gateway_tested", PLUGIN)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
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
    def __init__(self, module, *, private: bool):
        message_type = (
            module.MessageType.FRIEND_MESSAGE
            if private
            else module.MessageType.GROUP_MESSAGE
        )
        self.message_obj = types.SimpleNamespace(
            type=message_type, message=[], message_id="incoming-1",
            timestamp=1_725_000_000,
        )
        self.message_str = "hello"
        self._private = private
        self.stopped = False

    def get_platform_name(self):
        return "telegram"

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


def _plugin_instance(module, config):
    plugin = module.LLMPersonaGateway(None, config)
    plugin._client = _RecordingClient()
    return plugin


def test_reply_component_preserves_quoted_message_id():
    module = _import_plugin()
    event = types.SimpleNamespace(
        message_obj=types.SimpleNamespace(
            message=[module.Comp.Reply(id="quoted-42", sender_id="bot")]
        )
    )

    segments, is_at_me = module.LLMPersonaGateway._map_segments(
        object(), event, "bot"
    )

    assert segments == [{"type": "reply", "message_id": "quoted-42"}]
    assert is_at_me is True


def test_default_configuration_forwards_neither_groups_nor_private_messages():
    module = _import_plugin()
    plugin = _plugin_instance(module, {})

    async def collect(event):
        return [item async for item in plugin.forward_to_agent(event)]

    assert asyncio.run(collect(_Event(module, private=False))) == []
    assert asyncio.run(collect(_Event(module, private=True))) == []
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
    real_token_hex = module.secrets.token_hex
    module.time.time = lambda: 1_725_000_000
    module.secrets.token_hex = lambda _n: "00112233445566778899aabbccddeeff"
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
        module.secrets.token_hex = real_token_hex

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


def test_forwarding_failure_does_not_stop_astrbot_fallback():
    module = _import_plugin()
    plugin = _plugin_instance(
        module,
        {
            "private_enabled": True,
            "private_whitelist": ["user-1"],
            "block_default": True,
        },
    )
    event = _Event(module, private=True)

    async def fail(_neutral_event):
        return False, False, []

    plugin._post_to_agent = fail

    async def collect():
        return [item async for item in plugin.forward_to_agent(event)]

    assert asyncio.run(collect()) == []
    assert event.stopped is False


def test_unhandled_gateway_response_does_not_stop_astrbot_fallback():
    module = _import_plugin()
    plugin = _plugin_instance(
        module,
        {
            "private_enabled": True,
            "private_whitelist": ["user-1"],
            "block_default": True,
        },
    )
    plugin._client = _UnhandledClient()
    event = _Event(module, private=True)

    async def collect():
        return [item async for item in plugin.forward_to_agent(event)]

    assert asyncio.run(collect()) == []
    assert event.stopped is False


def test_a_silent_but_owned_conversation_blocks_the_fallback():
    """The agent is quiet far more often than it speaks — a PASS, a debounce
    merge, the rhythm gate. Treating that as "not mine" hands the room to
    AstrBot's own model, which answers in it as someone else. The test above
    pins the other direction: an agent too old to send `owned` still falls
    back to `handled`, so nothing changes for it."""
    module = _import_plugin()
    plugin = _plugin_instance(
        module,
        {
            "private_enabled": True,
            "private_whitelist": ["user-1"],
            "block_default": True,
        },
    )
    plugin._client = _SilentButOwnedClient()
    event = _Event(module, private=True)

    async def collect():
        return [item async for item in plugin.forward_to_agent(event)]

    assert asyncio.run(collect()) == []
    assert event.stopped is True


def test_forwarded_event_carries_source_timestamp_and_success_blocks_fallback():
    module = _import_plugin()
    plugin = _plugin_instance(
        module,
        {
            "private_enabled": True,
            "private_whitelist": ["user-1"],
            "block_default": True,
        },
    )
    event = _Event(module, private=True)
    captured = {}

    async def succeed(neutral_event):
        captured.update(neutral_event)
        return True, True, []

    plugin._post_to_agent = succeed

    async def collect():
        return [item async for item in plugin.forward_to_agent(event)]

    assert asyncio.run(collect()) == []
    assert captured["source_timestamp"] == 1_725_000_000
    assert event.stopped is True


def test_missing_source_timestamp_is_not_forwarded_or_blocked():
    module = _import_plugin()
    plugin = _plugin_instance(
        module,
        {
            "private_enabled": True,
            "private_whitelist": ["user-1"],
            "block_default": True,
        },
    )
    event = _Event(module, private=True)
    event.message_obj.timestamp = None

    async def collect():
        return [item async for item in plugin.forward_to_agent(event)]

    assert asyncio.run(collect()) == []
    assert plugin._client.calls == []
    assert event.stopped is False


if __name__ == "__main__":
    tests = [
        test_reply_component_preserves_quoted_message_id,
        test_default_configuration_forwards_neither_groups_nor_private_messages,
        test_signed_request_uses_canonical_body_and_replay_headers,
        test_off_host_endpoint_requires_https_and_a_token,
        test_malformed_endpoint_is_rejected_without_a_request,
        test_forwarding_failure_does_not_stop_astrbot_fallback,
        test_unhandled_gateway_response_does_not_stop_astrbot_fallback,
        test_a_silent_but_owned_conversation_blocks_the_fallback,
        test_forwarded_event_carries_source_timestamp_and_success_blocks_fallback,
        test_missing_source_timestamp_is_not_forwarded_or_blocked,
    ]
    for test in tests:
        test()
    print(f"ok: {len(tests)} AstrBot plugin tests")
