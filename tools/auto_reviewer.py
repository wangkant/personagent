"""tools/auto_reviewer.py — eval 低分自动诊断 + feedback 草稿生成

把 Hermes 闭环的"看 eval 低分 → 想该加什么约束 → 写 BAD/OK 配对"这步半自动化。

Workflow:
    python tools/auto_reviewer.py [--threshold 3] [--limit 20] [--dry-run]

读 eval.jsonl, 找 score ≤ threshold 的回复, 让 reviewer LLM 输出:
    1. 失败模式分类 (2-6 字标签)
    2. 一句话诊断 (具体哪儿不像真人)
    3. 建议补到哪个 tag (style / reasoning / intent_rules)
    4. 具体一行负向约束 (按 STYLE_GUIDE 错『...』对『...』格式)
    5. BAD/OK pair 草稿 (准备加进 feedback.jsonl)

输出到 candidates.jsonl, 人工 review 后把 approved 行复制进 feedback.jsonl。
Idempotent: 同一条 eval 不会重复诊断。
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
# deepseek-chat is known to return clean JSON for this prompt shape;
# v4-flash sometimes returns empty content via the anthropic endpoint.
# Override via REVIEWER_MODEL env if you want a different one.
REVIEWER_MODEL = os.getenv("REVIEWER_MODEL", "deepseek-chat")

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s",
                    datefmt="%H:%M:%S")
logger = logging.getLogger("auto-reviewer")


REVIEWER_PROMPT = """你是 LLM persona-agent 提示词工程师。下面是一个 QQ 群 persona chatbot 一次得分低的回复样本，诊断 AI 味问题 + 给出修复草稿。

[原始数据]
模式: {mode}
用户消息: {user_msg}
bot 回复: {reply}
评分: {score}/5
低分原因: {reason}

[严格按 JSON 一行输出，不要 markdown 包裹，所有字段必填]
{{"failure_mode":"<2-6 字标签，如：客服腔/分析腔/喊名字/列点/句号多/称呼过频/张冠李戴/抢答/解释腔>","bad_diagnosis":"<一句话讲具体哪儿不像真人>","tag_to_patch":"<style 或 reasoning 或 intent_rules 三选一>","constraint_to_add":"<一行负向约束，写法仿『错『...』 对『...』』给具体反例>","pair_draft":{{"scenario":"<场景短标签>","context":["<上下文 1-2 行>"],"mode":"<owner|called|followup|judge 之一>","reply":"<原 BAD 回复，照抄>","better":"<改写成像真人的版本>"}}}}"""


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
    # Strip ``` fences if model wrapped it despite instruction
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
                   help="score <= threshold 的算低分 (default 3)")
    p.add_argument("--limit", type=int, default=20,
                   help="单次最多诊断多少条 (default 20)")
    p.add_argument("--dry-run", action="store_true",
                   help="只打印不写文件")
    args = p.parse_args()

    if not ANTHROPIC_API_KEY:
        logger.error("ANTHROPIC_API_KEY 未配置，无法调 reviewer")
        return 1

    evals = load_evals(EVAL_FILE, args.threshold)
    seen = load_existing_candidates(CANDIDATES_FILE)
    pending = [e for e in evals if e.get("ts") not in seen][: args.limit]

    logger.info(
        "eval 低分 (score≤%d): %d 条；已诊断: %d；本轮处理: %d；reviewer=%s",
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
        "完成: %d/%d 条已写入 %s",
        written, len(pending),
        "stdout (dry-run)" if args.dry_run else CANDIDATES_FILE.name,
    )
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
