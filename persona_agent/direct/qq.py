"""QQ official bots through the documented API v2
(https://bot.q.qq.com/wiki/develop/api-v2/): an app access token, the
WebSocket gateway for C2C and group messages, and the v2 send endpoints.

Replies to a message are passive (carry its msg_id) while QQ allows them;
anything else is an active message, which QQ rate-limits and a person can
switch off."""
from __future__ import annotations

import asyncio
import base64
import collections
import json
import logging
import os
import random
import time
from datetime import datetime
from typing import Any, Callable
from urllib.parse import quote

import httpx

from .base import Platform, Refused, Unsupported, backoff_sleep, split_text

logger = logging.getLogger("personagent.direct.qq")

# Unified since 2026-08-10; the older hosts still answer and are tried second.
TOKEN_URLS = ("https://api.bot.qq.com/app/getAppAccessToken", "https://bots.qq.com/app/getAppAccessToken")
API_HOSTS = ("https://api.bot.qq.com", "https://api.sgroup.qq.com")
GROUP_AND_C2C_EVENT = 1 << 25
# QQ states no text limit, only an error when one is exceeded.
MAX_TEXT = 2000
# How long a message can be replied to passively, and how many times.
PASSIVE_S = {"group": 5 * 60, "c2c": 60 * 60}
PASSIVE_REPLIES = {"group": 5, "c2c": 4}
FATAL = {4914: "bot_offline", 4915: "bot_banned", 4013: "invalid_intents", 4014: "intents_not_allowed",
         4010: "invalid_shard", 4011: "sharding_required", 4012: "invalid_api_version"}
# Close codes after which the session cannot be resumed: identify again.
FRESH = {4004, 4006, 4007}
# An @ of the bot can arrive both as a group @-message and as a plain group
# message with one id; the plain copy waits this long for the @ copy.
AT_GRACE_S = 1.5

# Scan to bind, as Tencent's MIT-licensed qqbot-agent-sdk does it
# (onboard.py): mobile QQ creates or picks a bot when someone confirms the
# page, and the portal returns its secret sealed with a key only we hold.
PORTAL = "https://q.qq.com"
BIND_PAGE = PORTAL + "/qqbot/openclaw/connect.html?task_id={task}&_wv=2"
BIND_TTL_S = 300
BIND_REFRESHES = 3
BIND_POLL_S = 2


class BindFailed(Exception):
    """A scan that did not end in a bot: expired, refused or unreadable."""


async def _portal(client: httpx.AsyncClient, path: str, payload: dict) -> dict:
    # Without Accept the portal answers with an anti-bot page, not JSON.
    response = await client.post(PORTAL + path, json=payload, timeout=10,
                                 headers={"Accept": "application/json"})
    response.raise_for_status()
    answer = response.json()
    if answer.get("retcode") != 0:
        raise BindFailed(f"retcode {answer.get('retcode')}")
    return answer.get("data") or {}


def _unseal(sealed: str, key: str) -> str:
    """AES-256-GCM: a 12-byte IV, then the ciphertext and its 16-byte tag."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    raw = base64.b64decode(sealed)
    return AESGCM(base64.b64decode(key)).decrypt(raw[:12], raw[12:], None).decode("utf-8")


async def bind(client: httpx.AsyncClient, show: Callable[[str], None]) -> dict:
    """Show bind pages through `show(url)` until someone confirms one in
    mobile QQ; returns the values to store."""
    loop = asyncio.get_running_loop()
    for _ in range(BIND_REFRESHES + 1):
        key = base64.b64encode(os.urandom(32)).decode()
        task = str((await _portal(client, "/lite/create_bind_task", {"key": key})).get("task_id") or "")
        if not task:
            raise BindFailed("no task")
        show(BIND_PAGE.format(task=quote(task)))
        deadline = loop.time() + BIND_TTL_S
        while loop.time() < deadline:
            await asyncio.sleep(BIND_POLL_S)
            try:
                result = await _portal(client, "/lite/poll_bind_result", {"task_id": task})
            except (httpx.HTTPError, ValueError):
                continue    # one lost poll; the deadline still holds
            if result.get("status") == 2:
                appid = str(result.get("bot_appid") or "")
                sealed = str(result.get("bot_encrypt_secret") or "")
                if not appid.strip("0") or not sealed:
                    raise BindFailed("no credentials")
                try:
                    return {"appid": appid, "secret": _unseal(sealed, key)}
                except Exception:
                    raise BindFailed("unreadable secret") from None
            if result.get("status") == 3:
                break       # expired: show a new page
    raise BindFailed("expired")


class QQ(Platform):
    kind = "qq_official"
    capabilities = ("outbox",)

    def __init__(self, values: dict, *, client: httpx.AsyncClient | None = None, connect=None):
        super().__init__(values)
        self.app_id = str(values.get("appid") or "")
        self.secret = str(values.get("secret") or "")
        self.client = client or httpx.AsyncClient(timeout=30)
        self._connect = connect
        self.token, self.token_until = "", 0.0
        self.api = API_HOSTS[0]
        self.session_id, self.seq = "", None
        self.seen: collections.deque[str] = collections.deque(maxlen=512)
        # mid -> (timer, event, target) for plain group messages waiting for an @ copy
        self.held: dict[str, tuple[asyncio.Task, dict, tuple[str, str]]] = {}
        # (scene, id) -> [msg_id, received monotonic, replies used]
        self.passive: dict[tuple[str, str], list] = {}

    async def access_token(self) -> str:
        if self.token and time.monotonic() < self.token_until:
            return self.token
        for url in TOKEN_URLS:
            try:
                response = await self.client.post(url, json={"appId": self.app_id, "clientSecret": self.secret})
                answer = response.json()
            except (httpx.HTTPError, ValueError):
                continue
            if isinstance(answer, dict) and answer.get("access_token"):
                self.token = str(answer["access_token"])
                # QQ hands out a new token in its last 60 seconds.
                self.token_until = time.monotonic() + max(60, int(answer.get("expires_in") or 7200) - 60)
                return self.token
            if response.status_code < 500 and isinstance(answer, dict) and answer.get("code") is not None:
                # Wrong credentials come back as a code with HTTP 200.
                raise Refused("app_rejected")
            # Anything else is QQ having trouble: try the other host.
        raise ConnectionError("token endpoint unavailable")

    async def rest(self, method: str, path: str, **kwargs) -> Any:
        token = await self.access_token()
        headers = {"Authorization": f"QQBot {token}"}
        for host in (self.api, *[h for h in API_HOSTS if h != self.api]):
            try:
                response = await self.client.request(method, host + path, headers=headers, **kwargs)
            except (httpx.ConnectError, httpx.ConnectTimeout):
                continue        # never reached this host: the other one is safe to try
            except httpx.HTTPError as exc:
                # It may have arrived; repeating a send could post it twice.
                raise ConnectionError(f"{path}: {type(exc).__name__}") from None
            self.api = host
            if response.status_code == 401:
                self.token = ""
                raise ConnectionError(f"{path}: 401")
            if response.status_code >= 400:
                try:
                    code = response.json().get("code") or response.status_code
                except ValueError:
                    code = response.status_code
                raise ConnectionError(f"{path}: {code}")
            return response.json() if response.content else None
        raise ConnectionError(f"{path}: unreachable")

    async def check(self) -> str:
        if not self.app_id or not self.secret:
            raise Refused("app_rejected")
        await self.access_token()
        return self.app_id

    async def _open(self, url: str):
        if self._connect is not None:
            return await self._connect(url)
        import websockets

        return await websockets.connect(url, max_size=None, open_timeout=30)

    async def run(self, on_event, connected) -> None:
        await self.check()
        failures = 0
        while True:
            try:
                gateway = (await self.rest("GET", "/gateway/bot"))["url"]
                await self._session(gateway, on_event, connected)
                failures = 0
            except Refused:
                raise
            except Exception as exc:
                logger.warning("qq: gateway dropped (%s)", type(exc).__name__)
                self.dropped()
                await backoff_sleep(failures)
                failures += 1

    async def _session(self, url: str, on_event, connected) -> None:
        socket = await self._open(url)
        heartbeat = None
        try:
            hello = json.loads(await socket.recv())
            interval = hello["d"]["heartbeat_interval"] / 1000

            async def beat() -> None:
                while True:
                    await asyncio.sleep(interval)
                    await socket.send(json.dumps({"op": 1, "d": self.seq}))

            heartbeat = asyncio.create_task(beat())
            token = await self.access_token()
            if self.session_id:
                await socket.send(json.dumps({"op": 6, "d": {
                    "token": f"QQBot {token}", "session_id": self.session_id, "seq": self.seq}}))
            else:
                await socket.send(json.dumps({"op": 2, "d": {
                    "token": f"QQBot {token}", "intents": GROUP_AND_C2C_EVENT,
                    "shard": [0, 1], "properties": {}}}))
            async for raw in socket:
                frame = json.loads(raw)
                if frame.get("s") is not None:
                    self.seq = frame["s"]
                op = frame.get("op")
                if op == 7:
                    return
                if op == 9:
                    self.session_id, self.seq = "", None
                    await asyncio.sleep(1 + 4 * random.random())
                    return
                if op == 0:
                    await self._dispatch(frame.get("t"), frame.get("d") or {}, on_event, connected)
        finally:
            if heartbeat is not None:
                heartbeat.cancel()
            code = getattr(socket, "close_code", None)
            await socket.close()
            if code in FATAL:
                raise Refused(FATAL[code])
            if code in FRESH:
                self.session_id, self.seq = "", None
                if code == 4004:    # the token lapsed: get a new one
                    self.token = ""

    async def _dispatch(self, name: str, data: dict, on_event, connected) -> None:
        if name == "READY":
            self.session_id = str(data.get("session_id") or "")
            self.bot_id = str((data.get("user") or {}).get("id") or self.app_id)
            connected()
        elif name == "RESUMED":
            connected()
        elif name in ("C2C_MESSAGE_CREATE", "GROUP_AT_MESSAGE_CREATE", "GROUP_MESSAGE_CREATE"):
            mid = str(data.get("id") or "")
            if not mid:
                return
            # QQ may push one message more than once, and an @ both ways.
            if name == "GROUP_AT_MESSAGE_CREATE" and mid in self.held:
                self.held.pop(mid)[0].cancel()  # the @ copy replaces the plain one
            elif mid in self.seen:
                return
            else:
                self.seen.append(mid)
            event, target = self.event(name, data)
            if not event:
                return
            if name == "GROUP_MESSAGE_CREATE":
                timer = asyncio.create_task(self._release(mid, on_event))
                self.held[mid] = (timer, event, target)
                return
            # Earlier plain messages of this group go first, so order holds
            # and the passive reply below refers to this message.
            for earlier, (timer, held_event, held_target) in list(self.held.items()):
                if held_target == target:
                    timer.cancel()
                    del self.held[earlier]
                    await on_event(held_event, held_target)
            self.passive[target] = [mid, time.monotonic(), 0]
            await on_event(event, target)

    async def _release(self, mid: str, on_event) -> None:
        """Hand over a plain group message no @ copy has replaced."""
        await asyncio.sleep(AT_GRACE_S)
        held = self.held.pop(mid, None)
        if held is None:
            return
        _, event, target = held
        self.passive[target] = [mid, time.monotonic(), 0]
        await on_event(event, target)

    def event(self, name: str, data: dict) -> tuple[dict | None, tuple[str, str]]:
        author = data.get("author") or {}
        is_dm = name == "C2C_MESSAGE_CREATE"
        uid = str(author.get("user_openid") if is_dm else author.get("member_openid") or author.get("id") or "")
        target = ("c2c", uid) if is_dm else ("group", str(data.get("group_openid") or ""))
        if not uid or author.get("bot"):
            return None, target
        text = str(data.get("content") or "").strip()
        segments: list[dict] = []
        if text:
            segments.append({"type": "text", "text": text})
        for attachment in data.get("attachments") or []:
            url = str(attachment.get("url") or "")
            if url.startswith("//"):
                url = "https:" + url
            if str(attachment.get("content_type") or "").startswith("image/") and url.startswith("http"):
                segments.append({"type": "image", "url": url})
            else:
                segments.append({"type": "text", "text": f"(sent a file: {attachment.get('filename', '')})"})
        if not segments:
            return None, target
        try:
            sent_at = int(datetime.fromisoformat(str(data.get("timestamp"))).timestamp())
        except ValueError:
            sent_at = int(time.time())
        handle = f"{target[0]}:{target[1]}"
        return ({"conversation_type": "dm" if is_dm else "group",
                 **({} if is_dm else {"conversation_id": target[1]}),
                 "sender_id": uid, "sender_name": str(author.get("username") or ""),
                 "message_id": str(data.get("id")), "sent_at": sent_at,
                 "addressed": name != "GROUP_MESSAGE_CREATE", "text": text, "segments": segments,
                 "reply_handle": handle}, target)

    def target(self, delivery: dict) -> tuple[str, str]:
        scene, _, ident = str(delivery.get("reply_handle") or "").partition(":")
        if scene not in ("group", "c2c") or not ident:
            raise Unsupported()
        return scene, ident

    async def send(self, target: tuple[str, str], items: list) -> int:
        scene, ident = target
        path = f"/v2/groups/{ident}/messages" if scene == "group" else f"/v2/users/{ident}/messages"
        sent = 0
        for item in items:
            text = str(item.get("text") or "").strip() if item.get("type") == "text" else ""
            if not text:
                continue        # images need QQ's media upload first, not done here
            try:
                for piece in split_text(text, MAX_TEXT):
                    body: dict = {"msg_type": 0, "content": piece}
                    passive = self.passive.get(target)
                    if (passive and time.monotonic() - passive[1] < PASSIVE_S[scene]
                            and passive[2] < PASSIVE_REPLIES[scene]):
                        passive[2] += 1
                        body.update({"msg_id": passive[0], "msg_seq": passive[2]})
                    await self.rest("POST", path, json=body)
            except (ConnectionError, Refused) as exc:
                logger.warning("qq: sending stopped after %d item(s) (%s)", sent, exc)
                break
            sent += 1
        return sent

    async def close(self) -> None:
        for timer, _, _ in self.held.values():
            timer.cancel()
        await self.client.aclose()
