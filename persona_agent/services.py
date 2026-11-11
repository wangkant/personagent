"""Own the local service processes started by the welcome page or `up`."""
from __future__ import annotations

import argparse
import ctypes
import functools
import json
import os
from pathlib import Path
import re
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from typing import Callable, Optional

from . import langs
from . import home as homes
from .astrbot_install import AstrBotInstallation, hide_dashboard
from .setup_wizard import _read_json, env_get, write_env
from .storage import atomic_write_text

_ANSI = re.compile(r"\x1b\[[0-9;]*m")
# How much of a failed command's log its error carries.
TAIL_LINES = 20

# On POSIX a child's `python -m module ...` runs as `python -c _GUARD <app pid>
# -m module ...`: the module runs as -m would run it, and the child's process
# group is ended once the app is gone, however the app ended.
_GUARD = """\
import os, runpy, signal, subprocess, sys, threading, time
# Run from outside the group: a SIGTERM to its own group would end this
# process before the SIGKILL for whatever ignored the SIGTERM.
REAPER = ("import contextlib, os, signal, sys, time; g = int(sys.argv[1])\\n"
          "with contextlib.suppress(OSError): os.killpg(g, signal.SIGTERM); time.sleep(10); "
          "os.killpg(g, signal.SIGKILL)")
def guard(app):
    while os.getppid() == app:
        time.sleep(1)
    subprocess.Popen([sys.executable, "-c", REAPER, str(os.getpgid(0))], start_new_session=True)
threading.Thread(target=guard, args=(int(sys.argv[1]),), daemon=True).start()
del sys.argv[:3]
runpy.run_module(sys.argv[0], run_name="__main__", alter_sys=True)
"""

_CREATE_SUSPENDED = 0x4
_KILL_ON_JOB_CLOSE = 0x2000
_STILL_ACTIVE = 259


class _BasicLimits(ctypes.Structure):
    _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64),
                ("LimitFlags", ctypes.c_uint32), ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", ctypes.c_uint32),
                ("Affinity", ctypes.c_size_t), ("PriorityClass", ctypes.c_uint32),
                ("SchedulingClass", ctypes.c_uint32)]


class _ExtendedLimits(ctypes.Structure):
    _fields_ = [("BasicLimitInformation", _BasicLimits), ("IoInfo", ctypes.c_uint64 * 6),
                ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]


class _UnicodeString(ctypes.Structure):
    _fields_ = [("Length", ctypes.c_ushort), ("MaximumLength", ctypes.c_ushort),
                ("Buffer", ctypes.c_void_p)]


@functools.cache
def _win32():
    """kernel32 and ntdll, with signatures that keep 64-bit handles whole."""
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    ntdll = ctypes.WinDLL("ntdll")
    handle, dword, ulong = ctypes.c_void_p, ctypes.c_uint32, ctypes.c_ulong
    for function, argtypes, restype in (
            (kernel32.CreateJobObjectW, (ctypes.c_void_p, ctypes.c_wchar_p), handle),
            (kernel32.SetInformationJobObject, (handle, ctypes.c_int, ctypes.c_void_p, dword), ctypes.c_int),
            (kernel32.AssignProcessToJobObject, (handle, handle), ctypes.c_int),
            (kernel32.TerminateJobObject, (handle, ctypes.c_uint32), ctypes.c_int),
            (kernel32.OpenProcess, (dword, ctypes.c_int, dword), handle),
            (kernel32.GetExitCodeProcess, (handle, ctypes.POINTER(dword)), ctypes.c_int),
            (kernel32.CloseHandle, (handle,), ctypes.c_int),
            (kernel32.GetSystemDirectoryW, (ctypes.c_wchar_p, ctypes.c_uint32), ctypes.c_uint32),
            (ntdll.NtResumeProcess, (handle,), ctypes.c_long),
            (ntdll.NtQueryInformationProcess,
             (handle, ctypes.c_int, ctypes.c_void_p, ulong, ctypes.POINTER(ulong)), ctypes.c_long)):
        function.argtypes, function.restype = argtypes, restype
    return kernel32, ntdll


@functools.cache
def _job():
    """A job object whose processes are killed when its last handle closes.
    This process holds the only handle and never closes it, so the handle
    goes when the process does, however it ends, and takes the children
    with it."""
    kernel32, _ = _win32()
    job = kernel32.CreateJobObjectW(None, None)
    limits = _ExtendedLimits()
    limits.BasicLimitInformation.LimitFlags = _KILL_ON_JOB_CLOSE
    # 9: JobObjectExtendedLimitInformation
    if job and kernel32.SetInformationJobObject(job, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
        return job
    if job:
        kernel32.CloseHandle(job)
    return None


def _bind(pid: int) -> Optional[int]:
    """Put a child created suspended into the job, then let it run. It runs
    nothing before it is in the job, so what it starts, such as the
    interpreter a venv's python.exe launches, is in the job as well.
    Returns a job of the child's own inside that one, holding exactly the
    child and what it starts; None when one could not be made."""
    kernel32, ntdll = _win32()
    # PROCESS_TERMINATE | PROCESS_SET_QUOTA | PROCESS_SUSPEND_RESUME
    handle = kernel32.OpenProcess(0x0001 | 0x0100 | 0x0800, False, pid)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        job = _job()
        # Outside the job a child still runs; the record of started children
        # lets the next start stop it if this process dies first.
        if job:
            kernel32.AssignProcessToJobObject(job, handle)
        # Assigned second, so this one nests inside the first.
        own = kernel32.CreateJobObjectW(None, None)
        if own and not kernel32.AssignProcessToJobObject(own, handle):
            kernel32.CloseHandle(own)
            own = None
        # Popen keeps no handle to the main thread, so resume the whole process.
        if ntdll.NtResumeProcess(handle):
            if own:
                kernel32.CloseHandle(own)
            raise OSError(f"could not resume process {pid}")
        return own
    finally:
        kernel32.CloseHandle(handle)


def _command_line(pid: int) -> str:
    """The command line of the running process `pid`; "" when there is no
    such process or it cannot be read."""
    if os.name == "nt":
        kernel32, ntdll = _win32()
        handle = kernel32.OpenProcess(0x1000, False, pid)   # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return ""
        try:
            code, size = ctypes.c_uint32(), ctypes.c_ulong()
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)) or code.value != _STILL_ACTIVE:
                return ""
            # 60: ProcessCommandLineInformation, a UNICODE_STRING followed by its text.
            ntdll.NtQueryInformationProcess(handle, 60, None, 0, ctypes.byref(size))
            buffer = ctypes.create_string_buffer(max(size.value, ctypes.sizeof(_UnicodeString)))
            if ntdll.NtQueryInformationProcess(handle, 60, buffer, len(buffer), ctypes.byref(size)):
                return ""
            text = _UnicodeString.from_buffer(buffer)
            return ctypes.wstring_at(text.Buffer, text.Length // 2) if text.Buffer else ""
        finally:
            kernel32.CloseHandle(handle)
    try:
        if sys.platform.startswith("linux"):
            # Empty for a zombie, which counts as gone.
            raw = Path(f"/proc/{pid}/cmdline").read_bytes()
            return raw.replace(b"\0", b" ").decode("utf-8", "replace").strip()
        done = subprocess.run(["ps", "-ww", "-o", "command=", "-p", str(pid)],
                              capture_output=True, text=True, check=False)
        return done.stdout.strip() if done.returncode == 0 else ""
    except OSError:
        return ""


def _end(pid: int, command: str) -> None:
    """Stop a leftover child and what it started, and wait until it is gone."""
    if os.name == "nt":
        system = ctypes.create_unicode_buffer(260)
        _win32()[0].GetSystemDirectoryW(system, len(system))
        taskkill = [str(Path(system.value) / "taskkill.exe"), "/F", "/T", "/PID", str(pid)]
    for force in (False, True):
        if os.name == "nt":
            subprocess.run(taskkill, stdin=subprocess.DEVNULL, capture_output=True, check=False,
                           creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            try:
                # Each child leads its own process group.
                os.killpg(pid, signal.SIGKILL if force else signal.SIGTERM)
            except OSError:
                return
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if _command_line(pid) != command:
                return
            time.sleep(0.1)


def _signal_child(process, force: bool = False, job: Optional[int] = None) -> None:
    """Terminate (or kill) a child and what it started: on POSIX its group,
    which it leads; on Windows its own job, when it has one."""
    if os.name != "nt":
        try:
            os.killpg(process.pid, signal.SIGKILL if force else signal.SIGTERM)
            return
        except (OSError, AttributeError, TypeError):
            pass    # gone already, or not a real process
    elif job and _win32()[0].TerminateJobObject(job, 1):
        return
    process.kill() if force else process.terminate()


class Stopped(RuntimeError):
    """A command was ended before it finished: it was asked to stop, or the
    app closed."""


def _leads_group(pid: int) -> bool:
    """Whether `pid` leads its own process group, as every child is started on
    POSIX. A program the child replaced itself with still does; a later
    process that was given its number seldom does."""
    if os.name == "nt":
        return False
    try:
        return os.getpgid(pid) == pid
    except OSError:
        return False


def _still_child(line: str, argv: list, home: str, leads: bool) -> bool:
    """Whether the process now holding a recorded child's number is still that
    child, started as `argv` for `home`: `line` is its command line, and
    `leads` whether it leads its own process group."""
    if not line or home not in line:
        return False
    if all(str(arg) in line for arg in argv[1:]):
        return True
    # On POSIX a module can replace itself with a program of its own, as uv
    # does: the same process and group, no longer `python -m module`. Only
    # the program of that name beside the interpreter: a group leader that
    # merely names the home and an argument is someone else's.
    if not leads or len(argv) < 3 or argv[1] != "-m":
        return False
    interpreter = str(argv[0])
    program = interpreter[:len(interpreter) - len(os.path.basename(interpreter))] + str(argv[2])
    return (line.startswith(program + " ")
            and all(str(arg) in line for arg in argv[3:]))


def stop_leftovers(home: Path, under: Optional[Path] = None) -> list[str]:
    """Stop what an earlier run of the app for `home` left running, and return
    their names. A child is stopped only once its app is gone and while it is
    still the process that was recorded. Call before starting any child; with
    `under`, at any time, for only the children whose program is in that
    directory."""
    home = home.resolve()
    stopped = []
    for path in sorted((home / "runtime" / "desktop").glob("children-*.json")):
        record = _read_json(path)
        owner, command = record["owner"], record["command"]
        if owner == os.getpid() and under is not None:
            continue    # this app's own children, which it may be running
        # Before any child is started, a record under this number is an earlier process's.
        running = _command_line(owner) if owner != os.getpid() else ""
        if running and (running == command or not command):
            continue    # that app is still running and stops them itself
        kept = {}
        for name, child in record["children"].items():
            pid, argv = child["pid"], child["argv"]
            if under is not None and not Path(argv[0]).is_relative_to(under):
                kept[name] = child
                continue
            line = _command_line(pid)
            if _still_child(line, argv, str(home), _leads_group(pid)):
                _end(pid, line)
                stopped.append(name)
        if kept:
            atomic_write_text(path, json.dumps({**record, "children": kept}), fsync=False)
        else:
            path.unlink(missing_ok=True)
    return stopped


class Services:
    def __init__(self, home: Path):
        self.home = home.resolve()
        self.processes: dict[str, subprocess.Popen] = {}
        # What `stop_leftovers` needs to recognise each running child.
        self._launched: dict[str, dict] = {}
        # Windows: each running child's own job, which ends what it started.
        self._jobs: dict[str, int] = {}
        self._lock = threading.RLock()
        self._shutdown = False
        self.astrbot_log_offset = 0

    def running(self, name: str) -> bool:
        process = self.processes.get(name)
        return process is not None and process.poll() is None

    @property
    def agent_url(self) -> str:
        port = int(env_get(self.home / ".env", "SERVER_PORT") or 8080)
        return f"http://127.0.0.1:{port}"

    def _spawn(self, name: str, argv: list[str], *, cwd: Optional[Path], env: dict) -> None:
        """Start `argv` with its output in its log, so that it ends when this
        process does, and record it for `stop_leftovers`. On POSIX only a
        `python -m module ...` command ends with a killed app, and not once
        the module has replaced itself with another program, as uv does; the
        rest end when they are stopped, or at the next start."""
        logs = self.home / "runtime" / "desktop"
        logs.mkdir(parents=True, exist_ok=True)
        fd = os.open(logs / f"{name}.log", os.O_CREAT | os.O_APPEND | os.O_WRONLY, 0o600)
        job = None
        with os.fdopen(fd, "ab") as log:
            options = dict(cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
            if os.name == "nt":
                process = subprocess.Popen(
                    argv, creationflags=subprocess.CREATE_NO_WINDOW | _CREATE_SUSPENDED, **options)
                try:
                    job = _bind(process.pid)
                except OSError:
                    process.kill()
                    process.wait()
                    raise
            else:
                guarded = argv[1:2] == ["-m"]
                process = subprocess.Popen(
                    [argv[0], "-c", _GUARD, str(os.getpid()), *argv[1:]] if guarded else argv,
                    start_new_session=True, **options)
        self._forget_job(name)
        if job:
            self._jobs[name] = job
        self.processes[name] = process
        self._launched[name] = {"pid": process.pid, "argv": argv}
        self._record()

    def _record(self) -> None:
        path = self.home / "runtime" / "desktop" / f"children-{os.getpid()}.json"
        if self._launched:
            # The command line tells this process from a later one with its number.
            atomic_write_text(path, json.dumps({"owner": os.getpid(), "command": _command_line(os.getpid()),
                                                "children": self._launched}), fsync=False)
        else:
            path.unlink(missing_ok=True)

    def _ready(self, name: str, url: str, timeout: float = 45) -> None:
        deadline = time.monotonic() + timeout
        # Local checks must not pass through an environment's HTTP proxy.
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        while time.monotonic() < deadline:
            if not self.running(name):
                raise RuntimeError(f"{name} could not start; see runtime/desktop/{name}.log")
            try:
                with opener.open(url, timeout=1) as response:
                    if response.status == 200:
                        return
            except (OSError, urllib.error.URLError):
                pass
            time.sleep(0.2)
        self.stop(name)
        raise RuntimeError(f"{name} did not become ready; retry from the start page")

    def start_agent(self) -> None:
        with self._lock:
            if self._shutdown:
                raise RuntimeError("application_closed")
            if self.running("agent"):
                return
            # Choose a port before writing the shared connector settings.
            wanted = int(env_get(self.home / ".env", "SERVER_PORT") or 8080)
            with socket.socket() as sock:
                try:
                    sock.bind(("127.0.0.1", wanted))
                except OSError:
                    sock.bind(("127.0.0.1", 0))
                port = sock.getsockname()[1]
            write_env(self.home / ".env", {"SERVER_PORT": str(port)})
            env = os.environ.copy()
            env["AGENT_HOME"] = str(self.home)
            env["PYTHONUTF8"] = "1"
            # Config written in the page takes precedence over a stale parent.
            from dotenv import dotenv_values
            env.update({k: v for k, v in dotenv_values(self.home / ".env").items()
                        if v is not None})
            env["AGENT_HOME"] = str(self.home)
            cwd = homes.CHECKOUT if homes.is_checkout() else self.home
            self._spawn("agent", [sys.executable, "-m", "persona_agent", "--home",
                                 str(self.home), "run", "--host", "127.0.0.1", "--port", str(port)],
                        cwd=cwd, env=env)
            self._ready("agent", self.agent_url + "/health")

    def _started(self, name: str, needle: bytes, offset: int, timeout: float = 90) -> None:
        """Wait for `needle` in what the child has logged since `offset`."""
        log = self.home / "runtime" / "desktop" / f"{name}.log"
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                with log.open("rb") as stream:
                    stream.seek(offset)
                    if needle in stream.read():
                        return
            except OSError:
                pass
            if not self.running(name):
                raise RuntimeError(f"{name} could not start; see runtime/desktop/{name}.log")
            time.sleep(0.3)
        self.stop(name)
        raise RuntimeError(f"{name} did not become ready; retry from the start page")

    def start_astrbot(self) -> None:
        with self._lock:
            if self._shutdown:
                raise RuntimeError("application_closed")
            if self.running("astrbot"):
                return
            installation = AstrBotInstallation(self.home)
            if not installation.python.is_file():
                raise RuntimeError("Install the chat platform first")
            hide_dashboard(installation.root / "data")
            log = self.home / "runtime" / "desktop" / "astrbot.log"
            offset = log.stat().st_size if log.is_file() else 0
            self._spawn("astrbot", [str(installation.python), "-m", "astrbot.cli.__main__", "run"],
                        cwd=installation.root, env=installation.environment())
            # No dashboard to poll: AstrBot logs this once its adapters are loaded.
            self._started("astrbot", b"AstrBot started.", offset)
            self.astrbot_log_offset = offset

    def restart_astrbot(self) -> int:
        """Reload AstrBot's platform list, which it reads only when it starts.
        Returns where this run's output starts in its log."""
        with self._lock:
            self.stop("astrbot")
            self.start_astrbot()
            return self.astrbot_log_offset

    def logged(self, name: str, offset: int, pattern: re.Pattern, seconds: float) -> bool:
        """Whether `name` logs a line matching `pattern` (colour codes removed)
        after `offset`, within `seconds` or until it exits."""
        deadline = time.monotonic() + seconds
        while True:
            if any(pattern.search(line) for line in self._logged_since(name, offset).splitlines()):
                return True
            if time.monotonic() >= deadline or not self.running(name):
                return False
            time.sleep(0.5)

    def _logged_since(self, name: str, offset: int) -> str:
        """What `name` has logged after `offset`, colour codes removed."""
        try:
            with (self.home / "runtime" / "desktop" / f"{name}.log").open("rb") as stream:
                stream.seek(offset)
                return _ANSI.sub("", stream.read().decode("utf-8", "replace"))
        except OSError:
            return ""

    def run(self, name: str, argv: list[str], *, cwd: Optional[Path] = None, env: dict,
            should_stop: Callable[[], bool] = lambda: False) -> None:
        """Run `argv` to its end as a child like the others, so `stop` and
        `close` end it as well. Raises Stopped once `should_stop()` holds or
        the app closes, and CalledProcessError, carrying the end of what it
        logged, when it fails."""
        log = self.home / "runtime" / "desktop" / f"{name}.log"
        with self._lock:
            if self._shutdown or should_stop():
                raise Stopped(name)
            offset = log.stat().st_size if log.is_file() else 0
            self._spawn(name, argv, cwd=cwd, env=env)
            process = self.processes[name]
        try:
            while process.poll() is None and not (self._shutdown or should_stop()):
                time.sleep(0.1)
        finally:
            self.stop(name)
        if self._shutdown or should_stop():
            raise Stopped(name)
        if process.returncode:
            tail = "\n".join(self._logged_since(name, offset).splitlines()[-TAIL_LINES:])
            raise subprocess.CalledProcessError(process.returncode, argv, output=tail)

    def start_direct(self) -> None:
        """The platforms personagent connects itself, in one process; nothing
        to start when none is stored."""
        from .direct.base import load_credentials, status_path

        with self._lock:
            if self._shutdown:
                raise RuntimeError("application_closed")
            if self.running("direct") or not load_credentials(self.home):
                return
            status_path(self.home).unlink(missing_ok=True)
            env = os.environ.copy()
            env["PYTHONUTF8"] = "1"
            for key in ("PYTHONHOME", "PYTHONPATH"):
                env.pop(key, None)
            cwd = homes.CHECKOUT if homes.is_checkout() else self.home
            self._spawn("direct", [sys.executable, "-m", "persona_agent.direct", "--home", str(self.home)],
                        cwd=cwd, env=env)

    def restart_direct(self, between: Optional[Callable[[], None]] = None) -> None:
        """Pick up added or removed platforms; `between` runs while nothing
        is running, so it can clear state the old process would write back."""
        with self._lock:
            self.stop("direct")
            if between is not None:
                between()
            self.start_direct()

    def stop(self, name: str) -> None:
        with self._lock:
            process = self.processes.pop(name, None)
            job = self._jobs.get(name)
            if process is not None and process.poll() is None:
                _signal_child(process, job=job)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    _signal_child(process, force=True, job=job)
                    process.wait(timeout=5)
            self._forget_job(name)
            if self._launched.pop(name, None) is not None:
                self._record()

    def _forget_job(self, name: str) -> None:
        job = self._jobs.pop(name, None)
        if job:
            _win32()[0].CloseHandle(job)

    def close(self) -> None:
        # A command still running first, then the platforms before their agent.
        services = ("direct", "astrbot", "agent")
        for name in [*(name for name in list(self.processes) if name not in services), *services]:
            self.stop(name)

    def shutdown(self) -> None:
        with self._lock:
            self._shutdown = True
            self.close()


def _memory_problem(home: Path) -> str:
    """The sentence of a damaged memory file the agent would stop on, read with
    the settings the agent starts with; '' when there is none."""
    from dotenv import dotenv_values

    from . import memory_admin
    saved = dict(os.environ)
    os.environ.update({k: v for k, v in dotenv_values(home / ".env").items() if v is not None})
    os.environ["AGENT_HOME"] = str(home)
    try:
        error = memory_admin.memory_problem()
    except (OSError, ValueError):
        return ""  # a setting the agent's own start reports
    finally:
        os.environ.clear()
        os.environ.update(saved)
    return memory_admin.damaged_sentence(error) if error else ""


def main(argv: list[str] | None = None, prog: str = "personagent up") -> int:
    argparse.ArgumentParser(prog=prog, description=langs.term("Start personagent and its connected platforms together")).parse_args(argv)
    home = homes.find_home()
    if not env_get(home / ".env", "LLM_API_KEY"):
        from .setup_wizard import command
        print(langs.term(f"Finish the setup first: {command('start', home)}"))
        return 2
    damaged = _memory_problem(home)
    if damaged:
        print(damaged, file=sys.stderr)
        return 1
    from . import updates
    from .setup_wizard import connect_astrbot
    updates.refresh_soon(home)
    stopped = stop_leftovers(home)
    if stopped:
        print(langs.term(f"Stopped what an earlier personagent left running: {', '.join(stopped)}."))
    services = Services(home)
    try:
        if not env_get(home / ".env", "CONNECTOR_TOKEN"):
            import secrets
            write_env(home / ".env", {"CONNECTOR_TOKEN": secrets.token_urlsafe(32)})
        services.start_agent()
        started = ["agent"]
        installation = AstrBotInstallation(home)
        if installation.python.is_file():
            values = {}
            connect_astrbot(home / ".env", values, data_dir=installation.root / "data", qq=None,
                            groups=None, dm_users=None)
            write_env(home / ".env", values)
            services.start_astrbot()
            started.append("astrbot")
        services.start_direct()
        names = started + (["direct"] if services.running("direct") else [])
        print(langs.term(f"personagent is running ({', '.join(names)}). Press Ctrl+C to stop."))
        notice = updates.line(updates.notice(home), sub="up")
        if notice:
            print(langs.term(notice))
        direct_running = services.running("direct")
        # The direct process ends on its own when every platform in it was
        # refused; the agent and AstrBot keep running without it.
        while all(services.running(name) for name in started):
            if direct_running and not services.running("direct"):
                direct_running = False
                print(langs.term("The directly connected platforms stopped; see runtime/desktop/direct.log."),
                      file=sys.stderr)
            time.sleep(0.5)
        stopped = next(name for name in started if not services.running(name))
        print(langs.term(f"{stopped} stopped; see runtime/desktop/{stopped}.log."), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(langs.term(str(exc)), file=sys.stderr)
        return 1
    finally:
        services.close()
