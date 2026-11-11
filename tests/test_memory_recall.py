"""What a reply recalls: the running summary, facts and events within one
budget, ranked by relevance, recency, importance, use and time words; what
the gate sees; dated lines and gaps; and the use count after a send.

No model is called: prompts are built and read."""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

import pytest

from persona_agent import ranking, timewords
from persona_agent.agent import Agent
from persona_agent.textproc import _USER_DATA_CLOSE, _USER_DATA_OPEN

from helpers import CLOSED_ONEBOT_URL, check, isolated_agent

DAY = 86400.0
G = "telegram:room1"


@pytest.fixture(autouse=True)
def _fixed_zone(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PERSONA_TZ_OFFSET_HOURS", "8")


def make_agent(tmp: Path, *, lang: str = "en", **settings) -> Agent:
    a = isolated_agent(tmp, qq_bot_id="1", persona_name="Luna", lang=lang,
                       qq_onebot_url=CLOSED_ONEBOT_URL, **settings)
    a.memories.clear()
    return a


def note(text: str, *, uid: str = "", name: str = "", age_days: float = 1.0,
         imp: int = 3, uses: int = 0, nid: str = "", **extra) -> dict:
    t = time.time() - age_days * DAY
    row = {"text": text, "time": t, "born": t, "auto": True, "imp": imp,
           "uses": uses, "used": 0.0, "src": "reply",
           "id": nid or "m" + format(abs(hash(text)) % (16 ** 10), "010x"), **extra}
    if uid:
        row["user_id"], row["user_name"] = uid, name or uid
    return row


def event(a: Agent, conv: str, text: str, t0: float, *, hours: float = 1.0,
          names=("Sam",), who=("telegram:7",), imp: int = 3) -> dict:
    return a.episode_store.add(conv, {"text": text, "t0": t0, "t1": t0 + hours * 3600,
                                      "names": list(names), "who": list(who),
                                      "imp": imp})


def speak(a: Agent, conv: str, uid: str, name: str, text: str = "hi", t: float = 0.0) -> None:
    a.buffers[conv].append({"name": name, "text": text, "user_id": uid,
                            **({"t": t} if t else {})})


def counted(block: str) -> int:
    """What MEMORY_PROMPT_CHARS charges: the summary's quote, every item line
    and every person header; fixed wrapper text is free."""
    total = 0
    m = re.search(r"<earlier_in_chat>\n.*\n(\".*\")\n</earlier_in_chat>", block)
    if m:
        total += len(m.group(1))
    body = block.split("<memories>", 1)[1] if "<memories>" in block else ""
    for line in body.split("\n"):
        if line.startswith("- ") or line.startswith("About "):
            total += len(line) + 1
    return total


def item_lines(block: str, header: str) -> list[str]:
    body = block.split(header + "\n", 1)
    if len(body) < 2:
        return []
    return [ln for ln in body[1].split("\n\n", 1)[0].split("\n") if ln.startswith("- ")]


def crowded(a: Agent) -> None:
    """50 facts over 15 present people and the group, 120 events, a summary."""
    rows = []
    for i in range(15):
        speak(a, G, f"telegram:{100 + i}", f"Member{i:02d}")
    for i in range(50):
        if i < 12:
            rows.append(note(f"the group plans outing number {i} with a long description "
                             f"of where everyone meets and what they bring along", age_days=i))
        else:
            k = i % 15
            rows.append(note(f"Member{k:02d} collects old maps of harbour town {i} and "
                             f"keeps them in a wooden box", uid=f"telegram:{100 + k}",
                             name=f"Member{k:02d}", age_days=i % 9))
    a.memories[G] = rows
    for i in range(120):
        event(a, G, f"the group talked about trip plan {i} for a long while and "
                    f"settled who drives", time.time() - (i + 1) * 3600 * 5)
    a.episode_store.set_thread(G, "Sam is choosing a date for the trip; Alex asked "
                               "who brings the tent.", time.time() - DAY, time.time())


# ---------------------------------------------------------------------------
# The budget and the caps
# ---------------------------------------------------------------------------

def test_the_block_stays_within_the_budget_and_the_summary_comes_first(tmp: Path) -> None:
    for budget in (2400, 1200, 600):
        a = make_agent(tmp / str(budget), memory_prompt_chars=budget)
        crowded(a)
        block, placed = a._memory_block(G, "what about the outing")
        check(f"{budget}: within MEMORY_PROMPT_CHARS", counted(block) <= budget,
              f"{counted(block)} > {budget}")
        check(f"{budget}: the summary is first",
              block.index("<earlier_in_chat>") < block.index("<memories>"), block)
        check(f"{budget}: something was placed", placed, block)
    small = make_agent(tmp / "small", memory_prompt_chars=300)
    crowded(small)
    block, _ = small._memory_block(G, "")
    quote = re.search(r"\n(\".*\")\n</earlier_in_chat>", block).group(1)
    check("below 800 the summary takes at most half", len(quote) <= 150, quote)


def test_the_caps_hold_with_room_to_spare(tmp: Path) -> None:
    a = make_agent(tmp, memory_prompt_chars=100000)
    crowded(a)
    block, _ = a._memory_block(G, "outing maps trip")
    group = item_lines(block, "Things noted about the group:")
    persons = re.findall(r"^About .*:$", block, re.MULTILINE)
    check("at most 8 group facts", len(group) == 8, repr(group))
    check("at most 6 people", len(persons) == 6, repr(persons))
    for header in persons:
        check(f"at most 5 facts for {header}", len(item_lines(block, header)) <= 5)
    check("at most 4 events", len(item_lines(block, "What happened:")) == 4)
    a_week = timewords.resolve("last week", time.time(), a._prompt_tz())
    event(a, G, "the group talked about something last week", a_week[0] + 3600)
    block, _ = a._memory_block(G, "what did we do last week")
    check("one more event when a time word resolved",
          len(item_lines(block, "What happened:")) == 5)


# ---------------------------------------------------------------------------
# The ranking
# ---------------------------------------------------------------------------

def test_importance_and_use_rank_among_equal_matches(tmp: Path) -> None:
    a = make_agent(tmp, memory_prompt_chars=100000)
    a.memories[G] = [
        note("the group likes the harbour cafe", imp=1, age_days=0.1, nid="mnew0000001"),
        note("the group likes the harbour market", imp=5, age_days=5, nid="mold0000001"),
    ]
    block, _ = a._memory_block(G, "harbour")
    check("importance 5 beats a newer importance 1",
          block.index("harbour market") < block.index("harbour cafe"), block)

    a.memories[G] = [
        note("the group swims on sunday", age_days=3, nid="m0000000001"),
        note("the group runs on sunday", age_days=3, uses=4, nid="m0000000002"),
    ]
    stamp = a.memories[G][0]["time"]
    for row in a.memories[G]:
        row["time"] = row["born"] = stamp
    first, _ = a._memory_block(G, "sunday")
    check("use breaks a tie", first.index("runs") < first.index("swims"), first)
    second, _ = a._memory_block(G, "sunday")
    check("the same order on a second build", first == second)


def test_a_quiet_member_named_in_the_message_is_recalled(tmp: Path) -> None:
    a = make_agent(tmp)
    speak(a, G, "telegram:7", "Sam")
    a.memories[G] = [note("Kim keeps bees", uid="telegram:9", name="Kim"),
                     note("Lee plays the cello", uid="telegram:8", name="Lee")]
    check("an absent member is not recalled unnamed",
          "bees" not in a._memories_for_prompt(G, "how is everyone"))
    block = a._memories_for_prompt(G, "has anyone heard from kim lately")
    check("named, a quiet member's facts come in", "bees" in block, block)
    check("another absent member still does not", "cello" not in block, block)


@pytest.mark.parametrize("lang,question", [("en", "what did we do last week?"),
                                           ("zh", "上周干嘛了")])
def test_a_time_word_brings_that_weeks_event(tmp: Path, lang: str, question: str) -> None:
    a = make_agent(tmp, lang=lang)
    span = timewords.resolve(question, time.time(), a._prompt_tz())
    old = span[0] + 20 * 3600
    event(a, G, "we went to the climbing gym together", old)
    for i in range(6):
        event(a, G, f"chatted about lunch options number {i}", time.time() - 3600 * (i + 1),
              imp=5)
    plain = a._memories_for_prompt(G, "anything new")
    check("without a time word the old event loses its slot", "climbing" not in plain, plain)
    block = a._memories_for_prompt(G, question)
    check("the time word brings that week's event", "climbing" in block, block)
    line = next(ln for ln in block.split("\n") if "climbing" in ln)
    check("its date is made by code", ranking.day_label(old, a._prompt_tz()) in line
          and "days ago" in line, line)
    check("no 'nothing remembered' line when one matched", "Nothing is remembered" not in block)


def test_with_no_event_in_range_the_header_says_so(tmp: Path) -> None:
    a = make_agent(tmp)
    event(a, G, "we talked about the weather", time.time() - 3600)
    block = a._memories_for_prompt(G, "what happened last month")
    span = timewords.resolve("last month", time.time(), a._prompt_tz())
    check("the empty range is named",
          f"Nothing is remembered from {timewords.phrase(span, tz=a._prompt_tz())}." in block,
          block)
    check("the general rule is in the header",
          "no event below is from then, you have no recollection of it" in block)
    check("today is never 'nothing remembered': the chat itself shows it",
          "Nothing is remembered" not in a._memories_for_prompt(G, "what's up today"))


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def test_facts_and_events_render_with_who_and_when(tmp: Path) -> None:
    a = make_agent(tmp)
    speak(a, G, "telegram:7", "Sam")
    a.memories[G] = [note("Sam owes Kim money", uid="telegram:7", name="Sam",
                          said_by="telegram:5", said_by_name="Alex", age_days=14)]
    a.memories[G][0]["time"] = time.time()
    start = time.time() - 3 * DAY
    event(a, G, "Sam and Alex planned the trip", start, names=("Sam", "Alex"))
    block = a._memories_for_prompt(G, "money")
    check("reported speech says who said it",
          f"said by {_USER_DATA_OPEN}Alex{_USER_DATA_CLOSE}" in block, block)
    check("the age is first noted then confirmed",
          "first noted 14 days ago, confirmed today" in block, block)
    line = next(ln for ln in block.split("\n") if "planned the trip" in ln)
    check("an event carries its code-made date and its people",
          ranking.date_span(start, start + 3600, time.time(), a._prompt_tz()) in line
          and "3 days ago" in line
          and f"{_USER_DATA_OPEN}Sam, Alex{_USER_DATA_CLOSE}" in line, ascii(line))


def test_a_dm_files_unattributed_facts_under_this_chat(tmp: Path) -> None:
    a = make_agent(tmp, lang="zh")
    dm = "private:telegram:7"
    a.memories[dm] = [note("我们约了周五吃火锅"),
                      note("我喜欢吃辣", uid="telegram:7", name="张三")]
    block = a._memories_for_prompt(dm, "")
    check("unattributed: things noted in this chat",
          "Things noted in this chat:" in block and "about the group" not in block, block)
    check("the zh first person still becomes the name", "张三喜欢吃辣" in block, block)


def test_other_chats_events_and_summaries_never_come_in(tmp: Path) -> None:
    a = make_agent(tmp, memory_share_rooms=True)
    other = "telegram:room2"
    speak(a, G, "telegram:7", "Sam")
    speak(a, other, "telegram:7", "Sam")
    event(a, other, "Sam told room two a secret", time.time() - 3600)
    a.episode_store.set_thread(other, "room two is planning a surprise", 1.0, 2.0)
    a.memories[other] = [note("Sam keeps bees", uid="telegram:7", name="Sam"),
                         note("Sam is broke", uid="telegram:7", name="Sam",
                              said_by="telegram:5", said_by_name="Alex"),
                         note("room two meets on friday")]
    block = a._memories_for_prompt(G, "secret surprise bees broke friday")
    check("a shared fact about a present person travels", "bees" in block, block)
    check("no event, summary, reported speech or group fact from another room",
          not any(s in block for s in ("secret", "surprise", "broke", "friday")), block)


# ---------------------------------------------------------------------------
# The prompts
# ---------------------------------------------------------------------------

def test_the_gate_gets_the_summary_but_no_facts_or_events(tmp: Path) -> None:
    a = make_agent(tmp)
    speak(a, G, "telegram:7", "Sam", "anyone up for the trip")
    a.memories[G] = [note("the group likes trips")]
    event(a, G, "planned a trip", time.time() - DAY)
    a.episode_store.set_thread(G, "Sam is choosing a date.", time.time() - DAY, time.time())
    prompt = a._build_group_prompt(G, "called", "trip?")
    check("the reply prompt has both", "<memories>" in prompt.system
          and "<earlier_in_chat>" in prompt.system)
    check("the gate has the summary only", "<earlier_in_chat>" in prompt.gate_system
          and "<memories>" not in prompt.gate_system, prompt.gate_system[-800:])
    check("the placed items are kept for the use count",
          len(a._last_recalled[G]) == 2, repr(a._last_recalled))

    a.episode_store.set_thread(G, "Sam picked Saturday.", time.time() - DAY, time.time())
    later = a._build_group_prompt(G, "called", "trip?")
    shared = (next((i for i, (x, y) in enumerate(zip(prompt.system, later.system))
                       if x != y), min(len(prompt.system), len(later.system))))
    head = prompt.system.index("<earlier_in_chat>")
    check("a new summary changes only the tail: the cached front stays",
          shared >= head - 2, f"{shared} < {head}")


def test_pauses_and_the_first_line_time_are_marked(tmp: Path) -> None:
    a = make_agent(tmp)
    now = time.time()
    speak(a, G, "telegram:7", "Sam", "morning", now - 5 * 3600 - 1200)
    speak(a, G, "telegram:8", "Kim", "hey", now - 5 * 3600 - 600)
    speak(a, G, "telegram:7", "Sam", "back now", now - 2 * 3600)
    user = a._build_group_prompt(G, "called", "back now").user
    check("a 3 hour pause is marked outside the data", "[— 3 hours later —]" in user
          and f"{_USER_DATA_CLOSE}\n[— 3 hours later —]\n{_USER_DATA_OPEN}" in user, repr(user))
    check("a 10 minute pause is not", "minutes later" not in user, user)
    check("the first line's time is given", "[earliest line shown: " in user, user)


def test_a_small_chat_context_limits_what_a_reply_reads(tmp: Path) -> None:
    a = make_agent(tmp)
    a.chat_context_messages = 20
    a.buffers[G] = [{"name": "Sam", "text": f"line{i:02d}", "user_id": "telegram:7"}
                    for i in range(25)]
    user = a._build_group_prompt(G, "proactive", "").user
    check("20 lines are shown", "line05" in user and "line04" not in user, user)


def test_a_dm_sends_only_role_and_content_and_notes_the_pause(tmp: Path) -> None:
    a = make_agent(tmp)
    then = time.time() - 2 * DAY
    history = [{"role": "user", "content": "see you", "t": then - 60, "seq": 1},
               {"role": "assistant", "content": "bye", "t": then, "seq": 2},
               {"role": "user", "content": "back again", "t": time.time(), "seq": 3}]
    prompt = a._build_dm_prompt(history, is_admin=False, pkey="private:telegram:7")
    check("turns carry role and content only",
          all(set(m) == {"role", "content"} for m in prompt.messages), repr(prompt.messages))
    check("the pause goes into the turn context",
          "The message before this one came 2 days earlier." in prompt.turn_context)
    check("never into the turns", not any("earlier" in m["content"] for m in prompt.messages))
    history[-1]["t"] = then + 600
    check("a short pause is not noted", "[Pause]" not in a._build_dm_prompt(
        history, is_admin=False, pkey="private:telegram:7").turn_context)


# ---------------------------------------------------------------------------
# Use counting
# ---------------------------------------------------------------------------

def test_use_is_counted_only_for_what_the_sent_reply_drew_on(tmp: Path) -> None:
    a = make_agent(tmp)
    speak(a, G, "telegram:7", "Sam", "how was the climbing")
    a.memories[G] = [note("Sam started bouldering at the climbing gym", uid="telegram:7",
                          name="Sam", nid="mclimb00001"),
                     note("the group meets at the harbour cafe", nid="mcafe000001")]
    ep = event(a, G, "Sam fell off the climbing wall laughing", time.time() - DAY)
    a._build_group_prompt(G, "called", "how was the climbing")
    check("building a prompt counts nothing",
          all(not r.get("uses") for r in a.memories[G]) and not ep["uses"])
    a._mark_used(G, "did the climbing gym wall treat you better this time")
    climb, cafe = a.memories[G]
    check("the facts the reply shares two words with are counted",
          climb["uses"] == 1 and climb["used"] > 0, repr(climb))
    check("so is the event", ep["uses"] == 1, repr(ep))
    check("the unrelated one is not", not cafe.get("uses"), repr(cafe))
    stored = json.loads(a.memory_file.read_text(encoding="utf-8"))
    check("the count reached the file", stored[G][0]["uses"] == 1, repr(stored))
    a._mark_used(G, "did the climbing gym wall treat you better this time")
    check("one prompt counts once", climb["uses"] == 1)

    a._build_group_prompt(G, "called", "climbing")
    a._mark_used(G, "climbing gym again")
    check("a second use is counted in memory", climb["uses"] == 2)
    stored = json.loads(a.memory_file.read_text(encoding="utf-8"))
    check("but not written again within the minute", stored[G][0]["uses"] == 1)
    a._flush_memory_counters(force=True)
    stored = json.loads(a.memory_file.read_text(encoding="utf-8"))
    check("a forced flush writes it", stored[G][0]["uses"] == 2)

    a._build_group_prompt(G, "called", "climbing")
    a.memories[G] = [r for r in a.memories[G] if r["id"] != "mclimb00001"]
    a._mark_used(G, "climbing gym again")
    check("a forgotten item is never written back",
          all(r["id"] != "mclimb00001" for r in a.memories[G]))
