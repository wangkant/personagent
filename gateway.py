"""Platform-neutral gateway layer.

Lets an external forwarder (e.g. an AstrBot plugin bridging Telegram /
Discord / Slack) POST one inbound message to this agent
and receive the agent's replies in the same HTTP response. The QQ/NapCat
direct path is untouched: the gateway synthesizes a OneBot-v11-shaped
payload that the existing pipeline consumes unchanged, and a contextvar
sink diverts the NapCat send funnels into an in-memory reply list for the
duration of that one handle() call.

Neutral inbound event schema (the body of POST /webhook/gateway):

    {
      "platform":        str,                    # e.g. "telegram"
      "message_type":    "group" | "private",
      "conversation_id": str,                    # group/channel id on the platform
      "user_id":         str,                    # sender id on the platform
      "sender_name":     str,
      "self_id":         str,                    # the bot's own id on the platform
      "message_id":      str | int | null,
      "is_at_me":        bool,
      "segments": [
        {"type": "text", "text": str}
        | {"type": "mention", "user_id": str, "name": str}
        | {"type": "image", "url": str?, "b64": str?}
        | {"type": "emoji", "name": str?}
        | {"type": "reply"}
      ],
      "raw_text":        str
    }

Platform ids are namespaced as "<platform>:<raw id>" before they enter the
pipeline, so memory / RAG / buffers can never collide with real QQ numbers.
Message ids are additionally namespaced by conversation
("<platform>:<conversation>:<raw mid>") because some platforms issue ids
per chat, and the dedupe ring must not collide across chats.

Neutral outbound reply items (the "replies" list in the response):

    {"type": "text",  "text": str, "at_user_id": str?}
    {"type": "image", "b64": str,  "at_user_id": str?}

where at_user_id, when present, is the platform-prefixed id the reply
mentions (the forwarder converts it back to a native mention).
"""
from __future__ import annotations

import contextvars
import logging
from typing import Optional

logger = logging.getLogger("agent.gateway")

# Set (to a GatewaySink) only inside Agent.handle_gateway. The NapCat send
# funnels check it first and divert into the sink instead of doing HTTP, so
# every other caller — the entire QQ path — sees the default None and is
# behaviorally unchanged.
current_sink: contextvars.ContextVar[Optional["GatewaySink"]] = contextvars.ContextVar(
    "current_sink", default=None,
)


def message_to_reply_item(message) -> dict:
    """Convert one NapCat-shaped message (str or v11 segment list, exactly
    what _napcat_send_group/_napcat_send_private receive) into one neutral
    reply item. The send paths only ever emit a bare text chunk, [at?, text]
    or [at?, image base64://...], so a single folded item is lossless."""
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
        item["at_user_id"] = at_user_id
    return item


class GatewaySink:
    """Ordered collector for the replies produced while handling one gateway
    event. Closed once handle_gateway returns its HTTP response; a late add
    (e.g. from a background task that inherited the context) is dropped with
    a warning instead of being silently lost in a dead response."""

    def __init__(self) -> None:
        self.items: list[dict] = []
        self.closed = False

    def add(self, message) -> None:
        if self.closed:
            logger.warning("[Gateway] sink already closed; dropping late reply: %r",
                           str(message)[:120])
            return
        self.items.append(message_to_reply_item(message))


def synthesize_onebot_payload(event: dict, bot_qq: str) -> dict:
    """Convert a neutral inbound event (schema in the module docstring) into
    a OneBot-v11-shaped payload that _handle_inner/_extract_text consume
    unchanged. Mentions of the platform self_id are normalized to bot_qq so
    _is_at_me fires exactly like a real QQ @-mention."""
    platform = str(event.get("platform", "") or "gateway").strip()
    message_type = event.get("message_type", "group")
    self_id = str(event.get("self_id", ""))
    sender_name = str(event.get("sender_name", "") or "?")
    user_id = f"{platform}:{event.get('user_id', '')}"

    message: list[dict] = []
    has_self_mention = False
    for seg in event.get("segments") or []:
        if not isinstance(seg, dict):
            continue
        t = seg.get("type")
        if t == "text":
            message.append({"type": "text", "data": {"text": str(seg.get("text", ""))}})
        elif t == "mention":
            target = str(seg.get("user_id", ""))
            if self_id and target == self_id:
                message.append({"type": "at", "data": {"qq": bot_qq}})
                has_self_mention = True
            else:
                message.append({"type": "at", "data": {"qq": f"{platform}:{target}"}})
        elif t == "image":
            url = str(seg.get("url") or "")
            b64 = str(seg.get("b64") or "")
            if url:
                message.append({"type": "image", "data": {"url": url}})
            elif b64:
                message.append({"type": "image", "data": {"file": f"base64://{b64}"}})
        elif t == "emoji":
            message.append({"type": "face", "data": {}})
        elif t == "reply":
            message.append({"type": "reply", "data": {}})
    # Some platforms signal "this message addresses the bot" without a real
    # mention segment (e.g. a Telegram reply-to-bot). Prepend a synthetic at
    # so _is_at_me fires.
    if event.get("is_at_me") and not has_self_mention:
        message.insert(0, {"type": "at", "data": {"qq": bot_qq}})

    payload: dict = {
        "post_type": "message",
        "message_type": message_type,
        "user_id": user_id,
        "sender": {"user_id": user_id, "nickname": sender_name, "card": sender_name},
        "raw_message": str(event.get("raw_text", "") or ""),
        "message": message,
        "_gateway": True,
        "_platform": platform,
    }
    if message_type == "group":
        payload["group_id"] = f"{platform}:{event.get('conversation_id', '')}"
    mid = event.get("message_id")
    if mid is not None and mid != "":
        # Namespace the dedupe key by conversation as well: several platforms
        # (Telegram, Slack) issue message ids per chat, so the same raw mid
        # routinely appears in two different chats and a bare
        # "<platform>:<mid>" key would silently swallow the second message.
        # Private events use the sender as the conversation.
        conv = event.get("conversation_id") if message_type == "group" \
            else event.get("user_id")
        payload["message_id"] = f"{platform}:{conv}:{mid}"
    return payload
