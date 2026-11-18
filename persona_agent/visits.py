"""Lists of videos on sites the character visits, read signed out from what
each site's own page shows or loads: Bilibili's hot list and search, and
YouTube's search. Each returns what it found and, when the site put up a
wall for visitors, the wall's name instead."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote, urljoin, urlsplit

from .direct import browser as web

logger = logging.getLogger("personagent.roam")

BILIBILI = "https://www.bilibili.com"
BILIBILI_SEARCH = "https://search.bilibili.com"
YOUTUBE = "https://www.youtube.com"
LIST_MAX = 20
OPEN_MS = 20_000

_BV = re.compile(r"/video/(BV[0-9A-Za-z]{10})")
_YT_ID = re.compile(r"[A-Za-z0-9_-]{11}")
# Where a site sends a visitor it will not serve.
_WALL_PATHS = ("/login", "/signin", "/sign-in", "/passport", "/sorry/", "/captcha", "/challenge", "/consent")
_WALL_HOSTS = ("passport.", "accounts.", "consent.", "login.")


@dataclass
class Found:
    url: str
    title: str
    site: str


def wall_at(url: str) -> str:
    """"verification" or "sign_in" when `url` is where a site turns visitors away; "" otherwise."""
    try:
        parts = urlsplit(url)
    except ValueError:
        return ""
    host, path = (parts.hostname or "").lower(), parts.path.lower()
    if any(mark in path for mark in ("/sorry/", "/captcha", "/challenge")):
        return "verification"
    if host.startswith(_WALL_HOSTS) or any(path.startswith(mark) for mark in _WALL_PATHS):
        return "sign_in"
    return ""


def _clean(text: Any, limit: int = 200) -> str:
    return " ".join(str(text or "").split())[:limit] if isinstance(text, (str, int, float)) else ""


# Links to videos on the page, each with the best title the card around it gives.
_ANCHORS = """(pattern) => {
  const re = new RegExp(pattern);
  const out = [];
  for (const a of document.querySelectorAll('a[href]')) {
    if (!re.test(a.href)) continue;
    const card = a.closest('[class*="card"], ytd-video-renderer, ytd-rich-item-renderer, li') || a;
    const heading = card.querySelector('h3[title], h3, [title]');
    const title = a.getAttribute('title') || a.getAttribute('aria-label')
      || (heading && (heading.getAttribute('title') || heading.innerText)) || a.innerText || '';
    out.push([a.href, title]);
    if (out.length >= 200) break;
  }
  return out;
}"""


async def _anchors(page: Any, pattern: str) -> list[tuple[str, str]]:
    try:
        rows = await page.evaluate(_ANCHORS, pattern)
    except Exception:
        return []
    return [(str(r[0]), str(r[1])) for r in rows if isinstance(r, list) and len(r) == 2]


async def _wait_for(page: Any, selector: str, seconds: float = 8.0) -> None:
    try:
        await page.wait_for_selector(selector, timeout=int(seconds * 1000), state="attached")
    except Exception:
        pass


def _bilibili_list(pairs, video_base: str) -> list[Found]:
    found: dict[str, Found] = {}
    for href, title in pairs:
        match = _BV.search(href)
        title = _clean(title)
        if match and title and match.group(1) not in found:
            found[match.group(1)] = Found(f"{video_base}/video/{match.group(1)}/", title, "Bilibili")
    return list(found.values())[:LIST_MAX]


async def bilibili_hot(page: Any, *, base: str = BILIBILI) -> tuple[list[Found], str]:
    """The videos on Bilibili's popular page, from the list that page loads."""
    answers = await web.page_data(
        page, "/x/web-interface/popular",
        lambda: page.goto(f"{base}/v/popular/all", wait_until="domcontentloaded", timeout=OPEN_MS), wait_s=10)
    wall = wall_at(page.url)
    if wall:
        return [], wall
    pairs = []
    for answer in answers:
        data = answer.get("data") if isinstance(answer, dict) else None
        for row in (data.get("list") if isinstance(data, dict) else None) or []:
            if isinstance(row, dict) and isinstance(row.get("bvid"), str):
                pairs.append((f"/video/{row['bvid']}", row.get("title")))
    if not pairs:
        await _wait_for(page, 'a[href*="/video/BV"]')
        pairs = await _anchors(page, r"/video/BV[0-9A-Za-z]{10}")
    return _bilibili_list(pairs, base), ""


async def bilibili_search(page: Any, words: str, *, base: str = BILIBILI_SEARCH,
                          video_base: str = BILIBILI) -> tuple[list[Found], str]:
    """The videos Bilibili's search page shows for `words`."""
    await page.goto(f"{base}/all?keyword={quote(words)}", wait_until="domcontentloaded", timeout=OPEN_MS)
    wall = wall_at(page.url)
    if wall:
        return [], wall
    await _wait_for(page, 'a[href*="/video/BV"]')
    return _bilibili_list(await _anchors(page, r"/video/BV[0-9A-Za-z]{10}"), video_base), ""


# The search results the page was drawn from, as the page itself holds them.
_YT_RESULTS = """() => {
  const out = [];
  const walk = (node, depth) => {
    if (!node || typeof node !== 'object' || depth > 40 || out.length >= 60) return;
    if (Array.isArray(node)) { for (const x of node) walk(x, depth + 1); return; }
    const v = node.videoRenderer;
    if (v && typeof v.videoId === 'string') {
      const runs = v.title && v.title.runs;
      const title = Array.isArray(runs) ? runs.map(r => r.text || '').join('') : (v.title && v.title.simpleText) || '';
      out.push([v.videoId, title]);
      return;
    }
    for (const key in node) walk(node[key], depth + 1);
  };
  try { walk(window.ytInitialData, 0); } catch (e) {}
  return out;
}"""


async def youtube_search(page: Any, words: str, *, base: str = YOUTUBE) -> tuple[list[Found], str]:
    """The videos YouTube's search page shows for `words`."""
    await page.goto(f"{base}/results?search_query={quote(words)}", wait_until="domcontentloaded",
                    timeout=OPEN_MS)
    wall = wall_at(page.url)
    if wall:
        return [], wall
    try:
        rows = await page.evaluate(_YT_RESULTS)
    except Exception:
        rows = []
    pairs = [(str(r[0]), str(r[1])) for r in rows if isinstance(r, list) and len(r) == 2]
    if not pairs:
        await _wait_for(page, 'a[href*="/watch?v="]')
        for href, title in await _anchors(page, r"/watch\?v=[A-Za-z0-9_-]{11}"):
            ident = re.search(r"v=([A-Za-z0-9_-]{11})", href)
            if ident:
                pairs.append((ident.group(1), title))
    found: dict[str, Found] = {}
    for ident, title in pairs:
        title = _clean(title)
        if _YT_ID.fullmatch(ident) and title and ident not in found:
            found[ident] = Found(urljoin(base + "/", f"watch?v={ident}"), title, "YouTube")
    return list(found.values())[:LIST_MAX], ""
