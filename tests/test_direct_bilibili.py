"""Bilibili worked through its website, against a stand-in of the message
centre and a video page with the site's comment components: who is signed
in, the inbox read once from what the pages load, comments and private
messages answered through the site's own boxes, a verification, a sign-out
and a renamed control found again."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from persona_agent.direct import bilibili as bb
from persona_agent.direct import browser as web
from persona_agent.direct.base import Paused, Refused

from bilibili_standin import Bilibili as Site

try:
    import playwright  # noqa: F401
    DRIVER = True
except ImportError:
    DRIVER = False

needs_browser = pytest.mark.skipif(not DRIVER or web.find_browser() is None,
                                   reason="needs Playwright and an installed Chromium-family browser")


class Standin(bb.Bilibili):
    passport_host = "/passport/login"

    def __init__(self, site: Site, values: dict, **kwargs):
        super().__init__(values, **kwargs)
        self.message_url = site.url + "/"
        self._look_s = (0.2, 0.3)


@pytest.fixture
def site():
    made = Site()
    yield made
    made.close()


@pytest.fixture(autouse=True)
def quick(monkeypatch):
    async def glance(*_args) -> None:
        await asyncio.sleep(0.05)
    monkeypatch.setattr(web, "TYPE_MAX_S", 0.2)
    monkeypatch.setattr(bb, "SETTLE_S", 0.4)
    monkeypatch.setattr(bb, "look", glance)
    monkeypatch.setenv(web.HEADLESS_ENV, "1")


def platform(site: Site, tmp_path: Path, **kwargs) -> Standin:
    return Standin(site, {}, state=tmp_path / "state.json", browser=web.Browser(tmp_path / "profile"), **kwargs)


async def sign_in(site: Site, tmp_path: Path) -> None:
    """What the owner does in the sign-in window."""
    browser = web.Browser(tmp_path / "profile")
    context = await browser.start()
    page = context.pages[0] if context.pages else await context.new_page()
    await page.goto(site.url + "/login?as=1001")
    await browser.stop()


async def until(condition, seconds: float = 40.0) -> None:
    for _ in range(int(seconds / 0.1)):
        if condition():
            return
        await asyncio.sleep(0.1)
    raise AssertionError("did not happen in time")


# ---------------------------------------------------------------- without a browser

def feed_item(**item) -> dict:
    base = {"subject_id": 880001, "root_id": 0, "source_id": 7001, "target_id": 0, "type": "video",
            "business_id": 1, "business": "视频", "title": "A walk", "uri": "https://www.bilibili.com/video/BV1x",
            "source_content": "nice", "target_reply_content": "", "hide_reply_button": False}
    return {"id": 1, "user": {"mid": 2002, "nickname": "Kim"}, "item": {**base, **item}, "reply_time": 1700000000}


def test_feed_items_become_events_for_comments_written_to_the_account():
    made = bb.Bilibili({})
    made.bot_id, made.name = "1001", "Robin"
    item = made._comment(feed_item(type="reply", business="评论", root_id=6000, target_id=6000,
                                   target_reply_content="my comment"), "reply")
    assert item.key == "comment:7001"
    assert item.target == {"kind": "comment", "url": "https://www.bilibili.com/video/BV1x#reply7001",
                           "oid": "880001", "rpid": "7001", "root": "6000"}
    event = item.event
    assert (event["conversation_type"], event["conversation_id"], event["conversation_name"]) == \
        ("group", "av880001", "A walk")
    assert (event["sender_id"], event["sender_name"], event["sent_at"], event["addressed"]) == \
        ("2002", "Kim", 1700000000, True)
    assert event["segments"][0] == {"type": "reply", "message_id": "6000", "text": "my comment",
                                    "sender_id": "1001", "sender_name": "Robin"}
    mention = made._comment({**feed_item(), "at_time": 1700000001}, "at")
    assert mention.key == "comment:7001", "a comment that also names the account is answered once"
    assert mention.event["segments"][-1]["type"] == "mention"
    assert made._comment(feed_item(), "reply").target["root"] == "7001", "a top comment is its own thread"

    assert made._comment(feed_item(type="danmu", business="弹幕"), "reply") is None
    assert made._comment(feed_item(business_id=11), "reply") is None, "only a video's comments for now"
    assert made._comment({**feed_item(), "user": {"mid": 1001, "nickname": "Robin"}}, "reply") is None
    assert made._comment(feed_item(hide_reply_button=True), "reply") is None
    assert made._comment(feed_item(uri="bilibili://video/1"), "reply") is None


def test_private_messages_become_events():
    made = bb.Bilibili({})
    made.bot_id = "1001"
    made._learn_names([{"code": 0, "data": {"2002": {"mid": "2002", "name": "Kim"}}}])
    text = made._message("2002", {"sender_uid": 2002, "msg_type": 1, "content": json.dumps({"content": "hi"}),
                                  "msg_seqno": 9, "msg_key": 77, "timestamp": 1700000000})
    assert text.key == "dm:2002:9" and text.target == {"kind": "dm", "talker": "2002"}
    assert (text.event["conversation_type"], text.event["sender_name"], text.event["text"],
            text.event["message_id"]) == ("dm", "Kim", "hi", "77")
    picture = made._message("2002", {"msg_type": 2, "content": "{}", "msg_seqno": 10})
    assert picture.event["segments"] == [{"type": "media", "kind": "photo"}]
    assert made._message("2002", {"msg_type": 10, "content": "{}", "msg_seqno": 11}) is None
    assert made.place({"kind": "dm", "talker": "2002"}) == "dm:2002"
    assert made.place({"kind": "comment", "oid": "1", "root": "2", "rpid": "3"}) == "comment:1:2"


def test_nothing_is_written_unprompted():
    from persona_agent.direct.base import Unsupported
    with pytest.raises(Unsupported):
        bb.Bilibili({}).target({"conversation_id": "av880001"})


# ---------------------------------------------------------------- with one

@needs_browser
def test_nobody_signed_in_is_refused_and_nothing_is_left_running(site, tmp_path):
    made = platform(site, tmp_path)

    async def run() -> None:
        with pytest.raises(Refused, match="sign_in_missing"):
            await made.check()
    asyncio.run(run())
    assert made.browser.process is None


@needs_browser
def test_the_inbox_is_read_once_and_each_kind_is_answered(site, tmp_path):
    mine = site.own_comment("the light was lovely today")
    site.comment_on_video("3003", "was here before the character")
    site.whisper("3003", "1001", "an old message")
    events: list = []
    states: list = []

    async def run() -> None:
        await sign_in(site, tmp_path)
        made = platform(site, tmp_path)
        assert await made.check() == "Robin"
        assert made.keep()["account_id"] == "1001"

        made = platform(site, tmp_path)
        made.dropped = lambda cause=None: states.append(str(cause))

        async def on_event(event, target) -> None:
            events.append((event, target))
        task = asyncio.create_task(made.run(on_event, lambda: states.append("connected")))
        try:
            await until(lambda: "connected" in states)
            await until(lambda: made.seen.primed)
            assert events == [], "what was there before is not answered"

            top = site.comment_on_video("2002", "where is this river?")
            answer = site.reply_to(mine, "2002", "it really was")
            site.mention("3003", "you should see this")
            site.whisper("2002", "1001", "hello Robin")
            site.whisper("2002", "1001", "are you there?")
            await until(lambda: len(events) == 5)
            await asyncio.sleep(1.5)
            assert len(events) == 5, "each item is handed on once"
            by_text = {event["text"]: (event, target) for event, target in events}
            assert set(by_text) == {"where is this river?", "it really was", "@Robin you should see this",
                                    "hello Robin", "are you there?"}
            assert "an old message" not in by_text
            dms = [event["text"] for event, _ in events if event["conversation_type"] == "dm"]
            assert dms == ["hello Robin", "are you there?"], "oldest first"
            event, target = by_text["it really was"]
            assert event["segments"][0]["text"] == "the light was lovely today"
            assert (event["sender_id"], event["conversation_name"]) == ("2002", "A walk by the river")

            # A reply under the comment, on the video's page.
            assert await made.send(by_text["where is this river?"][1],
                                   [{"type": "text", "text": "by the old mill"}]) == 1
            assert site.sent_comments[-1]["root"] == site.sent_comments[-1]["parent"] == top["rpid_str"]
            assert site.sent_comments[-1]["message"] == "by the old mill"
            # A reply to a reply goes under that reply, in its thread.
            assert await made.send(target, [{"type": "text", "text": "glad you agree"}]) == 1
            assert (site.sent_comments[-1]["root"], site.sent_comments[-1]["parent"]) == \
                (mine["rpid_str"], answer["rpid_str"])
            # A private message in the conversation.
            assert await made.send(by_text["hello Robin"][1], [{"type": "text", "text": "I am here"}]) == 1
            assert json.loads(site.sent_messages[-1]["msg[content]"]) == {"content": "I am here"}
            assert site.sent_messages[-1]["msg[receiver_id]"] == "2002"

            # The account's own words never come back.
            await asyncio.sleep(2.0)
            assert len(events) == 5

            site.whisper("2002", "1001", "great, thanks")
            await until(lambda: len(events) == 6)
            assert events[-1][0]["text"] == "great, thanks"

            # A verification: the platform waits and says why, then goes on.
            site.wall = True
            await until(lambda: any(web.VERIFICATION in state for state in states))
            site.wall = False
            site.comment_on_video("3003", "still there?")
            await until(lambda: len(events) == 7)

            # Signed out by the site: that ends it, with the reason.
            site.signed_out = True
            with pytest.raises(Refused, match=web.SIGNED_OUT):
                await asyncio.wait_for(task, 60)
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            await made.close()
    asyncio.run(run())
    saved = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    assert saved["owner"] == "1001" and saved["primed"]


@needs_browser
def test_renamed_controls_are_found_again_and_remembered(site, tmp_path):
    first = site.comment_on_video("2002", "first")
    site.whisper("2002", "1001", "hi")
    asked: list = []

    async def repair(goal: str, controls: list) -> int:
        asked.append(goal)
        if goal == bb.GOAL_REPLY_OPEN:
            pick = next(c for c in controls if c["text"] == "回应")
        elif goal == bb.GOAL_REPLY_SEND:
            pick = next(c for c in controls if c["text"] == "提交")
        elif goal == bb.GOAL_MESSAGE_SEND:
            pick = next(c for c in controls if c["label"] == "发送消息")
        else:
            return 0
        return int(pick["ref"])

    async def run() -> None:
        await sign_in(site, tmp_path)
        made = platform(site, tmp_path, home=None)
        made.repair = repair
        try:
            await made._who()
            made.hands.learned = web.Learned(tmp_path / "learned.json")
            comment = {"kind": "comment", "url": f"{site.url}/video/BV1xx411c7aa#reply{first['rpid_str']}",
                       "oid": "880001", "rpid": first["rpid_str"], "root": first["rpid_str"]}
            dm = {"kind": "dm", "talker": "2002"}
            site.layout = 2
            assert await made.send(comment, [{"type": "text", "text": "after the change"}]) == 1
            assert await made.send(dm, [{"type": "text", "text": "a message after the change"}]) == 1
            assert len(asked) == 3
            assert await made.send(comment, [{"type": "text", "text": "and again"}]) == 1
            assert await made.send(dm, [{"type": "text", "text": "and once more"}]) == 1
            assert len(asked) == 3, "each is remembered by what it says"
        finally:
            await made.close()
    asyncio.run(run())
    assert [c["message"] for c in site.sent_comments] == ["after the change", "and again"]
    assert len(site.sent_messages) == 2
    learned = json.loads((tmp_path / "learned.json").read_text(encoding="utf-8"))
    assert learned["steps"] == {"bilibili_reply_open": ['span[aria-label="回复这条评论"]'],
                                "bilibili_reply_send": ['span:text-is("提交")'],
                                "bilibili_message_send": ['div[aria-label="发送消息"]']}


@needs_browser
def test_two_answers_in_a_row_on_one_video_each_find_their_comment(site, tmp_path):
    older = [site.comment_on_video("2002", f"comment {n}") for n in range(4)]

    async def run() -> None:
        await sign_in(site, tmp_path)
        made = platform(site, tmp_path)
        try:
            await made._who()
            for comment in older[:2]:
                target = {"kind": "comment", "url": f"{site.url}/video/BV1xx411c7aa#reply{comment['rpid_str']}",
                          "oid": "880001", "rpid": comment["rpid_str"], "root": comment["rpid_str"]}
                assert await made.send(target, [{"type": "text", "text": "answer to " + comment["rpid_str"]}]) == 1
        finally:
            await made.close()
    asyncio.run(run())
    assert [c["parent"] for c in site.sent_comments] == [older[0]["rpid_str"], older[1]["rpid_str"]]


@needs_browser
def test_the_lists_are_read_from_the_page_when_their_address_moves(site, tmp_path):
    site.feed_moved = True

    async def run() -> None:
        await sign_in(site, tmp_path)
        made = platform(site, tmp_path)
        try:
            await made._who()
            made.seen.primed = True
            site.comment_on_video("2002", "read from the rows")
            site.mention("3003", "and this one")
            found = await made.inbox(made.page)
            assert {i.event["text"] for i in found} == {"read from the rows", "@Robin and this one"}
            row = next(i for i in found if i.event["text"] == "read from the rows")
            assert row.target["url"].endswith("#reply" + row.target["rpid"])
            assert row.event["sender_name"] == "Kim"
        finally:
            await made.close()
    asyncio.run(run())


@needs_browser
def test_a_dry_run_stops_before_sending_and_a_signed_out_page_pauses(site, tmp_path):
    first = site.comment_on_video("2002", "first")

    async def run() -> None:
        await sign_in(site, tmp_path)
        made = platform(site, tmp_path)
        try:
            await made._who()
            target = {"kind": "comment", "url": f"{site.url}/video/BV1xx411c7aa#reply{first['rpid_str']}",
                      "oid": "880001", "rpid": first["rpid_str"], "root": first["rpid_str"]}
            await made.answer(made.page, target, "typed, never sent", dry=True)
            await made.answer(made.page, {"kind": "dm", "talker": "2002"}, "typed, never sent", dry=True)
            assert site.sent_comments == [] and site.sent_messages == []

            # The site signed the account out: pressing reply shows its sign-in box.
            site.signed_out = True
            made.hands.repair = None
            with pytest.raises(Paused, match=web.SIGNED_OUT):
                await made.answer(made.page, target, "never sent")
        finally:
            await made.close()
    asyncio.run(run())
    assert site.sent_comments == []
