"""Content understanding: what the bot can actually see.

Links, share cards, bilibili/YouTube metadata, images, OCR and sticker
aesthetics. All network egress here goes through the SSRF guard
(_safe_get / _host_is_internal) — third-party URLs are untrusted input."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import heapq
import io
import ipaddress
import json
import logging
import os
import random
import re
import socket
import time
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path
from typing import Awaitable, Callable, Optional
from urllib.parse import urlencode, urlsplit

import httpx

from .gateway import current_sink
from .textproc import _detect_image_mime

logger = logging.getLogger("agent")

# Hard ceiling on any image the bot will decode or forward. Bounds both
# memory and what a hostile URL can push through the vision path.
try:
    MAX_IMAGE_BYTES = max(1, int(os.getenv("MAX_IMAGE_BYTES", "5000000")))
except ValueError:
    MAX_IMAGE_BYTES = 5_000_000




class ContentIngestion:
    """Mixed into Agent; see agent.py."""

    async def _fetch_image_bytes(self, url: str) -> bytes | None:
        """Fetch image bytes. Handles base64:// (inline data from a gateway
        b64-only image segment), file:// (local read for NapCat local-cache
        mode) and http(s) (httpx)."""
        if not url:
            return None
        if url.startswith("base64://"):
            # synthesize_onebot_payload emits a base64:// file field when the
            # forwarder had no URL — the bytes are inline, nothing to fetch.
            encoded = url[len("base64://"):]
            max_encoded = ((MAX_IMAGE_BYTES + 2) // 3) * 4 + 4
            if len(encoded) > max_encoded:
                logger.warning("[Agent] base64 image exceeds size limit")
                return None
            try:
                data = base64.b64decode(encoded, validate=True)
            except Exception as e:
                logger.debug("[Agent] base64 image decode failed: %s", e)
                return None
            if len(data) > MAX_IMAGE_BYTES or not _detect_image_mime(data):
                return None
            return data
        if url.startswith("file://"):
            from urllib.parse import urlparse, unquote
            parsed = urlparse(url)
            local = unquote(parsed.path)
            if len(local) > 3 and local[0] == "/" and local[2] == ":":
                local = local[1:]
            try:
                path = Path(local).resolve()
            except Exception:
                return None
            allowed = os.getenv("NAPCAT_IMAGE_DIR", "").strip()
            if not allowed:
                logger.warning("[Agent] refusing file:// because NAPCAT_IMAGE_DIR is unset")
                return None
            try:
                allowed_path = Path(allowed).resolve(strict=True)
                if not path.is_relative_to(allowed_path):
                    logger.warning("[Agent] refusing file:// outside NAPCAT_IMAGE_DIR: %s", path)
                    return None
                stat = path.stat()
                if not path.is_file() or stat.st_size > MAX_IMAGE_BYTES:
                    return None
            except (OSError, ValueError):
                return None
            try:
                with path.open("rb") as fh:
                    data = fh.read(MAX_IMAGE_BYTES + 1)
            except Exception as e:
                logger.debug("[Agent] file:// read failed (%s): %s", local, e)
                return None
            if len(data) > MAX_IMAGE_BYTES or not _detect_image_mime(data):
                return None
            return data
        # SSRF guard: an image-segment URL can point at internal endpoints
        # (169.254.169.254 IMDS, RFC1918) and the fetched bytes get shipped to
        # the vision provider / sticker library. _safe_get re-checks every
        # redirect hop, so a public URL 302-ing to an internal address is
        # blocked too — this fetcher doesn't go through _should_skip_url.
        try:
            return await self._safe_get_bytes(
                url, timeout=15, headers={"User-Agent": "Mozilla/5.0"},
                max_bytes=MAX_IMAGE_BYTES)
        except Exception as e:
            logger.debug("[Agent] http fetch failed (%s): %s", url, e)
            return None

    async def _steal_image_async(
        self,
        url: str,
        sender_uid: str,
        group_id: str,
    ) -> None:
        """Background download + steal + maybe-tag. Fire-and-forget."""
        try:
            img_bytes = await self._fetch_image_bytes(url)
            if not img_bytes:
                return
            ctx_lines = self._sticker_context_lines(group_id)
            md5 = await self.stickers.steal(
                image_bytes=img_bytes,
                url=url,
                src_user=sender_uid,
                src_group=group_id,
                context_before=ctx_lines,
            )
            if md5:
                await self.stickers.maybe_tag(md5)
        except Exception as e:
            logger.debug("[Agent] steal failed: %s: %s",
                         type(e).__name__, str(e) or "(no message)")

    async def _record_sticker_context(self, md5: str, group_id: str, sender_uid: str) -> None:
        """Lightweight: log another context sighting for a known sticker
        (skipping the byte download since md5 already matches the entry)."""
        if not md5 or not group_id:
            return
        entry = self.stickers.lookup_by_md5(md5)
        if not entry:
            return
        filename = self.stickers._md5_index.get(md5)
        if not filename:
            return
        entry["use_count"] = entry.get("use_count", 0) + 1
        ctx = self._sticker_context_lines(group_id)
        self.stickers._append_context(filename, sender_uid, ctx)

    def _sticker_context_lines(self, group_id: str, n: int = 6) -> list[str]:
        """Format the most recent buffer entries as 'name: text' lines for
        sticker context capture. Excludes bot's own messages."""
        buf = list(self.buffers.get(group_id, []))
        out: list[str] = []
        for m in buf[-n:]:
            if not m.get("user_id"):
                continue
            out.append(f"{m.get('name','?')}: {m.get('text','')[:80]}")
        return out

    @staticmethod
    def _format_bili_line(info: dict, title_fallback: str = "") -> str:
        """Build the `[bilibili-video] "title" — by <up>, AI summary/description: ...`
        descriptor fed to the model. Shared by _describe_share and _describe_url
        (the share path passes a title_fallback; the URL path leaves it empty)."""
        title = info.get("title") or title_fallback
        up = info.get("up", "")
        summary = (info.get("summary", "") or "").strip().replace("\n", " ")
        desc = (info.get("desc", "") or "").strip().replace("\n", " ")[:80]
        line = f"[bilibili-video] \"{title}\""
        if up:
            line += f" — by {up}"
        if summary:
            line += f", AI summary: {summary[:200]}"
        elif desc:
            line += f", description: {desc}"
        return line

    async def _describe_share(self, raw_json: str) -> str:
        """Parse an IM mini-app share-card JSON segment into a text line the LLM
        can read. Special-cases Bilibili video shares (resolves shortlink,
        fetches full title/uploader/desc); other shares fall back to
        whatever title+desc the card already carries."""
        try:
            outer = json.loads(raw_json)
        except (TypeError, ValueError, json.JSONDecodeError):
            return ""
        if not isinstance(outer, dict):
            return ""

        # Every field below is sender-controlled and may be any JSON type
        # (int/dict/list where a string is expected). Non-strings are treated
        # as absent — a crafted card must degrade to a thin placeholder, not
        # raise out of here and drop the whole inbound message.
        def _text(v) -> str:
            return v if isinstance(v, str) else ""

        prompt = _text(outer.get("prompt"))
        meta = outer.get("meta") or {}
        if not isinstance(meta, dict):
            meta = {}
        detail = (
            meta.get("detail_1")
            or meta.get("news")
            or meta.get("music")
            or meta.get("video")
            or {}
        )
        if not isinstance(detail, dict):
            return prompt[:80]

        title_field = _text(detail.get("title"))
        desc_field = _text(detail.get("desc"))
        url = (
            _text(detail.get("qqdocurl"))
            or _text(detail.get("jumpUrl"))
            or _text(detail.get("url"))
        )

        is_bili = (
            "哔哩哔哩" in prompt
            or "哔哩哔哩" in title_field
            or "bilibili" in url.lower()
            or "b23.tv" in url.lower()
        )
        if is_bili:
            info = await self._fetch_bili_info(url)
            if info:
                return self._format_bili_line(info, title_fallback=desc_field)
            return f"[bilibili-video] \"{desc_field}\"" if desc_field else "[bilibili-video]"

        # Non-Bilibili mini-app share card: the card's own title/desc fields
        # are usually thin. If the card carries a jumpUrl/qqdocurl, route it
        # through the generic URL describer for richer OG-tag metadata.
        if url:
            url_info = await self._describe_url(url)
            if url_info and url_info != "[link]":
                src = (prompt or "").strip()
                if src and src not in url_info:
                    return f"{src} {url_info}"
                return url_info

        if title_field and desc_field:
            return f"[share|{title_field}] {desc_field[:120]}"
        return f"[share|{title_field or 'unknown'}]"

    async def _fetch_bili_info(self, url: str) -> dict:
        """Resolve b23.tv shortlinks → real URL → BVid; then call Bilibili web
        view API for title/up/desc. Returns {} on any failure so callers can
        gracefully fall back to the share-card's own title/desc."""
        if not url:
            return {}

        if url in self.bili_info_cache:
            return self.bili_info_cache[url]

        real_url = url
        if "b23.tv" in url:
            # SSRF gate: share-card JSON is group-member-controlled, and
            # "contains b23.tv" is not "is a Bilibili shortlink"
            # (http://10.0.0.1/x?b23.tv matches too) — never fetch internal hosts.
            if self._host_is_internal(url):
                logger.warning("[Agent] refusing internal-address b23 url: %s", url)
                self.bili_info_cache[url] = {}
                return {}
            try:
                # _safe_get follows the shortlink redirect manually, refusing
                # any hop that lands on an internal address.
                r = await self._safe_get(url, timeout=5,
                                         headers={"User-Agent": "Mozilla/5.0"})
                if r is not None:
                    real_url = str(r.url)
            except Exception as e:
                logger.debug("[Agent] b23.tv resolve failed (%s): %s", url, e)

        m = re.search(r"BV[a-zA-Z0-9]{10}", real_url)
        if not m:
            self.bili_info_cache[url] = {}
            return {}
        bvid = m.group(0)

        info: dict = {}
        cid: int = 0
        up_mid: int = 0
        try:
            async with self._http(timeout=5) as client:
                r = await client.get(
                    "https://api.bilibili.com/x/web-interface/view",
                    params={"bvid": bvid},
                    headers={"User-Agent": "Mozilla/5.0"},
                )
                r.raise_for_status()
                data = r.json()
                if data.get("code") == 0:
                    d = data.get("data") or {}
                    cid = int(d.get("cid") or 0)
                    up_mid = int((d.get("owner") or {}).get("mid") or 0)
                    info = {
                        "title": (d.get("title") or "")[:80],
                        "up": ((d.get("owner") or {}).get("name") or "")[:30],
                        "desc": (d.get("desc") or "")[:200],
                    }
        except Exception as e:
            logger.debug("[Agent] Bili view API failed (%s): %s", bvid, e)

        if info and cid and up_mid:
            summary = await self._fetch_bili_summary(bvid, cid, up_mid)
            if summary:
                info["summary"] = summary

        self.bili_info_cache[url] = info
        if len(self.bili_info_cache) > 200:
            for k in list(self.bili_info_cache.keys())[:50]:
                self.bili_info_cache.pop(k, None)
        logger.info("[Agent] bili view %s: %s", bvid, (info.get("title") or "(empty)")[:60])
        return info

    async def _fetch_wbi_keys(self) -> tuple[str, str]:
        """Fetch (img_key, sub_key) used to sign WBI requests; cached 24h.
        Returns ('','') on failure — caller should skip WBI-protected calls."""
        now = time.time()
        if self._wbi_keys[0] and now - self._wbi_keys_ts < 86400:
            return self._wbi_keys
        try:
            async with self._http(timeout=5) as client:
                r = await client.get(
                    "https://api.bilibili.com/x/web-interface/nav",
                    headers={"User-Agent": "Mozilla/5.0"},
                )
                data = (r.json().get("data") or {})
                wbi_img = data.get("wbi_img") or {}
                img_url = wbi_img.get("img_url", "") or ""
                sub_url = wbi_img.get("sub_url", "") or ""
                img_key = img_url.rsplit("/", 1)[-1].split(".")[0]
                sub_key = sub_url.rsplit("/", 1)[-1].split(".")[0]
                if img_key and sub_key:
                    self._wbi_keys = (img_key, sub_key)
                    self._wbi_keys_ts = now
                    return self._wbi_keys
        except Exception as e:
            logger.debug("[Agent] WBI keys fetch failed: %s", e)
        return ("", "")

    def _wbi_sign_params(
        self, params: dict, img_key: str, sub_key: str
    ) -> dict:
        """Apply WBI signing: appends wts + w_rid. Returns a new params dict."""
        orig = img_key + sub_key
        mixin = "".join(orig[i] for i in self._WBI_MIXIN_KEY_ENC_TAB if i < len(orig))[:32]
        signed = dict(sorted({**params, "wts": int(time.time())}.items()))
        signed = {
            k: "".join(c for c in str(v) if c not in "!'()*")
            for k, v in signed.items()
        }
        sign = hashlib.md5((urlencode(signed) + mixin).encode()).hexdigest()
        signed["w_rid"] = sign
        return signed

    async def _fetch_bili_summary(self, bvid: str, cid: int, up_mid: int) -> str:
        """Bilibili AI summary via view/conclusion/get. Returns empty string on failure or no summary."""
        img_key, sub_key = await self._fetch_wbi_keys()
        if not img_key or not sub_key:
            return ""
        params = self._wbi_sign_params(
            {"bvid": bvid, "cid": cid, "up_mid": up_mid},
            img_key, sub_key,
        )
        try:
            async with self._http(timeout=8) as client:
                r = await client.get(
                    "https://api.bilibili.com/x/web-interface/view/conclusion/get",
                    params=params,
                    headers={
                        "User-Agent": "Mozilla/5.0",
                        "Referer": f"https://www.bilibili.com/video/{bvid}",
                    },
                )
                r.raise_for_status()
                data = r.json()
                if data.get("code") != 0:
                    logger.debug("[Agent] bili summary %s: code=%s msg=%s",
                                 bvid, data.get("code"), data.get("message"))
                    return ""
                d = data.get("data") or {}
                mr = d.get("model_result") or {}
                if not mr.get("result_type"):
                    return ""
                summary = (mr.get("summary") or "").strip()
                outline = mr.get("outline") or []
                outline_titles: list[str] = []
                for sec in outline[:5]:
                    t = (sec.get("title") or "").strip()
                    if t:
                        outline_titles.append(t[:30])
                line = summary
                if outline_titles:
                    sep = " | outline:" if line else "outline:"
                    line += sep + " / ".join(outline_titles)
                line = line[:300]
                if line:
                    logger.info("[Agent] bili summary %s: %s", bvid, line[:80])
                return line
        except Exception as e:
            logger.debug("[Agent] bili summary failed (%s): %s", bvid, e)
        return ""

    @classmethod
    def _extract_urls(cls, text: str) -> list[str]:
        """Pull http(s) URLs out of text, deduped, order preserved."""
        if not text:
            return []
        urls = []
        seen = set()
        for u in cls.URL_PATTERN.findall(text):
            u = u.rstrip(').,;:!?。，；：！？)』」]>')
            if u in seen:
                continue
            seen.add(u)
            urls.append(u)
        return urls

    @staticmethod
    def _ip_is_internal(ip) -> bool:
        return (ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_reserved or ip.is_multicast or ip.is_unspecified)

    @classmethod
    def _host_is_internal(cls, url: str) -> bool:
        """SSRF guard: True if the URL's host is, or resolves to, an internal
        address — loopback, RFC1918, link-local (incl. the 169.254.169.254
        cloud-metadata endpoint), reserved, or IPv6 equivalents. Resolving the
        hostname also blocks public names that point at internal IPs.
        Redirect hops are re-checked by _safe_get (manual redirect follow)."""
        try:
            host = (urlsplit(url).hostname or "").strip("[]")
        except Exception:
            return True
        if not host:
            return True
        try:
            return cls._ip_is_internal(ipaddress.ip_address(host))
        except ValueError:
            pass  # not an IP literal — resolve the hostname below
        try:
            infos = socket.getaddrinfo(host, None)
        except Exception:
            return False  # can't resolve → let the normal fetch fail
        for info in infos:
            addr = info[4][0].split('%')[0]  # strip IPv6 zone id
            try:
                if cls._ip_is_internal(ipaddress.ip_address(addr)):
                    return True
            except ValueError:
                continue
        return False

    async def _safe_get(self, url: str, *, timeout: float,
                        headers: Optional[dict] = None,
                        max_redirects: int = 5) -> Optional[httpx.Response]:
        """GET with redirects followed manually so EVERY hop is re-checked
        against _host_is_internal. httpx's automatic following would happily
        chase a public URL that 302s to 127.0.0.1 (the protocol API) or
        169.254.169.254 (IMDS) — the initial-URL check alone can't see that.
        Returns the final response, or None if any hop is internal or the
        redirect cap is exceeded."""
        current = url
        for _ in range(max_redirects + 1):
            if self._host_is_internal(current):
                logger.warning("[Agent] refusing internal-address url hop: %s", current[:120])
                return None
            async with self._http(timeout=timeout) as c:
                r = await c.get(current, headers=headers)
            if r.status_code in (301, 302, 303, 307, 308):
                loc = r.headers.get("location", "")
                if not loc:
                    return r
                # Resolve relative Location against the current hop URL
                current = str(httpx.URL(current).join(loc))
                continue
            return r
        logger.warning("[Agent] redirect cap exceeded: %s", url[:120])
        return None

    async def _safe_get_bytes(self, url: str, *, timeout: float,
                              headers: Optional[dict] = None,
                              max_bytes: int,
                              max_redirects: int = 5) -> bytes | None:
        """Stream a bounded HTTP body while validating every redirect hop."""
        current = url
        for _ in range(max_redirects + 1):
            try:
                scheme = urlsplit(current).scheme.lower()
            except Exception:
                return None
            if scheme not in ("http", "https") or self._host_is_internal(current):
                logger.warning("[Agent] refusing internal/invalid image URL hop: %s",
                               current[:120])
                return None
            async with self._http(timeout=timeout) as client:
                async with client.stream(
                    "GET", current, headers=headers, follow_redirects=False,
                ) as response:
                    if response.status_code in (301, 302, 303, 307, 308):
                        location = response.headers.get("location", "")
                        if not location:
                            return None
                        current = str(httpx.URL(current).join(location))
                        continue
                    if response.status_code != 200:
                        return None
                    length = response.headers.get("content-length", "")
                    try:
                        if length and int(length) > max_bytes:
                            return None
                    except (TypeError, ValueError):
                        pass
                    chunks: list[bytes] = []
                    size = 0
                    async for chunk in response.aiter_bytes():
                        size += len(chunk)
                        if size > max_bytes:
                            return None
                        chunks.append(chunk)
                    data = b"".join(chunks)
                    return data if _detect_image_mime(data) else None
        logger.warning("[Agent] image redirect cap exceeded: %s", url[:120])
        return None

    @classmethod
    def _should_skip_url(cls, url: str) -> bool:
        u = url.lower()
        if any(u.split('?')[0].endswith(ext) for ext in cls._URL_SKIP_EXT):
            return True
        return cls._host_is_internal(url)

    async def _describe_url(self, url: str) -> str:
        """Fetch URL metadata and return a preformatted descriptor like
        `[bilibili-video] ...` / `[YouTube] "title" — author` / `[site] "title" desc`.

        Routing:
          - bilibili.com / b23.tv → reuse _fetch_bili_info (title + uploader + AI summary)
          - youtube.com / youtu.be → oEmbed (no API key required)
          - everything else → generic OG-tag scrape (og:title / og:description /
            og:site_name, falling back to <title>)

        Cache: same URL across the same group only hits the network once.
        Failures return "[link]" as a graceful placeholder so the model knows
        a URL was present without reciting the raw href."""
        if not url or self._should_skip_url(url):
            return ""
        if url in self.url_info_cache:
            return self.url_info_cache[url]
        if len(self.url_info_cache) >= 200:
            try:
                first = next(iter(self.url_info_cache))
                self.url_info_cache.pop(first, None)
            except StopIteration:
                pass

        result = ""
        try:
            host = url.split('//', 1)[-1].split('/', 1)[0].lower()
            if "bilibili.com" in host or "b23.tv" in host:
                info = await self._fetch_bili_info(url)
                if info:
                    result = self._format_bili_line(info)
            elif "youtube.com" in host or "youtu.be" in host:
                result = await self._fetch_oembed_youtube(url)
            else:
                result = await self._fetch_og_meta(url)
        except Exception as e:
            logger.debug("[Agent] _describe_url failed (%s): %s: %s", url, type(e).__name__, e)

        if not result:
            result = "[link]"
        self.url_info_cache[url] = result
        return result

    async def _fetch_oembed_youtube(self, url: str) -> str:
        """YouTube exposes a public oEmbed endpoint with no API key needed."""
        try:
            async with self._http(timeout=5, follow_redirects=True, max_redirects=5) as c:
                r = await c.get(
                    "https://www.youtube.com/oembed",
                    params={"url": url, "format": "json"},
                    headers={"User-Agent": "Mozilla/5.0"},
                )
                if r.status_code != 200:
                    return ""
                data = r.json()
                title = (data.get("title") or "").strip()
                author = (data.get("author_name") or "").strip()
                if title:
                    line = f'[YouTube] "{title}"'
                    if author:
                        line += f" — {author}"
                    return line
        except Exception as e:
            logger.debug("[Agent] youtube oembed failed (%s): %s", url, e)
        return ""

    async def _fetch_og_meta(self, url: str) -> str:
        """Generic Open Graph / Twitter card scraper. GET the first 100KB of
        HTML and pull og:title / og:description / og:site_name (falling back
        to <title>). Returns "" on every failure path so callers can shrug."""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            }
            # _safe_get: redirects re-checked per hop (SSRF via 302 blocked)
            r = await self._safe_get(url, timeout=5, headers=headers)
            if r is None or r.status_code != 200:
                return ""
            # Only read the first 100KB so a huge page can't eat memory.
            html = r.text[:100_000]
        except Exception as e:
            logger.debug("[Agent] OG fetch failed (%s): %s: %s", url, type(e).__name__, e)
            return ""

        t = self._OG_TITLE_PAT.search(html)
        d = self._OG_DESC_PAT.search(html)
        s = self._OG_SITE_PAT.search(html)
        title = (t.group(1) if t else "").strip()
        if not title:
            tt = self._TITLE_TAG_PAT.search(html)
            if tt:
                title = re.sub(r'\s+', ' ', tt.group(1)).strip()[:80]
        desc = (d.group(1) if d else "").strip()
        site = (s.group(1) if s else "").strip()
        if not title and not desc:
            return ""
        import html as _html
        title = _html.unescape(title)[:80]
        desc = _html.unescape(desc).replace("\n", " ")[:120]
        prefix = f"[{site}]" if site else "[link]"
        if title and desc:
            return f"{prefix} \"{title}\" {desc}"
        if title:
            return f"{prefix} \"{title}\""
        return f"{prefix}{desc}"

    @staticmethod
    def _image_cache_key(url: str) -> str:
        """Caption-cache key for an image 'url'. Gateway images with only
        inline bytes arrive as base64://<payload> pseudo-URLs — up to several
        MB each — so keying the cache on the raw string would park megabytes
        of dead base64 per entry. Hash those; real URLs stay as-is."""
        if url.startswith("base64://"):
            return "b64:" + hashlib.md5(url.encode()).hexdigest()
        return url

    def _accept_vision_caption(self, url: str, text: str, provider: str) -> str:
        # Truncated to 150 chars (a long caption is still useful); no longer
        # discard the whole caption for being "too long" — the old >80 reject
        # silently threw away many valid descriptions of complex images.
        text = (text or "").strip()[:150]
        hit = next((t for t in self._VISION_REJECT_TOKENS if t in text), "")
        if text and len(text) >= 4 and not hit:
            self.image_caption_cache[self._image_cache_key(url)] = text
            self._gc_image_cache()
            logger.info("[Agent] vision/%s (%s): %s", provider, url[:60], text[:60])
            return text
        logger.info(
            "[Agent] vision/%s rejected (%s, hit=%r, len=%d): %s",
            provider, url[:60], hit, len(text), text[:80],
        )
        return ""

    @staticmethod
    def _gif_first_frame_png(gif_bytes: bytes) -> bytes:
        """Extract a GIF's first frame as PNG. GLM-4V and many other vision
        endpoints reject GIF directly (error 1210 on Zhipu); the first frame
        as PNG carries enough signal for a caption. Returns empty bytes on
        failure so the caller can fall back to OCR."""
        try:
            from io import BytesIO
            from PIL import Image
            im = Image.open(BytesIO(gif_bytes))
            im.seek(0)
            out = BytesIO()
            im.convert("RGB").save(out, format="PNG")
            return out.getvalue()
        except Exception as e:
            logger.debug("[Agent] GIF→PNG failed: %s: %s", type(e).__name__, e)
            return b""

    async def _judge_sticker_aesthetic(self, img_bytes: bytes) -> bool | None:
        """Ask the vision model if a sticker is visually tacky / off-persona.
        Returns True (tacky → should ban), False (fine), or None on judgment
        failure (read error / API error / unparseable response — entry is
        left untouched). Reuses the GLM-4V infra: MIME detection, first-frame
        for GIF, base64 data URL."""
        try:
            if not img_bytes or len(img_bytes) < 200 or len(img_bytes) > 5_000_000:
                return None
            head = img_bytes[:16]
            if head[:8] == b"\x89PNG\r\n\x1a\n":
                mime = "image/png"
            elif head[:3] == b"\xff\xd8\xff":
                mime = "image/jpeg"
            elif head[:4] == b"GIF8":
                frame = self._gif_first_frame_png(img_bytes)
                if not frame:
                    return None
                img_bytes = frame
                mime = "image/png"
            elif head[:4] == b"RIFF" and head[8:12] == b"WEBP":
                mime = "image/webp"
            else:
                return None
            data_url = f"data:{mime};base64,{base64.b64encode(img_bytes).decode()}"

            # Aggressive backoff: aesthetic recheck is a startup burst, free
            # tiers rate-limit hard. Without retry many judgments return None
            # and the recheck appears to do nothing.
            payload = {
                "model": self.vision_model,
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": self.VISION_AESTHETIC_PROMPT},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }],
                "max_tokens": 60,
                "temperature": 0,
            }
            if "k2" in self.vision_model.lower():
                payload["thinking"] = {"type": "disabled"}
                # K2.6 only accepts temperature=0.6 (single-valued whitelist)
                payload["temperature"] = 0.6
            raw = ""
            async with self._http(timeout=30) as c:
                for attempt in range(4):
                    r = await c.post(
                        f"{self.glm_base_url}/chat/completions",
                        headers={"Authorization": f"Bearer {self.glm_api_key}"},
                        json=payload,
                    )
                    if r.status_code == 429:
                        if attempt == 3:
                            return None
                        await asyncio.sleep(2 ** attempt * 3.0)  # 3s, 6s, 12s
                        continue
                    if r.status_code != 200:
                        return None
                    raw = (r.json().get("choices", [{}])[0]
                                .get("message", {})
                                .get("content", "") or "").strip()
                    break
            raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.MULTILINE).strip()
            data = None
            try:
                data = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                m = re.search(r"\{.*\}", raw, re.S)
                if m:
                    try:
                        data = json.loads(m.group(0))
                    except json.JSONDecodeError:
                        data = None
            if not isinstance(data, dict) or "tacky" not in data:
                return None
            return bool(data.get("tacky"))
        except Exception as e:
            logger.debug("[Agent] sticker aesthetic judge failed: %s: %s",
                         type(e).__name__, e)
            return None

    async def visual_recheck_aesthetic_all(self, limit: int = 200) -> int:
        """Scan tagged stickers and demote visually-tacky ones to
        persona_fit=false. Complements the text-based recheck_persona_fit_all:
        that one only sees meaning/tags (LLM-inferred from usage context and
        oblivious to visual style), so two stickers with the same "smug"
        meaning but wildly different aesthetics (clean meme vs gaudy old
        family-group sticker) both look fit by text alone. This pass looks
        at the pixels.

        Version-gated via _visual_aesthetic_version on each entry. Bump
        VISUAL_AESTHETIC_VERSION to force re-judgment of all entries."""
        todo = [
            (fn, v) for fn, v in self.stickers.entries.items()
            if v.get("auto_tagged")
            and v.get("persona_fit") is not False
            and v.get("_visual_aesthetic_version", 0) < self.VISUAL_AESTHETIC_VERSION
        ][:limit]
        if not todo:
            return 0
        marked = 0
        for fn, v in todo:
            file_path = self.stickers.dir / fn
            if not file_path.exists():
                continue
            try:
                img_bytes = file_path.read_bytes()
            except Exception as e:
                logger.debug("[Agent] aesthetic read failed %s: %s", fn, e)
                continue
            tacky = await self._judge_sticker_aesthetic(img_bytes)
            v["_visual_aesthetic_version"] = self.VISUAL_AESTHETIC_VERSION
            if tacky is True:
                v["persona_fit"] = False
                marked += 1
                logger.info("[stickers] visual-aesthetic ban %s: meaning=%r",
                            fn, v.get("meaning", ""))
            # 5s pacing: free-tier vision rate limits are tight; tighter
            # spacing burns through the quota in seconds and most judgments
            # come back None from 429s.
            await asyncio.sleep(5.0)
        self.stickers._save()
        logger.info("[Agent] visual aesthetic recheck: scanned=%d banned=%d",
                    len(todo), marked)
        return marked

    async def _describe_image_glm(self, url: str) -> str:
        """OpenAI-compatible vision call (the name is historical — it was
        originally written for Zhipu GLM-4V but is now used by any vision
        model that exposes the OpenAI /chat/completions shape with
        image_url). Fetches the image bytes, sends as a base64 data URL —
        raw URLs trigger format errors on some providers; base64 is the
        reliable path."""
        try:
            img_bytes = await self._fetch_image_bytes(url)
            if not img_bytes:
                return ""
            if len(img_bytes) < 200:
                logger.debug("[Agent] GLM image too small (%d bytes), skipping", len(img_bytes))
                return ""
            if len(img_bytes) > MAX_IMAGE_BYTES:
                logger.warning("[Agent] GLM image too large (%d bytes), skipping", len(img_bytes))
                return ""
            mime = _detect_image_mime(img_bytes)
            if not mime:
                logger.debug("[Agent] GLM unknown image magic %s",
                             img_bytes[:12].hex())
                return ""
            if mime == "image/gif":
                # GLM rejects GIFs (error 1210, format/parse). Pull the first
                # frame as PNG so animated stickers/memes still get a caption.
                # PIL decode/transcode is CPU-bound — run it in a thread so it
                # doesn't stall the event loop.
                frame = await asyncio.to_thread(self._gif_first_frame_png, img_bytes)
                if not frame:
                    logger.info("[Agent] GLM skip GIF (first-frame extract failed), fallback to OCR")
                    return ""
                img_bytes = frame
                mime = "image/png"
            elif mime == "image/heic":
                # HEIC/HEIF — GLM doesn't accept this format; let caller fall through to OCR
                logger.info("[Agent] GLM skip HEIC/HEIF, fallback to OCR")
                return ""
            elif mime == "image/avif":
                # AVIF — GLM doesn't accept; OCR fallback
                logger.info("[Agent] GLM skip AVIF, fallback to OCR")
                return ""
            data_url = f"data:{mime};base64,{base64.b64encode(img_bytes).decode()}"

            # 429 backoff retry: free-tier vision endpoints rate-limit
            # aggressively. Each incoming group image goes through here, so
            # without retry many captions silently fall back to OCR.
            payload = {
                "model": self.vision_model,
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": self.VISION_PROMPT},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }],
                "max_tokens": 120,
                "temperature": 0.3,
            }
            # K2-family models are reasoning models — by default they spend
            # the entire max_tokens budget on reasoning_content and leave
            # the actual content empty. Short-caption tasks like this need
            # thinking disabled. Older vision-preview models reject this
            # field with HTTP 400, so gate on the model name.
            if "k2" in self.vision_model.lower():
                payload["thinking"] = {"type": "disabled"}
                # K2.6 only accepts temperature=0.6 (single-valued whitelist)
                payload["temperature"] = 0.6
            async with self._http(timeout=30) as c:
                r = None
                last_exc = None
                # Retry coverage: 429 throttling + 5xx + network timeouts
                # (connect/read) + the occasional 400 image reject (some vision
                # providers 400 even on magic-byte-valid images). The image
                # bytes don't change and a resend is cheap — better than the
                # caption silently falling out and the bot "not seeing" images.
                retryable = {400, 429, 500, 502, 503, 504}
                for attempt in range(3):
                    try:
                        r = await c.post(
                            f"{self.glm_base_url}/chat/completions",
                            headers={"Authorization": f"Bearer {self.glm_api_key}"},
                            json=payload,
                        )
                    except Exception as e:
                        # Connect/read timeouts are the most common transient
                        # failure; previously they fell straight through to the
                        # outer except (no retry) — back off and retry instead.
                        last_exc = e
                        r = None
                        if attempt == 2:
                            break
                        await asyncio.sleep(2 ** attempt)  # 1s, 2s
                        continue
                    if r.status_code not in retryable:
                        break  # 200 success, or a non-retryable error (e.g. 401)
                    if attempt == 2:
                        break  # retries exhausted; the non-200 branch below logs
                    await asyncio.sleep(2 ** attempt)  # 1s, 2s
                if r is None or r.status_code != 200:
                    logger.warning("[Agent] GLM vision HTTP %d: %s (exc=%s)",
                                   r.status_code if r else 0,
                                   (r.text if r else "")[:200], last_exc)
                    return ""
                data = r.json()
                text = (data.get("choices", [{}])[0]
                            .get("message", {})
                            .get("content", "") or "")
                return self._accept_vision_caption(url, text, "glm")
        except Exception as e:
            logger.debug("[Agent] GLM vision failed: %s: %s",
                         type(e).__name__, e)
            return ""

    async def _describe_image(self, url: str) -> str:
        """Vision goes through the OpenAI-compatible endpoint (_describe_image_glm
        is the general OpenAI-compatible path; the name is historical). OCR
        fallback on miss. Filters garbage OCR (too short / single-char fragments)."""
        if not url:
            return ""
        cache_key = self._image_cache_key(url)
        if cache_key in self.image_caption_cache:
            return self.image_caption_cache[cache_key]

        caption = ""
        if self.vision_model and self.glm_api_key and self.glm_base_url:
            # OpenAI-compatible: glm-* / moonshot-* / kimi-* / deepseek-vl-* / qwen-vl-* …
            caption = await self._describe_image_glm(url)
        if caption:
            return caption

        # The OCR fallback is a QQ-path facility: NapCat cannot fetch
        # foreign-platform URLs or base64 pseudo-URLs, so a gateway image
        # would only burn a doomed NapCat call. Skip it while the gateway
        # sink is set.
        if current_sink.get() is not None:
            return ""

        ocr_text = await self._ocr_image(url)
        if ocr_text and len(ocr_text) >= 4:
            tokens = ocr_text.split()
            avg_token_len = sum(len(t) for t in tokens) / max(len(tokens), 1)
            if avg_token_len >= 2:
                return ocr_text
        return ""

    def _gc_image_cache(self) -> None:
        if len(self.image_caption_cache) > 200:
            for k in list(self.image_caption_cache.keys())[:50]:
                self.image_caption_cache.pop(k, None)

    async def _ocr_image(self, url: str) -> str:
        """Call the OneBot /ocr_image endpoint (NapCat etc.) to extract text
        from an image. Returns "" on failure or when no text is detected."""
        if not url:
            return ""
        cache_key = self._image_cache_key(url)
        if cache_key in self.image_caption_cache:
            return self.image_caption_cache[cache_key]
        try:
            async with self._http(timeout=15) as client:
                r = await client.post(
                    f"{self.napcat_api}/ocr_image",
                    json={"image": url},
                )
                r.raise_for_status()
                data = r.json()
                items = data.get("data") or []
                text = " ".join(
                    it.get("text", "") for it in items if it.get("text")
                ).strip()[:120]
        except Exception as e:
            logger.warning("[Agent] NapCat OCR failed (%s): %s: %s",
                           url[:80], type(e).__name__, str(e) or "(no message)")
            return ""
        self.image_caption_cache[cache_key] = text
        self._gc_image_cache()
        logger.info("[Agent] OCR (%s): %s", url[:60], text[:60] or "(no text)")
        return text
