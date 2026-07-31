"""Diagnose low-score eval entries and close the feedback loop.

Stage 1 (review): score<=threshold entries in eval.jsonl are diagnosed by an
LLM into candidates.jsonl (failure mode + constraint + a BAD/OK pair draft).

Stage 2 (apply, opt-in): pending candidates are converted into preference
pairs and appended to runtime/feedback.<lang>.jsonl, which the running agent
hot-reloads into few-shot retrieval — no restart needed.

Usage:
    python tools/auto_reviewer.py                     # review only (as before)
    python tools/auto_reviewer.py --apply             # review, then y/n/e gate
    python tools/auto_reviewer.py --yes               # refused: unsafe legacy mode
    python tools/auto_reviewer.py --dry-run           # print diagnoses only

Uses the same OpenAI-compatible endpoint as the agent (DEEPSEEK_API_KEY /
DEEPSEEK_BASE_URL); REVIEWER_MODEL falls back to EVAL_MODEL, then the chat
model.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=False)

import httpx

from persona_agent import evolution
from persona_agent.paths import (
    resolve_runtime_lang_file,
    resolve_runtime_state_file,
    resolve_seed_lang_file,
)


def _runtime_file(value: str) -> Path:
    return resolve_runtime_state_file(value)


EVAL_FILE = _runtime_file(os.getenv("EVAL_FILE", "eval.jsonl"))
CANDIDATES_FILE = resolve_runtime_state_file("candidates.jsonl")

API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
BASE_URL = (os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")).rstrip("/")
REVIEWER_MODEL = (
    os.getenv("REVIEWER_MODEL", "")
    or os.getenv("EVAL_MODEL", "")
    or os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
)
AGENT_LANG = os.getenv("AGENT_LANG", "en").strip().lower()
# Keep the newest N machine-generated pairs (0 = no cap) — mirrors the running
# agent so both writers converge on the same pool size.
FEEDBACK_MAX_AUTO = int(os.getenv("FEEDBACK_MAX_AUTO", 500) or 0)

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s",
                    datefmt="%H:%M:%S")
logger = logging.getLogger("auto-reviewer")

# Windows consoles may default to a legacy codepage; never crash on output.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass


def _feedback_files() -> tuple[Path, Path]:
    return (
        resolve_seed_lang_file("feedback", "jsonl", AGENT_LANG),
        resolve_runtime_lang_file("feedback", "jsonl", AGENT_LANG),
    )


async def call_llm(prompt: str) -> str:
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{BASE_URL}/v1/chat/completions",
            headers={"Authorization": f"Bearer {API_KEY}",
                     "Content-Type": "application/json"},
            json={"model": REVIEWER_MODEL, "max_tokens": 600,
                  "messages": [{"role": "user", "content": prompt}]},
        )
        resp.raise_for_status()
        data = resp.json()
    return (data.get("choices") or [{}])[0].get("message", {}).get("content", "") or ""


async def review_pending(threshold: int, limit: int, dry_run: bool) -> list[dict]:
    """Stage 1: diagnose new low-score evals into candidates.jsonl."""
    evals = evolution.load_evals(EVAL_FILE, threshold)
    seen = evolution.load_reviewed_ts(CANDIDATES_FILE)
    pending = [e for e in evals if e.get("ts") not in seen][:limit]
    logger.info(
        "low-score evals (score<=%d): %d; already reviewed: %d; this run: %d; reviewer=%s",
        threshold, len(evals), len(seen), len(pending), REVIEWER_MODEL,
    )
    if not pending:
        return []
    if not API_KEY:
        logger.error("DEEPSEEK_API_KEY not configured; cannot call reviewer")
        return []

    written: list[dict] = []
    try:
        for ev in pending:
            prompt = evolution.build_review_prompt(ev, AGENT_LANG)
            try:
                raw = await call_llm(prompt)
            except Exception as e:
                logger.warning("reviewer call failed (%s): %s: %s",
                               str(ev.get("ts", "?"))[:19], type(e).__name__, e)
                continue
            diag = evolution.parse_review(raw)
            if not diag:
                logger.warning("reviewer output not JSON (%s): %s ...",
                               str(ev.get("ts", "?"))[:19], raw[:120])
                continue
            record = evolution.candidate_record(ev, diag)
            line = json.dumps(record, ensure_ascii=False)
            if dry_run:
                print(line)
            else:
                # One locked, fsynced append per record instead of a bare
                # long-lived handle. The running agent appends to this same
                # file throughout — that is the documented workflow — and the
                # unlocked handle lost ~25-30% of this run's own diagnoses.
                # Worse, a torn line lands mid-multibyte on Chinese payloads,
                # after which every reader of candidates.jsonl raises
                # UnicodeDecodeError and the negative half of the learning
                # loop stops permanently, including the code that could repair it.
                evolution.append_jsonl(CANDIDATES_FILE, [record])
            written.append(record)
            logger.info("  [%s] %s → %s",
                        str(ev.get("ts", "?"))[:19],
                        diag.get("failure_mode", "?"),
                        str(diag.get("constraint_to_add", ""))[:80])
    finally:
        pass
    logger.info("review done: %d/%d written to %s", len(written), len(pending),
                "stdout (dry-run)" if dry_run else CANDIDATES_FILE.name)
    return written


def apply_candidates(auto_yes: bool) -> None:
    """Stage 2: pending candidates -> feedback pairs, always human-gated."""
    if auto_yes:
        # Model output is not operator authority. Unattended self-review must
        # travel through evidence -> candidate -> promotion in the in-process
        # evolution loop; it may never write a trusted retrieval pool directly.
        logger.error(
            "--yes direct apply is disabled; use EVOLVE_AUTO for gated "
            "unattended review, or --apply for explicit per-pair approval")
        return
    feedback_seed, feedback = _feedback_files()
    pending = evolution.load_pending_candidates(CANDIDATES_FILE)
    if not pending:
        logger.info("apply: no pending candidates")
        return
    existing = evolution.load_feedback_keys([feedback_seed, feedback])
    now = datetime.now().isoformat(timespec="seconds")

    approved: list[dict] = []
    verdicts: dict[str, str] = {}
    for i, cand in enumerate(pending, 1):
        pair = evolution.pair_from_candidate(cand, now)
        ts = cand.get("src_eval_ts") or ""
        if pair is None:
            verdicts[ts] = "rejected"
            logger.info("[%d/%d] unusable pair_draft -> rejected", i, len(pending))
            continue
        if (pair["reply"], pair["better"]) in existing:
            verdicts[ts] = "rejected"
            logger.info("[%d/%d] duplicate of an existing pair -> skipped", i, len(pending))
            continue

        if auto_yes:
            verdict = "y"
        else:
            print(f"\n[{i}/{len(pending)}] {cand.get('failure_mode', '?')} "
                  f"(score {cand.get('src_score', '?')}/5, mode {pair['mode']})")
            print(f"  diagnosis:  {cand.get('bad_diagnosis', '')}")
            print(f"  constraint: {cand.get('constraint_to_add', '')}")
            print(f"  BAD: {pair['reply']}")
            print(f"  OK : {pair['better']}")
            verdict = input("  approve? [y]es / [n]o / [e]dit better / Enter=skip: ").strip().lower()

        if verdict == "e":
            edited = input("  new 'better' text: ").strip()
            if edited:
                pair["better"] = edited
                verdict = "y"
            else:
                verdict = ""
        if verdict == "y":
            approved.append(pair)
            existing.add((pair["reply"], pair["better"]))
            verdicts[ts] = "auto" if auto_yes else "approved"
        elif verdict == "n":
            verdicts[ts] = "rejected"
        # anything else: leave pending for a later run

    # Same auto-pool cap the running agent applies, on the same runtime file
    # (machine pairs carry a "src"; pairs you rated yourself don't and are
    # never dropped, and the data/ seed is never touched), so approving a
    # batch here can't push the pool past what retrieval wants to scan.
    trimmed = evolution.trim_pool(
        feedback, max_auto=FEEDBACK_MAX_AUTO,
        is_auto=lambda r: bool(r.get("src")))
    if trimmed:
        logger.info("feedback auto-pool trimmed: %d -> %d pairs (cap=%d)",
                    trimmed[0], trimmed[1], FEEDBACK_MAX_AUTO)
    n = evolution.append_jsonl(feedback, approved)
    if n < len(approved):
        logger.warning("feedback file at size cap: %d of %d pairs written",
                       n, len(approved))
    evolution.mark_candidates(CANDIDATES_FILE, verdicts)
    logger.info("apply done: %d approved -> %s, %d rejected, %d left pending",
                n, feedback.name,
                sum(1 for v in verdicts.values() if v == "rejected"),
                len(pending) - len(verdicts))


async def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--threshold", type=int, default=3,
                   help="treat score <= threshold as a low-score entry (default 3)")
    p.add_argument("--limit", type=int, default=20,
                   help="max entries to review per run (default 20)")
    p.add_argument("--dry-run", action="store_true",
                   help="print only, do not write candidates.jsonl")
    p.add_argument("--apply", action="store_true",
                   help="after reviewing, interactively approve pairs into feedback")
    p.add_argument("--yes", action="store_true",
                   help="deprecated unsafe mode; refused without writing feedback")
    args = p.parse_args()

    await review_pending(args.threshold, args.limit, args.dry_run)
    if (args.apply or args.yes) and not args.dry_run:
        apply_candidates(auto_yes=args.yes)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
