"""The memory stores: stable ids, eviction by worth, the daily copy, the core
note's guard and history, forget and restore, and what a chat forget leaves.

    python -m pytest tests/test_memory_store.py
"""
from __future__ import annotations

import json
import time
from datetime import date, timedelta
from pathlib import Path

from persona_agent import embeddings, memstore, ranking
from persona_agent.agent import Agent
from persona_agent.memory import _COMMAND_REPLIES

from helpers import check, isolated_agent


def make_agent(tmp: Path) -> Agent:
    a = isolated_agent(tmp, persona_name="Luna")
    a.memories.clear()
    return a


def _trash_rows(a: Agent) -> list[dict]:
    path = a.memory_trash.path
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def test_a_note_keeps_its_id_when_a_fuller_telling_merges_into_it(tmp: Path) -> None:
    a = make_agent(tmp)
    a._save_auto_memory("g", "Sam adopted a rescue dog called Biscuit")
    first = a.memories["g"][0]
    check("a new auto note gets an id and the new fields",
          first["id"].startswith("m") and len(first["id"]) == 11
          and (first["imp"], first["uses"], first["src"]) == (3, 0, "reply"), repr(first))
    a._save_auto_memory("g", "Sam adopted a rescue dog called Biscuit last spring")
    rows = a.memories["g"]
    check("merged in place, same id", len(rows) == 1 and rows[0]["id"] == first["id"]
          and rows[0]["text"].endswith("last spring"), repr(rows))
    on_disk = json.loads(a.memory_file.read_text(encoding="utf-8"))["g"][0]
    check("the id is on disk", on_disk["id"] == first["id"], repr(on_disk))


def test_eviction_keeps_the_useful_note_and_trashes_the_other(tmp: Path) -> None:
    a = make_agent(tmp)
    a.memory_max_per_conversation = 2
    now = time.time()
    a.memories["g"] = [
        {"id": "mold0000000", "text": "Sam's birthday is in March", "time": now - 40 * 86400,
         "auto": True, "imp": 5, "uses": 4, "used": now - 86400},
        {"id": "mnew0000000", "text": "Sam ate noodles", "time": now - 3600,
         "auto": True, "imp": 1, "uses": 0, "used": 0.0},
    ]
    a._append_memory("g", {"text": "Kim plays the cello", "time": now, "auto": True,
                           "imp": 3})
    texts = [it["text"] for it in a.memories["g"]]
    check("the important, used note stays though it is older",
          texts == ["Sam's birthday is in March", "Kim plays the cello"], repr(texts))
    rows = _trash_rows(a)
    check("the evicted note is in the trash, by the cap",
          [(r["item"]["text"], r["why"], r["by"]) for r in rows]
          == [("Sam ate noodles", "evicted", "cap")], repr(rows))
    check("the evicted row is returned", Agent._evict_memory(
        [{"text": "x", "auto": True}])["text"] == "x")


def test_the_age_phrase_starts_from_when_a_fact_was_first_noted() -> None:
    now = time.time()
    check("a two-week-old fact confirmed today",
          ranking.memory_age(now - 14 * 86400, now, now)
          == "first noted 14 days ago, confirmed today",
          ranking.memory_age(now - 14 * 86400, now, now))
    check("a fact written once", ranking.memory_age(now - 3 * 86400, now - 3 * 86400, now)
          == "first noted 3 days ago")
    check("a legacy row without born", ranking.memory_age(None, now, now)
          == "first noted today")
    check("gap phrases", (ranking.gap_phrase(10 * 60), ranking.gap_phrase(3 * 3600),
                          ranking.gap_phrase(2 * 86400 + 5))
          == ("10 minutes later", "3 hours later", "2 days later"))


def test_the_daily_copy_is_made_once_a_day(tmp: Path) -> None:
    a = make_agent(tmp)
    a._append_memory("g", {"text": "first fact", "time": 1.0})
    bak = a.memory_file.with_name("memory.json.bak")
    check("no copy before there was a file to copy", not bak.exists())
    a.memory_state.data["bak_day"] = {}
    a._append_memory("g", {"text": "second fact", "time": 2.0})
    first_copy = bak.read_text(encoding="utf-8")
    check("the first write of the day copies the file as it was",
          "first fact" in first_copy and "second fact" not in first_copy, first_copy)
    a._append_memory("g", {"text": "third fact", "time": 3.0})
    check("a later write the same day leaves the copy", bak.read_text(encoding="utf-8")
          == first_copy)
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    a.memory_state.data["bak_day"] = {"memory.json": yesterday}
    a._append_memory("g", {"text": "fourth fact", "time": 4.0})
    check("the next day copies again", "third fact" in bak.read_text(encoding="utf-8"))
    a._commit_core_memory("g", "the room likes jazz")
    a.memory_state.data["bak_day"].pop("core_memory.json", None)
    a._commit_core_memory("g", "the room likes jazz and blues")
    check("the core note has its own copy",
          a.core_memory_file.with_name("core_memory.json.bak").read_text(
              encoding="utf-8").count("jazz") == 1)


def test_a_cut_off_core_rewrite_is_refused_and_a_gradual_one_kept(tmp: Path) -> None:
    a = make_agent(tmp)
    long_note = ("Sam is a night owl who codes in Rust. Kim plays cello in a quartet. "
                 "Alex runs marathons and hates cilantro. The group plans a trip to "
                 "Kyoto in April and argues about ramen shops. Mia is learning Korean.")
    check("the note is long enough to guard", len(long_note) >= 120)
    a._commit_core_memory("g", long_note)
    a._commit_core_memory("g", "Weather is nice today, everyone is happy.")
    check("a short rewrite with few of its words is refused",
          a.core_memory["g"] == long_note, a.core_memory["g"])
    gradual = long_note.replace(" Mia is learning Korean.", "")
    a._commit_core_memory("g", gradual)
    check("a gradual edit is kept", a.core_memory["g"] == gradual)
    rows = [r for r in _trash_rows(a) if r["kind"] == "core"]
    check("the replaced version is in the trash",
          [(r["item"]["text"], r["why"], r["by"]) for r in rows]
          == [(long_note, "rewritten", "reply")], repr(rows))
    check("core_at is kept", a.memory_state.core_at("g") is not None)
    check("restore brings the earlier version back",
          a._restore(rows[0]["tid"]) == "ok" and a.core_memory["g"] == long_note)
    check("and the version it replaced is restorable in turn",
          any(r["item"]["text"] == gradual for r in _trash_rows(a)
              if r["kind"] == "core"))
    check("a restored row is gone", a._restore(rows[0]["tid"]) == "gone")


def test_the_page_forgets_by_id_and_by_the_old_text_key(tmp: Path) -> None:
    a = make_agent(tmp)
    a._append_memory("g", {"text": "Sam likes tea", "time": 1.0})
    a._append_memory("g", {"text": "Kim likes coffee", "time": 2.0})
    sam, kim = a.memories["g"]
    tid = a._forget_item("g", "note", sam["id"])
    check("by id", tid.startswith("r") and [it["text"] for it in a.memories["g"]]
          == ["Kim likes coffee"])
    check("a second forget finds nothing", a._forget_item("g", "note", sam["id"]) == "")
    check("by the legacy text key", a._forget_note("g", embeddings.text_key(kim["text"]))
          and a.memories["g"] == [])
    check("both are restorable", {r["item"]["text"] for r in a._removed_items("g")}
          == {"Sam likes tea", "Kim likes coffee"})
    check("a tombstone for each", len(a.memory_state.data["tombstones"]["g"]) == 2)


def test_restoring_an_update_brings_the_old_text_back_under_its_id(tmp: Path) -> None:
    a = make_agent(tmp)
    a._append_memory("g", {"text": "Sam lives in Berlin", "time": 1.0, "auto": True})
    note = a.memories["g"][0]
    tid = a._trash_put("g", "note", note, "replaced", "fold", ref=note["id"])
    note["text"] = "Sam lives in Lisbon"
    a._save_memories()
    check("restore", a._restore(tid) == "ok")
    rows = a.memories["g"]
    check("the old text is back under the same id", len(rows) == 1
          and rows[0]["id"] == note["id"] and rows[0]["text"] == "Sam lives in Berlin"
          and rows[0].get("restored") is True, repr(rows))
    check("the version it replaced went to the trash",
          any(r["item"]["text"] == "Sam lives in Lisbon" and r["why"] == "replaced"
              for r in _trash_rows(a)))
    check("an item already there is not restored twice",
          a._restore(a._trash_put("g", "note", rows[0], "ended", "fold")) == "exists")


def test_a_page_forget_is_restorable_for_a_day_only(tmp: Path, monkeypatch) -> None:
    a = make_agent(tmp)
    a._append_memory("g", {"text": "Sam likes tea", "time": 1.0})
    tid = a._forget_item("g", "note", a.memories["g"][0]["id"])
    later = time.time() + 25 * 3600
    monkeypatch.setattr("persona_agent.memory.time.time", lambda: later)
    check("after 24 hours it is gone", a._restore(tid) == "gone")
    check("an unknown id is gone", a._restore("rnope") == "gone")


def test_a_chat_forget_is_final_and_reaches_the_recent_lines(tmp: Path) -> None:
    a = make_agent(tmp)
    a.admin_ids = {"admin"}
    g = "g1"
    a._append_buffer(g, "Sam", "I moved to Berlin last month", "7")
    a._append_buffer(g, "Kim", "Berlin is cold", "9")
    a._append_buffer(g, "Sam", "anyway, tea?", "7")
    a._spill = {g: [{"name": "Sam", "text": "Berlin flat is tiny", "user_id": "7",
                     "t": 1.0, "seq": 1}]}
    a._handle_memory_command(g, "Luna remember Sam moved to Berlin", "admin", "Boss")
    out = a._handle_memory_command(g, "Luna forget Berlin", "7", "Sam") or ""
    check("the lines alone count as forgotten",
          out in _COMMAND_REPLIES["en"]["forgotten"], out)
    lines = [m["text"] for m in a.buffers[g]]
    check("the caller's own matching lines are gone, others' stay",
          lines == ["Berlin is cold", "anyway, tea?"], repr(lines))
    check("the spill lost the caller's line", a._spill[g] == [], repr(a._spill))
    check("the admin's note is not the member's to delete",
          [it["text"] for it in a.memories[g]] == ["Sam moved to Berlin"])
    a._handle_memory_command(g, "Luna forget Berlin", "admin", "Boss")
    check("the admin may delete it and every matching line",
          a.memories[g] == [] and [m["text"] for m in a.buffers[g]] == ["anyway, tea?"])
    check("nothing went to the trash", _trash_rows(a) == [], repr(_trash_rows(a)))
    stones = a.memory_state.data["tombstones"][g]
    check("a tombstone holds the forgotten words",
          any(set(memstore.token_hashes("Berlin")) <= set(s["tokens"]) for s in stones))
    check("an old line cannot bring it back", a.memory_state.tombstoned(
        g, memstore.token_hashes("Sam lives in Berlin now"), before=time.time() - 60))
    check("a person saying it again later can", not a.memory_state.tombstoned(
        g, memstore.token_hashes("Sam lives in Berlin now"), before=time.time() + 60))


def test_forget_this_chat_removes_its_trash_rows_only(tmp: Path) -> None:
    a = make_agent(tmp)
    for conv in ("g1", "g2"):
        a._append_memory(conv, {"text": f"{conv} fact one", "time": 1.0})
        a._append_memory(conv, {"text": f"{conv} fact two", "time": 2.0})
        a._forget_item(conv, "note", a.memories[conv][0]["id"])
    a.episode_store.add("g1", {"text": "the g1 picnic", "t0": 1.0, "t1": 2.0})
    a.episode_store.set_thread("g1", "planning the picnic", 1.0, 2.0)
    a._save_episodes()
    a.core_memory["g1"] = "g1 core"
    a._save_core_memory()
    a.buffers["g1"].append({"name": "x", "text": "hi", "user_id": "1"})
    check("forget this chat", a._forget_chat("g1"))
    check("its facts, events, summary, core and lines are gone",
          "g1" not in a.memories and a.episode_store.episodes("g1") == []
          and a.episode_store.thread("g1") is None and "g1" not in a.core_memory
          and "g1" not in a.buffers)
    convs = {r["conv"] for r in _trash_rows(a)}
    check("only the other chat's trash rows remain", convs == {"g2"}, repr(convs))
    check("the other chat is untouched", [it["text"] for it in a.memories["g2"]]
          == ["g2 fact two"])
    stored = json.loads(a.episode_store.path.read_text(encoding="utf-8"))
    check("episodes.json no longer holds it", "g1" not in stored, repr(stored))


def test_the_episode_store_evicts_by_worth_and_finds_a_month_to_roll_up(tmp: Path) -> None:
    from datetime import datetime as dt

    from persona_agent.episodes import EpisodeStore

    store = EpisodeStore(tmp / "episodes.json")
    now = time.time()
    keep = store.add("g", {"text": "the wedding", "t0": now - 90 * 86400,
                           "t1": now - 90 * 86400, "imp": 5, "uses": 3})
    store.add("g", {"text": "lunch talk", "t0": now - 80 * 86400,
                    "t1": now - 80 * 86400, "imp": 1})
    check("ids and defaults", keep["id"].startswith("e") and keep["followed"] is False)
    dropped = store.evict_one("g", now)
    check("the least worth keeping goes", dropped["text"] == "lunch talk")
    month = dt.fromtimestamp(now - 200 * 86400)
    start = dt(month.year, month.month, 1).timestamp()
    for i in range(3):
        store.add("g", {"text": f"old {i}", "t0": start + i * 86400,
                        "t1": start + i * 86400 + 60})
    rows = store.oldest_month("g", now)
    check("the oldest month with three old events", [r["text"] for r in rows]
          == ["old 0", "old 1", "old 2"], repr(rows))
    store.set_thread("g", "planning a trip", 1.0, 2.0)
    store.save()
    again = EpisodeStore(tmp / "episodes.json")
    check("saved and loaded", [r["text"] for r in again.episodes("g")]
          == ["the wedding", "old 0", "old 1", "old 2"]
          and again.thread("g")["text"] == "planning a trip")


def test_the_recent_store_caps_trims_and_survives_damage(tmp: Path) -> None:
    from persona_agent import recent

    store = recent.RecentStore(tmp / "recent.json")
    now = time.time()
    lost = store.put("g", {"seq": 300, "folded_upto": 10, "last_at": now,
                           "lines": [{"text": str(i), "seq": i} for i in range(80)],
                           "spill": [{"text": "s", "seq": i} for i in range(250)],
                           "unanswered": ["a", "b", "c", "d"]})
    entry = store.snapshot("g")
    check("lines capped to the newest 60", len(entry["lines"]) == 60
          and entry["lines"][0]["text"] == "20")
    check("spill capped, the overflow counted", len(entry["spill"]) == 240 and lost == 10)
    check("three unanswered lines", entry["unanswered"] == ["b", "c", "d"])
    store.put("old", {"last_at": now - 73 * 3600})
    for i in range(3):
        store.put(f"c{i}", {"last_at": now - i})
    small = recent.RecentStore(tmp / "r2.json", max_convs=2)
    small.convs = dict(store.convs)
    check("quiet chats and the overflow are trimmed",
          sorted(small.trim(now)) == ["c1", "c2", "old"] and set(small.convs) == {"c0", "g"})
    store.write()
    check("written and read back", recent.RecentStore(tmp / "recent.json").load()["g"]["seq"]
          == 300)
    (tmp / "recent.json").write_text("{broken", encoding="utf-8")
    check("a damaged file starts empty", recent.RecentStore(tmp / "recent.json").load() == {})
    check("and is moved aside", (tmp / "recent.json.corrupt").exists())
    store.delete()
    check("delete removes the file", not (tmp / "recent.json").exists())


def test_the_call_budget(tmp: Path) -> None:
    from persona_agent import memstate

    state = memstate.MemoryState(tmp / "memory_state.json")
    budget = memstate.CallBudget(state)
    now = 1_800_000_000.0
    check("off at zero", budget.allowed("g", now, 0) == "off")
    check("a first call may go", budget.allowed("g", now, 40) is None)
    budget.record_call("g", now)
    check("twenty minutes apart", budget.allowed("g", now + 600, 40) == "gap"
          and budget.allowed("g", now + 1200, 40) is None)
    check("eviction skips the gap", budget.allowed("g", now + 60, 40, reason="evict") is None)
    check("the total for all chats", budget.allowed("h", now + 60, 1) == "day_cap")
    for i in range(15):
        budget.record_call("g", now + (i + 1) * 1200)
    check("sixteen a day per chat", budget.allowed("g", now + 17 * 1200, 40) == "chat_cap")
    nexts = [budget.failed("k", now, TimeoutError()) - now for _ in range(7)]
    check("backoff doubles from ten minutes to six hours",
          nexts == [600.0, 1200.0, 2400.0, 4800.0, 9600.0, 19200.0, 21600.0], repr(nexts))
    check("three failures in a row pause every chat",
          budget.allowed("other", now + 60, 40) == "paused")
    check("the error class is kept", state.data["per_conv"]["k"]["last_error"]
          == "TimeoutError")
    budget.succeeded("k")
    check("success resets", state.data["fails_in_row"] == 0
          and state.data["per_conv"]["k"]["fails"] == 0)
    status = budget.status(now + 60, 40, "k")
    check("the status the page shows", status["calls_today"] == 16 and status["cap"] == 40
          and status["paused_until"] > 0, repr(status))
    state.save(force=True)
    check("saved and loaded", memstate.MemoryState(tmp / "memory_state.json").data
          ["per_conv"]["g"]["count"] == 16)
