"""YouTube worked through its own pages, against a stand-in that copies the
real pages' structure: who is signed in, comments and replies read once from
the notification list and Studio, answers typed under the comment and proven
sent, a verification, a sign-out, and a renamed control found again."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from persona_agent.direct import browser as web
from persona_agent.direct import youtube as yt
from persona_agent.direct.base import Refused

from youtube_standin import Site, packed

try:
    import playwright  # noqa: F401
    DRIVER = True
except ImportError:
    DRIVER = False

needs_browser = pytest.mark.skipif(not DRIVER or web.find_browser() is None,
                                   reason="needs Playwright and an installed Chromium-family browser")

ME = "UCrobin0000000000000000"


class StandinYouTube(yt.YouTube):
    def __init__(self, site: Site, values: dict, **kwargs):
        super().__init__(values, **kwargs)
        self.www, self.studio, self.accounts = site.url + "/yt", site.url + "/studio", site.url + "/accounts"
        self.home_url = self.www + "/"
        self._look_s = (0.2, 0.3)


@pytest.fixture
def site():
    made = Site()
    made.video("vidOwn00001", "我的第一个视频")
    made.video("vidOther001", "Someone else's video", owner="UCother00000000000000000")
    yield made
    made.close()


@pytest.fixture(autouse=True)
def quick(monkeypatch):
    monkeypatch.setattr(web, "TYPE_MAX_S", 0.2)
    monkeypatch.setenv(web.HEADLESS_ENV, "1")

    async def no_pause(low: float = 0.0, high: float = 0.0) -> None:
        await asyncio.sleep(0.05)
    monkeypatch.setattr(web, "look", no_pause)


def platform(site: Site, tmp_path: Path, **kwargs) -> StandinYouTube:
    return StandinYouTube(site, {}, state=tmp_path / "state.json",
                          browser=web.Browser(tmp_path / "profile"), **kwargs)


async def sign_in(site: Site, tmp_path: Path) -> None:
    """What the owner does in the sign-in window."""
    browser = web.Browser(tmp_path / "profile")
    context = await browser.start()
    page = context.pages[0] if context.pages else await context.new_page()
    await page.goto(f"{site.url}/accounts/login?as={ME}")
    await browser.stop()


async def until(condition, seconds: float = 40.0) -> None:
    for _ in range(int(seconds / 0.1)):
        if condition():
            return
        await asyncio.sleep(0.1)
    raise AssertionError("did not happen in time")


# ---------------------------------------------------------------- without a browser

def test_a_link_to_a_comment_is_read_and_others_are_not():
    assert yt.comment_in_link("/watch?v=dQw4w9WgXcQ&lc=Ugw10bSluCDSZMIxUSB4AaABAg&pp=0gcJ") == (
        "dQw4w9WgXcQ", "Ugw10bSluCDSZMIxUSB4AaABAg")
    assert yt.comment_in_link("https://www.youtube.com/watch?v=dQw4w9WgXcQ"
                              "&lc=Ugw10bSluCDSZMIxUSB4AaABAg.91mBELzM8-Q91nCi0qfFqm") == (
        "dQw4w9WgXcQ", "Ugw10bSluCDSZMIxUSB4AaABAg.91mBELzM8-Q91nCi0qfFqm")
    assert yt.comment_in_link("/watch?v=dQw4w9WgXcQ") is None
    assert yt.comment_in_link("/watch?v=dQw4w9WgXcQ&lc=nonsense") is None


def test_the_comment_a_packed_watch_link_points_at_is_found():
    # As the real page packs it for a comment's time link.
    assert yt.comment_in_params("ehpVZ3cxMGJTbHVDRFNaTUl4VVNCNEFhQUJBZ6ICA8ABAA%3D%3D") == "Ugw10bSluCDSZMIxUSB4AaABAg"
    reply = "Ugw10bSluCDSZMIxUSB4AaABAg.91mBELzM8-Q91nCi0qfFqm"
    assert yt.comment_in_params(packed(reply).replace("%3D", "=")) == reply
    assert yt.comment_in_params("") == "" and yt.comment_in_params("%%%") == ""


def test_comments_are_read_from_the_page_s_own_data():
    site_data = {"onResponseReceivedEndpoints": [], "frameworkUpdates": {"entityBatchUpdate": {"mutations": [
        {"payload": {"commentEntityPayload": {
            "properties": {"commentId": "UgyA", "content": {"content": "first"}, "replyLevel": 0},
            "author": {"channelId": "UC1", "displayName": "@one", "isCurrentUser": False}}}},
        {"payload": {"commentSurfaceEntityPayload": {"publishedTimeCommand": {}}}},
        {"payload": {"commentEntityPayload": {
            "properties": {"commentId": "UgyA.B", "content": {"content": "second"}, "replyLevel": 1},
            "author": {"channelId": "UC2", "displayName": "@two", "isCurrentUser": True}}}}]}}}
    found = yt.comment_entities(site_data)
    assert list(found) == ["UgyA", "UgyA.B"] and found["UgyA.B"]["author"]["isCurrentUser"]
    assert yt._text({"runs": [{"text": "a"}, {"text": "b"}]}) == "ab" and yt._text({"simpleText": "c"}) == "c"


def test_only_notifications_about_comments_count():
    site = Site.__new__(Site)
    site.lang, site.notifications = "zh", [
        {"video": "v1", "comment": "", "message": "a new video"},
        {"video": "v2", "comment": "UgzStandin0001xYz4AaABAg", "message": "a comment"},
        {"video": "v3", "comment": "UgzStandin0001xYz4AaABAg.zStandin0002xYz", "message": "packed",
         "packed_only": True}]
    assert yt.comments_in(site.notification_data()) == [
        ("v2", "UgzStandin0001xYz4AaABAg"), ("v3", "UgzStandin0001xYz4AaABAg.zStandin0002xYz")]


def test_the_account_is_read_from_its_menu():
    site = Site.__new__(Site)
    site.lang, site.accounts = "en", {ME: ("Robin", "@robin")}
    assert yt.account_in_menu(site.account_menu(ME)) == (ME, "Robin", "@robin")
    assert yt.account_in_menu({}) == ("", "", "")


# ---------------------------------------------------------------- with one

@needs_browser
def test_nobody_signed_in_is_refused(site, tmp_path):
    made = platform(site, tmp_path)

    async def run() -> None:
        with pytest.raises(Refused, match="sign_in_missing"):
            await made.check()
    asyncio.run(run())
    assert made.browser.process is None


@needs_browser
def test_comments_and_replies_are_read_once_and_answered(site, tmp_path, monkeypatch):
    monkeypatch.setattr(yt, "STUDIO_EVERY", 1)
    old = site.comment("vidOwn00001", "这是角色来之前的评论")
    mine = site.comment("vidOther001", "Robin's own comment elsewhere", by=ME, name="@robin")
    site.reply(mine, "an old reply")
    events: list = []
    states: list = []

    async def run() -> None:
        await sign_in(site, tmp_path)
        made = platform(site, tmp_path)
        assert await made.check() == "Robin"
        assert made.keep()["account_id"] == ME and made.keep()["handle"] == "@robin"

        made = platform(site, tmp_path)
        made.dropped = lambda cause=None: states.append(str(cause))

        async def on_event(event, target) -> None:
            events.append((event, target))
        task = asyncio.create_task(made.run(on_event, lambda: states.append("connected")))
        try:
            await until(lambda: "connected" in states)
            await until(lambda: made.seen.primed)
            assert events == [], "what was there before is not answered"

            # A comment on the account's video, a reply to its comment elsewhere
            # (whose notification only carries the packed link), a mention, the
            # account's own reply, a comment Studio lists but no notification
            # tells of, and a new upload.
            first = site.comment("vidOwn00001", "视频很好看！")
            answer = site.reply(mine, "I disagree @robin", by="UClee00000000000000000", name="@lee",
                                packed_only=True)
            site.reply(old, "the owner answers", by=ME, name="@robin")
            quiet = site.comment("vidOwn00001", "studio only", by="UCsam00000000000000000", name="@sam",
                                 notify=False)
            site.upload("vidNew00001", "a new video")
            await until(lambda: len(events) == 3)
            await asyncio.sleep(2.0)
            assert len(events) == 3, "each item is handed on once, the account's own never"
            by_id = {event["message_id"]: (event, target) for event, target in events}
            assert set(by_id) == {first, answer, quiet}

            event, target = by_id[first]
            assert (event["text"], event["sender_id"], event["sender_name"]) == ("视频很好看！", "UCkim00000000000000000", "@kim")
            assert (event["conversation_type"], event["conversation_id"], event["conversation_name"]) == (
                "group", "vidOwn00001", "我的第一个视频")
            assert event["addressed"] and event["segments"] == [{"type": "text", "text": "视频很好看！"}]
            assert target == {"video": "vidOwn00001", "comment": first}

            event, target = by_id[answer]
            assert event["segments"][0] == {"type": "reply", "message_id": mine,
                                            "text": "Robin's own comment elsewhere", "sender_id": ME,
                                            "sender_name": "@robin"}
            assert {"type": "mention", "user_id": ME, "name": "Robin"} in event["segments"]
            assert event["conversation_name"] == "Someone else's video"

            sent = await made.send(target, [{"type": "text", "text": "Fair point,\nlet us talk"},
                                            {"type": "image", "b64": "AAAA"}])
            assert sent == 1
            # The box starts with the name of the one answered, as YouTube puts it there.
            [reply] = site.replies
            assert (reply["video"], reply["parent"]) == ("vidOther001", answer)
            assert reply["text"].startswith("@lee") and reply["text"].endswith("Fair point,\nlet us talk")
            assert made.place(target) == "vidOther001"

            # A verification: the platform waits and says why, then goes on.
            site.wall = True
            await until(lambda: any(web.VERIFICATION in state for state in states))
            site.wall = False
            later = site.comment("vidOwn00001", "还在吗？")
            await until(lambda: len(events) == 4)
            assert events[-1][0]["message_id"] == later

            # Signed out by the site: that ends it, with the reason.
            site.signed_out = True
            with pytest.raises(Refused, match=web.SIGNED_OUT):
                await asyncio.wait_for(task, 40)
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            await made.close()

        # A restart does not answer again what it has seen.
        site.signed_out = False
        events.clear()
        made = platform(site, tmp_path)
        task = asyncio.create_task(made.run(on_event, lambda: states.append("again")))
        try:
            await until(lambda: "again" in states)
            await asyncio.sleep(4.0)
            assert events == []
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            await made.close()
    asyncio.run(run())
    saved = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    assert saved["owner"] == ME and saved["primed"] and saved["posted"]


@needs_browser
@pytest.mark.parametrize("lang", ["en", "zh"])
def test_the_reply_button_is_found_by_its_words_and_a_dry_run_sends_nothing(tmp_path, lang):
    site = Site(lang=lang)
    try:
        site.video("vidOwn00001", "video")
        comment = site.comment("vidOwn00001", "hello")
        site.layout = 3     # the button's id is gone; its label is still the site's word for Reply

        async def run() -> None:
            await sign_in(site, tmp_path)
            made = platform(site, tmp_path)
            made.repair = None
            try:
                await made._who()
                made.hands.repair = None
                target = {"video": "vidOwn00001", "comment": comment}
                row = await made.reply_box(made.page, target, "only typed")
                send = await made.hands.find("send_reply", yt.SEND_REPLY, within=row)
                assert await send.is_visible() and site.replies == []
                assert await made.send(target, [{"type": "text", "text": "now sent"}]) == 1
            finally:
                await made.close()
        asyncio.run(run())
        assert [reply["text"] for reply in site.replies] == ["now sent"]
    finally:
        site.close()


@needs_browser
def test_a_renamed_reply_control_is_found_again(site, tmp_path):
    comment = site.comment("vidOwn00001", "first")
    asked: list = []

    async def repair(goal: str, controls: list) -> int:
        asked.append(goal)
        if goal == yt.GOAL_OPEN_REPLY:
            return next(int(c["ref"]) for c in controls if c["label"] == "Write back")
        return next(int(c["ref"]) for c in controls if c["editable"])

    async def run() -> None:
        await sign_in(site, tmp_path)
        made = platform(site, tmp_path)
        made.repair = repair
        try:
            await made._who()
            made.hands.learned = web.Learned(tmp_path / "learned.json")
            target = {"video": "vidOwn00001", "comment": comment}
            site.layout = 2
            assert await made.send(target, [{"type": "text", "text": "after the change"}]) == 1
            assert asked == [yt.GOAL_OPEN_REPLY]
            assert await made.send(target, [{"type": "text", "text": "and again"}]) == 1
            assert len(asked) == 1, "remembered by what it says"
        finally:
            await made.close()
    asyncio.run(run())
    assert [reply["text"] for reply in site.replies] == ["after the change", "and again"]
    learned = json.loads((tmp_path / "learned.json").read_text(encoding="utf-8"))
    assert learned["steps"] == {"open_reply": ['button[aria-label="Write back"]']}
