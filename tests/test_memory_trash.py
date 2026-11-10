"""memory_trash.jsonl: written before the store, hides what is still live,
pruned by age and count, tolerant of a bad line.

    python -m pytest tests/test_memory_trash.py
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from persona_agent import memtrash

from helpers import check, isolated_agent


def test_the_trash_row_is_written_before_the_store(tmp: Path, monkeypatch) -> None:
    a = isolated_agent(tmp)
    a._append_memory("g", {"text": "Sam likes tea", "time": 1.0})
    note_id = a.memories["g"][0]["id"]

    def crash() -> None:
        raise RuntimeError("power cut")
    monkeypatch.setattr(a, "_save_memories", crash)
    with pytest.raises(RuntimeError):
        a._forget_item("g", "note", note_id)
    rows = memtrash.MemoryTrash(tmp / "memory_trash.jsonl").list()
    check("the trash row is on disk", [r["item"]["id"] for r in rows] == [note_id])
    b = isolated_agent(tmp)
    check("memory.json still holds the note", [it["id"] for it in b.memories["g"]]
          == [note_id])
    check("the list hides a row whose item is live", b._removed_items("g") == [])
    tid = rows[0]["tid"]
    check("restoring it answers that it exists", b._restore(tid) == "exists")


def test_prune_drops_expired_and_restored_rows_and_keeps_the_cap(tmp: Path,
                                                                  monkeypatch) -> None:
    trash = memtrash.MemoryTrash(tmp / "t.jsonl")
    now = time.time()
    old_fold = trash.put("g", "note", {"text": "a"}, "ended", "fold", now=now - 31 * 86400)
    fresh_fold = trash.put("g", "note", {"text": "b"}, "ended", "fold", now=now - 29 * 86400)
    old_page = trash.put("g", "note", {"text": "c"}, "forgotten_page", "page",
                         now=now - 25 * 3600)
    fresh_page = trash.put("g", "note", {"text": "d"}, "forgotten_page", "page",
                           now=now - 3600)
    restored = trash.put("g", "note", {"text": "e"}, "ended", "fold", now=now)
    trash.mark_restored(restored, now)
    listed = [r["tid"] for r in trash.list(now=now)]
    check("listed: restorable rows, newest first", listed == [fresh_page, fresh_fold],
          repr(listed))
    check("prune drops three rows", trash.prune(now) == 3)
    tids = [json.loads(line)["tid"] for line in
            (tmp / "t.jsonl").read_text(encoding="utf-8").splitlines()]
    check("what is left", tids == [fresh_fold, fresh_page], repr(tids))
    check("old rows are gone for get", trash.get(old_fold) is None
          and trash.get(old_page) is None)
    check("a second prune changes nothing", trash.prune(now) == 0)
    monkeypatch.setattr(memtrash, "MAX_ROWS", 1)
    trash.prune(now)
    check("past the cap only the newest stays",
          [r["tid"] for r in trash.list(now=now)] == [fresh_page])


def test_a_bad_line_is_skipped_and_reported(tmp: Path) -> None:
    path = tmp / "t.jsonl"
    trash = memtrash.MemoryTrash(path)
    tid = trash.put("g", "episode", {"id": "e1", "text": "the picnic"}, "evicted", "cap")
    with path.open("a", encoding="utf-8", newline="\n") as f:
        f.write("{torn line\n")
        f.write(json.dumps({"tid": "rx", "conv": "g"}) + "\n")
    rows = trash.list()
    check("the good row reads", [r["tid"] for r in rows] == [tid])
    check("two lines skipped", trash.skipped == 2, repr(trash.skipped))
    trash.prune()
    check("prune rewrites without them", len(path.read_text(
        encoding="utf-8").splitlines()) == 1)


def test_a_marker_row_hides_the_restored_row(tmp: Path) -> None:
    trash = memtrash.MemoryTrash(tmp / "t.jsonl")
    tid = trash.put("g", "core", {"text": "old core"}, "rewritten", "reply")
    other = trash.put("h", "core", {"text": "other"}, "rewritten", "reply")
    trash.mark_restored(tid)
    check("listed without it", [r["tid"] for r in trash.list()] == [other])
    check("get says it was restored", "restored_at" in trash.get(tid))
    check("per chat", [r["tid"] for r in trash.list("h")] == [other]
          and trash.list("g") == [])
    check("drop_conv removes a chat's rows", trash.drop_conv("h") == 1
          and trash.list() == [])
