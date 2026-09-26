"""Tests for decision.py: which mode a group turn runs in, and when pacing
skips it. Both are pure, so the rules are checked here without an agent;
tests/test_connector.py drives them through the real one."""
from __future__ import annotations

import random

from persona_agent import decision
from persona_agent.access import ADMIN_MODE
from persona_agent.textproc import SLEEP_PASS_PROB, SUB_TRIGGER_PASS_PROB


def check(name: str, cond: bool, detail: str = "") -> None:
    """Assert `cond`, naming the property so a failure reads as English."""
    assert cond, name + (f" - {detail}" if detail else "")


def mode(**kw) -> tuple[str, str]:
    base = dict(addressed=False, is_admin=False, sticky_admin=None,
                in_followup=False, counter=0, trigger_count=30,
                never_replied=False)
    base.update(kw)
    return decision.choose_group_mode(**base)


def test_a_call_wins_over_everything_else() -> None:
    check("an @ or a name-call is called", mode(addressed=True)[0] == "called")
    check("the admin calling is the admin's mode",
          mode(addressed=True, is_admin=True)[0] == ADMIN_MODE)
    check("a call beats a pending sticky call and the followup window",
          mode(addressed=True, sticky_admin=True, in_followup=True,
               counter=99) == ("called", "addressed"))


def test_a_sticky_call_keeps_its_callers_register() -> None:
    check("a sticky call from a member is called",
          mode(sticky_admin=False) == ("called", decision.STICKY_CALL))
    check("a sticky call from the admin is the admin's mode",
          mode(sticky_admin=True) == (ADMIN_MODE, decision.STICKY_CALL))
    check("uncalled admin chatter is not the admin's mode",
          mode(is_admin=True)[0] == "")


def test_the_spontaneous_modes_follow_the_counters() -> None:
    check("inside the followup window", mode(in_followup=True)[0] == "followup")
    check("at the trigger count", mode(counter=30)[0] == "judge")
    check("below it, silence", mode(counter=29) == ("", "below the trigger count"))
    check("a group never replied to gets a lower first threshold",
          mode(counter=10, never_replied=True) == ("judge", "first appearance"))
    check("that threshold is a third of the count once the count is large",
          mode(counter=19, trigger_count=60, never_replied=True)[0] == ""
          and mode(counter=20, trigger_count=60, never_replied=True)[0] == "judge")
    check("but never below ten (a third of 24 would be 8)",
          mode(counter=9, trigger_count=24, never_replied=True)[0] == ""
          and mode(counter=10, trigger_count=24, never_replied=True)
          == ("judge", "first appearance"))


def test_pacing_skips_only_spontaneous_turns(monkeypatch) -> None:
    monkeypatch.setattr(random, "random", lambda: 0.0)
    for asked in ("called", ADMIN_MODE):
        check(f"{asked} is never skipped",
              decision.pacing_skip(asked, first_appearance=False, sleep_hour=True) == "")
    check("the first appearance is never skipped",
          decision.pacing_skip("judge", first_appearance=True, sleep_hour=True) == "")
    check("night skips followup and judge",
          decision.pacing_skip("followup", first_appearance=False, sleep_hour=True)
          == decision.SLEEP_WINDOW)
    check("by day a judge turn can still be skipped",
          decision.pacing_skip("judge", first_appearance=False, sleep_hour=False)
          == "spontaneous skip")
    check("by day a followup never is",
          decision.pacing_skip("followup", first_appearance=False, sleep_hour=False) == "")


def test_pacing_draws_at_the_configured_odds(monkeypatch) -> None:
    draws = iter([SLEEP_PASS_PROB + 0.01, SUB_TRIGGER_PASS_PROB - 0.01])
    monkeypatch.setattr(random, "random", lambda: next(draws))
    check("a night draw above the odds goes on to the judge draw, which skips",
          decision.pacing_skip("judge", first_appearance=False, sleep_hour=True)
          == "spontaneous skip")
    monkeypatch.setattr(random, "random", lambda: 0.99)
    check("draws above both odds speak",
          decision.pacing_skip("judge", first_appearance=False, sleep_hour=True) == "")
