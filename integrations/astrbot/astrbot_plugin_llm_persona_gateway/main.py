"""AstrBot plugin: a personagent connector for every AstrBot platform.

It speaks the connector protocol in docs/connectors.md of the agent repo.
Each message AstrBot receives becomes the neutral inbound event, POSTed to
the agent's /webhook/gateway; the reply items that come back are sent as
AstrBot message chains. Messages nobody asked for (openers, follow-ups, the
excuse after a failed model call) wait in the agent's outbox, which this
plugin pulls and delivers through context.send_message.

What each adapter can and cannot do is in platforms.py. The signing and the
outbox loop are the connector SDK, vendored as personagent_connector.py.

Reply items: {"type": "text", "text", "at_user_id"?, "reply_to_message_id"?}
or {"type": "image", "b64", ...}. at_user_id is "<platform>:<raw id>";
reply_to_message_id is "<platform>:<conversation>:<raw mid>", the gateway's
own spelling of inbound message ids.
"""

import asyncio
import base64
import collections
import contextlib
import logging
import os
import random
import re
import secrets
import tempfile
import time
from urllib.parse import urlsplit

import httpx

from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, MessageChain, filter
from astrbot.api.platform import MessageType
from astrbot.api.star import Context, Star
import astrbot.api.message_components as Comp
from astrbot.core.platform.message_session import MessageSession

from . import personagent_connector as sdk
from .platforms import (
    LINE_PLACEHOLDERS,
    WECOM_AI_PLACEHOLDERS,
    Rules,
    _get,
    escape,
    image_suffix,
    is_private_url,
    kook_segments,
    media_note,
    native_message_id,
    rules_for,
    seconds,
    source_timestamp,
    split_text,
)

DEFAULT_AGENT_URL = "http://127.0.0.1:8080/webhook/gateway"
DEFAULT_TIMEOUT_S = 180
DEFAULT_FORWARD_THRESHOLD = 1500
DEFAULT_QUOTE_MAX_CHARS = 200
DEFAULT_MAX_INLINE_IMAGE_BYTES = 4_000_000
# Base64 an event may carry in total; the agent refuses bodies over 8 MB.
_EVENT_B64_BUDGET = 6_000_000
# How long a delivery waits for its platform to come up after a restart:
# AstrBot loads plugins before platforms.
_PLATFORM_WAIT_S = 30
# The plugin store key for the reply handles the plugin minted.
_HANDLES_KEY = "reply_handles"

# Retry policy for _post_to_agent. Only statuses where resending the exact
# same bytes is safe get a retry: 500 is the agent failing after accepting
# the envelope, and 429 is the gateway's admission gate, which runs before
# envelope verification (see gateway_webhook in the agent's main.py), so a
# 429 never burns a nonce and is always safe to resend. 400/403/413 mean the
# envelope or body itself is the problem -- resending unchanged bytes would
# just fail the same way again.
_RETRYABLE_STATUSES = frozenset({429, 500})
_RETRY_BACKOFFS_S = (0.3, 0.8)
# The agent rejects a signed envelope once its timestamp is older than this
# (ReplayGuard / _gateway_event_is_fresh in the agent's main.py). A retry
# reuses the original signed timestamp rather than re-signing, so each retry
# must START well inside this window (the age is checked on arrival).
_GATEWAY_REPLAY_WINDOW_S = 300
_RETRY_WINDOW_SAFETY_MARGIN_S = 20

# Discord leaves mentions, channels and custom emoji as raw markup in the text
# (discord.py's own syntax); Slack escapes links as <url|label>. Both are
# unfolded before the agent sees them, using the platform's own objects for
# names where it provides them.
_DISCORD_USER = re.compile(r"<@!?(\d+)>")
_DISCORD_ROLE = re.compile(r"<@&(\d+)>")
_DISCORD_CHANNEL = re.compile(r"<#(\d+)>")
_DISCORD_EMOJI = re.compile(r"<a?:(\w+):\d+>")
_SLACK_LINK = re.compile(r"<(https?://[^|>]+)(?:\|([^>]*))?>")
_VOICE_NOTE = "(sent a voice message)"
_VIDEO_NOTE = "(sent a video)"
_IMAGE_NOTE = "(sent an image)"


class _Prefixed(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        return f"llm_persona_gateway: outbox: {msg}", kwargs


# The SDK's pull loop reports into AstrBot's log, under this plugin's name.
sdk.logger = _Prefixed(logger, {})


def _comp_is(comp, name: str) -> bool:
    cls = getattr(Comp, name, None)
    return cls is not None and isinstance(comp, cls)


def _adapt_inbound(platform: str, event, segments: list) -> list:
    """Platform-specific unfolding of text the adapter left raw."""
    if platform not in ("discord", "slack", "kook"):
        return segments
    raw = getattr(event.message_obj, "raw_message", None)
    # The blocks path of the Slack adapter already unescaped the text.
    slack_escaped = not (isinstance(raw, dict) and raw.get("blocks"))
    out = []
    for seg in segments:
        if seg.get("type") != "text":
            out.append(seg)
        elif platform == "discord":
            out.extend(_discord_text(seg.get("text") or "", raw))
        elif platform == "kook":
            out.extend(kook_segments(seg.get("text") or ""))
        elif slack_escaped:
            out.append(dict(seg, text=_slack_text(seg.get("text") or "")))
        else:
            out.append(seg)
    return out


def _discord_text(text: str, raw) -> list:
    """Split Discord text into text + mention segments, resolving names
    from discord.py's Message.mentions / role_mentions / channel_mentions."""
    def names(attr, label):
        table = {}
        for obj in getattr(raw, attr, None) or []:
            oid = str(getattr(obj, "id", "") or "")
            if oid:
                table[oid] = str(getattr(obj, label, "") or getattr(obj, "name", "") or "")
        return table
    users = names("mentions", "display_name")
    roles = names("role_mentions", "name")
    channels = names("channel_mentions", "name")

    def plain(chunk: str) -> str:
        chunk = _DISCORD_EMOJI.sub(lambda m: f":{m.group(1)}:", chunk)
        chunk = _DISCORD_ROLE.sub(lambda m: "@" + (roles.get(m.group(1)) or "role"), chunk)
        return _DISCORD_CHANNEL.sub(lambda m: "#" + (channels.get(m.group(1)) or "channel"), chunk)

    out = []
    pos = 0
    for m in _DISCORD_USER.finditer(text):
        before = plain(text[pos:m.start()])
        if before:
            out.append({"type": "text", "text": before})
        uid = m.group(1)
        out.append({"type": "mention", "user_id": uid, "name": users.get(uid, "")})
        pos = m.end()
    tail = plain(text[pos:])
    if tail or not out:
        out.append({"type": "text", "text": tail})
    return out


def _flatten(segments: list) -> str:
    """Segments as one line of text, for a quote."""
    parts = []
    for seg in segments:
        if seg.get("type") == "text":
            parts.append(seg.get("text") or "")
        elif seg.get("type") == "mention":
            parts.append("@" + (seg.get("name") or seg.get("user_id") or ""))
        elif seg.get("type") == "emoji":
            parts.append(f":{seg.get('name') or ''}:")
    return "".join(parts)


def _slack_text(text: str) -> str:
    """Slack's mrkdwn escapes: <url|label> and the three HTML entities."""
    text = _SLACK_LINK.sub(lambda m: f"{m.group(2)} ({m.group(1)})" if m.group(2) else m.group(1), text)
    return text.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")


def _outline(chain) -> str:
    """What a quoted message showed, when the adapter gives only its parts."""
    parts = []
    for comp in chain or []:
        if isinstance(comp, Comp.Plain):
            parts.append(comp.text or "")
        elif isinstance(comp, Comp.Image):
            parts.append("(image)")
        elif _comp_is(comp, "Record"):
            parts.append("(voice message)")
        elif _comp_is(comp, "Video"):
            parts.append("(video)")
        elif _comp_is(comp, "File"):
            parts.append("(file)")
        elif isinstance(comp, Comp.Face):
            parts.append("(emoji)")
    return " ".join(p for p in parts if p).strip()


def _remove_files(paths) -> None:
    for path in paths:
        with contextlib.suppress(OSError):
            os.remove(path)


class _People:
    """Who the plugin has seen, per platform, bounded: the handle a mention
    needs where the platform mentions by username (Telegram, Mattermost,
    Misskey) while the agent knows people by id, and a display name."""

    def __init__(self, size: int = 4096):
        self._size = size
        self._by_id: collections.OrderedDict = collections.OrderedDict()
        self._by_handle: dict = {}

    def see(self, platform: str, user_id, handle=None, name=None) -> None:
        user_id = str(user_id or "")
        if not user_id:
            return
        handle = str(handle or "").lstrip("@") or None
        entry = self._by_id.pop((platform, user_id), {})
        entry = {"handle": handle or entry.get("handle"),
                 "name": str(name or "") or entry.get("name")}
        self._by_id[(platform, user_id)] = entry
        if handle:
            self._by_handle[(platform, handle.lower())] = user_id
        while len(self._by_id) > self._size:
            (plat, _uid), old = self._by_id.popitem(last=False)
            if old.get("handle"):
                self._by_handle.pop((plat, old["handle"].lower()), None)

    def handle(self, platform: str, user_id) -> str | None:
        return (self._by_id.get((platform, str(user_id))) or {}).get("handle")

    def name(self, platform: str, user_id) -> str | None:
        return (self._by_id.get((platform, str(user_id))) or {}).get("name")

    def id_for(self, platform: str, handle: str) -> str | None:
        return self._by_handle.get((platform, str(handle).lstrip("@").lower()))


class _Handles:
    """The reply handles this plugin minted, each bound to the conversation
    it came from, bounded like the agent's own store. The agent hands back
    whatever handle an admitted event carried, so only these are sent to."""

    def __init__(self, size: int = 4096):
        self._size = size
        self._bound: collections.OrderedDict = collections.OrderedDict()
        self.loaded = False

    def _trim(self) -> None:
        while len(self._bound) > self._size:
            self._bound.popitem(last=False)

    def mint(self, handle: str, platform: str, message_type: str,
             conversation_id: str) -> bool:
        """Bind a handle; True when that changed what should be stored."""
        entry = (str(platform), str(message_type), str(conversation_id))
        changed = self._bound.pop(handle, None) != entry
        self._bound[handle] = entry
        self._trim()
        return changed

    def bound(self, handle: str):
        """(platform, message_type, conversation_id), or None."""
        return self._bound.get(handle)

    def load(self, rows) -> None:
        """Take what the plugin store kept; handles minted meanwhile win."""
        kept = collections.OrderedDict()
        for row in rows if isinstance(rows, list) else []:
            if isinstance(row, list) and len(row) == 4 and all(isinstance(v, str) for v in row):
                kept[row[0]] = tuple(row[1:])
        for handle, entry in self._bound.items():
            kept.pop(handle, None)
            kept[handle] = entry
        self._bound = kept
        self._trim()
        self.loaded = True

    def rows(self) -> list:
        return [[handle, *entry] for handle, entry in self._bound.items()]


class LLMPersonaGateway(Star):
    """Forward all eligible messages to the persona agent, relay its replies,
    and deliver what it queues in its outbox."""

    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.context = context
        self.config = config
        # One shared client, made on first use; the timeout is applied per
        # request so config changes take effect without a reload.
        self._client = None
        self._forwarder_id = str(config.get("forwarder_id") or "").strip()
        self._people = _People()
        self._handles = _Handles()
        self._outbox_task = None
        self._outbox_stop = asyncio.Event()
        # Until then a delivery waits for its platform: AstrBot loads plugins
        # before platforms.
        self._starting_until = None

    async def initialize(self):
        await self._ensure_forwarder_id()
        self._starting_until = time.monotonic() + _PLATFORM_WAIT_S
        if self.config.get("outbox_enabled", True) and self._outbox_task is None:
            self._outbox_task = asyncio.create_task(self._run_outbox())

    async def terminate(self):
        # A terminate that raises leaves the old poller running next to the
        # reloaded one (AstrBot only logs it), so nothing here may raise.
        self._outbox_stop.set()
        task, self._outbox_task = self._outbox_task, None
        if task is not None:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await task
        client, self._client = self._client, None
        if client is not None:
            with contextlib.suppress(Exception):
                await client.aclose()

    async def _ensure_forwarder_id(self) -> str:
        """A stable id for this AstrBot, kept across restarts in AstrBot's
        plugin store: the agent queues outbox deliveries by it."""
        if self._forwarder_id:
            return self._forwarder_id
        stored = None
        with contextlib.suppress(Exception):
            stored = await self.get_kv_data("forwarder_id", None)
        if not stored:
            stored = "astrbot-" + secrets.token_hex(6)
            try:
                await self.put_kv_data("forwarder_id", stored)
            except Exception as e:
                logger.warning(
                    "llm_persona_gateway: could not store forwarder_id; the "
                    f"agent will see a new connector after a restart: {e}")
        self._forwarder_id = str(stored)
        return self._forwarder_id

    async def _load_handles(self) -> None:
        if self._handles.loaded:
            return
        rows = None
        try:
            rows = await self.get_kv_data(_HANDLES_KEY, None)
        except Exception as e:
            logger.warning(f"llm_persona_gateway: could not read the stored reply handles: {e}")
        self._handles.load(rows)

    async def _mint_handle(self, handle: str, platform: str, message_type: str,
                           conversation_id: str) -> None:
        """Bind a handle the outbox may later send to, before the agent can
        hand it back, and keep it across reloads."""
        await self._load_handles()
        if not self._handles.mint(handle, platform, message_type, conversation_id):
            return
        try:
            await self.put_kv_data(_HANDLES_KEY, self._handles.rows())
        except Exception as e:
            logger.warning(
                "llm_persona_gateway: could not store a reply handle; after a "
                f"reload the outbox waits for that conversation to write again: {e}")

    def _outbox_running(self) -> bool:
        task = self._outbox_task
        return task is not None and not task.done()

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
        if platform in self._excluded():
            return
        raw = getattr(event.message_obj, "raw_message", None)
        if not self._is_chat_message(platform, raw):
            return

        self_id = str(event.get_self_id())
        sender_id = str(event.get_sender_id())
        if sender_id and sender_id == self_id:
            return  # never forward the bot's own messages

        group_id = "" if event.is_private_chat() else str(event.get_group_id() or "")
        if (platform == "wecom_ai_bot" and msg_type == MessageType.GROUP_MESSAGE
                and not group_id):
            # The smart-bot adapter types group messages GROUP but leaves the
            # group id only in the raw payload.
            group_id = str(_get(raw, "message_data", "chatid") or "")
        is_group = bool(group_id)
        if not self._allowed(platform, is_group, group_id, sender_id):
            return

        self._remember_people(platform, event, raw)
        segments, is_at_me = await self._map_segments(event, self_id, platform)
        raw_text = event.message_str or ""
        if self._plain_note(platform, raw, raw_text.strip()) is not None:
            # "Sticker: X", "[voice消息]": the adapter's words, not the person's.
            raw_text = ""
        if platform == "telegram":
            # The Telegram adapter encodes "reply to the bot" as a wake-prefix
            # hack prepended to the text ("/@<bot> ", restored to "/ " by its
            # own command handling). AstrBot's wake stage cleans message_str
            # but not the component chain — strip the artifact from both so
            # the agent never sees it as user text.
            raw_text = self._strip_tg_wake_artifact(raw_text, self_id)
            stripped = False
            for seg in segments:
                if seg.get("type") == "text":
                    before = seg.get("text") or ""
                    seg["text"] = self._strip_tg_wake_artifact(before, self_id)
                    stripped = seg["text"] != before
                    break
            # That artifact, next to a quote, is the only sign a Telegram
            # reply-to-bot carries in the component chain: the Reply's
            # sender_id is numeric while self_id is the username, and no At
            # is emitted. AstrBot's is_at_or_wake_command is NOT used for
            # this — it is also set by any "/" wake-prefix text and by every
            # @all. The raw update below covers photos and voice too.
            if is_group and stripped and any(
                    seg.get("type") == "reply" for seg in segments):
                is_at_me = True
        if is_group and not is_at_me:
            is_at_me = self._addressed(platform, event, raw, self_id, raw_text)

        conversation_id = group_id if is_group else sender_id
        source_ts = source_timestamp(platform, raw)
        if source_ts is None:
            source_ts = (getattr(event.message_obj, "timestamp", None)
                         or getattr(event.message_obj, "time", None))
        try:
            source_ts = seconds(int(source_ts))
        except (TypeError, ValueError, OverflowError):
            logger.warning(
                "llm_persona_gateway: dropping event without a valid "
                "authoritative source timestamp"
            )
            return
        caps = []
        if self._outbox_running() and self._can_speak_first(platform, raw):
            caps.append("outbox")
        if any(seg.get("type") == "reply" and seg.get("text") for seg in segments):
            caps.append("quote_text")
        neutral_event = {
            "platform": platform,
            "message_type": "group" if is_group else "private",
            "conversation_id": conversation_id,
            "user_id": sender_id,
            "sender_name": event.get_sender_name() or sender_id,
            "self_id": self_id,
            "message_id": (native_message_id(platform, raw)
                           or getattr(event.message_obj, "message_id", None)),
            "source_timestamp": source_ts,
            "is_at_me": is_at_me,
            "segments": segments,
            "raw_text": raw_text,
            "forwarder_id": await self._ensure_forwarder_id(),
            "reply_handle": self._reply_handle(event),
            "caps": caps,
        }
        if not neutral_event["reply_handle"]:
            del neutral_event["reply_handle"]
        elif "outbox" in caps:
            await self._mint_handle(neutral_event["reply_handle"], platform,
                                    neutral_event["message_type"], conversation_id)

        rules = rules_for(platform)
        temps: list = []
        # AstrBot's own typing indicator, where the adapter has one (Telegram
        # today): the round-trip covers the agent's thinking and its typing
        # simulation, which is exactly when a person expects to see "typing".
        await self._typing(event, True)
        try:
            _replied, owned, replies = await self._post_to_agent(neutral_event)
            chains = self._render(
                replies, platform, is_group, conversation_id, temps,
                umo=neutral_event.get("reply_handle"))
            first = True
            for chain, _done in chains:
                if not first:
                    # Small pause between consecutive replies so multi-bubble
                    # answers read naturally instead of arriving as a burst.
                    await self._typing(event, True)
                    await asyncio.sleep(random.uniform(0.8, 1.8))
                first = False
                yield self._result(event, chain, rules)
        finally:
            _remove_files(temps)
            await self._typing(event, False)

        if owned and self.config.get("block_default", True):
            # Gate on ownership, not on whether a reply came back. The agent
            # stays quiet on purpose far more often than it speaks — PASS, a
            # debounce merge, the rhythm gate — and reading that as "not mine"
            # hands the conversation to AstrBot's built-in model, which then
            # answers as someone else in a room this persona chose to sit out.
            event.stop_event()

    def _excluded(self) -> list:
        return [str(p) for p in (self.config.get("excluded_platforms") or [])]

    def _allowed(self, platform: str, is_group: bool, conversation_id: str,
                 sender_id: str) -> bool:
        """The plugin's own filter, for an incoming message and again for an
        outbox delivery: the lists may have changed since it was queued."""
        if platform in self._excluded():
            return False
        if is_group:
            whitelist = [str(g) for g in (self.config.get("group_whitelist") or [])]
            return conversation_id in whitelist
        if not self.config.get("private_enabled", False):
            return False
        whitelist = [str(u) for u in (self.config.get("private_whitelist") or [])]
        return sender_id in whitelist

    @staticmethod
    def _is_chat_message(platform: str, raw) -> bool:
        """Something a person wrote, not a platform event the adapter types
        as a message."""
        if platform == "aiocqhttp" and raw is not None:
            # Notices (poke, recall, input status, member joins) and friend or
            # group requests arrive typed as messages with an empty chain.
            post_type = _get(raw, "post_type")
            return post_type in (None, "message")
        if platform == "slack" and isinstance(raw, dict):
            # Joins, topic changes and other subtypes are not someone talking.
            return raw.get("subtype") in (None, "file_share", "thread_broadcast", "me_message")
        if platform == "wecom" and isinstance(raw, dict) and "_wechat_kf_flag" in raw:
            # Customer service: origin 3 is the customer; 4 is a system event
            # and 5 a human agent writing from WeCom.
            return raw.get("origin") in (None, 3)
        return True

    def _can_speak_first(self, platform: str, raw=None, inst=None) -> bool:
        if not rules_for(platform).outbox:
            return False
        if platform == "wecom":
            # Customer-service mode refuses send_by_session.
            if isinstance(raw, dict) and "_wechat_kf_flag" in raw:
                return False
            if inst is not None and hasattr(getattr(inst, "client", None), "kf_message"):
                return False
        return True

    def _reply_handle(self, event) -> str:
        """Where the outbox can reach this conversation later: AstrBot's
        unified_msg_origin. With unique_session on, AstrBot rewrites a group
        event's session to one member; DingTalk, QQ official and Misskey then
        send to that member instead of the group, so the group's own session
        (kept on message_obj) is used."""
        umo = str(getattr(event, "unified_msg_origin", "") or "")
        obj = event.message_obj
        msg_type = getattr(obj, "type", None)
        session = str(getattr(obj, "session_id", "") or "")
        if msg_type == MessageType.GROUP_MESSAGE and session:
            try:
                platform_id = str(event.get_platform_id())
            except Exception:
                platform_id = umo.partition(":")[0]
            if platform_id:
                return f"{platform_id}:{msg_type.value}:{session}"
        return umo

    def _platform_inst_now(self, platform_id: str):
        try:
            return self.context.get_platform_inst(platform_id)
        except Exception:
            return None

    def _event_inst(self, event):
        try:
            return self._platform_inst_now(str(event.get_platform_id()))
        except Exception:
            return None

    def _remember_people(self, platform: str, event, raw) -> None:
        """Keep the usernames the outbound side needs to mention someone."""
        if platform == "telegram":
            for path in (("message", "from_user"),
                         ("message", "reply_to_message", "from_user")):
                user = _get(raw, *path)
                if user is not None and _get(user, "id") is not None:
                    self._people.see(platform, _get(user, "id"),
                                     _get(user, "username"), _get(user, "full_name"))
        elif platform == "mattermost":
            name = str(event.get_sender_name() or "")
            # Usernames never hold spaces; a display name would not mention.
            if name and not re.search(r"\s", name):
                self._people.see(platform, event.get_sender_id(), name, name)
        elif platform == "misskey":
            user = _get(raw, "fromUser") or _get(raw, "user")
            username = _get(user, "username")
            if username:
                host = _get(user, "host")
                self._people.see(platform, event.get_sender_id(),
                                 f"{username}@{host}" if host else username,
                                 _get(user, "name") or username)

    def _addressed(self, platform: str, event, raw, self_id: str,
                   text: str) -> bool:
        """The platform's own ways of addressing the bot that leave no At or
        Reply in the chain."""
        if platform == "telegram":
            replied = _get(raw, "message", "reply_to_message", "from_user", "username")
            return bool(replied and self_id and str(replied).lower() == self_id.lower())
        if platform == "discord":
            if any(str(_get(m, "id")) == self_id for m in _get(raw, "mentions") or []):
                return True  # the adapter strips a leading <@bot> from the text
            bot_roles = {str(_get(r, "id")) for r in _get(raw, "guild", "me", "roles") or []}
            if any(str(_get(r, "id")) in bot_roles for r in _get(raw, "role_mentions") or []):
                return True
            author = _get(raw, "reference", "resolved", "author", "id")
            return author is not None and str(author) == self_id
        if platform == "slack":
            return bool(self_id) and _get(raw, "parent_user_id") == self_id
        if platform == "kook":
            author = _get(raw, "extra", "quote", "author", "id")
            return author is not None and str(author) == self_id
        if platform == "satori":
            quoted = _get(raw, "message", "quote", "user", "id")
            return quoted is not None and str(quoted) == self_id
        if platform == "line":
            mentionees = _get(raw, "message", "mention", "mentionees") or []
            return any(isinstance(m, dict) and m.get("isSelf") for m in mentionees)
        if platform == "dingtalk":
            return bool(_get(raw, "is_in_at_list"))
        if platform == "wecom_ai_bot":
            return True  # WeCom delivers only group messages that @ the bot
        if platform == "misskey":
            # The adapter only sees a mention at the very start of a room text.
            name = getattr(self._event_inst(event), "_bot_username", "") or ""
            return bool(name) and re.search(
                rf"@{re.escape(name)}(?![\w.-])", text, re.I) is not None
        return False

    @staticmethod
    async def _typing(event, on: bool) -> None:
        fn = getattr(event, "send_typing" if on else "stop_typing", None)
        if fn is None:
            return
        try:
            await fn()
        except Exception as e:  # an indicator must never cost a reply
            logger.debug(f"llm_persona_gateway: typing indicator failed: {e}")

    def _quote_chars(self) -> int:
        if not self.config.get("forward_quoted_text", True):
            return 0
        try:
            return max(0, int(self.config.get("quote_max_chars", DEFAULT_QUOTE_MAX_CHARS)))
        except (TypeError, ValueError):
            return DEFAULT_QUOTE_MAX_CHARS

    def _reply_segment(self, message_id=None, text=None, sender_id=None,
                       sender_name=None) -> dict:
        seg = {"type": "reply"}
        if message_id not in (None, ""):
            seg["message_id"] = str(message_id)
        limit = self._quote_chars()
        if not limit:
            return seg
        text = str(text or "").strip()
        if text:
            seg["text"] = text if len(text) <= limit else text[:limit].rstrip() + "…"
        if sender_id not in (None, "", 0, "0"):
            seg["sender_id"] = str(sender_id)
        name = str(sender_name or "").strip()
        # Lark gives the first 8 characters of the sender's id as its name.
        if name and not (seg.get("sender_id") or "").startswith(name):
            seg["sender_name"] = name
        return seg

    async def _map_segments(self, event: AstrMessageEvent, self_id: str, platform: str = ""):
        """Map AstrBot message components to neutral segments."""
        segments = []
        is_at_me = False
        obj = event.message_obj
        raw = getattr(obj, "raw_message", None)
        components = getattr(obj, "message", None) or []
        # OneBot keeps what AstrBot's components drop: face names, sticker
        # flags and store stickers (mface) are read from the raw segments.
        onebot = []
        if platform == "aiocqhttp":
            onebot = [s for s in (_get(raw, "message") or []) if isinstance(s, dict)]
        raw_faces = iter([s.get("data") or {} for s in onebot if s.get("type") == "face"])
        raw_images = iter([s.get("data") or {} for s in onebot if s.get("type") == "image"])
        sticker = _get(raw, "message", "sticker") if platform == "telegram" else None
        budget = [_EVENT_B64_BUDGET]
        appid = None
        if platform == "lark" and any(isinstance(c, Comp.Reply) for c in components):
            # A message the bot sent names the app id as its sender.
            appid = getattr(self._event_inst(event), "appid", None)
        for comp in components:
            if _comp_is(comp, "File"):
                name = str(getattr(comp, "name", "") or "")
                note = self._file_note(platform, raw, comp)
                segments.append({"type": "text", "text": note or (
                    f"(sent a file: {name})" if name else "(sent a file)")})
                continue
            if _comp_is(comp, "Video"):
                segments.append({"type": "text", "text": _VIDEO_NOTE})
                continue
            if _comp_is(comp, "Record"):
                said = self._voice_transcript(platform, event, raw, components)
                segments.append({"type": "text", "text": (
                    f"(sent a voice message: {said})" if said else _VOICE_NOTE)})
                continue
            if isinstance(comp, Comp.Plain):
                text = comp.text or ""
                note = self._plain_note(platform, raw, text.strip())
                segments.extend(note if note is not None else [{"type": "text", "text": text}])
            elif isinstance(comp, Comp.At):
                target = str(comp.qq)
                name = str(getattr(comp, "name", "") or "")
                # Mentions arrive as typed (e.g. Telegram usernames are
                # case-insensitive), so compare case-insensitively, and emit
                # the canonical self_id on a match: the agent-side
                # synthesize_onebot_payload normalizes self-mentions with an
                # exact compare against the event's self_id.
                if self_id and target.lower() == self_id.lower():
                    is_at_me = True
                    target = self_id
                elif platform == "telegram":
                    # Telegram mentions by username but sends by numeric id;
                    # one person should be one id to the agent.
                    target = self._people.id_for(platform, target) or target
                segments.append({"type": "mention", "user_id": target, "name": name})
            elif isinstance(comp, Comp.Image):
                raw_image = next(raw_images, None)
                if sticker is not None and (_get(sticker, "is_animated")
                                            or _get(sticker, "is_video")):
                    continue  # .tgs / .webm: nothing the agent can look at
                seg = await self._image_segment(comp, platform, budget, raw)
                if seg is None:
                    continue
                if seg.get("type") == "image" and (
                        sticker is not None
                        or str((raw_image or {}).get("sub_type", "")) == "1"):
                    seg["sticker"] = True
                segments.append(seg)
            elif isinstance(comp, Comp.Face):
                data = next(raw_faces, None) or {}
                face_text = str(_get(data, "raw", "faceText") or data.get("faceText") or "")
                fid = str(getattr(comp, "id", "") or "")
                segments.append({"type": "emoji", "name": face_text.lstrip("/") or fid, "id": fid})
            elif isinstance(comp, Comp.Reply):
                # Quoting one of the bot's own messages addresses the bot,
                # even on platforms that emit no At component for it. (On
                # Telegram sender_id is numeric while self_id is the bot
                # username, so this match never fires there — forward_to_agent
                # reads the adapter's reply-to-bot text artifact instead.)
                sender = str(getattr(comp, "sender_id", "") or "")
                name = getattr(comp, "sender_nickname", "")
                text = (getattr(comp, "message_str", "") or getattr(comp, "text", "")
                        or _outline(getattr(comp, "chain", None)))
                if platform == "satori":
                    # The adapter reads the quote's author from a field
                    # Satori v1 does not send, and fills the gaps with
                    # placeholders of its own.
                    user = _get(raw, "message", "quote", "user")
                    if _get(user, "id"):
                        sender = str(_get(user, "id"))
                        name = _get(user, "nick") or _get(user, "name") or name
                    elif name == "内容":
                        name = ""
                    if text == "[引用消息]":
                        text = _outline(getattr(comp, "chain", None))
                if sender and (sender == self_id or (appid and sender == appid)):
                    is_at_me = True
                segments.append(self._reply_segment(
                    getattr(comp, "id", None), text, sender, name))
            # Any other component type carries nothing the agent understands.

        if onebot:
            if not is_at_me and any(
                    s.get("type") == "at" and str((s.get("data") or {}).get("qq")) == self_id
                    for s in onebot):
                is_at_me = True  # the adapter drops an At it cannot look up
            for s in onebot:
                if s.get("type") == "mface":
                    data = s.get("data") or {}
                    summary = str(data.get("summary") or "").strip("[]")
                    segments.append({"type": "emoji", "name": summary or "sticker",
                                     "id": str(data.get("emoji_id") or "")})
        segments = _adapt_inbound(platform, event, segments)
        segments.extend(self._raw_stickers(platform, raw))
        if not any(seg.get("type") == "reply" for seg in segments):
            reply = self._raw_reply(platform, raw)
            if reply is not None:
                segments.insert(0, reply)
        return segments, is_at_me

    def _plain_note(self, platform: str, raw, text: str):
        """Segments for a text the adapter wrote in place of something it
        did not map, or None when the text is the person's own."""
        if not text:
            return None
        if platform == "telegram":
            emoji = _get(raw, "message", "sticker", "emoji")
            if emoji and text == f"Sticker: {emoji}":
                return [{"type": "emoji", "name": str(emoji)}]
        elif platform == "wecom_ai_bot":
            kind = str(_get(raw, "message_data", "msgtype") or "")
            if text == f"[{kind}消息]" and text in WECOM_AI_PLACEHOLDERS:
                return [{"type": "text", "text": WECOM_AI_PLACEHOLDERS[text]}]
        elif platform == "line":
            message = _get(raw, "message") or {}
            kind = str(_get(message, "type") or "")
            if kind == "sticker" and text == "[sticker]":
                keywords = _get(message, "keywords") or []
                sticker_id = str(_get(message, "stickerId") or "")
                name = str(keywords[0]) if keywords else (sticker_id or "sticker")
                return [{"type": "emoji", "name": name, "id": sticker_id}]
            if kind and kind != "text" and text == f"[{kind}]":
                return [{"type": "text", "text": LINE_PLACEHOLDERS.get(kind, f"(sent a {kind})")}]
        return None

    @staticmethod
    def _file_note(platform: str, raw, comp) -> str | None:
        """Voice and video an adapter hands over as a generic File."""
        name = str(getattr(comp, "name", "") or "")
        url = str(getattr(comp, "url", "") or "")
        if platform == "discord":
            for att in _get(raw, "attachments") or []:
                if (url and str(_get(att, "url")) == url) or str(_get(att, "filename")) == name:
                    return media_note(str(_get(att, "content_type") or ""))
        elif platform == "slack" and isinstance(raw, dict):
            for f in raw.get("files") or []:
                if isinstance(f, dict) and f.get("name") == name:
                    return media_note(str(f.get("mimetype") or ""))
        return None

    @staticmethod
    def _voice_transcript(platform: str, event, raw, components) -> str:
        """What a voice message said, where the platform transcribes it."""
        said = None
        if platform == "wecom":
            said = _get(raw, "recognition")
        elif platform == "weixin_official_account":
            said = _get(raw, "message", "recognition")
        elif platform == "weixin_oc" and not any(
                isinstance(c, Comp.Plain) for c in components):
            said = event.message_str  # the adapter's message_str is the transcript
        return str(said or "").strip()

    async def _image_segment(self, comp, platform: str, budget: list, raw=None):
        """An image as the agent can fetch it: a public URL, or the bytes.
        Telegram URLs carry the bot token, and local paths, data: URIs and
        private hosts are out of the agent's reach, so those are inlined."""
        url = str(getattr(comp, "url", "") or "")
        file = str(getattr(comp, "file", "") or "")
        b64 = None
        if file.startswith("base64://"):
            b64 = file[len("base64://"):]
        else:
            src = url or file
            if not src:
                return None
            if src.startswith("data:"):
                head, _, data = src.partition(",")
                b64 = data if head.endswith(";base64") else None
            elif (src.startswith(("http://", "https://")) and platform != "telegram"
                    and not is_private_url(src)):
                return {"type": "image", "url": src}
            else:
                if platform == "telegram":
                    b64 = await self._telegram_download(raw, src)
                if not b64:
                    try:
                        b64 = await comp.convert_to_base64()
                    except Exception as e:
                        logger.debug(f"llm_persona_gateway: could not read an image: {e}")
        if not b64:
            return {"type": "text", "text": _IMAGE_NOTE}
        try:
            cap = int(self.config.get("max_inline_image_bytes", DEFAULT_MAX_INLINE_IMAGE_BYTES))
        except (TypeError, ValueError):
            cap = DEFAULT_MAX_INLINE_IMAGE_BYTES
        if len(b64) * 3 // 4 > cap or len(b64) > budget[0]:
            return {"type": "text", "text": _IMAGE_NOTE}
        budget[0] -= len(b64)
        return {"type": "image", "b64": b64}

    @staticmethod
    async def _telegram_download(raw, url: str):
        """Fetch a Telegram file through the adapter's own bot, so the proxy
        it is configured with applies."""
        try:
            bot = _get(raw, "message").get_bot()
            data = await bot.request.retrieve(url)
            return base64.b64encode(bytes(data)).decode()
        except Exception as e:
            logger.debug(f"llm_persona_gateway: telegram download failed: {e}")
            return None

    @staticmethod
    def _raw_stickers(platform: str, raw) -> list:
        """Stickers the adapter drops."""
        out = []
        if platform == "discord":
            for st in _get(raw, "stickers") or []:
                name = str(_get(st, "name") or "sticker")
                out.append({"type": "emoji", "name": name, "id": str(_get(st, "id") or "")})
                fmt = str(_get(st, "format", "name") or _get(st, "format") or "").lower()
                url = str(_get(st, "url") or "")
                if url and "lottie" not in fmt:
                    out.append({"type": "image", "url": url, "sticker": True})
        elif platform == "lark" and _get(raw, "message_type") == "sticker":
            out.append({"type": "emoji", "name": "sticker"})
        elif platform == "dingtalk" and _get(raw, "message_type") == "video":
            out.append({"type": "text", "text": _VIDEO_NOTE})
        elif platform == "satori":
            content = str(_get(raw, "message", "content") or "")
            if "<video" in content:
                out.append({"type": "text", "text": _VIDEO_NOTE})
        return out

    def _raw_reply(self, platform: str, raw):
        """A quote the adapter left in its raw message only."""
        if platform == "discord":
            ref = _get(raw, "reference")
            if ref is None:
                return None
            resolved = _get(ref, "resolved")
            content = _get(resolved, "content")
            text = _flatten(_discord_text(content, resolved)) if content else ""
            if not text and _get(resolved, "attachments"):
                text = "(attachment)"
            return self._reply_segment(
                _get(ref, "message_id"), text, _get(resolved, "author", "id"),
                _get(resolved, "author", "display_name"))
        if platform == "kook":
            quote = _get(raw, "extra", "quote")
            if not isinstance(quote, dict):
                return None
            content = quote.get("content")
            text = _flatten(kook_segments(content)) if isinstance(content, str) else ""
            return self._reply_segment(
                quote.get("id") or quote.get("rong_id"), text,
                _get(quote, "author", "id"),
                _get(quote, "author", "nickname") or _get(quote, "author", "username"))
        if platform == "slack":
            thread, ts = _get(raw, "thread_ts"), _get(raw, "ts")
            if not thread or thread == ts:
                return None
            return self._reply_segment(thread, None, _get(raw, "parent_user_id"))
        if platform == "telegram":
            # A voice message replaces the adapter's chain, Reply included.
            quoted = _get(raw, "message", "reply_to_message")
            if quoted is None or (_get(raw, "message", "is_topic_message") and _get(
                    raw, "message", "message_thread_id") == _get(quoted, "message_id")):
                return None
            user = _get(quoted, "from_user")
            return self._reply_segment(
                _get(quoted, "message_id"),
                _get(quoted, "text") or _get(quoted, "caption"),
                _get(user, "id"), _get(user, "username") or _get(user, "full_name"))
        if platform == "line":
            quoted = _get(raw, "message", "quotedMessageId")
            return self._reply_segment(quoted) if quoted else None
        if platform == "mattermost":
            root = _get(raw, "root_id")
            return self._reply_segment(root) if root else None
        if platform == "wecom_ai_bot":
            quote = _get(raw, "message_data", "quote")
            text = _get(quote, "text", "content")
            return self._reply_segment(None, text) if text and self._quote_chars() else None
        return None

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

    @staticmethod
    def _endpoint_is_allowed(url: str, token: str) -> tuple[bool, str]:
        """Reject credential-free or cleartext forwarding beyond loopback."""
        try:
            parsed = urlsplit(url)
        except ValueError:
            return False, "agent_url must be an absolute HTTP(S) URL"
        host = (parsed.hostname or "").lower()
        if not host or parsed.scheme not in ("http", "https"):
            return False, "agent_url must be an absolute HTTP(S) URL"
        if host in ("localhost", "127.0.0.1", "::1"):
            return True, ""
        if parsed.scheme != "https":
            return False, (
                "off-host agent_url must use HTTPS (or a private tunnel "
                "terminating at a loopback URL)"
            )
        if not token:
            return False, "off-host agent_url requires a non-empty gateway_token"
        return True, ""

    @staticmethod
    def _log_http_failure(exc, status: int) -> None:
        """Report one failed agent call at a level that matches its cause.

        403 in particular must carry the agent's own words: the gateway
        answers 403 for a peer that is not on the allowlist, for an envelope
        that failed HMAC or replayed, and for a source event outside the
        freshness window. Reporting all three as "bad token" sends the
        operator to rotate a key when the real fault is a drifting clock.
        """
        detail = ""
        try:
            payload = exc.response.json()
            if isinstance(payload, dict):
                detail = str(payload.get("error") or "")
        except Exception:
            detail = ""
        if status == 403:
            logger.error(
                "llm_persona_gateway: agent refused the request (403): "
                + (detail or "check gateway_token, the peer allowlist, and "
                             "this host's clock"))
        elif status == 413:
            logger.warning(
                "llm_persona_gateway: agent rejected the body as too large "
                f"(413){': ' + detail if detail else ''} -- usually an "
                "oversized inline image")
        elif status == 429:
            logger.info(
                "llm_persona_gateway: agent at capacity (429); this turn was "
                "dropped. Expected backpressure, not a fault.")
        elif status == 400:
            logger.warning(
                "llm_persona_gateway: agent rejected the event schema (400)"
                f"{': ' + detail if detail else ''} -- this is a bug in this "
                "plugin, not a configuration problem")
        else:
            logger.warning(
                f"llm_persona_gateway: agent request failed ({status})"
                f"{': ' + detail if detail else ''}")

    @staticmethod
    def _retry_wait(response, status: int, attempt: int) -> float:
        """Seconds to wait before resending. A 429 comes from the agent's
        admission gate, which says how long it expects to stay full; retrying
        sooner just spends every attempt against the same full gate."""
        if status == 429:
            try:
                wait = float(response.headers.get("Retry-After"))
            except (TypeError, ValueError, AttributeError):
                wait = None
            if wait is not None and 0 <= wait < float("inf"):
                return wait
        return _RETRY_BACKOFFS_S[attempt]

    def _agent_url(self) -> str:
        return str(self.config.get("agent_url") or DEFAULT_AGENT_URL)

    def _timeout(self) -> float:
        return float(self.config.get("timeout_s") or DEFAULT_TIMEOUT_S)

    async def _post_to_agent(
            self, neutral_event: dict) -> tuple[bool, bool, list]:
        """POST one event; return (replied, owned, reply items).

        `owned` is the agent's answer to "is this conversation mine", which is
        NOT the same as whether it replied: a PASS, a debounce merge and a
        rhythm-gate skip are all deliberate silence in a conversation it owns.
        Falling back to `handled` keeps an older agent — one that does not send
        the field — behaving exactly as it does today.
        """
        url = self._agent_url()
        timeout = self._timeout()
        token = str(self.config.get("gateway_token") or "")
        allowed, reason = self._endpoint_is_allowed(url, token)
        if not allowed:
            logger.warning(f"llm_persona_gateway: refusing unsafe agent_url: {reason}")
            return False, False, []

        body = sdk.canonical_body(neutral_event)
        headers = sdk.signed_headers(body, token)
        signed_ts = int(headers["X-Gateway-Timestamp"]) if token else None
        # The signed timestamp above is minted ONCE and every retry resends it
        # unchanged -- that is deliberate (the agent un-burns a nonce when its
        # own write fails, precisely so a correct client can resend the same
        # bytes). The agent checks the envelope's age when a request ARRIVES,
        # before the turn runs, so only the START of each attempt has to fall
        # inside the replay window; how long the turn then takes does not
        # matter. Every attempt therefore gets the full timeout_s, and a retry
        # is sent only while it would still start inside the window.
        attempts = len(_RETRY_BACKOFFS_S) + 1
        data = None
        if self._client is None:
            self._client = httpx.AsyncClient()
        for attempt in range(attempts):
            try:
                resp = await self._client.post(
                    url, content=body, headers=headers, timeout=timeout
                )
                resp.raise_for_status()
                data = resp.json()
                break
            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                if status in _RETRYABLE_STATUSES and attempt < attempts - 1:
                    wait = self._retry_wait(e.response, status, attempt)
                    if signed_ts is None or time.time() + wait < (
                            signed_ts + _GATEWAY_REPLAY_WINDOW_S
                            - _RETRY_WINDOW_SAFETY_MARGIN_S):
                        await asyncio.sleep(wait)
                        continue
                    logger.warning(
                        f"llm_persona_gateway: not retrying ({status}): the "
                        "signed envelope would be too old for the agent by "
                        "the time the retry arrived")
                self._log_http_failure(e, status)
                return False, False, []
            except (httpx.ReadTimeout, httpx.WriteTimeout):
                # NOT httpx.TimeoutException: that also covers ConnectTimeout
                # and PoolTimeout, which happen before the request reaches the
                # agent, where the warning below would simply be false.
                logger.error(
                    "llm_persona_gateway: timed out waiting for the agent "
                    f"(timeout_s={timeout:.0f}). The agent does not check "
                    "whether the caller is still connected, so it is finishing "
                    "this turn and committing the reply, the debounce state "
                    "and the learning evidence for a message nobody will see "
                    "-- and AstrBot's own model is about to answer the same "
                    "turn in a different voice. If this recurs, raise "
                    "timeout_s or lower the agent's LLM_TIMEOUT / "
                    "LLM_MAX_RETRIES: keep LLM_TIMEOUT x (1 + LLM_MAX_RETRIES) "
                    "under timeout_s."
                )
                return False, False, []
            except Exception as e:
                logger.warning(f"llm_persona_gateway: agent request failed: {e}")
                return False, False, []
        if data is None:
            return False, False, []
        replies = data.get("replies") if isinstance(data, dict) else None
        if not isinstance(replies, list):
            return False, False, []
        handled = bool(data.get("handled"))
        return handled, bool(data.get("owned", handled)), [
            r for r in replies if isinstance(r, dict)
        ]

    # ---------- outbox: messages nobody asked for ----------

    async def _run_outbox(self) -> None:
        url = self._agent_url()
        token = str(self.config.get("gateway_token") or "")
        allowed, reason = self._endpoint_is_allowed(url, token)
        if not allowed:
            logger.warning(f"llm_persona_gateway: outbox off: {reason}")
            return
        try:
            wait_s = min(30, max(1, int(self.config.get("outbox_wait_s") or 25)))
        except (TypeError, ValueError):
            wait_s = 25
        connector = sdk.Connector(url, token, forwarder_id=await self._ensure_forwarder_id(),
                                  timeout_s=self._timeout())
        try:
            await connector.run_outbox(self._deliver, wait_s=wait_s, stop=self._outbox_stop)
        finally:
            await connector.aclose()

    async def _platform_inst(self, platform_id: str):
        """The running adapter instance, waiting a little for one that is
        still starting."""
        if self._starting_until is not None and time.monotonic() > self._starting_until:
            return self._platform_inst_now(platform_id)
        for _ in range(_PLATFORM_WAIT_S):
            inst = self._platform_inst_now(platform_id)
            if inst is not None or self._outbox_stop.is_set():
                return inst
            await asyncio.sleep(1)
        return self._platform_inst_now(platform_id)

    async def _deliver(self, delivery: dict) -> tuple[str, int]:
        """Send one outbox delivery; return (ack status, items sent)."""
        handle = str(delivery.get("reply_handle") or "")
        items = [i for i in (delivery.get("items") or []) if isinstance(i, dict)]
        try:
            # AstrBot's own parse, the one context.send_message applies.
            session = MessageSession.from_str(handle)
        except ValueError:
            return "unsupported", 0
        platform_id = session.platform_id
        if not platform_id:
            return "unsupported", 0
        message_type = str(delivery.get("message_type") or "")
        is_group = message_type == "group"
        conversation_id = str(delivery.get("conversation_id") or "")
        await self._load_handles()
        bound = self._handles.bound(handle)
        # The agent hands back whatever handle an admitted event carried, and
        # the lists below name only the conversation: the handle must be one
        # this plugin took from that very conversation.
        if bound is None or bound[1:] != (message_type, conversation_id) or (
                session.message_type != (MessageType.GROUP_MESSAGE if is_group
                                         else MessageType.FRIEND_MESSAGE)):
            logger.warning(
                f"llm_persona_gateway: outbox: {handle!r} is not an address of "
                f"{message_type} {conversation_id!r}; refused")
            return "refused", 0
        inst = await self._platform_inst(platform_id)
        if inst is None:
            logger.warning(
                f"llm_persona_gateway: outbox: no running platform {platform_id!r}")
            return "failed", 0
        try:
            platform = str(inst.meta().name)
        except Exception:
            platform = str(delivery.get("platform") or "")
        wanted = str(delivery.get("platform") or "")
        # QQ's ids may be spelled under "qq" (docs/connectors.md, Addressing).
        if platform != bound[0] or (wanted and wanted != platform
                                    and not (wanted == "qq" and platform == "aiocqhttp")):
            logger.warning(
                f"llm_persona_gateway: outbox: {platform_id!r} is {platform}, "
                f"not {wanted or bound[0]}; refused")
            return "refused", 0
        if not self._allowed(platform, is_group, conversation_id, conversation_id):
            return "refused", 0
        if not self._can_speak_first(platform, inst=inst):
            return "unsupported", 0
        if platform == "wecom" and not getattr(inst, "agent_id", None):
            # Learnt from the first message after a restart; until then the
            # adapter drops the send and still reports success.
            return "failed", 0
        temps: list = []
        chains = self._render(items, platform, is_group, conversation_id, temps, umo=handle)
        sent = 0
        try:
            for n, (chain, done) in enumerate(chains):
                if n:
                    await asyncio.sleep(random.uniform(0.8, 1.8))
                try:
                    ok = await self.context.send_message(handle, MessageChain(chain=chain))
                except Exception as e:
                    logger.warning(f"llm_persona_gateway: outbox send failed: {e}")
                    ok = False
                if not ok:
                    return ("partial", sent) if sent else ("failed", 0)
                sent = done
        finally:
            _remove_files(temps)
        return "sent", len(items)

    # ---------- outbound: neutral reply items -> AstrBot chains ----------

    @staticmethod
    def _result(event, chain, rules: Rules):
        result = event.chain_result(chain)
        # A persona's bubble is chat, not a picture of text, and on QQ
        # official not the markdown the adapter defaults to.
        for method, arg in (("use_t2i", False),) + (
                (("use_markdown", False),) if rules.plain_text else ()):
            fn = getattr(result, method, None)
            if callable(fn):
                fn(arg)
        return result

    def _forward_threshold(self, umo=None) -> int:
        """Above this many characters AstrBot turns a QQ reply into a
        merged-forward card, which no person would send."""
        try:
            conf = self.context.get_config(umo) if umo else self.context.get_config()
            value = int(conf["platform_settings"]["forward_threshold"])
        except Exception:
            value = DEFAULT_FORWARD_THRESHOLD
        return max(value, 50)

    def _render(self, items: list, platform: str, is_group: bool,
                conversation_id: str, temps: list, umo=None) -> list:
        """Reply items as the chains to send, each with how many items are
        complete once it is out: [(chain, items_done), ...]."""
        rules = rules_for(platform)
        max_chars = rules.max_chars
        if platform == "aiocqhttp":
            max_chars = self._forward_threshold(umo)
        bubbles = []
        for index, item in enumerate(items, 1):
            parts = self._item_bubbles(item, platform, rules, is_group,
                                       conversation_id, max_chars, temps)
            for n, comps in enumerate(parts, 1):
                # A split item is done only once its last part is out.
                bubbles.append((comps, index if n == len(parts) else index - 1))
        if rules.merge and bubbles:
            texts = [c.text for comps, _ in bubbles for c in comps if isinstance(c, Comp.Plain)]
            rest = [c for comps, _ in bubbles for c in comps if not isinstance(c, Comp.Plain)]
            chain = ([Comp.Plain("\n".join(texts))] if texts else []) + rest
            return [(chain, bubbles[-1][1])]
        if rules.batch:
            packed = []
            for comps, index in bubbles:
                if packed and len(packed[-1][0]) + len(comps) <= rules.batch:
                    packed[-1] = (packed[-1][0] + comps, index)
                else:
                    packed.append((list(comps), index))
            return packed
        return bubbles

    def _item_bubbles(self, item: dict, platform: str, rules: Rules, is_group: bool,
                      conversation_id: str, max_chars: int, temps: list) -> list:
        """One reply item as the messages it takes on this platform."""
        at = self._resolve_at(item.get("at_user_id"), platform) if is_group else None
        reply_id = self._resolve_reply_id(
            item.get("reply_to_message_id"), platform, conversation_id
        ) if rules.quote else None
        prefix = [Comp.Reply(id=reply_id)] if reply_id else []
        rtype = item.get("type")
        if rtype == "text":
            text = item.get("text") or ""
            # The mention and the escapes count toward the platform's limit.
            reserve = rules.reserve + self._mention_len(
                self._with_mention(at, "", platform, rules))
            kind = rules.escape if rules.escape_counts else ""
            out = []
            for n, chunk in enumerate(split_text(text, max_chars, rules.max_bytes,
                                                 kind, reserve)):
                body = escape(chunk, rules.escape)
                if n == 0:
                    out.append(prefix + self._with_mention(at, body, platform, rules))
                else:
                    out.append([Comp.Plain(body)])
            return out
        if rtype == "image":
            b64 = item.get("b64") or ""
            if not b64:
                return []
            chain = list(prefix)
            if at and rules.mention in ("at", "at_spaced"):
                chain.append(Comp.At(qq=at, name=at))
            chain.append(self._outbound_image(b64, platform, temps))
            return [chain]
        logger.warning(f"llm_persona_gateway: dropping unknown reply type {rtype!r}")
        return []

    @staticmethod
    def _mention_len(comps) -> int:
        """Characters a mention adds in front of a text. An At renders as its
        name or id with at most three more ('<@id>', '@name ')."""
        n = 0
        for comp in comps:
            if isinstance(comp, Comp.Plain):
                n += len(comp.text or "")
            elif isinstance(comp, Comp.At):
                n += len(str(comp.name or comp.qq)) + 3
        return n

    def _with_mention(self, at, body: str, platform: str, rules: Rules) -> list:
        """A text, naming `at` the way this platform renders a mention."""
        mode = rules.mention if at else "none"
        if mode == "at_spaced":
            # The adapter puts its own space after an At.
            return [Comp.At(qq=at, name=at), Comp.Plain(body)]
        if mode == "at":
            # name= matters: several send paths render a mention from At.name.
            return [Comp.At(qq=at, name=at), Comp.Plain(" " + body)]
        if mode == "slack":
            # The Slack adapter drops At; its mrkdwn mention is text.
            return [Comp.Plain(f"<@{at}> {body}")]
        if mode == "kook":
            # An At would go out as a message of its own.
            return [Comp.Plain(f"(met){at}(met) {body}")]
        if mode == "telegram":
            # The adapter writes "@" + At.name, which only a username turns
            # into a mention; a user without one is linked by id instead.
            handle = self._people.handle(platform, at)
            if handle or not at.isdigit():
                handle = handle or at
                return [Comp.At(qq=handle, name=handle), Comp.Plain(body)]
            name = self._people.name(platform, at)
            if name:
                label = escape(name, "telegram")
                return [Comp.Plain(f"[{label}](tg://user?id={at}) {body}")]
            return [Comp.Plain(body)]
        if mode == "name":
            handle = self._people.handle(platform, at)
            if handle:
                return [Comp.At(qq=at, name=handle), Comp.Plain(" " + body)]
        return [Comp.Plain(body)]

    @staticmethod
    def _outbound_image(b64: str, platform: str, temps: list):
        if platform == "kook":
            # The KOOK client uploads base64 only when it starts with "/"
            # (JPEG) and posts the error text, data and all, otherwise; a
            # file path uploads any format.
            try:
                data = base64.b64decode(b64)
                fd, path = tempfile.mkstemp(prefix="persona_", suffix=image_suffix(data))
                with os.fdopen(fd, "wb") as f:
                    f.write(data)
                temps.append(path)
                return Comp.Image.fromFileSystem(path)
            except Exception as e:
                logger.warning(f"llm_persona_gateway: could not stage an image for KOOK: {e}")
        return Comp.Image.fromBase64(b64)

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
