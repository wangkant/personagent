"""First-run setup, browser chat boundary, and scoped QQ onboarding."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from persona_agent import setup_wizard as sw
from persona_agent import welcome


TOKEN = "test-local-capability"
HEADERS = {welcome.TOKEN_HEADER: TOKEN}


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    value = welcome.Workspace(tmp_path)
    monkeypatch.setattr(sw, "probe_key", lambda *a, **kw: sw.Probe("http://127.0.0.1", 200, ""))
    yield value
    value.close()


@pytest.fixture
def client(workspace):
    with TestClient(welcome.create_app(workspace.home, TOKEN, workspace=workspace),
                    base_url="http://127.0.0.1") as value:
        yield value


def test_page_requires_no_key_but_every_api_requires_the_capability(client):
    assert client.get("/").status_code == 200
    assert client.get("/assets/welcome.js").status_code == 200
    assert client.get("/assets/.env").status_code == 404
    assert client.get("/api/state").status_code == 403
    response = client.get("/api/state", headers=HEADERS)
    assert response.status_code == 200 and response.json()["configured"] is False
    assert response.headers["cache-control"] == "no-store"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]


@pytest.mark.parametrize("extra", [
    {"Origin": "https://other.example"}, {"Host": "other.example"},
    {"X-Forwarded-Host": "localhost"}, {"Forwarded": "for=127.0.0.1"},
])
def test_browser_boundary_rejects_foreign_origins_and_proxy_headers(client, extra):
    assert client.get("/api/state", headers={**HEADERS, **extra}).status_code == 403


def test_one_key_is_enough_and_state_does_not_leak_it(client, workspace):
    key = "sk-local-secret-123456789"
    response = client.post("/api/config", headers=HEADERS, json={"apiKey": key, "lang": "zh"})
    assert response.status_code == 200
    assert response.json()["configured"]
    assert key not in response.text
    values = workspace.config()
    assert values["LLM_BASE_URL"] == "https://api.deepseek.com"
    assert values["PERSONA_NAME"] == "小夏"
    assert values["CONNECTOR_TOKEN"]
    assert (workspace.home / "persona.txt").is_file()
    assert key not in client.get("/api/state", headers=HEADERS).text
    assert client.post("/api/key", headers=HEADERS, json={}).json() == {"apiKey": key}


def test_invalid_key_does_not_replace_a_working_configuration(client, workspace, monkeypatch):
    sw.write_env(workspace.env, {"LLM_API_KEY": "old-key", "LLM_BASE_URL": "https://api.deepseek.com"})
    monkeypatch.setattr(sw, "probe_key", lambda *a, **kw: sw.Probe("url", 401, "echoed-sensitive-key"))
    response = client.post("/api/config", headers=HEADERS, json={"apiKey": "new-key"})
    assert response.status_code == 400 and response.json()["error"] == "key_rejected"
    assert "echoed-sensitive-key" not in response.text
    assert workspace.config()["LLM_API_KEY"] == "old-key"


def test_custom_persona_and_unrelated_settings_survive_editing(client, workspace):
    sw.write_env(workspace.env, {"LLM_API_KEY": "old-key", "LLM_BASE_URL": "https://api.deepseek.com",
                                 "ADMIN_IDS": "qq:7", "PERSONA_NAME": "Mira"})
    persona = workspace.home / "persona.txt"
    persona.write_text("My own character", encoding="utf-8")
    response = client.post("/api/config", headers=HEADERS, json={"character": "custom", "name": "Mira"})
    assert response.status_code == 200
    assert persona.read_text(encoding="utf-8") == "My own character"
    assert workspace.config()["ADMIN_IDS"] == "qq:7"


def test_unknown_provider_or_insecure_remote_url_is_rejected(client):
    for fields in ({"provider": "unknown"}, {"baseUrl": "http://remote.example/v1"},
                   {"baseUrl": "https://user:password@remote.example/v1"}):
        response = client.post("/api/config", headers=HEADERS, json={"apiKey": "test", **fields})
        assert response.status_code == 400


def test_changing_the_api_endpoint_never_sends_the_saved_key(client, workspace, monkeypatch):
    sw.write_env(workspace.env, {"LLM_API_KEY": "old-key", "LLM_BASE_URL": "https://api.deepseek.com"})
    monkeypatch.setattr(sw, "probe_key", lambda *a, **kw: pytest.fail("must not send a saved key to a new endpoint"))
    response = client.post("/api/config", headers=HEADERS, json={"baseUrl": "https://new.example/v1"})
    assert response.status_code == 400 and response.json()["error"] == "key_required"


def test_large_and_malformed_posts_are_rejected(client):
    assert client.post("/api/config", headers=HEADERS, content="x" * 20_000).status_code == 413
    assert client.post("/api/config", headers=HEADERS, content="[]").status_code == 400
    assert client.post("/api/config", headers=HEADERS, content="{").status_code == 400


def test_qq_requires_the_explicit_scope_and_setup_first(client, workspace, monkeypatch):
    calls = []
    monkeypatch.setattr(workspace, "start_job", lambda kind: calls.append(kind))
    assert client.post("/api/qq", headers=HEADERS, json={}).status_code == 400
    assert calls == []
    assert client.post("/api/qq", headers=HEADERS, json={"allowConversations": True}).status_code == 200
    assert calls == ["qq"]


def test_qq_credentials_are_written_without_being_returned(workspace, monkeypatch):
    root = welcome.AstrBotInstallation(workspace.home).root
    data = root / "data"
    data.mkdir(parents=True)
    sw._write_json(data / "cmd_config.json", {"platform": []})
    sw.write_env(workspace.env, {"LLM_API_KEY": "key", "CONNECTOR_TOKEN": "existing-token"})
    monkeypatch.setattr(welcome, "install_astrbot", lambda home: data)

    class Process:
        def __init__(self, argv, **kwargs):
            Path(argv[-1]).write_text(json.dumps({"appid": "app-123", "secret": "qq-private-secret"}), encoding="utf-8")
        def wait(self, timeout):
            return 0
    monkeypatch.setattr(welcome.subprocess, "Popen", Process)
    workspace._bind_qq()
    cfg = sw._read_json(data / "cmd_config.json")
    assert cfg["platform"][0]["type"] == "qq_official"
    assert cfg["platform"][0]["secret"] == "qq-private-secret"
    plugin = sw.read_astrbot_config(data)
    assert plugin["groups"] == ["qq_official:*"]
    assert plugin["dm_users"] == ["qq_official:*"]
    assert "qq-private-secret" not in json.dumps(workspace.summary())
    assert workspace._login_dir is None
    assert not list((workspace.home / "runtime/desktop").glob("qq-login-*/result.json"))


def test_a_failed_background_job_returns_to_a_retryable_state(workspace, monkeypatch):
    sw.write_env(workspace.env, {"LLM_API_KEY": "still-kept"})
    monkeypatch.setattr(workspace, "_bind_qq", lambda: (_ for _ in ()).throw(RuntimeError("private")))
    workspace.start_job("qq")
    workspace._future.result(timeout=5)
    assert workspace.job == {"state": "error", "stage": "", "error": "setup_failed"}
    assert workspace.config()["LLM_API_KEY"] == "still-kept"


def test_chat_posts_to_the_real_character_connector_and_is_serialised(workspace, monkeypatch):
    sw.write_env(workspace.env, {"LLM_API_KEY": "key", "CONNECTOR_TOKEN": "token"})
    monkeypatch.setattr(workspace.services, "start_agent", lambda: None)
    events = []
    class Connector:
        def __init__(self, *args, **kwargs):
            pass
        async def send_event(self, event):
            events.append(event)
            return {"replies": [{"type": "text", "text": "hello"}]}
        async def aclose(self):
            pass
    monkeypatch.setattr(welcome, "_connector_type", lambda: Connector)
    import asyncio
    assert asyncio.run(workspace.chat("hello")) == {"reply": "hello"}
    assert events[0]["platform"] == "browser" and events[0]["conversation_type"] == "dm"
    from persona_agent.server import _validate_event_payload
    assert _validate_event_payload(events[0], connector=True)
    assert workspace.history()["messages"][-1] == {"role": "assistant", "text": "hello"}
    restored = welcome.Workspace(workspace.home)
    try:
        assert restored._conversation == workspace._conversation
        assert restored.history() == workspace.history()
        restored.reset_chat()
        assert restored.history() == {"messages": []}
        assert restored._conversation != workspace._conversation
    finally:
        restored.close()


def test_shutdown_stops_only_owned_services(client, workspace, monkeypatch):
    stopped = []
    monkeypatch.setattr(workspace.services, "shutdown", lambda: stopped.append(True))
    assert client.post("/api/exit", headers=HEADERS, json={}).status_code == 200
    assert stopped and workspace._closed
