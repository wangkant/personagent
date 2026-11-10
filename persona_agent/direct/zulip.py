"""Zulip through its REST API (https://zulip.com/api/): an event queue
long-polled with GET /events in, POST /messages out, as a Generic bot."""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import re
from typing import Any
from urllib.parse import urlsplit

import httpx

from .base import (MAX_INLINE_IMAGE_BYTES, Platform, Refused, Unsupported, backoff_sleep,
                   plain_name, raw_id, split_text)

logger = logging.getLogger("personagent.direct.zulip")

# Zulip's documented fallback when register does not say.
LONGPOLL_S = 90
# The server default; register's max_message_length overrides it.
MAX_TEXT = 10000
MAX_NAME = 100
MAX_IMAGES = 4
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
DEACTIVATED = {"USER_DEACTIVATED", "REALM_DEACTIVATED"}
UPLOAD = re.compile(r"(!?)\[([^\]]*)\]\((/user_uploads/(\d+)/([^)\s]+))\)")
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp")
# The quote-and-reply header: a silent mention of the author and a link to the message.
QUOTE = re.compile(r"^@_\*\*([^*|]*)\|(\d+)\*\* \[[^\]]*\]\(([^)]*)\):?\s*\n"
                   r"(`{3,}|~{3,})quote\n(.*?)\n\4[ \t]*(?:\n|$)", re.DOTALL)


class QueueGone(Exception):
    """The server dropped the event queue; register a new one."""


class ApiError(ConnectionError):
    def __init__(self, path: str, status: int, code: str):
        super().__init__(f"{path}: {status} {code}")
        self.status, self.code = status, code


def site_url(raw: Any) -> str:
    parts = urlsplit(str(raw or "").strip())
    return f"{parts.scheme}://{parts.netloc}{parts.path.rstrip('/')}" if parts.netloc else ""


class Zulip(Platform):
    kind = "zulip"

    def __init__(self, values: dict, *, client: httpx.AsyncClient | None = None):
        super().__init__(values)
        self.site = site_url(values.get("zulip_site"))
        self.auth = httpx.BasicAuth(str(values.get("zulip_email") or "").strip(),
                                    str(values.get("zulip_api_key") or "").strip())
        self.client = client or httpx.AsyncClient(timeout=30)
        self.full_name = ""
        self.names: dict[str, str] = {}
        self.queue_id = ""
        self.longpoll_s = LONGPOLL_S
        self.max_text = MAX_TEXT
        self.feature_level: int | None = None

    async def call(self, method: str, path: str, *, timeout: float | None = None, **kwargs) -> dict:
        """One API call, waiting out rate limits; the key never reaches a log."""
        for _ in range(5):
            try:
                response = await self.client.request(
                    method, f"{self.site}/api/v1{path}", auth=self.auth,
                    headers={"User-Agent": "personagent"},
                    **({"timeout": timeout} if timeout else {}), **kwargs)
            except httpx.HTTPError as exc:
                raise ConnectionError(f"{path}: {type(exc).__name__}") from None
            try:
                answer = response.json()
            except ValueError:
                answer = None
            status = response.status_code
            if not isinstance(answer, dict):
                answer = {}
            code = str(answer.get("code") or "")
            if status == 429 or code == "RATE_LIMIT_HIT":
                await asyncio.sleep(_retry_after(answer, response))
                continue
            if "result" not in answer:
                if status >= 500:
                    raise ConnectionError(f"{path}: {status}")
                # Something answered, but not a Zulip server.
                raise Refused("not_zulip_site")
            if answer.get("result") == "success":
                return answer
            if code == "BAD_EVENT_QUEUE_ID":
                raise QueueGone()
            if code in DEACTIVATED:
                raise Refused("account_deactivated")
            if status == 401 or code in ("UNAUTHORIZED", "INVALID_API_KEY"):
                raise Refused("token_rejected")
            raise ApiError(path, status, code)
        raise ConnectionError(f"{path}: rate limited")

    async def check(self) -> str:
        parts = urlsplit(self.site)
        if parts.scheme not in ("https", "http") or not parts.hostname:
            raise Refused("not_zulip_site")
        # Basic auth sends the key as it is, so only https off this computer.
        if parts.scheme != "https" and parts.hostname not in LOCAL_HOSTS:
            # Named as Stoat names it; the page's https_required is about model services.
            raise Refused("insecure_address")
        me = await self.call("GET", "/users/me")
        if not me.get("is_bot"):
            # A person's own key would make the character answer their private messages.
            raise Refused("not_a_bot")
        self.bot_id = str(me.get("user_id") or "")
        self.full_name = str(me.get("full_name") or "")
        if not self.bot_id:
            raise Refused("not_zulip_site")
        return plain_name(self.full_name, me.get("email"), self.bot_id)

    async def _register(self) -> int:
        try:
            answer = await self.call("POST", "/register", data={
                "event_types": json.dumps(["message"]),
                "fetch_event_types": json.dumps(["realm"]),
                "all_public_streams": "false", "apply_markdown": "false",
                "client_gravatar": "true"})
        except ApiError as exc:
            if 400 <= exc.status < 500:
                # An incoming-webhook bot may send but not read.
                raise Refused("wrong_bot_type") from None
            raise
        self.queue_id = str(answer.get("queue_id") or "")
        if not self.queue_id:
            raise ConnectionError("register: no queue")
        self.longpoll_s = float(answer.get("event_queue_longpoll_timeout_seconds") or LONGPOLL_S)
        self.max_text = int(answer.get("max_message_length") or MAX_TEXT)
        self.feature_level = int(answer.get("zulip_feature_level") or 0)
        return int(answer.get("last_event_id", -1))

    async def run(self, on_event, connected) -> None:
        await self.check()
        last, failures, lost, pending = -1, 0, 0, True
        while True:
            try:
                if not self.queue_id:
                    last = await self._register()
                    if pending:
                        connected()
                        pending = False
                answer = await self.call("GET", "/events", timeout=self.longpoll_s + 15, params={
                    "queue_id": self.queue_id, "last_event_id": last})
            except QueueGone:
                self.queue_id = ""
                if lost:
                    await backoff_sleep(lost)   # a queue lost again at once: slow down
                lost += 1
                continue
            except ConnectionError as exc:
                if isinstance(exc, ApiError):
                    self.queue_id = ""      # a queue the server will not serve: start a new one
                failures = await self._drop(exc, failures)
                pending = True
                continue
            if pending:
                connected()     # back after a drop
                pending = False
            failures, lost = 0, 0
            for item in answer.get("events") or []:
                last = max(last, int(item.get("id", last)))
                if item.get("type") == "message" and isinstance(item.get("message"), dict):
                    event = await self.event(item["message"], item.get("flags") or [])
                    if event:
                        await on_event(event, event["reply_handle"])

    async def _drop(self, exc: Exception, failures: int) -> int:
        logger.warning("zulip: %s", exc)
        self.dropped()
        await backoff_sleep(failures)
        return failures + 1

    async def event(self, message: dict, flags: list) -> dict | None:
        uid = str(message.get("sender_id") or "")
        if not uid or uid == self.bot_id:
            return None
        name = plain_name(message.get("sender_full_name"), message.get("sender_email"), uid)
        self.names[uid] = name
        text = str(message.get("content") or "")
        segments: list[dict] = []
        addressed = "mentioned" in flags
        quote = QUOTE.match(text)
        if quote:
            author_name, author_id, link, _, quoted = quote.groups()
            addressed = addressed or author_id == self.bot_id
            near = re.search(r"/near/(\d+)", link)
            segments.append({"type": "reply", "message_id": near.group(1) if near else "",
                             "text": quoted.strip(), "sender_id": author_id, "sender_name": author_name})
            text = text[quote.end():]
        if self.bot_id:
            mine = re.compile(r"@_?\*\*" + re.escape(self.full_name) + r"(\|" + self.bot_id + r")?\*\*"
                              if self.full_name else r"@_?\*\*[^*|]*\|" + self.bot_id + r"\*\*")
            if mine.search(text) and "mentioned" in flags:
                segments.append({"type": "mention", "user_id": self.bot_id, "name": self.full_name})
            text = mine.sub("", text)
        images, files = [], []
        for _, label, _, realm, rest in UPLOAD.findall(text):
            if rest.lower().endswith(IMAGE_EXT) and len(images) < MAX_IMAGES:
                images.append((realm, rest))
            else:
                files.append(label or rest.rsplit("/", 1)[-1])
        text = UPLOAD.sub(lambda m: "" if m.group(5).lower().endswith(IMAGE_EXT) else m.group(2), text)
        text = re.sub(r"[ \t]+", " ", text).strip()
        if text:
            segments.append({"type": "text", "text": text})
        for realm, rest in images:
            image = await self._image(realm, rest)
            segments.append(image or {"type": "text", "text": "(sent a photo)"})
        for label in files:
            segments.append({"type": "text", "text": f"(sent a file: {label})"})
        if not any(s["type"] in ("text", "image") for s in segments):
            return None
        if message.get("type") == "stream":
            stream = str(message.get("stream_id") or "")
            if not stream:
                return None
            topic = str(message.get("subject") or message.get("topic") or "")
            conversation, handle, is_dm = stream, f"stream/{stream}/{topic}", False
        else:
            people = message.get("display_recipient")
            ids = sorted({str(p.get("id")) for p in people if isinstance(p, dict) and p.get("id") is not None}
                         if isinstance(people, list) else set()) or [uid]
            others = [i for i in ids if i != self.bot_id] or [uid]
            is_dm = len(others) == 1
            conversation = ",".join(ids)
            handle = "dm/" + ",".join(others)
            addressed = addressed or is_dm
        return {"conversation_type": "dm" if is_dm else "group",
                **({} if is_dm else {"conversation_id": conversation}),
                "sender_id": uid, "sender_name": name, "message_id": str(message.get("id")),
                "sent_at": int(message.get("timestamp") or 0), "addressed": addressed,
                "text": text, "segments": segments, "reply_handle": handle}

    async def _image(self, realm: str, rest: str) -> dict | None:
        try:
            # A short-lived link that needs no key, fetched at once and never passed on.
            answer = await self.call("GET", f"/user_uploads/{realm}/{rest}")
            link = str(answer.get("url") or "")
            if not link:
                return None
            if link.startswith("/"):
                link = self.site + link
            response = await self.client.get(link, follow_redirects=True)
            response.raise_for_status()
        except (ConnectionError, Refused, QueueGone, httpx.HTTPError):
            return None
        if not response.content or len(response.content) > MAX_INLINE_IMAGE_BYTES:
            return None
        return {"type": "image", "b64": base64.b64encode(response.content).decode()}

    def target(self, delivery: dict) -> str:
        handle = str(delivery.get("reply_handle") or "")
        if not handle.startswith(("stream/", "dm/")):
            raise Unsupported()
        return handle

    def _where(self, target: str) -> dict:
        kind, _, rest = target.partition("/")
        if kind == "stream":
            stream, _, topic = rest.partition("/")
            return {"type": "stream", "to": stream, "topic": topic}
        ids = [int(i) for i in rest.split(",") if i.strip().isdigit()]
        legacy = self.feature_level is not None and self.feature_level < 174
        return {"type": "private" if legacy else "direct", "to": json.dumps(ids)}

    async def send(self, target: str, items: list) -> int:
        where = self._where(target)
        sent = 0
        for item in items:
            try:
                if item.get("type") == "image" and item.get("b64"):
                    data = base64.b64decode(item["b64"])
                    name, mime = _image_name(data)
                    uploaded = await self.call("POST", "/user_uploads", files={"filename": (name, data, mime)})
                    link = str(uploaded.get("url") or uploaded.get("uri") or "")
                    if not link:
                        raise ConnectionError("user_uploads: no url")
                    await self.call("POST", "/messages", data={**where, "content": f"[{name}]({link})"})
                elif item.get("type") == "text" and str(item.get("text") or "").strip():
                    mention = raw_id(item.get("mention_user_id"), self.kind)
                    name = re.sub(r"[*|]", "", self.names.get(mention, ""))[:MAX_NAME]
                    lead = f"@**{name}|{mention}** " if mention.isdigit() and name else ""
                    for i, piece in enumerate(split_text(str(item["text"]), self.max_text - MAX_NAME - 20)):
                        await self.call("POST", "/messages", data={
                            **where, "content": (lead if i == 0 else "") + piece})
                else:
                    continue
            except (ConnectionError, Refused, QueueGone, ValueError) as exc:
                logger.warning("zulip: sending stopped after %d item(s) (%s)", sent, exc)
                break
            sent += 1
        return sent

    async def close(self) -> None:
        if self.queue_id:
            try:
                await self.call("DELETE", "/events", timeout=5, data={"queue_id": self.queue_id})
            except (ConnectionError, Refused, QueueGone):
                logger.debug("zulip: the event queue was left to expire")
            self.queue_id = ""
        await self.client.aclose()


def _retry_after(answer: dict, response: httpx.Response) -> float:
    try:
        wait = float(answer.get("retry-after") or response.headers.get("retry-after") or 5)
    except ValueError:
        wait = 5.0
    return min(max(wait, 0.0), 300.0)


def _image_name(data: bytes) -> tuple[str, str]:
    if data.startswith(b"\x89PNG"):
        return "image.png", "image/png"
    if data.startswith(b"\xff\xd8"):
        return "image.jpg", "image/jpeg"
    if data.startswith(b"GIF8"):
        return "image.gif", "image/gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image.webp", "image/webp"
    return "image.png", "image/png"
