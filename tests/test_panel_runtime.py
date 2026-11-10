"""The runtime panel: running behind the window, and updating from inside the app."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import types
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from persona_agent import update_helper, updates, welcome
from persona_agent import home as homes
from persona_agent.panels import runtime

TOKEN = "test-local-capability"
HEADERS = {welcome.TOKEN_HEADER: TOKEN}


@pytest.fixture
def page(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENT_LANG", "en")
    workspace = welcome.Workspace(tmp_path)
    app = welcome.create_app(tmp_path, TOKEN, workspace=workspace)
    with TestClient(app, base_url="http://127.0.0.1") as client:
        yield types.SimpleNamespace(app=app, client=client, home=tmp_path, workspace=workspace,
                                    desktop=tmp_path / "runtime" / "desktop")
    workspace.close()


def _found(home: Path, latest: str = "99.0.0") -> None:
    cache = home / "runtime" / "desktop" / "update.json"
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps({"checked": time.time(), "latest": latest, "failed": False}), encoding="utf-8")


def test_the_panel_needs_the_capability(page) -> None:
    assert page.client.get("/api/runtime").status_code == 403
    for path in ("background", "hide", "check", "update", "update/seen"):
        assert page.client.post(f"/api/runtime/{path}", json={}).status_code == 403, path


def test_background_can_be_chosen_only_where_a_window_can_hide(page) -> None:
    seen = page.client.get("/api/runtime", headers=HEADERS).json()
    assert seen["background"] is False and seen["canHide"] is False
    refused = page.client.post("/api/runtime/background", json={"on": True}, headers=HEADERS)
    assert (refused.status_code, refused.json()) == (400, {"error": "background_unavailable"})
    hidden = []
    page.app.state.window = types.SimpleNamespace(can_hide=True, hide=lambda: hidden.append(1) or True)
    on = page.client.post("/api/runtime/background", json={"on": True}, headers=HEADERS).json()
    assert on["background"] is True and on["canHide"] is True
    assert welcome.app_settings(page.desktop) == {"background": True}
    assert page.client.post("/api/runtime/hide", json={}, headers=HEADERS).json() == {"ok": True}
    assert hidden == [1]
    off = page.client.post("/api/runtime/background", json={"on": False}, headers=HEADERS).json()
    assert off["background"] is False, "turning it off never needs the icon"


def test_checking_now_asks_and_shows_what_it_found(page, monkeypatch) -> None:
    asked = []

    def check(home, timeout):
        asked.append(timeout)
        _found(home)
        return "99.0.0"

    monkeypatch.setattr(updates, "check", check)
    monkeypatch.setattr(updates, "plan", lambda: ("pip", [["python", "-m", "pip", "install", "-U", "personagent"]]))
    seen = page.client.post("/api/runtime/check", json={}, headers=HEADERS).json()
    assert asked == [10.0]
    assert seen["update"]["version"] == "99.0.0" and seen["updateBlocked"] == ""
    assert seen["update"]["url"].endswith("v99.0.0") and seen["checked"]


@pytest.mark.parametrize("kind, commands, tools, refusal", [
    ("zip", [], (), "update_by_hand"),
    ("uvx", [], (), "update_by_hand"),
    ("uv-tool", [["uv", "tool", "upgrade", "personagent"]], (), "update_tool_missing"),
    ("uv-tool", [["uv", "tool", "upgrade", "personagent"]], ("uv",), ""),
    ("pip", [["python", "-m", "pip", "install", "-U", "personagent"]], (), ""),
])
def test_what_stops_the_app_from_updating_itself(monkeypatch, kind, commands, tools, refusal) -> None:
    import shutil

    monkeypatch.setattr(shutil, "which", lambda name: name if name in tools else None)
    assert updates.blocked(kind, commands) == refusal


def test_a_clone_someone_changed_is_theirs_to_update(monkeypatch) -> None:
    import shutil

    monkeypatch.setattr(shutil, "which", lambda name: name)
    answers = iter([b" M README.md\n", b""])
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: types.SimpleNamespace(returncode=0, stdout=next(answers)))
    commands = [["git", "-C", "x", "pull", "--ff-only"]]
    assert updates.blocked("git", commands) == "update_clone_changed"
    assert updates.blocked("git", commands) == ""


def test_the_plan_matches_the_command_the_page_shows(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(homes, "is_checkout", lambda path=homes.CHECKOUT: False)
    monkeypatch.setattr(updates.langs, "under_uvx", lambda: False)
    monkeypatch.setattr(sys, "prefix", str(tmp_path))
    kind, commands = updates.plan()
    assert kind == "pip" and commands == [[updates._python(), "-m", "pip", "install", "-U", "personagent"]]
    (tmp_path / "uv-receipt.toml").write_text("", encoding="utf-8")
    assert updates.plan() == ("uv-tool", [["uv", "tool", "upgrade", "personagent"]])
    monkeypatch.setattr(updates.langs, "under_uvx", lambda: True)
    assert updates.plan() == ("uvx", [])


def test_update_stops_everything_leaves_a_helper_and_quits(page, monkeypatch) -> None:
    refused = page.client.post("/api/runtime/update", json={}, headers=HEADERS)
    assert refused.json() == {"error": "update_none"}
    _found(page.home)
    monkeypatch.setattr(updates, "plan", lambda: ("zip", []))
    assert page.client.post("/api/runtime/update", json={}, headers=HEADERS).json() == {"error": "update_by_hand"}

    commands = [["python", "-m", "pip", "install", "-U", "personagent"]]
    monkeypatch.setattr(updates, "plan", lambda: ("pip", commands))
    order, spawned = [], {}
    monkeypatch.setattr(page.workspace, "close", lambda: order.append("stopped"))
    page.app.state.shutdown = lambda: order.append("quit")
    monkeypatch.setenv("LLM_API_KEY", "sk-secret")
    monkeypatch.setattr(homes, "FROM_ENV_FILE", {"LLM_API_KEY"})

    def popen(argv, **options):
        order.append("helper")
        spawned.update(argv=argv, env=options["env"])

    # runtime.subprocess is the one module everybody shares; nothing else spawns here.
    monkeypatch.setattr(runtime.subprocess, "Popen", popen)
    assert page.client.post("/api/runtime/update", json={}, headers=HEADERS).json() == {"ok": True}
    assert order == ["helper", "stopped", "quit"], "nothing stops until the helper is on its way"
    plan = json.loads((page.desktop / "update-plan.json").read_text(encoding="utf-8"))
    assert plan["commands"] == commands and plan["pid"] == os.getpid()
    assert plan["relaunch"][1:] == ["-m", "persona_agent", "start", "--home", str(page.home)]
    assert Path(spawned["argv"][1]) == page.desktop / "update_helper.py", "a copy outside the package"
    assert "LLM_API_KEY" not in spawned["env"], "the helper does not get the keys"


def test_an_update_that_cannot_start_leaves_the_app_as_it_was(page, monkeypatch) -> None:
    _found(page.home)
    monkeypatch.setattr(updates, "plan", lambda: ("pip", [["python", "-m", "pip", "install", "-U", "personagent"]]))
    stopped = []
    monkeypatch.setattr(page.workspace, "close", lambda: stopped.append(1))

    def no_helper(home, commands):
        raise OSError("python moved")

    monkeypatch.setattr(runtime, "start_update", no_helper)
    refused = page.client.post("/api/runtime/update", json={}, headers=HEADERS)
    assert (refused.status_code, refused.json()) == (400, {"error": "update_not_started"})
    assert stopped == []


def test_a_check_that_did_not_reach_the_server_is_not_called_up_to_date(page) -> None:
    cache = page.desktop / "update.json"
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps({"checked": time.time(), "latest": "", "failed": True}), encoding="utf-8")
    seen = page.client.get("/api/runtime", headers=HEADERS).json()
    assert seen["update"] is None and seen["checkFailed"] is True and seen["updateKind"]


def test_the_helper_updates_reports_and_reopens(tmp_path, monkeypatch) -> None:
    started = []
    monkeypatch.setattr(update_helper, "reopen", started.append)
    plan = {"pid": 0, "from": "1.0.0", "log": str(tmp_path / "update.log"),
            "result": str(tmp_path / "result.json"), "relaunch": ["app", "start"],
            "commands": [[sys.executable, "-c", "print('installing')"]]}
    monkeypatch.setattr(update_helper, "gone", lambda pid, seconds: True)
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(plan), encoding="utf-8")
    assert update_helper.main([str(path)]) == 0
    assert json.loads((tmp_path / "result.json").read_text(encoding="utf-8"))["ok"] is True
    assert "installing" in (tmp_path / "update.log").read_text(encoding="utf-8")

    plan["commands"] = [[sys.executable, "-c", "raise SystemExit(3)"], [sys.executable, "-c", "print('never')"]]
    path.write_text(json.dumps(plan), encoding="utf-8")
    assert update_helper.main([str(path)]) == 3
    assert json.loads((tmp_path / "result.json").read_text(encoding="utf-8"))["ok"] is False
    assert "never" not in (tmp_path / "update.log").read_text(encoding="utf-8")
    assert started == [["app", "start"]] * 2, "the app reopens whether or not the update worked"


def test_the_helper_waits_for_a_real_process_to_end() -> None:
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(0.6)"])
    assert update_helper.gone(child.pid, 0.1) is False
    assert update_helper.gone(child.pid, 10) is True
    child.wait()


def test_someone_who_asks_is_told_even_with_the_daily_check_off(page, monkeypatch) -> None:
    monkeypatch.setenv("UPDATE_CHECK_ENABLED", "false")
    _found(page.home)
    assert updates.notice(page.home) is None
    assert page.client.get("/api/runtime", headers=HEADERS).json()["update"]["version"] == "99.0.0"


def test_the_result_of_the_last_update_shows_once(page) -> None:
    page.desktop.mkdir(parents=True, exist_ok=True)
    (page.desktop / "update-result.json").write_text(json.dumps({"ok": False, "from": "1.0.0", "failed": "pip"}), encoding="utf-8")
    (page.desktop / "update.log").write_text("\n".join(f"line {n}" for n in range(100)), encoding="utf-8")
    assert page.client.get("/api/runtime", headers=HEADERS).json()["lastUpdate"] == {"ok": False, "from": "1.0.0"}
    lines = page.client.get("/api/runtime/update/log", headers=HEADERS).json()["lines"]
    assert len(lines) == runtime.LOG_TAIL and lines[-1] == "line 99"
    assert page.client.post("/api/runtime/update/seen", json={}, headers=HEADERS).json() == {"ok": True}
    assert page.client.get("/api/runtime", headers=HEADERS).json()["lastUpdate"] is None
