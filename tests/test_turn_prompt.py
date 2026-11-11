"""What the model is told on one turn: the owner's call, a picture it cannot
see, a long message that calls it, and several people calling at once."""
from __future__ import annotations

from pathlib import Path

from persona_agent.access import ADMIN_MODE

from helpers import check, isolated_agent

GROUP = "555"


def _agent(tmp: Path):
    a = isolated_agent(tmp, persona_name="Luna", admin_ids=("42",),
                       admin_name="Kay")
    return a


def test_the_owner_calling_is_told_it_was_called_and_not_invited_to_pass(
        tmp: Path) -> None:
    a = _agent(tmp)
    a._append_buffer(GROUP, "Ann", "anyone watching the match", "7")
    a._append_buffer(GROUP, "Kay", "@Luna what should I cook tonight", "42")
    owner = a._build_group_prompt(GROUP, ADMIN_MODE,
                                  "@Luna what should I cook tonight").user
    check("the owner's prompt says they called", "called you" in owner, owner)
    check("...and offers no PASS", "PASS" not in owner, owner)
    check("...and keeps the warmer register", "the owner" in owner
          and "lean towards replying" in owner, owner)
    called = a._build_group_prompt(GROUP, "called",
                                   "@Luna what should I cook tonight").user
    check("the called prompt is as before", "called you" in called
          and "PASS" not in called, called)


def test_a_private_picture_it_cannot_see_is_named_as_unseen(tmp: Path) -> None:
    a = _agent(tmp)
    blind = a._build_dm_prompt([{"role": "user", "content": "[image]"}],
                               pkey="private:42")
    notes = [line for line in blind.turn_context.splitlines()
             if "**can't see**" in line]
    check("a bare picture in a DM gets the can't-see note", len(notes) == 1,
          blind.turn_context)
    check("...which offers no PASS, a DM has none",
          notes and "PASS" not in notes[0], repr(notes))
    seen = a._build_dm_prompt([{"role": "user", "content": "[image: a cat on a sofa]"}],
                              pkey="private:42")
    check("a described picture does not",
          "**can't see**" not in seen.turn_context, seen.turn_context)
    check("the DM guide speaks of described pictures only",
          "When you see [image] / [sticker]" not in blind.system
          and "[image: …]" in blind.system, blind.system[:200])


def test_a_bare_picture_is_not_a_focus_item_in_a_group(tmp: Path) -> None:
    a = _agent(tmp)
    a._append_buffer(GROUP, "Ann", "[image]", "7")
    user = a._build_group_prompt(GROUP, "called", "[image]").user
    check("no 'engage with [image]' focus item", "Focus items" not in user, user)
    check("the can't-see note stays", "**can't see**" in user, user)
    b = _agent(tmp / "seen")
    b._append_buffer(GROUP, "Ann", "[image: a cat on a sofa]", "7")
    user = b._build_group_prompt(GROUP, "called", "[image: a cat on a sofa]").user
    check("a described picture is still one", "Focus items" in user
          and "[image: a cat on a sofa]" in user, user)
