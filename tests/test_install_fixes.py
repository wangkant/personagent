"""Setup and install edge cases: .env quoting, provider switches, AstrBot entries, commands, quickstart."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from dotenv import dotenv_values

import quickstart
from persona_agent import setup_wizard as sw

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _english():
    sw.set_lang("en")
    yield
    sw.set_lang("en")


@pytest.mark.parametrize("value", [
    "Zed #1", "#hash", " padded ", "it's", 'say "hi"', "a\\b", "C:\\Program Files\\x", "plain",
    "key-with-dash_and.dot", "sk-abc # not a comment", "'quoted'"])
def test_env_values_survive_the_round_trip_through_dotenv(tmp_path: Path, value: str) -> None:
    env = tmp_path / ".env"
    env.write_text("# keep\nPERSONA_NAME=old\n", encoding="utf-8")
    sw.write_env(env, {"PERSONA_NAME": value, "ADMIN_NAME": value})
    assert dotenv_values(env)["PERSONA_NAME"] == value
    assert dotenv_values(env)["ADMIN_NAME"] == value
    assert sw.env_get(env, "PERSONA_NAME") == value.strip()
    assert env.read_text(encoding="utf-8").startswith("# keep\n")


def test_a_plain_value_is_written_bare() -> None:
    assert sw.set_env_values("", {"A": "https://api.example.com/v1", "B": "C:\\x\\y"}) \
        == "A=https://api.example.com/v1\nB=C:\\x\\y"


def test_a_name_with_a_hash_reaches_the_agent_whole(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AGENT_HOME", str(tmp_path))
    args = sw.init_parser("init").parse_args(["--no-input", "--name", "Zed #1", "--lang", "en"])
    assert sw.apply_flags(tmp_path, args) == "Zed #1"
    assert dotenv_values(tmp_path / ".env")["PERSONA_NAME"] == "Zed #1"
    assert "Your name is Zed #1." in (tmp_path / "persona.txt").read_text(encoding="utf-8")


def test_init_without_a_terminal_or_flags_exits_nonzero(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setenv("AGENT_HOME", str(tmp_path))
    monkeypatch.setattr("builtins.input", lambda *_: pytest.fail("asked a question"))
    assert sw.main([]) == 2
    capsys.readouterr()
    assert sw.main(["--no-input"]) == 0, "asking for no questions is a choice"
    assert sw.main(["--name", "Mika"]) == 0, "flags configured it"
    assert sw.run([], "personagent init") == 0, "callers that wrap init decide for themselves"


def test_switching_provider_does_not_carry_the_old_key(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setenv("AGENT_HOME", str(tmp_path))
    monkeypatch.setenv("NEW_KEY", "sk-new")
    parse = sw.init_parser("init").parse_args
    sw.apply_flags(tmp_path, parse(["--no-input", "--lang", "en", "--provider", "deepseek"]))
    sw.write_env(tmp_path / ".env", {"LLM_API_KEY": "sk-old"})

    sw.apply_flags(tmp_path, parse(["--no-input", "--lang", "en", "--provider", "deepseek"]))
    assert sw.env_get(tmp_path / ".env", "LLM_API_KEY") == "sk-old", "same service keeps its key"

    capsys.readouterr()
    sw.apply_flags(tmp_path, parse(["--no-input", "--lang", "en", "--provider", "openai"]))
    assert sw.env_get(tmp_path / ".env", "LLM_API_KEY") == ""
    assert "cleared" in capsys.readouterr().out

    sw.write_env(tmp_path / ".env", {"LLM_API_KEY": "sk-old"})
    sw.apply_flags(tmp_path, parse(["--no-input", "--lang", "en", "--provider", "deepseek", "--key-env", "NEW_KEY"]))
    assert sw.env_get(tmp_path / ".env", "LLM_API_KEY") == "sk-new"


def test_an_existing_platform_entry_keeps_its_own_settings(tmp_path: Path) -> None:
    data = tmp_path / "data"
    data.mkdir()
    cfg = data / "cmd_config.json"
    mine = {"id": "telegram", "type": "telegram", "enable": False, "telegram_token": "old",
            "telegram_api_base_url": "https://tg.proxy.example/bot", "start_message": "hi"}
    other = {"id": "qq", "type": "aiocqhttp", "enable": True}
    cfg.write_text(json.dumps({"platform": [mine, other]}), encoding="utf-8")

    sw.write_astrbot_platform(data, sw.astrbot_platform_entry("telegram", {"telegram_token": "new"}))
    platforms = json.loads(cfg.read_text(encoding="utf-8"))["platform"]
    assert [p["id"] for p in platforms] == ["telegram", "qq"], "order is kept"
    assert platforms[0]["telegram_token"] == "new" and platforms[0]["enable"] is True
    assert platforms[0]["telegram_api_base_url"] == "https://tg.proxy.example/bot"
    assert platforms[0]["start_message"] == "hi"

    sw.write_astrbot_platform(data, sw.astrbot_platform_entry("discord", {"discord_token": "d"}))
    assert [p["id"] for p in json.loads(cfg.read_text(encoding="utf-8"))["platform"]] \
        == ["telegram", "qq", "discord"]


def test_a_command_names_a_home_the_bare_command_would_not_find(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("AGENT_HOME", raising=False)
    monkeypatch.setattr(sw.homes, "is_checkout", lambda *a: False)
    monkeypatch.setattr(sw.homes, "default_home", lambda: tmp_path / "personagent")
    cwd_home = sw.Launcher(python="python", home=tmp_path / "somewhere")
    assert "--home" in " ".join(cwd_home.shown("demo"))
    assert "--home" in " ".join(cwd_home.argv("chat"))
    usual = sw.Launcher(python="python", home=tmp_path / "personagent")
    assert "--home" not in " ".join(usual.shown("demo"))


def test_a_python_path_with_spaces_is_runnable_in_powershell(monkeypatch) -> None:
    path = "C:\\Users\\Jane Doe\\venv\\Scripts\\python.exe"
    monkeypatch.setattr(sw.os, "name", "nt")
    monkeypatch.delenv("PROMPT", raising=False)
    assert sw._program(path) == f'& "{path}"'
    monkeypatch.setenv("PROMPT", "$P$G")
    assert sw._program(path) == f'"{path}"', "cmd.exe takes the quoted path as it is"
    assert sw._program("C:\\py\\python.exe") == "C:\\py\\python.exe"


def test_a_failed_pip_install_ends_with_advice_not_a_traceback(monkeypatch, tmp_path: Path) -> None:
    def fail(cmd, **kw):
        raise subprocess.CalledProcessError(1, cmd)

    monkeypatch.setattr(quickstart.subprocess, "check_call", fail)
    with pytest.raises(SystemExit) as stop:
        quickstart.ensure_deps(tmp_path / ".venv")
    assert "network" in str(stop.value) and "python quickstart.py" in str(stop.value)
    monkeypatch.setattr(quickstart, "ROOT", tmp_path)
    with pytest.raises(SystemExit) as stop:
        quickstart.ensure_venv()
    assert "python quickstart.py" in str(stop.value)


def test_release_is_gated_on_main_and_the_tests() -> None:
    text = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    build = text.split("\n  pypi:")[0]
    assert "merge-base --is-ancestor" in build and "origin main" in build
    assert "python -m pytest" in build
    assert build.index("merge-base --is-ancestor") < build.index("python -m build")
    assert build.index("python -m pytest") < build.index("python -m build")
