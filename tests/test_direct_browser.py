"""The browser-worked platforms' shared layer, against a small site of our own:
the sign-in kept in a profile, an inbox read once, answers typed and proven
sent, a changed page found again, and nothing left running."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from persona_agent.direct import browser as web
from persona_agent.direct.base import Refused

from web_standin import Site

try:
    import playwright  # noqa: F401
    DRIVER = True
except ImportError:
    DRIVER = False

needs_browser = pytest.mark.skipif(not DRIVER or web.find_browser() is None,
                                   reason="needs Playwright and an installed Chromium-family browser")


class Standin(web.WebPlatform):
    kind = "standin"
    reply_names = (".reply-v1",)
    editor_names = (".editor-v1",)

    def __init__(self, site: Site, values: dict, **kwargs):
        super().__init__(values, **kwargs)
        self.site = site
        self._look_s = (0.2, 0.3)

    async def signed_in(self, page):
        await page.goto(self.site.url + "/")
        me = page.locator("#me")
        if not await me.count():
            return None
        return await me.get_attribute("data-id"), await me.inner_text()

    async def wall(self, page) -> str:
        if await page.locator("#verify").count():
            return web.VERIFICATION
        if await page.locator('a[href="/login"]').count():
            return web.SIGNED_OUT
        return ""

    async def inbox(self, page):
        await page.goto(self.site.url + "/inbox")
        if await self.wall(page):
            return []
        await page.locator("inbox-list[ready]").wait_for(state="attached")
        found = []
        for item in await page.locator("inbox-list .item").all():
            ident, thread = await item.get_attribute("data-id"), await item.get_attribute("data-thread")
            text = await item.locator(".said").inner_text()
            found.append(web.Incoming(
                key=f"reply:{ident}",
                event={"conversation_type": "group", "conversation_id": thread,
                       "sender_id": await item.get_attribute("data-from"),
                       "sender_name": await item.locator(".who").inner_text(),
                       "message_id": ident, "addressed": True, "text": text,
                       "segments": [{"type": "text", "text": text}]},
                target={"thread": thread, "comment": ident}))
        return found

    async def post(self, page, target, text: str) -> None:
        await page.goto(f"{self.site.url}/thread/{target['thread']}")
        row = page.locator(f'.comment[data-id="{target["comment"]}"]')
        await row.wait_for()
        editor = row.locator('[contenteditable="true"]')

        async def box_open() -> bool:
            return await editor.count() > 0

        await self.hands.press("open_reply", self.reply_names, within=row, proof=box_open,
                               goal="the button that opens a reply box under this comment")
        await self.hands.write("reply_box", self.editor_names, text, within=row,
                               goal="the box to type a reply in")
        before = len(self.site.replies)

        async def sent() -> bool:
            return len(self.site.replies) > before

        await self.hands.press("send_reply", (".send",), within=row, proof=sent, again=False,
                               goal="the button that sends the reply")


@pytest.fixture
def site():
    made = Site()
    yield made
    made.close()


@pytest.fixture(autouse=True)
def quick(monkeypatch):
    monkeypatch.setattr(web, "TYPE_MAX_S", 0.2)
    monkeypatch.setenv(web.HEADLESS_ENV, "1")


def platform(site: Site, tmp_path: Path, **kwargs) -> Standin:
    return Standin(site, {}, state=tmp_path / "state.json",
                   browser=web.Browser(tmp_path / "profile"), **kwargs)


async def sign_in(site: Site, tmp_path: Path) -> None:
    """What the owner does in the sign-in window."""
    browser = web.Browser(tmp_path / "profile")
    context = await browser.start()
    page = context.pages[0] if context.pages else await context.new_page()
    await page.goto(site.url + "/login?as=42")
    await browser.stop()


async def until(condition, seconds: float = 20.0) -> None:
    for _ in range(int(seconds / 0.1)):
        if condition():
            return
        await asyncio.sleep(0.1)
    raise AssertionError("did not happen in time")


# ---------------------------------------------------------------- without a browser

def test_the_browser_can_be_named(tmp_path, monkeypatch):
    chosen = tmp_path / "browser.exe"
    chosen.write_bytes(b"")
    monkeypatch.setenv(web.BROWSER_ENV, str(chosen))
    assert web.find_browser() == chosen
    monkeypatch.setenv(web.BROWSER_ENV, str(tmp_path / "missing"))
    assert web.find_browser() is None


def test_what_was_seen_is_kept_for_one_account(tmp_path):
    seen = web.Seen(tmp_path / "state.json")
    seen.load("42")
    assert seen.add("a") and not seen.add("a")
    seen.primed = True
    seen.save()
    again = web.Seen(tmp_path / "state.json")
    again.load("42")
    assert again.primed and not again.add("a")
    other = web.Seen(tmp_path / "state.json")
    other.load("43")
    assert not other.primed and other.add("a"), "another account starts over"


def test_a_control_is_remembered_by_what_it_says():
    assert web._lasting({"tag": "button", "label": "Reply to Kim"}) == 'button[aria-label="Reply to Kim"]'
    assert web._lasting({"tag": "div", "placeholder": "Write"}) == 'div[placeholder="Write"]'
    assert web._lasting({"tag": "button", "text": "Reply"}) == 'button:text-is("Reply")'
    assert web._lasting({"tag": "div", "text": "typed words", "editable": True}) == ""
    assert web._lasting({"tag": "button", "text": 'say "hi"'}) == ""


def test_what_was_learned_is_kept_and_asking_is_bounded(tmp_path):
    path = tmp_path / "learned.json"
    learned = web.Learned(path)
    learned.keep("open_reply", 'button:text-is("Reply")')
    assert web.Learned(path).steps == {"open_reply": ['button:text-is("Reply")']}
    for _ in range(web.REPAIRS_A_DAY):
        assert learned.may_ask()
        learned.count()
    assert not learned.may_ask()
    assert not web.Learned(path).may_ask(), "the count outlives a restart"


def test_no_browser_is_a_named_refusal(tmp_path, monkeypatch):
    monkeypatch.setenv(web.BROWSER_ENV, str(tmp_path / "missing"))
    with pytest.raises(Refused, match=web.NO_BROWSER):
        web.open_sign_in(tmp_path / "profile", "http://127.0.0.1:9/")
    if DRIVER:
        with pytest.raises(Refused, match=web.NO_BROWSER):
            asyncio.run(web.Browser(tmp_path / "profile").start())


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
def test_the_sign_in_is_kept_and_the_inbox_is_read_once_and_answered(site, tmp_path):
    site.say("c1", "was here before the character")
    events: list = []
    states: list = []

    async def run() -> None:
        await sign_in(site, tmp_path)
        made = platform(site, tmp_path)
        assert await made.check() == "Robin", "the sign-in outlived the browser"
        assert made.keep()["account_id"] == "42"

        made = platform(site, tmp_path)
        made.dropped = lambda cause=None: states.append(str(cause))

        async def on_event(event, target) -> None:
            events.append((event, target))
        task = asyncio.create_task(made.run(on_event, lambda: states.append("connected")))
        try:
            await until(lambda: "connected" in states)
            await asyncio.sleep(1.0)
            assert events == [], "what was there before is not answered"
            site.say("c2", "hello there")
            await until(lambda: len(events) == 1)
            event, target = events[0]
            assert (event["text"], event["sender_name"], event["message_id"]) == ("hello there", "Kim", "c2")
            await asyncio.sleep(1.0)
            assert len(events) == 1, "one item is handed on once"

            sent = await made.send(target, [{"type": "text", "text": "hi Kim,\nnice to meet you"},
                                            {"type": "image", "b64": "AAAA"}])
            assert sent == 1
            assert site.replies == [{"thread": "t1", "parent": "c2", "text": "hi Kim,\nnice to meet you"}]

            # A verification: the platform waits and says why, then goes on.
            site.wall = True
            await until(lambda: any(web.VERIFICATION in state for state in states))
            site.wall = False
            site.say("c3", "still there?")
            await until(lambda: len(events) == 2)

            # Signed out by the site: that ends it, with the reason.
            site.signed_out = True
            with pytest.raises(Refused, match=web.SIGNED_OUT):
                await asyncio.wait_for(task, 20)
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
            await asyncio.sleep(1.0)
            assert events == []
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            await made.close()
    asyncio.run(run())
    saved = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    assert saved["owner"] == "42" and saved["primed"] and "reply:c3" in saved["seen"]


@needs_browser
def test_a_changed_page_is_found_again_and_a_covered_button_is_pressed(site, tmp_path):
    site.say("c1", "first")
    asked: list = []

    async def repair(goal: str, controls: list) -> int:
        asked.append(goal)
        wanted = {"the button that opens a reply box under this comment": ("button", "Reply")}.get(goal)
        if wanted:
            return next(int(c["ref"]) for c in controls if (c["tag"], c["text"]) == wanted)
        return next(int(c["ref"]) for c in controls if c["editable"])

    async def run() -> None:
        await sign_in(site, tmp_path)
        made = platform(site, tmp_path, home=None)
        made.repair = repair
        try:
            await made._who()
            made.hands.learned = web.Learned(tmp_path / "learned.json")
            target = {"thread": "t1", "comment": "c1"}

            # Something lies over the page: the press still lands.
            site.cover = True
            assert await made.send(target, [{"type": "text", "text": "under a cover"}]) == 1
            site.cover = False
            assert asked == []

            # The site renames its classes: the model is asked, once per step.
            site.layout = 2
            assert await made.send(target, [{"type": "text", "text": "after the change"}]) == 1
            assert len(asked) == 2
            assert await made.send(target, [{"type": "text", "text": "and again"}]) == 1
            assert len(asked) == 2, "both are remembered by what they say"
        finally:
            await made.close()
    asyncio.run(run())
    assert [reply["text"] for reply in site.replies] == ["under a cover", "after the change", "and again"]
    learned = json.loads((tmp_path / "learned.json").read_text(encoding="utf-8"))
    assert learned["steps"] == {"open_reply": ['button:text-is("Reply")'],
                                "reply_box": ['div[aria-label="Write a reply"]']}


@needs_browser
def test_a_step_nobody_can_find_stops_the_sending_and_is_named(site, tmp_path):
    site.say("c1", "first")
    notices: list = []

    async def run() -> None:
        await sign_in(site, tmp_path)
        made = platform(site, tmp_path)
        made.notice = notices.append
        made.reply_names = (".gone",)
        try:
            await made._who()
            made.hands.repair = None
            import persona_agent.direct.browser as module
            original = module.STEP_MS
            module.STEP_MS = 1500
            try:
                sent = await made.send({"thread": "t1", "comment": "c1"},
                                       [{"type": "text", "text": "one"}, {"type": "text", "text": "two"}])
            finally:
                module.STEP_MS = original
            assert sent == 0
        finally:
            await made.close()
    asyncio.run(run())
    assert notices == [web.PAGE_CHANGED] and site.replies == []


def test_a_day_s_messages_are_counted_and_kept(tmp_path, monkeypatch):
    seen = web.Seen(tmp_path / "state.json")
    seen.load("42")
    seen.count_post()
    seen.count_post()
    again = web.Seen(tmp_path / "state.json")
    again.load("42")
    assert again.posts_today() == 2
    monkeypatch.setenv(web.POSTS_ENV, "5")
    assert web.posts_a_day() == 5
    monkeypatch.setenv(web.POSTS_ENV, "many")
    assert web.posts_a_day() == web.POSTS_A_DAY
