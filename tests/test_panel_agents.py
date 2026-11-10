"""The agents panel: coding assistants and an AstrBot the user already runs."""
from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess

from fastapi.testclient import TestClient
import pytest

from persona_agent import setup_wizard as sw
from persona_agent import welcome
from persona_agent.panels import agents

TOKEN = "test-local-capability"
HEADERS = {welcome.TOKEN_HEADER: TOKEN}
KEY = "sk-agents-secret-123456789"
CONNECTOR = "connector-secret-abcdefghijkl"


class FakeClaude:
    """Records claude CLI calls and keeps user-scope servers where Claude Code would."""

    def __init__(self, config: Path):
        self.config, self.calls, self.fail = config, [], False

    def __call__(self, args):
        self.calls.append(list(args))
        data = json.loads(self.config.read_text(encoding="utf-8")) if self.config.is_file() else {}
        servers = data.setdefault("mcpServers", {})
        if args[1:3] == ["mcp", "remove"]:
            servers.pop(args[3], None)
        elif args[1:3] == ["mcp", "add"]:
            if self.fail:
                return subprocess.CompletedProcess(args, 1, "", "boom")
            rest = args[args.index("--") + 1:]
            servers[args[5]] = {"type": "stdio", "command": rest[0], "args": rest[1:]}
        elif args[1:3] == ["mcp", "add-json"]:
            servers[args[5]] = json.loads(args[6])
        self.config.parent.mkdir(parents=True, exist_ok=True)
        self.config.write_text(json.dumps(data), encoding="utf-8")
        return subprocess.CompletedProcess(args, 0, "", "")


@pytest.fixture
def scratch(tmp_path, monkeypatch):
    places = {name: tmp_path / name for name in ("claude", "codex", "dsh", "ext")}
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(places["claude"]))
    monkeypatch.setenv("CODEX_HOME", str(places["codex"]))
    monkeypatch.setenv("DSH_HOME", str(places["dsh"]))
    installed = {"claude": "C:/fake/claude.exe"}
    monkeypatch.setattr(agents, "_which", lambda name: installed.get(name))
    fake = FakeClaude(places["claude"] / ".claude.json")
    monkeypatch.setattr(agents, "_claude", fake)
    monkeypatch.setattr(sw, "astrbot_roots", lambda: [places["ext"]])
    return {**places, "installed": installed, "claude_cli": fake}


@pytest.fixture
def workspace(tmp_path, scratch, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    (home / ".env").write_text(f"LLM_API_KEY={KEY}\nPERSONA_NAME=Nova\nCONNECTOR_TOKEN={CONNECTOR}\n"
                               "SERVER_PORT=8080\n", encoding="utf-8")
    value = welcome.Workspace(home)
    value.started = []
    monkeypatch.setattr(value.services, "start_agent", lambda: value.started.append("agent"))
    monkeypatch.setattr(value, "_restart_agent", lambda: value.started.append("restart"))
    yield value
    value.close()


@pytest.fixture
def client(workspace):
    with TestClient(welcome.create_app(workspace.home, TOKEN, workspace=workspace),
                    base_url="http://127.0.0.1") as value:
        yield value


def post(client, path, payload):
    return client.post(f"/api/agents/{path}", headers=HEADERS, json=payload)


def coding(response, target):
    return next(item for item in response.json()["coding"] if item["id"] == target)


def assert_no_secret(response):
    assert KEY not in response.text and CONNECTOR not in response.text


def test_overview_needs_the_token_and_reads_without_writing(client, scratch):
    assert client.get("/api/agents").status_code == 403
    response = client.get("/api/agents", headers=HEADERS)
    assert response.status_code == 200
    assert_no_secret(response)
    body = response.json()
    assert [item["id"] for item in body["coding"]] == ["claude-code", "codex", "dsh"]
    assert coding(response, "claude-code") == {"id": "claude-code", "installed": True, "state": "off",
                                               "react": False}
    assert coding(response, "codex")["installed"] is False
    assert coding(response, "dsh")["installed"] is False and coding(response, "dsh")["react"] is None
    assert body["cooldown"] == 1800 and body["name"] == "Nova"
    assert body["astrbot"] == {"folder": "", "connected": False, "docker": False, "url": "",
                               "groups": [], "dmUsers": []}
    # Looking never creates another program's folder.
    assert not any(scratch[name].exists() for name in ("claude", "codex", "dsh"))
    assert scratch["claude_cli"].calls == []


def test_claude_code_connect_react_keep_and_remove(client, workspace, scratch):
    response = post(client, "coding", {"target": "claude-code", "connect": True, "react": True})
    assert response.status_code == 200, response.text
    assert_no_secret(response)
    assert coding(response, "claude-code") == {"id": "claude-code", "installed": True, "state": "on",
                                               "react": True}
    remove, add = scratch["claude_cli"].calls
    assert remove[1:] == ["mcp", "remove", "personagent", "--scope", "user"]
    assert add[-3:] == ["--home", str(workspace.home), "mcp"]
    assert "pythonw" not in add[add.index("--") + 1].lower()
    settings = json.loads((scratch["claude"] / "settings.json").read_text(encoding="utf-8"))
    assert settings["hooks"]["Stop"][0]["hooks"][0]["command"].endswith("hook")
    # A reconnect that does not say keeps the hook the user turned on.
    response = post(client, "coding", {"target": "claude-code", "connect": True})
    assert coding(response, "claude-code")["react"] is True
    response = post(client, "coding", {"target": "claude-code", "connect": True, "react": False})
    assert coding(response, "claude-code") == {"id": "claude-code", "installed": True, "state": "on",
                                               "react": False}
    response = post(client, "coding", {"target": "claude-code", "connect": False})
    assert coding(response, "claude-code")["state"] == "off"


def test_claude_code_refusals(client, scratch):
    scratch["claude_cli"].fail = True
    response = post(client, "coding", {"target": "claude-code", "connect": True, "react": False})
    assert response.status_code == 400 and response.json() == {"error": "agents_cli_failed"}
    scratch["installed"].clear()
    response = post(client, "coding", {"target": "claude-code", "connect": True, "react": False})
    assert response.json() == {"error": "agents_no_cli"}
    assert post(client, "coding", {"target": "vim", "connect": True}).json() == {"error": "agents_bad_target"}


def test_a_registration_for_another_home_is_shown_as_other(client, workspace, scratch):
    config = scratch["claude"] / ".claude.json"
    config.parent.mkdir(parents=True)
    config.write_text(json.dumps({"mcpServers": {"personagent": {
        "command": str(Path(__file__)), "args": ["-m", "persona_agent", "--home", "D:/elsewhere", "mcp"]}}}),
        encoding="utf-8")
    assert coding(client.get("/api/agents", headers=HEADERS), "claude-code")["state"] == "other"


def test_a_failed_repair_puts_the_old_registration_back(client, scratch):
    config = scratch["claude"] / ".claude.json"
    config.parent.mkdir(parents=True)
    old = {"type": "stdio", "command": str(Path(__file__)),
           "args": ["-m", "persona_agent", "--home", "D:/elsewhere", "mcp"]}
    config.write_text(json.dumps({"mcpServers": {"personagent": old}}), encoding="utf-8")
    scratch["claude_cli"].fail = True
    response = post(client, "coding", {"target": "claude-code", "connect": True, "react": False})
    assert response.json() == {"error": "agents_cli_failed"}
    assert json.loads(config.read_text(encoding="utf-8"))["mcpServers"]["personagent"] == old
    assert coding(client.get("/api/agents", headers=HEADERS), "claude-code")["state"] == "other"


def test_codex_needs_codex_then_writes_its_config_and_keeps_others(client, workspace, scratch):
    response = post(client, "coding", {"target": "codex", "connect": True, "react": False})
    assert response.json() == {"error": "agents_no_codex"}
    assert not scratch["codex"].exists()
    scratch["codex"].mkdir()
    (scratch["codex"] / "config.toml").write_text('model = "x"\n\n[mcp_servers.other]\ncommand = "o"\n',
                                                  encoding="utf-8")
    response = post(client, "coding", {"target": "codex", "connect": True, "react": True})
    assert coding(response, "codex") == {"id": "codex", "installed": True, "state": "on", "react": True}
    text = (scratch["codex"] / "config.toml").read_text(encoding="utf-8")
    assert "[mcp_servers.other]" in text and "[mcp_servers.personagent]" in text
    assert json.loads((scratch["codex"] / "hooks.json").read_text(encoding="utf-8"))["hooks"]["Stop"]
    response = post(client, "coding", {"target": "codex", "connect": False})
    assert coding(response, "codex")["state"] == "off" and coding(response, "codex")["react"] is False
    assert "[mcp_servers.other]" in (scratch["codex"] / "config.toml").read_text(encoding="utf-8")


def test_dsh_profiles_partial_and_refusals(client, workspace, scratch):
    assert post(client, "coding", {"target": "dsh", "connect": True}).json() == {"error": "agents_no_dsh"}
    for name in ("desktop", "web"):
        (scratch["dsh"] / "profiles" / name).mkdir(parents=True)
        (scratch["dsh"] / "profiles" / name / "cordis.patch.yml").write_text("[]\n", encoding="utf-8")
    assert post(client, "coding", {"target": "dsh", "connect": True, "react": True}).json() == \
        {"error": "agents_no_react"}
    response = post(client, "coding", {"target": "dsh", "connect": True, "react": False})
    assert coding(response, "dsh") == {"id": "dsh", "installed": True, "state": "on", "react": None,
                                       "profiles": 2, "connected": 2}
    (scratch["dsh"] / "profiles" / "headless").mkdir()
    (scratch["dsh"] / "profiles" / "headless" / "cordis.patch.yml").write_text("[]\n", encoding="utf-8")
    item = coding(client.get("/api/agents", headers=HEADERS), "dsh")
    assert item["state"] == "partial" and item["connected"] == 2 and item["profiles"] == 3
    response = post(client, "coding", {"target": "dsh", "connect": False})
    assert coding(response, "dsh")["state"] == "off"


def test_connecting_needs_a_key_and_one_change_at_a_time(client, workspace):
    agents._busy.acquire()
    try:
        assert post(client, "coding", {"target": "codex", "connect": False}).json() == {"error": "busy"}
    finally:
        agents._busy.release()
    (workspace.home / ".env").write_text("PERSONA_NAME=Nova\n", encoding="utf-8")
    assert post(client, "coding", {"target": "claude-code", "connect": True}).json() == \
        {"error": "key_required"}


def test_cooldown_is_written_only_from_the_list(client, workspace):
    response = post(client, "cooldown", {"seconds": 3600})
    assert response.status_code == 200 and response.json()["cooldown"] == 3600
    assert workspace.config()["CODING_REACT_COOLDOWN_S"] == "3600"
    for bad in (5, "3600", True, None):
        assert post(client, "cooldown", {"seconds": bad}).json() == {"error": "agents_bad_cooldown"}
    assert workspace.config()["CODING_REACT_COOLDOWN_S"] == "3600"


def _astrbot(folder: Path) -> Path:
    data = folder / "data"
    data.mkdir(parents=True)
    (data / "cmd_config.json").write_text('{"platform": []}', encoding="utf-8")
    return data


def test_external_astrbot_connect_allow_and_remove(client, workspace, scratch):
    data = _astrbot(scratch["ext"])
    found = client.get("/api/agents", headers=HEADERS).json()["astrbot"]
    assert found["folder"] == str(data) and found["connected"] is False
    response = post(client, "astrbot", {"dataDir": str(scratch["ext"]), "url": ""})
    assert response.status_code == 200, response.text
    assert_no_secret(response)
    assert response.json()["astrbot"]["connected"] is True and "agent" in workspace.started
    assert (data / "plugins" / sw.PLUGIN_NAME).is_dir()
    cfg = sw.read_astrbot_config(data)
    assert cfg["connector_token"] == CONNECTOR and cfg["personagent_url"] == "http://127.0.0.1:8080"
    response = post(client, "astrbot/allow", {"dataDir": str(data), "groups": "123, 456",
                                              "dmUsers": ["789"]})
    assert response.json()["astrbot"]["groups"] == ["123", "456"]
    assert sw.read_astrbot_config(data)["dm_users"] == ["789"]
    assert post(client, "astrbot/allow", {"dataDir": str(data), "groups": ["a b"]}).json() == \
        {"error": "agents_bad_ids"}
    response = post(client, "astrbot", {"dataDir": str(data), "url": "https://bot.example.com"})
    assert response.json()["astrbot"]["url"] == "https://bot.example.com"
    response = post(client, "astrbot/remove", {"dataDir": str(data)})
    assert response.json()["astrbot"]["connected"] is False
    assert not (data / "plugins" / sw.PLUGIN_NAME).exists() and not sw.astrbot_config_path(data).exists()
    assert post(client, "astrbot/remove", {"dataDir": str(data)}).json() == {"error": "agents_not_connected"}
    assert post(client, "astrbot/allow", {"dataDir": str(data), "groups": []}).json() == \
        {"error": "agents_not_connected"}


def test_external_astrbot_refusals(client, workspace, scratch, tmp_path):
    data = _astrbot(scratch["ext"])
    assert post(client, "astrbot", {"dataDir": str(tmp_path / "nothing")}).json() == {"error": "agents_not_astrbot"}
    assert post(client, "astrbot", {"dataDir": ""}).json() == {"error": "agents_not_astrbot"}
    managed = _astrbot(workspace.home / "platforms" / "astrbot")
    assert post(client, "astrbot", {"dataDir": str(managed)}).json() == {"error": "agents_astrbot_managed"}
    assert post(client, "astrbot", {"dataDir": str(data), "url": "http://bot.example.com"}).json() == \
        {"error": "agents_bad_url"}

    class Running:
        def done(self):
            return False
    workspace._future = Running()
    assert post(client, "astrbot", {"dataDir": str(data)}).json() == {"error": "busy"}
    workspace._future = None
    workspace.services.start_agent = lambda: (_ for _ in ()).throw(RuntimeError("no"))
    assert post(client, "astrbot", {"dataDir": str(data)}).json() == {"error": "agents_service_failed"}
    assert not (data / "plugins").exists()


def test_every_error_has_a_sentence_in_both_languages():
    import test_welcome

    js = (welcome.ASSETS / "panels" / "agents.js").read_text(encoding="utf-8")
    en, zh = (test_welcome._table(js, code, "agents.js") for code in ("en", "zh"))
    assert en.keys() == zh.keys() and all(key.startswith("agents_") for key in en)
    assert agents.ERRORS <= en.keys()
    for key, text in zh.items():
        assert not any(word in text for word in ("主人", "您", "吧", "呢", "啦", "哦", "没能", "一下")), key
        assert set(re.findall(r"\{\w+\}", text)) == set(re.findall(r"\{\w+\}", en[key])), key
    for key, text in en.items():
        assert not re.search(r"\w'(t|s|re|ll|ve)\b", text.replace("assistant's", "")), key
        assert "owner" not in text.lower(), key


def test_the_page_keeps_focus_codes_and_one_dark_button():
    js = (welcome.ASSETS / "panels" / "agents.js").read_text(encoding="utf-8")
    body = js[js.index("(() => {"):]
    # Every control the person can use has an id the re-render restores focus to.
    for part in ('idOf(item, "connect")', 'idOf(item, "remove")', 'idOf(item, "react")', '"agents-recheck"',
                 '"agents-astrbot-connect"', '"agents-astrbot-remove"', '"agents-allow-save"',
                 '"agents-astrbot-summary"'):
        assert part in body, part
    # Errors and notes are kept as codes, so a language change translates them.
    assert "= PA.t(" not in body.replace("textContent = PA.t(", "").replace("question = PA.t(", "")
    # Rows of assistants carry no dark button; the AstrBot part has one at a time.
    row = body[body.index("function row("):body.index("function cooldownRow(")]
    assert "primary" not in row
    assert body.count('"primary small') == 2 and 'info.connected ? "secondary' in body
