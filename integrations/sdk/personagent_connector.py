"""Client side of the personagent connector protocol (docs/connectors.md).

A connector gets a platform message in, posts it with ``send_event``, and
delivers what comes back. If the platform can send unprompted, it also runs
``run_outbox`` with a ``deliver`` coroutine. Signing, the loopback/HTTPS rule,
at-most-once delivery and acks are handled here; everything about the platform
stays in the connector.

Only depends on httpx, so it can be copied next to a connector as one file.
"""
from __future__ import annotations

import asyncio
import collections
import hashlib
import hmac
import json
import logging
import secrets
import time
from typing import Awaitable, Callable, Optional
from urllib.parse import urlsplit

import httpx

logger = logging.getLogger("personagent_connector")

#: What ``deliver`` returns: (status, sent_items). status is one of
#: "sent", "partial", "failed", "refused", "unsupported".
DeliveryResult = tuple[str, int]
Deliver = Callable[[dict], Awaitable[DeliveryResult]]

_LOOPBACK = {"localhost", "127.0.0.1", "::1"}


def endpoint_allowed(url: str, token: str) -> bool:
    """Loopback, or HTTPS with a token: a token must never cross a network in
    clear text, and without one only a local caller is trusted."""
    try:
        parts = urlsplit(url)
    except ValueError:
        return False
    host = (parts.hostname or "").lower()
    if not host or parts.scheme not in ("http", "https"):
        return False
    return host in _LOOPBACK or (parts.scheme == "https" and bool(token))


def canonical_body(payload: dict) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def signed_headers(body: bytes, token: str, *, now: Optional[float] = None) -> dict:
    headers = {"Content-Type": "application/json"}
    if not token:
        return headers
    timestamp = str(int(time.time() if now is None else now))
    nonce = secrets.token_hex(16)
    mac = hmac.new(token.encode("utf-8"),
                   timestamp.encode() + b"." + nonce.encode() + b"." + body,
                   hashlib.sha256).hexdigest()
    headers.update({
        "X-Gateway-Token": token,
        "X-Gateway-Timestamp": timestamp,
        "X-Gateway-Nonce": nonce,
        "X-Gateway-Signature": f"sha256={mac}",
    })
    return headers


def outbox_url_for(event_url: str) -> str:
    return event_url.rstrip("/") + "/outbox"


class Connector:
    """One connector instance talking to one agent."""

    def __init__(self, agent_url: str, token: str = "", *, forwarder_id: str,
                 timeout_s: float = 180.0, client: Optional[httpx.AsyncClient] = None):
        if not endpoint_allowed(agent_url, token):
            raise ValueError("agent_url must be loopback, or HTTPS with a token")
        if not forwarder_id:
            raise ValueError("forwarder_id is required")
        self.event_url = agent_url
        self.outbox_url = outbox_url_for(agent_url)
        self.token = token
        self.forwarder_id = forwarder_id
        self.timeout_s = timeout_s
        self._client = client
        self._owns_client = client is None
        # Delivery ids already started; a delivery is never sent twice.
        self._started: collections.deque[str] = collections.deque(maxlen=512)
        self._pending_acks: list[dict] = []

    async def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient()
        return self._client

    async def aclose(self) -> None:
        if self._client is not None and self._owns_client:
            await self._client.aclose()
            self._client = None

    async def _post(self, url: str, payload: dict, timeout_s: float) -> httpx.Response:
        body = canonical_body(payload)
        client = await self._http()
        return await client.post(url, content=body, timeout=timeout_s,
                                 headers=signed_headers(body, self.token))

    async def send_event(self, event: dict) -> dict:
        """Post one neutral event; returns the agent's JSON response.

        Adds ``forwarder_id`` when the event has none. Raises httpx errors and
        ``httpx.HTTPStatusError`` for a non-2xx answer, whose body carries the
        agent's ``code`` and ``error``."""
        event = dict(event)
        event.setdefault("forwarder_id", self.forwarder_id)
        response = await self._post(self.event_url, event, self.timeout_s)
        response.raise_for_status()
        return response.json()

    async def pull_once(self, *, wait_s: int = 25, max_deliveries: int = 10) -> dict:
        acks, self._pending_acks = self._pending_acks, []
        payload = {"kind": "outbox.pull", "forwarder_id": self.forwarder_id,
                   "wait_s": wait_s, "max_deliveries": max_deliveries, "acks": acks}
        try:
            response = await self._post(self.outbox_url, payload, wait_s + 10)
            response.raise_for_status()
        except Exception:
            # The agent never saw these acks; they ride on the next pull.
            self._pending_acks = acks + self._pending_acks
            raise
        return response.json()

    async def _deliver_one(self, delivery: dict, deliver: Deliver, received_at: float) -> None:
        delivery_id = str(delivery.get("delivery_id") or "")
        if not delivery_id or delivery_id in self._started:
            return
        self._started.append(delivery_id)
        ttl = float(delivery.get("expires_in_s") or 0)
        if ttl and time.monotonic() - received_at > ttl:
            status, sent = "expired", 0
        else:
            try:
                status, sent = await deliver(delivery)
            except Exception:
                logger.exception("delivery %s failed", delivery_id)
                status, sent = "failed", 0
        self._pending_acks.append({"delivery_id": delivery_id, "status": status,
                                   "sent_items": int(sent)})

    async def run_outbox(self, deliver: Deliver, *, wait_s: int = 25, idle_s: float = 1.0,
                         stop: Optional[asyncio.Event] = None) -> None:
        """Pull and deliver until ``stop`` is set.

        Deliveries are sent in the order received; the next pull carries their
        acks and goes out as soon as they are done. An empty answer that came
        back at once (an agent not holding the long-poll) waits ``idle_s``
        before the next pull, so the loop never spins."""
        backoff = 1.0
        while stop is None or not stop.is_set():
            started = time.monotonic()
            try:
                answer = await self.pull_once(wait_s=wait_s)
            except httpx.HTTPStatusError as exc:
                pause = 600.0 if exc.response.status_code == 404 else backoff
                if exc.response.status_code == 404:
                    logger.info("agent has no outbox (older version); retrying in 10 minutes")
                else:
                    logger.warning("outbox pull refused (%s)", exc.response.status_code)
                backoff = min(backoff * 2, 60.0)
                await self._sleep(pause, stop)
                continue
            except Exception as exc:
                logger.warning("outbox pull failed: %s", exc)
                await self._sleep(backoff, stop)
                backoff = min(backoff * 2, 60.0)
                continue
            backoff = 1.0
            received_at = time.monotonic()
            deliveries = answer.get("deliveries") or []
            for delivery in deliveries:
                await self._deliver_one(delivery, deliver, received_at)
            if not deliveries and received_at - started < min(idle_s, 1.0):
                await self._sleep(idle_s, stop)

    @staticmethod
    async def _sleep(seconds: float, stop: Optional[asyncio.Event]) -> None:
        if stop is None:
            await asyncio.sleep(seconds)
            return
        try:
            await asyncio.wait_for(stop.wait(), timeout=seconds)
        except asyncio.TimeoutError:
            pass
