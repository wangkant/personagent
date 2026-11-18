"""YouTube through the owner's own account, signed in in the platform's
browser profile. What is answered: comments on the account's videos (from
YouTube Studio's comment list) and replies to the account's comments and
mentions of it (from the notification list). An answer is a reply under that
comment, typed on the video's page opened at the comment, which works the
same for all three. YouTube has no private messages."""
from __future__ import annotations

import asyncio
import base64
import logging
import re
from typing import Any, Optional
from urllib.parse import parse_qs, urlsplit

from . import browser as web
from .base import Paused, Refused
from .browser import SIGNED_OUT, VERIFICATION, Incoming, StepFailed, WebPlatform

logger = logging.getLogger("personagent.direct.youtube")

#: Raised by `check` when the account has no channel, which YouTube needs before it takes a comment.
CHANNEL_MISSING = "channel_missing"
# Comments a look reads in full; the rest wait for the next look.
RESOLVE_A_LOOK = 4
# The Studio list is read on the first look and on every this many looks after.
STUDIO_EVERY = 3
# Attempts at reading one comment before it is left alone (deleted, held for review).
RESOLVE_TRIES = 3
# Whether YouTube's own page says someone is signed in.
_LOGGED_IN = "() => { try { return window.ytcfg && ytcfg.get ? ytcfg.get('LOGGED_IN') : null; } catch (e) { return null; } }"
_COMMENT_ID = re.compile(r"Ug[\w-]{16,}(?:\.[\w-]{10,})?")


def _words(attribute: str, words: tuple[str, ...], tag: str = "button") -> list[str]:
    return [f'{tag}[{attribute}="{word}"]' for word in words]


# The same control in the languages YouTube is most often used in.
REPLY_WORDS = ("Reply", "回复", "回覆", "返信", "답글", "Responder", "Répondre", "Antworten", "Rispondi",
               "Ответить", "Balas", "Trả lời", "Yanıtla", "Odpowiedz", "Beantwoorden", "Відповісти", "ตอบกลับ")
NOTIFICATION_WORDS = ("Notifications", "通知", "알림", "Notificaciones", "Benachrichtigungen", "Notifiche",
                      "Уведомления", "Notificações", "Powiadomienia", "Thông báo", "Bildirimler", "Meldingen")
ACCOUNT_WORDS = ("Account menu", "帐号菜单", "账号菜单", "帳戶選單", "アカウント メニュー", "계정 메뉴",
                 "Menú de la cuenta", "Menu du compte", "Kontomenü", "Menu account", "Меню аккаунта",
                 "Menu da conta")
CANCEL_WORDS = ("Cancel", "取消", "キャンセル", "취소", "Cancelar", "Annuler", "Abbrechen", "Annulla", "Отмена")
# A part of the reply box's label in each language ("Add a reply…").
REPLY_BOX_WORDS = ("reply", "回复", "回覆", "返信", "답글", "respuesta", "réponse", "antwort", "risposta",
                   "ответ", "resposta", "balas", "phản hồi", "yanıt", "odpowied")

AVATAR = ("ytd-masthead ytd-topbar-menu-button-renderer button#avatar-btn", "button#avatar-btn",
          *_words("aria-label", ACCOUNT_WORDS))
BELL = ("ytd-masthead ytd-notification-topbar-button-renderer button",
        "ytd-notification-topbar-button-renderer yt-icon-button button",
        *_words("aria-label", NOTIFICATION_WORDS))
OPEN_REPLY = ("ytd-comment-engagement-bar #reply-button-end button", "#reply-button-end button",
              *_words("aria-label", REPLY_WORDS), *[f'button:text-is("{word}")' for word in REPLY_WORDS])
REPLY_BOX = ("ytd-commentbox #contenteditable-root[contenteditable]",
             "#reply-dialog [contenteditable='true']", "#reply-dialog [contenteditable='plaintext-only']",
             *[f'[contenteditable][aria-label*="{word}" i]' for word in REPLY_BOX_WORDS],
             "#reply-dialog textarea")
SEND_REPLY = ("ytd-commentbox #submit-button button", "#reply-dialog #submit-button button",
              *[f'#reply-dialog button[aria-label="{word}"]' for word in REPLY_WORDS])
CANCEL_REPLY = ("ytd-commentbox #cancel-button button", "#reply-dialog #cancel-button button",
                *[f'#reply-dialog button[aria-label="{word}"]' for word in CANCEL_WORDS])

GOAL_AVATAR = ("the round account picture at the right end of the top bar, which opens the account menu "
               "(not the notifications bell, not the create button)")
GOAL_BELL = "the bell button in the top bar that opens the list of notifications"
GOAL_OPEN_REPLY = ("the small reply button under the highlighted comment, beside its like and dislike "
                   "buttons, which opens a box to answer that comment")
GOAL_REPLY_BOX = "the empty text box that opened under the highlighted comment for writing a reply"
GOAL_SEND = ("the button at the right below the reply box that posts the typed reply; not the cancel "
             "button and not the reply button that opened the box")


def _text(value: Any) -> str:
    """The words of a YouTube text object: a string, {"simpleText"}, {"runs"} or {"content"}."""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        if "simpleText" in value:
            return str(value["simpleText"])
        if isinstance(value.get("runs"), list):
            return "".join(str(run.get("text") or "") for run in value["runs"] if isinstance(run, dict))
        if "content" in value:
            return _text(value["content"])
    return ""


def _walk(value: Any):
    """Every dict inside `value`, depth first."""
    stack = [value]
    while stack:
        item = stack.pop()
        if isinstance(item, dict):
            yield item
            stack.extend(reversed(list(item.values())))
        elif isinstance(item, list):
            stack.extend(reversed(item))


def comment_in_link(link: str) -> Optional[tuple[str, str]]:
    """(video id, comment id) of a link to a comment (`/watch?v=...&lc=...`), or None."""
    query = parse_qs(urlsplit(str(link or "")).query)
    video, comment = (query.get("v") or [""])[0], (query.get("lc") or [""])[0]
    return (video, comment) if video and _COMMENT_ID.fullmatch(comment) else None


def comment_in_params(params: str) -> str:
    """The comment a watch link's packed `params` points at, as the page builds them
    for a link to a comment; "" when it points at none."""
    try:
        raw = base64.urlsafe_b64decode(params.replace("%3D", "=") + "=" * (-len(params) % 4))
    except (ValueError, TypeError):
        return ""
    found = _COMMENT_ID.search(raw.decode("latin-1"))
    return found.group(0) if found else ""


def comments_in(data: Any) -> list[tuple[str, str]]:
    """(video id, comment id) of every comment a notification list or Studio's
    comment list points at, in the order given and once each."""
    found: dict[tuple[str, str], None] = {}
    for item in _walk(data):
        pair = None
        url = (((item.get("commandMetadata") or {}).get("webCommandMetadata") or {}).get("url")
               if isinstance(item.get("commandMetadata"), dict) else None)
        if url:
            pair = comment_in_link(url)
        watch = item.get("watchEndpoint")
        if pair is None and isinstance(watch, dict) and watch.get("videoId"):
            comment = comment_in_params(str(watch.get("params") or ""))
            if comment:
                pair = (str(watch["videoId"]), comment)
        if pair is None and isinstance(item.get("commentId"), str) and isinstance(item.get("videoId"), str):
            if _COMMENT_ID.fullmatch(item["commentId"]):
                pair = (item["videoId"], item["commentId"])
        if pair:
            found.setdefault(pair, None)
    return list(found)


def comment_entities(data: Any) -> dict[str, dict]:
    """commentId -> the comment entity the watch page loads its comments as."""
    found: dict[str, dict] = {}
    for item in _walk(data):
        entity = item.get("commentEntityPayload")
        if isinstance(entity, dict):
            ident = str((entity.get("properties") or {}).get("commentId") or "")
            if ident:
                found.setdefault(ident, entity)
    return found


def account_in_menu(data: Any) -> tuple[str, str, str]:
    """(channel id, name, handle) from the account menu the page loads; "" for what it lacks."""
    channel = name = handle = ""
    for item in _walk(data):
        header = item.get("activeAccountHeaderRenderer")
        if isinstance(header, dict):
            name = name or _text(header.get("accountName"))
            handle = handle or _text(header.get("channelHandle"))
        browse = item.get("browseEndpoint")
        if not channel and isinstance(browse, dict) and str(browse.get("browseId") or "").startswith("UC"):
            channel = str(browse["browseId"])
    return channel, name.strip(), handle.strip()


class YouTube(WebPlatform):
    kind = "youtube"
    max_text = 2000
    www = "https://www.youtube.com"
    studio = "https://studio.youtube.com"
    accounts = "https://accounts.google.com"
    sign_in_url = "https://accounts.google.com/ServiceLogin?service=youtube&continue=https://www.youtube.com/"
    home_url = "https://www.youtube.com/"

    def __init__(self, values: dict, **kwargs):
        super().__init__(values, **kwargs)
        self.handle = str(values.get("handle") or "")
        self._looks = 0
        self._tries: dict[str, int] = {}

    def keep(self) -> dict:
        return {**super().keep(), "handle": self.handle}

    def place(self, target: Any) -> str:
        return str(target.get("video") if isinstance(target, dict) else target)

    # ---------------------------------------------------------------- who

    async def _logged_in(self, page: Any) -> Optional[bool]:
        try:
            value = await page.evaluate(_LOGGED_IN)
        except Exception:
            return None
        return value if isinstance(value, bool) else None

    async def _sign_in_offered(self, page: Any) -> bool:
        return await page.locator(f'ytd-masthead a[href^="{self.accounts}/ServiceLogin"]').count() > 0

    async def signed_in(self, page: Any) -> Optional[tuple[str, str]]:
        await page.goto(self.home_url, wait_until="domcontentloaded")
        if self._on_accounts(page.url):
            return None
        if await self.wall(page) == VERIFICATION:
            raise Paused(VERIFICATION)
        await page.locator("ytd-masthead").first.wait_for(state="attached")
        await web.look(0.8, 1.6)
        if await self._logged_in(page) is False or await self._sign_in_offered(page):
            return None
        try:
            answers = await web.page_data(page, "account/account_menu", lambda: self.hands.press(
                "account_menu", AVATAR, proof=lambda: self._popup_shown(page), goal=GOAL_AVATAR))
        except StepFailed:
            answers = []        # Studio still names the channel
        channel, name, handle = "", "", ""
        for answer in answers:
            channel, name, handle = account_in_menu(answer)
            if channel or name:
                break
        await page.keyboard.press("Escape")
        if not channel:
            channel = await self._channel_from_studio(page)
        if not channel:
            raise Refused(CHANNEL_MISSING)
        self.handle = handle
        return channel, name or handle or channel

    async def _channel_from_studio(self, page: Any) -> str:
        """Studio opens on the signed-in channel's own address."""
        await page.goto(self.studio + "/", wait_until="domcontentloaded")
        for _ in range(40):
            found = re.search(r"/channel/(UC[\w-]{10,})", page.url)
            if found:
                return found.group(1)
            if self._on_accounts(page.url):
                return ""
            await asyncio.sleep(0.25)
        return ""

    # ---------------------------------------------------------------- walls

    def _on_accounts(self, url: str) -> bool:
        return url.startswith(self.accounts)

    async def _popup_shown(self, page: Any) -> bool:
        # The dropdown shows even when the list in it is empty.
        shown = page.locator("ytd-popup-container tp-yt-iron-dropdown:visible, "
                             "ytd-popup-container ytd-multi-page-menu-renderer:visible").first
        return await shown.count() > 0 and await shown.is_visible()

    async def wall(self, page: Any) -> str:
        url = page.url
        if "/sorry/" in url or "/challenge" in url or "/speedbump" in url:
            return VERIFICATION
        if self._on_accounts(url):
            return SIGNED_OUT
        try:
            if await page.locator('form#captcha-form, iframe[src*="recaptcha"]').count():
                return VERIFICATION
            if url.startswith(self.www) and (await self._logged_in(page) is False or await self._sign_in_offered(page)):
                return SIGNED_OUT
        except Exception:
            return ""
        return ""

    # ---------------------------------------------------------------- inbox

    async def _notifications(self, page: Any) -> list[tuple[str, str]]:
        await page.goto(self.home_url, wait_until="domcontentloaded")
        if await self.wall(page):
            return []
        await page.locator("ytd-masthead").first.wait_for(state="attached")
        if await self.wall(page):
            return []
        await web.look(0.8, 1.6)
        panel = page.locator("ytd-popup-container ytd-multi-page-menu-renderer").first
        answers = await web.page_data(page, "notification/get_notification_menu", lambda: self.hands.press(
            "notifications", BELL, proof=lambda: self._popup_shown(page), goal=GOAL_BELL))
        pairs = [pair for answer in answers for pair in comments_in(answer)]
        if not pairs:
            for link in await panel.locator('a[href*="lc="]').all():
                pair = comment_in_link(await link.get_attribute("href") or "")
                if pair and pair not in pairs:
                    pairs.append(pair)
        await page.keyboard.press("Escape")
        return pairs

    async def _studio(self, page: Any) -> list[tuple[str, str]]:
        url = f"{self.studio}/channel/{self.bot_id}/comments/inbox"
        answers = await web.page_data(page, "/youtubei/v1/comment", lambda: page.goto(url, wait_until="domcontentloaded"),
                                  settle_s=2.0)
        if await self.wall(page):
            return []
        pairs = [pair for answer in answers for pair in comments_in(answer)]
        if not pairs:
            for link in await page.locator('ytcp-comment-thread a[href*="lc="], ytcp-comment a[href*="lc="]').all():
                pair = comment_in_link(await link.get_attribute("href") or "")
                if pair and pair not in pairs:
                    pairs.append(pair)
        return pairs

    async def inbox(self, page: Any) -> list[Incoming]:
        self._looks += 1
        pairs = await self._notifications(page)
        if await self.wall(page):
            return []
        if not self.seen.primed or (self._looks - 1) % STUDIO_EVERY == 0:
            for pair in await self._studio(page):
                if pair not in pairs:
                    pairs.append(pair)
            if await self.wall(page):
                return []
        # Both lists show the newest first.
        pairs.reverse()
        if not self.seen.primed:
            return [Incoming(key=f"comment:{comment}", event={}) for _, comment in pairs]
        found: list[Incoming] = []
        for video, comment in pairs:
            key = f"comment:{comment}"
            if self.seen.has(key):
                continue
            if len(found) >= RESOLVE_A_LOOK:
                break
            item = await self._read(page, video, comment)
            if await self.wall(page):
                return found
            if item is None:
                self._tries[key] = self._tries.get(key, 0) + 1
                if self._tries[key] >= RESOLVE_TRIES:
                    self._skip(key)
                continue
            if item is False:
                self._skip(key)
                continue
            self._tries.pop(key, None)
            found.append(item)
        return found

    def _skip(self, key: str) -> None:
        """Count an item as seen without handing it on: the account's own, or one that cannot be read."""
        self._tries.pop(key, None)
        if self.seen.add(key):
            self.seen.save()

    async def _to_comment(self, page: Any, video: str, comment: str) -> tuple[Any, list]:
        """Open the video's page at `comment` and bring the comments in: the
        highlighted comment's row, and what the page loaded for them."""
        await page.goto(f"{self.www}/watch?v={video}&lc={comment}", wait_until="domcontentloaded")
        await web.look(1.0, 2.0)
        row = page.locator("ytd-comment-view-model[linked]:visible").first

        async def scroll() -> None:
            for _ in range(12):
                if await row.count() and await row.is_visible():
                    return
                await page.mouse.wheel(0, 700)
                await asyncio.sleep(0.6)

        answers = await web.page_data(page, "youtubei/v1/next", scroll, settle_s=0.5)
        try:
            await row.wait_for(state="visible", timeout=web.STEP_MS)
        except Exception:
            return None, answers
        await row.scroll_into_view_if_needed()
        return row, answers

    async def _read(self, page: Any, video: str, comment: str) -> Any:
        """The event for one comment; False for one never to answer, None when it could not be read now."""
        try:
            row, answers = await self._to_comment(page, video, comment)
        except Exception as exc:
            logger.info("youtube: a comment was not read (%s)", type(exc).__name__)
            return None
        entities: dict[str, dict] = {}
        for answer in answers:
            entities.update(comment_entities(answer))
        title = await self._title(page)
        entity = entities.get(comment)
        if entity is not None:
            author = entity.get("author") or {}
            sender_id, sender_name = str(author.get("channelId") or ""), str(author.get("displayName") or "")
            text = _text((entity.get("properties") or {}).get("content"))
            own = bool(author.get("isCurrentUser"))
        elif row is not None:
            sender_name = (await row.locator("#author-text").first.inner_text()).strip()
            sender_id = (await row.locator("#author-text").first.get_attribute("href") or "").rsplit("/", 1)[-1]
            text = (await row.locator("#content-text").first.inner_text()).strip()
            own = False
        else:
            return None
        if own or (sender_id and sender_id in (self.bot_id, self.handle)) or (
                self.handle and sender_name.strip() == self.handle):
            return False
        if not sender_id or not text.strip():
            return None
        segments: list[dict] = []
        parent = comment.split(".", 1)[0] if "." in comment else ""
        quoted = entities.get(parent) if parent else None
        if quoted is not None:
            quoted_author = quoted.get("author") or {}
            segments.append({"type": "reply", "message_id": parent,
                             "text": _text((quoted.get("properties") or {}).get("content")),
                             "sender_id": str(quoted_author.get("channelId") or ""),
                             "sender_name": str(quoted_author.get("displayName") or "")})
        segments.append({"type": "text", "text": text})
        if self.handle and self.handle.lower() in text.lower():
            segments.append({"type": "mention", "user_id": self.bot_id, "name": self.name})
        event = {"conversation_type": "group", "conversation_id": video, "conversation_name": title,
                 "sender_id": sender_id, "sender_name": sender_name.strip(), "message_id": comment,
                 "addressed": True, "text": text, "segments": segments}
        return Incoming(key=f"comment:{comment}", event=event, target={"video": video, "comment": comment})

    async def _title(self, page: Any) -> str:
        try:
            heading = page.locator("ytd-watch-metadata h1").first
            if await heading.count():
                return " ".join((await heading.inner_text(timeout=3000)).split())
        except Exception:
            pass
        title = await page.title()
        return re.sub(r"\s*-\s*YouTube\s*$", "", title)

    # ---------------------------------------------------------------- answers

    async def reply_box(self, page: Any, target: dict, text: str) -> Any:
        """Open the reply box under the target comment and type `text` in it;
        the comment's row. Nothing is sent."""
        row, _ = await self._to_comment(page, target["video"], target["comment"])
        if row is None:
            raise StepFailed("comment")
        # Any box to type in under the comment proves it opened, whatever the box is called now.
        box = row.locator('[contenteditable="true"], [contenteditable="plaintext-only"], textarea').first

        async def box_open() -> bool:
            return await box.is_visible()

        await self.hands.press("open_reply", OPEN_REPLY, within=row, proof=box_open, goal=GOAL_OPEN_REPLY)
        await self.hands.write("reply_box", REPLY_BOX, text, within=row, goal=GOAL_REPLY_BOX)
        return row

    async def post(self, page: Any, target: Any, text: str) -> None:
        row = await self.reply_box(page, target, text)
        head = " ".join(text.split())[:20]
        shown = page.locator("ytd-comment-view-model #content-text", has_text=head)
        before = await shown.count()
        answered: list = []

        def heard(response: Any) -> None:
            if "comment/create_comment_reply" in response.url and response.ok:
                answered.append(response)

        async def sent() -> bool:
            return bool(answered) or await shown.count() > before

        page.on("response", heard)
        try:
            await self.hands.press("send_reply", SEND_REPLY, within=row, proof=sent, again=False, goal=GOAL_SEND)
        finally:
            page.remove_listener("response", heard)
