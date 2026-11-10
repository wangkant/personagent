"""memory.json from before ids: migrated once on the first start, losing
nothing, safe to run again; a damaged file stops the start.

    python -m pytest tests/test_memory_migration.py
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from persona_agent import embeddings, memstore, storage

from helpers import check, isolated_agent

LEGACY = {
    "g1": [
        {"text": "the room likes jazz", "time": 1000.0},
        {"text": "Sam has a dog", "time": 2000.0, "born": 1500.0, "auto": True,
         "user_id": "7", "user_name": "Sam"},
        {"text": "Kim is moving soon", "time": 3000.0, "auto": True},
        {"text": "Alex runs marathons", "time": 4000.0, "born": 4000.0, "auto": True,
         "tidied": True},
        {"text": "Bob likes chess", "time": 5000.0, "saved_by": "42",
         "saved_by_name": "alex", "user_id": "9", "user_name": "Bob"},
    ],
    "private:5": [{"text": "我喜欢猫", "time": 6000.0, "born": 6000.0, "auto": True}],
}


def _write_legacy(tmp: Path, data=LEGACY) -> bytes:
    tmp.mkdir(parents=True, exist_ok=True)
    blob = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    (tmp / "memory.json").write_bytes(blob)
    return blob


def test_legacy_memory_migrates_losslessly(tmp: Path) -> None:
    original = _write_legacy(tmp)
    a = isolated_agent(tmp)
    on_disk = json.loads((tmp / "memory.json").read_text(encoding="utf-8"))
    for conv, rows in LEGACY.items():
        check(f"{conv}: every row kept, in order", len(on_disk[conv]) == len(rows))
        for old, new in zip(rows, on_disk[conv]):
            check(f"every old field kept: {old['text']}",
                  all(new.get(k) == v for k, v in old.items()), repr(new))
            check("the text is byte-identical", new["text"] == old["text"])
            check("the id is derived from the text",
                  new["id"] == "m" + embeddings.text_key(old["text"])[:10]
                  and len(new["id"]) == 11, new["id"])
            check("importance by origin", new["imp"] == (3 if old.get("auto") else 4))
            check("the use fields", (new["uses"], new["used"], new["src"])
                  == (0, 0.0, "migration"))
            check("born from born or time", new["born"] == old.get("born", old["time"]))
    check("the agent holds what the file says", a.memories == on_disk)
    check("an untouched copy was made first",
          (tmp / "memory.json.pre-v2").read_bytes() == original)
    state = json.loads((tmp / "memory_state.json").read_text(encoding="utf-8"))
    check("the format marker", state["format"] == memstore.FORMAT == 2, repr(state))


def test_migration_is_idempotent(tmp: Path) -> None:
    _write_legacy(tmp)
    first = isolated_agent(tmp)
    stamp = storage.file_stamp(tmp / "memory.json")
    content = (tmp / "memory.json").read_bytes()
    second = isolated_agent(tmp)
    check("a second start writes nothing", storage.file_stamp(tmp / "memory.json") == stamp)
    check("the same ids", [it["id"] for it in second.memories["g1"]]
          == [it["id"] for it in first.memories["g1"]])
    (tmp / "memory_state.json").unlink()
    isolated_agent(tmp)
    check("with the marker lost, the same file again",
          (tmp / "memory.json").read_bytes() == content)


class _Crash(BaseException):
    pass


def test_a_crash_between_the_two_writes_loses_nothing(tmp: Path, monkeypatch) -> None:
    original = _write_legacy(tmp)
    real = storage.atomic_write_text

    def crash_on_state(path, text, **kw):
        if Path(path).name == "memory_state.json":
            raise _Crash()
        return real(path, text, **kw)
    monkeypatch.setattr("persona_agent.memstate.atomic_write_text", crash_on_state)
    with pytest.raises(_Crash):
        isolated_agent(tmp)
    monkeypatch.undo()
    check("memory.json was written before the marker",
          "id" in json.loads((tmp / "memory.json").read_text(encoding="utf-8"))["g1"][0])
    content = (tmp / "memory.json").read_bytes()
    a = isolated_agent(tmp)
    check("the repeat changes nothing", (tmp / "memory.json").read_bytes() == content)
    check("the copy is still the original", (tmp / "memory.json.pre-v2").read_bytes()
          == original)
    check("and the marker is now there", a.memory_state.data.get("format") == 2)


def test_unreadable_rows_go_to_trash(tmp: Path) -> None:
    _write_legacy(tmp, {"g1": [{"text": "kept one", "time": 1.0}, {"x": 1},
                               "a bare string", {"text": "kept two", "time": 2.0}]})
    a = isolated_agent(tmp)
    check("the readable rows stay, in order",
          [it["text"] for it in a.memories["g1"]] == ["kept one", "kept two"])
    rows = [json.loads(line) for line in
            (tmp / "memory_trash.jsonl").read_text(encoding="utf-8").splitlines()]
    check("two trash rows, unreadable, by the load",
          [(r["why"], r["by"], r["conv"]) for r in rows]
          == [("unreadable", "load", "g1")] * 2, repr(rows))
    check("what they held is kept",
          [r["item"] for r in rows] == [{"x": 1}, {"value": "a bare string"}])


def test_damaged_memory_stops_with_the_backup_named(tmp: Path) -> None:
    tmp.mkdir(parents=True, exist_ok=True)
    (tmp / "memory.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(memstore.MemoryFileDamaged) as no_copy:
        isolated_agent(tmp)
    check("without a copy it says only that", str(no_copy.value)
          == "memory.json is damaged and was left untouched.", str(no_copy.value))
    (tmp / "memory.json.bak").write_text("{}", encoding="utf-8")
    with pytest.raises(memstore.MemoryFileDamaged) as named:
        isolated_agent(tmp)
    message = str(named.value)
    check("it names the daily copy and what to do", "memory.json.bak" in message
          and "move it in place of memory.json" in message, message)
    check("the damaged file is untouched",
          (tmp / "memory.json").read_text(encoding="utf-8") == "{not json")
    (tmp / "memory.json").write_text("[1, 2]", encoding="utf-8")
    with pytest.raises(memstore.MemoryFileDamaged):
        isolated_agent(tmp)
    (tmp / "memory.json").write_text("{}", encoding="utf-8")
    (tmp / "episodes.json").write_text("{oops", encoding="utf-8")
    with pytest.raises(memstore.MemoryFileDamaged) as events:
        isolated_agent(tmp)
    check("a damaged events file stops the start too", "episodes.json" in str(events.value))


def test_page_still_forgets_by_text_key(tmp: Path) -> None:
    _write_legacy(tmp)
    a = isolated_agent(tmp)
    key = embeddings.text_key("Sam has a dog")
    check("the page's forget takes the old 32-hex key", a._forget_note("g1", key))
    check("the migrated note is gone", "Sam has a dog" not in
          [it["text"] for it in a.memories["g1"]])


def test_old_page_chat_notes_reach_the_new_page_chat(tmp: Path) -> None:
    old, new = "private:browser:" + "a" * 32, "private:browser:" + "b" * 32
    _write_legacy(tmp, {old: [{"text": "I am learning the violin", "time": 1.0,
                               "auto": True}]})
    a = isolated_agent(tmp)
    a.memories.setdefault(new, [])
    prompt = a._memories_for_prompt(new)
    check("a fact from the old page chat is in the new one's prompt",
          "learning the violin" in prompt, prompt)
    check("but never in a room's", "violin" not in a._memories_for_prompt("telegram:c1"))
