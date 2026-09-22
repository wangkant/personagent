"""Fixtures the suites share: a scratch directory, and coroutine tests."""
from __future__ import annotations

import asyncio
import inspect
from pathlib import Path

import pytest


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
