"""Matrix through the Client-Server API (https://spec.matrix.org/latest/client-server-api/):
long-polled /sync in, PUT /rooms/{id}/send out, as an ordinary bot account.

There is no crypto library here, so end-to-end encrypted rooms cannot be read:
they are detected and left alone, and invites to them are declined."""
from __future__ import annotations

import asyncio
import base64
import html
import json
import logging
import re
import secrets
import time
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote, urlsplit

import httpx

from .base import (MAX_INLINE_IMAGE_BYTES, Platform, Refused, Unsupported, backoff_sleep,
                   plain_name, raw_id, split_text)
from ..storage import atomic_write_text

logger = logging.getLogger("personagent.direct.matrix")

CLIENT = "/_matrix/client/v3"
POLL_MS = 30_000
CALL_TIMEOUT_S = 30
# A whole event is capped at 64 KiB, formatted_body and CJK bytes included.
MAX_TEXT = 4000
# After a long sleep, messages older than this are not answered.
MAX_AGE_S = 600
TYPING_MS = 30_000
RATE_LIMIT_MAX_S = 300
RECENT_EVENTS = 1024
HTML_FORMAT = "org.matrix.custom.html"
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
OWNER_ID = re.compile(r"^@[^:\s]+:\S+$")
# Lazy-loaded members keep the first sync small in big rooms; presence is unused.
SYNC_FILTER = json.dumps({"presence": {"not_types": ["*"]},
                          "room": {"state": {"lazy_load_members": True},
                                   "timeline": {"limit": 50, "lazy_load_members": True}}},
                         separators=(",", ":"))
FIRST_FILTER = json.dumps({"presence": {"not_types": ["*"]},
                           "room": {"state": {"lazy_load_members": True},
                                    "timeline": {"limit": 1, "lazy_load_members": True}}},
                          separators=(",", ":"))
ENCRYPTED_REASON = ("This bot cannot read end-to-end encrypted rooms. "
                    "Invite it to a room with encryption turned off.")
_BLOCK_TAGS = frozenset({"p", "div", "li", "blockquote", "pre", "tr", "ul", "ol", "table",
                         "h1", "h2", "h3", "h4", "h5", "h6"})
_FALLBACK_SENDER = re.compile(r"^\*?\s*<[^>]*>\s?")
_MEDIA_NOTES = {"m.image": "(sent an image)", "m.video": "(sent a video)",
                "m.location": "(shared a location)"}


def secure_base(url: str) -> bool:
    """https, or plain http only to this computer."""
    parts = urlsplit(url)
    if not parts.hostname:
        return False
    return parts.scheme == "https" or (parts.scheme == "http" and parts.hostname in LOCAL_HOSTS)


def localpart(user_id: str) -> str:
    return user_id[1:].split(":", 1)[0] if user_id.startswith("@") else user_id


def pill_target(href: str) -> str | None:
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
    """(body without a pre-1.13 reply fallback, the text it quoted)."""
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
    """formatted_body as segments: a pill to the bot becomes a mention."""

    def __init__(self, self_id: str):
        super().__init__(convert_charrefs=True)
        self.self_id = self_id
        self.segments: list[dict] = []
        self._text: list[str] = []
        self._skip = 0
        self._link: tuple[str | None, str] | None = None
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
            self._link = (pill_target(a.get("href", "")), a.get("href", ""))
            self._label = []
        elif tag == "img":
            alt = (a.get("alt") or a.get("title") or "").strip()
            if "data-mx-emoticon" in a:
                self._flush()
                self.segments.append({"type": "emoji", "name": alt.strip(":") or "emoji", "id": ""})
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
    # Only the outer ends: the space after a mention separates it from the next word.
    if segments and segments[0].get("type") == "text":
        segments[0]["text"] = segments[0]["text"].lstrip()
    if segments and segments[-1].get("type") == "text":
        segments[-1]["text"] = segments[-1]["text"].rstrip()
    return [s for s in segments if s.get("type") != "text" or s["text"]]


def _mapping(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def media_note(msgtype: str, content: dict) -> str:
    if msgtype in _MEDIA_NOTES:
        return _MEDIA_NOTES[msgtype]
    name = str(content.get("filename") or content.get("body") or "").strip()
    if msgtype == "m.audio":
        return ("(sent a voice message)" if "org.matrix.msc3245.voice" in content
                else f"(sent an audio file: {name})")
    if msgtype == "m.file":
        return f"(sent a file: {name})"
    return f"(sent a {msgtype or 'message'})"


def _caption(content: dict) -> str:
    # Matrix 1.10: a media body that differs from `filename` is a caption.
    filename = str(content.get("filename") or "")
    body = str(content.get("body") or "").strip()
    return body if filename and body and body != filename else ""


def plain_text(event_type: str, content: dict) -> str:
    if event_type == "m.sticker":
        return f"(sent a sticker: {str(content.get('body') or '').strip()})"
    msgtype = str(content.get("msgtype") or "")
    if msgtype in ("m.text", "m.notice", "m.emote"):
        return strip_reply_fallback(str(content.get("body") or ""))[0].strip()
    caption = _caption(content)
    return media_note(msgtype, content) + (f" {caption}" if caption else "")


def image_type(data: bytes) -> tuple[str, str]:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png", "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg", "jpg"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif", "gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp", "webp"
    return "application/octet-stream", "bin"


def _starts_with_name(text: str, names: list[str]) -> bool:
    low = text.strip().lower()
    for name in names:
        name = name.strip().lower()
        if name and low.startswith(name) and (len(low) == len(name) or not low[len(name)].isalnum()):
            return True
    return False


class Matrix(Platform):
    kind = "matrix"

    def __init__(self, values: dict, *, client: httpx.AsyncClient | None = None,
                 state: Path | None = None):
        super().__init__(values)
        self.base = str(values.get("matrix_homeserver") or "https://matrix.org").strip().rstrip("/")
        self.token = str(values.get("matrix_token") or "").strip()
        self.owner = str(values.get("matrix_owner") or "").strip()
        self.client = client or httpx.AsyncClient(timeout=POLL_MS / 1000 + 15)
        self.state_path = state
        self.display = ""
        self.since = ""
        self.rooms: dict[str, dict] = {}        # room id -> {"members": n, "encrypted": bool}
        self.direct: set[str] = set()
        self.names: dict[tuple[str, str], str] = {}
        self.recent: dict[str, tuple[str, str]] = {}    # event id -> (sender, text)
        self._invites_done: set[str] = set()
        self._warned: set[str] = set()
        self._txn = 0

    # ------------------------------------------------------------ transport

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token}"}

    async def call(self, method: str, path: str, *, strict: bool = False, **kwargs) -> Any:
        """One API call, waiting out M_LIMIT_EXCEEDED; the token rides in a
        header and never reaches a URL, a log or an exception."""
        url = path if path.startswith("/_matrix") else CLIENT + path
        kwargs.setdefault("timeout", CALL_TIMEOUT_S)
        for _ in range(5):
            try:
                response = await self.client.request(method, self.base + url, headers=self._headers(),
                                                      **kwargs)
            except httpx.HTTPError as exc:
                raise ConnectionError(f"{path.split('?')[0]}: {type(exc).__name__}") from None
            try:
                answer = response.json()
            except ValueError:
                answer = None
            body = answer if isinstance(answer, dict) else {}
            code = str(body.get("errcode") or "")
            if response.status_code == 429 or code == "M_LIMIT_EXCEEDED":
                await asyncio.sleep(_retry_after(response, body))
                continue
            if response.status_code == 401 or code in ("M_UNKNOWN_TOKEN", "M_MISSING_TOKEN"):
                raise Refused("token_rejected")
            if code == "M_USER_DEACTIVATED":
                raise Refused("account_deactivated")
            if strict and (response.status_code in (404, 405) or answer is None):
                # Something answered, but not a Matrix homeserver.
                raise Refused("homeserver_invalid")
            if response.status_code >= 400:
                raise ConnectionError(f"{_where(path)}: {response.status_code} {code}".rstrip())
            if answer is None and response.content:
                raise ConnectionError(f"{_where(path)}: not JSON")
            return body
        raise ConnectionError(f"{_where(path)}: rate limited")

    async def _discover(self) -> None:
        """A server name like https://matrix.org may serve its API elsewhere."""
        try:
            response = await self.client.get(self.base + "/.well-known/matrix/client",
                                             timeout=15, follow_redirects=True)
            found = str(_mapping(response.json().get("m.homeserver")).get("base_url") or "")
        except (httpx.HTTPError, ValueError, AttributeError):
            return
        found = found.strip().rstrip("/")
        if found and secure_base(found):
            self.base = found

    async def check(self) -> str:
        return await self._login(strict=True)

    async def _login(self, strict: bool) -> str:
        if not secure_base(self.base):
            raise Refused("homeserver_invalid")
        if not OWNER_ID.match(self.owner):
            raise Refused("owner_invalid")
        if not self.token:
            raise Refused("token_rejected")
        await self._discover()
        try:
            me = await self.call("GET", "/account/whoami", strict=strict)
        except ConnectionError as exc:
            if strict and " 403" in str(exc):
                raise Refused("token_rejected") from None   # an appservice token for an unknown user
            raise
        user_id = str(me.get("user_id") or "")
        if not user_id.startswith("@"):
            if strict:
                raise Refused("homeserver_invalid")
            raise ConnectionError("whoami: no user id")
        self.bot_id = user_id
        if self.owner == self.bot_id:
            raise Refused("owner_invalid")
        try:
            profile = await self.call("GET", f"/profile/{quote(user_id, safe='')}/displayname")
            self.display = str(profile.get("displayname") or "")
        except ConnectionError:
            self.display = ""
        return plain_name(self.display, user_id)

    # ------------------------------------------------------------ state

    def _load(self) -> None:
        if self.state_path is None or not self.state_path.exists():
            return
        try:
            saved = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        if not isinstance(saved, dict) or saved.get("user") != self.bot_id:
            return      # another account's cursor would skip or replay messages
        self.since = str(saved.get("since") or "")
        self.rooms = {str(k): dict(v) for k, v in _mapping(saved.get("rooms")).items() if isinstance(v, dict)}
        self.direct = {str(r) for r in saved.get("direct") or []}

    def _save(self) -> None:
        if self.state_path is None:
            return
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self.state_path, json.dumps(
            {"user": self.bot_id, "since": self.since, "rooms": self.rooms,
             "direct": sorted(self.direct)}, ensure_ascii=False))

    # ------------------------------------------------------------ receiving

    async def run(self, on_event, connected) -> None:
        await self._login(strict=False)
        self._load()
        failures, announced = 0, False
        while True:
            first = not self.since
            params = {"filter": FIRST_FILTER if first else SYNC_FILTER,
                      "timeout": 0 if first else POLL_MS, "set_presence": "online"}
            if self.since:
                params["since"] = self.since
            try:
                batch = await self.call("GET", "/sync", params=params, timeout=POLL_MS / 1000 + 15)
                if not batch.get("next_batch"):
                    raise ConnectionError("sync: no next_batch")
            except ConnectionError as exc:
                logger.warning("matrix: %s", exc)
                self.dropped()
                announced = False
                await backoff_sleep(failures)
                failures += 1
                continue
            failures = 0
            if not announced:
                connected()
                announced = True
            # The first sync is the backlog: rooms and invites are read, messages are not answered.
            await self._absorb(batch, on_event, deliver=not first)
            self.since = str(batch["next_batch"])
            self._save()

    async def _absorb(self, batch: dict, on_event, deliver: bool) -> None:
        rooms = _mapping(batch.get("rooms"))
        for event in _mapping(batch.get("account_data")).get("events") or []:
            if isinstance(event, dict) and event.get("type") == "m.direct":
                self.direct = {str(r) for ids in _mapping(event.get("content")).values()
                               if isinstance(ids, list) for r in ids}
        for room_id in _mapping(rooms.get("leave")):
            self.rooms.pop(room_id, None)
            self.direct.discard(room_id)
        for room_id, invite in _mapping(rooms.get("invite")).items():
            await self._invite(str(room_id), _mapping(invite))
        for room_id, joined in _mapping(rooms.get("join")).items():
            joined = _mapping(joined)
            room = self.rooms.setdefault(str(room_id), {"members": 0, "encrypted": False})
            count = _mapping(joined.get("summary")).get("m.joined_member_count")
            if isinstance(count, int):
                room["members"] = count
            timeline = [e for e in _mapping(joined.get("timeline")).get("events") or [] if isinstance(e, dict)]
            for key in ("state", "state_after"):
                for event in _mapping(joined.get(key)).get("events") or []:
                    if isinstance(event, dict):
                        self._state_event(str(room_id), event)
            for event in timeline:
                if "state_key" in event:
                    self._state_event(str(room_id), event)
                    continue
                if deliver:
                    await self._timeline_event(str(room_id), event, on_event)

    def _state_event(self, room_id: str, event: dict) -> None:
        kind = event.get("type")
        if kind == "m.room.encryption":
            self.rooms.setdefault(room_id, {"members": 0, "encrypted": False})["encrypted"] = True
        elif kind == "m.room.member":
            content = _mapping(event.get("content"))
            user = str(event.get("state_key") or "")
            if content.get("membership") == "join" and content.get("displayname"):
                self.names[(room_id, user)] = str(content["displayname"])

    async def _invite(self, room_id: str, invite: dict) -> None:
        if room_id in self._invites_done:
            return
        events = [e for e in _mapping(invite.get("invite_state")).get("events") or [] if isinstance(e, dict)]
        mine = next((e for e in events if e.get("type") == "m.room.member"
                     and e.get("state_key") == self.bot_id
                     and _mapping(e.get("content")).get("membership") == "invite"), None)
        if mine is None:
            return
        inviter = str(mine.get("sender") or "")
        encrypted = any(e.get("type") == "m.room.encryption" for e in events)
        path = f"/rooms/{quote(room_id, safe='')}"
        try:
            if inviter != self.owner:
                # Only the owner decides where the bot talks; anyone else would spend their model budget.
                logger.info("matrix: declined an invite from someone other than the owner")
                await self.call("POST", path + "/leave", json={})
            elif encrypted:
                logger.warning("matrix: declined an invite to an encrypted room; encryption is not supported")
                await self.call("POST", path + "/leave", json={"reason": ENCRYPTED_REASON})
            else:
                await self.call("POST", path + "/join", json={})
                self.rooms.setdefault(room_id, {"members": 0, "encrypted": False})
                if _mapping(mine.get("content")).get("is_direct"):
                    self.direct.add(room_id)
                logger.info("matrix: joined a room on the owner's invite")
        except ConnectionError as exc:
            logger.warning("matrix: could not answer an invite (%s)", exc)
            return
        self._invites_done.add(room_id)

    def is_direct(self, room_id: str) -> bool:
        return room_id in self.direct or self.rooms.get(room_id, {}).get("members") == 2

    def _remember(self, event_id: str, sender: str, text: str) -> None:
        self.recent[event_id] = (sender, text)
        while len(self.recent) > RECENT_EVENTS:
            self.recent.pop(next(iter(self.recent)))

    async def _timeline_event(self, room_id: str, source: dict, on_event) -> None:
        kind = str(source.get("type") or "")
        if kind == "m.room.encrypted":
            self.rooms.setdefault(room_id, {"members": 0, "encrypted": True})["encrypted"] = True
            if room_id not in self._warned:
                self._warned.add(room_id)
                logger.warning("matrix: a room is end-to-end encrypted; its messages cannot be read")
            return
        event = await self.event(room_id, source)
        if event is None:
            return
        relates = _mapping(_mapping(source.get("content")).get("m.relates_to"))
        thread = str(relates.get("event_id") or "") if relates.get("rel_type") == "m.thread" else ""
        if event["addressed"]:
            await self._typing(room_id, True)
        await on_event(event, (room_id, thread, event["message_id"]))

    async def event(self, room_id: str, source: dict) -> dict | None:
        kind = str(source.get("type") or "")
        content = _mapping(source.get("content"))
        sender = str(source.get("sender") or "")
        event_id = str(source.get("event_id") or "")
        if kind not in ("m.room.message", "m.sticker") or not sender or not event_id or not content:
            return None
        self._remember(event_id, sender, plain_text(kind, content))
        msgtype = str(content.get("msgtype") or "")
        relates = _mapping(content.get("m.relates_to"))
        # Notices are bot talk (answering them is how bots loop); edits repeat a message.
        if (sender == self.bot_id or msgtype == "m.notice" or "m.new_content" in content
                or relates.get("rel_type") == "m.replace"):
            return None
        try:
            sent_at = int(source["origin_server_ts"]) // 1000
        except (KeyError, TypeError, ValueError):
            return None
        if time.time() - sent_at > MAX_AGE_S:
            return None
        dm = self.is_direct(room_id)
        name = await self.member_name(room_id, sender)
        segments: list[dict] = []
        parent_id = str(_mapping(relates.get("m.in_reply_to")).get("event_id") or "")
        if relates.get("rel_type") == "m.thread" and relates.get("is_falling_back"):
            parent_id = ""      # a thread's fallback for older clients, not a quote
        body, fallback = str(content.get("body") or ""), ""
        if parent_id:
            body, fallback = strip_reply_fallback(body)
        mentions = content.get("m.mentions")
        if isinstance(mentions, dict):
            addressed = self.bot_id in (mentions.get("user_ids") or [])
        else:
            addressed = bool(self.bot_id) and self.bot_id in body
        addressed = addressed or dm or _starts_with_name(body, [self.display, localpart(self.bot_id)])
        if parent_id:
            parent = await self._parent(room_id, parent_id)
            quote_segment: dict = {"type": "reply", "message_id": parent_id, "text": fallback,
                                   "sender_id": "", "sender_name": ""}
            if parent:
                quote_segment.update(sender_id=parent[0], text=parent[1],
                                     sender_name=await self.member_name(room_id, parent[0]))
                addressed = addressed or parent[0] == self.bot_id
            segments.append(quote_segment)
        if kind == "m.sticker":
            image = await self._image(content)
            segments.append(dict(image, sticker=True) if image
                            else {"type": "emoji", "name": str(content.get("body") or "sticker"), "id": ""})
            text = plain_text(kind, content)
        elif msgtype in ("m.text", "m.emote"):
            formatted = str(content.get("formatted_body") or "")
            if content.get("format") == HTML_FORMAT and formatted:
                parts = formatted_segments(formatted, self.bot_id)
            else:
                parts = _trim([{"type": "text", "text": body}])
            if msgtype == "m.emote":
                parts.insert(0, {"type": "text", "text": f"* {name} "})
            addressed = addressed or any(p.get("type") == "mention" for p in parts)
            segments.extend(parts)
            text = body.strip()
        elif msgtype == "m.image":
            image = await self._image(content)
            segments.append(image or {"type": "text", "text": media_note(msgtype, content)})
            if _caption(content):
                segments.append({"type": "text", "text": _caption(content)})
            text = plain_text(kind, content)
        else:
            text = plain_text(kind, content)
            segments.append({"type": "text", "text": text})
        if not any(s["type"] in ("text", "image", "emoji") for s in segments):
            return None
        return {"conversation_type": "dm" if dm else "group",
                **({} if dm else {"conversation_id": room_id}),
                "sender_id": sender, "sender_name": name, "message_id": event_id,
                "sent_at": sent_at, "addressed": bool(addressed), "text": text,
                "segments": segments, "reply_handle": room_id}

    async def member_name(self, room_id: str, user_id: str) -> str:
        key = (room_id, user_id)
        if key not in self.names:
            try:
                member = await self.call("GET", f"/rooms/{quote(room_id, safe='')}/state/m.room.member/"
                                                f"{quote(user_id, safe='')}")
                self.names[key] = plain_name(member.get("displayname"), localpart(user_id))
            except (ConnectionError, Refused):
                return localpart(user_id)
        return self.names[key]

    async def _parent(self, room_id: str, event_id: str) -> tuple[str, str] | None:
        if event_id in self.recent:
            return self.recent[event_id]
        try:
            source = await self.call("GET", f"/rooms/{quote(room_id, safe='')}/event/{quote(event_id, safe='')}")
        except (ConnectionError, Refused):
            return None
        if not source.get("sender"):
            return None
        found = (str(source["sender"]), plain_text(str(source.get("type") or ""), _mapping(source.get("content"))))
        self._remember(event_id, *found)
        return found

    async def _image(self, content: dict) -> dict | None:
        """Authenticated media needs the token, so the bytes go inline, never a URL."""
        mxc = str(content.get("url") or "")
        size = _mapping(content.get("info")).get("size")
        if not mxc.startswith("mxc://") or (isinstance(size, int) and size > MAX_INLINE_IMAGE_BYTES):
            return None     # encrypted media ("file") cannot be opened without keys
        server, _, media = mxc[len("mxc://"):].partition("/")
        if not server or not media:
            return None
        where = f"{quote(server, safe='')}/{quote(media, safe='')}"
        for path in (f"/_matrix/client/v1/media/download/{where}", f"/_matrix/media/v3/download/{where}"):
            data = await self._download(self.base + path)
            if data is not None:
                return {"type": "image", "b64": base64.b64encode(data).decode()} if data else None
        return None

    async def _download(self, url: str) -> bytes | None:
        """The bytes, b"" when too big or refused, None to try the older endpoint."""
        try:
            async with self.client.stream("GET", url, headers=self._headers(), timeout=CALL_TIMEOUT_S,
                                          follow_redirects=True) as response:
                if response.status_code in (404, 405):
                    return None     # a server from before authenticated media (Matrix 1.11)
                if response.status_code != 200:
                    return b""
                data = bytearray()
                async for chunk in response.aiter_bytes():
                    data.extend(chunk)
                    if len(data) > MAX_INLINE_IMAGE_BYTES:
                        return b""
                return bytes(data)
        except httpx.HTTPError:
            return b""

    async def _typing(self, room_id: str, typing: bool) -> None:
        body: dict = {"typing": typing, **({"timeout": TYPING_MS} if typing else {})}
        try:
            await self.call("PUT", f"/rooms/{quote(room_id, safe='')}/typing/{quote(self.bot_id, safe='')}",
                            json=body, timeout=10)
        except (ConnectionError, Refused):
            pass        # an indicator must never cost a reply

    # ------------------------------------------------------------ sending

    def target(self, delivery: dict) -> tuple[str, str, str]:
        room = str(delivery.get("reply_handle") or "")
        if not room.startswith("!") or self.rooms.get(room, {}).get("encrypted"):
            raise Unsupported()
        return room, "", ""

    def _next_txn(self) -> str:
        self._txn += 1
        return f"pa{int(time.time() * 1000)}.{self._txn}.{secrets.token_hex(4)}"

    async def _post(self, room_id: str, content: dict) -> str:
        answer = await self.call("PUT", f"/rooms/{quote(room_id, safe='')}/send/m.room.message/"
                                        f"{self._next_txn()}", json=content)
        return str(answer.get("event_id") or "")

    async def send(self, target: Any, items: list) -> int:
        if isinstance(target, str):
            target = (target, "", "")
        room_id, thread, reply_to = target
        if self.rooms.get(room_id, {}).get("encrypted"):
            logger.warning("matrix: not replying in an encrypted room")
            return 0
        relation = ({"rel_type": "m.thread", "event_id": thread, "is_falling_back": True,
                     "m.in_reply_to": {"event_id": reply_to or thread}} if thread else None)
        sent = 0
        try:
            for item in items:
                mention = raw_id(item.get("mention_user_id"), self.kind)
                if not mention.startswith("@") or mention == self.bot_id or self.is_direct(room_id):
                    mention = ""
                try:
                    if item.get("type") == "image" and item.get("b64"):
                        content = await self._image_content(base64.b64decode(item["b64"]))
                        await self._post(room_id, {**content, **({"m.relates_to": relation} if relation else {})})
                    elif item.get("type") == "text" and str(item.get("text") or "").strip():
                        name = (await self.member_name(room_id, mention))[:60] if mention else ""
                        for i, piece in enumerate(split_text(str(item["text"]), MAX_TEXT)):
                            content = text_content(piece, (mention, name) if i == 0 and mention else None)
                            if relation:
                                content["m.relates_to"] = relation
                            event_id = await self._post(room_id, content)
                            self._remember(event_id, self.bot_id, piece)
                    else:
                        continue
                except (ConnectionError, Refused, ValueError) as exc:
                    logger.warning("matrix: sending stopped after %d item(s) (%s)", sent, exc)
                    break
                sent += 1
        finally:
            await self._typing(room_id, False)
        return sent

    async def _image_content(self, data: bytes) -> dict:
        mimetype, extension = image_type(data)
        filename = f"image.{extension}"
        uploaded = await self._upload(data, mimetype, filename)
        return {"msgtype": "m.image", "body": filename, "filename": filename, "url": uploaded,
                "info": {"mimetype": mimetype, "size": len(data)}, "m.mentions": {}}

    async def _upload(self, data: bytes, mimetype: str, filename: str) -> str:
        for _ in range(5):
            try:
                response = await self.client.post(self.base + "/_matrix/media/v3/upload",
                                                  params={"filename": filename}, content=data,
                                                  headers={**self._headers(), "Content-Type": mimetype},
                                                  timeout=60)
            except httpx.HTTPError as exc:
                raise ConnectionError(f"upload: {type(exc).__name__}") from None
            try:
                body = _mapping(response.json())
            except ValueError:
                body = {}
            if response.status_code == 429 or body.get("errcode") == "M_LIMIT_EXCEEDED":
                await asyncio.sleep(_retry_after(response, body))
                continue
            if response.status_code == 401:
                raise Refused("token_rejected")
            uri = str(body.get("content_uri") or "")
            if response.status_code >= 400 or not uri.startswith("mxc://"):
                raise ConnectionError(f"upload: {response.status_code} {body.get('errcode') or ''}".rstrip())
            return uri
        raise ConnectionError("upload: rate limited")

    async def close(self) -> None:
        await self.client.aclose()


def text_content(text: str, mention: tuple[str, str] | None = None) -> dict:
    """An m.text message. An empty m.mentions pings nobody, so no client
    guesses a mention from a name that happens to be in the text."""
    content: dict = {"msgtype": "m.text", "body": text, "m.mentions": {}}
    if mention:
        user_id, name = mention
        content["body"] = f"{name} {text}"
        content["format"] = HTML_FORMAT
        content["formatted_body"] = f"{pill(user_id, name)} " + html.escape(text).replace("\n", "<br>")
        content["m.mentions"] = {"user_ids": [user_id]}
    return content


def _retry_after(response: httpx.Response, body: dict) -> float:
    """Retry-After (preferred since Matrix 1.10), else retry_after_ms."""
    try:
        wait = float(response.headers.get("retry-after") or 0)
    except ValueError:
        wait = 0.0
    if not wait:
        try:
            wait = float(body.get("retry_after_ms") or 0) / 1000
        except (TypeError, ValueError):
            wait = 0.0
    return min(max(wait, 1.0), RATE_LIMIT_MAX_S)


def _where(path: str) -> str:
    return path.split("?")[0]
