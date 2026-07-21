"""Self-evolution core — the negative half of the learning loop.

The positive half already runs in-process: every reply is self-scored
(eval.jsonl) and top-scoring replies are auto-appended to
data/examples.<lang>.jsonl, so the few-shot pool grows from real successes.

This module owns the shared logic for the negative half:

    low-score eval entry
      -> LLM diagnosis (failure mode + a BAD/OK pair draft)
      -> candidates.jsonl (audit trail, dedup by src_eval_ts)
      -> approved pairs appended to data/feedback.<lang>.jsonl
      -> the running agent hot-reloads feedback into few-shot retrieval

Consumers:
- tools/auto_reviewer.py   offline CLI; human-gated (--apply) or unattended (--yes)
- agent.Agent.loop_evolve  opt-in background loop (EVOLVE_AUTO=true)

Pure logic only: no env reads, no LLM client — callers pass an async
``call_llm(prompt) -> str`` so the CLI and the agent can reuse their own
transport (retry / fallback / throttling included).
"""
from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path

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

VALID_MODES = {"owner", "called", "followup", "judge"}

# Feedback is a curated dataset, not a log — refuse to grow it unbounded.
FEEDBACK_MAX_BYTES = 5_000_000


def build_review_prompt(ev: dict, lang: str) -> str:
    tmpl = REVIEWER_PROMPTS.get(lang, REVIEWER_PROMPTS["en"])
    return tmpl.format(
        mode=ev.get("mode", "?"),
        user_msg=(ev.get("user_msg") or "")[:200],
        reply=(ev.get("reply") or "")[:300],
        score=ev.get("score", "?"),
        reason=(ev.get("reason") or "")[:200],
    )


def parse_review(raw: str) -> dict | None:
    """Parse the reviewer model's one-line JSON diagnosis. None on garbage."""
    raw = (raw or "").strip()
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.MULTILINE).strip()
    try:
        diag = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(diag, dict) or not isinstance(diag.get("pair_draft"), dict):
        return None
    return diag


def _read_jsonl(path: Path) -> list[dict]:
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
        if isinstance(r, dict):
            out.append(r)
    return out


def load_evals(path: Path, threshold: int) -> list[dict]:
    """Eval entries with score <= threshold, in file order."""
    out: list[dict] = []
    for r in _read_jsonl(path):
        try:
            score = int(r.get("score", 5))
        except (TypeError, ValueError):
            continue
        if score <= threshold:
            out.append(r)
    return out


def load_reviewed_ts(path: Path) -> set[str]:
    """src_eval_ts of every candidate ever written — the review dedup set."""
    return {r["src_eval_ts"] for r in _read_jsonl(path) if r.get("src_eval_ts")}


def load_pending_candidates(path: Path) -> list[dict]:
    """Candidates not yet approved/rejected (no 'applied' verdict)."""
    return [r for r in _read_jsonl(path) if not r.get("applied")]


def candidate_record(ev: dict, diag: dict, applied: str = "") -> dict:
    rec = {
        "src_eval_ts": ev.get("ts"),
        "src_score": ev.get("score"),
        "src_mode": ev.get("mode"),
        **diag,
    }
    if applied:
        rec["applied"] = applied
    return rec


def pair_from_candidate(cand: dict, ts: str) -> dict | None:
    """Convert a candidate's pair_draft into a feedback.jsonl entry.

    Returns None when the draft is unusable (missing sides, or the model
    'rewrote' the reply into itself). The output matches what the agent's
    _reload_pairs_if_stale considers a preference pair: rating == 'better'
    with non-empty reply and better fields.
    """
    pd = cand.get("pair_draft")
    if not isinstance(pd, dict):
        return None
    reply = str(pd.get("reply") or "").strip()
    better = str(pd.get("better") or "").strip()
    if not reply or not better or reply == better:
        return None
    mode = str(pd.get("mode") or "").strip()
    if mode not in VALID_MODES:
        mode = str(cand.get("src_mode") or "called")
    context = pd.get("context")
    if not isinstance(context, list):
        context = [str(context)] if context else []
    return {
        "ts": ts,
        "scenario": str(pd.get("scenario") or cand.get("failure_mode") or "auto-reviewed"),
        "context": [str(c) for c in context][:4],
        "mode": mode,
        "reply": reply,
        "rating": "better",
        "better": better,
        "src": "auto_reviewer",
        "src_eval_ts": cand.get("src_eval_ts"),
    }


def load_feedback_keys(path: Path) -> set[tuple[str, str]]:
    """(reply, better) of every existing feedback pair — the apply dedup set."""
    return {
        (str(r.get("reply") or "").strip(), str(r.get("better") or "").strip())
        for r in _read_jsonl(path)
    }


def append_jsonl(path: Path, records: list[dict],
                 max_bytes: int = FEEDBACK_MAX_BYTES) -> int:
    """Append records; returns how many were written. Refuses past max_bytes
    so an unattended loop can't grow a curated dataset without bound."""
    if not records:
        return 0
    try:
        size = path.stat().st_size if path.exists() else 0
    except OSError:
        size = 0
    written = 0
    with path.open("a", encoding="utf-8", newline="\n") as fh:
        for rec in records:
            line = json.dumps(rec, ensure_ascii=False) + "\n"
            if size + len(line.encode("utf-8")) > max_bytes:
                break
            fh.write(line)
            size += len(line.encode("utf-8"))
            written += 1
    return written


def mark_candidates(path: Path, verdicts: dict[str, str]) -> None:
    """Stamp 'applied' verdicts ('approved'/'rejected'/'auto') onto candidates,
    keyed by src_eval_ts. Atomic rewrite (tmp + replace)."""
    if not verdicts or not path.exists():
        return
    records = _read_jsonl(path)
    for r in records:
        ts = r.get("src_eval_ts")
        if ts in verdicts and not r.get("applied"):
            r["applied"] = verdicts[ts]
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            for r in records:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        os.replace(tmp, path)
    except OSError:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
