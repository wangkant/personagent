"""The learned panel: everything learned, read and decided from the files."""
from __future__ import annotations

import json

from fastapi.testclient import TestClient
import pytest

from persona_agent import candidates, evidence
from persona_agent import setup_wizard as sw
from persona_agent import welcome
from persona_agent.panels import learned

TOKEN = "test-local-capability"
HEADERS = {welcome.TOKEN_HEADER: TOKEN}
SECRET = "sk-learned-secret-0123456789"
CONV = "telegram:123456789"


def _event(reply, said, *, rtype="correction", better="", speaker="u1", name="Alice",
           ts="2026-11-01T10:00:00", conv=CONV):
    return evidence.make_event(
        kind=evidence.KIND_REACTION, ts=ts, lang="en", platform="telegram", conv_id=conv,
        persona="Nova", speaker_id=speaker, speaker_name=name, recipient_id="u1",
        reply=reply, reaction_text=said, directed=True, direction="reply",
        reaction_type=rtype, adjudication={"accept": True, "better": better, "reason": "a short fix"})


def _seed(runtime, lang="en"):
    """One item in each state, plus a rival pair; returns their ids."""
    runtime.mkdir(parents=True, exist_ok=True)
    ledger = candidates.CandidateLedger(runtime / f"candidate_ledger.{lang}.jsonl")
    log = evidence.EvidenceLog(runtime / f"evidence.{lang}.jsonl")
    ids = {}

    def add(key, ctype, reply, better="", said="that was odd", lesson=""):
        ev = _event(reply, said, better=better,
                    rtype="correction" if ctype == candidates.TYPE_PAIR else "positive")
        log.append(ev)
        cand = candidates.make_candidate(
            ctype=ctype, scope=candidates.scope_from_event(ev),
            payload={"reply": reply, "better": better, "lesson": lesson,
                     "context": ["Bob: how are you?"]},
            evidence=[ev["event_id"]], created_at="2026-11-01T10:00:00")
        ledger.propose(cand)
        ids[key] = cand["candidate_id"]

    ts = dict(ts="2026-11-02T09:00:00", actor="auto", reason="2 compatible events, 1 strong")
    add("waiting", candidates.TYPE_PAIR, "Greetings, human.", "hey!",
        said=f"too stiff, my key is {SECRET}", lesson="keep it casual")
    add("in_use", candidates.TYPE_EXAMPLE, "lol same")
    ledger.promote(ids["in_use"], **ts)
    add("discarded", candidates.TYPE_EXAMPLE, "whatever")
    ledger.reject(ids["discarded"], ts="2026-11-02T09:00:00", actor="admin", reason="too rude")
    add("undone", candidates.TYPE_EXAMPLE, "sure thing")
    ledger.promote(ids["undone"], **ts)
    ledger.rollback(ids["undone"], ts="2026-11-03T09:00:00", actor="auto",
                    reason="the person it was for disagreed")
    # Two rewrites of one reply: the first in use, the second waiting.
    add("rival_live", candidates.TYPE_PAIR, "Good day.", "hi")
    ledger.promote(ids["rival_live"], **ts)
    add("rival_new", candidates.TYPE_PAIR, "Good day.", "yo")
    return ids


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    for name in ("AGENT_LANG", "AGENT_RUNTIME_DIR", "PROMOTE_AUTO_ENABLED", "ADMIN_IDS",
                 "PERSONA_NAME", "PERSONA_VERSION", "PROMOTE_MIN_SPEAKERS"):
        monkeypatch.delenv(name, raising=False)
    (tmp_path / ".env").write_text(f"LLM_API_KEY={SECRET}\nAGENT_LANG=en\nPERSONA_NAME=Nova\n",
                                   encoding="utf-8")
    value = welcome.Workspace(tmp_path)
    monkeypatch.setattr(sw, "probe_key", lambda *a, **kw: sw.Probe("http://127.0.0.1", 200, ""))
    yield value
    value.close()


@pytest.fixture
def client(workspace):
    with TestClient(welcome.create_app(workspace.home, TOKEN, workspace=workspace),
                    base_url="http://127.0.0.1") as value:
        yield value


@pytest.fixture
def ids(workspace):
    return _seed(workspace.home / "runtime")


def _ledger(workspace, lang="en"):
    return candidates.CandidateLedger(workspace.home / "runtime" / f"candidate_ledger.{lang}.jsonl")


def _error(response):
    assert response.status_code == 400, response.text
    return response.json()["error"]


def test_every_route_needs_the_local_token(client, ids):
    assert client.get("/api/learned").status_code == 403
    assert client.get(f"/api/learned/item?id={ids['waiting']}").status_code == 403
    assert client.post("/api/learned/decide", json={"id": ids["waiting"], "action": "use"}).status_code == 403


def test_overview_works_with_the_character_stopped(client, ids):
    value = client.get("/api/learned", headers=HEADERS).json()
    assert value["running"] is False and value["lang"] == "en"
    assert value["totals"] == {"in_use": 2, "observing": 2, "set_aside": 2}
    assert value["chats"] == 1 and value["tab"] == "in_use" and value["count"] == 2
    assert {row["id"] for row in value["items"]} == {ids["in_use"], ids["rival_live"]}
    row = next(r for r in value["items"] if r["id"] == ids["in_use"])
    assert row["chat"]["platform"] == "telegram" and row["chat"]["kind"] == "group"
    assert row["chat"]["tail"] == "…456789" and row["kind"] == "repeat" and row["when"] > 0
    waiting = client.get("/api/learned?tab=observing&limit=1", headers=HEADERS).json()
    assert waiting["count"] == 2 and len(waiting["items"]) == 1 and waiting["items"][0]["by"] == ""
    aside = client.get("/api/learned?tab=set_aside", headers=HEADERS).json()["items"]
    assert {row["state"]: row["by"] for row in aside} == {"rejected": "person", "rolled_back": "reactions"}
    assert _error(client.get("/api/learned?tab=bogus", headers=HEADERS)) == "learned_invalid"
    assert _error(client.get("/api/learned?lang=../x", headers=HEADERS)) == "learned_invalid"


def test_nothing_secret_or_persona_internal_leaves(client, ids):
    for response in (client.get("/api/learned?tab=observing", headers=HEADERS),
                     client.get(f"/api/learned/item?id={ids['waiting']}", headers=HEADERS)):
        assert response.status_code == 200
        assert SECRET not in response.text and "persona_hash" not in response.text
    said = client.get(f"/api/learned/item?id={ids['waiting']}", headers=HEADERS).json()["events"][0]["said"]
    assert said == "too stiff, my key is ***"


def test_an_empty_home_has_nothing_yet(client):
    value = client.get("/api/learned", headers=HEADERS).json()
    assert value["totals"] == dict.fromkeys(learned.TABS, 0) and value["items"] == []
    assert value["langs"] == [{"code": "en", "count": 0, "current": True}]


def test_the_other_language_pool_is_listed_and_readable(client, workspace, ids):
    zh = _seed(workspace.home / "runtime", "zh")
    value = client.get("/api/learned", headers=HEADERS).json()
    assert {p["code"]: p["count"] for p in value["langs"]} == {"en": 6, "zh": 6}
    other = client.get("/api/learned?lang=zh&tab=observing", headers=HEADERS).json()
    assert other["lang"] == "zh" and other["current"] == "en"
    assert client.get(f"/api/learned/item?id={zh['waiting']}&lang=zh", headers=HEADERS).status_code == 200


def test_one_item_in_full_says_where_it_stands(client, ids):
    item = client.get(f"/api/learned/item?id={ids['waiting']}", headers=HEADERS).json()
    assert item["tab"] == "observing" and item["kind"] == "wording"
    assert item["better"] == "hey!" and item["lesson"] == "keep it casual"
    assert item["context"] == ["Bob: how are you?"]
    event = item["events"][0]
    assert event["who"] == "Alice" and event["what"] == "correction" and event["counts"] is True
    assert event["reading"] == "a short fix"
    # One correction from the person it was for, past its fix window, with
    # nobody confirming it: the character decides it.
    stand = item["standing"]
    assert stand["stage"] == "deciding" and stand["missing"] == ""
    assert stand["events"] == 1 and stand["needEvents"] == 2
    assert item["actions"] == ["use", "set_aside"] and item["replaces"] == ""
    assert item["history"] == [] and item["decided"] is None


def test_the_master_switch_off_puts_nothing_into_use(client, workspace, ids):
    with workspace.env.open("a", encoding="utf-8") as handle:
        handle.write("PROMOTE_AUTO_ENABLED=false\n")
    item = client.get(f"/api/learned/item?id={ids['waiting']}", headers=HEADERS).json()
    assert item["standing"]["stage"] == "off" and item["standing"]["expires"] == 0


def test_decided_items_explain_who_and_why(client, ids):
    done = client.get(f"/api/learned/item?id={ids['undone']}", headers=HEADERS).json()
    assert [h["state"] for h in done["history"]] == ["promoted", "rolled_back"]
    assert done["history"][0]["by"] == "auto" and done["history"][0]["why"] == {"key": "agreed", "n": "2"}
    assert done["history"][1]["why"]["key"] == "disagreed"
    assert done["tab"] == "set_aside" and done["decided"] == {"by": "reactions", "why": ""}
    # What a rule or the character withdrew comes back; a person's own undo does not.
    assert done["actions"] == ["bring_back"] and done["standing"] is None
    gone = client.get(f"/api/learned/item?id={ids['discarded']}", headers=HEADERS).json()
    assert gone["history"][0]["by"] == "terminal" and gone["decided"]["by"] == "person"
    assert gone["history"][0]["why"] == {"key": "note", "n": "", "text": "too rude"}
    assert gone["actions"] == []
    live = client.get(f"/api/learned/item?id={ids['in_use']}", headers=HEADERS).json()
    assert live["actions"] == ["undo"] and live["decided"]["by"] == "reactions"


def test_item_refusals(client, ids):
    assert _error(client.get("/api/learned/item?id=nope", headers=HEADERS)) == "learned_unknown"
    assert _error(client.get("/api/learned/item?id=a/b", headers=HEADERS)) == "learned_invalid"
    assert _error(client.get("/api/learned/item", headers=HEADERS)) == "learned_invalid"


def test_use_undo_and_set_aside_write_the_ledger_and_views(client, workspace, ids):
    runtime = workspace.home / "runtime"
    kept = client.post("/api/learned/decide", headers=HEADERS,
                       json={"id": ids["waiting"], "action": "use"}).json()
    assert kept["tab"] == "in_use" and kept["history"][-1]["by"] == "page"
    assert kept["decided"]["by"] == "person"
    pairs = [json.loads(line) for line in (runtime / "promoted.feedback.en.jsonl").read_text(
        encoding="utf-8").splitlines()]
    assert ids["waiting"] in {p["candidate_id"] for p in pairs}
    undone = client.post("/api/learned/decide", headers=HEADERS,
                         json={"id": ids["waiting"], "action": "undo"}).json()
    # A person's undo is final from this page.
    assert undone["tab"] == "set_aside" and undone["state"] == "rolled_back" and undone["actions"] == []
    assert ids["waiting"] not in (runtime / "promoted.feedback.en.jsonl").read_text(encoding="utf-8")
    assert _error(client.post("/api/learned/decide", headers=HEADERS,
                              json={"id": ids["waiting"], "action": "use"})) == "learned_changed"
    gone = client.post("/api/learned/decide", headers=HEADERS,
                       json={"id": ids["rival_new"], "action": "set_aside"}).json()
    assert gone["tab"] == "set_aside" and gone["actions"] == [] and gone["decided"]["by"] == "person"
    assert _ledger(workspace).get(ids["rival_new"])["history"][-1]["actor"] == learned.ACTOR


def test_keep_replaces_the_rewrite_in_use(client, workspace, ids):
    item = client.get(f"/api/learned/item?id={ids['rival_new']}", headers=HEADERS).json()
    assert item["replaces"] == "hi"
    kept = client.post("/api/learned/decide", headers=HEADERS,
                       json={"id": ids["rival_new"], "action": "use"}).json()
    assert kept["tab"] == "in_use"
    old = client.get(f"/api/learned/item?id={ids['rival_live']}", headers=HEADERS).json()
    assert old["state"] == "superseded" and old["replacedBy"] == "yo" and old["actions"] == []
    assert client.get("/api/learned", headers=HEADERS).json()["totals"]["set_aside"] == 3


def test_decide_refusals(client, workspace, ids):
    post = lambda body: client.post("/api/learned/decide", headers=HEADERS, json=body)  # noqa: E731
    for old in ("promote", "keep", "discard"):
        assert _error(post({"id": ids["waiting"], "action": old})) == "learned_invalid"
    assert _error(post({"id": "../x", "action": "use"})) == "learned_invalid"
    assert _error(post({"id": "nope", "action": "use"})) == "learned_unknown"
    assert _error(post({"id": ids["discarded"], "action": "use"})) == "learned_changed"
    # A person's own discard is never brought back.
    assert _error(post({"id": ids["discarded"], "action": "bring_back"})) == "learned_changed"
    assert _error(post({"id": ids["in_use"], "action": "set_aside"})) == "learned_changed"
    assert _ledger(workspace).get(ids["discarded"])["state"] == candidates.STATE_REJECTED


def test_a_busy_lock_is_refused(client, workspace, ids, monkeypatch):
    class Held(learned.FileLock):
        def acquire(self):
            raise learned.LockUnavailable("held")

    monkeypatch.setattr(learned, "FileLock", Held)
    assert _error(client.post("/api/learned/decide", headers=HEADERS,
                              json={"id": ids["waiting"], "action": "use"})) == "learned_busy"
    assert _ledger(workspace).get(ids["waiting"])["state"] == candidates.STATE_PROPOSED


def test_a_running_character_decides_its_own_pool(client, workspace, ids, monkeypatch):
    calls = []

    async def call(method, path, **kwargs):
        calls.append((method, path, kwargs))
        return {"ok": True}

    monkeypatch.setattr(workspace.services, "running", lambda name: name == "agent")
    monkeypatch.setattr(workspace, "_activity_call", call)
    assert client.get("/api/learned", headers=HEADERS).json()["running"] is True
    response = client.post("/api/learned/decide", headers=HEADERS,
                           json={"id": ids["rival_new"], "action": "use"})
    assert response.status_code == 200
    assert calls == [("POST", f"/api/dashboard/candidates/{ids['rival_new']}/replace",
                      {"json": {"reason": "local page"}})]
    # The service writes; the page did not touch the files itself.
    assert _ledger(workspace).get(ids["rival_new"])["state"] == candidates.STATE_PROPOSED


def test_the_other_pool_is_decided_here_even_while_running(client, workspace, ids, monkeypatch):
    zh = _seed(workspace.home / "runtime", "zh")

    async def call(*args, **kwargs):
        raise AssertionError("the running character does not hold the other pool")

    monkeypatch.setattr(workspace.services, "running", lambda name: name == "agent")
    monkeypatch.setattr(workspace, "_activity_call", call)
    done = client.post("/api/learned/decide", headers=HEADERS,
                       json={"id": zh["in_use"], "action": "undo", "lang": "zh"}).json()
    assert done["state"] == "rolled_back" and done["lang"] == "zh"


@pytest.mark.parametrize("raised, code", [("activity_changed", "learned_changed"),
                                          ("activity_unavailable", "learned_unavailable")])
def test_running_character_refusals(client, workspace, ids, monkeypatch, raised, code):
    async def call(*args, **kwargs):
        raise ValueError(raised)

    monkeypatch.setattr(workspace.services, "running", lambda name: name == "agent")
    monkeypatch.setattr(workspace, "_activity_call", call)
    assert _error(client.post("/api/learned/decide", headers=HEADERS,
                              json={"id": ids["waiting"], "action": "use"})) == code


def test_activity_turned_off_falls_back_to_the_files(client, workspace, ids, monkeypatch):
    async def call(*args, **kwargs):
        return {"off": True}

    monkeypatch.setattr(workspace.services, "running", lambda name: name == "agent")
    monkeypatch.setattr(workspace, "_activity_call", call)
    done = client.post("/api/learned/decide", headers=HEADERS,
                       json={"id": ids["in_use"], "action": "undo"}).json()
    assert done["state"] == "rolled_back"


def _env_add(workspace, text):
    with workspace.env.open("a", encoding="utf-8") as handle:
        handle.write(text)


def test_everything_in_scope_by_default(client, ids):
    value = client.get("/api/learned", headers=HEADERS).json()
    assert value["idle"] == dict.fromkeys(learned.TABS, 0)
    assert all(row["gap"] == "" for row in value["items"])


@pytest.mark.parametrize("extra", ["PERSONA_VERSION=fresh-1\n", "PERSONA_NAME=Echo\n"])
def test_an_earlier_character_is_not_shown_as_in_use(client, workspace, ids, extra):
    _env_add(workspace, extra)
    value = client.get("/api/learned", headers=HEADERS).json()
    assert value["idle"]["in_use"] == 2 and value["idle"]["observing"] == 2 and value["chats"] == 0
    assert {row["gap"] for row in value["items"]} == {"persona"}
    item = client.get(f"/api/learned/item?id={ids['waiting']}", headers=HEADERS).json()
    assert item["gap"] == "persona" and item["actions"] == ["set_aside"]
    # Putting it into use would change nothing the character says, so it is refused, not faked.
    assert _error(client.post("/api/learned/decide", headers=HEADERS,
                              json={"id": ids["waiting"], "action": "use"})) == "learned_scope"
    assert _ledger(workspace).get(ids["waiting"])["state"] == candidates.STATE_PROPOSED
    done = client.post("/api/learned/decide", headers=HEADERS,
                       json={"id": ids["in_use"], "action": "undo"}).json()
    assert done["state"] == "rolled_back"


def test_a_lineage_from_another_document_is_another_character(client, workspace, ids):
    (workspace.home / "runtime" / "persona_lineage.json").write_text(
        json.dumps({"lineages": {"": ["0123456789ab"]}}), encoding="utf-8")
    rows = client.get("/api/learned", headers=HEADERS).json()["items"]
    assert {row["gap"] for row in rows} == {"persona"}


def test_the_other_language_can_still_be_put_into_use(client, workspace, ids):
    zh = _seed(workspace.home / "runtime", "zh")
    value = client.get("/api/learned?lang=zh&tab=observing", headers=HEADERS).json()
    assert {row["gap"] for row in value["items"]} == {"lang"}
    item = client.get(f"/api/learned/item?id={zh['waiting']}&lang=zh", headers=HEADERS).json()
    assert item["actions"] == ["use", "set_aside"] and item["gap"] == "lang"


def _page_item(workspace, conv, speaker):
    """A waiting rewrite taught twice in the page chat by its sender."""
    runtime = workspace.home / "runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    ledger = candidates.CandidateLedger(runtime / "candidate_ledger.en.jsonl")
    log = evidence.EvidenceLog(runtime / "evidence.en.jsonl")
    events = []
    for day in ("05", "06"):
        ev = evidence.make_event(
            kind=evidence.KIND_REACTION, ts=f"2026-11-{day}T10:00:00", lang="en", platform="browser",
            conv_id=conv, persona="Nova", speaker_id=speaker, speaker_name="you", recipient_id=speaker,
            reply="Salutations.", reaction_text=f"say hi ({day})", directed=True, direction="reply",
            reaction_type="correction", adjudication={"accept": True, "better": "hi", "reason": "shorter"})
        log.append(ev)
        events.append(ev)
    cand = candidates.make_candidate(
        ctype=candidates.TYPE_PAIR, scope=candidates.scope_from_event(events[0]),
        payload={"reply": "Salutations.", "better": "hi"},
        evidence=[e["event_id"] for e in events], created_at="2026-11-05T10:00:00")
    ledger.propose(cand)
    return cand["candidate_id"]


def test_the_page_chat_sender_counts_as_an_admin(client, workspace):
    _env_add(workspace, "PROMOTE_MIN_SPEAKERS=2\n")
    cid = _page_item(workspace, "dm:browser:ownerconv12", "browser:ownerconv12")
    url = f"/api/learned/item?id={cid}"
    stand = client.get(url, headers=HEADERS).json()["standing"]
    assert stand["stage"] == "reactions" and stand["missing"] == "speakers"
    (workspace.home / "runtime" / "page.owner").write_text("ownerconv12", encoding="utf-8")
    item = client.get(url, headers=HEADERS).json()
    assert item["gap"] == "" and item["standing"]["stage"] == "ready" and item["standing"]["speakersOk"]


def test_an_earlier_page_chat_is_not_in_use(client, workspace):
    cid = _page_item(workspace, "dm:browser:oldconv1234", "browser:oldconv1234")
    (workspace.home / "runtime" / "page.owner").write_text("newconv5678", encoding="utf-8")
    item = client.get(f"/api/learned/item?id={cid}", headers=HEADERS).json()
    assert item["gap"] == "chat" and item["actions"] == ["set_aside"]


def test_page_strings_cover_every_code(ids):
    import re
    from pathlib import Path
    script = (Path(learned.__file__).parents[1] / "static" / "welcome" / "panels" / "learned.js").read_text(
        encoding="utf-8")
    tables = re.split(r"\n  zh: \{", script.split("PA.strings(")[1].split("\n});")[0])
    keys = [set(re.findall(r"^\s+(learned_\w+):", part, re.M)) for part in tables]
    assert keys[0] == keys[1]
    for code in learned.ERRORS:
        assert code in keys[0]
    for gap in ("lang", "persona", "chat"):
        assert f"learned_gap_{gap}" in keys[0] and f"learned_why_scope_{gap}" in keys[0]
    for tab in learned.TABS:
        assert {f"learned_tab_{tab}", f"learned_hint_{tab}", f"learned_empty_{tab}"} <= keys[0]
    for state in candidates._ALLOWED_FROM:
        assert f"learned_h_{state}" in keys[0]
    for state in learned.TABS["set_aside"]:
        assert f"learned_now_{state}" in keys[0]
    for by in ("auto", "character", "person", "time", "rule"):
        assert f"learned_out_{by}" in keys[0]
    for rule in ("policy", "lesson", "blocked", "confirmed"):
        assert f"learned_r_rule_{rule}" in keys[0]
    # Every reaction type the evidence log can store has a label; anything else shows none.
    for what in evidence.REACTION_TYPES:
        assert f"learned_what_{what}" in keys[0]
    assert "KNOWN_WHAT" in script and 'what.startsWith("learned_")' not in script


def test_a_runtime_folder_outside_the_home_is_refused(client, workspace, tmp_path):
    with workspace.env.open("a", encoding="utf-8") as handle:
        handle.write(f"AGENT_RUNTIME_DIR={tmp_path.parent / 'elsewhere'}\n")
    assert _error(client.get("/api/learned", headers=HEADERS)) == "learned_unavailable"


def test_a_configured_runtime_folder_inside_the_home_is_used(client, workspace):
    _seed(workspace.home / "state")
    with workspace.env.open("a", encoding="utf-8") as handle:
        handle.write("AGENT_RUNTIME_DIR=state\n")
    assert client.get("/api/learned", headers=HEADERS).json()["totals"]["in_use"] == 2


# ------------------------------------------------- the character decides ----

def _approved(workspace, reply):
    """A reply two people approved: only the character can settle it."""
    from datetime import datetime, timedelta
    runtime = workspace.home / "runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    ledger, log = _ledger(workspace), evidence.EvidenceLog(runtime / "evidence.en.jsonl")
    now = datetime.now().replace(microsecond=0)
    events = []
    for n, uid in enumerate(("u1", "u2")):
        ev = _event(reply, "ha, love it", rtype="positive", speaker=uid, name=uid,
                    ts=(now - timedelta(hours=2 - n)).isoformat())
        log.append(ev)
        events.append(ev)
    cand = candidates.make_candidate(
        ctype=candidates.TYPE_EXAMPLE, scope=candidates.scope_from_event(events[0]),
        payload={"reply": reply}, evidence=[e["event_id"] for e in events],
        created_at=(now - timedelta(hours=3)).isoformat())
    ledger.propose(cand)
    return cand["candidate_id"], [e["event_id"] for e in events], events[-1]["ts"]


def test_an_item_only_the_character_can_settle_is_being_decided_then_observed(client, workspace):
    from persona_agent import promotion
    cid, seen, newest = _approved(workspace, "lol same")
    url = f"/api/learned/item?id={cid}"
    stand = client.get(url, headers=HEADERS).json()["standing"]
    assert stand["stage"] == "deciding" and stand["reason"] == ""
    # As learning._expire_observing: the newest reaction plus PROMOTE_OBSERVE_MAX_DAYS.
    assert stand["expires"] == promotion.epoch(newest) + 30 * 86400
    _ledger(workspace).review(cid, ts="2026-11-10T10:00:00", reason="One more voice would settle it.",
                              seen=seen, judge="adoption-judge/1")
    stand = client.get(url, headers=HEADERS).json()["standing"]
    assert stand["stage"] == "observing" and stand["reason"] == "One more voice would settle it."
    history = client.get(url, headers=HEADERS).json()["history"]
    assert history[-1]["state"] == "review" and history[-1]["by"] == "character"
    # New evidence: the character looks again.
    log = evidence.EvidenceLog(workspace.home / "runtime" / "evidence.en.jsonl")
    fresh = _event("lol same", "so true", rtype="positive", speaker="u3", name="u3")
    log.append(fresh)
    _ledger(workspace).link_evidence(cid, [fresh["event_id"]], ts="2026-11-10T11:00:00")
    assert client.get(url, headers=HEADERS).json()["standing"]["stage"] == "deciding"
    _env_add(workspace, "PROMOTE_JUDGE_ENABLED=false\n")
    stand = client.get(url, headers=HEADERS).json()["standing"]
    # Nobody decides it and nothing sets it aside; still nobody is asked.
    assert stand["stage"] == "held" and stand["expires"] == 0
    _env_add(workspace, "PROMOTE_JUDGE_ENABLED=true\nPROMOTE_OBSERVE_MAX_DAYS=0\n")
    assert client.get(url, headers=HEADERS).json()["standing"]["expires"] == 0


def test_what_the_character_decided_says_so_and_why(client, workspace):
    adopted, _, _ = _approved(workspace, "fair point")
    dropped, _, _ = _approved(workspace, "whatever")
    ledger = _ledger(workspace)
    ledger.promote(adopted, ts="2026-11-10T10:00:00", actor="character",
                   reason="It matches how I talk.", judge="adoption-judge/1")
    ledger.reject(dropped, ts="2026-11-10T10:00:00", actor="character",
                  reason="It reads as dismissive.", judge="adoption-judge/1")
    used = client.get(f"/api/learned/item?id={adopted}", headers=HEADERS).json()
    assert used["decided"] == {"by": "character", "why": "It matches how I talk."}
    assert used["history"][-1]["by"] == "character"
    assert used["history"][-1]["why"] == {"key": "said", "n": "", "text": "It matches how I talk."}
    aside = client.get(f"/api/learned/item?id={dropped}", headers=HEADERS).json()
    assert aside["decided"]["by"] == "character" and aside["actions"] == ["bring_back"]


def test_bring_back_follows_the_ledger_and_writes_a_person(client, workspace):
    cid, _, _ = _approved(workspace, "whatever")
    _ledger(workspace).reject(cid, ts="2026-11-10T10:00:00", actor="character",
                              reason="It reads as dismissive.")
    back = client.post("/api/learned/decide", headers=HEADERS,
                       json={"id": cid, "action": "bring_back"}).json()
    assert back["tab"] == "in_use" and back["decided"]["by"] == "person"
    last = _ledger(workspace).get(cid)["history"][-1]
    assert last["state"] == "promoted" and last["actor"] == learned.ACTOR
    rows = (workspace.home / "runtime" / "promoted.examples.en.jsonl").read_text(encoding="utf-8")
    assert "whatever" in rows


def test_the_time_limit_says_so_and_is_brought_back_exactly_when_the_ledger_allows(client, workspace):
    from persona_agent import learning
    cid, _, _ = _approved(workspace, "sure thing")
    _ledger(workspace).reject(cid, ts="2026-11-10T10:00:00", actor="auto",
                              reason=learning.REASON_EXPIRED.format(days="30"),
                              judge=getattr(candidates, "JUDGE_EXPIRY", learning.RULES_VERSION))
    item = client.get(f"/api/learned/item?id={cid}", headers=HEADERS).json()
    assert item["decided"] == {"by": "time", "why": "", "days": "30"}
    assert item["history"][-1]["by"] == "time" and item["history"][-1]["why"] == {"key": "expired", "n": "30"}
    assert ("bring_back" in item["actions"]) == candidates.restorable(_ledger(workspace).get(cid))


def test_a_rule_says_which_rule(client, workspace):
    from persona_agent import learning
    cid, _, _ = _approved(workspace, "you idiot")
    _ledger(workspace).reject(cid, ts="2026-11-10T10:00:00", actor="auto",
                              reason=learning.REASON_POLICY, judge=learning.RULES_VERSION)
    item = client.get(f"/api/learned/item?id={cid}", headers=HEADERS).json()
    assert item["decided"] == {"by": "rule", "why": "policy"} and item["actions"] == []
    assert item["history"][-1]["why"]["key"] == "rule_policy"
