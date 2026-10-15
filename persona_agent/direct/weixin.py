"""Personal WeChat through Tencent's iLink bot API, as documented in
Tencent's MIT-licensed openclaw-weixin repository
(https://github.com/Tencent/openclaw-weixin/blob/main/docs/protocol.md):
QR login, long-polled getupdates in, sendmessage out.

iLink delivers one-to-one chats; a reply must echo the context_token of the
person's latest message, so those tokens are kept on disk per person."""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import random
import secrets
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import quote

import httpx

from .. import __version__
from .base import Platform, Refused, Unsupported, backoff_sleep, split_text
from ..storage import atomic_write_text

logger = logging.getLogger("personagent.direct.weixin")

API = "https://ilinkai.weixin.qq.com"
POLL_TIMEOUT_S = 35
CALL_TIMEOUT_S = 15
# The reference client's chunk size; the protocol states no server limit.
MAX_TEXT = 4000
# getupdates and sendmessage answer this when the bot session is no longer valid.
STALE_SESSION = -14
QR_TTL_S = 300
QR_REFRESHES = 3


def client_version(version: str) -> str:
    """The version as 0x00MMNNPP, sent as a decimal string."""
    numbers = [int(p) if p.isdigit() else 0 for p in version.split(".")[:3]]
    major, minor, patch = (numbers + [0, 0, 0])[:3]
    return str(((major & 0xFF) << 16) | ((minor & 0xFF) << 8) | (patch & 0xFF))


def app_headers() -> dict:
    return {"iLink-App-Id": "bot", "iLink-App-ClientVersion": client_version(__version__.split("dev")[0].rstrip("."))}


def post_headers(token: str = "") -> dict:
    headers = {**app_headers(), "Content-Type": "application/json",
               "AuthorizationType": "ilink_bot_token",
               "X-WECHAT-UIN": base64.b64encode(str(random.getrandbits(32)).encode()).decode()}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def base_info() -> dict:
    return {"channel_version": __version__, "bot_agent": f"personagent/{__version__}"}


class LoginFailed(Exception):
    """The QR login ended without credentials; the message is a code."""


async def login(client: httpx.AsyncClient, show: Callable[[str], None]) -> dict:
    """Show QR codes through `show(content)` until someone confirms one;
    returns the values to store."""
    for _ in range(QR_REFRESHES + 1):
        response = await client.post(f"{API}/ilink/bot/get_bot_qrcode?bot_type=3",
                                     headers=post_headers(), json={"local_token_list": []},
                                     timeout=CALL_TIMEOUT_S)
        response.raise_for_status()
        issued = response.json()
        qrcode, content = str(issued.get("qrcode") or ""), str(issued.get("qrcode_img_content") or "")
        if not qrcode or not content:
            raise LoginFailed("no_qr_code")
        show(content)
        base = API
        deadline = asyncio.get_running_loop().time() + QR_TTL_S
        while asyncio.get_running_loop().time() < deadline:
            try:
                answer = (await client.get(f"{base}/ilink/bot/get_qrcode_status?qrcode={quote(qrcode)}",
                                           headers=app_headers(), timeout=POLL_TIMEOUT_S + 5)).json()
            except (httpx.HTTPError, ValueError):
                answer = {"status": "wait"}
            status = answer.get("status")
            if status == "confirmed":
                if not answer.get("bot_token"):
                    raise LoginFailed("no_token")
                return {"weixin_oc_token": str(answer["bot_token"]),
                        "weixin_oc_account_id": str(answer.get("ilink_bot_id") or ""),
                        "weixin_oc_base_url": str(answer.get("baseurl") or API).rstrip("/"),
                        "weixin_oc_user_id": str(answer.get("ilink_user_id") or "")}
            if status == "expired":
                break
            if status == "scaned_but_redirect" and answer.get("redirect_host"):
                base = "https://" + str(answer["redirect_host"]).strip("/")
            elif status in ("need_verifycode", "verify_code_blocked", "binded_redirect"):
                raise LoginFailed(status)
            await asyncio.sleep(1)
    raise LoginFailed("expired")


class Weixin(Platform):
    kind = "weixin_oc"

    def __init__(self, values: dict, *, state: Optional[Path] = None,
                 client: httpx.AsyncClient | None = None):
        super().__init__(values)
        self.token = str(values.get("weixin_oc_token") or "")
        self.base = str(values.get("weixin_oc_base_url") or API).rstrip("/")
        self.bot_id = str(values.get("weixin_oc_account_id") or "")
        self.client = client or httpx.AsyncClient()
        self.state_path = state
        saved = self._load()
        self.cursor = str(saved.get("cursor") or "")
        self.contexts: dict[str, str] = {k: str(v) for k, v in (saved.get("contexts") or {}).items()}

    def _load(self) -> dict:
        if self.state_path is None:
            return {}
        try:
            value = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return value if isinstance(value, dict) else {}

    def _save(self) -> None:
        if self.state_path is None:
            return
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self.state_path, json.dumps(
            {"cursor": self.cursor, "contexts": self.contexts}, ensure_ascii=False))

    async def call(self, path: str, body: dict, timeout: float = CALL_TIMEOUT_S) -> dict:
        try:
            response = await self.client.post(f"{self.base}/ilink/bot/{path}",
                                              headers=post_headers(self.token),
                                              json={**body, "base_info": base_info()}, timeout=timeout)
        except httpx.TimeoutException:
            return {"ret": 0}       # a long poll that ran out is an empty answer
        except httpx.HTTPError as exc:
            raise ConnectionError(f"{path}: {type(exc).__name__}") from None
        if response.status_code in (401, 403):
            raise Refused("session_expired")
        if response.status_code >= 400:
            raise ConnectionError(f"{path}: {response.status_code}")
        try:
            answer = response.json()
        except ValueError:
            raise ConnectionError(f"{path}: not JSON") from None
        if STALE_SESSION in (answer.get("ret"), answer.get("errcode")):
            raise Refused("session_expired")
        return answer if isinstance(answer, dict) else {}

    async def check(self) -> str:
        if not self.token:
            raise Refused("token_missing")
        return self.bot_id

    async def run(self, on_event, connected) -> None:
        await self.check()
        try:
            await self.call("msg/notifystart", {})
        except ConnectionError as exc:
            logger.warning("weixin: notifystart failed (%s)", exc)
        timeout, failures, announced = POLL_TIMEOUT_S, 0, False
        while True:
            try:
                answer = await self.call("getupdates", {"get_updates_buf": self.cursor}, timeout + 10)
            except ConnectionError as exc:
                logger.warning("weixin: %s", exc)
                await backoff_sleep(failures)
                failures += 1
                continue
            if answer.get("ret") not in (0, None) or answer.get("errcode") not in (0, None):
                logger.warning("weixin: getupdates answered ret=%s errcode=%s",
                               answer.get("ret"), answer.get("errcode"))
                await backoff_sleep(failures)
                failures += 1
                continue
            failures = 0
            if not announced:
                connected()
                announced = True
            if answer.get("longpolling_timeout_ms"):
                timeout = max(5, int(answer["longpolling_timeout_ms"]) // 1000)
            changed = False
            for message in answer.get("msgs") or []:
                if not isinstance(message, dict) or message.get("message_type") != 1:
                    continue
                uid = str(message.get("from_user_id") or "")
                if message.get("context_token") and uid:
                    self.contexts[uid] = str(message["context_token"])
                    changed = True
                event = self.event(message)
                if event:
                    await on_event(event, uid)
            if answer.get("get_updates_buf"):
                self.cursor = str(answer["get_updates_buf"])
                changed = True
            if changed:
                self._save()

    def event(self, message: dict) -> dict | None:
        uid = str(message.get("from_user_id") or "")
        if not uid:
            return None
        segments: list[dict] = []
        texts: list[str] = []
        for item in message.get("item_list") or []:
            kind = item.get("type")
            reference = item.get("ref_msg") or {}
            quoted = (reference.get("message_item") or {}).get("text_item") or {}
            if quoted.get("text"):
                segments.append({"type": "reply", "message_id": str(reference.get("msg_id") or ""),
                                 "text": str(quoted["text"]), "sender_id": "", "sender_name": ""})
            if kind == 1:
                text = str((item.get("text_item") or {}).get("text") or "")
                if text:
                    texts.append(text)
                    segments.append({"type": "text", "text": text})
            elif kind == 3:
                transcript = str((item.get("voice_item") or {}).get("text") or "")
                note = f"(voice message) {transcript}" if transcript else "(sent a voice message)"
                texts.append(note)
                segments.append({"type": "text", "text": note})
            elif kind in (2, 4, 5):
                name = str((item.get("file_item") or {}).get("file_name") or "")
                note = {2: "(sent an image)", 4: f"(sent a file: {name})", 5: "(sent a video)"}[kind]
                segments.append({"type": "text", "text": note})
        if not segments:
            return None
        group = str(message.get("group_id") or "")
        return {"conversation_type": "group" if group else "dm",
                **({"conversation_id": group} if group else {}),
                "sender_id": uid, "sender_name": "",
                "message_id": str(message.get("message_id") or message.get("seq") or secrets.token_hex(8)),
                "sent_at": int(message.get("create_time_ms") or 0) // 1000,
                "addressed": not group, "text": "\n".join(texts), "segments": segments,
                "reply_handle": uid}

    def target(self, delivery: dict) -> str:
        uid = str(delivery.get("reply_handle") or "")
        if not uid or uid not in self.contexts:
            raise Unsupported()
        return uid

    async def send(self, target: str, items: list) -> int:
        sent = 0
        for item in items:
            text = str(item.get("text") or "").strip() if item.get("type") == "text" else ""
            if not text:
                continue        # images need the encrypted CDN upload, not done here
            for piece in split_text(text, MAX_TEXT):
                answer = await self.call("sendmessage", {"msg": {
                    "from_user_id": "", "to_user_id": target, "client_id": secrets.token_hex(16),
                    "message_type": 2, "message_state": 2,
                    "context_token": self.contexts.get(target, ""),
                    "item_list": [{"type": 1, "text_item": {"text": piece}}]}})
                if answer.get("ret") not in (0, None):
                    raise ConnectionError(f"sendmessage: {answer.get('ret')}")
            sent += 1
        return sent

    async def close(self) -> None:
        try:
            await self.call("msg/notifystop", {})
        except Exception:
            pass
        await self.client.aclose()
