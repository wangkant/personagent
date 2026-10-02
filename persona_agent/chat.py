"""Try the agent in your terminal: a simulated group chat, no platform needed.

    personagent chat                # or: python try_chat.py in a checkout
    personagent chat --dm           # a one-to-one chat instead of a group
    personagent chat --lang zh      # the Chinese variant
    personagent chat --name Alex    # your display name
    personagent chat --admin        # speak as the configured admin
    personagent chat --trigger 4    # messages before it considers joining in

Every line runs through the functions the live bot runs. A plain line is
ordinary group chat and meets the same speak-or-stay-quiet decision, and the
trial says why when it stays quiet. A line with its name is a call; memory
commands are the bot's own. Reply to it and the reaction is judged and
recorded in the learning ledger. The trial keeps its state in
<runtime>/trial/, apart from the live bot's.
"""
from __future__ import annotations

import argparse
import asyncio
import itertools
import os
import re
import shutil
import sys
import time
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from persona_agent import access, candidates, channels, evidence, home, paths, promotion
from persona_agent.access import ADMIN_MODE
from persona_agent.agent import Agent
from persona_agent.connector import ConnectorSink, current_sink
from persona_agent.decision import GATED_MODES, choose_group_mode, pacing_skip
from persona_agent.settings import AgentSettings
from persona_agent.textproc import (
    TextProcessing,
    _clean_prompt_source,
    _example_field,
    _strip_web_desc,
    _truncate_framed,
)

#: The trial's state folder, under the live runtime directory.
TRIAL_DIR = "trial"
#: The simulated group.
GROUP_ID = "trial"
#: Messages before the trial considers joining in; the live default is 30.
TRIAL_TRIGGER = 4
#: Your account in the trial.
YOU_UID = "2001"

_TEXT = {
    "en": {
        "banner": "personagent chat: {name} in a simulated group (model {model}, {lang})",
        "banner_dm": "personagent chat: a one-to-one chat with {name} (model {model}, {lang})",
        "you_are": 'You are "{you}". A plain line is group chat; put "{name}" in it to call {name}.',
        "you_are_dm": 'You are "{you}". Everything you type goes to {name}.',
        "trigger": ("{name} considers joining in after {n} messages here "
                    "(the live bot waits for {live}; --trigger N)."),
        "state": "What the trial learns stays in {path}, apart from the live bot.",
        "commands": [
            ("/reply <text>", "quote {name}'s last reply"),
            ("/as Name <msg>", "speak as someone else"),
            ("/admin <msg>", "speak once as the admin"),
            ("/why", "why it said its last reply, from the ledger"),
            ("/learned", "what it has learned in this chat"),
            ("/reset", "start over: clear this chat and what the trial learned"),
            ("/quit", "leave"),
        ],
        "no_key": ("No model key yet. Run `personagent init` to choose a model and "
                   "key, or `personagent demo` to watch it work without one."),
        "bye": "bye",
        "reset": "(started over: this chat and what the trial learned are gone)",
        "nothing_to_quote": "(nothing to quote yet: {name} has not replied)",
        "usage_as": "usage: /as Name your message",
        "error": "[error: {error}]",
        "quiet": "({name} stays quiet: {reason})",
        "joins": "({name} joins in: {reason})",
        "below": "not addressed, {count} of {trigger} messages",
        "trigger_count": "{count} of {trigger} messages",
        "first_appearance": "{count} messages and it has not spoken here yet",
        "followup": "it spoke in the last {window} s",
        "gate_pass": "{why}, but the gate model said stay quiet",
        "gate_speak": "{why}, and the gate model said speak",
        "sleep": "it is night where {name} lives (sleep window)",
        "skip": "a random pass; people let some openings go",
        "pass": "the model chose PASS",
        "filter": "the output filter blocked its reply",
        "character": "the character check rejected its reply {raw}",
        "dm_none": "no usable reply came back",
        "model_error": "model error: {error}",
        "learning": "[learning] {text}",
        "judged": "judged: {reaction}, accepted ({strength})",
        "judged_dismissed": "judged: {reaction}, dismissed",
        "and": "; ",
        "then": " - ",
        "retry_ok": "its retry was accepted ({strength})",
        "retry_moved_on": "its retry got a move-on, not a thanks ({strength})",
        "no_verdict": "no verdict: the judge's answer could not be read",
        "blocked_teacher": ("not judged: this person's teaching is mostly dismissed, "
                            "so it is no longer weighed"),
        "promoted": "PROMOTED: {events} events, {strong} strong{chat}",
        "same_chat": ", same chat",
        "held": "held: {why}",
        "rolled_back": "stopped using {n} learned row(s) about that reply",
        "armed": "waiting for your reaction to its retry",
        "nothing": "nothing to learn",
        "why_off": "automatic promotion is off",
        "why_against": "evidence about it disagrees; left for the admin",
        "why_conflict": "a different fix for the same reply exists; left for the admin",
        "why_person": "this kind only a person can approve",
        "why_strong": "{strong} of {need} strong events",
        "why_events": "{events} of {need} agreeing events",
        "why_speakers": "{speakers} of {need} different people",
        "why_head": 'why {name} said "{reply}":',
        "why_none": "nothing to explain yet: {name} has not replied",
        "why_named": "  answered {who}: named",
        "why_admin": "  answered {who}: the admin named it",
        "why_joined": "  joined in after {who}: {reason}",
        "why_memory": "  a memory command from {who}, no model call",
        "why_dm": "  answered {who} in a one-to-one chat",
        "why_retry": '  it is its retry for "{text}"',
        "why_prompt_none": "  learned material in its prompt: none",
        "why_prompt": "  learned material in its prompt:",
        "why_ledger_none": ("  the ledger has nothing about it yet; reply with its "
                            "name, or /reply, to teach it"),
        "why_ledger": "  the ledger:",
        "kind_pair": "fix",
        "kind_example": "example",
        "states": {},
        "reactions": {},
        "strengths": {"strong": "strong", "negative_only": "negative only",
                      "weak": "weak"},
    },
    "zh": {
        "banner": "personagent chat：模拟群聊里的{name}（模型 {model}，{lang}）",
        "banner_dm": "personagent chat：和{name}私聊（模型 {model}，{lang}）",
        "you_are": "你是「{you}」。普通的一句话就是群聊；带上「{name}」就是在叫它。",
        "you_are_dm": "你是「{you}」。你说的每句话都发给{name}。",
        "trigger": "这里{name}攒够 {n} 条消息才考虑插话（正式运行时是 {live} 条；--trigger N 可改）。",
        "state": "试用里学到的东西存在 {path}，和正式运行的 bot 分开。",
        "commands": [
            ("/reply <内容>", "引用{name}的上一条回复"),
            ("/as 名字 <消息>", "换一个人说话"),
            ("/admin <消息>", "以管理员身份说一句"),
            ("/why", "它上一条回复的来由（看账本）"),
            ("/learned", "它在这个聊天里学到了什么"),
            ("/reset", "从头来：清空聊天和试用里学到的东西"),
            ("/quit", "退出"),
        ],
        "no_key": ("还没有配置模型密钥。运行 `personagent init` 选择模型并填写密钥；"
                   "也可以先运行 `personagent demo`，不用密钥就能看效果。"),
        "bye": "再见",
        "reset": "（已从头开始：这个聊天和试用里学到的东西都清空了）",
        "nothing_to_quote": "（还没有可引用的：{name}还没回复过）",
        "usage_as": "用法：/as 名字 你的消息",
        "error": "[出错：{error}]",
        "quiet": "（{name}没说话：{reason}）",
        "joins": "（{name}插话：{reason}）",
        "below": "没被点名，{count}/{trigger} 条消息",
        "trigger_count": "攒够 {count}/{trigger} 条消息",
        "first_appearance": "已经 {count} 条消息，它在这里还没说过话",
        "followup": "它 {window} 秒内刚说过话",
        "gate_pass": "{why}，但判断模型认为不该开口",
        "gate_speak": "{why}，判断模型认为该开口",
        "sleep": "{name}那边是深夜（睡眠时段）",
        "skip": "随机跳过；人也不是每次都接话",
        "pass": "模型选择了 PASS",
        "filter": "输出过滤器拦下了回复",
        "character": "回复没通过字符校验 {raw}",
        "dm_none": "没有拿到能发出的回复",
        "model_error": "模型出错：{error}",
        "learning": "[学习] {text}",
        "judged": "判定：{reaction}，采信（{strength}）",
        "judged_dismissed": "判定：{reaction}，不采信",
        "and": "；",
        "then": "，",
        "retry_ok": "它的重试被接受了（{strength}）",
        "retry_moved_on": "对重试没表态，只是聊别的了（{strength}）",
        "no_verdict": "没有判定：判定模型的回答读不出来",
        "blocked_teacher": "不判定：此人教的东西大多被驳回，已不再考虑",
        "promoted": "已生效：{events} 条证据，{strong} 条强证据{chat}",
        "same_chat": "，同一个聊天",
        "held": "暂不生效：{why}",
        "rolled_back": "停用了 {n} 条关于那条回复的学习结果",
        "armed": "等你对它的重试作出反应",
        "nothing": "没有可学的",
        "why_off": "自动生效已关闭",
        "why_against": "关于它的证据互相矛盾，留给管理员",
        "why_conflict": "同一条回复已有另一种改法，留给管理员",
        "why_person": "这类只能由人来批准",
        "why_strong": "强证据 {strong}/{need}",
        "why_events": "一致证据 {events}/{need}",
        "why_speakers": "不同的人 {speakers}/{need}",
        "why_head": "{name}说「{reply}」的来由：",
        "why_none": "还没什么可解释的：{name}还没回复过",
        "why_named": "  回答{who}：被点了名",
        "why_admin": "  回答{who}：管理员点了名",
        "why_joined": "  在{who}之后插话：{reason}",
        "why_memory": "  {who}的记忆指令，没调用模型",
        "why_dm": "  私聊回答{who}",
        "why_retry": "  这是它对「{text}」的重试",
        "why_prompt_none": "  提示词里的学习结果：无",
        "why_prompt": "  提示词里的学习结果：",
        "why_ledger_none": "  账本里还没有关于它的记录；带上它的名字或用 /reply 回复它，就能教它",
        "why_ledger": "  账本：",
        "kind_pair": "改写",
        "kind_example": "范例",
        "states": {"proposed": "待定", "promoted": "已生效", "rejected": "已驳回",
                   "rolled_back": "已撤销", "superseded": "已替换"},
        "reactions": {"correction": "纠正", "rejection": "否定",
                      "positive": "正面", "neutral": "中性"},
        "strengths": {"strong": "强", "negative_only": "仅否定", "weak": "弱"},
    },
}


def text_for(lang: str) -> dict:
    return _TEXT.get(lang, _TEXT["en"])


def clip(text, width: int = 40) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= width else text[:width - 3] + "..."


# ---------------------------------------------------------------------------
# What a turn and a reaction did
# ---------------------------------------------------------------------------

@dataclass
class Checklist:
    """The promotion rules for one candidate, and where each stands.

    Counted with the policy's own functions; the verdict is the policy's."""

    events: int
    need_events: int
    strong: int
    need_strong: int
    can_be_strong: bool
    speakers: int
    need_speakers: int
    speakers_ok: bool
    same_chat: bool
    against: list
    conflicts: list
    auto: bool
    decision: promotion.Decision

    def waiting_for(self) -> str:
        """The first rule that holds it back, in the order the policy checks."""
        if not self.auto:
            return "why_off"
        if self.against:
            return "why_against"
        if self.conflicts:
            return "why_conflict"
        if self.strong < self.need_strong:
            return "why_strong" if self.can_be_strong else "why_person"
        if self.events < self.need_events:
            return "why_events"
        if not self.speakers_ok:
            return "why_speakers"
        return ""


def checklist(agent: Agent, cand: dict) -> Checklist:
    policy = agent.promotion_policy
    log = agent.evidence_log
    now = time.time()
    max_age = policy.max_evidence_age_days * 86400.0
    supporting = [
        e for e in log.many(cand.get("evidence") or [])
        if promotion.supports_candidate(e, cand, policy=policy)
        and not (max_age > 0 and now - promotion.epoch(e.get("ts")) > max_age)]
    strong = [e for e in supporting
              if evidence.classify_strength(e) == evidence.STRONG]
    speakers = {str(e.get("speaker_id") or "") for e in supporting} - {""}
    admins = {str(a).strip()[:64] for a in agent._admins()} - {""}
    related = promotion.related_events(cand, log.all())
    if cand.get("state") == candidates.STATE_PROPOSED:
        decision = agent._decide_promotion(cand["candidate_id"])
    else:
        history = cand.get("history") or [{}]
        decision = promotion.Decision(
            cand.get("state") == candidates.STATE_PROMOTED,
            str(history[-1].get("reason") or ""), len(supporting), len(strong))
    return Checklist(
        events=len(supporting), need_events=policy.min_events,
        strong=len(strong), need_strong=policy.min_strong,
        can_be_strong=evidence.can_be_strong(str(cand.get("type") or "")),
        speakers=len(speakers), need_speakers=policy.min_speakers,
        speakers_ok=(not speakers or bool(admins & speakers)
                     or len(speakers) >= policy.min_speakers),
        same_chat=policy.require_same_conversation,
        against=promotion.counter_evidence(cand, related, now=now, policy=policy),
        conflicts=promotion.find_conflicts(cand, agent.candidate_ledger.all(),
                                           policy=policy, related_events=related),
        auto=policy.auto_promote, decision=decision)


@dataclass
class Reaction:
    """What one reaction to a bot reply did to the ledger."""

    reply: str
    target: str
    events: list
    blocked: bool = False
    promoted: list = field(default_factory=list)   # (candidate, Checklist)
    held: list = field(default_factory=list)       # (candidate, Checklist)
    rolled_back: int = 0
    armed: bool = False


@dataclass
class Turn:
    """What one message did."""

    speaker: str
    uid: str
    text: str
    reply: str = ""
    mode: str = ""
    why: str = ""
    count: int = 0
    trigger: int = 0
    window: int = 0
    #: Why it stayed quiet, a key into the text table; "" when it spoke.
    quiet: str = ""
    raw: str = ""
    error: str = ""
    memory: bool = False
    memory_saved: bool = False
    reaction: Reaction | None = None
    retry_of: str = ""
    offered: list = field(default_factory=list)


def _awaiting_fix(agent: Agent, conv: str) -> dict | None:
    """The rejected reply the bot's next reply in `conv` will be a retry for."""
    return agent.pending_reactions.awaiting(conv)


def _names_bot(agent: Agent, text: str) -> bool:
    """The live name-call test (turns.py), so the trial calls when it would."""
    return agent._names_me(text)


# ---------------------------------------------------------------------------
# The trial: one conversation driven through the bot's own turn functions
# ---------------------------------------------------------------------------

class Trial:
    """Feeds lines to an Agent the way the live intake does, step for step,
    and reports what each decision was and why. Nothing is sent anywhere:
    the reply is shown instead of delivered."""

    def __init__(self, agent: Agent, *, conv: str = GROUP_ID, dm: bool = False,
                 factory: Callable[[], Agent] | None = None,
                 state_dir: Path | None = None) -> None:
        self.conv = conv
        self.dm = dm
        self.factory = factory
        self.state_dir = state_dir
        self.last: Turn | None = None
        self.last_mid = ""
        self._mids = itertools.count(1)
        self._gate_verdict: bool | None = None
        self._attach(agent)

    def _attach(self, agent: Agent) -> None:
        self.agent = agent
        gate = agent._gate

        async def observed_gate(prompt):
            # Read the verdict, change nothing: from outside the turn a quiet
            # gate and a PASS from the reply model look the same.
            speak, intent = await gate(prompt)
            self._gate_verdict = speak
            return speak, intent
        agent._gate = observed_gate

    async def reset(self) -> None:
        """Forget this chat and everything the trial learned."""
        await self.agent.aclose()
        if self.state_dir is not None and self.state_dir.name == TRIAL_DIR:
            shutil.rmtree(self.state_dir, ignore_errors=True)
        if self.factory is not None:
            self._attach(self.factory())
        self.last = None
        self.last_mid = ""

    def conv_of(self, uid: str) -> str:
        return channels.dm_learning_key(uid) if self.dm else self.conv

    async def say(self, name: str, uid: str, text: str, *,
                  quote: bool = False) -> Turn:
        if self.dm:
            return await self._dm_turn(name, uid, text)
        return await self._group_turn(name, uid, text,
                                      self.last_mid if quote else "")

    # -- reactions -----------------------------------------------------------

    async def _react(self, entry: dict, text: str, name: str, uid: str,
                     is_admin: bool, conv: str) -> Reaction:
        """Judge a reaction as the live turn does, but wait for the verdict,
        then read back what the ledger recorded."""
        agent = self.agent
        seen = {e["event_id"] for e in agent.evidence_log.all()}
        before = {c["candidate_id"]: (c.get("state"), set(c.get("evidence") or ()))
                  for c in agent.candidate_ledger.all()}
        blocked = not is_admin and agent.teacher_stats.hard_block(uid)
        await agent._process_reaction(entry, text, name, uid, is_admin,
                                      conv_id=conv, is_dm=self.dm)
        events = [e for e in agent.evidence_log.all() if e["event_id"] not in seen]
        new_ids = {e["event_id"] for e in events}
        out = Reaction(reply=str(entry.get("reply") or ""),
                       target=str(entry.get("target_name") or ""),
                       events=events, blocked=blocked)
        for cand in agent.candidate_ledger.all():
            old_state, old_ev = before.get(cand["candidate_id"], ("", set()))
            state = cand.get("state")
            if state == candidates.STATE_PROMOTED and old_state != state:
                out.promoted.append((cand, checklist(agent, cand)))
            elif (state == candidates.STATE_ROLLED_BACK
                  and old_state == candidates.STATE_PROMOTED):
                out.rolled_back += 1
            elif (state == candidates.STATE_PROPOSED
                  and new_ids & (set(cand.get("evidence") or ()) - old_ev)):
                out.held.append((cand, checklist(agent, cand)))
        # A fix first: it is what the person was arguing about.
        out.held.sort(key=lambda pair: pair[0].get("type") != candidates.TYPE_PAIR)
        awaiting = _awaiting_fix(agent, conv)
        out.armed = bool(awaiting) and awaiting.get("evidence_id") in new_ids
        return out

    # -- the group turn ------------------------------------------------------

    async def _group_turn(self, name: str, uid: str, text: str,
                          quote_mid: str) -> Turn:
        """turns.Turns._handle_inner, minus admission, debounce and delivery."""
        agent, conv = self.agent, self.conv
        nickname = (_clean_prompt_source(name) or "?")[:8]
        payload = {"message_type": "group", "group_id": conv, "user_id": uid,
                   "sender": {"nickname": nickname},
                   "message": [{"type": "text", "data": {"text": text}}]}
        text = await agent._extract_text(payload)
        turn = Turn(speaker=nickname, uid=uid, text=text,
                    trigger=agent.chat_trigger_count,
                    window=agent.chat_followup_window_s)
        if not text:
            return turn
        ctrl_text = _strip_web_desc(text)
        addressed = _names_bot(agent, ctrl_text)
        is_admin = access.is_admin(uid, agent._admins())

        if agent.react_learn_enabled:
            entry = agent.pending_reactions.match(
                conv, sender_uid=uid, quote_mid=quote_mid, at_bot=addressed,
                now=time.time())
            if entry:
                turn.reaction = await self._react(entry, text, nickname, uid,
                                                  is_admin, conv)

        agent._append_buffer(conv, nickname, _truncate_framed(text, 200), uid)
        agent.last_activity_at[conv] = time.time()
        agent.active_users[conv].append((uid, nickname))
        if len(text.strip()) >= 4 or addressed:
            agent.counters[conv] += 1

        if addressed:
            notes = len(agent.memories.get(conv, []))
            mem_reply = agent._handle_memory_command(conv, ctrl_text, uid, nickname)
            if mem_reply is not None:
                turn.mode, turn.memory = "memory", True
                turn.memory_saved = len(agent.memories.get(conv, [])) > notes
                turn.reply = TextProcessing._sanitize_reply(
                    mem_reply, agent._validator_lang(), agent.reply_style)
                agent.last_reply_at[conv] = time.time()
                agent._append_buffer(conv, agent.persona_name, mem_reply)
                self.last = turn
                return turn

        never_replied = agent.last_reply_at[conv] == 0.0
        turn.count = agent.counters[conv]
        mode, why = choose_group_mode(
            addressed=addressed, is_admin=is_admin, sticky_admin=None,
            in_followup=(time.time() - agent.last_reply_at[conv]
                         < agent.chat_followup_window_s),
            counter=turn.count, trigger_count=agent.chat_trigger_count,
            never_replied=never_replied)
        turn.mode, turn.why = mode, why
        if not mode:
            turn.quiet = "below"
            return turn
        agent.counters[conv] = 0
        skip = pacing_skip(mode, first_appearance=never_replied,
                           sleep_hour=TextProcessing._is_sleep_hour())
        if skip:
            turn.quiet = "sleep" if skip == "sleep window" else "skip"
            return turn

        self._gate_verdict = None
        try:
            reply, intent, auto_mem = await agent._think(conv, mode, text)
        except Exception as e:
            turn.quiet, turn.error = "model_error", f"{type(e).__name__}: {e}"
            return turn
        if mode in GATED_MODES and self._gate_verdict is False:
            turn.quiet = "gate_pass"
            return turn
        return self._commit_group(turn, reply, intent, auto_mem)

    def _commit_group(self, turn: Turn, raw: str, intent: str,
                      auto_mem: str) -> Turn:
        agent, conv = self.agent, self.conv
        final = agent._finalize_reply(raw, log_ctx=f"trial mode={turn.mode}")
        if final is None:
            turn.quiet = "filter"
            return turn
        reply, at_uid, pending_core, had_visible = final
        if not at_uid and turn.mode == "called":
            at_uid = turn.uid
        if had_visible and not reply:
            turn.quiet, turn.raw = "character", clip(raw, 60)
            return turn
        if not reply or re.match(r"PASS\b", reply, re.IGNORECASE):
            turn.quiet = "pass"
            if turn.mode == "followup":
                agent.last_reply_at[conv] = (
                    time.time() - agent.chat_followup_window_s - 1)
            return turn
        sent = TextProcessing._sanitize_reply(
            reply, agent._validator_lang(), agent.reply_style)
        if not sent:
            turn.quiet, turn.raw = "character", clip(reply, 60)
            return turn
        context = [f"{m['name']}: {m['text']}" for m in list(agent.buffers[conv])[-5:]]
        awaiting = _awaiting_fix(agent, conv)
        agent.last_reply_at[conv] = time.time()
        agent._append_buffer(conv, agent.persona_name, sent)
        agent._commit_core_memory(conv, pending_core)
        if auto_mem:
            agent._save_auto_memory(conv, auto_mem)
        self.last_mid = f"{conv}-{next(self._mids)}"
        if agent.react_learn_enabled:
            agent.pending_reactions.record(
                conv, reply=sent, ctx_lines=context, mode=turn.mode,
                intent=intent,
                target_uid=agent._reaction_recipient(conv, turn.mode, at_uid, turn.uid),
                target_name=turn.speaker, mids=[self.last_mid], ts=time.time())
            if awaiting and _awaiting_fix(agent, conv) is None:
                turn.retry_of = str(awaiting.get("reply") or "")
        turn.reply = _render(sent)
        turn.offered = self.offered(conv, turn.text, turn.mode)
        self.last = turn
        return turn

    # -- the one-to-one turn -------------------------------------------------

    async def _dm_turn(self, name: str, uid: str, text: str) -> Turn:
        """The live DM handler itself, with its reaction judged first and
        waited for. That match takes the one reply a DM can have pending, so
        the handler's own match finds nothing left to judge twice."""
        agent = self.agent
        conv = channels.dm_learning_key(uid)
        is_admin = access.is_admin(uid, agent._admins())
        turn = Turn(speaker=name, uid=uid, text=text,
                    mode=ADMIN_MODE if is_admin else "called", why="dm")
        if agent.react_learn_enabled:
            entry = agent.pending_reactions.match(
                conv, sender_uid=uid, is_dm=True, now=time.time())
            if entry:
                turn.reaction = await self._react(
                    entry, text, "owner" if is_admin else "friend", uid,
                    is_admin, conv)
        awaiting = _awaiting_fix(agent, conv)
        payload = {"message_type": "private", "user_id": uid,
                   "sender": {"nickname": name},
                   "message": [{"type": "text", "data": {"text": text}}]}
        sink = ConnectorSink(bot_id=agent._self_mention_id())
        token = current_sink.set(sink)
        try:
            await agent._handle_dm(uid, payload, is_admin=is_admin)
        except Exception as e:
            turn.quiet, turn.error = "model_error", f"{type(e).__name__}: {e}"
            return turn
        finally:
            sink.closed = True
            current_sink.reset(token)
        said = [item.get("text", "") for item in sink.items
                if item.get("type") == "text" and item.get("text")]
        if not said:
            turn.quiet = "dm_none"
            return turn
        turn.reply = "\n".join(said)
        if awaiting and _awaiting_fix(agent, conv) is None:
            turn.retry_of = str(awaiting.get("reply") or "")
        turn.offered = self.offered(conv, text, "")
        self.last = turn
        return turn

    # -- reading back ----------------------------------------------------------

    def offered(self, conv: str, focus: str, mode: str) -> list[dict]:
        """Learned rows from this chat that retrieval puts in the prompt for
        `focus` now."""
        agent = self.agent
        agent._reload_views_if_stale()
        scope = agent._live_scope(conv)
        rows = [r for r in agent._view_pairs_cache + agent._view_examples_cache
                if agent._scope_authorizes(r.get("scope"), scope)]
        if not rows:
            return []
        block = agent._examples_for_prompt(focus, mode, conv_id=conv)
        return [r for r in rows
                if _example_field(r.get("better") or r.get("reply") or "") in block]

    async def probe(self, name: str, uid: str, text: str) -> Turn:
        """What it would answer to `text` in this chat now, from a clean
        context, without the chat seeing it."""
        agent, conv = self.agent, self.conv
        turn = Turn(speaker=name, uid=uid, text=text, mode="called")
        saved = agent.buffers.pop(conv, None)
        try:
            agent._append_buffer(conv, name, text, uid)
            reply, _intent, _mem = await agent._think(
                conv, "called", text, caller_override=(name, uid))
        finally:
            agent.buffers.pop(conv, None)
            if saved is not None:
                agent.buffers[conv] = saved
        final = agent._finalize_reply(reply, log_ctx="trial probe")
        turn.reply = _render(final[0]) if final else ""
        if not turn.reply or re.match(r"PASS\b", turn.reply, re.IGNORECASE):
            turn.reply, turn.quiet = "", "pass"
        turn.offered = self.offered(conv, text, "called")
        return turn

    def about(self, reply: str) -> tuple[list[dict], list[dict]]:
        """Ledger events and candidates about one reply, oldest first."""
        reply = reply.strip()
        events = [e for e in self.agent.evidence_log.all()
                  if str(e.get("reply") or "").strip() == reply
                  or str((e.get("adjudication") or {}).get("better") or "").strip() == reply]
        cands = [c for c in self.agent.candidate_ledger.all()
                 if reply in (str(c.get("reply") or "").strip(),
                              str(c.get("better") or "").strip())]
        return events, cands


def _render(text: str) -> str:
    """A reply as the terminal shows it: stickers named, not sent."""
    parts = []
    for kind, value in TextProcessing._parse_sticker_markers(text or ""):
        parts.append(value if kind == "text" else f"(sticker: {value})")
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Rendering, shared with the demo
# ---------------------------------------------------------------------------

def reason(lang: str, turn: Turn, name: str) -> str:
    """Why the turn spoke or stayed quiet, in one phrase."""
    t = text_for(lang)
    counts = {"count": turn.count, "trigger": turn.trigger, "window": turn.window}
    base = {"below the trigger count": t["below"], "trigger count": t["trigger_count"],
            "first appearance": t["first_appearance"],
            "followup window": t["followup"]}.get(turn.why, "").format(**counts)
    if turn.quiet == "below":
        return base
    if turn.quiet == "gate_pass":
        return t["gate_pass"].format(why=base)
    if turn.mode in GATED_MODES and not turn.quiet:
        return t["gate_speak"].format(why=base)
    key = turn.quiet
    if key in ("sleep", "skip", "pass", "filter", "dm_none"):
        return t[key].format(name=name)
    if key == "character":
        return t["character"].format(raw=f'"{turn.raw}"' if turn.raw else "")
    if key == "model_error":
        return t["model_error"].format(error=turn.error)
    return base


def held_reason(lang: str, check: Checklist) -> str:
    t = text_for(lang)
    key = check.waiting_for()
    if not key:
        return check.decision.reason
    need = {"why_strong": check.need_strong, "why_events": check.need_events,
            "why_speakers": check.need_speakers}.get(key, 0)
    return t[key].format(strong=check.strong, need=need, events=check.events,
                         speakers=check.speakers)


def promoted_line(lang: str, check: Checklist) -> str:
    t = text_for(lang)
    return t["promoted"].format(events=check.events, strong=check.strong,
                                chat=t["same_chat"] if check.same_chat else "")


def reaction_label(lang: str, rtype: str) -> str:
    return text_for(lang)["reactions"].get(rtype, rtype)


def strength_label(lang: str, strength: str) -> str:
    return text_for(lang)["strengths"].get(strength, strength)


def state_label(lang: str, state: str) -> str:
    return text_for(lang)["states"].get(state, state)


def judged(lang: str, event: dict) -> str:
    """One evidence event as a verdict."""
    t = text_for(lang)
    strength = strength_label(lang, event.get("strength", ""))
    if event.get("kind") == evidence.KIND_RETRY_ACCEPTANCE:
        key = "retry_ok" if event.get("reaction_type") == "positive" else "retry_moved_on"
        return t[key].format(strength=strength)
    reaction = reaction_label(lang, event.get("reaction_type", ""))
    if not (event.get("adjudication") or {}).get("accept"):
        # A dismissed verdict supports nothing, whatever its strength.
        return t["judged_dismissed"].format(reaction=reaction)
    return t["judged"].format(reaction=reaction, strength=strength)


def trace(lang: str, r: Reaction) -> str:
    """A reaction's one-line learning trace."""
    t = text_for(lang)
    if not r.events:
        return t["learning"].format(
            text=t["blocked_teacher" if r.blocked else "no_verdict"])
    verdicts = t["and"].join(judged(lang, e) for e in r.events)
    if r.promoted:
        outcome = promoted_line(lang, r.promoted[0][1])
    elif r.rolled_back:
        outcome = t["rolled_back"].format(n=r.rolled_back)
    elif r.armed:
        outcome = t["armed"]
    elif r.held:
        outcome = t["held"].format(why=held_reason(lang, r.held[0][1]))
    else:
        outcome = t["nothing"]
    return t["learning"].format(text=verdicts + t["then"] + outcome)


def candidate_line(lang: str, agent: Agent, cand: dict) -> str:
    t = text_for(lang)
    kind = t["kind_pair" if cand.get("type") == candidates.TYPE_PAIR else "kind_example"]
    what = f'"{clip(cand.get("reply"))}"'
    if cand.get("better"):
        what += f' -> "{clip(cand.get("better"))}"'
    state = cand.get("state", "")
    line = f"{kind} {cand['candidate_id'][:8]} {what}: {state_label(lang, state)}"
    if state == candidates.STATE_PROPOSED:
        line += f" ({held_reason(lang, checklist(agent, cand))})"
    return line


def why_lines(lang: str, trial: Trial, name: str) -> list[str]:
    """/why: how the last reply came about, and what the ledger holds on it."""
    t = text_for(lang)
    turn = trial.last
    if turn is None or not turn.reply:
        return [t["why_none"].format(name=name)]
    lines = [t["why_head"].format(name=name, reply=clip(turn.reply, 60))]
    if turn.memory:
        lines.append(t["why_memory"].format(who=turn.speaker))
    elif turn.why == "dm":
        lines.append(t["why_dm"].format(who=turn.speaker))
    elif turn.mode in GATED_MODES:
        lines.append(t["why_joined"].format(who=turn.speaker,
                                            reason=reason(lang, turn, name)))
    else:
        lines.append(t["why_admin" if turn.mode == ADMIN_MODE else "why_named"]
                     .format(who=turn.speaker))
    if turn.retry_of:
        lines.append(t["why_retry"].format(text=clip(turn.retry_of, 60)))
    if not turn.memory:
        if turn.offered:
            lines.append(t["why_prompt"])
            for row in turn.offered:
                shown = f'    "{clip(row.get("reply"))}"'
                if row.get("better"):
                    shown += f' -> "{clip(row.get("better"))}"'
                lines.append(shown)
        else:
            lines.append(t["why_prompt_none"])
    events, cands = trial.about(turn.reply)
    if not events and not cands:
        lines.append(t["why_ledger_none"])
        return lines
    lines.append(t["why_ledger"])
    for e in events:
        lines.append(f"    {e.get('speaker_name') or '?'}: {judged(lang, e)}")
    for cand in cands:
        lines.append("    " + candidate_line(lang, trial.agent, cand))
    return lines


# ---------------------------------------------------------------------------
# The terminal session
# ---------------------------------------------------------------------------

def _admin_id() -> str:
    """Who "--admin" speaks as: a configured admin account, if there is one."""
    return min(access.identity_from_env().admins, default="") or "1969"


def build_agent(lang: str, trigger: int) -> tuple[Agent, Path]:
    """The live configuration, with every state file in the trial folder."""
    state = paths.runtime_dir() / TRIAL_DIR
    saved = os.environ.get("AGENT_RUNTIME_DIR")
    # Only while the Agent resolves its paths.
    os.environ["AGENT_RUNTIME_DIR"] = str(state)
    try:
        settings = AgentSettings.from_env(
            lang=lang,
            persona_name=os.getenv("PERSONA_NAME", "") or "bot",
            qq_bot_id=os.getenv("QQ_BOT_ID", "") or "10000",
            admin_ids=(_admin_id(),),
            admin_name=os.getenv("ADMIN_NAME", "") or "admin",
            chat_trigger_count=trigger, message_debounce_sec=0,
            memory_file="memory.json", eval_file="eval.jsonl",
            stickers_dir=str(state / "stickers"), stickers_file="stickers.json",
            # Self-scoring costs tokens, the terminal sends no images, and the
            # follow-up ask would go to a platform two minutes later.
            eval_enabled=False, vision_model="", react_elicit_enabled=False,
            proactive_enabled=False, evolve_auto_enabled=False,
        )
        agent = Agent(settings)
    finally:
        if saved is None:
            os.environ.pop("AGENT_RUNTIME_DIR", None)
        else:
            os.environ["AGENT_RUNTIME_DIR"] = saved
    return agent, state


def _shown_path(path: Path) -> str:
    try:
        return str(path.relative_to(paths.ROOT)) + os.sep
    except ValueError:
        return str(path) + os.sep


class ChatSession:
    """The terminal side: parses a line, runs it, prints what happened."""

    def __init__(self, trial: Trial, *, lang: str, you: str, admin: bool,
                 live_trigger: int) -> None:
        self.trial = trial
        self.lang = lang
        self.t = text_for(lang)
        agent = trial.agent
        self.name = agent.persona_name
        self.admin = (agent.admin_name or "admin", _admin_id())
        self.you = self.admin if admin else (you, YOU_UID)
        self.live_trigger = live_trigger
        self._others: dict[str, str] = {}

    def banner(self) -> None:
        t, agent = self.t, self.trial.agent
        head = t["banner_dm" if self.trial.dm else "banner"]
        print(head.format(name=self.name, model=agent.model, lang=agent.agent_lang))
        print(t["you_are_dm" if self.trial.dm else "you_are"].format(
            you=self.you[0], name=self.name))
        if not self.trial.dm:
            print(t["trigger"].format(name=self.name, n=agent.chat_trigger_count,
                                      live=self.live_trigger))
        if self.trial.state_dir is not None:
            print(t["state"].format(path=_shown_path(self.trial.state_dir)))
        self.commands()

    def commands(self) -> None:
        print()
        for cmd, desc in self.t["commands"]:
            # Wide (CJK) characters take two columns in a terminal.
            width = sum(2 if unicodedata.east_asian_width(c) in "WF" else 1
                        for c in cmd)
            print(f"  {cmd}{' ' * max(1, 16 - width)}{desc.format(name=self.name)}")
        print()

    async def handle(self, line: str) -> bool:
        """Run one input line. False when the user leaves."""
        line = line.strip()
        if not line:
            return True
        if line in ("/quit", "/exit", "/q"):
            return False
        if line == "/reset":
            await self.trial.reset()
            print("  " + self.t["reset"] + "\n")
            return True
        if line == "/why":
            for out in why_lines(self.lang, self.trial, self.name):
                print("  " + out)
            print()
            return True
        if line == "/learned":
            conv = self.trial.conv_of(self.you[1])
            for out in self.trial.agent._learned_summary(conv).splitlines():
                print(f"  {self.name} > {out}")
            print()
            return True
        (name, uid), quote, msg = self.you, False, line
        command, _, rest = line.partition(" ")
        if command == "/admin":
            (name, uid), msg = self.admin, rest
        elif command == "/as":
            speaker, _, msg = rest.strip().partition(" ")
            if not speaker or not msg.strip():
                print("  " + self.t["usage_as"])
                return True
            name = speaker
            uid = self._others.setdefault(speaker, str(3001 + len(self._others)))
        elif command == "/reply":
            if not self.trial.dm and not self.trial.last_mid:
                print("  " + self.t["nothing_to_quote"].format(name=self.name))
                return True
            quote, msg = True, rest
        elif command.startswith("/"):
            self.commands()
            return True
        if not msg.strip():
            return True
        try:
            turn = await self.trial.say(name, uid, msg.strip(), quote=quote)
        except Exception as e:
            print("  " + self.t["error"].format(error=f"{type(e).__name__}: {e}"))
            return True
        self.show(turn)
        return True

    def show(self, turn: Turn) -> None:
        t = self.t
        if turn.reaction is not None:
            print("  " + trace(self.lang, turn.reaction))
        if turn.reply:
            if turn.mode in GATED_MODES:
                print("  " + t["joins"].format(
                    name=self.name, reason=reason(self.lang, turn, self.name)))
            for out in turn.reply.splitlines():
                print(f"  {self.name} > {out}")
        elif turn.quiet:
            print("  " + t["quiet"].format(
                name=self.name, reason=reason(self.lang, turn, self.name)))
        print()


def utf8_console() -> None:
    """Chinese output must not crash a console on a legacy code page."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError, ValueError):
            pass


async def main(argv: list[str] | None = None, prog: str | None = None) -> int:
    utf8_console()
    home.load_env()
    p = argparse.ArgumentParser(
        prog=prog, description="Talk to the character in a simulated group chat.")
    p.add_argument("--lang", default=os.getenv("AGENT_LANG", "en"),
                   help="agent language: en (default) or zh")
    p.add_argument("--admin", action="store_true",
                   help="speak as the configured admin (closer relationship)")
    p.add_argument("--name", default="you", help="your display name in the chat")
    p.add_argument("--dm", action="store_true",
                   help="a one-to-one chat instead of a group")
    p.add_argument("--trigger", type=int, default=TRIAL_TRIGGER,
                   help=f"messages before it considers joining in (default "
                        f"{TRIAL_TRIGGER}; the live bot uses CHAT_TRIGGER_COUNT)")
    args = p.parse_args(argv)
    lang = args.lang.strip().lower()
    trigger = max(1, args.trigger)

    live = AgentSettings.from_env(lang=lang)
    if not live.api_key:
        # Before anything is built: a home without a key gets no trial folder.
        print(text_for(live.agent_lang)["no_key"])
        return 1
    agent, state = build_agent(lang, trigger)
    trial = Trial(agent, dm=args.dm, state_dir=state,
                  factory=lambda: build_agent(lang, trigger)[0])
    session = ChatSession(trial, lang=agent.agent_lang, you=args.name,
                          admin=args.admin, live_trigger=live.chat_trigger_count)
    session.banner()
    try:
        while True:
            try:
                line = input(f"{session.you[0]}> ")
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not await session.handle(line):
                break
        print(session.t["bye"])
        return 0
    finally:
        await trial.agent.aclose()


def run(argv: list[str] | None = None, prog: str | None = None) -> int:
    try:
        return asyncio.run(main(argv, prog))
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(run())
