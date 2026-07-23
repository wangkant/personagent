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
from persona_agent import evolution  # noqa: E402

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


def test_run_arm_isolation_and_growth() -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        train = [{"id": "tr1", "family": "service-desk", "scenario": "s",
                  "mode": "called", "context": ["alex: <bot-name> hi"]}]
        holdout = [{"id": "ho1", "family": "service-desk", "scenario": "s",
                    "mode": "called", "context": ["taylor: <bot-name> yo"]}]

        # Patch the Agent factory to stub the model + self-eval so no network.
        orig = bench.build_isolated_agent

        def patched(state_dir, bot_name, lang, eval_enable):
            a = orig(state_dir, bot_name, lang, eval_enable)

            async def fake_call(system, messages, model, **kw):
                return json.dumps({"reasoning": "x", "intent": "chat",
                                   "reply": "Great question! Let me help.", "mem": ""})
            a._call_anthropic = fake_call

            async def fake_eval(group_id, mode, user_msg, reply,
                                sticker_files=None, intent="", ctx_msgs=None):
                return None  # no-op self-eval; the loop is driven by fake_eval_tick
            a._evaluate_reply = fake_eval

            async def fake_eval_tick():
                # Emulate a low score turning into one feedback pair.
                pair = {"ts": "t", "scenario": "s", "context": ["alex: hi"],
                        "mode": "called", "reply": "Great question! Let me help.",
                        "rating": "better", "better": "lol what's up", "src": "auto_reviewer"}
                evolution.append_jsonl(a.feedback_file, [pair])
                return 1
            a._evolve_tick = fake_eval_tick
            return a
        bench.build_isolated_agent = patched
        try:
            on = asyncio.run(bench.run_arm(train, holdout, "Robin", "en", 2,
                                           True, tmp / "on", "claude"))
            off = asyncio.run(bench.run_arm(train, holdout, "Robin", "en", 2,
                                            False, tmp / "off", "claude"))
        finally:
            bench.build_isolated_agent = orig

        check("on arm rounds recorded", len(on["rounds"]) == 3)  # round 0 + 2
        check("on arm feedback grew", on["rounds"][-1]["feedback_pairs"] >= 1)
        check("off arm feedback frozen", off["rounds"][-1]["feedback_pairs"] == 0)
        check("holdout replies present",
              all(r["holdout"] for r in on["rounds"]))
        # Repo state untouched: the real feedback file must be unchanged.
        real_fb = ROOT / "data" / "feedback.en.jsonl"
        check("repo feedback untouched (no auto_reviewer rows)",
              "auto_reviewer" not in real_fb.read_text(encoding="utf-8"))


def test_inbox_is_blind_and_ingest() -> None:
    arms = [{"arm": "evolve-on", "rounds": [
        {"round": 0, "feedback_pairs": 0,
         "holdout": [{"scenario_id": "ho1", "family": "f", "reply": "hello"}]},
        {"round": 1, "feedback_pairs": 2,
         "holdout": [{"scenario_id": "ho1", "family": "f", "reply": "sup"}]},
    ]}]
    inbox, key_map = bench.build_inbox(arms, votes=1)
    leaked = [k for it in inbox for k in it
              if k in ("arm", "round", "family", "scenario_id")]
    check("inbox blind (no leak fields)", leaked == [])
    check("inbox has item_id + reply only", all(set(it) == {"item_id", "reply"} for it in inbox))
    check("key_map covers all items", set(key_map) == {it["item_id"] for it in inbox})

    scores = {it["item_id"]: {"score": 3 + i, "reason": "r"} for i, it in enumerate(inbox)}
    agg = bench.aggregate(key_map, scores)
    check("aggregate has both rounds",
          ("evolve-on", 0) in agg["by_round"] and ("evolve-on", 1) in agg["by_round"])

    # Missing score -> error, not silent partial average.
    partial = dict(list(scores.items())[:1])
    raised = False
    try:
        bench.aggregate(key_map, partial)
    except ValueError:
        raised = True
    check("aggregate errors on missing score", raised)


def test_outputs() -> None:
    agg = {"by_round": {("evolve-on", 0): 2.5, ("evolve-on", 1): 3.4,
                        ("evolve-off", 0): 2.5, ("evolve-off", 1): 2.6},
           "by_family": {}}
    with tempfile.TemporaryDirectory() as td:
        csv_p = Path(td) / "r.csv"
        svg_p = Path(td) / "r.svg"
        bench.write_csv(agg, csv_p)
        bench.write_svg(agg, svg_p)
        csv_txt = csv_p.read_text(encoding="utf-8")
        check("csv header", csv_txt.splitlines()[0] == "arm,round,mean_score")
        check("csv has on row", "evolve-on,1,3.4" in csv_txt)
        svg_txt = svg_p.read_text(encoding="utf-8")
        check("svg is svg", svg_txt.lstrip().startswith("<svg"))
        check("svg well-formed", svg_txt.count("<svg") == 1 and "</svg>" in svg_txt)
        import xml.dom.minidom
        xml.dom.minidom.parseString(svg_txt)  # raises if malformed
        check("svg parses as xml", True)


def test_export_writes_blind_inbox() -> None:
    arms = [{"arm": "evolve-on", "rounds": [
        {"round": 0, "feedback_pairs": 0,
         "holdout": [{"scenario_id": "ho1", "family": "f", "reply": "hi there"}]}]}]
    inbox, _ = bench.build_inbox(arms, votes=1)
    with tempfile.TemporaryDirectory() as td:
        out = Path(td)
        asyncio.run(bench.judge_export(inbox, out))
        written = (out / "judge_inbox.jsonl").read_text(encoding="utf-8")
        rec = json.loads(written.splitlines()[0])
        check("exported item blind", set(rec) == {"item_id", "reply"})
        check("exported reply present", rec["reply"] == "hi there")


def main() -> int:
    test_scenario_sets()
    test_seed_buffer()
    test_drive_scenario_stubbed()
    test_run_arm_isolation_and_growth()
    test_inbox_is_blind_and_ingest()
    test_outputs()
    test_export_writes_blind_inbox()
    print()
    if _failures:
        print(f"{len(_failures)} test(s) FAILED: {', '.join(_failures)}")
        return 1
    print("all tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
