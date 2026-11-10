"""Twitch chat through EventSub over WebSocket and the Twitch API
(https://dev.twitch.tv/docs/chat/): channel.chat.message in, Send Chat
Message out, with a user token from the device code flow of a public app.

The bot sits only in the channels the owner listed; Twitch whispers are
not used, so there are no DMs."""
from __future__ import annotations

import asyncio
import collections
import hashlib
import json
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import httpx

from .base import Platform, Refused, Unsupported, backoff_sleep, plain_name, raw_id, split_text
from ..storage import atomic_write_text

logger = logging.getLogger("personagent.direct.twitch")

API = "https://api.twitch.tv/helix"
ID = "https://id.twitch.tv/oauth2"
WS_URL = "wss://eventsub.wss.twitch.tv/ws?keepalive_timeout_seconds=30"
SCOPES = ("user:read:chat", "user:write:chat")
DEVICE_GRANT = "urn:ietf:params:oauth:grant-type:device_code"
MAX_TEXT = 500
# Room for "@login " in front of the first piece; logins are at most 25 characters.
MENTION_ROOM = 30
MAX_CHANNELS = 20
# Twitch asks apps to validate their token at start and hourly after.
VALIDATE_S = 3600
# Refresh this long before the access token runs out.
REFRESH_EARLY_S = 300
# Sending limits for an account that is not a moderator or VIP there;
# going over makes Twitch ignore the bot for an hour.
SEND_WINDOW_S = 30.0
SEND_PER_WINDOW = 20
CHANNEL_GAP_S = 1.1
DEVICE_REFRESHES = 3
# Shortest and longest wait after a 429, whatever Ratelimit-Reset says.
RATE_WAIT_S = (1.0, 60.0)
LOGIN = re.compile(r"[a-z0-9_]{1,25}")


class LoginFailed(Exception):
    """The device login ended without a token; the message is a code."""


def channel_names(raw: Any) -> list[str]:
    """Logins from what a person typed: names, #names or channel links."""
    names: list[str] = []
    for part in re.split(r"[\s,;]+", str(raw or "")):
        part = part.strip().rstrip("/").split("/")[-1].lstrip("#@").lower()
        if LOGIN.fullmatch(part) and part not in names:
            names.append(part)
    return names


def _error(response: httpx.Response) -> str:
    try:
        return str(response.json().get("message") or "").lower()
    except (ValueError, AttributeError):
        return ""


async def login(client: httpx.AsyncClient, show: Callable[[str], None], values: dict | None = None) -> dict:
    """Show a Twitch activation link (it carries the code) until someone
    approves it; returns the values to store, tokens included."""
    values = dict(values or {})
    client_id = str(values.get("twitch_client_id") or "").strip()
    if not client_id:
        raise LoginFailed("app_rejected")
    scopes = " ".join(SCOPES)
    loop = asyncio.get_running_loop()
    for _ in range(DEVICE_REFRESHES + 1):
        response = await client.post(f"{ID}/device", data={"client_id": client_id, "scopes": scopes}, timeout=15)
        if response.status_code in (400, 401, 403, 404):
            raise LoginFailed("app_rejected")
        response.raise_for_status()
        issued = response.json()
        device, uri = str(issued.get("device_code") or ""), str(issued.get("verification_uri") or "")
        if not device or not uri:
            raise LoginFailed("no_code")
        show(uri)
        interval = max(1, int(issued.get("interval") or 5))
        deadline = loop.time() + int(issued.get("expires_in") or 1800)
        while loop.time() < deadline:
            await asyncio.sleep(interval)
            try:
                answer = await client.post(f"{ID}/token", data={
                    "client_id": client_id, "scopes": scopes, "device_code": device,
                    "grant_type": DEVICE_GRANT}, timeout=15)
            except httpx.HTTPError:
                continue        # one lost poll; the deadline still holds
            if answer.status_code == 200:
                tokens = answer.json()
                if not tokens.get("access_token") or not tokens.get("refresh_token"):
                    raise LoginFailed("no_token")
                return {**values, "twitch_client_id": client_id,
                        "twitch_access_token": str(tokens["access_token"]),
                        "twitch_refresh_token": str(tokens["refresh_token"])}
            message = _error(answer)
            if "pending" in message:
                continue
            if "slow" in message:
                interval += 5
                continue
            if "device code" in message or "expired" in message:
                break       # used up or timed out: show a new code
            if "denied" in message:
                raise LoginFailed("denied")
            if "client" in message:
                # A confidential app needs a secret this flow never has.
                raise LoginFailed("app_rejected")
            if answer.status_code >= 500:
                continue
            raise LoginFailed("rejected")
    raise LoginFailed("expired")


class Twitch(Platform):
    kind = "twitch"

    def __init__(self, values: dict, *, client: httpx.AsyncClient | None = None, connect=None,
                 state: Path | None = None):
        super().__init__(values)
        self.client_id = str(values.get("twitch_client_id") or "").strip()
        self.channels = channel_names(values.get("twitch_channels"))[:MAX_CHANNELS]
        self.client = client or httpx.AsyncClient(timeout=30)
        self._connect = connect
        self.state_path = state
        given = str(values.get("twitch_refresh_token") or "")
        self.seed = hashlib.sha256(given.encode()).hexdigest()[:16]
        self.access = str(values.get("twitch_access_token") or "")
        self.refresh_token = given
        self.expires_at = 0.0
        saved = self._load()
        # Refresh tokens are single-use, so the newest pair on disk wins
        # unless it belongs to an earlier login.
        if saved.get("seed") == self.seed and saved.get("refresh_token"):
            self.access = str(saved.get("access_token") or "")
            self.refresh_token = str(saved["refresh_token"])
            self.expires_at = float(saved.get("expires_at") or 0)
        self.login_name = ""
        self.channel_ids: dict[str, str] = {}      # broadcaster id -> login
        self.logins: dict[str, str] = {}           # chatter id -> login, for mentions
        self.seen: collections.deque[str] = collections.deque(maxlen=512)
        self.sent_times: collections.deque[float] = collections.deque()
        self.last_sent: dict[str, float] = {}
        self.next_validate = 0.0
        self._refreshing = asyncio.Lock()
        self._sending = asyncio.Lock()

    # ---- tokens

    def _load(self) -> dict:
        if not self.state_path or not self.state_path.exists():
            return {}
        try:
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        except ValueError:
            return {}

    def _save(self) -> None:
        if not self.state_path:
            return
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self.state_path, json.dumps({
            "seed": self.seed, "access_token": self.access, "refresh_token": self.refresh_token,
            "expires_at": self.expires_at}))

    async def _refresh(self, stale: str) -> None:
        async with self._refreshing:
            if self.access != stale:
                return      # another caller already refreshed
            if not self.refresh_token or not self.client_id:
                raise Refused("session_expired")
            try:
                response = await self.client.post(f"{ID}/token", data={
                    "client_id": self.client_id, "grant_type": "refresh_token",
                    "refresh_token": self.refresh_token})
            except httpx.HTTPError as exc:
                raise ConnectionError(f"refresh: {type(exc).__name__}") from None
            if response.status_code in (400, 401, 403):
                raise Refused("session_expired")
            if response.status_code >= 400:
                raise ConnectionError(f"refresh: {response.status_code}")
            try:
                tokens = response.json()
                self.access = str(tokens["access_token"])
            except (ValueError, KeyError):
                raise ConnectionError("refresh: not JSON") from None
            self.refresh_token = str(tokens.get("refresh_token") or self.refresh_token)
            self.expires_at = time.time() + int(tokens.get("expires_in") or 0)
            self._save()

    async def token(self) -> str:
        if not self.access or (self.expires_at and time.time() > self.expires_at - REFRESH_EARLY_S):
            await self._refresh(self.access)
        return self.access

    async def validate(self) -> dict:
        """Who the token belongs to; Twitch wants this at start and hourly."""
        for attempt in range(2):
            access = await self.token()
            try:
                response = await self.client.get(f"{ID}/validate", headers={"Authorization": f"OAuth {access}"})
            except httpx.HTTPError as exc:
                raise ConnectionError(f"validate: {type(exc).__name__}") from None
            if response.status_code == 401 and attempt == 0:
                await self._refresh(access)
                continue
            if response.status_code == 401:
                raise Refused("session_expired")
            if response.status_code >= 400:
                raise ConnectionError(f"validate: {response.status_code}")
            info = response.json()
            if self.client_id and str(info.get("client_id") or "") != self.client_id:
                raise Refused("app_rejected")
            if not set(SCOPES) <= set(info.get("scopes") or []):
                raise Refused("token_rejected")
            if info.get("expires_in"):
                self.expires_at = time.time() + int(info["expires_in"])
            self.next_validate = time.monotonic() + VALIDATE_S
            return info
        raise Refused("session_expired")

    async def helix(self, method: str, path: str, **kwargs) -> httpx.Response:
        """One API call: refreshes once on 401 and waits out 429."""
        refreshed = False
        for _ in range(5):
            access = await self.token()
            headers = {"Authorization": f"Bearer {access}", "Client-Id": self.client_id}
            try:
                response = await self.client.request(method, API + path, headers=headers, **kwargs)
            except httpx.HTTPError as exc:
                raise ConnectionError(f"{path}: {type(exc).__name__}") from None
            if response.status_code == 401 and not refreshed:
                refreshed = True
                await self._refresh(access)
                continue
            if response.status_code == 401:
                raise Refused("session_expired")
            if response.status_code == 429:
                try:
                    wait = float(response.headers.get("ratelimit-reset") or 0) - time.time()
                except ValueError:
                    wait = 0
                await asyncio.sleep(min(max(wait, RATE_WAIT_S[0]), RATE_WAIT_S[1]))
                continue
            return response
        raise ConnectionError(f"{path}: rate limited")

    # ---- platform

    async def check(self) -> str:
        if not self.client_id or not (self.access or self.refresh_token):
            raise Refused("session_expired")
        if not self.channels:
            raise Refused("channel_not_found")
        info = await self.validate()
        self.bot_id = str(info.get("user_id") or "")
        self.login_name = str(info.get("login") or "").lower()
        response = await self.helix("GET", "/users", params=[("login", c) for c in self.channels])
        if response.status_code >= 400:
            raise ConnectionError(f"/users: {response.status_code}")
        users = response.json().get("data") or []
        self.channel_ids = {str(u["id"]): str(u.get("login") or "").lower() for u in users if u.get("id")}
        if set(self.channel_ids.values()) != set(self.channels):
            raise Refused("channel_not_found")
        return plain_name(self.login_name, self.bot_id)

    async def _open(self, url: str):
        if self._connect is not None:
            return await self._connect(url)
        import websockets

        return await websockets.connect(url, max_size=2 ** 20, open_timeout=30)

    async def run(self, on_event, connected) -> None:
        await self.check()
        failures = 0
        while True:
            try:
                await self._session(on_event, connected)
            except Refused:
                raise
            except Exception as exc:
                logger.warning("twitch: chat connection dropped (%s)", type(exc).__name__)
                self.dropped()
                await backoff_sleep(failures)
                failures += 1
                continue
            failures = 0

    async def _welcome(self, socket) -> tuple[str, float]:
        frame = json.loads(await asyncio.wait_for(socket.recv(), 30))
        if (frame.get("metadata") or {}).get("message_type") != "session_welcome":
            raise ConnectionError("no welcome")
        session = (frame.get("payload") or {}).get("session") or {}
        return str(session.get("id") or ""), float(session.get("keepalive_timeout_seconds") or 30)

    async def _subscribe(self, session_id: str) -> None:
        for broadcaster in self.channel_ids:
            response = await self.helix("POST", "/eventsub/subscriptions", json={
                "type": "channel.chat.message", "version": "1",
                "condition": {"broadcaster_user_id": broadcaster, "user_id": self.bot_id},
                "transport": {"method": "websocket", "session_id": session_id}})
            if response.status_code in (202, 409):
                continue
            if response.status_code == 403:
                raise Refused("token_rejected")     # the login lacks a chat scope
            raise ConnectionError(f"subscribe: {response.status_code}")

    async def _session(self, on_event, connected) -> None:
        socket = await self._open(WS_URL)
        try:
            session_id, keepalive = await self._welcome(socket)
            await self._subscribe(session_id)
            connected()
            while True:
                if time.monotonic() > self.next_validate:
                    await self.validate()
                # No message or keepalive within the timeout means the link is dead.
                raw = await asyncio.wait_for(socket.recv(), keepalive + 10)
                frame = json.loads(raw)
                meta = frame.get("metadata") or {}
                kind = meta.get("message_type")
                payload = frame.get("payload") or {}
                if kind == "notification":
                    mid = str(meta.get("message_id") or "")
                    if mid and mid in self.seen:
                        continue
                    if mid:
                        self.seen.append(mid)
                    if (payload.get("subscription") or {}).get("type") == "channel.chat.message":
                        event = self.event(payload.get("event") or {}, meta.get("message_timestamp"))
                        if event:
                            await on_event(event, event["reply_handle"])
                elif kind == "session_reconnect":
                    url = str(((payload.get("session") or {}).get("reconnect_url")) or "")
                    if not url:
                        raise ConnectionError("reconnect without url")
                    fresh = await self._open(url)
                    try:
                        _, keepalive = await self._welcome(fresh)
                    except BaseException:
                        await fresh.close()
                        raise
                    # Subscriptions move with the session; the old socket can go.
                    old, socket = socket, fresh
                    await old.close()
                elif kind == "revocation":
                    status = str((payload.get("subscription") or {}).get("status") or "")
                    logger.warning("twitch: a chat subscription was revoked (%s)", status)
                    if status == "authorization_revoked":
                        raise Refused("session_expired")
                    if status == "version_removed":
                        raise Refused("platform_rejected")
        finally:
            code = getattr(socket, "close_code", None)
            await socket.close()
            if code:
                logger.warning("twitch: chat socket closed with %s", code)

    def event(self, data: dict, stamp: Any = None) -> dict | None:
        uid = str(data.get("chatter_user_id") or "")
        channel = str(data.get("broadcaster_user_id") or "")
        if not uid or uid == self.bot_id or channel not in self.channel_ids:
            return None
        source = data.get("source_broadcaster_user_id")
        if source and str(source) != channel:
            return None     # shared chat from a channel the owner did not list
        login = str(data.get("chatter_user_login") or "").lower()
        if login:
            self.logins[uid] = login
        message = data.get("message") or {}
        text = str(message.get("text") or "").strip()
        mentioned = any(f.get("type") == "mention" and str((f.get("mention") or {}).get("user_id")) == self.bot_id
                        for f in message.get("fragments") or [])
        reply = data.get("reply") or {}
        addressed = mentioned or (bool(reply) and str(reply.get("parent_user_id")) == self.bot_id)
        segments: list[dict] = []
        if reply:
            segments.append({"type": "reply", "message_id": str(reply.get("parent_message_id") or ""),
                             "text": str(reply.get("parent_message_body") or ""),
                             "sender_id": str(reply.get("parent_user_id") or ""),
                             "sender_name": plain_name(reply.get("parent_user_name"), reply.get("parent_user_login"))})
        if mentioned:
            segments.append({"type": "mention", "user_id": self.bot_id, "name": self.login_name})
        if not text:
            return None
        segments.append({"type": "text", "text": text})
        return {"conversation_type": "group", "conversation_id": channel,
                "sender_id": uid, "sender_name": plain_name(data.get("chatter_user_name"), login, uid),
                "message_id": str(data.get("message_id") or ""), "sent_at": _stamp(stamp),
                "addressed": addressed, "text": text, "segments": segments, "reply_handle": channel}

    def target(self, delivery: dict) -> str:
        handle = str(delivery.get("reply_handle") or "")
        if not handle or (self.channel_ids and handle not in self.channel_ids):
            raise Unsupported()
        return handle

    async def _pace(self, channel: str) -> None:
        """Stay under Twitch's chat limits, which silence a bot for an hour."""
        while True:
            now = time.monotonic()
            while self.sent_times and now - self.sent_times[0] > SEND_WINDOW_S:
                self.sent_times.popleft()
            wait = 0.0
            if len(self.sent_times) >= SEND_PER_WINDOW:
                wait = SEND_WINDOW_S - (now - self.sent_times[0])
            wait = max(wait, CHANNEL_GAP_S - (now - self.last_sent.get(channel, -1e9)))
            if wait <= 0:
                self.sent_times.append(now)
                self.last_sent[channel] = now
                return
            await asyncio.sleep(wait)

    async def _post(self, channel: str, text: str) -> None:
        async with self._sending:
            await self._pace(channel)
            response = await self.helix("POST", "/chat/messages", json={
                "broadcaster_id": channel, "sender_id": self.bot_id, "message": text})
        if response.status_code >= 400:
            raise ConnectionError(f"send: {response.status_code}")
        result = (response.json().get("data") or [{}])[0]
        if not result.get("is_sent"):
            reason = (result.get("drop_reason") or {}).get("code") or "dropped"
            raise ConnectionError(f"send: {reason}")

    async def send(self, target: str, items: list) -> int:
        sent = 0
        for item in items:
            text = str(item.get("text") or "").strip() if item.get("type") == "text" else ""
            if not text:
                continue        # Twitch chat carries text only
            try:
                mention = self.logins.get(raw_id(item.get("mention_user_id"), self.kind), "")
                for i, piece in enumerate(split_text(text, MAX_TEXT - MENTION_ROOM)):
                    lead = f"@{mention} " if i == 0 and mention else ""
                    await self._post(target, lead + piece)
            except (ConnectionError, Refused) as exc:
                logger.warning("twitch: sending stopped after %d item(s) (%s)", sent, exc)
                break
            sent += 1
        return sent

    async def close(self) -> None:
        await self.client.aclose()


def _stamp(value: Any) -> int:
    """EventSub timestamps carry nanoseconds, which Python 3.10 cannot parse."""
    text = str(value or "")
    try:
        return int(datetime.strptime(text[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc).timestamp())
    except ValueError:
        return int(time.time())
