"""The page's chat: pictures the character sends, and messages it sends later."""
from __future__ import annotations

import asyncio
import base64
import hashlib
import os
import time

from fastapi.testclient import TestClient
import httpx
import pytest

from persona_agent import setup_wizard as sw
from persona_agent import welcome
from persona_agent.outbox import HandleStore, Outbox

TOKEN = "test-local-capability"
HEADERS = {welcome.TOKEN_HEADER: TOKEN}
# The smallest PNG: one transparent pixel.
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==")


@pytest.fixture
def workspace(tmp_path):
    value = welcome.Workspace(tmp_path)
    sw.write_env(value.env, {"LLM_API_KEY": "key", "CONNECTOR_TOKEN": "token"})
    yield value
    value.close()


@pytest.fixture
def client(workspace):
    with TestClient(welcome.create_app(workspace.home, TOKEN, workspace=workspace),
                    base_url="http://127.0.0.1") as value:
        yield value


def _replying(monkeypatch, workspace, replies, events=None):
    monkeypatch.setattr(workspace.services, "start_agent", lambda: None)

    class Connector:
        def __init__(self, *args, **kwargs):
            pass

        async def send_event(self, event):
            if events is not None:
                events.append(event)
            return {"replies": replies}

    monkeypatch.setattr(welcome, "_connector_type", lambda: Connector)


def test_a_picture_reply_is_kept_shown_and_served_only_to_the_page(client, workspace, monkeypatch):
    _replying(monkeypatch, workspace, [{"type": "text", "text": "look"},
                                       {"type": "image", "b64": base64.b64encode(PNG).decode()}])
    answer = client.post("/api/chat", headers=HEADERS, json={"text": "hi"}).json()
    picture = answer["messages"][-1]["picture"]
    assert [m.get("text") for m in answer["messages"][:2]] == ["hi", "look"]
    assert welcome.PICTURE_NAME.fullmatch(picture)
    served = client.get(f"/api/chat/picture/{picture}", headers=HEADERS)
    assert served.status_code == 200 and served.content == PNG
    assert served.headers["content-type"] == "image/png"
    assert client.get(f"/api/chat/picture/{picture}").status_code == 403
    # Still there for a page opened again.
    again = welcome.Workspace(workspace.home)
    try:
        assert again.history()["messages"][-1]["picture"] == picture
    finally:
        again.close()


def test_the_picture_route_reads_nothing_but_stored_pictures(client, workspace, tmp_path):
    (workspace.home / ".env").write_text("LLM_API_KEY=secret\n", encoding="utf-8")
    name = workspace._keep_picture(base64.b64encode(PNG).decode())
    for bad in ("..%2F..%2F.env", "..%5C..%5C.env", "%2Fetc%2Fpasswd", "C%3A%5CWindows%5Cwin.ini",
                ".env", name.upper(), name + ".png", name[:-4] + ".txt", "..", "%2E%2E"):
        response = client.get(f"/api/chat/picture/{bad}", headers=HEADERS)
        # A bare ".." is folded by the client into another route, which refuses a GET.
        assert response.status_code in (404, 405), bad
        assert b"secret" not in response.content
    assert workspace.picture("../../.env") is None and workspace.picture(str(workspace.env)) is None


def test_a_linked_picture_is_refused(client, workspace, tmp_path):
    outside = tmp_path / "outside.png"
    outside.write_bytes(PNG)
    link = workspace._pictures / ("a" * 40 + ".png")
    workspace._pictures.mkdir(parents=True, exist_ok=True)
    workspace._append([{"role": "assistant", "picture": link.name}])
    try:
        os.symlink(outside, link)
    except (OSError, NotImplementedError):
        pytest.skip("this system does not let the test create a symbolic link")
    assert client.get(f"/api/chat/picture/{link.name}", headers=HEADERS).status_code == 404


def test_a_pictures_folder_that_leads_elsewhere_is_refused(client, workspace, tmp_path):
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    name = "b" * 40 + ".png"
    (elsewhere / name).write_bytes(PNG)
    workspace._pictures.parent.mkdir(parents=True, exist_ok=True)
    workspace._append([{"role": "assistant", "picture": name}])
    try:
        if os.name == "nt":
            import _winapi
            _winapi.CreateJunction(str(elsewhere), str(workspace._pictures))
        else:
            os.symlink(elsewhere, workspace._pictures, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("this system does not let the test link a folder")
    assert client.get(f"/api/chat/picture/{name}", headers=HEADERS).status_code == 404
    # Nor is anything stored there or removed from there.
    assert workspace._keep_picture(base64.b64encode(PNG).decode()) == ""
    workspace.reset_chat()
    assert (elsewhere / name).is_file()


def test_a_picture_no_message_shows_is_not_served(client, workspace):
    name = workspace._keep_picture(base64.b64encode(PNG).decode())
    assert (workspace._pictures / name).is_file()
    assert client.get(f"/api/chat/picture/{name}", headers=HEADERS).status_code == 404
    workspace._append([{"role": "assistant", "picture": name}])
    assert client.get(f"/api/chat/picture/{name}", headers=HEADERS).status_code == 200


def test_a_link_in_the_pictures_folder_is_never_written_through(workspace, tmp_path):
    outside = tmp_path / "outside.png"
    workspace._pictures.mkdir(parents=True, exist_ok=True)
    link = workspace._pictures / f"{hashlib.sha256(PNG).hexdigest()[:40]}.png"
    try:
        os.symlink(outside, link)
    except (OSError, NotImplementedError):
        pytest.skip("this system does not let the test create a symbolic link")
    assert workspace._keep_picture(base64.b64encode(PNG).decode()) == ""
    assert not outside.exists()


def test_a_removed_picture_is_missing_and_what_is_not_a_picture_is_not_kept(client, workspace):
    name = workspace._keep_picture(base64.b64encode(PNG).decode())
    workspace._append([{"role": "assistant", "picture": name}])
    (workspace._pictures / name).unlink()
    assert client.get(f"/api/chat/picture/{name}", headers=HEADERS).status_code == 404
    assert workspace._keep_picture(base64.b64encode(b"<svg onload=x>").decode()) == ""
    assert workspace._keep_picture("not base64!") == ""


def test_pictures_leave_with_the_messages_that_showed_them(monkeypatch, workspace):
    _replying(monkeypatch, workspace, [{"type": "image", "b64": base64.b64encode(PNG).decode()}])
    asyncio.run(workspace.chat("hi"))
    assert list(workspace._pictures.iterdir())
    workspace.reset_chat()
    assert not list(workspace._pictures.iterdir())


def test_a_failed_reply_leaves_no_message_behind(monkeypatch, workspace):
    monkeypatch.setattr(workspace.services, "start_agent", lambda: None)

    class Connector:
        def __init__(self, *args, **kwargs):
            pass

        async def send_event(self, event):
            raise ConnectionError("down")

    monkeypatch.setattr(welcome, "_connector_type", lambda: Connector)
    with pytest.raises(ConnectionError):
        asyncio.run(workspace.chat("hi"))
    assert workspace.history()["messages"] == []
    assert welcome.Workspace(workspace.home).history()["messages"] == []


def test_the_service_can_reach_the_page_chat_after_a_message(monkeypatch, workspace, tmp_path):
    """What the service records from the page's message gives it a way back, once the page pulls."""
    from persona_agent.connector import event_connector

    events = []
    _replying(monkeypatch, workspace, [{"type": "text", "text": "ok"}], events)
    asyncio.run(workspace.chat("hi"))
    outbox = Outbox(HandleStore(tmp_path / "handles.json"))
    connector = event_connector({**events[0], "connector_id": welcome.PAGE_CONNECTOR})
    outbox.handles.record(workspace._page_key(), **connector, platform="browser", native=False,
                          conversation_type="dm", conversation_id=workspace._conversation)
    assert outbox.route(workspace._page_key()) is None   # nobody pulls for it yet
    outbox._stamp(welcome.PAGE_CONNECTOR)
    assert outbox.route(workspace._page_key())["connector_id"] == welcome.PAGE_CONNECTOR


def test_the_coding_assistants_send_as_before(monkeypatch, workspace):
    events = []
    _replying(monkeypatch, workspace, [{"type": "text", "text": "a"}, {"type": "image", "b64": "x"},
                                       {"type": "text", "text": "b"}], events)
    text = asyncio.run(welcome.send_chat_event("http://127.0.0.1:1", "t", "conv", "hi",
                                               connector_id="coding-agent", timeout_s=5))
    assert text == "a\nb" and "capabilities" not in events[0]


def test_a_later_message_reaches_the_page_and_its_history_in_order(monkeypatch, workspace):
    _replying(monkeypatch, workspace, [{"type": "text", "text": "first"}])
    asyncio.run(workspace.chat("hi"))
    seen = workspace.history()["last"]
    status = workspace.take_delivery({"conversation_key": workspace._page_key(), "reason": "follow_up",
                                      "items": [{"type": "text", "text": "noted"},
                                                {"type": "image", "b64": base64.b64encode(PNG).decode()}]})
    assert status == ("sent", 2)
    later = workspace.history(seen)["messages"]
    assert [m.get("text") for m in later] == ["noted", None] and later[1]["picture"]
    assert [m["seq"] for m in later] == [seen + 1, seen + 2]
    again = welcome.Workspace(workspace.home)
    try:
        assert [m.get("text") for m in again.history()["messages"]] == ["hi", "first", "noted", None]
    finally:
        again.close()
    # A chat that was replaced gets nothing more, and the service stops trying.
    old = workspace._page_key()
    workspace.reset_chat()
    assert workspace.take_delivery({"conversation_key": old, "items": [{"type": "text", "text": "x"}]}) \
        == ("unsupported", 0)
    assert workspace.history()["messages"] == []


def test_the_page_pulls_only_its_own_deliveries_and_a_connector_keeps_its_own(monkeypatch, workspace, tmp_path):
    """The real outbox, the page's pull loop, and a platform connector's
    delivery queued beside the page's."""
    async def scenario():
        outbox = Outbox(HandleStore(tmp_path / "handles.json"))
        page_key = workspace._page_key()
        page = {"reply_handle": "", "connector_id": welcome.PAGE_CONNECTOR, "capabilities": ["outbox"],
                "platform": "browser", "native": False, "conversation_type": "dm",
                "conversation_id": workspace._conversation}
        other = {**page, "connector_id": "telegram-bot", "platform": "telegram", "conversation_id": "42"}
        outbox._stamp("telegram-bot")
        pulls = []

        class Connector(welcome._connector_type()):
            async def pull_once(self, *, wait_s=25, max_deliveries=10):
                acks, self._pending_acks = self._pending_acks, []
                pulls.append(self.connector_id)
                return await outbox.pull(self.connector_id, wait_s=min(wait_s, 0.5), acks=acks)

        monkeypatch.setattr(welcome, "_connector_type", lambda: Connector)
        monkeypatch.setattr(workspace.services, "running", lambda name: name == "agent")
        loop = asyncio.create_task(workspace.outbox_loop())
        for _ in range(100):
            if outbox.live(welcome.PAGE_CONNECTOR):
                break
            await asyncio.sleep(0.02)
        theirs = asyncio.create_task(outbox.deliver("telegram:42", other,
                                                    [{"type": "text", "text": "for telegram"}],
                                                    reason="proactive"))
        ours = await asyncio.wait_for(outbox.deliver(page_key, page, [{"type": "text", "text": "for the page"}],
                                                     reason="follow_up"), 10)
        assert ours.status == "sent"
        assert [m["text"] for m in workspace.history()["messages"]] == ["for the page"]
        assert not theirs.done() and outbox._queues["telegram:42"][0].items[0]["text"] == "for telegram"
        assert set(pulls) == {welcome.PAGE_CONNECTOR}
        workspace._closed = True
        loop.cancel()
        theirs.cancel()
        await outbox.aclose()

    asyncio.run(scenario())


def test_after_a_coding_assistant_speaks_the_character_still_reaches_the_page(monkeypatch, workspace, tmp_path):
    """A real agent and outbox: the page speaks, a coding assistant speaks in
    the same chat, then the character speaks first and the page shows it."""
    from helpers import CLOSED_ONEBOT_URL, isolated_agent

    async def scenario():
        agent = isolated_agent(tmp_path / "agent", qq_onebot_url=CLOSED_ONEBOT_URL)
        agent._typing_delay = lambda chunk: 0.0
        said = []

        async def chat_dm(history, is_admin=False, pkey="", proactive=False, proactive_cue=""):
            said.append(proactive)
            return ("good evening" if proactive else "hi back"), ""

        agent._chat_dm = chat_dm
        agent.proactive_dm_min_silence_s = 0
        agent.proactive_dm_cooldown_s = 0
        agent.proactive_dm_prob = 1.0

        class Connector(welcome._connector_type()):
            async def send_event(self, event):
                return await agent.handle_event({**event, "connector_id": event.get(
                    "connector_id", self.connector_id)})

            async def pull_once(self, *, wait_s=25, max_deliveries=10):
                acks, self._pending_acks = self._pending_acks, []
                return await agent.outbox.pull(self.connector_id, wait_s=min(wait_s, 0.3), acks=acks)

        monkeypatch.setattr(welcome, "_connector_type", lambda: Connector)
        monkeypatch.setattr(workspace.services, "start_agent", lambda: None)
        monkeypatch.setattr(workspace.services, "running", lambda name: name == "agent")
        key = workspace._page_key()
        loop = asyncio.create_task(workspace.outbox_loop())
        try:
            page = await workspace.chat("hello")
            assert page["reply"] == "hi back"
            coding = await welcome.send_chat_items(
                workspace.services.agent_url, "token", workspace._conversation, "from the terminal",
                connector_id="coding-agent", timeout_s=5)
            # What the coding assistant gets back is unchanged.
            assert [i.get("text") for i in coding if i.get("type") == "text"] == ["hi back"]
            assert agent.connector_handles.get(key)["connector_id"] == welcome.PAGE_CONNECTOR
            for _ in range(100):
                if agent.outbox.live(welcome.PAGE_CONNECTOR):
                    break
                await asyncio.sleep(0.02)
            agent.last_dm_activity_at[f"{welcome.access.PAGE_PLATFORM}:{workspace._conversation}"] = time.time() - 1
            assert await asyncio.wait_for(agent._maybe_proactive_dms(), 10) is True
            assert said[-1] is True
            texts = [m.get("text") for m in workspace.history()["messages"]]
            assert texts[-1] == "good evening" and texts.count("good evening") == 1
        finally:
            workspace._closed = True
            loop.cancel()
            await agent.outbox.aclose()

    asyncio.run(scenario())


def test_a_delivery_during_forgetting_is_not_counted_as_shown(monkeypatch, workspace):
    """What arrives while the chat is forgotten would vanish with it, so it is not acknowledged as sent."""
    async def scenario():
        monkeypatch.setattr(workspace.services, "start_agent", lambda: None)
        asked, release = asyncio.Event(), asyncio.Event()

        async def activity_call(method, path, **kwargs):
            asked.set()
            await release.wait()
            return {"ok": True, "forgotten": 0}

        monkeypatch.setattr(workspace, "_activity_call", activity_call)
        old = workspace._page_key()
        forgetting = asyncio.create_task(workspace.forget_chat())
        await asyncio.wait_for(asked.wait(), 5)
        status = workspace.take_delivery({"conversation_key": old, "items": [{"type": "text", "text": "late"}]})
        release.set()
        await forgetting
        assert status == ("failed", 0)
        assert workspace.history()["messages"] == [] and workspace._page_key() != old
        # Afterwards the new chat takes deliveries again.
        assert workspace.take_delivery({"conversation_key": workspace._page_key(),
                                        "items": [{"type": "text", "text": "next"}]}) == ("sent", 1)

    asyncio.run(scenario())


def test_one_page_runs_one_pull_loop(monkeypatch, workspace):
    async def scenario():
        monkeypatch.setattr(workspace.services, "running", lambda name: False)
        first = asyncio.create_task(workspace.outbox_loop())
        await asyncio.sleep(0.05)
        await asyncio.wait_for(workspace.outbox_loop(), 1)
        assert not first.done()
        workspace._closed = True
        first.cancel()

    asyncio.run(scenario())


def test_a_restarted_service_is_pulled_at_once_after_its_outbox_was_off(monkeypatch, workspace):
    """A 404 pauses the pulls for a minute, but a service started since may have the outbox on."""
    async def scenario():
        monkeypatch.setattr(welcome, "OUTBOX_IDLE_S", 0.05)
        monkeypatch.setattr(workspace.services, "running", lambda name: name == "agent")
        workspace.services.processes["agent"] = object()
        pulls = []

        class Connector(welcome._connector_type()):
            async def pull_once(self, *, wait_s=25, max_deliveries=10):
                pulls.append(time.monotonic())
                if len(pulls) == 1:
                    request = httpx.Request("POST", "http://127.0.0.1/v1/outbox")
                    raise httpx.HTTPStatusError("off", request=request,
                                                response=httpx.Response(404, request=request))
                await asyncio.sleep(0.2)
                return {"deliveries": []}

        monkeypatch.setattr(welcome, "_connector_type", lambda: Connector)
        loop = asyncio.create_task(workspace.outbox_loop())
        try:
            await asyncio.sleep(0.5)
            assert len(pulls) == 1    # switched off: no pull for now
            workspace.services.processes["agent"] = object()    # restarted, settings read again
            for _ in range(100):
                if len(pulls) > 1:
                    break
                await asyncio.sleep(0.02)
            assert len(pulls) > 1
        finally:
            workspace._closed = True
            loop.cancel()
            workspace.services.processes.pop("agent", None)

    asyncio.run(scenario())


def test_history_since_a_number_and_older_files_without_numbers(client, workspace):
    workspace._history_path.parent.mkdir(parents=True, exist_ok=True)
    workspace._history_path.write_text(
        '{"conversation": "c1", "messages": [{"role": "user", "text": "a"}, {"role": "assistant", "text": "b"}]}',
        encoding="utf-8")
    older = welcome.Workspace(workspace.home)
    try:
        assert [m["seq"] for m in older.history()["messages"]] == [1, 2]
        assert older.history(1)["messages"] == [{"role": "assistant", "text": "b", "seq": 2}]
    finally:
        older.close()
    assert client.get("/api/chat/history?after=0", headers=HEADERS).json()["messages"] == []
    assert client.get("/api/chat/history?after=x", headers=HEADERS).status_code == 422
    assert workspace.history()["kept"] == welcome.CHAT_KEPT


def test_the_pull_loop_outlives_settings_it_cannot_read(monkeypatch, workspace):
    """A bad SERVER_PORT, say, while the page runs: the loop waits and pulls once it is fixed."""
    async def scenario():
        monkeypatch.setattr(welcome, "OUTBOX_IDLE_S", 0.02)
        monkeypatch.setattr(workspace.services, "running", lambda name: name == "agent")
        sw.write_env(workspace.env, {"LLM_API_KEY": "key", "CONNECTOR_TOKEN": "token", "SERVER_PORT": "80 80"})
        pulls = []

        class Connector(welcome._connector_type()):
            async def pull_once(self, *, wait_s=25, max_deliveries=10):
                pulls.append(wait_s)
                await asyncio.sleep(0.05)
                return {"deliveries": []}

        monkeypatch.setattr(welcome, "_connector_type", lambda: Connector)
        loop = asyncio.create_task(workspace.outbox_loop())
        try:
            await asyncio.sleep(0.2)
            assert not loop.done() and pulls == []
            sw.write_env(workspace.env, {"LLM_API_KEY": "key", "CONNECTOR_TOKEN": "token", "SERVER_PORT": "8080"})
            for _ in range(100):
                if pulls:
                    break
                await asyncio.sleep(0.02)
            assert pulls and not loop.done()
        finally:
            workspace._closed = True
            loop.cancel()

    asyncio.run(scenario())


def test_only_what_the_page_can_show_is_acknowledged_as_sent(workspace):
    key = workspace._page_key()
    picture = {"type": "image", "b64": base64.b64encode(PNG).decode()}
    broken = {"type": "image", "b64": base64.b64encode(b"not a picture").decode()}
    assert workspace.take_delivery({"conversation_key": key, "items": [broken]}) == ("failed", 0)
    assert workspace.take_delivery({"conversation_key": key, "items": [{"type": "voice"}]}) == ("failed", 0)
    assert workspace.history()["messages"] == []
    status = workspace.take_delivery({"conversation_key": key, "items": [
        {"type": "text", "text": "look"}, picture, {"type": "video"}, {"type": "text", "text": "after"}]})
    assert status == ("partial", 2)
    shown = workspace.history()["messages"]
    assert [m.get("text") for m in shown] == ["look", None] and shown[1]["picture"]
    assert all(m.get("picture") != "" for m in shown)


def test_a_reply_that_cannot_be_shown_leaves_no_empty_picture(monkeypatch, workspace):
    _replying(monkeypatch, workspace, [{"type": "text", "text": "here"}, {"type": "image", "b64": "x"}])
    asyncio.run(workspace.chat("hi"))
    assert [m.get("text") for m in workspace.history()["messages"]] == ["hi", "here"]


def _page_agent(tmp_path, fail):
    from helpers import CLOSED_ONEBOT_URL, isolated_agent

    agent = isolated_agent(tmp_path / "agent", qq_onebot_url=CLOSED_ONEBOT_URL)
    agent._typing_delay = lambda chunk: 0.0

    async def chat_dm(history, is_admin=False, pkey="", proactive=False, proactive_cue=""):
        if fail:
            raise TimeoutError("model down")
        return "hi back", ""

    agent._chat_dm = chat_dm
    return agent


def _through(monkeypatch, workspace, agent):
    class Connector(welcome._connector_type()):
        async def send_event(self, event):
            return await agent.handle_event({**event, "connector_id": self.connector_id})

    monkeypatch.setattr(welcome, "_connector_type", lambda: Connector)
    monkeypatch.setattr(workspace.services, "start_agent", lambda: None)


def test_a_model_failure_is_reported_in_the_page_and_never_stored(monkeypatch, workspace, tmp_path):
    """Every failure, not once per cooldown, and the casual excuse never becomes a message."""
    fail = [True]
    agent = _page_agent(tmp_path, True)

    async def chat_dm(history, is_admin=False, pkey="", proactive=False, proactive_cue=""):
        if fail[0]:
            raise TimeoutError("model down")
        return "hi back", ""

    agent._chat_dm = chat_dm
    _through(monkeypatch, workspace, agent)
    with TestClient(welcome.create_app(workspace.home, TOKEN, workspace=workspace),
                    base_url="http://127.0.0.1") as client:
        for _ in range(2):
            answer = client.post("/api/chat", headers=HEADERS, json={"text": "hi"})
            assert answer.status_code == 502 and answer.json() == {"error": "chat_failed"}
            assert workspace.history()["messages"] == []
        fail[0] = False
        answer = client.post("/api/chat", headers=HEADERS, json={"text": "hi"}).json()
    assert answer["reply"] == "hi back"
    assert [m["text"] for m in workspace.history()["messages"]] == ["hi", "hi back"]


def test_a_chat_platform_keeps_its_marked_excuse(tmp_path):
    agent = _page_agent(tmp_path, True)
    event = {"platform": "telegram", "conversation_type": "dm", "sender_id": "7", "sender_name": "Kay",
             "bot_id": "999000", "message_id": "m1", "sent_at": int(time.time()), "text": "hi",
             "segments": [{"type": "text", "text": "hi"}]}
    replies = asyncio.run(agent.handle_event(event))["replies"]
    assert len(replies) == 1 and replies[0]["text"] and replies[0]["reason"] == "excuse"


def test_the_page_chat_shows_in_activity_once_with_what_was_said(monkeypatch, workspace, tmp_path):
    from persona_agent import dashboard, decision_log

    agent = _page_agent(tmp_path, False)
    _through(monkeypatch, workspace, agent)
    runtime = workspace._runtime()
    monkeypatch.setattr(dashboard, "runtime_dir", lambda: runtime)
    decision_log.LOG.clear()
    try:
        asyncio.run(workspace.chat("first chat"))
        workspace.reset_chat()
        asyncio.run(workspace.chat("hello there"))
        page = [c for c in dashboard.conversations_payload(agent)["conversations"]
                if c["platform"] == welcome.access.PAGE_PLATFORM]
        assert [c["id"] for c in page] == [workspace._page_key()]
        recent = dashboard.conversation_payload(agent, workspace._page_key())["decisions"]
        assert [(d["answered"], d["excerpt"], d["spoke"]) for d in recent] == [("hello there", "hi back", True)]
    finally:
        decision_log.LOG.clear()
