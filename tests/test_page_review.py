"""What the pre-release review of the page from another device found: a burst
of sign-ins, what a remote session may change on the server, a proxy's Host,
and the Docker gateway address."""
from __future__ import annotations

import asyncio
from pathlib import Path
import threading
import time

from fastapi.testclient import TestClient
import httpx
import pytest

from helpers import check
from persona_agent import pageaccess
from persona_agent import setup_wizard as sw
from persona_agent import welcome
from persona_agent.panels import agents

TOKEN = "test-local-capability"
PASSWORD = "plum-orchard-41-lantern"
SERVER = "http://192.168.1.5:8090"
SESSION = {pageaccess.SESSION_HEADER: "1"}
ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _no_page_settings(monkeypatch):
    for name in (*pageaccess.SETTINGS, pageaccess.CONTAINER_ENV):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(pageaccess, "FAIL_DELAY_S", 0.0)


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    # A plain password from the environment: the checks below time the stand-in, not scrypt.
    monkeypatch.setenv("PAGE_PASSWORD", PASSWORD)
    sw.write_env(tmp_path / ".env", {"PAGE_HOST": "0.0.0.0", "LLM_API_KEY": "k", "CONNECTOR_TOKEN": "conn-token"})
    value = welcome.Workspace(tmp_path)
    yield value
    value.close()


@pytest.fixture
def app(workspace):
    app = welcome.create_app(workspace.home, TOKEN, workspace=workspace, gate=pageaccess.Gate(workspace.home))
    return app


class _Counted:
    """pageaccess.verify, slowed and counted: how many ran, and how many at once."""

    def __init__(self, seconds: float = 0.15):
        self.lock = threading.Lock()
        self.calls = self.running = self.most = 0
        self.seconds = seconds
        self.real = pageaccess.verify

    def __call__(self, stored: str, attempt: str) -> bool:
        with self.lock:
            self.calls += 1
            self.running += 1
            self.most = max(self.most, self.running)
        try:
            time.sleep(self.seconds)
            return self.real(stored, attempt)
        finally:
            with self.lock:
                self.running -= 1


async def _burst(app, passwords: list[str], address: str = "192.168.1.20") -> list[httpx.Response]:
    transport = httpx.ASGITransport(app=app, client=(address, 50000))
    async with httpx.AsyncClient(transport=transport, base_url=SERVER) as client:
        return list(await asyncio.gather(*(client.post("/auth/signin", json={"password": p})
                                           for p in passwords)))


# ---- 1. a burst of sign-ins

async def test_a_burst_from_one_address_is_checked_at_most_the_limit(app, monkeypatch):
    counted = _Counted()
    monkeypatch.setattr(pageaccess, "verify", counted)
    # Room for every check at once, so only the count per address can hold the burst.
    monkeypatch.setattr(pageaccess, "CHECKS_AT_ONCE", 100)
    answers = await _burst(app, ["wrong-password-000"] * 30 + [PASSWORD] + ["wrong-password-000"] * 29)
    check("never more checks than the limit", counted.calls <= pageaccess.FAIL_LIMIT, str(counted.calls))
    refused = [a for a in answers if a.status_code == 429]
    check("the rest are refused at once", len(refused) >= len(answers) - pageaccess.FAIL_LIMIT)
    signed = [a for a in answers if a.status_code == 200]
    check("the right one signs in only if it was among those checked", len(signed) <= 1)
    before = counted.calls
    later = await _burst(app, ["wrong-password-000"] * 10)
    check("a second burst is held to the limit as well", counted.calls - before <= pageaccess.FAIL_LIMIT
          and all(a.status_code in (401, 429) for a in later), str(counted.calls - before))


async def test_the_right_password_signs_in_while_the_address_has_attempts_left(app, monkeypatch):
    counted = _Counted()
    monkeypatch.setattr(pageaccess, "verify", counted)
    monkeypatch.setattr(pageaccess, "CHECKS_AT_ONCE", 100)
    wrong = await _burst(app, ["wrong-password-000"] * (pageaccess.FAIL_LIMIT - 2))
    check("the wrong ones are refused as wrong", all(a.status_code == 401 for a in wrong))
    right = await _burst(app, [PASSWORD])
    check("the right one still signs in", right[0].status_code == 200)
    again = await _burst(app, ["wrong-password-000"] * (pageaccess.FAIL_LIMIT - 1))
    check("and a success starts the count again", all(a.status_code == 401 for a in again))


async def test_two_checks_run_at_once_and_a_full_bound_is_not_held_against_the_caller(app, monkeypatch):
    counted = _Counted(seconds=0.3)
    monkeypatch.setattr(pageaccess, "verify", counted)
    addresses = [f"10.0.0.{i}" for i in range(1, 9)]
    started = time.monotonic()
    groups = await asyncio.gather(*(_burst(app, ["wrong-password-000"], address=a) for a in addresses))
    answers = {a: group[0] for a, group in zip(addresses, groups)}
    busy = [a for a, answer in answers.items() if answer.status_code == 429]
    check("at most two checks at a time", counted.most <= pageaccess.CHECKS_AT_ONCE, str(counted.most))
    check("the others are refused, not queued", len(busy) >= len(addresses) - pageaccess.CHECKS_AT_ONCE
          and all(answers[a].json()["error"] == "signin_busy" for a in busy))
    check("at once: the burst took about one check's time", time.monotonic() - started < 2 * counted.seconds + 1)
    limiter = app.state.gate.limiter
    for address in busy:
        check(f"{address}: turned away by the bound, not counted", not limiter._failures.get(address))
    after = await _burst(app, [PASSWORD], address=busy[0])
    check("and signs in afterwards", after[0].status_code == 200)


def test_the_checks_run_on_threads_of_their_own(app, monkeypatch):
    seen = []
    real = pageaccess.verify

    def where(stored, attempt):
        seen.append(threading.current_thread().name)
        return real(stored, attempt)
    monkeypatch.setattr(pageaccess, "verify", where)
    with TestClient(app, base_url=SERVER, client=("192.168.1.20", 50000)) as phone:
        phone.post("/auth/signin", json={"password": PASSWORD})
    check("not the shared pool the API uses", seen and seen[0].startswith("personagent-signin"), str(seen))


# ---- 2. what a session from another device may change on the server

def _astrbot(folder: Path, token: str) -> Path:
    data = folder / "data"
    (data / "plugins" / sw.PLUGIN_NAME).mkdir(parents=True)
    (data / "cmd_config.json").write_text("{}", encoding="utf-8")
    sw.write_astrbot_config(data, {"connector_token": token})
    return data


def test_another_device_cannot_connect_coding_assistants_or_name_an_astrbot_folder(app, workspace, tmp_path):
    connected = _astrbot(tmp_path / "connected", "conn-token")
    other = _astrbot(tmp_path / "other", "conn-token")
    agents._remember(workspace, connected)
    with TestClient(app, base_url=SERVER, client=("192.168.1.20", 50000)) as phone:
        assert phone.post("/auth/signin", json={"password": PASSWORD}).status_code == 200
        for path, payload in (("coding", {"target": "claude-code", "connect": True}),
                              ("astrbot", {"dataDir": str(other)}),
                              ("astrbot/remove", {"dataDir": str(other)})):
            answer = phone.post(f"/api/agents/{path}", json=payload, headers=SESSION)
            check(path, answer.status_code == 403 and answer.json()["error"] == "local_only", answer.text)
        check("the other folder's plugin is still there", (other / "plugins" / sw.PLUGIN_NAME).is_dir())
        refused = phone.post("/api/agents/astrbot/allow", json={"dataDir": str(other), "groups": ["g1"]},
                             headers=SESSION)
        check("reply lists of another folder: refused", refused.status_code == 400
              and refused.json()["error"] == "local_only", refused.text)
        check("left as it was", "groups" not in sw.read_astrbot_config(other))
        allowed = phone.post("/api/agents/astrbot/allow", json={"dataDir": str(connected), "groups": ["g1"]},
                             headers=SESSION)
        check("reply lists of the AstrBot connected here: allowed", allowed.status_code == 200, allowed.text)
        check("and saved", sw.read_astrbot_config(connected).get("groups") == ["g1"])


def test_on_this_computer_the_agents_routes_are_unchanged(app, workspace, tmp_path):
    other = _astrbot(tmp_path / "other", "conn-token")
    with TestClient(app, base_url="http://127.0.0.1:8090", client=("127.0.0.1", 50000)) as here:
        answer = here.post("/api/agents/astrbot/allow", json={"dataDir": str(other), "groups": ["g2"]},
                           headers={welcome.TOKEN_HEADER: TOKEN})
        check("any folder of ours, as before", answer.status_code == 200, answer.text)


# ---- 3. a proxy that drops the port

def test_a_host_without_the_port_the_browser_used_is_named_on_the_sign_in(app):
    with TestClient(app, base_url="https://192.168.1.5:8443", client=("192.168.1.20", 50000)) as phone:
        good = phone.post("/auth/signin", json={"password": PASSWORD},
                          headers={"Origin": "https://192.168.1.5:8443"})
        check("Host with its port: signed in", good.status_code == 200, good.text)
        dropped = phone.post("/auth/signin", json={"password": PASSWORD},
                             headers={"Origin": "https://192.168.1.5:8443", "Host": "192.168.1.5"})
        check("Host without it: a code the sign-in page explains",
              dropped.status_code == 403 and dropped.json() == {"error": "signin_origin"}, dropped.text)
        api = phone.get("/api/state", headers={**SESSION, "Origin": "https://evil.example"})
        check("the API still says no more than before", api.json() == {"error": "forbidden"})
    script = (ROOT / "persona_agent" / "static" / "welcome" / "signin.js").read_text(encoding="utf-8")
    check("the sign-in page has its sentence", script.count("signin_origin:") == 2)


def test_every_deploy_guide_passes_the_host_with_its_port():
    for path in sorted((ROOT / "docs").glob("deploy*.md")):
        text = path.read_text(encoding="utf-8")
        check(f"{path.name}: $http_host", "proxy_set_header Host $http_host;" in text
              and "proxy_set_header Host $host;" not in text)


# ---- 5. one gateway address for every device

def test_the_docker_guide_says_desktop_shares_one_address():
    for name in ("deploy.md", "deploy.zh-CN.md"):
        text = (ROOT / "docs" / name).read_text(encoding="utf-8")
        check(name, "Docker Desktop" in text and "127.0.0.1:8090:8090" in text)
