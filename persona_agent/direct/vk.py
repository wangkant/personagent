"""VK community bots through the Bots Long Poll API
(https://dev.vk.com/ru/api/bots-long-poll/getting-started): message_new in,
messages.send out, with a community access token."""
from __future__ import annotations

import asyncio
import base64
import logging
import random
import re
from typing import Any

import httpx

from .base import (MAX_INLINE_IMAGE_BYTES, Platform, Refused, Unsupported, backoff_sleep,
                   has_content, media, plain_name, raw_id, split_text)

logger = logging.getLogger("personagent.direct.vk")

API = "https://api.vk.com/method"
VERSION = "5.199"
WAIT_S = 25
# peer_id of a group chat is 2000000000 + its chat id.
CHAT_PEER = 2_000_000_000
MAX_TEXT = 4096
MAX_NAME = 60
# Too many requests per second / flood control / rate limit reached.
RATE_LIMITED = {6: 1.0, 9: 5.0, 29: 10.0}
# Unknown error / internal server error: worth another try later.
TRANSIENT = {1, 10}
# Permission denied / access denied / method unavailable with this token.
NO_RIGHTS = {7, 15, 27}


class ApiError(Exception):
    """An error answer from the API; the message never carries the token."""

    def __init__(self, method: str, code: int, text: str = ""):
        super().__init__(f"{method}: {code}")
        self.code = code
        self.text = text


class VK(Platform):
    kind = "vk"

    def __init__(self, values: dict, *, client: httpx.AsyncClient | None = None):
        super().__init__(values)
        self.token = str(values.get("vk_token") or "").strip()
        self.client = client or httpx.AsyncClient(timeout=WAIT_S + 20)
        self.group_id = 0
        self.screen_name = ""
        self.names: dict[str, str] = {}

    async def call(self, method: str, **params) -> Any:
        """One API call; the token goes in the POST body, never in a URL or a log."""
        body = {k: v for k, v in params.items() if v is not None}
        body.update(access_token=self.token, v=VERSION)
        for _ in range(5):
            try:
                response = await self.client.post(f"{API}/{method}", data=body)
            except httpx.HTTPError as exc:
                raise ConnectionError(f"{method}: {type(exc).__name__}") from None
            if response.status_code >= 500 or response.status_code == 429:
                raise ConnectionError(f"{method}: {response.status_code}")
            try:
                answer = response.json()
            except ValueError:
                raise ConnectionError(f"{method}: not json") from None
            error = answer.get("error") if isinstance(answer, dict) else None
            if not error:
                return answer.get("response") if isinstance(answer, dict) else None
            code = int(error.get("error_code") or 0)
            if code in RATE_LIMITED:
                await asyncio.sleep(RATE_LIMITED[code])
                continue
            if code in (5, 28):
                raise Refused("token_rejected")
            if code in TRANSIENT:
                raise ConnectionError(f"{method}: {code}")
            raise ApiError(method, code, str(error.get("error_msg") or ""))
        raise ConnectionError(f"{method}: rate limited")

    async def check(self) -> str:
        try:
            # With a community token and no ids this answers with the community itself.
            found = await self.call("groups.getById")
        except ApiError:
            raise Refused("token_rejected") from None
        groups = found.get("groups") if isinstance(found, dict) else found
        if not groups:
            raise Refused("token_rejected")
        group = groups[0]
        if group.get("deactivated"):
            raise Refused("bot_banned")
        self.group_id = int(group["id"])
        # A community writes as -id; users have positive ids that may equal the group's.
        self.bot_id = str(-self.group_id)
        self.screen_name = str(group.get("screen_name") or "")
        try:
            settings = await self.call("groups.getLongPollSettings", group_id=self.group_id)
        except ApiError as exc:
            raise _refusal(exc) from None
        if not settings.get("is_enabled"):
            raise Refused("long_poll_off")
        if not int((settings.get("events") or {}).get("message_new") or 0):
            raise Refused("message_events_off")
        return plain_name(group.get("name"), self.screen_name, str(self.group_id))

    async def _server(self) -> dict:
        try:
            server = await self.call("groups.getLongPollServer", group_id=self.group_id)
        except ApiError as exc:
            raise _refusal(exc) from None
        url = str(server.get("server") or "")
        if not url.startswith("http"):
            url = "https://" + url
        return {"server": url, "key": str(server.get("key") or ""), "ts": str(server.get("ts") or "")}

    async def _poll(self, session: dict) -> dict:
        try:
            # The key sits in the query string; httpx's own log is kept at WARNING.
            response = await self.client.get(session["server"], params={
                "act": "a_check", "key": session["key"], "ts": session["ts"], "wait": WAIT_S})
        except httpx.HTTPError as exc:
            raise ConnectionError(f"poll: {type(exc).__name__}") from None
        if response.status_code >= 400:
            raise ConnectionError(f"poll: {response.status_code}")
        try:
            return response.json()
        except ValueError:
            raise ConnectionError("poll: not json") from None

    async def run(self, on_event, connected) -> None:
        await self.check()
        session = await self._server()
        connected()
        failures = 0
        while True:
            try:
                if not session.get("key"):
                    kept = {"ts": session["ts"]} if session.get("ts") else {}
                    session = {**await self._server(), **kept}
                answer = await self._poll(session)
                if failures:
                    connected()     # back after a drop
                failures = 0
            except ConnectionError as exc:
                logger.warning("vk: %s", exc)
                self.dropped()
                await backoff_sleep(failures)
                failures += 1
                continue
            failed = answer.get("failed")
            if failed == 1:
                session["ts"] = str(answer.get("ts") or session["ts"])
                continue
            if failed == 2:
                session["key"] = ""     # only the key expired; keep reading from ts
                continue
            if failed == 3:
                session = {}            # key and ts are both lost
                continue
            if failed:
                raise ConnectionError(f"poll: failed {failed}")
            session["ts"] = str(answer.get("ts") or session["ts"])
            for update in answer.get("updates") or []:
                if update.get("type") != "message_new":
                    continue
                payload = update.get("object") or {}
                message = payload.get("message") if isinstance(payload.get("message"), dict) else payload
                event = await self.event(message)
                if event:
                    await on_event(event, event["reply_handle"])

    async def event(self, message: dict) -> dict | None:
        sender = int(message.get("from_id") or 0)
        peer = int(message.get("peer_id") or 0)
        # Other communities and the bot itself write with negative ids.
        if sender <= 0 or message.get("out") or message.get("action"):
            return None
        uid = str(sender)
        name = await self._name(uid)
        is_dm = peer < CHAT_PEER
        raw = str(message.get("text") or "")
        mentioned = bool(self._mention_re().search(raw))
        text = _readable(self._mention_re().sub("", raw)).strip()
        addressed = is_dm or mentioned
        segments: list[dict] = []
        quoted = message.get("reply_message")
        if isinstance(quoted, dict):
            author = int(quoted.get("from_id") or 0)
            if self.group_id and author == -self.group_id:
                addressed = True
            segments.append({"type": "reply", "message_id": str(quoted.get("id") or quoted.get("conversation_message_id") or ""),
                             "text": _readable(str(quoted.get("text") or "")),
                             "sender_id": str(author or ""),
                             "sender_name": self.names.get(str(author), "") if author > 0 else ""})
        if mentioned and not is_dm:
            segments.append({"type": "mention", "user_id": self.bot_id, "name": self.screen_name})
        if text:
            segments.append({"type": "text", "text": text})
        for attachment in message.get("attachments") or []:
            segments.append(await self._attachment(attachment))
        if message.get("fwd_messages"):
            segments.append({"type": "text", "text": "(forwarded messages)"})
        if not has_content(segments, self.bot_id):
            return None
        return {"conversation_type": "dm" if is_dm else "group",
                **({} if is_dm else {"conversation_id": str(peer)}),
                "sender_id": uid, "sender_name": name,
                "message_id": str(message.get("id") or message.get("conversation_message_id") or ""),
                "sent_at": int(message.get("date") or 0),
                "addressed": addressed, "text": text, "segments": segments,
                "reply_handle": str(peer)}

    def _mention_re(self) -> re.Pattern:
        names = [f"club{self.group_id}", f"public{self.group_id}"]
        if self.screen_name:
            names.append(re.escape(self.screen_name))
        alt = "|".join(names)
        return re.compile(rf"\[(?:{alt})\|[^\]]*\]|@(?:{alt})\b(?:\s*\([^)]*\))?", re.IGNORECASE)

    async def _name(self, uid: str) -> str:
        if uid in self.names:
            return self.names[uid]
        try:
            users = await self.call("users.get", user_ids=uid)
            user = (users or [{}])[0]
            name = plain_name(" ".join(filter(None, (user.get("first_name"), user.get("last_name")))), uid)
        except (ApiError, ConnectionError, Refused, IndexError, AttributeError):
            name = uid
        self.names[uid] = name
        return name

    async def _attachment(self, attachment: dict) -> dict:
        kind = str(attachment.get("type") or "")
        if kind == "photo":
            image = await self._photo(attachment.get("photo") or {})
            return image or media("photo")
        if kind == "sticker":
            sticker = attachment.get("sticker") or {}
            return {"type": "emoji", "name": "sticker", "id": str(sticker.get("sticker_id") or "")}
        body = attachment.get(kind) if isinstance(attachment.get(kind), dict) else {}
        if kind == "audio_message":
            return media("voice", transcript=body.get("transcript"))
        if kind == "video":
            return media("video")
        if kind == "graffiti":
            return media("photo")
        if kind == "doc":
            return media("file", name=body.get("title"))
        if kind == "audio":
            return media("file", name=" - ".join(filter(None, (body.get("artist"), body.get("title")))))
        notes = {"wall": "(shared a post)", "link": "(sent a link)", "poll": "(sent a poll)"}
        return {"type": "text", "text": notes.get(kind, "(sent an attachment)")}

    async def _photo(self, photo: dict) -> dict | None:
        sizes = [s for s in photo.get("sizes") or [] if s.get("url")]
        if not sizes:
            return None
        best = max(sizes, key=lambda s: int(s.get("width") or 0) * int(s.get("height") or 0))
        data = bytearray()
        try:
            async with self.client.stream("GET", best["url"]) as response:
                if response.status_code >= 400:
                    return None
                async for chunk in response.aiter_bytes():
                    data.extend(chunk)
                    if len(data) > MAX_INLINE_IMAGE_BYTES:
                        return None
        except httpx.HTTPError:
            return None
        return {"type": "image", "b64": base64.b64encode(bytes(data)).decode()} if data else None

    def target(self, delivery: dict) -> str:
        handle = str(delivery.get("reply_handle") or delivery.get("conversation_id") or "")
        if not handle.lstrip("-").isdigit():
            raise Unsupported()
        return handle

    async def send(self, target: str, items: list) -> int:
        sent = 0
        for item in items:
            try:
                if item.get("type") == "image" and item.get("b64"):
                    attachment = await self._upload(target, base64.b64decode(item["b64"]))
                    await self.call("messages.send", peer_id=target, random_id=_random_id(),
                                    attachment=attachment)
                elif item.get("type") == "text" and str(item.get("text") or "").strip():
                    mention = raw_id(item.get("mention_user_id"), self.kind)
                    for i, piece in enumerate(split_text(str(item["text"]), MAX_TEXT - MAX_NAME - 20)):
                        if i == 0 and mention.isdigit():
                            name = re.sub(r"[\[\]|]", "", self.names.get(mention, "") or f"id{mention}")
                            piece = f"[id{mention}|{name[:MAX_NAME]}] {piece}"
                        await self.call("messages.send", peer_id=target, random_id=_random_id(),
                                        message=piece)
                else:
                    continue
            except (ConnectionError, Refused, ApiError, ValueError) as exc:
                logger.warning("vk: sending stopped after %d item(s) (%s)", sent, exc)
                break
            sent += 1
        return sent

    async def _upload(self, peer: str, data: bytes) -> str:
        server = await self.call("photos.getMessagesUploadServer", peer_id=peer)
        try:
            response = await self.client.post(str(server["upload_url"]),
                                              files={"photo": (_filename(data), data)})
            uploaded = response.json()
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            raise ConnectionError("photo upload failed") from None
        if not uploaded.get("photo") or uploaded.get("photo") == "[]":
            raise ConnectionError("photo upload failed")
        saved = await self.call("photos.saveMessagesPhoto", photo=uploaded["photo"],
                                server=uploaded.get("server"), hash=uploaded.get("hash"))
        try:
            photo = saved[0]
            key = f"_{photo['access_key']}" if photo.get("access_key") else ""
            return f"photo{photo['owner_id']}_{photo['id']}{key}"
        except (IndexError, KeyError, TypeError):
            raise ConnectionError("photo save failed") from None

    async def close(self) -> None:
        await self.client.aclose()


def _refusal(exc: ApiError) -> Exception:
    if exc.code == 100 and "longpoll" in exc.text.replace(" ", "").lower():
        return Refused("long_poll_off")
    if exc.code in NO_RIGHTS:
        return Refused("token_rights_missing")
    return ConnectionError(str(exc))


def _readable(text: str) -> str:
    """[id42|Alex] and [club7|Shop] become @Alex and @Shop."""
    return re.sub(r"\[(?:id|club|public)\d+\|([^\]]*)\]", r"@\1", text)


def _random_id() -> int:
    # Lets VK drop a duplicate if a request is retried.
    return random.randint(1, 2**31 - 1)


def _filename(data: bytes) -> str:
    if data.startswith(b"\x89PNG"):
        return "image.png"
    if data.startswith(b"GIF8"):
        return "image.gif"
    return "image.jpg"
