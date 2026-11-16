"""Approval of new chats: the waiting list, the agent's gate, the page and `personagent access`."""
from __future__ import annotations

import json
from pathlib import Path

from dotenv import dotenv_values
from fastapi.testclient import TestClient
import pytest

from persona_agent import access, approvals, chatlangs, welcome
from persona_agent.direct.__main__ import admits

from helpers import CLOSED_ONEBOT_URL, check, isolated_agent

TOKEN = "test-local-capability"
HEADERS = {welcome.TOKEN_HEADER: TOKEN}


class Clock:
    def __init__(self, now: float = 1_800_000_000.0):
        self.now = now

    def __call__(self) -> float:
        return self.now


def _home(tmp: Path, env: str = "") -> Path:
    home = tmp / "home"
    home.mkdir(parents=True, exist_ok=True)
    (home / ".env").write_text("LLM_API_KEY=sk-test\nPERSONA_NAME=Nova\n" + env, encoding="utf-8")
    return home


def _env(home: Path) -> dict:
    return {k: v or "" for k, v in dotenv_values(home / ".env").items()}


# ---------------------------------------------------------------- the waiting list

def test_a_request_gets_a_short_code_and_one_answer_a_day(tmp: Path) -> None:
    clock = Clock()
    store = approvals.Store(tmp / "approvals.json", clock=clock)
    code, tell = store.note(platform="telegram", kind="dm", chat_id="telegram:42", name="Ann", words="hello")
    check("a code of six unambiguous characters",
          len(code) == approvals.CODE_LENGTH and set(code) <= set(approvals.ALPHABET), code)
    check("no 0/O, 1/I/L, 2/Z, 5/S or 8/B to misread", not set("0O1IL2Z5S8B") & set(approvals.ALPHABET))
    check("the first message is answered", tell)
    again = [store.note(platform="telegram", kind="dm", chat_id="telegram:42", words="hi?") for _ in range(30)]
    check("however often they write, no second answer within a day",
          all(c == code and not t for c, t in again), repr(again[:2]))
    clock.now += approvals.TELL_EVERY_S
    check("a day later the same code is said once more",
          store.note(platform="telegram", kind="dm", chat_id="telegram:42") == (code, True))
    saved = store.snapshot()["waiting"]
    check("one entry, its first words kept, not the later ones",
          len(saved) == 1 and saved[0]["words"] == "hello" and saved[0]["name"] == "Ann", repr(saved))
    clock.now += approvals.CODE_TTL_S
    check("an expired request is gone with its words", store.snapshot()["waiting"] == [])
    fresh, tell = store.note(platform="telegram", kind="dm", chat_id="telegram:42")
    check("...and the next message makes a new one", tell and fresh != "")


def test_a_flood_of_strangers_gets_a_bounded_list_and_bounded_answers(tmp: Path) -> None:
    store = approvals.Store(tmp / "approvals.json", clock=Clock())
    told = sum(store.note(platform="discord", kind="dm", chat_id=f"discord:{n}")[1] for n in range(200))
    check("at most MAX_WAITING answers for a whole flood", told == approvals.MAX_WAITING["dm"], str(told))
    check("the list holds MAX_WAITING per platform",
          len(store.snapshot()["waiting"]) == approvals.MAX_WAITING["dm"])
    check("another platform has its own room",
          store.note(platform="telegram", kind="dm", chat_id="telegram:1")[1])
    codes = [w["code"] for w in store.snapshot()["waiting"]]
    check("codes are unique", len(set(codes)) == len(codes))


def test_what_a_stranger_writes_is_kept_short_and_harmless(tmp: Path) -> None:
    store = approvals.Store(tmp / "approvals.json", clock=Clock())
    store.note(platform="telegram", kind="dm", chat_id="telegram:7",
               name="\x1b[31mEve‮" + "x" * 200, words="line\none\x07 <script>alert(1)</script>" + "y" * 300)
    entry = store.snapshot()["waiting"][0]
    check("no control, escape or bidi characters survive",
          not any(ch in entry["name"] + entry["words"] for ch in "\x1b‮\x07\n"), repr(entry))
    check("the name and the words are cut",
          len(entry["name"]) <= approvals.NAME_CHARS + 1 and len(entry["words"]) <= approvals.WORDS_CHARS + 1)
    for bad in ("telegram:a b", "telegram:", ":1", "telegram:" + "x" * 200, "telegram:a\x00"):
        check(f"an id the file cannot hold makes no request: {bad!r}",
              store.note(platform="telegram", kind="dm", chat_id=bad) == ("", False))


def test_approvals_are_kept_apart_and_the_code_works_once(tmp: Path) -> None:
    home = _home(tmp, "ACCESS_DM_USERS=telegram:5\n")
    store = approvals.Store(approvals.store_path(home), clock=Clock())
    dm, _ = store.note(platform="telegram", kind="dm", chat_id="telegram:42", words="hi")
    group, _ = store.note(platform="telegram", kind="group", chat_id="telegram:-100", name="Book club")
    me, _ = store.note(platform="discord", kind="dm", chat_id="discord:9")
    no, _ = store.note(platform="discord", kind="dm", chat_id="discord:66", words="buy now")
    store.decide("approve", code=dm.lower())
    with pytest.raises(approvals.Refused):
        store.decide("admin", code=group)
    store.decide("approve", code=group)
    store.decide("admin", code=f" {me[:3]}-{me[3:]} ")
    store.decide("decline", code=no)
    view = store.view()
    check("the settings are left as they were", _env(home).get("ACCESS_DM_USERS") == "telegram:5"
          and "ADMIN_IDS" not in _env(home) and "ACCESS_GROUPS" not in _env(home), repr(_env(home)))
    check("approved: a DM, a group, an admin",
          view["dm"] == {"telegram:42", "discord:9"} and view["group"] == {"telegram:-100"}
          and view["admins"] == {"discord:9"}, repr(view))
    check("the declined id is not approved", view["declined"] == {"discord:66"})
    data = store.snapshot()
    check("decided requests leave the list", data["waiting"] == [])
    check("a decline keeps the id but not the words",
          data["declined"][0]["id"] == "discord:66" and "words" not in data["declined"][0]
          and "buy now" not in approvals.store_path(home).read_text(encoding="utf-8"))
    with pytest.raises(LookupError):
        store.decide("approve", code=dm)
    check("a declined chat is never answered or listed again",
          store.note(platform="discord", kind="dm", chat_id="discord:66") == ("", False))
    check("undo lets it ask again", store.undo("discord:66") == "declined"
          and store.note(platform="discord", kind="dm", chat_id="discord:66")[1])
    check("undo forgets an approval too", store.undo("telegram:42") == "approved"
          and "telegram:42" not in store.view()["dm"])
    check("undoing an unknown id says so", not store.undo("discord:404"))


def test_policy_and_the_live_settings(tmp: Path) -> None:
    home = _home(tmp, "ADMIN_IDS=1\n")
    live = approvals.LiveEnv(home / ".env")
    check("a key unchanged since the start keeps its startup value", live.get("ADMIN_IDS") is None)
    check("policy: on", approvals.set_policy(home, "Telegram", True))
    check("policy: on twice changes nothing", not approvals.set_policy(home, "telegram", True))
    approvals.set_policy(home, "discord", True)
    check("the page and the API never ask",
          not approvals.set_policy(home, "browser", True) and not approvals.set_policy(home, "api", True))
    check("both are listed", approvals.policy(_env(home)) == {"telegram", "discord"})
    check("the running service sees the change", live.get(access.APPROVAL_SETTING) == "telegram,discord")
    approvals.set_policy(home, "telegram", False)
    check("policy: off", approvals.policy(_env(home)) == {"discord"})
    check("...seen at once", live.get(access.APPROVAL_SETTING) == "discord")


def test_who_waits_for_approval() -> None:
    on = {"telegram", "aiocqhttp", "irc"}
    dm = access.awaits_dm_approval
    check("a stranger on a platform that asks waits",
          dm("telegram:42", "telegram", set(), set(), on, via_connector=True))
    check("the admin does not", not dm("telegram:1", "telegram", {"telegram:1"}, set(), on, via_connector=True))
    check("a listed person does not",
          not dm("telegram:42", "telegram", set(), {"telegram:42"}, on, via_connector=True))
    check("a platform that does not ask is left to the old rules",
          not dm("discord:9", "discord", set(), set(), on, via_connector=True))
    check("a native connector's bare id is judged by its platform",
          dm("555", "aiocqhttp", set(), set(), on, via_connector=True))
    check("a namespaced id on the QQ webhook is refused, not held",
          not dm("telegram:42", "qq", set(), set(), {"qq"}, via_connector=False))
    check("the page and the API never ask", access.approval_platforms("browser,api,Telegram") == {"telegram"})
    group = access.awaits_group_approval
    check("an unlisted group waits", group("telegram:-1", "telegram", set(), on, via_connector=True))
    check("a listed group does not", not group("telegram:-1", "telegram", {"telegram:-1"}, on, via_connector=True))
    check("channels typed in at connecting count as approved",
          not group("irc:#chan", "irc", set(), on, via_connector=True))


# ---------------------------------------------------------------- the agent

def _agent(tmp: Path, **settings):
    agent = isolated_agent(tmp, qq_bot_id="10001", qq_onebot_url=CLOSED_ONEBOT_URL,
                           admin_ids=("telegram:1",), **settings)
    agent._typing_delay = lambda chunk: 0.0
    served: list = []

    async def fake_think(group_id, mode, text="", caller_override=None):
        served.append((group_id, mode))
        return "on my way", "called", ""

    async def fake_chat_dm(history, is_admin=False, pkey="", proactive=False):
        served.append((pkey, "owner" if is_admin else "friend"))
        return "hi back", ""

    agent._think = fake_think
    agent._chat_dm = fake_chat_dm
    return agent, served


def _dm(platform: str, uid: str, mid, text: str = "hi there", **extra) -> dict:
    return {"platform": platform, "conversation_type": "dm", "conversation_id": uid, "sender_id": uid,
            "sender_name": "Someone", "bot_id": "999000", "message_id": mid, "addressed": False,
            "segments": [{"type": "text", "text": text}], "text": text, **extra}


def _group(platform: str, gid: str, uid: str, mid, *, at_me: bool = True, text: str = " are you there",
           **extra) -> dict:
    segments = [{"type": "text", "text": text}]
    if at_me:
        segments.insert(0, {"type": "mention", "user_id": "999000", "name": "TestBot"})
    return {"platform": platform, "conversation_type": "group", "conversation_id": gid, "sender_id": uid,
            "sender_name": "Someone", "bot_id": "999000", "message_id": mid, "addressed": at_me,
            "segments": segments, "text": text.strip(), **extra}


async def test_an_existing_home_answers_as_before(tmp: Path) -> None:
    agent, served = _agent(tmp)
    reply = await agent.handle_event(_dm("telegram", "42", 1))
    check("no platform asks: a stranger's DM is answered, as before",
          reply["owned"] and ("private:telegram:42", "friend") in served, repr(reply))
    group = await agent.handle_event(_group("telegram", "-100", "42", 2))
    check("...and an unlisted group too", group["owned"] and ("telegram:-100", "called") in served)
    check("nothing waits", not approvals.path_in(tmp).exists())


async def test_a_stranger_gets_the_fixed_line_and_no_model_turn(tmp: Path) -> None:
    agent, served = _agent(tmp, access_approval_platforms=("telegram",))
    first = await agent.handle_event(_dm("telegram", "42", 1, text="hello, can we talk"))
    check("no model turn", served == [], repr(served))
    texts = [item.get("text", "") for item in first["replies"]]
    waiting = approvals.Store(approvals.path_in(tmp)).snapshot()["waiting"]
    code = waiting[0]["code"] if waiting else "?"
    check("claimed, so a connector's own model stays quiet", first["owned"] is True)
    check("one fixed answer naming the code",
          len(texts) >= 1 and code in " ".join(texts) and "administrator" in " ".join(texts), repr(texts))
    check("the request waits with its first words",
          waiting and waiting[0]["id"] == "telegram:42" and waiting[0]["words"] == "hello, can we talk"
          and waiting[0]["platform"] == "telegram", repr(waiting))
    later = [await agent.handle_event(_dm("telegram", "42", 2 + n)) for n in range(5)]
    check("writing again brings no second answer", all(r["replies"] == [] and r["owned"] for r in later))
    check("still no model turn", served == [])
    check("nothing of theirs is kept as a conversation", "telegram:42" not in agent.dm_history)
    admin = await agent.handle_event(_dm("telegram", "1", 20))
    check("the admin is answered without approval", ("private:telegram:1", "owner") in served, repr(admin))
    page = await agent.handle_event(_dm("browser", "abcdef0123", 21))
    check("the page chat never asks", page["owned"] and any(k.startswith("private:browser") for k, _ in served))


async def test_the_fixed_line_follows_the_characters_language(tmp: Path) -> None:
    agent, _ = _agent(tmp, access_approval_platforms=("telegram",), lang="zh")
    reply = await agent.handle_event(_dm("telegram", "42", 1, text="hello"))
    text = "".join(item.get("text", "") for item in reply["replies"])
    check("in Chinese, whatever the stranger wrote", "管理员" in text, repr(text))


async def test_an_approval_reaches_the_running_service(tmp: Path) -> None:
    home = _home(tmp, "ACCESS_APPROVAL_PLATFORMS=telegram\n")
    agent, served = _agent(tmp / "rt", access_approval_platforms=("telegram",))
    agent.settings_env = approvals.LiveEnv(home / ".env")
    agent._approval_store = approvals.Store(approvals.store_path(home))
    await agent.handle_event(_dm("telegram", "42", 1))
    code = agent._approvals().snapshot()["waiting"][0]["code"]
    agent._approvals().decide("approve", code=code)
    reply = await agent.handle_event(_dm("telegram", "42", 2))
    check("approved: answered on the next message, no restart",
          reply["owned"] and ("private:telegram:42", "friend") in served, repr((reply, served)))
    await agent.handle_event(_dm("telegram", "77", 3))
    me = agent._approvals().snapshot()["waiting"][0]["code"]
    agent._approvals().decide("admin", code=me)
    await agent.handle_event(_dm("telegram", "77", 4))
    check("This is me: answered as the admin", ("private:telegram:77", "owner") in served, repr(served))
    approvals.set_policy(home, "discord", True)
    served.clear()
    await agent.handle_event(_dm("discord", "9", 5))
    check("a platform that starts asking does so at once", served == [], repr(served))


async def test_an_unapproved_group_stays_silent(tmp: Path) -> None:
    agent, served = _agent(tmp, access_approval_platforms=("telegram", "irc"))
    chatter = await agent.handle_event(_group("telegram", "-100", "42", 1, at_me=False,
                                              text="just chatting here", conversation_name="Book club"))
    check("chatter there: nothing said, nothing waiting, no model turn",
          chatter["replies"] == [] and chatter["owned"] and served == []
          and not approvals.Store(approvals.path_in(tmp)).snapshot()["waiting"], repr(chatter))
    called = await agent.handle_event(_group("telegram", "-100", "42", 2, conversation_name="Book club"))
    texts = " ".join(item.get("text", "") for item in called["replies"])
    waiting = approvals.Store(approvals.path_in(tmp)).snapshot()["waiting"]
    check("addressed: one fixed line", "not approved this group" in texts and served == [], repr(texts))
    check("the group waits under its name",
          waiting and waiting[0]["kind"] == "group" and waiting[0]["name"] == "Book club", repr(waiting))
    again = await agent.handle_event(_group("telegram", "-100", "43", 3))
    check("at most one line a day", again["replies"] == [])
    await agent.handle_event(_group("irc", "#chan", "nick", 4))
    check("a channel typed in at connecting is answered", ("irc:#chan", "called") in served, repr(served))


async def test_a_declined_stranger_hears_nothing(tmp: Path) -> None:
    agent, served = _agent(tmp, access_approval_platforms=("telegram",))
    await agent.handle_event(_dm("telegram", "66", 1))
    store = agent._approvals()
    store.decide("decline", code=store.snapshot()["waiting"][0]["code"])
    reply = await agent.handle_event(_dm("telegram", "66", 2))
    check("no answer, no request, no model turn",
          reply["replies"] == [] and reply["owned"] and served == [] and not store.snapshot()["waiting"])


async def test_the_qq_webhook_asks_too(tmp: Path) -> None:
    agent, served = _agent(tmp, access_approval_platforms=("qq",))
    sent = []

    async def fake_onebot(target, message):
        sent.append((target, message))
        return True
    agent._onebot_send_group = agent._onebot_send_dm = fake_onebot
    await agent.handle_onebot({"post_type": "message", "message_type": "private", "user_id": "555",
                               "sender": {"user_id": "555", "nickname": "Bob"}, "message_id": 1,
                               "message": [{"type": "text", "data": {"text": "hi"}}]})
    waiting = agent._approvals().snapshot()["waiting"]
    check("a QQ DM waits and hears the code", waiting and waiting[0]["id"] == "555" and sent, repr(sent))
    check("no model turn", served == [])


async def test_no_unprompted_message_reaches_a_chat_that_waits(tmp: Path) -> None:
    """Someone who wrote before the platform started asking hears nothing unprompted."""
    import time

    from persona_agent.transport import SendResult

    agent, _ = _agent(tmp, access_approval_platforms=("telegram",))
    agent.proactive_dm_prob = 1.0
    quiet = time.time() - agent.proactive_dm_min_silence_s - 100
    for uid in ("telegram:1", "telegram:42"):
        agent.last_dm_activity_at[uid] = quiet
    agent._background_route = lambda key: {"platform": "telegram", "prefiltered": True}
    asked: list = []

    async def fake_chat_dm(history, is_admin=False, pkey="", proactive=False):
        asked.append(pkey)
        return "PASS", ""

    async def fake_send_dm(uid, text):
        return SendResult(success=True)
    agent._chat_dm = fake_chat_dm
    agent._send_dm = fake_send_dm
    await agent._maybe_proactive_dms()
    check("only the admin is considered, not the one who waits", asked == ["private:telegram:1"], repr(asked))


def test_the_typing_sign_is_not_raised_for_a_group_that_waits(tmp: Path) -> None:
    home = _home(tmp, "ACCESS_APPROVAL_PLATFORMS=telegram\nACCESS_GROUPS=telegram:-1\n")
    answered = admits(home)
    check("an approved group", answered({"platform": "telegram", "conversation_id": "-1"}))
    check("a group that waits", not answered({"platform": "telegram", "conversation_id": "-2"}))
    check("a platform that does not ask", answered({"platform": "discord", "conversation_id": "-2"}))


def test_every_language_has_both_fixed_lines() -> None:
    for code in chatlangs.CODES:
        replies = chatlangs.spec(code).replies
        check(f"{code}: the DM line names the code", "{code}" in replies["approval_dm"][0])
        check(f"{code}: the group line has no slot", "{" not in replies["approval_group"][0])


# ---------------------------------------------------------------- the page

@pytest.fixture
def workspace(tmp_path, monkeypatch):
    home = _home(tmp_path, "ACCESS_APPROVAL_PLATFORMS=telegram\n")
    (home / "platforms").mkdir()
    (home / "platforms" / "direct.json").write_text(json.dumps({"telegram": {"telegram_token": "x"}}),
                                                     encoding="utf-8")
    value = welcome.Workspace(home)
    monkeypatch.setattr(value.services, "running", lambda name: False)
    yield value
    value.close()


@pytest.fixture
def client(workspace):
    with TestClient(welcome.create_app(workspace.home, TOKEN, workspace=workspace),
                    base_url="http://127.0.0.1") as value:
        yield value


def test_the_page_lists_decides_and_switches(client, workspace) -> None:
    store = approvals.Store(approvals.store_path(workspace.home))
    code, _ = store.note(platform="telegram", kind="dm", chat_id="telegram:42", name="<b>Ann</b>",
                         words="<img src=x onerror=alert(1)>")
    assert client.get("/api/approvals").status_code == 403
    state = client.get("/api/state", headers=HEADERS).json()
    assert state["approvalsWaiting"] == {"telegram": 1}
    assert state["platformApproval"] == {"telegram": True}
    assert state["platformReach"]["telegram"] == "approval"
    body = client.get("/api/approvals", headers=HEADERS).json()
    item = body["waiting"][0]
    assert "code" not in item and item["hasAdmin"] is False and item["kind"] == "dm"
    assert item["id"] == "telegram:42" and code not in json.dumps(body), "the page never shows the code"
    assert item["name"] == "<b>Ann</b>", "kept as text: the page shows it with textContent"
    post = lambda path, payload: client.post(f"/api/approvals/{path}", headers=HEADERS, json=payload)
    assert post("decide", {"id": "telegram:42", "action": "nope"}).json() == {"error": "approvals_bad_request"}
    done = post("decide", {"id": "telegram:42", "action": "admin", "code": code}).json()
    assert done["waiting"] == [] and [a["id"] for a in done["approved"] if a["admin"]] == ["telegram:42"]
    assert post("decide", {"id": "telegram:42", "action": "approve"}).json() == {"error": "approvals_gone"}
    store.note(platform="telegram", kind="dm", chat_id="telegram:43")
    assert client.get("/api/approvals", headers=HEADERS).json()["waiting"][0]["hasAdmin"] is True
    declined = post("decide", {"id": "telegram:43", "action": "decline"}).json()
    assert [d["id"] for d in declined["declined"]] == ["telegram:43"]
    assert post("undo", {"id": "telegram:43"}).json()["declined"] == []
    assert post("undo", {"id": "telegram:43"}).json() == {"error": "approvals_gone"}
    assert post("undo", {"id": "telegram:42"}).json()["approved"] == []
    assert post("policy", {"platform": "telegram", "approve": False}).json()["policy"] == []
    state = client.get("/api/state", headers=HEADERS).json()
    assert state["platformApproval"] == {"telegram": False} and state["platformReach"]["telegram"] != "approval"
    assert post("policy", {"platform": "twitch", "approve": True}).json() == {"error": "approvals_bad_request"}
    assert post("policy", {"platform": "browser", "approve": True}).json() == {"error": "approvals_bad_request"}


def test_a_platform_connected_for_the_first_time_asks(tmp_path, monkeypatch) -> None:
    home = _home(tmp_path)
    space = welcome.Workspace(home)
    try:
        monkeypatch.setattr(space, "_connected", lambda kind: kind == "discord")
        monkeypatch.setattr(approvals, "used_before", lambda home, kind: False)
        for name in ("start_agent", "start_direct", "restart_direct", "start_astrbot", "stop"):
            monkeypatch.setattr(space.services, name, lambda *a, **k: None)
        monkeypatch.setattr(space, "_connect_direct", lambda spec, values: None)
        monkeypatch.setattr(space, "_await_direct", lambda spec: None)
        space.start_job("connect", "telegram", {"telegram_token": "1:x"})
        space._future.result(timeout=10)
        space.start_job("connect", "discord", {"discord_token": "x"})
        space._future.result(timeout=10)
    finally:
        space.close()
    check("a new platform asks; one reconnected keeps what it had",
          approvals.policy(_env(home)) == {"telegram"}, repr(_env(home)))


# ---------------------------------------------------------------- the terminal

def test_the_terminal_commands(tmp_path, monkeypatch, capsys) -> None:
    home = _home(tmp_path, "ACCESS_APPROVAL_PLATFORMS=telegram\n")
    monkeypatch.setenv("AGENT_HOME", str(home))
    store = approvals.Store(approvals.store_path(home))
    code, _ = store.note(platform="telegram", kind="dm", chat_id="telegram:42", name="Ann", words="hello")
    assert approvals.main(["list"]) == 0
    out = capsys.readouterr().out
    assert code in out and "Ann" in out and "hello" in out and "Telegram" in out
    assert approvals.main(["approve", "ZZZZZZ"]) == 1
    assert approvals.main(["approve", code]) == 0
    assert store.view()["dm"] == {"telegram:42"} and "ACCESS_DM_USERS" not in _env(home)
    second, _ = store.note(platform="telegram", kind="dm", chat_id="telegram:43")
    assert approvals.main(["decline", second]) == 0
    assert approvals.main(["undo", "telegram:43"]) == 0
    assert approvals.main(["policy", "discord", "approve"]) == 0
    assert approvals.policy(_env(home)) == {"telegram", "discord"}
    assert approvals.main(["policy", "nowhere", "approve"]) == 2
    capsys.readouterr()
    assert approvals.main(["list", "--json"]) == 0
    listed = json.loads(capsys.readouterr().out)
    assert listed["policy"] == ["discord", "telegram"] and listed["waiting"] == []
    assert [a["id"] for a in listed["approved"]] == ["telegram:42"]


def test_the_settings_page_takes_the_platform_list() -> None:
    from persona_agent.panels import tuning

    field = tuning.BY_KEY[access.APPROVAL_SETTING]
    check("read live: saving it restarts nothing", field.live)
    check("names are lowercased and deduplicated",
          tuning.clean(field, "Telegram, discord，telegram") == "telegram,discord")
    for bad in ("tele gram", "telegram:1", "${X}", "1abc"):
        with pytest.raises(ValueError):
            tuning.clean(field, bad)
