"""The tools panel: adding servers three ways, the per-tool settings, Check
and Try, and no secret value ever sent back to the page."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from persona_agent import mcp_tools, welcome

TOKEN = "test-local-capability"
HEADERS = {welcome.TOKEN_HEADER: TOKEN}
STANDIN = str(Path(__file__).with_name("mcp_standin.py"))


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    (home / ".env").write_text("LLM_API_KEY=sk-model\nPERSONA_NAME=Nova\n", encoding="utf-8")
    value = welcome.Workspace(home)
    value.up = False
    monkeypatch.setattr(value.services, "running", lambda name: value.up)
    yield value
    value.close()


@pytest.fixture
def client(workspace):
    with TestClient(welcome.create_app(workspace.home, TOKEN, workspace=workspace),
                    base_url="http://127.0.0.1") as value:
        yield value


def post(client, path, payload):
    return client.post(f"/api/tools/{path}", headers=HEADERS, json=payload)


def test_the_overview_needs_the_token_and_offers_starters_only_with_uvx(client, monkeypatch):
    assert client.get("/api/tools").status_code == 403
    monkeypatch.setattr(mcp_tools, "find_program", lambda name, env=None: "")
    body = client.get("/api/tools", headers=HEADERS).json()
    assert body == {"servers": [], "starters": [], "uvx": False, "running": False}
    monkeypatch.setattr(mcp_tools, "find_program", lambda name, env=None: "/bin/uvx")
    body = client.get("/api/tools", headers=HEADERS).json()
    assert [s["id"] for s in body["starters"]] == ["time", "fetch"]
    added = post(client, "add", {"starter": "time"}).json()
    assert added["added"] == ["time"] and [s["id"] for s in added["starters"]] == ["fetch"]
    assert added["servers"][0]["command"] == "uvx" and added["servers"][0]["args"] == ["mcp-server-time"]


def test_a_pasted_block_or_filled_fields_add_servers_and_secrets_stay_home(client, workspace):
    snippet = json.dumps({"mcpServers": {"remote": {"url": "https://example.com/mcp",
                                                    "headers": {"Authorization": "Bearer hdr-secret"}}}})
    response = post(client, "add", {"snippet": snippet})
    assert response.status_code == 200 and "hdr-secret" not in response.text
    response = post(client, "add", {"command": sys.executable, "args": STANDIN + "\n", "env": "API_KEY=env-secret\n",
                                    "name": "stand"})
    assert response.status_code == 200 and "env-secret" not in response.text
    view = client.get("/api/tools", headers=HEADERS)
    assert "env-secret" not in view.text and "hdr-secret" not in view.text
    servers = {s["name"]: s for s in view.json()["servers"]}
    assert servers["stand"]["env"] == [{"name": "API_KEY", "set": True}]
    assert servers["remote"]["headers"] == [{"name": "Authorization", "set": True}]
    saved = json.loads(mcp_tools.config_path(workspace.home).read_text(encoding="utf-8"))
    assert saved["mcpServers"]["stand"]["env"] == {"API_KEY": "env-secret"}
    assert post(client, "add", {"command": "x", "name": "stand"}).json() == {"error": "tools_name_taken"}
    assert post(client, "add", {"snippet": "nonsense"}).json() == {"error": "tools_bad_snippet"}
    assert post(client, "add", {"url": "https://x.example/sse"}).json() == {"error": "tools_sse_unsupported"}


def test_check_try_switch_and_remove(client, workspace):
    post(client, "add", {"command": sys.executable, "args": STANDIN, "name": "stand"})
    checked = post(client, "check", {"server": "stand"}).json()
    assert checked["ok"] is True and checked["tools"] > 3
    tools = {t["name"]: t for t in checked["view"]["servers"][0]["tools"]}
    assert tools["echo"]["enabled"] is True and tools["echo"]["who"] == "admin"
    assert tools["echo"]["description"] == "Say the text back."
    tried = post(client, "call", {"server": "stand", "tool": "echo", "arguments": {"text": "hello"}}).json()
    assert tried["ok"] and tried["text"] == "hello" and tried["isError"] is False
    wrong = post(client, "call", {"server": "stand", "tool": "add", "arguments": {"a": "x", "b": 1}}).json()
    assert wrong == {"ok": False, "error": "bad_arguments", "detail": "arguments.a: expected integer"}
    view = post(client, "set", {"server": "stand", "tool": "echo", "who": "anyone", "enabled": False}).json()
    echo = next(t for t in view["servers"][0]["tools"] if t["name"] == "echo")
    assert echo["who"] == "anyone" and echo["enabled"] is False
    assert post(client, "set", {"server": "stand", "tool": "echo", "who": "all"}).json() == {"error": "tools_bad_request"}
    assert post(client, "remove", {"server": "stand"}).json()["servers"] == []
    assert post(client, "remove", {"server": "stand"}).json() == {"error": "tools_unknown_server"}


def test_a_server_that_does_not_start_says_why(client):
    post(client, "add", {"command": sys.executable, "args": f"{STANDIN}\n--die", "name": "broken"})
    checked = post(client, "check", {"server": "broken"}).json()
    assert checked["ok"] is False and checked["error"] == "exited"
    assert "cannot open the database" in checked["detail"]
    post(client, "add", {"command": "no-such-program-personagent-test", "name": "gone"})
    assert post(client, "check", {"server": "gone"}).json()["error"] == "not_found"


def test_every_page_string_is_in_english_and_chinese_and_every_code_is_named():
    source = (welcome.ASSETS / "panels" / "tools.js").read_text(encoding="utf-8")
    en, zh = source.split("\n  zh: {\n")
    keys_en = set(re.findall(r"^    (tools_\w+): ", en, re.M))
    keys_zh = set(re.findall(r"^    (tools_\w+): ", zh, re.M))
    assert keys_en and keys_en == keys_zh
    from persona_agent.panels import tools
    assert tools.ERRORS <= keys_en
    for code in mcp_tools.ERROR_SENTENCES:
        assert f"tools_err_{code}" in keys_en, code
    page = (welcome.ASSETS / "index.html").read_text(encoding="utf-8")
    assert 'id="tools-root"' in page and "/assets/panels/tools.js" in page


def test_a_session_from_another_device_adds_addresses_but_no_programs(client, workspace):
    from persona_agent.panels import tools as panel

    block = json.dumps({"mcpServers": {"prog": {"command": sys.executable, "args": [STANDIN]}}})
    for payload in ({"snippet": block}, {"command": sys.executable, "args": STANDIN}, {"starter": "time"}):
        with pytest.raises(ValueError, match="^tools_local_only$"):
            panel.add(workspace, {**payload, "_remote": True})
    assert mcp_tools.load_config(workspace.home)["mcpServers"] == {}
    # Nor an address on this computer or its network.
    for url in ("http://127.0.0.1:9/mcp", "http://localhost:9/mcp", "http://10.0.0.5/mcp",
                "http://169.254.169.254/mcp", "http://[::1]:9/mcp", "http://192.168.1.2/mcp"):
        with pytest.raises(ValueError, match="^tools_local_address$"):
            panel.add(workspace, {"url": url, "name": "inner", "_remote": True})
    added = panel.add(workspace, {"url": "https://8.8.8.8/mcp", "name": "far", "_remote": True})
    assert added["added"] == ["far"]
    # Where the request came from is the server's to say, never the page's.
    local = post(client, "add", {"snippet": block, "_remote": True})
    assert local.status_code == 200 and "prog" in local.json()["added"]


def test_a_remote_session_cannot_check_or_call_an_inward_address(tmp_path, monkeypatch):
    from persona_agent import pageaccess
    from persona_agent import setup_wizard as sw

    for name in (*pageaccess.SETTINGS, pageaccess.CONTAINER_ENV):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(pageaccess, "FAIL_DELAY_S", 0.0)
    password = "plum-orchard-41-lantern"
    sw.write_env(tmp_path / ".env", {"PAGE_HOST": "0.0.0.0", "PAGE_PASSWORD": pageaccess.hash_password(password)})
    # Written by hand on the computer itself, then used from a phone.
    mcp_tools.add_servers(tmp_path, {"inner": {"url": "http://127.0.0.1:9/mcp"}})
    space = welcome.Workspace(tmp_path)
    app = welcome.create_app(space.home, TOKEN, workspace=space, gate=pageaccess.Gate(space.home))
    try:
        with TestClient(app, base_url="http://192.168.1.5:8090", client=("192.168.1.20", 50000)) as phone:
            phone.post("/auth/signin", json={"password": password})
            session = {pageaccess.SESSION_HEADER: "1"}
            for path, payload in (("check", {"server": "inner"}),
                                  ("call", {"server": "inner", "tool": "echo", "arguments": {}})):
                answer = phone.post(f"/api/tools/{path}", json=payload, headers=session)
                assert answer.json() == {"error": "tools_local_address"}, answer.text
    finally:
        space.close()
