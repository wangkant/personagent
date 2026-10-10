"""Tests for retract_example, how a human disagreement pulls a reply out of
the hand-approved example pool. What the ledger decides lives in
tests/test_ledger.py.

Run from the repo root:

    python -m pytest tests/test_promotion.py
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from persona_agent.promotion import retract_example


def check(name: str, cond: bool, detail: str = "") -> None:
    """Assert `cond`, naming the property so a failure reads as English.

    The suites state a property per line rather than one per function, and
    they keep saying it that way; this turns each statement into the assert
    pytest reports on."""
    assert cond, name + (f" - {detail}" if detail else "")


def ex(reply: str) -> dict:
    return {"reply": reply, "scenario": "s", "mode": "called",
            "intent": "joke", "context": ["[u] hi"], "score": 5}


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
