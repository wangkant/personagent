"""The 1:1 register: a DM persona is company, not a service.

`[COMPANY, NOT SERVICE]` and `[CONTINUITY]` in `dm_style_guide` are
unconditional text, which is why they are checked over the WHOLE knob space
rather than over the default style: the failure is not a persona choosing
badly (no knob offers "be a service"), it is a later edit moving a section
inside a variant table, or a new variant in a table between them
dropping what follows. Both ship green against one style and fail here."""
from __future__ import annotations

import itertools
import json
from pathlib import Path

from persona_agent.agent import Agent
from persona_agent.prompts import (
    HONEST_DISCLOSURE,
    DM_TOOL_GUIDE,
    STYLE_GUIDE,
    STYLE_KNOBS,
    PersonaStyle,
    dm_intent_rules,
    dm_output_protocol,
    dm_style_guide,
)

from helpers import check, isolated_agent


def make_agent(tmp: Path) -> Agent:
    """The persona is a stub: the bundled example is the operator's text, and
    what these suites own is the text the engine writes around it."""
    return isolated_agent(tmp, seeds=True, qq_bot_id="1", persona_name="B")


def _every_style() -> list[PersonaStyle]:
    """Every combination of the knobs, built from `STYLE_KNOBS` so a knob or
    a value added later is covered on the commit that adds it."""
    knobs = sorted(STYLE_KNOBS)
    return [PersonaStyle(**dict(zip(knobs, values)))
            for values in itertools.product(*(STYLE_KNOBS[k] for k in knobs))]


def _assembled_dm_prompt(style: PersonaStyle) -> str:
    """Every block of the 1:1 system prompt a `PersonaStyle` can change, in
    served order."""
    return "\n\n".join((dm_style_guide(style),
                        dm_intent_rules(style),
                        DM_TOOL_GUIDE,
                        dm_output_protocol(style)))


async def _served_dm_prompts(tmp: Path) -> dict[str, str]:
    """The whole system prompt `_chat_dm` sends, for the admin and for
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
        for who, is_admin in (("friend", False), ("admin", True)):
            await agent._chat_dm([{"role": "user", "content": "hey"}],
                                      is_admin=is_admin, pkey="private:7")
            served[who] = captured[-1]
    finally:
        await agent.aclose()
    return served


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
        assembled = _assembled_dm_prompt(style)
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

    guide = dm_style_guide(PersonaStyle())
    voice = _section(guide, "[VOICE")
    check("the floors sit under the teasing licence they bound",
          voice.index("Light teasing only") < voice.index("Never win at")
          and "Say the thing" in voice, voice)
    check("continuity follows DON'T FAKE KNOWING, which it defers to",
          guide.index("[CONTINUITY") > guide.index("[DON'T FAKE KNOWING")
          and "DON'T FAKE KNOWING wins" in _section(guide, "[CONTINUITY"))


async def test_the_dm_guide_tells_the_character_to_receive_affection(
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
    guide = dm_style_guide(PersonaStyle())
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

    for who, served in (await _served_dm_prompts(tmp)).items():
        check(f"the {who}'s honesty block really is below the guide",
              served.index(HONEST_DISCLOSURE)
              > served.index("receive it, do not deflect"), who)
        check(f"...and is the one place the {who}'s prompt says it",
              served.lower().count("answer honestly") == 1, who)


def test_a_cards_emoji_opt_in_and_length_reach_the_prompt(tmp: Path) -> None:
    """The tuning panel edits `reply_style`; the prompt said emoji were banned
    whatever the card said. The default card must give today's exact text, or
    the provider's prompt cache starts over."""
    import dataclasses

    agent = make_agent(tmp)
    default_group = agent._build_group_prompt("g1", "called", "hi").system
    default_dm = agent._build_dm_prompt([{"role": "user", "content": "hi"}]).system
    check("the default card keeps the group guide byte for byte",
          STYLE_GUIDE in default_group)
    check("...and the 1:1 guide", dm_style_guide(agent.persona_style) in default_dm)

    agent.reply_style = dataclasses.replace(agent.reply_style, allow_emoji=True)
    group = agent._build_group_prompt("g1", "called", "hi").system
    dm = agent._build_dm_prompt([{"role": "user", "content": "hi"}]).system
    for who, text in (("group", group), ("1:1", dm)):
        banned = next(line for line in text.splitlines() if line.startswith("- Banned:"))
        check(f"{who}: emoji are no longer banned", "emoji," not in banned, banned)
        check(f"{who}: ...but used only as the character does",
              "emoji only as this character uses them" in text, banned)
        check(f"{who}: no length line at the default length",
              "Stay under" not in text)

    agent.reply_style = dataclasses.replace(agent.reply_style, max_chars=120)
    group = agent._build_group_prompt("g1", "called", "hi").system
    dm = agent._build_dm_prompt([{"role": "user", "content": "hi"}]).system
    check("a shorter limit is stated in both guides",
          "Stay under 120 characters" in group and "Stay under 120 characters" in dm)
