"""The optional platform installer: no downloads or services in the unit tests."""
from __future__ import annotations

import io
import subprocess
from pathlib import Path

import pytest

from persona_agent import astrbot_install as installer
from persona_agent import setup_wizard as sw


def _touch(path: Path, text: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_install_initialise_and_repeat_without_redownloading(monkeypatch, tmp_path):
    installation = installer.AstrBotInstallation(tmp_path)
    monkeypatch.setenv("ASTRBOT_ROOT", "some-other-install")
    monkeypatch.setenv("PYTHONPATH", "some-other-python")
    monkeypatch.setenv("VIRTUAL_ENV", "some-other-venv")
    calls = []
    monkeypatch.setattr(installer.venv.EnvBuilder, "create", lambda self, path: None)

    def run(argv, **kw):
        calls.append((argv, kw))
        assert kw["check"]
        assert kw["env"]["ASTRBOT_ROOT"] == str(installation.root)
        assert "PYTHONPATH" not in kw["env"]
        assert "VIRTUAL_ENV" not in kw["env"]
        assert Path(kw["env"]["UV_TOOL_DIR"]).is_relative_to(tmp_path)
        if "tool" in argv:
            _touch(installation.executable)
            _touch(installation.python)
        elif "init" in argv:
            _touch(installation.root / ".astrbot")
        elif "-c" in argv:
            _touch(installation.root / "data/cmd_config.json", '{"platform": []}')

    monkeypatch.setattr(installer.subprocess, "run", run)
    data = installer.install_astrbot(tmp_path)
    assert len(calls) == 4
    assert calls[1][0][-3:] == ["--python", "3.12", "astrbot>=4.29,<5"]
    assert data == installation.root / "data"
    assert installer.install_astrbot(tmp_path) == data
    assert len(calls) == 4
    assert (installation.root / ".initial-dashboard-login").is_file()


def test_an_interrupted_install_is_retried(monkeypatch, tmp_path):
    installation = installer.AstrBotInstallation(tmp_path)
    _touch(installation.executable)  # executable without a working environment
    monkeypatch.setattr(installer.venv.EnvBuilder, "create", lambda self, path: None)
    calls = []

    def fail(argv, **kw):
        calls.append(argv)
        raise subprocess.CalledProcessError(1, argv)

    monkeypatch.setattr(installer.subprocess, "run", fail)
    with pytest.raises(subprocess.CalledProcessError):
        installer.install_astrbot(tmp_path)
    assert calls and "pip" in calls[0]
    assert not (installation.root / "data/cmd_config.json").exists()


def test_first_start_prints_a_password_and_later_starts_keep_it(monkeypatch, tmp_path):
    installation = installer.AstrBotInstallation(tmp_path)
    _touch(installation.executable)
    marker = installation.root / ".initial-dashboard-login"
    _touch(marker)
    calls = []
    monkeypatch.setattr(installer.subprocess, "call", lambda argv, **kw: calls.append((argv, kw)) or 0)
    assert installer.start_astrbot(tmp_path) == 0
    assert calls[0][0][-1] == "--reset-password"
    assert calls[0][1]["cwd"] == installation.root
    assert not marker.exists()
    installer.start_astrbot(tmp_path)
    assert calls[1][0][-1] == "run"


def test_missing_install_has_an_actionable_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="connect astrbot --install"):
        installer.start_astrbot(tmp_path)


def test_install_flag_connects_the_platform_and_shares_the_token(monkeypatch, tmp_path, capsys):
    home = tmp_path / "agent"
    data = installer.AstrBotInstallation(home).root / "data"
    monkeypatch.setattr(sw.homes, "find_home", lambda: home)
    _touch(data / "cmd_config.json", '{"platform": []}')
    monkeypatch.setattr(sw, "_install_astrbot", lambda home: data)
    assert sw.connect_main(["astrbot", "--install", "--platform", "telegram", "--token", "bot:token"]) == 0
    cfg = sw.read_astrbot_config(data)
    assert cfg["connector_token"] == sw.env_get(home / ".env", "CONNECTOR_TOKEN")
    assert cfg["connector_token"]
    assert cfg["groups"] == [] and cfg["dm_users"] == []
    output = capsys.readouterr().out
    assert "connect astrbot --start" in output
    assert "bot:token" not in output


def test_invalid_install_flags_do_not_download(monkeypatch, tmp_path):
    monkeypatch.setattr(sw.homes, "find_home", lambda: tmp_path)
    monkeypatch.setattr(sw, "_install_astrbot", lambda home: pytest.fail("must validate first"))
    with pytest.raises(SystemExit):
        sw.connect_main(["astrbot", "--install", "--platform", "telegram"])
    with pytest.raises(SystemExit, match="omit DATA_DIR"):
        sw.connect_main(["astrbot", str(tmp_path), "--install"])


def test_install_failure_keeps_model_settings(monkeypatch, tmp_path, capsys):
    _touch(tmp_path / ".env", "LLM_API_KEY=existing-key\n")
    monkeypatch.setattr(sw, "find_astrbot_data", lambda: None)
    monkeypatch.setattr(sw, "ask_yn", lambda *a, **kw: True)
    monkeypatch.setattr(sw, "_install_astrbot", lambda home: (_ for _ in ()).throw(OSError("offline")))
    assert sw.step_astrbot(tmp_path / ".env", {}, {}) is None
    assert sw.env_get(tmp_path / ".env", "LLM_API_KEY") == "existing-key"
    assert "--install" in capsys.readouterr().out


def test_install_in_the_wizard_continues_into_platform_configuration(monkeypatch, tmp_path):
    data = installer.AstrBotInstallation(tmp_path).root / "data"
    _touch(data / "cmd_config.json", '{"platform": []}')
    _touch(tmp_path / ".env")
    sw.set_lang("en")
    monkeypatch.setattr(sw, "find_astrbot_data", lambda: None)
    monkeypatch.setattr(sw, "_install_astrbot", lambda home: data)
    def yes(prompt, default_yes=True):
        return "Docker" not in prompt
    monkeypatch.setattr(sw, "ask_yn", yes)
    monkeypatch.setattr(sw, "ask_number", lambda *a, **kw: 2)
    answers = iter(["bot:token", "", "", ""])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))
    current = dict.fromkeys(("ADMIN_IDS", "ACCESS_GROUPS", "ACCESS_DM_USERS", "ADMIN_NAME"), "")
    result = sw.step_astrbot(tmp_path / ".env", current, {})
    assert result["data_dir"] == data and result["kind"] == "telegram"
    assert sw.read_astrbot_config(data)["connector_token"]


@pytest.mark.parametrize("visible", [False, True])
def test_api_key_display_is_explicit(monkeypatch, tmp_path, capsys, visible):
    sw.set_lang("en")
    key = "sk-existing-1234567890"
    current = {"LLM_API_KEY": key, "LLM_BASE_URL": "https://api.deepseek.com", "LLM_MODEL": "deepseek-flash"}
    answers = iter(["", "", "y" if visible else "n", ""] if visible else ["", "", "n"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))
    hidden_calls = []
    monkeypatch.setattr(sw, "_read_secret", lambda prompt: hidden_calls.append(prompt) or "")
    assert sw.step_model(current)["LLM_API_KEY"] == key
    output = capsys.readouterr().out
    assert (key in output) is visible
    assert bool(hidden_calls) is not visible


class Terminal(io.StringIO):
    def isatty(self):
        return True


def test_start_menu_reloads_settings_and_keeps_the_key_masked(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(sw.homes, "find_home", lambda: tmp_path)
    monkeypatch.setattr(sw.sys, "stdin", Terminal())
    choices = iter(["2", "0"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(choices))
    def configure(argv, **kw):
        assert argv[-2:] == ["init", "--terminal"]
        _touch(tmp_path / ".env", "PERSONA_NAME=Mira\nLLM_API_KEY=sk-secret-1234567890\nAGENT_LANG=en\n")
        return 0
    monkeypatch.setattr(sw.subprocess, "call", configure)
    assert sw.start_main([]) == 0
    output = capsys.readouterr().out
    assert "Mira" in output and "sk-secret-1234567890" not in output


def test_managed_install_is_found_on_the_next_connection(monkeypatch, tmp_path):
    monkeypatch.setattr(sw.homes, "find_home", lambda: tmp_path)
    monkeypatch.delenv(sw.ASTRBOT_ROOT_VAR, raising=False)
    data = installer.AstrBotInstallation(tmp_path).root / "data"
    _touch(data / "cmd_config.json", "{}")
    assert sw.find_astrbot_data() == data
