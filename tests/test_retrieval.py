"""Tests for few-shot retrieval and its append-aware dataset loading.

examples.jsonl / feedback.jsonl are read on the reply hot path and appended to
by the offline tools, so the loader parses only the appended tail when it can
prove the prefix is unchanged (see _read_jsonl_appended). That optimization is
invisible when it works and silently corrupts the few-shot pool when it
doesn't, so the reload cases below are the important half of this file: every
one of them asserts the incrementally-maintained cache equals what a cold
process would have loaded.

Retrieval has a third source: the materialized view of promoted candidates,
which is where automatic learning now lands (tests/test_ledger.py owns the
promotion rules; the case here checks it reaches the prompt without disturbing
the append-aware loaders).

Run from the repo root with no test framework required:

    python tests/test_retrieval.py
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path

# Make the repo root importable when invoked as `python tests/test_retrieval.py`.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from persona_agent import evolution  # noqa: E402
from persona_agent.agent import Agent  # noqa: E402
from persona_agent.pools import _needs_leading_newline  # noqa: E402

_failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {name}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        _failures.append(name)


def make_agent(tmp: Path) -> Agent:
    """Agent with every state file redirected into `tmp` — never touch the
    repo's real datasets from a test.

    Retrieval reads a read-only data/ seed plus a learned runtime/ file; both
    are redirected here, and the seeds are left absent unless a test writes
    one, so row counts reflect only what the test put there."""
    tmp.mkdir(parents=True, exist_ok=True)
    a = Agent(
        api_key="k", bot_qq="1", bot_name="B", lang="en",
        memory_file=str(tmp / "memory.json"),
        eval_enable=False, eval_file=str(tmp / "eval.jsonl"),
        stickers_dir=str(tmp / "stickers"), stickers_file=str(tmp / "stickers.json"),
    )
    a._seen_msg_file = tmp / "seen_msg_ids.json"
    a.core_memory_file = tmp / "core_memory.json"
    a.core_memory = {}
    a.examples_seed_file = tmp / "seed_examples.jsonl"
    a.examples_file = tmp / "examples.jsonl"
    a.feedback_seed_file = tmp / "seed_feedback.jsonl"
    a.feedback_file = tmp / "feedback.jsonl"
    return a


def ex(reply: str, *, scenario: str = "s", mode: str = "called",
       context: list[str] | None = None, ts: str = "") -> dict:
    rec = {"scenario": scenario, "mode": mode,
           "context": context if context is not None else ["[u|qq=2] hi"],
           "reply": reply}
    if ts:
        rec["ts"] = ts
    return rec


def write_jsonl(path: Path, records: list[dict], trailing_newline: bool = True) -> None:
    body = "\n".join(json.dumps(r, ensure_ascii=False) for r in records)
    path.write_text(body + ("\n" if trailing_newline and body else ""),
                    encoding="utf-8")


def append_jsonl(path: Path, records: list[dict]) -> None:
    with path.open("a", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    # Coarse mtime resolution on some filesystems would otherwise hide the
    # append from the staleness check; the size change catches it either way,
    # but bump mtime so the test exercises the same signal production does.
    os.utime(path, None)


def bank_example(a: Agent, rec: dict) -> None:
    """Append one machine-written example the way the offline tools do: cap the
    auto half first, then append.

    The agent itself no longer writes this pool — automatic learning goes
    through the evidence ledger and lands in a separate promoted view (see
    tests/test_ledger.py). `tools/auto_reviewer.py` and `tools/prompt_lab.py`
    still write here, and this is their pattern: trim_pool + append. The cap and
    the append-aware reload have to keep agreeing about the result, which is
    what the tests below check."""
    evolution.trim_pool(a.examples_file, max_auto=a.examples_max_auto,
                        is_auto=lambda r: "score" in r)
    with a.examples_file.open("a", encoding="utf-8") as f:
        if _needs_leading_newline(a.examples_file):
            f.write("\n")
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def bank_pair(a: Agent, rec: dict) -> int:
    """The feedback-side equivalent of bank_example (see auto_reviewer.py)."""
    evolution.trim_pool(a.feedback_file, max_auto=a.feedback_max_auto,
                        is_auto=lambda r: bool(r.get("src")))
    return evolution.append_jsonl(a.feedback_file, [rec])


def replies(agent: Agent) -> list[str]:
    return [r.get("reply") for r in agent._examples_cache]


def cold_replies(tmp: Path) -> list[str]:
    """What a freshly started process would load from the same file."""
    fresh = make_agent(tmp)
    fresh._reload_examples_if_stale()
    return replies(fresh)


# ---------------------------------------------------------------------------
# Reload: incremental vs. full must never disagree
# ---------------------------------------------------------------------------

def test_append_is_incremental_and_matches_cold_load() -> None:
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        a = make_agent(tmp)
        write_jsonl(a.examples_file, [ex(f"r{i}") for i in range(20)])
        a._reload_examples_if_stale()
        check("reload: initial full load", len(a._examples_cache) == 20)
        check("reload: offset lands on EOF for a newline-terminated file",
              a._examples_offset == a._examples_eof == a.examples_file.stat().st_size)

        append_jsonl(a.examples_file, [ex(f"r{i}") for i in range(20, 25)])
        a._reload_examples_if_stale()
        check("reload: append picked up", replies(a) == [f"r{i}" for i in range(25)])
        check("reload: append result == cold load", replies(a) == cold_replies(tmp))
        check("reload: append consumed the whole file",
              a._examples_offset == a.examples_file.stat().st_size)

        # Repeated appends must not duplicate or drop.
        for i in range(25, 40):
            append_jsonl(a.examples_file, [ex(f"r{i}")])
            a._reload_examples_if_stale()
        check("reload: 15 successive appends stay exact",
              replies(a) == [f"r{i}" for i in range(40)] == cold_replies(tmp))


def test_same_mtime_append_is_still_seen() -> None:
    """Filesystem mtime resolution is coarse enough that an append can land in
    the same tick as the previous read. Staleness must key on size too, or a
    freshly banked reply sits unseen until some later write moves the clock."""
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        a = make_agent(tmp)
        write_jsonl(a.examples_file, [ex("r0")])
        a._reload_examples_if_stale()
        frozen = a.examples_file.stat().st_mtime

        with a.examples_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(ex("r1")) + "\n")
        os.utime(a.examples_file, (frozen, frozen))   # pin mtime to the old value
        a._reload_examples_if_stale()
        check("reload: append with an unchanged mtime is still picked up",
              replies(a) == ["r0", "r1"])


def test_torn_append_waits_for_its_newline() -> None:
    """A line still being written must not be half-consumed and then lost."""
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        a = make_agent(tmp)
        write_jsonl(a.examples_file, [ex(f"r{i}") for i in range(5)])
        a._reload_examples_if_stale()

        with a.examples_file.open("a", encoding="utf-8") as f:
            f.write('{"scenario":"torn","mode":"called","context":[],"reply":"half')
        os.utime(a.examples_file, None)
        a._reload_examples_if_stale()
        check("reload: torn tail not consumed", len(a._examples_cache) == 5)
        check("reload: torn tail leaves offset short of EOF",
              a._examples_offset < a._examples_eof)

        with a.examples_file.open("a", encoding="utf-8") as f:
            f.write('-line"}\n')
        os.utime(a.examples_file, None)
        a._reload_examples_if_stale()
        check("reload: completed line picked up exactly once",
              replies(a) == [f"r{i}" for i in range(5)] + ["half-line"])
        check("reload: completed line == cold load", replies(a) == cold_replies(tmp))


def test_atomic_replacement_does_not_reuse_a_matching_tail() -> None:
    """An edited head plus an unchanged 64-byte tail is not an append."""
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        a = make_agent(tmp)
        tail = ex("unchanged " * 30)
        write_jsonl(a.examples_file, [ex("old"), tail])
        a._reload_examples_if_stale()
        replacement = tmp / "replacement.jsonl"
        write_jsonl(replacement, [ex("new"), tail, ex("added")])
        os.replace(replacement, a.examples_file)
        a._reload_examples_if_stale()
        check("reload: replaced file cannot append onto stale cached head",
              replies(a) == ["new", "unchanged " * 30, "added"]
              == cold_replies(tmp), repr(replies(a)))


def test_atomic_replacement_with_preserved_metadata_is_seen() -> None:
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        a = make_agent(tmp)
        write_jsonl(a.examples_file, [ex("old")])
        a._reload_examples_if_stale()
        old_stat = a.examples_file.stat()
        replacement = tmp / "replacement.jsonl"
        write_jsonl(replacement, [ex("new")])
        os.utime(replacement, ns=(old_stat.st_atime_ns, old_stat.st_mtime_ns))
        os.replace(replacement, a.examples_file)
        a._reload_examples_if_stale()
        check("reload: atomic replacement with same size and time is visible",
              replies(a) == ["new"], repr(replies(a)))


def test_json_config_reload_tracks_restores_and_failed_edits() -> None:
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        a = make_agent(tmp)
        a.output_filter_file = tmp / "filters.json"
        a.lorebook_file = tmp / "lorebook.json"

        def write_configs(word, stamp):
            a.output_filter_file.write_text(json.dumps([
                {"name": "block", "pattern": word, "action": "reject"},
            ]), encoding="utf-8")
            a.lorebook_file.write_text(json.dumps([
                {"name": "fact", "keywords": ["tea"], "content": word},
            ]), encoding="utf-8")
            for path in (a.output_filter_file, a.lorebook_file):
                os.utime(path, ns=(stamp, stamp))

        def verify(word, label):
            check(f"config reload: filter {label}",
                  a._apply_output_filter(word)[0] == "")
            check(f"config reload: lorebook {label}",
                  word in a._lorebook_for_prompt([], focus_text="tea"))

        stamp = 1_700_000_000_000_000_000
        write_configs("first", stamp)
        verify("first", "initial load")
        write_configs("restored", stamp - 10_000_000_000)
        verify("restored", "accepts older restored file")
        write_configs("changed-size", stamp - 10_000_000_000)
        verify("changed-size", "accepts size change with same mtime")

        for path in (a.output_filter_file, a.lorebook_file):
            path.write_text("{broken", encoding="utf-8")
        verify("changed-size", "retains last valid config after malformed edit")
        write_configs("repaired", stamp + 10_000_000_000)
        verify("repaired", "recovers after malformed edit")
        for path in (a.output_filter_file, a.lorebook_file):
            path.unlink()
        check("config reload: deleted filter clears cache",
              a._apply_output_filter("repaired") == ("repaired", ""))
        check("config reload: deleted lorebook clears cache",
              a._lorebook_for_prompt([], focus_text="tea") == "")
        write_configs("recreated", stamp)
        verify("recreated", "loads recreated file")


def test_json_config_stat_failure_preserves_valid_cache() -> None:
    from unittest.mock import patch

    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        a = make_agent(tmp)
        a.output_filter_file = tmp / "filters.json"
        a.lorebook_file = tmp / "lorebook.json"
        a.output_filter_file.write_text(json.dumps([
            {"name": "block", "pattern": "blocked", "action": "reject"},
        ]), encoding="utf-8")
        a.lorebook_file.write_text(json.dumps([
            {"name": "tea", "keywords": ["tea"], "content": "Alice likes tea"},
        ]), encoding="utf-8")
        check("config I/O: initial filter rejects", a._apply_output_filter("blocked")[0] == "")
        check("config I/O: initial lorebook loads",
              "Alice likes tea" in a._lorebook_for_prompt([], focus_text="tea"))
        original_stat = Path.stat

        def unavailable(path, *args, **kwargs):
            if path in (a.output_filter_file, a.lorebook_file):
                raise PermissionError("temporarily unavailable")
            return original_stat(path, *args, **kwargs)

        with patch.object(Path, "stat", unavailable):
            check("config I/O: stat failure does not disable a loaded filter",
                  a._apply_output_filter("blocked")[0] == "")
            check("config I/O: stat failure preserves loaded lorebook",
                  "Alice likes tea" in a._lorebook_for_prompt([], focus_text="tea"))
        check("config I/O: filter recovers when readable",
              a._apply_output_filter("blocked")[0] == "")


def test_shrink_and_rewrite_fall_back_to_full_reload() -> None:
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        a = make_agent(tmp)
        write_jsonl(a.examples_file, [ex(f"r{i}") for i in range(30)])
        a._reload_examples_if_stale()

        # Shrink: what a trim does when the pool is over budget.
        time.sleep(0.01)
        write_jsonl(a.examples_file, [ex(f"r{i}") for i in range(8)])
        a._reload_examples_if_stale()
        check("reload: shrink triggers a full reload",
              replies(a) == [f"r{i}" for i in range(8)] == cold_replies(tmp))

        # In-place rewrite that leaves the file LONGER with a different prefix:
        # the only shape a blind seek-and-append would corrupt. The tail
        # signature is what catches it.
        time.sleep(0.01)
        write_jsonl(a.examples_file, [ex(f"z{i}") for i in range(20)])
        a._reload_examples_if_stale()
        check("reload: grown-but-rewritten file caught by the tail signature",
              replies(a) == [f"z{i}" for i in range(20)] == cold_replies(tmp))

        # Same-size in-place rewrite (reordering), newer mtime.
        time.sleep(0.01)
        write_jsonl(a.examples_file, [ex(f"z{i}") for i in reversed(range(20))])
        a._reload_examples_if_stale()
        check("reload: same-size rewrite reloaded",
              replies(a) == [f"z{i}" for i in reversed(range(20))])


def test_force_reload_and_malformed_lines() -> None:
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        a = make_agent(tmp)
        write_jsonl(a.examples_file, [ex(f"r{i}") for i in range(6)])
        a._reload_examples_if_stale()

        # `_examples_mtime = 0.0` is the force-reload switch tools/ and tests
        # use; it must still bypass the incremental path.
        a._examples_cache = []
        a._examples_mtime = 0.0
        a._reload_examples_if_stale()
        check("reload: mtime=0.0 forces a full reparse", len(a._examples_cache) == 6)

        # A corrupted line must not freeze the pool at its pre-corruption state.
        with a.examples_file.open("a", encoding="utf-8") as f:
            f.write("{ not json at all\n")
            f.write(json.dumps(ex("after_garbage")) + "\n")
        os.utime(a.examples_file, None)
        a._reload_examples_if_stale()
        check("reload: malformed line skipped, following line kept",
              replies(a) == [f"r{i}" for i in range(6)] + ["after_garbage"])

        # A deleted runtime file resets the cache rather than serving stale
        # entries, and clears the byte bookkeeping with it.
        a.examples_file.unlink()
        a._reload_examples_if_stale()
        check("reload: missing file clears the cache",
              a._examples_cache == [] and a._examples_offset == 0
              and a._examples_eof == 0 and a._examples_sig == b"")

        # The seed alone must still load once the runtime file is gone.
        write_jsonl(a.examples_seed_file, [ex("seed_only")])
        a._reload_examples_if_stale()
        check("reload: seed loads with no runtime file", replies(a) == ["seed_only"])


def test_file_without_trailing_newline_is_fully_parsed() -> None:
    """Hand-edited datasets may lack the final newline — that last entry must
    still load (it just isn't claimed as consumed, so the next change re-reads
    the file whole instead of double-counting the fragment)."""
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        a = make_agent(tmp)
        write_jsonl(a.examples_file, [ex(f"r{i}") for i in range(4)],
                    trailing_newline=False)
        a._reload_examples_if_stale()
        check("reload: newline-less final line still parsed",
              replies(a) == [f"r{i}" for i in range(4)])
        check("reload: newline-less tail not claimed as consumed",
              a._examples_offset < a._examples_eof)

        # Banking a new example must not glue itself onto that unterminated
        # last line — which would destroy a hand-curated entry AND the new one.
        bank_example(a, ex("r4"))
        os.utime(a.examples_file, None)
        a._reload_examples_if_stale()
        check("reload: banking onto a newline-less file preserves both records",
              replies(a) == [f"r{i}" for i in range(5)] == cold_replies(tmp))


def test_auto_example_dedup_set_tracks_appends() -> None:
    """_auto_examples_seen gates runtime example banking; an incremental
    reload has to extend it, not leave it stale."""
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        a = make_agent(tmp)
        write_jsonl(a.examples_file, [ex("first one")])
        a._reload_examples_if_stale()
        check("dedup set: built from disk", a._auto_examples_seen == {"first one"})

        append_jsonl(a.examples_file, [ex("second one")])
        a._reload_examples_if_stale()
        check("dedup set: extended on incremental append",
              a._auto_examples_seen == {"first one", "second one"})

        # A rewrite that removes an entry must drop it from the set too.
        time.sleep(0.01)
        write_jsonl(a.examples_file, [ex("second one")])
        a._reload_examples_if_stale()
        check("dedup set: rebuilt on full reload", a._auto_examples_seen == {"second one"})


def test_feedback_append_onto_unterminated_file() -> None:
    """Same hazard on the feedback side: evolution.append_jsonl must not merge
    its record into an unterminated last line."""
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        a = make_agent(tmp)
        curated = dict(ex("curated bad"), rating="better", better="curated good")
        write_jsonl(a.feedback_file, [curated], trailing_newline=False)
        evolution.append_jsonl(
            a.feedback_file,
            [dict(ex("new bad"), rating="better", better="new good")])
        a._reload_pairs_if_stale()
        check("pairs: append onto a newline-less file preserves both",
              [p["reply"] for p in a._pairs_cache] == ["curated bad", "new bad"])


def test_feedback_pairs_reload() -> None:
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        a = make_agent(tmp)
        pair = dict(ex("bad reply"), rating="better", better="good reply")
        write_jsonl(a.feedback_file, [pair, dict(ex("x"), rating="worse")])
        a._reload_pairs_if_stale()
        check("pairs: only rating=better rows kept",
              [p["reply"] for p in a._pairs_cache] == ["bad reply"])

        append_jsonl(a.feedback_file,
                     [dict(ex("bad two"), rating="better", better="good two"),
                      dict(ex("skipped"), rating="worse")])
        a._reload_pairs_if_stale()
        check("pairs: append filtered incrementally",
              [p["reply"] for p in a._pairs_cache] == ["bad reply", "bad two"])


# ---------------------------------------------------------------------------
# Pool caps: bound the auto-grown half, never touch the curated head
# ---------------------------------------------------------------------------

def auto_ex(reply: str) -> dict:
    """An auto-banked example — machine entries are the ones carrying a score."""
    return dict(ex(reply), score=5)


def test_examples_auto_pool_capped_curated_kept() -> None:
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        a = make_agent(tmp)
        a.examples_max_auto = 20
        curated = [ex(f"curated{i}") for i in range(3)]
        write_jsonl(a.examples_file, curated + [auto_ex(f"a{i}") for i in range(20)])

        # Inside the slack window (10% of the cap, min 8): no rewrite yet — a
        # pool sitting at the cap must not rewrite the whole file per append.
        for i in range(20, 24):
            bank_example(a, auto_ex(f"a{i}"))
        a._examples_mtime = 0.0
        a._reload_examples_if_stale()
        check("cap: slack absorbs small overshoot without a rewrite",
              len(a._examples_cache) == 3 + 24)

        # Past the slack window: trim back so the auto count settles in
        # [cap, cap+slack] instead of growing without bound.
        for i in range(24, 60):
            bank_example(a, auto_ex(f"a{i}"))
        a._examples_mtime = 0.0
        a._reload_examples_if_stale()
        got = replies(a)
        autos = [r for r in got if r.startswith("a")]
        check("cap: auto entries bounded by cap + slack", len(autos) <= 20 + 8 + 1,
              f"kept {len(autos)}")
        check("cap: newest auto entries survive", autos[-1] == "a59")
        check("cap: oldest auto entries dropped", "a0" not in autos)
        check("cap: every curated entry kept",
              [r for r in got if r.startswith("curated")]
              == ["curated0", "curated1", "curated2"])
        check("cap: curated head stays at the front of the file",
              got[:3] == ["curated0", "curated1", "curated2"])


def test_examples_cap_disabled_keeps_everything() -> None:
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        a = make_agent(tmp)
        a.examples_max_auto = 0  # opt out -> pre-cap behaviour
        write_jsonl(a.examples_file, [auto_ex(f"a{i}") for i in range(30)])
        for i in range(30, 60):
            bank_example(a, auto_ex(f"a{i}"))
        a._examples_mtime = 0.0
        a._reload_examples_if_stale()
        check("cap: 0 disables the cap", len(a._examples_cache) == 60)


def test_seed_pool_never_trimmed_and_always_retrieved() -> None:
    """The read-only data/ seed is outside the cap entirely: never rewritten,
    always at the front of the retrieved pool."""
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        a = make_agent(tmp)
        a.examples_max_auto = 5
        write_jsonl(a.examples_seed_file, [ex(f"seed{i}") for i in range(3)])
        seed_bytes = a.examples_seed_file.read_bytes()
        write_jsonl(a.examples_file, [auto_ex(f"a{i}") for i in range(40)])
        bank_example(a, auto_ex("fresh"))
        a._examples_mtime = 0.0
        a._reload_examples_if_stale()
        got = replies(a)
        check("seed: untouched on disk",
              a.examples_seed_file.read_bytes() == seed_bytes)
        check("seed: still leads the retrieved pool",
              got[:3] == ["seed0", "seed1", "seed2"])
        check("seed: rows are not counted against the cap",
              len([r for r in got if r.startswith("a")]) <= 5 + 8 + 1)


def test_all_curated_pool_never_trimmed() -> None:
    """A pool with no machine entries at all must survive untouched however
    far past the cap it is — the cap counts auto entries only."""
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        a = make_agent(tmp)
        a.examples_max_auto = 5
        write_jsonl(a.examples_file, [ex(f"curated{i}") for i in range(40)])
        bank_example(a, auto_ex("fresh"))
        a._examples_mtime = 0.0
        a._reload_examples_if_stale()
        check("cap: all-curated pool untouched", len(a._examples_cache) == 41)


def test_feedback_auto_pool_capped() -> None:
    def pair(reply: str, src: str = "") -> dict:
        p = dict(ex(reply), rating="better", better=f"good {reply}")
        if src:
            p["src"] = src
        return p

    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        a = make_agent(tmp)
        a.feedback_max_auto = 10
        write_jsonl(a.feedback_file,
                    [pair("hand1"), pair("hand2")]
                    + [pair(f"m{i}", "user_reaction") for i in range(10)])
        for i in range(10, 30):
            bank_pair(a, pair(f"m{i}", "user_reaction"))
        a._pairs_mtime = 0.0
        a._reload_pairs_if_stale()
        got = [p["reply"] for p in a._pairs_cache]
        machine = [r for r in got if r.startswith("m")]
        check("cap: machine pairs bounded by cap + slack", len(machine) <= 10 + 8 + 1,
              f"kept {len(machine)}")
        check("cap: newest machine pair survives", machine[-1] == "m29")
        check("cap: hand-authored pairs kept",
              [r for r in got if r.startswith("hand")] == ["hand1", "hand2"])


def test_feedback_write_survives_a_full_pool() -> None:
    """append_jsonl refuses past FEEDBACK_MAX_BYTES; the cap has to trim first
    so the primary learning channel doesn't go quiet when the file fills up."""
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        a = make_agent(tmp)
        a.feedback_max_auto = 5
        filler = "x" * 400
        rows = [dict(ex(f"m{i}"), rating="better", better=filler,
                     src="user_reaction") for i in range(60)]
        write_jsonl(a.feedback_file, rows)
        # Byte ceiling just above the current size: without the trim, nothing
        # more can ever be written.
        size = a.feedback_file.stat().st_size
        real_cap, evolution.FEEDBACK_MAX_BYTES = evolution.FEEDBACK_MAX_BYTES, size + 100
        try:
            wrote = bank_pair(
                a, dict(ex("brand new"), rating="better", better="fixed",
                        src="user_reaction"))
        finally:
            evolution.FEEDBACK_MAX_BYTES = real_cap
        a._pairs_mtime = 0.0
        a._reload_pairs_if_stale()
        check("cap: write succeeds against a full pool", wrote == 1)
        check("cap: the new pair is in the pool",
              "brand new" in [p["reply"] for p in a._pairs_cache])


def test_promoted_views_are_a_third_retrieval_source() -> None:
    """Promoted candidates reach the prompt from their own view files, and are
    ranked by the same scorer as seed and learned rows. Keeping them separate is
    what lets a rollback rewrite the view atomically without touching a single
    hand-approved row."""
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        a = make_agent(tmp)
        scope = {
            "lang": a.agent_lang, "platform": "qq", "conv_id": "g1",
            "persona": a.bot_name, "persona_hash": a.persona_hash,
            "persona_version": a.persona_version,
        }
        write_jsonl(a.examples_file, [ex("learned reply")])
        write_jsonl(a.feedback_file,
                    [dict(ex("learned bad"), rating="better",
                          better="learned good")])
        write_jsonl(a.promoted_examples_file,
                    [dict(ex("promoted reply"), src="promoted_candidate",
                          candidate_id="c1", scope=scope)])
        write_jsonl(a.promoted_feedback_file,
                    [dict(ex("promoted bad"), rating="better",
                          better="promoted good", src="promoted_candidate",
                          candidate_id="c2", scope=scope)])
        block = a._examples_for_prompt("hi", "called", conv_id="g1")
        for label in ("learned reply", "learned good", "promoted reply",
                      "promoted good"):
            check(f"view: {label} reaches the prompt", label in block)
        check("view: learned pool cache is unaffected by the views",
              replies(a) == ["learned reply"], str(replies(a)))

        # A rewritten view is picked up; a rewritten view of nothing empties it.
        time.sleep(0.01)
        write_jsonl(a.promoted_feedback_file, [])
        block = a._examples_for_prompt("hi", "called", conv_id="g1")
        check("view: an emptied view drops out of retrieval",
              "promoted good" not in block)
        check("view: the learned pool survives the view rewrite",
              "learned good" in block)

        # Rows that are not usable pairs must not be read as pairs.
        time.sleep(0.01)
        write_jsonl(a.promoted_feedback_file,
                    [dict(ex("half a pair"), rating="better", better="")])
        a._reload_views_if_stale()
        check("view: unusable pair rows are skipped", a._view_pairs_cache == [])


def test_persona_edit_keeps_promoted_rows_in_scope() -> None:
    """A one-byte persona edit used to orphan the whole learned corpus. Every
    hash seen under one PERSONA_VERSION is one character; a new version is a
    new one."""
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        a = make_agent(tmp)
        a.persona_lineage  # record the first revision
        scope = {
            "lang": a.agent_lang, "platform": "qq", "conv_id": "g1",
            "persona": a.bot_name, "persona_hash": a.persona_hash,
            "persona_version": a.persona_version,
        }
        write_jsonl(a.promoted_examples_file,
                    [dict(ex("promoted reply"), src="promoted_candidate",
                          candidate_id="c1", scope=scope)])
        b = make_agent(tmp)
        b.persona_hash = "edited000000"
        block = b._examples_for_prompt("hi", "called", conv_id="g1")
        check("lineage: a persona edit keeps promoted rows in scope",
              "promoted reply" in block, block)
        check("lineage: both revisions are recorded",
              set(b.persona_lineage.hashes(b.persona_version))
              == {a.persona_hash, "edited000000"},
              str(b.persona_lineage.versions()))
        check("lineage: the file lives beside the ledgers",
              (tmp / "persona_lineage.json").is_file())
        c = make_agent(tmp)
        c.persona_hash = "third0000000"
        c.persona_version = "v2"
        block = c._examples_for_prompt("hi", "called", conv_id="g1")
        check("lineage: a new PERSONA_VERSION starts a clean slate",
              "promoted reply" not in block, block)


def test_promoted_views_enforce_full_scope() -> None:
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        a = make_agent(tmp)
        base_scope = {
            "lang": a.agent_lang,
            "platform": "qq",
            "persona": a.bot_name,
            "persona_hash": a.persona_hash,
            "persona_version": a.persona_version,
        }
        write_jsonl(a.promoted_examples_file, [
            dict(ex("ROOM_A_ONLY"), src="promoted_candidate",
                 candidate_id="c-a",
                 scope=dict(base_scope, conv_id="room-a")),
            dict(ex("ROOM_B_ONLY"), src="promoted_candidate",
                 candidate_id="c-b",
                 scope=dict(base_scope, conv_id="room-b")),
        ])
        room_a = a._examples_for_prompt(
            "room", "called", conv_id="room-a")
        no_scope = a._examples_for_prompt("room", "called")
        check("view scope: matching room is retrieved",
              "ROOM_A_ONLY" in room_a, room_a)
        check("view scope: other room is excluded",
              "ROOM_B_ONLY" not in room_a, room_a)
        check("view scope: scoped authority is excluded without context",
              "ROOM_A_ONLY" not in no_scope and "ROOM_B_ONLY" not in no_scope,
              no_scope)


# ---------------------------------------------------------------------------
# Ranking: what the retrieved block is expected to prefer
# ---------------------------------------------------------------------------

def test_relevance_outranks_recency() -> None:
    """A stale entry that matches the focus text beats a fresh irrelevant one —
    the recency bonus is a tiebreaker, not a ranking signal of its own."""
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        a = make_agent(tmp)
        write_jsonl(a.examples_file, [
            ex("OLD_MATCH", scenario="deploy broke prod", ts="2020-01-01T00:00:00"),
            ex("NEW_MISS", scenario="unrelated chatter", ts="2099-01-01T00:00:00"),
        ])
        block = a._examples_for_prompt(focus_text="the deploy broke again", mode="",
                                       limit_good=1)
        check("rank: content match beats recency",
              "OLD_MATCH" in block and "NEW_MISS" not in block)


def test_future_timestamp_cannot_outrank_a_match() -> None:
    """The recency bonus is capped at +0.3; a future-dated entry must not be
    able to exceed that and jump the queue."""
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        a = make_agent(tmp)
        write_jsonl(a.examples_file, [
            ex("MATCH", scenario="gacha pulls", ts="2020-01-01T00:00:00"),
            ex("FUTURE", scenario="nothing alike", ts="2999-01-01T00:00:00"),
        ])
        block = a._examples_for_prompt(focus_text="gacha", mode="", limit_good=1)
        check("rank: future timestamp stays under the +0.3 cap",
              "MATCH" in block and "FUTURE" not in block)


def test_no_signal_falls_back_to_the_newest_entries() -> None:
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        a = make_agent(tmp)
        write_jsonl(a.examples_file, [ex(f"r{i}") for i in range(10)])
        block = a._examples_for_prompt(focus_text="", mode="", limit_good=2)
        check("rank: no focus/mode signal takes the tail of the pool",
              "r9" in block and "r8" in block and "r7" not in block)


def test_pair_rewrite_not_repeated_as_a_positive_example() -> None:
    """The [OK] side of a contrastive pair shouldn't also show up in the
    positive-examples section — that wastes prompt budget on a duplicate."""
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        a = make_agent(tmp)
        write_jsonl(a.feedback_file, [dict(
            ex("bad line", scenario="gacha pulls"), rating="better",
            better="the good line")])
        write_jsonl(a.examples_file, [ex("the good line", scenario="gacha pulls")])
        block = a._examples_for_prompt(focus_text="gacha pulls", mode="called")
        check("rank: pair rewrite excluded from positives",
              block.count("the good line") == 1)


def test_empty_pool_returns_nothing() -> None:
    with tempfile.TemporaryDirectory() as d:
        a = make_agent(Path(d))
        check("rank: empty pool yields no examples block",
              a._examples_for_prompt(focus_text="anything", mode="called") == "")


def main() -> int:
    test_append_is_incremental_and_matches_cold_load()
    test_same_mtime_append_is_still_seen()
    test_torn_append_waits_for_its_newline()
    test_atomic_replacement_does_not_reuse_a_matching_tail()
    test_atomic_replacement_with_preserved_metadata_is_seen()
    test_json_config_reload_tracks_restores_and_failed_edits()
    test_json_config_stat_failure_preserves_valid_cache()
    test_shrink_and_rewrite_fall_back_to_full_reload()
    test_force_reload_and_malformed_lines()
    test_file_without_trailing_newline_is_fully_parsed()
    test_auto_example_dedup_set_tracks_appends()
    test_feedback_append_onto_unterminated_file()
    test_feedback_pairs_reload()
    test_examples_auto_pool_capped_curated_kept()
    test_examples_cap_disabled_keeps_everything()
    test_seed_pool_never_trimmed_and_always_retrieved()
    test_all_curated_pool_never_trimmed()
    test_feedback_auto_pool_capped()
    test_feedback_write_survives_a_full_pool()
    test_promoted_views_are_a_third_retrieval_source()
    test_persona_edit_keeps_promoted_rows_in_scope()
    test_promoted_views_enforce_full_scope()
    test_relevance_outranks_recency()
    test_future_timestamp_cannot_outrank_a_match()
    test_no_signal_falls_back_to_the_newest_entries()
    test_pair_rewrite_not_repeated_as_a_positive_example()
    test_empty_pool_returns_nothing()
    print()
    if _failures:
        print(f"{len(_failures)} test(s) FAILED: {', '.join(_failures)}")
        return 1
    print("all tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
