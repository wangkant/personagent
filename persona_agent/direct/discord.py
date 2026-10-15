"""Discord through Gateway v10 and the REST API
(https://discord.com/developers/docs/events/gateway): MESSAGE_CREATE in,
POST /channels/{id}/messages out."""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import random
from datetime import datetime
from typing import Any

import httpx

from .base import Platform, Refused, Unsupported, backoff_sleep, plain_name, raw_id, split_text

logger = logging.getLogger("personagent.direct.discord")

API = "https://discord.com/api/v10"
MAX_TEXT = 2000
# GUILDS | GUILD_MESSAGES | DIRECT_MESSAGES | MESSAGE_CONTENT
INTENTS = (1 << 0) | (1 << 9) | (1 << 12) | (1 << 15)
# Close codes after which reconnecting with the same settings cannot work.
FATAL = {4004: "token_rejected", 4010: "invalid_shard", 4011: "sharding_required",
         4012: "invalid_api_version", 4013: "invalid_intents", 4014: "message_content_intent_off"}
# Close codes after which the session cannot be resumed.
FRESH = {4007, 4009}


class Discord(Platform):
    kind = "discord"

    def __init__(self, values: dict, *, client: httpx.AsyncClient | None = None, connect=None):
        super().__init__(values)
        self.token = str(values.get("discord_token") or "")
        self.client = client or httpx.AsyncClient(timeout=30)
        self._connect = connect
        self.session_id = ""
        self.resume_url = ""
        self.seq = None

    def _headers(self) -> dict:
        return {"Authorization": f"Bot {self.token}", "User-Agent": "DiscordBot (personagent, 1)"}

    async def rest(self, method: str, path: str, **kwargs) -> Any:
        for _ in range(5):
            try:
                response = await self.client.request(method, API + path, headers=self._headers(), **kwargs)
            except httpx.HTTPError as exc:
                raise ConnectionError(f"{path}: {type(exc).__name__}") from None
            if response.status_code == 429:
                await asyncio.sleep(float(response.json().get("retry_after") or 2))
                continue
            if response.status_code == 401:
                raise Refused("token_rejected")
            if response.status_code >= 400:
                raise ConnectionError(f"{path}: {response.status_code}")
            return response.json() if response.content else None
        raise ConnectionError(f"{path}: rate limited")

    async def check(self) -> str:
        me = await self.rest("GET", "/users/@me")
        self.bot_id = str(me["id"])
        return plain_name(me.get("username"), self.bot_id)

    async def _open(self, url: str):
        if self._connect is not None:
            return await self._connect(url)
        import websockets

        return await websockets.connect(url, max_size=None, open_timeout=30)

    async def run(self, on_event, connected) -> None:
        await self.check()
        gateway = (await self.rest("GET", "/gateway/bot"))["url"]
        failures = 0
        while True:
            resuming = bool(self.session_id and self.resume_url)
            url = (self.resume_url if resuming else gateway) + "/?v=10&encoding=json"
            try:
                await self._session(url, resuming, on_event, connected)
                failures = 0
            except Refused:
                raise
            except Exception as exc:
                logger.warning("discord: gateway dropped (%s)", type(exc).__name__)
                await backoff_sleep(failures)
                failures += 1

    async def _session(self, url: str, resuming: bool, on_event, connected) -> None:
        socket = await self._open(url)
        heartbeat = None
        try:
            hello = json.loads(await socket.recv())
            interval = hello["d"]["heartbeat_interval"] / 1000
            acked = asyncio.Event()
            acked.set()

            async def beat() -> None:
                await asyncio.sleep(interval * random.random())
                while True:
                    if not acked.is_set():
                        await socket.close(4000)    # a zombie connection: start over
                        return
                    acked.clear()
                    await socket.send(json.dumps({"op": 1, "d": self.seq}))
                    await asyncio.sleep(interval)

            heartbeat = asyncio.create_task(beat())
            if resuming:
                await socket.send(json.dumps({"op": 6, "d": {
                    "token": self.token, "session_id": self.session_id, "seq": self.seq}}))
            else:
                await socket.send(json.dumps({"op": 2, "d": {
                    "token": self.token, "intents": INTENTS,
                    "properties": {"os": "personagent", "browser": "personagent", "device": "personagent"}}}))
            async for raw in socket:
                frame = json.loads(raw)
                op = frame.get("op")
                if frame.get("s") is not None:
                    self.seq = frame["s"]
                if op == 11:
                    acked.set()
                elif op == 1:
                    await socket.send(json.dumps({"op": 1, "d": self.seq}))
                elif op == 7:
                    return                  # asked to reconnect; resume next
                elif op == 9:
                    if not frame.get("d"):
                        self.session_id, self.resume_url, self.seq = "", "", None
                    await asyncio.sleep(1 + 4 * random.random())
                    return
                elif op == 0:
                    await self._dispatch(frame.get("t"), frame.get("d") or {}, on_event, connected)
        finally:
            if heartbeat is not None:
                heartbeat.cancel()
            code = getattr(socket, "close_code", None)
            await socket.close()
            if code in FATAL:
                raise Refused(FATAL[code])
            if code in FRESH:
                self.session_id, self.resume_url, self.seq = "", "", None

    async def _dispatch(self, name: str, data: dict, on_event, connected) -> None:
        if name == "READY":
            self.session_id = str(data.get("session_id") or "")
            self.resume_url = str(data.get("resume_gateway_url") or "")
            self.bot_id = str((data.get("user") or {}).get("id") or self.bot_id)
            connected()
        elif name == "RESUMED":
            connected()
        elif name == "MESSAGE_CREATE":
            event = self.event(data)
            if event:
                await on_event(event, str(data.get("channel_id")))

    def event(self, data: dict) -> dict | None:
        author = data.get("author") or {}
        if not author or author.get("bot") or data.get("webhook_id"):
            return None
        uid = str(author.get("id"))
        is_dm = not data.get("guild_id")
        name = plain_name((data.get("member") or {}).get("nick"), author.get("global_name"),
                          author.get("username"), uid)
        text = str(data.get("content") or "")
        mentioned = any(str(m.get("id")) == self.bot_id for m in data.get("mentions") or [])
        quoted = data.get("referenced_message") or {}
        quoted_author = quoted.get("author") or {}
        addressed = is_dm or mentioned or str(quoted_author.get("id")) == self.bot_id
        for token in (f"<@{self.bot_id}>", f"<@!{self.bot_id}>"):
            text = text.replace(token, "").strip()
        segments: list[dict] = []
        if quoted:
            segments.append({"type": "reply", "message_id": str(quoted.get("id")),
                             "text": str(quoted.get("content") or ""),
                             "sender_id": str(quoted_author.get("id") or ""),
                             "sender_name": plain_name(quoted_author.get("global_name"),
                                                       quoted_author.get("username"))})
        if mentioned:
            segments.append({"type": "mention", "user_id": self.bot_id, "name": ""})
        if text:
            segments.append({"type": "text", "text": text})
        for attachment in data.get("attachments") or []:
            if str(attachment.get("content_type") or "").startswith("image/") and attachment.get("url"):
                segments.append({"type": "image", "url": attachment["url"]})
            else:
                segments.append({"type": "text", "text": f"(sent a file: {attachment.get('filename', '')})"})
        for sticker in data.get("sticker_items") or []:
            segments.append({"type": "emoji", "name": str(sticker.get("name") or ""), "id": str(sticker.get("id"))})
        if not any(s["type"] in ("text", "image", "emoji") for s in segments):
            return None
        try:
            sent_at = int(datetime.fromisoformat(str(data.get("timestamp")).replace("Z", "+00:00")).timestamp())
        except ValueError:
            sent_at = 0
        channel = str(data.get("channel_id"))
        return {"conversation_type": "dm" if is_dm else "group",
                **({} if is_dm else {"conversation_id": channel}),
                "sender_id": uid, "sender_name": name, "message_id": str(data.get("id")),
                "sent_at": sent_at, "addressed": addressed, "text": text, "segments": segments,
                "reply_handle": channel}

    def target(self, delivery: dict) -> str:
        handle = str(delivery.get("reply_handle") or "")
        if not handle:
            raise Unsupported()
        return handle

    async def send(self, target: str, items: list) -> int:
        sent = 0
        for item in items:
            if item.get("type") == "image" and item.get("b64"):
                await self.rest("POST", f"/channels/{target}/messages", data={"payload_json": "{}"},
                                files={"files[0]": ("image.png", base64.b64decode(item["b64"]))})
            elif item.get("type") == "text" and str(item.get("text") or "").strip():
                mention = raw_id(item.get("mention_user_id"), self.kind)
                for i, piece in enumerate(split_text(str(item["text"]), MAX_TEXT - 40)):
                    lead = f"<@{mention}> " if i == 0 and mention else ""
                    await self.rest("POST", f"/channels/{target}/messages", json={
                        "content": lead + piece,
                        "allowed_mentions": {"parse": [], "users": [mention] if lead else []}})
            else:
                continue
            sent += 1
        return sent

    async def close(self) -> None:
        await self.client.aclose()
