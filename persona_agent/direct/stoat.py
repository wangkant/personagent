"""Stoat, formerly Revolt (https://developers.stoat.chat): Bonfire events over
a WebSocket in, POST /channels/{id}/messages out, images through Autumn."""
from __future__ import annotations

import asyncio
import base64
import collections
import json
import logging
import time
import uuid
from typing import Any
from urllib.parse import urlsplit

import httpx

from .base import (MAX_INLINE_IMAGE_BYTES, Platform, Refused, Unsupported, backoff_sleep,
                   plain_name, raw_id, split_text)

logger = logging.getLogger("personagent.direct.stoat")

API = "https://api.stoat.chat"
MAX_TEXT = 2000
# The docs ask for a Ping every 10 to 30 seconds.
PING_S = 20
# How long a server's "the owner is a member here" answer is trusted.
ROOM_TTL_S = 600
# Bonfire errors and REST error types that mean the token is no good.
BAD_TOKEN = {"InvalidSession", "InvalidToken", "NotAuthenticated", "OnboardingNotFinished"}
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
ULID_DIGITS = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


class HTTPStatus(ConnectionError):
    def __init__(self, label: str, status: int):
        super().__init__(f"{label}: {status}")
        self.status = status


def ulid_seconds(ulid: str) -> int:
    """Stoat ids are ULIDs: the first ten digits are the creation time in ms."""
    ms = 0
    try:
        for char in str(ulid)[:10].upper():
            ms = ms * 32 + ULID_DIGITS.index(char)
    except ValueError:
        return 0
    return ms // 1000 if len(str(ulid)) >= 10 else 0


def image_type(data: bytes) -> tuple[str, str]:
    if data.startswith(b"\xff\xd8"):
        return "image.jpg", "image/jpeg"
    if data.startswith(b"GIF8"):
        return "image.gif", "image/gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image.webp", "image/webp"
    return "image.png", "image/png"


class Stoat(Platform):
    kind = "stoat"

    def __init__(self, values: dict, *, client: httpx.AsyncClient | None = None, connect=None):
        super().__init__(values)
        self.token = str(values.get("stoat_token") or "")
        self.api = str(values.get("stoat_api") or API).rstrip("/")
        self.client = client or httpx.AsyncClient(timeout=30)
        self._connect = connect
        self.owner_id = ""
        self.own_names: list[str] = []
        self.max_text = MAX_TEXT
        self.root: dict | None = None
        self.channels: dict[str, dict] = {}
        self.users: dict[str, dict] = {}
        self.rooms: dict[str, tuple[bool, float]] = {}
        self.mine: collections.deque = collections.deque(maxlen=500)

    # ------------------------------------------------------------ rest

    def _headers(self) -> dict:
        return {"X-Bot-Token": self.token}

    async def request(self, method: str, url: str, label: str, **kwargs) -> Any:
        """One call, waiting out a 429 and an empty bucket; the token never reaches a log."""
        for _ in range(5):
            try:
                response = await self.client.request(method, url, headers={
                    **self._headers(), **kwargs.get("headers", {})},
                    **{k: v for k, v in kwargs.items() if k != "headers"})
            except httpx.HTTPError as exc:
                raise ConnectionError(f"{label}: {type(exc).__name__}") from None
            try:
                answer = response.json() if response.content else None
            except ValueError:
                answer = None
            error = answer.get("type") if isinstance(answer, dict) else None
            if response.status_code == 429:
                wait = answer.get("retry_after") if isinstance(answer, dict) else None
                wait = wait if wait is not None else response.headers.get("x-ratelimit-reset-after") or 3000
                await asyncio.sleep(float(wait) / 1000)
                continue
            if response.status_code == 401 or error in BAD_TOKEN:
                raise Refused("token_rejected")
            if response.status_code >= 400:
                raise HTTPStatus(f"{label} {error or ''}".strip(), response.status_code)
            if response.headers.get("x-ratelimit-remaining") == "0":
                # The bucket is empty: wait for it rather than earn a 429.
                await asyncio.sleep(float(response.headers.get("x-ratelimit-reset-after") or 0) / 1000)
            return answer
        raise ConnectionError(f"{label}: rate limited")

    async def rest(self, method: str, path: str, **kwargs) -> Any:
        return await self.request(method, self.api + path, path.split("/")[1], **kwargs)

    async def _root(self) -> dict:
        """The API root names the events and file servers, so self-hosted instances work."""
        if self.root is not None:
            return self.root
        parts = urlsplit(self.api)
        if parts.scheme != "https" and (parts.hostname or "") not in LOCAL_HOSTS:
            raise Refused("insecure_address")
        try:
            response = await self.client.get(self.api + "/")
            root = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ConnectionError(f"root: {type(exc).__name__}") from None
        if response.status_code >= 400 or not isinstance(root, dict) or not root.get("ws"):
            raise ConnectionError(f"root: {response.status_code}")
        limits = ((root.get("features") or {}).get("limits") or {}).get("default") or {}
        if isinstance(limits.get("message_length"), int) and limits["message_length"] > 100:
            self.max_text = limits["message_length"]
        self.root = root
        return root

    def _autumn(self) -> str:
        autumn = ((self.root or {}).get("features") or {}).get("autumn") or {}
        return str(autumn.get("url") or "").rstrip("/") if autumn.get("enabled") else ""

    async def check(self) -> str:
        await self._root()
        me = await self.rest("GET", "/users/@me")
        if not isinstance(me, dict) or not me.get("bot"):
            # A person's session token: this connects bots only.
            raise Refused("token_rejected")
        self.bot_id = str(me["_id"])
        self.users[self.bot_id] = me
        self.owner_id = str((me.get("bot") or {}).get("owner") or "")
        self.own_names = [n.lower() for n in (me.get("display_name"), me.get("username")) if n]
        return plain_name(me.get("display_name"), me.get("username"), self.bot_id)

    # ------------------------------------------------------------ events

    async def _open(self, url: str):
        if self._connect is not None:
            return await self._connect(url)
        import websockets

        return await websockets.connect(url, max_size=None, open_timeout=30)

    async def run(self, on_event, connected) -> None:
        await self.check()
        ws = str(self.root["ws"])
        url = ws + ("&" if "?" in ws else "?") + "version=1&format=json"
        failures = 0
        while True:
            try:
                if await self._session(url, on_event, connected):
                    failures = 0
                logger.warning("stoat: the events connection closed")
            except Refused:
                raise
            except Exception as exc:
                logger.warning("stoat: events connection dropped (%s)", type(exc).__name__)
            self.dropped()
            await backoff_sleep(failures)
            failures += 1

    async def _session(self, url: str, on_event, connected) -> bool:
        """One connection until it closes; True if it got as far as Ready."""
        socket = await self._open(url)
        state = {"ready": False}
        ponged = asyncio.Event()
        ponged.set()

        async def ping() -> None:
            while True:
                await asyncio.sleep(PING_S)
                if not ponged.is_set():
                    await socket.close()        # no Pong: a dead connection
                    return
                ponged.clear()
                await socket.send(json.dumps({"type": "Ping", "data": int(time.time() * 1000)}))

        pinger = None
        try:
            # Sent as a frame, not in the URL, so the token is never part of an address.
            await socket.send(json.dumps({"type": "Authenticate", "token": self.token}))
            pinger = asyncio.create_task(ping())
            async for raw in socket:
                frame = json.loads(raw)
                for item in (frame.get("v") or []) if frame.get("type") == "Bulk" else [frame]:
                    if isinstance(item, dict):
                        await self._frame(item, state, ponged, on_event, connected)
        finally:
            if pinger is not None:
                pinger.cancel()
            await socket.close()
        return state["ready"]

    async def _frame(self, frame: dict, state: dict, ponged, on_event, connected) -> None:
        kind = frame.get("type")
        if kind == "Pong":
            ponged.set()
        elif kind == "Error":
            error = str(frame.get("error") or "")
            if error in BAD_TOKEN:
                raise Refused("token_rejected")
            if error != "AlreadyAuthenticated":
                raise ConnectionError(f"bonfire: {error}")
        elif kind == "Logout":
            raise Refused("token_rejected")
        elif kind == "Ready":
            for user in frame.get("users") or []:
                self.users[str(user.get("_id"))] = user
            for channel in frame.get("channels") or []:
                self.channels[str(channel.get("_id"))] = channel
            state["ready"] = True
            connected()
        elif kind == "ChannelCreate":
            self.channels[str(frame.get("_id"))] = frame
        elif kind in ("ChannelUpdate", "ChannelDelete"):
            self.channels.pop(str(frame.get("id")), None)   # fetched again when next needed
        elif kind in ("ChannelGroupJoin", "ChannelGroupLeave"):
            channel = self.channels.get(str(frame.get("id")))
            if channel is not None:
                people = set(channel.get("recipients") or [])
                (people.add if kind == "ChannelGroupJoin" else people.discard)(str(frame.get("user")))
                channel["recipients"] = sorted(people)
        elif kind in ("ServerMemberJoin", "ServerMemberLeave"):
            if str(frame.get("user")) == self.owner_id:
                self.rooms[str(frame.get("id"))] = (kind == "ServerMemberJoin", time.monotonic() + ROOM_TTL_S)
        elif kind == "Message":
            found = await self.event(frame)
            if found:
                await on_event(*found)

    async def _channel(self, cid: str) -> dict | None:
        if cid not in self.channels:
            try:
                self.channels[cid] = await self.rest("GET", f"/channels/{cid}")
            except ConnectionError:
                return None
        return self.channels[cid]

    async def _user(self, uid: str, given: Any) -> dict:
        if isinstance(given, dict) and given.get("_id"):
            self.users[uid] = given
        if uid not in self.users:
            try:
                self.users[uid] = await self.rest("GET", f"/users/{uid}") or {}
            except ConnectionError:
                return {}
        return self.users[uid]

    async def room_allowed(self, channel: dict) -> bool:
        """Only rooms the owner is in: a stranger cannot pull the bot in to spend the owner's budget."""
        if not self.owner_id:
            return False
        if channel.get("channel_type") == "Group":
            return self.owner_id in (channel.get("recipients") or [])
        server = str(channel.get("server") or "")
        if not server:
            return False
        known = self.rooms.get(server)
        if known and known[1] > time.monotonic():
            return known[0]
        try:
            await self.rest("GET", f"/servers/{server}/members/{self.owner_id}")
            answer, ttl = True, ROOM_TTL_S
        except HTTPStatus as exc:
            answer, ttl = False, ROOM_TTL_S if exc.status == 404 else 60
        except ConnectionError:
            answer, ttl = False, 60
        self.rooms[server] = (answer, time.monotonic() + ttl)
        return answer

    async def event(self, message: dict) -> tuple[dict, str] | None:
        author = str(message.get("author") or "")
        mid = str(message.get("_id") or "")
        if author and author == self.bot_id:
            self.mine.append(mid)
            return None
        if not author or message.get("webhook") or message.get("system"):
            return None
        cid = str(message.get("channel") or "")
        channel = await self._channel(cid)
        if not channel or channel.get("channel_type") == "SavedMessages":
            return None
        is_dm = channel.get("channel_type") == "DirectMessage"
        user = await self._user(author, message.get("user"))
        if user.get("bot"):
            return None
        if not is_dm and not await self.room_allowed(channel):
            return None
        name = plain_name((message.get("member") or {}).get("nickname"), user.get("display_name"),
                          user.get("username"), author)
        text = str(message.get("content") or "")
        tag = f"<@{self.bot_id}>"
        mentioned = self.bot_id in (message.get("mentions") or []) or tag in text
        lowered = text.lower()
        called = any(lowered.startswith(n) and not lowered[len(n):len(n) + 1].isalnum()
                     for n in self.own_names)
        text = text.replace(tag, "").strip()
        segments: list[dict] = []
        to_bot = False
        replies = message.get("replies") or []
        if replies:
            rid = str(replies[0])
            quoted = await self._quoted(cid, rid)
            quoted_author = str(quoted.get("author") or "")
            to_bot = rid in self.mine or (bool(quoted_author) and quoted_author == self.bot_id)
            quoted_user = self.users.get(quoted_author) or {}
            segments.append({"type": "reply", "message_id": rid, "text": str(quoted.get("content") or ""),
                             "sender_id": quoted_author,
                             "sender_name": plain_name(quoted_user.get("display_name"),
                                                       quoted_user.get("username"))})
        if mentioned:
            segments.append({"type": "mention", "user_id": self.bot_id, "name": ""})
        if text:
            segments.append({"type": "text", "text": text})
        for attachment in message.get("attachments") or []:
            if str(attachment.get("content_type") or "").startswith("image/"):
                image = await self._image(attachment)
                segments.append(image or {"type": "text", "text": "(sent a photo)"})
            else:
                segments.append({"type": "text", "text": f"(sent a file: {attachment.get('filename', '')})"})
        if not any(s["type"] in ("text", "image") for s in segments):
            return None
        event = {"conversation_type": "dm" if is_dm else "group",
                 **({} if is_dm else {"conversation_id": cid}),
                 "sender_id": author, "sender_name": name, "message_id": mid,
                 "sent_at": ulid_seconds(mid) or int(time.time()),
                 "addressed": is_dm or mentioned or to_bot or called,
                 "text": text, "segments": segments, "reply_handle": cid}
        return event, f"{cid}/{mid}"

    async def _quoted(self, cid: str, rid: str) -> dict:
        try:
            return await self.rest("GET", f"/channels/{cid}/messages/{rid}") or {}
        except ConnectionError:
            return {}

    async def _image(self, attachment: dict) -> dict | None:
        autumn = self._autumn()
        if not autumn or int(attachment.get("size") or 0) > MAX_INLINE_IMAGE_BYTES:
            return None
        try:
            # File reads need no token, so none is sent to the file server.
            response = await self.client.get(f"{autumn}/{attachment.get('tag') or 'attachments'}/"
                                             f"{attachment.get('_id')}", follow_redirects=True)
            response.raise_for_status()
        except httpx.HTTPError:
            return None
        if not response.content or len(response.content) > MAX_INLINE_IMAGE_BYTES:
            return None
        return {"type": "image", "b64": base64.b64encode(response.content).decode()}

    # ------------------------------------------------------------ out

    def target(self, delivery: dict) -> str:
        handle = str(delivery.get("reply_handle") or delivery.get("conversation_id") or "")
        if not handle:
            raise Unsupported()
        return handle

    async def _post(self, channel: str, body: dict, reply: str) -> None:
        if reply:
            body["replies"] = [{"id": reply, "mention": False, "fail_if_not_exists": False}]
        # The same key on a retried request keeps it from being posted twice.
        sent = await self.rest("POST", f"/channels/{channel}/messages", json=body,
                               headers={"Idempotency-Key": uuid.uuid4().hex})
        if isinstance(sent, dict) and sent.get("_id"):
            self.mine.append(str(sent["_id"]))

    async def send(self, target: str, items: list) -> int:
        channel, _, reply = target.partition("/")
        sent = 0
        for item in items:
            try:
                if item.get("type") == "image" and item.get("b64"):
                    if self.root is None:
                        await self._root()
                    autumn = self._autumn()
                    if not autumn:
                        continue            # this instance has no file server
                    data = base64.b64decode(item["b64"])
                    filename, mime = image_type(data)
                    uploaded = await self.request("POST", f"{autumn}/attachments", "autumn",
                                                  files={"file": (filename, data, mime)})
                    await self._post(channel, {"attachments": [str(uploaded["id"])]}, reply)
                elif item.get("type") == "text" and str(item.get("text") or "").strip():
                    mention = raw_id(item.get("mention_user_id"), self.kind)
                    for i, piece in enumerate(split_text(str(item["text"]), self.max_text - 40)):
                        lead = f"<@{mention}> " if i == 0 and mention else ""
                        await self._post(channel, {"content": lead + piece}, reply)
                        reply = ""
                else:
                    continue
            except (ConnectionError, Refused, KeyError, TypeError, ValueError) as exc:
                logger.warning("stoat: sending stopped after %d item(s) (%s)", sent, type(exc).__name__)
                break
            reply = ""
            sent += 1
        return sent

    async def close(self) -> None:
        await self.client.aclose()
