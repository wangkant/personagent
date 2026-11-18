"""Bilibili through its website, signed in by the owner in the platform's own
browser profile.

Read: the message centre's "replies to me" and "@ me" lists and its private
messages, from the data the message centre itself loads as it is opened.
Written: a reply under the comment on the video's own page, and a private
message in the message centre's conversation, each typed into the site's own
box and sent with its own button. Only something written to the account is
answered; nothing is posted unprompted.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Awaitable, Callable, Optional, Sequence

from .base import Paused, media, plain_name
from .browser import SIGNED_OUT, STEP_MS, VERIFICATION, Incoming, StepFailed, WebPlatform, look

logger = logging.getLogger("personagent.direct.bilibili")

# Addresses the message centre and the video page load their data from.
NAV = "/x/web-interface/nav"
REPLIES = "/x/msgfeed/reply"
MENTIONS = "/x/msgfeed/at"
SESSIONS = "/session_svr/v1/session_svr/get_sessions"
MESSAGES = "/svr_sync/v1/svr_sync/fetch_session_msgs"
CARDS = "/user/cards"
COMMENTS = "/x/v2/reply/wbi/main"
COMMENT_SENT = "/x/v2/reply/add"
MESSAGE_SENT = "/web_im/v1/web_im/send_msg"

# A video's comments; other kinds (posts, articles, live) have pages of their own.
VIDEO = 1
TEXT_MESSAGE, PICTURE_MESSAGE = 1, 2
# Conversations opened in one look, and messages taken from one the account never answered.
OPEN_A_LOOK = 5
UNANSWERED_MAX = 5
SETTLE_S = 2.5

# The comment section is a tree of web components; each renderer carries its comment as `data`.
_MARK_COMMENT = """([rpid, root]) => {
  const hosts = [];
  const walk = (node) => {
    for (const el of node.querySelectorAll('*')) {
      if (el.shadowRoot) walk(el.shadowRoot);
      const tag = el.tagName.toLowerCase();
      if (tag === 'bili-comment-renderer' || tag === 'bili-comment-reply-renderer' ||
          tag === 'bili-comment-thread-renderer') hosts.push(el);
    }
  };
  walk(document);
  const id = (el) => { const d = el.data || {}; return String(d.rpid_str || d.rpid || ''); };
  const thread = hosts.find(el => el.tagName.toLowerCase() === 'bili-comment-thread-renderer' && id(el) === root);
  if (!thread) return '';
  thread.setAttribute('data-pa-thread', root);
  const exact = hosts.find(el => el.tagName.toLowerCase() !== 'bili-comment-thread-renderer' && id(el) === rpid);
  const own = hosts.find(el => el.tagName.toLowerCase() === 'bili-comment-renderer' && id(el) === root);
  const chosen = exact || own;
  if (!chosen) return '';
  chosen.setAttribute('data-pa-rpid', rpid);
  return exact ? 'exact' : 'thread';
}"""

# The message centre's rows keep what they show as component data; read when its own request was missed.
_FEED_ROWS = """() => [...document.querySelectorAll('.interaction-item')].map(el => {
  const vm = el.__vue__ || (el.parentElement && el.parentElement.__vue__) || {};
  const d = vm.data || (vm.$props && vm.$props.data) || null;
  return d ? JSON.parse(JSON.stringify(d)) : null;
}).filter(Boolean)"""

_GEETEST = (".geetest_panel", ".geetest_box", ".geetest_holder", ".geetest_widget", "[class*='geetest_']")
_LOGIN_MASK = (".bili-mini-mask .bili-mini-login-right-wp", ".bili-mini-mask .login-pwd-wp",
               ".bili-mini-mask .login-scan-wp")

# Every control, most durable name first: what it says, then where it sits.
REPLY_OPEN = ('bili-comment-action-buttons-renderer #reply button', '#reply button',
              'button:text-is("回复")', 'button:text-is("Reply")', 'button[aria-label*="回复"]')
REPLY_BOX = ('bili-comment-rich-textarea .brt-editor[contenteditable="true"]',
             '.brt-editor[contenteditable="true"]', '#editor [contenteditable="true"]',
             '[contenteditable="true"]', 'textarea')
REPLY_SEND = ('#pub button', 'button:text-is("发布")', 'button:has-text("发布")', 'button:text-is("Post")',
              'button:text-is("发送")')
MESSAGE_BOX = ('.msb-textarea .brt-editor[contenteditable="true"]',
               '[class*="MessageSendBox__Textarea"] [contenteditable="true"]',
               '[class*="MessageSendBox"] [contenteditable="true"]', '.brt-editor[contenteditable="true"]',
               'textarea[placeholder*="消息"]')
MESSAGE_SEND = ('[class*="MessageSendBox__SendBtn"]', 'button:text-is("发送")', ':text-is("发送")',
                'button:text-is("Send")')

GOAL_REPLY_OPEN = ("the 回复 (Reply) button in the action row under this one comment, which opens a "
                   "box for answering it; not like, dislike, share, report or the more menu")
GOAL_REPLY_BOX = ("the editable box where the text of a reply to this comment is typed (it shows "
                  "请输入内容 or 回复 @name before anything is typed); not the emoji, @ or picture buttons")
GOAL_REPLY_SEND = ("the 发布 (Post) button of this reply box, which publishes the reply typed in it; "
                   "not the emoji, @, picture or the forward-to-my-posts checkbox")
GOAL_MESSAGE_BOX = ("the editable box at the bottom of this private conversation where a message is "
                    "typed (it shows 请输入消息内容 before anything is typed)")
GOAL_MESSAGE_SEND = ("the 发送 (Send) button next to the message box of this private conversation, "
                     "which sends the typed message; not the picture or emoji buttons")


class Bilibili(WebPlatform):
    kind = "bilibili"
    sign_in_url = "https://passport.bilibili.com/login"
    home_url = "https://message.bilibili.com/"
    # A private message takes 500 characters; a comment more.
    max_text = 500
    #: Where the message centre and the sign-in live; a test points them at a stand-in.
    message_url = "https://message.bilibili.com/"
    passport_host = "passport.bilibili.com"

    def __init__(self, values: dict, **kwargs):
        super().__init__(values, **kwargs)
        self.names: dict[str, str] = {}

    # ---------------------------------------------------------------- reading

    async def _gather(self, page: Any, parts: Sequence[str], action: Callable[[], Awaitable[Any]],
                      *, settle_s: Optional[float] = None) -> dict[str, list]:
        """The JSON answers to what the page itself requests from addresses
        containing each of `parts` while `action` runs, in order of arrival."""
        found: dict[str, list] = {part: [] for part in parts}
        pending: list[asyncio.Task] = []

        async def read(part: str, response: Any) -> None:
            try:
                found[part].append(await response.json())
            except Exception:
                pass

        def heard(response: Any) -> None:
            if not response.ok:
                return
            for part in parts:
                if part in response.url:
                    pending.append(asyncio.ensure_future(read(part, response)))
                    break
        page.on("response", heard)
        try:
            await action()
            deadline = time.monotonic() + STEP_MS / 1000
            # The first part is the one wanted; the others come with it or not at all.
            while not _good(found[parts[0]]) and time.monotonic() < deadline and not self._away(page):
                await asyncio.sleep(0.25)
            await asyncio.sleep(SETTLE_S if settle_s is None else settle_s)
            if pending:
                await asyncio.wait(pending, timeout=5)
        finally:
            page.remove_listener("response", heard)
        return found

    def _away(self, page: Any) -> bool:
        """Sent to the sign-in page: nothing more will load."""
        return self.passport_host in (page.url or "")

    async def _open_centre(self, page: Any, section: str, parts: Sequence[str]) -> dict[str, list]:
        url = self.message_url.rstrip("/") + "/#/" + section

        async def go() -> None:
            # Going to the address already shown changes nothing, so the list would not load again.
            if page.url == url:
                await page.reload(wait_until="domcontentloaded")
            else:
                await page.goto(url, wait_until="domcontentloaded")
        return await self._gather(page, parts, go)

    async def signed_in(self, page: Any) -> Optional[tuple[str, str]]:
        found = await self._open_centre(page, "reply", (NAV,))
        for answer in found[NAV]:
            data = answer.get("data") if isinstance(answer, dict) else None
            if not isinstance(data, dict):
                continue
            if data.get("isLogin") and data.get("mid"):
                return str(data["mid"]), plain_name(data.get("uname"), str(data["mid"]))
            if data.get("isLogin") is False:
                return None
        if self._away(page):
            return None
        raise StepFailed("who")

    async def wall(self, page: Any) -> str:
        try:
            for selector in _GEETEST:
                if await page.locator(f"{selector} >> visible=true").count():
                    return VERIFICATION
            if self._away(page):
                return SIGNED_OUT
            for selector in _LOGIN_MASK:
                if await page.locator(f"{selector} >> visible=true").count():
                    return SIGNED_OUT
        except Exception:
            return ""
        return ""

    async def inbox(self, page: Any) -> list[Incoming]:
        found = await self._open_centre(page, "reply", (REPLIES, NAV))
        if self._away(page) or await self.wall(page):
            return []
        replies = _items(found[REPLIES])
        if replies is None:
            replies = await self._rows(page, "reply")
        if replies is None:
            raise StepFailed("replies")
        items = [i for i in (self._comment(row, "reply") for row in replies) if i]

        found = await self._open_centre(page, "at", (MENTIONS,))
        mentions = _items(found[MENTIONS])
        if mentions is None:
            mentions = await self._rows(page, "at") or []
        items += [i for i in (self._comment(row, "at") for row in mentions) if i]

        if not self._away(page) and not await self.wall(page):
            items += await self._messages(page)
        items.sort(key=lambda item: item.event.get("sent_at") or 0)
        return items

    async def _rows(self, page: Any, section: str) -> Optional[list]:
        """The list's rows as the page keeps them, turned back into feed items."""
        try:
            await page.locator(".interaction-item").first.wait_for(timeout=4000)
            rows = await page.evaluate(_FEED_ROWS)
        except Exception:
            return None
        items = []
        for row in rows or []:
            reply = ((row.get("action") or {}).get("reply") or {}).get("params") or {}
            user = (row.get("users") or [{}])[0]
            url = str(row.get("url") or "")
            text = "".join(str(node.get("text") or "") for node in row.get("msgNodes") or []
                           if isinstance(node, dict))
            items.append({"id": row.get("id"), "user": user,
                          f"{'reply' if section == 'reply' else 'at'}_time": row.get("time"),
                          "item": {"type": "reply", "business_id": reply.get("type"),
                                   "subject_id": reply.get("oid"), "root_id": reply.get("root"),
                                   "source_id": reply.get("parent"), "uri": url.split("#")[0],
                                   "source_content": text, "title": (row.get("cover") or {}).get("text") or "",
                                   "target_reply_content": str(row.get("reference") or "").split(" : ", 1)[-1],
                                   "hide_reply_button": not reply}})
        return items

    def _comment(self, row: Any, section: str) -> Optional[Incoming]:
        """One "replies to me" or "@ me" item: a comment written to the account under a video."""
        if not isinstance(row, dict):
            return None
        item, user = row.get("item") or {}, row.get("user") or {}
        sender = str(user.get("mid") or "")
        source, oid = str(item.get("source_id") or ""), str(item.get("subject_id") or "")
        uri = str(item.get("uri") or "")
        if (not sender or sender == self.bot_id or not source or source == "0" or not oid
                or item.get("type") == "danmu" or _int(item.get("business_id")) != VIDEO
                or item.get("hide_reply_button") or not uri.startswith(("http://", "https://", "//"))):
            return None
        text = str(item.get("source_content") or "")
        if not text.strip():
            return None
        if uri.startswith("//"):
            uri = "https:" + uri
        name = plain_name(user.get("nickname"), sender)
        self.names[sender] = name
        root = str(item.get("root_id") or "")
        root = source if root in ("", "0") else root
        segments: list[dict] = []
        quoted = str(item.get("target_reply_content") or "")
        if quoted:
            segments.append({"type": "reply", "message_id": str(item.get("target_id") or root), "text": quoted,
                             "sender_id": self.bot_id, "sender_name": self.name})
        segments.append({"type": "text", "text": text})
        if section == "at":
            segments.append({"type": "mention", "user_id": self.bot_id, "name": self.name})
        when = _int(row.get("reply_time") or row.get("at_time"))
        return Incoming(
            # One comment both replying to the account and naming it is answered once.
            key=f"comment:{source}",
            event={"conversation_type": "group", "conversation_id": f"av{oid}",
                   "conversation_name": plain_name(item.get("title"), item.get("desc")),
                   "sender_id": sender, "sender_name": name, "message_id": source,
                   **({"sent_at": when} if when else {}),
                   "addressed": True, "text": text, "segments": segments},
            target={"kind": "comment", "url": uri.split("#")[0] + "#reply" + source,
                    "oid": oid, "rpid": source, "root": root})

    async def _messages(self, page: Any) -> list[Incoming]:
        found = await self._open_centre(page, "whisper", (SESSIONS, CARDS))
        sessions = []
        for answer in found[SESSIONS]:
            data = answer.get("data") if isinstance(answer, dict) and answer.get("code") == 0 else None
            if isinstance(data, dict) and isinstance(data.get("session_list"), list):
                sessions = data["session_list"]
                break
        else:
            if not self._away(page):
                logger.info("bilibili: the private messages did not load this time")
            return []
        self._learn_names(found[CARDS])
        items: list[Incoming] = []
        opened = 0
        for session in sessions:
            if not isinstance(session, dict) or _int(session.get("session_type")) != 1:
                continue
            if session.get("system_msg_type"):
                continue
            talker = str(session.get("talker_id") or "")
            last = session.get("last_msg") or {}
            if not talker or not isinstance(last, dict) or str(last.get("sender_uid")) != talker:
                continue
            latest = self._message(talker, last)
            if latest is None:
                continue
            if not self.seen.primed or self.seen.has(latest.key):
                # The first look only learns what is there; nothing new since the last look here.
                items.append(latest)
                continue
            if opened >= OPEN_A_LOOK:
                continue
            opened += 1
            items += await self._conversation(page, talker) or [latest]
        return items

    async def _conversation(self, page: Any, talker: str) -> list[Incoming]:
        """The messages of one conversation that came after what was seen or answered."""
        found = await self._open_centre(page, f"whisper/mid{talker}", (MESSAGES, CARDS))
        self._learn_names(found[CARDS])
        messages: list = []
        for answer in found[MESSAGES]:
            data = answer.get("data") if isinstance(answer, dict) and answer.get("code") == 0 else None
            if isinstance(data, dict) and isinstance(data.get("messages"), list):
                messages = data["messages"]
                break
        messages = sorted((m for m in messages if isinstance(m, dict)), key=lambda m: _int(m.get("msg_seqno")))
        prefix = f"dm:{talker}:"
        known = [_int(key[len(prefix):]) for key in self.seen.keys if key.startswith(prefix)]
        if known:
            after = max(known)
        else:
            # A conversation never seen here: only what came since the account last wrote in it.
            mine = [_int(m.get("msg_seqno")) for m in messages if str(m.get("sender_uid")) == self.bot_id]
            after = max(mine) if mine else 0
        fresh = [m for m in messages if _int(m.get("msg_seqno")) > after and str(m.get("sender_uid")) == talker]
        if not known:
            fresh = fresh[-UNANSWERED_MAX:]
        return [i for i in (self._message(talker, m) for m in fresh) if i]

    def _message(self, talker: str, message: dict) -> Optional[Incoming]:
        seqno = _int(message.get("msg_seqno"))
        if not seqno:
            return None
        kind = _int(message.get("msg_type"))
        try:
            content = json.loads(message.get("content") or "{}")
        except (TypeError, ValueError):
            content = {}
        if not isinstance(content, dict):
            content = {}
        if kind == TEXT_MESSAGE:
            text = str(content.get("content") or "")
            segments = [{"type": "text", "text": text}] if text.strip() else []
        elif kind == PICTURE_MESSAGE:
            text, segments = "", [media("photo")]
        else:
            return None
        if not segments:
            return None
        name = self.names.get(talker) or talker
        when = _int(message.get("timestamp"))
        return Incoming(
            key=f"dm:{talker}:{seqno}",
            event={"conversation_type": "dm", "sender_id": talker, "sender_name": name,
                   "message_id": str(message.get("msg_key") or seqno),
                   **({"sent_at": when} if when else {}),
                   "addressed": True, "text": text, "segments": segments},
            target={"kind": "dm", "talker": talker})

    def _learn_names(self, answers: list) -> None:
        def walk(value: Any) -> None:
            if isinstance(value, dict):
                mid = value.get("mid")
                name = value.get("name") or value.get("uname")
                if mid and isinstance(name, str) and name.strip():
                    self.names[str(mid)] = name.strip()
                for child in value.values():
                    walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)
        for answer in answers:
            walk(answer.get("data") if isinstance(answer, dict) else None)

    # ---------------------------------------------------------------- writing

    def place(self, target: Any) -> str:
        if isinstance(target, dict) and target.get("kind") == "comment":
            return f"comment:{target.get('oid')}:{target.get('root')}"
        if isinstance(target, dict):
            return f"dm:{target.get('talker')}"
        return str(target)

    async def post(self, page: Any, target: Any, text: str) -> None:
        await self.answer(page, target, text)

    async def answer(self, page: Any, target: dict, text: str, *, dry: bool = False) -> None:
        """Type `text` as the answer to `target` and send it; `dry` stops with
        the send control found and not pressed."""
        try:
            if target.get("kind") == "comment":
                await self._reply(page, target, text, dry)
            else:
                await self._whisper(page, target, text, dry)
        except StepFailed:
            problem = await self.wall(page)
            if problem:
                raise Paused(problem) from None
            raise

    async def _reply(self, page: Any, target: dict, text: str, dry: bool) -> None:
        rpid, root = str(target["rpid"]), str(target["root"])
        same_page = (page.url or "").split("#")[0] == target["url"].split("#")[0]
        await page.goto(target["url"], wait_until="domcontentloaded")
        if same_page:
            # Only the #reply part changed: the page did not load again, so it would not seek the comment.
            await page.reload(wait_until="domcontentloaded")
        await look()
        marked = ""
        for _ in range(12):
            marked = await page.evaluate(_MARK_COMMENT, [rpid, root])
            if marked or self._away(page):
                break
            # The comments load as the reader scrolls down to them.
            await page.mouse.wheel(0, 700)
            await asyncio.sleep(1.2)
        if not marked:
            raise StepFailed("comment")
        if marked != "exact":
            logger.info("bilibili: the answered comment is folded; replying in its thread")
        comment = page.locator(f'[data-pa-rpid="{rpid}"]').first
        thread = page.locator(f'[data-pa-thread="{root}"]').first
        box = thread.locator("#reply-container bili-comment-box").first
        await comment.scroll_into_view_if_needed(timeout=5000)

        async def box_open() -> bool:
            return await box.is_visible()

        await self.hands.press("bilibili_reply_open", REPLY_OPEN, within=comment, proof=box_open,
                               goal=GOAL_REPLY_OPEN)
        await self.hands.write("bilibili_reply_box", REPLY_BOX, text, within=box, goal=GOAL_REPLY_BOX)
        await self._send(page, "bilibili_reply_send", REPLY_SEND, box, COMMENT_SENT, GOAL_REPLY_SEND, dry)

    async def _whisper(self, page: Any, target: dict, text: str, dry: bool) -> None:
        url = self.message_url.rstrip("/") + f"/#/whisper/mid{target['talker']}"
        if page.url != url:
            await page.goto(url, wait_until="domcontentloaded")
            await look()
        await self.hands.write("bilibili_message_box", MESSAGE_BOX, text, goal=GOAL_MESSAGE_BOX)
        await self._send(page, "bilibili_message_send", MESSAGE_SEND, None, MESSAGE_SENT, GOAL_MESSAGE_SEND, dry)

    async def _send(self, page: Any, step: str, selectors: Sequence[str], within: Any, part: str,
                    goal: str, dry: bool) -> None:
        """Press the send control once; sent when the site's own answer to it says so."""
        if dry:
            await self.hands.find(step, selectors, within=within, goal=goal)
            return
        answers: list = []

        async def read(response: Any) -> None:
            try:
                answers.append(await response.json())
            except Exception:
                answers.append({})

        def heard(response: Any) -> None:
            if part in response.url and response.request.method == "POST":
                asyncio.ensure_future(read(response))

        async def sent() -> bool:
            return any(isinstance(a, dict) and a.get("code") == 0 for a in answers)

        page.on("response", heard)
        try:
            await self.hands.press(step, selectors, within=within, proof=sent, again=False, goal=goal)
        except StepFailed:
            refused = [a.get("code") for a in answers if isinstance(a, dict) and a.get("code")]
            if refused:
                # The site took the press and said no (a closed section, a muted account).
                raise ConnectionError(f"bilibili: the site refused the message ({refused[0]})") from None
            raise
        finally:
            page.remove_listener("response", heard)


def _int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _good(answers: list) -> bool:
    return any(isinstance(a, dict) and "code" in a for a in answers)


def _items(answers: list) -> Optional[list]:
    """A feed's items from the page's own answer; None when it did not come."""
    for answer in answers:
        if isinstance(answer, dict) and answer.get("code") == 0:
            data = answer.get("data") or {}
            items = data.get("items") if isinstance(data, dict) else None
            return items if isinstance(items, list) else []
    return None
