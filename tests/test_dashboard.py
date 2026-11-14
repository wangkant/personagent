"""The Activity API: who may call it, what it returns, what it may change.

Run from the repo root:

    python -m pytest tests/test_dashboard.py
"""
from __future__ import annotations

import asyncio
import os
import time
import warnings
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI

from persona_agent import (candidates, dashboard, decision_log, evidence, memstate,
                           promotion, welcome)
from persona_agent import server
from persona_agent.agent import Agent
from persona_agent.paths import runtime_dir
from persona_agent.textproc import TextProcessing

from helpers import CLOSED_ONEBOT_URL, check, isolated_agent

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from fastapi.testclient import TestClient

LOCAL = "http://127.0.0.1:8080"
PROBE = "/api/dashboard/conversations"
API = (PROBE, "/api/dashboard/conversation?id=telegram:c1")
WRITE = {"content-type": "application/json", "x-personagent-dashboard": "1"}
SECRET_KEY = "sk-live-SECRET-0123456789abcdef"
SECRET_TOKEN = "connector-SECRET-token-987654"
DASH_TOKEN = "dashTOKEN-0123456789abcdefghijklmnopqrstuv"


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
    a = isolated_agent(tmp, seeds=True, api_key=SECRET_KEY, qq_bot_id="1",
                       persona_name="Nova", qq_onebot_url=CLOSED_ONEBOT_URL,
                       react_elicit_enabled=False)
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
    """A caller that sends the dashboard token, unless `signed_in` is off."""
    if signed_in:
        headers = {dashboard.TOKEN_HEADER: DASH_TOKEN, **headers}
    return TestClient(server.app, base_url=base, client=(peer, 50000),
                      headers=headers or None)


# ---------------------------------------------------------------- access ----

def test_the_token_header_gets_the_data(live) -> None:
    c = client()
    for path in API:
        r = c.get(path)
        check(f"token: {path} answered", r.status_code == 200, r.text[:200])
        check(f"token: {path} is JSON", r.headers["content-type"].startswith("application/json"))
        for name, value in (("x-content-type-options", "nosniff"),
                            ("referrer-policy", "no-referrer"),
                            ("cache-control", "no-store")):
            check(f"token: {path} {name}", r.headers.get(name) == value, repr(r.headers.get(name)))
        check(f"token: {path} CSP", "frame-ancestors 'none'"
              in r.headers.get("content-security-policy", ""))


def test_every_request_needs_the_token_however_local_it_looks(live) -> None:
    cid = seed_candidate(live, seed_event(live))
    write = f"/api/dashboard/candidates/{cid}/reject"
    # What a same-host proxy (nginx's default proxy_pass, an ssh -R or frp
    # tunnel) forwards: a loopback peer, a local Host, no forwarding header.
    looks_local = client(signed_in=False)
    for path in API:
        r = looks_local.get(path)
        check(f"no token: {path} refused", r.status_code == 401, repr((r.status_code, r.text[:120])))
    r = looks_local.post(write, json={}, headers=WRITE)
    check("no token: a write is refused", r.status_code == 401, r.text)
    check("no token: nothing reached the ledger",
          live.candidate_ledger.get(cid)["state"] == candidates.STATE_PROPOSED)

    server.CONNECTOR_TOKEN = SECRET_TOKEN
    r = looks_local.get(PROBE, headers={"x-personagent-token": SECRET_TOKEN})
    check("CONNECTOR_TOKEN opens nothing here", r.status_code == 401, r.text)

    remote = client(peer="203.0.113.9", base="https://bot.example.com", signed_in=False)
    ok = remote.get(PROBE, headers={dashboard.TOKEN_HEADER: DASH_TOKEN})
    check("the dashboard token in its header admits any client", ok.status_code == 200, ok.text)
    bad = remote.get(PROBE, headers={dashboard.TOKEN_HEADER: "nope"})
    check("a wrong one is refused", bad.status_code == 403, bad.text)
    cookie = TestClient(server.app, base_url=LOCAL, client=("127.0.0.1", 1),
                        cookies={"personagent_dashboard": DASH_TOKEN})
    check("a cookie opens nothing", cookie.get(PROBE).status_code == 401)
    for site in ("cross-site", "same-site"):
        r = client(**{"sec-fetch-site": site}).get(PROBE)
        check(f"a {site} fetch of the data is refused", r.status_code == 403, r.text)


def test_the_status_route_is_gone(live) -> None:
    for name, caller in (("with the token", client()),
                         ("without it", client(signed_in=False))):
        r = caller.get("/api/dashboard/status")
        check(f"status, {name}: no such route", r.status_code == 404,
              repr((r.status_code, r.text[:120])))
    check("nothing builds a status payload", not hasattr(dashboard, "status_payload"))


def test_the_root_only_points_at_the_local_page(live) -> None:
    c = client(signed_in=False)
    c.follow_redirects = False
    page = c.get("/")
    check("root: answered without the token", page.status_code == 200, page.text)
    check("root: plain text, in both languages",
          page.headers["content-type"].startswith("text/plain")
          and "Activity" in page.text and "learned`" in page.text
          and "本地页面" in page.text, page.text)
    check("root: hardened", page.headers.get("x-content-type-options") == "nosniff")
    check("root: holds no token", DASH_TOKEN not in page.text)
    link = c.get("/", params={"token": DASH_TOKEN})
    check("root: an old link signs nothing in",
          link.status_code == 200 and "set-cookie" not in link.headers, link.text)
    for path in ("/dashboard/app.js", "/dashboard/app.css", "/dashboard/mark.svg"):
        r = client().get(path)
        check(f"{path} is gone", r.status_code == 404, repr((r.status_code, r.text[:120])))


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
        "a caller without the token": client(signed_in=False).post(url, json={}, headers=WRITE),
    }
    for name, r in refused.items():
        check(f"write: {name} refused", r.status_code in (401, 403, 415),
              repr((r.status_code, r.text)))
    check("write: GET cannot change anything", c.get(url).status_code == 405)
    check("write: nothing reached the ledger",
          live.candidate_ledger.get(cid)["state"] == candidates.STATE_PROPOSED)
    same = c.post(url, json={}, headers={**WRITE, "origin": LOCAL})
    check("write: the service's own origin is accepted", same.status_code == 200, same.text)


def test_forgetting_a_note_follows_the_same_rules(live) -> None:
    live.memories["telegram:c1"] = [{"text": "likes tea", "time": time.time()}]
    c = client()
    url = "/api/dashboard/memory/forget"
    note = c.get("/api/dashboard/conversation",
                 params={"id": "telegram:c1"}).json()["memories"][0]
    body = {"conv": note["conv"], "kind": "note", "id": note["id"]}
    refused = {
        "a caller without the token": client(signed_in=False).post(url, json=body, headers=WRITE),
        "no custom header": c.post(url, json=body),
        "foreign origin": c.post(url, json=body,
                                 headers={**WRITE, "origin": "https://evil.example"}),
    }
    for name, r in refused.items():
        check(f"forget: {name} refused", r.status_code in (401, 403),
              repr((r.status_code, r.text)))
    check("forget: the note is still there", len(live.memories["telegram:c1"]) == 1)
    done = c.post(url, json=body, headers=WRITE)
    check("forget: a note goes by the conv and id its entry carries",
          done.status_code == 200 and live.memories["telegram:c1"] == [], done.text)
    again = c.post(url, json=body, headers=WRITE)
    check("forget: a note already gone is a 409", again.status_code == 409, again.text)


# ----------------------------------------------------------------- memory ----

def _remember(agent: Agent, conv: str = "telegram:c1") -> dict:
    """A chat with a fact, an event, a summary and an always-present note."""
    now = time.time()
    agent._append_memory(conv, {"text": "Sam has a dog now", "time": now - 3600, "born": now - 86400,
                                "auto": True, "user_id": "telegram:42", "user_name": "Sam",
                                "used": now - 600, "said_by": "telegram:7", "said_by_name": "Alex"})
    store = agent.episode_store
    event = store.add(conv, {"text": "Sam and Alex planned a hike", "t0": now - 7200, "t1": now - 5400,
                             "who": ["telegram:42", "telegram:7"], "names": ["Sam", "Alex"]})
    store.set_thread(conv, "They are choosing a trail for Saturday.", now - 9000, now - 5400)
    agent._save_episodes()
    agent.core_memory[conv] = "Speak plainly with this group."
    agent._save_core_memory()
    return {"note": agent.memories[conv][0]["id"], "episode": event["id"],
            "thread": store.thread(conv)["id"]}


def test_the_chat_payload_carries_every_kind_of_memory(live) -> None:
    ids = _remember(live)
    live.memory_tidy_every = 8
    memstate.CallBudget(live.memory_state).record_call("telegram:c1", time.time())
    old = live.memory_trash.put("telegram:c1", "core", {"text": "Be terse."}, "rewritten", "reply")
    detail = client().get("/api/dashboard/conversation", params={"id": "telegram:c1"}).json()
    note = detail["memories"][0]
    check("the fact: its id, who said it, when first noted and last used",
          note["id"] == ids["note"] and note["said_by_name"] == "Alex" and note["about"] == "Sam"
          and note["born"] < note["time"] and note["used"] > 0, repr(note))
    check("the event, with its times and people",
          [(e["id"], e["names"]) for e in detail["episodes"]] == [(ids["episode"], ["Sam", "Alex"])]
          and detail["episodes"][0]["t0"] < detail["episodes"][0]["t1"], repr(detail["episodes"]))
    check("the summary, with the stretch it covers",
          detail["thread"]["id"] == ids["thread"] and detail["thread"]["from_t"] < detail["thread"]["to_t"],
          repr(detail["thread"]))
    check("the earlier always-present note can be brought back",
          [(r["tid"], r["kind"], r["why"], r["text"]) for r in detail["removed"]]
          == [(old, "core", "rewritten", "Be terse.")] and detail["removed"][0]["until"] > time.time(),
          repr(detail["removed"]))
    check("consolidation status while it is on",
          detail["memory_status"] == {"calls_today": 1, "cap": 40, "paused_until": 0.0, "next_at": 0.0},
          repr(detail["memory_status"]))
    memstate.CallBudget(live.memory_state).failed("telegram:c1", time.time(), "TimeoutError")
    backing_off = client().get("/api/dashboard/conversation", params={"id": "telegram:c1"}).json()
    check("after a failed call the status says when it tries again",
          backing_off["memory_status"]["next_at"] > time.time(), repr(backing_off["memory_status"]))
    live.memory_tidy_every = 0
    off = client().get("/api/dashboard/conversation", params={"id": "telegram:c1"}).json()
    check("no status line while consolidation is off", off["memory_status"] is None)


def test_each_kind_is_forgotten_and_brought_back(live) -> None:
    ids = _remember(live)
    c = client()
    url = "/api/dashboard/memory/forget"
    tids = {}
    for kind in ("note", "episode", "thread", "core"):
        r = c.post(url, json={"conv": "telegram:c1", "kind": kind, "id": ids.get(kind, "")}, headers=WRITE)
        check(f"forget {kind}: done, with a trash id", r.status_code == 200 and r.json()["tid"], r.text)
        tids[kind] = r.json()["tid"]
    store = live.episode_store
    check("forget: every kind is gone from its store",
          not live.memories.get("telegram:c1") and not store.episodes("telegram:c1")
          and store.thread("telegram:c1") is None and "telegram:c1" not in live.core_memory)
    check("forget: a second forget of the event is a 409",
          c.post(url, json={"conv": "telegram:c1", "kind": "episode", "id": ids["episode"]},
                 headers=WRITE).status_code == 409)
    check("forget: an unknown kind is refused",
          c.post(url, json={"conv": "telegram:c1", "kind": "all"}, headers=WRITE).status_code == 400)
    restore = "/api/dashboard/memory/restore"
    refused = client(signed_in=False).post(restore, json={"tid": tids["note"]}, headers=WRITE)
    check("restore: no token, refused", refused.status_code == 401, refused.text)
    check("restore: no custom header, refused",
          c.post(restore, json={"tid": tids["note"]}).status_code == 403)
    for kind, tid in tids.items():
        r = c.post(restore, json={"tid": tid}, headers=WRITE)
        check(f"restore {kind}: done", r.status_code == 200, r.text)
    check("restore: every kind is back",
          live.memories["telegram:c1"][0]["id"] == ids["note"]
          and store.get("telegram:c1", ids["episode"]) is not None
          and store.thread("telegram:c1")["text"].startswith("They are choosing")
          and live.core_memory["telegram:c1"] == "Speak plainly with this group.")
    again = c.post(restore, json={"tid": tids["note"]}, headers=WRITE)
    check("restore: a second time it is gone (404)", again.status_code == 404
          and again.json()["code"] == "restore_gone", again.text)
    # The same fact put back by hand while the removal is still restorable.
    tid = c.post(url, json={"conv": "telegram:c1", "kind": "note", "id": ids["note"]}, headers=WRITE).json()["tid"]
    live._append_memory("telegram:c1", dict(live.memory_trash.get(tid)["item"]))
    exists = c.post(restore, json={"tid": tid}, headers=WRITE)
    check("restore: what is already there is a 409", exists.status_code == 409, exists.text)
    stale = live.memory_trash.put("telegram:c1", "note", {"id": "m0000000001", "text": "likes tea"},
                                  "forgotten_page", "page", now=time.time() - 90_000)
    late = c.post(restore, json={"tid": stale}, headers=WRITE)
    check("restore: a page forget past its day is gone (404)", late.status_code == 404, late.text)
    check("restore: an unknown id is gone (404)",
          c.post(restore, json={"tid": "r0000000000"}, headers=WRITE).status_code == 404)


def test_forget_this_chat_clears_that_chat_only(live) -> None:
    _remember(live, "telegram:c1")
    _remember(live, "telegram:c2")
    live._forget_item("telegram:c1", "note", live.memories["telegram:c1"][0]["id"])
    live._forget_item("telegram:c2", "note", live.memories["telegram:c2"][0]["id"])
    live._recent = None
    r = client().post("/api/dashboard/memory/forget_chat", json={"conv": "telegram:c1"}, headers=WRITE)
    check("forget chat: done, counting what it remembered", r.status_code == 200
          and r.json() == {"ok": True, "forgotten": 3}, r.text)
    store = live.episode_store
    check("forget chat: the chat's events, summary and note are gone, and nothing is restorable",
          not store.episodes("telegram:c1") and store.thread("telegram:c1") is None
          and "telegram:c1" not in live.core_memory and live._removed_items("telegram:c1") == [])
    check("forget chat: the other chat keeps everything",
          store.episodes("telegram:c2") and store.thread("telegram:c2")
          and live.core_memory.get("telegram:c2") and len(live._removed_items("telegram:c2")) == 1)
    check("forget chat: without a chat it is refused",
          client().post("/api/dashboard/memory/forget_chat", json={}, headers=WRITE).status_code == 400)


def test_forgetting_the_page_chat_takes_its_earlier_chats_too(live) -> None:
    _remember(live, "private:browser:old")
    _remember(live, "private:browser:now")
    _remember(live, "private:telegram:u1")
    r = client().post("/api/dashboard/memory/forget_chat",
                      json={"conv": "private:browser:now", "earlier_page": True}, headers=WRITE)
    check("page forget: both page chats are counted", r.status_code == 200
          and r.json()["forgotten"] == 2 * dashboard._memory_count(live, "private:telegram:u1"), r.text)
    check("page forget: neither page chat remembers anything",
          not live.memories.get("private:browser:old") and not live.memories.get("private:browser:now"))
    check("page forget: a chat on a platform keeps everything",
          bool(live.memories.get("private:telegram:u1")))
    _remember(live, "telegram:c1")
    _remember(live, "telegram:c2")
    client().post("/api/dashboard/memory/forget_chat",
                  json={"conv": "telegram:c1", "earlier_page": True}, headers=WRITE)
    check("page forget: asked of a platform chat, it forgets that chat alone",
          bool(live.memories.get("telegram:c2")))


def test_the_memory_list_is_what_the_terminal_reads(live) -> None:
    ids = _remember(live)
    live._forget_item("telegram:c1", "episode", ids["episode"], by="terminal")
    url = "/api/dashboard/memory/list"
    check("list: the token is needed", client(signed_in=False).get(url).status_code == 401)
    listed = client().get(url).json()
    chat = listed["chats"][0]
    check("list: the chat with its always-present note, summary and fact",
          chat["conv"] == "telegram:c1" and chat["core"]["text"].startswith("Speak plainly")
          and chat["thread"]["id"] == ids["thread"] and chat["facts"][0]["id"] == ids["note"]
          and chat["events"] == [], repr(chat))
    check("list: the forgotten event can be brought back",
          [(r["kind"], r["by"]) for r in listed["removed"]] == [("episode", "terminal")], repr(listed["removed"]))
    check("list: one chat only", client().get(url, params={"conv": "telegram:c9"}).json()
          == {"chats": [], "removed": []})


def test_a_replaced_page_chat_is_listed_while_it_remembers(live, tmp, monkeypatch) -> None:
    runtime = tmp / "runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    (runtime / "page.owner").write_text("b" * 32, encoding="utf-8")
    monkeypatch.setattr(dashboard, "runtime_dir", lambda: runtime)
    old = "private:browser:" + "a" * 32
    live.episode_store.add(old, {"text": "We set up the character together", "t0": time.time(),
                                 "t1": time.time(), "who": ["browser:" + "a" * 32]})
    live.last_dm_activity_at["browser:" + "a" * 32] = time.time()
    listed = [c["id"] for c in client().get(PROBE).json()["conversations"]]
    check("an old page chat with an event is listed", old in listed, repr(listed))
    live.episode_store.drop_conv(old)
    listed = [c["id"] for c in client().get(PROBE).json()["conversations"]]
    check("once it remembers nothing it is not", old not in listed, repr(listed))


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
    learned = c.get("/api/dashboard/conversation",
                    params={"id": "telegram:c1"}).json()["learned"]
    check("promote: listed as learned, with who asked for it and its way back",
          [(v["id"], v["actions"], v["evidence"], v["by"]) for v in learned]
          == [(cid, ["rollback"], [{"speaker": "Alex"}], {"by": "person", "why": ""})], repr(learned))

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
    back = c.post(f"/api/dashboard/candidates/{cid}/promote", json={}, headers=WRITE)
    check("a person's undo is not brought back by promote",
          back.status_code == 409 and live.candidate_ledger.get(cid)["state"] == "rolled_back", back.text)
    missing = c.post("/api/dashboard/candidates/feedfacefeedface/promote", json={}, headers=WRITE)
    check("unknown candidate: 404", missing.status_code == 404, missing.text)
    unknown = c.post(f"/api/dashboard/candidates/{cid}/delete", json={}, headers=WRITE)
    check("unknown action: 404", unknown.status_code == 404, unknown.text)

    detail = c.get("/api/dashboard/conversation", params={"id": "telegram:c1"}).json()
    check("detail: a rolled-back candidate is no longer listed",
          detail["observing"] == [] and detail["learned"] == [], repr(detail))


def test_an_observed_proposal_carries_what_the_page_shows(live) -> None:
    ev = seed_event(live)
    pair = seed_candidate(live, ev)
    positive = seed_event(live, reply="ugh, that sounds rough",
                          reaction_type="positive", text="haha thanks")
    example = seed_candidate(live, positive, ctype=candidates.TYPE_EXAMPLE)
    detail = client().get("/api/dashboard/conversation",
                          params={"id": "telegram:c1"}).json()
    by_id = {c["id"]: c for c in detail["observing"]}
    check("observing: both proposals listed", set(by_id) == {pair, example}, repr(list(by_id)))
    view = by_id[pair]
    check("observing: the reply, its rewrite and who asked for it",
          view["type"] == candidates.TYPE_PAIR and view["reply"] == ev["reply"]
          and view["better"] == "ugh, that sounds rough" and view["created"] > 0
          and view["evidence"] == [{"speaker": "Alex"}], repr(view))
    check("observing: a person's optional actions", view["actions"] == ["promote", "reject"])
    check("observing: where it stands, from the policy's own decision",
          view["standing"]["stage"] == "reactions" and view["standing"]["missing"] == "strong"
          and (view["standing"]["strong"], view["standing"]["needStrong"]) == (0, 1)
          and set(view["standing"]) == set(dashboard.STANDING_SENT)
          and view["by"] is None, repr(view["standing"]))
    check("observing: an example has no rewrite",
          by_id[example]["type"] == candidates.TYPE_EXAMPLE
          and by_id[example]["better"] == "", repr(by_id[example]))


class _Seen(dict):
    """A payload object that notes which of its keys a reader asks for."""

    def __init__(self, data: dict) -> None:
        super().__init__({key: _seen(value) for key, value in data.items()})
        self.asked: set[str] = set()

    def get(self, key, default=None):
        self.asked.add(key)
        return super().get(key, default)


def _seen(value):
    if isinstance(value, dict):
        return _Seen(value)
    return [_seen(v) for v in value] if isinstance(value, list) else value


def _mismatch(value, where: str = "") -> list[str]:
    """Keys the reader never asked for (-), or asked for and did not get (+)."""
    if isinstance(value, list):
        return sorted({m for v in value for m in _mismatch(v, where)})
    if not isinstance(value, _Seen):
        return []
    out = [f"-{where}{key}" for key in value.keys() - value.asked]
    out += [f"+{where}{key}" for key in value.asked - value.keys()]
    for key, inner in value.items():
        out += _mismatch(inner, f"{where}{key}.")
    return sorted(out)


def test_the_api_sends_what_the_local_page_reads_and_nothing_else(live) -> None:
    kept = seed_candidate(live, seed_event(live))
    live.candidate_ledger.promote(kept, ts=now_iso(), actor="auto", reason="seed")
    seed_candidate(live, seed_event(live, reply="lol nice", reaction_type="positive",
                                    text="haha"), ctype=candidates.TYPE_EXAMPLE)
    live.memories["telegram:c1"] = [{"text": "likes tea", "time": time.time()}]
    decision_log.record("telegram:c1", "called", True, "addressed", "count me in",
                        answered="Nova?", sender="Sam")
    c = client()
    chat = _seen(c.get("/api/dashboard/conversation", params={"id": "telegram:c1"}).json())
    shown = welcome._activity_chat(chat)
    check("chat: a proposal, a kept change, a note and a decision were sent",
          all(shown[part] for part in ("observing", "learned", "notes", "recent")), repr(shown))
    check("chat: nothing observed offers a decision, and nothing is called review",
          shown["observing"][0]["actions"] == [] and "review" not in shown, repr(shown))
    check("chat: who asked for a change reaches the page",
          shown["learned"][0]["from"] == ["Alex"], repr(shown["learned"]))
    check("chat: every field sent is one the page reads", _mismatch(chat) == [],
          repr(_mismatch(chat)))

    listing = _seen(c.get(PROBE).json())

    async def served(method, path, **kwargs):
        return listing

    listed = asyncio.run(welcome.Workspace.activity(SimpleNamespace(_activity_call=served)))
    check("list: the chat is there, with its counts",
          [(row["id"], row["observing"], row["learned"], row["notes"]) for row in listed["chats"]]
          == [("telegram:c1", 1, 1, 1)], repr(listed))
    check("list: when something last came into use here", listed["chats"][0]["latest"] > 0)
    rows = listing["conversations"]
    check("list: every field sent is one the page reads", _mismatch(rows) == [],
          repr(_mismatch(rows)))


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
    bodies = [c.get(path).text for path in (*API, "/")]
    blob = "\n".join(bodies)
    for secret in (SECRET_KEY, SECRET_TOKEN, "tvly-SECRET-55555555"):
        check(f"secrets: {secret[:10]}... never sent", secret not in blob)
    detail = c.get("/api/dashboard/conversation", params={"id": "telegram:c1"}).json()
    check("secrets: masked where they were quoted",
          detail["memories"][0]["text"] == "the key is ***", repr(detail["memories"]))


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
    other = _pair(live, "want me to look at it?", speaker="u2")
    c = client()

    def offered() -> list[str]:
        detail = c.get("/api/dashboard/conversation", params={"id": "telegram:c1"}).json()
        return {cand["id"]: cand for cand in detail["observing"]}[other]["actions"]

    check("with no rewrite in use, the page offers Promote",
          offered() == ["promote", "reject"], repr(offered()))
    active = _pair(live, "ugh, that sounds rough", state=candidates.STATE_PROMOTED)
    check("the page offers Replace, not Promote",
          offered() == ["replace", "reject"], repr(offered()))

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


def test_a_person_puts_in_use_through_the_one_shared_function(live, monkeypatch) -> None:
    from persona_agent import learning
    cid = _pair(live, "ugh, that sounds rough")
    seen = []
    real = learning.put_in_use

    def spy(ledger, cid, **kwargs):
        seen.append((cid, kwargs["actor"]))
        return real(ledger, cid, **kwargs)

    monkeypatch.setattr(learning, "put_in_use", spy)
    r = client().post(f"/api/dashboard/candidates/{cid}/promote", json={}, headers=WRITE)
    check("promote: through learning.put_in_use, as the dashboard",
          r.status_code == 200 and seen == [(cid, "dashboard")], repr(seen))


def test_bring_back_is_only_for_what_the_character_set_aside(live) -> None:
    ledger = live.candidate_ledger
    by_character = _pair(live, "want me to look at it?", speaker="u2")
    ledger.reject(by_character, ts=now_iso(), actor="character", reason="It sounds pushy.")
    in_use = _pair(live, "ugh, that sounds rough", state=candidates.STATE_PROMOTED)
    by_person = _pair(live, "that sounds like a long day", speaker="u3")
    ledger.reject(by_person, ts=now_iso(), actor="dashboard", reason="local page")
    c = client()
    refused = c.post(f"/api/dashboard/candidates/{by_person}/restore", json={}, headers=WRITE)
    check("restore: a person's discard stays final",
          refused.status_code == 409 and ledger.get(by_person)["state"] == "rejected", refused.text)
    r = c.post(f"/api/dashboard/candidates/{by_character}/restore", json={}, headers=WRITE)
    check("restore: what the character set aside comes back",
          r.status_code == 200 and r.json()["after"] == "promoted", r.text)
    check("restore: written as the dashboard",
          ledger.get(by_character)["history"][-1]["actor"] == "dashboard")
    check("restore: the rewrite in use steps aside for it",
          ledger.get(in_use)["state"] == candidates.STATE_ROLLED_BACK
          and ledger.get(in_use)["history"][-1]["reason"] == f"replaced by {by_character}")


def test_learned_items_say_who_put_them_in_use(live) -> None:
    ledger = live.candidate_ledger
    adopted = _pair(live, "want me to look at it?", speaker="u2")
    ledger.promote(adopted, ts=now_iso(), actor="character", reason="It offers help kindly.")
    agreed = seed_candidate(live, seed_event(live, reply="lol nice", reaction_type="positive",
                                             text="haha"), ctype=candidates.TYPE_EXAMPLE)
    ledger.promote(agreed, ts=now_iso(), actor="auto", reason="2 compatible events, 0 strong")
    learned = client().get("/api/dashboard/conversation",
                           params={"id": "telegram:c1"}).json()["learned"]
    by = {v["id"]: v["by"] for v in learned}
    check("by the character, with its reason",
          by[adopted] == {"by": "character", "why": "It offers help kindly."}, repr(by))
    check("by the reactions", by[agreed] == {"by": "reactions", "why": ""}, repr(by))


def test_expiry_and_rules_are_named_from_the_ledger_reasons() -> None:
    from persona_agent import learning
    entry = {"actor": "auto", "reason": learning.REASON_EXPIRED.format(days="30")}
    check("time limit", dashboard.decided_by(entry) == {"by": "time", "why": "", "days": "30"})
    check("rule", dashboard.decided_by({"actor": "auto", "reason": learning.REASON_LESSON})
          == {"by": "rule", "why": "lesson"})
    check("a person", dashboard.decided_by({"actor": "admin", "reason": learning.REASON_LESSON})
          == {"by": "person", "why": ""})


# ------------------------------------------------------------- big chats ----

def test_a_busy_chat_sends_the_newest_and_judges_only_what_it_shows(live, monkeypatch) -> None:
    n = dashboard.LIST_LIMIT + 30
    for i in range(n):
        seed_candidate(live, seed_event(live, reply=f"reply {i}", reaction_type="correction",
                                        better=f"better {i}"), better=f"better {i}")
    rules = ("decide", "related_events", "counter_evidence", "supports_candidate")
    calls = []

    def counted(owner, name: str) -> None:
        real = getattr(owner, name)

        def call(*args, **kwargs):
            calls.append(name)
            return real(*args, **kwargs)

        monkeypatch.setattr(owner, name, call)

    for name in rules:
        counted(promotion, name)
    for name in ("all", "many"):
        counted(live.evidence_log, name)
    c = client()
    detail = c.get("/api/dashboard/conversation", params={"id": "telegram:c1"}).json()
    check("newest first, cut to the limit",
          len(detail["observing"]) == dashboard.LIST_LIMIT
          and detail["observing"][0]["created"] >= detail["observing"][-1]["created"],
          str(len(detail["observing"])))
    # Each shown item says where it stands; nothing more is judged.
    check("a poll decides each shown item once", calls.count("decide") == dashboard.LIST_LIMIT,
          repr(calls.count("decide")))
    check("and reads the evidence log once",
          calls.count("all") + calls.count("many") == 1, repr(calls))
    listed = c.get(PROBE).json()["conversations"]
    check("the list of chats carries the full count",
          [(row["id"], row["observing"]) for row in listed] == [("telegram:c1", n)], repr(listed))


def test_a_fresh_install_has_empty_lists_not_errors(live, tmp) -> None:
    c = client()
    check("fresh: no conversations", c.get(PROBE).json() == {"conversations": []})
    detail = c.get("/api/dashboard/conversation", params={"id": "g1"}).json()
    check("fresh: an unknown conversation is empty, not missing",
          all(detail[k] == [] for k in ("decisions", "memories", "observing", "learned")),
          repr(detail))
    check("fresh: a missing id is a 400",
          c.get("/api/dashboard/conversation").status_code == 400)
    server.agent = None
    check("agent off: conversations still listed", c.get(PROBE).status_code == 200)
    off = c.get("/api/dashboard/conversation", params={"id": "g1"})
    check("agent off: a chat still answers, with no notes",
          off.status_code == 200 and off.json()["memories"] == [], off.text[:200])


def test_dashboard_enabled_false_removes_the_routes(monkeypatch) -> None:
    monkeypatch.setenv("DASHBOARD_ENABLED", "false")
    app = FastAPI()
    check("disabled: install says so", dashboard.install(app) is False)
    check("disabled: the app records it", app.state.dashboard is False)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        check("disabled: / is a 404",
              TestClient(app, base_url=LOCAL, client=("127.0.0.1", 1)).get("/").status_code == 404)
    monkeypatch.setenv("DASHBOARD_ENABLED", "true")
    enabled = FastAPI()
    check("enabled: install says so", dashboard.install(enabled) is True)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        status = TestClient(enabled, base_url=LOCAL, client=("127.0.0.1", 1)).get(
            PROBE).status_code
    check("enabled: the route answers (asking for its token)", status == 401, str(status))
    check("the service includes it by default", server.app.state.dashboard is True
          and server._dashboard_served())


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
    log.record("g3", "called", True, "addressed", "x" * 500 + "\x02secret\x03",
               answered="y" * 500 + "\x02page\x03", sender="z" * 100 + "\n", now=22)
    row = log.recent("g3")[0]
    for field, limit in (("excerpt", decision_log.EXCERPT_CHARS),
                         ("answered", decision_log.EXCERPT_CHARS),
                         ("sender", decision_log.NAME_CHARS)):
        check(f"{field}: short and printable",
              len(row[field]) <= limit and "\x02" not in row[field]
              and "\n" not in row[field], repr(row[field]))
    log.record("g3", "judge", False, "passed", "lol", answered="ignored", sender="Sam", now=23)
    quiet = log.recent("g3")[0]
    check("a silence names who wrote what it let pass, and answered nothing",
          quiet["sender"] == "Sam" and quiet["answered"] == "", repr(quiet))


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
          and below["excerpt"] == "anyone around this evening"
          and below["sender"] == "Sam" and below["answered"] == "", repr(below))
    check("called: spoke, with what it said and the message it answered",
          spoke["spoke"] is True and spoke["mode"] == "called"
          and spoke["reason"] == "addressed" and spoke["excerpt"] == "sure, on it"
          and spoke["answered"] == "Nova can you take a look"
          and spoke["sender"] == "Sam", repr(spoke))
    check("a pass is recorded as a choice to stay quiet",
          quiet_followup["spoke"] is False and quiet_followup["reason"] == "passed"
          and quiet_followup["mode"] == "followup"
          and quiet_followup["sender"] == "Sam", repr(quiet_followup))


def test_the_chat_carries_the_message_each_reply_answered(live) -> None:
    decision_log.record("telegram:c1", "", False, "below the trigger count",
                        "which match?", sender="Priya")
    decision_log.record("telegram:c1", "called", True, "addressed", "count me in",
                        answered=f"Nova, the key is {SECRET_KEY}", sender="Sam")
    server.CONNECTOR_TOKEN = SECRET_TOKEN
    rows = client().get("/api/dashboard/conversation",
                        params={"id": "telegram:c1"}).json()["decisions"]
    check("newest first, both lines", len(rows) == 2, repr(rows))
    spoke, quiet = rows
    check("a reply carries the start of the message it answered and its sender",
          spoke["answered"].startswith("Nova, the key is") and spoke["sender"] == "Sam"
          and spoke["excerpt"] == "count me in", repr(spoke))
    check("the excerpt is masked like every other field", SECRET_KEY not in spoke["answered"],
          spoke["answered"])
    check("a silence carries the sender of the message it let pass",
          quiet["sender"] == "Priya" and quiet["answered"] == ""
          and quiet["excerpt"] == "which match?", repr(quiet))
    check("the line keeps its earlier fields",
          set(quiet) >= {"ts", "mode", "spoke", "reason", "excerpt", "count"}, repr(quiet))
