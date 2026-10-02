"""Settings 1.0 retired: refuse to start on them, rename them with `doctor --fix`."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from persona_agent import cli, preflight, server

ROOT = Path(__file__).resolve().parents[1]
OLD_ENV = (
    "# my bot\n"
    "LLM_API_KEY=sk-x\n"
    "QQ_GROUPS=111,222  # the groups\n"
    "export OWNER_QQ=42\n"
    "PORT=9000\n"
    "BOT_NAME=Mira\n")


def _home(tmp_path: Path, text: str = OLD_ENV) -> Path:
    (tmp_path / ".env").write_text(text, encoding="utf-8", newline="")
    return tmp_path


def _clean_env() -> dict:
    env = {k: v for k, v in os.environ.items()
           if k not in preflight.RENAMED and not k.startswith(("LLM_", "AGENT_", "ACCESS_"))}
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def _personagent(*args: str, home: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "persona_agent", *args],
                          cwd=ROOT, env={**_clean_env(), "AGENT_HOME": str(home)},
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=120)


def test_a_retired_name_in_env_or_the_environment_is_found(tmp_path: Path) -> None:
    home = _home(tmp_path)
    found = {(old, new, where)
             for old, new, where in preflight.retired_settings(home, environ={})}
    assert found == {("QQ_GROUPS", "ACCESS_GROUPS", ".env"),
                     ("OWNER_QQ", "ADMIN_IDS", ".env"),
                     ("PORT", "SERVER_PORT", ".env"),
                     ("BOT_NAME", "PERSONA_NAME", ".env")}
    bare = _home(tmp_path / "bare", "LLM_API_KEY=x\n") if (tmp_path / "bare").mkdir() is None else None
    live = preflight.retired_settings(bare, environ={"GATEWAY_TOKEN": "t", "HOST": "zsh", "PORT": "1"})
    assert live == [("GATEWAY_TOKEN", "CONNECTOR_TOKEN", "environment")], \
        "HOST and PORT from the shell or a host are not the operator's settings"


def test_a_current_env_has_nothing_retired(tmp_path: Path) -> None:
    home = _home(tmp_path, "LLM_API_KEY=x\nACCESS_GROUPS=1\nSERVER_PORT=8080\n")
    assert preflight.retired_settings(home, environ={}) == []
    assert preflight.retired_problem("personagent doctor --fix", home, environ={}) is None


def test_the_refusal_says_one_sentence_per_setting_and_the_fix(tmp_path: Path) -> None:
    home = _home(tmp_path)
    problem = preflight.retired_problem("personagent doctor --fix", home, environ={})
    lines = problem.splitlines()
    assert "QQ_GROUPS -> ACCESS_GROUPS" in problem and "OWNER_QQ -> ADMIN_IDS" in problem
    assert len(lines) == 5 and "personagent doctor --fix" in lines[-1]


def test_start_is_refused_while_a_retired_name_is_set(monkeypatch, tmp_path: Path) -> None:
    home = _home(tmp_path)
    monkeypatch.setattr(server, "ROOT", home)
    problem = server.startup_problem("127.0.0.1", 0)
    assert problem and "QQ_GROUPS -> ACCESS_GROUPS" in problem
    result = _personagent("run", home=home)
    assert result.returncode == 2, result.stderr
    assert "BOT_NAME -> PERSONA_NAME" in result.stderr


def test_fix_renames_in_place_keeping_values_comments_and_a_backup(tmp_path: Path) -> None:
    home = _home(tmp_path)
    changes = preflight.migrate_env_file(home / ".env")
    assert {(o, n, a) for o, n, a in changes} == {
        ("QQ_GROUPS", "ACCESS_GROUPS", "renamed"), ("OWNER_QQ", "ADMIN_IDS", "renamed"),
        ("PORT", "SERVER_PORT", "renamed"), ("BOT_NAME", "PERSONA_NAME", "renamed")}
    assert (home / ".env").read_text(encoding="utf-8") == (
        "# my bot\n"
        "LLM_API_KEY=sk-x\n"
        "ACCESS_GROUPS=111,222  # the groups\n"
        "export ADMIN_IDS=42\n"
        "SERVER_PORT=9000\n"
        "PERSONA_NAME=Mira\n")
    assert (home / ".env.bak").read_text(encoding="utf-8") == OLD_ENV
    assert preflight.retired_settings(home, environ={}) == []
    assert preflight.migrate_env_file(home / ".env") == [], "a second run changes nothing"


def test_fix_never_overwrites_a_new_name_that_is_already_set(tmp_path: Path) -> None:
    home = _home(tmp_path, "ACCESS_GROUPS=9\r\nQQ_GROUPS=1,2\r\nALLOWED_GROUPS=3\r\n")
    changes = preflight.migrate_env_file(home / ".env")
    assert [(o, a) for o, _n, a in changes] == [("QQ_GROUPS", "dropped"),
                                                ("ALLOWED_GROUPS", "dropped")]
    text = (home / ".env").read_bytes().decode("utf-8")
    assert text.startswith("ACCESS_GROUPS=9\r\n"), "CRLF line endings survive"
    assert "\n# retired, ACCESS_GROUPS is already set: QQ_GROUPS=1,2\r\n" in text
    assert preflight.retired_settings(home, environ={}) == []


def test_two_old_names_for_one_new_name_keep_the_first(tmp_path: Path) -> None:
    home = _home(tmp_path, "QQ_GROUPS=1\nALLOWED_GROUPS=2\n")
    preflight.migrate_env_file(home / ".env")
    lines = (home / ".env").read_text(encoding="utf-8").splitlines()
    assert lines[0] == "ACCESS_GROUPS=1" and lines[1].startswith("# retired")


def test_doctor_fix_then_the_service_may_start(tmp_path: Path) -> None:
    home = _home(tmp_path)
    before = _personagent("doctor", "--json", home=home)
    assert before.returncode == 1 and '"retired_settings"' in before.stdout
    fixed = _personagent("doctor", "--fix", home=home)
    assert fixed.returncode == 0, fixed.stderr
    assert "renamed QQ_GROUPS -> ACCESS_GROUPS" in fixed.stdout
    assert preflight.retired_settings(home, environ={}) == []
    again = _personagent("doctor", "--fix", home=home)
    assert "Nothing to rename" in again.stdout


def test_doctor_help_and_hints_use_the_installed_spelling(tmp_path: Path) -> None:
    helped = _personagent("doctor", "--help", home=tmp_path)
    assert helped.stdout.startswith("usage: personagent doctor"), helped.stdout
    assert "tools/healthcheck.py" not in helped.stdout
    bare = _personagent("doctor", home=tmp_path)
    assert "`personagent init`" in bare.stdout, bare.stdout


def test_learned_help_names_the_command_not_a_script(capsys) -> None:
    with pytest.raises(SystemExit):
        cli.main(["learned", "--help"])
    assert "tools/candidates_admin.py" not in capsys.readouterr().out
    from persona_agent import ledger_admin

    assert "tools/" not in ledger_admin.__doc__


def test_home_is_accepted_after_the_command_too(monkeypatch, tmp_path: Path) -> None:
    seen: dict = {}

    def probe(argv, prog):
        seen.update(argv=argv, prog=prog, home=os.environ.get("AGENT_HOME"))
        return 0

    monkeypatch.setitem(cli.COMMANDS, "chat", (__name__, "probe", "x"))
    monkeypatch.setattr(sys.modules[__name__], "probe", probe, raising=False)
    monkeypatch.setenv("AGENT_HOME", "restored by monkeypatch")
    for argv in (["chat", "--home", str(tmp_path), "--x"], ["chat", "--x", f"--home={tmp_path}"],
                 ["--home", str(tmp_path), "chat", "--x"]):
        seen.clear()
        os.environ.pop("AGENT_HOME", None)
        assert cli.main(argv) == 0
        assert seen["argv"] == ["--x"], argv
        assert Path(seen["home"]) == tmp_path.resolve(), argv
