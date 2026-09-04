"""Self-evolution core — the negative half of the learning loop.

The positive half already runs in-process: every delivered reply can be
self-scored (eval.jsonl), with top scores recorded as weak evidence and a
positive-example candidate. Self-scoring alone never grants retrieval
authority.

This module owns the shared logic for the negative half:

    low-score eval entry
      -> LLM diagnosis (failure mode + a BAD/OK pair draft)
      -> candidates.jsonl (audit trail, dedup by src_eval_ts)
      -> approved pairs appended to runtime/feedback.<lang>.jsonl
      -> the running agent hot-reloads feedback into few-shot retrieval

Consumers:
- tools/auto_reviewer.py   offline CLI; human-gated (--apply); --yes is refused
- agent.Agent.loop_evolve  opt-in background loop (EVOLVE_AUTO=true)

Pure logic only: no env reads, no LLM client — callers pass an async
``call_llm(prompt) -> str`` so the CLI and the agent can reuse their own
transport (retry / fallback / throttling included).
"""
from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

from .paths import read_jsonl
from .textproc import strip_json_fences

from .storage import append_jsonl_unlocked, append_lock, atomic_write_text

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

# Stamped onto evidence produced by REVIEWER_PROMPTS; bump on meaning changes
# (see reactions.ADJUDICATOR_VERSION).
REVIEWER_VERSION = "self-reviewer/1"

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
    raw = strip_json_fences(raw)
    try:
        diag = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(diag, dict) or not isinstance(diag.get("pair_draft"), dict):
        return None
    for key in ("failure_mode", "bad_diagnosis", "tag_to_patch",
                "constraint_to_add"):
        if not isinstance(diag.get(key), str):
            return None
    pd = diag["pair_draft"]
    for key in ("scenario", "mode", "reply", "better"):
        if not isinstance(pd.get(key), str):
            return None
    context = pd.get("context")
    if not isinstance(context, list) or not all(
            isinstance(line, str) for line in context):
        return None
    return diag


def load_evals(path: Path, threshold: int) -> list[dict]:
    """Eval entries with score <= threshold, in file order."""
    out: list[dict] = []
    for r in read_jsonl((path,)):
        try:
            score = int(r.get("score", 5))
        except (TypeError, ValueError):
            continue
        if score <= threshold:
            out.append(r)
    return out


def load_reviewed_ts(path: Path) -> set[str]:
    """src_eval_ts of every candidate ever written — the review dedup set."""
    return {r["src_eval_ts"] for r in read_jsonl((path,)) if r.get("src_eval_ts")}


def load_pending_candidates(path: Path) -> list[dict]:
    """Candidates not yet approved/rejected (no 'applied' verdict)."""
    return [r for r in read_jsonl((path,)) if not r.get("applied")]


def candidate_record(ev: dict, diag: dict, applied: str = "") -> dict:
    rec = {
        "src_eval_ts": ev.get("ts"),
        "src_score": ev.get("score"),
        "src_mode": ev.get("mode"),
        "src_reply": ev.get("reply"),
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
    source_reply = cand.get("src_reply")
    if not isinstance(source_reply, str) or reply != source_reply.strip():
        return None
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


def load_feedback_keys(paths: Path | Iterable[Path]) -> set[tuple[str, str]]:
    """(reply, better) of every existing feedback pair — the apply dedup set."""
    if isinstance(paths, Path):
        paths = (paths,)
    return {
        (str(r.get("reply") or "").strip(), str(r.get("better") or "").strip())
        for path in paths
        for r in read_jsonl((path,))
    }


def _encoded_len(rec: dict) -> int:
    """Bytes one record will occupy on disk, matching append_jsonl_unlocked's
    compact encoding plus its newline. Used for the size budget only."""
    return len(json.dumps(
        rec, ensure_ascii=False, separators=(",", ":")).encode("utf-8")) + 1


def append_jsonl(path: Path, records: list[dict],
                 max_bytes: int = FEEDBACK_MAX_BYTES) -> int:
    """Append records; returns how many were written. Refuses past max_bytes
    so an unattended loop can't grow a curated dataset without bound."""
    if not records:
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    # One lock for the whole batch. The agent (learning.py) and
    # tools/auto_reviewer.py both append to candidates.jsonl, and the previous
    # bare open("a") lost records outright: on Windows O_APPEND is
    # seek-to-end-then-write rather than an atomic append, so two writers
    # silently overwrite each other. append_jsonl_unlocked also fsyncs and
    # repairs a missing trailing newline, which this used to do by hand.
    with append_lock(path):
        try:
            size = path.stat().st_size if path.exists() else 0
        except OSError:
            size = 0
        for rec in records:
            if size + _encoded_len(rec) > max_bytes:
                break
            size += append_jsonl_unlocked(path, rec)
            written += 1
    return written


def trim_pool(path: Path, *, max_auto: int, slack: int | None = None,
              is_auto=lambda r: True) -> tuple[int, int] | None:
    """Cap the machine-generated half of a growing retrieval dataset.

    examples.jsonl / feedback.jsonl are scanned on the reply hot path but only
    ever surface a handful of entries per turn (top-4 examples, top-6 pairs),
    so an unbounded pool buys nothing. It costs a longer relevance scan, and —
    the part that actually matters — it lets months-old auto-banked entries,
    written under an older prompt and waved through by a self-eval that grades
    generously, pile up and outvote the newer ones. Keeping the newest
    `max_auto` machine entries makes retrieval track the persona as it is now.

    Hand-curated entries are NEVER dropped: `is_auto` is what tells them apart
    (examples carry a "score", machine feedback pairs carry a "src"), and the
    curated head is the bootstrap pool a fresh checkout retrieves from.

    Rewrites only once the overshoot exceeds `slack` (default 10% of the cap),
    so a pool sitting at the cap doesn't rewrite the whole file on every single
    append — the auto count therefore oscillates in [max_auto, max_auto+slack]
    rather than pinning to max_auto exactly. Atomic (tmp + replace). Returns
    (before, after) auto counts if it rewrote, else None — including when
    there is nothing to do or max_auto <= 0 (no cap).
    """
    if max_auto <= 0 or not path.exists():
        return None
    if slack is None:
        slack = max(8, max_auto // 10)
    # Called on every append but rewrites once per `slack` of them, so decide
    # without parsing: the auto count can never exceed the line count. (A file
    # missing its final newline undercounts by one, which only ever defers a
    # trim to the next append.)
    try:
        with path.open("rb") as fh:
            if fh.read().count(b"\n") <= max_auto + max(0, slack):
                return None
    except OSError:
        return None
    # Read and replace under the same lock appenders take: this is a
    # read-modify-write of the whole file, so any row appended between the
    # read and the atomic replace would be discarded with no trace.
    with append_lock(path):
        records = read_jsonl((path,))
        auto_at = [i for i, r in enumerate(records) if is_auto(r)]
        if len(auto_at) <= max_auto + max(0, slack):
            return None
        dropped = set(auto_at[:len(auto_at) - max_auto])
        kept = [r for i, r in enumerate(records) if i not in dropped]
        atomic_write_text(
            path,
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in kept),
        )
    return len(auto_at), len(auto_at) - len(dropped)


def mark_candidates(path: Path, verdicts: dict[str, str]) -> None:
    """Stamp 'applied' verdicts ('approved'/'rejected'/'auto') onto candidates,
    keyed by src_eval_ts. Atomic rewrite (tmp + replace)."""
    if not verdicts or not path.exists():
        return
    # Read-modify-write of the whole candidates file while the agent may be
    # appending to it: without the lock, every row written between the read
    # and the replace is silently dropped.
    with append_lock(path):
        records = read_jsonl((path,))
        for r in records:
            ts = r.get("src_eval_ts")
            if ts in verdicts and not r.get("applied"):
                r["applied"] = verdicts[ts]
        atomic_write_text(
            path,
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records),
        )
