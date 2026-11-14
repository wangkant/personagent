"""`personagent memory`: look at, forget and bring back what the character
remembers, on a stopped home through the files and on a running one through
the service's API.

    python -m pytest tests/test_memory_admin.py
"""
from __future__ import annotations

import json
import time
import warnings
from pathlib import Path

import pytest

from persona_agent import dashboard, memory_admin, memstore, server
from persona_agent.settings import AgentSettings
from persona_agent.storage import RuntimeInstanceLock

from helpers import check, isolated_agent

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from fastapi.testclient import TestClient

DASH_TOKEN = "dashTOKEN-memory-0123456789abcdefghijklmnop"
FACT = {"text": "Sam has a dog now", "time": 1762800000.0, "auto": True,
        "user_id": "telegram:42", "user_name": "Sam"}


@pytest.fixture
def home(tmp_path: Path, monkeypatch) -> Path:
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    (runtime / "memory.json").write_text(json.dumps({"telegram:c1": [FACT]}), encoding="utf-8")
    (runtime / "core_memory.json").write_text(json.dumps({"telegram:c1": "Speak plainly."}),
                                              encoding="utf-8")
    monkeypatch.setenv("AGENT_HOME", str(tmp_path))
    monkeypatch.setenv("AGENT_LANG", "en")
    monkeypatch.setattr(memory_admin, "_root", lambda: tmp_path)
    monkeypatch.setattr(memory_admin, "_file_backend", lambda: memory_admin.FileBackend(
        runtime / "memory.json", runtime / "core_memory.json", runtime, AgentSettings(api_key="")))
    monkeypatch.setattr(memory_admin, "_restore_command", lambda tid: f"personagent memory restore {tid}")
    return tmp_path


def run(*argv: str) -> int:
    return memory_admin.main(list(argv), prog="personagent memory")


def stored(home: Path) -> dict:
    return json.loads((home / "runtime" / "memory.json").read_text(encoding="utf-8"))


def test_a_stopped_home_is_read_and_edited_through_its_files(home, capsys) -> None:
    check("list: exit 0", run() == 0)
    out = capsys.readouterr().out
    fact_id = stored(home)["telegram:c1"][0]["id"]
    check("list: the chat, its note and its fact with the id", "Chat: telegram:c1" in out
          and "Always in mind" in out and "Speak plainly." in out
          and fact_id in out and "Sam has a dog now" in out, out)
    check("forget by the start of the id", run("forget", fact_id[:5]) == 0)
    out = capsys.readouterr().out
    check("forget: said, with the command that brings it back",
          "Forgotten." in out and "personagent memory restore r" in out, out)
    check("forget: gone from the file", stored(home)["telegram:c1"] == [])
    check("removed: listed with its reason", run("removed") == 0)
    out = capsys.readouterr().out
    tid = next(word for word in out.split() if word.startswith("r") and len(word) == 11)
    check("removed: the reason and the text", "Forgotten with this command" in out
          and "Sam has a dog now" in out, out)
    check("restore", run("restore", tid) == 0 and "Restored." in capsys.readouterr().out)
    check("restore: back in the file under the same id",
          [row["id"] for row in stored(home)["telegram:c1"]] == [fact_id])
    check("restore again: no longer restorable", run("restore", tid) == 1
          and "This item can no longer be restored." in capsys.readouterr().out)
    check("the always-present note by its name", run("forget", "core") == 0)
    capsys.readouterr()
    core = json.loads((home / "runtime" / "core_memory.json").read_text(encoding="utf-8"))
    check("core: gone", "telegram:c1" not in core, repr(core))
    check("an unknown id is refused", run("forget", "zzz") == 1
          and "No item has that id." in capsys.readouterr().out)
    check("json: the data", run("list", "--json") == 0
          and json.loads(capsys.readouterr().out)[0]["facts"][0]["id"] == fact_id)


def test_an_ambiguous_prefix_is_refused(home, capsys) -> None:
    second = dict(FACT, text="Sam moved to Lisbon")
    (home / "runtime" / "memory.json").write_text(
        json.dumps({"telegram:c1": [FACT, second]}), encoding="utf-8")
    run()
    capsys.readouterr()
    check("forget 'm' matches both facts", run("forget", "m") == 1)
    check("and says to give more", "That id matches more than one item; give more characters."
          in capsys.readouterr().out)
    check("nothing was forgotten", len(stored(home)["telegram:c1"]) == 2)


def test_the_terminal_speaks_the_install_language(home, monkeypatch, capsys) -> None:
    monkeypatch.setenv("AGENT_LANG", "zh")
    run()
    out = capsys.readouterr().out
    check("zh: the header, columns and kind", "聊天：telegram:c1" in out and "首次记下" in out
          and "常驻记忆" in out and "事实" in out, out)
    run("forget", "zzz")
    check("zh: the refusal", "没有与该编号对应的项。" in capsys.readouterr().out)


def test_refusals_say_where_to_look(home, monkeypatch, capsys) -> None:
    monkeypatch.setattr(memory_admin, "_memory_command", lambda sub="": f"personagent memory {sub}".strip())
    check("an unknown id", run("forget", "zzz") == 1)
    out = capsys.readouterr().out
    check("the refusal and the listing to run",
          "No item has that id.\nRun `personagent memory` to see the ids." in out, out)
    check("an unknown removed id", run("restore", "xyz") == 1)
    check("points at what was removed", "Run `personagent memory removed` to see the ids."
          in capsys.readouterr().out)
    check("an unknown chat", run("list", "--chat", "telegram:nope") == 0)
    out = capsys.readouterr().out
    check("not read as an empty memory",
          "No chat with the key telegram:nope holds anything remembered. Run `personagent "
          "memory` to see the chats and their keys." in out and "Nothing is remembered." not in out, out)
    monkeypatch.setenv("AGENT_LANG", "zh")
    run("list", "--chat", "telegram:nope")
    check("zh", "键为 telegram:nope 的聊天中没有任何记忆。" in capsys.readouterr().out)


def test_a_damaged_memory_file_is_one_sentence_naming_the_copy(home, capsys) -> None:
    memory = home / "runtime" / "memory.json"
    (home / "runtime" / "memory.json.bak").write_text("{}", encoding="utf-8")
    memory.write_text('{"broken', encoding="utf-8")
    check("exit 1, no traceback", run() == 1)
    err = capsys.readouterr().err
    check("the file, the copy and what to do",
          err.startswith(f"The memory file {memory} is damaged and was left untouched. "
                         "A copy from ")
          and str(home / "runtime" / "memory.json.bak") in err and "Traceback" not in err, err)
    check("the damaged file is left as it was", memory.read_text(encoding="utf-8") == '{"broken')


def test_the_damaged_sentence_is_translated(home, monkeypatch) -> None:
    monkeypatch.setenv("AGENT_LANG", "de")
    error = memstore.MemoryFileDamaged(home / "runtime" / "episodes.json")
    path = home / "runtime" / "episodes.json"
    check("without a copy", memory_admin.damaged_sentence(error)
          == f"Die Gedächtnisdatei {path} ist beschädigt und wurde nicht verändert; eine "
          "frühere Kopie davon gibt es nicht. Verschieben Sie die beschädigte Datei, zum "
          "Beispiel durch Umbenennen, um mit einem leeren Gedächtnis zu starten.")
    trial = home / "runtime" / "trial"
    sentence = memory_admin.damaged_sentence(
        memstore.MemoryFileDamaged(trial / "memory.json"), trial=trial)
    check("the trial's own file is named as the trial's",
          sentence.startswith(f"Die Gedächtnisdatei {trial / 'memory.json'} des Probechats")
          and f"Löschen Sie den Ordner {trial}," in sentence, sentence)


@pytest.fixture
def service(home, tmp_path, monkeypatch):
    """The home held by a running service whose API answers the command."""
    saved = (server.agent, dashboard._token)
    agent = isolated_agent(tmp_path / "agent", seeds=True)
    agent.memories["telegram:c1"] = [dict(FACT, id="m0123456789")]
    server.agent, dashboard._token = agent, DASH_TOKEN
    monkeypatch.setattr(memory_admin, "_service_client", lambda: TestClient(
        server.app, base_url="http://127.0.0.1:8080", client=("127.0.0.1", 50000),
        headers={dashboard.TOKEN_HEADER: DASH_TOKEN}))
    monkeypatch.setattr(memory_admin, "_file_backend",
                        lambda: pytest.fail("the files were opened while the service runs"))
    lock = RuntimeInstanceLock(home).acquire()
    try:
        yield agent
    finally:
        lock.release()
        server.agent, dashboard._token = saved


def test_a_running_service_is_asked_through_its_api(service, home, capsys) -> None:
    check("list", run() == 0 and "m0123456789" in capsys.readouterr().out)
    check("forget", run("forget", "m01") == 0 and "Forgotten." in capsys.readouterr().out)
    check("forget: the running agent forgot it", service.memories["telegram:c1"] == [])
    removed = service._removed_items("telegram:c1")
    check("forget: recorded as the terminal's", [r["by"] for r in removed] == ["terminal"])
    check("restore", run("restore", removed[0]["tid"]) == 0 and "Restored." in capsys.readouterr().out)
    check("restore: the running agent has it back",
          [row["id"] for row in service.memories["telegram:c1"]] == ["m0123456789"])
    check("the stopped-home files were never touched",
          stored(home)["telegram:c1"][0].get("id") is None)


def test_a_service_with_activity_off_says_so(service, monkeypatch, capsys) -> None:
    monkeypatch.setattr(memory_admin, "_service_client", lambda: TestClient(
        __import__("fastapi").FastAPI(), base_url="http://127.0.0.1:8080"))
    check("exit 1", run() == 1)
    check("names the setting", "DASHBOARD_ENABLED=false" in capsys.readouterr().out)


def test_a_restore_past_its_time_is_refused(home, capsys) -> None:
    run()
    capsys.readouterr()
    backend = memory_admin._file_backend()
    tid = backend.files.memory_trash.put("telegram:c1", "note", dict(FACT, id="m9999999999"),
                                         "forgotten_page", "page", now=time.time() - 90_000)
    check("not listed as restorable", run("removed") == 0
          and tid not in capsys.readouterr().out)
    check("refused by its whole id", run("restore", tid) == 1
          and "This item can no longer be restored." in capsys.readouterr().out)


def test_the_page_chat_is_named_as_the_page_names_it(monkeypatch) -> None:
    monkeypatch.setenv("AGENT_LANG", "en")
    check("the page's chat", memory_admin._chat_line("private:browser:abc")
          == "Chat: This page (key private:browser:abc)")
    check("another chat by its key", memory_admin._chat_line("group:telegram:9") == "Chat: group:telegram:9")
