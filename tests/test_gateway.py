"""Tests for the platform-neutral gateway layer (gateway.py + agent hooks).

Run from the repo root with no test framework required:

    python tests/test_gateway.py
"""
from __future__ import annotations

import asyncio
import base64
import sys
import tempfile
from pathlib import Path

# Make the repo root importable when invoked as `python tests/test_gateway.py`.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gateway import GatewaySink, message_to_reply_item, synthesize_onebot_payload  # noqa: E402
from agent import Agent  # noqa: E402

BOT_QQ = "10001"

_failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {name}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        _failures.append(name)


# ---------------------------------------------------------------------------
# Unit: synthesize_onebot_payload
# ---------------------------------------------------------------------------

def test_synthesize_group_self_mention() -> None:
    event = {
        "platform": "telegram",
        "message_type": "group",
        "conversation_id": "-100777",
        "user_id": "42",
        "sender_name": "Alice",
        "self_id": "999000",
        "message_id": 555,
        "is_at_me": True,
        "segments": [
            {"type": "mention", "user_id": "999000", "name": "TestBot"},
            {"type": "text", "text": " hello there"},
        ],
        "raw_text": "@TestBot hello there",
    }
    p = synthesize_onebot_payload(event, BOT_QQ)
    check("group: post_type", p["post_type"] == "message", repr(p))
    check("group: message_type", p["message_type"] == "group", repr(p))
    check("group: user_id prefixed", p["user_id"] == "telegram:42", repr(p["user_id"]))
    check("group: group_id prefixed", p["group_id"] == "telegram:-100777", repr(p["group_id"]))
    check("group: message_id namespaced by conversation",
          p["message_id"] == "telegram:-100777:555", repr(p["message_id"]))
    check("group: sender fields", p["sender"] == {
        "user_id": "telegram:42", "nickname": "Alice", "card": "Alice",
    }, repr(p["sender"]))
    check("group: gateway flags", p["_gateway"] is True and p["_platform"] == "telegram")
    check("group: self mention -> bot_qq",
          p["message"][0] == {"type": "at", "data": {"qq": BOT_QQ}}, repr(p["message"]))
    check("group: text segment kept",
          p["message"][1] == {"type": "text", "data": {"text": " hello there"}}, repr(p["message"]))
    # A real self-mention segment exists, so is_at_me must NOT add a second at.
    at_count = sum(1 for s in p["message"] if s["type"] == "at")
    check("group: no duplicate at prepend", at_count == 1, repr(p["message"]))


def test_synthesize_mention_other_user() -> None:
    event = {
        "platform": "discord",
        "message_type": "group",
        "conversation_id": "c1",
        "user_id": "u1",
        "sender_name": "Bob",
        "self_id": "botid",
        "message_id": None,
        "is_at_me": False,
        "segments": [{"type": "mention", "user_id": "77", "name": "Carl"}],
        "raw_text": "@Carl",
    }
    p = synthesize_onebot_payload(event, BOT_QQ)
    check("other mention: prefixed qq",
          p["message"][0] == {"type": "at", "data": {"qq": "discord:77"}}, repr(p["message"]))
    check("other mention: no message_id key", "message_id" not in p, repr(p.keys()))


def test_synthesize_is_at_me_prepend() -> None:
    event = {
        "platform": "telegram",
        "message_type": "group",
        "conversation_id": "g1",
        "user_id": "42",
        "sender_name": "Alice",
        "self_id": "999000",
        "message_id": "m1",
        "is_at_me": True,  # e.g. a reply-to-bot with no mention segment
        "segments": [{"type": "text", "text": "ping"}],
        "raw_text": "ping",
    }
    p = synthesize_onebot_payload(event, BOT_QQ)
    check("is_at_me: synthetic at prepended",
          p["message"][0] == {"type": "at", "data": {"qq": BOT_QQ}}, repr(p["message"]))
    check("is_at_me: text follows",
          p["message"][1] == {"type": "text", "data": {"text": "ping"}}, repr(p["message"]))


def test_synthesize_private() -> None:
    event = {
        "platform": "telegram",
        "message_type": "private",
        "conversation_id": "42",
        "user_id": "42",
        "sender_name": "Alice",
        "self_id": "999000",
        "message_id": 9,
        "is_at_me": False,
        "segments": [{"type": "text", "text": "hi"}, {"type": "emoji", "name": "wave"},
                     {"type": "reply"}],
        "raw_text": "hi",
    }
    p = synthesize_onebot_payload(event, BOT_QQ)
    check("private: message_type", p["message_type"] == "private", repr(p))
    check("private: no group_id", "group_id" not in p, repr(p.keys()))
    check("private: user_id prefixed", p["user_id"] == "telegram:42", repr(p["user_id"]))
    types = [s["type"] for s in p["message"]]
    check("private: emoji->face, reply->reply", types == ["text", "face", "reply"], repr(types))


def test_synthesize_mid_namespacing() -> None:
    """Dedupe keys must be namespaced per conversation: Telegram/Slack issue
    message ids per chat, so a bare "<platform>:<mid>" key would collide
    across chats and silently swallow the second message."""
    base = {
        "platform": "telegram",
        "user_id": "42",
        "sender_name": "Alice",
        "self_id": "999000",
        "message_id": 700,
        "is_at_me": False,
        "segments": [{"type": "text", "text": "x"}],
        "raw_text": "x",
    }
    g1 = synthesize_onebot_payload(
        dict(base, message_type="group", conversation_id="-100111"), BOT_QQ)
    g2 = synthesize_onebot_payload(
        dict(base, message_type="group", conversation_id="-100222"), BOT_QQ)
    check("mid namespace: distinct conversations get distinct keys",
          g1["message_id"] == "telegram:-100111:700"
          and g2["message_id"] == "telegram:-100222:700",
          f"{g1['message_id']!r} vs {g2['message_id']!r}")
    pv = synthesize_onebot_payload(dict(base, message_type="private"), BOT_QQ)
    check("mid namespace: private uses user_id as the conversation",
          pv["message_id"] == "telegram:42:700", repr(pv["message_id"]))


def test_synthesize_image_segments() -> None:
    event = {
        "platform": "slack",
        "message_type": "group",
        "conversation_id": "c",
        "user_id": "u",
        "sender_name": "D",
        "self_id": "s",
        "message_id": 1,
        "is_at_me": False,
        "segments": [
            {"type": "image", "url": "https://example.com/a.png"},
            {"type": "image", "b64": "QUJD"},
        ],
        "raw_text": "",
    }
    p = synthesize_onebot_payload(event, BOT_QQ)
    check("image: url form",
          p["message"][0] == {"type": "image", "data": {"url": "https://example.com/a.png"}},
          repr(p["message"]))
    check("image: b64-only form",
          p["message"][1] == {"type": "image", "data": {"file": "base64://QUJD"}},
          repr(p["message"]))


# ---------------------------------------------------------------------------
# Unit: message_to_reply_item / GatewaySink
# ---------------------------------------------------------------------------

def test_message_to_reply_item() -> None:
    item = message_to_reply_item("plain chunk")
    check("reply item: str", item == {"type": "text", "text": "plain chunk"}, repr(item))

    item = message_to_reply_item([
        {"type": "at", "data": {"qq": "telegram:42"}},
        {"type": "text", "data": {"text": "sup"}},
    ])
    check("reply item: at+text",
          item == {"type": "text", "text": "sup", "at_user_id": "telegram:42"}, repr(item))

    item = message_to_reply_item([
        {"type": "at", "data": {"qq": "telegram:42"}},
        {"type": "image", "data": {"file": "base64://QUJD"}},
    ])
    check("reply item: at+image",
          item == {"type": "image", "b64": "QUJD", "at_user_id": "telegram:42"}, repr(item))


def test_sink_closed_drop() -> None:
    sink = GatewaySink()
    sink.add("kept")
    sink.closed = True
    sink.add("dropped after close")
    check("sink: closed drops late adds",
          sink.items == [{"type": "text", "text": "kept"}], repr(sink.items))


def test_validator_accepts_prefixed_at_marker() -> None:
    ok, reason = Agent._validate_reply_safe("[AT:telegram:42] sup", lang="en")
    check("validator: prefixed AT marker passes", ok, reason)
    ok, reason = Agent._validate_reply_safe("[AT:telegram:42]", lang="en")
    check("validator: marker-only reply passes", ok, reason)


# ---------------------------------------------------------------------------
# Unit: AstrBot forwarder plugin helpers (imported with stubbed astrbot)
# ---------------------------------------------------------------------------

def _import_plugin_module():
    """Import the AstrBot forwarder plugin with stubbed astrbot modules so
    its pure helpers can be tested without an AstrBot install."""
    import enum
    import importlib.util
    import logging
    import types

    if "astrbot" not in sys.modules:
        def _register(name: str) -> types.ModuleType:
            m = types.ModuleType(name)
            sys.modules[name] = m
            return m

        astrbot_pkg = _register("astrbot")
        api = _register("astrbot.api")
        astrbot_pkg.api = api
        api.AstrBotConfig = dict
        api.logger = logging.getLogger("plugin-test")

        event_mod = _register("astrbot.api.event")

        class _EventMessageType(enum.Flag):
            GROUP_MESSAGE = enum.auto()
            PRIVATE_MESSAGE = enum.auto()
            OTHER_MESSAGE = enum.auto()
            ALL = GROUP_MESSAGE | PRIVATE_MESSAGE | OTHER_MESSAGE

        class _Filter:
            EventMessageType = _EventMessageType

            @staticmethod
            def event_message_type(_t):
                def deco(fn):
                    return fn
                return deco

        event_mod.AstrMessageEvent = object
        event_mod.filter = _Filter
        api.event = event_mod

        star_mod = _register("astrbot.api.star")
        star_mod.Context = object
        star_mod.Star = object
        api.star = star_mod

        platform_mod = _register("astrbot.api.platform")

        class _MessageType(enum.Enum):
            GROUP_MESSAGE = "GroupMessage"
            FRIEND_MESSAGE = "FriendMessage"
            OTHER_MESSAGE = "OtherMessage"

        platform_mod.MessageType = _MessageType
        api.platform = platform_mod

        comp_mod = _register("astrbot.api.message_components")

        class _Seg:
            def __init__(self, *args, **kwargs):
                self.__dict__.update(kwargs)

        for seg_name in ("Plain", "At", "Image", "Face", "Reply"):
            setattr(comp_mod, seg_name, type(seg_name, (_Seg,), {}))
        comp_mod.Image.fromBase64 = staticmethod(lambda b64: b64)
        api.message_components = comp_mod

    plugin_path = (Path(__file__).resolve().parents[1] / "integrations" / "astrbot"
                   / "astrbot_plugin_llm_persona_gateway" / "main.py")
    spec = importlib.util.spec_from_file_location(
        "llm_persona_gateway_plugin", str(plugin_path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_plugin_reply_id_strip() -> None:
    """The plugin's quote-id strip must match the conversation-namespaced
    inbound id format ("<platform>:<conversation>:<raw mid>")."""
    cls = _import_plugin_module().LLMPersonaGateway
    check("plugin strip: same-conversation id recovered",
          cls._resolve_reply_id("telegram:-100777:555", "telegram", "-100777") == "555")
    check("plugin strip: other-conversation id dropped",
          cls._resolve_reply_id("telegram:-100999:555", "telegram", "-100777") is None)
    check("plugin strip: legacy two-part id dropped",
          cls._resolve_reply_id("telegram:555", "telegram", "-100777") is None)
    check("plugin strip: other-platform id dropped",
          cls._resolve_reply_id("slack:C42:555", "telegram", "-100777") is None)
    check("plugin strip: empty id dropped",
          cls._resolve_reply_id("", "telegram", "-100777") is None)
    check("tg artifact: '/ ' prefix removed",
          cls._strip_tg_wake_artifact("/ hello there", "MyBot") == "hello there")
    check("tg artifact: '/@bot ' prefix removed case-insensitively",
          cls._strip_tg_wake_artifact("/@mybot hello", "MyBot") == "hello")
    check("tg artifact: ordinary text untouched",
          cls._strip_tg_wake_artifact("hello / world", "MyBot") == "hello / world")


# ---------------------------------------------------------------------------
# Integration: real Agent + handle_gateway round-trip
# ---------------------------------------------------------------------------

def make_agent(tmp: Path) -> Agent:
    """Lightest viable Agent: real ctor, no network config, all writable
    state files redirected into a temp directory."""
    a = Agent(
        api_key="test-key",  # non-empty so the agent is enabled
        bot_qq=BOT_QQ,
        bot_name="TestBot",
        napcat_api="http://127.0.0.1:9",  # closed port; never reached when the sink is set
        memory_file=str(tmp / "memory.json"),
        persona="test persona",
        eval_enable=False,
        eval_file=str(tmp / "eval.jsonl"),
        stickers_dir=str(tmp / "stickers"),
        stickers_file=str(tmp / "stickers.json"),
        message_debounce_sec=0,
        lang="en",
        gateway_owner_ids=("telegram:1",),
    )
    # Keep runtime state files out of the repo during tests.
    a._seen_msg_file = tmp / "seen_msg_ids.json"
    a.core_memory_file = tmp / "core_memory.json"
    # Skip the typing-simulation sleeps so the round-trip is instant.
    a._typing_delay = lambda chunk: 0.0
    return a


async def integration_round_trip(tmp: Path) -> None:
    agent = make_agent(tmp)

    async def fake_think(group_id, mode, text="", caller_override=None):
        return "[AT:telegram:42] hold up, omw", "called", ""

    agent._think = fake_think

    event = {
        "platform": "telegram",
        "message_type": "group",
        "conversation_id": "-100777",
        "user_id": "42",
        "sender_name": "Alice",
        "self_id": "999000",
        "message_id": 555,
        "is_at_me": True,
        "segments": [
            {"type": "mention", "user_id": "999000", "name": "TestBot"},
            {"type": "text", "text": " are you there today"},
        ],
        "raw_text": "@TestBot are you there today",
    }
    result = await agent.handle_gateway(event)
    check("integration: handled", result["handled"] is True, repr(result))
    texts = [r for r in result["replies"] if r.get("type") == "text"]
    check("integration: got a text reply", len(texts) >= 1, repr(result))
    if texts:
        first = texts[0]
        check("integration: at_user_id extracted",
              first.get("at_user_id") == "telegram:42", repr(first))
        check("integration: marker stripped from text",
              "[AT:" not in first.get("text", "") and "hold up" in first.get("text", ""),
              repr(first))

    # Same message_id again must dedupe (ring shared with the QQ path).
    result2 = await agent.handle_gateway(event)
    check("integration: duplicate message_id deduped",
          result2["handled"] is False and result2["replies"] == [], repr(result2))


async def integration_second_marker_stripped(tmp: Path) -> None:
    """A second, hallucinated [AT:] marker must be stripped from the outgoing
    text instead of leaking literally: the validator removes markers before
    whitelisting, so nothing downstream would catch the leftover."""
    agent = make_agent(tmp)

    async def fake_think(group_id, mode, text="", caller_override=None):
        return "[AT:telegram:42] hold up [AT:Bob] omw", "called", ""

    agent._think = fake_think
    event = {
        "platform": "telegram",
        "message_type": "group",
        "conversation_id": "-100777",
        "user_id": "42",
        "sender_name": "Alice",
        "self_id": "999000",
        "message_id": 556,
        "is_at_me": True,
        "segments": [
            {"type": "mention", "user_id": "999000", "name": "TestBot"},
            {"type": "text", "text": " you coming"},
        ],
        "raw_text": "@TestBot you coming",
    }
    result = await agent.handle_gateway(event)
    joined = " ".join(r.get("text", "") for r in result["replies"]
                      if r.get("type") == "text")
    check("second marker: stripped from outgoing text",
          "[AT:" not in joined and "omw" in joined, repr(result))


async def unit_b64_image_fetch(tmp: Path) -> None:
    """base64:// pseudo-URLs (b64-only gateway inbound images) decode to
    bytes locally instead of being routed through httpx."""
    agent = make_agent(tmp)
    raw = b"\x89PNG\r\n\x1a\nxx"
    data = await agent._fetch_image_bytes("base64://" + base64.b64encode(raw).decode())
    check("b64 fetch: decodes inline data", data == raw, repr(data))
    bad = await agent._fetch_image_bytes("base64://QQ")  # bad padding
    check("b64 fetch: invalid data returns None", bad is None, repr(bad))


async def integration_same_mid_distinct_conversations(tmp: Path) -> None:
    """F6 regression: per-chat message counters (Telegram/Slack) produce the
    same raw mid in different chats; both messages must be handled instead of
    the second being swallowed by the dedupe ring."""
    agent = make_agent(tmp)

    async def fake_think(group_id, mode, text="", caller_override=None):
        return "on it", "called", ""

    agent._think = fake_think

    def event_for(conv: str) -> dict:
        return {
            "platform": "telegram",
            "message_type": "group",
            "conversation_id": conv,
            "user_id": "42",
            "sender_name": "Alice",
            "self_id": "999000",
            "message_id": 700,  # same raw mid in both chats
            "is_at_me": True,
            "segments": [
                {"type": "mention", "user_id": "999000", "name": "TestBot"},
                {"type": "text", "text": " hello"},
            ],
            "raw_text": "@TestBot hello",
        }

    r1 = await agent.handle_gateway(event_for("-100111"))
    r2 = await agent.handle_gateway(event_for("-100222"))
    check("same mid: chat A handled", r1["handled"] is True, repr(r1))
    check("same mid: chat B handled (no cross-chat dedupe)",
          r2["handled"] is True, repr(r2))


async def regression_forged_gateway_flag_rejected(tmp: Path) -> None:
    """F3 regression: a forged "_gateway": true in a /webhook/qq-style
    payload (no sink set) must not bypass the private-chat whitelist, while
    the same DM through handle_gateway (sink set) must still pass."""
    agent = make_agent(tmp)
    agent.private_allowed_qqs = set()
    reached: list[str] = []

    async def fake_private(user_id, payload, is_owner=False):
        reached.append(user_id)
        return True

    agent._handle_private = fake_private
    forged = {
        "post_type": "message",
        "message_type": "private",
        "user_id": "telegram:999",
        "sender": {"user_id": "telegram:999", "nickname": "Mallory"},
        "raw_message": "hi",
        "message": [{"type": "text", "data": {"text": "hi"}}],
        "_gateway": True,
        "message_id": 424242,
    }
    handled = await agent.handle(forged)
    check("forged _gateway: DM whitelist still applies without sink",
          handled is False and reached == [], repr((handled, reached)))

    event = {
        "platform": "telegram",
        "message_type": "private",
        "conversation_id": "999",
        "user_id": "999",
        "sender_name": "Eve",
        "self_id": "999000",
        "message_id": 424243,
        "is_at_me": False,
        "segments": [{"type": "text", "text": "hi"}],
        "raw_text": "hi",
    }
    result = await agent.handle_gateway(event)
    check("genuine gateway DM: passes the gate via the sink",
          result["handled"] is True and reached == ["telegram:999"],
          repr((result, reached)))


async def regression_no_sink_send(tmp: Path) -> None:
    """QQ-path regression: with no sink set, a non-numeric group id must not
    raise out of _napcat_send_group — it takes the network-failure path."""
    agent = make_agent(tmp)
    ok = await agent._napcat_send_group("telegram:1", "x")
    check("regression: no-sink send returns False without raising", ok is False, repr(ok))


async def regression_numeric_at_kept_in_payload(tmp: Path) -> None:
    """The non-numeric at-target guard must not affect numeric QQ targets and
    must drop prefixed ids on the QQ path (no sink)."""
    agent = make_agent(tmp)
    sent: list = []

    async def fake_send(group_id, message):
        sent.append(message)
        return True

    agent._napcat_send_group = fake_send
    await agent._send_qq("123456", "yo", at_user_id="654321")
    check("at guard: numeric target keeps at segment",
          isinstance(sent[0], list) and sent[0][0] == {"type": "at", "data": {"qq": "654321"}},
          repr(sent))
    sent.clear()
    await agent._send_qq("123456", "yo", at_user_id="telegram:42")
    check("at guard: prefixed target dropped on QQ path",
          sent == ["yo"], repr(sent))


async def main_async() -> None:
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        await integration_round_trip(tmp / "a")
        await regression_no_sink_send(tmp / "b")
        await regression_numeric_at_kept_in_payload(tmp / "c")
        await integration_second_marker_stripped(tmp / "d")
        await unit_b64_image_fetch(tmp / "e")
        await integration_same_mid_distinct_conversations(tmp / "f")
        await regression_forged_gateway_flag_rejected(tmp / "g")


def main() -> int:
    test_synthesize_group_self_mention()
    test_synthesize_mention_other_user()
    test_synthesize_is_at_me_prepend()
    test_synthesize_private()
    test_synthesize_mid_namespacing()
    test_synthesize_image_segments()
    test_message_to_reply_item()
    test_sink_closed_drop()
    test_validator_accepts_prefixed_at_marker()
    test_plugin_reply_id_strip()
    asyncio.run(main_async())
    print()
    if _failures:
        print(f"{len(_failures)} test(s) FAILED: {', '.join(_failures)}")
        return 1
    print("all tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
