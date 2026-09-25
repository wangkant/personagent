"""The 1:1 register: a DM persona is company, not a service.

`[COMPANY, NOT SERVICE]` and `[CONTINUITY]` in `private_style_guide` are
unconditional text, which is why they are checked over the WHOLE knob space
rather than over the default style: the failure is not a persona choosing
badly (no knob offers "be a service"), it is a later edit moving a section
inside a `_variant(...)` table, or a new variant in a table between them
dropping what follows. Both ship green against one style and fail here."""
from __future__ import annotations

import itertools
import json
from pathlib import Path

from persona_agent.agent import Agent
from persona_agent.prompts import (
    HONEST_DISCLOSURE,
    INTENT_RULES,
    PRIVATE_TOOL_GUIDE,
    REASONING_PROTOCOL,
    STYLE_GUIDE,
    STYLE_KNOBS,
    PersonaStyle,
    private_intent_rules,
    private_output_protocol,
    private_style_guide,
)


def check(name: str, cond: bool, detail: str = "") -> None:
    """Assert `cond`, naming the property so a failure reads as English."""
    assert cond, name + (f" - {detail}" if detail else "")


def make_agent(tmp: Path) -> Agent:
    """Agent with every state file redirected into `tmp`. The persona is a
    stub: the bundled example is the operator's text, and what these suites
    own is the text the engine writes around it."""
    tmp.mkdir(parents=True, exist_ok=True)
    a = Agent(
        api_key="k", qq_bot_id="1", persona_name="B", lang="en", persona="test persona",
        memory_file=str(tmp / "memory.json"),
        eval_enabled=False, eval_file=str(tmp / "eval.jsonl"),
        stickers_dir=str(tmp / "stickers"), stickers_file=str(tmp / "stickers.json"),
    )
    a._seen_msg_file = tmp / "seen_msg_ids.json"
    a.core_memory_file = tmp / "core_memory.json"
    a.core_memory = {}
    a.examples_seed_file = tmp / "seed_examples.jsonl"
    a.examples_file = tmp / "examples.jsonl"
    a.feedback_seed_file = tmp / "seed_feedback.jsonl"
    a.feedback_file = tmp / "feedback.jsonl"
    return a


def _every_style() -> list[PersonaStyle]:
    """Every combination of the knobs, built from `STYLE_KNOBS` so a knob or
    a value added later is covered on the commit that adds it."""
    knobs = sorted(STYLE_KNOBS)
    return [PersonaStyle(**dict(zip(knobs, values)))
            for values in itertools.product(*(STYLE_KNOBS[k] for k in knobs))]


def _assembled_private_prompt(style: PersonaStyle) -> str:
    """Every block of the 1:1 system prompt a `PersonaStyle` can change, in
    served order."""
    return "\n\n".join((private_style_guide(style),
                        private_intent_rules(style),
                        PRIVATE_TOOL_GUIDE,
                        private_output_protocol(style)))


async def _served_private_prompts(tmp: Path) -> dict[str, str]:
    """The whole system prompt `_chat_private` sends, for the owner and for
    anyone else: the engine-authored rest of it (overrides, `<rules>`, the
    sticker guide) is where a banned phrase would slip back in unnoticed."""
    agent = make_agent(tmp)
    captured: list = []

    async def fake_call(system, messages, **kwargs):
        captured.append(system)
        return json.dumps({"reply": "mhm"})

    async def no_search(_messages, hint=""):
        return ""

    agent._call_llm = fake_call
    agent._decide_and_search = no_search
    served = {}
    try:
        for who, is_owner in (("friend", False), ("owner", True)):
            await agent._chat_private([{"role": "user", "content": "hey"}],
                                      is_owner=is_owner, pkey="private:7")
            served[who] = captured[-1]
    finally:
        await agent.aclose()
    return served


#: The phrases the register bans, in both languages a reply is written in: a
#: zh build reads the same guide, and an English-only ban would leave it
#: closing every turn like a support ticket.
BANNED_ASSISTANT_PHRASES = (
    "Is there anything else",
    "I'm here to help",
    "Let me know if",
    "有什么我可以帮你的",
    "还有什么需要我帮忙的",
    "有需要随时告诉我",
)

#: The header of the one section allowed to contain those strings.
COMPANY_HEADER = "[COMPANY, NOT SERVICE]"


def _section(guide: str, header: str) -> str:
    """One `[HEADER]` section of the style guide, header line included: from
    its header to the next line opening a bracket at column 0, or `""`."""
    lines = guide.splitlines()
    starts = [i for i, line in enumerate(lines) if line.startswith(header)]
    if not starts:
        return ""
    start = starts[0]
    end = next((i for i, line in enumerate(lines[start + 1:], start + 1)
                if line.startswith("[")), len(lines))
    return "\n".join(lines[start:end])


def test_the_companionship_register_survives_every_knob_combination() -> None:
    """Each anchor is a distinct rule, pinned by a phrase short enough to
    survive rewording and specific enough that deleting the rule deletes it.
    The crisis safety exception is re-checked too: these sections sit on
    both sides of the emotional-scenes block, and "the exception survived
    when its neighbours moved" is the property at risk."""
    styles = _every_style()
    check("the knob space really is the full cross product",
          len(styles) == 216 and len(set(map(repr, styles))) == len(styles),
          f"{len(styles)} styles")

    anchors = (
        # [COMPANY, NOT SERVICE]
        (COMPANY_HEADER, "the section header"),
        ("Never open with an offer of help", "no opening offer of help"),
        ("Don't summarize their message back at them", "no read-back"),
        ("Don't end every turn with a question", "not every turn a question"),
        ("You have a life offscreen", "a day of your own is fair game"),
        ("A silence-adjacent reply is a full reply", "'mhm' is a whole reply"),
        ("You are somebody, not a general-purpose engine", "a person, not a tool"),
        ("turning into the tool", "the character never becomes the deliverable"),
        ("You know what this person would know", "knowledge is bounded by the character"),
        # [VOICE]: the two floors under every character
        ("Never win at their expense", "a tease is never a verdict on them"),
        ("Say the thing", "understood on one read"),
        # [WHEN IT IS ABOUT THE TWO OF YOU]
        ("receive it, do not deflect", "affection is received"),
        ("Do not overcorrect into devotion", "and not performed back"),
        # [CONTINUITY]
        ("[CONTINUITY", "the continuity header"),
        ("briefly, once", "raise an open thread briefly and once"),
        ("Never announce that you remembered", "don't narrate the recall"),
        ("never promise to remind them", "no reminder service"),
    )
    missing: dict[str, list[str]] = {}
    unsafe: list[str] = []
    for style in styles:
        assembled = _assembled_private_prompt(style)
        for anchor, label in anchors:
            if anchor not in assembled:
                missing.setdefault(label, []).append(repr(style))
        if not ("SAFETY EXCEPTION" in assembled and "crisis line" in assembled
                and "crisis helpline" in assembled):
            unsafe.append(repr(style))

    for _anchor, label in anchors:
        hits = missing.get(label, [])
        check(f"every one of the {len(styles)} styles carries: {label}",
              not hits, f"{len(hits)} styles missing it, e.g. {hits[:1]}")
    check("...and none of them lost the crisis safety exception",
          not unsafe, f"{len(unsafe)} styles, e.g. {unsafe[:1]}")

    guide = private_style_guide(PersonaStyle())
    voice = _section(guide, "[VOICE")
    check("the floors sit under the teasing licence they bound",
          voice.index("Light teasing only") < voice.index("Never win at")
          and "Say the thing" in voice, voice)
    check("continuity follows DON'T FAKE KNOWING, which it defers to",
          guide.index("[CONTINUITY") > guide.index("[DON'T FAKE KNOWING")
          and "DON'T FAKE KNOWING wins" in _section(guide, "[CONTINUITY"))


async def test_no_assistant_ism_survives_the_assembled_private_prompt(
        tmp: Path) -> None:
    """The banned phrases appear nowhere in the 1:1 prompt except in the one
    section that forbids them. A flat "nowhere" is unsatisfiable, because the
    ban is written by quoting them; so: each occurs exactly once, inside
    `[COMPANY, NOT SERVICE]`, on a line that forbids it, and the prompt with
    that section removed contains none of them in any casing — which is what
    catches an example reply or a protocol line teaching one."""
    styles = _every_style()
    headerless: list[str] = []
    not_once: dict[str, list[str]] = {}
    not_a_ban: dict[str, list[str]] = {}
    leaked: dict[str, list[str]] = {}

    def audit(label: str, assembled: str) -> None:
        section = _section(assembled, COMPANY_HEADER)
        if not section:
            headerless.append(label)
            return
        outside = assembled.replace(section, "\n")
        for phrase in BANNED_ASSISTANT_PHRASES:
            if assembled.count(phrase) != 1 or phrase not in section:
                not_once.setdefault(phrase, []).append(
                    f"{label}: {assembled.count(phrase)} occurrences")
            carrier = [line for line in section.splitlines() if phrase in line]
            if not any("Never" in line or "Don't" in line for line in carrier):
                not_a_ban.setdefault(phrase, []).append(repr(carrier))
            hits = [line for line in outside.splitlines()
                    if phrase.lower() in line.lower()]
            if hits:
                leaked.setdefault(phrase, []).append(f"{label}: {hits[0]!r}")

    for style in styles:
        audit(repr(style), _assembled_private_prompt(style))
    for who, served in (await _served_private_prompts(tmp)).items():
        audit(f"served to the {who}", served)

    check(f"every prompt renders a {COMPANY_HEADER} section",
          not headerless, f"{len(headerless)} without one, e.g. {headerless[:1]}")
    for phrase in BANNED_ASSISTANT_PHRASES:
        check(f"{phrase!r} is written exactly once, inside the section that "
              f"bans it", phrase not in not_once,
              repr(not_once.get(phrase, [])[:1]))
        check(f"...on a line that FORBIDS it rather than demonstrating it — "
              f"{phrase!r}", phrase not in not_a_ban,
              repr(not_a_ban.get(phrase, [])[:1]))
        check(f"...and nowhere else in the 1:1 prompt, in any casing — "
              f"{phrase!r}", phrase not in leaked,
              repr(leaked.get(phrase, [])[:1]))


async def test_a_tool_shaped_request_is_answered_by_the_character(
        tmp: Path) -> None:
    """A DM persona asked for the first hundred digits of pi typed out a
    hundred digits: the prompt banned every assistant PHRASE and said nothing
    about assistant SUBSTANCE. Beside the two style bullets, three more
    places say it, each where the model reads it at a different moment: the
    `question` intent, the reasoning protocol's tool check, and the <rules>
    block after the persona. The group prompt, where the persona is one
    member of a room, is untouched."""
    style = PersonaStyle()
    question = next(line for line in private_intent_rules(style).splitlines()
                    if line.startswith("- `question`"))
    check("the question intent answers as this person, from what they'd know",
          "as this person and from what they'd know" in question, question)
    check("...and not having it, said in their own words, is the answer",
          "saying so in their own words IS the direct answer" in question,
          question)
    protocol = private_output_protocol(style)
    check("the reasoning protocol runs a tool check",
          "- Tool check:" in protocol and "decide as the character" in protocol)
    bullets = protocol.split("Cover these ", 1)[1].split("\n\nintent", 1)[0]
    stated = int(bullets.split(" ", 1)[0])
    check("...and counts it among the points it asks for",
          stated == bullets.count("\n- "), bullets)

    tool_check = next(line for line in protocol.splitlines()
                      if line.startswith("- Tool check:"))
    # "look up" is in the tool check's list, and PRIVATE_TOOL_GUIDE says to
    # answer from fetched results as if already known. Without this the two
    # disagreed about a search the engine had already paid for.
    check("...which counts fetched search results as something they have",
          "[external_web_search_data]" in tool_check, tool_check)

    served_by_who = await _served_private_prompts(tmp)
    for who, served in served_by_who.items():
        rules = served.split("<rules>", 1)[1].split("</rules>", 1)[0]
        check(f"the {who}'s <rules> say the character decides what gets done",
              "The person never turns into the tool" in rules, rules)
        check(f"...and the {who}'s count fetched search results as known",
              "[external_web_search_data]" in rules, rules)

    # The owner's overrides come after <rules> and say "engage directly" to
    # a lookup. They name the option they retract, and keep the character
    # rather than handing over a deliverable, so the two lines agree.
    overrides = served_by_who["owner"].split(
        "<private_overrides>", 1)[1].split("</private_overrides>", 1)[0]
    ask = next(line for line in overrides.splitlines()
               if "look something up" in line)
    check("the owner's lookup override names the <rules> option it retracts",
          "<rules>" in ask and "no interest" in ask, ask)
    check("...and still answers in the character's voice",
          "own voice" in ask, ask)

    group = "\n".join((STYLE_GUIDE, INTENT_RULES, REASONING_PROTOCOL))
    check("the group prompt keeps its own question intent and protocol",
          "general-purpose engine" not in group and "Tool check" not in group
          and "encyclopedia entry" not in group)


async def test_the_private_guide_tells_the_character_to_receive_affection(
        tmp: Path) -> None:
    """Four turns of "I like you" / "do you like me" / "I'm gay" came back as
    four deflections ending in "we only talk online, don't take it too
    seriously". No rule asked for that, and that was the cause: with nothing
    in the prompt about being cared for, the model fell back on the
    deflection its training rewards.

    The second half is the important one. "Never tell them you are just a
    program" is one edit from "never say you are an AI", and that answer is
    still owed to anyone who sincerely asks. The style rule forbids offering
    it UNASKED, and points at the honesty block instead of restating it."""
    guide = private_style_guide(PersonaStyle())
    check("1:1 guide: affection is received rather than deflected",
          "receive it, do not deflect" in guide)
    check("1:1 guide: the dodge it was measured making is named",
          "别太当真" in guide and "哦 知道了" in guide)
    check("1:1 guide: a direct question about feelings gets an answer",
          "**answer it**" in guide)
    check("1:1 guide: and it does not swing into devotion",
          "Do not overcorrect into devotion" in guide)
    check("the honest answer is still owed to anyone who sincerely asks",
          "sincerely asks whether you are an AI, answer honestly"
          in HONEST_DISCLOSURE)
    check("the style rule defers to the honesty block instead of replacing it",
          "sincere question about whether you are an AI, which the honesty "
          "block below covers" in guide)

    for who, served in (await _served_private_prompts(tmp)).items():
        check(f"the {who}'s honesty block really is below the guide",
              served.index(HONEST_DISCLOSURE)
              > served.index("receive it, do not deflect"), who)
        check(f"...and is the one place the {who}'s prompt says it",
              served.lower().count("answer honestly") == 1, who)
