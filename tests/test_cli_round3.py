"""Terminal and connector fixes from the third round of simulated users."""
from __future__ import annotations

import sys
from pathlib import Path

from persona_agent import setup_wizard as sw


def _not_checkout(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("AGENT_HOME", raising=False)
    monkeypatch.setattr(sw.homes, "is_checkout", lambda *a: False)
    monkeypatch.setattr(sw.homes, "default_home", lambda: tmp_path / "personagent")
    monkeypatch.setattr(sw.langs, "under_uvx", lambda: False)
    monkeypatch.setattr(sw.shutil, "which", lambda name: None)


def test_hints_name_the_launcher_that_started_the_process(monkeypatch, tmp_path: Path) -> None:
    _not_checkout(monkeypatch, tmp_path)
    scripts = tmp_path / "my venv" / "Scripts"
    scripts.mkdir(parents=True)
    (scripts / "personagent.exe").write_bytes(b"")
    monkeypatch.setattr(sys, "executable", str(scripts / "python.exe"))
    # Windows launchers report themselves without the extension.
    monkeypatch.setattr(sys, "argv", [str(scripts / "personagent"), "init"])
    launcher = sw.Launcher(python=sys.executable, home=tmp_path / "personagent")
    line = launcher.shown("doctor")[0]
    assert "-m persona_agent" not in line
    assert str(scripts / "personagent.exe") in line and line.endswith(" doctor")
    assert '"' in line, "a path with spaces is quoted"


def test_hints_keep_the_interpreter_form_without_a_launcher(monkeypatch, tmp_path: Path) -> None:
    _not_checkout(monkeypatch, tmp_path)
    monkeypatch.setattr(sys, "argv", ["-m", "init"])
    launcher = sw.Launcher(python="python", home=tmp_path / "personagent")
    assert launcher.shown("doctor") == ["python -m persona_agent doctor"]


def test_hints_say_the_bare_launcher_when_it_is_on_path(monkeypatch, tmp_path: Path) -> None:
    _not_checkout(monkeypatch, tmp_path)
    monkeypatch.setattr(sw.shutil, "which", lambda name: "/usr/bin/personagent")
    launcher = sw.Launcher(python="python", home=tmp_path / "personagent")
    assert launcher.shown("doctor") == ["personagent doctor"]


def test_key_env_help_says_the_value_is_saved_in_env(monkeypatch) -> None:
    monkeypatch.setenv("AGENT_LANG", "en")
    assert "save a copy of its value in .env" in " ".join(sw.init_parser("personagent init").format_help().split())


def test_a_misspelt_option_before_the_command_is_called_unknown(monkeypatch, capsys) -> None:
    import pytest

    from persona_agent import cli

    monkeypatch.setenv("AGENT_LANG", "en")
    with pytest.raises(SystemExit) as stop:
        cli.main(["--hme", "somewhere", "doctor"])
    assert stop.value.code == 2
    err = capsys.readouterr().err
    assert "unrecognized arguments: --hme" in err and "invalid choice" not in err, err
    assert cli._unknown_leading_option(["--home", "-weird-folder", "doctor"]) is None
    assert cli._unknown_leading_option(["doctor", "--jsn"]) is None


# --- connector endpoints ------------------------------------------------------

def _event(**changes) -> dict:
    import time

    event = {"platform": "mychat", "conversation_type": "dm", "sender_id": "u1",
             "message_id": "m1", "sent_at": int(time.time()), "text": "hi"}
    event.update(changes)
    return event


async def _post(path: str, *, client_host: str = "127.0.0.1", headers=None, **kw):
    import httpx

    from persona_agent import server

    transport = httpx.ASGITransport(app=server.app, client=(client_host, 1234))
    async with httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:8080") as client:
        if path.startswith("GET "):
            return await client.get(path[4:], headers=headers or {})
        return await client.post(path, headers=headers or {}, **kw)


async def test_a_forwarded_local_request_is_non_local_and_names_the_header(monkeypatch) -> None:
    from persona_agent import server

    monkeypatch.setattr(server, "agent", None)
    monkeypatch.setattr(server, "CONNECTOR_TOKEN", "")
    # uvicorn hands the app the X-Forwarded-For address as the peer.
    r = await _post("/v1/events", client_host="1.2.3.4", json=_event(),
                    headers={"x-forwarded-for": "1.2.3.4"})
    assert r.status_code == 403 and r.json()["code"] == "non_local_request", r.text
    assert "X-Forwarded-For" in r.json()["error"] and "1.2.3.4" not in r.json()["error"]
    r = await _post("/v1/events", json=_event(), headers={"origin": "http://evil.example"})
    assert "Origin header" in r.json()["error"] and "evil" not in r.json()["error"]
    r = await _post("/v1/events", client_host="1.2.3.4", json=_event())
    assert r.json()["code"] == "unauthenticated"


async def test_health_details_says_a_wrong_token_does_not_match(monkeypatch) -> None:
    from persona_agent import server

    monkeypatch.setattr(server, "CONNECTOR_TOKEN", "right-token")
    r = await _post("GET /health/details", headers={"x-personagent-token": "wrong"})
    assert r.status_code == 403 and r.json()["code"] == "forbidden"
    assert "does not match" in r.json()["error"]
    r = await _post("GET /health/details")
    assert "send the X-Personagent-Token header" in r.json()["error"]


async def test_event_refusals_name_their_reason(monkeypatch) -> None:
    import time

    from persona_agent import server

    monkeypatch.setattr(server, "agent", None)
    monkeypatch.setattr(server, "CONNECTOR_TOKEN", "")
    now = int(time.time())
    cases = {now * 1000: "looks like milliseconds", now - 25 * 3600: "in the past",
             "yesterday": "not a number", now + 3 * 86400: "in the future; check both clocks"}
    for sent_at, said in cases.items():
        r = await _post("/v1/events", json=_event(sent_at=sent_at))
        assert r.status_code == 403 and r.json()["code"] == "stale_event", r.text
        assert r.json()["error"].startswith("stale or invalid sent_at: ") and said in r.json()["error"], r.text
    r = await _post("/v1/events", json=_event(sent_at=now + 0.32))
    assert r.status_code == 200, "a fraction of a second is accepted, as documented"
    r = await _post("/v1/events", json=_event(platform="my:chat"))
    assert r.status_code == 400 and "platform must not contain ':'" in r.json()["error"], r.text
    r = await _post("/v1/events", content=b"")
    assert r.status_code == 400 and r.json()["error"].endswith("the body is empty"), r.text


def test_an_ack_with_an_unknown_status_is_warned_once(tmp_path, caplog) -> None:
    import logging

    from persona_agent import outbox

    box = outbox.Outbox(outbox.HandleStore(tmp_path / "handles.json"))
    caplog.set_level(logging.WARNING, logger="agent.outbox")
    for _ in range(2):
        box._handed["d1"] = type("D", (), {"connector_id": "c1", "items": [1], "delivery_id": "d1",
                                           "future": type("F", (), {"done": lambda self: False})(),
                                           "key": "k", "handle": {}})()
        box._resolve = lambda d, status, sent: None
        box.ack("c1", {"delivery_id": "d1", "status": "success"})
    said = [r.getMessage() for r in caplog.records if "unknown status" in r.getMessage()]
    assert len(said) == 1 and "sent" in said[0], said


def test_french_help_puts_a_space_before_argparse_colons(monkeypatch, capsys) -> None:
    import argparse

    import pytest

    from persona_agent import doctor, langs

    monkeypatch.setenv("AGENT_LANG", "fr")
    langs._terminal_lang.clear()
    monkeypatch.setattr(argparse, "_", langs.term)
    with pytest.raises(SystemExit):
        doctor.main(["--help"], prog="personagent doctor")
    langs._terminal_lang.clear()
    assert "\noptions :" in capsys.readouterr().out
