"""Fixtures the suites share: a scratch directory, and coroutine tests."""
from __future__ import annotations

import asyncio
import inspect
import os
from pathlib import Path

import pytest

from persona_agent import home as _home

_real_load_env = _home.load_env


def _load_env_outside_the_checkout() -> Path:
    """Modules load <home>/.env as they import; a developer's own .env in the
    checkout, with its keys and language, must not reach the tests."""
    found = _home.find_home()
    return found if found == _home.CHECKOUT else _real_load_env()


_home.load_env = _load_env_outside_the_checkout


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers", "bare_call_wait: keep the real bare-call debounce")


@pytest.fixture(autouse=True)
def _no_bare_call_wait(request: pytest.FixtureRequest,
                       monkeypatch: pytest.MonkeyPatch) -> None:
    """Skip the 5 s bare-call debounce unless a test is marked bare_call_wait."""
    if request.node.get_closest_marker("bare_call_wait") is None:
        monkeypatch.setattr("persona_agent.turns.BARE_CALL_DEBOUNCE_S", 0.0)


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
