"""The practice panel: the scripted demo and the practice group, with the
child process stood in for; the child's own side runs on the scripted model."""
from __future__ import annotations

import io
import itertools
import json
import queue
import re
import subprocess
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from persona_agent import chat, demo, paths, welcome
from persona_agent.panels import practice
from persona_agent.textproc import TextProcessing

PANELS = Path(practice.__file__).parents[1] / "static" / "welcome" / "panels"
JS = (PANELS / "practice.js").read_text(encoding="utf-8")
CSS = (PANELS / "practice.css").read_text(encoding="utf-8")
TOKEN = "test-local-capability"
HEADERS = {welcome.TOKEN_HEADER: TOKEN}
KEY = "sk-practice-secret-0123456789"


class FakeChild:
    """A stand-in for the trial child: answers each request line with `answer(req)`."""

    made: list["FakeChild"] = []

    def __init__(self, argv, *, answer, ready=None, **options) -> None:
        self.argv, self.options, self.answer = argv, options, answer
        self.requests: list[dict] = []
        self.lines: queue.Queue = queue.Queue()
        self.stdout = iter(self.lines.get, None)
        self.stdin = self
        self.returncode = None
        self.lines.put(json.dumps(ready or {"ready": True, "name": "Nova"}).encode() + b"\n")
        FakeChild.made.append(self)

    def write(self, data: bytes) -> None:
        request = json.loads(data)
        self.requests.append(request)
        reply = self.answer(request)
        if reply == "die":
            self.close()
        elif reply is not None:
            self.lines.put(json.dumps(reply).encode() + b"\n")

    def flush(self) -> None:
        pass

    def close(self) -> None:
        if self.returncode is None:
            self.returncode = 0
            self.lines.put(None)

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        return self.returncode

    def kill(self) -> None:
        self.close()


def answers(request: dict):
    op = request.get("op")
    if op == "say":
        named = "nova" in request["text"].lower()
        return {"turn": len(FakeChild.made[-1].requests), "speaker": request["name"] or "admin",
                "what": "named" if named else "quiet", "reply": "hi there" if named else "",
                "mid": "trial-1" if named else "", "reason": "" if named else "not addressed, 1 of 4 messages",
                "learning": "judged: rejection" if request.get("quote") else "", "retry": False,
                "memory": "", "failure": ""}
    if op == "why":
        return {"what": "named", "speaker": "Alex", "text": "Nova?", "reply": "hi there", "reason": "",
                "retryOf": "", "learning": "", "offered": [], "ledger": [], "candidates": []}
    if op == "learned":
        return {"summary": "0 memories", "items": []}
    if op == "texts":
        return {"texts": {str(n): {"reason": f"{request['lang']}: not addressed", "learning": ""}
                          for n in request["turns"]}}
    if op == "reset":
        return {"ok": True}
    return {"error": "practice_invalid"}


@pytest.fixture
def child(monkeypatch):
    FakeChild.made = []
    behaviour = {"answer": answers, "ready": None}

    def popen(argv, **options):
        options.pop("stdin"), options.pop("stdout"), options.pop("stderr")
        return FakeChild(argv, answer=behaviour["answer"], ready=behaviour["ready"], **options)
    monkeypatch.setattr(practice.subprocess, "Popen", popen)
    return behaviour


@pytest.fixture
def workspace(tmp_path):
    (tmp_path / ".env").write_text(f"LLM_API_KEY={KEY}\nLLM_MODEL=fake\nAGENT_LANG=en\n", encoding="utf-8")
    value = welcome.Workspace(tmp_path)
    yield value
    value.close()


@pytest.fixture
def client(workspace, child):
    app = welcome.create_app(workspace.home, TOKEN, workspace=workspace)
    with TestClient(app, base_url="http://127.0.0.1") as value:
        yield value
        app.state.practice.stop()


def post(client, path: str, payload: dict | None = None):
    return client.post(f"/api/practice/{path}", json=payload or {}, headers=HEADERS)


def view(client) -> dict:
    return client.app.state.practice.view()


def test_every_route_needs_the_local_token(client):
    for path in ("start", "say", "why", "learned", "reset", "demo"):
        assert client.post(f"/api/practice/{path}", json={}).status_code == 403
    assert client.get("/assets/panels/practice.js").status_code == 200


def test_the_page_reads_the_group_only_through_start(client):
    # start returns the transcript, so no second route duplicates it.
    paths_ = {getattr(route, "path", "") for route in client.app.routes}
    assert "/api/practice/state" not in paths_
    assert "practice/state" not in JS


def test_start_runs_the_trial_child_on_this_home(client, workspace):
    assert view(client) == {"running": False, "name": "", "entries": []}
    started = post(client, "start").json()
    assert started == {"running": True, "name": "Nova", "entries": []}
    made = FakeChild.made[-1]
    assert made.argv[1:] == ["-m", "persona_agent.panels.practice", "trial"]
    assert made.options["env"]["AGENT_HOME"] == str(workspace.home)
    # Starting again reuses the running child.
    post(client, "start")
    assert len(FakeChild.made) == 1


def test_start_without_a_key_is_refused(client, workspace):
    (workspace.home / ".env").write_text("LLM_MODEL=fake\n", encoding="utf-8")
    response = post(client, "start")
    assert response.status_code == 400 and response.json() == {"error": "practice_needs_key"}
    assert FakeChild.made == []


def test_a_child_that_cannot_build_the_character_fails_plainly(client, child):
    child["ready"] = {"error": "practice_failed"}
    response = post(client, "start")
    assert response.json() == {"error": "practice_failed"}


def test_say_keeps_a_transcript_with_reasons_and_replies(client):
    quiet = post(client, "say", {"as": "member", "name": "Alex", "text": "anyone around?"}).json()
    assert [e["kind"] for e in quiet["entries"]] == ["said"]
    assert quiet["entries"][0]["what"] == "quiet"
    assert quiet["entries"][0]["reason"] == "not addressed, 1 of 4 messages"
    named = post(client, "say", {"as": "member", "name": "Sam", "text": "Nova, film tonight?"}).json()
    said, reply = named["entries"]
    assert said["name"] == "Sam" and reply == {"id": reply["id"], "kind": "reply", "text": "hi there",
                                                "after": said["id"], "retry": False, "quotable": True}
    requests = FakeChild.made[-1].requests
    # Each member keeps one account; a new name gets the next.
    assert (requests[0]["uid"], requests[1]["uid"]) == ("3001", "3002")
    assert [e["id"] for e in view(client)["entries"]] == [quiet["entries"][0]["id"], said["id"], reply["id"]]


def test_start_says_earlier_reasons_again_in_a_new_language(client):
    post(client, "say", {"as": "member", "name": "Alex", "text": "anyone?", "lang": "en"})
    post(client, "say", {"as": "member", "name": "Sam", "text": "Nova, hi", "lang": "en"})
    child = FakeChild.made[-1]
    entries = post(client, "start", {"lang": "zh"}).json()["entries"]
    asked = child.requests[-1]
    # Only the said lines are said again; the child still knows both turns.
    assert asked == {"op": "texts", "lang": "zh", "turns": [1, 2]}
    said = [e for e in entries if e["kind"] == "said"]
    assert [e["reason"] for e in said] == ["zh: not addressed"] * 2
    assert {e["lang"] for e in said} == {"zh"}
    count = len(child.requests)
    post(client, "start", {"lang": "zh"})
    assert len(child.requests) == count


def test_the_owner_and_a_reply_reach_the_child(client):
    first = post(client, "say", {"as": "member", "name": "Alex", "text": "Nova, hi"}).json()
    reply = first["entries"][1]
    second = post(client, "say", {"as": "owner", "text": "no, shorter", "quote": reply["id"]}).json()
    request = FakeChild.made[-1].requests[-1]
    assert request["owner"] is True and request["quote"] == "trial-1"
    assert second["entries"][0]["quote"] == "hi there"
    assert second["entries"][0]["learning"] == "judged: rejection"


@pytest.mark.parametrize("payload", [
    {"as": "member", "name": "Alex", "text": "   "},
    {"as": "member", "name": "Alex", "text": "x" * 2001},
    {"as": "member", "name": "", "text": "hello"},
    {"as": "member", "name": "N" * 17, "text": "hello"},
    {"as": "member", "name": "bad\x07name", "text": "hello"},
])
def test_say_refuses_bad_messages(client, payload):
    response = post(client, "say", payload)
    assert response.status_code == 400 and response.json() == {"error": "practice_invalid"}


def test_a_reply_to_an_unknown_line_is_gone(client):
    response = post(client, "say", {"as": "owner", "text": "hi", "quote": "e99"})
    assert response.json() == {"error": "practice_gone"}


def test_one_message_at_a_time(client):
    lock = client.app.state.practice.lock
    lock.acquire()
    try:
        response = post(client, "say", {"as": "owner", "text": "hello"})
    finally:
        lock.release()
    assert response.json() == {"error": "practice_busy"}


def test_why_reads_the_childs_decision(client):
    entry = post(client, "say", {"as": "member", "name": "Alex", "text": "Nova?"}).json()["entries"][1]
    why = post(client, "why", {"id": entry["id"], "lang": "zh"}).json()
    assert why["what"] == "named" and why["reply"] == "hi there"
    request = FakeChild.made[-1].requests[-1]
    assert request == {"op": "why", "lang": "zh", "turn": 1}
    assert post(client, "why", {"id": "e404"}).json() == {"error": "practice_gone"}


def test_learned_and_start_over(client):
    post(client, "say", {"as": "member", "name": "Alex", "text": "Nova?"})
    assert post(client, "learned", {"lang": "en"}).json() == {"summary": "0 memories", "items": []}
    cleared = post(client, "reset").json()
    assert cleared["entries"] == [] and FakeChild.made[-1].requests[-1] == {"op": "reset"}
    assert view(client)["entries"] == []


def test_a_child_that_dies_is_reported_and_started_again(client, child):
    child["answer"] = lambda request: "die"
    assert post(client, "say", {"as": "owner", "text": "hi"}).json() == {"error": "practice_failed"}
    assert view(client)["running"] is False
    child["answer"] = answers
    assert post(client, "start").json()["running"] is True
    assert len(FakeChild.made) == 2


def test_a_child_that_never_answers_times_out(client, child, monkeypatch):
    monkeypatch.setattr(practice, "TURN_TIMEOUT", 0.2)
    child["answer"] = lambda request: None
    assert post(client, "say", {"as": "owner", "text": "hi"}).json() == {"error": "practice_timeout"}
    assert FakeChild.made[-1].returncode is not None


def test_new_settings_build_the_character_again(client, workspace):
    post(client, "start")
    env = workspace.home / ".env"
    env.write_text(env.read_text(encoding="utf-8") + "PERSONA_NAME=Mia\n", encoding="utf-8")
    practice_ = client.app.state.practice
    practice_.stamp -= 1  # the file system's clock may not have moved
    post(client, "start")
    assert len(FakeChild.made) == 2 and FakeChild.made[0].returncode is not None


def test_nothing_secret_comes_back(client):
    bodies = [post(client, "start").text,
              post(client, "say", {"as": "member", "name": "Alex", "text": "Nova?"}).text,
              post(client, "learned").text, post(client, "reset").text]
    assert not any(KEY in body for body in bodies)


# ---- the demo -------------------------------------------------------------

def scripted_demo(tmp_path: Path, monkeypatch, lang: str = "en") -> bytes:
    monkeypatch.setattr(paths, "ROOT", tmp_path)
    out = io.StringIO()
    assert practice._demo(lang, out) == 0
    return out.getvalue().encode()


def test_the_demo_child_plays_three_scenes_as_beats(tmp_path, monkeypatch):
    monkeypatch.setattr(TextProcessing, "_is_sleep_hour", staticmethod(lambda: False))
    beats = [json.loads(line) for line in scripted_demo(tmp_path, monkeypatch).decode().splitlines()]
    scenes = [b for b in beats if b["kind"] == "scene"]
    assert [s["key"] for s in scenes] == ["quiet", "teach", "troll"]
    assert scenes[0]["title"].startswith("quiet") and "\n" not in scenes[0]["intro"]
    kinds = {b["kind"] for b in beats}
    assert {"say", "bot", "note", "info", "check"} <= kinds
    notes = [b["text"] for b in beats if b["kind"] == "note"]
    assert "not addressed, 1 of 4 messages" in notes[0] and not notes[0].startswith("(")
    assert any("second try" in n for n in notes)
    # Nothing outlives the scenes.
    assert not any((tmp_path / "runtime" / "desktop").iterdir())


def test_the_demo_route_serves_and_keeps_the_scenes(client, tmp_path, monkeypatch):
    monkeypatch.setattr(TextProcessing, "_is_sleep_hour", staticmethod(lambda: False))
    output = scripted_demo(tmp_path / "scratch", monkeypatch)
    runs = []

    def run(argv, **options):
        runs.append((argv, options))
        return subprocess.CompletedProcess(argv, 0, stdout=output)
    monkeypatch.setattr(practice.subprocess, "run", run)
    scenes = post(client, "demo", {"lang": "en"}).json()["scenes"]
    assert [s["key"] for s in scenes] == ["quiet", "teach", "troll"]
    assert scenes[1]["beats"][0]["kind"] == "info"
    assert runs[0][0][-3:] == ["demo", "--lang", "en"]
    post(client, "demo", {"lang": "en"})
    assert len(runs) == 1
    post(client, "demo", {"lang": "nonsense"})
    assert len(runs) == 1


@pytest.mark.parametrize("outcome", ["exit", "timeout", "short"])
def test_a_demo_that_cannot_play_says_so(client, monkeypatch, outcome):
    def run(argv, **options):
        if outcome == "timeout":
            raise subprocess.TimeoutExpired(argv, 1)
        if outcome == "exit":
            return subprocess.CompletedProcess(argv, 1, stdout=b"")
        return subprocess.CompletedProcess(argv, 0, stdout=b'{"kind": "scene", "key": "quiet"}\nnot json\n')
    monkeypatch.setattr(practice.subprocess, "run", run)
    response = post(client, "demo", {"lang": "zh"})
    assert response.status_code == 400 and response.json() == {"error": "practice_demo_failed"}


# ---- the trial child --------------------------------------------------------

VENTING = demo._verdict("rejection", True, "Alex was venting", better="ugh, again?",
                        scenario="venting")


async def test_the_trial_child_answers_say_why_learned_and_reset(tmp, monkeypatch):
    monkeypatch.setattr(TextProcessing, "_is_sleep_hour", staticmethod(lambda: False))
    with demo.throwaway_home(str(tmp)) as root:
        agent, model = demo.build_agent("en", root, offline=True)
        session = object.__new__(practice._Trial)
        session.chat = chat
        session.trial = chat.Trial(agent, conv="g1",
                                   factory=lambda: demo.build_agent("en", root, offline=True)[0])
        session.turns, session.count = {}, itertools.count(1)
        try:
            quiet = await session.handle({"op": "say", "lang": "en", "name": "Sam", "uid": "3001",
                                          "text": "anyone around?"})
            assert (quiet["what"], quiet["reply"], quiet["reason"]) == (
                "quiet", "", "not addressed, 1 of 4 messages")
            model.load(demo.Beat("alex", "x", reply="did you check the logs?"))
            named = await session.handle({"op": "say", "lang": "en", "name": "Alex", "uid": "3002",
                                          "text": "Nova, the deploy failed"})
            assert named["what"] == "named" and named["reply"] == "did you check the logs?"
            assert named["mid"]
            model.load(demo.Beat("alex", "x", reply="fair, rough day", verdict=VENTING))
            taught = await session.handle({"op": "say", "lang": "en", "name": "Alex", "uid": "3002",
                                           "text": "I was just venting", "quote": named["mid"]})
            assert taught["learning"].startswith("judged: rejection, accepted")
            why = await session.handle({"op": "why", "lang": "en", "turn": named["turn"]})
            assert why["what"] == "named" and why["ledger"][0]["who"] == "Alex"
            why_zh = await session.handle({"op": "why", "lang": "zh", "turn": quiet["turn"]})
            assert why_zh["what"] == "quiet" and "1/4" in why_zh["reason"]
            texts = (await session.handle({"op": "texts", "lang": "zh",
                                           "turns": [quiet["turn"], taught["turn"], 99]}))["texts"]
            assert set(texts) == {str(quiet["turn"]), str(taught["turn"])}
            assert texts[str(quiet["turn"])]["reason"] == why_zh["reason"]
            assert texts[str(taught["turn"])]["learning"].startswith("判定")
            assert await session.handle({"op": "why", "turn": 99}) == {"error": "practice_gone"}
            learned = await session.handle({"op": "learned", "lang": "en"})
            assert learned["summary"] and isinstance(learned["items"], list)
            assert await session.handle({"op": "nope"}) == {"error": "practice_invalid"}
            assert await session.handle({"op": "reset"}) == {"ok": True}
            assert session.turns == {}
        finally:
            await session.trial.agent.aclose()


def test_the_trial_child_without_a_key_says_so(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENT_HOME", str(tmp_path))
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    out = io.StringIO()
    assert practice._trial(out) == 1
    assert json.loads(out.getvalue()) == {"error": "practice_needs_key"}


@pytest.mark.parametrize("gate, key", [("person", "practice_held_character"),
                                       ("against", "practice_held_character"),
                                       ("conflict", "practice_held_character"),
                                       ("events", "")])
def test_an_item_the_character_decides_never_says_the_admin_approves(gate, key):
    from types import SimpleNamespace
    from persona_agent import promotion
    check = SimpleNamespace(decision=promotion.Decision(False, "", gate=gate))
    fake = SimpleNamespace(chat=SimpleNamespace(checklist=lambda agent, cand: check,
                                                held_reason=lambda lang, c: "1/2 compatible events"),
                           agent=None)
    found = practice._Trial._held(fake, "ja", {})
    assert found == (key, "" if key else "1/2 compatible events")
    assert "admin" not in JS.split("practice_held_character")[1].split("\n")[0]


def tables() -> dict[str, dict[str, str]]:
    found = re.findall(r"\n  (en|zh): \{\n(.*?)\n  \},", JS, re.S)
    return {code: dict(re.findall(r'^    (practice_\w+): "(.*)",$', body, re.M)) for code, body in found}


def test_page_strings_match_in_both_languages():
    keys = {code: list(table) for code, table in tables().items()}
    assert keys["en"] and keys["en"] == keys["zh"]
    code = JS.split("PA.strings")[1].split("});", 1)[1]
    used = set(re.findall(r'"(practice_[a-z_0-9]+)"', code))
    assert used <= set(keys["en"]), used - set(keys["en"])
    assert practice.ERRORS <= set(keys["en"])
    assert {f"practice_fail_{kind}" for kind in practice.FAILURES} <= set(keys["en"])


def test_page_strings_use_the_pages_names_and_register():
    en, zh = tables()["en"], tables()["zh"]
    # The settings view goes by its full name, as the rest of the page calls it.
    assert en["practice_open_settings"] == "Open Character & settings"
    assert zh["practice_open_settings"] == "打开「角色与设置」"
    for key in ("practice_needs_key", "practice_fail_auth", "practice_fail_request",
                "practice_fail_unreachable", "practice_fail_other", "practice_failed"):
        assert "Character & settings" in en[key] and "「角色与设置」" in zh[key], key
    for text in en.values():
        assert not re.search(r"\b(owner|Settings)\b|n't|'re|'s\b", text.replace("character's", "")), text
    for text in zh.values():
        assert not re.search(r"主人|您|应用|去设置|假的|捣乱|从头再来|吧|呢|啦|哦|不吭声", text), text
    # The confirmation names everything a reset deletes.
    for word in ("消息", "学到的内容", "记忆"):
        assert word in zh["practice_reset_ask"]
    for word in ("messages", "learned", "memories"):
        assert word in en["practice_reset_ask"]


def test_page_controls_keep_focus_and_announce_results():
    code = JS.split("PA.strings")[1].split("});", 1)[1]
    # Every control made by button() is given an id.
    assert not re.search(r'button\("[^"]*", "[^"]*"\)', code)
    assert re.search(r"if \(focused\) PA\.\$\(focused\)\?\.focus\(\)", code)
    for node in ("demoError", "groupErrorText", "sendError"):
        assert f'{node}.setAttribute("role", "alert")' in code, node
    for node in ("demoStatus", "groupStatus"):
        assert f'{node}.setAttribute("role", "status")' in code, node


def test_message_box_has_a_label_and_grows():
    code = JS.split("PA.strings")[1].split("});", 1)[1]
    assert 'boxLabel.htmlFor = "practice-message"' in code
    assert 'input.addEventListener("input", fitBox)' in code
    assert "Math.min(input.scrollHeight, BOX_MAX)" in code


def test_the_group_explains_a_missing_model_without_asking_the_server():
    code = JS.split("PA.strings")[1].split("});", 1)[1]
    opening = code.split("async function openGroup()")[1].split("PA.api(")[0]
    assert "PA.state?.configured" in opening and 'showGroupError("practice_needs_key")' in opening
    assert 'PA.showView("settings")' in code


def test_the_scene_switcher_is_text_tabs():
    rule = re.search(r"\n\.practice-scene \{(.*?)\}", CSS, re.S).group(1)
    assert "background: none" in rule and "var(--side)" not in rule
    active = re.search(r"\n\.practice-scene\.active \{(.*?)\}", CSS, re.S).group(1)
    assert "background" not in active and "border-bottom-color" in active
