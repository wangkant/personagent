"""The page's chat: pictures the character sends, and messages it sends later."""
from __future__ import annotations

import asyncio
import base64
import os

from fastapi.testclient import TestClient
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


def test_a_removed_picture_is_missing_and_what_is_not_a_picture_is_not_kept(client, workspace):
    name = workspace._keep_picture(base64.b64encode(PNG).decode())
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
