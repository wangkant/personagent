"""The chat languages: memory commands, their replies, the learned summary
and the failure line in every language in `chatlangs`, each checked against
its own cases in tests/chat_language_cases/<code>.json.

A case file holds the persona's name in that language and:
- commands: a message and the command it is ("remember" with the "note"
  kept, "forget" with the note it "deletes", "recall", "learned"), or null
  for conversation that must stay conversation;
- first_person: a note and whether it is about the person saving it;
- detect: a message and the chat language `chatlangs.detect` must name.
"""
from __future__ import annotations

import json
from pathlib import Path
import re

import pytest

from persona_agent import chatlangs
from persona_agent.textproc import TextProcessing

from helpers import CLOSED_ONEBOT_URL, check, isolated_agent

CASES = Path(__file__).with_name("chat_language_cases")


def _cases(code: str) -> dict:
    return json.loads((CASES / f"{code}.json").read_text(encoding="utf-8"))


def _fields(template: str) -> set:
    return set(re.findall(r"\{(\w+)\}", template))


def _agent(tmp: Path, code: str, name: str):
    lang = "zh" if code in ("zh", "zh-TW") else "en"
    agent = isolated_agent(tmp, qq_bot_id="1", persona_name=name, lang=lang,
                           qq_onebot_url=CLOSED_ONEBOT_URL)
    agent.memories.clear()
    return agent


def _passes(text: str) -> bool:
    return TextProcessing._sanitize_reply(text, "en") == text


def test_every_chat_language_is_written_and_has_cases() -> None:
    for code in chatlangs.CODES:
        check(f"{code} has a spec", code in chatlangs.SPECS)
        check(f"{code} has a case file", (CASES / f"{code}.json").is_file())


@pytest.mark.parametrize("code", sorted(chatlangs.SPECS))
def test_the_lines_a_language_says_pass_the_character_policy(code: str) -> None:
    spec = chatlangs.SPECS[code]
    check(f"{code}: its code", spec.code == code)
    check(f"{code}: every reply key", set(spec.replies) == set(chatlangs.REPLY_KEYS),
          repr(sorted(set(spec.replies) ^ set(chatlangs.REPLY_KEYS))))
    for key, lines in spec.replies.items():
        check(f"{code}/{key}: some lines", bool(lines) and isinstance(lines, tuple))
        for line in lines:
            want = {"name"} if key in ("about", "from") else set()
            check(f"{code}/{key}: {line!r} fields", _fields(line) == want)
            shown = line.format(name="Kay") + "x"
            check(f"{code}/{key}: {line!r} survives the policy", _passes(shown))
    check(f"{code}: failure lines", bool(spec.failure_excuses))
    for line in spec.failure_excuses:
        check(f"{code}: {line!r} survives the policy", _passes(line))
    if code == "en":
        check("English builds its own summary", spec.learned_text == {})
        return
    text = spec.learned_text
    check(f"{code}: every summary template",
          set(text) == set(chatlangs.LEARNED_FIELDS), repr(sorted(text)))
    sample = {"memories": 3, "examples": 2, "fixes": 1, "voice": 1, "admin": 0,
              "score": "4.5", "was": "ok", "better": "fine", "who": "Kay",
              "events": 2, "strong": 1, "steps": "x"}
    for key, fields in chatlangs.LEARNED_FIELDS.items():
        check(f"{code}/{key}: fields {sorted(fields)}",
              _fields(text[key]) == set(fields), text[key])
    head = text["head"].format(**sample) + text["score"].format(**sample)
    check(f"{code}: the summary head survives the policy", _passes(head), head)
    chain = text["why"].format(steps=text["sep"].join(
        [text["retry"].format(who="Kay"), text["corrected"].format(who="Kay"),
         text["passed"].format(events=2, strong=1)]))
    check(f"{code}: the why line survives the policy", _passes(chain), chain)
    pair = text["pair"].format(was="ok", better="fine")
    check(f"{code}: the pair line survives the policy", _passes(pair), pair)


@pytest.mark.parametrize("code", sorted(chatlangs.SPECS))
def test_memory_commands_in_each_language(tmp: Path, code: str) -> None:
    cases = _cases(code)
    spec = chatlangs.SPECS[code]
    kinds = [c["kind"] for c in cases["commands"]]
    for kind, least in (("remember", 3), ("forget", 2), (None, 4),
                        ("recall", 1), ("learned", 1)):
        check(f"{code}: at least {least} {kind or 'conversation'} cases",
              kinds.count(kind) >= least)
    for i, case in enumerate(cases["commands"]):
        text, kind = case["text"], case["kind"]
        agent = _agent(tmp / f"{code}-{i}", code, cases["name"])
        parsed = agent._parse_memory_command(text)
        if kind is None:
            check(f"{code}: conversation, not a command: {text!r}", parsed is None,
                  repr(parsed))
            continue
        check(f"{code}: {text!r} is {kind} in {code}",
              parsed is not None and parsed[0] == kind and parsed[2] == code,
              repr(parsed))
        g = "g1"
        if kind == "remember":
            reply = agent._handle_memory_command(g, text, "42", "Kay")
            kept = [it["text"] for it in agent.memories.get(g, [])]
            if case["note"] is None:
                # A command with nothing to keep asks what to remember.
                check(f"{code}: {text!r} asks what to remember",
                      reply in spec.replies["remember_what"] and not kept, repr(reply))
                continue
            check(f"{code}: noted {text!r}", reply in spec.replies["noted"], repr(reply))
            check(f"{code}: the note of {text!r}", kept == [case["note"]], repr(kept))
        elif kind == "forget":
            agent.memories[g] = [{"text": case["deletes"], "time": 1.0, "saved_by": "42"},
                                 {"text": "zzz unrelated 无关 kept", "time": 2.0}]
            reply = agent._handle_memory_command(g, text, "42", "Kay")
            check(f"{code}: forgotten {text!r}", reply in spec.replies["forgotten"],
                  repr(reply))
            left = [it["text"] for it in agent.memories[g]]
            check(f"{code}: only the named note goes", left == ["zzz unrelated 无关 kept"],
                  repr(left))
        elif kind == "recall":
            agent.memories[g] = [{"text": "note one", "time": 1.0}]
            reply = agent._handle_memory_command(g, text, "42", "Kay") or ""
            check(f"{code}: recall answers in {code}",
                  reply.split("\n")[0] in spec.replies["recall_head"], repr(reply))
        else:
            reply = agent._handle_memory_command(g, text, "42", "Kay") or ""
            check(f"{code}: the summary answers", bool(reply), repr(reply))


@pytest.mark.parametrize("code", sorted(chatlangs.SPECS))
def test_first_person_and_detection_in_each_language(code: str) -> None:
    cases = _cases(code)
    spec = chatlangs.SPECS[code]
    check(f"{code}: first-person cases", len(cases["first_person"]) >= 2)
    for case in cases["first_person"]:
        found = bool(re.search(spec.first_person, case["text"], re.IGNORECASE))
        check(f"{code}: {case['text']!r} is about the saver: {case['mine']}",
              found is case["mine"])
    check(f"{code}: detection cases", len(cases["detect"]) >= 3)
    for case in cases["detect"]:
        got = chatlangs.detect(case["text"], case.get("default", "en"))
        check(f"{code}: {case['text']!r} reads as {case['code']}", got == case["code"],
              got)


@pytest.mark.parametrize("code", sorted(chatlangs.SPECS))
def test_the_failure_line_answers_in_the_language_asked(tmp: Path, code: str) -> None:
    cases = _cases(code)
    agent = _agent(tmp, code, cases["name"])
    asked = next(c["text"] for c in cases["detect"] if c["code"] == code)
    check(f"{code}: a failed model call answers {asked!r} in {code}",
          agent._model_failure_excuse(asked) in chatlangs.SPECS[code].failure_excuses)
