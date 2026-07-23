"""Learn from real user reactions — the primary self-evolution signal.

The LLM self-eval channel (eval.jsonl -> EVOLVE_AUTO) scores generously, so
its negative half rarely fires. Real users, by contrast, tell the bot
directly: "no, I meant X" is a correction with the right answer inside it;
laughing and riffing is proof a reply landed. Reading a *reaction relative to
a reply* is a far easier LLM task than scoring human-likeness — that is why
this channel works where score-based eval stalls.

Pure logic only (no I/O, no clock reads — callers pass timestamps):

- ``PendingReplies``    bounded per-conversation table of recently sent bot
                        replies awaiting a reaction (record / match / expire,
                        one-shot pop so each reply learns at most once)
- prompt builders       single adjudicator call: classify the reaction,
                        judge genuineness (owner-weighted), draft the rewrite
- ``parse_adjudication``fail-closed JSON parse
- ``to_feedback_pair`` / ``to_example``  write-shapes for the existing
                        feedback / examples pipelines
"""
from __future__ import annotations

import json
import re
from collections import defaultdict, deque

REACTION_TYPES = {"correction", "rejection", "positive", "neutral"}

ADJUDICATOR_PROMPTS = {
    "en": """You are the self-review module of a group-chat persona bot named {bot_name}. The bot sent a reply, and a user reacted to it. Decide what the reaction means and whether the bot should learn from it.

[chat context before the bot's reply]
{context}

[the bot's reply]
{reply}

[the reaction]
{reactor}: {reaction_text}

Reactor identity: {reactor_role}.

Classify the reaction:
- "correction" — the user says the reply was wrong AND states or implies the right direction ("no, I meant X", "that's not what I asked, I wanted Y")
- "rejection" — the user says it was wrong/off/didn't land, or re-asks the same thing in other words, without giving the right answer
- "positive" — the user laughs, agrees, plays along, builds on the reply
- "neutral" — anything else (new topic, unrelated, mere acknowledgement)

Then judge whether to LEARN from it (accept):
- Owner corrections: accept unless it is clearly banter/teasing rather than a real correction.
- Non-owner corrections: accept only if the correction is self-evidently right given the context (protect the bot from trolling / being taught wrong).
- rejection: accept only if the bot's reply really does misread the context.
- positive: accept only if it is a genuine positive reaction to THIS reply (not sarcasm) and the reply is worth imitating.
- When in doubt, accept=false.

If accepting a correction/rejection, write "better": how the bot SHOULD have replied — in the bot's own casual voice, short, no assistant tone, satisfying the user's actual intent. Otherwise "better" is "".

Output ONE line of JSON only, no markdown fences:
{{"reaction":"correction|rejection|positive|neutral","accept":true|false,"reason":"<one short sentence>","better":"<improved reply or empty>","scenario":"<2-5 word scene label>"}}""",
    "zh": """你是群聊人设 bot「{bot_name}」的自审模块。bot 发了一条回复,有用户对它作出了反应。判断这个反应的含义,以及 bot 是否应该从中学习。

[bot 回复前的聊天上下文]
{context}

[bot 的回复]
{reply}

[用户的反应]
{reactor}: {reaction_text}

反应者身份: {reactor_role}。

先给反应分类:
- "correction" — 用户说回复错了并且说出/暗示了正确方向(「不是,我是说X」「我问的不是这个,我想要Y」)
- "rejection" — 用户说不对/没懂/答非所问,或换个说法把同一件事又问了一遍,但没给正确答案
- "positive" — 用户笑了、认同、接梗、顺着聊下去
- "neutral" — 其他(换话题、无关、单纯敷衍)

再判断要不要学(accept):
- owner 的纠正: 除非明显是在开玩笑/调侃,否则采信。
- 非 owner 的纠正: 只有结合上下文一眼就能看出用户说得对才采信(防止被恶意教坏)。
- rejection: 只有 bot 的回复确实读错了语境才采信。
- positive: 只有确定是对这条回复的真心正向反应(不是阴阳怪气)、且这条回复值得模仿才采信。
- 拿不准就 accept=false。

如果采信 correction/rejection,写出 "better": bot 当时应该怎么回——用 bot 自己的口语人设、简短、没有助手腔、满足用户真实意图。否则 "better" 留空。

只输出一行 JSON,不要 markdown 包裹:
{{"reaction":"correction|rejection|positive|neutral","accept":true|false,"reason":"<一句短话>","better":"<改进后的回复或空>","scenario":"<2-6字场景标签>"}}""",
}


class PendingReplies:
    """Recently sent bot replies awaiting a user reaction.

    Per-conversation deque, size-capped; entries expire after ``ttl_sec``.
    A successful match POPS the entry — each reply learns at most once.
    """

    def __init__(self, max_per_conv: int = 4, ttl_sec: float = 900.0):
        self.max_per_conv = max_per_conv
        self.ttl_sec = ttl_sec
        self._by_conv: dict[str, deque] = defaultdict(
            lambda: deque(maxlen=self.max_per_conv))

    def record(self, conv_id: str, *, reply: str, ctx_lines: list[str],
               mode: str, intent: str = "", target_uid: str = "",
               target_name: str = "", mids: list[str] | None = None,
               ts: float = 0.0) -> None:
        reply = (reply or "").strip()
        if not reply or reply.upper() == "PASS":
            return
        self._by_conv[conv_id].append({
            "reply": reply,
            "ctx_lines": list(ctx_lines or [])[-4:],
            "mode": mode,
            "intent": intent,
            "target_uid": str(target_uid or ""),
            "target_name": target_name or "",
            "mids": [str(m) for m in (mids or [])],
            "ts": ts,
        })

    def _expire(self, conv_id: str, now: float) -> None:
        q = self._by_conv.get(conv_id)
        if not q:
            return
        while q and now - q[0]["ts"] > self.ttl_sec:
            q.popleft()

    def match(self, conv_id: str, *, sender_uid: str, quote_mid: str = "",
              at_bot: bool = False, is_private: bool = False,
              now: float = 0.0) -> dict | None:
        """Attribute an incoming message to a pending bot reply, or None.

        Precision-first (locked in design): group messages count only when
        they quote a pending bot message or @ the bot; private chat counts
        when the interlocutor speaks again within the TTL.
        A match pops the entry (one-shot).
        """
        self._expire(conv_id, now)
        q = self._by_conv.get(conv_id)
        if not q:
            return None
        if quote_mid:
            qm = str(quote_mid)
            for i in range(len(q) - 1, -1, -1):
                if qm in q[i]["mids"]:
                    entry = q[i]
                    del q[i]
                    return entry
            # A quote of a non-pending (older / foreign) message is not a
            # reaction to anything we track — do NOT fall through to @-logic:
            # the quote already names its target.
            return None
        if at_bot or (is_private and str(sender_uid) == q[-1]["target_uid"]):
            return q.pop()
        return None


def build_adjudicator_prompt(entry: dict, reaction_text: str, reactor_name: str,
                             is_owner: bool, bot_name: str, lang: str) -> str:
    tmpl = ADJUDICATOR_PROMPTS.get(lang, ADJUDICATOR_PROMPTS["en"])
    if lang == "zh":
        role = "owner(bot 最信任的人)" if is_owner else "普通群友"
    else:
        role = ("the OWNER (the person the bot trusts most)" if is_owner
                else "a regular group member")
    return tmpl.format(
        bot_name=bot_name or "bot",
        context="\n".join(entry.get("ctx_lines") or []) or "(none)",
        reply=entry.get("reply", ""),
        reactor=reactor_name or "user",
        reaction_text=(reaction_text or "")[:300],
        reactor_role=role,
    )


def parse_adjudication(raw: str) -> dict | None:
    """Fail-closed parse of the adjudicator's one-line JSON."""
    raw = (raw or "").strip()
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.MULTILINE).strip()
    try:
        d = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(d, dict) or d.get("reaction") not in REACTION_TYPES:
        return None
    d["accept"] = bool(d.get("accept"))
    d["better"] = str(d.get("better") or "").strip()
    d["scenario"] = str(d.get("scenario") or "").strip()
    d["reason"] = str(d.get("reason") or "").strip()
    return d


def to_feedback_pair(entry: dict, adj: dict, ts: str,
                     reactor_name: str = "") -> dict | None:
    """Accepted correction/rejection -> a feedback.jsonl preference pair.

    None when unusable (no rewrite, or rewrite == original). Matches the
    agent loader contract: rating == 'better', non-empty reply and better.
    """
    if adj.get("reaction") not in ("correction", "rejection") or not adj.get("accept"):
        return None
    reply = str(entry.get("reply") or "").strip()
    better = adj.get("better", "")
    if not reply or not better or reply == better:
        return None
    return {
        "ts": ts,
        "scenario": adj.get("scenario") or f"user-corrected:{entry.get('mode', '')}",
        "context": list(entry.get("ctx_lines") or [])[:4],
        "mode": entry.get("mode", "called"),
        "reply": reply,
        "rating": "better",
        "better": better,
        "src": "user_reaction",
        "reactor": reactor_name,
    }


def to_example(entry: dict, adj: dict, ts: str) -> dict | None:
    """Accepted positive reaction -> an examples.jsonl entry (proven reply)."""
    if adj.get("reaction") != "positive" or not adj.get("accept"):
        return None
    reply = str(entry.get("reply") or "").strip()
    if not reply or reply.upper() == "PASS":
        return None
    mode = entry.get("mode", "called")
    intent = entry.get("intent", "")
    return {
        "ts": ts,
        "scenario": adj.get("scenario") or (f"{mode}:{intent}" if intent else mode),
        "mode": mode,
        "intent": intent,
        "context": list(entry.get("ctx_lines") or [])[:4],
        "reply": reply,
        "score": 5,
        "src": "user_reaction",
    }
