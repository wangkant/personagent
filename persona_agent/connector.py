"""Platform-neutral connector layer.

Lets an external connector (e.g. an AstrBot plugin bridging Telegram /
Discord / Slack) POST one inbound message to this agent
and receive the agent's replies in the same HTTP response. The QQ/NapCat
direct path is untouched: the connector event is turned into a
OneBot-v11-shaped payload that the existing pipeline consumes unchanged, and
a contextvar sink diverts the NapCat send funnels into an in-memory reply
list for the duration of that one handle_event() call.

Neutral inbound event schema (the body of POST /v1/events):

    {
      "kind":              "event"?,
      "platform":          str,                  # e.g. "telegram"
      "conversation_type": "group" | "dm",
      "conversation_id":   str,                  # group/channel id on the platform
      "sender_id":         str,                  # sender id on the platform
      "sender_name":       str,
      "bot_id":            str,                  # the bot's own id on the platform
      "message_id":        str | int | null,
      "sent_at":           int,                  # REQUIRED; unix seconds
      "addressed":         bool,
      "segments": [
        {"type": "text", "text": str}
        | {"type": "mention", "user_id": str, "name": str}
        | {"type": "image", "url": str?, "b64": str?, "sticker": bool?}
        | {"type": "emoji", "name": str?, "id": str?}
        | {"type": "reply", "message_id": str?, "text": str?,
           "sender_id": str?, "sender_name": str?}
      ],
      "text":              str,
      "proactive":         bool?,                # see below
      "prefiltered":       bool?,                # default true; see below
      "connector_id":      str?,                 # see below
      "reply_handle":      str?,
      "capabilities":      [str]?
    }

A reply segment's `text` is the quoted message as the connector saw it. The
agent prefers its own record of that message and uses the connector's only
when it never saw the original (a quote of its own reply, or of something
older than its index), fenced as text the sender did not write. An emoji's
`name` reaches the model as `[emoji: name]`; an image with `sticker` true
reads as `[sticker: ...]` instead of `[image: ...]`.

`connector_id`, `reply_handle` and `capabilities` say how to reach the
conversation later without an incoming message (docs/connectors.md,
"Outbox"). They are remembered per conversation once a turn is admitted
(outbox.HandleStore); a value of the wrong type or shape is ignored, never a
400, so a connector that sends none of them just gets no outbox.

`prefiltered` says whether the connector applied its own allowlist. Absent or
true, a platform with no ACCESS_GROUPS / ACCESS_DM_USERS entries is left to
the connector; false makes the agent's lists the only filter, so that
platform is refused until it has entries. It can only tighten, which is why
a connector may assert it (access.py).

`sent_at` is the moment the SOURCE platform stamped the message, not the
moment the connector sent it on: the two ages are checked separately, so a
connector that retries for a minute is not mistaken for a replayed event. It
is rejected when it differs from now by more than CONNECTOR_MAX_EVENT_AGE_S
(`_connector_event_is_fresh` in main.py), and it is required — an event
without it is a 400, which is why it appears in `main._validate_event_payload`'s
required tuple.

`proactive` marks a turn NOBODY SENT. It says the text on this event is a cue
the CALLER wrote to brief the persona — "they have been quiet a while, say
something if you genuinely have something to say" — rather than a message
from the person on the other end. The model reads it for that one call, as
reference beside the engine's own proactive instructions (which are what
allow the persona to stay silent), fenced as external material and cut at
500 characters. Left out, which is every ordinary forwarded turn, nothing
changes.

It is how a connector that cannot poll the outbox gets proactive turns. The
agent cannot open a conversation through such a connector: the reply sink
closes when the request returns, so there is no channel to speak into
between requests. Inverting it removes the problem instead of solving it —
the connector issues the request on a schedule of its own, and if the persona
has something to say the reply comes back in the response like any other.
It stamps the same DM cooldown the agent's own proactive loop reads.

The flag is load-bearing, not decorative. Without it the caller's own
directive is indistinguishable from the reader's words: it lands in
`private_history` as `{"role": "user"}`, stays for 40 turns, can be quoted
back at somebody who never wrote it, and can be promoted into a memory about
them.

It is honoured on DM events only. A group event carrying it is claimed
(`owned` comes back true, so the connector keeps its own model quiet too) and
dropped before the text is buffered: a room has no transient cue to carry it
as, and it is never read as anyone's words.

Platform ids are namespaced as "<platform>:<raw id>" before they enter the
pipeline, so memory / RAG / buffers can never collide with real QQ numbers.
Message ids are additionally namespaced by conversation
("<platform>:<conversation>:<raw mid>") because some platforms issue ids
per chat, and the dedupe ring must not collide across chats.

Neutral outbound reply items (the "replies" list in the response):

    {"type": "text",  "text": str, "mention_user_id": str?}
    {"type": "image", "b64": str,  "mention_user_id": str?}

where mention_user_id, when present, is the platform-prefixed id the reply
mentions (the connector converts it back to a native mention).
"""
from __future__ import annotations

import contextvars
import logging
from typing import Optional

from . import channels

logger = logging.getLogger("agent.connector")

#: The id a forwarded mention of the bot itself is rewritten to when QQ_BOT_ID is
#: blank, which it is on every install without QQ: QQ_BOT_ID is the bot's QQ
#: account and nothing else. Without it the self mention became an @ of "" and
#: _is_at_me could not recognise it. No namespaced id (those always contain
#: ':') and no QQ number (digits) can equal it.
CONNECTOR_BOT_ID = "persona-self"

#: The platform an event is filed under when it names none, or names QQ
#: without being a CONNECTOR_QQ_PLATFORMS one. A stored name: ids minted under
#: it are already in the memory and ledger rows, so it keeps its spelling.
FALLBACK_PLATFORM = "gateway"

#: Inbound segment types this version understands. Anything else is dropped
#: (see synthesize_onebot_payload) — listed here so the drop can say so.
_KNOWN_SEGMENT_TYPES = frozenset({"text", "mention", "image", "emoji", "reply"})


def _ns_mid(platform: str, native: bool, conversation_id, mid) -> str:
    """Namespace a MESSAGE id.

    A non-native platform gets the conversation in the key too, because
    several of them (Telegram, Slack) issue message ids per chat: the same raw
    mid routinely appears in two rooms, and a bare "<platform>:<mid>" would let
    the dedupe ring swallow the second one.

    A native mid must stay bare for the opposite reason. QQ mids are already
    globally unique, and the ring holds them bare from the NapCat path — so
    namespacing one would make the same message delivered by both doors look
    like two messages, and it would be answered twice.
    """
    return str(mid) if native else f"{platform}:{conversation_id}:{mid}"


def _ns(platform: str, native: bool, raw: object) -> str:
    """Namespace a USER or GROUP id — unless the platform is native.

    A key with NO namespace is QQ (`channels.NATIVE_PLATFORM`), and every store
    on disk has been keyed that way since QQ was the only channel. So a QQ
    message that reaches the agent through a connector rather than from NapCat
    has to mint exactly the ids NapCat would have: prefix it and it addresses a
    different conversation than the one it came from, orphaning everything
    already learned about that room and everyone in it. Worse, the ledgers
    content-address their rows over `conv_id`, so the rename cannot be repaired
    by rewriting a field — every id derived from it changes too.

    `native` is NOT the connector's decision. It is the operator's, via
    CONNECTOR_QQ_PLATFORMS, because minting a bare id claims QQ authority:
    bare ids are what the QQ entries of ADMIN_IDS, ACCESS_GROUPS and
    ACCESS_DM_USERS are compared against. A connector that could assert it
    for itself could address any QQ conversation the agent can reach.
    Default empty — every platform is namespaced until an operator says
    otherwise.
    """
    return str(raw) if native else f"{platform}:{raw}"

# Set (to a ConnectorSink) only inside Agent.handle_event. The NapCat send
# funnels check it first and divert into the sink instead of doing HTTP, so
# every other caller — the entire QQ path — sees the default None and is
# behaviorally unchanged.
current_sink: contextvars.ContextVar[Optional["ConnectorSink"]] = contextvars.ContextVar(
    "current_sink", default=None,
)

# A contextvar rather than a threaded parameter, for the same reason
# `current_sink` is one: per-turn state on an Agent instance shared by every
# conversation, where asyncio hands each Task its own copy so two turns in
# flight cannot see each other's value. None means "not supplied" and the
# PERSONA_TZ_OFFSET_HOURS env default still applies, so a deployment that never sets
# it is behaviorally unchanged. A connector embedder with a per-user notion of
# "local time" may set it for the duration of a turn.
current_tz_offset_h: contextvars.ContextVar[Optional[float]] = contextvars.ContextVar(
    "current_tz_offset_h", default=None,
)


def message_to_reply_item(
        message, *, platform: str = "", native: bool = False,
        bot_id: str = "") -> dict:
    """Convert one NapCat-shaped message (str or v11 segment list, exactly
    what _napcat_send_group/_napcat_send_private receive) into one neutral
    reply item. The send paths only ever emit a bare text chunk, [at?, text]
    or [at?, image base64://...], so a single folded item is lossless.

    `platform`/`native` re-namespace an outbound mention. Inbound, `_ns` mints
    ids for a native platform BARE, because every store on disk is keyed that
    way — but `mention_user_id` is read by the connector, not by a store, and
    the connector resolves "<platform>:<raw>". So a mention that came in bare goes
    back out bare, and the reference client drops it on the floor: on the
    supported QQ path (CONNECTOR_QQ_PLATFORMS=aiocqhttp) every group
    @-mention silently disappeared. Restoring the prefix here keeps the two
    spellings where they each belong — bare for the ledgers, namespaced on the
    wire — and leaves `_ns` and every id in every store untouched.

    `bot_id` is never prefixed: it is the agent's own id on the native side,
    and addressing it would make the connector @ the bot itself."""
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
        # Which platform this turn arrived from, and whether the operator
        # authorized it to mint bare (native-spelled) ids. Both are needed to
        # put an outbound mention back into the "<platform>:<raw>" form the
        # connector resolves — see message_to_reply_item. The defaults
        # reproduce the previous behaviour exactly, so a bare ConnectorSink()
        # is unchanged.
        self.platform = str(platform or "")
        self.native = bool(native)
        self.bot_id = str(bot_id or "")
        # Whether the connector filtered this turn itself; see the schema.
        self.prefiltered = bool(prefiltered)
        self.items: list[dict] = []
        self.closed = False
        # Set once this turn clears the admission gates. It answers a
        # different question than `items`: whether the conversation is OURS,
        # not whether we chose to speak in it. A connector that conflates the
        # two hands every deliberate silence — a PASS, a debounce merge, a
        # rhythm-gate skip — to its own built-in model, which then answers as
        # someone else in a conversation this persona had decided to sit out.
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
    """Convert a neutral inbound event (schema in the module docstring) into
    a OneBot-v11-shaped payload that _handle_inner/_extract_text consume
    unchanged. Mentions of the platform bot_id are normalized to
    `self_mention_id` so _is_at_me fires exactly like a real QQ @-mention. The
    agent passes QQ_BOT_ID, or CONNECTOR_BOT_ID when that is blank
    (Agent._self_mention_id).

    `native_platforms` is the operator's list of connector platforms whose ids
    are minted bare instead of namespaced — see `_ns`. Empty by default.

    The payload keeps OneBot's own vocabulary ("private", user_id, self
    mentions as at segments): it is what the QQ pipeline reads."""
    platform = str(event.get("platform", "") or FALLBACK_PLATFORM).strip()
    native = platform in (native_platforms or ())
    if not native and platform == channels.NATIVE_PLATFORM:
        # An unauthorized connector must not mint "qq:123" either. It looks
        # namespaced, but platform_of() reads the segment before the colon and
        # would report the NATIVE platform — so this event's evidence would
        # compare compatible with real QQ evidence, which is the cross-platform
        # mixing that function exists to prevent. Give it a name that cannot.
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
            # Graceful degradation is intended — a connector may legitimately
            # send a segment type this version predates. DEBUG, not WARNING,
            # so forward-compatible traffic is not reported as a fault; but
            # not silence either, because a typo ("iamge") and a sticker from
            # next year's plugin look identical from here, and today both
            # leave the reader's message quietly truncated.
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
    # Some platforms signal "this message addresses the bot" without a real
    # mention segment (e.g. a Telegram reply-to-bot). Prepend a synthetic at
    # so _is_at_me fires.
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
        # Namespace the dedupe key by conversation as well: several platforms
        # (Telegram, Slack) issue message ids per chat, so the same raw mid
        # routinely appears in two different chats and a bare
        # "<platform>:<mid>" key would silently swallow the second message.
        # DM events use the sender as the conversation.
        payload["message_id"] = _ns_mid(platform, native, conversation_id, mid)
    return payload
