"""The local supervisor owns only processes it starts, can be paused safely,
and leaves none of them running when it ends, however it ends."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from persona_agent import services as svc
from persona_agent.services import Services
from persona_agent import setup_wizard as sw
import pytest

ROOT = Path(__file__).resolve().parents[1]

# Stands in for a service: says which process it is and how it was run, then waits.
PROBE = """\
import os, sys, time
with open(sys.argv[1] + ".tmp", "w") as out:
    out.write(f"{os.getpid()} {__name__}")
os.replace(sys.argv[1] + ".tmp", sys.argv[1])
time.sleep(float(sys.argv[2]))
sys.exit(3)
"""

# An app that starts a probe and is then killed before it can stop it.
APP = """\
import os, sys, time
from pathlib import Path
from persona_agent.services import Services
home = Path(sys.argv[1])
Services(home)._spawn("probe", [sys.executable, "-m", "probe_child", sys.argv[2], "60"],
                      cwd=home, env=dict(os.environ))
time.sleep(60)
"""

NO_SUCH_PROCESS = 2 ** 30


def _probe_env(tmp_path: Path) -> dict:
    (tmp_path / "probe_child.py").write_text(PROBE, encoding="utf-8")
    return dict(os.environ, PYTHONPATH=os.pathsep.join([str(ROOT), str(tmp_path)]))


def _probe_says(out: Path, seconds: float = 30) -> list[str]:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if out.is_file():
            return out.read_text(encoding="utf-8").split()
        time.sleep(0.05)
    raise AssertionError("the probe never started")


def _gone(pid: int, seconds: float = 15) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if "probe_child" not in svc._command_line(pid):
            return True
        time.sleep(0.1)
    return False


def _kill(pid: int) -> None:
    if "probe_child" in svc._command_line(pid):
        os.kill(pid, signal.SIGTERM if os.name == "nt" else signal.SIGKILL)


def test_close_terminates_only_registered_live_processes(tmp_path):
    calls = []
    class Process:
        def poll(self):
            return None
        def terminate(self):
            calls.append("terminate")
        def wait(self, timeout):
            calls.append("wait")
            return 0
    services = Services(tmp_path)
    services.processes["agent"] = Process()
    services.processes["astrbot"] = Process()
    services.close()
    assert calls == ["terminate", "wait", "terminate", "wait"]
    assert services.processes == {}
    services.close()
    assert len(calls) == 4


def test_shutdown_prevents_a_background_job_from_starting_more_children(tmp_path):
    services = Services(tmp_path)
    services.shutdown()
    with pytest.raises(RuntimeError, match="closed"):
        services.start_agent()
    with pytest.raises(RuntimeError, match="closed"):
        services.start_astrbot()


def test_agent_launcher_uses_fresh_configuration_and_never_puts_keys_in_argv(tmp_path, monkeypatch):
    services = Services(tmp_path)
    sw.write_env(tmp_path / ".env", {"LLM_API_KEY": "fresh-secret", "SERVER_PORT": "0"})
    monkeypatch.setenv("LLM_API_KEY", "stale-secret")
    launches = []
    monkeypatch.setattr(services, "_spawn", lambda *args, **kwargs: launches.append((args, kwargs)))
    monkeypatch.setattr(services, "_ready", lambda *args, **kwargs: None)
    services.start_agent()
    args, kwargs = launches[0]
    assert "fresh-secret" not in " ".join(args[1])
    assert kwargs["env"]["LLM_API_KEY"] == "fresh-secret"
    assert kwargs["env"]["AGENT_HOME"] == str(tmp_path)
    assert int(sw.env_get(tmp_path / ".env", "SERVER_PORT")) > 0


def test_astrbot_starts_without_its_dashboard_and_waits_for_its_own_log(tmp_path, monkeypatch):
    from persona_agent.astrbot_install import AstrBotInstallation

    installation = AstrBotInstallation(tmp_path)
    installation.python.parent.mkdir(parents=True)
    installation.python.write_text("", encoding="utf-8")
    data = installation.root / "data"
    data.mkdir(parents=True)
    sw._write_json(data / "cmd_config.json", {"dashboard": {"enable": True, "host": "0.0.0.0"}})
    log = tmp_path / "runtime" / "desktop" / "astrbot.log"
    log.parent.mkdir(parents=True)
    log.write_bytes(b"AstrBot started.\n")   # from an earlier run: must not count
    services = Services(tmp_path)
    launches = []

    class Process:
        def poll(self):
            return None
        def terminate(self):
            pass
        def wait(self, timeout):
            return 0

    def spawn(name, argv, **kwargs):
        launches.append(argv)
        services.processes[name] = Process()
        with log.open("ab") as stream:
            stream.write(b"loading adapters\n")
    offset = log.stat().st_size
    spawn("astrbot", [])
    with pytest.raises(RuntimeError, match="did not become ready"):
        services._started("astrbot", b"AstrBot started.", offset, timeout=0.5)
    assert "astrbot" not in services.processes

    def spawn_and_start(name, argv, **kwargs):
        spawn(name, argv, **kwargs)
        with log.open("ab") as stream:
            stream.write(b"[INFO] AstrBot started.\n")
    monkeypatch.setattr(services, "_spawn", spawn_and_start)
    services.start_astrbot()
    assert "--reset-password" not in launches[-1]
    assert sw._read_json(data / "cmd_config.json")["dashboard"] == {"enable": False, "host": "127.0.0.1"}


def test_a_child_runs_as_python_m_runs_it_and_is_recorded_until_stopped(tmp_path):
    env = _probe_env(tmp_path)
    out = tmp_path / "out.txt"
    record = tmp_path / "runtime" / "desktop" / f"children-{os.getpid()}.json"
    services = Services(tmp_path)
    argv = [sys.executable, "-m", "probe_child", str(out), "0"]
    services._spawn("probe", argv, cwd=tmp_path, env=env)
    process = services.processes["probe"]
    saved = json.loads(record.read_text(encoding="utf-8"))
    assert saved["owner"] == os.getpid() and saved["command"] == svc._command_line(os.getpid())
    assert saved["children"] == {"probe": {"pid": process.pid, "argv": argv}}
    # On Windows it was started suspended, so it must have been let go.
    assert process.wait(timeout=30) == 3
    assert _probe_says(out)[1] == "__main__"
    services.stop("probe")
    assert not record.exists()


def test_children_end_with_the_app_when_it_is_killed(tmp_path):
    env = _probe_env(tmp_path)
    out = tmp_path / "out.txt"
    app = subprocess.Popen([sys.executable, "-c", APP, str(tmp_path), str(out)], cwd=ROOT, env=env)
    pid = None
    try:
        # The interpreter running the probe: under a venv's python.exe, its grandchild.
        pid = int(_probe_says(out)[0])
        # What closing its console window does: the app ends without its exit path.
        app.kill()
        app.wait(timeout=30)
        assert _gone(pid)
    finally:
        app.kill()
        if pid is not None:
            _kill(pid)


def test_leftovers_are_stopped_only_once_their_app_is_gone_and_while_they_are_its(tmp_path, monkeypatch):
    desktop = tmp_path / "runtime" / "desktop"
    desktop.mkdir(parents=True)
    home = str(tmp_path.resolve())
    agent = ["python", "-m", "persona_agent", "--home", home, "run", "--host", "127.0.0.1", "--port", "8080"]
    direct = ["python", "-m", "persona_agent.direct", "--home", home]
    astrbot = [home + "/platforms/tools/envs/astrbot/bin/python", "-m", "astrbot.cli.__main__", "run"]

    def record(owner, command, **children):
        (desktop / f"children-{owner}.json").write_text(
            json.dumps({"owner": owner, "command": command, "children": children}), encoding="utf-8")
    record(101, "personagent start", agent={"pid": 11, "argv": agent}, direct={"pid": 12, "argv": direct},
           astrbot={"pid": 13, "argv": astrbot})
    record(202, "personagent up", agent={"pid": 21, "argv": agent})
    record(303, "personagent start", direct={"pid": 31, "argv": direct})
    lines = {
        101: "",                                      # that app is gone
        11: " ".join(agent),                          # and this is still its agent
        12: f"notepad {home}/persona_agent/x.py",     # a later process with the direct's number
        13: "",                                       # already gone
        202: "personagent up",                        # that app still runs and owns its agent
        21: " ".join(agent),
        303: "unrelated.exe",                         # a later process with that app's number
        31: " ".join(direct),
    }
    monkeypatch.setattr(svc, "_command_line", lambda pid: lines.get(pid, ""))
    ended = []
    monkeypatch.setattr(svc, "_end", lambda pid, command: ended.append(pid))
    assert svc.stop_leftovers(tmp_path) == ["agent", "direct"]
    assert ended == [11, 31]
    assert [path.name for path in desktop.iterdir()] == ["children-202.json"]


def test_a_leftover_child_is_stopped_with_what_it_started(tmp_path):
    env = _probe_env(tmp_path)
    out = tmp_path / "out.txt"
    home = tmp_path.resolve()
    argv = [sys.executable, "-m", "probe_child", str(out), "60", "--home", str(home)]
    # As the app starts a child on POSIX: leading its own process group.
    process = subprocess.Popen(argv, cwd=tmp_path, env=env, start_new_session=os.name != "nt",
                               creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    pid = None
    try:
        pid = int(_probe_says(out)[0])
        desktop = home / "runtime" / "desktop"
        desktop.mkdir(parents=True)
        (desktop / "children-1.json").write_text(json.dumps({
            "owner": NO_SUCH_PROCESS, "command": "personagent start",
            "children": {"probe": {"pid": process.pid, "argv": argv}}}), encoding="utf-8")
        assert svc.stop_leftovers(home) == ["probe"]
        process.wait(timeout=15)
        assert _gone(pid)
        assert not (desktop / "children-1.json").exists()
    finally:
        process.kill()
        if pid is not None:
            _kill(pid)
