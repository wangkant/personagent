"""The home and the days over HTTP: the service's API and the page's."""
from __future__ import annotations

import json
import warnings

import httpx
import pytest

from persona_agent import dashboard, life, server, welcome
from persona_agent.library import KEPT, Item, Library

from helpers import isolated_agent

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from fastapi.testclient import TestClient

NOW = 1_800_000_000
TOKEN = "test-local-capability"
HEADERS = {welcome.TOKEN_HEADER: TOKEN}
DASH_TOKEN = "dashTOKEN-0123456789abcdefghijklmnopqrstuv"
WRITE = {"content-type": "application/json", "x-personagent-dashboard": "1"}
REAL_ASYNC_CLIENT = httpx.AsyncClient
PLAYER = "https://www.youtube-nocookie.com/embed/abc"


@pytest.fixture(autouse=True)
def fixed_clock(monkeypatch):
    monkeypatch.setattr(life, "clock", lambda: NOW)


def fill(runtime) -> list[Item]:
    library = Library(runtime)
    told = library.add(Item(url="https://www.youtube.com/watch?v=abc", site="YouTube", kind="video",
                            title="Slow train north", why="You said you miss long rides.", fits=True,
                            embed=PLAYER, seen_at=NOW - 120, text="A night on the line."))
    plain = library.add(Item(url="https://example.test/post", site="Example", kind="article",
                             title="On kettles", fits=True, seen_at=NOW - 60))
    other = library.add(Item(url="https://example.test/other", title="Not for the owner", seen_at=NOW - 30))
    return [told, plain, other]


# ---------------------------------------------------------------- page ----

@pytest.fixture
def workspace(tmp_path):
    value = welcome.Workspace(tmp_path)
    yield value
    value.close()


@pytest.fixture
def client(workspace):
    with TestClient(welcome.create_app(workspace.home, TOKEN, workspace=workspace),
                    base_url="http://127.0.0.1") as value:
        yield value


def service(workspace, monkeypatch, handler):
    """The character service, answered by `handler`."""
    monkeypatch.setattr(workspace.services, "running", lambda name: name == "agent")
    monkeypatch.setattr(welcome.httpx, "AsyncClient",
                        lambda **kw: REAL_ASYNC_CLIENT(transport=httpx.MockTransport(handler), **kw))
    runtime = workspace.home / "runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    (runtime / "dashboard.token").write_text("service-token\n", encoding="utf-8")


def test_with_the_service_stopped_the_home_is_read_from_its_files(client, workspace):
    fill(workspace.home / "runtime")
    shown = client.get("/api/home", headers=HEADERS).json()
    assert shown["now"]["state"] == "off" and shown["canGoOut"] is False and shown["whyNot"] == "off"
    assert shown["tell"] == 2
    assert shown["growth"]["day"] == 0, "no model yet: not moved in"
    (workspace.home / ".env").write_text("LLM_API_KEY=sk-test-0123456789\n", encoding="utf-8")
    assert client.get("/api/home", headers=HEADERS).json()["growth"]["day"] == 1
    assert (workspace.home / "runtime" / life.BORN_FILE).is_file()
    refused = client.post("/api/home/out", headers=HEADERS, json={})
    assert (refused.status_code, refused.json()) == (409, {"error": "off"})


def test_things_to_tell_become_its_messages_with_their_cards_once(client, workspace):
    told, plain, _ = fill(workspace.home / "runtime")
    client.post("/api/chat/reset", headers=HEADERS, json={})
    said = client.post("/api/home/tell", headers=HEADERS, json={}).json()
    assert said["count"] == 2
    first, second = said["messages"]
    assert first["role"] == "assistant" and first["text"] == "You said you miss long rides."
    assert first["card"]["embed"] == PLAYER and first["card"]["kind"] == "video" and first["card"]["readable"]
    assert second["text"] == "On kettles", "no sentence of its own: the title"
    history = client.get("/api/chat/history", headers=HEADERS).json()["messages"]
    assert [m.get("card", {}).get("url") for m in history] == [told.url, plain.url]
    assert Library(workspace.home / "runtime").get(told.id).told
    assert client.post("/api/home/tell", headers=HEADERS, json={}).json()["count"] == 0
    assert client.get("/api/home", headers=HEADERS).json()["tell"] == 0
    # The chat file holds it too, for the next start of the page.
    saved = json.loads((workspace.home / "runtime" / "desktop" / "browser-chat.json").read_text(encoding="utf-8"))
    assert saved["messages"][0]["card"]["url"] == told.url


def test_the_days_are_read_kept_dismissed_and_talked_about_without_the_service(client, workspace):
    told, plain, other = fill(workspace.home / "runtime")
    days = client.get("/api/days", headers=HEADERS, params={"limit": 2}).json()
    assert [e["id"] for e in days["items"]] == [other.id, plain.id] and days["more"]
    rest = client.get("/api/days", headers=HEADERS, params={"before": plain.id}).json()
    assert [e["id"] for e in rest["items"]] == [told.id]
    assert client.post("/api/days/keep", headers=HEADERS, json={"id": told.id}).json() == {"ok": True, "kept": True}
    shelf = client.get("/api/days", headers=HEADERS, params={"kept": 1}).json()["items"]
    assert [e["id"] for e in shelf] == [told.id]
    assert client.post("/api/days/keep", headers=HEADERS, json={"id": told.id, "kept": False}).json()["kept"] is False
    client.post("/api/days/dismiss", headers=HEADERS, json={"id": other.id})
    assert other.id not in [e["id"] for e in client.get("/api/days", headers=HEADERS).json()["items"]]
    talked = client.post("/api/days/talk", headers=HEADERS, json={"id": other.id}).json()
    assert talked["messages"][-1]["card"]["url"] == other.url
    for path in ("/api/days/keep", "/api/days/dismiss", "/api/days/talk"):
        for ident in ("0" * 16, "../../x", ""):
            r = client.post(path, headers=HEADERS, json={"id": ident})
            assert (r.status_code, r.json()) == (400, {"error": "item_gone"}), (path, ident)
    assert client.get("/api/days", headers=HEADERS).status_code == 200
    assert client.get("/api/days").status_code == 403, "the page's token is needed as for every API"


def test_the_reading_view_and_the_cover_come_from_the_library_only(client, workspace):
    told, plain, _ = fill(workspace.home / "runtime")
    library = Library(workspace.home / "runtime")
    assert client.get("/api/library/text", headers=HEADERS, params={"id": told.id}).json() == {
        "title": "Slow train north", "text": "A night on the line."}
    assert client.get("/api/library/text", headers=HEADERS, params={"id": plain.id}).status_code == 400
    told.picture = library.save_picture(told.id, b"\xff\xd8\xff" + b"x" * 50)
    library.add(told)
    cover = client.get(f"/api/library/picture/{told.id}", headers=HEADERS)
    assert cover.status_code == 200 and cover.headers["content-type"] == "image/jpeg"
    assert cover.content.startswith(b"\xff\xd8\xff")
    for name in (plain.id, "0" * 16, "..%2F..%2F.env"):
        assert client.get(f"/api/library/picture/{name}", headers=HEADERS).status_code == 404


def test_the_page_may_frame_the_listed_players_only(client):
    policy = client.get("/", headers=HEADERS).headers["content-security-policy"]
    frames = next(part for part in policy.split(";") if part.strip().startswith("frame-src")).split()[1:]
    assert frames == ["https://www.youtube-nocookie.com", "https://www.youtube.com", "https://player.bilibili.com"]
    assert "img-src 'self' data: blob:" in policy and "frame-ancestors 'none'" in policy


def test_a_reply_item_keeps_a_clean_card_and_loses_a_foreign_player(workspace):
    card = {"kind": "video", "title": "T", "url": "https://example.test/v", "embed": "https://evil.test/p"}
    entry = workspace._entry({"type": "text", "text": "look", "card": card})
    assert entry["card"]["embed"] == "" and entry["card"]["url"] == card["url"]
    assert "card" not in workspace._entry({"type": "text", "text": "plain"})
    assert "card" not in workspace._entry({"type": "text", "text": "x", "card": {"url": "file:///c:/x"}})


def test_the_running_service_answers_the_home_and_is_asked_to_go_out(client, workspace, monkeypatch):
    seen = []
    home = {"now": {"state": "out", "where": "Bilibili", "since": NOW, "until": None, "count": 0},
            "growth": {"day": 3, "level": 1, "remembers": 0, "learned": 0, "sites": 1, "kept": 0},
            "tell": 0, "canGoOut": False, "whyNot": "out"}
    answers = {"/api/dashboard/home": home, "/api/dashboard/home/out": {"error": "recent"},
               "/api/dashboard/days": {"items": [], "more": False}, "/api/dashboard/days/keep": {"ok": True, "kept": True}}

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json=answers[request.url.path])
    service(workspace, monkeypatch, handler)
    assert client.get("/api/home", headers=HEADERS).json() == home
    refused = client.post("/api/home/out", headers=HEADERS, json={})
    assert (refused.status_code, refused.json()) == (409, {"error": "recent"})
    answers["/api/dashboard/home/out"] = {"ok": True}
    assert client.post("/api/home/out", headers=HEADERS, json={}).json() == {"ok": True}
    assert client.get("/api/days", headers=HEADERS, params={"before": "x" * 16}).json() == {"items": [], "more": False}
    assert seen[-1].url.params["before"] == "x" * 16
    told, *_ = fill(workspace.home / "runtime")
    assert client.post("/api/days/keep", headers=HEADERS, json={"id": told.id}).json()["kept"] is True
    assert json.loads(seen[-1].content) == {"id": told.id, "kept": True}
    assert all(r.headers["x-personagent-dashboard-token"] == "service-token" for r in seen)
    assert all(r.headers.get("x-personagent-dashboard") == "1" for r in seen if r.method == "POST")


def test_a_service_that_cannot_answer_leaves_the_home_readable(client, workspace, monkeypatch):
    service(workspace, monkeypatch, lambda request: httpx.Response(500, json={"code": "boom"}))
    fill(workspace.home / "runtime")
    shown = client.get("/api/home", headers=HEADERS).json()
    assert shown["now"]["state"] == "home" and shown["tell"] == 2
    assert len(client.get("/api/days", headers=HEADERS).json()["items"]) == 3


# ------------------------------------------------------------- service ----

class Roam:
    def __init__(self):
        self.asked, self.allowed = 0, (True, "")

    def available(self):
        return ""

    def can_go_out(self):
        return self.allowed

    def request(self):
        self.asked += 1


@pytest.fixture
def live(tmp_path, monkeypatch):
    saved = (server.agent, server.CONNECTOR_TOKEN, dashboard._token)
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    monkeypatch.setattr(dashboard, "runtime_dir", lambda: runtime)
    agent = isolated_agent(tmp_path / "agent", seeds=True, persona_name="Nova")
    server.agent, server.CONNECTOR_TOKEN, dashboard._token = agent, "", DASH_TOKEN
    try:
        yield agent, runtime
    finally:
        server.agent, server.CONNECTOR_TOKEN, dashboard._token = saved


def service_client() -> TestClient:
    return TestClient(server.app, base_url="http://127.0.0.1:8080", client=("127.0.0.1", 50000),
                      headers={dashboard.TOKEN_HEADER: DASH_TOKEN})


def test_the_service_home_says_what_the_running_character_does(live, monkeypatch):
    agent, runtime = live
    monkeypatch.setattr(life, "asleep_until", lambda now, offset: None)
    c = service_client()
    assert TestClient(server.app, base_url="http://127.0.0.1:8080").get("/api/dashboard/home").status_code == 401
    shown = c.get("/api/dashboard/home").json()
    assert shown["now"]["state"] == "home" and (shown["canGoOut"], shown["whyNot"]) == (False, "off")
    assert shown["growth"]["day"] == 1 and (runtime / life.BORN_FILE).is_file(), "the first start is marked"
    agent._pending_outbound["private:telegram:7"] = type("Gate", (), {"busy": True})()
    assert c.get("/api/dashboard/home").json()["now"] == {
        "state": "answering", "where": "telegram", "chat": "dm", "since": NOW, "until": None, "count": 0}
    agent._pending_outbound.clear()
    monkeypatch.setattr(life, "asleep_until", lambda now, offset: NOW + 600)
    assert c.get("/api/dashboard/home").json()["now"]["state"] == "asleep"


def test_the_service_asks_the_roam_part_to_go_out_and_marks_the_days(live):
    agent, runtime = live
    c = service_client()
    assert c.post("/api/dashboard/home/out", headers=WRITE, json={}).json() == {"error": "off"}
    agent.roam = Roam()
    assert c.post("/api/dashboard/home/out", json={}).status_code == 403, "a write needs its header"
    assert c.post("/api/dashboard/home/out", headers=WRITE, json={}).json() == {"ok": True}
    assert agent.roam.asked == 1
    agent.roam.allowed = (False, "recent")
    assert c.post("/api/dashboard/home/out", headers=WRITE, json={}).json() == {"error": "recent"}
    assert agent.roam.asked == 1
    told, *_ = fill(runtime)
    assert c.get("/api/dashboard/home").json()["canGoOut"] is False
    days = c.get("/api/dashboard/days", params={"limit": 2}).json()
    assert len(days["items"]) == 2 and days["more"]
    assert c.post("/api/dashboard/days/keep", headers=WRITE, json={"id": told.id}).json() == {"ok": True, "kept": True}
    assert Library(runtime).get(told.id).state == KEPT
    assert c.post("/api/dashboard/days/told", headers=WRITE, json={"id": told.id}).json()["ok"]
    assert Library(runtime).get(told.id).told
    assert c.post("/api/dashboard/days/burn", headers=WRITE, json={"id": told.id}).status_code == 404
    assert c.post("/api/dashboard/days/keep", headers=WRITE, json={"id": "0" * 16}).status_code == 404
    assert c.post("/api/dashboard/days/keep", headers=WRITE, json={"id": "../x"}).status_code == 400
