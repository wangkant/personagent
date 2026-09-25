"""The connector SDK: its signatures pass the agent's own check, and its
outbox loop sends each delivery at most once and acks it on the next pull."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import httpx
import pytest

import main as main_module

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "integrations" / "sdk"))
import personagent_connector as sdk  # noqa: E402


def test_the_agent_accepts_what_the_sdk_signs() -> None:
    body = sdk.canonical_body({"b": "中文", "a": 1})
    assert body == '{"a":1,"b":"中文"}'.encode("utf-8")
    headers = {k.lower(): v for k, v in sdk.signed_headers(body, "tok-123").items()}
    guard = main_module.ReplayGuard()
    assert main_module._verify_gateway_envelope(body, headers, "tok-123", replay_guard=guard)
    assert not main_module._verify_gateway_envelope(body + b" ", headers, "tok-123",
                                                   replay_guard=main_module.ReplayGuard())
    assert not main_module._verify_gateway_envelope(body, headers, "other",
                                                   replay_guard=main_module.ReplayGuard())


def test_the_endpoint_rule_matches_the_plugin() -> None:
    assert sdk.endpoint_allowed("http://127.0.0.1:8080/webhook/gateway", "")
    assert sdk.endpoint_allowed("http://[::1]:8080/webhook/gateway", "")
    assert sdk.endpoint_allowed("https://agent.example.com/webhook/gateway", "t")
    assert not sdk.endpoint_allowed("https://agent.example.com/webhook/gateway", "")
    assert not sdk.endpoint_allowed("http://agent.example.com/webhook/gateway", "t")
    assert not sdk.endpoint_allowed("localhost:8080/webhook/gateway", "")
    with pytest.raises(ValueError):
        sdk.Connector("http://agent:8080/webhook/gateway", "t", forwarder_id="x")
    assert sdk.outbox_url_for("http://127.0.0.1:8080/webhook/gateway/") \
        == "http://127.0.0.1:8080/webhook/gateway/outbox"


def _agent(pulls: list[dict], seen: list[dict]):
    """A fake agent: records every request body, answers outbox pulls in turn."""
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        seen.append({"path": request.url.path, **payload})
        if request.url.path.endswith("/outbox"):
            return httpx.Response(200, json=pulls.pop(0) if pulls else {"deliveries": []})
        return httpx.Response(200, json={"handled": True, "owned": True, "replies": []})
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def test_send_event_adds_the_forwarder_id() -> None:
    seen: list[dict] = []

    async def run() -> dict:
        conn = sdk.Connector("http://127.0.0.1:8080/webhook/gateway", forwarder_id="c1",
                             client=_agent([], seen))
        return await conn.send_event({"platform": "matrix", "message_type": "private"})

    assert asyncio.run(run())["owned"] is True
    assert seen[0]["forwarder_id"] == "c1" and seen[0]["path"] == "/webhook/gateway"


def test_the_outbox_loop_delivers_once_and_acks() -> None:
    delivery = {"delivery_id": "d1", "conversation_key": "matrix:!r", "expires_in_s": 60,
                "items": [{"type": "text", "text": "hi"}]}
    fresh = {"delivery_id": "d3", "conversation_key": "matrix:!r", "expires_in_s": 60,
             "items": [{"type": "text", "text": "again"}]}
    stale = {"delivery_id": "d2", "conversation_key": "matrix:!r", "expires_in_s": 0.01,
             "items": [{"type": "text", "text": "late"}]}
    # d1 is offered twice (a replayed response) and must be sent once; d3
    # takes long enough that d2 has expired by the time its turn comes.
    pulls = [{"deliveries": [delivery]}, {"deliveries": [delivery, fresh, stale]},
             {"deliveries": []}]
    seen: list[dict] = []
    sent: list[str] = []

    async def deliver(d: dict) -> tuple[str, int]:
        await asyncio.sleep(0.05)      # long enough for d2's 10 ms to run out
        sent.append(d["delivery_id"])
        return "sent", len(d["items"])

    async def run() -> None:
        conn = sdk.Connector("http://127.0.0.1:8080/webhook/gateway", forwarder_id="c1",
                             client=_agent(pulls, seen))
        stop = asyncio.Event()

        async def stopper() -> None:
            while len(seen) < 4:
                await asyncio.sleep(0.01)
            stop.set()

        await asyncio.wait_for(
            asyncio.gather(conn.run_outbox(deliver, wait_s=0, idle_s=0.01, stop=stop),
                           stopper()), timeout=10)

    asyncio.run(run())
    assert sent == ["d1", "d3"], sent
    acks = [a for req in seen for a in req.get("acks", [])]
    assert {"delivery_id": "d1", "status": "sent", "sent_items": 1} in acks, acks
    assert any(a["delivery_id"] == "d2" and a["status"] == "expired" for a in acks), acks
    assert all(req["kind"] == "outbox.pull" and req["forwarder_id"] == "c1"
               for req in seen if req["path"].endswith("/outbox"))


def test_acks_survive_a_failed_pull() -> None:
    attempts: list[list] = []

    def handler(request: httpx.Request) -> httpx.Response:
        attempts.append(json.loads(request.content)["acks"])
        return httpx.Response(503) if len(attempts) == 1 else httpx.Response(200, json={})

    async def run() -> None:
        conn = sdk.Connector("http://127.0.0.1:8080/webhook/gateway", forwarder_id="c1",
                             client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
        conn._pending_acks = [{"delivery_id": "d9", "status": "sent", "sent_items": 1}]
        with pytest.raises(httpx.HTTPStatusError):
            await conn.pull_once(wait_s=0)
        await conn.pull_once(wait_s=0)

    asyncio.run(run())
    assert attempts[0] == attempts[1] == [{"delivery_id": "d9", "status": "sent", "sent_items": 1}]
