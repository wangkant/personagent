"""Platform-neutral connector layer: an event in, its replies in the same response.

The event and reply schemas are in docs/connectors.md. An event becomes a
OneBot-v11-shaped payload that the QQ pipeline consumes unchanged, and the
`current_sink` contextvar diverts the NapCat send funnels into that turn's
reply list for the one handle_event() call.

Ids are namespaced "<platform>:<raw id>" so they never collide with QQ
numbers, and message ids also carry the conversation because some platforms
issue them per chat. A CONNECTOR_QQ_PLATFORMS platform mints bare ids
instead (see `_ns`). A mention of the bot becomes QQ_BOT_ID, or
CONNECTOR_BOT_ID when that is blank.
"""
from __future__ import annotations

import contextvars
import logging
from typing import Optional

from . import channels

logger = logging.getLogger("agent.connector")

#: What a mention of the bot becomes when QQ_BOT_ID (the bot's QQ account) is
#: blank, so _is_at_me still sees it. No namespaced id or QQ number equals it.
CONNECTOR_BOT_ID = "persona-self"

#: The platform an event is filed under when it names none, or names QQ
#: without being a CONNECTOR_QQ_PLATFORMS one. Stored in ids, so keep it.
FALLBACK_PLATFORM = "gateway"

#: Inbound segment types this version understands. Anything else is dropped
#: (see synthesize_onebot_payload) — listed here so the drop can say so.
_KNOWN_SEGMENT_TYPES = frozenset({"text", "mention", "image", "emoji", "reply"})


def _ns_mid(platform: str, native: bool, conversation_id, mid) -> str:
    """Namespace a MESSAGE id.

    A non-native one carries the conversation, since Telegram and Slack issue
    ids per chat. A native one stays bare, as NapCat delivers it, or a message
    arriving through both doors would be answered twice.
    """
    return str(mid) if native else f"{platform}:{conversation_id}:{mid}"


def _ns(platform: str, native: bool, raw: object) -> str:
    """Namespace a USER or GROUP id, unless the platform is native.

    An unprefixed key is QQ and every store is keyed that way, so a QQ message
    relayed by a connector must mint exactly NapCat's ids; the ledgers
    content-address rows over `conv_id`, so a rename cannot be repaired.

    `native` comes from the operator's CONNECTOR_QQ_PLATFORMS, never from the
    connector: a bare id is compared against the QQ entries of ADMIN_IDS,
    ACCESS_GROUPS and ACCESS_DM_USERS.
    """
    return str(raw) if native else f"{platform}:{raw}"

# A ConnectorSink only inside Agent.handle_event: the NapCat send funnels
# divert into it, and every other caller sees None.
current_sink: contextvars.ContextVar[Optional["ConnectorSink"]] = contextvars.ContextVar(
    "current_sink", default=None,
)

# Per-turn, like `current_sink`. None means PERSONA_TZ_OFFSET_HOURS applies;
# an embedder may set a per-user offset for the duration of a turn.
current_tz_offset_h: contextvars.ContextVar[Optional[float]] = contextvars.ContextVar(
    "current_tz_offset_h", default=None,
)


def message_to_reply_item(
        message, *, platform: str = "", native: bool = False,
        bot_id: str = "") -> dict:
    """One NapCat-shaped message (str or v11 segments) as one neutral reply
    item; the send paths emit only text, [at?, text] or [at?, image], so the
    fold is lossless.

    `platform`/`native` restore the prefix of an outbound mention: native ids
    are stored bare, but the connector resolves "<platform>:<raw>". `bot_id`
    is never prefixed, or the connector would @ the bot itself."""
    if isinstance(message, str):
        return {"type": "text", "text": message}
    at_user_id = ""
    texts: list[str] = []
    image_b64 = ""
    for seg in message or []:
        if not isinstance(seg, dict):
            continue
        t = seg.get("type")
        d = seg.get("data") if isinstance(seg.get("data"), dict) else {}
        if t == "at":
            at_user_id = str(d.get("qq", ""))
        elif t == "text":
            texts.append(str(d.get("text", "")))
        elif t == "image":
            file_field = str(d.get("file", ""))
            if file_field.startswith("base64://"):
                image_b64 = file_field[len("base64://"):]
    if image_b64:
        item: dict = {"type": "image", "b64": image_b64}
    else:
        item = {"type": "text", "text": "".join(texts)}
    if at_user_id:
        if (native and platform and ":" not in at_user_id
                and at_user_id != str(bot_id)):
            at_user_id = f"{platform}:{at_user_id}"
        item["mention_user_id"] = at_user_id
    return item


class ConnectorSink:
    """Ordered collector for the replies produced while handling one connector
    event. Closed once handle_event returns its HTTP response; a late add
    (e.g. from a background task that inherited the context) is dropped with
    a warning instead of being silently lost in a dead response."""

    def __init__(self, platform: str = "", native: bool = False,
                 bot_id: str = "", prefiltered: bool = True) -> None:
        # For re-prefixing outbound mentions (message_to_reply_item).
        self.platform = str(platform or "")
        self.native = bool(native)
        self.bot_id = str(bot_id or "")
        # Whether the connector filtered this turn itself.
        self.prefiltered = bool(prefiltered)
        self.items: list[dict] = []
        self.closed = False
        # Set once the turn clears admission: the conversation is ours whether
        # or not we spoke, so a deliberate silence is not handed to the
        # connector's own model.
        self.owned = False

    def add(self, message) -> bool:
        if self.closed:
            logger.warning("[Connector] sink already closed; dropping late reply: %r",
                           str(message)[:120])
            return False
        self.items.append(message_to_reply_item(
            message, platform=self.platform, native=self.native,
            bot_id=self.bot_id))
        return True


#: The body `kind` of an inbound event, which may be left out. The signature
#: does not cover the URL path, so each endpoint checks the body is its own.
EVENT_KIND = "event"

#: The two conversation types an event may name.
CONVERSATION_TYPES = ("group", "dm")

#: Longest connector id and reply handle kept; a longer one is ignored. A
#: handle is opaque and echoed back verbatim, so it is refused, not cut.
MAX_CONNECTOR_ID_CHARS = 128
MAX_REPLY_HANDLE_CHARS = 512
_MAX_CAPABILITIES = 16


def opaque_value(value, limit: int) -> str:
    """A string the agent stores and hands back, or "" when it is not one:
    not a string, blank, too long, or carrying control characters."""
    if not isinstance(value, str):
        return ""
    value = value.strip()
    if not value or len(value) > limit:
        return ""
    if any(ord(c) < 32 or ord(c) == 127 for c in value):
        return ""
    return value


def event_connector(event: dict) -> dict:
    """The event's outbox fields, cleaned: `connector_id`, `reply_handle`
    and `capabilities` (a sorted tuple of lowercase names). Invalid parts
    read as absent rather than refusing the event."""
    capabilities: set[str] = set()
    raw = event.get("capabilities")
    if isinstance(raw, (list, tuple)):
        for cap in raw[:_MAX_CAPABILITIES]:
            name = opaque_value(cap, 32).lower()
            if name and ":" not in name:
                capabilities.add(name)
    return {
        "connector_id": opaque_value(event.get("connector_id"),
                                     MAX_CONNECTOR_ID_CHARS),
        "reply_handle": opaque_value(event.get("reply_handle"),
                                     MAX_REPLY_HANDLE_CHARS),
        "capabilities": tuple(sorted(capabilities)),
    }


def event_prefiltered(event: dict) -> bool:
    """The event's `prefiltered` flag; anything but an explicit no is yes.

    A connector that filters need not send it, so absence reads as true.
    A spelled-out "false" counts as false: the flag only ever tightens."""
    value = event.get("prefiltered", True)
    if isinstance(value, str):
        return value.strip().lower() not in ("false", "0", "no", "off")
    return value is not False and value != 0


def synthesize_onebot_payload(
        event: dict, self_mention_id: str, native_platforms=()) -> dict:
    """A neutral inbound event (docs/connectors.md) as the OneBot-v11 payload,
    in OneBot's vocabulary, that _handle_inner/_extract_text consume unchanged.

    A mention of the platform bot_id becomes `self_mention_id` (QQ_BOT_ID, or
    CONNECTOR_BOT_ID when blank) so _is_at_me fires; `native_platforms` mint
    bare ids (see `_ns`)."""
    platform = str(event.get("platform", "") or FALLBACK_PLATFORM).strip()
    native = platform in (native_platforms or ())
    if not native and platform == channels.NATIVE_PLATFORM:
        # Not "qq:123" either: platform_of() would read it as native and mix
        # its evidence with real QQ evidence.
        platform = FALLBACK_PLATFORM
    message_type = "private" if event.get("conversation_type") == "dm" else "group"
    conversation_id = (
        event.get("conversation_id")
        if message_type == "group"
        else event.get("sender_id")
    )
    bot_id = str(event.get("bot_id", ""))
    sender_name = str(event.get("sender_name", "") or "?")
    user_id = _ns(platform, native, event.get("sender_id", ""))

    message: list[dict] = []
    has_self_mention = False
    for seg in event.get("segments") or []:
        if not isinstance(seg, dict):
            logger.debug("[Connector] %s: dropping non-dict segment %s",
                         platform, type(seg).__name__)
            continue
        t = seg.get("type")
        if t not in _KNOWN_SEGMENT_TYPES:
            # DEBUG: a newer connector may send types this version predates,
            # but a typo looks the same, so not silent either.
            logger.debug("[Connector] %s: dropping unknown segment type %r",
                         platform, t)
            continue
        if t == "text":
            message.append({"type": "text", "data": {"text": str(seg.get("text", ""))}})
        elif t == "mention":
            target = str(seg.get("user_id", ""))
            if bot_id and target == bot_id:
                message.append({"type": "at", "data": {"qq": self_mention_id}})
                has_self_mention = True
            else:
                message.append(
                    {"type": "at", "data": {"qq": _ns(platform, native, target)}})
        elif t == "image":
            url = str(seg.get("url") or "")
            b64 = str(seg.get("b64") or "")
            image: dict = {}
            if url:
                image = {"url": url}
            elif b64:
                image = {"file": f"base64://{b64}"}
            if image:
                if seg.get("sticker") is True:
                    image["sticker"] = True
                message.append({"type": "image", "data": image})
        elif t == "emoji":
            face = {}
            for key in ("name", "id"):
                value = seg.get(key)
                if isinstance(value, (str, int)) and str(value).strip():
                    face[key] = str(value).strip()[:64]
            message.append({"type": "face", "data": face})
        elif t == "reply":
            reply_id = seg.get("message_id", seg.get("id"))
            data = {}
            if reply_id is not None and reply_id != "":
                data["id"] = _ns_mid(
                    platform, native, conversation_id, reply_id)
            # What the connector saw of the quoted message; _extract_text
            # uses it only when the agent has no record of its own.
            quoted = seg.get("text")
            if isinstance(quoted, str) and quoted.strip():
                data["quote_text"] = quoted[:500]
                sender = str(seg.get("sender_id") or "")
                if bot_id and sender == bot_id:
                    data["quote_self"] = True
                else:
                    name = seg.get("sender_name")
                    if isinstance(name, str) and name.strip():
                        data["quote_name"] = name[:64]
            message.append({"type": "reply", "data": data})
    # Addressed without a mention (a Telegram reply to the bot): prepend a
    # synthetic at so _is_at_me fires.
    if event.get("addressed") and not has_self_mention:
        message.insert(0, {"type": "at", "data": {"qq": self_mention_id}})

    payload: dict = {
        "post_type": "message",
        "message_type": message_type,
        "user_id": user_id,
        "sender": {"user_id": user_id, "nickname": sender_name, "card": sender_name},
        "raw_message": str(event.get("text", "") or ""),
        "message": message,
        "_connector": True,
        "_platform": platform,
    }
    if message_type == "group":
        payload["group_id"] = _ns(
            platform, native, event.get("conversation_id", ""))
    mid = event.get("message_id")
    if mid is not None and mid != "":
        # Per-conversation dedupe key (see _ns_mid); a DM's is its sender.
        payload["message_id"] = _ns_mid(platform, native, conversation_id, mid)
    return payload
