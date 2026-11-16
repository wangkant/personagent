"""Package and Python downloads where PyPI or GitHub cannot be reached, as in
mainland China: a short probe of both, and the mirrors the installers use
(install.ps1, install.sh). PERSONAGENT_MIRROR, as for the installers: auto
(the default), cn (always the mirrors) or off (never)."""
from __future__ import annotations

import os
import urllib.request
from dataclasses import dataclass
from typing import Callable

PYPI_PROBE = "https://pypi.org/simple/personagent/"
# A release asset, as the Python download is one.
GITHUB_PROBE = "https://github.com/astral-sh/python-build-standalone/releases/download/20241016/SHA256SUMS"
INDEX_MIRRORS = ("https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple",
                 "https://mirrors.aliyun.com/pypi/simple")
PYTHON_MIRROR = "https://registry.npmmirror.com/-/binary/python-build-standalone"
PROBE_S = 8


@dataclass(frozen=True)
class Route:
    """Which downloads go through a mirror."""
    index: bool = False
    python: bool = False

    @property
    def mirrored(self) -> bool:
        return self.index or self.python


def reachable(url: str, timeout: float = PROBE_S) -> bool:
    """Whether `url` answers within `timeout`, through the system's proxy settings."""
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=timeout):
            return True
    except Exception:
        return False


def mode(setting: str | None = None) -> str:
    """PERSONAGENT_MIRROR: the given value (from .env), else the environment's."""
    value = (setting if setting else os.environ.get("PERSONAGENT_MIRROR", "")).strip().lower()
    return value if value in ("cn", "off") else "auto"


def choose(probe: Callable[[str], bool] = None, setting: str | None = None) -> Route:
    """The route for a first attempt: the mirrors for whatever does not answer."""
    probe = probe or reachable
    chosen = mode(setting)
    if chosen == "cn":
        return Route(True, True)
    if chosen == "off":
        return Route()
    return Route(index=not probe(PYPI_PROBE), python=not probe(GITHUB_PROBE))


def attempts(first: Route, setting: str | None = None) -> list[Route]:
    """`first`, then once more through every mirror when that one fails."""
    if mode(setting) == "auto" and first != Route(True, True):
        return [first, Route(True, True)]
    return [first]


def pip_args(route: Route) -> list[str]:
    return ["--index-url", INDEX_MIRRORS[0]] if route.index else []


def uv_args(route: Route) -> list[str]:
    # On the command line, so that later upgrades of the tool keep the index.
    # uv's own UV_DEFAULT_INDEX, set by the person, wins.
    return ["--default-index", INDEX_MIRRORS[0]] if route.index and "UV_DEFAULT_INDEX" not in os.environ else []


def uv_env(route: Route, env: dict) -> dict:
    env = dict(env)
    if route.python and "UV_PYTHON_INSTALL_MIRROR" not in os.environ:
        env["UV_PYTHON_INSTALL_MIRROR"] = PYTHON_MIRROR
    return env
