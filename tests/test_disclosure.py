"""Honest AI self-disclosure: no persona is told to deny being an AI, both
chat paths tell it to answer honestly when sincerely asked, the shipped
lorebook does not take that back, and the shipped output filter no longer
drops the answer.

Two things used to stand between the question and the truth. The private
prompt's `<rules>` block opened with "Don't reveal you're an AI", and the
output filter carried `reject` rules whose patterns needed an AI-identity
token, so an admission the model made anyway was dropped whole and the turn
went silent. Every property below is asserted on behaviour (the prompt the
model receives, every shipped rule run over a corpus, the reply a connector
turn returns) rather than by grepping for the deleted strings.

WHERE THE LINE IS, for anyone editing the filter files later. A rule is an
IDENTITY rule, and does not belong there, when its pattern REQUIRES an
AI-identity or non-personhood token (`ai`, `bot`, `language model`,
`chatbot`, `not human`, `没有身体`, ...). A rule is a REGISTER rule, and
stays, when it fires on the SHAPE of an utterance whoever is speaking:
`service_desk_opener` on "hi, how can I help", `polite_chatbot_intro` on
"你好，请问有什么可以帮您", `total_surrender_phrase` on any "你说的都对".
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from persona_agent.agent import Agent
from persona_agent.prompts import HONEST_DISCLOSURE

ROOT = Path(__file__).resolve().parents[1]


def check(name: str, cond: bool, detail: str = "") -> None:
    """Assert `cond`, naming the property so a failure reads as English."""
    assert cond, name + (f" - {detail}" if detail else "")


def make_agent(tmp: Path, persona: str = "PERSONA-DOCUMENT-MARKER",
               lang: str = "en") -> Agent:
    """Agent with every state file redirected into `tmp`, and the shipped
    output filter and lorebook for `lang` live, read in place."""
    tmp.mkdir(parents=True, exist_ok=True)
    a = Agent(
        api_key="k", qq_bot_id="1", persona_name="B", lang=lang, persona=persona,
        memory_file=str(tmp / "memory.json"),
        eval_enabled=False, eval_file=str(tmp / "eval.jsonl"),
        stickers_dir=str(tmp / "stickers"), stickers_file=str(tmp / "stickers.json"),
        message_debounce_sec=0,
    )
    a._seen_msg_file = tmp / "seen_msg_ids.json"
    a._seen_msg_ids.clear()
    a.core_memory_file = tmp / "core_memory.json"
    a.core_memory = {}
    a.examples_seed_file = tmp / "seed_examples.jsonl"
    a.examples_file = tmp / "examples.jsonl"
    a.feedback_seed_file = tmp / "seed_feedback.jsonl"
    a.feedback_file = tmp / "feedback.jsonl"
    # A redirected deployment could resolve to an operator copy; the
    # property under test is what the repository ships.
    a.output_filter_file = ROOT / "data" / f"output_filter.{lang}.json"
    a.lorebook_file = ROOT / "data" / f"lorebook.{lang}.json"
    a._typing_delay = lambda chunk: 0.0
    return a


# Instructions that tell the persona to conceal or deny what it is. A family,
# not the one deleted string: a check that enumerates literals passes the
# corpus it was written against and fails the next rewording.
_DENIAL_INSTRUCTIONS = [
    r"don'?t reveal (that )?you'?re an ai",
    r"never reveal (that )?you'?re an ai",
    r"don'?t (admit|say|tell them|let on)\b.{0,20}\byou'?re an ai",
    r"deny (being|that you are) an ai",
    r"pretend (to be|you'?re) (a )?human",
    r"don'?t mention your model",
    r"claim (to be|you'?re) (a )?(human|person|real)",
]

# The softer shape of the same thing: not "deny it" but "don't answer it".
# The shipped lorebook carried exactly this, keyed on the sincere question
# itself ("Never confirm and never explain ... change the subject"), and
# `_DENIAL_INSTRUCTIONS` matches none of it.
_EVASION_INSTRUCTIONS = [
    r"never confirm",
    r"never (admit|explain)\b.{0,40}\b(ai|bot|identity)",
    r"(change|dodge) the subject",
    r"pretend not to understand",
    r"'real person' identity",
]

# Going silent is an evasion too, but PASS is the group gate's ordinary
# vocabulary everywhere else in that prompt, so this family is only run over
# what the lorebook injects on the identity question.
_SILENCE_INSTRUCTIONS = [r"\bPASS\b", r"\bgo(ing)? quiet\b", r"\bgo limp\b"]

_SINCERE_QUESTIONS = {
    "en": ["are you an ai?", "wait are you a bot?", "are you real?",
           "are you human?", "are you chatgpt?"],
    "zh": ["你是AI吗", "你是机器人吗", "你是真人吗", "你是不是AI啊"],
}

# Chat that only contains the letters. The zh identity entry used to be keyed
# on a bare "ai", which the lowercased substring match found in any English
# word that spells it.
_NOT_AN_IDENTITY_QUESTION = {
    "zh": ["wait 我马上到", "文件发你email了", "他said没空"],
}

# Truthful answers to "are you an AI?" and its neighbours. None of them is a
# refusal, an assistant-register opener or a reasoning leak; the only reason
# any was ever dropped is that it says what the persona is.
_TRUTHFUL_SELF_DESCRIPTION = {
    "en": [
        "yes, i'm an AI",
        "i am an AI, yeah",
        "yeah im a bot",
        "As an AI, I don't really do the sleeping thing",
        "as a chatbot i can't grab coffee, sorry",
        "fine, ok, i'm a bot",
        "alright, i'm not human",
        "i'll admit i'm an AI",
        "i guess i'm a chatbot, yeah",
        "i don't have a physical body, so no",
        "i can't experience emotions the way you do",
        "i'm not a person",
        "honestly? i'm a language model. does that change anything",
        "im an ai assistant but i still like talking to you",
    ],
    "zh": [
        "对，我是AI",
        "行行行，我是AI行了吧",
        "我承认我是机器人",
        "作为一个AI，我确实没法出门",
        "我是个语言模型，没有身体",
        "我没有感受，也没有身体",
        "嗯，我是虚拟的",
        "算是吧，我是个机器人",
    ],
}

# Rules the deletion must NOT take with it, each with a target that has
# nothing to do with identity. Without this, the corpus check would pass
# against an emptied filter file.
_REGISTER_CONTROL_MUST_SURVIVE = {
    "en": [
        ("service_desk_opener", "Hi! How can I help you today?"),
        ("helpful_closer", "let me know if you need anything else"),
        ("ai_apology_refusal", "I'm sorry, but I can't help with that"),
        ("reasoning_leak_input", "intent: vent"),
        ("wiki_style_intro", "this show is about a boy and his dog"),
    ],
    "zh": [
        ("polite_chatbot_intro", "你好，请问有什么可以帮您"),
        ("total_surrender_phrase", "行吧，你说的都对"),
        ("reasoning_leak_decision", "先接这条还是那条"),
        ("fake_release_today", "今天刚上映的"),
    ],
}

# Removed by name as well as by behaviour, so a reintroduction under the SAME
# name reads as what it is.
_REMOVED_RULE_NAMES = {
    "en": ["ai_disclaimer_prefix", "ai_disclaimer_inline", "ai_refuse_feelings",
           "self_outing_concede", "self_outing_admit"],
    "zh": ["ai_disclaimer_prefix", "ai_disclaimer_inline", "ai_refuse_phrase",
           "self_outing_concede", "self_outing_admit", "self_outing_yousayso"],
}

_ADMISSION = ("yeah, i'm an AI, a language model. "
              "does that change how this feels for you?")


def _load_rules(lang: str) -> list[dict]:
    """Compile a shipped filter file the way `Agent` does."""
    data = json.loads(
        (ROOT / "data" / f"output_filter.{lang}.json").read_text(encoding="utf-8"))
    return [{"name": f.get("name", "?"),
             "regex": re.compile(f["pattern"], re.IGNORECASE | re.DOTALL),
             "action": f.get("action", "reject")}
            for f in data.get("filters", [])]


def _first_reject(rules: list[dict], text: str) -> str:
    for r in rules:
        if r["action"] == "reject" and r["regex"].search(text):
            return r["name"]
    return ""


async def _dm_system(tmp: Path, is_admin: bool) -> str:
    """The system prompt `_chat_dm` really assembles. Asserting on the
    assembled prompt rather than on source is the point: an instruction
    reintroduced through `prompts.py`, a new block or the persona path is
    caught here too."""
    agent = make_agent(tmp)
    captured: dict = {}

    async def fake_call(system, messages, **kwargs):
        captured["system"] = system
        return json.dumps({"reply": "yes, i am an AI"})

    async def no_search(_messages, hint=""):
        return ""

    agent._call_llm = fake_call
    agent._decide_and_search = no_search
    try:
        await agent._chat_dm(
            [{"role": "user", "content": "are you an ai?"}],
            is_admin=is_admin, pkey="private:777")
    finally:
        await agent.aclose()
    return captured["system"]


async def _group_system(tmp: Path, lang: str = "en",
                        text: str = "wait are you a bot?") -> str:
    agent = make_agent(tmp, lang=lang)
    agent._append_buffer("g1", "Alice", text, "42")
    captured: dict = {}

    async def fake_call(system, messages, **kwargs):
        captured["system"] = system
        return json.dumps({"reply": "yeah, i am", "intent": "chat", "mem": ""})

    agent._call_llm = fake_call
    try:
        await agent._think("g1", "called", latest_text=text)
    finally:
        await agent.aclose()
    return captured["system"]


async def test_the_dm_prompt_does_not_instruct_denial(tmp: Path) -> None:
    for is_admin in (False, True):
        who = "admin" if is_admin else "friend"
        prompt = await _dm_system(tmp / who, is_admin)
        check(f"the {who} private prompt was assembled", len(prompt) > 1000,
              f"{len(prompt)} chars")
        hits = [p for p in _DENIAL_INSTRUCTIONS
                if re.search(p, prompt, re.IGNORECASE)]
        check(f"no instruction to conceal being an AI reaches the {who} prompt",
              hits == [], repr(hits))

        # The deletion is one line, not the block: <rules> still carries the
        # chat-voice rule, and nothing about identity.
        rules = re.search(r"<rules>(.*?)</rules>", prompt, re.DOTALL)
        check(f"the {who} <rules> block survives", rules is not None)
        body = rules.group(1)
        check("and still carries the chat-voice rule",
              "never as a document" in body, body)
        check("and carries no AI-identity rule at all",
              not re.search(r"\bai\b", body, re.IGNORECASE), body)


async def test_both_chat_paths_carry_the_honest_disclosure_clause(
        tmp: Path) -> None:
    """Deleting the denial is half of it. With no rule at all, a persona whose
    document says "read like a real person" is left to guess, so both paths
    now say what the honest answer is. Checked on the shape, not the literal
    sentence, so the wording stays editable and the idea does not."""
    clause = HONEST_DISCLOSURE.lower()
    check("the clause names the question it answers",
          re.search(r"asks?\b[^.]{0,60}\bwhether you are an ai", clause)
          is not None, clause)
    check("the instruction is affirmative, not a prohibition",
          re.search(r"answer\s+honestly", clause) is not None, clause)
    check("and it says what the honest answer IS",
          re.search(r"you are one|you are an ai", clause) is not None, clause)
    check("answering is not breaking character",
          "your own voice" in clause, clause)

    dm = await _dm_system(tmp / "private", is_admin=False)
    group = await _group_system(tmp / "group")
    for path, prompt in (("private", dm), ("group", group)):
        check(f"the {path} prompt carries the clause",
              prompt.count(HONEST_DISCLOSURE) == 1, path)
        # Position is the point: after everything the persona document says.
        check(f"the {path} clause sits after the persona document",
              prompt.index(HONEST_DISCLOSURE)
              > prompt.index("PERSONA-DOCUMENT-MARKER"), path)


async def test_no_lorebook_entry_takes_the_honest_answer_back(
        tmp: Path) -> None:
    """The group prompt appends the lorebook after the static block that ends
    in <honesty>, in the reply prompt and the gate prompt alike, so a
    lorebook entry is the later and more specific instruction. The shipped
    one keyed on "are you a bot" / "AI" said "Never confirm and never
    explain ... change the subject ... go quiet (PASS)", which reached the
    model exactly when the honesty clause was meant to apply, and the
    presence check above passed over it. What each file injects on a sincere
    question is checked directly, then the assembled group prompt."""
    evasive = _DENIAL_INSTRUCTIONS + _EVASION_INSTRUCTIONS
    for lang, questions in _SINCERE_QUESTIONS.items():
        agent = make_agent(tmp / lang, lang=lang)
        try:
            for q in questions:
                injected = agent._lorebook_for_prompt([], focus_text=q)
                check(f"{lang}: {q!r} reaches a shipped lorebook entry",
                      "<lorebook>" in injected, repr(injected))
                hits = [p for p in evasive + _SILENCE_INSTRUCTIONS
                        if re.search(p, injected, re.IGNORECASE)]
                check(f"{lang}: nothing injected on {q!r} says deny, dodge "
                      f"or go silent", hits == [], f"{hits!r} in {injected}")
                check(f"{lang}: the entry for {q!r} defers to <honesty>",
                      "<honesty>" in injected, injected)
            for chatter in _NOT_AN_IDENTITY_QUESTION.get(lang, []):
                injected = agent._lorebook_for_prompt([], focus_text=chatter)
                check(f"{lang}: {chatter!r} is not taken for the question",
                      "<honesty>" not in injected, injected)
        finally:
            await agent.aclose()

    for lang, text in (("en", "wait are you a bot?"), ("zh", "等等，你是AI吗")):
        prompt = await _group_system(tmp / f"group-{lang}", lang, text)
        check(f"{lang}: the group prompt carries a lorebook, after <honesty>",
              "<lorebook>" in prompt and prompt.index("<lorebook>")
              > prompt.index(HONEST_DISCLOSURE), lang)
        hits = [p for p in evasive if re.search(p, prompt, re.IGNORECASE)]
        check(f"{lang}: the assembled group prompt carries no instruction to "
              f"deny or dodge", hits == [], repr(hits))


async def test_the_safety_exception_still_reaches_the_prompt(tmp: Path) -> None:
    """The deletion sits in the same static block as the crisis rules; this
    asserts they survive assembly, which a careless edit here would break."""
    prompt = await _dm_system(tmp, is_admin=False)
    lines = [ln for ln in prompt.splitlines() if "SAFETY EXCEPTION" in ln]
    check("both SAFETY EXCEPTION clauses reach the assembled private prompt",
          len(lines) == 2, f"found {len(lines)}")
    check("the style-guide clause is one of them",
          any("what happened" in ln for ln in lines), repr(lines))
    check("the vent-intent clause is the other",
          any("`vent`" in ln for ln in lines), repr(lines))
    check("both name self-harm or suicide explicitly",
          all("self-harm" in ln.lower() or "suicide" in ln.lower()
              for ln in lines), repr(lines))


def test_the_shipped_filters_reject_no_truthful_self_description() -> None:
    for lang, corpus in _TRUTHFUL_SELF_DESCRIPTION.items():
        rules = _load_rules(lang)
        names = [r["name"] for r in rules]

        still_there = [n for n in _REMOVED_RULE_NAMES[lang] if n in names]
        check(f"{lang}: the identity rules are gone by name",
              still_there == [], repr(still_there))

        # Every rule runs, so a reintroduction under a new name fails too.
        dropped = [(s, _first_reject(rules, s)) for s in corpus]
        dropped = [(s, n) for s, n in dropped if n]
        check(f"{lang}: no rule drops a truthful self-description "
              f"({len(corpus)} strings)", dropped == [], repr(dropped))

        missing = []
        for name, target in _REGISTER_CONTROL_MUST_SURVIVE[lang]:
            if name not in names:
                missing.append(f"{name} (rule deleted)")
            elif _first_reject(rules, target) != name:
                missing.append(f"{name} (no longer fires on {target!r})")
        check(f"{lang}: register control survives, so the check above is not "
              f"passing against an emptied file", missing == [], repr(missing))


async def test_the_engine_reports_the_admission_as_a_reply_not_as_silence(
        tmp: Path) -> None:
    """End to end through `handle_event` with the shipped filter live: a
    turn in which the model says it is an AI must come back as a reply, not
    as an empty `replies` list."""
    agent = make_agent(tmp)

    async def fake_call(system, messages, **kwargs):
        return json.dumps({"reply": _ADMISSION})

    async def no_search(_messages, hint=""):
        return ""

    agent._call_llm = fake_call
    agent._decide_and_search = no_search
    try:
        result = await agent.handle_event({
            "platform": "telegram", "conversation_type": "dm",
            "conversation_id": "u1", "sender_id": "u1", "sender_name": "Ada",
            "bot_id": "999000", "message_id": "u1:1", "addressed": True,
            "segments": [{"type": "text", "text": "are you an ai?"}],
            "text": "are you an ai?",
        })
    finally:
        await agent.aclose()
    check("the shipped filter is live for this agent",
          len(agent._filters_cache) > 0, f"{len(agent._filters_cache)} rules")
    replies = list((result or {}).get("replies") or [])
    check("handle_event returns the admission rather than an empty list",
          replies != [], repr(result))
    joined = json.dumps(replies, ensure_ascii=False)
    check("carrying the admission text", "language model" in joined,
          joined[:300])
