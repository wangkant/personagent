"""Tests for what is left of the pre-ledger example pool.

The weight-based gate this file used to cover (weights, decay, promotion
threshold) is gone: nothing had called `CandidatePool.record` since the
evidence ledger took over promotion, so those tests were exercising a second,
divergent set of rules and reporting it as coverage of the live one. What the
ledger decides now lives in tests/test_ledger.py.

What is protected here is the part a deployment that learned before the ledger
still depends on: its `example_candidates.json` keeps loading, and a human
disagreement can still pull a reply out of the pool it was banked in.

Run from the repo root:

    python -m pytest tests/test_promotion.py
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from persona_agent.promotion import CandidatePool, retract_example

NOW = 1_800_000_000.0


def check(name: str, cond: bool, detail: str = "") -> None:
    """Assert `cond`, naming the property so a failure reads as English.

    The suites state a property per line rather than one per function, and
    they keep saying it that way; this turns each statement into the assert
    pytest reports on."""
    assert cond, name + (f" - {detail}" if detail else "")


def ex(reply: str) -> dict:
    return {"reply": reply, "scenario": "s", "mode": "called",
            "intent": "joke", "context": ["[u] hi"], "score": 5}


def pool(tmp: Path) -> CandidatePool:
    return CandidatePool(tmp / "cand.json")


def seed(tmp: Path, *replies: str) -> Path:
    """Write a pool file in the shape the retired `record` used to leave behind.

    Seeding from disk rather than through the class is the point: this is how
    the file arrives now — written by a version that no longer runs."""
    path = tmp / "cand.json"
    path.write_text(json.dumps({
        r: {"weight": 0.6, "ts": NOW, "n": 1,
            "sources": ["reaction_owner"], "example": ex(r)}
        for r in replies
    }, ensure_ascii=False), encoding="utf-8")
    return path


def test_a_legacy_pool_still_loads() -> None:
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        seed(tmp, "banked earlier", "also banked")
        p = pool(tmp)
        check("legacy pool: rows written by the old gate are read back",
              set(p._d) == {"banked earlier", "also banked"}, str(sorted(p._d)))


def test_a_corrupt_pool_file_degrades_to_empty() -> None:
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        (tmp / "cand.json").write_text("{not json", encoding="utf-8")
        check("legacy pool: unreadable file loads as empty, does not raise",
              pool(tmp)._d == {})


def test_withdraw() -> None:
    """The one mutation still reachable in production (learning.py)."""
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        seed(tmp, "disputed", "untouched")
        p = pool(tmp)
        check("withdraw reports a hit", p.withdraw("disputed") is True)
        check("withdraw drops only its own row",
              set(p._d) == {"untouched"}, str(sorted(p._d)))
        check("withdrawing an unknown reply is a no-op",
              p.withdraw("never seen") is False)
        check("withdraw is persisted, not just in memory",
              set(pool(tmp)._d) == {"untouched"}, str(sorted(pool(tmp)._d)))


def test_retract_example_from_pool() -> None:
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "examples.jsonl"
        rows = [ex("keep me"), ex("drop me"), ex("keep me too")]
        f.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
        n = retract_example(f, "drop me")
        left = [json.loads(l)["reply"] for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
        check("retract removes exactly the rejected reply", n == 1 and left == ["keep me", "keep me too"],
              f"n={n} left={left}")
        check("retracting an absent reply rewrites nothing",
              retract_example(f, "not here") == 0)

        # A malformed row must survive untouched rather than be silently eaten.
        f.write_text('{"reply": "drop me"}\nnot json\n', encoding="utf-8")
        retract_example(f, "drop me")
        check("malformed row preserved",
              f.read_text(encoding="utf-8").strip() == "not json")
