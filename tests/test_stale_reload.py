"""Files re-read only when they change: the retrieval pools and promoted
views (views.py), the owner profile (prompt.py), and the evidence log's
append (evidence.py)."""
from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from persona_agent import evidence
from persona_agent import prompt as prompt_mod
from persona_agent import views as views_mod

from helpers import check, isolated_agent


def _write_rows(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


EXAMPLE = {"reply": "sup", "scenario": "greeting", "mode": "called",
           "context": ["alex: hey"], "score": 5}
PAIR = {"reply": "just restart it", "better": "check the logs first",
        "rating": "better", "scenario": "ops", "mode": "called", "context": []}


# ---------------------------------------------------------------------------
# views.py: the pools and the promoted views
# ---------------------------------------------------------------------------

def test_the_pools_and_views_reload_through_one_helper(tmp: Path) -> None:
    a = isolated_agent(tmp, seeds=True)
    seen = []
    real = a._reload_if_stale

    def spy(paths, stamp_attr, load):
        seen.append(stamp_attr)
        return real(paths, stamp_attr, load)

    a._reload_if_stale = spy
    a._reload_examples_if_stale()
    a._reload_pairs_if_stale()
    a._reload_views_if_stale()
    check("one helper: every pool and view goes through it, under its own stamp",
          seen == ["_examples_mtime", "_pairs_mtime",
                   "_view_examples_stamp", "_view_pairs_stamp"], repr(seen))


def test_a_pool_is_reread_only_when_a_file_changes(tmp: Path) -> None:
    a = isolated_agent(tmp, seeds=True)
    reads = []
    real_read = a._read_pool

    def counting(seed, runtime):
        reads.append(runtime.name)
        return real_read(seed, runtime)

    a._read_pool = counting
    a._reload_examples_if_stale()
    a._reload_examples_if_stale()
    check("examples: absent files are read once and give an empty pool",
          len(reads) == 1 and a._examples_cache == [], repr(reads))

    _write_rows(a.examples_file, [EXAMPLE, dict(EXAMPLE, reply="  ")])
    a._reload_examples_if_stale()
    a._reload_examples_if_stale()
    check("examples: a changed file is read once more, its rows tagged",
          len(reads) == 2 and len(a._examples_cache) == 2
          and all("_rt" in r for r in a._examples_cache), repr(reads))
    check("examples: the replies already pooled are remembered",
          a._auto_examples_seen == {"sup"}, repr(a._auto_examples_seen))

    a._examples_mtime = 0.0
    a._reload_examples_if_stale()
    check("examples: a cleared stamp forces a reload", len(reads) == 3)

    reads.clear()
    _write_rows(a.feedback_file, [PAIR, dict(PAIR, rating="worse"),
                                  dict(PAIR, better="")])
    a._reload_pairs_if_stale()
    a._reload_pairs_if_stale()
    check("pairs: read once per change, keeping only the better-rated pairs",
          reads == [a.feedback_file.name]
          and [r["better"] for r in a._pairs_cache] == ["check the logs first"]
          and "_rt" in a._pairs_cache[0], repr((reads, a._pairs_cache)))


def _locked(seed, runtime):
    raise PermissionError("locked")


def test_an_examples_read_error_keeps_the_pool_and_tries_again(
        tmp: Path, caplog) -> None:
    caplog.set_level(logging.WARNING, logger="agent")
    a = isolated_agent(tmp, seeds=True)
    _write_rows(a.examples_file, [EXAMPLE, dict(EXAMPLE, reply="  ")])
    a._reload_examples_if_stale()
    stamp, real_read = a._examples_mtime, a._read_pool
    a._read_pool = _locked
    _write_rows(a.examples_file, [EXAMPLE, dict(EXAMPLE, reply="hello")])
    caplog.clear()
    a._reload_examples_if_stale()
    said = [r.getMessage() for r in caplog.records]
    check("examples: a read error keeps the pool and its stamp, with a warning",
          {r["reply"] for r in a._examples_cache} == {"sup", "  "}
          and a._auto_examples_seen == {"sup"}
          and a._examples_mtime == stamp
          and len(said) == 1 and "examples.jsonl reload failed" in said[0],
          repr(said))
    a._read_pool = real_read
    a._reload_examples_if_stale()
    check("examples: and the next turn tries again",
          {r["reply"] for r in a._examples_cache} == {"sup", "hello"}
          and a._auto_examples_seen == {"sup", "hello"}
          and a._examples_mtime != stamp)


def test_a_pairs_read_error_keeps_the_pairs_and_tries_again(
        tmp: Path, caplog) -> None:
    caplog.set_level(logging.WARNING, logger="agent")
    a = isolated_agent(tmp, seeds=True)
    _write_rows(a.feedback_file, [PAIR])
    a._reload_pairs_if_stale()
    stamp, real_read = a._pairs_mtime, a._read_pool
    a._read_pool = _locked
    _write_rows(a.feedback_file, [])
    caplog.clear()
    a._reload_pairs_if_stale()
    said = [r.getMessage() for r in caplog.records]
    check("pairs: a read error keeps the pairs and their stamp, with a warning",
          [r["better"] for r in a._pairs_cache] == ["check the logs first"]
          and a._pairs_mtime == stamp
          and len(said) == 1 and "feedback.jsonl reload failed" in said[0],
          repr(said))
    a._read_pool = real_read
    a._reload_pairs_if_stale()
    check("pairs: and the next turn tries again",
          a._pairs_cache == [] and a._pairs_mtime != stamp)


@pytest.mark.parametrize("attr, file_attr, row", [
    ("_view_examples", "promoted_examples_file", EXAMPLE),
    ("_view_pairs", "promoted_feedback_file", PAIR),
])
def test_a_promoted_view_read_error_is_raised_not_passed_over(
        tmp: Path, monkeypatch, caplog, attr: str, file_attr: str, row: dict) -> None:
    """Unlike a pool: the view is where a rollback takes a row out of the
    prompt, so its old rows are never kept behind a warning."""
    caplog.set_level(logging.WARNING, logger="agent")
    a = isolated_agent(tmp, seeds=True)
    path = getattr(a, file_attr)
    _write_rows(path, [row])
    a._reload_views_if_stale()
    stamp = getattr(a, attr + "_stamp")
    check("views: the row is loaded", len(getattr(a, attr + "_cache")) == 1)
    real_read = views_mod.read_jsonl

    def locked(paths):
        if path in paths:
            raise PermissionError("locked")
        return real_read(paths)

    monkeypatch.setattr(views_mod, "read_jsonl", locked)
    _write_rows(path, [row, dict(row, reply="another one")])
    caplog.clear()
    with pytest.raises(PermissionError, match="locked"):
        a._reload_views_if_stale()
    check("views: a read error reaches the caller, with no warning in its place",
          not caplog.records, repr([r.getMessage() for r in caplog.records]))
    check("views: and leaves the stamp, so the file is not taken as read",
          getattr(a, attr + "_stamp") == stamp)
    with pytest.raises(PermissionError, match="locked"):
        a._reload_views_if_stale()
    monkeypatch.setattr(views_mod, "read_jsonl", real_read)
    a._reload_views_if_stale()
    check("views: the next turn that can read it loads the file",
          len(getattr(a, attr + "_cache")) == 2
          and getattr(a, attr + "_stamp") != stamp)


def test_a_promoted_view_that_cannot_be_read_gives_no_rows(
        tmp: Path, monkeypatch) -> None:
    a = isolated_agent(tmp, seeds=True)
    path = a.promoted_examples_file
    _write_rows(path, [EXAMPLE])
    a._reload_views_if_stale()
    check("views: the row is loaded", len(a._view_examples_cache) == 1)
    real_read = Path.read_bytes

    def locked(self):
        if self == path:
            raise PermissionError("locked")
        return real_read(self)

    monkeypatch.setattr(Path, "read_bytes", locked)
    _write_rows(path, [EXAMPLE, dict(EXAMPLE, reply="yo")])
    a._reload_views_if_stale()
    check("views: a file the disk will not hand over leaves nothing in the prompt",
          a._view_examples_cache == [])


def test_a_promoted_view_is_reread_only_when_its_file_changes(
        tmp: Path, monkeypatch) -> None:
    a = isolated_agent(tmp, seeds=True)
    reads = []
    real_read = views_mod.read_jsonl

    def counting(paths):
        reads.extend(p.name for p in paths)
        return real_read(paths)

    monkeypatch.setattr(views_mod, "read_jsonl", counting)
    examples, pairs = a.promoted_examples_file, a.promoted_feedback_file
    _write_rows(examples, [EXAMPLE])
    _write_rows(pairs, [PAIR, dict(PAIR, rating="worse")])
    a._view_examples_stamp = a._view_pairs_stamp = ()
    a._reload_views_if_stale()
    a._reload_views_if_stale()
    check("views: each file is read once",
          reads == [examples.name, pairs.name], repr(reads))
    check("views: rows are tagged, and only better-rated pairs are kept",
          [r["reply"] for r in a._view_examples_cache] == ["sup"]
          and [r["better"] for r in a._view_pairs_cache] == ["check the logs first"]
          and "_rt" in a._view_examples_cache[0] and "_rt" in a._view_pairs_cache[0])

    _write_rows(examples, [EXAMPLE, dict(EXAMPLE, reply="yo")])
    a._reload_views_if_stale()
    check("views: only the file that changed is read again",
          reads == [examples.name, pairs.name, examples.name]
          and len(a._view_examples_cache) == 2, repr(reads))
    examples.unlink()
    a._reload_views_if_stale()
    check("views: a rolled-back view empties on the next turn",
          a._view_examples_cache == [] and len(a._view_pairs_cache) == 1)


# ---------------------------------------------------------------------------
# prompt.py: the owner profile behind the sticker guide
# ---------------------------------------------------------------------------

def test_the_owner_profile_is_parsed_once_per_change(
        tmp: Path, monkeypatch) -> None:
    a = isolated_agent(tmp)
    a.admin_name = "Kay"
    profile = a.owner_profile_file
    parses = []
    real_loads = json.loads

    def counting(text, *args, **kwargs):
        parses.append(1)
        return real_loads(text, *args, **kwargs)

    monkeypatch.setattr(prompt_mod.json, "loads", counting)

    block = a._admin_sticker_pattern_block()
    check("profile: without the file, the moderate default",
          "haven't analyzed Kay's chat style yet" in block and not parses, block)

    profile.write_text(json.dumps(
        {"total_msgs": 100, "msgs_with_image": 25, "sticker_only_msgs": 5}),
        encoding="utf-8")
    blocks = {a._admin_sticker_pattern_block() for _ in range(3)}
    block = blocks.pop()
    check("profile: the measured rate, parsed once for three prompts",
          not blocks and len(parses) == 1
          and "1 sticker every 4 messages (25%)" in block
          and "20% are sticker-only" in block and "Kay's actual style" in block,
          repr((len(parses), block)))

    profile.write_text(json.dumps(
        {"total_msgs": 1000, "msgs_with_image": 100, "sticker_only_msgs": 50}),
        encoding="utf-8")
    block = a._admin_sticker_pattern_block()
    check("profile: a rewritten file is parsed again",
          len(parses) == 2 and "1 sticker every 10 messages (10%)" in block, block)

    profile.write_text(json.dumps({"total_msgs": 5}), encoding="utf-8")
    check("profile: too few messages to measure says nothing",
          a._admin_sticker_pattern_block() == "" and len(parses) == 3)

    other = tmp / "elsewhere" / "owner_profile.json"
    other.parent.mkdir()
    other.write_text(json.dumps(
        {"total_msgs": 40, "msgs_with_image": 20, "sticker_only_msgs": 0}),
        encoding="utf-8")
    a.owner_profile_file = other
    check("profile: a repointed path is not answered from the old file",
          "1 sticker every 2 messages (50%)" in a._admin_sticker_pattern_block())
    a.owner_profile_file = profile

    profile.unlink()
    check("profile: a removed file is the default again",
          "haven't analyzed" in a._admin_sticker_pattern_block())


def test_a_damaged_owner_profile_gives_the_default_and_one_warning(
        tmp: Path, caplog) -> None:
    """A hand-edited or cut-off profile must not fail every reply: the prompt
    falls back to the moderate default, and the log says so once per file
    version, not on every build."""
    a = isolated_agent(tmp)
    a.admin_name = "Kay"
    profile = a.owner_profile_file
    good = json.dumps({"total_msgs": 100, "msgs_with_image": 25,
                       "sticker_only_msgs": 5})
    profile.write_text(good, encoding="utf-8")
    check("damaged profile: starts from a good one",
          "every 4 messages" in a._admin_sticker_pattern_block())

    for label, text in (("cut off", '{"total_msgs": 1'),
                        ("empty", ""),
                        ("a list", "[1, 2, 3]"),
                        ("a word for a count", '{"total_msgs": "many"}')):
        profile.write_text(text, encoding="utf-8")
        caplog.clear()
        with caplog.at_level(logging.WARNING, logger="agent"):
            blocks = [a._admin_sticker_pattern_block() for _ in range(3)]
            group = a._build_group_prompt("g1", "called", "hi")
        warnings = [r for r in caplog.records if "owner_profile" in r.getMessage()]
        check(f"damaged profile, {label}: the moderate default every time",
              all("moderate frequency" in b for b in blocks), repr(blocks))
        check(f"damaged profile, {label}: a group prompt is still built",
              isinstance(group.system, str), repr(group))
        check(f"damaged profile, {label}: exactly one warning",
              len(warnings) == 1, repr([r.getMessage() for r in warnings]))
    profile.write_text(good, encoding="utf-8")
    check("damaged profile: a repaired file is read again",
          "every 4 messages" in a._admin_sticker_pattern_block())


# ---------------------------------------------------------------------------
# evidence.py: append reads through the same loader as every other access
# ---------------------------------------------------------------------------

def _event(reply: str) -> dict:
    return evidence.make_event(
        kind=evidence.KIND_REACTION, ts="2026-01-01T00:00:00", conv_id="g1",
        reply=reply, reaction_type="positive", adjudication={"accept": True})


def test_append_reads_through_the_log_loader(tmp: Path, monkeypatch) -> None:
    path = tmp / "evidence.jsonl"
    ours, theirs = evidence.EvidenceLog(path), evidence.EvidenceLog(path)
    first, second, third = _event("one"), _event("two"), _event("three")

    loads = []
    real_load = ours._load

    def spy():
        loads.append(1)
        return real_load()

    ours._load = spy
    check("append: a new event is recorded", ours.append(first) is True)
    check("append: it reads the log through _load", loads == [1], repr(loads))
    held = ours.all()
    check("append: a log never loaded dedupes against the file",
          theirs.append(first) is False and theirs.append(second) is True)
    check("append: another writer's row is seen before deciding",
          ours.append(second) is False and ours.append(third) is True)
    check("append: the list handed out earlier is not grown in place",
          [e["reply"] for e in held] == ["one"])
    check("append: both logs agree with the file",
          [e["reply"] for e in ours.all()] == ["one", "two", "three"]
          and [e["reply"] for e in theirs.all()] == ["one", "two", "three"]
          and len(path.read_text(encoding="utf-8").splitlines()) == 3)

    reads = []
    real_read = evidence.read_validated_jsonl

    def counting(*args, **kwargs):
        reads.append(1)
        return real_read(*args, **kwargs)

    monkeypatch.setattr(evidence, "read_validated_jsonl", counting)
    ours.all()
    check("append: an unchanged log is not read again, by append or after it",
          ours.append(third) is False and ours.append(_event("four")) is True
          and len(ours.all()) == 4 and reads == [], repr(reads))

    with path.open("ab") as handle:
        handle.write(b"not json\n")
    check("append: a bad row another writer left is counted, not replayed",
          ours.append(_event("five")) is True and reads == [1]
          and ours.health_metadata()["quarantined_rows"] == 1
          and len(ours.all()) == 5)


def test_a_failed_append_leaves_the_log_usable(tmp: Path, monkeypatch) -> None:
    path = tmp / "evidence.jsonl"
    log = evidence.EvidenceLog(path)
    log.append(_event("one"))
    real_append = evidence.append_jsonl_unlocked

    def disk_full(path, row):
        raise OSError("no space left on device")

    monkeypatch.setattr(evidence, "append_jsonl_unlocked", disk_full)
    raised = False
    try:
        log.append(_event("two"))
    except OSError:
        raised = True
    check("failed append: the error reaches the caller, and nothing is claimed",
          raised and [e["reply"] for e in log.all()] == ["one"])
    monkeypatch.setattr(evidence, "append_jsonl_unlocked", real_append)
    check("failed append: the same event is recorded once on the retry",
          log.append(_event("two")) is True and log.append(_event("two")) is False
          and [e["reply"] for e in log.all()] == ["one", "two"])
