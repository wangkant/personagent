"""Matrix connector for personagent (docs/connectors.md).

The bot logs in to a Matrix homeserver as an ordinary user. Every room
message it can read becomes a neutral event for the agent, and the agent's
replies go back into the room. Through mautrix bridges the same rooms reach
WhatsApp, Signal, Messenger, Instagram, Google Messages and more; see
README.md.

matrix-nio holds the Matrix side: login, sync, end-to-end encryption and the
media repository. integrations/sdk/personagent_connector.py holds the agent
side: signing and the outbox loop. This file maps one to the other, and
touches the client only through a few duck-typed calls so the tests can run
without matrix-nio.

    python integrations/matrix/matrix_connector.py [--config FILE]

Settings come from the environment or from a dotenv-style file (default: .env
next to this script); the environment wins. .env.example lists them.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import binascii
import collections
import hashlib
import html
import io
import json
import logging
import os
import random
import re
import sys
import time
from dataclasses import dataclass, field
from fnmatch import fnmatchcase
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Optional
from urllib.parse import unquote, urlsplit

import httpx

try:
    import personagent_connector as sdk
except ImportError:  # running from a checkout: the SDK sits in integrations/sdk
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sdk"))
    import personagent_connector as sdk

logger = logging.getLogger("matrix_connector")

PLATFORM = "matrix"
DEFAULT_AGENT_URL = "http://127.0.0.1:8080/webhook/gateway"
DEFAULT_CONFIG = Path(__file__).resolve().parent / ".env"
# `runtime/` is gitignored at any depth, so a checkout never commits keys.
DEFAULT_STORE = Path(__file__).resolve().parent / "runtime"

KNOWN_KEYS = (
    "MATRIX_HOMESERVER", "MATRIX_USER_ID", "MATRIX_ACCESS_TOKEN", "MATRIX_PASSWORD",
    "MATRIX_DEVICE_ID", "MATRIX_DEVICE_NAME", "PERSONAGENT_URL", "GATEWAY_TOKEN",
    "MATRIX_FORWARDER_ID", "MATRIX_ROOMS", "MATRIX_DM_USERS", "MATRIX_INVITE_FROM",
    "MATRIX_IGNORE_USERS", "MATRIX_E2EE", "MATRIX_STORE_PATH", "MATRIX_OUTBOX",
    "MATRIX_READ_RECEIPTS", "MATRIX_TIMEOUT_S", "MATRIX_MAX_EVENT_AGE_S",
    "MATRIX_LOG_LEVEL",
)

# The agent refuses a request body over 8 MB, and base64 adds a third.
MAX_IMAGE_BYTES = 4_000_000
DOWNLOAD_TIMEOUT_S = 30.0
TYPING_TIMEOUT_MS = 30_000
TYPING_REFRESH_S = 20.0
MAX_CONCURRENT_TURNS = 16
RECENT_EVENTS = 1024
HTML_FORMAT = "org.matrix.custom.html"
_BLOCK_TAGS = frozenset({"p", "div", "li", "blockquote", "pre", "tr", "ul", "ol", "table",
                         "h1", "h2", "h3", "h4", "h5", "h6"})
_FALLBACK_SENDER = re.compile(r"^\*?\s*<[^>]*>\s?")
_MEDIA_NOTES = {"m.image": "(sent an image)", "m.video": "(sent a video)",
                "m.location": "(shared a location)"}


def _csv(value: Optional[str]) -> tuple[str, ...]:
    return tuple(p.strip() for p in str(value or "").replace("\n", ",").split(",")
                 if p.strip())


def _flag(value: Optional[str], default: bool) -> bool:
    if value is None or not str(value).strip():
        return default
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def _number(values: Mapping[str, str], key: str, default: float, minimum: float) -> float:
    raw = str(values.get(key) or "").strip()
    if not raw:
        return default
    try:
        return max(float(raw), minimum)
    except ValueError:
        raise ValueError(f"{key} must be a number, got {raw!r}") from None


def matches(patterns: Iterable[str], value: str) -> bool:
    """Glob match against an allowlist: `*` is everyone, `@*:example.org` a
    whole server. Matrix ids are case-sensitive, so the match is too."""
    return bool(value) and any(fnmatchcase(value, p) for p in patterns)


def default_forwarder_id(user_id: str) -> str:
    # Stable per bot account, so the agent's outbox survives a restart.
    return "matrix-" + hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:12]


@dataclass
class Settings:
    homeserver: str
    user_id: str = ""
    access_token: str = field(default="", repr=False)
    password: str = field(default="", repr=False)
    device_id: str = ""
    device_name: str = "personagent"
    agent_url: str = DEFAULT_AGENT_URL
    gateway_token: str = field(default="", repr=False)
    forwarder_id: str = ""
    rooms: tuple[str, ...] = ()
    dm_users: tuple[str, ...] = ()
    invite_from: tuple[str, ...] = ()
    ignore_users: tuple[str, ...] = ()
    e2ee: bool = False
    store_path: Path = DEFAULT_STORE
    outbox: bool = True
    read_receipts: bool = True
    # The agent's own ceiling is LLM_TIMEOUT x (1 + LLM_MAX_RETRIES) plus a
    # debounce: 360 s and change with its defaults.
    timeout_s: float = 420.0
    max_event_age_s: float = 300.0
    log_level: str = "INFO"

    @classmethod
    def from_env(cls, values: Mapping[str, str]) -> "Settings":
        get = lambda key, default="": str(values.get(key) or default).strip()  # noqa: E731
        homeserver = get("MATRIX_HOMESERVER")
        if not homeserver:
            raise ValueError("MATRIX_HOMESERVER is required")
        if "://" not in homeserver:
            homeserver = "https://" + homeserver
        if urlsplit(homeserver).scheme not in ("http", "https"):
            raise ValueError(f"MATRIX_HOMESERVER must be an http(s) URL, got {homeserver!r}")
        settings = cls(
            homeserver=homeserver.rstrip("/"),
            user_id=get("MATRIX_USER_ID"),
            access_token=get("MATRIX_ACCESS_TOKEN"),
            password=str(values.get("MATRIX_PASSWORD") or ""),
            device_id=get("MATRIX_DEVICE_ID"),
            device_name=get("MATRIX_DEVICE_NAME", "personagent"),
            agent_url=get("PERSONAGENT_URL", DEFAULT_AGENT_URL),
            gateway_token=get("GATEWAY_TOKEN"),
            forwarder_id=get("MATRIX_FORWARDER_ID"),
            rooms=_csv(values.get("MATRIX_ROOMS")),
            dm_users=_csv(values.get("MATRIX_DM_USERS")),
            invite_from=_csv(values.get("MATRIX_INVITE_FROM")),
            ignore_users=_csv(values.get("MATRIX_IGNORE_USERS")),
            e2ee=_flag(values.get("MATRIX_E2EE"), False),
            store_path=Path(get("MATRIX_STORE_PATH") or DEFAULT_STORE),
            outbox=_flag(values.get("MATRIX_OUTBOX"), True),
            read_receipts=_flag(values.get("MATRIX_READ_RECEIPTS"), True),
            timeout_s=_number(values, "MATRIX_TIMEOUT_S", 420.0, 1.0),
            max_event_age_s=_number(values, "MATRIX_MAX_EVENT_AGE_S", 300.0, 1.0),
            log_level=get("MATRIX_LOG_LEVEL", "INFO").upper(),
        )
        if not settings.access_token and not (settings.user_id and settings.password):
            raise ValueError("set MATRIX_ACCESS_TOKEN, or MATRIX_USER_ID and MATRIX_PASSWORD")
        if not sdk.endpoint_allowed(settings.agent_url, settings.gateway_token):
            raise ValueError("PERSONAGENT_URL must be loopback, or HTTPS with GATEWAY_TOKEN set")
        if not settings.rooms and not settings.dm_users:
            logger.warning("MATRIX_ROOMS and MATRIX_DM_USERS are both empty: "
                           "nothing will be forwarded")
        return settings


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


# ---------- message content ----------

def pill_target(href: str) -> Optional[str]:
    """The user a matrix.to or matrix: link points at, or None."""
    href = unquote(str(href or "").strip())
    for prefix in ("https://matrix.to/#/", "http://matrix.to/#/"):
        if href.startswith(prefix):
            target = href[len(prefix):].split("?", 1)[0]
            return target if target.startswith("@") else None
    if href.startswith("matrix:u/"):
        return "@" + href[len("matrix:u/"):].split("?", 1)[0]
    return None


def pill(user_id: str, name: str) -> str:
    return f'<a href="https://matrix.to/#/{html.escape(user_id)}">{html.escape(name)}</a>'


def strip_reply_fallback(body: str) -> tuple[str, str]:
    """(body without a reply fallback, the text the fallback quoted).

    Clients before Matrix 1.13 prefix a reply with "> <@sender> quoted" lines
    and a blank line; the agent must not read them as the sender's words."""
    lines = str(body or "").split("\n")
    count = 0
    while count < len(lines) and lines[count].startswith(">"):
        count += 1
    if not count:
        return str(body or ""), ""
    quoted = [line[1:].lstrip(" ") for line in lines[:count]]
    rest = lines[count:]
    if rest and not rest[0].strip():
        rest = rest[1:]
    quoted[0] = _FALLBACK_SENDER.sub("", quoted[0], count=1)
    return "\n".join(rest), "\n".join(quoted).strip()


class _Formatted(HTMLParser):
    """An HTML formatted_body as segments: pills to the bot become mention
    segments, custom emoji emoji segments, everything else text."""

    def __init__(self, self_id: str):
        super().__init__(convert_charrefs=True)
        self.self_id = self_id
        self.segments: list[dict] = []
        self._text: list[str] = []
        self._skip = 0
        self._link: Optional[tuple[Optional[str], str]] = None
        self._label: list[str] = []

    def _flush(self) -> None:
        if self._text:
            self.segments.append({"type": "text", "text": "".join(self._text)})
            self._text = []

    def _newline(self) -> None:
        if self._text and not self._text[-1].endswith("\n"):
            self._text.append("\n")

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag == "mx-reply":
            self._skip += 1
            return
        if self._skip:
            return
        a = {k: (v or "") for k, v in attrs}
        if tag == "br":
            self._text.append("\n")
        elif tag in _BLOCK_TAGS:
            self._newline()
        elif tag == "a":
            href = a.get("href", "")
            self._link = (pill_target(href), href)
            self._label = []
        elif tag == "img":
            alt = (a.get("alt") or a.get("title") or "").strip()
            if "data-mx-emoticon" in a:
                self._flush()
                self.segments.append({"type": "emoji", "name": alt.strip(":") or "emoji",
                                      "id": a.get("src", "")})
            elif alt:
                self._text.append(alt)

    def handle_endtag(self, tag: str) -> None:
        if tag == "mx-reply":
            self._skip = max(0, self._skip - 1)
            return
        if self._skip:
            return
        if tag == "a" and self._link is not None:
            (user, href), label = self._link, "".join(self._label)
            self._link = None
            if user and user == self.self_id:
                self._flush()
                self.segments.append({"type": "mention", "user_id": user,
                                      "name": label.lstrip("@").strip() or user})
            elif user or not href or href == label:
                self._text.append(label)
            else:
                self._text.append(f"{label} ({href})")
        elif tag in _BLOCK_TAGS:
            self._newline()

    def handle_data(self, data: str) -> None:
        if not self._skip:
            (self._label if self._link is not None else self._text).append(data)


def formatted_segments(formatted_body: str, self_id: str) -> list[dict]:
    parser = _Formatted(self_id)
    parser.feed(formatted_body)
    parser.close()
    parser._flush()
    return _trim(parser.segments)


def _trim(segments: list[dict]) -> list[dict]:
    # Only the outer ends: the agent joins segments with no separator, so the
    # space after a mention is the only thing between it and the next word.
    if segments and segments[0].get("type") == "text":
        segments[0]["text"] = segments[0]["text"].lstrip()
    if segments and segments[-1].get("type") == "text":
        segments[-1]["text"] = segments[-1]["text"].rstrip()
    return [s for s in segments if s.get("type") != "text" or s["text"]]


def mentions_user(content: Mapping, user_id: str, body: str) -> bool:
    """m.mentions when the sender's client set it (Matrix 1.7+); otherwise the
    bare user id in the text, the rule older clients relied on. `body` is the
    text without a reply fallback, which quotes someone else's words. Pills
    are found by formatted_segments."""
    mentions = content.get("m.mentions")
    if isinstance(mentions, Mapping):
        return user_id in (mentions.get("user_ids") or [])
    return bool(user_id) and user_id in body


def _mapping(value: Any) -> Mapping:
    return value if isinstance(value, Mapping) else {}


def _is_edit(content: Mapping) -> bool:
    return ("m.new_content" in content
            or _mapping(content.get("m.relates_to")).get("rel_type") == "m.replace")


def _file_name(content: Mapping) -> str:
    return str(content.get("filename") or content.get("body") or "").strip()


def _caption(content: Mapping) -> str:
    # Matrix 1.10: a media body differing from `filename` is a caption.
    filename = str(content.get("filename") or "")
    body = str(content.get("body") or "").strip()
    return body if filename and body and body != filename else ""


def media_note(msgtype: str, content: Mapping) -> str:
    if msgtype in _MEDIA_NOTES:
        return _MEDIA_NOTES[msgtype]
    if msgtype == "m.audio":
        if "org.matrix.msc3245.voice" in content:
            return "(sent a voice message)"
        return f"(sent an audio file: {_file_name(content)})"
    if msgtype == "m.file":
        return f"(sent a file: {_file_name(content)})"
    return f"(sent a {msgtype or 'message'})"


def plain_text(event_type: str, content: Mapping) -> str:
    """What a person would read in a message, for quotes and raw_text."""
    if event_type == "m.sticker":
        return f"(sent a sticker: {str(content.get('body') or '').strip()})"
    msgtype = str(content.get("msgtype") or "")
    if msgtype in ("m.text", "m.notice", "m.emote"):
        return strip_reply_fallback(str(content.get("body") or ""))[0].strip()
    caption = _caption(content)
    return media_note(msgtype, content) + (f" {caption}" if caption else "")


def text_content(text: str, mention: Optional[tuple[str, str]] = None) -> dict:
    """An m.text reply. An empty m.mentions says it pings nobody, so no
    client guesses a mention from a name that happens to be in the text."""
    content: dict = {"msgtype": "m.text", "body": text, "m.mentions": {}}
    if mention:
        user_id, name = mention
        content["body"] = f"{name} {text}"
        content["format"] = HTML_FORMAT
        content["formatted_body"] = (f"{pill(user_id, name)} "
                                     + html.escape(text).replace("\n", "<br>"))
        content["m.mentions"] = {"user_ids": [user_id]}
    return content


def image_type(data: bytes) -> tuple[str, str]:
    """(mimetype, extension) from the magic bytes; the agent sends base64."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png", "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg", "jpg"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif", "gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp", "webp"
    return "application/octet-stream", "bin"


def _localpart(user_id: str) -> str:
    return user_id[1:].split(":", 1)[0] if user_id.startswith("@") else user_id


def _ok_event_id(response: Any) -> str:
    return str(getattr(response, "event_id", "") or "")


def _nio_decrypt(ciphertext: bytes, key: str, sha256: str, iv: str) -> bytes:
    from nio.crypto.attachments import decrypt_attachment
    return decrypt_attachment(ciphertext, key, sha256, iv)


class SendError(Exception):
    pass


@dataclass
class _Target:
    """Where a batch of replies goes."""
    room: Any
    conversation_id: str
    is_group: bool
    thread_root: str = ""
    in_reply_to: str = ""


# ---------- the connector ----------

class MatrixConnector:
    """Room events in, agent replies out, over one logged-in client.

    `client` is a matrix-nio AsyncClient, or anything with the same few
    methods: room_send, room_typing, upload, download, room_get_event,
    room_read_markers, join, list_direct_rooms, and the `rooms` and `user_id`
    attributes."""

    def __init__(self, client: Any, settings: Settings, agent: sdk.Connector, *,
                 decrypt: Optional[Callable[[bytes, str, str, str], bytes]] = None):
        self.client = client
        self.settings = settings
        self.agent = agent
        self.decrypt = decrypt or _nio_decrypt
        self.direct_rooms: set[str] = set()
        self.pause_s = (0.8, 1.8)
        self.now: Callable[[], float] = time.time
        # event id -> (sender, text), so most replies resolve without a fetch.
        self._recent: collections.OrderedDict[str, tuple[str, str]] = collections.OrderedDict()
        self._typing: dict[str, int] = {}
        self._typing_tasks: dict[str, asyncio.Task] = {}
        self._tasks: set[asyncio.Task] = set()
        self._turns = asyncio.Semaphore(MAX_CONCURRENT_TURNS)
        self._joining: set[str] = set()
        self._warned: set[str] = set()

    @property
    def me(self) -> str:
        return str(getattr(self.client, "user_id", "") or "")

    def caps(self) -> list[str]:
        return ["outbox", "quote_text"] if self.settings.outbox else ["quote_text"]

    # ----- rooms and people -----

    def _room(self, room_id: str) -> Any:
        rooms = getattr(self.client, "rooms", None) or {}
        return rooms.get(room_id)

    @staticmethod
    def _joined(room: Any) -> list[str]:
        users = getattr(room, "users", None) or {}
        return [uid for uid, user in users.items() if not getattr(user, "invited", False)]

    @staticmethod
    def member_name(room: Any, user_id: str) -> str:
        user = (getattr(room, "users", None) or {}).get(user_id)
        return str(getattr(user, "display_name", "") or "") or _localpart(user_id)

    def _listed_room(self, room_id: str) -> bool:
        # Named outright (not through `*`): the operator said it is a group.
        return any(p != "*" and fnmatchcase(room_id, p) for p in self.settings.rooms)

    def is_direct(self, room: Any) -> bool:
        """m.direct first, then a room with one other real member. Bridge bots
        and other MATRIX_IGNORE_USERS do not count: a bridged WhatsApp DM
        holds the bot, the contact's ghost and the bridge bot."""
        room_id = str(getattr(room, "room_id", ""))
        if self._listed_room(room_id):
            return False
        if room_id in self.direct_rooms:
            return True
        others = [uid for uid in self._joined(room)
                  if uid != self.me and not matches(self.settings.ignore_users, uid)]
        return len(others) == 1

    async def refresh_direct_rooms(self) -> None:
        try:
            response = await self.client.list_direct_rooms()
        except Exception as exc:
            logger.debug("m.direct unavailable: %s", exc)
            return
        rooms = getattr(response, "rooms", None)
        if isinstance(rooms, Mapping):
            self.direct_rooms = {str(r) for ids in rooms.values() for r in (ids or [])}

    def invite_allowed(self, room_id: str, inviter: str, is_direct: bool) -> bool:
        return (self._listed_room(room_id)
                or matches(self.settings.invite_from, inviter)
                or (is_direct and matches(self.settings.dm_users, inviter)))

    async def on_invite(self, room: Any, event: Any) -> None:
        """nio callback for InviteMemberEvent."""
        room_id = str(getattr(room, "room_id", ""))
        if (getattr(event, "state_key", None) != self.me
                or getattr(event, "membership", None) != "invite"
                or room_id in self._joining):
            return
        inviter = str(getattr(event, "sender", "") or "")
        content = getattr(event, "content", None) or {}
        is_direct = bool(content.get("is_direct"))
        if not self.invite_allowed(room_id, inviter, is_direct):
            logger.info("leaving an invite to %s from %s alone: not allowed by "
                        "MATRIX_ROOMS, MATRIX_INVITE_FROM or MATRIX_DM_USERS", room_id, inviter)
            return
        self._joining.add(room_id)
        try:
            response = await self.client.join(room_id)
        except Exception as exc:
            response = exc
        if not getattr(response, "room_id", None):
            self._joining.discard(room_id)
            logger.warning("could not join %s: %s", room_id, response)
            return
        if is_direct:
            self.direct_rooms.add(room_id)
        logger.info("joined %s on an invite from %s", room_id, inviter)

    # ----- inbound -----

    def on_room_event(self, room: Any, event: Any) -> None:
        """nio callback for room messages. It must return at once: nio awaits
        callbacks inside the sync loop, and one agent turn can take minutes."""
        source = getattr(event, "source", None)
        if not isinstance(source, dict):
            return
        if source.get("type") == "m.room.encrypted":
            room_id = str(getattr(room, "room_id", ""))
            if room_id not in self._warned:
                self._warned.add(room_id)
                logger.warning("cannot decrypt messages in %s: %s", room_id,
                               "set MATRIX_E2EE=true" if not self.settings.e2ee
                               else "no room key for this device yet")
            return
        task = asyncio.ensure_future(self.handle(room, source))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    def _remember(self, event_id: str, sender: str, text: str) -> None:
        self._recent[event_id] = (sender, text)
        self._recent.move_to_end(event_id)
        while len(self._recent) > RECENT_EVENTS:
            self._recent.popitem(last=False)

    async def _parent(self, room: Any, event_id: str) -> Optional[tuple[str, str]]:
        if event_id in self._recent:
            return self._recent[event_id]
        try:
            response = await self.client.room_get_event(room.room_id, event_id)
            event = getattr(response, "event", None)
            source = getattr(event, "source", None)
            if isinstance(source, dict) and source.get("type") == "m.room.encrypted":
                if not getattr(event, "room_id", None):
                    event.room_id = room.room_id
                source = getattr(self.client.decrypt_event(event), "source", None)
        except Exception as exc:
            logger.debug("could not fetch %s in %s: %s", event_id, room.room_id, exc)
            return None
        if not isinstance(source, dict) or not source.get("sender"):
            return None
        found = (str(source["sender"]),
                 plain_text(str(source.get("type") or ""), source.get("content") or {}))
        self._remember(event_id, *found)
        return found

    async def _image(self, content: Mapping, *, sticker: bool = False) -> Optional[dict]:
        encrypted = _mapping(content.get("file"))
        mxc = str((encrypted or {}).get("url") or content.get("url") or "")
        info = _mapping(content.get("info"))
        size = info.get("size")
        if not mxc.startswith("mxc://") or (isinstance(size, int) and size > MAX_IMAGE_BYTES):
            return None
        try:
            # Authenticated media (Matrix 1.11): the bytes need the bot's
            # token, so they travel to the agent inline, never as a URL.
            response = await asyncio.wait_for(self.client.download(mxc=mxc),
                                              DOWNLOAD_TIMEOUT_S)
            data = getattr(response, "body", None)
            if not isinstance(data, (bytes, bytearray)):
                raise SendError(str(response))
            if encrypted:
                data = self.decrypt(bytes(data), encrypted["key"]["k"],
                                    encrypted["hashes"]["sha256"], encrypted["iv"])
        except Exception as exc:
            logger.info("image %s not forwarded: %s", mxc, exc)
            return None
        if len(data) > MAX_IMAGE_BYTES:
            return None
        return {"type": "image", "b64": base64.b64encode(bytes(data)).decode("ascii"),
                "sticker": sticker}

    async def build_event(self, room: Any, source: Mapping) -> Optional[dict]:
        """The neutral event for one room event, or None to skip it."""
        etype = str(source.get("type") or "")
        content = _mapping(source.get("content"))
        sender = str(source.get("sender") or "")
        event_id = str(source.get("event_id") or "")
        room_id = str(getattr(room, "room_id", ""))
        if etype not in ("m.room.message", "m.sticker") or not sender or not event_id:
            return None
        self._remember(event_id, sender, plain_text(etype, content))
        msgtype = str(content.get("msgtype") or "")
        if (sender == self.me or matches(self.settings.ignore_users, sender)
                or msgtype == "m.notice" or _is_edit(content)):
            return None  # notices are bot talk; answering them is how bots loop
        try:
            timestamp = int(source["origin_server_ts"]) / 1000
        except (KeyError, TypeError, ValueError):
            return None
        if self.now() - timestamp > self.settings.max_event_age_s:
            return None  # backlog, or history a bridge backfilled
        private = self.is_direct(room)
        if private and not matches(self.settings.dm_users, sender):
            return None
        if not private and not matches(self.settings.rooms, room_id):
            return None

        name = self.member_name(room, sender)
        segments: list[dict] = []
        relates = _mapping(content.get("m.relates_to"))
        parent_id = str(_mapping(relates.get("m.in_reply_to")).get("event_id") or "")
        if relates.get("rel_type") == "m.thread" and relates.get("is_falling_back"):
            parent_id = ""  # a thread's fallback reply, not a quote
        body, fallback = str(content.get("body") or ""), ""
        if parent_id:
            body, fallback = strip_reply_fallback(body)
        is_at_me = etype == "m.room.message" and mentions_user(content, self.me, body)
        if parent_id:
            parent = await self._parent(room, parent_id)
            quote = {"type": "reply", "message_id": parent_id}
            if parent:
                quote.update(sender_id=parent[0], sender_name=self.member_name(room, parent[0]),
                             text=parent[1])
                is_at_me = is_at_me or parent[0] == self.me
            elif fallback:
                quote["text"] = fallback
            segments.append(quote)

        if etype == "m.sticker":
            image = await self._image(content, sticker=True)
            segments.append(image or {"type": "emoji",
                                      "name": str(content.get("body") or "sticker")})
            raw_text = plain_text(etype, content)
        elif msgtype in ("m.text", "m.emote"):
            formatted = str(content.get("formatted_body") or "")
            if content.get("format") == HTML_FORMAT and formatted:
                parts = formatted_segments(formatted, self.me)
            else:
                parts = _trim([{"type": "text", "text": body}])
            if msgtype == "m.emote":
                parts.insert(0, {"type": "text", "text": f"* {name} "})
            is_at_me = is_at_me or any(p.get("type") == "mention" for p in parts)
            segments.extend(parts)
            raw_text = body.strip()
        elif msgtype == "m.image":
            image = await self._image(content)
            segments.append(image or {"type": "text", "text": media_note(msgtype, content)})
            if _caption(content):
                segments.append({"type": "text", "text": _caption(content)})
            raw_text = plain_text(etype, content)
        else:
            raw_text = plain_text(etype, content)
            segments.append({"type": "text", "text": raw_text})

        thread_root = str(relates.get("event_id") or "") if relates.get("rel_type") == "m.thread" else ""
        event = {
            "platform": PLATFORM,
            "message_type": "private" if private else "group",
            "conversation_id": sender if private else room_id,
            "user_id": sender,
            "sender_name": name,
            "self_id": self.me,
            "message_id": event_id,
            "source_timestamp": int(timestamp),
            "is_at_me": bool(is_at_me),
            "raw_text": raw_text,
            "segments": segments,
            "reply_handle": room_id,
            "caps": self.caps(),
        }
        if thread_root:
            event["_thread_root"] = thread_root
        return event

    async def handle(self, room: Any, source: Mapping) -> None:
        async with self._turns:
            try:
                event = await self.build_event(room, source)
            except Exception:
                logger.exception("could not read event %s", source.get("event_id"))
                return
            if event is not None:
                await self._turn(room, event)

    async def _turn(self, room: Any, event: dict) -> None:
        room_id = room.room_id
        thread_root = event.pop("_thread_root", "")
        await self._typing_start(room_id)
        try:
            try:
                answer = await self.agent.send_event(event)
            except httpx.HTTPStatusError as exc:
                logger.warning("agent refused %s (%s): %s", event["message_id"],
                               exc.response.status_code, exc.response.text[:200])
                return
            except httpx.TimeoutException:
                logger.warning("timed out waiting for the agent (MATRIX_TIMEOUT_S=%.0f); "
                               "it should cover LLM_TIMEOUT x (1 + LLM_MAX_RETRIES)",
                               self.settings.timeout_s)
                return
            except httpx.HTTPError as exc:
                logger.warning("agent unreachable at %s: %s", self.settings.agent_url, exc)
                return
            if not isinstance(answer, dict):
                return
            if answer.get("owned") and self.settings.read_receipts:
                await self._quietly(self.client.room_read_markers(
                    room_id, event["message_id"], event["message_id"]))
            target = _Target(room, event["conversation_id"], event["message_type"] == "group",
                             thread_root=thread_root, in_reply_to=event["message_id"])
            await self.send_items(target, answer.get("replies") or [])
        finally:
            await self._typing_stop(room_id)

    # ----- outbound -----

    def _mention(self, target: _Target, at_user_id: Any) -> Optional[tuple[str, str]]:
        """Only in groups, only Matrix users, never the bot itself."""
        prefix = PLATFORM + ":"
        raw = str(at_user_id or "")
        if not target.is_group or not raw.startswith(prefix):
            return None
        user_id = raw[len(prefix):]
        if not user_id.startswith("@") or user_id == self.me:
            return None
        return user_id, self.member_name(target.room, user_id)

    def _relation(self, target: _Target, item: Mapping) -> Optional[dict]:
        quoted = ""
        reply_to = str(item.get("reply_to_message_id") or "")
        prefix = f"{PLATFORM}:{target.conversation_id}:"
        if reply_to.startswith(prefix):
            quoted = reply_to[len(prefix):]
        if target.thread_root:
            return {"rel_type": "m.thread", "event_id": target.thread_root,
                    "is_falling_back": not quoted,
                    "m.in_reply_to": {"event_id": quoted or target.in_reply_to
                                      or target.thread_root}}
        return {"m.in_reply_to": {"event_id": quoted}} if quoted else None

    async def _image_content(self, target: _Target, item: Mapping,
                             mention: Optional[tuple[str, str]]) -> Optional[dict]:
        try:
            data = base64.b64decode(str(item.get("b64") or ""), validate=True)
        except (binascii.Error, ValueError):
            data = b""
        if not data:
            logger.warning("dropping an image reply with no valid base64")
            return None
        mimetype, extension = image_type(data)
        filename = f"image.{extension}"
        encrypt = bool(getattr(target.room, "encrypted", False))
        response, keys = await self.client.upload(io.BytesIO(data), content_type=mimetype,
                                                  filename=filename, encrypt=encrypt,
                                                  filesize=len(data))
        uri = str(getattr(response, "content_uri", "") or "")
        if not uri:
            raise SendError(f"upload failed: {response}")
        content: dict = {"msgtype": "m.image", "body": filename, "filename": filename,
                         "info": {"mimetype": mimetype, "size": len(data)}, "m.mentions": {}}
        if encrypt:
            content["file"] = {**(keys or {}), "url": uri}
        else:
            content["url"] = uri
        if mention:
            user_id, name = mention
            content.update(body=name, format=HTML_FORMAT, formatted_body=pill(user_id, name),
                           **{"m.mentions": {"user_ids": [user_id]}})
        return content

    async def _send_one(self, target: _Target, item: Mapping) -> None:
        room = target.room
        if getattr(room, "encrypted", False) and not self.settings.e2ee:
            raise SendError("the room is encrypted and MATRIX_E2EE is off")
        mention = self._mention(target, item.get("at_user_id"))
        kind = item.get("type")
        if kind == "text":
            text = str(item.get("text") or "")
            if not text.strip():
                return
            content = text_content(text, mention)
            remembered = text
        elif kind == "image":
            content = await self._image_content(target, item, mention)
            if content is None:
                return
            remembered = "(sent an image)"
        else:
            logger.warning("dropping a reply of unknown type %r", kind)
            return
        relation = self._relation(target, item)
        if relation:
            content["m.relates_to"] = relation
        # Unverified devices are the norm for a bot's rooms: refusing to send
        # to them would leave every encrypted room silent.
        response = await self.client.room_send(room.room_id, "m.room.message", content,
                                               ignore_unverified_devices=True)
        event_id = _ok_event_id(response)
        if not event_id:
            raise SendError(str(response))
        self._remember(event_id, self.me, remembered)

    async def send_items(self, target: _Target, items: list) -> int:
        """Send in order; returns how many went out before the first failure."""
        room_id = target.room.room_id
        for index, item in enumerate(items):
            if not isinstance(item, Mapping):
                continue
            if index:
                await self._typing_start(room_id)
                try:
                    low, high = self.pause_s
                    await asyncio.sleep(random.uniform(low, high))
                finally:
                    await self._typing_stop(room_id)
            try:
                await self._send_one(target, item)
            except Exception as exc:
                logger.warning("could not send to %s: %s", room_id, exc)
                return index
        return len(items)

    async def deliver(self, delivery: dict) -> sdk.DeliveryResult:
        """Outbox delivery: reply_handle is the room id."""
        room_id = str(delivery.get("reply_handle") or "")
        room = self._room(room_id) if room_id else None
        if room is None:
            return "refused", 0  # the bot left, or never was there
        private = delivery.get("message_type") == "private"
        conversation_id = str(delivery.get("conversation_id") or "")
        allowed = (matches(self.settings.dm_users, conversation_id) if private
                   else matches(self.settings.rooms, room_id))
        if not allowed:
            return "refused", 0
        if getattr(room, "encrypted", False) and not self.settings.e2ee:
            return "unsupported", 0
        items = [i for i in (delivery.get("items") or []) if isinstance(i, Mapping)]
        sent = await self.send_items(_Target(room, conversation_id or room_id, not private),
                                     items)
        if sent >= len(items):
            return "sent", sent
        return ("partial", sent) if sent else ("failed", 0)

    # ----- typing -----

    async def _typing_start(self, room_id: str) -> None:
        self._typing[room_id] = self._typing.get(room_id, 0) + 1
        if self._typing[room_id] == 1:
            self._typing_tasks[room_id] = asyncio.ensure_future(self._typing_refresh(room_id))
            await self._quietly(self.client.room_typing(room_id, True, timeout=TYPING_TIMEOUT_MS))

    async def _typing_refresh(self, room_id: str) -> None:
        # A typing notice lapses after its timeout; a turn can outlast several.
        while True:
            await asyncio.sleep(TYPING_REFRESH_S)
            await self._quietly(self.client.room_typing(room_id, True, timeout=TYPING_TIMEOUT_MS))

    async def _typing_stop(self, room_id: str) -> None:
        # Several turns can be open in one room; the last one out stops it.
        self._typing[room_id] = self._typing.get(room_id, 1) - 1
        if self._typing[room_id] > 0:
            return
        self._typing.pop(room_id, None)
        task = self._typing_tasks.pop(room_id, None)
        if task is not None:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        await self._quietly(self.client.room_typing(room_id, False))

    @staticmethod
    async def _quietly(call: Any) -> None:
        try:
            await call
        except Exception as exc:  # an indicator must never cost a reply
            logger.debug("ignored: %s", exc)

    async def drain(self) -> None:
        if self._tasks:
            await asyncio.gather(*list(self._tasks), return_exceptions=True)


# ---------- running it with matrix-nio ----------

def _import_nio() -> Any:
    try:
        import nio
    except ImportError:
        raise SystemExit("matrix-nio is not installed: "
                         "pip install -r integrations/matrix/requirements.txt") from None
    return nio


def _session_file(settings: Settings) -> Path:
    return settings.store_path / "session.json"


async def login(client: Any, settings: Settings) -> None:
    """Access token first; else a session saved by an earlier password login
    (a new login is a new device, which would strand the E2EE keys); else
    the password, saving the session it gets."""
    if settings.access_token:
        client.access_token = settings.access_token
        user_id, device_id = settings.user_id, settings.device_id
        if not (user_id and device_id):
            who = await client.whoami()
            user_id = user_id or str(getattr(who, "user_id", "") or "")
            device_id = device_id or str(getattr(who, "device_id", "") or "")
            if not user_id:
                raise SystemExit(f"MATRIX_ACCESS_TOKEN was refused: {who}")
        if device_id:
            client.restore_login(user_id, device_id, settings.access_token)
        elif settings.e2ee:
            raise SystemExit("E2EE needs a device: set MATRIX_DEVICE_ID for this token")
        else:
            # restore_login insists on a device id whenever the E2EE extra is
            # installed, even with encryption off; an appservice token has none.
            client.user_id = user_id
        return

    saved = _session_file(settings)
    try:
        session = json.loads(saved.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        session = None
    # Keyed by what the operator typed: MATRIX_USER_ID may be a bare localpart.
    if (isinstance(session, dict) and session.get("login") == settings.user_id
            and session.get("homeserver") == settings.homeserver):
        client.access_token = session["access_token"]
        who = await client.whoami()
        if getattr(who, "user_id", None):
            client.restore_login(session["user_id"], session["device_id"],
                                 session["access_token"])
            return
        logger.info("the saved session was revoked; logging in again")

    response = await client.login(settings.password, device_name=settings.device_name)
    if not getattr(response, "access_token", None):
        raise SystemExit(f"Matrix login failed: {response}")
    saved.parent.mkdir(parents=True, exist_ok=True)
    saved.write_text(json.dumps({
        "homeserver": settings.homeserver, "login": settings.user_id,
        "user_id": response.user_id, "device_id": response.device_id,
        "access_token": response.access_token,
    }), encoding="utf-8")
    try:
        saved.chmod(0o600)
    except OSError:
        pass


async def run(settings: Settings, *, nio_module: Any = None,
              agent_client: Optional[httpx.AsyncClient] = None,
              stop: Optional[asyncio.Event] = None) -> None:
    nio = nio_module or _import_nio()
    if settings.e2ee:
        settings.store_path.mkdir(parents=True, exist_ok=True)
    config = nio.AsyncClientConfig(encryption_enabled=settings.e2ee,
                                   store_sync_tokens=settings.e2ee)
    client = nio.AsyncClient(settings.homeserver, settings.user_id,
                             device_id=settings.device_id or None,
                             store_path=str(settings.store_path) if settings.e2ee else "",
                             config=config)
    agent = None
    stop = stop or asyncio.Event()
    try:
        await login(client, settings)
        agent = sdk.Connector(settings.agent_url, settings.gateway_token,
                              forwarder_id=settings.forwarder_id
                              or default_forwarder_id(client.user_id),
                              timeout_s=settings.timeout_s, client=agent_client)
        connector = MatrixConnector(client, settings, agent)
        client.add_event_callback(connector.on_invite, nio.InviteMemberEvent)
        if settings.e2ee and client.should_upload_keys:
            await client.keys_upload()
        # The first sync is the backlog: its messages were sent before this
        # process was listening, so no message callback is registered yet.
        first = await client.sync(timeout=0, full_state=True)
        if not getattr(first, "next_batch", None):
            raise SystemExit(f"first sync failed: {first}")
        await connector.refresh_direct_rooms()
        client.add_event_callback(connector.on_room_event,
                                  (nio.RoomMessage, nio.StickerEvent, nio.MegolmEvent))
        logger.info("listening as %s on %s", client.user_id, settings.homeserver)

        jobs = [asyncio.ensure_future(client.sync_forever(timeout=30_000)),
                asyncio.ensure_future(stop.wait())]
        if settings.outbox:
            jobs.append(asyncio.ensure_future(agent.run_outbox(connector.deliver, stop=stop)))
        done, _ = await asyncio.wait(jobs, return_when=asyncio.FIRST_COMPLETED)
        stop.set()
        for job in jobs:
            job.cancel()
        await asyncio.gather(*jobs, return_exceptions=True)
        await connector.drain()
        for job in done:
            if not job.cancelled() and job.exception() is not None:
                raise job.exception()
    finally:
        if agent is not None:
            await agent.aclose()
        await client.close()


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description="Forward Matrix rooms to personagent.")
    parser.add_argument("--config", help="dotenv-style settings file "
                        f"(default: {DEFAULT_CONFIG.name} next to this script)")
    args = parser.parse_args(argv)
    try:
        settings = Settings.from_env(load_env(args.config))
    except (ValueError, FileNotFoundError) as exc:
        print(f"matrix_connector: {exc}", file=sys.stderr)
        return 2
    logging.basicConfig(level=getattr(logging, settings.log_level, logging.INFO),
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        asyncio.run(run(settings))
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
