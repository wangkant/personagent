"""An optional AstrBot installation under the agent home, using its own Python.

personagent's own page sets this AstrBot up, so it runs without its web
dashboard: there is no second login or password to manage."""
from __future__ import annotations

import functools
import json
import os
import shutil
import subprocess
import time
import venv
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional


@dataclass(frozen=True)
class AstrBotInstallation:
    home: Path

    @property
    def root(self) -> Path:
        return self.home / "platforms" / "astrbot"

    @property
    def tools(self) -> Path:
        return self.home / "platforms" / "tools"

    @property
    def executable(self) -> Path:
        return self.tools / "bin" / ("astrbot.exe" if os.name == "nt" else "astrbot")

    @property
    def python(self) -> Path:
        base = self.tools / "envs" / "astrbot"
        return base / ("Scripts/python.exe" if os.name == "nt" else "bin/python")

    def environment(self) -> dict[str, str]:
        env = os.environ.copy()
        env.update({
            "UV_TOOL_DIR": str(self.tools / "envs"),
            "UV_TOOL_BIN_DIR": str(self.tools / "bin"),
            "UV_PYTHON_INSTALL_DIR": str(self.tools / "python"),
            "ASTRBOT_ROOT": str(self.root),
        })
        # A caller's Python environment must not leak into the separate tool.
        for key in ("PYTHONHOME", "PYTHONPATH", "VIRTUAL_ENV"):
            env.pop(key, None)
        return env


def _discard(installation: AstrBotInstallation) -> None:
    """Remove a half-made environment, so the next attempt starts clean. The
    Python that uv downloaded stays: uv puts it in place whole."""
    tools = installation.tools
    for path in (tools / "installer", tools / "envs", tools / "bin"):
        # On Windows a process that just ended can hold its files a moment longer.
        for _ in range(30):
            shutil.rmtree(path, ignore_errors=True)
            if not path.exists():
                break
            time.sleep(0.1)


def install_astrbot(home: Path, *, run: Optional[Callable[..., object]] = None) -> Path:
    """Install once, initialise with AstrBot's own config class, and return data/.

    `run(argv, env=..., cwd=...)` runs one step to its end and raises when
    the step fails or is stopped; left out, each step runs in this terminal."""
    if run is None:
        run = functools.partial(subprocess.run, check=True)
    installation = AstrBotInstallation(home.resolve())
    installation.root.mkdir(parents=True, exist_ok=True)
    env = installation.environment()
    if not (installation.executable.is_file() and installation.python.is_file()):
        bootstrap = installation.tools / "installer"
        python = bootstrap / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        # An attempt that never got to clean up, such as a closed window.
        _discard(installation)
        try:
            # pip is a step of its own: the builder's own pip setup cannot be stopped.
            venv.EnvBuilder(with_pip=False).create(bootstrap)
            run([str(python), "-m", "ensurepip", "--upgrade", "--default-pip"], env=env)
            run([str(python), "-m", "pip", "install", "uv>=0.8,<1"], env=env)
            run([str(python), "-m", "uv", "--no-config", "tool", "install",
                 "--python", "3.12", "astrbot>=4.29,<5"], env=env)
        except BaseException:
            _discard(installation)
            raise
    data = installation.root / "data"
    if not (installation.root / ".astrbot").is_file():
        run([str(installation.executable), "init", "--yes"], cwd=installation.root, env=env)
    if not (data / "cmd_config.json").is_file():
        # `astrbot init` only creates directories; write AstrBot's default config.
        run([str(installation.python), "-c",
             "from astrbot.core.config.astrbot_config import AstrBotConfig; "
             "AstrBotConfig(config_path='data/cmd_config.json')"],
            cwd=installation.root, env=env)
    hide_dashboard(data)
    return data


def hide_dashboard(data: Path) -> dict:
    """Turn the managed AstrBot's dashboard off and keep it on loopback should
    it ever be turned back on. Returns the main config as written."""
    from .storage import atomic_write_text

    path = data / "cmd_config.json"
    cfg = json.loads(path.read_text(encoding="utf-8-sig"))  # AstrBot writes a BOM
    dashboard = cfg.setdefault("dashboard", {})
    if dashboard.get("enable") is not False or dashboard.get("host") != "127.0.0.1":
        dashboard.update({"enable": False, "host": "127.0.0.1"})
        atomic_write_text(path, json.dumps(cfg, ensure_ascii=False, indent=4) + "\n")
    # Installs before 1.1 printed a dashboard password on their first start.
    (data.parent / ".initial-dashboard-login").unlink(missing_ok=True)
    return cfg


def start_astrbot(home: Path) -> int:
    installation = AstrBotInstallation(home.resolve())
    if not installation.executable.is_file():
        raise FileNotFoundError("AstrBot is not installed; run personagent connect astrbot --install")
    hide_dashboard(installation.root / "data")
    return subprocess.call([str(installation.executable), "run"],
                           cwd=installation.root, env=installation.environment())
