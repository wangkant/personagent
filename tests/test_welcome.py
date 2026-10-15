"""First-run setup, browser chat boundary, and scoped platform connections."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from persona_agent import connections as conn
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


def _managed(workspace, monkeypatch, template=None):
    """A managed AstrBot that is already installed, with a fixed template."""
    data = welcome.AstrBotInstallation(workspace.home).root / "data"
    data.mkdir(parents=True)
    sw._write_json(data / "cmd_config.json", {"platform": []})
    sw.write_env(workspace.env, {"LLM_API_KEY": "key", "CONNECTOR_TOKEN": "existing-token"})
    monkeypatch.setattr(welcome, "install_astrbot", lambda home: data)
    monkeypatch.setattr(conn, "astrbot_template", lambda installation, kind: dict(template or {}))
    return data


def test_connecting_requires_the_scope_and_valid_fields_before_any_work(client, workspace, monkeypatch):
    sw.write_env(workspace.env, {"LLM_API_KEY": "key"})
    jobs = []
    monkeypatch.setattr(workspace, "_job", lambda *args: jobs.append(args))
    url = "/api/platforms/connect"
    telegram = {"platform": "telegram", "values": {"telegram_token": "bot:token"}}
    assert client.post(url, headers=HEADERS, json=telegram).json()["error"] == "permission_required"
    for payload, error in (({"platform": "nowhere"}, "invalid_platform"),
                           ({"platform": "telegram", "values": {}}, "field_required"),
                           ({"platform": "mattermost", "values": {"mattermost_url": "ftp://x",
                                                                 "mattermost_bot_token": "t"}},
                            "invalid_field")):
        response = client.post(url, headers=HEADERS, json={**payload, "allowConversations": True})
        assert response.status_code == 400 and response.json()["error"] == error
    assert jobs == []
    response = client.post(url, headers=HEADERS, json={**telegram, "allowConversations": True})
    assert response.status_code == 200
    workspace._future.result(timeout=5)
    assert jobs == [("connect", conn.platform("telegram"), {"telegram_token": "bot:token"})]
    assert client.post(url, headers=HEADERS, json={"platform": "qq_official", "allowConversations": True}
                       ).status_code == 200
    workspace._future.result(timeout=5)
    assert jobs[-1] == ("scan", conn.platform("qq_official"))


def test_scanned_credentials_are_written_without_being_returned(workspace, monkeypatch):
    data = _managed(workspace, monkeypatch,
                    {"id": "default", "type": "qq_official", "enable": True, "appid": "",
                     "secret": "", "use_markdown": True})

    class Process:
        def __init__(self, argv, **kwargs):
            assert argv[2] == "qq_official"
            Path(argv[-1]).write_text(json.dumps({"appid": "app-123", "secret": "qq-private-secret"}),
                                      encoding="utf-8")
        def wait(self, timeout):
            return 0
    monkeypatch.setattr(welcome.subprocess, "Popen", Process)
    workspace._scan(conn.platform("qq_official"))
    entry = sw._read_json(data / "cmd_config.json")["platform"][0]
    assert entry == {"id": "qq_official", "type": "qq_official", "enable": True,
                     "appid": "app-123", "secret": "qq-private-secret", "use_markdown": True}
    plugin = sw.read_astrbot_config(data)
    assert plugin["groups"] == ["qq_official:*"]
    assert plugin["dm_users"] == ["qq_official:*"]
    summary = workspace.summary()
    assert summary["platforms"] == ["qq_official"]
    assert "qq-private-secret" not in json.dumps(summary)
    assert workspace._login_dir is None
    assert not list((workspace.home / "runtime/desktop").glob("login-*/result.json"))


def test_a_failed_scan_saves_nothing(workspace, monkeypatch):
    data = _managed(workspace, monkeypatch)

    class Process:
        def __init__(self, argv, **kwargs):
            pass
        def wait(self, timeout):
            return 1
    monkeypatch.setattr(welcome.subprocess, "Popen", Process)
    with pytest.raises(RuntimeError, match="scan_failed"):
        workspace._scan(conn.platform("weixin_oc"))
    assert sw._read_json(data / "cmd_config.json")["platform"] == []


def test_each_platform_keeps_astrbot_defaults_and_opens_only_itself(workspace, monkeypatch):
    data = _managed(workspace, monkeypatch,
                    {"id": "telegram", "type": "telegram", "enable": True, "telegram_token": "",
                     "start_message": "Hello, I'm AstrBot!", "telegram_command_register": True,
                     "telegram_polling_restart_delay": 5.0})
    workspace._connect(conn.platform("telegram"), {"telegram_token": "bot:token"})
    monkeypatch.setattr(conn, "astrbot_template", lambda installation, kind: {})
    workspace._connect(conn.platform("discord"), {"discord_token": "discord-token"})
    entries = {p["id"]: p for p in sw._read_json(data / "cmd_config.json")["platform"]}
    assert entries["telegram"]["telegram_token"] == "bot:token"
    assert entries["telegram"]["start_message"] == ""
    assert entries["telegram"]["telegram_command_register"] is False
    assert entries["telegram"]["telegram_polling_restart_delay"] == 5.0
    assert entries["discord"]["discord_command_register"] is False
    assert sw.read_astrbot_config(data)["groups"] == ["telegram:*", "discord:*"]
    assert workspace.summary()["platforms"] == ["telegram", "discord"]

    workspace._disconnect(conn.platform("telegram"))
    assert [p["id"] for p in sw._read_json(data / "cmd_config.json")["platform"]] == ["discord"]
    plugin = sw.read_astrbot_config(data)
    assert plugin["groups"] == ["discord:*"] and plugin["dm_users"] == ["discord:*"]


def test_onebot_is_the_one_platform_read_as_bare_qq_numbers(workspace, monkeypatch):
    data = _managed(workspace, monkeypatch)
    workspace._connect(conn.platform("aiocqhttp"), conn.clean_values(conn.platform("aiocqhttp"), {}))
    entry = sw._read_json(data / "cmd_config.json")["platform"][0]
    assert entry["ws_reverse_host"] == "127.0.0.1" and entry["ws_reverse_port"] == 6199
    assert "aiocqhttp" not in sw.read_astrbot_config(data)["excluded_platforms"]
    assert sw.env_get(workspace.env, "CONNECTOR_QQ_PLATFORMS") == "aiocqhttp"
    workspace._disconnect(conn.platform("aiocqhttp"))
    assert "aiocqhttp" in sw.read_astrbot_config(data)["excluded_platforms"]
    assert sw.env_get(workspace.env, "CONNECTOR_QQ_PLATFORMS") == ""


def test_a_failed_background_job_returns_to_a_retryable_state(workspace, monkeypatch):
    sw.write_env(workspace.env, {"LLM_API_KEY": "still-kept"})
    monkeypatch.setattr(workspace, "_connect", lambda *a: (_ for _ in ()).throw(RuntimeError("private")))
    workspace.start_job("connect", "telegram", {"telegram_token": "bot:token"})
    workspace._future.result(timeout=5)
    assert workspace.job["state"] == "error" and workspace.job["error"] == "setup_failed"
    assert workspace.job["platform"] == "telegram"
    assert "private" not in json.dumps(workspace.summary())
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


def test_credentials_the_platform_refuses_are_rolled_back(workspace, monkeypatch):
    data = _managed(workspace, monkeypatch)
    monkeypatch.setattr(workspace.services, "start_agent", lambda: None)
    monkeypatch.setattr(workspace.services, "restart_astrbot", lambda: 0)
    seen = []
    def logged(name, offset, pattern, seconds):
        seen.append(pattern.pattern)
        return True
    monkeypatch.setattr(workspace.services, "logged", logged)
    workspace.start_job("connect", "telegram", {"telegram_token": "bot:refused-secret"})
    workspace._future.result(timeout=5)
    assert workspace.job["state"] == "error" and workspace.job["error"] == "platform_rejected"
    assert "telegram" in seen[0]
    assert sw._read_json(data / "cmd_config.json")["platform"] == []
    assert "telegram:*" not in sw.read_astrbot_config(data)["groups"]
    assert "refused-secret" not in json.dumps(workspace.summary())


def test_an_accepted_connection_ends_ready(workspace, monkeypatch):
    _managed(workspace, monkeypatch)
    monkeypatch.setattr(workspace.services, "start_agent", lambda: None)
    monkeypatch.setattr(workspace.services, "restart_astrbot", lambda: 0)
    monkeypatch.setattr(workspace.services, "logged", lambda *a: False)
    workspace.start_job("connect", "kook", {"kook_bot_token": "kook-token"})
    workspace._future.result(timeout=5)
    assert workspace.job == {"state": "ready", "stage": "ready", "error": "", "action": "connect",
                             "platform": "kook"}
    assert workspace.summary()["platforms"] == ["kook"]
