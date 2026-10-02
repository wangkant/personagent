"""The operator dashboard: who may open it, what it shows, what it may change.

Run from the repo root:

    python -m pytest tests/test_dashboard.py
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import warnings
from datetime import datetime
from pathlib import Path

import pytest
from fastapi import FastAPI

from persona_agent import (candidates, dashboard, decision_log, evidence,
                           preflight, promotion, reactions)
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
DASH_TOKEN = "dashTOKEN-0123456789abcdefghijklmnopqrstuv"


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
    saved = (server.agent, server.CONNECTOR_TOKEN, dashboard._token)
    agent = make_agent(tmp)
    server.agent = agent
    server.CONNECTOR_TOKEN = ""
    dashboard._token = DASH_TOKEN
    decision_log.LOG.clear()
    try:
        yield agent
    finally:
        server.agent, server.CONNECTOR_TOKEN, dashboard._token = saved
        decision_log.LOG.clear()


def client(peer: str = "127.0.0.1", base: str = LOCAL, signed_in: bool = True,
           **headers) -> TestClient:
    """A browser that has opened the dashboard's link, unless `signed_in` is off."""
    cookies = {dashboard.cookie_name(DASH_TOKEN): DASH_TOKEN} if signed_in else None
    return TestClient(server.app, base_url=base, client=(peer, 50000),
                      headers=headers or None, cookies=cookies)


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


def test_every_request_needs_the_token_however_local_it_looks(live) -> None:
    cid = seed_candidate(live, seed_event(live))
    write = f"/api/dashboard/candidates/{cid}/reject"
    # What a same-host proxy (nginx's default proxy_pass, an ssh -R or frp
    # tunnel) forwards: a loopback peer, a local Host, no forwarding header.
    looks_local = client(signed_in=False)
    for path in PAGES + API:
        r = looks_local.get(path)
        check(f"no token: {path} refused", r.status_code == 401, repr((r.status_code, r.text[:120])))
    r = looks_local.post(write, json={}, headers=WRITE)
    check("no token: a write is refused", r.status_code == 401, r.text)
    check("no token: nothing reached the ledger",
          live.candidate_ledger.get(cid)["state"] == candidates.STATE_PROPOSED)
    page = looks_local.get("/")
    check("no token: the page says where the link is",
          page.headers["content-type"].startswith("text/plain")
          and "doctor" in page.text and "面板" in page.text, page.text)

    server.CONNECTOR_TOKEN = SECRET_TOKEN
    r = looks_local.get("/api/dashboard/status", headers={"x-personagent-token": SECRET_TOKEN})
    check("CONNECTOR_TOKEN opens nothing here", r.status_code == 401, r.text)

    remote = client(peer="203.0.113.9", base="https://bot.example.com", signed_in=False)
    ok = remote.get("/api/dashboard/status", headers={dashboard.TOKEN_HEADER: DASH_TOKEN})
    check("the dashboard token in its header admits any client", ok.status_code == 200, ok.text)
    bad = remote.get("/api/dashboard/status", headers={dashboard.TOKEN_HEADER: "nope"})
    check("a wrong one is refused", bad.status_code == 403, bad.text)
    wrong_cookie = TestClient(server.app, base_url=LOCAL, client=("127.0.0.1", 1),
                              cookies={dashboard.cookie_name(DASH_TOKEN): "nope"})
    check("a forged cookie is refused", wrong_cookie.get("/api/dashboard/status").status_code == 401)
    r = client(**{"sec-fetch-site": "cross-site"}).get("/api/dashboard/status")
    check("a cross-site fetch of the data is refused", r.status_code == 403, r.text)


def test_the_link_signs_the_browser_in_and_drops_the_token_from_the_address(live) -> None:
    browser = client(signed_in=False)
    browser.follow_redirects = False
    r = browser.get("/", params={"token": DASH_TOKEN, "lang": "zh"})
    check("link: redirected", r.status_code == 303 and r.headers["location"] == "./?lang=zh",
          repr((r.status_code, r.headers.get("location"))))
    cookie = r.headers.get("set-cookie", "")
    check("link: the cookie is HttpOnly, SameSite=Strict, site-wide",
          cookie.startswith(dashboard.cookie_name(DASH_TOKEN) + "=")
          and "httponly" in cookie.lower() and "samesite=strict" in cookie.lower()
          and "path=/" in cookie.lower(), cookie)
    page = browser.get("/")
    check("link: the page then opens on the cookie alone", page.status_code == 200, page.text[:200])
    check("link: and so does its data", browser.get("/api/dashboard/status").status_code == 200)

    other = client(signed_in=False)
    other.follow_redirects = False
    wrong = other.get("/", params={"token": "x" * 43})
    check("a wrong link sets nothing", wrong.status_code == 403
          and "set-cookie" not in wrong.headers, wrong.text)
    started_elsewhere = other.get("/", params={"token": DASH_TOKEN},
                                  headers={"sec-fetch-site": "cross-site"})
    check("a link opened from another site still signs in, by a page that reloads",
          started_elsewhere.status_code == 200 and "set-cookie" in started_elsewhere.headers
          and 'http-equiv="refresh"' in started_elsewhere.text, started_elsewhere.text)


def test_a_browser_must_name_a_host_no_rebinding_page_can(live) -> None:
    rebound = client(base="http://evil.example:8080")
    for path in PAGES + API:
        r = rebound.get(path)
        check(f"rebound name: {path} refused", r.status_code == 403, repr((r.status_code, r.text[:120])))
    sign_in = client(base="http://evil.example:8080", signed_in=False)
    sign_in.follow_redirects = False
    r = sign_in.get("/", params={"token": DASH_TOKEN})
    check("rebound name: the link signs nothing in", r.status_code == 403
          and "set-cookie" not in r.headers, r.text)
    for host in ("100.64.1.5:8080", "[::1]:8080", "localhost:8080"):
        r = client(peer="100.64.1.5").get("/api/dashboard/status", headers={"host": host})
        check(f"{host} is answered", r.status_code == 200, r.text)
    saved = dict(server._LISTEN)
    server._LISTEN["host"] = "mybox.lan"
    try:
        r = client(peer="192.168.1.9", base="http://mybox.lan:8080").get("/api/dashboard/status")
    finally:
        server._LISTEN.clear()
        server._LISTEN.update(saved)
    check("the name SERVER_HOST gives is answered", r.status_code == 200, r.text)


def test_the_token_file_is_made_once_and_kept(tmp, monkeypatch) -> None:
    monkeypatch.setattr(dashboard, "_token", "")
    monkeypatch.setattr(dashboard, "runtime_dir", lambda: tmp / "runtime")
    check("no file: no token unless asked to make one", dashboard.load_token() == "")
    made = dashboard.load_token(create=True)
    path = tmp / "runtime" / dashboard.TOKEN_FILE
    check("made: long and on disk", len(made) >= 32
          and path.read_text(encoding="utf-8").strip() == made)
    if os.name == "posix":
        check("made: owner-only", (path.stat().st_mode & 0o777) == 0o600, oct(path.stat().st_mode))
    monkeypatch.setattr(dashboard, "_token", "")
    check("kept: a restart reads the same one", dashboard.load_token(create=True) == made)
    check("link: names it", dashboard.link("0.0.0.0", 8080)
          == f"http://127.0.0.1:8080/?token={made}")
    check("link: a specific address stays that address",
          dashboard.link("100.64.1.5", 9000).startswith("http://100.64.1.5:9000/?token="))
    path.write_text("short\n", encoding="utf-8")
    monkeypatch.setattr(dashboard, "_token", "")
    fresh = dashboard.load_token(create=True)
    check("an unusable file is replaced", fresh != made and len(fresh) >= 32)


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
        "a browser not signed in": client(signed_in=False).post(url, json={}, headers=WRITE),
    }
    for name, r in refused.items():
        check(f"write: {name} refused", r.status_code in (401, 403, 415),
              repr((r.status_code, r.text)))
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


def test_a_credential_inside_a_configured_url_is_not_shown(live, monkeypatch) -> None:
    real = preflight.check_config
    url = "https://kant:pw-0000@gw.example.com/v1beta?api-key=qk-1234"
    monkeypatch.setattr(preflight, "check_config",
                        lambda: real(env={"LLM_BASE_URL": url, "LLM_API_KEY": "x"}))
    status = client().get("/api/dashboard/status").json()
    finding = [f for f in status["preflight"] if f["key"] == "LLM_BASE_URL"]
    check("the misjoined URL is still reported", len(finding) == 1, repr(status["preflight"]))
    detail = finding[0]["detail"]
    check("its user:password and query are masked",
          "pw-0000" not in detail and "qk-1234" not in detail and "kant" not in detail
          and "gw.example.com/v1beta/v1/chat/completions" in detail, detail)


# ---------------------------------------------------- one active rewrite ----

def _pair(live, better: str, *, state: str = candidates.STATE_PROPOSED,
          speaker: str = "u1") -> str:
    ev = seed_event(live, reaction_type="correction", better=better, speaker=speaker,
                    text=f"just say {better}")
    cid = seed_candidate(live, ev, better=better)
    if state == candidates.STATE_PROMOTED:
        live.candidate_ledger.promote(cid, ts=now_iso(), actor="auto", reason="seed")
    return cid


def test_promote_never_leaves_one_reply_two_active_rewrites(live) -> None:
    active = _pair(live, "ugh, that sounds rough", state=candidates.STATE_PROMOTED)
    other = _pair(live, "want me to look at it?", speaker="u2")
    c = client()
    detail = c.get("/api/dashboard/conversation", params={"id": "telegram:c1"}).json()
    view = {cand["id"]: cand for cand in detail["pending"]}[other]
    check("the page offers Replace, not Promote",
          view["actions"] == ["replace", "reject"]
          and [r["id"] for r in view["replaces"]] == [active], repr(view))

    r = c.post(f"/api/dashboard/candidates/{other}/promote", json={}, headers=WRITE)
    check("promote: refused while the other is in use",
          r.status_code == 409 and r.json()["code"] == "active_rival"
          and r.json()["rivals"] == [active], r.text)
    ledger = live.candidate_ledger
    check("promote: nothing changed",
          ledger.get(other)["state"] == candidates.STATE_PROPOSED
          and ledger.get(active)["state"] == candidates.STATE_PROMOTED)

    r = c.post(f"/api/dashboard/candidates/{other}/replace", json={}, headers=WRITE)
    check("replace: accepted", r.status_code == 200 and r.json()["after"] == "promoted", r.text)
    check("replace: the old one is superseded by the new",
          ledger.get(active)["state"] == candidates.STATE_SUPERSEDED
          and ledger.get(active)["superseded_by"] == other)
    live._reload_views_if_stale()
    check("replace: one rewrite of the reply in the view",
          [row.get("candidate_id") for row in live._view_pairs_cache] == [other],
          repr(live._view_pairs_cache))

    r = c.post(f"/api/dashboard/candidates/{other}/rollback", json={}, headers=WRITE)
    check("rollback: accepted", r.status_code == 200, r.text)
    third = _pair(live, "that sounds like a long day", state=candidates.STATE_PROMOTED,
                  speaker="u3")
    r = c.post(f"/api/dashboard/candidates/{other}/promote", json={}, headers=WRITE)
    check("re-promoting a rolled-back rewrite is held to the same rule",
          r.status_code == 409 and r.json()["rivals"] == [third], r.text)


def test_a_dashboard_promote_retires_the_drafts_it_answered(live) -> None:
    complaint = seed_event(live, reaction_type="correction", better="want me to look?",
                           text="that is not helpful")
    draft = seed_candidate(live, complaint, better="want me to look?")
    retry = seed_event(live, reaction_type="correction", better="ugh, that sounds rough",
                       text="yes that")
    answer = seed_candidate(live, retry, better="ugh, that sounds rough")
    live.candidate_ledger.link_evidence(answer, [complaint["event_id"]], ts=now_iso())
    r = client().post(f"/api/dashboard/candidates/{answer}/promote", json={}, headers=WRITE)
    check("promote: accepted", r.status_code == 200, r.text)
    cand = live.candidate_ledger.get(draft)
    check("the draft only its evidence argued for is rejected, as the dashboard",
          cand["state"] == candidates.STATE_REJECTED
          and cand["history"][-1]["actor"] == "dashboard", repr(cand["history"]))


# ------------------------------------------------------------- big chats ----

def test_a_busy_chat_reads_the_log_once_and_sends_the_newest(live, monkeypatch) -> None:
    n = dashboard.LIST_LIMIT + 30
    for i in range(n):
        seed_candidate(live, seed_event(live, reply=f"reply {i}", reaction_type="correction",
                                        better=f"better {i}"), better=f"better {i}")
    scanned = []
    real = promotion.related_events

    def counting(cand, events):
        events = list(events)
        scanned.append(len(events))
        return real(cand, events)

    monkeypatch.setattr(promotion, "related_events", counting)
    detail = client().get("/api/dashboard/conversation", params={"id": "telegram:c1"}).json()
    check("newest first, cut to the limit, with the total",
          len(detail["pending"]) == dashboard.LIST_LIMIT
          and detail["totals"]["pending"] == n
          and detail["pending"][0]["created"] >= detail["pending"][-1]["created"],
          repr(detail["totals"]))
    check("each proposal reads only the events about its own reply",
          sum(scanned) <= 2 * len(scanned), repr(scanned[:5]))
    shown = live.candidate_ledger.get(detail["pending"][0]["id"])
    events = live.evidence_log.all()
    expected = promotion.decide(
        shown, linked_events=live.evidence_log.many(shown["evidence"]),
        related_events=real(shown, events), peers=live.candidate_ledger.all(),
        now=time.time(), policy=live.promotion_policy)
    check("the verdict is the one the whole log gives",
          detail["pending"][0]["checklist"]["verdict"] == expected.reason,
          repr((detail["pending"][0]["checklist"]["verdict"], expected.reason)))


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


_PAGE_PROBE = r"""
const fs = require("fs"), vm = require("vm");
const ctx = { window: { localStorage: null, location: { origin: "http://127.0.0.1:8080" },
                        matchMedia: () => ({ matches: false }) },
              document: { addEventListener() {}, hidden: false }, console };
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(process.argv[1], "utf8"), ctx);
ctx.render = () => {};
const answer = (status, body) => async () => ({ ok: false, status, statusText: "",
                                                json: async () => body });
(async () => {
  const out = {};
  for (const [name, fetch] of [
    ["unreachable", async () => { throw new TypeError("Failed to fetch"); }],
    ["server error", answer(500, { error: "boom", code: "internal" })],
    ["signed out", answer(401, { error: "no token", code: "dashboard_token" })],
  ]) {
    ctx.fetch = fetch;
    await vm.runInContext("refresh()", ctx);
    out[name] = vm.runInContext("({ down: view.down, hints: hintList() })", ctx);
  }
  out.counts = vm.runInContext(
    '[t("notes_n", { n: 1 }), t("notes_n", { n: 2 }), t("convs_n", { n: 1 })]', ctx);
  console.log(JSON.stringify(out));
})();
"""


@pytest.mark.skipif(shutil.which("node") is None, reason="needs node")
def test_the_page_tells_an_error_answer_from_an_unreachable_service() -> None:
    script = Path(dashboard.STATIC_DIR) / "app.js"
    run = subprocess.run(["node", "-e", _PAGE_PROBE, str(script)], capture_output=True,
                         text=True, encoding="utf-8", timeout=60)
    check("probe ran", run.returncode == 0, run.stderr)
    out = json.loads(run.stdout)
    down = out["unreachable"]
    check("nothing answered: unreachable", down["down"] is True
          and "run` still running" in down["hints"][0]["items"][0], repr(down))
    error = out["server error"]
    check("an error answer is not 'unreachable'", error["down"] is False
          and "500" in error["hints"][0]["title"]
          and error["hints"][0]["items"] == ["boom (internal)"], repr(error))
    signed_out = out["signed out"]
    check("signed out: says to open the link again", signed_out["down"] is False
          and "doctor" in signed_out["hints"][0]["items"][0], repr(signed_out))
    check("counts read as English", out["counts"] == ["1 note", "2 notes", "1 chat"],
          repr(out["counts"]))


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
