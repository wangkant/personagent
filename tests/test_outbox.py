"""The outbox: where a gateway conversation's address is kept, how queued
messages are handed to a connector exactly once, and the endpoint it pulls
from (docs/connectors.md, "Outbox")."""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import time
from pathlib import Path

import httpx

import main as main_module
from persona_agent import outbox as outbox_mod
from persona_agent import promotion
from persona_agent.agent import Agent
from persona_agent.outbox import HandleStore, Outbox

BOT_QQ = "10001"
TOKEN = "outbox-secret"


def check(name: str, cond: bool, detail: str = "") -> None:
    assert cond, name + (f" - {detail}" if detail else "")


def make_agent(tmp: Path) -> Agent:
    """A real agent with every state file it may write redirected to `tmp`."""
    a = Agent(
        api_key="test-key", bot_qq=BOT_QQ, bot_name="TestBot",
        napcat_api="http://127.0.0.1:9",
        memory_file=str(tmp / "memory.json"), persona="test persona",
        eval_enable=False, eval_file=str(tmp / "eval.jsonl"),
        stickers_dir=str(tmp / "stickers"),
        stickers_file=str(tmp / "stickers.json"),
        message_debounce_sec=0, lang="en",
    )
    a._seen_msg_file = tmp / "seen_msg_ids.json"
    a.example_candidates = promotion.CandidatePool(tmp / "example_candidates.json")
    a.core_memory_file = tmp / "core_memory.json"
    a.gateway_handles.path = tmp / "gateway_handles.json"
    a.examples_file = tmp / "examples.jsonl"
    a.feedback_file = tmp / "feedback.jsonl"
    a._seen_msg_ids.clear()
    a.core_memory.clear()
    a._typing_delay = lambda chunk: 0.0

    async def fake_think(group_id, mode, text="", caller_override=None):
        return "on it", "called", ""

    async def fake_chat_private(history, is_owner=False, pkey="",
                                proactive=False, proactive_cue=""):
        return "hi back", ""

    a._think = fake_think
    a._chat_private = fake_chat_private
    return a


FORWARDER = {"forwarder_id": "fw1", "reply_handle": "tg-bot:GroupMessage:c1",
             "caps": ["outbox", "quote_text"]}


def group_event(mid, *, platform="telegram", gid="c1", uid="42", **extra) -> dict:
    return {
        "platform": platform, "message_type": "group", "conversation_id": gid,
        "user_id": uid, "sender_name": "Alice", "self_id": "999000",
        "message_id": mid, "source_timestamp": int(time.time()),
        "is_at_me": True, "raw_text": "you there",
        "segments": [{"type": "text", "text": "you there"}], **extra,
    }


def dm_event(mid, *, platform="telegram", uid="1", **extra) -> dict:
    return {
        "platform": platform, "message_type": "private", "user_id": uid,
        "sender_name": "Kay", "self_id": "999000", "message_id": mid,
        "source_timestamp": int(time.time()), "is_at_me": False,
        "raw_text": "hi", "segments": [{"type": "text", "text": "hi"}],
        **extra,
    }


# ---------------------------------------------------------------------------
# The handle store
# ---------------------------------------------------------------------------

async def test_an_admitted_turn_leaves_an_address(tmp: Path) -> None:
    agent = make_agent(tmp)
    agent.gateway_native_platforms = {"aiocqhttp"}

    await agent.handle_gateway(group_event("m1", **FORWARDER))
    room = agent.gateway_handles.get("telegram:c1")
    check("group: the handle is stored under the routing key",
          room is not None and room["reply_handle"] == "tg-bot:GroupMessage:c1"
          and room["forwarder_id"] == "fw1"
          and room["caps"] == ["outbox", "quote_text"]
          and room["platform"] == "telegram" and room["native"] is False
          and room["message_type"] == "group"
          and room["conversation_id"] == "c1", repr(room))

    await agent.handle_gateway(dm_event(
        "m2", forwarder_id="fw1", reply_handle="tg-bot:FriendMessage:1",
        caps=["outbox"]))
    dm = agent.gateway_handles.get("private:telegram:1")
    check("DM: stored under the DM routing key, with the raw user id",
          dm is not None and dm["message_type"] == "private"
          and dm["conversation_id"] == "1", repr(dm))

    await agent.handle_gateway(group_event(
        "m3", platform="aiocqhttp", gid="555", uid="777",
        forwarder_id="fw1", reply_handle="qq:GroupMessage:555", caps=["outbox"]))
    native = agent.gateway_handles.get("555")
    check("native: stored under the bare key, marked native",
          native is not None and native["native"] is True
          and native["platform"] == "aiocqhttp", repr(native))

    agent.allowed_groups = {"telegram:c1"}
    refused = await agent.handle_gateway(group_event(
        "m4", gid="c2", forwarder_id="fw1", reply_handle="h", caps=["outbox"]))
    check("refused: a turn the agent refuses stores nothing",
          refused["owned"] is False
          and agent.gateway_handles.get("telegram:c2") is None, repr(refused))

    rebuilt = HandleStore(tmp / "gateway_handles.json")
    check("persisted: a new store on the same file has the handles",
          rebuilt.get("telegram:c1") == room and rebuilt.get("555") == native)


async def test_an_old_forwarder_sees_no_change(tmp: Path) -> None:
    """An event with none of the new fields is answered exactly as before,
    and leaves nothing behind."""
    agent = make_agent(tmp)
    result = await agent.handle_gateway(group_event("m1"))
    check("old event: answered the old way",
          set(result) == {"handled", "owned", "replies"}
          and result["handled"] is True and result["owned"] is True
          and result["replies"][0]["text"] == "on it", repr(result))
    check("old event: no handle, no file",
          agent.gateway_handles.keys() == []
          and not (tmp / "gateway_handles.json").exists())
    check("old event: no way to reach it unprompted",
          agent.outbox.route("telegram:c1") is None)

    await agent.handle_gateway(group_event(
        "m2", gid="c9", forwarder_id="fw1", reply_handle="bad\x00handle",
        caps=["outbox"]))
    await agent.outbox.pull("fw1", wait_s=0)
    check("a malformed handle is ignored, so there is no route",
          agent.gateway_handles.get("telegram:c9")["reply_handle"] == ""
          and agent.outbox.route("telegram:c9") is None)


def test_the_handle_store_is_bounded_and_keeps_unsupported(tmp: Path) -> None:
    store = HandleStore(tmp / "h.json", cap=2)

    def put(key, handle="h"):
        store.record(key, reply_handle=handle, forwarder_id="fw", caps=["outbox"],
                     platform="telegram", native=False, message_type="group",
                     conversation_id=key)

    put("a")
    put("b")
    put("a")          # touched: b is now the oldest
    put("c")
    check("bounded: the least recently updated entry goes",
          sorted(store.keys()) == ["a", "c"], repr(store.keys()))
    reloaded = HandleStore(tmp / "h.json", cap=2)
    check("bounded: the file holds what memory holds",
          sorted(reloaded.keys()) == ["a", "c"], repr(reloaded.keys()))

    store.mark_unsupported("a", "h")
    put("a")
    check("unsupported: kept while the connector keeps the same address",
          store.get("a").get("unsupported") is True)
    put("a", handle="h2")
    check("unsupported: cleared by a new address",
          "unsupported" not in store.get("a"))

    (tmp / "bad.json").write_text("{not json", encoding="utf-8")
    check("a corrupt file reads as empty", HandleStore(tmp / "bad.json").keys() == [])


# ---------------------------------------------------------------------------
# The queue
# ---------------------------------------------------------------------------

HANDLE = {"reply_handle": "tg-bot:GroupMessage:c1", "forwarder_id": "fw1",
          "caps": ["outbox"], "platform": "telegram", "native": False,
          "message_type": "group", "conversation_id": "c1"}
ITEMS = [{"type": "text", "text": "anyone up?"}, {"type": "text", "text": "hm"}]


def fresh_outbox(tmp: Path) -> Outbox:
    box = Outbox(HandleStore(tmp / "handles.json"))
    box.poll_s = 0.02
    return box


async def test_a_long_poll_wakes_when_something_is_queued(tmp: Path) -> None:
    box = fresh_outbox(tmp)
    started = time.monotonic()
    pull = asyncio.create_task(box.pull("fw1", wait_s=5))
    await asyncio.sleep(0.05)
    sending = asyncio.create_task(
        box.deliver("telegram:c1", HANDLE, ITEMS, reason="proactive"))
    answer = await asyncio.wait_for(pull, 2)
    elapsed = time.monotonic() - started
    check("long-poll: returns as soon as a delivery is queued",
          elapsed < 1.0 and len(answer["deliveries"]) == 1, repr((elapsed, answer)))
    d = answer["deliveries"][0]
    check("long-poll: the delivery carries what the connector needs",
          d["reply_handle"] == HANDLE["reply_handle"]
          and d["conversation_key"] == "telegram:c1" and d["platform"] == "telegram"
          and d["message_type"] == "group" and d["conversation_id"] == "c1"
          and d["reason"] == "proactive" and d["items"] == ITEMS
          and 0 < d["expires_in_s"] <= 300 and d["delivery_id"].startswith("d_"),
          repr(d))
    check("long-poll: tells the connector how long to wait next",
          answer["next_wait_s"] == outbox_mod.DEFAULT_WAIT_S)

    again = await box.pull("fw1", wait_s=0)
    check("at most once: a later pull does not hand it out again",
          again["deliveries"] == [], repr(again))
    await box.pull("fw2", wait_s=0, acks=[{"delivery_id": d["delivery_id"],
                                           "status": "failed"}])
    check("at most once: another connector cannot settle it",
          not sending.done())
    await box.pull("fw1", wait_s=0, acks=[
        {"delivery_id": d["delivery_id"], "status": "sent", "sent_items": 2}])
    result = await asyncio.wait_for(sending, 2)
    check("ack: sent settles the waiting caller",
          (result.status, result.sent_items) == ("sent", 2), repr(result))
    await box.pull("fw1", wait_s=0, acks=[
        {"delivery_id": d["delivery_id"], "status": "failed"}])
    check("ack: a repeated ack changes nothing", result.status == "sent")

    empty_started = time.monotonic()
    empty = await box.pull("fw1", wait_s=0.2)
    check("long-poll: an empty pull waits out wait_s and returns nothing",
          empty["deliveries"] == [] and time.monotonic() - empty_started >= 0.18)


async def _settle(box: Outbox, ack: dict) -> outbox_mod.OutboxResult:
    await box.pull("fw1", wait_s=0)
    sending = asyncio.create_task(
        box.deliver("telegram:c1", HANDLE, ITEMS, reason="follow_up"))
    answer = await box.pull("fw1", wait_s=2)
    ack = dict(ack, delivery_id=answer["deliveries"][0]["delivery_id"])
    await box.pull("fw1", wait_s=0, acks=[ack])
    return await asyncio.wait_for(sending, 2)


async def test_acks_map_to_what_was_sent(tmp: Path) -> None:
    box = fresh_outbox(tmp)
    cases = [
        ({"status": "partial", "sent_items": 1}, ("partial", 1)),
        ({"status": "partial", "sent_items": 2}, ("sent", 2)),
        ({"status": "partial", "sent_items": "x"}, ("failed", 0)),
        ({"status": "failed"}, ("failed", 0)),
        ({"status": "expired"}, ("expired", 0)),
        ({"status": "refused"}, ("refused", 0)),
        ({"status": "made-up"}, ("failed", 0)),
    ]
    for ack, expected in cases:
        result = await _settle(box, ack)
        check(f"ack {ack}: -> {expected}",
              (result.status, result.sent_items) == expected, repr(result))

    box.handles.record("telegram:c1", reply_handle=HANDLE["reply_handle"],
                       forwarder_id="fw1", caps=["outbox"], platform="telegram",
                       native=False, message_type="group", conversation_id="c1")
    check("route: a live connector with the outbox cap is a route",
          box.route("telegram:c1") is not None)
    result = await _settle(box, {"status": "unsupported"})
    check("unsupported: the conversation stops being a route",
          result.status == "unsupported" and box.route("telegram:c1") is None)


async def test_what_is_never_pulled_or_never_acked_is_not_sent(tmp: Path) -> None:
    box = fresh_outbox(tmp)
    box.ttl_s["excuse"] = 0.2
    await box.pull("fw1", wait_s=0)
    result = await asyncio.wait_for(
        box.deliver("telegram:c1", HANDLE, ITEMS, reason="excuse"), 2)
    check("expiry: a delivery nobody pulled in time ends unsent",
          result.status == "expired_unpulled", repr(result))
    check("expiry: and is not handed out afterwards",
          (await box.pull("fw1", wait_s=0))["deliveries"] == [])

    box.ttl_s["excuse"] = 0.3
    box.ack_grace_s = 0.1
    sending = asyncio.create_task(
        box.deliver("telegram:c1", HANDLE, ITEMS, reason="excuse"))
    handed = await box.pull("fw1", wait_s=2)
    result = await asyncio.wait_for(sending, 3)
    check("no ack: handed out but never acked counts as not sent",
          len(handed["deliveries"]) == 1 and result.status == "no_ack"
          and result.sent_items == 0, repr(result))


async def test_a_connector_that_stops_pulling_is_gone(tmp: Path) -> None:
    box = fresh_outbox(tmp)
    box.liveness_s = 0.2
    box.handles.record("telegram:c1", reply_handle="h", forwarder_id="fw1",
                       caps=["outbox"], platform="telegram", native=False,
                       message_type="group", conversation_id="c1")
    check("liveness: never pulled, never live", box.route("telegram:c1") is None)
    await box.pull("fw1", wait_s=0)
    check("liveness: a pull makes it live", box.route("telegram:c1") is not None)
    sending = asyncio.create_task(
        box.deliver("telegram:c1", HANDLE, ITEMS, reason="proactive"))
    result = await asyncio.wait_for(sending, 2)
    check("liveness: a queued delivery ends when its connector goes quiet",
          result.status == "gone", repr(result))
    check("liveness: after the window, no route",
          box.route("telegram:c1") is None)
    box.handles.record("telegram:c2", reply_handle="h", forwarder_id="fw1",
                       caps=["quote_text"], platform="telegram", native=False,
                       message_type="group", conversation_id="c2")
    await box.pull("fw1", wait_s=0)
    check("caps: no outbox cap, no route", box.route("telegram:c2") is None)


async def test_order_bounds_and_connectors_are_kept_apart(tmp: Path) -> None:
    box = fresh_outbox(tmp)
    await box.pull("fw1", wait_s=0)
    await box.pull("fw2", wait_s=0)
    other = dict(HANDLE, forwarder_id="fw2")
    tasks = [asyncio.create_task(box.deliver(key, handle, [{"type": "text", "text": t}],
                                             reason="proactive"))
             for key, handle, t in (("telegram:c1", HANDLE, "a1"),
                                    ("telegram:c2", HANDLE, "b1"),
                                    ("telegram:c1", HANDLE, "a2"),
                                    ("slack:x", other, "s1"))]
    await asyncio.sleep(0.01)
    first = await box.pull("fw1", wait_s=0)
    texts = [d["items"][0]["text"] for d in first["deliveries"]]
    check("order: handed out in the order queued",
          texts == ["a1", "b1", "a2"], repr(texts))
    second = await box.pull("fw2", wait_s=0)
    check("connectors: each pulls only its own conversations",
          [d["items"][0]["text"] for d in second["deliveries"]] == ["s1"])

    fill = [asyncio.create_task(box.deliver("telegram:c9", HANDLE, ITEMS,
                                            reason="proactive"))
            for _ in range(outbox_mod.MAX_PER_CONVERSATION + 1)]
    await asyncio.sleep(0.01)
    done = [t.result() for t in fill if t.done()]
    check("bounded: past the per-conversation cap a delivery is refused",
          len(done) == 1 and done[0].status == "full", repr(done))

    await box.aclose()
    results = await asyncio.wait_for(asyncio.gather(*tasks, *fill), 2)
    check("close: every waiting caller ends as not sent",
          all(r.status in ("closed", "full") for r in results), repr(results))
    check("close: a pull after close returns at once",
          (await asyncio.wait_for(box.pull("fw1", wait_s=5), 1))["deliveries"] == [])


def test_a_pull_body_is_checked() -> None:
    parse = outbox_mod.parse_pull
    good = parse({"kind": "outbox.pull", "forwarder_id": "fw1"})
    check("pull: defaults fill the optional fields",
          good == {"forwarder_id": "fw1", "wait_s": 25.0, "max_deliveries": 10,
                   "acks": []}, repr(good))
    for bad in ({"forwarder_id": "fw1"},
                {"kind": "event", "forwarder_id": "fw1"},
                {"kind": "outbox.pull"},
                {"kind": "outbox.pull", "forwarder_id": "fw1", "wait_s": "25"},
                {"kind": "outbox.pull", "forwarder_id": "fw1", "wait_s": float("nan")},
                {"kind": "outbox.pull", "forwarder_id": "fw1", "max_deliveries": True},
                {"kind": "outbox.pull", "forwarder_id": "fw1", "acks": {}},
                ["outbox.pull"]):
        check(f"pull: refused {bad!r}", parse(bad) is None)


# ---------------------------------------------------------------------------
# The endpoint
# ---------------------------------------------------------------------------

def _body(payload: dict) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def _signed(body: bytes, *, nonce: str, token: str = TOKEN) -> dict:
    stamp = str(int(time.time()))
    mac = hmac.new(token.encode(), stamp.encode() + b"." + nonce.encode()
                   + b"." + body, hashlib.sha256).hexdigest()
    return {"content-type": "application/json", "x-gateway-token": token,
            "x-gateway-timestamp": stamp, "x-gateway-nonce": nonce,
            "x-gateway-signature": "sha256=" + mac}


def _client() -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=main_module.app, client=("127.0.0.1", 1234))
    return httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:8080")


class _Served:
    """Point main at an agent and a fresh replay guard, and put them back."""

    def __init__(self, agent, token: str = TOKEN) -> None:
        self.agent, self.token = agent, token

    def __enter__(self):
        self.saved = (main_module.agent, main_module.GATEWAY_TOKEN,
                      main_module._gateway_replay)
        main_module.agent = self.agent
        main_module.GATEWAY_TOKEN = self.token
        main_module._gateway_replay = main_module.ReplayGuard()
        return self

    def __exit__(self, *exc):
        (main_module.agent, main_module.GATEWAY_TOKEN,
         main_module._gateway_replay) = self.saved


PULL = {"kind": "outbox.pull", "forwarder_id": "fw1", "wait_s": 0,
        "max_deliveries": 10, "acks": []}


async def test_the_outbox_endpoint_is_authenticated_like_the_gateway(
        tmp: Path) -> None:
    agent = make_agent(tmp)
    body = _body(PULL)
    event = _body(group_event("m1"))
    with _Served(agent):
        async with _client() as client:
            unsigned = await client.post("/webhook/gateway/outbox", content=body)
            wrong = await client.post(
                "/webhook/gateway/outbox", content=body,
                headers=_signed(body, nonce="n0", token="nope"))
            ok = await client.post("/webhook/gateway/outbox", content=body,
                                   headers=_signed(body, nonce="n1"))
            replayed = await client.post("/webhook/gateway/outbox", content=body,
                                         headers=_signed(body, nonce="n1"))
            event_here = await client.post(
                "/webhook/gateway/outbox", content=event,
                headers=_signed(event, nonce="n2"))
            pull_there = await client.post(
                "/webhook/gateway", content=body, headers=_signed(body, nonce="n3"))
            kinded = _body(dict(group_event("m5"), kind="event"))
            event_kinded = await client.post(
                "/webhook/gateway", content=kinded,
                headers=_signed(kinded, nonce="n4"))
            agent.gateway_outbox = False
            disabled = await client.post("/webhook/gateway/outbox", content=body,
                                         headers=_signed(body, nonce="n5"))
    check("auth: no envelope is refused",
          unsigned.status_code == 403
          and unsigned.json()["code"] == "invalid_envelope", unsigned.text)
    check("auth: a wrong token is refused", wrong.status_code == 403)
    check("auth: a signed pull is answered",
          ok.status_code == 200 and ok.json()["deliveries"] == [], ok.text)
    check("auth: a replayed nonce is refused",
          replayed.status_code == 403
          and replayed.json()["code"] == "invalid_envelope", replayed.text)
    check("kind: an event body on the outbox is refused",
          event_here.status_code == 400
          and event_here.json()["code"] == "invalid_schema", event_here.text)
    check("kind: a pull body on the event endpoint is refused",
          pull_there.status_code == 400
          and pull_there.json()["code"] == "invalid_schema", pull_there.text)
    check("kind: an event may name its kind",
          event_kinded.status_code == 200
          and event_kinded.json()["owned"] is True, event_kinded.text)
    check("disabled: GATEWAY_OUTBOX=false answers 404 with a code",
          disabled.status_code == 404
          and disabled.json()["code"] == "outbox_disabled", disabled.text)

    with _Served(None):
        async with _client() as client:
            no_agent = await client.post("/webhook/gateway/outbox", content=body,
                                         headers=_signed(body, nonce="n6"))
    check("disabled: no agent, no outbox", no_agent.status_code == 404)

    agent.gateway_outbox = True
    with _Served(agent, token=""):
        async with _client() as client:
            browser = await client.post(
                "/webhook/gateway/outbox", content=body,
                headers={"origin": "https://evil.example"})
            local = await client.post("/webhook/gateway/outbox", content=body)
    check("local: without a token a browser-shaped caller is refused",
          browser.status_code == 403
          and browser.json()["code"] == "non_local_request", browser.text)
    check("local: without a token a local program may pull",
          local.status_code == 200, local.text)


async def test_a_pull_over_http_delivers_and_its_ack_commits(tmp: Path) -> None:
    agent = make_agent(tmp)
    with _Served(agent):
        async with _client() as client:
            first = _body(PULL)
            await client.post("/webhook/gateway/outbox", content=first,
                              headers=_signed(first, nonce="p0"))
            waiting = _body(dict(PULL, wait_s=5))
            pull = asyncio.create_task(client.post(
                "/webhook/gateway/outbox", content=waiting,
                headers=_signed(waiting, nonce="p1")))
            await asyncio.sleep(0.1)
            sending = asyncio.create_task(agent.outbox.deliver(
                "telegram:c1", HANDLE, ITEMS, reason="proactive"))
            answer = (await asyncio.wait_for(pull, 3)).json()
            delivery_id = answer["deliveries"][0]["delivery_id"]
            ack = _body(dict(PULL, acks=[{"delivery_id": delivery_id,
                                          "status": "partial", "sent_items": 1}]))
            await client.post("/webhook/gateway/outbox", content=ack,
                              headers=_signed(ack, nonce="p2"))
            result = await asyncio.wait_for(sending, 2)
    check("http: the long-poll hands the delivery over",
          answer["deliveries"][0]["items"] == ITEMS, repr(answer))
    check("http: the ack on the next pull settles it",
          (result.status, result.sent_items) == ("partial", 1), repr(result))


async def test_long_polls_and_turns_do_not_share_slots(tmp: Path) -> None:
    agent = make_agent(tmp)
    gate, outbox_gate = main_module._gateway_admission, main_module._outbox_admission
    body = _body(PULL)
    with _Served(agent):
        taken = 0
        try:
            while await gate.try_acquire():
                taken += 1
            async with _client() as client:
                pull = await client.post("/webhook/gateway/outbox", content=body,
                                         headers=_signed(body, nonce="s1"))
        finally:
            for _ in range(taken):
                await gate.release()
        check("slots: a pull is served while every turn slot is taken",
              pull.status_code == 200, pull.text)

        taken = 0
        event = _body(group_event("m1"))
        try:
            while await outbox_gate.try_acquire():
                taken += 1
            async with _client() as client:
                refused = await client.post("/webhook/gateway/outbox", content=body,
                                            headers=_signed(body, nonce="s2"))
                turn = await client.post("/webhook/gateway", content=event,
                                         headers=_signed(event, nonce="s3"))
        finally:
            for _ in range(taken):
                await outbox_gate.release()
    check("slots: a full outbox budget is a 429 for pulls only",
          refused.status_code == 429
          and refused.json()["code"] == "capacity_exceeded", refused.text)
    check("slots: ...and turns are still served",
          turn.status_code == 200 and turn.json()["owned"] is True, turn.text)
