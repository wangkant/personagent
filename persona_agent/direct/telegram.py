"""Telegram through the Bot API (https://core.telegram.org/bots/api):
long-polled getUpdates in, sendMessage and sendPhoto out."""
from __future__ import annotations

import asyncio
import base64
import logging
from typing import Any

import httpx

from .base import (MAX_INLINE_IMAGE_BYTES, Platform, Refused, Unsupported, backoff_sleep,
                   plain_name, raw_id, split_text)

logger = logging.getLogger("personagent.direct.telegram")

API = "https://api.telegram.org"
POLL_S = 50
# sendMessage takes 4096 characters after entity parsing; plain text is sent.
MAX_TEXT = 4096


def utf16_len(text: str) -> int:
    """Entity offsets and lengths count UTF-16 code units."""
    return len(text.encode("utf-16-le")) // 2


class Telegram(Platform):
    kind = "telegram"

    def __init__(self, values: dict, *, client: httpx.AsyncClient | None = None):
        super().__init__(values)
        self.token = str(values.get("telegram_token") or "")
        self.client = client or httpx.AsyncClient(timeout=POLL_S + 15)
        self.username = ""
        self.names: dict[str, str] = {}

    def _url(self, method: str) -> str:
        return f"{API}/bot{self.token}/{method}"

    async def call(self, method: str, **kwargs) -> Any:
        """One API call, waiting out a 429; the token never reaches a log."""
        for _ in range(5):
            try:
                response = await self.client.post(self._url(method), **kwargs)
            except httpx.HTTPError as exc:
                raise ConnectionError(f"{method}: {type(exc).__name__}") from None
            try:
                answer = response.json()
            except ValueError:
                answer = {}
            if answer.get("ok"):
                return answer.get("result")
            code = answer.get("error_code") or response.status_code
            if code == 429:
                await asyncio.sleep(float((answer.get("parameters") or {}).get("retry_after") or 3))
                continue
            if code in (401, 404):
                raise Refused("token_rejected")
            if code == 409:
                # Another getUpdates poller or a webhook holds this bot.
                raise Refused("bot_in_use")
            raise ConnectionError(f"{method}: {code}")
        raise ConnectionError(f"{method}: rate limited")

    async def check(self) -> str:
        me = await self.call("getMe")
        self.bot_id = str(me["id"])
        self.username = str(me.get("username") or "")
        return self.username or self.bot_id

    async def run(self, on_event, connected) -> None:
        await self.check()
        # A webhook left by another tool makes getUpdates fail with 409.
        await self.call("deleteWebhook", json={"drop_pending_updates": False})
        connected()
        offset, failures = 0, 0
        while True:
            try:
                updates = await self.call("getUpdates", json={
                    "offset": offset, "timeout": POLL_S, "allowed_updates": ["message"]})
                failures = 0
            except ConnectionError as exc:
                logger.warning("telegram: %s", exc)
                await backoff_sleep(failures)
                failures += 1
                continue
            for update in updates or []:
                offset = max(offset, int(update.get("update_id", 0)) + 1)
                message = update.get("message")
                if isinstance(message, dict):
                    event = await self.event(message)
                    if event:
                        await on_event(event, str(message["chat"]["id"]))

    async def event(self, message: dict) -> dict | None:
        sender = message.get("from") or {}
        chat = message.get("chat") or {}
        if not sender or sender.get("is_bot"):
            return None
        uid = str(sender.get("id"))
        name = plain_name(" ".join(filter(None, (sender.get("first_name"), sender.get("last_name")))),
                          sender.get("username"), uid)
        self.names[uid] = name
        is_dm = chat.get("type") == "private"
        text = str(message.get("text") or message.get("caption") or "")
        entities = message.get("entities") or message.get("caption_entities") or []
        addressed = is_dm
        segments: list[dict] = []
        handle = "@" + self.username.lower() if self.username else ""
        for entity in entities:
            piece = _entity_text(text, entity)
            if entity.get("type") == "mention" and handle and piece.lower() == handle:
                addressed = True
            if entity.get("type") == "text_mention" and str((entity.get("user") or {}).get("id")) == self.bot_id:
                addressed = True
        if text:
            segments.append({"type": "text", "text": text})
        if addressed and not is_dm:
            segments.append({"type": "mention", "user_id": self.bot_id, "name": self.username})
        photo = await self._photo(message.get("photo"))
        if photo:
            segments.append(photo)
        elif message.get("photo"):
            segments.append({"type": "text", "text": "(sent a photo)"})
        for key, note in (("voice", "(sent a voice message)"), ("video", "(sent a video)"),
                          ("sticker", "(sent a sticker)"), ("document", "(sent a file)")):
            if message.get(key):
                segments.append({"type": "text", "text": note})
        quoted = message.get("reply_to_message")
        if isinstance(quoted, dict):
            author = quoted.get("from") or {}
            if str(author.get("id")) == self.bot_id:
                addressed = True
            segments.insert(0, {"type": "reply", "message_id": str(quoted.get("message_id")),
                                "text": str(quoted.get("text") or quoted.get("caption") or ""),
                                "sender_id": str(author.get("id") or ""),
                                "sender_name": plain_name(author.get("first_name"), author.get("username"))})
        if not any(s["type"] in ("text", "image") for s in segments):
            return None
        return {"conversation_type": "dm" if is_dm else "group",
                **({} if is_dm else {"conversation_id": str(chat.get("id"))}),
                "sender_id": uid, "sender_name": name,
                "message_id": str(message.get("message_id")), "sent_at": int(message.get("date") or 0),
                "addressed": addressed, "text": text, "segments": segments,
                "reply_handle": str(chat.get("id"))}

    async def _photo(self, sizes: Any) -> dict | None:
        if not isinstance(sizes, list) or not sizes:
            return None
        fitting = [s for s in sizes if int(s.get("file_size") or 0) <= MAX_INLINE_IMAGE_BYTES]
        if not fitting:
            return None
        try:
            info = await self.call("getFile", json={"file_id": fitting[-1]["file_id"]})
            # The file URL carries the token, so the bytes go inline instead.
            response = await self.client.get(f"{API}/file/bot{self.token}/{info['file_path']}")
            response.raise_for_status()
        except (ConnectionError, httpx.HTTPError, KeyError, Refused):
            return None
        if len(response.content) > MAX_INLINE_IMAGE_BYTES:
            return None
        return {"type": "image", "b64": base64.b64encode(response.content).decode()}

    def target(self, delivery: dict) -> str:
        handle = str(delivery.get("reply_handle") or delivery.get("conversation_id") or "")
        if not handle:
            raise Unsupported()
        return handle

    async def send(self, target: str, items: list) -> int:
        sent = 0
        for item in items:
            if item.get("type") == "image" and item.get("b64"):
                await self.call("sendPhoto", data={"chat_id": target}, files={
                    "photo": ("image", base64.b64decode(item["b64"]))})
            elif item.get("type") == "text" and str(item.get("text") or "").strip():
                pieces = split_text(str(item["text"]), MAX_TEXT - 80)
                mention = raw_id(item.get("mention_user_id"), self.kind)
                for i, piece in enumerate(pieces):
                    payload: dict = {"chat_id": target, "text": piece}
                    name = self.names.get(mention)
                    if i == 0 and mention and name:
                        payload["text"] = f"{name} {piece}"
                        payload["entities"] = [{"type": "text_mention", "offset": 0,
                                                "length": utf16_len(name), "user": {"id": int(mention)}}]
                    await self.call("sendMessage", json=payload)
            else:
                continue
            sent += 1
        return sent

    async def close(self) -> None:
        await self.client.aclose()


def _entity_text(text: str, entity: dict) -> str:
    units = text.encode("utf-16-le")
    start, length = int(entity.get("offset", 0)) * 2, int(entity.get("length", 0)) * 2
    return units[start:start + length].decode("utf-16-le", "ignore")
