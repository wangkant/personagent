"""tools/scenario_probe.py — calibrate candidate benchmark scenarios.

A scenario earns its place in the benchmark by demonstrating, against the real
model, that it does the one thing the ablation needs: make a weakly-styled
agent produce a reply the measurement instruments can actually see. A scenario
that "should" bait assistant-voice but does not is dead weight — it dilutes
the curve and inflates run cost — and intuition is a poor predictor of which
prompts actually trip a given model. So: measure, keep what fires, record why
the rest were dropped.

For every candidate scenario this probe reports two numbers:

- self_eval: the agent's own 1-5 quality score for its weak-style reply. This
  is the learning trigger — only scores <= EVOLVE_THRESHOLD (default 2)
  become material the evolve tick can turn into feedback pairs. A family
  whose replies never dip that low gives the evolve-on arm nothing to learn.
- judge: the blind judge's 1-5 AI-tell score (via --judge-model, an
  OpenAI-compatible endpoint). This is the measurement — if the judge cannot
  see the tell either, the failure the loop fixes would be invisible in the
  curve.

Usage:
    python tools/scenario_probe.py --candidates data/benchmark/candidates.jsonl \
        --judge-model deepseek-v4-pro --outdir benchmark_runs/probe

Writes probe_results.jsonl (one row per scenario: reply + both scores) and a
per-family summary to stdout. Selection is left to the operator: the numbers
are the evidence, not the verdict.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import evolution_benchmark as bench  # noqa: E402


async def probe_one(scn: dict, bot_name: str, lang: str, state_root: Path) -> dict:
    """Drive one scenario with the weak style guide and self-eval the reply."""
    state_dir = state_root / scn["id"]
    agent = bench.build_isolated_agent(state_dir, bot_name, lang, eval_enable=False)
    reply = await bench.drive_scenario(agent, scn, bot_name)
    row = {"id": scn["id"], "family": scn["family"], "mode": scn["mode"],
           "scenario": scn.get("scenario", ""), "reply": reply,
           "self_eval": None, "self_eval_reason": ""}
    if not reply:
        row["self_eval_reason"] = "empty reply"
        return row
    # Same trigger chain as the benchmark: the buffer still holds the context,
    # the eval model falls back to the main model when EVAL_MODEL is unset.
    # ctx_msgs keeps the latest user line: in the live path the snapshot window
    # ends at the bot's own reply, so the message being replied to is part of
    # the eval context there too.
    ctx_lines = [f"{m['name']}: {m['text']}" for m in list(agent.buffers["g1"])]
    latest = ctx_lines[-1] if ctx_lines else ""
    await agent._evaluate_reply("g1", scn["mode"], latest, reply,
                                ctx_msgs=ctx_lines)
    try:
        rows = [json.loads(l) for l in
                (state_dir / "eval.jsonl").read_text(encoding="utf-8").splitlines()
                if l.strip()]
        if rows:
            row["self_eval"] = int(rows[-1].get("score", 0)) or None
            row["self_eval_reason"] = str(rows[-1].get("reason", ""))[:160]
    except (OSError, json.JSONDecodeError, ValueError):
        pass
    return row


async def main_async(args) -> int:
    scns = bench.load_scenarios(Path(args.candidates))
    print(f"probing {len(scns)} scenario(s) with the weak style guide "
          f"(model={bench.os.getenv('DEEPSEEK_MODEL', 'deepseek-chat')})")
    import persona_agent.agent as pa
    pa.STYLE_GUIDE = bench.WEAK_STYLE_GUIDE

    bot_name = bench.os.getenv("BOT_NAME", "Robin") or "Robin"
    out_dir = Path(args.outdir)
    out_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    with tempfile.TemporaryDirectory() as td:
        for scn in scns:  # sequential on purpose: stay inside the rate window
            row = await probe_one(scn, bot_name, args.lang, Path(td))
            rows.append(row)
            print(f"  {row['id']} [{row['family']}] self_eval="
                  f"{row['self_eval']} reply={row['reply'][:70]!r}")

    if args.judge_model:
        by_id = {s["id"]: s for s in scns}
        inbox = [{"item_id": r["id"], "reply": r["reply"],
                  "context": [ln.replace("<bot-name>", bot_name)
                              for ln in by_id[r["id"]]["context"]]}
                 for r in rows if r["reply"]]
        scores = await bench.judge_openai_compatible(inbox, args.judge_model)
        for r in rows:
            hit = scores.get(r["id"])
            r["judge"] = hit["score"] if hit else None
            r["judge_reason"] = hit["reason"] if hit else ""

    out = out_dir / "probe_results.jsonl"
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
                   encoding="utf-8", newline="\n")

    # Per-family summary: does the family produce trigger material (self_eval
    # <= 2) and visible tells (judge <= 3)?
    fams: dict[str, list[dict]] = {}
    for r in rows:
        fams.setdefault(r["family"], []).append(r)
    print(f"\n{'family':<14} {'n':>2} {'self<=2':>7} {'judge<=3':>8}  verdict")
    for fam, frs in sorted(fams.items()):
        trig = sum(1 for r in frs if (r["self_eval"] or 5) <= 2)
        tell = sum(1 for r in frs if (r.get("judge") or 5) <= 3)
        verdict = ("fires" if trig and tell else
                   "invisible-to-judge" if trig else
                   "no-trigger" if tell else "inert")
        print(f"{fam:<14} {len(frs):>2} {trig:>7} {tell:>8}  {verdict}")
    print(f"\nWrote {out}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--candidates", required=True,
                   help="candidate scenarios JSONL (same schema as train/holdout)")
    p.add_argument("--lang", default="en")
    p.add_argument("--judge-model", default="",
                   help="OpenAI-compatible judge model; empty skips the judge pass")
    p.add_argument("--outdir", default="benchmark_runs/probe")
    return asyncio.run(main_async(p.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
