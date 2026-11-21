"""Fixtures the suites share: a scratch directory, and coroutine tests."""
from __future__ import annotations

import asyncio
import errno
import inspect
import ipaddress
import os
import socket
from pathlib import Path

import dotenv
import pytest

from persona_agent import home as _home


def _no_env_file() -> Path:
    """Modules load <home>/.env as they import; whatever home is found, a
    developer's real .env, with its keys and language, must not reach the tests."""
    return _home.find_home()


_home.load_env = _no_env_file
# tools/*.py load <checkout>/.env as they import.
dotenv.load_dotenv = lambda *args, **kwargs: False


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers", "bare_call_wait: keep the real bare-call debounce")
    config.addinivalue_line(
        "markers", "typing_pace: keep the typing pace of the direct connectors")


@pytest.fixture(autouse=True)
def _no_typing_pace(request: pytest.FixtureRequest,
                    monkeypatch: pytest.MonkeyPatch) -> None:
    """Direct connectors relay replies at once unless a test is marked typing_pace."""
    if request.node.get_closest_marker("typing_pace") is None:
        monkeypatch.setattr("persona_agent.direct.base.Bridge.paced", False)


@pytest.fixture(autouse=True)
def _no_bare_call_wait(request: pytest.FixtureRequest,
                       monkeypatch: pytest.MonkeyPatch) -> None:
    """Skip the 5 s bare-call debounce unless a test is marked bare_call_wait."""
    if request.node.get_closest_marker("bare_call_wait") is None:
        monkeypatch.setattr("persona_agent.turns.BARE_CALL_DEBOUNCE_S", 0.0)


_LOCAL_NAMES = {"localhost", socket.gethostname()}


def _is_local(host) -> bool:
    host = host.decode() if isinstance(host, bytes) else str(host or "localhost")
    try:
        return ipaddress.ip_address(host.split("%")[0]).is_loopback
    except ValueError:
        return host in _LOCAL_NAMES or host.endswith(".localhost")


@pytest.fixture(autouse=True)
def _offline(monkeypatch: pytest.MonkeyPatch) -> None:
    """The suite is offline: a lookup or connection off this host fails as
    it would without a network."""
    real_lookup, real_connect, real_connect_ex = (
        socket.getaddrinfo, socket.socket.connect, socket.socket.connect_ex)

    def lookup(host, *args, **kwargs):
        if not _is_local(host):
            raise socket.gaierror(socket.EAI_NONAME, f"offline test run: {host!r}")
        return real_lookup(host, *args, **kwargs)

    def guarded(real):
        def connect(self, address):
            if isinstance(address, tuple) and not _is_local(address[0]):
                raise OSError(errno.ENETUNREACH, f"offline test run: {address[0]}")
            return real(self, address)
        return connect

    monkeypatch.setattr(socket, "getaddrinfo", lookup)
    monkeypatch.setattr(socket.socket, "connect", guarded(real_connect))
    monkeypatch.setattr(socket.socket, "connect_ex", guarded(real_connect_ex))


@pytest.fixture(autouse=True)
def _no_mirror_probe(monkeypatch: pytest.MonkeyPatch) -> None:
    """No test probes PyPI or GitHub: both count as reachable."""
    monkeypatch.setattr("persona_agent.mirrors.reachable", lambda url, timeout=0: True)
    monkeypatch.delenv("PERSONAGENT_MIRROR", raising=False)


@pytest.fixture(autouse=True)
def _no_update_check(monkeypatch: pytest.MonkeyPatch) -> None:
    """No test asks PyPI; tests/test_updates.py turns the check back on."""
    monkeypatch.setenv("UPDATE_CHECK_ENABLED", "false")


@pytest.fixture(autouse=True)
def _same_on_every_machine(monkeypatch: pytest.MonkeyPatch) -> None:
    """English output whatever the system language, and no waiting on the
    disk: no test checks that a write was flushed."""
    monkeypatch.setenv("AGENT_LANG", "en")
    monkeypatch.setattr(os, "fsync", lambda fd: None)


@pytest.fixture
def tmp(tmp_path: Path) -> Path:
    """The per-test scratch directory the suites take as `tmp`.

    Every test that writes state redirects it here, so nothing a test does
    can reach the checkout's own runtime files."""
    return tmp_path


def pytest_pyfunc_call(pyfuncitem: pytest.Function):
    """Run an `async def` test on its own event loop.

    Each coroutine test is self-contained and builds whatever it needs inside
    the call, so a fresh loop per test is the whole requirement — and pytest
    stays the only thing this repository needs installed to run its tests."""
    if not inspect.iscoroutinefunction(pyfuncitem.obj):
        return None
    arguments = {
        name: pyfuncitem.funcargs[name]
        for name in pyfuncitem._fixtureinfo.argnames
    }
    asyncio.run(pyfuncitem.obj(**arguments))
    return True
