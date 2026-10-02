"""The operator dashboard: who may open it, what it shows, what it may change.

Run from the repo root:

    python -m pytest tests/test_dashboard.py
"""
from __future__ import annotations

import time
import warnings
from datetime import datetime
from pathlib import Path

import pytest
from fastapi import FastAPI

from persona_agent import (candidates, dashboard, decision_log, evidence,
                           promotion, reactions)
from persona_agent import server
from persona_agent.agent import Agent
from persona_agent.paths import runtime_dir
from persona_agent.textproc import TextProcessing

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from fastapi.testclient import TestClient

LOCAL = "http://127.0.0.1:8080"
API = ("/api/dashboard/status", "/api/dashboard/conversations",
       "/api/dashboard/conversation?id=telegram:c1")
PAGES = ("/", "/dashboard/app.js", "/dashboard/app.css")
WRITE = {"content-type": "application/json", "x-personagent-dashboard": "1"}
SECRET_KEY = "sk-live-SECRET-0123456789abcdef"
SECRET_TOKEN = "connector-SECRET-token-987654"


def check(name: str, cond: bool, detail: str = "") -> None:
    assert cond, name + (f" - {detail}" if detail else "")


def _runtime_listing() -> list[str]:
    real = runtime_dir()
    return sorted(p.name for p in real.glob("*")) if real.exists() else []


@pytest.fixture(scope="module", autouse=True)
def real_runtime_directory_is_untouched():
    before = _runtime_listing()
    yield
    check("the real runtime directory was not written",
          _runtime_listing() == before)


def make_agent(tmp: Path) -> Agent:
    """A real Agent whose every learned-state path is inside `tmp`."""
    tmp.mkdir(parents=True, exist_ok=True)
    a = Agent(
        api_key=SECRET_KEY, qq_bot_id="1", persona_name="Nova", lang="en",
        qq_onebot_url="http://127.0.0.1:9",
        memory_file=str(tmp / "memory.json"), persona="test persona",
        eval_enabled=False, eval_file=str(tmp / "eval.jsonl"),
        stickers_dir=str(tmp / "stickers"), stickers_file=str(tmp / "stickers.json"),
        message_debounce_sec=0,
    )
    a._seen_msg_file = tmp / "seen_msg_ids.json"
    a._seen_msg_ids.clear()
    a.core_memory_file = tmp / "core_memory.json"
    a.core_memory = {}
    a.candidates_file = tmp / "candidates.jsonl"
    a.examples_seed_file = tmp / "seed_examples.jsonl"
    a.examples_file = tmp / "examples.jsonl"
    a.feedback_seed_file = tmp / "seed_feedback.jsonl"
    a.feedback_file = tmp / "feedback.jsonl"
    a.teacher_stats = reactions.TeacherStats(tmp / "teacher_stats.json")
    a.connector_handles.path = tmp / "connector_handles.json"
    a.react_elicit_enabled = False
    a._typing_delay = lambda chunk: 0.0
    return a


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def seed_event(agent: Agent, *, conv: str = "telegram:c1",
               reply: str = "have you checked the logs?",
               reaction_type: str = "rejection", better: str = "",
               speaker: str = "u1", text: str = "I was just venting") -> dict:
    ev = evidence.make_event(
        kind=evidence.KIND_REACTION, ts=now_iso(), lang="en",
        platform="telegram", conv_id=conv, persona=agent.persona_name,
        persona_hash=agent.persona_hash, persona_version=agent.persona_version,
        speaker_id=speaker, speaker_name="Alex", recipient_id="u1", reply=reply,
        reaction_text=text, reaction_type=reaction_type, directed=True,
        adjudication={"accept": True, "better": better, "mode": "called",
                      "reason": "wanted sympathy, not advice"})
    agent.evidence_log.append(ev)
    return ev


def seed_candidate(agent: Agent, ev: dict, *, ctype: str = candidates.TYPE_PAIR,
                   better: str = "ugh, that sounds rough") -> str:
    payload = {"reply": ev["reply"], "rating": "better", "src": "user_reaction",
               "context": ["Alex: the deploy failed again"]}
    if ctype == candidates.TYPE_PAIR:
        payload["better"] = better
    cand = candidates.make_candidate(
        ctype=ctype, scope=candidates.scope_from_event(ev), payload=payload,
        evidence=[ev["event_id"]], created_at=now_iso())
    agent.candidate_ledger.propose(cand)
    return cand["candidate_id"]


@pytest.fixture
def live(tmp: Path):
    """The server module wired to a real agent, restored afterwards."""
    saved = (server.agent, server.CONNECTOR_TOKEN)
    agent = make_agent(tmp)
    server.agent = agent
    server.CONNECTOR_TOKEN = ""
    decision_log.LOG.clear()
    try:
        yield agent
    finally:
        server.agent, server.CONNECTOR_TOKEN = saved
        decision_log.LOG.clear()


def client(peer: str = "127.0.0.1", base: str = LOCAL, **headers) -> TestClient:
    return TestClient(server.app, base_url=base, client=(peer, 50000),
                      headers=headers or None)


# ---------------------------------------------------------------- access ----

def test_a_local_browser_gets_the_page_and_the_data(live) -> None:
    c = client()
    page = c.get("/")
    check("page: served", page.status_code == 200, page.text[:200])
    check("page: html", page.headers["content-type"].startswith("text/html"))
    csp = page.headers.get("content-security-policy", "")
    check("page: strict CSP", "default-src 'self'" in csp and "script-src 'self'" in csp
          and "frame-ancestors 'none'" in csp and "unsafe" not in csp, csp)
    for name, value in (("x-content-type-options", "nosniff"),
                        ("referrer-policy", "no-referrer")):
        check(f"page: {name}", page.headers.get(name) == value, repr(page.headers.get(name)))
    for path in PAGES[1:] + API:
        r = c.get(path)
        check(f"local: {path} answered", r.status_code == 200, r.text[:200])
        check(f"local: {path} hardened",
              r.headers.get("x-content-type-options") == "nosniff"
              and "frame-ancestors 'none'" in r.headers.get("content-security-policy", ""))
    check("assets: only the shipped files",
          c.get("/dashboard/..%2Fdashboard.py").status_code == 404
          and c.get("/dashboard/index.html").status_code == 404)
    check("assets: javascript type",
          c.get("/dashboard/app.js").headers["content-type"].startswith("text/javascript"))


def test_a_non_local_client_is_refused_without_the_token(live) -> None:
    cases = {
        "remote peer": client(peer="203.0.113.9"),
        "rebound host name": client(base="http://evil.example:8080"),
        "a tunnel": client(**{"x-forwarded-for": "203.0.113.9"}),
    }
    for name, c in cases.items():
        for path in PAGES + API:
            r = c.get(path)
            check(f"{name}: {path} refused",
                  r.status_code == 403 and r.json().get("code") == "non_local_request",
                  repr((r.status_code, r.text[:120])))
    r = client(**{"sec-fetch-site": "cross-site"}).get("/api/dashboard/status")
    check("a cross-site fetch of the data is refused", r.status_code == 403, r.text)


def test_the_token_admits_a_remote_operator(live) -> None:
    server.CONNECTOR_TOKEN = SECRET_TOKEN
    remote = client(peer="203.0.113.9", base="https://bot.example.com")
    ok = remote.get("/api/dashboard/status",
                    headers={"x-personagent-token": SECRET_TOKEN})
    check("token: a remote operator with it is answered", ok.status_code == 200, ok.text)
    bad = remote.get("/api/dashboard/status",
                     headers={"x-personagent-token": "nope"})
    check("token: a wrong one is refused", bad.status_code == 403, bad.text)
    local = client().get("/api/dashboard/status",
                         headers={"x-personagent-token": "nope"})
    check("token: a wrong one is refused locally too", local.status_code == 403)
    check("token: a local browser needs none", client().get("/").status_code == 200)
    server.CONNECTOR_TOKEN = ""
    ignored = remote.get("/api/dashboard/status",
                         headers={"x-personagent-token": SECRET_TOKEN})
    check("token: with none configured a remote client stays refused",
          ignored.status_code == 403, ignored.text)


def test_state_changes_need_the_header_and_the_same_origin(live) -> None:
    cid = seed_candidate(live, seed_event(live))
    url = f"/api/dashboard/candidates/{cid}/promote"
    c = client()
    refused = {
        "no custom header": c.post(url, json={}),
        "foreign origin": c.post(url, json={}, headers={**WRITE, "origin": "https://evil.example"}),
        "opaque origin": c.post(url, json={}, headers={**WRITE, "origin": "null"}),
        "another local port": c.post(url, json={}, headers={**WRITE, "origin": "http://127.0.0.1:3000"}),
        "a form post": c.post(url, content=b"reason=x", headers={
            "x-personagent-dashboard": "1",
            "content-type": "application/x-www-form-urlencoded"}),
        "a remote peer": client(peer="203.0.113.9").post(url, json={}, headers=WRITE),
    }
    for name, r in refused.items():
        check(f"write: {name} refused", r.status_code in (403, 415), repr((r.status_code, r.text)))
    check("write: GET cannot change anything", c.get(url).status_code == 405)
    check("write: nothing reached the ledger",
          live.candidate_ledger.get(cid)["state"] == candidates.STATE_PROPOSED)
    same = c.post(url, json={}, headers={**WRITE, "origin": LOCAL})
    check("write: the page's own origin is accepted", same.status_code == 200, same.text)


# --------------------------------------------------------------- actions ----

def test_promote_and_roll_back_round_trip_through_the_ledger_and_views(live) -> None:
    ev = seed_event(live)
    cid = seed_candidate(live, ev)
    c = client()

    r = c.post(f"/api/dashboard/candidates/{cid}/promote", json={}, headers=WRITE)
    check("promote: accepted", r.status_code == 200, r.text)
    check("promote: reported", r.json() == {"ok": True, "id": cid, "before": "proposed",
                                            "after": "promoted", "views_rebuilt": True}, r.text)
    cand = live.candidate_ledger.get(cid)
    check("promote: the ledger says promoted", cand["state"] == candidates.STATE_PROMOTED)
    check("promote: recorded as the dashboard",
          cand["history"][-1]["actor"] == "dashboard", repr(cand["history"]))
    replay = candidates.CandidateLedger(live.candidate_ledger_file).get(cid)
    check("promote: a cold replay agrees", replay["state"] == candidates.STATE_PROMOTED)
    live._reload_views_if_stale()
    check("promote: the running agent's view carries it",
          [row.get("candidate_id") for row in live._view_pairs_cache] == [cid])

    r = c.post(f"/api/dashboard/candidates/{cid}/rollback",
               json={"reason": "too pushy"}, headers=WRITE)
    check("rollback: accepted", r.status_code == 200 and r.json()["after"] == "rolled_back", r.text)
    cand = live.candidate_ledger.get(cid)
    check("rollback: reason kept", cand["history"][-1]["reason"] == "too pushy")
    live._reload_views_if_stale()
    check("rollback: gone from the view", live._view_pairs_cache == [])
    check("rollback: history is append-only",
          [h["state"] for h in cand["history"]] == ["promoted", "rolled_back"])

    again = c.post(f"/api/dashboard/candidates/{cid}/rollback", json={}, headers=WRITE)
    check("rollback: an illegal transition is a 409",
          again.status_code == 409 and again.json()["code"] == "illegal_transition", again.text)
    missing = c.post("/api/dashboard/candidates/feedfacefeedface/promote", json={}, headers=WRITE)
    check("unknown candidate: 404", missing.status_code == 404, missing.text)
    unknown = c.post(f"/api/dashboard/candidates/{cid}/delete", json={}, headers=WRITE)
    check("unknown action: 404", unknown.status_code == 404, unknown.text)

    detail = c.get("/api/dashboard/conversation", params={"id": "telegram:c1"}).json()
    past = detail["past"]
    check("detail: a rolled-back candidate is listed with its way back",
          len(past) == 1 and past[0]["actions"] == ["promote", "reject"], repr(past))
    check("detail: its evidence chain is shown",
          past[0]["evidence"][0]["speaker"] == "Alex"
          and past[0]["evidence"][0]["reaction_type"] == "rejection", repr(past[0]["evidence"]))


def test_a_pending_proposal_explains_what_it_waits_for(live) -> None:
    ev = seed_event(live)
    pair = seed_candidate(live, ev)
    positive = seed_event(live, reply="ugh, that sounds rough",
                          reaction_type="positive", text="haha thanks")
    example = seed_candidate(live, positive, ctype=candidates.TYPE_EXAMPLE)
    detail = client().get("/api/dashboard/conversation",
                          params={"id": "telegram:c1"}).json()
    by_id = {c["id"]: c for c in detail["pending"]}
    check("pending: both proposals listed", set(by_id) == {pair, example}, repr(list(by_id)))

    cl = by_id[pair]["checklist"]
    rules = {r["id"]: r for r in cl["rules"]}
    check("checklist: one weak event is not enough",
          not rules["strong"]["ok"] and rules["strong"]["have"] == 0
          and not rules["events"]["ok"] and rules["events"]["have"] == 1, repr(rules))
    check("checklist: nothing disagrees", rules["no_disagreement"]["ok"]
          and rules["no_conflict"]["ok"], repr(rules))
    check("checklist: waits for a strong signal and a second event",
          cl["waiting_for"] == ["strong", "events"], repr(cl["waiting_for"]))
    ledger = live.candidate_ledger
    expected = promotion.decide(
        ledger.get(pair), linked_events=live.evidence_log.many([ev["event_id"]]),
        related_events=promotion.related_events(ledger.get(pair), live.evidence_log.all()),
        peers=ledger.all(), now=time.time(), policy=live.promotion_policy)
    check("checklist: the verdict is the policy's own",
          cl["verdict"] == expected.reason and cl["promote"] is False, cl["verdict"])
    check("checklist: actions offered", by_id[pair]["actions"] == ["promote", "reject"])

    ex = by_id[example]["checklist"]
    check("checklist: an example waits for a person",
          ex["waiting_for"] == ["admin"]
          and any(r["id"] == "strong_impossible" for r in ex["rules"]), repr(ex))


# ------------------------------------------------------- data and secrets ----

def test_no_secret_reaches_any_response(live, monkeypatch) -> None:
    server.CONNECTOR_TOKEN = SECRET_TOKEN
    monkeypatch.setenv("LLM_API_KEY", SECRET_KEY)
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-SECRET-55555555")
    live.memories["telegram:c1"] = [{"text": f"the key is {SECRET_KEY}", "time": time.time()}]
    seed_candidate(live, seed_event(live, text=f"use {SECRET_TOKEN} please"))
    live.connector_handles.record(
        "telegram:c1", reply_handle="h1", connector_id="astrbot-home",
        capabilities=("outbox",), platform="telegram", native=False,
        conversation_type="group", conversation_id="c1")
    c = client()
    bodies = [c.get(path).text for path in API + PAGES]
    blob = "\n".join(bodies)
    for secret in (SECRET_KEY, SECRET_TOKEN, "tvly-SECRET-55555555"):
        check(f"secrets: {secret[:10]}... never sent", secret not in blob)
    detail = c.get("/api/dashboard/conversation", params={"id": "telegram:c1"}).json()
    check("secrets: masked where they were quoted",
          detail["memories"][0]["text"] == "the key is ***", repr(detail["memories"]))
    status = c.get("/api/dashboard/status").json()
    check("status: model names are shown",
          {m["role"] for m in status["models"]} >= {"reply", "gate"}, repr(status["models"]))
    check("status: the connector is listed",
          [k["id"] for k in status["connectors"]] == ["astrbot-home"], repr(status["connectors"]))


def test_a_fresh_install_has_empty_lists_not_errors(live, tmp) -> None:
    c = client()
    status = c.get("/api/dashboard/status").json()
    check("fresh: running", status["agent"] == "ready", repr(status["agent"]))
    check("fresh: nothing received yet", status["activity"]["received"] is False
          and status["activity"]["spoke"] is False, repr(status["activity"]))
    check("fresh: no connectors", status["connectors"] == [])
    check("fresh: persona lineage counts the running document",
          status["persona"]["name"] == "Nova" and status["persona"]["revisions"] == 1,
          repr(status["persona"]))
    check("fresh: no conversations",
          c.get("/api/dashboard/conversations").json() == {"conversations": []})
    detail = c.get("/api/dashboard/conversation", params={"id": "g1"}).json()
    check("fresh: an unknown conversation is empty, not missing",
          all(detail[k] == [] for k in ("decisions", "memories", "pending", "learned", "past")),
          repr(detail))
    check("fresh: a missing id is a 400",
          c.get("/api/dashboard/conversation").status_code == 400)
    server.agent = None
    off = c.get("/api/dashboard/status").json()
    check("agent off: still answered", off["agent"] == "off" and off["models"] == [], repr(off))
    check("agent off: conversations still listed",
          c.get("/api/dashboard/conversations").status_code == 200)


def test_the_page_never_parses_server_text_as_html() -> None:
    static = Path(dashboard.STATIC_DIR)
    js = (static / "app.js").read_text(encoding="utf-8")
    for sink in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval(",
                 "new Function"):
        check(f"page script: no {sink}", sink not in js)
    html = (static / "index.html").read_text(encoding="utf-8")
    check("page: no inline script", "<script>" not in html and "<script " in html
          and 'src="dashboard/app.js"' in html)
    check("page: no inline style", "style=" not in html and "<style" not in html)
    check("page: nothing loaded from elsewhere", "http" not in html.replace(
        'http-equiv', ''))


def test_dashboard_enabled_false_removes_the_routes(monkeypatch) -> None:
    monkeypatch.setenv("DASHBOARD_ENABLED", "false")
    app = FastAPI()
    check("disabled: install says so", dashboard.install(app) is False)
    paths = {getattr(r, "path", "") for r in app.routes}
    check("disabled: no dashboard route", not any(
        p == "/" or p.startswith(("/api/dashboard", "/dashboard")) for p in paths), repr(paths))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        check("disabled: the page is a 404",
              TestClient(app, base_url=LOCAL, client=("127.0.0.1", 1)).get("/").status_code == 404)
    monkeypatch.setenv("DASHBOARD_ENABLED", "true")
    enabled = FastAPI()
    check("enabled: install says so", dashboard.install(enabled) is True)
    check("enabled: routes present", "/api/dashboard/status" in {
        getattr(r, "path", "") for r in enabled.routes})
    check("the service includes it by default", "/api/dashboard/status" in {
        getattr(r, "path", "") for r in server.app.routes})


# ---------------------------------------------------------- decision log ----

def test_the_decision_log_is_bounded_and_coalesces_silence() -> None:
    log = decision_log.DecisionLog(per_conversation=3, conversations=2)
    for i in range(5):
        log.record("g1", "", False, "below the trigger count", f"msg {i}", now=i)
    rows = log.recent("g1")
    check("coalesced: one row for a run of identical silences",
          len(rows) == 1 and rows[0]["count"] == 5 and rows[0]["excerpt"] == "msg 4", repr(rows))
    for i in range(4):
        log.record("g1", "called", True, "addressed", f"reply {i}", now=10 + i)
    rows = log.recent("g1")
    check("bounded per conversation, newest first",
          [r["excerpt"] for r in rows] == ["reply 3", "reply 2", "reply 1"], repr(rows))
    log.record("g2", "judge", False, "passed", now=20)
    log.record("g3", "judge", False, "passed", now=21)
    check("bounded in conversations, oldest dropped",
          set(log.last_seen()) == {"g2", "g3"}, repr(log.last_seen()))
    log.record("g3", "called", True, "addressed", "x" * 500 + "\x02secret\x03", now=22)
    excerpt = log.recent("g3")[0]["excerpt"]
    check("excerpt: short and printable",
          len(excerpt) <= decision_log.EXCERPT_CHARS and "\x02" not in excerpt, repr(excerpt))
    decision_log.record(None, "called", True, "addressed")  # must not raise


async def test_a_group_turn_records_why_it_spoke_or_stayed_quiet(tmp, monkeypatch) -> None:
    # Night hours may skip a follow-up at random; this test is about recording.
    monkeypatch.setattr(TextProcessing, "_is_sleep_hour", staticmethod(lambda: False))
    agent = make_agent(tmp)
    decision_log.LOG.clear()
    replies = iter(["sure, on it", "PASS"])

    async def fake_think(group_id, mode, text="", caller_override=None):
        return next(replies), "chat", ""

    agent._think = fake_think

    def turn(mid: str, text: str) -> dict:
        return {"platform": "telegram", "conversation_type": "group",
                "conversation_id": "c1", "sender_id": "42", "sender_name": "Sam",
                "message_id": mid, "segments": [{"type": "text", "text": text}],
                "sent_at": int(time.time())}

    try:
        await agent.handle_event(turn("m1", "anyone around this evening"))
        await agent.handle_event(turn("m2", "Nova can you take a look"))
        agent.chat_followup_window_s = 3600
        await agent.handle_event(turn("m3", "thanks for that, really"))
        rows = decision_log.LOG.recent("telegram:c1")
    finally:
        decision_log.LOG.clear()
    check("three decisions recorded", len(rows) == 3, repr(rows))
    quiet_followup, spoke, below = rows
    check("below the trigger count: quiet with the reason",
          below["spoke"] is False and below["reason"] == "below the trigger count"
          and below["excerpt"] == "anyone around this evening", repr(below))
    check("called: spoke, with what it said",
          spoke["spoke"] is True and spoke["mode"] == "called"
          and spoke["reason"] == "addressed" and spoke["excerpt"] == "sure, on it", repr(spoke))
    check("a pass is recorded as a choice to stay quiet",
          quiet_followup["spoke"] is False and quiet_followup["reason"] == "passed"
          and quiet_followup["mode"] == "followup", repr(quiet_followup))
