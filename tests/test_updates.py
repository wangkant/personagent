"""The update notice: asking PyPI, remembering the answer, and how to update."""
from __future__ import annotations

import json
import sys
import threading
import time

import httpx
import pytest

from persona_agent import __version__, doctor, home as homes, updates, welcome


def _no_network(url, **kw):
    raise AssertionError(f"a test reached the network: {url}")


@pytest.fixture(autouse=True)
def _check_on(monkeypatch):
    monkeypatch.setenv("UPDATE_CHECK_ENABLED", "true")
    monkeypatch.setattr(httpx, "get", _no_network)
    updates._attempted.clear()


class _Answer:
    def __init__(self, version: str):
        self.version = version

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict:
        return {"info": {"version": self.version}}


def _remember(home, latest: str, checked: float | None = None, failed: bool = False) -> None:
    path = home / "runtime" / "desktop" / "update.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"checked": time.time() if checked is None else checked,
                                "latest": latest, "failed": failed}), encoding="utf-8")


def _wait_idle() -> None:
    deadline = time.time() + 5
    while updates._running and time.time() < deadline:
        time.sleep(0.01)


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

    def offline(url, **kw):
        raise httpx.ConnectError("offline")

    monkeypatch.setattr(httpx, "get", offline)
    assert updates.check(tmp_path) == "99.0.0"
    assert updates.notice(tmp_path)["version"] == "99.0.0"
    assert updates._read(tmp_path)["failed"] is True
    # A home that does not exist yet gets no cache written into it.
    assert updates.check(tmp_path / "missing") == ""
    assert not (tmp_path / "missing").exists()


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


def test_asks_in_the_background_only_when_the_answer_is_stale(tmp_path, monkeypatch):
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
    _wait_idle()
    updates._attempted.clear()
    done.clear()
    _remember(tmp_path, "", checked=time.time() - updates.RETRY_AFTER_S - 60, failed=True)
    updates.refresh_soon(tmp_path)
    assert done.wait(5)
    _wait_idle()
    updates._attempted.clear()
    monkeypatch.setenv("UPDATE_CHECK_ENABLED", "false")
    done.clear()
    updates.refresh_soon(tmp_path)
    assert not done.wait(0.2)


def test_an_unwritable_cache_does_not_turn_polling_into_requests(tmp_path, monkeypatch):
    asked = []
    monkeypatch.setattr(httpx, "get", lambda url, **kw: asked.append(url) or _Answer("99.0.0"))

    def full_disk(*args, **kw):
        raise OSError("no space left")

    monkeypatch.setattr(updates, "atomic_write_text", full_disk)
    for _ in range(5):
        updates.refresh_soon(tmp_path)
        _wait_idle()
    assert len(asked) == 1


@pytest.mark.parametrize("marker, command", [
    ("uv-receipt.toml", "uv tool upgrade personagent"),
    ("pipx_metadata.json", "pipx upgrade personagent"),
])
def test_tool_environments_are_told_apart_by_their_marker_files(tmp_path, monkeypatch, marker, command):
    monkeypatch.setattr(homes, "is_checkout", lambda path=None: False)
    monkeypatch.setattr(sys, "prefix", str(tmp_path))
    (tmp_path / marker).write_text("", encoding="utf-8")
    assert updates.how_to_update() == (command, False)


def test_uvx_uv_venvs_and_pip(tmp_path, monkeypatch):
    monkeypatch.setattr(homes, "is_checkout", lambda path=None: False)
    monkeypatch.setattr(sys, "prefix", "C:/Users/a/AppData/Local/uv/cache/archive-v0/abc")
    assert updates.how_to_update() == ("uvx personagent@latest", True)
    # A folder that merely starts with "archive-v" is not uv's cache.
    monkeypatch.setattr(sys, "prefix", str(tmp_path / "Archive-Videos" / ".venv"))
    command, opens = updates.how_to_update()
    assert command.endswith("-m pip install -U personagent") and not opens
    (tmp_path / "pyvenv.cfg").write_text("home = /usr/bin\nuv = 0.8.3\n", encoding="utf-8")
    monkeypatch.setattr(sys, "prefix", str(tmp_path))
    assert updates.how_to_update()[0].startswith("uv pip install -U personagent --python ")


def test_a_clone_pulls_and_reinstalls_and_a_source_zip_downloads(tmp_path, monkeypatch):
    monkeypatch.setattr(homes, "is_checkout", lambda path=None: True)
    monkeypatch.setattr(homes, "CHECKOUT", tmp_path)
    assert updates.how_to_update() == ("", False)
    (tmp_path / ".git").mkdir()
    pull, install = updates.how_to_update()[0].splitlines()
    assert pull.startswith("git -C ") and pull.endswith(" pull")
    assert install.endswith(f"-m pip install -e {tmp_path}")


def test_the_terminal_line_ends_with_the_command():
    base = {"version": "9.9.9", "url": "https://example.invalid/v9.9.9"}
    assert updates.line({**base, "command": "", "opens": False}).endswith(base["url"])
    opens = updates.line({**base, "command": "uvx personagent@latest", "opens": True}, sub="up")
    assert opens.endswith("\n  uvx personagent@latest up")
    two = updates.line({**base, "command": "git -C x pull\npython -m pip install -e x", "opens": False})
    assert two.endswith("\n  git -C x pull\n  python -m pip install -e x")


def test_doctor_asks_only_when_the_answer_is_stale(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENT_HOME", str(tmp_path))
    asked = []
    monkeypatch.setattr(updates, "check", lambda home, timeout=0: asked.append(timeout) or "99.0.0")
    _remember(tmp_path, "99.0.0")
    assert doctor.update_notice()["version"] == "99.0.0"
    assert not asked
    _remember(tmp_path, "", checked=time.time() - updates.CHECK_EVERY_S - 60)
    assert doctor.update_notice()["version"] == "99.0.0"
    assert asked and asked[0] <= 10


def test_the_local_page_carries_the_notice_once_set_up(tmp_path, monkeypatch):
    _remember(tmp_path, "99.0.0")
    workspace = welcome.Workspace(tmp_path)
    try:
        assert workspace.summary()["update"]["version"] == "99.0.0"
        monkeypatch.setenv("UPDATE_CHECK_ENABLED", "false")
        assert workspace.summary()["update"] is None
    finally:
        workspace.close()
