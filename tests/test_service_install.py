"""`personagent service`: the unit and plist it writes, and the commands it runs
through stand-ins for systemctl, loginctl and launchctl."""
from __future__ import annotations

import json
import os
from pathlib import Path
import plistlib
import shlex
import sys

import pytest

from helpers import check
from persona_agent import pageaccess, service
from persona_agent import setup_wizard as sw

STANDIN = """\
import json, os, sys
from pathlib import Path
with Path(os.environ["STANDIN_LOG"]).open("a", encoding="utf-8") as out:
    out.write(json.dumps(sys.argv[1:]) + "\\n")
words = [word for word in sys.argv[2:] if word != "--user"]
if words[:1] == ["show-user"]:
    print("Linger=no")
elif words[:1] == ["is-enabled"]:
    print("enabled")
elif words[:1] == ["is-active"]:
    print("active")
elif words[:1] == ["print"]:
    print("state = running")
elif words[:1] == ["enable-linger"]:
    sys.exit(1)
"""


@pytest.fixture
def standins(tmp_path, monkeypatch):
    """systemctl, loginctl and launchctl on PATH, each recording its arguments."""
    folder = tmp_path / "bin"
    folder.mkdir()
    script = tmp_path / "standin.py"
    script.write_text(STANDIN, encoding="utf-8")
    log = tmp_path / "calls.jsonl"
    monkeypatch.setenv("STANDIN_LOG", str(log))
    for tool in ("systemctl", "loginctl", "launchctl"):
        if os.name == "nt":
            # Found by the batch file's own folder: a path outside ASCII does not survive cmd's code page.
            (folder / f"{tool}.cmd").write_text(
                f'@"{sys.executable}" "%~dp0..\\standin.py" {tool} %*\r\n', encoding="utf-8")
        else:
            path = folder / tool
            path.write_text(f"#!/bin/sh\nexec {shlex.quote(sys.executable)} {shlex.quote(str(script))} "
                            f"{tool} \"$@\"\n", encoding="utf-8")
            path.chmod(0o755)
    monkeypatch.setenv("PATH", str(folder))

    def calls() -> list[list[str]]:
        if not log.is_file():
            return []
        return [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
    return calls


@pytest.fixture
def home(tmp_path, monkeypatch):
    place = tmp_path / "my home %d $HOME"
    place.mkdir()
    sw.write_env(place / ".env", {"LLM_API_KEY": "k"})
    monkeypatch.setenv("AGENT_HOME", str(place))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("HOME", str(tmp_path / "user"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "user"))
    for name in (*pageaccess.SETTINGS, pageaccess.CONTAINER_ENV):
        monkeypatch.delenv(name, raising=False)
    return place


def _exec_words(line: str) -> list[str]:
    """ExecStart= read back as systemd reads it: quotes group, \\ escapes, %% and $$ are one."""
    words = shlex.split(line[len("ExecStart="):], posix=True)
    return [word.replace("%%", "%").replace("$$", "$") for word in words]


def test_the_unit_runs_up_for_this_home_with_this_python(home):
    text = service.unit(home)
    lines = text.splitlines()
    execs = [line for line in lines if line.startswith("ExecStart=")]
    check("one ExecStart", len(execs) == 1)
    argv = _exec_words(execs[0])
    check("this interpreter, on this home, up", argv[0] == service.command(home)[0][0]
          and argv[1:] == ["-m", "persona_agent", "--home", str(home.resolve()), "up"], argv)
    check("an absolute program", Path(argv[0]).is_absolute())
    check("% and $ are escaped", "%d" not in execs[0].replace("%%", "") and "$HOME" not in execs[0].replace("$$", ""))
    for setting in ("Restart=on-failure", "RestartPreventExitStatus=2", "KillMode=mixed", "UMask=0077",
                    "WantedBy=default.target", "Type=simple"):
        check(setting, setting in lines)
    log = next(line for line in lines if line.startswith("StandardOutput="))
    check("output beside the home's other logs", log == "StandardOutput=append:"
          + str(home.resolve() / "runtime" / "desktop" / "service.log").replace("%", "%%"))
    check("no network target a user manager cannot see", "network-online" not in text)


def test_the_plist_keeps_up_running_and_logs_with_the_rest(home):
    data = plistlib.loads(service.plist(home))
    check("its label", data["Label"] == service.label(home) and data["Label"].startswith(service.LABEL))
    check("up for this home", data["ProgramArguments"][1:] == ["-m", "persona_agent", "--home", str(home.resolve()), "up"])
    check("started at load, again after a failure", data["RunAtLoad"] is True
          and data["KeepAlive"] == {"SuccessfulExit": False})
    check("its log", data["StandardOutPath"] == data["StandardErrorPath"]
          == str(home.resolve() / "runtime" / "desktop" / "service.log"))


def test_another_home_gets_a_name_of_its_own(home, tmp_path):
    other = tmp_path / "second"
    check("a suffix for another home", service.name(home).startswith("personagent-")
          and service.name(home) != service.name(other))
    check("the same home, the same name", service.name(home) == service.name(home))


def test_dry_run_prints_and_changes_nothing(home, standins, monkeypatch, capsys):
    monkeypatch.setattr(service, "system", lambda: "linux")
    assert service.main(["install", "--dry-run"]) == 0
    said = capsys.readouterr().out
    check("the unit", "[Service]" in said and "ExecStart=" in said)
    check("the commands", "systemctl --user enable --now" in said and "loginctl enable-linger" in said)
    check("nothing ran", standins() == [])
    check("nothing written", not service.unit_path(home).exists())


def test_install_status_restart_and_remove_on_linux(home, standins, monkeypatch, capsys):
    monkeypatch.setattr(service, "system", lambda: "linux")
    unit_name = f"{service.name(home)}.service"
    assert service.main(["install"]) == 0
    said = capsys.readouterr().out
    check("the unit is written", service.unit_path(home).read_text(encoding="utf-8") == service.unit(home))
    check("in the user's systemd folder", service.unit_path(home).parent.parts[-2:] == ("systemd", "user"))
    names = [call[:4] for call in standins()]
    check("reloaded, enabled and started", ["systemctl", "--user", "daemon-reload"] in names
          and ["systemctl", "--user", "enable", "--now"] in names, str(names))
    check("lingering asked for", any(call[:2] == ["loginctl", "enable-linger"] for call in standins()))
    check("its refusal is explained", "sudo loginctl enable-linger" in said)
    check("and no reboot is promised without it", "after a reboot" not in said and "while you are logged in" in said)
    log = home / "runtime" / "desktop" / "service.log"
    check("the log exists before the service writes it", log.is_file())
    assert service.main(["status"]) == 0
    said = capsys.readouterr().out
    check("status reads systemd", "enabled" in said and "active" in said and "Lingering is off" in said, said)
    assert service.main(["restart"]) == 0
    check("restart", ["systemctl", "--user", "restart", unit_name] in standins())
    assert service.main(["remove"]) == 0
    check("removed", not service.unit_path(home).exists()
          and ["systemctl", "--user", "disable", "--now", unit_name] in standins())
    assert service.main(["status"]) == 3


def test_install_and_remove_on_macos(home, standins, monkeypatch, capsys):
    monkeypatch.setattr(service, "system", lambda: "macos")
    monkeypatch.setattr(service, "_domain", lambda: "gui/501")
    monkeypatch.setattr(service.Path, "home", classmethod(lambda cls: home.parent / "user"))
    assert service.main(["install"]) == 0
    path = service.plist_path(home)
    check("in LaunchAgents", path.parent.name == "LaunchAgents" and path.is_file())
    check("the plist", plistlib.loads(path.read_bytes()) == plistlib.loads(service.plist(home)))
    target = f"gui/501/{service.label(home)}"
    check("bootstrapped", ["launchctl", "bootstrap", "gui/501", str(path)] in standins())
    check("and enabled", ["launchctl", "enable", target] in standins())
    assert service.main(["status"]) == 0
    assert service.main(["restart"]) == 0
    check("restart kicks it", ["launchctl", "kickstart", "-k", target] in standins())
    assert service.main(["remove"]) == 0
    check("booted out and gone", not path.exists() and ["launchctl", "bootout", target] in standins())


def test_install_is_refused_when_up_would_not_stay_up(home, standins, monkeypatch, capsys):
    monkeypatch.setattr(service, "system", lambda: "linux")
    sw.write_env(home / ".env", {"LLM_API_KEY": ""})
    assert service.main(["install"]) == 1
    check("no key and no page for other devices", "Finish the setup first" in capsys.readouterr().err)
    sw.write_env(home / ".env", {"PAGE_HOST": "0.0.0.0"})
    assert service.main(["install"]) == 1
    check("a network page without a password", "PAGE_PASSWORD" in capsys.readouterr().err)
    sw.write_env(home / ".env", {"PAGE_PASSWORD": pageaccess.hash_password("plum-orchard-41-lantern")})
    assert service.main(["install", "--dry-run"]) == 0
    check("setup from another device is enough", "ExecStart=" in capsys.readouterr().out)
    check("nothing ran", standins() == [])


def test_windows_uses_the_apps_own_start_at_sign_in(home, monkeypatch, capsys):
    monkeypatch.setattr(service, "system", lambda: "windows")
    assert service.main(["install", "--dry-run"]) == 0
    said = capsys.readouterr().out
    check("the startup shortcut", "--background" in said and "CreateShortcut" in said and str(home) in said, said)
    ran = []
    from persona_agent import shortcut
    monkeypatch.setattr(shortcut, "run", lambda source: ran.append(source) or "")
    assert service.main(["install"]) == 0
    check("one shortcut kind: start at sign-in", len(ran) == 1 and "--background" in ran[0])
    assert service.main(["remove"]) == 0
    check("removed through the same", "Remove-Item" in ran[1])
    assert service.main(["restart"]) == 1


def test_the_launch_agent_says_which_manager_started_it(home):
    import plistlib

    made = plistlib.loads(service.plist(home))
    check("so that a refusal can end cleanly there", made["EnvironmentVariables"]["PERSONAGENT_SERVICE"] == "launchd")
