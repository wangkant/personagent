"""Tests for the self-evolution benchmark (tools/evolution_benchmark.py).

Run from the repo root, no test framework:

    python tests/test_benchmark.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import evolution_benchmark as bench  # noqa: E402

_failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {name}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        _failures.append(name)


def test_scenario_sets() -> None:
    train = bench.load_scenarios(ROOT / "data" / "benchmark" / "scenarios.train.en.jsonl")
    holdout = bench.load_scenarios(ROOT / "data" / "benchmark" / "scenarios.holdout.en.jsonl")
    check("train non-empty", len(train) >= 1)
    check("holdout non-empty", len(holdout) >= 1)
    train_ids = {s["id"] for s in train}
    holdout_ids = {s["id"] for s in holdout}
    check("ids disjoint", train_ids.isdisjoint(holdout_ids))
    check("families shared", bench.scenario_families(train) == bench.scenario_families(holdout))
    check("every scenario has context", all(s.get("context") for s in train + holdout))
    check("modes valid", all(s["mode"] in {"owner", "called", "followup", "judge"}
                             for s in train + holdout))


def main() -> int:
    test_scenario_sets()
    print()
    if _failures:
        print(f"{len(_failures)} test(s) FAILED: {', '.join(_failures)}")
        return 1
    print("all tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
