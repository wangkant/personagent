"""Try the agent in your terminal: a simulated group chat, no platform needed.

    personagent chat
    personagent chat --dm           # a one-to-one chat instead of a group
    personagent chat --lang zh      # the Chinese variant
    personagent chat --name Alex    # your display name
    personagent chat --admin        # speak as the configured admin
    personagent chat --trigger 4    # messages before it considers joining in

Every line runs through the functions the live bot runs, and the trial says
why when it stays quiet. A reply to it is judged and recorded in the learning
ledger. State lives in <runtime>/trial/, apart from the live bot's.
"""
from __future__ import annotations

import argparse
import asyncio
import contextlib
import functools
import itertools
import logging
import os
import shutil
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from persona_agent import access, candidates, channels, evidence, home, langs, paths, promotion
from persona_agent.access import ADMIN_MODE
from persona_agent.agent import Agent
from persona_agent.connector import ConnectorSink, current_sink
from persona_agent.decision import (GATED_MODES, choose_group_mode, is_pass_sentinel,
                                    pacing_skip)
from persona_agent.llm import _status_of
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
        "trigger": ("{name} considers joining in after {n} {messages} here "
                    "(the live bot waits for {live}; --trigger N)."),
        "state": ("What the trial learns stays in {path}, apart from the live bot: "
                  "{learned} does not show it, and /reset clears it."),
        "resumed": "(this folder already holds what an earlier session learned; /reset starts clean)",
        "name_unset": ('PERSONA_NAME is not set, so the character is called "{name}" '
                       "here; set it in {env} to give it its own name."),
        "admin_name": "--admin speaks as {admin}, so --name is ignored.",
        "commands": [
            ("/reply <text>", "quote {name}'s last reply"),
            ("/as Name <msg>", "speak as someone else"),
            ("/admin <msg>", "speak once as the admin"),
            ("/why", "why it said its last reply, from the ledger"),
            ("/learned", "what it has learned in this chat"),
            ("/reset", "start over: clear this chat and what the trial learned"),
            ("/quit", "leave"),
        ],
        "no_key": ("No model key yet. Run {init} to choose a model and "
                   "key, or {demo} to watch it work without one."),
        "bye": "Goodbye.",
        "reset": "(started over: this chat and what the trial learned have been cleared)",
        "nothing_to_quote": "(no reply from {name} is waiting to be quoted)",
        "usage_as": "usage: /as Name your message",
        "usage_reply": "usage: /reply your message",
        "usage_admin": "usage: /admin your message",
        "you": "you",
        "unknown": "unknown command {cmd}; the commands are:",
        "error": "[error: {error}]",
        "failures": {
            "auth": ("the model provider refused the key or the account{http}; "
                     "check LLM_API_KEY, then run {doctor}"),
            "request": ("the model provider rejected the request{http}; check "
                        "LLM_MODEL and LLM_BASE_URL, then run {doctor}"),
            "rate_limit": ("the model provider is rate limiting or out of credit"
                           "{http}; wait a moment and try again"),
            "unreachable": ("could not reach the model provider; check "
                            "LLM_BASE_URL and the network, then run {doctor}"),
            "server": "the model provider had an error{http}; try again in a moment",
            "other": "the model call failed ({detail})",
        },
        "quiet": "({name} stays quiet: {reason})",
        "joins": "({name} joins in: {reason})",
        "below": "not addressed, {count} of {trigger} messages",
        "short": ("not addressed, {count} of {trigger} messages so far; this one "
                  "is too short to count (under 4 characters)"),
        "trigger_count": "{count} of {trigger} messages",
        "first_appearance": "{count} {messages} and it has not spoken here yet",
        "followup": "it spoke in the last {window} s",
        "gate_pass": "{why}, but the gate model said stay quiet",
        "gate_speak": "{why}, and the gate model said speak",
        "sleep": "it is night where {name} lives (sleep window)",
        "skip": "skipped at random, as a person does not take every chance to speak",
        "pass": "the model chose PASS",
        "filter": "the output filter blocked its reply",
        "character": "the character check rejected its reply {raw}",
        "dm_none": "no usable reply came back",
        "learning": "[learning] {text}",
        "judged": "judged: {reaction}, accepted ({strength})",
        "judged_dismissed": "judged: {reaction}, dismissed",
        "and": "; ",
        "then": " - ",
        "retry_ok": "its retry was accepted ({strength})",
        "retry_moved_on": "its retry received no thanks; the conversation moved on ({strength})",
        "no_verdict": "no verdict: the judge model's answer could not be read",
        "judge_failed": "no verdict: the call to the judge model failed: {why}",
        "blocked_teacher": ("not judged: this person's teaching is mostly dismissed, "
                            "so it is no longer weighed (/reset clears that)"),
        "promoted": "now in use: {events} agreeing {reactions}, {strong} strong{chat}",
        "same_chat": ", same chat",
        "held": "not in use yet: {why}",
        "rolled_back": "stopped using {n} learned {rows} about that reply",
        "armed": "waiting for your reaction to its retry",
        "nothing": "nothing to learn",
        "why_off": "automatic learning is switched off, so nothing new is put in use",
        "why_deciding": "the character is deciding it itself",
        "why_observing": "the character looked at it and keeps observing: {reason}",
        "why_judge_off": ("no further reaction can settle it, and the character's own "
                          "decisions are switched off (PROMOTE_JUDGE_ENABLED)"),
        "why_liked": "waiting for an approving reaction from someone in the chat",
        "why_other": "",
        "by_character": "the character decided: {reason}",
        "by_time": "set aside after a long time without a new reaction",
        "why_strong": "{strong} of {need} strong reactions so far",
        "why_events": "{events} of {need} agreeing reactions so far",
        "why_speakers": "{speakers} of {need} different people so far",
        "why_head": 'why {name} said "{reply}":',
        "why_none": "nothing to explain yet: {name} has not replied",
        "why_named": "  answered {who}: {who} used its name",
        "why_admin": "  answered {who}: the admin used its name",
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
        "states": {"proposed": "observing", "promoted": "promoted", "rejected": "rejected",
                   "rolled_back": "rolled back", "superseded": "superseded"},
        "reactions": {"correction": "correction", "rejection": "rejection",
                      "positive": "positive", "neutral": "neutral"},
        "strengths": {"strong": "strong", "negative_only": "negative only",
                      "weak": "weak"},
    },
    "zh": {
        "banner": "personagent chat：模拟群聊中的{name}（模型 {model}，{lang}）",
        "banner_dm": "personagent chat：与{name}的私聊（模型 {model}，{lang}）",
        "you_are": "你的名称为「{you}」。普通消息即为群聊发言；消息中包含「{name}」即为点名{name}。",
        "you_are_dm": "你的名称为「{you}」。你输入的每条消息都将发送给{name}。",
        "trigger": ("在此处，{name}每累计 {n} 条消息才会考虑主动发言"
                    "（正式运行时为 {live} 条；可通过 --trigger N 修改）。"),
        "state": ("试用中学到的内容保存在 {path}，与正式运行的角色相互独立：{learned} 不会显示这些内容，"
                  "使用 /reset 可将其清空。"),
        "resumed": "（此文件夹中保留有此前试用学到的内容；使用 /reset 可重新开始）",
        "name_unset": "未设置 PERSONA_NAME，因此角色在此处名为「{name}」；在 {env} 中设置后，角色将使用其专属名称。",
        "admin_name": "--admin 以 {admin} 的身份发言，因此 --name 不生效。",
        "commands": [
            ("/reply <内容>", "引用{name}的上一条回复"),
            ("/as 名字 <消息>", "以其他成员的身份发言"),
            ("/admin <消息>", "以管理员身份发送一条消息"),
            ("/why", "查看上一条回复的依据（来自学习记录）"),
            ("/learned", "查看角色在本聊天中学到的内容"),
            ("/reset", "重新开始：清空本聊天及试用中学到的内容"),
            ("/quit", "退出"),
        ],
        "no_key": ("尚未配置模型密钥。请运行 {init} 选择模型并填写密钥；"
                   "也可以运行 {demo}，无需密钥即可查看演示。"),
        "bye": "再见。",
        "reset": "（已重新开始：本聊天及试用中学到的内容均已清空）",
        "nothing_to_quote": "（当前没有可引用的{name}的回复）",
        "usage_as": "用法：/as 名字 消息内容",
        "usage_reply": "用法：/reply 消息内容",
        "usage_admin": "用法：/admin 消息内容",
        "you": "用户",
        "unknown": "未知命令 {cmd}。可用命令如下：",
        "error": "[错误：{error}]",
        "failures": {
            "auth": "模型服务拒绝了该密钥或账号{http}；请检查 LLM_API_KEY，然后运行 {doctor}",
            "request": "模型服务拒绝了此次请求{http}；请检查 LLM_MODEL 和 LLM_BASE_URL，然后运行 {doctor}",
            "rate_limit": "模型服务已限流或额度不足{http}；请稍后重试",
            "unreachable": "无法连接模型服务；请检查 LLM_BASE_URL 和网络连接，然后运行 {doctor}",
            "server": "模型服务发生错误{http}；请稍后重试",
            "other": "模型调用失败（{detail}）",
        },
        "quiet": "（{name}未发言：{reason}）",
        "joins": "（{name}主动发言：{reason}）",
        "below": "未被点名，已累计 {count}/{trigger} 条消息",
        "short": "未被点名，目前已累计 {count}/{trigger} 条消息；此条消息过短（少于 4 个字符），不计入",
        "trigger_count": "已累计 {count}/{trigger} 条消息",
        "first_appearance": "已累计 {count} 条消息，且角色尚未在此发言",
        "followup": "角色在 {window} 秒内刚发过言",
        "gate_pass": "{why}，但判断模型认为不应发言",
        "gate_speak": "{why}，判断模型认为应当发言",
        "sleep": "{name}所在时区当前为深夜（休息时段）",
        "skip": "随机跳过，以模拟真人并非每次都会参与对话",
        "pass": "模型选择了 PASS（不发言）",
        "filter": "回复已被输出过滤器拦截",
        "character": "回复未通过字符校验 {raw}",
        "dm_none": "未获得可发送的回复",
        "learning": "[学习] {text}",
        "judged": "判定：{reaction}，采信（{strength}）",
        "judged_dismissed": "判定：{reaction}，不采信",
        "and": "；",
        "then": "，",
        "retry_ok": "重试回复已被接受（{strength}）",
        "retry_moved_on": "重试回复未获致谢，对话已转向其他话题（{strength}）",
        "no_verdict": "无判定结果：无法解析判定模型的回答",
        "judge_failed": "无判定结果：调用判定模型失败：{why}",
        "blocked_teacher": "未判定：该成员提出的纠正多数未被采信，已不再纳入考虑（使用 /reset 可清除此状态）",
        "promoted": "已生效：{events} 条一致的反应，其中 {strong} 条为强{chat}",
        "same_chat": "，来自同一聊天",
        "held": "尚未生效：{why}",
        "rolled_back": "已停用 {n} 条与该回复相关的学习结果",
        "armed": "正在等待你对重试回复作出反应",
        "nothing": "无可学习的内容",
        "why_off": "自动学习已关闭，不会启用任何新内容",
        "why_deciding": "角色正在自行判断此项",
        "why_observing": "角色已审视此项，决定继续观察：{reason}",
        "why_judge_off": "后续反应已无法决定此项，且角色自行判断的功能已关闭（PROMOTE_JUDGE_ENABLED）",
        "why_liked": "等待聊天中有成员对其作出认可的反应",
        "why_other": "尚未满足自动生效的条件",
        "by_character": "角色已自行决定：{reason}",
        "by_time": "因长时间未收到新的反应，已按时限搁置",
        "why_strong": "强反应目前为 {strong}/{need} 条",
        "why_events": "一致的反应目前为 {events}/{need} 条",
        "why_speakers": "不同成员目前为 {speakers}/{need} 人",
        "why_head": "{name}回复「{reply}」的依据：",
        "why_none": "暂无可解释的内容：{name}尚未回复",
        "why_named": "  回复{who}：{who}提及了角色名称",
        "why_admin": "  回复{who}：管理员提及了角色名称",
        "why_joined": "  在{who}之后主动发言：{reason}",
        "why_memory": "  来自{who}的记忆指令，未调用模型",
        "why_dm": "  在私聊中回复{who}",
        "why_retry": "  这是对「{text}」的重试回复",
        "why_prompt_none": "  提示词中的学习结果：无",
        "why_prompt": "  提示词中的学习结果：",
        "why_ledger_none": "  学习记录中尚无相关条目；在消息中提及角色名称或使用 /reply 回复，即可进行教学",
        "why_ledger": "  学习记录：",
        "kind_pair": "改写",
        "kind_example": "范例",
        "states": {"proposed": "观察中", "promoted": "已生效", "rejected": "已驳回",
                   "rolled_back": "已撤销", "superseded": "已替换"},
        "reactions": {"correction": "纠正", "rejection": "否定",
                      "positive": "正面", "neutral": "中性"},
        "strengths": {"strong": "强", "negative_only": "仅否定", "weak": "弱"},
    },
}


@functools.lru_cache(maxsize=None)
def text_for(lang: str) -> dict:
    return langs.table(_TEXT["en"], _TEXT["zh"], lang)


def clip(text, width: int = 40) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= width else text[:width - 3] + "..."


def normalize_lang(value: str | None) -> str:
    """The language code for a spelling of one; English for anything else."""
    return langs.normalize(value) or "en"


def plural(lang: str, n: int, one: str, many: str) -> str:
    return langs.say(one if n == 1 else many, "", lang)


@functools.lru_cache(maxsize=None)
def hint(sub: str, lang: str = "en") -> str:
    """`personagent <sub>` as this install runs it, ready to show in a sentence.
    Cached so the demo can ask before it swaps in its throwaway home."""
    from persona_agent.setup_wizard import Launcher
    lines = Launcher(python=sys.executable, home=paths.ROOT).shown(sub)
    return langs.say(", then ", "，然后 ", lang).join(f"`{line}`" for line in lines)


@dataclass(frozen=True)
class Failure:
    """Why a model call failed, in terms a newcomer can act on."""

    kind: str
    status: int | None = None
    detail: str = ""


def describe_failure(exc: BaseException) -> Failure:
    if isinstance(exc, (httpx.TransportError, OSError, asyncio.TimeoutError)):
        return Failure("unreachable")
    status = _status_of(exc)
    kind = Agent._classify_api_error(exc)
    if kind == "fatal_auth":
        return Failure("auth", status)
    if kind == "fatal_request":
        return Failure("request", status)
    if kind == "rate_limit":
        return Failure("rate_limit", status)
    if status and status >= 500:
        return Failure("server", status)
    first = (str(exc).strip().splitlines() or [""])[0]
    return Failure("other", status, f"{type(exc).__name__}: {clip(first, 100)}")


def failure_text(lang: str, failure: Failure, doctor: str | None = None) -> str:
    http = f" (HTTP {failure.status})" if failure.status else ""
    return text_for(lang)["failures"][failure.kind].format(
        http=http, detail=failure.detail,
        doctor=doctor if doctor is not None else hint("doctor", lang))


# ---------------------------------------------------------------------------
# What a turn and a reaction did
# ---------------------------------------------------------------------------

@dataclass
class Checklist:
    """The promotion rules for one candidate and where each stands, counted
    with the policy's own functions."""

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
    #: No further reaction can settle it: the character's own decision.
    character: bool = False
    #: PROMOTE_JUDGE_ENABLED.
    judging: bool = True
    #: The character's reason, when it already looked at this very evidence.
    observed: str = ""

    def waiting_for(self) -> str:
        """Where it stands: the character's decision, or the first count
        more reactions must reach."""
        if not self.auto:
            return "why_off"
        if self.character:
            if not self.judging:
                return "why_judge_off"
            return "why_observing" if self.observed else "why_deciding"
        if self.can_be_strong and self.strong < self.need_strong:
            return "why_strong"
        if self.events < self.need_events:
            return "why_events"
        if not self.speakers_ok:
            return "why_speakers"
        if self.decision.gate == promotion.GATE_PERSON:
            return "why_liked"
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
    strong = [e for e in supporting if promotion.anchors(e, cand)]
    speakers = {str(e.get("speaker_id") or "") for e in supporting} - {""}
    admins = {str(a).strip()[:64] for a in agent._admins()} - {""}
    related = promotion.related_events(cand, log.all())
    character, observed = False, ""
    if cand.get("state") == candidates.STATE_PROPOSED:
        decision = agent._decide_promotion(cand["candidate_id"])
        character = promotion.needs_character(decision, cand)
        if character:
            basis = agent._basis(cand["candidate_id"])
            if basis is not None and agent._judged_on(basis.cand, basis.seen, basis.peers):
                observed = str((basis.cand.get("review") or {}).get("reason") or "")
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
        auto=policy.auto_promote, decision=decision, character=character,
        judging=bool(getattr(agent, "promote_judge_enabled", True)), observed=observed)


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
    #: Set when the judge could not be reached, as opposed to giving no verdict.
    failure: Failure | None = None


@dataclass
class Turn:
    """What one message did."""

    speaker: str
    uid: str
    text: str
    reply: str = ""
    #: The reply as the ledger stores it, stickers unrendered.
    sent: str = ""
    mode: str = ""
    why: str = ""
    count: int = 0
    trigger: int = 0
    window: int = 0
    #: Why it stayed quiet, a key into the text table; "" when it spoke.
    quiet: str = ""
    #: The line was too short to count toward the trigger.
    short: bool = False
    raw: str = ""
    #: Set when the model could not answer; nothing was said and nothing is kept.
    failure: Failure | None = None
    memory: bool = False
    memory_saved: bool = False
    reaction: Reaction | None = None
    retry_of: str = ""
    offered: list = field(default_factory=list)
    conv: str = ""


def _awaiting_fix(agent: Agent, conv: str) -> dict | None:
    """The rejected reply the bot's next reply in `conv` will be a retry for."""
    return agent.pending_reactions.awaiting(conv)


def _names_bot(agent: Agent, text: str) -> bool:
    """The live name-call test (turns.py), so the trial calls when it would."""
    return agent._names_me(text)


@contextlib.contextmanager
def _patched(obj, **wrappers):
    """Wrap methods of one instance for the block; each wrapper gets the original."""
    own = {name: name in vars(obj) for name in wrappers}
    saved = {name: getattr(obj, name) for name in wrappers}
    for name, wrap in wrappers.items():
        setattr(obj, name, wrap(saved[name]))
    try:
        yield
    finally:
        for name in wrappers:
            if own[name]:
                setattr(obj, name, saved[name])
            else:
                delattr(obj, name)


def _collecting(sink: list):
    """A wrapper that appends every result of a sync call to `sink`."""
    def wrap(inner):
        def wrapped(*args, **kwargs):
            out = inner(*args, **kwargs)
            sink.append(out)
            return out
        return wrapped
    return wrap


def _catching(sink: list):
    """A wrapper that notes the exception an async call raises, and re-raises it."""
    def wrap(inner):
        async def wrapped(*args, **kwargs):
            try:
                return await inner(*args, **kwargs)
            except Exception as e:
                sink.append(e)
                raise
        return wrapped
    return wrap


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
        #: False plays every opening the way a person at the keyboard would,
        #: with no random pass and no sleep window.
        self.pacing = True
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
        turn = await self._group_turn(name, uid, text,
                                      self.last_mid if quote else "")
        if quote and turn.reaction is not None:
            self.last_mid = ""
        return turn

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
        errors: list[Exception] = []
        # The judge's failures are swallowed inside, so listen from outside.
        with _patched(agent, _call_llm=_catching(errors)):
            await agent._process_reaction(entry, text, name, uid, is_admin,
                                          conv_id=conv, is_dm=self.dm)
        events = [e for e in agent.evidence_log.all() if e["event_id"] not in seen]
        new_ids = {e["event_id"] for e in events}
        out = Reaction(reply=str(entry.get("reply") or ""),
                       target=str(entry.get("target_name") or ""),
                       events=events, blocked=blocked)
        if errors and not events:
            out.failure = describe_failure(errors[-1])
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
        turn = Turn(speaker=nickname, uid=uid, text=text, conv=conv,
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
        turn.short = not (len(text.strip()) >= 4 or addressed)
        if not turn.short:
            agent.counters[conv] += 1

        if addressed:
            notes = len(agent.memories.get(conv, []))
            mem_reply = agent._handle_memory_command(conv, ctrl_text, uid, nickname)
            if mem_reply is not None:
                turn.mode, turn.memory = "memory", True
                turn.memory_saved = len(agent.memories.get(conv, [])) > notes
                turn.reply = turn.sent = TextProcessing._sanitize_reply(
                    mem_reply, agent.agent_lang, agent.reply_style)
                agent._spoke_in(conv)
                agent._append_buffer(conv, agent.persona_name, mem_reply)
                self.last = turn
                return turn

        never_replied = agent.last_reply_at[conv] == 0.0
        turn.count = agent.counters[conv]
        mode, why = choose_group_mode(
            addressed=addressed, is_admin=is_admin, sticky_admin=None,
            in_followup=agent._followup_open(conv, uid),
            counter=turn.count, trigger_count=agent.chat_trigger_count,
            never_replied=never_replied)
        if mode == "followup" and turn.short:
            # As live: a "lol" in the window takes no turn and no gate call.
            mode, why = "", "below the trigger count"
        turn.mode, turn.why = mode, why
        if not mode:
            turn.quiet = "below"
            return turn
        agent.counters[conv] = 0
        skip = (pacing_skip(mode, first_appearance=never_replied,
                            sleep_hour=TextProcessing._is_sleep_hour())
                if self.pacing else "")
        if skip:
            turn.quiet = "sleep" if skip == "sleep window" else "skip"
            return turn

        self._gate_verdict = None
        blocks: list[str] = []
        try:
            with _patched(agent, _examples_for_prompt=_collecting(blocks)):
                reply, intent, auto_mem = await agent._think(conv, mode, text)
        except Exception as e:
            # Not a decision: the count it spent goes back.
            agent.counters[conv] = turn.count
            turn.failure = describe_failure(e)
            return turn
        if mode in GATED_MODES and self._gate_verdict is False:
            turn.quiet = "gate_pass"
            if mode == "followup":
                agent._followup_pass(conv, uid)
            return turn
        return self._commit_group(turn, reply, intent, auto_mem, blocks)

    def _commit_group(self, turn: Turn, raw: str, intent: str,
                      auto_mem: str, blocks: list[str]) -> Turn:
        agent, conv = self.agent, self.conv
        final = agent._finalize_reply(raw, log_ctx=f"trial mode={turn.mode}")
        if final is None:
            turn.quiet = "filter"
            return turn
        reply, at_uid, pending_core, had_visible = final
        if not at_uid and turn.mode in ("called", ADMIN_MODE):
            at_uid = turn.uid
        if had_visible and not reply:
            turn.quiet, turn.raw = "character", clip(raw, 60)
            return turn
        if not reply or is_pass_sentinel(reply):
            turn.quiet = "pass"
            if turn.mode == "followup":
                agent._followup_pass(conv, turn.uid)
            return turn
        sent = TextProcessing._sanitize_reply(
            reply, agent.agent_lang, agent.reply_style)
        if not sent:
            turn.quiet, turn.raw = "character", clip(reply, 60)
            return turn
        context = [f"{m['name']}: {m['text']}" for m in list(agent.buffers[conv])[-5:]]
        awaiting = _awaiting_fix(agent, conv)
        agent._spoke_in(conv)
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
        turn.reply, turn.sent = _render(sent), sent
        turn.offered = self.offered(conv, blocks)
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
        turn = Turn(speaker=name, uid=uid, text=text, conv=conv,
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
        failures: list[Exception] = []
        recorded: list[dict] = []
        blocks: list[str] = []

        def spy_record(inner):
            def wrapped(conv_key, **kwargs):
                recorded.append(kwargs)
                return inner(conv_key, **kwargs)
            return wrapped
        try:
            # The handler answers a failed call with an excuse in the persona's
            # voice; that is not a reply, so listen for the failure itself.
            with _patched(agent, _chat_dm=_catching(failures),
                          _examples_for_prompt=_collecting(blocks)), \
                    _patched(agent.pending_reactions, record=spy_record):
                await agent._handle_dm(uid, payload, is_admin=is_admin)
        except Exception as e:
            failures.append(e)
        finally:
            sink.closed = True
            current_sink.reset(token)
        if failures:
            turn.failure = describe_failure(failures[-1])
            return turn
        said = [item.get("text", "") for item in sink.items
                if item.get("type") == "text" and item.get("text")]
        if not said:
            turn.quiet = "dm_none"
            return turn
        turn.reply = "\n".join(said)
        turn.sent = str(recorded[-1].get("reply") or "") if recorded else turn.reply
        if awaiting and _awaiting_fix(agent, conv) is None:
            turn.retry_of = str(awaiting.get("reply") or "")
        turn.offered = self.offered(conv, blocks)
        self.last = turn
        return turn

    # -- reading back ----------------------------------------------------------

    def offered(self, conv: str, blocks: list[str]) -> list[dict]:
        """Learned rows from this chat that were in the prompt: those whose
        text is in the examples block the turn's own prompt build produced."""
        agent = self.agent
        if not blocks:
            return []
        agent._reload_views_if_stale()
        scope = agent._live_scope(conv)
        rows = [r for r in agent._view_pairs_cache + agent._view_examples_cache
                if agent._scope_authorizes(r.get("scope"), scope)]
        used = "\n".join(blocks)
        return [r for r in rows
                if _example_field(r.get("better") or r.get("reply") or "") in used]

    async def probe(self, name: str, uid: str, text: str) -> Turn:
        """What it would answer to `text` in this chat now, from a clean
        context, without the chat seeing it."""
        agent, conv = self.agent, self.conv
        turn = Turn(speaker=name, uid=uid, text=text, mode="called", conv=conv)
        saved = agent.buffers.pop(conv, None)
        blocks: list[str] = []
        try:
            agent._append_buffer(conv, name, text, uid)
            with _patched(agent, _examples_for_prompt=_collecting(blocks)):
                reply, _intent, _mem = await agent._think(
                    conv, "called", text, caller_override=(name, uid))
        finally:
            agent.buffers.pop(conv, None)
            if saved is not None:
                agent.buffers[conv] = saved
        final = agent._finalize_reply(reply, log_ctx="trial probe")
        turn.reply = _render(final[0]) if final else ""
        if not turn.reply or is_pass_sentinel(turn.reply):
            turn.reply, turn.quiet = "", "pass"
        turn.offered = self.offered(conv, blocks)
        return turn

    def about(self, turn: Turn) -> tuple[list[dict], list[dict]]:
        """Ledger events and candidates about the reply `turn` made, in its own
        chat, oldest first."""
        reply, conv = turn.sent.strip(), turn.conv
        events = [e for e in self.agent.evidence_log.all()
                  if e.get("conv_id") == conv
                  and (str(e.get("reply") or "").strip() == reply
                       or str((e.get("adjudication") or {}).get("better") or "").strip() == reply)]
        cands = [c for c in self.agent.candidate_ledger.all()
                 if (c.get("scope") or {}).get("conv_id") == conv
                 and reply in (str(c.get("reply") or "").strip(),
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
    counts = {"count": turn.count, "trigger": turn.trigger, "window": turn.window,
              "messages": plural(lang, turn.count, "message", "messages")}
    base = {"below the trigger count": t["below"], "trigger count": t["trigger_count"],
            "first appearance": t["first_appearance"],
            "followup window": t["followup"]}.get(turn.why, "").format(**counts)
    if turn.quiet == "below":
        return t["short"].format(**counts) if turn.short else base
    if turn.quiet == "gate_pass":
        return t["gate_pass"].format(why=base)
    if turn.mode in GATED_MODES and not turn.quiet:
        return t["gate_speak"].format(why=base)
    key = turn.quiet
    if key in ("sleep", "skip", "pass", "filter", "dm_none"):
        return t[key].format(name=name)
    if key == "character":
        return t["character"].format(raw=f'"{turn.raw}"' if turn.raw else "")
    return base


def held_reason(lang: str, check: Checklist) -> str:
    t = text_for(lang)
    key = check.waiting_for()
    if not key:
        return t["why_other"] or check.decision.reason
    need = {"why_strong": check.need_strong, "why_events": check.need_events,
            "why_speakers": check.need_speakers}.get(key, 0)
    return t[key].format(strong=check.strong, need=need, events=check.events,
                         speakers=check.speakers, reason=check.observed)


def decided_reason(lang: str, cand: dict) -> str:
    """Who settled a decided item, when it was not a person or the counts:
    the character with its reason, or the time limit."""
    t = text_for(lang)
    last = (cand.get("history") or [{}])[-1]
    if last.get("actor") == candidates.ACTOR_CHARACTER and last.get("reason"):
        return t["by_character"].format(reason=last["reason"])
    if (last.get("actor") == candidates.ACTOR_AUTO
            and last.get("judge") == candidates.JUDGE_EXPIRY):
        return t["by_time"]
    return ""


def promoted_line(lang: str, check: Checklist) -> str:
    t = text_for(lang)
    return t["promoted"].format(
        events=check.events, strong=check.strong,
        reactions=plural(lang, check.events, "reaction", "reactions"),
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


def trace(lang: str, r: Reaction, doctor: str | None = None) -> str:
    """A reaction's one-line learning trace."""
    t = text_for(lang)
    if not r.events:
        if r.failure is not None:
            text = t["judge_failed"].format(
                why=failure_text(lang, r.failure, doctor))
        else:
            text = t["blocked_teacher" if r.blocked else "no_verdict"]
        return t["learning"].format(text=text)
    verdicts = t["and"].join(judged(lang, e) for e in r.events)
    if r.promoted:
        outcome = promoted_line(lang, r.promoted[0][1])
    elif r.rolled_back:
        outcome = t["rolled_back"].format(
            n=r.rolled_back, rows=plural(lang, r.rolled_back, "row", "rows"))
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
    elif decided_reason(lang, cand):
        line += f" ({decided_reason(lang, cand)})"
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
    events, cands = trial.about(turn)
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
            memory_tidy_every=0,
        )
        agent = Agent(settings)
    finally:
        if saved is None:
            os.environ.pop("AGENT_RUNTIME_DIR", None)
        else:
            os.environ["AGENT_RUNTIME_DIR"] = saved
    return agent, state


class ChatSession:
    """The terminal side: parses a line, runs it, prints what happened."""

    def __init__(self, trial: Trial, *, lang: str, you: str, admin: bool,
                 live_trigger: int, resumed: bool = False, name_unset: bool = False,
                 name_ignored: bool = False) -> None:
        self.trial = trial
        self.resumed = resumed
        self.name_unset = name_unset
        self.name_ignored = name_ignored
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
        print(head.format(name=self.name, model=agent.model, lang=self.lang))
        print(t["you_are_dm" if self.trial.dm else "you_are"].format(
            you=self.you[0], name=self.name))
        if self.name_ignored:
            print(t["admin_name"].format(admin=self.you[0]))
        if self.name_unset:
            print(t["name_unset"].format(name=self.name, env=paths.ROOT / ".env"))
        if not self.trial.dm:
            print(t["trigger"].format(
                name=self.name, n=agent.chat_trigger_count, live=self.live_trigger,
                messages=plural(self.lang, agent.chat_trigger_count,
                                "message", "messages")))
        if self.trial.state_dir is not None:
            print(t["state"].format(path=str(self.trial.state_dir) + os.sep,
                                    learned=hint("learned", self.lang)))
            if self.resumed:
                print(t["resumed"])
        self.commands()

    def commands(self) -> None:
        print()
        for cmd, desc in self.t["commands"]:
            print(f"  {cmd}{' ' * max(1, 16 - langs.width(cmd))}{desc.format(name=self.name)}")
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
        if command in ("/admin", "/reply") and not rest.strip():
            print("  " + self.t["usage_admin" if command == "/admin" else "usage_reply"])
            return True
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
            print("  " + self.t["unknown"].format(cmd=command))
            self.commands()
            return True
        if not msg.strip():
            return True
        try:
            turn = await self.trial.say(name, uid, msg.strip(), quote=quote)
        except Exception as e:
            print("  " + self.t["error"].format(
                error=failure_text(self.lang, describe_failure(e))))
            return True
        self.show(turn)
        return True

    def show(self, turn: Turn) -> None:
        t = self.t
        if turn.reaction is not None:
            print("  " + trace(self.lang, turn.reaction))
        if turn.failure is not None:
            print("  " + t["error"].format(
                error=failure_text(self.lang, turn.failure)))
        elif turn.reply:
            if turn.mode in GATED_MODES:
                print("  " + t["joins"].format(
                    name=self.name, reason=reason(self.lang, turn, self.name)))
            for out in turn.reply.splitlines():
                print(f"  {self.name} > {out}")
        elif turn.quiet:
            print("  " + t["quiet"].format(
                name=self.name, reason=reason(self.lang, turn, self.name)))
        print()


async def main(argv: list[str] | None = None, prog: str | None = None) -> int:
    langs.utf8_console()
    home.load_env()
    p = argparse.ArgumentParser(
        prog=prog, description=langs.term("Talk to the character in a simulated group chat."))
    from persona_agent.setup_wizard import lang_option

    p.add_argument("--lang", type=lang_option, default=None,
                   help=langs.term("language code: " + ", ".join(langs.CODES) + " (default: en)"))
    p.add_argument("--admin", action="store_true",
                   help=langs.term("speak as the configured admin (closer relationship)"))
    p.add_argument("--name", default=None, help=langs.term("your display name in the chat"))
    p.add_argument("--dm", action="store_true",
                   help=langs.term("a one-to-one chat instead of a group"))
    p.add_argument("--trigger", type=int, default=TRIAL_TRIGGER,
                   help=langs.term(f"messages before it considers joining in (default "
                        f"{TRIAL_TRIGGER}; the live bot uses CHAT_TRIGGER_COUNT)"))
    args = p.parse_args(argv)
    lang = args.lang or normalize_lang(os.getenv("AGENT_LANG", "en"))
    trigger = max(1, args.trigger)

    live = AgentSettings.from_env(lang=lang)
    if not live.api_key.strip():
        # Before anything is built: a home without a key gets no trial folder.
        print(text_for(lang)["no_key"].format(init=hint("init", lang),
                                              demo=hint("demo", lang)))
        return 1
    trial_dir = paths.runtime_dir() / TRIAL_DIR
    resumed = trial_dir.is_dir() and any(trial_dir.iterdir())
    agent, state = build_agent(lang, trigger)
    trial = Trial(agent, dm=args.dm, state_dir=state,
                  factory=lambda: build_agent(lang, trigger)[0])
    session = ChatSession(
        trial, lang=lang, you=args.name or text_for(lang)["you"], admin=args.admin,
        live_trigger=live.chat_trigger_count, resumed=resumed,
        name_unset=not os.getenv("PERSONA_NAME", "").strip(),
        name_ignored=args.admin and args.name is not None)
    session.banner()
    # The trial words every failure itself; the agent's log lines would repeat it.
    logger = logging.getLogger("agent")
    level = logger.level
    logger.setLevel(logging.CRITICAL)
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
        logger.setLevel(level)
        await trial.agent.aclose()


def run(argv: list[str] | None = None, prog: str | None = None) -> int:
    try:
        return asyncio.run(main(argv, prog))
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(run())
