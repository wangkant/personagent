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
    assert client.post("/api/learned/decide", json={"id": ids["waiting"], "action": "keep"}).status_code == 403


def test_overview_works_with_the_character_stopped(client, ids):
    value = client.get("/api/learned", headers=HEADERS).json()
    assert value["running"] is False and value["lang"] == "en"
    assert value["totals"] == {"in_use": 2, "waiting": 2, "discarded": 1, "undone": 1, "replaced": 0}
    assert value["chats"] == 1 and value["tab"] == "in_use" and value["count"] == 2
    assert {row["id"] for row in value["items"]} == {ids["in_use"], ids["rival_live"]}
    row = next(r for r in value["items"] if r["id"] == ids["in_use"])
    assert row["chat"]["platform"] == "telegram" and row["chat"]["kind"] == "group"
    assert row["chat"]["tail"] == "…456789" and row["kind"] == "repeat" and row["when"] > 0
    waiting = client.get("/api/learned?tab=waiting&limit=1", headers=HEADERS).json()
    assert waiting["count"] == 2 and len(waiting["items"]) == 1
    assert _error(client.get("/api/learned?tab=bogus", headers=HEADERS)) == "learned_invalid"
    assert _error(client.get("/api/learned?lang=../x", headers=HEADERS)) == "learned_invalid"


def test_nothing_secret_or_persona_internal_leaves(client, ids):
    for response in (client.get("/api/learned?tab=waiting", headers=HEADERS),
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
    other = client.get("/api/learned?lang=zh&tab=waiting", headers=HEADERS).json()
    assert other["lang"] == "zh" and other["current"] == "en"
    assert client.get(f"/api/learned/item?id={zh['waiting']}&lang=zh", headers=HEADERS).status_code == 200


def test_one_item_in_full_says_why_it_waits(client, ids):
    item = client.get(f"/api/learned/item?id={ids['waiting']}", headers=HEADERS).json()
    assert item["tab"] == "waiting" and item["kind"] == "wording"
    assert item["better"] == "hey!" and item["lesson"] == "keep it casual"
    assert item["context"] == ["Bob: how are you?"]
    event = item["events"][0]
    assert event["who"] == "Alice" and event["what"] == "correction" and event["counts"] is True
    assert event["reading"] == "a short fix"
    # One correction: the policy needs two agreeing reactions.
    assert item["waiting"]["key"] == "events"
    assert item["waiting"]["events"] == 1 and item["waiting"]["needEvents"] == 2
    assert item["actions"] == ["keep", "discard"] and item["replaces"] == ""
    assert item["history"] == []


def test_waiting_reason_follows_the_auto_apply_switch(client, workspace, ids):
    with workspace.env.open("a", encoding="utf-8") as handle:
        handle.write("PROMOTE_AUTO_ENABLED=false\n")
    item = client.get(f"/api/learned/item?id={ids['waiting']}", headers=HEADERS).json()
    assert item["waiting"]["key"] == "off" and item["waiting"]["auto"] is False


def test_decided_items_explain_who_and_why(client, ids):
    done = client.get(f"/api/learned/item?id={ids['undone']}", headers=HEADERS).json()
    assert [h["tab"] for h in done["history"]] == ["in_use", "undone"]
    assert done["history"][0]["by"] == "auto" and done["history"][0]["why"] == {"key": "agreed", "n": "2"}
    assert done["history"][1]["why"]["key"] == "disagreed"
    assert done["actions"] == ["keep", "discard"] and done["waiting"] is None
    gone = client.get(f"/api/learned/item?id={ids['discarded']}", headers=HEADERS).json()
    assert gone["history"][0]["by"] == "terminal"
    assert gone["history"][0]["why"] == {"key": "note", "n": "", "text": "too rude"}
    assert gone["actions"] == []
    live = client.get(f"/api/learned/item?id={ids['in_use']}", headers=HEADERS).json()
    assert live["actions"] == ["undo"]


def test_item_refusals(client, ids):
    assert _error(client.get("/api/learned/item?id=nope", headers=HEADERS)) == "learned_unknown"
    assert _error(client.get("/api/learned/item?id=a/b", headers=HEADERS)) == "learned_invalid"
    assert _error(client.get("/api/learned/item", headers=HEADERS)) == "learned_invalid"


def test_keep_discard_undo_and_bring_back_write_the_ledger_and_views(client, workspace, ids):
    runtime = workspace.home / "runtime"
    kept = client.post("/api/learned/decide", headers=HEADERS,
                       json={"id": ids["waiting"], "action": "keep"}).json()
    assert kept["tab"] == "in_use" and kept["history"][-1]["by"] == "page"
    pairs = [json.loads(line) for line in (runtime / "promoted.feedback.en.jsonl").read_text(
        encoding="utf-8").splitlines()]
    assert ids["waiting"] in {p["candidate_id"] for p in pairs}
    undone = client.post("/api/learned/decide", headers=HEADERS,
                         json={"id": ids["waiting"], "action": "undo"}).json()
    assert undone["tab"] == "undone" and undone["actions"] == ["keep", "discard"]
    assert ids["waiting"] not in (runtime / "promoted.feedback.en.jsonl").read_text(encoding="utf-8")
    back = client.post("/api/learned/decide", headers=HEADERS,
                       json={"id": ids["waiting"], "action": "keep"}).json()
    assert back["tab"] == "in_use"
    gone = client.post("/api/learned/decide", headers=HEADERS,
                       json={"id": ids["undone"], "action": "discard"}).json()
    assert gone["tab"] == "discarded" and gone["actions"] == []
    assert _ledger(workspace).get(ids["undone"])["state"] == candidates.STATE_REJECTED


def test_keep_replaces_the_rewrite_in_use(client, workspace, ids):
    item = client.get(f"/api/learned/item?id={ids['rival_new']}", headers=HEADERS).json()
    assert item["replaces"] == "hi"
    kept = client.post("/api/learned/decide", headers=HEADERS,
                       json={"id": ids["rival_new"], "action": "keep"}).json()
    assert kept["tab"] == "in_use"
    old = client.get(f"/api/learned/item?id={ids['rival_live']}", headers=HEADERS).json()
    assert old["tab"] == "replaced" and old["replacedBy"] == "yo" and old["actions"] == []
    assert client.get("/api/learned", headers=HEADERS).json()["totals"]["replaced"] == 1


def test_decide_refusals(client, workspace, ids):
    post = lambda body: client.post("/api/learned/decide", headers=HEADERS, json=body)  # noqa: E731
    assert _error(post({"id": ids["waiting"], "action": "promote"})) == "learned_invalid"
    assert _error(post({"id": "../x", "action": "keep"})) == "learned_invalid"
    assert _error(post({"id": "nope", "action": "keep"})) == "learned_unknown"
    assert _error(post({"id": ids["discarded"], "action": "keep"})) == "learned_changed"
    assert _error(post({"id": ids["in_use"], "action": "discard"})) == "learned_changed"
    assert _ledger(workspace).get(ids["discarded"])["state"] == candidates.STATE_REJECTED


def test_a_busy_lock_is_refused(client, workspace, ids, monkeypatch):
    class Held(learned.FileLock):
        def acquire(self):
            raise learned.LockUnavailable("held")

    monkeypatch.setattr(learned, "FileLock", Held)
    assert _error(client.post("/api/learned/decide", headers=HEADERS,
                              json={"id": ids["waiting"], "action": "keep"})) == "learned_busy"
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
                           json={"id": ids["rival_new"], "action": "keep"})
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
    assert done["tab"] == "undone" and done["lang"] == "zh"


@pytest.mark.parametrize("raised, code", [("activity_changed", "learned_changed"),
                                          ("activity_unavailable", "learned_unavailable")])
def test_running_character_refusals(client, workspace, ids, monkeypatch, raised, code):
    async def call(*args, **kwargs):
        raise ValueError(raised)

    monkeypatch.setattr(workspace.services, "running", lambda name: name == "agent")
    monkeypatch.setattr(workspace, "_activity_call", call)
    assert _error(client.post("/api/learned/decide", headers=HEADERS,
                              json={"id": ids["waiting"], "action": "keep"})) == code


def test_activity_turned_off_falls_back_to_the_files(client, workspace, ids, monkeypatch):
    async def call(*args, **kwargs):
        return {"off": True}

    monkeypatch.setattr(workspace.services, "running", lambda name: name == "agent")
    monkeypatch.setattr(workspace, "_activity_call", call)
    done = client.post("/api/learned/decide", headers=HEADERS,
                       json={"id": ids["in_use"], "action": "undo"}).json()
    assert done["tab"] == "undone"


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
    assert value["idle"]["in_use"] == 2 and value["idle"]["waiting"] == 2 and value["chats"] == 0
    assert {row["gap"] for row in value["items"]} == {"persona"}
    item = client.get(f"/api/learned/item?id={ids['waiting']}", headers=HEADERS).json()
    assert item["waiting"]["key"] == "scope" and item["actions"] == ["discard"]
    assert client.get(f"/api/learned/item?id={ids['undone']}", headers=HEADERS).json()["actions"] == ["discard"]
    # Keep would change nothing the character says, so it is refused, not faked.
    assert _error(client.post("/api/learned/decide", headers=HEADERS,
                              json={"id": ids["waiting"], "action": "keep"})) == "learned_scope"
    assert _ledger(workspace).get(ids["waiting"])["state"] == candidates.STATE_PROPOSED
    done = client.post("/api/learned/decide", headers=HEADERS,
                       json={"id": ids["in_use"], "action": "undo"}).json()
    assert done["tab"] == "undone"


def test_a_lineage_from_another_document_is_another_character(client, workspace, ids):
    (workspace.home / "runtime" / "persona_lineage.json").write_text(
        json.dumps({"lineages": {"": ["0123456789ab"]}}), encoding="utf-8")
    rows = client.get("/api/learned", headers=HEADERS).json()["items"]
    assert {row["gap"] for row in rows} == {"persona"}


def test_the_other_language_can_still_be_kept(client, workspace, ids):
    zh = _seed(workspace.home / "runtime", "zh")
    value = client.get("/api/learned?lang=zh&tab=waiting", headers=HEADERS).json()
    assert {row["gap"] for row in value["items"]} == {"lang"}
    item = client.get(f"/api/learned/item?id={zh['waiting']}&lang=zh", headers=HEADERS).json()
    assert item["actions"] == ["keep", "discard"] and item["waiting"]["key"] == "scope"


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
    assert client.get(url, headers=HEADERS).json()["waiting"]["key"] == "speakers"
    (workspace.home / "runtime" / "page.owner").write_text("ownerconv12", encoding="utf-8")
    item = client.get(url, headers=HEADERS).json()
    assert item["gap"] == "" and item["waiting"]["key"] == "ready" and item["waiting"]["speakersOk"]


def test_an_earlier_page_chat_is_not_in_use(client, workspace):
    cid = _page_item(workspace, "dm:browser:oldconv1234", "browser:oldconv1234")
    (workspace.home / "runtime" / "page.owner").write_text("newconv5678", encoding="utf-8")
    item = client.get(f"/api/learned/item?id={cid}", headers=HEADERS).json()
    assert item["gap"] == "chat" and item["actions"] == ["discard"] and item["waiting"]["key"] == "scope"


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
