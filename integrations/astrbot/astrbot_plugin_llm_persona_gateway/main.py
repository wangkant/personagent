"""AstrBot plugin: forward messages to an external LLM persona agent.

This plugin turns AstrBot into a thin transport for the persona-llm-agent
gateway (POST /webhook/gateway). Every message AstrBot receives on any
platform adapter (Telegram, Discord, Slack, WeChat bridges, ...) is mapped
to a platform-neutral inbound event, POSTed to the agent, and the agent's
neutral reply items are converted back into AstrBot message chains.

Neutral inbound event schema (must stay in sync with gateway.py in the
agent repo):

    {
      "platform": str,                  # AstrBot platform adapter name
      "message_type": "group"|"private",
      "conversation_id": str,           # group id, or sender id for DMs
      "user_id": str,                   # raw platform sender id
      "sender_name": str,
      "self_id": str,                   # raw platform bot id
      "message_id": str|int|null,
      "is_at_me": bool,
      "segments": [
        {"type": "text", "text": str},
        {"type": "mention", "user_id": str, "name": str},
        {"type": "image", "url": str} | {"type": "image", "b64": str},
        {"type": "emoji", "name": str},
        {"type": "reply"}
      ],
      "raw_text": str
    }

Agent response schema:

    {"handled": bool,
     "replies": [{"type": "text", "text": str, "at_user_id": str|null,
                  "reply_to_message_id": str|null} |
                 {"type": "image", "b64": str, "at_user_id": str|null,
                  "reply_to_message_id": str|null}]}

at_user_id is platform-prefixed ("<platform>:<raw>"); reply_to_message_id is
conversation-namespaced ("<platform>:<conversation>:<raw mid>", matching the
gateway's inbound message_id synthesis). Some agent builds address people via
at_user_id (mention), others via reply_to_message_id (quote-reply); the
plugin maps whichever is present back to the native component.
"""

import asyncio
import random

import httpx

from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.platform import MessageType
from astrbot.api.star import Context, Star
import astrbot.api.message_components as Comp

DEFAULT_AGENT_URL = "http://127.0.0.1:8080/webhook/gateway"
DEFAULT_TIMEOUT_S = 180


class LLMPersonaGateway(Star):
    """Forward all eligible messages to the persona agent and relay replies."""

    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        # One shared client; the timeout is applied per request so config
        # changes take effect without a reload.
        self._client = httpx.AsyncClient()

    async def terminate(self):
        await self._client.aclose()

    # ---------- inbound: AstrBot event -> neutral event ----------

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def forward_to_agent(self, event: AstrMessageEvent):
        # EventMessageType.ALL also matches OTHER_MESSAGE (system/channel
        # events). Those report is_private_chat() False with an empty group
        # id, so the group/private split below would misclassify them as
        # DMs and run the agent's DM persona on them — skip them outright.
        msg_type = getattr(event.message_obj, "type", None)
        if msg_type not in (MessageType.GROUP_MESSAGE, MessageType.FRIEND_MESSAGE):
            return

        platform = event.get_platform_name()
        excluded = [str(p) for p in (self.config.get("excluded_platforms") or [])]
        if platform in excluded:
            return

        self_id = str(event.get_self_id())
        sender_id = str(event.get_sender_id())
        if sender_id and sender_id == self_id:
            return  # never forward the bot's own messages

        group_id = "" if event.is_private_chat() else str(event.get_group_id() or "")
        is_group = bool(group_id)

        if is_group:
            whitelist = [str(g) for g in (self.config.get("group_whitelist") or [])]
            if whitelist and group_id not in whitelist:
                return
        else:
            if not self.config.get("private_enabled", True):
                return
            whitelist = [str(u) for u in (self.config.get("private_whitelist") or [])]
            if whitelist and sender_id not in whitelist:
                return

        segments, is_at_me = self._map_segments(event, self_id)
        raw_text = event.message_str or ""
        if platform == "telegram":
            # The Telegram adapter encodes "reply to the bot" as a wake-prefix
            # hack prepended to the text ("/@<bot> ", restored to "/ " by its
            # own command handling). AstrBot's wake stage cleans message_str
            # but not the component chain — strip the artifact from both so
            # the agent never sees it as user text.
            raw_text = self._strip_tg_wake_artifact(raw_text, self_id)
            for seg in segments:
                if seg.get("type") == "text":
                    seg["text"] = self._strip_tg_wake_artifact(
                        seg.get("text") or "", self_id
                    )
                    break
        if is_group and bool(getattr(event, "is_at_or_wake_command", False)):
            # Some adapters signal "this message addresses the bot" only via
            # the pipeline wake flag (e.g. a Telegram reply-to-bot emits no
            # At component at all).
            is_at_me = True

        conversation_id = group_id if is_group else sender_id
        neutral_event = {
            "platform": platform,
            "message_type": "group" if is_group else "private",
            "conversation_id": conversation_id,
            "user_id": sender_id,
            "sender_name": event.get_sender_name() or sender_id,
            "self_id": self_id,
            "message_id": getattr(event.message_obj, "message_id", None),
            "is_at_me": is_at_me,
            "segments": segments,
            "raw_text": raw_text,
        }

        replies = await self._post_to_agent(neutral_event)

        first = True
        for item in replies:
            chain = self._build_chain(item, platform, is_group, conversation_id)
            if not chain:
                continue
            if not first:
                # Small pause between consecutive replies so multi-bubble
                # answers read naturally instead of arriving as a burst.
                await asyncio.sleep(random.uniform(0.8, 1.8))
            first = False
            yield event.chain_result(chain)

        if self.config.get("block_default", True):
            # The agent owns these conversations: keep AstrBot's built-in
            # LLM pipeline from producing a second reply.
            event.stop_event()

    def _map_segments(self, event: AstrMessageEvent, self_id: str):
        """Map AstrBot message components to neutral segments."""
        segments = []
        is_at_me = False
        components = getattr(event.message_obj, "message", None) or []
        for comp in components:
            if isinstance(comp, Comp.Plain):
                segments.append({"type": "text", "text": comp.text or ""})
            elif isinstance(comp, Comp.At):
                target = str(comp.qq)
                # Mentions arrive as typed (e.g. Telegram usernames are
                # case-insensitive), so compare case-insensitively, and emit
                # the canonical self_id on a match: the agent-side
                # synthesize_onebot_payload normalizes self-mentions with an
                # exact compare against the event's self_id.
                if self_id and target.lower() == self_id.lower():
                    is_at_me = True
                    target = self_id
                segments.append(
                    {
                        "type": "mention",
                        "user_id": target,
                        "name": str(getattr(comp, "name", "") or ""),
                    }
                )
            elif isinstance(comp, Comp.Image):
                seg = {"type": "image"}
                url = str(getattr(comp, "url", "") or "")
                file = str(getattr(comp, "file", "") or "")
                if file.startswith("base64://"):
                    seg["b64"] = file[len("base64://"):]
                elif url:
                    seg["url"] = url
                elif file:
                    seg["url"] = file
                if "url" in seg or "b64" in seg:
                    segments.append(seg)
            elif isinstance(comp, Comp.Face):
                segments.append({"type": "emoji", "name": str(getattr(comp, "id", ""))})
            elif isinstance(comp, Comp.Reply):
                # Quoting one of the bot's own messages addresses the bot,
                # even on platforms that emit no At component for it. (On
                # Telegram sender_id is numeric while self_id is the bot
                # username, so this match never fires there — the wake-flag
                # OR in forward_to_agent covers that case.)
                if self_id and str(getattr(comp, "sender_id", "") or "") == self_id:
                    is_at_me = True
                segments.append({"type": "reply"})
            # Any other component type carries nothing the agent understands.
        return segments, is_at_me

    @staticmethod
    def _strip_tg_wake_artifact(text: str, self_id: str) -> str:
        """Remove the Telegram adapter's reply-to-bot wake hack from the
        start of a text. The adapter prepends "/@<bot username> " (its own
        command restoration turns that into "/ ") purely to trip AstrBot's
        wake stage; neither form is something the user typed."""
        if not text:
            return text
        if self_id:
            marker = f"/@{self_id.lower()}"
            low = text.lower()
            if low.startswith(marker + " "):
                return text[len(marker) + 1:]
            if low == marker:
                return ""
        if text.startswith("/ "):
            return text[2:]
        return text

    # ---------- transport ----------

    async def _post_to_agent(self, neutral_event: dict) -> list:
        url = str(self.config.get("agent_url") or DEFAULT_AGENT_URL)
        timeout = float(self.config.get("timeout_s") or DEFAULT_TIMEOUT_S)
        headers = {}
        token = str(self.config.get("gateway_token") or "")
        if token:
            headers["X-Gateway-Token"] = token
        try:
            resp = await self._client.post(
                url, json=neutral_event, headers=headers, timeout=timeout
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.warning(f"llm_persona_gateway: agent request failed: {e}")
            return []
        replies = data.get("replies") if isinstance(data, dict) else None
        if not isinstance(replies, list):
            return []
        return [r for r in replies if isinstance(r, dict)]

    # ---------- outbound: neutral reply item -> AstrBot chain ----------

    def _build_chain(self, item: dict, platform: str, is_group: bool,
                     conversation_id: str):
        at_target = self._resolve_at(item.get("at_user_id"), platform) if is_group else None
        reply_id = self._resolve_reply_id(
            item.get("reply_to_message_id"), platform, conversation_id
        )
        prefix = [Comp.Reply(id=reply_id)] if reply_id else []
        rtype = item.get("type")
        # name= matters: the Telegram send path renders outbound mentions
        # from At.name only (qq is ignored there, and name defaults to ""),
        # while aiocqhttp reads qq — pass both so every adapter works.
        if rtype == "text":
            text = item.get("text") or ""
            if not text:
                return None
            if at_target:
                return prefix + [Comp.At(qq=at_target, name=at_target),
                                 Comp.Plain(" " + text)]
            return prefix + [Comp.Plain(text)]
        if rtype == "image":
            b64 = item.get("b64") or ""
            if not b64:
                return None
            chain = list(prefix)
            if at_target:
                chain.append(Comp.At(qq=at_target, name=at_target))
            chain.append(Comp.Image.fromBase64(b64))
            return chain
        logger.warning(f"llm_persona_gateway: dropping unknown reply type {rtype!r}")
        return None

    @staticmethod
    def _resolve_at(at_user_id, platform: str):
        """Recover the raw platform id from a gateway-prefixed mention target.

        Gateway user ids are "<platform>:<raw id>". A bare value without a
        platform prefix is the agent's QQ-side bot id (or a hallucinated
        marker) and is never addressable here, so it is dropped.
        """
        if not at_user_id:
            return None
        target = str(at_user_id)
        prefix = f"{platform}:"
        if target.startswith(prefix):
            raw = target[len(prefix):]
            return raw or None
        if ":" in target:
            logger.warning(
                f"llm_persona_gateway: mention target {target!r} is not on "
                f"platform {platform!r}, sending without at"
            )
        return None

    @staticmethod
    def _resolve_reply_id(reply_to, platform: str, conversation_id: str):
        """Recover the raw platform message id from a conversation-namespaced
        reply_to_message_id ("<platform>:<conversation>:<raw mid>", emitted
        by agent builds that point at people via quote-reply instead of
        mentions). An id from another platform or another conversation can't
        be quoted here, so it is dropped and the reply goes out without a
        quote."""
        if not reply_to:
            return None
        target = str(reply_to)
        prefix = f"{platform}:{conversation_id}:"
        if target.startswith(prefix):
            raw = target[len(prefix):]
            return raw or None
        return None
