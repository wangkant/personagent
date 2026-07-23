"""tools/evolution_benchmark.py — quantify the self-evolution loop.

Drives the real Agent over synthetic train / held-out scenario sets across N
rounds and two arms (evolve-on, evolve-off control), each in an isolated temp
state dir, then exports blind held-out replies for an independent judge
(Claude) and plots mean score vs round. See
docs/superpowers/specs/2026-07-22-evolution-benchmark-design.md.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

VALID_MODES = {"owner", "called", "followup", "judge"}


def load_scenarios(path: Path) -> list[dict]:
    out: list[dict] = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        r = json.loads(ln)
        if r.get("mode") not in VALID_MODES:
            raise ValueError(f"scenario {r.get('id')} has bad mode {r.get('mode')!r}")
        if not r.get("context"):
            raise ValueError(f"scenario {r.get('id')} has empty context")
        out.append(r)
    return out


def scenario_families(scns: list[dict]) -> set[str]:
    return {s["family"] for s in scns}
