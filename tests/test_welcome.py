"""First-run setup, browser chat boundary, and scoped platform connections."""
from __future__ import annotations

import json

from fastapi.testclient import TestClient
import httpx
import pytest

from persona_agent import connections as conn
from persona_agent.direct import base as direct_base
from persona_agent import setup_wizard as sw
from persona_agent import welcome


TOKEN = "test-local-capability"
REAL_ASYNC_CLIENT = httpx.AsyncClient
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


def test_the_persona_is_shown_as_the_agent_reads_it_and_edits_become_its_own(client, workspace, monkeypatch):
    sw.write_env(workspace.env, {"LLM_API_KEY": "key", "PERSONA_NAME": "Mira", "AGENT_LANG": "en"})
    persona = workspace.home / "persona.txt"
    # No persona.txt yet: the agent fills in the bundled template, and so does the page.
    assert "Mira" in client.get("/api/persona", headers=HEADERS).json()["text"]
    assert not persona.exists()
    restarts = []
    monkeypatch.setattr(workspace, "_restart_agent", lambda: restarts.append(True))
    state = client.post("/api/persona", headers=HEADERS,
                        json={"text": "  Your name is Mira. You only talk about tea.\r\n"}).json()
    assert persona.read_text(encoding="utf-8") == "Your name is Mira. You only talk about tea.\n"
    assert state["character"] == "custom" and restarts == [True]
    assert client.get("/api/persona", headers=HEADERS).json()["text"] == "Your name is Mira. You only talk about tea."
    for bad in ("   ", "x" * (welcome.PERSONA_LIMIT + 1)):
        response = client.post("/api/persona", headers=HEADERS, json={"text": bad})
        assert response.status_code == 400 and response.json()["error"] == "invalid_persona"
    assert "tea" in persona.read_text(encoding="utf-8") and restarts == [True]


def test_a_saved_persona_restarts_only_an_agent_that_was_running(workspace, monkeypatch):
    running, calls = {"agent": True}, []
    monkeypatch.setattr(workspace.services, "running", lambda name: running.get(name, False))
    monkeypatch.setattr(workspace.services, "stop", lambda name: calls.append(("stop", name)))
    monkeypatch.setattr(workspace.services, "start_agent", lambda: calls.append(("start", "agent")))
    workspace.save_persona("First")
    assert calls == [("stop", "agent"), ("start", "agent")]
    running["agent"], calls[:] = False, []
    workspace.save_persona("Second")
    assert calls == [("stop", "agent")]
    assert (workspace.home / "persona.txt").read_text(encoding="utf-8") == "Second\n"


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
    assert client.post(url, headers=HEADERS, json={"platform": "weixin_oc", "allowConversations": True}
                       ).status_code == 200
    workspace._future.result(timeout=5)
    assert jobs[-1] == ("scan", conn.platform("weixin_oc"))
    # QQ scans unless the page says the values were pasted; WeChat has nothing to paste.
    assert client.post(url, headers=HEADERS, json={"platform": "qq_official", "allowConversations": True}
                       ).status_code == 200
    workspace._future.result(timeout=5)
    assert jobs[-1] == ("scan", conn.platform("qq_official"))
    pasted = {"platform": "qq_official", "mode": "paste", "values": {"appid": "102", "secret": "s"},
              "allowConversations": True}
    assert client.post(url, headers=HEADERS, json=pasted).status_code == 200
    workspace._future.result(timeout=5)
    assert jobs[-1] == ("connect", conn.platform("qq_official"), {"appid": "102", "secret": "s"})
    response = client.post(url, headers=HEADERS, json={"platform": "weixin_oc", "mode": "paste",
                                                        "allowConversations": True})
    assert response.status_code == 400 and response.json()["error"] == "invalid_platform"


def test_a_wechat_scan_stores_the_token_where_the_page_never_returns_it(workspace, monkeypatch):
    data = _managed(workspace, monkeypatch)
    # A WeChat bot connected through AstrBot before is handed over, not polled twice.
    conn.save_entry(data, {"id": "weixin_oc", "type": "weixin_oc", "enable": True})
    from persona_agent.direct import weixin

    async def login(client, show):
        show("https://scan.example/q")
        assert workspace.job["stage"] == "scan"
        assert workspace.job["qrImage"].startswith("data:image/png;base64,")
        return {"weixin_oc_token": "wx-private-token", "weixin_oc_account_id": "b@im.bot"}
    monkeypatch.setattr(weixin, "login", login)
    workspace.job = {"state": "working", "stage": "prepare", "platform": "weixin_oc"}
    workspace._scan_direct(conn.platform("weixin_oc"))
    assert direct_base.load_credentials(workspace.home)["weixin_oc"]["weixin_oc_token"] == "wx-private-token"
    assert conn.connected(data) == []
    summary = workspace.summary()
    assert summary["platforms"] == ["weixin_oc"] and summary["platformStatus"]["weixin_oc"] == "paused"
    assert "wx-private-token" not in json.dumps(summary)


def test_a_qq_scan_keeps_the_bound_bot_and_hands_it_over_from_astrbot(workspace, monkeypatch):
    data = _managed(workspace, monkeypatch)
    conn.save_entry(data, {"id": "qq_official", "type": "qq_official", "enable": True})
    from persona_agent.direct import qq

    async def bind(client, show):
        show("https://q.qq.com/qqbot/openclaw/connect.html?task_id=t1&_wv=2")
        assert workspace.job["stage"] == "scan" and workspace.job["qrImage"].startswith("data:image/png")
        return {"appid": "102", "secret": "qq-private-secret"}
    monkeypatch.setattr(qq, "bind", bind)
    workspace.job = {"state": "working", "stage": "prepare", "platform": "qq_official"}
    workspace._scan_direct(conn.platform("qq_official"))
    assert direct_base.load_credentials(workspace.home)["qq_official"] == {
        "appid": "102", "secret": "qq-private-secret"}
    assert conn.connected(data) == []
    assert "qq-private-secret" not in json.dumps(workspace.summary())

    async def refused(client, show):
        raise qq.BindFailed("expired")
    monkeypatch.setattr(qq, "bind", refused)
    with pytest.raises(RuntimeError, match="scan_failed"):
        workspace._scan_direct(conn.platform("qq_official"))


def test_a_failed_scan_saves_nothing(workspace, monkeypatch):
    from persona_agent.direct import weixin

    async def login(client, show):
        raise weixin.LoginFailed("expired")
    monkeypatch.setattr(weixin, "login", login)
    with pytest.raises(RuntimeError, match="scan_failed"):
        workspace._scan_direct(conn.platform("weixin_oc"))
    assert direct_base.load_credentials(workspace.home) == {}


class FakeDirect:
    def __init__(self, refusal=None):
        self.refusal = refusal

    async def check(self):
        if self.refusal:
            raise self.refusal
        return "bot"

    async def close(self):
        pass


def _direct_job(workspace, monkeypatch, platform, states):
    sw.write_env(workspace.env, {"LLM_API_KEY": "key"})
    monkeypatch.setattr(welcome.direct, "platform_for", lambda kind, values, home: platform)
    monkeypatch.setattr(workspace.services, "start_agent", lambda: None)
    monkeypatch.setattr(workspace.services, "restart_direct",
                        lambda between=None: between() if between else None)
    monkeypatch.setattr(workspace.services, "running", lambda name: name == "direct")
    monkeypatch.setattr(direct_base, "read_status", lambda home: next(states))
    monkeypatch.setattr(welcome.time, "sleep", lambda s: None)


def test_a_direct_platform_is_checked_then_kept_once_it_connects(workspace, monkeypatch):
    states = iter([{}, {"telegram": {"state": "connecting"}}, {"telegram": {"state": "connected"}}]
                  + [{"telegram": {"state": "connected"}}] * 5)
    _direct_job(workspace, monkeypatch, FakeDirect(), states)
    workspace.start_job("connect", "telegram", {"telegram_token": "123:abc"})
    workspace._future.result(timeout=5)
    assert workspace.job["state"] == "ready", workspace.job
    assert direct_base.load_credentials(workspace.home) == {"telegram": {"telegram_token": "123:abc"}}
    summary = workspace.summary()
    assert summary["platforms"] == ["telegram"] and summary["platformStatus"] == {"telegram": "running"}


def test_a_direct_platform_refused_up_front_is_never_stored(workspace, monkeypatch):
    _direct_job(workspace, monkeypatch, FakeDirect(direct_base.Refused("token_rejected")), iter([]))
    workspace.start_job("connect", "telegram", {"telegram_token": "123:abc"})
    workspace._future.result(timeout=5)
    assert workspace.job["error"] == "token_rejected"
    assert direct_base.load_credentials(workspace.home) == {}


def test_a_direct_platform_refused_after_login_is_rolled_back_with_its_reason(workspace, monkeypatch):
    states = iter([{"discord": {"state": "refused", "detail": "message_content_intent_off"}}] * 3)
    _direct_job(workspace, monkeypatch, FakeDirect(), states)
    workspace.start_job("connect", "discord", {"discord_token": "tok"})
    workspace._future.result(timeout=5)
    assert workspace.job["error"] == "message_content_intent_off"
    assert direct_base.load_credentials(workspace.home) == {}


def test_an_unreachable_platform_is_reported_as_a_network_problem(workspace, monkeypatch):
    _direct_job(workspace, monkeypatch, FakeDirect(ConnectionError("getMe: ConnectTimeout")), iter([]))
    workspace.start_job("connect", "telegram", {"telegram_token": "123:abc"})
    workspace._future.result(timeout=5)
    assert workspace.job["error"] == "network_failed"


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
    workspace.start_job("connect", "kook", {"kook_bot_token": "kook-token"})
    workspace._future.result(timeout=5)
    assert workspace.job["state"] == "error" and workspace.job["error"] == "setup_failed"
    assert workspace.job["platform"] == "kook"
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
    workspace.start_job("connect", "kook", {"kook_bot_token": "refused-secret"})
    workspace._future.result(timeout=5)
    assert workspace.job["state"] == "error" and workspace.job["error"] == "platform_rejected"
    assert "kook" in seen[0]
    assert sw._read_json(data / "cmd_config.json")["platform"] == []
    assert "kook:*" not in sw.read_astrbot_config(data)["groups"]
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


def test_a_refused_direct_platform_shows_as_failed_even_after_the_runner_exits(workspace, monkeypatch):
    direct_base.save_credentials(workspace.home, "telegram", {"telegram_token": "t"})
    direct_base.save_credentials(workspace.home, "discord", {"discord_token": "d"})
    direct_base.Status(workspace.home).set("telegram", "refused", "token_rejected")
    monkeypatch.setattr(workspace.services, "running", lambda name: False)
    assert workspace.summary()["platformStatus"] == {"telegram": "failed", "discord": "paused"}
    assert [p["id"] for p in welcome.conn.catalog() if not p["groups"]] == ["weixin_oc"]


def test_moving_a_platform_off_astrbot_restarts_it_and_disconnecting_clears_both(workspace, monkeypatch):
    data = _managed(workspace, monkeypatch)
    conn.save_entry(data, {"id": "telegram", "type": "telegram", "enable": True})
    conn.save_entry(data, {"id": "kook", "type": "kook", "enable": True})
    states = iter([{"telegram": {"state": "connected"}}] * 5)
    _direct_job(workspace, monkeypatch, FakeDirect(), states)
    calls = []
    monkeypatch.setattr(workspace.services, "restart_astrbot", lambda: calls.append("restart") or 0)
    monkeypatch.setattr(workspace.services, "start_astrbot", lambda: calls.append("start"))
    workspace.start_job("connect", "telegram", {"telegram_token": "123:abc"})
    workspace._future.result(timeout=5)
    assert workspace.job["state"] == "ready", workspace.job
    assert calls == ["restart"] and conn.connected(data) == ["kook"]

    # A WeChat bot connected through AstrBot before direct connections existed.
    conn.save_entry(data, {"id": "weixin_oc", "type": "weixin_oc", "enable": True})
    state = welcome.direct.state_path(workspace.home, "weixin_oc")
    state.parent.mkdir(parents=True, exist_ok=True)
    state.write_text("{}", encoding="utf-8")
    workspace._disconnect_direct(conn.platform("weixin_oc"))
    assert conn.connected(data) == ["kook"] and state.exists()      # the old process may still run
    workspace._clear_stale_state()
    assert not state.exists()


def test_features_keep_keys_out_of_state_and_never_forward_one(client, workspace, monkeypatch):
    sw.write_env(workspace.env, {"LLM_API_KEY": "chat-key", "LLM_BASE_URL": "https://api.example.com/v1"})
    monkeypatch.setattr(workspace, "_restart_agent", lambda: None)
    url = "/api/features"
    state = client.post(url, headers=HEADERS, json={
        "search": {"tavilyKey": "tvly-secret"},
        "vision": {"enabled": True, "model": "vl-model", "sameAsChat": True},
        "proactive": {"enabled": True, "platforms": ["qq_official"]}}).json()
    values = workspace.config()
    assert values["TAVILY_API_KEY"] == "tvly-secret" and values["VISION_API_KEY"] == "chat-key"
    assert values["VISION_BASE_URL"] == "https://api.example.com/v1" and values["PROACTIVE_PLATFORMS"] == "qq_official"
    assert state["features"]["vision"] == {"enabled": True, "model": "vl-model", "sameAsChat": True,
                                           "baseUrl": "", "keyHint": ""}
    assert state["features"]["search"] == "tavily" and state["features"]["proactive"]["enabled"]
    assert "tvly-secret" not in json.dumps(state) and "chat-key" not in json.dumps(state)
    # Another vision address never gets the saved key: a blank key there is refused.
    response = client.post(url, headers=HEADERS, json={
        "vision": {"enabled": True, "model": "vl", "baseUrl": "https://other.example.com/v1", "apiKey": ""}})
    assert response.status_code == 400 and response.json()["error"] == "key_required"
    for bad, error in (({"vision": {"enabled": True, "model": "vl", "baseUrl": "http://remote.example.com",
                                    "apiKey": "k"}}, "https_required"),
                       ({"vision": {"enabled": True, "model": ""}}, "model_required"),
                       ({"proactive": {"platforms": ["nowhere"]}}, "invalid_feature"),
                       ({"search": {"tavilyKey": "has space"}}, "invalid_feature")):
        response = client.post(url, headers=HEADERS, json=bad)
        assert response.status_code == 400 and response.json()["error"] == error, bad
    # dotenv would expand ${...} into another setting, the chat key included.
    for bad, error in (({"search": {"tavilyKey": "${LLM_API_KEY}"}}, "invalid_feature"),
                       ({"vision": {"enabled": True, "model": "vl", "baseUrl": "https://x.example/v1",
                                    "apiKey": "${LLM_API_KEY}"}}, "invalid_feature")):
        response = client.post(url, headers=HEADERS, json=bad)
        assert response.status_code == 400 and response.json()["error"] == error, bad
    response = client.post("/api/config", headers=HEADERS, json={"apiKey": "k", "name": "${LLM_API_KEY}"})
    assert response.status_code == 400 and response.json()["error"] == "invalid_character"
    cleared = client.post(url, headers=HEADERS, json={"search": {"clear": True}}).json()
    assert cleared["features"]["search"] == "free" and not cleared["features"]["vision"]["enabled"]
    assert workspace.config()["VISION_API_KEY"] == "chat-key"   # off keeps the key for next time


def _activity_service(workspace, monkeypatch, handler):
    """The character service's Activity API, answered by `handler`."""
    monkeypatch.setattr(workspace.services, "running", lambda name: name == "agent")
    monkeypatch.setattr(welcome.httpx, "AsyncClient",
                        lambda **kw: REAL_ASYNC_CLIENT(transport=httpx.MockTransport(handler), **kw))
    runtime = workspace.home / "runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    (runtime / "dashboard.token").write_text("service-token\n", encoding="utf-8")


CONVERSATION = {
    "id": "telegram:-100", "platform": "telegram", "kind": "group",
    "pending": [{"id": "abc123", "type": "preference_pair", "reply": "dune again", "better": "paddington 2",
                 "created": 5.0, "actions": ["promote", "reject"], "checklist": {"rules": []},
                 "evidence": [{"speaker": "Priya"}, {"speaker": "Priya"}, {"speaker": ""}]}],
    "learned": [{"id": "def456", "type": "positive_example", "reply": "fair", "better": "",
                 "created": 4.0, "actions": ["rollback"], "evidence": [], "history": [{"state": "x"}]}],
    "past": [{"id": "old", "type": "preference_pair"}],
    "memories": [{"text": "match night at Sam's", "by": "Sam", "time": 3.0, "auto": False}],
    "decisions": [{"ts": 2.0, "mode": "called", "spoke": True, "reason": "addressed", "excerpt": "sure",
                   "answered": "Nova?", "sender": "Alex", "count": 1},
                  {"ts": 1.0, "mode": "", "spoke": False, "reason": "below the trigger count",
                   "excerpt": "lol", "answered": "", "sender": "Sam", "count": 3}],
}


def test_activity_reads_the_service_with_its_token_and_keeps_only_what_the_view_shows(client, workspace,
                                                                                      monkeypatch):
    seen = []
    def handler(request):
        seen.append(request)
        if request.url.path == "/api/dashboard/conversations":
            return httpx.Response(200, json={"conversations": [
                {"id": "telegram:-100", "platform": "telegram", "kind": "group", "last_activity": 9.0,
                 "memories": 1, "learned": 1, "pending": 1},
                {"id": "private:browser:x", "platform": "browser", "kind": "dm", "last_activity": 8.0,
                 "memories": 0, "learned": 0, "pending": 0}]})
        return httpx.Response(200, json=CONVERSATION)
    _activity_service(workspace, monkeypatch, handler)
    listed = client.get("/api/activity", headers=HEADERS).json()
    assert listed["running"] and not listed["off"]
    assert [c["id"] for c in listed["chats"]] == ["telegram:-100", "private:browser:x"]
    assert listed["chats"][0] == {"id": "telegram:-100", "platform": "telegram", "kind": "group",
                                  "last": 9.0, "review": 1, "learned": 1, "notes": 1}
    chat = client.get("/api/activity/chat", params={"id": "telegram:-100"}, headers=HEADERS).json()
    assert seen[-1].url.params["id"] == "telegram:-100"
    assert all(r.headers["x-personagent-dashboard-token"] == "service-token" for r in seen)
    assert chat["review"] == [{"id": "abc123", "kind": "wording", "said": "dune again", "better": "paddington 2",
                               "when": 5.0, "from": ["Priya"], "actions": ["promote", "reject"]}]
    assert chat["learned"][0]["kind"] == "repeat" and chat["learned"][0]["actions"] == ["rollback"]
    assert chat["notes"] == [{"text": "match night at Sam's", "by": "Sam", "when": 3.0}]
    # Oldest first, like a chat; the service lists newest first.
    assert [r["text"] for r in chat["recent"]] == ["lol", "sure"] and chat["recent"][0]["count"] == 3
    assert "checklist" not in json.dumps(chat) and "past" not in chat and "history" not in json.dumps(chat)


def test_activity_decisions_go_to_the_service_as_writes_and_come_back_as_the_chat(client, workspace,
                                                                                monkeypatch):
    writes = []
    def handler(request):
        if request.method == "POST":
            writes.append(request)
            if "/stale/" in request.url.path:
                return httpx.Response(409, json={"error": "cannot", "code": "illegal_transition"})
            return httpx.Response(200, json={"ok": True})
        return httpx.Response(200, json=CONVERSATION)
    _activity_service(workspace, monkeypatch, handler)
    url = "/api/activity/decide"
    chat = client.post(url, headers=HEADERS, json={"id": "abc123", "action": "promote",
                                                   "chat": "telegram:-100"}).json()
    assert chat["id"] == "telegram:-100"
    request = writes[-1]
    assert request.url.path == "/api/dashboard/candidates/abc123/promote"
    assert request.headers["x-personagent-dashboard"] == "1"
    assert request.headers["content-type"] == "application/json"
    assert json.loads(request.content) == {"reason": "local page"}
    response = client.post(url, headers=HEADERS, json={"id": "stale", "action": "reject", "chat": "telegram:-100"})
    assert response.status_code == 400 and response.json()["error"] == "activity_changed"
    for bad in ({"id": "abc123", "action": "delete", "chat": "x"}, {"id": "../x", "action": "reject", "chat": "x"},
                {"id": "abc123", "action": "reject", "chat": ""}):
        response = client.post(url, headers=HEADERS, json=bad)
        assert response.status_code == 400 and response.json()["error"] == "invalid_chat", bad
    assert len(writes) == 2   # nothing invalid is ever written


def test_activity_says_when_the_service_is_not_running_or_turned_off(client, workspace, monkeypatch):
    monkeypatch.setattr(workspace.services, "running", lambda name: False)
    assert client.get("/api/activity", headers=HEADERS).json() == {"running": False, "off": False, "chats": []}
    _activity_service(workspace, monkeypatch, lambda request: httpx.Response(404, json={"detail": "Not Found"}))
    assert client.get("/api/activity", headers=HEADERS).json() == {"running": True, "off": True, "chats": []}
    _activity_service(workspace, monkeypatch, lambda request: httpx.Response(403, json={"code": "wrong_token"}))
    response = client.get("/api/activity", headers=HEADERS)
    assert response.status_code == 400 and response.json()["error"] == "activity_unavailable"
    assert client.get("/api/activity").status_code == 403


def test_activity_reads_the_token_where_the_service_keeps_it(workspace, monkeypatch):
    def token_in(folder, text):
        path = workspace.home / folder
        path.mkdir(parents=True, exist_ok=True)
        (path / "dashboard.token").write_text(text + "\n", encoding="utf-8")
    token_in("runtime", "default-token")
    token_in("state-a", "shell-token")
    token_in("state-b", "env-token")
    monkeypatch.delenv("AGENT_RUNTIME_DIR", raising=False)
    assert workspace._activity_token() == "default-token"
    monkeypatch.setenv("AGENT_RUNTIME_DIR", "state-a")
    assert workspace._activity_token() == "shell-token"
    # The service's process takes .env over the shell, an empty value included.
    sw.write_env(workspace.env, {"AGENT_RUNTIME_DIR": "state-b"})
    assert workspace._activity_token() == "env-token"
    sw.write_env(workspace.env, {"AGENT_RUNTIME_DIR": ""})
    assert workspace._activity_token() == "default-token"
