"""First-run setup, browser chat boundary, and scoped platform connections."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import signal
import sys
import time
import types

from fastapi.testclient import TestClient
import httpx
import pytest

from helpers import check
from persona_agent import astrbot_install as installer
from persona_agent import connections as conn
from persona_agent.direct import base as direct_base
from persona_agent import services as svc
from persona_agent import setup_wizard as sw
from persona_agent import welcome


TOKEN = "test-local-capability"
REAL_ASYNC_CLIENT = httpx.AsyncClient
HEADERS = {welcome.TOKEN_HEADER: TOKEN}


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    value = welcome.Workspace(tmp_path)
    monkeypatch.setattr(sw, "probe_key", lambda *a, **kw: sw.Probe("http://127.0.0.1", 200, ""))
    monkeypatch.setattr(welcome, "_vision_works", lambda model, base, key: True)
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
    assert values["LLM_BASE_URL"] == "https://openrouter.ai/api/v1"
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


FAN_MADE = ("chatgpt", "deepseek", "claude")
SPRITE = b"RIFF\x04\x00\x00\x00WEBP"


@pytest.fixture
def portraits(monkeypatch, tmp_path_factory):
    """Portrait sprites for the fan-made characters, never the package's own folder."""
    folder = tmp_path_factory.mktemp("portraits")
    for key in FAN_MADE:
        (folder / f"{key}.webp").write_bytes(SPRITE)
    monkeypatch.setattr(sw, "PORTRAITS", folder)
    return folder


def test_the_catalog_names_each_character_and_its_portrait(client, portraits):
    (portraits / "deepseek.webp").unlink()
    characters = {c["id"]: c for c in client.get("/api/catalog", headers=HEADERS).json()["characters"]}
    assert list(characters) == list(sw.PERSONA_KEYS)
    assert characters["claude"]["defaultName"] == "Claude"
    assert characters["claude"]["avatar"] == "/assets/characters/claude.webp"
    assert characters["deepseek"]["defaultName"] == "DeepSeek" and characters["deepseek"]["avatar"] is None
    assert characters["gamer"]["defaultName"] is None and characters["gamer"]["avatar"] is None


def test_portraits_are_served_for_characters_and_nothing_else(client, portraits):
    response = client.get("/assets/characters/claude.webp")
    assert response.status_code == 200 and response.content == SPRITE
    assert response.headers["content-type"] == "image/webp"
    assert response.headers["cache-control"] == "max-age=86400"
    (portraits / "stray.webp").write_bytes(SPRITE)
    (portraits / "deepseek.webp").unlink()
    for name in ("deepseek.webp", "gamer.webp", "template.webp", "stray.webp", "claude", "claude.png",
                 "claude.webp.bak", "..%2Fwelcome%2Fwelcome.js", "..%2F..%2Fwelcome.py", "%2E%2E.webp"):
        assert client.get(f"/assets/characters/{name}").status_code == 404, name


def test_choosing_a_character_sets_its_portrait_and_editing_keeps_it(client, workspace, portraits,
                                                                    monkeypatch):
    monkeypatch.setattr(workspace, "_restart_agent", lambda: None)
    url = "/api/config"
    state = client.post(url, headers=HEADERS, json={"apiKey": "k", "character": "claude", "lang": "en"}).json()
    assert workspace.config()["PERSONA_AVATAR"] == "claude"
    assert (state["avatar"], state["character"], state["name"]) == ("claude", "claude", "Claude")
    state = client.post("/api/persona", headers=HEADERS, json={"text": "Your name is Claude. Tea only."}).json()
    assert (state["avatar"], state["character"]) == ("claude", "custom")
    state = client.post(url, headers=HEADERS, json={"apiKey": "k", "character": "custom", "name": "Claude"}).json()
    assert workspace.config()["PERSONA_AVATAR"] == "claude" and state["avatar"] == "claude"
    state = client.post(url, headers=HEADERS, json={"apiKey": "k", "character": "gamer", "name": "Mira"}).json()
    assert workspace.config()["PERSONA_AVATAR"] == "" and state["avatar"] == ""
    state = client.post(url, headers=HEADERS, json={"apiKey": "k", "character": "deepseek", "name": "Mira"}).json()
    assert (state["avatar"], state["name"]) == ("deepseek", "Mira")


def test_state_shows_the_portrait_of_an_unedited_shipped_character(workspace, portraits):
    sw.write_env(workspace.env, {"LLM_API_KEY": "k", "AGENT_LANG": "en"})
    assert workspace.summary()["avatar"] == ""
    sw.write_persona(workspace.home, "chatgpt", name="ChatGPT", lang="en")
    assert workspace.summary()["avatar"] == "chatgpt"
    sw.write_env(workspace.env, {"PERSONA_AVATAR": "claude"})
    assert workspace.summary()["avatar"] == "claude"
    sw.write_env(workspace.env, {"PERSONA_AVATAR": "../claude"})
    assert workspace.summary()["avatar"] == "chatgpt"
    (portraits / "chatgpt.webp").unlink()
    assert workspace.summary()["avatar"] == ""
    sw.write_env(workspace.env, {"PERSONA_AVATAR": ""})
    sw.write_persona(workspace.home, "gamer", name="Mira", lang="en")
    assert workspace.summary()["avatar"] == ""


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
    assert client.post("/api/config", headers=HEADERS, content="x" * (welcome.MAX_BODY + 1)).status_code == 413
    assert client.post("/api/config", headers=HEADERS, content="[]").status_code == 400
    assert client.post("/api/config", headers=HEADERS, content="{").status_code == 400


def _managed(workspace, monkeypatch, template=None):
    """A managed AstrBot that is already installed, with a fixed template."""
    data = welcome.AstrBotInstallation(workspace.home).root / "data"
    data.mkdir(parents=True)
    sw._write_json(data / "cmd_config.json", {"platform": []})
    sw.write_env(workspace.env, {"LLM_API_KEY": "key", "CONNECTOR_TOKEN": "existing-token"})
    monkeypatch.setattr(welcome, "install_astrbot", lambda home, **kw: data)
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


# The values the page sends, and one refusal each platform names.
NEW_DIRECT = {
    "matrix": ({"matrix_token": "syt_x", "matrix_owner": "@me:example.org"}, "owner_invalid"),
    "irc": ({"irc_nick": "NovaBot", "irc_channels": "#nova"}, "nick_in_use"),
    "zulip": ({"zulip_site": "https://z.example.org", "zulip_email": "bot@z.example.org",
               "zulip_api_key": "k"}, "not_a_bot"),
    "vk": ({"vk_token": "vk1.a.x"}, "long_poll_off"),
    "stoat": ({"stoat_token": "t"}, "insecure_address"),
}


@pytest.mark.parametrize("kind", sorted(NEW_DIRECT))
def test_each_new_paste_platform_is_checked_kept_and_refused_by_name(workspace, monkeypatch, kind):
    values, refusal = NEW_DIRECT[kind]
    built = []
    _direct_job(workspace, monkeypatch, FakeDirect(), iter([{kind: {"state": "connected"}}] * 5))
    monkeypatch.setattr(welcome.direct, "platform_for",
                        lambda k, v, home: built.append((k, v)) or FakeDirect())
    workspace.start_job("connect", kind, values)
    workspace._future.result(timeout=5)
    assert workspace.job["state"] == "ready", workspace.job
    stored = direct_base.load_credentials(workspace.home)[kind]
    assert built == [(kind, stored)] and values.items() <= stored.items()
    assert workspace.summary()["platforms"] == [kind]

    workspace._disconnect_direct(conn.platform(kind))
    assert refusal in welcome.NAMED_REFUSALS
    monkeypatch.setattr(welcome.direct, "platform_for",
                        lambda k, v, home: FakeDirect(direct_base.Refused(refusal)))
    workspace.start_job("connect", kind, values)
    workspace._future.result(timeout=5)
    assert workspace.job["error"] == refusal
    assert direct_base.load_credentials(workspace.home) == {}


def test_twitch_signs_in_by_link_then_checks_the_tokens_before_keeping_them(workspace, monkeypatch):
    from persona_agent.direct import twitch

    asked = {}

    async def login(client, show, values):
        asked.update(values)
        show("https://www.twitch.tv/activate?public=true&device-code=ABCDEFGH")
        assert workspace.job["stage"] == "scan" and workspace.job["qrUrl"].endswith("ABCDEFGH")
        assert workspace.job["qrImage"].startswith("data:image/png;base64,")
        return {**values, "twitch_access_token": "twitch-private-access",
                "twitch_refresh_token": "twitch-private-refresh"}
    monkeypatch.setattr(twitch, "login", login)
    checked = []
    _direct_job(workspace, monkeypatch, FakeDirect(), iter([{"twitch": {"state": "connected"}}] * 5))
    monkeypatch.setattr(welcome.direct, "platform_for",
                        lambda k, v, home: checked.append(dict(v)) or FakeDirect())
    form = {"twitch_client_id": "client", "twitch_channels": "nova, friend"}
    workspace.start_job("connect", "twitch", form)
    workspace._future.result(timeout=5)
    assert workspace.job["state"] == "ready", workspace.job
    assert asked == form
    stored = direct_base.load_credentials(workspace.home)["twitch"]
    assert checked == [stored] and stored["twitch_access_token"] == "twitch-private-access"
    assert "twitch-private" not in json.dumps(workspace.summary())

    # Refused after the sign-in: nothing kept, the code named.
    workspace._disconnect_direct(conn.platform("twitch"))
    monkeypatch.setattr(welcome.direct, "platform_for",
                        lambda k, v, home: FakeDirect(direct_base.Refused("channel_not_found")))
    workspace.start_job("connect", "twitch", form)
    workspace._future.result(timeout=5)
    assert workspace.job["error"] == "channel_not_found"
    assert direct_base.load_credentials(workspace.home) == {}

    # The login itself: an app Twitch does not accept is named; any other end is a failed sign-in.
    for code, error in (("app_rejected", "app_rejected"), ("denied", "scan_failed")):
        async def failed(client, show, values, code=code):
            raise twitch.LoginFailed(code)
        monkeypatch.setattr(twitch, "login", failed)
        workspace.start_job("connect", "twitch", form)
        workspace._future.result(timeout=5)
        assert workspace.job["error"] == error
        assert direct_base.load_credentials(workspace.home) == {}


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


# Stands in for pip or uv: half-makes the environment, starts a process of its
# own, and would take ten minutes.
SLOW_INSTALLER = """\
import os, subprocess, sys, time
from pathlib import Path
out, envs = sys.argv[1], Path(sys.argv[2])
(envs / "astrbot").mkdir(parents=True, exist_ok=True)
(envs / "astrbot" / "half-made").write_text("x", encoding="utf-8")
grand = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(600)", "fake_installer-grandchild"])
print("downloading", flush=True)
with open(out + ".tmp", "w") as started:
    started.write(f"{os.getpid()} {grand.pid}")
os.replace(out + ".tmp", out)
time.sleep(600)
"""

# Stands in for a download that fails: says why, then exits with an error.
FAILING_INSTALLER = """\
import sys
print("resolver: no route to the package index", flush=True)
sys.exit(1)
"""


def _installer(workspace, monkeypatch, tmp_path_factory, source: str) -> Path:
    """Run `source` as a real child in place of each installer step; returns
    the file a started one writes its process numbers to."""
    modules = tmp_path_factory.mktemp("installer")
    (modules / "fake_installer.py").write_text(source, encoding="utf-8")
    out = modules / "started.txt"
    envs = welcome.AstrBotInstallation(workspace.home).tools / "envs"
    sw.write_env(workspace.env, {"LLM_API_KEY": "key"})
    monkeypatch.setattr(installer.venv.EnvBuilder, "create", lambda self, path: None)
    real = workspace.services.run

    def run(name, argv, **kw):
        kw["env"] = dict(os.environ, PYTHONPATH=str(modules))
        return real(name, [sys.executable, "-m", "fake_installer", str(out), str(envs)], **kw)
    monkeypatch.setattr(workspace.services, "run", run)
    return out


def _installer_started(out: Path, seconds: float = 30) -> list[int]:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if out.is_file():
            return [int(pid) for pid in out.read_text(encoding="utf-8").split()]
        time.sleep(0.05)
    raise AssertionError("the installer never started")


def _installer_gone(pid: int, seconds: float = 5) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if "fake_installer" not in svc._command_line(pid):
            return True
        time.sleep(0.05)
    return False


def _end_installer(pids: list[int]) -> None:
    for pid in pids:
        if "fake_installer" in svc._command_line(pid):
            os.kill(pid, signal.SIGTERM if os.name == "nt" else signal.SIGKILL)


def test_cancelling_the_first_download_stops_the_installer_and_a_later_one_works(workspace, monkeypatch,
                                                                                 tmp_path_factory, capfd):
    out = _installer(workspace, monkeypatch, tmp_path_factory, SLOW_INSTALLER)
    installation = welcome.AstrBotInstallation(workspace.home)
    pids = []
    try:
        workspace.start_job("connect", "kook", {"kook_bot_token": "kook-token"})
        pids = _installer_started(out)
        check("the page shows the download", workspace.summary()["job"]["stage"] == "install")
        began = time.monotonic()
        workspace.cancel()
        workspace._future.result(timeout=15)
        took = time.monotonic() - began
        check("cancelling ends the job in about a second", took < 3, f"{took:.1f}s")
        check("the installer and what it started are gone", all(_installer_gone(pid) for pid in pids))
    finally:
        _end_installer(pids)
    check("the job is back where the page offers the platform again",
          workspace.job == {"state": "idle", "stage": "", "error": ""}, str(workspace.job))
    check("nothing half-made is left", not (installation.tools / "envs").exists())
    check("and nothing was connected", workspace.summary()["platforms"] == [])
    log = (workspace.home / "runtime" / "desktop" / "install.log").read_text(encoding="utf-8")
    shown = capfd.readouterr()
    check("the installer's output is in its log, not in the launch window",
          "downloading" in log and "downloading" not in shown.out + shown.err, shown.out + shown.err)

    def finish(name, argv, **kw):
        if "tool" in argv:
            for path in (installation.executable, installation.python):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("", encoding="utf-8")
        elif "init" in argv:
            (installation.root / ".astrbot").write_text("", encoding="utf-8")
        elif "-c" in argv:
            (installation.root / "data").mkdir()
            sw._write_json(installation.root / "data" / "cmd_config.json", {"platform": []})
    monkeypatch.setattr(workspace.services, "run", finish)
    monkeypatch.setattr(conn, "astrbot_template", lambda installation, kind: {})
    monkeypatch.setattr(workspace.services, "start_agent", lambda: None)
    monkeypatch.setattr(workspace.services, "restart_astrbot", lambda: 0)
    monkeypatch.setattr(workspace.services, "logged", lambda *a: False)
    workspace.start_job("connect", "kook", {"kook_bot_token": "kook-token"})
    workspace._future.result(timeout=15)
    check("a later install finishes and connects",
          workspace.job["state"] == "ready" and workspace.summary()["platforms"] == ["kook"], str(workspace.job))


def test_quitting_during_the_first_download_stops_the_installer(workspace, monkeypatch, tmp_path_factory):
    out = _installer(workspace, monkeypatch, tmp_path_factory, SLOW_INSTALLER)
    pids = []
    try:
        workspace.start_job("connect", "kook", {"kook_bot_token": "kook-token"})
        pids = _installer_started(out)
        workspace.close()
        check("closing returns with the installer and what it started gone",
              not workspace.services.processes and all(_installer_gone(pid, 2) for pid in pids))
        workspace._future.result(timeout=15)
    finally:
        _end_installer(pids)
    check("and nothing half-made is left",
          not (welcome.AstrBotInstallation(workspace.home).tools / "envs").exists())


def test_a_failed_download_says_why_in_the_launch_window_and_only_there(workspace, monkeypatch,
                                                                         tmp_path_factory, capfd):
    _installer(workspace, monkeypatch, tmp_path_factory, FAILING_INSTALLER)
    workspace.start_job("connect", "kook", {"kook_bot_token": "kook-token"})
    workspace._future.result(timeout=30)
    check("the page says the download failed",
          workspace.job["state"] == "error" and workspace.job["error"] == "download_failed", str(workspace.job))
    shown = capfd.readouterr()
    check("the launch window shows the end of the installer's output and where the rest is",
          "no route to the package index" in shown.err and "install.log" in shown.err, shown.err)
    check("the page never does", "package index" not in json.dumps(workspace.summary()))


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
    answer = asyncio.run(workspace.chat("hello"))
    assert answer["reply"] == "hello"
    assert [(m["role"], m["text"]) for m in answer["messages"]] == [("user", "hello"), ("assistant", "hello")]
    assert events[0]["platform"] == "browser" and events[0]["conversation_type"] == "dm"
    # The page pulls the outbox for its own chat under its own connector id.
    assert events[0]["capabilities"] == ["outbox"] and events[0]["reply_handle"] == workspace._conversation
    from persona_agent.server import _validate_event_payload
    assert _validate_event_payload(events[0], connector=True)
    assert workspace.history()["messages"][-1] == {"role": "assistant", "text": "hello", "seq": 2}
    restored = welcome.Workspace(workspace.home)
    try:
        assert restored._conversation == workspace._conversation
        assert restored.history() == workspace.history()
        restored.reset_chat()
        assert restored.history()["messages"] == []
        assert restored.history()["chat"] != workspace.history()["chat"]
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


def test_both_saves_judge_a_base_url_in_one_place(client, workspace, monkeypatch):
    judged = []
    real = welcome._endpoint
    monkeypatch.setattr(welcome, "_endpoint", lambda value: judged.append(value) or real(value))
    monkeypatch.setattr(workspace, "_restart_agent", lambda: None)

    def chat(base):
        return client.post("/api/config", headers=HEADERS, json={"apiKey": "k", "baseUrl": base})

    def vision(base):
        return client.post("/api/features", headers=HEADERS, json={
            "vision": {"enabled": True, "model": "vl", "baseUrl": base, "apiKey": "vk"}})
    saved = [chat(" https://api.example.com/v1/ "), vision("https://vision.example.com/v1/")]
    check("both addresses are accepted", [r.status_code for r in saved] == [200, 200], saved[0].text + saved[1].text)
    check("and each save asked the one judge",
          judged == ["https://api.example.com/v1/", "https://vision.example.com/v1/"], str(judged))
    values = workspace.config()
    check("the chat address is kept as typed", values["LLM_BASE_URL"] == "https://api.example.com/v1/",
          values["LLM_BASE_URL"])
    check("the vision address loses its last slash", values["VISION_BASE_URL"] == "https://vision.example.com/v1",
          values["VISION_BASE_URL"])
    for bad, error in (("ftp://files.example/v1", "invalid_url"), ("https://user:pw@api.example/v1", "invalid_url"),
                       ("https://api.example/${LLM_API_KEY}", "invalid_url"),
                       ("http://remote.example/v1", "https_required")):
        answers = [save(bad).json().get("error") for save in (chat, vision)]
        check(f"both saves refuse {bad} the same way", answers == [error, error], str(answers))
    check("a model on this computer may use http", chat("http://localhost:11434/v1").status_code == 200
          and vision("http://127.0.0.1:11434/v1").status_code == 200)


def test_the_page_and_the_direct_connectors_load_one_sdk(monkeypatch):
    check("the page talks through the bundled connector", welcome._connector_type().__name__ == "Connector")

    class Marker:
        pass
    monkeypatch.setattr(direct_base, "sdk", lambda: types.SimpleNamespace(Connector=Marker))
    check("which it gets from the loader the direct connectors use", welcome._connector_type() is Marker)


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
    "observing": [{"id": "abc123", "type": "preference_pair", "reply": "dune again", "better": "paddington 2",
                   "lesson": "Priya hates rewatching Dune.", "created": 5.0, "actions": ["promote", "reject"],
                   "checklist": {"rules": []}, "evidence": [{"speaker": "Priya"}, {"speaker": "Priya"}, {"speaker": ""}],
                   "standing": {"stage": "observing", "reason": "Priya alone asked for it.", "expires": 9.0,
                                "secret": "x"}, "by": None}],
    "learned": [{"id": "def456", "type": "positive_example", "reply": "fair", "better": "",
                 "created": 4.0, "actions": ["rollback"], "evidence": [], "history": [{"state": "x"}],
                 "standing": None, "by": {"by": "character", "why": "It fits.", "judge": "j"}}],
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
                 "memories": 1, "learned": 1, "observing": 1, "latest": 7.0},
                {"id": "private:browser:x", "platform": "browser", "kind": "dm", "last_activity": 8.0,
                 "memories": 0, "learned": 0, "observing": 0, "latest": 0}]})
        return httpx.Response(200, json=CONVERSATION)
    _activity_service(workspace, monkeypatch, handler)
    listed = client.get("/api/activity", headers=HEADERS).json()
    assert listed["running"] and not listed["off"]
    assert [c["id"] for c in listed["chats"]] == ["telegram:-100", "private:browser:x"]
    assert listed["chats"][0] == {"id": "telegram:-100", "platform": "telegram", "kind": "group",
                                  "last": 9.0, "observing": 1, "learned": 1, "latest": 7.0, "notes": 1}
    chat = client.get("/api/activity/chat", params={"id": "telegram:-100"}, headers=HEADERS).json()
    assert seen[-1].url.params["id"] == "telegram:-100"
    assert all(r.headers["x-personagent-dashboard-token"] == "service-token" for r in seen)
    # Observed items are only read: no decision reaches the view, and nothing is "review".
    assert "review" not in chat
    assert chat["observing"] == [{"id": "abc123", "kind": "wording", "said": "dune again", "better": "paddington 2",
                                  "lesson": "Priya hates rewatching Dune.", "when": 5.0, "from": ["Priya"], "actions": [],
                                  "standing": {"stage": "observing", "reason": "Priya alone asked for it.",
                                               "expires": 9.0}}]
    assert chat["learned"][0]["kind"] == "repeat" and chat["learned"][0]["actions"] == ["rollback"]
    assert chat["learned"][0]["by"] == {"by": "character", "why": "It fits."}
    assert chat["notes"] == [{"text": "match night at Sam's", "by": "Sam", "about": "", "when": 3.0,
                              "id": "", "conv": "", "born": 0, "used": 0, "saidBy": ""}]
    assert chat["thread"] is None and chat["events"] == chat["removed"] == [] and chat["status"] is None
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
    chat = client.post(url, headers=HEADERS, json={"id": "abc123", "action": "rollback",
                                                   "chat": "telegram:-100"}).json()
    assert chat["id"] == "telegram:-100"
    request = writes[-1]
    assert request.url.path == "/api/dashboard/candidates/abc123/rollback"
    assert request.headers["x-personagent-dashboard"] == "1"
    assert request.headers["content-type"] == "application/json"
    assert json.loads(request.content) == {"reason": "local page"}
    response = client.post(url, headers=HEADERS, json={"id": "stale", "action": "rollback", "chat": "telegram:-100"})
    assert response.status_code == 400 and response.json()["error"] == "activity_changed"
    # Nobody confirms what the character learns: the view keeps only Undo.
    for bad in ({"id": "abc123", "action": "promote", "chat": "x"}, {"id": "abc123", "action": "replace", "chat": "x"},
                {"id": "abc123", "action": "reject", "chat": "x"}, {"id": "abc123", "action": "delete", "chat": "x"},
                {"id": "../x", "action": "rollback", "chat": "x"}, {"id": "abc123", "action": "rollback", "chat": ""}):
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


def test_memory_forget_restore_and_forget_chat_go_to_the_service(client, workspace, monkeypatch):
    writes = []
    def handler(request):
        if request.method == "POST":
            body = json.loads(request.content)
            writes.append((request.url.path, body))
            if body.get("tid") == "r00000000aa":
                return httpx.Response(409, json={"code": "already_exists"})
            if body.get("tid") == "r00000000bb":
                return httpx.Response(404, json={"code": "restore_gone"})
            if request.url.path.endswith("/forget_chat"):
                return httpx.Response(200, json={"ok": True, "forgotten": 4})
            return httpx.Response(200, json={"ok": True, "tid": "r1234567890"})
        return httpx.Response(200, json=CONVERSATION)
    _activity_service(workspace, monkeypatch, handler)
    done = client.post("/api/activity/forget", headers=HEADERS,
                       json={"chat": "telegram:-100", "kind": "episode", "id": "e0123456789"}).json()
    assert done["tid"] == "r1234567890" and done["chat"]["id"] == "telegram:-100"
    assert writes[-1] == ("/api/dashboard/memory/forget",
                          {"conv": "telegram:-100", "kind": "episode", "id": "e0123456789"})
    # The older body still forgets a fact, or with no id the always-present note.
    client.post("/api/activity/forget", headers=HEADERS, json={"chat": "telegram:-100", "note": "m1"})
    assert writes[-1][1] == {"conv": "telegram:-100", "kind": "note", "id": "m1"}
    client.post("/api/activity/forget", headers=HEADERS, json={"chat": "telegram:-100"})
    assert writes[-1][1] == {"conv": "telegram:-100", "kind": "core", "id": ""}
    back = client.post("/api/activity/restore", headers=HEADERS, json={"chat": "telegram:-100", "tid": "r1234567890"})
    assert back.json()["id"] == "telegram:-100" and writes[-1] == ("/api/dashboard/memory/restore",
                                                                  {"tid": "r1234567890"})
    for tid, code in (("r00000000aa", "activity_restore_exists"), ("r00000000bb", "activity_restore_gone")):
        r = client.post("/api/activity/restore", headers=HEADERS, json={"chat": "telegram:-100", "tid": tid})
        assert r.status_code == 400 and r.json()["error"] == code
    count = len(writes)
    for path, bad in (("forget", {"chat": "telegram:-100", "kind": "everything", "id": "x"}),
                      ("restore", {"chat": "telegram:-100", "tid": "../r1"}),
                      ("restore", {"chat": "", "tid": "r1234567890"}),
                      ("forget_chat", {"chat": ""})):
        r = client.post(f"/api/activity/{path}", headers=HEADERS, json=bad)
        assert r.status_code == 400 and r.json()["error"] == "invalid_chat", bad
    assert len(writes) == count   # nothing invalid is ever written
    other = client.post("/api/activity/forget_chat", headers=HEADERS, json={"chat": "telegram:-100"}).json()
    assert other == {"ok": True, "forgotten": 4}
    assert writes[-1] == ("/api/dashboard/memory/forget_chat", {"conv": "telegram:-100"})
    # This page's own chat is forgotten whole, then starts anew.
    monkeypatch.setattr(workspace.services, "start_agent", lambda: None)
    before = workspace._page_key()
    own = client.post("/api/activity/forget_chat", headers=HEADERS, json={"chat": before}).json()
    assert own == {"ok": True, "forgotten": 4} and workspace._page_key() != before
    assert writes[-1] == ("/api/dashboard/memory/forget_chat", {"conv": before})


def _table(js, code, name):
    """One `  <code>: {` table of `key: "sentence",` lines in a script, or {}."""
    start = js.find(f"\n  {code}: {{\n")
    if start < 0:
        return {}
    block = js[start:js.index("\n  },\n", start)]
    found = re.findall(r'^ {4}(\w+):\s*("(?:[^"\\]|\\.)*"),?$', block, re.M)
    assert len(found) == len(re.findall(r"^ {4}\w+:", block, re.M)), f"{name}: a {code} line the page test cannot read"
    return {key: json.loads(value) for key, value in found}


def _page_strings(code):
    """The page's sentences in en or zh: welcome.js and every panel carry theirs inline."""
    scripts = [welcome.ASSETS / "welcome.js",
               *(welcome.ASSETS / "panels" / f"{name}.js" for name in welcome.PANELS)]
    strings = {}
    for script in scripts:
        table = _table(script.read_text(encoding="utf-8"), code, script.name)
        again = strings.keys() & table.keys()
        assert not again, f"{script.name} repeats {sorted(again)}"
        strings.update(table)
    return strings


def test_every_panel_has_its_module_its_script_and_its_stylesheet(client):
    import importlib

    for name in welcome.PANELS:
        module = importlib.import_module(f"persona_agent.panels.{name}")
        assert callable(module.mount) and isinstance(module.ERRORS, frozenset), name
        for kind in ("js", "css"):
            assert client.get(f"/assets/panels/{name}.{kind}").status_code == 200, (name, kind)
    html = (welcome.ASSETS / "index.html").read_text(encoding="utf-8")
    assert re.findall(r'/assets/panels/(\w+)\.js', html) == list(welcome.PANELS)
    for name in ("unknown.js", "health.py", "..%2Fwelcome.js", "health.js.bak"):
        assert client.get(f"/assets/panels/{name}").status_code == 404, name


def _catalog_english(client):
    english = set()

    def walk(value):
        if isinstance(value, dict):
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            if len(value) == 2 and all(isinstance(item, str) for item in value):
                english.add(value[0])
            else:
                for item in value:
                    walk(item)
    walk(client.get("/api/catalog", headers=HEADERS).json())
    return english


def _fields(text):
    return set(re.findall(r"\{(\w+)\}", text))


def test_page_languages_are_listed_once_everywhere():
    html = (welcome.ASSETS / "index.html").read_text(encoding="utf-8")
    menu = re.search(r'<select id="language".*?</select', html, re.S).group(0)
    assert re.findall(r'<option value="([^"]+)"', menu) == ["en", "zh", *welcome.PAGE_LANGUAGES]
    js = (welcome.ASSETS / "welcome.js").read_text(encoding="utf-8")
    table = re.search(r"const LANGS = \{(.*?)\};", js, re.S).group(1)
    assert re.findall(r'^\s+"?([\w-]+)"?:', table, re.M) == ["en", "zh", *welcome.PAGE_LANGUAGES]
    assert _page_strings("en").keys() == _page_strings("zh").keys()


@pytest.mark.parametrize("code", welcome.PAGE_LANGUAGES)
def test_each_page_language_translates_known_strings_with_their_fields(client, code):
    data = json.loads((welcome.ASSETS / "i18n" / f"{code}.json").read_text(encoding="utf-8"))
    english = _page_strings("en")
    assert set(data) == {"language", "strings", "catalog"}
    # A string a translation lacks shows in English, so a subset is enough;
    # an unknown key or a lost {field} is a mistake.
    assert set(data["strings"]) <= set(english)
    for key, text in data["strings"].items():
        assert isinstance(text, str) and text.strip(), key
        assert _fields(text) == _fields(english[key]), key
    catalog = _catalog_english(client)
    assert set(data["catalog"]) <= catalog
    for source, text in data["catalog"].items():
        assert isinstance(text, str) and text.strip(), source


@pytest.mark.parametrize("code", welcome.PAGE_LANGUAGES)
def test_every_learning_sentence_is_translated(code):
    """What says where a learned item stands never falls back to English."""
    data = json.loads((welcome.ASSETS / "i18n" / f"{code}.json").read_text(encoding="utf-8"))["strings"]
    english = _page_strings("en")
    wanted = {k for k in english if k.startswith(("activity", "learned_", "practice_held"))
              or k.startswith(("tuning_f_promote", "tuning_h_promote"))}
    assert sorted(wanted - set(data)) == []


# Phrases that tell the reader a learned item waits for them, in every page language.
WAITS_FOR_THE_READER = {
    "en": ("waiting for you", "await your decision", "awaits your decision", "left to you",
           "only an admin", "waits for your decision", "until you keep"),
    "zh": ("待你确认", "等待你", "由你决定", "管理员批准", "待确认"),
    "zh-TW": ("待你確認", "等待你", "由你決定", "管理員核准", "待確認"),
    "ja": ("確認待ち", "あなたの判断を待", "管理者のみ"),
    "ko": ("확인 대기", "결정을 기다리", "관리자만"),
    "es": ("pendiente de su decisión", "espera su decisión", "solo un administrador"),
    "fr": ("en attente de votre décision", "attend votre décision", "seul un administrateur"),
    "de": ("wartet auf sie", "warten auf ihre entscheidung", "nur ein administrator"),
    "pt-BR": ("aguardando sua decisão", "aguarda sua decisão", "aguarda a sua decisão", "apenas um administrador"),
    "ru": ("требует вашего решения", "ожидает вашего решения", "только администратор"),
}


@pytest.mark.parametrize("code", ["en", "zh", *welcome.PAGE_LANGUAGES])
def test_no_page_sentence_says_a_learned_item_waits_for_the_reader(code):
    if code in ("en", "zh"):
        strings = _page_strings(code)
    else:
        strings = json.loads((welcome.ASSETS / "i18n" / f"{code}.json").read_text(encoding="utf-8"))["strings"]
    found = [(key, text) for key, text in strings.items()
             if any(phrase in text.lower() for phrase in WAITS_FOR_THE_READER[code])]
    assert found == []


def test_the_observed_items_in_activity_have_no_buttons_and_light_no_dot():
    js = (welcome.ASSETS / "welcome.js").read_text(encoding="utf-8")
    card = re.search(r"\nfunction change\(item, observed\) \{\n(.*?)\n\}\n", js, re.S).group(1)
    # The card returns before any button is built.
    assert card.index("if (observed) return card;") < card.index('el("div", "change-actions")')
    dot = re.search(r"\nfunction renderActivityDot\(\) \{\n(.*?)\n\}\n", js, re.S).group(1)
    # Only something new in use lights it, never an item still observed.
    assert "observing" not in dot and "review" not in dot and "activityLatest()" in dot
    assert '"activity/decide"' in js and '"promote"' not in js.split("async function decide(item, verb)")[1][:600]
    html = (welcome.ASSETS / "index.html").read_text(encoding="utf-8")
    assert 'id="activity-dot" class="dot"' in html


def _recorded_reasons() -> set[str]:
    """Every reason the code can hand decision_log, read from the source."""
    import ast

    found: set[str] = set()

    def words(node) -> set[str]:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return {node.value}
        if isinstance(node, ast.IfExp):
            return words(node.body) | words(node.orelse)
        return set()

    for path in Path(welcome.__file__).parent.glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call):
                func = node.func
                if (getattr(func, "attr", "") == "record" and len(node.args) >= 4
                        and getattr(getattr(func, "value", None), "id", "") == "decision_log"):
                    found |= words(node.args[3])
                elif getattr(func, "id", "") == "silent" and node.args:
                    found |= words(node.args[0])
            # `mode, why = "", "below the trigger count"` and `return "judge", "trigger count"`.
            elif (isinstance(node, (ast.Assign, ast.Return)) and isinstance(node.value, ast.Tuple)
                  and len(node.value.elts) == 2 and path.name in ("decision.py", "turns.py")):
                found |= words(node.value.elts[1])
            elif (path.name == "decision.py" and isinstance(node, ast.Assign)
                  and isinstance(node.targets[0], ast.Name) and node.targets[0].id.isupper()):
                found |= words(node.value)
    # A reason is a few lower-case words; prompt notes among the constants are not.
    return {text for text in found if re.fullmatch(r"[a-z]+(?: [a-z]+)*", text)}


def _reason_map() -> dict[str, str]:
    js = (welcome.ASSETS / "welcome.js").read_text(encoding="utf-8")
    block = re.search(r"const REASONS = \{(.*?)\};", js, re.S).group(1)
    return dict(re.findall(r'^\s+"?([\w ]+?)"?: "(r_\w+)",', block, re.M))


def test_every_reason_the_service_records_reads_as_a_sentence_in_every_language():
    recorded = _recorded_reasons()
    assert {"model failed", "blocked", "delivery failed", "proactive", "passed",
            "below the trigger count", "sleep window", "sticky call"} <= recorded, recorded
    mapped = _reason_map()
    assert recorded <= set(mapped), sorted(recorded - set(mapped))
    assert "answered together" in mapped
    keys = set(mapped.values()) | {"r_other", "chatViaCoding", "vision_unsupported"}
    for code in ("en", "zh"):
        assert not keys - set(_page_strings(code)), (code, keys - set(_page_strings(code)))
    for code in welcome.PAGE_LANGUAGES:
        strings = json.loads((welcome.ASSETS / "i18n" / f"{code}.json").read_text(encoding="utf-8"))["strings"]
        missing = {k for k in keys if not strings.get(k, "").strip()}
        assert not missing, (code, missing)


def test_an_unknown_reason_is_never_shown_raw_and_a_coding_entry_is_labelled():
    js = (welcome.ASSETS / "welcome.js").read_text(encoding="utf-8")
    reason = re.search(r"\nfunction reasonText\(row\) \{\n(.*?)\n\}\n", js, re.S).group(1)
    assert "row.reason;" not in reason and 't("r_other")' in reason
    mode = re.search(r"\nfunction modeText\(row\) \{\n(.*?)\n\}\n", js, re.S).group(1)
    assert "|| row.mode" not in mode
    shown = re.search(r"\nfunction showMessage\(item, arrived = false\) \{\n(.*?)\n\}\n", js, re.S).group(1)
    assert 'item.via === "coding"' in shown and 't("chatViaCoding")' in shown


def test_page_language_files_are_served_and_nothing_else(client):
    for code in welcome.PAGE_LANGUAGES:
        response = client.get(f"/assets/i18n/{code}.json")
        assert response.status_code == 200 and response.json()["strings"]
    for name in ("en.json", "zh.json", "xx.json", "ja", "ja.json.bak", "..%2Fwelcome.js", "..%2F..%2Fwelcome.py"):
        assert client.get(f"/assets/i18n/{name}").status_code == 404, name


def test_vision_is_saved_only_when_the_model_can_read_an_image(client, workspace, monkeypatch):
    """A model that cannot read images used to be saved as on, then refused
    every picture three times. The save now asks it once, with the values
    being saved."""
    sw.write_env(workspace.env, {"LLM_API_KEY": "chat-key", "LLM_BASE_URL": "https://api.example.com/v1"})
    monkeypatch.setattr(workspace, "_restart_agent", lambda: None)
    asked = []

    def probe(model, base, key):
        asked.append((model, base, key))
        return model == "vl-model"
    monkeypatch.setattr(welcome, "_vision_works", probe)
    url = "/api/features"
    refused = client.post(url, headers=HEADERS, json={"vision": {"enabled": True, "model": "text-only",
                                                                  "baseUrl": "https://v.example.com/v1",
                                                                  "apiKey": "vk"}})
    check("refused by name", refused.status_code == 400 and refused.json()["error"] == "vision_unsupported",
          refused.text)
    check("asked once with what was being saved",
          asked == [("text-only", "https://v.example.com/v1", "vk")], repr(asked))
    check("and nothing was saved", not workspace.config().get("VISION_MODEL"), repr(workspace.config()))
    saved = client.post(url, headers=HEADERS, json={"vision": {"enabled": True, "model": "vl-model",
                                                                "sameAsChat": True}})
    check("a model that can see is saved", saved.status_code == 200
          and workspace.config()["VISION_MODEL"] == "vl-model", saved.text)
    check("against the chat endpoint", asked[-1] == ("vl-model", "https://api.example.com/v1", "chat-key"))
    asked.clear()
    client.post(url, headers=HEADERS, json={"vision": {"enabled": False}})
    check("turning it off asks nothing", asked == [], repr(asked))


def test_the_vision_probe_runs_the_health_check_on_the_values_given(monkeypatch):
    from persona_agent import health

    seen = []

    def check_vision():
        seen.append((os.environ.get("VISION_MODEL"), os.environ.get("VISION_BASE_URL"),
                     os.environ.get("VISION_API_KEY")))
        return True, "ok"
    monkeypatch.setattr(health, "check_vision", check_vision)
    monkeypatch.setenv("VISION_MODEL", "before")
    monkeypatch.delenv("VISION_API_KEY", raising=False)
    check("a passing check", welcome._vision_works("vl", "https://v.example/v1", "vk") is True)
    check("it saw the values given", seen == [("vl", "https://v.example/v1", "vk")], repr(seen))
    check("and the environment is as it was", os.environ.get("VISION_MODEL") == "before"
          and "VISION_API_KEY" not in os.environ)

    def failing():
        raise OSError("HTTP Error 400: model does not support image input")
    monkeypatch.setattr(health, "check_vision", failing)
    check("a refusal is a no", welcome._vision_works("vl", "https://v.example/v1", "vk") is False)
