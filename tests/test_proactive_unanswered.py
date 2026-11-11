"""Speaking first: no second opener into silence, and an opener on record."""
from __future__ import annotations

import time
from pathlib import Path

from persona_agent import reactions
from persona_agent.decision_log import LOG
from persona_agent.transport import SendResult

from helpers import check
from test_turns import GROUP, _dm, _group, make_agent

UID = "42"


def _ready_to_open(agent) -> None:
    """Every cooldown and silence long past, and the dice always say yes."""
    agent.proactive_prob = agent.proactive_dm_prob = 1.0
    long_ago = time.time() - 10 * 86400
    for d in (agent.last_proactive_at, agent.last_reply_at):
        for key in list(d):
            d[key] = long_ago


def _opening_agent(tmp: Path):
    agent = make_agent(tmp)
    sent: list = []
    calls: list = []

    async def send_group(group_id, text, at_user_id=""):
        sent.append((group_id, text))
        return SendResult(success=True, message_ids=[f"m{len(sent)}"])

    async def send_dm(user_id, text):
        sent.append((user_id, text))
        return SendResult(success=True, message_ids=[f"m{len(sent)}"])

    async def think(group_id, mode, text="", caller_override=None):
        calls.append(group_id)
        return "anyone around?", "chat", ""

    async def chat_dm(history, is_admin=False, pkey="", proactive=False,
                      proactive_cue=""):
        calls.append(pkey)
        return "how did the exam go?", ""

    agent._send_group, agent._send_dm = send_group, send_dm
    agent._think, agent._chat_dm = think, chat_dm
    return agent, sent, calls


async def test_no_second_group_opener_until_someone_speaks(tmp: Path) -> None:
    """A room silent for days got an opener every time the cooldown passed."""
    agent, sent, calls = _opening_agent(tmp)
    agent._append_buffer(GROUP, "Ann", "night all", "7")
    agent.last_activity_at[GROUP] = time.time() - 10 * 86400
    _ready_to_open(agent)
    check("the first opener goes out",
          await agent._maybe_proactive_groups() is True and len(sent) == 1)
    for _ in range(3):
        _ready_to_open(agent)
        check("no other while nobody answered",
              await agent._maybe_proactive_groups() is False
              and len(calls) == 1 and len(sent) == 1, repr(sent))
    await agent.handle_onebot(_group("morning", "h1"))
    agent.proactive_min_silence_s = -1
    _ready_to_open(agent)
    check("a line from a person opens the way again",
          await agent._maybe_proactive_groups() is True and len(sent) == 2,
          repr(sent))


async def test_no_second_dm_opener_until_they_write(tmp: Path) -> None:
    agent, sent, calls = _opening_agent(tmp)
    agent.last_dm_activity_at[UID] = time.time() - 10 * 86400
    _ready_to_open(agent)
    check("the first opener goes out",
          await agent._maybe_proactive_dms() is True and len(sent) == 1)
    for _ in range(3):
        _ready_to_open(agent)
        check("no other while they did not answer",
              await agent._maybe_proactive_dms() is False
              and len(calls) == 1, repr(calls))
    await agent.handle_onebot(_dm("it went fine", "h1"))
    agent.proactive_dm_min_silence_s = -1
    _ready_to_open(agent)
    check("their message opens the way again",
          await agent._maybe_proactive_dms() is True and len(sent) == 3,
          repr(sent))


async def test_a_reply_with_the_last_word_does_not_block_openers(
        tmp: Path) -> None:
    agent, sent, _calls = _opening_agent(tmp)
    await agent.handle_onebot(_group("Luna, you there?", "c1", at_bot=True))
    check("the call was answered", len(sent) == 1, repr(sent))
    agent.last_activity_at[GROUP] -= 10 * 86400
    _ready_to_open(agent)
    check("an opener may still follow",
          await agent._maybe_proactive_groups() is True and len(sent) == 2,
          repr(sent))


async def test_an_opener_is_on_record_and_can_be_reacted_to(tmp: Path) -> None:
    """An opener left no row in Activity, and an @ to it taught nothing."""
    LOG.clear()
    agent, sent, _calls = _opening_agent(tmp)
    agent.react_learn_enabled = True
    agent.pending_reactions = reactions.PendingReplies()
    agent._append_buffer(GROUP, "Ann", "night all", "7")
    agent.last_activity_at[GROUP] = time.time() - 10 * 86400
    _ready_to_open(agent)
    await agent._maybe_proactive_groups()
    rows = LOG.recent(GROUP)
    check("one row, spoken, as an opener",
          len(rows) == 1 and rows[0]["reason"] == "proactive"
          and rows[0]["spoke"] is True
          and rows[0]["excerpt"] == "anyone around?", repr(rows))
    entry = agent.pending_reactions.match(
        GROUP, sender_uid="7", at_bot=True, now=time.time())
    check("an @ to it is matched to the opener",
          entry is not None and entry["matched_by"] == "at"
          and entry["mode"] == "proactive"
          and entry["reply"] == "anyone around?"
          and entry["ctx_lines"] == ["Ann: night all"], repr(entry))

    LOG.clear()
    agent.last_dm_activity_at[UID] = time.time() - 10 * 86400
    _ready_to_open(agent)
    await agent._maybe_proactive_dms()
    rows = LOG.recent(f"private:{UID}")
    check("a DM opener has its row too",
          len(rows) == 1 and rows[0]["reason"] == "proactive"
          and rows[0]["spoke"] is True, repr(rows))
    LOG.clear()


async def test_an_opener_the_model_declines_is_on_record(tmp: Path) -> None:
    LOG.clear()
    agent, sent, _calls = _opening_agent(tmp)

    async def think(group_id, mode, text="", caller_override=None):
        return "PASS", "chat", ""

    agent._think = think
    agent._append_buffer(GROUP, "Ann", "night all", "7")
    agent.last_activity_at[GROUP] = time.time() - 10 * 86400
    _ready_to_open(agent)
    check("nothing is sent", await agent._maybe_proactive_groups() is False
          and sent == [])
    rows = LOG.recent(GROUP)
    check("a silent row, as an opener",
          len(rows) == 1 and rows[0]["reason"] == "proactive"
          and rows[0]["spoke"] is False, repr(rows))
    LOG.clear()
