"""Addressing: when a line calls the persona by its name or a nickname, in
every chat language, at no model cost (tests/data/address.jsonl).

    python -m pytest tests/test_addressing.py
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

from persona_agent import agent as agent_module
from persona_agent import chatlangs
from persona_agent.addressing import mentions_name
from persona_agent.decision import choose_group_mode

from helpers import CLOSED_ONEBOT_URL, check, isolated_agent

SUITE = Path(__file__).resolve().parent / "data" / "address.jsonl"
CASES = [json.loads(ln) for ln in SUITE.read_text(encoding="utf-8").splitlines()
         if ln.strip()]


def test_the_suite_covers_every_chat_language_both_ways() -> None:
    for c in CASES:
        check(f"row is well formed: {c}",
              c["lang"] in chatlangs.CODES and isinstance(c["name"], str)
              and isinstance(c["aliases"], list) and isinstance(c["addressed"], bool))
    for code in chatlangs.CODES:
        got = Counter(c["addressed"] for c in CASES if c["lang"] == code)
        check(f"{code}: at least five rows, called and not called",
              sum(got.values()) >= 5 and got[True] >= 2 and got[False] >= 2, str(got))


@pytest.mark.parametrize("case", CASES, ids=lambda c: f"{c['lang']}:{c['text']}")
def test_a_line_calls_the_persona_exactly_when_labelled(case) -> None:
    called = mentions_name(case["text"], case["name"], case["aliases"])
    check(f"{case['name']} {case['aliases']} in {case['text']!r}",
          called is case["addressed"])
    mode, _why = choose_group_mode(
        addressed=called, is_admin=False, sticky_admin=None, in_followup=False,
        counter=0, trigger_count=30, never_replied=False)
    check("a called line opens a called turn, any other waits",
          mode == ("called" if case["addressed"] else ""), mode)


def _agent_with_card(tmp: Path, monkeypatch, card: dict, name: str, lang: str):
    (tmp / "persona.card.json").write_text(json.dumps(card), encoding="utf-8")
    monkeypatch.setattr(agent_module, "ROOT", tmp)
    monkeypatch.setenv("PERSONA_CARD_FILE", "persona.card.json")
    a = isolated_agent(tmp / "state", qq_bot_id="1", persona_name=name, lang=lang,
                       qq_onebot_url=CLOSED_ONEBOT_URL)
    a.memories.clear()
    return a


def test_the_persona_card_gives_the_character_its_nicknames(tmp, monkeypatch) -> None:
    a = _agent_with_card(tmp, monkeypatch, {"aliases": ["鲸鱼", " ", 7]}, "鲸鱼娘", "zh")
    check("the card's aliases are read, blanks and non-text dropped",
          a.persona_aliases == ("鲸鱼",), str(a.persona_aliases))
    check("a nickname calls the persona", a._names_me("鲸鱼你在吗"))
    check("so does the name", a._names_me("鲸鱼娘在吗"))
    check("a line without either does not", not a._names_me("晚饭吃什么"))
    parsed = a._parse_memory_command("鲸鱼，记住 我下周搬家")
    check("a memory command through the nickname is a command",
          parsed is not None and parsed[0] == "remember"
          and "下周搬家" in parsed[1], str(parsed))


def test_no_card_means_no_nicknames(tmp, monkeypatch) -> None:
    monkeypatch.setattr(agent_module, "ROOT", tmp)
    monkeypatch.setenv("PERSONA_CARD_FILE", "persona.card.json")
    a = isolated_agent(tmp / "state", qq_bot_id="1", persona_name="Sofía",
                       qq_onebot_url=CLOSED_ONEBOT_URL)
    check("no aliases", a.persona_aliases == ())
    check("an unaccented call still reaches an accented name",
          a._names_me("sofia, are you there"))
    parsed = a._parse_memory_command("sofia, remember I moved to Lisbon")
    check("and a memory command written without the accent is a command",
          parsed is not None and parsed[0] == "remember"
          and "Lisbon" in parsed[1], str(parsed))
