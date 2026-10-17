"""The update notice: asking PyPI, remembering the answer, and how to update."""
from __future__ import annotations

import json
import sys
import threading
import time

import httpx
import pytest

from persona_agent import __version__, home as homes, updates, welcome


@pytest.fixture(autouse=True)
def _check_on(monkeypatch):
    monkeypatch.setenv("UPDATE_CHECK_ENABLED", "true")


class _Answer:
    def __init__(self, version: str):
        self.version = version

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict:
        return {"info": {"version": self.version}}


def _remember(home, latest: str, checked: float | None = None) -> None:
    path = home / "runtime" / "desktop" / "update.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"checked": time.time() if checked is None else checked,
                                "latest": latest}), encoding="utf-8")


def test_only_a_higher_plain_release_counts():
    assert updates.newer("1.2.2", "1.2.1")
    assert updates.newer("1.10.0", "1.9.9")
    assert updates.newer("2.0.0", "1.99.0")
    assert not updates.newer("1.2.1", "1.2.1")
    assert not updates.newer("1.2.0", "1.2.1")
    assert not updates.newer("1.3.0rc1", "1.2.1")
    assert not updates.newer("", "1.2.1")
    assert not updates.newer("1.3.0", "not a version")


def test_a_check_remembers_the_answer_and_a_failure_keeps_the_last_one(tmp_path, monkeypatch):
    asked = []
    monkeypatch.setattr(httpx, "get", lambda url, **kw: asked.append((url, kw)) or _Answer("99.0.0"))
    assert updates.check(tmp_path) == "99.0.0"
    url, kw = asked[0]
    assert url == updates.PYPI_URL
    # Only the version travels: no key, no home, nothing from .env.
    assert kw["headers"] == {"User-Agent": f"personagent/{__version__}"}
    found = updates.notice(tmp_path)
    assert found["version"] == "99.0.0"
    assert found["url"].endswith("/releases/tag/v99.0.0")
    assert "99.0.0" in updates.line(found)

    def offline(url, **kw):
        raise httpx.ConnectError("offline")

    monkeypatch.setattr(httpx, "get", offline)
    assert updates.check(tmp_path) == "99.0.0"
    assert updates.notice(tmp_path)["version"] == "99.0.0"
    assert updates._read(tmp_path)["failed"] is True


def test_no_notice_when_current_or_switched_off(tmp_path, monkeypatch):
    _remember(tmp_path, __version__)
    assert updates.notice(tmp_path) is None
    assert updates.line(None) == ""
    _remember(tmp_path, "99.0.0")
    (tmp_path / ".env").write_text("UPDATE_CHECK_ENABLED=false\n", encoding="utf-8")
    monkeypatch.delenv("UPDATE_CHECK_ENABLED")
    assert not updates.enabled(tmp_path)
    assert updates.notice(tmp_path) is None
    # The shell wins over .env.
    monkeypatch.setenv("UPDATE_CHECK_ENABLED", "true")
    assert updates.notice(tmp_path)["version"] == "99.0.0"


def test_asks_in_the_background_only_once_a_day(tmp_path, monkeypatch):
    calls, done = [], threading.Event()
    monkeypatch.setattr(updates, "check", lambda home: calls.append(home) or done.set() or "")
    _remember(tmp_path, "", checked=time.time() - 60)
    updates.refresh_soon(tmp_path)
    assert not calls
    _remember(tmp_path, "", checked=time.time() - updates.CHECK_EVERY_S - 60)
    updates.refresh_soon(tmp_path)
    assert done.wait(5)
    assert calls == [tmp_path]
    # A failed attempt is retried after an hour, not a day.
    deadline = time.time() + 5
    while updates._running and time.time() < deadline:
        time.sleep(0.01)
    done.clear()
    path = tmp_path / "runtime" / "desktop" / "update.json"
    path.write_text(json.dumps({"checked": time.time() - updates.RETRY_AFTER_S - 60,
                                "latest": "", "failed": True}), encoding="utf-8")
    updates.refresh_soon(tmp_path)
    assert done.wait(5)
    monkeypatch.setenv("UPDATE_CHECK_ENABLED", "false")
    done.clear()
    updates.refresh_soon(tmp_path)
    assert not done.wait(0.2)


@pytest.mark.parametrize("prefix, command, opens", [
    ("C:/Users/a/AppData/Local/uv/cache/archive-v0/abc", "uvx personagent@latest", True),
    ("C:/Users/a/AppData/Roaming/uv/tools/personagent", "uv tool upgrade personagent", False),
    ("/home/a/.local/pipx/venvs/personagent", "pipx upgrade personagent", False),
])
def test_the_command_follows_how_personagent_was_installed(monkeypatch, prefix, command, opens):
    monkeypatch.setattr(homes, "is_checkout", lambda path=None: False)
    monkeypatch.setattr(sys, "prefix", prefix)
    assert updates.how_to_update() == (command, opens)


def test_pip_and_checkout_commands(tmp_path, monkeypatch):
    monkeypatch.setattr(homes, "is_checkout", lambda path=None: False)
    monkeypatch.setattr(sys, "prefix", "/home/a/venv")
    command, opens = updates.how_to_update()
    assert command.endswith("-m pip install -U personagent") and not opens
    monkeypatch.setattr(homes, "is_checkout", lambda path=None: True)
    monkeypatch.setattr(homes, "CHECKOUT", tmp_path)
    assert updates.how_to_update() == ("", False)  # an unpacked source ZIP
    (tmp_path / ".git").mkdir()
    command, _ = updates.how_to_update()
    assert command.startswith("git -C ") and command.endswith(" pull")


def test_the_local_page_carries_the_notice(tmp_path, monkeypatch):
    _remember(tmp_path, "99.0.0")
    workspace = welcome.Workspace(tmp_path)
    try:
        assert workspace.summary()["update"]["version"] == "99.0.0"
        monkeypatch.setenv("UPDATE_CHECK_ENABLED", "false")
        assert workspace.summary()["update"] is None
    finally:
        workspace.close()
