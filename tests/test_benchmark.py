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


def test_isolated_agent_state_stays_in_one_tree() -> None:
    """Every state path of a benchmark agent must resolve inside state_dir.

    The Agent ctor re-anchors relative state paths under the repo's runtime/
    dir, so a relative --outdir split one arm's state across two trees: the
    ctor-resolved eval file landed in runtime/<outdir>/ while the post-ctor
    assignments landed in <outdir>/. Found because state-on had no eval.jsonl
    while the evolve tick was demonstrably reading one."""
    import os
    with tempfile.TemporaryDirectory() as td:
        old_cwd = os.getcwd()
        os.chdir(td)
        try:
            a = bench.build_isolated_agent(Path("rel-out") / "state-on",
                                           "Robin", "en", eval_enable=True)
            base = (Path(td) / "rel-out" / "state-on").resolve()
            for name in ("eval_file", "candidates_file", "feedback_file",
                         "examples_file", "memory_file", "core_memory_file"):
                p = Path(getattr(a, name))
                check(f"isolation: {name} inside state_dir",
                      p.is_absolute() and str(p.resolve()).startswith(str(base)),
                      str(p))
        finally:
            os.chdir(old_cwd)


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
            a._call_llm = fake_call

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


def _install_external_llm_fakes(agent: Agent) -> None:
    """Replace only the two network boundaries used by the real pipeline."""
    bad_reply = "Great question! Let me help."

    async def fake_call(system, messages, model, **kw):
        prompt = str(messages[-1].get("content", ""))
        if "[raw data]" in prompt and '"failure_mode"' in prompt:
            return json.dumps({
                "failure_mode": "service-desk tone",
                "bad_diagnosis": "opens like a support agent",
                "tag_to_patch": "style",
                "constraint_to_add":
                    "BAD 'Great question!' -> OK 'probably, your commit'",
                "pair_draft": {
                    "scenario": "casual status question",
                    "context": ["alex: is the build broken"],
                    "mode": "called",
                    "reply": bad_reply,
                    "better": "probably, it was your commit",
                },
            })
        return json.dumps({
            "reasoning": "direct question",
            "intent": "chat",
            "reply": bad_reply,
            "mem": "",
        })

    class EvalResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [{
                    "message": {
                        "content": json.dumps({
                            "score": 1,
                            "reason": "service-desk tone",
                        }),
                    },
                }],
            }

    class EvalClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, *args, **kwargs):
            return EvalResponse()

    agent._call_llm = fake_call
    agent._http = lambda **kwargs: EvalClient()


def test_real_evolution_pipeline_with_external_calls_stubbed() -> None:
    """The benchmark drives real eval, evolution, promotion, and retrieval."""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        agent = bench.build_isolated_agent(
            tmp / "state", "Robin", "en", eval_enable=True)
        _install_external_llm_fakes(agent)
        train = [{
            "id": "tr-real",
            "family": "service-desk",
            "scenario": "casual status question",
            "mode": "called",
            "context": ["alex: <bot-name> is the build still broken"],
        }]
        holdout = [{
            "id": "ho-real",
            "family": "service-desk",
            "scenario": "casual status question",
            "mode": "called",
            "context": ["taylor: <bot-name> did deploy recover"],
        }]

        replies = asyncio.run(
            bench.run_round(
                agent, train, holdout, "Robin",
                evolve_on=True, judge_model="stub-judge",
            )
        )

        eval_rows = evolution.load_evals(agent.eval_file, threshold=5)
        promoted = [
            cand for cand in agent.candidate_ledger.all()
            if cand.get("state") == "promoted"
        ]
        learned_pairs = evolution.load_feedback_keys(
            agent.promoted_feedback_file)
        check("real pipeline: holdout still produces a reply",
              replies[0]["reply"] == "Great question! Let me help.",
              repr(replies))
        check("real pipeline: evaluator persisted the low score",
              len(eval_rows) == 1 and eval_rows[0]["score"] == 1,
              repr(eval_rows))
        check("real pipeline: evolve tick recorded self-review evidence",
              [event["kind"] for event in agent.evidence_log.all()]
              == ["self_review"],
              repr(agent.evidence_log.all()))
        check("real pipeline: benchmark gate promoted the candidate",
              len(promoted) == 1, repr(promoted))
        check("real pipeline: promoted correction is retrievable",
              ("Great question! Let me help.", "probably, it was your commit")
              in learned_pairs,
              repr(learned_pairs))


def test_inbox_is_blind_and_ingest() -> None:
    arms = [{"arm": "evolve-on", "rounds": [
        {"round": 0, "feedback_pairs": 0,
         "holdout": [{"scenario_id": "ho1", "family": "vent", "reply": "hello",
                      "context": ["alex: rough day"]}]},
        {"round": 1, "feedback_pairs": 2,
         "holdout": [{"scenario_id": "ho1", "family": "vent", "reply": "sup",
                      "context": ["alex: rough day"]}]},
    ]}]
    inbox, key_map = bench.build_inbox(arms, votes=2)
    leaked = [k for it in inbox for k in it
              if k in ("arm", "round", "family", "scenario_id")]
    check("inbox blind (no leak fields)", leaked == [])
    check("inbox carries item_id + reply + context only",
          all(set(it) == {"item_id", "reply", "context"} for it in inbox))
    check("key_map covers all items", set(key_map) == {it["item_id"] for it in inbox})

    # The identifier is the thing the judge reads next to every reply, so the
    # blinding has to hold there.  Checking only that no dict *key* is named
    # "arm" passes happily on item_id="evolve-on|0|ho1#v1", which is exactly
    # what this function used to emit: the judge saw the arm on every line.
    # The hex-shape check below is the airtight one: a lowercase hex digest
    # cannot spell "evolve-on" or "vent". The substring check backs it up if
    # the id format is ever changed, and ignores values under 3 characters
    # because a single digit or an "f" collides with hex by chance, not by leak.
    exposed = [(it["item_id"], field, value)
               for it in inbox
               for field, value in key_map[it["item_id"]].items()
               if len(str(value)) >= 3 and str(value) in it["item_id"]]
    check("item_id leaks no metadata value", exposed == [], str(exposed[:3]))
    check("item_id is an opaque fixed-width digest",
          all(len(it["item_id"]) == 16 and all(c in "0123456789abcdef" for c in it["item_id"])
              for it in inbox),
          str([it["item_id"] for it in inbox[:3]]))
    # Repeat votes must not collapse: two votes on one reply need separate ids,
    # or the second vote silently overwrites the first in the score file.
    check("every vote gets a distinct id",
          len({it["item_id"] for it in inbox}) == len(inbox),
          f"{len({it['item_id'] for it in inbox})} ids for {len(inbox)} items")
    check("context rides along for the judge",
          all(it["context"] == ["alex: rough day"] for it in inbox))
    legacy = [{"arm": "evolve-on", "rounds": [
        {"round": 0, "feedback_pairs": 0,
         "holdout": [{"scenario_id": "ho1", "family": "vent", "reply": "hey"}]}]}]
    linbox, _ = bench.build_inbox(legacy, votes=1)
    check("legacy arms.json without context still exports",
          linbox and linbox[0]["context"] == [])
    check("build_inbox is deterministic",
          [it["item_id"] for it in bench.build_inbox(arms, votes=2)[0]]
          == [it["item_id"] for it in inbox])

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


def test_pass_sentinel_is_protocol_not_text() -> None:
    """The PASS sentinel must never reach the evaluator or the judge.

    The production gateway swallows PASS-prefixed replies before anything
    downstream sees them. The harness calls _think directly, and used to feed
    the raw string onward: the self-eval graded the literal word PASS as a
    reply (observed live: 'too terse and robotic', 2/5), the evolve tick got
    protocol noise as learning material, and the judge inbox asked a blind
    judge to rate "PASS" as if a person had typed it."""
    check("PASS collapses to silence", bench.strip_pass_sentinel("PASS") == "")
    check("PASS with tail collapses (production word-boundary rule)",
          bench.strip_pass_sentinel("PASS lol") == "")
    check("case-insensitive like production",
          bench.strip_pass_sentinel("pass.") == "")
    check("genuine reply is untouched",
          bench.strip_pass_sentinel("passable lol") == "passable lol")
    check("empty stays empty", bench.strip_pass_sentinel(None) == "")

    arms = [{"arm": "evolve-on", "rounds": [
        {"round": 0, "feedback_pairs": 0,
         "holdout": [{"scenario_id": "ho1", "family": "vent", "reply": "hey"},
                     {"scenario_id": "ho2", "family": "vent", "reply": ""}]},
    ]}]
    inbox, key_map = bench.build_inbox(arms, votes=1)
    check("silent replies never reach the judge inbox",
          len(inbox) == 1 and inbox[0]["reply"] == "hey", str(inbox))
    check("key_map matches the filtered inbox", set(key_map) == {inbox[0]["item_id"]})

    with tempfile.TemporaryDirectory() as td:
        ap = Path(td) / "arms.json"
        ap.write_text(json.dumps([
            {"arm": "evolve-on", "rounds": [
                {"round": 0, "holdout": [{"reply": ""}, {"reply": ""},
                                         {"reply": ""}, {"reply": "hey"}]}]},
            {"arm": "evolve-off", "rounds": [
                {"round": 0, "holdout": [{"reply": "a"}, {"reply": "b"},
                                         {"reply": "c"}, {"reply": "d"}]}]},
        ]), encoding="utf-8")
        counts = bench._pass_counts(ap)
        check("pass counts read from arms.json",
              counts[("evolve-on", 0)] == (3, 4)
              and counts[("evolve-off", 0)] == (0, 4), str(counts))
        w = bench._pass_warnings(counts)
        check("75-point silence gap is flagged",
              len(w) == 1 and "not like-for-like".replace(" ", " ") in w[0], str(w))
        balanced = {("evolve-on", 0): (1, 14), ("evolve-off", 0): (2, 14)}
        check("small silence gap is not flagged",
              bench._pass_warnings(balanced) == [])


def test_void_runs_are_reported_not_plotted() -> None:
    """A run the judge could not discriminate must not be presented as a result.

    aggregate() happily returns four tidy means when the judge answered 5 to
    every item, write_svg() plots them, and the operator sees a flat curve that
    looks like a measured null result. It is not one: zero variance means the
    comparison had no power to detect any difference at all."""
    km = {}
    flat = {}
    for arm in ("evolve-on", "evolve-off"):
        for rnd in (0, 1):
            for i in range(4):
                iid = f"{arm}{rnd}{i}"
                km[iid] = {"arm": arm, "round": rnd, "scenario_id": f"ho{i}",
                           "family": "vent"}
                flat[iid] = {"score": 5, "reason": "r"}
    agg = bench.aggregate(km, flat)
    check("void run: means still computed", len(agg["by_round"]) == 4)
    check("void run: flagged as unusable",
          any("zero variance" in w for w in agg["warnings"]), str(agg["warnings"]))

    near = {k: {"score": 4 + (i % 2), "reason": "r"} for i, k in enumerate(km)}
    check("near-ceiling run: flagged as low power",
          any("near-ceiling" in w for w in bench.aggregate(km, near)["warnings"]))

    spread = {k: {"score": 1 + (i % 5), "reason": "r"} for i, k in enumerate(km)}
    check("discriminating run: no warning",
          bench.aggregate(km, spread)["warnings"] == [],
          str(bench.aggregate(km, spread)["warnings"]))

    # A ceiling run with style=full means the ablation was off, not broken.
    with tempfile.TemporaryDirectory() as td:
        mp = Path(td) / "meta.json"
        mp.write_text(json.dumps({"style": "full"}), encoding="utf-8")
        check("full-style ceiling names the real cause",
              any("--style weak" in w
                  for w in bench._style_warnings(mp, ["zero variance"])))
        check("full-style is not flagged when the run discriminated",
              bench._style_warnings(mp, []) == [])
        mp.write_text(json.dumps({"style": "weak"}), encoding="utf-8")
        check("weak-style ceiling is not blamed on the flag",
              bench._style_warnings(mp, ["zero variance"]) == [])

    # An evolve-on arm that never banked a feedback pair is the control.
    with tempfile.TemporaryDirectory() as td:
        ap = Path(td) / "arms.json"
        ap.write_text(json.dumps([
            {"arm": "evolve-on", "rounds": [{"round": 0, "feedback_pairs": 0},
                                            {"round": 1, "feedback_pairs": 0}]},
            {"arm": "evolve-off", "rounds": [{"round": 0, "feedback_pairs": 0}]},
        ]), encoding="utf-8")
        w = bench._arm_warnings(ap)
        check("no-feedback on-arm is flagged",
              len(w) == 1 and "nothing to learn from" in w[0], str(w))
        ap.write_text(json.dumps([
            {"arm": "evolve-on", "rounds": [{"round": 0, "feedback_pairs": 0},
                                            {"round": 1, "feedback_pairs": 3}]},
        ]), encoding="utf-8")
        check("on-arm that did learn is not flagged", bench._arm_warnings(ap) == [])


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
        check("exported item blind",
              set(rec) == {"item_id", "context", "reply"}
              and not any(k in rec for k in ("arm", "round", "family", "scenario_id")))
        check("exported reply present", rec["reply"] == "hi there")


def main() -> int:
    test_scenario_sets()
    test_seed_buffer()
    test_drive_scenario_stubbed()
    test_isolated_agent_state_stays_in_one_tree()
    test_run_arm_isolation_and_growth()
    test_real_evolution_pipeline_with_external_calls_stubbed()
    test_inbox_is_blind_and_ingest()
    test_pass_sentinel_is_protocol_not_text()
    test_void_runs_are_reported_not_plotted()
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
