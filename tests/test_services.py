"""The local supervisor owns only processes it starts, can be paused safely,
and leaves none of them running when it ends, however it ends."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time

from helpers import check
from persona_agent import services as svc
from persona_agent.services import Services
from persona_agent import setup_wizard as sw
import pytest

ROOT = Path(__file__).resolve().parents[1]

# Stands in for a service: says which process it is and how it was run, then waits.
PROBE = """\
import os, subprocess, sys, time
# A service that started a process of its own, which must end with it.
grand = (subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)", "probe_child-grandchild"])
         if float(sys.argv[2]) else None)
with open(sys.argv[1] + ".tmp", "w") as out:
    out.write(f"{os.getpid()} {__name__} {grand.pid if grand else 0}")
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

# Stands in for a command that runs to its end: logs lines, then exits with a code.
TASK = """\
import sys
for n in range(int(sys.argv[2])):
    print(sys.argv[1], n, flush=True)
sys.exit(int(sys.argv[3]))
"""

NO_SUCH_PROCESS = 2 ** 30
# An app's number that no test process has; its command line is whatever the test says.
GONE_APP = NO_SUCH_PROCESS + 1


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
    pids = []
    try:
        # The interpreter running the probe (under a venv's python.exe, a
        # grandchild of the app) and the process the probe started.
        said = _probe_says(out)
        pids = [int(said[0]), int(said[2])]
        # What closing its console window does: the app ends without its exit path.
        app.kill()
        app.wait(timeout=30)
        assert all(_gone(pid) for pid in pids)
    finally:
        app.kill()
        for pid in pids:
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
    # Leading a group never makes another program's command line a child's.
    monkeypatch.setattr(svc, "_leads_group", lambda pid: True)
    ended = []
    monkeypatch.setattr(svc, "_end", lambda pid, command: ended.append(pid))
    assert svc.stop_leftovers(tmp_path) == ["agent", "direct"]
    assert ended == [11, 31]
    assert [path.name for path in desktop.iterdir()] == ["children-202.json"]


UV_STEP = ["-m", "uv", "--no-config", "tool", "install", "--python", "3.12", "astrbot>=4.29,<5"]
UV_ARGS = " ".join(UV_STEP[2:])


def test_a_child_is_told_by_its_command_line_as_posix_lists_it():
    home = "/home/kim/my agent"
    bin_ = home + "/platforms/tools/installer/bin"
    uv = [bin_ + "/python", *UV_STEP]
    # As `_spawn` starts it: the guard's source and the app's number, then the module.
    guarded = f"{bin_}/python -c import os, runpy 4242 {' '.join(UV_STEP)}"
    # uv's module replaces itself with the uv program: same number, same group.
    replaced = f"{bin_}/uv {UV_ARGS}"
    check("the child as it was started", svc._still_child(guarded, uv, home, True))
    check("the program its module replaced itself with", svc._still_child(replaced, uv, home, True))
    check("not that command line on a process that leads no group, a later one with the number",
          not svc._still_child(replaced, uv, home, False))
    check("not the same program doing something else",
          not svc._still_child(f"{bin_}/uv pip list", uv, home, True))
    check("not another home's installer",
          not svc._still_child(replaced.replace("my agent", "other"), uv, home, True))
    check("not a process that is gone", not svc._still_child("", uv, home, True))
    check("not some group leader that only names the home",
          not svc._still_child(f"vim {home}/.env", uv, home, True))
    # What is left of a module's arguments can be as little as "run".
    astrbot = [home + "/platforms/tools/bin/python", "-m", "astrbot", "run"]
    check("not an editor on a file under the home, whose path happens to hold an argument",
          not svc._still_child(f"vim {home}/runtime/desktop/astrbot.log", astrbot, home, True)
          and not svc._still_child(f"tail -f {home}/runtime/desktop/agent.log", astrbot, home, True))
    direct = ["/usr/bin/python3", "-m", "persona_agent", "--home", home, "run"]
    check("not another command given the same home",
          not svc._still_child(f"personagent --home {home} doctor", direct, home, True))
    check("not a program of that name somewhere else",
          not svc._still_child(f"/usr/local/bin/uv {UV_ARGS} {home}", uv, home, True))
    init = [home + "/platforms/tools/bin/astrbot", "init", "--yes"]
    check("a command that is no module is matched whole",
          svc._still_child(" ".join(init), init, home, True)
          and not svc._still_child(f"{home}/platforms/tools/bin/astrbot --yes", init, home, True))
    agent = ["/usr/bin/python3", "-m", "persona_agent", "--home", home, "run", "--port", "8080"]
    check("the home may be in an argument, not the program's path",
          svc._still_child(f"/usr/bin/python3 -c import os 4242 {' '.join(agent[1:])}", agent, home, True))


def test_a_child_is_told_by_its_command_line_as_windows_lists_it():
    home = r"C:\Users\Kim Lee\agent"
    scripts = home + r"\platforms\tools\installer\Scripts"
    uv = [scripts + r"\python.exe", *UV_STEP]
    # Windows keeps one string, quoted where an argument has a space.
    started = subprocess.list2cmdline(uv)
    check("the path with a space is quoted", started.startswith('"' + uv[0] + '" -m uv '), started)
    check("the child as it was started; there is no group to lead",
          svc._still_child(started, uv, home, False))
    # There the module starts uv.exe and waits, so the recorded process stays python.
    check("not uv.exe under that number, which is a later process",
          not svc._still_child(f'"{scripts}\\uv.exe" {UV_ARGS}', uv, home, False))
    check("not another home's installer",
          not svc._still_child(started.replace("Kim Lee", "Kim"), uv, home, False))
    check("not a process that is gone", not svc._still_child("", uv, home, False))
    agent = [r"C:\Python312\python.exe", "-m", "persona_agent", "--home", home, "run"]
    check("the home may be in a quoted argument",
          svc._still_child(subprocess.list2cmdline(agent), agent, home, False))


def test_only_a_process_that_leads_its_own_group_is_taken_as_leading():
    check("no such process leads nothing", not svc._leads_group(NO_SUCH_PROCESS))
    if os.name == "nt":
        check("Windows has no groups to lead", not svc._leads_group(os.getpid()))
        return
    sleep = [sys.executable, "-c", "import time; time.sleep(60)"]
    # As `_spawn` starts a child, and as that child starts one of its own.
    child, grandchild = subprocess.Popen(sleep, start_new_session=True), subprocess.Popen(sleep)
    try:
        check("a child started in its own session leads its group", svc._leads_group(child.pid))
        check("a process started inside a group does not", not svc._leads_group(grandchild.pid))
    finally:
        for process in (child, grandchild):
            process.kill()
            process.wait()


def _records(desktop: Path):
    desktop.mkdir(parents=True)

    def record(owner, command, **children):
        (desktop / f"children-{owner}.json").write_text(
            json.dumps({"owner": owner, "command": command, "children": children}), encoding="utf-8")
    return record


def test_an_installer_that_replaced_itself_is_stopped_at_the_next_start(tmp_path, monkeypatch):
    """The app was killed while uv downloaded: on POSIX the recorded
    `python -m uv` had become the uv program, which nothing ended."""
    bin_ = tmp_path.resolve() / "platforms" / "tools" / "installer" / "bin"
    uv = [str(bin_ / "python"), *UV_STEP]
    record = _records(tmp_path / "runtime" / "desktop")
    record(GONE_APP, "personagent start", install={"pid": 41, "argv": uv})
    record(GONE_APP + 1, "personagent start", install={"pid": 51, "argv": uv})
    lines = {41: f"{bin_ / 'uv'} {UV_ARGS}",    # still the installer, leading its group
             51: f"{bin_ / 'uv'} {UV_ARGS}"}    # in someone else's group: not what was started
    monkeypatch.setattr(svc, "_command_line", lambda pid: lines.get(pid, ""))
    monkeypatch.setattr(svc, "_leads_group", lambda pid: pid == 41, raising=False)
    ended = []
    monkeypatch.setattr(svc, "_end", lambda pid, command: ended.append((pid, command)))
    check("the installer is stopped", svc.stop_leftovers(tmp_path) == ["install"], str(ended))
    check("by its number, which is its group's, as the line it has now", ended == [(41, lines[41])], str(ended))
    check("and both records are done with", not list((tmp_path / "runtime" / "desktop").iterdir()))


def test_leftovers_under_a_directory_can_be_stopped_while_the_app_runs(tmp_path, monkeypatch):
    home = tmp_path.resolve()
    tools = home / "platforms" / "tools"
    desktop = home / "runtime" / "desktop"
    uv = [str(tools / "installer" / "bin" / "python"), *UV_STEP]
    astrbot = [str(tools / "envs" / "astrbot" / "bin" / "python"), "-m", "astrbot.cli.__main__", "run"]
    agent = ["python", "-m", "persona_agent", "--home", str(home), "run"]
    record = _records(desktop)
    running_app = GONE_APP + 1
    record(GONE_APP, "personagent start", install={"pid": 11, "argv": uv}, agent={"pid": 12, "argv": agent},
           astrbot={"pid": 13, "argv": astrbot})
    record(running_app, "personagent up", astrbot={"pid": 21, "argv": astrbot})
    record(os.getpid(), "personagent start", install={"pid": 31, "argv": uv})
    lines = {11: " ".join(uv), 12: " ".join(agent), 13: " ".join(astrbot),
             running_app: "personagent up", 21: " ".join(astrbot), 31: " ".join(uv)}
    monkeypatch.setattr(svc, "_command_line", lambda pid: lines.get(pid, ""))
    monkeypatch.setattr(svc, "_leads_group", lambda pid: True)
    ended = []
    monkeypatch.setattr(svc, "_end", lambda pid, command: ended.append(pid))
    stopped = svc.stop_leftovers(home, under=tools)
    check("a dead app's children that run from the directory are stopped",
          stopped == ["install", "astrbot"] and ended == [11, 13], f"{stopped} {ended}")
    kept = json.loads((desktop / f"children-{GONE_APP}.json").read_text(encoding="utf-8"))
    check("its other children stay recorded for the next start",
          kept == {"owner": GONE_APP, "command": "personagent start",
                   "children": {"agent": {"pid": 12, "argv": agent}}}, str(kept))
    own = json.loads((desktop / f"children-{os.getpid()}.json").read_text(encoding="utf-8"))
    check("a running app's record is left alone, this one's included",
          own["children"] == {"install": {"pid": 31, "argv": uv}}
          and sorted(path.name for path in desktop.iterdir())
          == sorted(f"children-{owner}.json" for owner in (GONE_APP, running_app, os.getpid())))
    ended.clear()
    # At a start, a record under this process's number is an earlier process's.
    check("the next start stops the rest",
          sorted(svc.stop_leftovers(home)) == ["agent", "install"] and sorted(ended) == [12, 31], str(ended))
    check("and keeps only the running app's record",
          [path.name for path in desktop.iterdir()] == [f"children-{running_app}.json"])


def test_a_leftover_child_is_stopped_with_what_it_started(tmp_path):
    env = _probe_env(tmp_path)
    out = tmp_path / "out.txt"
    home = tmp_path.resolve()
    argv = [sys.executable, "-m", "probe_child", str(out), "60", "--home", str(home)]
    # As the app starts a child on POSIX: leading its own process group.
    process = subprocess.Popen(argv, cwd=tmp_path, env=env, start_new_session=os.name != "nt",
                               creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    pids = []
    try:
        said = _probe_says(out)
        pids = [int(said[0]), int(said[2])]
        desktop = home / "runtime" / "desktop"
        desktop.mkdir(parents=True)
        (desktop / "children-1.json").write_text(json.dumps({
            "owner": NO_SUCH_PROCESS, "command": "personagent start",
            "children": {"probe": {"pid": process.pid, "argv": argv}}}), encoding="utf-8")
        assert svc.stop_leftovers(home) == ["probe"]
        process.wait(timeout=15)
        assert all(_gone(pid) for pid in pids)
        assert not (desktop / "children-1.json").exists()
    finally:
        process.kill()
        for pid in pids:
            _kill(pid)


def test_stopping_a_child_ends_what_it_started(tmp_path):
    env = _probe_env(tmp_path)
    out = tmp_path / "out.txt"
    services = Services(tmp_path)
    services._spawn("probe", [sys.executable, "-m", "probe_child", str(out), "60"], cwd=tmp_path, env=env)
    pids = []
    try:
        said = _probe_says(out)
        pids = [int(said[0]), int(said[2])]
        services.stop("probe")
        check("the child and the process it started are gone", all(_gone(pid, 5) for pid in pids))
        check("nothing is kept for it", not services.processes and not services._jobs)
    finally:
        services.close()
        for pid in pids:
            _kill(pid)


def _task_env(tmp_path: Path) -> dict:
    (tmp_path / "task_child.py").write_text(TASK, encoding="utf-8")
    return _probe_env(tmp_path)


def test_a_command_runs_to_its_end_and_a_failure_carries_the_end_of_its_log(tmp_path, capfd):
    env = _task_env(tmp_path)
    services = Services(tmp_path)
    record = tmp_path / "runtime" / "desktop" / f"children-{os.getpid()}.json"
    services.run("task", [sys.executable, "-m", "task_child", "earlier", "3", "0"], cwd=tmp_path, env=env)
    check("a finished command is no longer a child", not services.processes and not record.exists())
    with pytest.raises(subprocess.CalledProcessError) as failed:
        services.run("task", [sys.executable, "-m", "task_child", "later", "50", "3"], cwd=tmp_path, env=env)
    tail = failed.value.output.splitlines()
    check("the error carries its exit code", failed.value.returncode == 3, str(failed.value.returncode))
    check("and the end of what this run logged", tail[-1] == "later 49" and len(tail) == svc.TAIL_LINES, str(tail))
    check("not an earlier run's output", "earlier" not in failed.value.output)
    log = (tmp_path / "runtime" / "desktop" / "task.log").read_text(encoding="utf-8")
    check("the whole output is in its log", "earlier 0" in log and "later 0" in log)
    shown = capfd.readouterr()
    check("none of it reaches this window", "later" not in shown.out + shown.err, shown.out + shown.err)


def test_a_running_command_stops_when_asked_and_when_the_app_closes(tmp_path):
    env = _probe_env(tmp_path)
    services = Services(tmp_path)
    pids = []

    def start(out: Path, should_stop) -> tuple[threading.Thread, list]:
        raised = []

        def body():
            try:
                services.run("task", [sys.executable, "-m", "probe_child", str(out), "600"],
                             cwd=tmp_path, env=env, should_stop=should_stop)
            except Exception as exc:
                raised.append(exc)
        thread = threading.Thread(target=body)
        thread.start()
        said = _probe_says(out)
        pids.extend([int(said[0]), int(said[2])])
        return thread, raised

    try:
        asked = threading.Event()
        thread, raised = start(tmp_path / "first.txt", asked.is_set)
        began = time.monotonic()
        asked.set()
        thread.join(timeout=10)
        took = time.monotonic() - began
        check("it stops soon after it is asked to", not thread.is_alive() and took < 3, f"{took:.1f}s")
        check("and says it was stopped", [type(exc) for exc in raised] == [svc.Stopped], repr(raised))
        check("with what it started", all(_gone(pid, 5) for pid in pids))

        thread, raised = start(tmp_path / "second.txt", lambda: False)
        services.shutdown()
        check("closing the app returns with the command gone",
              not services.processes and all(_gone(pid, 2) for pid in pids))
        thread.join(timeout=10)
        check("and the command says it was stopped", [type(exc) for exc in raised] == [svc.Stopped], repr(raised))
        with pytest.raises(svc.Stopped):
            services.run("task", [sys.executable, "-m", "probe_child", str(tmp_path / "third.txt"), "600"],
                         cwd=tmp_path, env=env)
        check("a closed app starts no command", not (tmp_path / "third.txt").exists())
    finally:
        services.close()
        for pid in pids:
            _kill(pid)


def test_a_second_up_on_a_running_home_refuses_and_leaves_env_alone(tmp_path, monkeypatch, capsys):
    from persona_agent.storage import RuntimeInstanceLock

    sw.write_env(tmp_path / ".env", {"LLM_API_KEY": "k", "SERVER_PORT": "18160", "AGENT_LANG": "en"})
    before = (tmp_path / ".env").read_bytes()
    monkeypatch.setenv("AGENT_HOME", str(tmp_path))
    monkeypatch.setenv("UPDATE_CHECK_ENABLED", "false")
    held = RuntimeInstanceLock(tmp_path)
    held.acquire()
    try:
        assert svc.main([]) == 2
    finally:
        held.release()
    assert "already running" in capsys.readouterr().err
    assert (tmp_path / ".env").read_bytes() == before
