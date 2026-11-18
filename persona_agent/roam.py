"""The character's walks: it goes out on its own as a signed-out visitor,
reads pages on any site and brings back what it saw.

A visitor browser (one headless browser on its own profile, never signed in)
reads a page into a library Item: the facts the page declares about itself
(Open Graph, Twitter card, schema.org JSON-LD) and its readable text. A walk
reads a few pages, asks the model once which to keep and why, and keeps those
in the library. Pages are only read; nothing is signed, posted or got around.
"""
from __future__ import annotations

import asyncio
import contextlib
import html
import importlib.util
import io
import ipaddress
import json
import logging
import random
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional
from urllib.parse import parse_qs, urljoin, urlsplit

from . import people, visits
from .direct import browser as web
from .ingestion import MAX_IMAGE_PIXELS, _RESERVED_LOCAL_NAMES, _is_internal_ip, _resolve_public_target
from .library import PICTURE_MAX_BYTES, TEXT_MAX, Item, Library, item_id
from .llm import purpose
from .storage import atomic_write_text
from .textproc import (SLEEP_HOUR_END, SLEEP_HOUR_START, _UNTRUSTED_INPUT_RULES, _WEB_DESC_CLOSE,
                       _WEB_DESC_OPEN, _clean_prompt_source, _env_tz_offset, _fence_user_data,
                       strip_json_fences)

logger = logging.getLogger("personagent.roam")

# What stops a walk; the life line shows these.
OUT, ASLEEP, RECENT, LIMIT, OFF, NO_MODEL = "out", "asleep", "recent", "limit", "off", "no_model"

#: Players a card may embed, the page's CSP frame-src lists the same hosts.
PLAYER_HOSTS = ("www.youtube-nocookie.com", "player.bilibili.com", "player.vimeo.com")
IDLE_S = 300.0
OPEN_MS = 20_000
SETTLE_S = 1.5
TICK_S = 30.0
FIRST_WALK_S = 120.0
#: The owner may send it out again this long after it came back.
REQUEST_GAP_S = 1800.0
KEEP_MAX = 3
PICTURE_SIDE = 480
PICTURE_FETCH_MAX = 8_000_000
DESCRIPTION_MAX = 1000
PROMPT_EXCERPT = 400
WHY_MAX = 200

_KNOWN_SITES = {"bilibili.com": "Bilibili", "b23.tv": "Bilibili", "youtube.com": "YouTube",
                "youtu.be": "YouTube"}
_VIDEO_TYPES = {"VideoObject"}
_ARTICLE_TYPES = {"Article", "NewsArticle", "BlogPosting", "ReportageNewsArticle", "TechArticle",
                  "ScholarlyArticle", "AnalysisNewsArticle"}
_POST_TYPES = {"SocialMediaPosting", "DiscussionForumPosting"}
_YT_ID = re.compile(r"[A-Za-z0-9_-]{11}")
_BV = re.compile(r"/video/(BV[0-9A-Za-z]{10})")
_ISO_DURATION = re.compile(r"P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?)?")
# General words for a walk with no topic of the owner's; a hot list does the rest.
_GENERAL = {"zh": ("科普", "音乐", "旅行", "美食", "历史", "手工"),
            "en": ("science", "music", "travel", "cooking", "history", "crafts")}
# A note that names an interest: the words after these are what it is about.
_INTEREST_ZH = re.compile(r"(?:喜欢|爱看|爱玩|爱听|感兴趣|在学|在玩|在看|迷上了?|关注)(?:看|玩|听|学)?([^，。！？；,.!?;、\s]{2,12})")
_INTEREST_EN = re.compile(r"\b(?:likes?|loves?|enjoys?|is into|interested in|is learning|learns|plays|watches|"
                          r"a fan of)\s+([A-Za-z][A-Za-z0-9' -]{2,30})", re.I)

# The page's own description of itself, its readable text and any sign of a wall.
_FACTS = r"""() => {
  const DROP = 'script,style,noscript,template,svg,nav,header,footer,aside,iframe,button,select,dialog,' +
               '[role=navigation],[role=banner],[role=contentinfo],[aria-hidden=true]';
  const BLOCKS = 'h1,h2,h3,h4,p,li,pre,blockquote,figcaption';
  const size = (el) => (el.innerText || '').length;
  const readable = () => {
    let root = null;
    const marked = [...document.querySelectorAll('article,[role=main],main,[itemprop=articleBody]')]
      .filter(el => !el.closest(DROP));
    if (marked.length) root = marked.reduce((a, b) => size(b) > size(a) ? b : a);
    if (!root || size(root) < 200) {
      const score = new Map();
      for (const p of document.querySelectorAll('p')) {
        if (p.closest(DROP)) continue;
        const n = (p.innerText || '').trim().length;
        if (n >= 20) score.set(p.parentElement, (score.get(p.parentElement) || 0) + n);
      }
      let best = null, top = 0;
      for (const [el, n] of score) if (n > top) { best = el; top = n; }
      if (best && (!root || top > size(root))) root = best;
    }
    root = root || document.body;
    if (!root) return '';
    const dropped = (el) => { for (let n = el; n && n !== root; n = n.parentElement) if (n.matches(DROP)) return true; return false; };
    const parts = []; let total = 0;
    for (const el of root.querySelectorAll(BLOCKS)) {
      if (el.querySelector(BLOCKS) || dropped(el)) continue;
      const line = (el.innerText || '').replace(/\s+/g, ' ').trim();
      if (!line) continue;
      parts.push(line); total += line.length;
      if (total > 25000) break;
    }
    return total >= 200 ? parts.join('\n\n') : (root.innerText || '').slice(0, 25000);
  };
  const meta = [];
  for (const m of document.querySelectorAll('meta')) {
    const key = (m.getAttribute('property') || m.getAttribute('name') || m.getAttribute('itemprop') || '').trim().toLowerCase();
    const value = (m.getAttribute('content') || '').trim();
    if (key && value && meta.length < 300) meta.push([key, value.slice(0, 2000)]);
  }
  const ld = [...document.querySelectorAll('script[type="application/ld+json"]')].slice(0, 10)
    .map(s => (s.textContent || '').slice(0, 100000));
  const link = (sel) => { const el = document.querySelector(sel); return el ? el.href : ''; };
  const pick = (o, keys) => { const out = {}; for (const k of keys) { const v = o[k];
    if (['string', 'number', 'boolean'].includes(typeof v)) out[k] = v; } return out; };
  let bili = null, yt = null;
  try { const v = window.__INITIAL_STATE__ && window.__INITIAL_STATE__.videoData;
    if (v && typeof v === 'object') { bili = pick(v, ['bvid', 'title', 'desc', 'pic', 'duration', 'pubdate']);
      bili.owner = v.owner && typeof v.owner.name === 'string' ? v.owner.name : ''; } } catch (e) {}
  try { const p = window.ytInitialPlayerResponse, d = p && p.videoDetails;
    if (p && typeof p === 'object') { yt = {status: p.playabilityStatus && typeof p.playabilityStatus.status === 'string'
      ? p.playabilityStatus.status : ''}; }
    if (d && typeof d === 'object') { Object.assign(yt, pick(d, ['videoId', 'title', 'author', 'lengthSeconds', 'shortDescription']));
      const th = d.thumbnail && d.thumbnail.thumbnails;
      yt.thumbnail = Array.isArray(th) && th.length ? String(th[th.length - 1].url || '') : '';
      const mf = p.microformat && p.microformat.playerMicroformatRenderer;
      yt.publishDate = mf && typeof mf.publishDate === 'string' ? mf.publishDate : '';
      yt.embeddable = !(p.playabilityStatus && p.playabilityStatus.playableInEmbed === false); } } catch (e) {}
  const shown = (el) => { const box = el.getBoundingClientRect(); return box.width > 2 && box.height > 2; };
  const wall = {
    password: [...document.querySelectorAll('input[type=password]')].some(shown),
    captcha: !!document.querySelector('iframe[src*="captcha"], iframe[src*="recaptcha"], iframe[src*="hcaptcha"],' +
      ' iframe[src*="challenges.cloudflare.com"], .g-recaptcha, .h-captcha, #challenge-form, .geetest_panel,' +
      ' .geetest_holder, #cf-challenge-running'),
    words: (document.body && document.body.innerText || '').length,
  };
  return {meta, ld, title: document.title || '', canonical: link('link[rel="canonical"]'),
          oembed: link('link[rel="alternate"][type="application/json+oembed"]'),
          text: readable(), bili, yt, wall};
}"""


# ---------------------------------------------------------------- addresses

def host_ok(host: str) -> bool:
    """False for a name or literal address that is this computer or its network."""
    host = (host or "").strip("[]").rstrip(".").lower()
    if not host or host in _RESERVED_LOCAL_NAMES or host.endswith(".localhost"):
        return False
    try:
        ipaddress.ip_address(host.split("%", 1)[0])
    except ValueError:
        return True
    return not _is_internal_ip(host)


async def public_address(url: str) -> bool:
    """http(s) to a name whose every address is public."""
    return await _resolve_public_target(url) is not None


def _host(url: str) -> str:
    try:
        return (urlsplit(url).hostname or "").lower()
    except ValueError:
        return ""


def _on(host: str, domain: str) -> bool:
    return host == domain or host.endswith("." + domain)


def site_name(url: str) -> str:
    host = _host(url)
    for domain, name in _KNOWN_SITES.items():
        if _on(host, domain):
            return name
    return host[4:] if host.startswith("www.") else host


def youtube_id(url: str) -> str:
    try:
        parts = urlsplit(url)
    except ValueError:
        return ""
    host, path = (parts.hostname or "").lower(), parts.path
    ident = ""
    if _on(host, "youtu.be"):
        ident = path.strip("/").split("/")[0]
    elif _on(host, "youtube.com") or _on(host, "youtube-nocookie.com"):
        if path == "/watch":
            ident = (parse_qs(parts.query).get("v") or [""])[0]
        else:
            bits = path.strip("/").split("/")
            if len(bits) >= 2 and bits[0] in ("shorts", "embed", "live", "v"):
                ident = bits[1]
    return ident if _YT_ID.fullmatch(ident) else ""


def bilibili_id(url: str) -> str:
    if not _on(_host(url), "bilibili.com"):
        return ""
    match = _BV.search(urlsplit(url).path)
    return match.group(1) if match else ""


def player_for(url: str) -> str:
    """The embeddable player of a YouTube or Bilibili video page, else ""."""
    ident = youtube_id(url)
    if ident:
        return f"https://www.youtube-nocookie.com/embed/{ident}"
    ident = bilibili_id(url)
    if ident:
        return f"https://player.bilibili.com/player.html?bvid={ident}&autoplay=0"
    return ""


def allowed_player(url: str) -> str:
    """`url` when it is an https player on the list, a YouTube embed made cookieless; else ""."""
    try:
        parts = urlsplit(url)
    except ValueError:
        return ""
    if parts.scheme != "https":
        return ""
    host = (parts.hostname or "").lower()
    if _on(host, "youtube.com") or _on(host, "youtube-nocookie.com"):
        return player_for(url)
    return url if host in PLAYER_HOSTS else ""


# ---------------------------------------------------------------- facts

def _text(value: Any, limit: int = 300) -> str:
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        return ""
    return " ".join(html.unescape(str(value)).split())[:limit]


def _person(value: Any) -> str:
    if isinstance(value, list):
        value = value[0] if value else ""
    if isinstance(value, dict):
        value = value.get("name")
    name = _text(value, 120)
    return "" if name.startswith(("http://", "https://")) else name


def _image(value: Any) -> str:
    if isinstance(value, list):
        value = value[0] if value else ""
    if isinstance(value, dict):
        value = value.get("url") or value.get("contentUrl")
    return _text(value, 2000)


def _seconds(value: Any) -> Optional[int]:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value) if 0 < value < 360_000 else None
    text = str(value or "").strip()
    if text.isdigit():
        return _seconds(int(text))
    match = _ISO_DURATION.fullmatch(text)
    if not match or not any(match.groups()):
        return None
    days, hours, minutes, seconds = (float(g) if g else 0.0 for g in match.groups())
    return _seconds(int(days * 86400 + hours * 3600 + minutes * 60 + seconds))


def _ld_objects(blobs: Any) -> list[dict]:
    found: list[dict] = []
    for blob in (blobs if isinstance(blobs, list) else [])[:10]:
        try:
            queue = [json.loads(blob)] if isinstance(blob, str) else []
        except ValueError:
            continue
        while queue and len(found) < 50:
            value = queue.pop(0)
            if isinstance(value, list):
                queue.extend(value[:20])
            elif isinstance(value, dict):
                found.append(value)
                if isinstance(value.get("@graph"), list):
                    queue.extend(value["@graph"][:30])
    return found


def _types(obj: dict) -> set[str]:
    kind = obj.get("@type")
    return {str(k) for k in (kind if isinstance(kind, list) else [kind]) if isinstance(k, str)}


def _absolute(base: str, address: str) -> str:
    if not address:
        return ""
    url = urljoin(base, address.strip())
    return url if urlsplit(url).scheme in ("http", "https") else ""


def facts_from(data: Any, url: str) -> dict:
    """Item fields from what `_FACTS` read off a page; every value checked, as the page wrote it."""
    data = data if isinstance(data, dict) else {}
    meta: dict[str, str] = {}
    for row in data.get("meta") if isinstance(data.get("meta"), list) else []:
        if isinstance(row, list) and len(row) == 2 and isinstance(row[0], str) and isinstance(row[1], str):
            meta.setdefault(row[0], row[1])
    objects = _ld_objects(data.get("ld"))
    main = (next((o for o in objects if _types(o) & _VIDEO_TYPES), None)
            or next((o for o in objects if _types(o) & _ARTICLE_TYPES), None)
            or next((o for o in objects if _types(o) & _POST_TYPES), None) or {})
    kinds = _types(main)
    bili = data.get("bili") if isinstance(data.get("bili"), dict) else {}
    yt = data.get("yt") if isinstance(data.get("yt"), dict) else {}

    def first(*values: Any, limit: int = 300) -> str:
        return next((t for t in (_text(v, limit) for v in values) if t), "")

    published =first(main.get("datePublished"), main.get("uploadDate"), meta.get("article:published_time"),
                      meta.get("datepublished"), meta.get("uploaddate"), yt.get("publishDate"), limit=40)
    if not published and isinstance(bili.get("pubdate"), int) and bili["pubdate"] > 0:
        published = datetime.fromtimestamp(bili["pubdate"], timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    pictures = [meta.get("og:image:secure_url"), meta.get("og:image"), meta.get("twitter:image"),
                _image(main.get("thumbnailUrl")), _image(main.get("image")), bili.get("pic"), yt.get("thumbnail")]
    picture = next((p for p in (_absolute(url, _text(v, 2000)) for v in pictures)
                    if p and len(p) <= 2000), "")
    embed = player_for(url) or player_for(_text(data.get("canonical"), 2000))
    if yt.get("embeddable") is False:
        embed = ""
    elif not embed:
        for declared in (meta.get("og:video:secure_url"), meta.get("og:video:url"), meta.get("og:video"),
                         meta.get("twitter:player"), main.get("embedUrl")):
            embed = allowed_player(_absolute(url, _text(declared, 2000)))
            if embed:
                break
    length = (_seconds(main.get("duration")) or _seconds(meta.get("og:video:duration"))
              or _seconds(meta.get("video:duration")) or _seconds(meta.get("duration"))
              or _seconds(bili.get("duration")) or _seconds(yt.get("lengthSeconds")))
    text = str(data.get("text") or "") if isinstance(data.get("text"), str) else ""
    text = "\n".join(" ".join(line.split()) for line in text.splitlines()).strip()
    text = re.sub(r"\n{3,}", "\n\n", text)[:TEXT_MAX]
    og_type = meta.get("og:type", "").lower()
    if embed or kinds & _VIDEO_TYPES or og_type.startswith("video") or yt or bili:
        kind = "video"
    elif kinds & _ARTICLE_TYPES or og_type == "article":
        kind = "article"
    elif kinds & _POST_TYPES:
        kind = "post"
    else:
        kind = "article" if len(text) >= 1500 else "page"
    free = main.get("isAccessibleForFree")
    if kind == "video":
        # A video page's text is its surroundings; its words are in the description.
        text = ""
    known = site_name(url) if any(_on(_host(url), d) for d in _KNOWN_SITES) else ""
    return {
        "title": first(bili.get("title"), yt.get("title"), meta.get("og:title"), meta.get("twitter:title"),
                       main.get("headline"), main.get("name"), data.get("title")),
        "site": known or first(meta.get("og:site_name"), meta.get("application-name"), limit=80) or site_name(url),
        "author": _person(main.get("author")) or first(meta.get("author"), bili.get("owner"), yt.get("author"),
                                                       limit=120),
        "published": published,
        "length": length,
        # A video site's own description first: its meta tags carry counts and links to other videos.
        "description": first(bili.get("desc") if bili.get("desc") != "-" else "", yt.get("shortDescription"),
                             meta.get("og:description"), meta.get("twitter:description"), meta.get("description"),
                             main.get("description"), limit=DESCRIPTION_MAX),
        "picture": picture,
        "embed": embed,
        "text": text,
        "kind": kind,
        "paywall": free is False or str(free).lower() == "false",
    }


def wall_of(data: Any, url: str, facts: dict) -> str:
    """Why this page is not for a visitor: "verification", "sign_in", "paywall" or ""."""
    found = visits.wall_at(url)
    if found:
        return found
    sign = (data.get("wall") if isinstance(data, dict) else None) or {}
    title = str(data.get("title") or "").lower() if isinstance(data, dict) else ""
    if sign.get("captcha") is True or title.startswith(("just a moment", "attention required")):
        return "verification"
    yt = data.get("yt") if isinstance(data, dict) and isinstance(data.get("yt"), dict) else {}
    # YouTube's player asks a visitor it doubts to sign in "to confirm you are not a bot".
    if yt.get("status") == "LOGIN_REQUIRED":
        return "verification"
    if yt.get("status") in ("AGE_CHECK_REQUIRED", "CONTENT_CHECK_REQUIRED"):
        return "sign_in"
    if facts.get("paywall"):
        return "paywall"
    words = sign.get("words") if isinstance(sign.get("words"), int) else 0
    if sign.get("password") is True and not facts.get("title") and words < 800:
        return "sign_in"
    return ""


def small_picture(data: bytes) -> bytes:
    """A JPEG of the picture fitting PICTURE_SIDE and under the library's size limit, or b""."""
    try:
        from PIL import Image
    except ImportError:
        return b""
    try:
        with Image.open(io.BytesIO(data)) as source:
            if source.width * source.height > MAX_IMAGE_PIXELS:
                return b""
            source.draft("RGB", (PICTURE_SIDE * 2, PICTURE_SIDE * 2))
            picture = source.convert("RGB")
        picture.thumbnail((PICTURE_SIDE, PICTURE_SIDE))
        for quality in (82, 70, 55):
            out = io.BytesIO()
            picture.save(out, "JPEG", quality=quality, optimize=True)
            if out.tell() <= PICTURE_MAX_BYTES:
                return out.getvalue()
    except Exception:
        return b""
    return b""


# ---------------------------------------------------------------- the browser

class Visitor:
    """One headless browser on a profile that is never signed in, started when
    a page is wanted and stopped when none has been for a while."""

    def __init__(self, profile: Path, *, executable: Optional[Path] = None,
                 host_check: Callable[[str], bool] = host_ok,
                 public: Callable[[str], Awaitable[bool]] = public_address, clock: Callable[[], float] = time.monotonic):
        self.browser = web.Browser(profile, executable=executable, headless=True)
        self.host_check = host_check
        self.public = public
        self.clock = clock
        self.lock = asyncio.Lock()
        self.used = 0.0
        self.context: Any = None

    def _allowed(self, url: str) -> bool:
        parts = urlsplit(url)
        return parts.scheme in ("http", "https") and self.host_check(parts.hostname or "")

    async def _guard(self, route: Any) -> None:
        if self._allowed(route.request.url):
            await route.continue_()
        else:
            await route.abort("blockedbyclient")

    async def _watch(self, page: Any) -> None:
        """Check every request of `page`, each redirect hop included, which the
        route above is not shown; a page's own address is resolved too."""
        session = await page.context.new_cdp_session(page)
        pending: set = set()

        async def paused(event: dict) -> None:
            url, ident = str(event.get("request", {}).get("url", "")), event.get("requestId")
            try:
                if self._allowed(url) and (event.get("resourceType") != "Document" or await self.public(url)):
                    await session.send("Fetch.continueRequest", {"requestId": ident})
                else:
                    logger.info("roam: a request to %s was refused", urlsplit(url).hostname or "?")
                    await session.send("Fetch.failRequest", {"requestId": ident, "errorReason": "BlockedByClient"})
            except Exception:
                pass

        def heard(event: dict) -> None:
            task = asyncio.ensure_future(paused(event))
            pending.add(task)
            task.add_done_callback(pending.discard)
        session.on("Fetch.requestPaused", heard)
        await session.send("Fetch.enable", {"patterns": [{"urlPattern": "*", "requestStage": "Request"}]})

    async def _open(self) -> Any:
        if self.context is None:
            context = await self.browser.start()
            try:
                await context.route("**/*", self._guard)
                session = await context.browser.new_browser_cdp_session()
                await session.send("Browser.setDownloadBehavior", {"behavior": "deny"})
            except BaseException:
                await self.browser.stop()
                raise
            self.context = context
        return self.context

    @contextlib.asynccontextmanager
    async def page(self):
        """A fresh tab, the only one in use, closed after."""
        async with self.lock:
            context = await self._open()
            page = await context.new_page()
            try:
                await self._watch(page)
                yield page
            finally:
                self.used = self.clock()
                with contextlib.suppress(Exception):
                    await page.close()

    async def stop_if_idle(self) -> None:
        if self.context is not None and not self.lock.locked() and self.clock() - self.used >= IDLE_S:
            async with self.lock:
                await self.stop()

    async def stop(self) -> None:
        self.context = None
        await self.browser.stop()


@dataclass
class _Read:
    item: Item
    picture: bytes = b""


@dataclass
class _Plan:
    sources: list = field(default_factory=list)     # (site, name, words)
    topic: str = ""


# ---------------------------------------------------------------- the walk

class Roam:
    """The walk loop and the reader the rest of the service uses."""

    def __init__(self, agent: Any, *, home: Path, runtime: Path, executable: Optional[Path] = None,
                 clock: Callable[[], float] = time.time, public: Callable[[str], Awaitable[bool]] = public_address,
                 host_check: Callable[[str], bool] = host_ok, bases: Optional[dict] = None):
        self.agent = agent
        self.settings = agent.settings
        self.library = Library(runtime)
        self.clock = clock
        self.public = public
        self.host_check = host_check
        self.executable = executable
        self.visitor = Visitor(web.profile_path(home, "visitor"), executable=executable, host_check=host_check,
                               public=public)
        self.bases = {"bilibili": visits.BILIBILI, "bilibili_search": visits.BILIBILI_SEARCH,
                      "youtube": visits.YOUTUBE, **(bases or {})}
        self.state_path = Path(runtime) / "roam.json"
        self.started = clock()
        self.pause = (3.0, 8.0)
        self.settle_s = SETTLE_S
        self._requested = False
        self._walking = False
        self._topics: list[str] = []
        if self.library.outing().state == "out":
            # A walk the service was stopped in the middle of has ended.
            self.library.returned(0, now=self.started)

    # -- what the life line asks

    def available(self) -> str:
        if importlib.util.find_spec("playwright") is None:
            return web.NO_DRIVER
        if (self.executable or web.find_browser()) is None:
            return web.NO_BROWSER
        if not getattr(self.agent, "enabled", False):
            return NO_MODEL
        return ""

    def _asleep(self, now: float) -> bool:
        hour = datetime.fromtimestamp(now, timezone(timedelta(hours=_env_tz_offset()))).hour
        if SLEEP_HOUR_START <= SLEEP_HOUR_END:
            return SLEEP_HOUR_START <= hour < SLEEP_HOUR_END
        return hour >= SLEEP_HOUR_START or hour < SLEEP_HOUR_END

    def _walks_today(self, now: float) -> int:
        outing = self.library.outing()
        return outing.today if outing.day == time.strftime("%Y-%m-%d", time.localtime(now)) else 0

    def _held(self, now: float) -> str:
        code = self.available()
        if code:
            return code
        if not self.settings.roam_enabled:
            return OFF
        if self._walking or self.library.outing().state == "out":
            return OUT
        if self._asleep(now):
            return ASLEEP
        if self._walks_today(now) >= self.settings.roam_walks_a_day:
            return LIMIT
        return ""

    def can_go_out(self, now: Optional[float] = None) -> tuple[bool, str]:
        """Whether the owner may send it out now, and if not, why."""
        now = self.clock() if now is None else now
        code = self._held(now)
        if not code and now - self.library.outing().last_end < REQUEST_GAP_S:
            code = RECENT
        return not code, code

    def request(self) -> None:
        """Go at the next tick, sooner than the walks' own spacing allows."""
        self._requested = True

    def _due(self, now: float) -> bool:
        if self._held(now):
            return False
        last = self.library.outing().last_end
        if self._requested:
            return now - last >= REQUEST_GAP_S
        return now - self.started >= FIRST_WALK_S and now - last >= self.settings.roam_gap_h * 3600

    async def loop(self) -> None:
        code = self.available()
        if code or not self.settings.roam_enabled:
            logger.info("roam: walks are off (%s)", code or OFF)
        try:
            while True:
                await asyncio.sleep(TICK_S)
                try:
                    await self.tick()
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    logger.warning("roam: a walk failed (%s)", type(exc).__name__)
        finally:
            await self.visitor.stop()

    async def tick(self, now: Optional[float] = None) -> int:
        """One look at the clock: a walk when one is due. Returns what it kept, or -1 when it stayed in."""
        now = self.clock() if now is None else now
        await self.visitor.stop_if_idle()
        if not self._due(now):
            return -1
        self._requested = False
        return await self.walk(now)

    # -- the day's page counts, per site

    def _counts(self, now: float) -> dict:
        day = time.strftime("%Y-%m-%d", time.localtime(now))
        try:
            saved = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            saved = {}
        if not isinstance(saved, dict) or saved.get("day") != day or not isinstance(saved.get("sites"), dict):
            saved = {"day": day, "sites": {}}
        return saved

    def _may_visit(self, site: str, now: float) -> bool:
        return int(self._counts(now)["sites"].get(site, 0)) < self.settings.roam_site_pages_a_day

    def _count_page(self, site: str, now: float) -> None:
        counts = self._counts(now)
        counts["sites"][site] = int(counts["sites"].get(site, 0)) + 1
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_text(self.state_path, json.dumps(counts, ensure_ascii=False))
        except OSError:
            pass

    # -- reading one page

    async def read(self, url: str) -> Optional[Item]:
        """`url` read as a visitor into an Item (not yet in the library), its
        cover saved; None when it cannot or may not be read."""
        found = await self._read(url)
        if found is None:
            return None
        if found.picture:
            found.item.picture = self.library.save_picture(found.item.id, found.picture)
        return found.item

    async def _read(self, url: str) -> Optional[_Read]:
        url = str(url or "").strip()
        if len(url) > 4096 or urlsplit(url).scheme not in ("http", "https"):
            return None
        if not await self.public(url):
            logger.info("roam: %s is not a public address; not read", _host(url) or "?")
            return None
        async with self.visitor.page() as page:
            try:
                response = await page.goto(url, wait_until="domcontentloaded", timeout=OPEN_MS)
            except Exception as exc:
                logger.info("roam: %s did not open (%s)", _host(url), type(exc).__name__)
                return None
            kind = (response.headers.get("content-type", "") if response is not None else "").lower()
            if response is None or response.status >= 400 or "html" not in kind:
                logger.info("roam: %s answered %s", _host(url), response.status if response else "nothing")
                return None
            final = page.url
            if not await self.public(final):
                return None
            await asyncio.sleep(self.settle_s)
            try:
                data = await page.evaluate(_FACTS)
            except Exception:
                return None
            facts = facts_from(data, final)
            wall = wall_of(data, final, facts)
            if wall:
                logger.info("roam: %s shows a %s wall to visitors; the page is left", _host(final), wall)
                return None
            picture = await self._picture(page, facts["picture"], final)
        if not facts["title"]:
            return None
        item = Item(url=final, site=facts["site"], kind=facts["kind"], title=facts["title"],
                    author=facts["author"], published=facts["published"], length=facts["length"],
                    description=facts["description"], text=facts["text"], embed=facts["embed"])
        item.id = item_id(item.url)
        return _Read(item, picture)

    async def _picture(self, page: Any, address: str, referer: str) -> bytes:
        if not address or not self.host_check(_host(address)):
            return b""
        try:
            # Opened in the same tab, so the browser's own network and the guards above apply.
            response = await page.goto(address, referer=referer, timeout=10_000)
            if (response is None or not response.ok
                    or not response.headers.get("content-type", "").lower().startswith("image/")
                    or int(response.headers.get("content-length") or 0) > PICTURE_FETCH_MAX):
                return b""
            body = await response.body()
        except Exception:
            return b""
        return small_picture(body) if len(body) <= PICTURE_FETCH_MAX else b""

    # -- where to go

    def _owner_notes(self) -> list[str]:
        """What it remembers about its owner, newest first; never anyone else."""
        memories = getattr(self.agent, "memories", None)
        if not isinstance(memories, dict):
            return []
        operator = people.operator_ids(getattr(self.agent, "admin_ids", ()) or (), memories)
        rows = []
        for key, notes in memories.items():
            in_dm = people.is_operator_dm(str(key), operator)
            for note in notes if isinstance(notes, list) else []:
                if not isinstance(note, dict) or not isinstance(note.get("text"), str):
                    continue
                about = str(note.get("user_id") or "")
                if about in operator or (in_dm and not about):
                    rows.append((float(note.get("time") or note.get("born") or 0), note["text"].strip()))
        rows.sort(reverse=True)
        return [text for _, text in rows if text][:40]

    def _topic(self, notes: list[str]) -> str:
        """An interest named in a note, as a few search words, never the note itself."""
        found = []
        for note in notes:
            for pattern in (_INTEREST_ZH, _INTEREST_EN):
                match = pattern.search(note)
                if match:
                    words = re.split(r"[,.;!?，。；！？]", match.group(1))[0].strip(" '")
                    if len(words) >= 2 and not any(ch.isdigit() for ch in words) and words not in self._topics:
                        found.append(words)
        if not found:
            return ""
        topic = random.choice(found[:10])
        self._topics = (self._topics + [topic])[-5:]
        return topic

    def _plan(self) -> _Plan:
        lang = "zh" if str(getattr(self.agent, "agent_lang", "en")) == "zh" else "en"
        topic = self._topic(self._owner_notes())
        if topic:
            searches = [("Bilibili", "bilibili_search", topic), ("YouTube", "youtube_search", topic)]
            return _Plan(searches if lang == "zh" else searches[::-1], topic)
        return _Plan([("Bilibili", "bilibili_hot", ""),
                      ("YouTube", "youtube_search", random.choice(_GENERAL[lang]))])

    async def _list(self, name: str, words: str) -> list[visits.Found]:
        async with self.visitor.page() as page:
            try:
                if name == "bilibili_hot":
                    found, wall = await visits.bilibili_hot(page, base=self.bases["bilibili"])
                elif name == "bilibili_search":
                    found, wall = await visits.bilibili_search(page, words, base=self.bases["bilibili_search"],
                                                               video_base=self.bases["bilibili"])
                else:
                    found, wall = await visits.youtube_search(page, words, base=self.bases["youtube"])
            except Exception as exc:
                logger.info("roam: the list %s did not open (%s)", name, type(exc).__name__)
                return []
        if wall:
            logger.info("roam: %s shows a %s wall to visitors; nothing is read there", name, wall)
        return found

    # -- the walk itself

    async def walk(self, now: Optional[float] = None) -> int:
        """Go out, read a few pages, keep what is worth keeping. Returns how many were kept."""
        now = self.clock() if now is None else now
        self._walking = True
        outing = uuid.uuid4().hex[:12]
        plan = self._plan()
        sites: list[str] = []
        kept = 0
        self.library.left(plan.sources[0][0] if plan.sources else "", now=now)
        try:
            lists: list[list[visits.Found]] = []
            for site, name, words in plan.sources:
                if not self._may_visit(site, now):
                    continue
                found = await self._list(name, words)
                self._count_page(site, now)
                if found:
                    # Only a site that let it in counts as one it has been to.
                    self.library.at(site)
                lists.append(found)
                await self._rest()
            if plan.topic and not any(lists) and self._may_visit("Bilibili", now):
                lists.append(await self._list("bilibili_hot", ""))
                self._count_page("Bilibili", now)
            wanted = random.randint(3, max(3, self.settings.roam_pages))
            read: list[_Read] = []
            for found in _interleave(lists):
                if len(read) >= wanted:
                    break
                if self.library.seen(found.url) or not self._may_visit(found.site, now):
                    continue
                self.library.at(found.site)
                self._count_page(found.site, now)
                page = await self._read(found.url)
                if page is not None:
                    read.append(page)
                    if found.site not in sites:
                        sites.append(found.site)
                await self._rest()
            for index, why, fits in await self._choose(read):
                chosen = read[index]
                chosen.item.outing, chosen.item.why, chosen.item.fits = outing, why, fits
                chosen.item.seen_at = int(now)
                if chosen.picture:
                    chosen.item.picture = self.library.save_picture(chosen.item.id, chosen.picture)
                self.library.add(chosen.item)
                kept += 1
            logger.info("roam: back from a walk, read %d pages, kept %d", len(read), kept)
        finally:
            self._walking = False
            self.library.returned(kept, sites, now=self.clock())
        return kept

    async def _rest(self) -> None:
        await asyncio.sleep(random.uniform(*self.pause))

    async def _choose(self, read: list[_Read]) -> list[tuple[int, str, bool]]:
        """Which pages to keep, why, and whether each fits the owner, asked of the model once."""
        if not read:
            return []
        try:
            system, user = self._prompt(read)
            with purpose("roam"):
                answer = await self.agent._call_llm(system, [{"role": "user", "content": user}], self.agent.model,
                                                    max_tokens=600, enable_search=False, disable_thinking=True,
                                                    temperature=0.4, json_object=True)
            chosen = parse_choice(answer, len(read))
        except Exception as exc:
            logger.warning("roam: the model did not choose (%s)", type(exc).__name__)
            chosen = None
        if chosen is None:
            return [(n, "", n == 0) for n in range(min(KEEP_MAX, len(read)))]
        return chosen

    def _prompt(self, read: list[_Read]) -> tuple[str, str]:
        from .langs import NAMES
        lang = str(getattr(self.agent, "chat_lang", "") or getattr(self.agent, "agent_lang", "en"))
        name = str(getattr(self.agent, "persona_name", "") or "")
        persona = str(getattr(self.agent, "persona", "") or "")[:1500]
        system = (
            f"You are {name or 'the character described below'}.\n{persona}\n\n"
            "You have just been out on the web as a visitor and read the pages listed below. Choose at most "
            f"{KEEP_MAX} worth keeping. For each, write one sentence in {NAMES.get(lang, lang)}, in your own "
            "voice, on why you stopped there, and say whether it fits your owner, judged by what you know about "
            "them. Answer with JSON only: "
            '{"keep": [{"n": <page number>, "why": "<one sentence>", "fits": true or false}]}. '
            "An empty list is allowed.\n\n" + _UNTRUSTED_INPUT_RULES)
        notes = self._owner_notes()[:15]
        pages = []
        for number, page in enumerate(read, 1):
            item = page.item
            excerpt = " ".join((item.description or item.text).split())[:PROMPT_EXCERPT]
            pages.append(f"{number}. [{item.kind}] {item.title}\nsite: {item.site}\nauthor: {item.author or '-'}\n"
                         f"{excerpt}")
        user = ("What you know about your owner:\n"
                + (_fence_user_data("\n".join(f"- {n}" for n in notes)) if notes else "(nothing yet)")
                + "\n\nThe pages:\n" + fence_pages("\n\n".join(pages)))
        return system, user


def fence_pages(text: str) -> str:
    """Pages' words as external material their content cannot close."""
    cleaned = html.escape(_clean_prompt_source(text), quote=False)
    return f"{_WEB_DESC_OPEN}[external_web_pages]\n{cleaned}\n[/external_web_pages]{_WEB_DESC_CLOSE}"


def parse_choice(answer: Any, count: int) -> Optional[list[tuple[int, str, bool]]]:
    """[(page index, why, fits)] from the model's answer, or None when it is not exactly the asked form."""
    try:
        value = json.loads(strip_json_fences(str(answer or "")))
    except ValueError:
        return None
    keep = value.get("keep") if isinstance(value, dict) else None
    if not isinstance(keep, list) or len(keep) > KEEP_MAX:
        return None
    chosen, seen = [], set()
    for row in keep:
        if not isinstance(row, dict):
            return None
        number, why, fits = row.get("n"), row.get("why"), row.get("fits")
        if (isinstance(number, bool) or not isinstance(number, int) or not 1 <= number <= count
                or number in seen or not isinstance(why, str) or not isinstance(fits, bool)):
            return None
        why = " ".join(why.split())
        if not why or len(why) > WHY_MAX:
            return None
        seen.add(number)
        chosen.append((number - 1, why, fits))
    return chosen


def _interleave(lists: list[list[visits.Found]]) -> list[visits.Found]:
    """One from each list in turn, each address once."""
    out, seen = [], set()
    for row in range(max((len(x) for x in lists), default=0)):
        for found in lists:
            if row < len(found) and found[row].url not in seen:
                seen.add(found[row].url)
                out.append(found[row])
    return out
