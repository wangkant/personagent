"""The health panel: service checks, settings findings, start failures and logs."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from fastapi.testclient import TestClient
import httpx
import pytest

from persona_agent import connections as conn
from persona_agent import welcome
from persona_agent.direct import base as direct_base
from persona_agent.panels import health

TOKEN = "test-local-capability"
HEADERS = {welcome.TOKEN_HEADER: TOKEN}
KEY = "sk-health-secret-abcdefghijklmnop"
CONNECTOR = "connector-token-0123456789abcdef"
REAL_ASYNC_CLIENT = httpx.AsyncClient
ASSETS = Path(welcome.__file__).with_name("static") / "welcome" / "panels"

DOCTOR = {
    "ok": False, "config_findings": [], "retired_settings": [], "update": None,
    "services": [
        {"name": "Ledger sizes", "ok": True, "critical": False, "detail": "evidence absent", "ms": 3},
        {"name": "DM chat", "ok": False, "critical": True,
         "detail": f"HTTPError: HTTP Error 401: Unauthorized (key {KEY})", "ms": 120},
        {"name": "Group replies", "ok": True, "critical": True, "detail": "ok", "ms": 300},
        {"name": "Vision", "ok": None, "critical": False, "detail": "not configured", "ms": 0},
        {"name": "Web search (Tavily)", "ok": False, "critical": False,
         "detail": "URLError: <urlopen error timed out>", "ms": 30000},
    ],
}


@pytest.fixture
def workspace(tmp_path):
    (tmp_path / ".env").write_text(
        f"LLM_BASE_URL=https://api.example.com/v1\nLLM_MODEL=m\nLLM_API_KEY={KEY}\n"
        f"PERSONA_NAME=Test\nAGENT_LANG=en\nCONNECTOR_TOKEN={CONNECTOR}\n", encoding="utf-8")
    value = welcome.Workspace(tmp_path)
    yield value
    value.close()


@pytest.fixture
def client(workspace):
    with TestClient(welcome.create_app(workspace.home, TOKEN, workspace=workspace),
                    base_url="http://127.0.0.1") as value:
        yield value


class Ran:
    def __init__(self, stdout: str):
        self.stdout = stdout.encode()
        self.calls = []

    def __call__(self, argv, **kwargs):
        self.calls.append((argv, kwargs))
        return subprocess.CompletedProcess(argv, 1, stdout=self.stdout, stderr=b"")


class Dead:
    returncode = 2
    pid = 0

    def poll(self):
        return 2


def _log(home: Path, name: str, text: str) -> None:
    logs = home / "runtime" / "desktop"
    logs.mkdir(parents=True, exist_ok=True)
    (logs / f"{name}.log").write_text(text, encoding="utf-8")


def test_every_route_needs_the_local_token(client):
    for method, path in (("get", "/api/health/state"), ("post", "/api/health/check"),
                         ("get", "/api/health/log?name=agent"), ("post", "/api/health/fix"),
                         ("post", "/api/health/open")):
        assert getattr(client, method)(path).status_code == 403


def test_assets_are_served(client):
    assert client.get("/assets/panels/health.js").status_code == 200
    assert client.get("/assets/panels/health.css").status_code == 200


def test_check_runs_doctor_in_a_child_with_the_homes_settings_and_hides_keys(client, workspace, monkeypatch):
    ran = Ran("noise before\n" + json.dumps(DOCTOR))
    monkeypatch.setattr(health.subprocess, "run", ran)
    result = client.post("/api/health/check", headers=HEADERS, json={})
    assert result.status_code == 200
    value = result.json()
    assert KEY not in result.text
    argv, kwargs = ran.calls[0]
    assert argv[-2:] == ["doctor", "--json"]
    assert argv[argv.index("--home") + 1] == str(workspace.home)
    assert kwargs["env"]["AGENT_HOME"] == str(workspace.home)
    assert kwargs["env"]["LLM_API_KEY"] == KEY and kwargs["timeout"] == health.CHECK_TIMEOUT
    assert value["via"] == "doctor" and value["ok"] is False and value["reused"] is False
    by = {s["id"]: s for s in value["services"]}
    assert by["dm"]["reason"] == "key" and by["dm"]["critical"]
    assert by["search"]["reason"] == "unreachable" and by["vision"]["ok"] is None
    assert by["ledger"]["ok"] is True and by["chat"]["reason"] == ""
    # A second press within a minute reuses the answer instead of spending again.
    again = client.post("/api/health/check", headers=HEADERS, json={}).json()
    assert again["reused"] is True and len(ran.calls) == 1
    assert client.get("/api/health/state", headers=HEADERS).json()["last"]["services"] == value["services"]
    client.post("/api/health/check", headers=HEADERS, json={"fresh": True})
    assert len(ran.calls) == 2


def test_check_asks_the_running_character_with_its_connector_token(client, workspace, monkeypatch):
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(503, json={"status": "degraded", "services": DOCTOR["services"]})
    monkeypatch.setattr(workspace.services, "running", lambda name: name == "agent")
    monkeypatch.setattr(health.httpx, "AsyncClient",
                        lambda **kw: REAL_ASYNC_CLIENT(transport=httpx.MockTransport(handler), **kw))
    monkeypatch.setattr(health.subprocess, "run", lambda *a, **k: pytest.fail("no child while it runs"))
    response = client.post("/api/health/check", headers=HEADERS, json={})
    assert response.status_code == 200 and response.json()["via"] == "agent"
    assert seen[0].url.path == "/health/details"
    assert seen[0].headers["x-personagent-token"] == CONNECTOR
    assert KEY not in response.text and CONNECTOR not in response.text


def test_a_character_that_cannot_answer_falls_back_to_the_child(client, workspace, monkeypatch):
    monkeypatch.setattr(workspace.services, "running", lambda name: name == "agent")
    monkeypatch.setattr(health.httpx, "AsyncClient", lambda **kw: REAL_ASYNC_CLIENT(
        transport=httpx.MockTransport(lambda r: httpx.Response(403, json={"error": "forbidden"})), **kw))
    monkeypatch.setattr(health.subprocess, "run", Ran(json.dumps(DOCTOR)))
    assert client.post("/api/health/check", headers=HEADERS, json={}).json()["via"] == "doctor"


@pytest.mark.parametrize("outcome", ["garbage", "timeout", "oserror"])
def test_a_check_that_cannot_run_says_so(client, monkeypatch, outcome):
    def run(*a, **k):
        if outcome == "timeout":
            raise subprocess.TimeoutExpired("doctor", 1)
        if outcome == "oserror":
            raise OSError("no python")
        return subprocess.CompletedProcess(a[0], 1, stdout=b"Traceback: boom", stderr=b"")
    monkeypatch.setattr(health.subprocess, "run", run)
    response = client.post("/api/health/check", headers=HEADERS, json={})
    assert response.status_code == 400 and response.json() == {"error": "health_failed"}


def test_only_one_check_runs_at_a_time(client, monkeypatch):
    holder = {}

    def run(*a, **k):
        holder["second"] = client.post("/api/health/check", headers=HEADERS, json={})
        return subprocess.CompletedProcess(a[0], 0, stdout=json.dumps(DOCTOR).encode(), stderr=b"")
    monkeypatch.setattr(health.subprocess, "run", run)
    assert client.post("/api/health/check", headers=HEADERS, json={}).status_code == 200
    assert holder["second"].status_code == 400 and holder["second"].json() == {"error": "health_busy"}


def test_state_lists_findings_without_secrets(client, workspace):
    with (workspace.home / ".env").open("a", encoding="utf-8") as env:
        env.write("PERSONA_NAAME=typo\n")
    value = client.get("/api/health/state", headers=HEADERS)
    assert value.status_code == 200 and KEY not in value.text and CONNECTOR not in value.text
    found = {f["key"]: f for f in value.json()["findings"]}
    assert found["PERSONA_NAAME"]["kind"] == "unknown" and found["PERSONA_NAAME"]["level"] == "ERROR"
    assert value.json()["failure"] is None and value.json()["platforms"] == []
    assert value.json()["checking"] is False and value.json()["agentRunning"] is False


def test_missing_key_is_named_for_the_page(client, workspace, monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    (workspace.home / ".env").write_text("LLM_MODEL=m\n", encoding="utf-8")
    kinds = [f["kind"] for f in client.get("/api/health/state", headers=HEADERS).json()["findings"]]
    assert "missing_key" in kinds


def test_a_character_that_refused_to_start_is_explained_and_its_retired_names_fixed(client, workspace):
    with (workspace.home / ".env").open("a", encoding="utf-8") as env:
        env.write("PRIVATE_MODEL=small\n")
    _log(workspace.home, "agent",
         f"starting\nAuthorization: Bearer {KEY}\n"
         "personagent: the setting PRIVATE_MODEL was renamed PRIVATE_MODEL -> LLM_DM_MODEL\n"
         "Run `personagent doctor --fix` to rename them in .env, then start again.\n")
    workspace.services.processes["agent"] = Dead()
    workspace.job = {"state": "error", "stage": "", "error": "service_failed"}
    state = client.get("/api/health/state", headers=HEADERS).json()
    assert state["failure"]["service"] == "agent" and state["failure"]["exitCode"] == 2
    assert state["failure"]["said"].startswith("the setting PRIVATE_MODEL was renamed")
    assert state["retired"] == [{"old": "PRIVATE_MODEL", "new": "LLM_DM_MODEL", "where": ".env"}]
    # Listed once, as a retired name, not again as a finding.
    assert "PRIVATE_MODEL" not in [f["key"] for f in state["findings"]]
    started = []
    workspace.start_job = lambda action, *a, **k: started.append(action)
    fixed = client.post("/api/health/fix", headers=HEADERS, json={})
    assert fixed.status_code == 200, fixed.text
    value = fixed.json()
    assert value["changes"] == [{"old": "PRIVATE_MODEL", "new": "LLM_DM_MODEL", "action": "renamed"}]
    assert value["remaining"] == [] and value["started"] is True and started == ["start"]
    assert "LLM_DM_MODEL=small" in (workspace.home / ".env").read_text(encoding="utf-8")
    assert (workspace.home / ".env.bak").is_file() and KEY not in fixed.text
    again = client.post("/api/health/fix", headers=HEADERS, json={})
    assert again.status_code == 400 and again.json() == {"error": "health_nothing_to_fix"}


def test_fix_waits_for_a_running_job(client, workspace):
    with (workspace.home / ".env").open("a", encoding="utf-8") as env:
        env.write("PRIVATE_MODEL=small\n")

    class Busy:
        def done(self):
            return False
    workspace._future = Busy()
    response = client.post("/api/health/fix", headers=HEADERS, json={})
    workspace._future = None
    assert response.status_code == 400 and response.json() == {"error": "busy"}
    assert "PRIVATE_MODEL=small" in (workspace.home / ".env").read_text(encoding="utf-8")


def test_a_crash_is_named_by_the_exception_it_ended_on(client, workspace):
    _log(workspace.home, "astrbot", "Traceback (most recent call last):\n  File x\n"
                                    f"RuntimeError: refused token={CONNECTOR}\nbye\n")
    workspace.services.processes["astrbot"] = Dead()
    failure = client.get("/api/health/state", headers=HEADERS).json()["failure"]
    assert failure["service"] == "astrbot" and failure["said"].startswith("RuntimeError: refused token=")
    assert CONNECTOR not in failure["said"]


def test_a_failed_download_points_at_the_install_log(client, workspace):
    workspace.job = {"state": "error", "stage": "", "error": "download_failed"}
    _log(workspace.home, "install", "pip: network down\n")
    failure = client.get("/api/health/state", headers=HEADERS).json()["failure"]
    assert failure == {"service": "install", "error": "download_failed", "exitCode": None,
                       "said": "pip: network down"}


def test_logs_are_read_by_name_only_masked_and_capped(client, workspace):
    kind = next(p.kind for p in conn.PLATFORMS if conn.is_direct(p.kind))
    direct_base.save_credentials(workspace.home, kind, {"token": "123456:platform-credential-value"})
    secret_lines = [f"line {i}" for i in range(400)] + [
        f"key={KEY}", "using 123456:platform-credential-value now", f"Bearer {CONNECTOR}",
        "\x1b[32mgreen\x1b[0m", "sk-unrelatedsecret123456"]
    _log(workspace.home, "agent", "\n".join(secret_lines) + "\n")
    value = client.get("/api/health/log", params={"name": "agent", "lines": 50}, headers=HEADERS)
    assert value.status_code == 200
    text = value.text
    for secret in (KEY, CONNECTOR, "123456:platform-credential-value", "sk-unrelatedsecret123456"):
        assert secret not in text
    lines = value.json()["lines"]
    assert len(lines) == 50 and lines[-2] == "green" and value.json()["exists"]
    assert len(client.get("/api/health/log", params={"name": "agent", "lines": 9999},
                          headers=HEADERS).json()["lines"]) == health.MAX_LINES
    empty = client.get("/api/health/log", params={"name": "direct"}, headers=HEADERS).json()
    assert empty == {"name": "direct", "exists": False, "lines": []}
    for name in ("../.env", ".env", "C:/Windows/win", "agent.log", ""):
        bad = client.get("/api/health/log", params={"name": name}, headers=HEADERS)
        assert bad.status_code == 400 and bad.json() == {"error": "health_invalid_log"}
    listed = client.get("/api/health/state", headers=HEADERS).json()["logs"]
    assert [entry["name"] for entry in listed] == ["agent"]


def test_logs_hide_telegram_tokens_in_urls_and_astrbot_platform_credentials(client, workspace):
    data = workspace.home / "platforms" / "astrbot" / "data"
    data.mkdir(parents=True)
    discord = "MTA4.short-part.discord-secret-xyz"
    app_secret = "qqofficialappsecret0123456789abcd"
    (data / "cmd_config.json").write_text(json.dumps({"platform": [
        {"id": "discord", "type": "discord", "enable": True, "discord_token": discord},
        {"id": "qq_official", "type": "qq_official", "enable": True, "appid": "102030",
         "secret": app_secret, "port": 6199, "enable_group_c2c": True}]}), encoding="utf-8")
    telegram = "123456789:AAH" + "b" * 32
    _log(workspace.home, "astrbot", f"POST https://api.telegram.org/bot{telegram}/getUpdates\n"
                                    f"login with {discord}\nqq app 102030 secret {app_secret} ok\n")
    text = client.get("/api/health/log", params={"name": "astrbot"}, headers=HEADERS).text
    for secret in (telegram, discord, app_secret):
        assert secret not in text
    assert "api.telegram.org/bot" in text and "102030" in text


def test_a_failed_platform_shows_only_a_named_reason(client, workspace):
    kinds = [p.kind for p in conn.PLATFORMS if conn.is_direct(p.kind)][:2]
    for kind in kinds:
        direct_base.save_credentials(workspace.home, kind, {"token": "x" * 20})
    path = direct_base.status_path(workspace.home)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({kinds[0]: {"state": "refused", "detail": "session_expired", "since": 5},
                                kinds[1]: {"state": "error", "detail": "upstream said <secret text>",
                                           "since": 6}}), encoding="utf-8")
    rows = {p["id"]: p for p in client.get("/api/health/state", headers=HEADERS).json()["platforms"]}
    assert rows[kinds[0]]["failed"] and rows[kinds[0]]["reason"] == "session_expired"
    assert rows[kinds[1]]["reason"] == "error" and rows[kinds[1]]["since"] == 6
    assert "secret text" not in json.dumps(rows) and "x" * 20 not in json.dumps(rows)


def test_open_asks_the_file_manager_for_known_folders_only(client, workspace, monkeypatch):
    opened = []
    monkeypatch.setattr(health, "open_folder", opened.append)
    assert client.post("/api/health/open", headers=HEADERS, json={"folder": "logs"}).json() == {"ok": True}
    assert client.post("/api/health/open", headers=HEADERS, json={"folder": "home"}).status_code == 200
    assert opened == [workspace.home / "runtime" / "desktop", workspace.home]
    bad = client.post("/api/health/open", headers=HEADERS, json={"folder": "C:/Windows"})
    assert bad.status_code == 400 and bad.json() == {"error": "health_open_failed"}

    def broken(path):
        raise OSError("no file manager")
    monkeypatch.setattr(health, "open_folder", broken)
    failed = client.post("/api/health/open", headers=HEADERS, json={"folder": "logs"})
    assert failed.json() == {"error": "health_open_failed"}


def test_open_folder_creates_it_and_uses_the_system_opener(tmp_path, monkeypatch):
    seen = []
    monkeypatch.setattr(health.os, "startfile", seen.append, raising=False)
    monkeypatch.setattr(health.subprocess, "Popen", lambda argv, **k: seen.append(argv[-1]))
    target = tmp_path / "runtime" / "desktop"
    health.open_folder(target)
    assert target.is_dir() and seen == [str(target)]


def test_the_page_strings_match_and_cover_every_code():
    source = (ASSETS / "health.js").read_text(encoding="utf-8")
    tables = {}
    for lang in ("en", "zh"):
        block = re.search(rf"\n  {lang}: {{\n(.*?)\n  }},", source, re.S).group(1)
        tables[lang] = re.findall(r'^    (\w+): "', block, re.M)
        assert len(tables[lang]) == len(block.splitlines())
    assert tables["en"] == tables["zh"] and all(k.startswith("health_") for k in tables["en"])
    assert health.ERRORS <= set(tables["en"])
    assert "innerHTML" not in source and "eval(" not in source


def _table(lang: str) -> dict[str, str]:
    source = (ASSETS / "health.js").read_text(encoding="utf-8")
    block = re.search(rf"\n  {lang}: {{\n(.*?)\n  }},", source, re.S).group(1)
    return dict(re.findall(r'^    (\w+): "(.*)",$', block, re.M))


def test_every_probe_row_has_its_name_in_every_page_language():
    """A row the page has no name for shows the service's English name."""
    ids = set(health.PROBES.values())
    assert {"chat", "searchdecide", "react"} <= ids
    for lang in ("en", "zh"):
        missing = {i for i in ids if f"health_probe_{i}" not in _table(lang)}
        assert not missing, (lang, missing)
    for path in sorted((ASSETS.parent / "i18n").glob("*.json")):
        strings = json.loads(path.read_text(encoding="utf-8"))["strings"]
        missing = {i for i in ids if not strings.get(f"health_probe_{i}", "").strip()}
        assert not missing, (path.name, missing)


def test_the_wording_is_formal_and_uses_the_pages_names():
    en, zh = _table("en"), _table("zh")
    for key, text in en.items():
        assert re.findall(r"\{\w+\}", text) == re.findall(r"\{\w+\}", zh[key]), key
        assert not re.search(r"\b\w+n't\b|\b(?:I'm|you're|it's|Got it)\b", text), (key, text)
    for key, text in zh.items():
        assert not re.search(r"[吧呢啦哦]。?$|您|主人|主文件夹|不肯|不太对|看看|一下|捣乱|接口地址|应用外面|聊天软件", text), (key, text)
    # The confirmation names exactly what it renames.
    assert "{names}" in en["health_fix_ask"] and ".env.bak" in zh["health_fix_ask"]
    assert "quota" in en["health_hint"] and "服务地址" in zh["health_verdict_unreachable"]


def test_the_page_keeps_focus_announces_results_and_stores_codes():
    source = (ASSETS / "health.js").read_text(encoding="utf-8")
    assert 'verdict.setAttribute("role", "status")' in source
    assert 'checkNote.setAttribute("role", "status")' in source
    assert source.count('setAttribute("role", "alert")') >= 3
    # A check started before this page loaded keeps the button disabled through render().
    assert "checking || Boolean(data && data.checking)" in source
    assert "startsWith(\"zh\")" not in source and 'PA.lang === "zh"' in source
    # Translated when shown, not when stored.
    assert not re.search(r"(Error|error)\w* = PA\.t\(", source)
    assert "alerts.contains(active)" in source and "restoreFocus()" in source
