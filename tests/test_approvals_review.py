"""Approval of new chats: the cases a pre-release review found, one test each."""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path

from dotenv import dotenv_values
from fastapi.testclient import TestClient
import pytest

from persona_agent import approvals, welcome
from persona_agent import setup_wizard as sw
from persona_agent.direct import irc

from helpers import CLOSED_ONEBOT_URL, check, isolated_agent

TOKEN = "test-local-capability"
HEADERS = {welcome.TOKEN_HEADER: TOKEN}


def _home(tmp: Path, env: str = "") -> Path:
    home = tmp / "home"
    home.mkdir(parents=True, exist_ok=True)
    (home / ".env").write_text("LLM_API_KEY=sk-test\nPERSONA_NAME=Nova\n" + env, encoding="utf-8")
    return home


def _agent(tmp: Path, home: Path, **settings):
    agent = isolated_agent(tmp / "rt", qq_bot_id="10001", qq_onebot_url=CLOSED_ONEBOT_URL, **settings)
    agent._typing_delay = lambda chunk: 0.0
    agent.settings_env = approvals.LiveEnv(home / ".env")
    agent.approvals_file = approvals.store_path(home)
    served: list = []

    async def fake_think(group_id, mode, text="", caller_override=None):
        served.append((group_id, mode))
        return "on my way", "called", ""

    async def fake_chat_dm(history, is_admin=False, pkey="", proactive=False):
        served.append((pkey, "owner" if is_admin else "friend"))
        return "hi back", ""
    agent._think, agent._chat_dm = fake_think, fake_chat_dm
    return agent, served


def _dm(platform: str, uid: str, mid, **extra) -> dict:
    return {"platform": platform, "conversation_type": "dm", "conversation_id": uid, "sender_id": uid,
            "sender_name": "Someone", "bot_id": "999000", "message_id": mid, "addressed": False,
            "segments": [{"type": "text", "text": "hi"}], "text": "hi", **extra}


def _group(platform: str, gid: str, uid: str, mid) -> dict:
    return {"platform": platform, "conversation_type": "group", "conversation_id": gid, "sender_id": uid,
            "sender_name": "Someone", "bot_id": "999000", "message_id": mid, "addressed": True,
            "segments": [{"type": "mention", "user_id": "999000", "name": "TestBot"},
                         {"type": "text", "text": " hello"}], "text": "hello"}


def _waiting_code(home: Path, chat_id: str) -> str:
    return next(w["code"] for w in approvals.Store(approvals.store_path(home)).snapshot()["waiting"]
                if w["id"] == chat_id)


# 1 ---------------------------------------------------------------------------

async def test_an_approval_adds_to_lists_from_the_environment_and_survives_a_restart(tmp: Path) -> None:
    """ADMIN_IDS and ACCESS_DM_USERS given in the environment, not in .env."""
    home = _home(tmp, "ACCESS_APPROVAL_PLATFORMS=telegram\n")
    settings = dict(admin_ids=("telegram:1",), access_dm_users=("telegram:5",),
                    access_approval_platforms=("telegram",))
    agent, served = _agent(tmp, home, **settings)
    await agent.handle_event(_dm("telegram", "42", 1))
    await agent.handle_event(_dm("telegram", "43", 2))
    store = approvals.Store(approvals.store_path(home))
    store.decide("admin", code=_waiting_code(home, "telegram:42"))
    store.decide("approve", code=_waiting_code(home, "telegram:43"))
    check("the configured admin stays an admin", {"telegram:1", "telegram:42"} <= agent._admins(),
          repr(agent._admins()))
    await agent.handle_event(_dm("telegram", "1", 3))
    await agent.handle_event(_dm("telegram", "5", 4))
    await agent.handle_event(_dm("telegram", "43", 5))
    check("the configured admin and DM user, and the approved one, are answered",
          {("private:telegram:1", "owner"), ("private:telegram:5", "friend"),
           ("private:telegram:43", "friend")} <= set(served), repr(served))
    check(".env is not touched", "ADMIN_IDS" not in dotenv_values(home / ".env")
          and "ACCESS_DM_USERS" not in dotenv_values(home / ".env"))
    again, served_again = _agent(tmp / "after", home, **settings)
    await again.handle_event(_dm("telegram", "42", 6))
    check("after a restart the approval holds", ("private:telegram:42", "owner") in served_again,
          repr(served_again))


# 2 ---------------------------------------------------------------------------

def test_one_approvals_file_for_a_home_with_its_own_runtime_folder(tmp: Path, monkeypatch) -> None:
    home = _home(tmp, "AGENT_RUNTIME_DIR=state\n")
    monkeypatch.delenv("AGENT_RUNTIME_DIR", raising=False)
    check("the page and the terminal follow AGENT_RUNTIME_DIR in .env",
          approvals.store_path(home) == (home / "state" / "approvals.json").resolve(),
          str(approvals.store_path(home)))
    monkeypatch.setenv("AGENT_RUNTIME_DIR", "elsewhere")
    check("...and the environment first, as the service does",
          approvals.store_path(home) == (home / "elsewhere" / "approvals.json").resolve())
    monkeypatch.delenv("AGENT_RUNTIME_DIR")
    approvals.Store(approvals.store_path(home)).note(platform="telegram", kind="dm", chat_id="telegram:42")
    check("a request the service kept is counted where the page looks",
          approvals.waiting_counts(home) == {"telegram": 1})


# 3 ---------------------------------------------------------------------------

@pytest.fixture
def client(tmp_path, monkeypatch):
    home = _home(tmp_path, "ACCESS_APPROVAL_PLATFORMS=telegram\n")
    (home / "platforms").mkdir()
    (home / "platforms" / "direct.json").write_text(json.dumps({"telegram": {"telegram_token": "x"}}),
                                                     encoding="utf-8")
    space = welcome.Workspace(home)
    monkeypatch.setattr(space.services, "running", lambda name: False)
    with TestClient(welcome.create_app(home, TOKEN, workspace=space), base_url="http://127.0.0.1") as value:
        value.home = home
        yield value
    space.close()


def _post(client, path, payload):
    return client.post(f"/api/approvals/{path}", headers=HEADERS, json=payload).json()


def test_this_is_me_needs_the_code_the_owners_chat_received(client) -> None:
    store = approvals.Store(approvals.store_path(client.home))
    code, _ = store.note(platform="telegram", kind="dm", chat_id="telegram:42", name="Kant")
    shown = client.get("/api/approvals", headers=HEADERS).json()
    row = shown["waiting"][0]
    check("the page shows the id beside a chosen name, and never the code",
          row["id"] == "telegram:42" and row["name"] == "Kant" and code not in json.dumps(shown))
    check("without the code: refused",
          _post(client, "decide", {"id": "telegram:42", "action": "admin"}) == {"error": "approvals_code_mismatch"})
    wrong = "ACDEFG" if code != "ACDEFG" else "HJKMNP"
    check("with another code: refused",
          _post(client, "decide", {"id": "telegram:42", "action": "admin", "code": wrong})
          == {"error": "approvals_code_mismatch"})
    check("still waiting", store.snapshot()["waiting"] and not store.view()["admins"])
    done = _post(client, "decide", {"id": "telegram:42", "action": "admin", "code": code.lower()})
    check("with the code: an admin", [a["id"] for a in done["approved"] if a["admin"]] == ["telegram:42"])


# 4 ---------------------------------------------------------------------------

def test_an_irc_sender_the_network_did_not_vouch_for_is_never_an_admin(tmp: Path) -> None:
    bot = irc.IRC({"irc_server": "irc.libera.chat", "irc_port": 6697, "irc_nick": "Nova", "irc_channels": "#room"})
    bot.nick, bot.bot_id = "Nova", "nova"
    check("no account tags: the nick is marked", bot.event("Kant!~k@h", "Nova", "hi")["sender_id"] == "~kant")
    bot.accounts = True
    check("an account the network reports is the id", bot.sender_id("Kant", "kantacct") == "kantacct")
    check("no account: marked", bot.sender_id("Kant", None) == "~kant")
    store = approvals.Store(tmp / "approvals.json")
    store.note(platform="irc", kind="dm", chat_id="irc:~kant")
    with pytest.raises(approvals.Refused, match="approvals_unverified"):
        store.decide("admin", code=store.snapshot()["waiting"][0]["code"])
    check("approving is still possible", store.decide("approve", chat_id="irc:~kant")["id"] == "irc:~kant")
    check("an identified account is not marked", not approvals.unverified("irc:kantacct"))


# 5 ---------------------------------------------------------------------------

def test_a_flood_cannot_keep_the_owner_from_getting_a_code(tmp: Path) -> None:
    store = approvals.Store(tmp / "approvals.json")
    groups = sum(store.note(platform="discord", kind="group", chat_id=f"discord:g{n}")[1] for n in range(50))
    check("groups have their own, smaller bound", groups == approvals.MAX_WAITING["group"], str(groups))
    dms = sum(store.note(platform="discord", kind="dm", chat_id=f"discord:{n}", has_admin=False)[1]
              for n in range(approvals.MAX_WAITING["dm"]))
    check("groups did not take the places of direct messages", dms == approvals.MAX_WAITING["dm"])
    code, tell = store.note(platform="discord", kind="dm", chat_id="discord:owner", has_admin=False)
    check("with no admin yet, a direct message still gets a code", code and tell)
    kinds = [w["kind"] for w in store.snapshot()["waiting"]]
    check("the oldest direct message made room",
          kinds.count("dm") == approvals.MAX_WAITING["dm"] and "discord:0" not in
          {w["id"] for w in store.snapshot()["waiting"]})
    check("once there is an admin, a full list takes no more",
          store.note(platform="discord", kind="dm", chat_id="discord:late", has_admin=True) == ("", False))
    told = sum(store.note(platform="discord", kind="dm", chat_id=f"discord:x{n}", has_admin=False)[1]
               for n in range(100))
    check("evicting answers a bounded number an hour", told <= approvals.FULL_TELLS_PER_HOUR, str(told))


def test_the_page_says_when_the_list_is_full(client) -> None:
    store = approvals.Store(approvals.store_path(client.home))
    for n in range(approvals.MAX_WAITING["group"]):
        store.note(platform="telegram", kind="group", chat_id=f"telegram:-{n}")
    check("full is named", client.get("/api/approvals", headers=HEADERS).json()["full"] == ["telegram:group"])


# 6 ---------------------------------------------------------------------------

async def test_open_means_open_and_a_decline_holds_whatever_the_policy(tmp: Path) -> None:
    home = _home(tmp, "ACCESS_APPROVAL_PLATFORMS=telegram\n")
    agent, served = _agent(tmp, home, access_approval_platforms=("telegram",))
    for uid, mid in (("42", 1), ("66", 2)):
        await agent.handle_event(_dm("telegram", uid, mid))
    store = approvals.Store(approvals.store_path(home))
    store.decide("approve", chat_id="telegram:42")
    store.decide("decline", chat_id="telegram:66")
    approvals.set_policy(home, "telegram", False)
    stranger = await agent.handle_event(_dm("telegram", "43", 3))
    check("open: a new stranger is answered", stranger["owned"]
          and ("private:telegram:43", "friend") in served, repr((stranger, served)))
    declined = await agent.handle_event(_dm("telegram", "66", 4))
    check("open: the declined chat is still not answered, and claimed",
          declined["owned"] and declined["replies"] == [] and not any("66" in k for k, _ in served))
    await agent.handle_event(_dm("telegram", "42", 5))
    check("open: the approved chat is answered", ("private:telegram:42", "friend") in served)


# 7 ---------------------------------------------------------------------------

def test_reconnecting_keeps_the_owners_choice(tmp: Path) -> None:
    home = _home(tmp)
    check("a platform never seen asks", approvals.adopt(home, "telegram"))
    approvals.set_policy(home, "telegram", False)
    check("the owner chose open: connecting again keeps it",
          not approvals.adopt(home, "telegram") and "telegram" not in approvals.current_policy(home))
    runtime = approvals.runtime_of(home)
    runtime.mkdir(parents=True, exist_ok=True)
    (runtime / "connector_handles.json").write_text(json.dumps({"private:discord:9": {}}), encoding="utf-8")
    check("a platform with history is decided open", not approvals.adopt(home, "discord")
          and approvals.Store(approvals.store_path(home)).decided("discord") == "open")
    check("one connected before is decided open", not approvals.adopt(home, "vk", connected=True))
    sw.write_env(home / ".env", {"ACCESS_GROUPS": "matrix:!r"})
    check("one with entries is decided open", not approvals.adopt(home, "matrix"))


def test_setting_up_a_platform_again_on_the_page_does_not_switch_approval_on(tmp_path, monkeypatch) -> None:
    home = _home(tmp_path)
    space = welcome.Workspace(home)
    try:
        monkeypatch.setattr(space, "_connected", lambda kind: True)
        for name in ("start_agent", "start_direct", "restart_direct", "start_astrbot", "stop"):
            monkeypatch.setattr(space.services, name, lambda *a, **k: None)
        monkeypatch.setattr(space, "_connect_direct", lambda spec, values: None)
        monkeypatch.setattr(space, "_await_direct", lambda spec: None)
        space.start_job("connect", "telegram", {"telegram_token": "1:x"})
        space._future.result(timeout=10)
    finally:
        space.close()
    check("still open", approvals.policy(dict(dotenv_values(home / ".env"))) == frozenset())


# 8 ---------------------------------------------------------------------------

async def test_a_held_chat_leaves_no_route_behind(tmp: Path) -> None:
    home = _home(tmp, "ACCESS_APPROVAL_PLATFORMS=telegram\n")
    agent, _ = _agent(tmp, home, access_approval_platforms=("telegram",))
    held = await agent.handle_event(_dm("telegram", "42", 1, connector_id="c1", reply_handle="h1",
                                        capabilities=["outbox"]))
    check("claimed", held["owned"])
    check("no handle kept for it", "private:telegram:42" not in agent.connector_handles._data())
    agent.access_dm_users = {"telegram:5"}
    await agent.handle_event(_dm("telegram", "5", 2, connector_id="c1", reply_handle="h5",
                                 capabilities=["outbox"]))
    check("an admitted chat still keeps its handle", "private:telegram:5" in agent.connector_handles._data())


# 9 ---------------------------------------------------------------------------

async def test_a_zulip_group_dm_can_be_approved(tmp: Path) -> None:
    home = _home(tmp, "ACCESS_APPROVAL_PLATFORMS=zulip\n")
    agent, served = _agent(tmp, home, access_approval_platforms=("zulip",))
    await agent.handle_event(_group("zulip", "1,2,3", "1", 1))
    store = approvals.Store(approvals.store_path(home))
    check("it waits", [w["id"] for w in store.snapshot()["waiting"]] == ["zulip:1,2,3"])
    store.decide("approve", chat_id="zulip:1,2,3")
    await agent.handle_event(_group("zulip", "1,2,3", "2", 2))
    check("approved: answered", ("zulip:1,2,3", "called") in served, repr(served))


# 10 --------------------------------------------------------------------------

def test_a_file_that_cannot_be_read_is_not_saved_over(tmp: Path, monkeypatch) -> None:
    store = approvals.Store(tmp / "approvals.json")
    store.note(platform="telegram", kind="dm", chat_id="telegram:1")
    store.decide("decline", chat_id="telegram:1")
    before = store.path.read_bytes()
    real = Path.read_bytes

    def busy(self):
        if self.name == "approvals.json":
            raise PermissionError(13, "in use")
        return real(self)
    monkeypatch.setattr(Path, "read_bytes", busy)
    with pytest.raises(PermissionError):
        store.note(platform="telegram", kind="dm", chat_id="telegram:2")
    monkeypatch.setattr(Path, "read_bytes", real)
    check("the declined list is intact", store.path.read_bytes() == before)
    store.path.write_text("{broken", encoding="utf-8")
    check("a damaged file starts empty", store.snapshot()["declined"] == [])
    check("...and is kept beside it", store.path.with_name("approvals.json.damaged").read_text(encoding="utf-8")
          == "{broken")


def test_writers_of_the_env_file_do_not_lose_each_others_values(tmp: Path, monkeypatch) -> None:
    env = tmp / ".env"
    env.write_text("A=1\n", encoding="utf-8")
    real = sw.set_env_values

    def slow(text, values):
        time.sleep(0.05)
        return real(text, values)
    monkeypatch.setattr(sw, "set_env_values", slow)
    errors: list = []

    def write(n: int) -> None:
        try:
            sw.write_env(env, {f"K{n}": str(n)})
        except Exception as exc:
            errors.append(exc)
    threads = [threading.Thread(target=write, args=(n,)) for n in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    values = dotenv_values(env)
    check("no writer failed", not errors, repr(errors))
    check("every value is there", all(values.get(f"K{n}") == str(n) for n in range(6)) and values["A"] == "1",
          repr(values))
    check("no temporary file is left", [p.name for p in tmp.iterdir() if p.suffix == ".tmp"] == [])


# 11 --------------------------------------------------------------------------

def test_a_line_deleted_from_the_env_file_reads_as_empty(tmp: Path) -> None:
    home = _home(tmp, "ACCESS_APPROVAL_PLATFORMS=telegram\n")
    live = approvals.LiveEnv(home / ".env")
    check("unchanged: the startup value", live.get("ACCESS_APPROVAL_PLATFORMS") is None)
    (home / ".env").write_text("LLM_API_KEY=sk-test\n", encoding="utf-8")
    check("deleted: empty", live.get("ACCESS_APPROVAL_PLATFORMS") == "")
    check("a key never there: the startup value", live.get("ADMIN_IDS") is None)


def test_a_policy_set_in_the_environment_is_not_changed_behind_its_back(tmp: Path, monkeypatch, client) -> None:
    home = _home(tmp)
    monkeypatch.setenv("ACCESS_APPROVAL_PLATFORMS", "telegram")
    check("the page and the terminal read it", approvals.current_policy(home) == {"telegram"})
    with pytest.raises(approvals.PolicyLocked):
        approvals.set_policy(home, "telegram", False)
    check("the page says why", _post(client, "policy", {"platform": "telegram", "approve": False})
          == {"error": "approvals_env_locked"})
    check(".env is not written", "ACCESS_APPROVAL_PLATFORMS" not in dotenv_values(home / ".env"))
