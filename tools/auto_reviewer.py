"""Diagnose low-score eval entries and draft feedback patches.

Usage:
    python tools/auto_reviewer.py [--threshold 3] [--limit 20] [--dry-run]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=True)

import anthropic

EVAL_FILE = ROOT / "eval.jsonl"
CANDIDATES_FILE = ROOT / "candidates.jsonl"

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_BASE_URL = os.getenv("ANTHROPIC_BASE_URL", "")
REVIEWER_MODEL = os.getenv("REVIEWER_MODEL", "deepseek-chat")
AGENT_LANG = os.getenv("AGENT_LANG", "en").strip().lower()

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s",
                    datefmt="%H:%M:%S")
logger = logging.getLogger("auto-reviewer")

REVIEWER_PROMPTS = {
    "en": """You are a prompt engineer for an LLM persona agent. Below is one low-scoring reply from a group-chat persona chatbot. Diagnose the "AI tell" and draft a fix.

[raw data]
mode: {mode}
user message: {user_msg}
bot reply: {reply}
score: {score}/5
low-score reason: {reason}

[Output a single line of JSON, no markdown fences, all fields required]
{{"failure_mode":"<2-4 word label, e.g. service-desk tone / analytical tone / name-at-start / bulleted / too many periods / over-addressing / wrong-target / jumped-the-gun / explainer tone>","bad_diagnosis":"<one sentence: exactly what doesn't read like a real person>","tag_to_patch":"<one of: style | reasoning | intent_rules>","constraint_to_add":"<one negative constraint with a concrete counter-example, written as: BAD 'x' -> OK 'y'>","pair_draft":{{"scenario":"<short scene label>","context":["<1-2 context lines>"],"mode":"<one of owner|called|followup|judge>","reply":"<the original BAD reply, copied verbatim>","better":"<rewrite that reads like a real person>"}}}}""",
    "zh": """你是 LLM persona-agent 提示词工程师。下面是一个群 persona chatbot 一次得分低的回复样本，诊断 AI 味问题 + 给出修复草稿。

[原始数据]
模式: {mode}
用户消息: {user_msg}
bot 回复: {reply}
评分: {score}/5
低分原因: {reason}

[严格按 JSON 一行输出，不要 markdown 包裹，所有字段必填]
{{"failure_mode":"<2-6 字标签，如：客服腔/分析腔/喊名字/列点/句号多/称呼过频/张冠李戴/抢答/解释腔>","bad_diagnosis":"<一句话讲具体哪儿不像真人>","tag_to_patch":"<style 或 reasoning 或 intent_rules 三选一>","constraint_to_add":"<一行负向约束，写法仿『错『...』 对『...』』给具体反例>","pair_draft":{{"scenario":"<场景短标签>","context":["<上下文 1-2 行>"],"mode":"<owner|called|followup|judge 之一>","reply":"<原 BAD 回复，照抄>","better":"<改写成像真人的版本>"}}}}""",
}
REVIEWER_PROMPT = REVIEWER_PROMPTS.get(AGENT_LANG, REVIEWER_PROMPTS["en"])

def load_evals(path: Path, threshold: int) -> list[dict]:
    if not path.exists():
        return []
    out: list[dict] = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            r = json.loads(ln)
        except json.JSONDecodeError:
            continue
        try:
            score = int(r.get("score", 5))
        except (TypeError, ValueError):
            continue
        if score <= threshold:
            out.append(r)
    return out

def load_existing_candidates(path: Path) -> set[str]:
    if not path.exists():
        return set()
    seen: set[str] = set()
    for ln in path.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            r = json.loads(ln)
        except json.JSONDecodeError:
            continue
        ts = r.get("src_eval_ts")
        if ts:
            seen.add(ts)
    return seen

async def review_one(client: anthropic.AsyncAnthropic, ev: dict) -> dict | None:
    prompt = REVIEWER_PROMPT.format(
        mode=ev.get("mode", "?"),
        user_msg=(ev.get("user_msg") or "")[:200],
        reply=(ev.get("reply") or "")[:300],
        score=ev.get("score", "?"),
        reason=(ev.get("reason") or "")[:200],
    )
    try:
        resp = await client.messages.create(
            model=REVIEWER_MODEL,
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as e:
        logger.warning("reviewer call failed (%s): %s: %s",
                       ev.get("ts", "?")[:19], type(e).__name__, e)
        return None

    raw = "".join(
        getattr(b, "text", "") for b in resp.content if getattr(b, "text", "")
    ).strip()
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.MULTILINE).strip()

    try:
        diag = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.warning("reviewer output not JSON (%s): %s ... | err=%s",
                       ev.get("ts", "?")[:19], raw[:120], e)
        return None
    return diag

async def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--threshold", type=int, default=3,
                   help="treat score <= threshold as a low-score entry (default 3)")
    p.add_argument("--limit", type=int, default=20,
                   help="max entries to review per run (default 20)")
    p.add_argument("--dry-run", action="store_true",
                   help="print only, do not write candidates.jsonl")
    args = p.parse_args()

    if not ANTHROPIC_API_KEY:
        logger.error("ANTHROPIC_API_KEY not configured; cannot call reviewer")
        return 1

    evals = load_evals(EVAL_FILE, args.threshold)
    seen = load_existing_candidates(CANDIDATES_FILE)
    pending = [e for e in evals if e.get("ts") not in seen][: args.limit]

    logger.info(
        "low-score evals (score<=%d): %d; already reviewed: %d; this run: %d; reviewer=%s",
        args.threshold, len(evals), len(seen), len(pending), REVIEWER_MODEL,
    )
    if not pending:
        return 0

    client = anthropic.AsyncAnthropic(
        api_key=ANTHROPIC_API_KEY,
        base_url=ANTHROPIC_BASE_URL or None,
    )

    written = 0
    fh = None if args.dry_run else open(CANDIDATES_FILE, "a", encoding="utf-8", newline="\n")
    try:
        for ev in pending:
            diag = await review_one(client, ev)
            if not diag:
                continue
            record = {
                "src_eval_ts": ev.get("ts"),
                "src_score": ev.get("score"),
                "src_mode": ev.get("mode"),
                **diag,
            }
            line = json.dumps(record, ensure_ascii=False)
            if args.dry_run:
                print(line)
            else:
                fh.write(line + "\n")
            written += 1
            logger.info(
                "  [%s] %s → %s",
                ev.get("ts", "?")[:19],
                diag.get("failure_mode", "?"),
                diag.get("constraint_to_add", "")[:80],
            )
    finally:
        if fh:
            fh.close()

    logger.info(
        "done: %d/%d written to %s",
        written, len(pending),
        "stdout (dry-run)" if args.dry_run else CANDIDATES_FILE.name,
    )
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
