"""What a newcomer's first setup meets: a blank NapCat URL, a persona copied
from the template, a model that fails, a connector that echoes the bot."""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from persona_agent import promotion
from persona_agent.agent import Agent
from persona_agent.access import ADMIN_MODE
from persona_agent.connector import synthesize_onebot_payload
from persona_agent.prompts import MODEL_FAILURE_EXCUSES, render_persona_template
from persona_agent.transport import SendResult

QQ_BOT_ID = "10001"


def check(name: str, cond: bool, detail: str = "") -> None:
    assert cond, name + (f" - {detail}" if detail else "")


def make_agent(tmp: Path, **overrides) -> Agent:
    settings = dict(
        api_key="test-key", qq_bot_id=QQ_BOT_ID, persona_name="Luna",
        memory_file=str(tmp / "memory.json"), persona="test persona",
        eval_file=str(tmp / "eval.jsonl"), stickers_dir=str(tmp / "stickers"),
        stickers_file=str(tmp / "stickers.json"), message_debounce_sec=0,
        lang="en", admin_ids=("42",))
    settings.update(overrides)
    a = Agent(**settings)
    a._seen_msg_file = tmp / "seen_msg_ids.json"
    a.example_candidates = promotion.CandidatePool(tmp / "example_candidates.json")
    a.core_memory_file = tmp / "core_memory.json"
    a.connector_handles.path = tmp / "connector_handles.json"
    a._seen_msg_ids.clear()
    a.core_memory.clear()
    a._typing_delay = lambda chunk: 0.0
    return a


def _group(text: str, *, user: str = "7", mid: str = "m1", at_bot: bool = True) -> dict:
    segments = ([{"type": "at", "data": {"qq": QQ_BOT_ID}}] if at_bot else [])
    return {"post_type": "message", "message_type": "group", "group_id": "555",
            "user_id": user, "message_id": mid, "sender": {"nickname": "Ann"},
            "message": segments + [{"type": "text", "data": {"text": text}}],
            "raw_message": text}


# ---- the persona template ---------------------------------------------------

_TEMPLATE = (
    "You're {bot_name}, a regular here.\n\n"
    "Relationships (optional):\n"
    "- The person you're closest to is {admin_name} ({admin_relationship}). Be looser with them\n"
    "- Everyone else: read the room\n\n"
    "————\n"
    "This is the persona template. Copy it to persona.txt and rewrite it.\n")


def test_the_template_placeholders_are_filled_and_its_note_dropped() -> None:
    out = render_persona_template(_TEMPLATE, bot_name="Luna")
    check("the name is filled in", out.startswith("You're Luna, a regular here."), out)
    check("no admin: the line about one is dropped", "{admin" not in out
          and "closest" not in out and "Everyone else" in out, out)
    check("the note to the reader is cut", "persona.txt" not in out
          and "————" not in out, out)
    out = render_persona_template(_TEMPLATE, bot_name="Luna", admin_name="Kai")
    check("an admin without a relationship loses only the parenthesis",
          "closest to is Kai. Be looser" in out, out)
    out = render_persona_template(_TEMPLATE, bot_name="Luna", admin_name="Kai",
                                  admin_relationship="old friend")
    check("both filled", "closest to is Kai (old friend)." in out, out)
    own = "I'm Mira.\n---\nSecond section, kept."
    check("a document of the user's own is unchanged",
          render_persona_template(own, bot_name="Luna") == own)


def test_a_persona_file_copied_from_the_template_reaches_the_model_filled(
        tmp: Path, monkeypatch) -> None:
    persona = tmp / "persona.txt"
    persona.write_text(_TEMPLATE, encoding="utf-8")
    monkeypatch.setenv("PERSONA_FILE", str(persona))
    agent = make_agent(tmp, persona=None, admin_name="")
    check("the loaded persona has no placeholder and no note",
          "{" not in agent.persona and "persona.txt" not in agent.persona
          and agent.persona.startswith("You're Luna"), agent.persona)


# ---- the connector's own echo and the synthesized mention -------------------

async def test_the_bots_own_message_is_owned_and_not_answered(tmp: Path) -> None:
    agent = make_agent(tmp)
    thought: list = []

    async def fake_think(*a, **k):
        thought.append(a)
        return "hi", "chat", ""

    agent._think = fake_think
    out = await agent.handle_event({
        "platform": "telegram", "conversation_type": "group",
        "conversation_id": "-100", "sender_id": "999", "bot_id": "999",
        "sender_name": "Luna", "sent_at": 0, "addressed": True,
        "segments": [{"type": "text", "text": "Luna says hi"}], "text": "Luna says hi"})
    check("owned, not handled, nothing to relay",
          out == {"handled": False, "owned": True, "replies": []}, repr(out))
    check("and no model turn ran", not thought)


async def test_a_synthesized_mention_is_followed_by_a_space(tmp: Path) -> None:
    agent = make_agent(tmp, qq_bot_id="")
    payload = synthesize_onebot_payload(
        {"platform": "telegram", "conversation_type": "group",
         "conversation_id": "-1", "sender_id": "5", "bot_id": "999",
         "addressed": True, "segments": [{"type": "text", "text": "thanks"}]},
        agent._self_mention_id())
    check("reply-to-bot reads as '@Luna thanks'",
          await agent._extract_text(payload) == "@Luna thanks",
          repr(await agent._extract_text(payload)))
    qq = {"message": [{"type": "at", "data": {"qq": agent._self_mention_id()}},
                      {"type": "text", "data": {"text": " thanks"}},
                      {"type": "at", "data": {"qq": "77"}},
                      {"type": "at", "data": {"qq": "78"}}]}
    check("a client's own space is not doubled, and two mentions are apart",
          await agent._extract_text(qq) == "@Luna thanks@77 @78",
          repr(await agent._extract_text(qq)))


# ---- a model that fails -----------------------------------------------------

async def _failing_turn(agent: Agent, payload: dict) -> list:
    sent: list = []

    async def failing_think(*a, **k):
        raise RuntimeError("401 Unauthorized")

    async def fake_send(group_id, text, at_user_id=""):
        sent.append(text)
        return SendResult(success=True)

    agent._think = failing_think
    agent._send_group = fake_send
    await agent.handle_onebot(payload)
    for _ in range(20):
        await asyncio.sleep(0)
    return sent


async def test_the_admins_call_gets_an_excuse_once_per_cooldown(tmp: Path) -> None:
    agent = make_agent(tmp, qq_onebot_url="http://127.0.0.1:9")
    sent = await _failing_turn(agent, _group("you there?", user="42", mid="a1"))
    check("the admin's @ is answered with an excuse, not silence",
          len(sent) == 1 and sent[0] in MODEL_FAILURE_EXCUSES["en"], repr(sent))
    sent = await _failing_turn(agent, _group("hello??", user="7", mid="a2"))
    check("the next failure in the same chat stays quiet (cooldown)", sent == [],
          repr(sent))
    agent._last_excuse_at.clear()
    sent = await _failing_turn(agent, _group("hey are you around", user="7", mid="a3"))
    check("a called turn gets it too", len(sent) == 1, repr(sent))
    sent = await _failing_turn(agent, _group("chatter", user="7", mid="a4", at_bot=False))
    check("a turn nobody addressed to it never does", sent == [], repr(sent))
    check("the admin mode is the one the excuse covers", ADMIN_MODE == "owner")


async def test_a_dm_gets_an_excuse_in_the_agents_language(tmp: Path) -> None:
    agent = make_agent(tmp, lang="zh", qq_onebot_url="http://127.0.0.1:9")
    dms: list = []

    async def failing_chat(*a, **k):
        raise RuntimeError("402 Payment Required")

    async def fake_send_dm(user_id, text):
        dms.append((user_id, text))
        return SendResult(success=True)

    agent._chat_dm = failing_chat
    agent._send_dm = fake_send_dm
    payload = {"post_type": "message", "message_type": "private", "user_id": "42",
               "message_id": "d1", "sender": {"nickname": "K"},
               "message": [{"type": "text", "data": {"text": "在吗"}}],
               "raw_message": "在吗"}
    await agent.handle_onebot(payload)
    check("the DM is told why it is quiet, in Chinese",
          len(dms) == 1 and dms[0][1] in MODEL_FAILURE_EXCUSES["zh"], repr(dms))
    check("and the reader's message waits for the next turn",
          agent._dm_unanswered.get("42") == ["在吗"], repr(agent._dm_unanswered))
    await agent.handle_onebot({**payload, "message_id": "d2"})
    check("the cooldown holds in DMs too", len(dms) == 1, repr(dms))


async def test_an_undelivered_excuse_does_not_spend_the_cooldown(tmp: Path) -> None:
    agent = make_agent(tmp, qq_onebot_url="")
    sent = await _failing_turn(agent, _group("you there?", user="42", mid="u1"))
    check("no route: nothing goes out", sent == [], repr(sent))
    check("and the cooldown is not started", "555" not in agent._last_excuse_at,
          repr(agent._last_excuse_at))
    agent.qq_onebot_url = "http://127.0.0.1:9"
    sent = await _failing_turn(agent, _group("you there?", user="42", mid="u2"))
    check("once a route exists the next failure gets its excuse", len(sent) == 1,
          repr(sent))
    check("and that delivery starts the cooldown", "555" in agent._last_excuse_at)

    dm_agent = make_agent(tmp, qq_onebot_url="http://127.0.0.1:9")
    outcomes = [SendResult(success=False), SendResult(success=True)]
    dms: list = []

    async def failing_chat(*a, **k):
        raise RuntimeError("402 Payment Required")

    async def fake_send_dm(user_id, text):
        dms.append(text)
        return outcomes.pop(0)

    dm_agent._chat_dm = failing_chat
    dm_agent._send_dm = fake_send_dm
    payload = {"post_type": "message", "message_type": "private", "user_id": "42",
               "message_id": "e1", "sender": {"nickname": "K"},
               "message": [{"type": "text", "data": {"text": "hi"}}],
               "raw_message": "hi"}
    await dm_agent.handle_onebot(payload)
    await dm_agent.handle_onebot({**payload, "message_id": "e2"})
    await dm_agent.handle_onebot({**payload, "message_id": "e3"})
    check("a failed DM excuse is retried on the next message, then held",
          len(dms) == 2, repr(dms))


# ---- no NapCat HTTP server ---------------------------------------------------

async def test_a_blank_onebot_url_means_no_napcat_calls(tmp: Path, caplog) -> None:
    agent = make_agent(tmp, qq_onebot_url="")
    posts: list = []

    class _NoHTTP:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, **kw):
            posts.append(url)
            raise AssertionError("no NapCat call without QQ_ONEBOT_URL")

    agent._http = lambda **kw: _NoHTTP()
    agent.access_groups = {"555"}
    with caplog.at_level(logging.INFO, logger="agent"):
        await agent.check_missed_mentions()
        check("no sweep", posts == [], repr(posts))
        sent = await agent._send_group("555", "hello there")
        sent_again = await agent._send_group("555", "hello again")
        check("a direct QQ send fails without an HTTP call",
              not sent.success and not sent_again.success and posts == [])
        out = await agent._send_background(
            "555", lambda: agent._send_group("555", "nobody asked"), reason="proactive")
        check("an unprompted QQ message has no route", not out.success)
    lines = [r.getMessage() for r in caplog.records]
    check("the direct send says why, once",
          sum("QQ_ONEBOT_URL" in m and "cannot send" in m for m in lines) == 1,
          repr(lines))
    check("the unprompted one says why too",
          any("unprompted" in m and "QQ_ONEBOT_URL is not set" in m for m in lines),
          repr(lines))


async def test_the_sweep_needs_the_bots_qq_number(tmp: Path) -> None:
    agent = make_agent(tmp, qq_bot_id="", qq_onebot_url="http://127.0.0.1:9")
    posts: list = []

    class _Spy:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, **kw):
            posts.append(url)
            raise AssertionError("no sweep without QQ_BOT_ID")

    agent._http = lambda **kw: _Spy()
    agent.access_groups = {"555"}
    await agent.check_missed_mentions()
    check("no QQ_BOT_ID, no sweep (a bare '@' matches every email address)",
          posts == [], repr(posts))


# ---- what the model and the operator read -------------------------------------

def test_no_prompt_names_a_placeholder_nothing_fills() -> None:
    from persona_agent.prompts import STYLE_GUIDE

    check("the group style guide speaks of 'your own name', not BOT_NAME",
          "BOT_NAME" not in STYLE_GUIDE and "your own name" in STYLE_GUIDE)


def test_a_rejected_key_is_one_operator_line(tmp: Path, caplog) -> None:
    import httpx

    agent = make_agent(tmp, base_url="https://api.openai.com")
    error = httpx.HTTPStatusError(
        "401", request=httpx.Request("POST", "https://api.openai.com/v1/chat/completions"),
        response=httpx.Response(401, json={"error": {"message": "Incorrect API key"}}))
    with caplog.at_level(logging.ERROR, logger="agent"):
        agent._report_fatal(error, agent.model)
        agent._report_fatal(error, agent.model)
    lines = [r.getMessage() for r in caplog.records if "model provider" in r.getMessage()]
    check("one line naming the host and the settings to check",
          len(lines) == 1 and "api.openai.com" in lines[0] and "API key" in lines[0]
          and "LLM_API_KEY" in lines[0] and "LLM_BASE_URL" in lines[0], repr(lines))


def test_operator_labels_say_dm() -> None:
    from persona_agent import health

    names = [name for name, _fn, _critical in health.CHECKS]
    check("the DM probe is labelled DM, with no vendor in it",
          "DM chat" in names and not any("openai" in n.lower() or "private" in n.lower()
                                         for n in names), repr(names))


# ---- background tasks ---------------------------------------------------------

async def test_a_crashed_background_task_is_logged_with_its_name(tmp: Path, caplog) -> None:
    agent = make_agent(tmp)

    async def tag_the_sticker():
        raise ValueError("bad sticker")

    with caplog.at_level(logging.ERROR, logger="agent"):
        task = agent._spawn(tag_the_sticker())
        await asyncio.gather(task, return_exceptions=True)
        await asyncio.sleep(0)
    lines = [r.getMessage() for r in caplog.records]
    check("named and explained", any("tag_the_sticker" in m and "bad sticker" in m
                                     for m in lines), repr(lines))
    check("and released", task not in agent._bg_tasks)


def test_a_direct_qq_setup_without_a_napcat_url_is_named() -> None:
    """On the direct route every reply goes out through QQ_ONEBOT_URL, which
    is blank by default; through AstrBot it is optional."""
    from persona_agent import preflight

    def named(**env) -> bool:
        return any(f.key == "QQ_ONEBOT_URL" and f.level == "WARN"
                   for f in preflight.check_config(env={"LLM_API_KEY": "k", **env}))

    check("QQ_BOT_ID with no URL", named(QQ_BOT_ID="10001"))
    check("a OneBot secret with no URL", named(QQ_ONEBOT_SECRET="s"))
    check("not with the URL set",
          not named(QQ_BOT_ID="10001", QQ_ONEBOT_URL="http://127.0.0.1:3000"))
    check("not when QQ comes through AstrBot",
          not named(QQ_BOT_ID="10001", CONNECTOR_QQ_PLATFORMS="aiocqhttp"))
    check("not without QQ at all", not named())
