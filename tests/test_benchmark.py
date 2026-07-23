"""Tests for the self-evolution benchmark (tools/evolution_benchmark.py).

Run from the repo root, no test framework:

    python tests/test_benchmark.py
"""
from __future__ import annotations

import asyncio  # noqa: E402
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import evolution_benchmark as bench  # noqa: E402
from persona_agent.agent import Agent  # noqa: E402

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


def _make_agent(tmp: Path) -> Agent:
    a = Agent(
        api_key="test-key", bot_qq="10001", bot_name="Robin",
        napcat_api="http://127.0.0.1:9",
        memory_file=str(tmp / "memory.json"), persona="test persona",
        eval_enable=False, eval_file=str(tmp / "eval.jsonl"),
        stickers_dir=str(tmp / "stickers"), stickers_file=str(tmp / "stickers.json"),
        message_debounce_sec=0, lang="en",
    )
    a._seen_msg_file = tmp / "seen_msg_ids.json"
    a.core_memory_file = tmp / "core_memory.json"
    a._seen_msg_ids.clear()
    a.core_memory.clear()
    return a


def test_seed_buffer() -> None:
    with tempfile.TemporaryDirectory() as td:
        a = _make_agent(Path(td))
        scn = {"id": "x", "family": "f", "scenario": "s", "mode": "called",
               "context": ["alex: morning <bot-name>", "jordan: <bot-name> you up"]}
        latest, caller = bench.seed_buffer(a, "g1", scn, "Robin")
        buf = list(a.buffers["g1"])
        check("buffer filled", len(buf) == 2)
        check("bot-name substituted", "<bot-name>" not in buf[0]["text"]
              and "Robin" in buf[0]["text"])
        check("name parsed", buf[0]["name"] == "alex" and buf[1]["name"] == "jordan")
        check("latest is last text", latest == buf[-1]["text"])
        check("caller is last speaker", caller == ("jordan", bench.NAME_QQ["jordan"]))


def test_drive_scenario_stubbed() -> None:
    with tempfile.TemporaryDirectory() as td:
        a = _make_agent(Path(td))

        async def fake_think(group_id, mode, latest_text="", caller_override=None):
            return "yo whats up", "chat", ""
        a._think = fake_think
        scn = {"id": "x", "family": "f", "scenario": "s", "mode": "called",
               "context": ["alex: <bot-name> hi"]}
        reply = asyncio.run(bench.drive_scenario(a, scn, "Robin"))
        check("drive returns reply", reply == "yo whats up")


def main() -> int:
    test_scenario_sets()
    test_seed_buffer()
    test_drive_scenario_stubbed()
    print()
    if _failures:
        print(f"{len(_failures)} test(s) FAILED: {', '.join(_failures)}")
        return 1
    print("all tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
