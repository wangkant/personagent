"""Starting the service: refusals in one sentence, the banner, the replay log, a disabled agent."""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import socket
import time
from types import SimpleNamespace

import httpx
import pytest

from persona_agent import server
from persona_agent.storage import RuntimeInstanceLock


# --- refusals ---------------------------------------------------------------

def test_a_network_bind_needs_the_connector_token_but_not_the_onebot_secret() -> None:
    with pytest.raises(ValueError, match="CONNECTOR_TOKEN"):
        server._validate_exposure_config("0.0.0.0", "qq-secret", "")
    server._validate_exposure_config("0.0.0.0", "", "connector-token")
    server._validate_exposure_config("::1", "", "")
    # Without its secret the direct ingress refuses every peer off this host.
    assert server._request_peer_is_allowed("203.0.113.10", "") is False


def test_a_missing_home_is_refused_in_one_sentence(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setattr(server, "ROOT", tmp_path / "nowhere")
    with pytest.raises(SystemExit) as stop:
        server.main(host="127.0.0.1", port=1)
    assert stop.value.code == 2
    err = capsys.readouterr().err.strip()
    assert err.count("\n") == 0 and "personagent init" in err, err


def test_a_second_instance_is_refused_in_one_sentence(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(server, "ROOT", tmp_path)
    monkeypatch.setattr(server, "AGENT_ENABLED", True)
    holder = RuntimeInstanceLock(tmp_path)
    holder.acquire()
    try:
        problem = server.startup_problem("127.0.0.1", 0)
    finally:
        holder.release()
    assert problem and "already running" in problem and "--home" in problem, problem
    assert server.startup_problem("127.0.0.1", 0) is None, "the lock is let go"


def test_a_taken_port_is_refused_in_one_sentence() -> None:
    with socket.socket() as taken:
        taken.bind(("127.0.0.1", 0))
        taken.listen(1)
        port = taken.getsockname()[1]
        problem = server._bind_problem("127.0.0.1", port)
    assert problem and f"port {port} is already in use" in problem, problem
    assert "--port" in problem


def test_an_open_network_bind_is_refused_before_uvicorn(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(server, "ROOT", tmp_path)
    monkeypatch.setattr(server, "CONNECTOR_TOKEN", "")
    problem = server.startup_problem("0.0.0.0", 0)
    assert problem and "CONNECTOR_TOKEN" in problem, problem


# --- banner ------------------------------------------------------------------

def test_the_banner_names_version_address_home_and_agent_state(monkeypatch) -> None:
    monkeypatch.setattr(server, "agent", SimpleNamespace(
        enabled=True, model="m-1", agent_lang="zh"))
    monkeypatch.setattr(server, "_dashboard_served", lambda: True)
    banner = server._banner("0.0.0.0", 8080)
    assert f"personagent {server.__version__}" in banner
    assert "listening:  http://0.0.0.0:8080" in banner
    assert f"home:       {server.ROOT}" in banner
    assert "dashboard:  http://127.0.0.1:8080/" in banner
    assert "on (model m-1, lang zh)" in banner

    monkeypatch.setattr(server, "agent", SimpleNamespace(enabled=False))
    monkeypatch.setattr(server, "_dashboard_served", lambda: False)
    banner = server._banner("::1", 9000)
    assert "http://[::1]:9000" in banner and "dashboard" not in banner
    assert "OFF" in banner and "LLM_API_KEY" in banner


# --- the replay log ----------------------------------------------------------

def test_the_replay_log_appends_instead_of_rewriting(monkeypatch, tmp_path) -> None:
    rewrites = []
    monkeypatch.setattr(server, "atomic_write_text",
                        lambda *a, **k: rewrites.append(a))
    state = tmp_path / "runtime" / "gateway_nonces.json"
    guard = server.ReplayGuard(ttl_seconds=300, state_file=state)
    now = int(time.time())
    for n in range(50):
        assert guard.accept(f"n{n}", now, now) is True
    assert rewrites == [], "no whole-file rewrite per request"
    assert len(state.read_text(encoding="utf-8").splitlines()) == 50

    restarted = server.ReplayGuard(ttl_seconds=300, state_file=state)
    assert restarted.accept("n7", now, now + 10) is False, "a replay after a restart"
    assert restarted.accept("fresh", now + 10, now + 10) is True
    later = server.ReplayGuard(ttl_seconds=300, state_file=state)
    assert later.accept("n7", now + 400, now + 400) is True, "outside the window"


def test_the_replay_log_compacts_once_stale_lines_dominate(tmp_path) -> None:
    state = tmp_path / "gateway_nonces.json"
    guard = server.ReplayGuard(ttl_seconds=10, state_file=state)
    start = int(time.time())
    for n in range(1100):
        assert guard.accept(f"old{n}", start, start)
    assert guard.accept("new", start + 100, start + 100)
    lines = state.read_text(encoding="utf-8").splitlines()
    assert lines == [json.dumps(["new", start + 100])], lines[:3]


def test_the_replay_log_reads_a_whole_file_json_object(tmp_path) -> None:
    now = int(time.time())
    state = tmp_path / "gateway_nonces.json"
    state.write_text(json.dumps({"a": now, "b": now}) + "\n", encoding="utf-8")
    guard = server.ReplayGuard(state_file=state)
    assert guard.accept("a", now, now) is False
    assert guard.accept("c", now, now) is True


def test_a_failed_append_does_not_burn_the_nonce(tmp_path) -> None:
    state = tmp_path / "gateway_nonces.json"
    state.mkdir()  # a directory where the log should be: every append fails
    guard = server.ReplayGuard(state_file=state)
    now = int(time.time())
    with pytest.raises(OSError):
        guard.accept("n", now, now)
    state.rmdir()
    assert guard.accept("n", now, now) is True


# --- a disabled agent ----------------------------------------------------------

def _signed(token: str, event: dict, nonce: str) -> tuple[bytes, dict]:
    body = json.dumps(event, separators=(",", ":")).encode()
    stamp = str(int(time.time()))
    sig = "sha256=" + hmac.new(token.encode(), stamp.encode() + b"." + nonce.encode()
                               + b"." + body, hashlib.sha256).hexdigest()
    return body, {"x-personagent-token": token, "x-personagent-timestamp": stamp,
                  "x-personagent-nonce": nonce, "x-personagent-signature": sig}


async def test_a_disabled_agent_answers_owned_false_and_says_why_once(
        monkeypatch, caplog) -> None:
    async def handle_event(event):
        return {"handled": False, "owned": False, "replies": []}

    monkeypatch.setattr(server, "CONNECTOR_TOKEN", "tok")
    monkeypatch.setattr(server, "_connector_replay", server.ReplayGuard())
    monkeypatch.setattr(server, "_AGENT_OFF_WARNED", False)
    event = {"platform": "telegram", "conversation_type": "group",
             "conversation_id": "g", "sender_id": "u", "segments": [],
             "sent_at": int(time.time())}
    transport = httpx.ASGITransport(app=server.app)
    caplog.set_level(logging.ERROR, logger="bot")
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        for n, agent in enumerate((None, SimpleNamespace(enabled=False,
                                                         handle_event=handle_event))):
            monkeypatch.setattr(server, "agent", agent)
            body, headers = _signed("tok", dict(event, message_id=f"m{n}"), f"nonce-{n}")
            response = await client.post("/v1/events", content=body, headers=headers)
            assert response.status_code == 200, response.text
            assert response.json() == {"handled": False, "owned": False, "replies": []}
    loud = [r for r in caplog.records if "cannot answer" in r.getMessage()]
    assert len(loud) == 1 and "LLM_API_KEY" in loud[0].getMessage(), loud


def test_the_startup_refusal_path_is_wired_into_main(monkeypatch, tmp_path, capsys) -> None:
    started = []
    monkeypatch.setattr(server, "ROOT", tmp_path)
    monkeypatch.setattr(server, "_LISTEN", dict(server._LISTEN))
    monkeypatch.setattr(server, "_bind_problem", lambda host, port: "port 1 is taken")

    import uvicorn
    monkeypatch.setattr(uvicorn.Server, "run", lambda self: started.append(self))
    with pytest.raises(SystemExit):
        server.main(host="127.0.0.1", port=1)
    assert not started
    assert capsys.readouterr().err.strip() == "personagent: port 1 is taken"

    monkeypatch.setattr(server, "_bind_problem", lambda host, port: None)
    server.main(host="127.0.0.1", port=5)
    assert started and server._LISTEN == {"host": "127.0.0.1", "port": 5}
    assert started[0].config.app == "persona_agent.server:app"
