"""An optional AstrBot installation under the agent home, using its own Python."""
from __future__ import annotations

import os
import subprocess
import venv
from dataclasses import dataclass
from pathlib import Path


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


def install_astrbot(home: Path) -> Path:
    """Install once, initialise with AstrBot's own config class, and return data/."""
    installation = AstrBotInstallation(home.resolve())
    installation.root.mkdir(parents=True, exist_ok=True)
    env = installation.environment()
    if not (installation.executable.is_file() and installation.python.is_file()):
        bootstrap = installation.tools / "installer"
        python = bootstrap / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        if not python.is_file():
            venv.EnvBuilder(with_pip=True).create(bootstrap)
        subprocess.run([str(python), "-m", "pip", "install", "uv>=0.8,<1"],
                       check=True, env=env)
        subprocess.run([str(python), "-m", "uv", "--no-config", "tool", "install",
                        "--python", "3.12", "astrbot>=4.29,<5"], check=True, env=env)
    data = installation.root / "data"
    if not (installation.root / ".astrbot").is_file():
        subprocess.run([str(installation.executable), "init", "--yes"],
                       check=True, cwd=installation.root, env=env)
    if not (data / "cmd_config.json").is_file():
        # `astrbot init` creates directories; the config is normally created
        # at first start. Use AstrBot's defaults rather than an empty JSON file.
        subprocess.run([str(installation.python), "-c",
                        "from astrbot.core.config.astrbot_config import AstrBotConfig; "
                        "AstrBotConfig(config_path='data/cmd_config.json')"],
                       check=True, cwd=installation.root, env=env)
        # Config creation can generate a password in a short-lived process.
        # Let the first real start print a fresh one through AstrBot's CLI.
        (installation.root / ".initial-dashboard-login").touch()
    if not (data / "cmd_config.json").is_file():
        raise OSError(f"AstrBot did not create {data / 'cmd_config.json'}")
    return data


def start_astrbot(home: Path) -> int:
    installation = AstrBotInstallation(home.resolve())
    if not installation.executable.is_file():
        raise FileNotFoundError("AstrBot is not installed; run personagent connect astrbot --install")
    marker = installation.root / ".initial-dashboard-login"
    argv = [str(installation.executable), "run"]
    if marker.is_file():
        argv.append("--reset-password")
    code = subprocess.call(argv, cwd=installation.root, env=installation.environment())
    if code == 0:
        marker.unlink(missing_ok=True)
    return code
