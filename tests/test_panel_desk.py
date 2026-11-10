"""The desk panel: icon and start-at-sign-in links, opening the data folders,
backups, restore and starting over."""
from __future__ import annotations

import concurrent.futures
import io
import json
import os
import zipfile

from fastapi.testclient import TestClient
import pytest

from persona_agent import langs, shortcut
from persona_agent import setup_wizard as sw
from persona_agent import welcome
from persona_agent.panels import desk

TOKEN = "test-local-capability"
HEADERS = {welcome.TOKEN_HEADER: TOKEN}
KEY = "sk-desk-secret-0123456789"
PLATFORM_SECRET = "bot-token-secret-987654"


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    desktop, documents = tmp_path / "Desktop", tmp_path / "Documents"
    desktop.mkdir()
    documents.mkdir()
    monkeypatch.setenv(desk.DIRS_ENV, os.pathsep.join([str(desktop), str(documents)]))
    links = [tmp_path / "links" / k for k in shortcut.SPECIAL]
    monkeypatch.setenv(shortcut.DIRS_ENV, os.pathsep.join(map(str, links)))
    monkeypatch.delenv("AGENT_RUNTIME_DIR", raising=False)
    value = welcome.Workspace(home)
    yield value
    value.close()


@pytest.fixture
def client(workspace):
    with TestClient(welcome.create_app(workspace.home, TOKEN, workspace=workspace),
                    base_url="http://127.0.0.1") as value:
        yield value


@pytest.fixture
def opened(monkeypatch):
    seen = []
    monkeypatch.setattr(desk, "open_path", seen.append)
    return seen


def seed(home):
    sw.write_env(home / ".env", {"LLM_API_KEY": KEY, "LLM_MODEL": "m", "PERSONA_NAME": "Ann"})
    (home / "persona.txt").write_text("You are Ann.\n", encoding="utf-8")
    runtime = home / "runtime"
    (runtime / "desktop").mkdir(parents=True)
    (runtime / "desktop" / "app.log").write_text("log line\n", encoding="utf-8")
    (runtime / "memory.json").write_text('{"a": "likes tea"}', encoding="utf-8")
    (runtime / "core_memory.json").write_text("{}", encoding="utf-8")
    (runtime / "stickers.json").write_text("{}", encoding="utf-8")
    (runtime / "dashboard.token").write_text("dash-token", encoding="utf-8")
    (runtime / "trial").mkdir()
    (runtime / "trial" / "x.json").write_text("{}", encoding="utf-8")
    (home / "stickers").mkdir()
    (home / "stickers" / "cat.png").write_bytes(b"png")
    (home / "data").mkdir()
    (home / "data" / "lorebook.en.json").write_text("[]", encoding="utf-8")
    (home / "platforms" / "astrbot" / "bin").mkdir(parents=True)
    (home / "platforms" / "astrbot" / "bin" / "big.exe").write_bytes(b"x" * 10)
    (home / "platforms" / "direct.json").write_text(
        json.dumps({"telegram": {"token": PLATFORM_SECRET}}), encoding="utf-8")


def post(client, path, payload=None):
    return client.post(f"/api/desk{path}", headers=HEADERS, json=payload or {})


def test_every_route_needs_the_local_token(client):
    assert client.get("/api/desk").status_code == 403
    assert client.post("/api/desk/reset", json={}).status_code == 403
    assert client.post("/api/desk/open", json={"place": "home"},
                       headers={**HEADERS, "Origin": "https://other.example"}).status_code == 403


def test_overview_shows_where_things_are_and_no_secret(client, workspace, tmp_path):
    seed(workspace.home)
    answer = client.get("/api/desk", headers=HEADERS)
    assert answer.status_code == 200
    value = answer.json()
    assert value["home"] == str(workspace.home)
    assert {p["id"] for p in value["places"]} == set(desk.PLACES)
    assert {t["id"]: t["path"] for t in value["targets"]} == {
        "desktop": str(tmp_path / "Desktop"), "documents": str(tmp_path / "Documents"),
        "backups": str(workspace.home / "backups")}
    assert value["backups"] == []
    assert KEY not in answer.text and PLATFORM_SECRET not in answer.text


def test_open_shows_only_known_places(client, workspace, opened):
    seed(workspace.home)
    home = workspace.home
    expected = {"home": home, "persona": home / "persona.txt", "logs": home / "runtime" / "desktop",
                "memory": home / "runtime", "stickers": home / "stickers", "data": home / "data"}
    for place, path in expected.items():
        assert post(client, "/open", {"place": place}).json() == {"ok": True}
        assert opened[-1] == path.resolve() or opened[-1] == path
    for place in ("..", "C:\\Windows", "../.env", ""):
        answer = post(client, "/open", {"place": place})
        assert answer.status_code == 400 and answer.json() == {"error": "desk_invalid_place"}
    assert len(opened) == len(expected)


def test_open_makes_a_missing_folder_but_not_a_missing_persona(client, workspace, opened, monkeypatch):
    assert post(client, "/open", {"place": "stickers"}).status_code == 200
    assert (workspace.home / "stickers").is_dir()
    answer = post(client, "/open", {"place": "persona"})
    assert answer.json() == {"error": "desk_missing"}

    def broken(path):
        raise OSError("no file manager")
    monkeypatch.setattr(desk, "open_path", broken)
    assert post(client, "/open", {"place": "home"}).json() == {"error": "desk_open_failed"}


def test_a_runtime_outside_the_home_is_refused(client, workspace, opened):
    sw.write_env(workspace.env, {"AGENT_RUNTIME_DIR": "../elsewhere"})
    assert post(client, "/open", {"place": "memory"}).json() == {"error": "desk_runtime_elsewhere"}
    assert opened == []


# -- links ------------------------------------------------------------------

def fake_windows(monkeypatch, found):
    """Windows' answer about the links, and every script it was asked to run."""
    ran = []

    def powershell(source):
        ran.append(source)
        return (json.dumps(found) if "ConvertTo-Json" in source else ""), ""
    monkeypatch.setattr(shortcut, "WINDOWS", True)
    monkeypatch.setattr(shortcut, "_powershell", powershell)
    monkeypatch.setattr(langs, "under_uvx", lambda: False)
    return ran


def test_link_status_tells_this_copy_from_another(client, workspace, monkeypatch):
    program, arguments = shortcut.target(workspace.home)
    mine = {"target": str(program), "arguments": arguments}
    fake_windows(monkeypatch, [{"kind": "desktop", **mine}, {"kind": "programs", **mine},
                               {"kind": "startup", "target": str(program), "arguments": "-m other"}])
    value = client.get("/api/desk/shortcuts", headers=HEADERS).json()
    assert value == {"supported": True, "uvx": False, "icon": "on", "login": "other"}
    fake_windows(monkeypatch, [{"kind": "desktop", **mine}])
    assert client.get("/api/desk/shortcuts", headers=HEADERS).json()["icon"] == "other"
    fake_windows(monkeypatch, [])
    value = client.get("/api/desk/shortcuts", headers=HEADERS).json()
    assert value["icon"] == "off" and value["login"] == "off"


def test_status_asks_only_the_redirected_folders(workspace, tmp_path, monkeypatch):
    ran = fake_windows(monkeypatch, [])
    shortcut.status(workspace.home)
    assert "GetFolderPath" not in ran[-1] and str(tmp_path / "links" / "startup") in ran[-1]
    monkeypatch.setenv(shortcut.DIRS_ENV, "only-one")
    with pytest.raises(ValueError):
        shortcut.status(workspace.home)


def test_adding_and_removing_links_writes_only_their_folders(client, workspace, tmp_path, monkeypatch):
    ran = fake_windows(monkeypatch, [])
    answer = post(client, "/shortcut", {"which": "login", "on": True})
    assert answer.status_code == 200 and answer.json()["supported"] is True
    made = [s for s in ran if "CreateShortcut((Join-Path" in s][-1]
    assert str(tmp_path / "links" / "startup") in made and "Desktop" not in made
    assert f'--home "{workspace.home}"' in made
    post(client, "/shortcut", {"which": "icon", "on": True})
    made = [s for s in ran if "CreateShortcut((Join-Path" in s][-1]
    assert str(tmp_path / "links" / "desktop") in made and str(tmp_path / "links" / "programs") in made
    assert "startup" not in made
    post(client, "/shortcut", {"which": "icon", "on": False})
    assert "Remove-Item" in [s for s in ran if "ConvertTo-Json" not in s][-1]


def test_link_refusals(client, monkeypatch):
    fake_windows(monkeypatch, [])
    assert post(client, "/shortcut", {"which": "tray", "on": True}).json() == {"error": "desk_invalid_place"}
    monkeypatch.setattr(langs, "under_uvx", lambda: True)
    assert post(client, "/shortcut", {"which": "icon", "on": True}).json() == {"error": "desk_uvx"}
    # Taking a link away needs no install that stays.
    assert post(client, "/shortcut", {"which": "icon", "on": False}).status_code == 200
    monkeypatch.setattr(langs, "under_uvx", lambda: False)
    monkeypatch.setattr(shortcut, "_powershell", lambda source: ("", "access denied"))
    assert post(client, "/shortcut", {"which": "icon", "on": True}).json() == {"error": "desk_shortcut_failed"}
    assert client.get("/api/desk/shortcuts", headers=HEADERS).json() == {"error": "desk_shortcut_failed"}
    monkeypatch.setattr(shortcut, "WINDOWS", False)
    assert client.get("/api/desk/shortcuts", headers=HEADERS).json()["supported"] is False
    assert post(client, "/shortcut", {"which": "icon", "on": True}).json() == {"error": "desk_unsupported"}


# -- backups ----------------------------------------------------------------

def test_backup_holds_the_state_and_leaves_out_logs_and_downloads(client, workspace, tmp_path):
    seed(workspace.home)
    answer = post(client, "/backup", {"to": "documents"})
    assert answer.status_code == 200
    value = answer.json()
    path = tmp_path / "Documents" / value["name"]
    assert value["path"] == str(path) and value["size"] == path.stat().st_size > 0
    assert KEY not in answer.text and PLATFORM_SECRET not in answer.text
    names = set(zipfile.ZipFile(path).namelist())
    assert {desk.MANIFEST, ".env", "persona.txt", "runtime/memory.json", "runtime/core_memory.json",
            "runtime/stickers.json", "stickers/cat.png", "data/lorebook.en.json",
            "platforms/direct.json"} <= names
    assert not any(n.startswith(("runtime/desktop", "runtime/trial", "platforms/astrbot")) for n in names)
    assert "runtime/dashboard.token" not in names
    assert [b["name"] for b in value["backups"]] == [value["name"]]
    assert value["backups"][0]["place"] == "documents"
    assert post(client, "/backup", {"to": "D:/anywhere"}).json() == {"error": "desk_invalid_place"}


def test_backup_reports_a_folder_it_cannot_write(client, workspace, monkeypatch, tmp_path):
    blocker = tmp_path / "file-not-folder"
    blocker.write_text("x", encoding="utf-8")
    monkeypatch.setenv(desk.DIRS_ENV, os.pathsep.join([str(blocker / "inside"), str(tmp_path)]))
    assert post(client, "/backup", {"to": "desktop"}).json() == {"error": "desk_backup_failed"}
    monkeypatch.setenv(desk.DIRS_ENV, "")
    monkeypatch.setattr(desk, "_known_folder", lambda kind: None)
    assert post(client, "/backup", {"to": "desktop"}).json() == {"error": "desk_missing"}


def stopped_services(workspace, monkeypatch, running=()):
    """Every stop and start, in order; `running` is what ran before."""
    calls = []
    running = set(desk.SERVICES) if running is True else set(running)
    monkeypatch.setattr(workspace.services, "running", lambda name: name in running)
    monkeypatch.setattr(workspace.services, "close", lambda: calls.append("close"))
    for name in desk.SERVICES:
        monkeypatch.setattr(workspace.services, f"start_{name}",
                            lambda name=name: calls.append(f"start {name}"))
    monkeypatch.setattr(workspace, "_connect_plugin", lambda: None)
    return calls


def settled(workspace, calls):
    if workspace._future is not None:
        workspace._future.result(timeout=10)
    return calls


def test_restore_brings_the_backup_back_after_saving_the_present(client, workspace, monkeypatch):
    seed(workspace.home)
    name = post(client, "/backup", {"to": "backups"}).json()["name"]
    home = workspace.home
    (home / "runtime" / "memory.json").write_text('{"b": "new"}', encoding="utf-8")
    (home / "runtime" / "learned-later.jsonl").write_text("{}\n", encoding="utf-8")
    (home / "stickers" / "dog.png").write_bytes(b"png")
    (home / "persona.txt").write_text("Someone else.\n", encoding="utf-8")
    calls = stopped_services(workspace, monkeypatch, running=True)
    answer = post(client, "/restore", {"place": "backups", "name": name})
    assert answer.status_code == 200, answer.text
    value = answer.json()
    assert settled(workspace, calls) == ["close", "start agent", "start direct"],         "stopped first, started again after"
    assert (home / "runtime" / "memory.json").read_text(encoding="utf-8") == '{"a": "likes tea"}'
    assert not (home / "runtime" / "learned-later.jsonl").exists()
    assert not (home / "stickers" / "dog.png").exists() and (home / "stickers" / "cat.png").exists()
    assert (home / "persona.txt").read_text(encoding="utf-8") == "You are Ann.\n"
    assert (home / "runtime" / "desktop" / "app.log").exists(), "logs are left alone"
    safety = zipfile.ZipFile(value["safety"])
    assert safety.read("persona.txt").strip() == b"Someone else."
    assert KEY not in answer.text


def make_zip(path, members, manifest=True):
    with zipfile.ZipFile(path, "w") as archive:
        if manifest:
            archive.writestr(desk.MANIFEST, "{}")
        for name, data in members.items():
            archive.writestr(name, data)


@pytest.mark.parametrize("members,manifest", [
    ({"../evil.txt": "x"}, True),
    ({"runtime/../../evil.txt": "x"}, True),
    ({"persona_agent/welcome.py": "x"}, True),
    ({"/abs.txt": "x"}, True),
    ({"C:/abs.txt": "x"}, True),
    ({"runtime\\..\\evil.txt": "x"}, True),
    ({"platforms/astrbot/bin/x.exe": "x"}, True),
    ({"runtime/desktop/children-1.json": "{}"}, True),
    ({"runtime/desktop/webview/x": "x"}, True),
    ({"persona.txt": "x"}, False),
])
def test_restore_refuses_a_zip_with_unexpected_files(client, workspace, tmp_path, monkeypatch, members, manifest):
    seed(workspace.home)
    make_zip(tmp_path / "Desktop" / "personagent-backup-bad.zip", members, manifest)
    calls = stopped_services(workspace, monkeypatch)
    answer = post(client, "/restore", {"place": "desktop", "name": "personagent-backup-bad.zip"})
    assert answer.json() == {"error": "desk_invalid_backup"}
    assert calls == [], "nothing was stopped"
    assert (workspace.home / "persona.txt").read_text(encoding="utf-8") == "You are Ann.\n"
    assert not (tmp_path / "evil.txt").exists() and not (workspace.home / "backups").exists()


def test_restore_refusals(client, workspace, tmp_path, monkeypatch):
    for payload in ({"place": "desktop", "name": "../x.zip"}, {"place": "desktop", "name": "other.zip"},
                    {"place": "elsewhere", "name": "personagent-backup-1.zip"}):
        assert post(client, "/restore", payload).json() == {"error": "desk_invalid_backup"}
    assert post(client, "/restore", {"place": "desktop", "name": "personagent-backup-none.zip"}).json() \
        == {"error": "desk_missing"}
    (tmp_path / "Desktop" / "personagent-backup-junk.zip").write_bytes(b"not a zip")
    assert post(client, "/restore", {"place": "desktop", "name": "personagent-backup-junk.zip"}).json() \
        == {"error": "desk_invalid_backup"}
    make_zip(tmp_path / "Desktop" / "personagent-backup-ok.zip", {"persona.txt": "x"})
    pending = concurrent.futures.Future()
    workspace._future = pending
    assert post(client, "/restore", {"place": "desktop", "name": "personagent-backup-ok.zip"}).json() \
        == {"error": "busy"}
    assert post(client, "/forget").json() == {"error": "busy"}
    assert post(client, "/reset").json() == {"error": "busy"}
    pending.set_result(None)


# -- starting over ----------------------------------------------------------

def test_forget_keeps_settings_persona_and_stickers(client, workspace, monkeypatch):
    seed(workspace.home)
    home = workspace.home
    calls = stopped_services(workspace, monkeypatch, running=True)
    answer = post(client, "/forget")
    assert answer.status_code == 200
    assert settled(workspace, calls) == ["close", "start agent", "start direct"]
    assert not (home / "runtime" / "memory.json").exists()
    assert not (home / "runtime" / "core_memory.json").exists()
    assert not (home / "runtime" / "trial").exists()
    assert (home / "runtime" / "stickers.json").exists() and (home / "stickers" / "cat.png").exists()
    assert (home / ".env").exists() and (home / "persona.txt").exists()
    assert (home / "platforms" / "direct.json").exists()
    assert (home / "runtime" / "desktop" / "app.log").exists()
    safety = zipfile.ZipFile(answer.json()["safety"])
    assert "runtime/memory.json" in safety.namelist()
    assert KEY not in answer.text


def test_reset_goes_back_to_the_first_run(client, workspace, monkeypatch):
    seed(workspace.home)
    home = workspace.home
    calls = stopped_services(workspace, monkeypatch, running=True)
    answer = post(client, "/reset")
    assert answer.status_code == 200
    assert calls == ["close"], "nothing starts again: nothing is set up"
    for gone in (".env", "persona.txt", "platforms/direct.json", "runtime/memory.json",
                 "runtime/stickers.json"):
        assert not (home / gone).exists(), gone
    assert (home / "stickers" / "cat.png").exists() and (home / "data" / "lorebook.en.json").exists()
    assert client.get("/api/state", headers=HEADERS).json()["configured"] is False
    safety = zipfile.ZipFile(answer.json()["safety"])
    assert ".env" in safety.namelist() and "platforms/direct.json" in safety.namelist()
    assert KEY not in answer.text and PLATFORM_SECRET not in answer.text
    listed = client.get("/api/desk", headers=HEADERS).json()["backups"]
    assert [b["place"] for b in listed] == ["backups"]


def test_a_startup_link_made_here_reads_as_on(workspace, monkeypatch):
    program, arguments = shortcut.target(workspace.home)
    made = shortcut.script(workspace.home, kinds=shortcut.LOGIN)
    assert f"$link.Arguments = '{arguments} --background'" in made
    fake_windows(monkeypatch, [{"kind": "startup", "target": str(program),
                                "arguments": arguments + " --background"}])
    assert shortcut.status(workspace.home)["startup"] == "on"
    fake_windows(monkeypatch, [{"kind": "startup", "target": str(program), "arguments": arguments},
                               {"kind": "desktop", "target": str(program),
                                "arguments": arguments + " --background"}])
    found = shortcut.status(workspace.home)
    assert found["startup"] == "other" and found["desktop"] == "other"


def test_starting_over_stops_the_panels_children_and_restarts_only_what_ran(client, workspace, monkeypatch):
    seed(workspace.home)
    calls = stopped_services(workspace, monkeypatch, running={"agent"})
    client.app.state.closers.append(lambda: calls.append("practice stopped"))
    assert post(client, "/forget").status_code == 200
    assert settled(workspace, calls) == ["practice stopped", "close", "start agent"]
    calls.clear()
    monkeypatch.setattr(workspace.services, "running", lambda name: name == "astrbot")
    monkeypatch.setattr(desk.conn, "connected", lambda data: ["aiocqhttp"])
    assert post(client, "/forget").status_code == 200
    assert settled(workspace, calls) == ["practice stopped", "close", "start astrbot"]


def test_a_failed_safety_backup_changes_nothing_and_starts_again(client, workspace, monkeypatch):
    seed(workspace.home)
    calls = stopped_services(workspace, monkeypatch, running={"agent", "direct"})

    def refuse(*args, **kwargs):
        raise ValueError("desk_backup_failed")
    monkeypatch.setattr(desk.Desk, "_write_backup", refuse)
    assert post(client, "/forget").json() == {"error": "desk_backup_failed"}
    assert settled(workspace, calls) == ["close", "start agent", "start direct"]
    assert (workspace.home / "runtime" / "memory.json").exists()


def test_a_runtime_elsewhere_is_refused_before_anything_stops(client, workspace, monkeypatch):
    seed(workspace.home)
    sw.write_env(workspace.env, {"AGENT_RUNTIME_DIR": "../elsewhere"})
    calls = stopped_services(workspace, monkeypatch, running=True)
    for action in ("/forget", "/reset"):
        assert post(client, action).json() == {"error": "desk_runtime_elsewhere"}
    assert calls == [] and (workspace.home / ".env").exists()


def test_reset_clears_a_runtime_folder_named_in_the_env(client, workspace, monkeypatch):
    seed(workspace.home)
    sw.write_env(workspace.env, {"AGENT_RUNTIME_DIR": "state"})
    state = workspace.home / "state"
    state.mkdir()
    (state / "memory.json").write_text("{}", encoding="utf-8")
    stopped_services(workspace, monkeypatch)
    answer = post(client, "/reset")
    assert answer.status_code == 200, answer.text
    assert not (state / "memory.json").exists()
    assert "runtime/memory.json" in zipfile.ZipFile(answer.json()["safety"]).namelist()


def test_a_restore_that_fails_midway_puts_the_present_back(client, workspace, monkeypatch):
    seed(workspace.home)
    name = post(client, "/backup", {"to": "backups"}).json()["name"]
    home = workspace.home
    (home / "runtime" / "memory.json").write_text('{"b": "now"}', encoding="utf-8")
    calls = stopped_services(workspace, monkeypatch, running={"agent"})
    real, failed = desk.shutil.copyfileobj, []

    def flaky(source, out, *args):
        # Only the copy out of a backup: zipfile uses the same function to write one.
        if not failed and isinstance(out, io.BufferedWriter):
            failed.append(True)
            raise OSError("disk full")
        return real(source, out, *args)
    monkeypatch.setattr(desk.shutil, "copyfileobj", flaky)
    answer = post(client, "/restore", {"place": "backups", "name": name})
    assert answer.json() == {"error": "desk_restore_undone"}
    assert (home / "runtime" / "memory.json").read_text(encoding="utf-8") == '{"b": "now"}'
    assert (home / "stickers" / "cat.png").exists() and (home / "persona.txt").exists()
    assert settled(workspace, calls) == ["close", "start agent"]


def test_nothing_changes_while_a_service_from_elsewhere_holds_the_home(client, workspace, monkeypatch):
    seed(workspace.home)
    calls = stopped_services(workspace, monkeypatch, running={"agent"})
    with desk.RuntimeInstanceLock(workspace.home):
        assert post(client, "/forget").json() == {"error": "desk_service_elsewhere"}
        assert post(client, "/reset").json() == {"error": "desk_service_elsewhere"}
    assert (workspace.home / "runtime" / "memory.json").exists() and (workspace.home / ".env").exists()
    assert not (workspace.home / "backups").exists()
    assert settled(workspace, calls)[-1] == "start agent"


def test_errors_are_ones_the_page_can_show(client):
    assert all(code.startswith("desk_") for code in desk.ERRORS)
    js = (welcome.ASSETS / "panels" / "desk.js").read_text(encoding="utf-8")
    for code in desk.ERRORS:
        assert js.count(f"    {code}: ") == 2, code
