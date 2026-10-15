"""Own the local service processes started by the welcome page or `up`."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

from . import home as homes
from .astrbot_install import AstrBotInstallation
from .setup_wizard import env_get, write_env


class Services:
    def __init__(self, home: Path):
        self.home = home.resolve()
        self.processes: dict[str, subprocess.Popen] = {}
        self._lock = threading.RLock()
        self._shutdown = False

    def running(self, name: str) -> bool:
        process = self.processes.get(name)
        return process is not None and process.poll() is None

    @property
    def agent_url(self) -> str:
        port = int(env_get(self.home / ".env", "SERVER_PORT") or 8080)
        return f"http://127.0.0.1:{port}"

    def _spawn(self, name: str, argv: list[str], *, cwd: Path, env: dict) -> None:
        logs = self.home / "runtime" / "desktop"
        logs.mkdir(parents=True, exist_ok=True)
        fd = os.open(logs / f"{name}.log", os.O_CREAT | os.O_APPEND | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "ab") as log:
            self.processes[name] = subprocess.Popen(
                argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                stdout=log, stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )

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

    def start_astrbot(self) -> None:
        with self._lock:
            if self._shutdown:
                raise RuntimeError("application_closed")
            if self.running("astrbot"):
                return
            installation = AstrBotInstallation(self.home)
            if not installation.python.is_file():
                raise RuntimeError("Install the chat platform first")
            argv = [str(installation.python), "-m", "astrbot.cli.__main__", "run"]
            marker = installation.root / ".initial-dashboard-login"
            if marker.is_file():
                argv.append("--reset-password")
            cfg = json.loads((installation.root / "data/cmd_config.json").read_text(encoding="utf-8-sig"))
            port = int(cfg.get("dashboard", {}).get("port") or 6185)
            with socket.socket() as sock:
                try:
                    sock.bind(("127.0.0.1", port))
                except OSError:
                    sock.bind(("127.0.0.1", 0))
                chosen = sock.getsockname()[1]
            # This is our own managed instance; keep its dashboard local.
            from .setup_wizard import _write_json
            cfg.setdefault("dashboard", {}).update({"host": "127.0.0.1", "port": chosen})
            _write_json(installation.root / "data/cmd_config.json", cfg)
            self._spawn("astrbot", argv, cwd=installation.root, env=installation.environment())
            self._ready("astrbot", f"http://127.0.0.1:{chosen}/", timeout=60)
            marker.unlink(missing_ok=True)

    def stop(self, name: str) -> None:
        with self._lock:
            process = self.processes.pop(name, None)
            if process is not None and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)

    def close(self) -> None:
        for name in ("astrbot", "agent"):
            self.stop(name)

    def shutdown(self) -> None:
        with self._lock:
            self._shutdown = True
            self.close()


def main(argv: list[str] | None = None, prog: str = "personagent up") -> int:
    argparse.ArgumentParser(prog=prog, description="Start personagent and the managed AstrBot together").parse_args(argv)
    home = homes.find_home()
    if not env_get(home / ".env", "LLM_API_KEY"):
        print("Open personagent start to finish setup first.")
        return 2
    from .setup_wizard import connect_astrbot
    services = Services(home)
    try:
        if not env_get(home / ".env", "CONNECTOR_TOKEN"):
            import secrets
            write_env(home / ".env", {"CONNECTOR_TOKEN": secrets.token_urlsafe(32)})
        services.start_agent()
        data = AstrBotInstallation(home).root / "data"
        values = {}
        connect_astrbot(home / ".env", values, data_dir=data, qq=None,
                        groups=None, dm_users=None)
        write_env(home / ".env", values)
        services.start_astrbot()
        print("personagent + AstrBot are running. Press Ctrl+C to stop both.")
        while all(services.running(name) for name in ("agent", "astrbot")):
            time.sleep(0.5)
        return 1
    except KeyboardInterrupt:
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    finally:
        services.close()
