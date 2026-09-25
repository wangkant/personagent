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

QQ_BOT_ID = "10001"
TOKEN = "outbox-secret"


def check(name: str, cond: bool, detail: str = "") -> None:
    assert cond, name + (f" - {detail}" if detail else "")


def make_agent(tmp: Path) -> Agent:
    """A real agent with every state file it may write redirected to `tmp`."""
    a = Agent(
        api_key="test-key", qq_bot_id=QQ_BOT_ID, persona_name="TestBot",
        qq_onebot_url="http://127.0.0.1:9",
        memory_file=str(tmp / "memory.json"), persona="test persona",
        eval_enabled=False, eval_file=str(tmp / "eval.jsonl"),
        stickers_dir=str(tmp / "stickers"),
        stickers_file=str(tmp / "stickers.json"),
        message_debounce_sec=0, lang="en",
    )
    a._seen_msg_file = tmp / "seen_msg_ids.json"
    a.example_candidates = promotion.CandidatePool(tmp / "example_candidates.json")
    a.core_memory_file = tmp / "core_memory.json"
    a.gateway_handles.path = tmp / "connector_handles.json"
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


CONNECTOR = {"connector_id": "fw1", "reply_handle": "tg-bot:GroupMessage:c1",
             "capabilities": ["outbox", "quote_text"]}


def group_event(mid, *, platform="telegram", gid="c1", uid="42", **extra) -> dict:
    return {
        "platform": platform, "conversation_type": "group", "conversation_id": gid,
        "sender_id": uid, "sender_name": "Alice", "bot_id": "999000",
        "message_id": mid, "sent_at": int(time.time()),
        "addressed": True, "text": "you there",
        "segments": [{"type": "text", "text": "you there"}], **extra,
    }


def dm_event(mid, *, platform="telegram", uid="1", **extra) -> dict:
    return {
        "platform": platform, "conversation_type": "dm", "sender_id": uid,
        "sender_name": "Kay", "bot_id": "999000", "message_id": mid,
        "sent_at": int(time.time()), "addressed": False,
        "text": "hi", "segments": [{"type": "text", "text": "hi"}],
        **extra,
    }


# ---------------------------------------------------------------------------
# The handle store
# ---------------------------------------------------------------------------

async def test_an_admitted_turn_leaves_an_address(tmp: Path) -> None:
    agent = make_agent(tmp)
    agent.connector_qq_platforms = {"aiocqhttp"}

    await agent.handle_gateway(group_event("m1", **CONNECTOR))
    room = agent.gateway_handles.get("telegram:c1")
    check("group: the handle is stored under the routing key",
          room is not None and room["reply_handle"] == "tg-bot:GroupMessage:c1"
          and room["connector_id"] == "fw1"
          and room["capabilities"] == ["outbox", "quote_text"]
          and room["platform"] == "telegram" and room["native"] is False
          and room["conversation_type"] == "group"
          and room["conversation_id"] == "c1", repr(room))

    await agent.handle_gateway(dm_event(
        "m2", connector_id="fw1", reply_handle="tg-bot:FriendMessage:1",
        capabilities=["outbox"]))
    dm = agent.gateway_handles.get("private:telegram:1")
    check("DM: stored under the DM routing key, with the raw user id",
          dm is not None and dm["conversation_type"] == "dm"
          and dm["conversation_id"] == "1", repr(dm))

    await agent.handle_gateway(group_event(
        "m3", platform="aiocqhttp", gid="555", uid="777",
        connector_id="fw1", reply_handle="qq:GroupMessage:555", capabilities=["outbox"]))
    native = agent.gateway_handles.get("555")
    check("native: stored under the bare key, marked native",
          native is not None and native["native"] is True
          and native["platform"] == "aiocqhttp", repr(native))

    agent.access_groups = {"telegram:c1"}
    refused = await agent.handle_gateway(group_event(
        "m4", gid="c2", connector_id="fw1", reply_handle="h", capabilities=["outbox"]))
    check("refused: a turn the agent refuses stores nothing",
          refused["owned"] is False
          and agent.gateway_handles.get("telegram:c2") is None, repr(refused))

    rebuilt = HandleStore(tmp / "connector_handles.json")
    check("persisted: a new store on the same file has the handles",
          rebuilt.get("telegram:c1") == room and rebuilt.get("555") == native)


async def test_an_event_without_outbox_fields_leaves_no_address(tmp: Path) -> None:
    """An event with no connector_id, reply_handle or capabilities is
    answered in its response and leaves nothing behind."""
    agent = make_agent(tmp)
    result = await agent.handle_gateway(group_event("m1"))
    check("plain event: answered in the response",
          set(result) == {"handled", "owned", "replies"}
          and result["handled"] is True and result["owned"] is True
          and result["replies"][0]["text"] == "on it", repr(result))
    check("plain event: no handle, no file",
          agent.gateway_handles.keys() == []
          and not (tmp / "connector_handles.json").exists())
    check("plain event: no way to reach it unprompted",
          agent.outbox.route("telegram:c1") is None)

    await agent.handle_gateway(group_event(
        "m2", gid="c9", connector_id="fw1", reply_handle="bad\x00handle",
        capabilities=["outbox"]))
    await agent.outbox.pull("fw1", wait_s=0)
    check("a malformed handle is ignored, so there is no route",
          agent.gateway_handles.get("telegram:c9")["reply_handle"] == ""
          and agent.outbox.route("telegram:c9") is None)


def test_the_handle_store_is_bounded_and_keeps_unsupported(tmp: Path) -> None:
    store = HandleStore(tmp / "h.json", cap=2)

    def put(key, handle="h"):
        store.record(key, reply_handle=handle, connector_id="fw", capabilities=["outbox"],
                     platform="telegram", native=False, conversation_type="group",
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

HANDLE = {"reply_handle": "tg-bot:GroupMessage:c1", "connector_id": "fw1",
          "capabilities": ["outbox"], "platform": "telegram", "native": False,
          "conversation_type": "group", "conversation_id": "c1"}
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
          and d["conversation_type"] == "group" and d["conversation_id"] == "c1"
          and d["reason"] == "proactive" and d["items"] == ITEMS
          and 0 < d["expires_in_s"] <= 300 and d["delivery_id"].startswith("d_"),
          repr(d))
    check("long-poll: tells the connector how long to wait next",
          answer["next_wait_s"] == outbox_mod.DEFAULT_WAIT_S)

    await box.pull("fw2", wait_s=0, acks=[{"delivery_id": d["delivery_id"],
                                           "status": "failed"}])
    check("at most once: another connector cannot settle it",
          not sending.done())
    # The ack rides on the connector's next pull, as the contract says.
    again = await box.pull("fw1", wait_s=0, acks=[
        {"delivery_id": d["delivery_id"], "status": "sent", "sent_items": 2}])
    check("at most once: a later pull does not hand it out again",
          again["deliveries"] == [], repr(again))
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
        # json.loads accepts Infinity, and int() of it overflows.
        ({"status": "partial", "sent_items": float("inf")}, ("failed", 0)),
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
                       connector_id="fw1", capabilities=["outbox"], platform="telegram",
                       native=False, conversation_type="group", conversation_id="c1")
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


async def test_a_delivery_lost_with_its_pull_ends_at_the_next_pull(
        tmp: Path) -> None:
    """A restarted connector leaves its old long-poll behind, and what that
    poll is handed never arrives. The next pull settles it, instead of the
    conversation's send lock waiting out expires_in plus the grace."""
    box = fresh_outbox(tmp)
    await box.pull("fw1", wait_s=0)
    sending = asyncio.create_task(
        box.deliver("telegram:c1", HANDLE, ITEMS, reason="proactive"))
    lost = await box.pull("fw1", wait_s=2)
    await box.pull("fw1", wait_s=0)
    result = await asyncio.wait_for(sending, 2)
    check("lost pull: the next pull without its ack ends it as not sent",
          len(lost["deliveries"]) == 1 and result.status == "no_ack", repr(result))

    async def hung_up() -> bool:
        return True

    sending = asyncio.create_task(
        box.deliver("telegram:c1", HANDLE, ITEMS, reason="proactive"))
    gone = await box.pull("fw1", wait_s=2, disconnected=hung_up)
    kept = await box.pull("fw1", wait_s=2)
    check("hung up: a caller that has gone is handed nothing",
          gone["deliveries"] == [], repr(gone))
    check("hung up: the delivery waits for the next pull",
          len(kept["deliveries"]) == 1, repr(kept))
    await box.pull("fw1", wait_s=0, acks=[
        {"delivery_id": kept["deliveries"][0]["delivery_id"], "status": "sent"}])
    result = await asyncio.wait_for(sending, 2)
    check("hung up: acked on the live pull, it counts as sent",
          result.status == "sent", repr(result))


async def test_a_connector_that_stops_pulling_is_gone(tmp: Path) -> None:
    box = fresh_outbox(tmp)
    box.liveness_s = 0.2
    box.handles.record("telegram:c1", reply_handle="h", connector_id="fw1",
                       capabilities=["outbox"], platform="telegram", native=False,
                       conversation_type="group", conversation_id="c1")
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

    # Handed out, then the connector died mid-send: the caller, which holds
    # the conversation's send lock, is released after the liveness window,
    # not after the full ack grace.
    await box.pull("fw1", wait_s=0)
    started = time.monotonic()
    sending = asyncio.create_task(
        box.deliver("telegram:c1", HANDLE, ITEMS, reason="proactive"))
    handed = await box.pull("fw1", wait_s=1)
    result = await asyncio.wait_for(sending, 2)
    check("liveness: a handed-out delivery ends unacked when its connector dies",
          len(handed["deliveries"]) == 1 and result.status == "no_ack"
          and time.monotonic() - started < 1.5, repr(result))

    box.handles.record("telegram:c2", reply_handle="h", connector_id="fw1",
                       capabilities=["quote_text"], platform="telegram", native=False,
                       conversation_type="group", conversation_id="c2")
    await box.pull("fw1", wait_s=0)
    check("capabilities: no outbox, no route", box.route("telegram:c2") is None)


async def test_order_bounds_and_connectors_are_kept_apart(tmp: Path) -> None:
    box = fresh_outbox(tmp)
    await box.pull("fw1", wait_s=0)
    await box.pull("fw2", wait_s=0)
    other = dict(HANDLE, connector_id="fw2")
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
    good = parse({"kind": "outbox.pull", "connector_id": "fw1"})
    check("pull: defaults fill the optional fields",
          good == {"connector_id": "fw1", "wait_s": 25.0, "max_deliveries": 10,
                   "acks": []}, repr(good))
    for bad in ({"connector_id": "fw1"},
                {"kind": "event", "connector_id": "fw1"},
                {"kind": "outbox.pull"},
                {"kind": "outbox.pull", "connector_id": "fw1", "wait_s": "25"},
                {"kind": "outbox.pull", "connector_id": "fw1", "wait_s": float("nan")},
                {"kind": "outbox.pull", "connector_id": "fw1", "max_deliveries": True},
                {"kind": "outbox.pull", "connector_id": "fw1", "acks": {}},
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
    return {"content-type": "application/json", "x-personagent-token": token,
            "x-personagent-timestamp": stamp, "x-personagent-nonce": nonce,
            "x-personagent-signature": "sha256=" + mac}


def _client() -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=main_module.app, client=("127.0.0.1", 1234))
    return httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:8080")


class _Served:
    """Point main at an agent and a fresh replay guard, and put them back."""

    def __init__(self, agent, token: str = TOKEN) -> None:
        self.agent, self.token = agent, token

    def __enter__(self):
        self.saved = (main_module.agent, main_module.CONNECTOR_TOKEN,
                      main_module._connector_replay)
        main_module.agent = self.agent
        main_module.CONNECTOR_TOKEN = self.token
        main_module._connector_replay = main_module.ReplayGuard()
        return self

    def __exit__(self, *exc):
        (main_module.agent, main_module.CONNECTOR_TOKEN,
         main_module._connector_replay) = self.saved


PULL = {"kind": "outbox.pull", "connector_id": "fw1", "wait_s": 0,
        "max_deliveries": 10, "acks": []}


async def test_the_outbox_endpoint_is_authenticated_like_the_gateway(
        tmp: Path) -> None:
    agent = make_agent(tmp)
    body = _body(PULL)
    event = _body(group_event("m1"))
    with _Served(agent):
        async with _client() as client:
            unsigned = await client.post("/v1/outbox", content=body)
            wrong = await client.post(
                "/v1/outbox", content=body,
                headers=_signed(body, nonce="n0", token="nope"))
            ok = await client.post("/v1/outbox", content=body,
                                   headers=_signed(body, nonce="n1"))
            replayed = await client.post("/v1/outbox", content=body,
                                         headers=_signed(body, nonce="n1"))
            event_here = await client.post(
                "/v1/outbox", content=event,
                headers=_signed(event, nonce="n2"))
            pull_there = await client.post(
                "/v1/events", content=body, headers=_signed(body, nonce="n3"))
            kinded = _body(dict(group_event("m5"), kind="event"))
            event_kinded = await client.post(
                "/v1/events", content=kinded,
                headers=_signed(kinded, nonce="n4"))
            agent.connector_outbox_enabled = False
            disabled = await client.post("/v1/outbox", content=body,
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
    check("disabled: CONNECTOR_OUTBOX_ENABLED=false answers 404 with a code",
          disabled.status_code == 404
          and disabled.json()["code"] == "outbox_disabled", disabled.text)

    with _Served(None):
        async with _client() as client:
            no_agent = await client.post("/v1/outbox", content=body,
                                         headers=_signed(body, nonce="n6"))
    check("disabled: no agent, no outbox", no_agent.status_code == 404)

    agent.connector_outbox_enabled = True
    with _Served(agent, token=""):
        async with _client() as client:
            browser = await client.post(
                "/v1/outbox", content=body,
                headers={"origin": "https://evil.example"})
            local = await client.post("/v1/outbox", content=body)
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
            await client.post("/v1/outbox", content=first,
                              headers=_signed(first, nonce="p0"))
            waiting = _body(dict(PULL, wait_s=5))
            pull = asyncio.create_task(client.post(
                "/v1/outbox", content=waiting,
                headers=_signed(waiting, nonce="p1")))
            await asyncio.sleep(0.1)
            sending = asyncio.create_task(agent.outbox.deliver(
                "telegram:c1", HANDLE, ITEMS, reason="proactive"))
            answer = (await asyncio.wait_for(pull, 3)).json()
            delivery_id = answer["deliveries"][0]["delivery_id"]
            ack = _body(dict(PULL, acks=[{"delivery_id": delivery_id,
                                          "status": "partial", "sent_items": 1}]))
            await client.post("/v1/outbox", content=ack,
                              headers=_signed(ack, nonce="p2"))
            result = await asyncio.wait_for(sending, 2)
    check("http: the long-poll hands the delivery over",
          answer["deliveries"][0]["items"] == ITEMS, repr(answer))
    check("http: the ack on the next pull settles it",
          (result.status, result.sent_items) == ("partial", 1), repr(result))


async def test_long_polls_and_turns_do_not_share_slots(tmp: Path) -> None:
    agent = make_agent(tmp)
    gate, outbox_gate = main_module._connector_admission, main_module._outbox_admission
    body = _body(PULL)
    with _Served(agent):
        taken = 0
        try:
            while await gate.try_acquire():
                taken += 1
            async with _client() as client:
                pull = await client.post("/v1/outbox", content=body,
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
                refused = await client.post("/v1/outbox", content=body,
                                            headers=_signed(body, nonce="s2"))
                turn = await client.post("/v1/events", content=event,
                                         headers=_signed(event, nonce="s3"))
        finally:
            for _ in range(taken):
                await outbox_gate.release()
    check("slots: a full outbox budget is a 429 for pulls only",
          refused.status_code == 429
          and refused.json()["code"] == "capacity_exceeded", refused.text)
    check("slots: ...and turns are still served",
          turn.status_code == 200 and turn.json()["owned"] is True, turn.text)


# ---------------------------------------------------------------------------
# What goes through it: openers, the follow-up question, the excuse
# ---------------------------------------------------------------------------

async def _connected(tmp: Path) -> Agent:
    """An agent whose connector fw1 is polling and whose Telegram room c1
    and DM with telegram:1 have both been admitted with an outbox handle."""
    agent = make_agent(tmp)
    agent.outbox.poll_s = 0.02
    await agent.outbox.pull("fw1", wait_s=0)
    await agent.handle_gateway(group_event("setup-1", **CONNECTOR))
    await agent.handle_gateway(dm_event(
        "setup-2", connector_id="fw1", reply_handle="tg-bot:FriendMessage:1",
        capabilities=["outbox"]))
    return agent


async def _ack_next(agent: Agent, status: str = "sent", **extra) -> dict:
    """Pull like a connector, then ack what came back; returns the delivery."""
    answer = await agent.outbox.pull("fw1", wait_s=3)
    check("a delivery was queued", len(answer["deliveries"]) == 1, repr(answer))
    delivery = answer["deliveries"][0]
    ack = {"delivery_id": delivery["delivery_id"], "status": status,
           "sent_items": len(delivery["items"]), **extra}
    await agent.outbox.pull("fw1", wait_s=0, acks=[ack])
    return delivery


async def test_the_route_table(tmp: Path) -> None:
    agent = await _connected(tmp)
    check("route: a QQ group goes to NapCat", agent._background_route("555") == "onebot")
    check("route: a QQ DM goes to NapCat",
          agent._background_route("private:777") == "onebot")
    check("route: a room with a live outbox connector goes to it",
          agent._background_route("telegram:c1")["reply_handle"]
          == CONNECTOR["reply_handle"])
    check("route: a room nobody left an address for has none",
          agent._background_route("telegram:c2") is None)
    agent.connector_outbox_enabled = False
    check("route: CONNECTOR_OUTBOX_ENABLED=false closes it",
          agent._background_route("telegram:c1") is None)
    agent.connector_outbox_enabled = True
    agent.connector_qq_platforms = {"aiocqhttp"}
    await agent.handle_gateway(group_event(
        "setup-3", platform="aiocqhttp", gid="556", uid="43",
        connector_id="fw1", reply_handle="qq:GroupMessage:556", capabilities=["outbox"]))
    check("route: a QQ group behind a live outbox connector goes to it",
          agent._background_route("556")["reply_handle"] == "qq:GroupMessage:556")
    agent.outbox.liveness_s = -1.0  # not 0: monotonic() can repeat on Windows
    check("route: a connector that stopped pulling closes it",
          agent._background_route("telegram:c1") is None)
    check("route: ...and its QQ group falls back to NapCat",
          agent._background_route("556") == "onebot")


async def test_a_qq_send_from_a_finished_gateway_turn_reaches_napcat(
        tmp: Path) -> None:
    """A task spawned by a gateway turn inherits its sink, closed by the time
    the task runs: every such send was dropped with "sink already closed".
    On the QQ route the sink is lifted, so NapCat is reached."""
    from persona_agent.gateway import GatewaySink, current_sink

    agent = make_agent(tmp)
    posted: list = []

    async def fake_napcat(group_id, message):
        posted.append((group_id, message))
        return True

    agent._napcat_send_group = fake_napcat
    dead = GatewaySink(platform="aiocqhttp", native=True)
    dead.closed = True
    tok = current_sink.set(dead)
    try:
        result = await agent._send_background(
            "555", lambda: agent._send_qq("555", "back in a sec"), reason="excuse")
    finally:
        current_sink.reset(tok)
    check("onebot: sent through NapCat, not the dead sink",
          result.success and posted == [("555", "back in a sec")] and not dead.items,
          repr((result, posted)))


async def test_the_excuse_reaches_a_gateway_conversation(tmp: Path) -> None:
    agent = await _connected(tmp)

    async def bad_think(group_id, mode, text="", caller_override=None):
        raise RuntimeError("model down")

    agent._think = bad_think
    result = await agent.handle_gateway(group_event("m1", **CONNECTOR))
    check("excuse: the turn itself answers with nothing, and owns the room",
          result["owned"] is True and result["replies"] == [], repr(result))
    delivery = await _ack_next(agent)
    item = delivery["items"][0]
    check("excuse: queued for the connector as an excuse, @ing the caller",
          delivery["reason"] == "excuse" and item["type"] == "text"
          and item.get("mention_user_id") == "telegram:42", repr(delivery))
    said: list = []
    for _ in range(100):
        said = [m for m in agent.buffers["telegram:c1"] if m["name"] == "TestBot"]
        if any(m["text"] == item["text"] for m in said):
            break
        await asyncio.sleep(0.02)
    check("excuse: committed once the connector acked it",
          any(m["text"] == item["text"] for m in said), repr(said))

    # A connector that never said "outbox": nothing is queued, nothing said.
    await agent.handle_gateway(group_event(
        "m2", gid="c5", connector_id="fw1", reply_handle="h5", capabilities=[]))
    await asyncio.sleep(0.1)
    check("excuse: no outbox, no excuse",
          (await agent.outbox.pull("fw1", wait_s=0))["deliveries"] == []
          and not [m for m in agent.buffers["telegram:c5"] if m["name"] == "TestBot"])


async def test_the_excuse_on_qq_still_goes_to_napcat(tmp: Path) -> None:
    agent = make_agent(tmp)
    agent.connector_qq_platforms = {"aiocqhttp"}
    posted: list = []

    async def fake_napcat(group_id, message):
        posted.append(group_id)
        return True

    async def bad_think(group_id, mode, text="", caller_override=None):
        raise RuntimeError("model down")

    agent._napcat_send_group = fake_napcat
    agent._think = bad_think
    await agent.handle({
        "post_type": "message", "message_type": "group", "group_id": "556",
        "user_id": "42", "message_id": 92002, "sender": {"nickname": "Alice"},
        "message": [{"type": "at", "data": {"qq": QQ_BOT_ID}},
                    {"type": "text", "data": {"text": "you free tonight?"}}],
        "raw_message": "you free tonight?"})
    await agent.handle_gateway(group_event(
        "m3", platform="aiocqhttp", gid="557", uid="43", self_id=QQ_BOT_ID))
    for _ in range(50):
        if len(posted) == 2:
            break
        await asyncio.sleep(0.02)
    check("excuse: direct QQ and QQ through a connector both reach NapCat",
          sorted(posted) == ["556", "557"], repr(posted))


async def test_a_proactive_opener_reaches_a_gateway_room(tmp: Path) -> None:
    agent = await _connected(tmp)
    agent.proactive_prob = 1.0
    thought: list = []

    async def opener(group_id, mode, text="", caller_override=None):
        thought.append(group_id)
        return "anyone around tonight", "chat", ""

    agent._think = opener
    room = "telegram:c1"
    quiet = time.time() - agent.proactive_min_silence_s - 10

    def make_quiet() -> None:
        agent.last_activity_at[room] = quiet
        agent.last_reply_at[room] = 0.0
        agent.last_proactive_at.pop(room, None)

    make_quiet()
    task = asyncio.create_task(agent._maybe_proactive_groups())
    delivery = await _ack_next(agent)
    acted = await asyncio.wait_for(task, 3)
    check("opener: queued as proactive for the room",
          delivery["reason"] == "proactive" and delivery["conversation_key"] == room
          and delivery["items"][0]["text"] == "anyone around tonight",
          repr(delivery))
    check("opener: committed after the ack",
          acted is True
          and agent.buffers[room][-1]["text"].endswith("anyone around tonight"),
          repr(list(agent.buffers[room])[-1:]))

    make_quiet()
    thought.clear()
    agent.proactive_platforms = {"qq"}
    check("PROACTIVE_PLATFORMS=qq: a Telegram room is not considered",
          await agent._maybe_proactive_groups() is False and thought == [])

    agent.proactive_platforms = set()
    agent.outbox.liveness_s = -1.0
    check("no live connector: no model call is spent",
          await agent._maybe_proactive_groups() is False and thought == [])

    agent.outbox.liveness_s = 90.0
    await agent.outbox.pull("fw1", wait_s=0)
    before = list(agent.buffers[room])
    task = asyncio.create_task(agent._maybe_proactive_groups())
    await _ack_next(agent, status="failed")
    acted = await asyncio.wait_for(task, 3)
    check("failed ack: nothing committed, the attempt still stamped",
          acted is False and list(agent.buffers[room]) == before
          and agent.last_proactive_at.get(room, 0) > 0)


async def test_a_proactive_dm_reaches_a_gateway_user(tmp: Path) -> None:
    agent = await _connected(tmp)
    agent.proactive_dm_prob = 1.0
    uid = "telegram:1"
    agent.last_dm_activity_at[uid] = time.time() - agent.proactive_dm_min_silence_s - 10
    history_before = list(agent.private_history.get(uid, []))

    async def opener(history, is_owner=False, pkey="", proactive=False,
                     proactive_cue=""):
        return "how did the exam go", ""

    agent._chat_private = opener
    task = asyncio.create_task(agent._maybe_proactive_dms())
    answer = await agent.outbox.pull("fw1", wait_s=3)
    delivery = answer["deliveries"][0]
    check("DM opener: queued for the DM",
          delivery["conversation_key"] == "private:telegram:1"
          and delivery["conversation_type"] == "dm"
          and delivery["conversation_id"] == "1"
          and delivery["reply_handle"] == "tg-bot:FriendMessage:1", repr(delivery))
    check("DM opener: not in the history before the ack",
          agent.private_history.get(uid, []) == history_before)
    await agent.outbox.pull("fw1", wait_s=0, acks=[
        {"delivery_id": delivery["delivery_id"], "status": "sent", "sent_items": 1}])
    check("DM opener: in the history after it", await asyncio.wait_for(task, 3)
          and agent.private_history[uid][-1]
          == {"role": "assistant", "content": "how did the exam go"})

    agent.last_proactive_at.clear()
    agent.access_dm_users = {"telegram:99"}
    called: list = []

    async def spy(history, **kw):
        called.append(kw)
        return "x", ""

    agent._chat_private = spy
    check("DM opener: someone the lists now refuse is not DMed",
          await agent._maybe_proactive_dms() is False and called == [])


async def test_a_connectors_own_proactive_cue_shares_the_cooldown(
        tmp: Path) -> None:
    """The inverted "proactive": true event is the connector's scheduler
    speaking first. It stamps the DM cooldown the agent's loop reads, and is
    not activity by the reader."""
    agent = make_agent(tmp)
    result = await agent.handle_gateway(dm_event(
        "p1", proactive=True, text="they had an exam today",
        segments=[{"type": "text", "text": "they had an exam today"}]))
    check("cue: still answered in the response",
          result["owned"] is True and result["replies"], repr(result))
    check("cue: counts against the DM cooldown",
          agent.last_proactive_at.get("dm:telegram:1", 0) > 0)
    check("cue: is not the reader's activity",
          agent.last_dm_activity_at.get("telegram:1", 0) == 0)


async def test_the_follow_up_question_reaches_a_gateway_conversation(
        tmp: Path) -> None:
    agent = await _connected(tmp)
    agent.react_elicit_delay_s = 0.0
    entry = {"reply": "just restart it", "ctx_lines": ["alex: server down"],
             "mode": "called", "intent": "chat"}

    task = asyncio.create_task(agent._maybe_elicit(
        "telegram:c1", entry, "wait, what did you mean?", "telegram:42", False))
    delivery = await _ack_next(agent)
    await asyncio.wait_for(task, 3)
    check("follow-up: queued as follow_up, @ing who rejected",
          delivery["reason"] == "follow_up"
          and delivery["items"][0].get("mention_user_id") == "telegram:42", repr(delivery))
    check("follow-up: said, and armed for their answer",
          agent.buffers["telegram:c1"][-1]["text"].endswith("what did you mean?")
          and agent.pending_reactions.match(
              "telegram:c1", sender_uid="telegram:42", at_bot=False,
              now=time.time()) is not None)

    task = asyncio.create_task(agent._maybe_elicit(
        "dm:telegram:1", entry, "which part was wrong?", "telegram:1", True))
    delivery = await _ack_next(agent)
    await asyncio.wait_for(task, 3)
    check("follow-up: a DM gets it too, and keeps it in the history",
          delivery["conversation_key"] == "private:telegram:1"
          and agent.private_history["telegram:1"][-1]["content"]
          == "which part was wrong?", repr(delivery))

    agent.outbox.liveness_s = -1.0
    await agent._maybe_elicit("telegram:c2", entry, "hm?", "telegram:42", False)
    check("follow-up: unreachable, so nothing is sent and the cooldown is unspent",
          agent._last_elicit_at.get("telegram:c2", 0) == 0
          and "telegram:c2" not in agent.buffers)


def test_an_outbox_result_carries_no_message_ids() -> None:
    """Acks carry no platform message ids; nothing may start relying on them."""
    from persona_agent.transport import SendResult, _acked_result

    items = [{"type": "text", "text": "a"}, {"type": "image", "b64": "x"},
             {"type": "text", "text": "b"}]
    collected = SendResult(success=True, sticker_files=["s.png"])
    full = _acked_result(items, outbox_mod.OutboxResult("sent", 3), collected)
    part = _acked_result(items, outbox_mod.OutboxResult("partial", 2), collected)
    none = _acked_result(items, outbox_mod.OutboxResult("no_ack", 0), collected)
    check("acked: all sent", full.success and full.delivered == "a\nb"
          and full.sticker_files == ["s.png"] and full.message_ids == [])
    check("acked: a partial commits only the acked prefix",
          not part.success and part.partial and part.delivered == "a"
          and part.sticker_files == [] and part.message_ids == [])
    check("acked: no ack is nothing", not none.success and not none.partial
          and none.delivered == "")


async def test_the_sdk_and_the_agent_speak_the_same_outbox(tmp: Path) -> None:
    """End to end: the connector SDK signs an event with the new fields and
    runs its pull loop against the real app; an opener the agent queues is
    delivered once and committed on the SDK's ack."""
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent
                           / "integrations" / "sdk"))
    import personagent_connector as sdk

    agent = make_agent(tmp)
    agent.outbox.poll_s = 0.02
    agent.proactive_prob = 1.0
    delivered: list = []

    async def deliver(delivery: dict) -> tuple[str, int]:
        delivered.append(delivery)
        return "sent", len(delivery["items"])

    async def opener(group_id, mode, text="", caller_override=None):
        return ("anyone around tonight", "chat", "") if mode == "proactive" \
            else ("on it", "called", "")

    agent._think = opener
    with _Served(agent):
        client = httpx.AsyncClient(transport=httpx.ASGITransport(
            app=main_module.app, client=("127.0.0.1", 1234)))
        conn = sdk.Connector("http://127.0.0.1:8080", TOKEN,
                             connector_id="fw1", client=client)
        answer = await conn.send_event(group_event(
            "e1", reply_handle="tg-bot:GroupMessage:c1", capabilities=["outbox"]))
        check("sdk: the event is answered", answer["owned"] is True, repr(answer))
        stop = asyncio.Event()
        loop = asyncio.create_task(conn.run_outbox(deliver, wait_s=1, stop=stop))
        for _ in range(100):
            if agent.outbox.route("telegram:c1"):
                break
            await asyncio.sleep(0.02)
        agent.last_activity_at["telegram:c1"] = (
            time.time() - agent.proactive_min_silence_s - 10)
        agent.last_reply_at["telegram:c1"] = 0.0
        acted = await asyncio.wait_for(agent._maybe_proactive_groups(), 5)
        stop.set()
        await asyncio.wait_for(loop, 5)
        await client.aclose()
    check("sdk: delivered once, with the handle it sent",
          len(delivered) == 1
          and delivered[0]["reply_handle"] == "tg-bot:GroupMessage:c1", repr(delivered))
    check("sdk: its ack commits the opener",
          acted is True
          and agent.buffers["telegram:c1"][-1]["text"].endswith("anyone around tonight"))
