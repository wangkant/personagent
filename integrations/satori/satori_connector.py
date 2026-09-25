"""Satori connector for personagent (docs/connectors.md).

Satori is a chat protocol many frameworks serve: Koishi (server-satori),
Chronocat, LLOneBot, and satori-python's own server. One connection reaches
every platform the server has a login on.

satori-python's client holds the Satori side: the websocket, IDENTIFY,
heartbeat and resume, the login list, message-element parsing and the HTTP
API. integrations/sdk/personagent_connector.py holds the agent side: signing
and the outbox loop. This file maps one to the other.

    python integrations/satori/satori_connector.py [--config FILE]

Settings come from the environment or from a dotenv-style file (default: .env
next to this script); the environment wins. .env.example lists them.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import binascii
import hashlib
import ipaddress
import json
import logging
import os
import random
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Optional
from urllib.parse import urlsplit

import httpx

try:
    import personagent_connector as sdk
except ImportError:  # running from a checkout: the SDK sits in integrations/sdk
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sdk"))
    import personagent_connector as sdk

logger = logging.getLogger("satori_connector")

DEFAULT_ENDPOINT = "http://127.0.0.1:5140/satori"
DEFAULT_AGENT_URL = "http://127.0.0.1:8080/webhook/gateway"
DEFAULT_CONFIG = Path(__file__).resolve().parent / ".env"

KNOWN_KEYS = (
    "SATORI_ENDPOINT", "SATORI_TOKEN", "PERSONAGENT_URL", "GATEWAY_TOKEN",
    "SATORI_FORWARDER_ID", "SATORI_PLATFORMS", "SATORI_PLATFORM_NAMES",
    "SATORI_GROUPS", "SATORI_DM_USERS", "SATORI_OUTBOX", "SATORI_TIMEOUT_S",
    "SATORI_INLINE_IMAGES", "SATORI_LOG_LEVEL",
)

# The agent refuses a request body over 8 MB, and base64 adds a third.
MAX_IMAGE_BYTES = 4_000_000
MAX_INLINE_IMAGES = 4
DOWNLOAD_TIMEOUT_S = 20.0
MAX_HANDLE_LEN = 512
DIRECT_CHANNEL = 1  # Satori Channel.Type.DIRECT
# An adapter that stamps seconds where Satori says milliseconds reaches us as a
# January 1970 date; below this it is scaled back, and never sent as stale.
_MIN_PLAUSIBLE_TS = 1_000_000_000
_MEDIA_NOTES = {"audio": "(sent a voice message)", "video": "(sent a video)"}
# personagent reads "qq" as QQ numbers; Koishi's "qq" login is the official
# bot API, whose ids are openids, so it gets a name of its own.
DEFAULT_PLATFORM_NAMES = {"qq": "qqbot"}
_SKIPPED_TAGS = frozenset({"author", "button"})


def _csv(value: Optional[str]) -> list[str]:
    return [p.strip() for p in str(value or "").replace("\n", ",").split(",") if p.strip()]


def _flag(value: Optional[str], default: bool) -> bool:
    if value is None or not str(value).strip():
        return default
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def _platform_name(raw: str) -> str:
    # The contract's platform names are lowercase and colon-free.
    return str(raw or "satori").strip().lower().replace(":", "-") or "satori"


@dataclass
class Config:
    endpoint: str = DEFAULT_ENDPOINT
    satori_token: str = field(default="", repr=False)
    agent_url: str = DEFAULT_AGENT_URL
    gateway_token: str = field(default="", repr=False)
    forwarder_id: str = ""
    platforms: frozenset = frozenset()
    platform_names: dict = field(default_factory=lambda: dict(DEFAULT_PLATFORM_NAMES))
    groups: frozenset = frozenset()
    dm_users: frozenset = frozenset()
    outbox: bool = True
    timeout_s: float = 180.0
    inline_images: bool = False
    reply_gap_s: tuple = (0.8, 1.8)

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> "Config":
        endpoint = (env.get("SATORI_ENDPOINT") or DEFAULT_ENDPOINT).strip()
        names = dict(DEFAULT_PLATFORM_NAMES)
        for pair in _csv(env.get("SATORI_PLATFORM_NAMES")):
            raw, sep, name = pair.partition("=")
            if sep and raw.strip() and name.strip():
                names[raw.strip().lower()] = _platform_name(name)
        forwarder = (env.get("SATORI_FORWARDER_ID") or "").strip() or (
            "satori-" + hashlib.sha256(endpoint.encode("utf-8")).hexdigest()[:8])
        try:
            timeout = float(env.get("SATORI_TIMEOUT_S") or 180)
        except ValueError:
            timeout = 180.0
        return cls(
            endpoint=endpoint,
            satori_token=(env.get("SATORI_TOKEN") or "").strip(),
            agent_url=(env.get("PERSONAGENT_URL") or DEFAULT_AGENT_URL).strip(),
            gateway_token=(env.get("GATEWAY_TOKEN") or "").strip(),
            forwarder_id=forwarder,
            platforms=frozenset(p.lower() for p in _csv(env.get("SATORI_PLATFORMS"))),
            platform_names=names,
            groups=frozenset(_csv(env.get("SATORI_GROUPS"))),
            dm_users=frozenset(_csv(env.get("SATORI_DM_USERS"))),
            outbox=_flag(env.get("SATORI_OUTBOX"), True),
            timeout_s=max(timeout, 1.0),
            inline_images=_flag(env.get("SATORI_INLINE_IMAGES"), False),
        )

    def websocket_kwargs(self) -> dict:
        """Arguments for satori-python's WebsocketsInfo, from one URL."""
        parts = urlsplit(self.endpoint)
        if parts.scheme not in ("http", "https", "ws", "wss") or not parts.hostname:
            raise ValueError("SATORI_ENDPOINT must look like http://host:port/path")
        secure = parts.scheme in ("https", "wss")
        path = parts.path.rstrip("/")
        if path.endswith("/v1"):  # WebsocketsInfo appends /v1 itself
            path = path[:-3]
        host = parts.hostname
        if ":" in host:
            host = f"[{host}]"
        return {"host": host, "port": parts.port or (443 if secure else 80), "path": path,
                "secure": secure, "token": self.satori_token or None}

    @property
    def satori_host(self) -> str:
        return (urlsplit(self.endpoint).hostname or "").lower()


def load_env(path: Optional[str] = None, environ: Optional[Mapping[str, str]] = None) -> dict:
    """The file's settings with the environment's on top."""
    values: dict = {}
    file = Path(path) if path else DEFAULT_CONFIG
    if path and not file.is_file():
        raise FileNotFoundError(f"config file not found: {file}")
    if file.is_file():
        from dotenv import dotenv_values
        values = {k: v for k, v in dotenv_values(file).items() if v is not None}
    environ = os.environ if environ is None else environ
    values.update({k: v for k, v in environ.items() if k in KNOWN_KEYS})
    return values


# ---------- message elements (duck-typed on satori-python's Element) ----------

def _tag(el: Any) -> str:
    return str(getattr(el, "tag", "") or "").lower()


def _attr(el: Any, name: str) -> str:
    value = getattr(el, name, None)
    if value is None:
        attrs = getattr(el, "_attrs", None)
        if isinstance(attrs, dict):
            value = attrs.get(name)
    return "" if value is None else str(value)


def _children(el: Any) -> list:
    return list(getattr(el, "children", None) or [])


def _text_of(segments: list, *, media: bool = False) -> str:
    out = []
    for seg in segments:
        kind = seg.get("type")
        if kind == "text":
            out.append(seg.get("text", ""))
        elif kind == "mention":
            out.append("@" + (seg.get("name") or seg.get("user_id") or ""))
        elif media and kind == "image":
            out.append("[image]")
    return "".join(out).strip()


class _Walker:
    """Satori message elements to neutral segments, in order."""

    def __init__(self, self_id: str, self_name: str = ""):
        self.self_id = self_id
        self.self_name = self_name.lower().lstrip("@")
        self.segments: list[dict] = []
        self.quote: Optional[dict] = None
        self.at_me = False

    def text(self, value: str) -> None:
        if not value:
            return
        if self.segments and self.segments[-1]["type"] == "text":
            self.segments[-1]["text"] += value
        else:
            self.segments.append({"type": "text", "text": value})

    def newline(self) -> None:
        last = self.segments[-1] if self.segments else None
        if last and last["type"] == "text" and not last["text"].endswith("\n"):
            self.text("\n")

    def walk(self, elements: Iterable) -> "_Walker":
        for el in elements or []:
            tag = _tag(el)
            if tag == "text":
                self.text(_attr(el, "text"))
            elif tag == "at":
                self.at(el)
            elif tag == "sharp":
                self.text("#" + (_attr(el, "name") or _attr(el, "id")))
            elif tag in ("a", "link"):
                label = _text_of(_Walker(self.self_id).walk(_children(el)).segments)
                href = _attr(el, "href")
                self.text(f"{label} ({href})" if label and href and label != href
                          else label or href)
            elif tag in ("img", "image"):
                self.segments.append({"type": "image", "src": _attr(el, "src")})
            elif tag in ("emoji", "face"):
                # <face> is how Koishi's QQ adapters send a built-in QQ face.
                self.segments.append({"type": "emoji", "name": _attr(el, "name"),
                                      "id": _attr(el, "id")})
            elif tag in _MEDIA_NOTES:
                self.text(_MEDIA_NOTES[tag])
            elif tag == "file":
                title = _attr(el, "title")
                self.text(f"(sent a file: {title})" if title else "(sent a file)")
            elif tag == "quote":
                if self.quote is None:
                    self.quote = self.quote_of(el)
            elif tag == "br":
                self.text("\n")
            elif tag == "p":
                self.newline()
                self.walk(_children(el))
                self.newline()
            elif tag in _SKIPPED_TAGS:
                continue
            else:
                # Styling (<b>, <spl>, <message>, ...) and unknown tags: keep
                # what they wrap.
                self.walk(_children(el))
        return self

    def at(self, el: Any) -> None:
        kind = _attr(el, "type")
        if kind in ("all", "here"):
            self.text("@" + kind)
            return
        uid, name = _attr(el, "id"), _attr(el, "name")
        if not uid and _attr(el, "role"):
            self.text("@" + (name or _attr(el, "role")))
            return
        if not uid and name and self.self_name and name.lower().lstrip("@") == self.self_name:
            uid = self.self_id
        if not uid:
            if name:
                self.text("@" + name)
            return
        if uid == self.self_id:
            self.at_me = True
        self.segments.append({"type": "mention", "user_id": uid, "name": name})

    def quote_of(self, el: Any) -> dict:
        seg: dict = {"type": "reply"}
        if _attr(el, "id"):
            seg["message_id"] = _attr(el, "id")
        body, member_name = [], ""
        for child in _children(el):
            tag = _tag(child)
            # The spec names the quoted sender <author>; Koishi encodes the
            # quoted message's <user> and <member> resources instead.
            if tag in ("author", "user"):
                seg["sender_id"] = _attr(child, "id")
                seg["sender_name"] = _attr(child, "nick") or _attr(child, "name")
            elif tag == "member":
                member_name = _attr(child, "nick") or _attr(child, "name")
            elif tag not in ("channel", "quote"):
                body.append(child)
        if member_name:
            seg["sender_name"] = member_name
        text = _text_of(_Walker(self.self_id).walk(body).segments, media=True)
        if text:
            seg["text"] = text
        return {k: v for k, v in seg.items() if v != ""}

    def finish(self) -> list[dict]:
        segments = [s for s in self.segments if s["type"] != "text" or s["text"].strip()]
        if segments and segments[-1]["type"] == "text":
            segments[-1]["text"] = segments[-1]["text"].rstrip("\n")
        return segments


def _unix_seconds(value: Any) -> Optional[int]:
    if isinstance(value, datetime):
        seconds = value.timestamp()
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        seconds = value / 1000 if value > 10**11 else value
    else:
        return None
    if 0 < seconds < _MIN_PLAUSIBLE_TS:
        seconds *= 1000  # seconds read as milliseconds: undo the division
    if seconds < _MIN_PLAUSIBLE_TS or seconds > time.time() + 86_400:
        return None
    return int(seconds)


def _public_host(host: str) -> bool:
    host = host.lower().strip("[]")
    if not host or host == "localhost" or host.endswith(".localhost"):
        return False
    try:
        return ipaddress.ip_address(host).is_global
    except ValueError:
        return "." in host  # a single-label name only resolves on a private network


def encode_handle(**parts: str) -> str:
    return json.dumps({k: v for k, v in parts.items() if v}, sort_keys=True,
                      separators=(",", ":"), ensure_ascii=False)


def decode_handle(handle: Any) -> Optional[dict]:
    try:
        parts = json.loads(handle) if isinstance(handle, str) else None
    except ValueError:
        return None
    if not isinstance(parts, dict):
        return None
    if not all(isinstance(parts.get(k), str) and parts.get(k)
               for k in ("platform", "self_id", "channel_id", "type")):
        return None
    return parts


class SatoriBridge:
    """Satori events in, neutral events out, and the way back.

    ``lib`` is the satori package (its element classes and MessageObject);
    ``accounts`` returns the live satori-python Accounts. Both are injected so
    tests run without satori-python or a server."""

    def __init__(self, config: Config, connector: "sdk.Connector", *,
                 accounts: Callable[[], Iterable], lib: Any,
                 sleep: Callable[[float], Any] = asyncio.sleep):
        self.config = config
        self.connector = connector
        self.accounts = accounts
        self.lib = lib
        self._sleep = sleep

    def platform_name(self, raw_platform: str) -> str:
        raw = str(raw_platform or "").lower()
        return self.config.platform_names.get(raw) or _platform_name(raw)

    def admit(self, raw_platform: str, *, is_group: bool, channel_id: str = "",
              guild_id: str = "", user_id: str = "") -> Optional[bool]:
        """None when this conversation is not ours to forward; otherwise the
        event's ``prefiltered`` flag."""
        names = {str(raw_platform or "").lower(), self.platform_name(raw_platform)}
        if self.config.platforms and not names & self.config.platforms:
            return None
        allow = self.config.groups if is_group else self.config.dm_users
        if "*" in allow:
            return False  # forward everything; the agent's own lists decide
        for ident in ((channel_id, guild_id) if is_group else (user_id,)):
            if ident and (ident in allow or any(f"{n}:{ident}" in allow for n in names)):
                return True
        return None

    # ---------- inbound ----------

    async def build_event(self, account: Any, event: Any) -> Optional[dict]:
        message = getattr(event, "message", None)
        login = getattr(event, "login", None)
        channel = getattr(event, "channel", None) or getattr(message, "channel", None)
        user = getattr(event, "user", None) or getattr(message, "user", None)
        if message is None or channel is None or user is None or login is None:
            return None
        raw_platform = str(getattr(login, "platform", "") or getattr(account, "platform", "")
                           or "satori")
        login_user = getattr(login, "user", None)
        self_id = str(getattr(login_user, "id", "") or getattr(account, "self_id", ""))
        user_id = str(getattr(user, "id", "") or "")
        if not user_id or user_id == self_id:
            return None
        guild = getattr(event, "guild", None) or getattr(message, "guild", None)
        guild_id = str(getattr(guild, "id", "") or "")
        channel_id = str(getattr(channel, "id", "") or "")
        # Satori marks a DM with channel type DIRECT; an implementation that
        # leaves the type out still sends DMs without a guild.
        is_group = bool(guild_id) and _channel_type(channel) != DIRECT_CHANNEL
        prefiltered = self.admit(raw_platform, is_group=is_group, channel_id=channel_id,
                                 guild_id=guild_id, user_id=user_id)
        if prefiltered is None:
            return None
        message_id = str(getattr(message, "id", "") or "")
        timestamp = (_unix_seconds(getattr(message, "created_at", None))
                     or _unix_seconds(getattr(event, "timestamp", None)))
        if not message_id or timestamp is None:
            logger.warning("dropping a %s message without an id or a usable timestamp",
                           raw_platform)
            return None

        walker = _Walker(self_id, str(getattr(login_user, "name", "") or ""))
        walker.walk(getattr(message, "message", None) or [])
        quote = self._merge_quote(walker.quote, self._raw_quote(message))
        segments = walker.finish()
        if quote:
            segments.insert(0, quote)
        segments = await self._resolve_images(account, segments)
        is_at_me = walker.at_me or bool(quote and quote.get("sender_id") == self_id)

        member = getattr(event, "member", None)
        sender_name = str(getattr(member, "nick", "") or getattr(user, "nick", "")
                          or getattr(user, "name", "") or user_id)
        name = self.platform_name(raw_platform)
        neutral = {
            "platform": name,
            "message_type": "group" if is_group else "private",
            "conversation_id": channel_id if is_group else user_id,
            "user_id": user_id,
            "sender_name": sender_name,
            "self_id": self_id,
            "message_id": message_id,
            "source_timestamp": timestamp,
            "is_at_me": is_at_me,
            "raw_text": _text_of([s for s in segments if s["type"] != "reply"]),
            "segments": segments,
            "prefiltered": prefiltered,
            "caps": ["quote_text"],
        }
        if self.config.outbox:
            handle = encode_handle(platform=raw_platform, self_id=self_id,
                                   channel_id=channel_id,
                                   type="group" if is_group else "private",
                                   guild_id=guild_id if is_group else "",
                                   user_id="" if is_group else user_id)
            if len(handle) <= MAX_HANDLE_LEN:
                neutral["reply_handle"] = handle
                neutral["caps"] = ["outbox", "quote_text"]
        return neutral

    def _raw_quote(self, message: Any) -> Optional[dict]:
        """Satori's message.quote, which satori-python keeps only in the raw
        payload. Koishi reports quotes (and so replies to the bot) this way."""
        raw = getattr(message, "_raw_data", None)
        quote = raw.get("quote") if isinstance(raw, dict) else None
        if not isinstance(quote, dict):
            return None
        seg: dict = {"type": "reply"}
        if quote.get("id"):
            seg["message_id"] = str(quote["id"])
        user = quote.get("user") if isinstance(quote.get("user"), dict) else {}
        member = quote.get("member") if isinstance(quote.get("member"), dict) else {}
        if user.get("id"):
            seg["sender_id"] = str(user["id"])
        name = member.get("nick") or user.get("nick") or user.get("name")
        if name:
            seg["sender_name"] = str(name)
        content = quote.get("content")
        if content and isinstance(content, str):
            try:
                parsed = self.lib.MessageObject.parse({"id": seg.get("message_id", ""),
                                                       "content": content})
                text = _text_of(_Walker("").walk(parsed.message).segments, media=True)
            except Exception:
                logger.debug("could not parse quoted content", exc_info=True)
                text = ""
            if text:
                seg["text"] = text
        return seg

    @staticmethod
    def _merge_quote(element: Optional[dict], raw: Optional[dict]) -> Optional[dict]:
        if element is None or raw is None:
            return element or raw
        if element.get("message_id") and raw.get("message_id") \
                and element["message_id"] != raw["message_id"]:
            return element
        return {**raw, **element}

    def _image_route(self, account: Any, src: str) -> tuple[str, str]:
        """How an inbound image reaches the agent: ("b64", data),
        ("download", src), ("url", src), or ("", "") when it cannot."""
        if src.startswith("data:"):
            header, _, data = src.partition(",")
            return ("b64", data) if ";base64" in header and data else ("", "")
        if src.startswith("base64://"):
            return ("b64", src[len("base64://"):])
        if src.startswith("internal:"):
            return ("download", src)
        if any(p and src.startswith(p) for p in getattr(account, "proxy_urls", None) or []):
            return ("download", src)
        parts = urlsplit(src)
        if parts.scheme not in ("http", "https"):
            return ("", "")
        host = (parts.hostname or "").lower()
        satori_host = self.config.satori_host
        if host and (host == satori_host or (_loopback(host) and _loopback(satori_host))):
            return ("download", src)
        # The agent fetches URLs through an SSRF guard that refuses private
        # addresses, and this process must not fetch them for it either.
        if not _public_host(host):
            return ("", "")
        return ("download", src) if self.config.inline_images else ("url", src)

    async def _resolve_images(self, account: Any, segments: list) -> list:
        out, downloads = [], 0
        for seg in segments:
            if seg.get("type") != "image":
                out.append(seg)
                continue
            route, value = self._image_route(account, seg.get("src") or "")
            if route == "download" and downloads < MAX_INLINE_IMAGES:
                downloads += 1
                route, value = ("b64", await self._download(account, value) or "")
            if route == "b64" and value:
                out.append({"type": "image", "b64": value})
            elif route == "url":
                out.append({"type": "image", "url": value})
            else:
                out.append({"type": "text", "text": "(sent an image)"})
        merged: list = []
        for seg in out:
            if seg["type"] == "text" and merged and merged[-1]["type"] == "text":
                merged[-1] = {"type": "text", "text": merged[-1]["text"] + seg["text"]}
            else:
                merged.append(seg)
        return merged

    async def _download(self, account: Any, src: str) -> Optional[str]:
        try:
            data = await asyncio.wait_for(account.protocol.download(src), DOWNLOAD_TIMEOUT_S)
        except Exception as exc:
            logger.warning("could not fetch an image from the Satori server: %s", exc)
            return None
        if not data or len(data) > MAX_IMAGE_BYTES:
            logger.info("skipping an image of %d bytes", len(data or b""))
            return None
        return base64.b64encode(data).decode("ascii")

    async def on_message(self, account: Any, event: Any) -> None:
        """satori-python's message-created callback."""
        try:
            neutral = await self.build_event(account, event)
        except Exception:
            logger.exception("could not map a Satori message")
            return
        if neutral is None:
            return
        answer = await self._post(neutral)
        if not answer:
            return
        replies = [r for r in answer.get("replies") or [] if isinstance(r, dict)]
        channel = getattr(event, "channel", None) or getattr(event.message, "channel", None)
        # The referrer lets passive-reply platforms (the official QQ bot API)
        # accept an answer; satori-python's own send() passes it the same way.
        await self.send_items(account, str(channel.id), replies, neutral["platform"],
                              neutral["message_type"] == "group",
                              referrer=getattr(event, "referrer", None))

    async def _post(self, neutral: dict) -> Optional[dict]:
        for attempt in range(2):
            try:
                answer = await self.connector.send_event(neutral)
                return answer if isinstance(answer, dict) else None
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                if status == 429 and attempt == 0:
                    await self._sleep(_retry_after(exc.response))
                    continue
                logger.warning("agent refused the event (%s): %s", status,
                               _agent_error(exc.response) or "no detail")
                if status == 403:
                    logger.warning("403: check GATEWAY_TOKEN, the agent's peer allowlist "
                                   "and this host's clock")
                return None
            except (httpx.ReadTimeout, httpx.WriteTimeout):
                logger.error(
                    "timed out waiting for the agent (SATORI_TIMEOUT_S=%.0f). It still "
                    "finishes the turn, so that reply is lost; keep LLM_TIMEOUT x "
                    "(1 + LLM_MAX_RETRIES) under SATORI_TIMEOUT_S", self.config.timeout_s)
                return None
            except Exception as exc:
                logger.warning("agent request failed: %s", exc)
                return None
        return None

    # ---------- outbound ----------

    def render(self, item: dict, platform_name: str, is_group: bool) -> list:
        """One neutral reply item as Satori elements: at, img, text."""
        lib = self.lib
        head = []
        target = _mention_target(item.get("at_user_id"), platform_name) if is_group else None
        if target:
            head = [lib.At(id=target)]
        kind = item.get("type")
        if kind == "text":
            text = str(item.get("text") or "")
            return head + [lib.Text((" " if head else "") + text)] if text else []
        if kind == "image":
            image = self._image_element(str(item.get("b64") or ""))
            return head + [image] if image is not None else []
        logger.warning("dropping a reply item of unknown type %r", kind)
        return []

    def _image_element(self, b64: str) -> Any:
        if not b64:
            return None
        try:
            data = base64.b64decode(b64, validate=True)
        except (binascii.Error, ValueError):
            logger.warning("dropping a reply image that is not valid base64")
            return None
        try:
            return self.lib.Image.of(raw=data)
        except ValueError:  # satori-python could not tell the format
            return self.lib.Image.of(raw=data, mime="image/png")

    async def send_items(self, account: Any, channel_id: str, items: list,
                         platform_name: str, is_group: bool, *,
                         referrer: Optional[dict] = None) -> int:
        """Send items in order, each as its own message; stop at the first
        failure. Returns how many items are done (an empty one counts)."""
        done, sent_any = 0, False
        for item in items:
            elements = self.render(item, platform_name, is_group)
            if elements:
                if sent_any:
                    await self._sleep(random.uniform(*self.config.reply_gap_s))
                try:
                    await account.protocol.send_message(channel_id, elements, referrer)
                except Exception as exc:
                    logger.warning("sending to %s channel %s failed: %s",
                                   platform_name, channel_id, exc)
                    break
                sent_any = True
            done += 1
        return done

    def find_account(self, raw_platform: str, self_id: str) -> Any:
        for account in self.accounts() or []:
            if str(account.platform) == raw_platform and str(account.self_id) == self_id:
                connected = getattr(account, "connected", None)
                if connected is None or connected.is_set():
                    return account
        return None

    async def deliver(self, delivery: dict) -> "sdk.DeliveryResult":
        """The outbox ``deliver``: send one delivery through its reply_handle."""
        handle = decode_handle(delivery.get("reply_handle"))
        if handle is None:
            return "unsupported", 0
        is_group = handle["type"] == "group"
        if self.admit(handle["platform"], is_group=is_group, channel_id=handle["channel_id"],
                      guild_id=handle.get("guild_id", ""),
                      user_id=handle.get("user_id", "")) is None:
            return "refused", 0
        account = self.find_account(handle["platform"], handle["self_id"])
        if account is None:
            logger.warning("no online Satori login %s/%s for delivery %s",
                           handle["platform"], handle["self_id"], delivery.get("delivery_id"))
            return "failed", 0
        items = [i for i in delivery.get("items") or [] if isinstance(i, dict)]
        done = await self.send_items(account, handle["channel_id"], items,
                                     self.platform_name(handle["platform"]), is_group)
        if done == len(items):
            return "sent", done
        return ("partial" if done else "failed"), done


def _channel_type(channel: Any) -> Optional[int]:
    # satori-python defaults a missing type to TEXT, so ask the raw payload.
    raw = getattr(channel, "_raw_data", None)
    value = raw.get("type") if isinstance(raw, dict) and raw else getattr(channel, "type", None)
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _mention_target(at_user_id: Any, platform_name: str) -> Optional[str]:
    """The raw id in a "<platform>:<id>" mention; another platform's id cannot
    be mentioned here."""
    target = str(at_user_id or "")
    prefix = platform_name + ":"
    if not target.startswith(prefix):
        return None
    return target[len(prefix):] or None


def _agent_error(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except Exception:
        return ""
    return str(payload.get("error") or "") if isinstance(payload, dict) else ""


def _retry_after(response: httpx.Response) -> float:
    try:
        return min(max(float(response.headers.get("Retry-After") or 3), 0.0), 10.0)
    except ValueError:
        return 3.0


def redacted_info(base: type) -> type:
    """satori-python's WebsocketsInfo with a repr that leaves the token out:
    the library logs the whole config when the server reports no login."""
    class WebsocketsInfo(base):
        def __repr__(self) -> str:
            return (f"WebsocketsInfo(host={self.host!r}, port={self.port!r}, "
                    f"path={self.path!r}, secure={self.secure!r})")
    return WebsocketsInfo


async def serve(config: Config) -> None:
    import satori
    from satori.client import App, WebsocketsInfo
    from satori.client.network.websocket import WsNetwork

    connector = sdk.Connector(config.agent_url, config.gateway_token,
                              forwarder_id=config.forwarder_id, timeout_s=config.timeout_s)
    info = config.websocket_kwargs()
    if info["token"] and not info["secure"] and not _loopback(config.satori_host):
        logger.warning("SATORI_TOKEN goes to %s in clear text; use https or a tunnel",
                       config.satori_host)
    safe_info = redacted_info(WebsocketsInfo)
    # App picks the network by the config's exact class, not a subclass.
    App.register_config(safe_info, WsNetwork)
    app = App(safe_info(**info))
    bridge = SatoriBridge(config, connector, accounts=lambda: list(app.accounts.values()),
                          lib=satori)
    app.register_on(satori.EventType.MESSAGE_CREATED)(bridge.on_message)
    stop = asyncio.Event()
    online = asyncio.Event()

    async def on_status(account: Any, status: Any) -> None:
        # The platform name here is the one the allowlists and settings use.
        logger.info("Satori login %s:%s is %s", account.platform, account.self_id,
                    getattr(status, "name", status))
        if int(status) == 1:  # LoginStatus.ONLINE
            online.set()

    app.lifecycle(on_status)

    async def run_outbox() -> None:
        # Pulling before any login is online would hand deliveries to a
        # connector that can only fail them; until the first pull the agent
        # treats this connector as gone and queues nothing.
        await online.wait()
        await connector.run_outbox(bridge.deliver, stop=stop)

    outbox = asyncio.create_task(run_outbox()) if config.outbox else None
    logger.info("forwarding Satori at %s to %s as %s", config.endpoint, config.agent_url,
                config.forwarder_id)
    try:
        await app.run_async()
    finally:
        stop.set()
        if outbox is not None:
            try:
                await asyncio.wait_for(outbox, 5)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                pass
        await connector.aclose()


def _loopback(host: str) -> bool:
    return host in ("localhost", "127.0.0.1", "::1")


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description="Forward a Satori server to personagent.")
    parser.add_argument("--config", help="dotenv-style settings file "
                                         "(default: .env next to this script)")
    args = parser.parse_args(argv)
    try:
        env = load_env(args.config)
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 2
    level = getattr(logging, str(env.get("SATORI_LOG_LEVEL") or "INFO").upper(), None)
    logging.basicConfig(level=level if isinstance(level, int) else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    config = Config.from_env(env)
    if not sdk.endpoint_allowed(config.agent_url, config.gateway_token):
        print("PERSONAGENT_URL must be loopback, or HTTPS with GATEWAY_TOKEN set",
              file=sys.stderr)
        return 2
    try:
        config.websocket_kwargs()
        import satori.client  # noqa: F401
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2
    except ImportError:
        print("satori-python is not installed: "
              "pip install -r integrations/satori/requirements.txt", file=sys.stderr)
        return 2
    asyncio.run(serve(config))
    return 0


if __name__ == "__main__":
    sys.exit(main())
