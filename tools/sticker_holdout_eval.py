"""tools/sticker_holdout_eval.py — measure the visual aesthetic gate's
stability and accuracy against a human-labeled holdout set.

Why this exists: the VISION_AESTHETIC_PROMPT in agent.py is hand-tuned. If
you only iterate the prompt against the same handful of failure examples
you have on hand, "the next version" is fitting that handful — not
improving real performance on borderline images. A holdout set you don't
touch while tuning is the only way to tell those two apart.

How to use it:
  1) Hand-label 30-50 stickers from `stickers/auto/` into `holdout.jsonl`.
     One JSON object per line:
       {"filename": "abc.png", "expected_approved": true}
     Pick a mix of clear-yes / clear-no / borderline cases. See
     `tools/holdout.example.jsonl` for the format.
  2) Run:
       python tools/sticker_holdout_eval.py [--runs 5] [--file holdout.jsonl]
     This judges each image multiple times and reports:
       - per-image vote distribution (how many of N runs voted approve)
       - confusion matrix vs the labels (accuracy / precision / recall)
       - stability count: how many images flipped between runs

  After changing the prompt, run the same holdout again and compare. If
  accuracy went up and stability didn't get worse, the change actually
  helped. If accuracy is flat but the failure cases you targeted got
  better, you most likely fit the targeted cases at the expense of
  something else.

Budget: ~30 images × 5 runs = ~150 vision calls. With a cheap vision
endpoint this should cost well under $1.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=True)

from agent import Agent

STICKERS_DIR = ROOT / "stickers" / "auto"


async def main(holdout_path: Path, runs: int) -> None:
    if not holdout_path.exists():
        print(f"holdout file not found: {holdout_path}")
        print("see tools/holdout.example.jsonl for the expected format")
        sys.exit(1)

    holdout = []
    for line in holdout_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            holdout.append(json.loads(line))
        except json.JSONDecodeError as e:
            print(f"skipping bad line: {line[:80]} ({e})")
    if not holdout:
        print("no valid entries in holdout file")
        sys.exit(1)
    print(f"loaded {len(holdout)} holdout entries, runs={runs}")

    # Spin up an Agent purely for the vision aesthetic pipeline. Most
    # fields aren't exercised; we just need vision_model + glm_* creds.
    agent = Agent(
        api_key=os.getenv("DEEPSEEK_API_KEY", ""),
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        model=os.getenv("DEEPSEEK_MODEL", ""),
        bot_qq=os.getenv("BOT_QQ", ""),
        bot_name=os.getenv("BOT_NAME", ""),
        anthropic_key=os.getenv("ANTHROPIC_API_KEY", ""),
        anthropic_base_url=os.getenv("ANTHROPIC_BASE_URL", ""),
        anthropic_private_model=os.getenv("ANTHROPIC_PRIVATE_MODEL", ""),
        vision_model=os.getenv("VISION_MODEL", ""),
        glm_api_key=os.getenv("GLM_API_KEY", ""),
        glm_base_url=os.getenv("GLM_BASE_URL", ""),
    )

    results: dict[str, list] = defaultdict(list)
    missing: list[str] = []

    for run_i in range(runs):
        print(f"\n=== run {run_i + 1}/{runs} ===")
        for entry in holdout:
            fn = entry["filename"]
            path = STICKERS_DIR / fn
            if not path.exists():
                if run_i == 0:
                    missing.append(fn)
                results[fn].append(None)
                continue
            img_bytes = path.read_bytes()
            # The aesthetic judge returns True (tacky → ban), False (fine), or
            # None (judgment failed). Invert so "approved" = "not tacky".
            verdict_raw = await agent._judge_sticker_aesthetic(img_bytes)
            verdict = (None if verdict_raw is None else (not verdict_raw))
            results[fn].append(verdict)
            print(f"  {fn[:40]:40s} expected={entry['expected_approved']!s:>5s} → {verdict!s}")

    print("\n" + "=" * 72)
    print(f"summary across {runs} runs")
    print("=" * 72)

    tp = fp = fn_ = tn = unstable = judge_fail = 0
    per_image_lines = []
    for entry in holdout:
        fn = entry["filename"]
        expected = entry["expected_approved"]
        verdicts = results[fn]
        true_count = sum(1 for v in verdicts if v is True)
        false_count = sum(1 for v in verdicts if v is False)
        none_count = sum(1 for v in verdicts if v is None)
        majority = (true_count > false_count)
        is_unstable = 2 <= true_count <= (runs - 2) if runs >= 4 else (
            0 < true_count < runs
        )
        if is_unstable:
            unstable += 1
        if none_count == runs:
            judge_fail += 1
        else:
            if expected and majority:
                tp += 1
            elif expected and not majority:
                fn_ += 1
            elif not expected and majority:
                fp += 1
            else:
                tn += 1
        flag = "!" if is_unstable else " "
        per_image_lines.append(
            f"  {flag} {fn[:38]:38s} expected={expected!s:>5s} "
            f"true={true_count}/{runs} false={false_count}/{runs} "
            f"none={none_count}/{runs}"
        )

    print("\n".join(per_image_lines))
    print()
    if missing:
        print(f"[!] {len(missing)} files not found in {STICKERS_DIR}:")
        for m in missing[:10]:
            print(f"    - {m}")
        if len(missing) > 10:
            print(f"    ... +{len(missing) - 10} more")
        print()

    total = tp + fp + fn_ + tn
    if total == 0:
        print("no judgments to score (all missing or all failed)")
        return
    print(f"confusion matrix (n={total}):")
    print(f"                  predicted_approved  predicted_rejected")
    print(f"  actual_approved {tp:>18d}  {fn_:>18d}")
    print(f"  actual_rejected {fp:>18d}  {tn:>18d}")
    accuracy = (tp + tn) / total
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn_, 1)
    print(f"\naccuracy:  {accuracy:.1%}  ({tp + tn}/{total})")
    print(f"precision: {precision:.1%}  (when the model approves, how often it's right)")
    print(f"recall:    {recall:.1%}  (of truly-approved images, how many were caught)")
    print(f"\nstability: {unstable}/{total} images flipped at least once across {runs} runs")
    if judge_fail:
        print(f"judge fail: {judge_fail} images returned None on every run "
              f"(API/parse error — check vision_model and credentials)")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--file", type=Path, default=ROOT / "holdout.jsonl",
                   help="path to holdout jsonl (default: ./holdout.jsonl)")
    p.add_argument("--runs", type=int, default=5,
                   help="how many times to judge each image (default 5)")
    args = p.parse_args()
    asyncio.run(main(args.file, args.runs))
