"""Calibrate candidate benchmark scenarios against the real model.

A scenario is worth keeping only if a weakly-styled agent's reply to it is
something both instruments can see. For each candidate this reports:

- self_eval: the agent's own 1-5 score for its weak-style reply, the learning
  trigger (only scores <= EVOLVE_THRESHOLD, default 3, become feedback pairs).
- judge: the blind judge's 1-5 AI-tell score (--judge-model, an
  OpenAI-compatible endpoint), the measurement.

Usage:
    python tools/scenario_probe.py --candidates my_candidates.jsonl \
        --judge-model <a model other than LLM_MODEL> --outdir benchmark_runs/probe

Writes probe_results.jsonl (one row per scenario: reply + both scores) and a
per-family summary to stdout.
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


async def probe_one(scn: dict, persona_name: str, lang: str, state_root: Path) -> dict:
    """Drive one scenario with the weak style guide and self-eval the reply."""
    state_dir = state_root / scn["id"]
    agent = bench.build_isolated_agent(state_dir, persona_name, lang, eval_enabled=False)
    reply = await bench.drive_scenario(agent, scn, persona_name)
    row = {"id": scn["id"], "family": scn["family"], "mode": scn["mode"],
           "scenario": scn.get("scenario", ""), "reply": reply,
           "self_eval": None, "self_eval_reason": ""}
    if not reply:
        row["self_eval_reason"] = "empty reply"
        return row
    # ctx_msgs keeps the latest user line, as the live snapshot window does.
    ctx_lines = [f"{m['name']}: {m['text']}" for m in list(agent.buffers["g1"])]
    latest = ctx_lines[-1] if ctx_lines else ""
    await agent._evaluate_reply("g1", scn["mode"], latest, reply,
                                ctx_msgs=ctx_lines)
    # No eval.jsonl when the eval call failed.
    eval_file = state_dir / "eval.jsonl"
    if eval_file.exists():
        rows = [json.loads(l) for l in
                eval_file.read_text(encoding="utf-8").splitlines() if l.strip()]
        if rows:
            row["self_eval"] = rows[-1]["score"] or None
            row["self_eval_reason"] = str(rows[-1].get("reason", ""))[:160]
    return row


async def main_async(args) -> int:
    scns = bench.load_scenarios(Path(args.candidates))
    print(f"probing {len(scns)} scenario(s) with the weak style guide "
          f"(model={bench.os.getenv('LLM_MODEL', bench.DEFAULT_LLM_MODEL)})")
    import persona_agent.prompt as group_prompt
    group_prompt.STYLE_GUIDE = bench.WEAK_STYLE_GUIDE

    persona_name = bench.os.getenv("PERSONA_NAME", "Robin") or "Robin"
    out_dir = Path(args.outdir)
    out_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    with tempfile.TemporaryDirectory() as td:
        for scn in scns:  # sequential: stay inside the rate window
            row = await probe_one(scn, persona_name, args.lang, Path(td))
            rows.append(row)
            print(f"  {row['id']} [{row['family']}] self_eval="
                  f"{row['self_eval']} reply={row['reply'][:70]!r}")

    if args.judge_model:
        by_id = {s["id"]: s for s in scns}
        inbox = [{"item_id": r["id"], "reply": r["reply"],
                  "context": [ln.replace("<bot-name>", persona_name)
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

    # Per family: trigger material (self_eval <= 2) and visible tells (judge <= 3).
    fams: dict[str, list[dict]] = {}
    for r in rows:
        fams.setdefault(r["family"], []).append(r)
    judged = any(r.get("judge") is not None for r in rows)
    print(f"\n{'family':<14} {'n':>2} {'self<=2':>7} {'judge<=3':>8}  verdict")
    for fam, frs in sorted(fams.items()):
        trig = sum(1 for r in frs if (r["self_eval"] or 5) <= 2)
        if not judged:
            print(f"{fam:<14} {len(frs):>2} {trig:>7} {'-':>8}  "
                  f"{'triggers' if trig else 'no-trigger'}")
            continue
        tell = sum(1 for r in frs if (r.get("judge") or 5) <= 3)
        verdict = ("fires" if trig and tell else
                   "invisible-to-judge" if trig else
                   "no-trigger" if tell else "inert")
        print(f"{fam:<14} {len(frs):>2} {trig:>7} {tell:>8}  {verdict}")
    if not judged:
        print("\nNo judge ran (--judge-model empty); pass --judge-model for "
              "the tell verdicts.")
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
