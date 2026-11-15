"""What a group owner uses to keep the character in check: replying only when
named (CHAT_ONLY_WHEN_CALLED), pausing chosen groups (ACCESS_PAUSED_GROUPS)
and learning only from the admin (REACT_LEARN_ADMIN_ONLY).

Run from the repo root:

    python -m pytest tests/test_controls.py
"""
from __future__ import annotations

import dataclasses
import time
from pathlib import Path

from persona_agent import decision, decision_log, preflight
from persona_agent.settings import AgentSettings
from persona_agent.textproc import TextProcessing

from helpers import check
from test_character_decides import (CORRECTION, REJECTION, REPLY, RETRY, THANKS,
                                    pairs, react, send)
from test_character_decides import make_agent as learning_agent
from test_proactive_unanswered import _opening_agent, _ready_to_open
from test_turns import GROUP, _collect_sends, _event, _group, _scripted_think, make_agent


def test_the_settings_default_to_todays_behaviour() -> None:
    s = AgentSettings.from_env(env={"LLM_API_KEY": "k"})
    check("all three are off by default",
          s.chat_only_when_called is False and s.access_paused_groups == ()
          and s.promotion_policy.admin_only is False)
    s = AgentSettings.from_env(env={
        "LLM_API_KEY": "k", "CHAT_ONLY_WHEN_CALLED": "true",
        "ACCESS_PAUSED_GROUPS": "qq:555, telegram:-100", "REACT_LEARN_ADMIN_ONLY": "on"})
    check("and read from .env, ids canonical",
          s.chat_only_when_called is True and s.promotion_policy.admin_only is True
          and s.access_paused_groups == ("555", "telegram:-100"), repr(s.access_paused_groups))


def test_only_when_called_leaves_only_the_called_modes() -> None:
    def mode(**kw):
        base = dict(addressed=False, is_admin=False, sticky_admin=None, in_followup=False,
                    counter=0, trigger_count=30, never_replied=False, only_when_called=True)
        return decision.choose_group_mode(**{**base, **kw})

    check("a call is still answered", mode(addressed=True)[0] == "called")
    check("so is a call that lost the debounce race",
          mode(sticky_admin=False) == ("called", decision.STICKY_CALL))
    for quiet in (dict(in_followup=True), dict(counter=99),
                  dict(counter=12, never_replied=True)):
        check(f"nothing unprompted: {quiet}",
              mode(**quiet) == ("", decision.ONLY_WHEN_CALLED), repr(mode(**quiet)))


async def test_a_group_turn_runs_only_when_called(tmp: Path, monkeypatch) -> None:
    monkeypatch.setattr(TextProcessing, "_is_sleep_hour", staticmethod(lambda: False))
    decision_log.LOG.clear()
    agent = make_agent(tmp, chat_trigger_count=1, chat_followup_window_s=600,
                       chat_only_when_called=True)
    sent = _collect_sends(agent)
    calls: list = []

    async def think(group_id, mode, text="", caller_override=None, retry_note=""):
        calls.append(mode)
        return "here", "chat", ""

    agent._think = think
    await agent.handle_onebot(_group("what a match last night", "o1"))
    check("past the trigger count, no turn", calls == [] and sent == [], repr(calls))
    check("Activity says why",
          decision_log.LOG.recent(GROUP)[0]["reason"] == decision.ONLY_WHEN_CALLED)
    await agent.handle_onebot(_group("Luna, did you see it?", "o2", at_bot=True))
    check("a call is answered", calls == ["called"] and len(sent) == 1, repr(calls))
    await agent.handle_onebot(_group("and the second half?", "o3"))
    check("the follow-up window does not open", calls == ["called"], repr(calls))

    off = make_agent(tmp / "off", chat_trigger_count=1)
    _collect_sends(off)
    _scripted_think(off, "PASS")
    await off.handle_onebot(_group("what a match last night", "p1"))
    check("off, the trigger count still asks the gate as before",
          decision_log.LOG.recent(GROUP)[0]["mode"] == "judge",
          repr(decision_log.LOG.recent(GROUP)[0]))


async def test_only_when_called_starts_no_group_conversation(tmp: Path) -> None:
    agent, sent, calls = _opening_agent(tmp)
    agent.settings = dataclasses.replace(agent.settings, chat_only_when_called=True)
    agent._append_buffer(GROUP, "Ann", "night all", "7")
    agent.last_activity_at[GROUP] = time.time() - 10 * 86400
    _ready_to_open(agent)
    check("no group opener", await agent._maybe_proactive_groups() is False
          and sent == [] and calls == [], repr(sent))


async def test_a_paused_group_is_claimed_and_left_alone(tmp: Path) -> None:
    decision_log.LOG.clear()
    agent = make_agent(tmp, access_paused_groups=("telegram:c1",))
    _collect_sends(agent)
    calls = _scripted_think(agent, "hi there")
    seen: list = []

    async def fake_reaction(*args, **kwargs):
        seen.append(args)

    agent._process_reaction = fake_reaction
    answer = await agent.handle_event(_event("Luna, are you there?", 1, sender="5",
                                             name="Eve", at_bot=True))
    check("owned with no replies, so a connector's own bot stays quiet",
          answer == {"handled": False, "owned": True, "replies": []}, repr(answer))
    check("nothing asked, kept or recorded",
          calls == [] and not agent.buffers.get("telegram:c1")
          and decision_log.LOG.recent("telegram:c1") == [] and seen == [],
          repr((calls, list(agent.buffers.get("telegram:c1") or ()))))
    check("its id is not taken, so it is read anew once resumed",
          "1" not in agent._seen_msg_ids)
    await agent.handle_onebot(_group("Luna, you there?", "q1", at_bot=True))
    check("every other group is answered as usual", len(calls) == 1, repr(calls))


async def test_a_paused_group_gets_no_opener(tmp: Path) -> None:
    agent, sent, calls = _opening_agent(tmp)
    agent.settings = dataclasses.replace(agent.settings, access_paused_groups=(GROUP,))
    agent._append_buffer(GROUP, "Ann", "night all", "7")
    agent.last_activity_at[GROUP] = time.time() - 10 * 86400
    _ready_to_open(agent)
    check("no opener in a paused group",
          await agent._maybe_proactive_groups() is False and sent == [], repr(sent))


def _admin_only(agent) -> None:
    agent.promotion_policy = dataclasses.replace(agent.promotion_policy, admin_only=True)


async def test_admin_only_others_corrections_are_kept_but_not_used(tmp: Path) -> None:
    a, model = learning_agent(tmp)
    _admin_only(a)
    send(a, REPLY, "42")
    await react(a, model, "42", CORRECTION)
    send(a, RETRY, "42")
    await react(a, model, "42", THANKS)
    check("the reactions are recorded", len(a.evidence_log.all()) >= 2)
    check("the rewrite is proposed but not in use",
          pairs(a) == [] and any(c.get("better") == RETRY for c in a.candidate_ledger.all()),
          repr(pairs(a)))


async def test_admin_only_others_lessons_are_not_kept(tmp: Path) -> None:
    lesson = dict(CORRECTION, better="", lesson="This group calls the gym the cave.")
    for admin_only, expected in ((False, 1), (True, 0)):
        a, model = learning_agent(tmp / str(admin_only))
        if admin_only:
            _admin_only(a)
        kept: list = []
        a._save_lesson_fact = lambda conv, text: kept.append(text) or True
        send(a, REPLY, "42")
        await react(a, model, "42", lesson)
        check(f"admin_only={admin_only}: {expected} lesson kept", len(kept) == expected, repr(kept))


async def test_admin_only_the_admins_correction_teaches(tmp: Path) -> None:
    a, model = learning_agent(tmp)
    a.admin_ids = {"42"}
    _admin_only(a)
    send(a, REPLY, "42")
    await react(a, model, "42", CORRECTION, is_admin=True)
    send(a, RETRY, "42")
    await react(a, model, "42", THANKS, is_admin=True)
    check("in use", pairs(a) == [(REPLY, RETRY)], repr(pairs(a)))


async def test_admin_only_others_cannot_take_a_lesson_out_of_use(tmp: Path) -> None:
    a, model = learning_agent(tmp)
    send(a, REPLY, "42")
    await react(a, model, "42", CORRECTION)
    send(a, RETRY, "42")
    await react(a, model, "42", THANKS)
    assert pairs(a) == [(REPLY, RETRY)], pairs(a)
    _admin_only(a)
    send(a, RETRY, "42")
    await react(a, model, "42", REJECTION)
    check("the person it was for disagreeing no longer rolls it back",
          pairs(a) == [(REPLY, RETRY)], repr(pairs(a)))


def test_preflight_warns_when_admin_only_has_no_admin() -> None:
    def keys(**env):
        return {(f.level, f.key) for f in preflight.check_config(env={"LLM_API_KEY": "k", **env})}

    check("on with no admin warns",
          ("WARN", "REACT_LEARN_ADMIN_ONLY") in keys(REACT_LEARN_ADMIN_ONLY="true"))
    check("on with an admin is fine",
          ("WARN", "REACT_LEARN_ADMIN_ONLY") not in keys(REACT_LEARN_ADMIN_ONLY="true",
                                                         ADMIN_IDS="telegram:1"))
    check("off is fine", ("WARN", "REACT_LEARN_ADMIN_ONLY") not in keys())
    check("a malformed pause entry is reported like the other lists",
          ("WARN", "ACCESS_PAUSED_GROUPS") in keys(ACCESS_PAUSED_GROUPS="telegram:"))
