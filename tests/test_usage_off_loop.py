"""The model-use tally is written on a worker thread: a slow disk never
stalls the event loop that the turns run on."""
from __future__ import annotations

import threading
import time
from pathlib import Path

from helpers import isolated_agent
from persona_agent import storage, usage


class _Resp:
    def json(self):
        return {"usage": {"prompt_tokens": 7}}


async def test_a_slow_write_does_not_stall_the_loop(tmp: Path, monkeypatch) -> None:
    agent = isolated_agent(tmp)
    agent.memory_file = tmp / "memory.json"
    writers: list = []
    real = storage.atomic_write_text

    def slow(path, text, **kwargs):
        writers.append(threading.current_thread())
        time.sleep(0.5)
        real(path, text, **kwargs)

    monkeypatch.setattr(storage, "atomic_write_text", slow)
    started = time.perf_counter()
    agent._count_usage("m", _Resp())
    spent = time.perf_counter() - started
    assert spent < 0.25, spent
    book = agent.__dict__["_usage_book"]
    book.flush(time.time())
    assert writers and all(w is not threading.main_thread() for w in writers[:1]), writers
    day = usage.day_of(time.time())
    assert usage.load(tmp / usage.USAGE_FILE)[day]["m"]["prompt_tokens"] == 7


def test_a_flush_waits_for_the_write_in_flight_and_ends_newest(tmp: Path, monkeypatch) -> None:
    book = usage.UsageBook(tmp / usage.USAGE_FILE)
    real = storage.atomic_write_text

    def slow(path, text, **kwargs):
        time.sleep(0.2)
        real(path, text, **kwargs)

    monkeypatch.setattr(storage, "atomic_write_text", slow)
    book.add("m", {"prompt_tokens": 1}, 1000.0)
    book.flush_soon(1000.0)
    book.add("m", {"prompt_tokens": 1}, 1001.0)
    book.flush(1001.0)
    assert usage.load(tmp / usage.USAGE_FILE)[usage.day_of(1000.0)]["m"]["calls"] == 2
