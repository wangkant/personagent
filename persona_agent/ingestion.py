"""Content understanding: links, share cards, images, OCR and sticker aesthetics.

All network egress goes through the SSRF guard; third-party URLs are untrusted."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import io
import ipaddress
import json
import logging
import os
import re
import socket
import ssl
import time
import warnings
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode, urlsplit

import httpcore
import httpx
from httpcore._backends.auto import AutoBackend

from .config_env import env_int
from .endpoints import adapt_rejected_payload
from .connector import current_sink
from .textproc import (_detect_image_mime, _truncate_framed, apply_k2_quirks,
                       salvage_json_object, strip_json_fences)

logger = logging.getLogger("agent")

# Hard ceiling on any image the bot decodes or forwards.
VISION_MAX_IMAGE_BYTES = env_int("VISION_MAX_IMAGE_BYTES", 5_000_000, minimum=1)

MAX_URL_LENGTH = 4096
MAX_HTML_WIRE_BYTES = 128 * 1024
MAX_HTML_DECODED_BYTES = 128 * 1024
MAX_IMAGE_PIXELS = 16_000_000
MAX_IMAGE_DIMENSION = 8192

# Internal by definition (RFC 6761/2606), so rejected without a lookup.
_RESERVED_LOCAL_NAMES = frozenset({
    "localhost", "localhost.localdomain",
    "ip6-localhost", "ip6-loopback",
})


@dataclass(frozen=True)
class SafeFetchResult:
    """A bounded body plus the final URL after validated redirects."""

    url: str
    status_code: int
    headers: dict[str, str]
    content: bytes


def _ip_obj_is_internal(ip) -> bool:
    # A mapped address reaches the IPv4 host it names, so judge that host.
    mapped = getattr(ip, "ipv4_mapped", None)
    if mapped is not None:
        ip = mapped
    # `not is_global` catches CGNAT 100.64.0.0/10 (a cloud metadata range no
    # flag below covers); site-local fec0::/10 still reports is_global on 3.11.
    return (not ip.is_global or getattr(ip, "is_site_local", False)
            or ip.is_private or ip.is_loopback or ip.is_link_local
            or ip.is_reserved or ip.is_multicast or ip.is_unspecified)


def _is_internal_ip(value: str) -> bool:
    """Unparsable counts as internal: the SSRF guard fails closed."""
    try:
        ip = ipaddress.ip_address(value.split("%", 1)[0])
    except ValueError:
        return True
    return _ip_obj_is_internal(ip)


def _url_for_log(url: str) -> str:
    """`scheme://host[:port]/…` of a fetched URL, for a log line: the path can
    carry a token (Telegram file URLs do)."""
    try:
        parts = urlsplit(str(url))
        scheme = parts.scheme.lower()
        if scheme and scheme not in ("http", "https"):
            # base64:// and file:// "hosts" are payload or path, not a host.
            return f"{scheme[:16]}://…"
        host = parts.hostname or ""
        port = parts.port
    except (TypeError, ValueError):
        return "<unparsable url>"
    if not scheme or not host:
        return "<unparsable url>"
    if ":" in host:
        host = f"[{host}]"
    return f"{scheme}://{host}{f':{port}' if port else ''}/…"


def _cap_cache(cache: dict, cap: int = 200, drop: int = 50) -> None:
    if len(cache) > cap:
        for k in list(cache)[:drop]:
            cache.pop(k, None)


async def _resolve_public_target(url: str) -> tuple[str, str, int] | None:
    """Resolve once and return (hostname, pinned public IP, port), or None.
    Fails closed unless every returned address is public."""
    try:
        parsed = urlsplit(url)
        scheme = parsed.scheme.lower()
        host = (parsed.hostname or "").strip("[]").rstrip(".")
        if scheme not in ("http", "https") or not host:
            return None
        port = parsed.port or (443 if scheme == "https" else 80)
    except (TypeError, ValueError):
        return None

    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        try:
            infos = await asyncio.to_thread(
                socket.getaddrinfo,
                host,
                port,
                type=socket.SOCK_STREAM,
            )
        except Exception:
            return None
        addresses: list[str] = []
        for info in infos:
            address = str(info[4][0]).split("%", 1)[0]
            if address not in addresses:
                addresses.append(address)
        if not addresses or any(_is_internal_ip(address) for address in addresses):
            return None
        return host, addresses[0], port
    else:
        address = str(literal)
        if _is_internal_ip(address):
            return None
        return host, address, port


class _PinnedNetworkBackend(httpcore.AsyncNetworkBackend):
    """Connect only to the address validated for one URL hop."""

    def __init__(self, hostname: str, pinned_ip: str) -> None:
        self.hostname = hostname.casefold().rstrip(".")
        self.pinned_ip = pinned_ip
        self._backend = AutoBackend()

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options=None,
    ):
        requested = str(host).casefold().rstrip(".")
        if requested != self.hostname:
            raise OSError("pinned transport refused an unexpected hostname")
        return await self._backend.connect_tcp(
            self.pinned_ip,
            port,
            timeout=timeout,
            local_address=local_address,
            socket_options=socket_options,
        )

    async def connect_unix_socket(
        self,
        path: str,
        timeout: float | None = None,
        socket_options=None,
    ):
        raise OSError("pinned HTTP transport does not permit Unix sockets")

    async def sleep(self, seconds: float) -> None:
        await self._backend.sleep(seconds)


class _PinnedAsyncHTTPTransport(httpx.AsyncHTTPTransport):
    """httpx transport that pins TCP while retaining the original Host/SNI."""

    def __init__(self, hostname: str, pinned_ip: str) -> None:
        ssl_context = ssl.create_default_context()
        backend = _PinnedNetworkBackend(hostname, pinned_ip)
        super().__init__(
            verify=ssl_context,
            trust_env=False,
            http1=True,
            http2=False,
        )
        # httpcore receives the original URL origin, so HTTP Host and TLS SNI
        # remain the hostname. Only connect_tcp is replaced with the pinned IP.
        self._pool = httpcore.AsyncConnectionPool(
            ssl_context=ssl_context,
            max_connections=10,
            max_keepalive_connections=0,
            http1=True,
            http2=False,
            network_backend=backend,
        )
        self.pinned_ip = pinned_ip


def _decode_body(
    chunks: list[bytes],
    encoding: str,
    max_decoded_bytes: int,
) -> bytes | None:
    """Decode one bounded HTTP content-coding without unbounded allocation."""
    if encoding in ("", "identity"):
        body = b"".join(chunks)
        return body if len(body) <= max_decoded_bytes else None
    if encoding == "gzip":
        decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
    elif encoding == "deflate":
        decoder = zlib.decompressobj()
    else:
        return None

    decoded = bytearray()
    try:
        for chunk in chunks:
            remaining = max_decoded_bytes - len(decoded)
            if remaining < 0:
                return None
            part = decoder.decompress(chunk, remaining + 1)
            decoded.extend(part)
            if len(decoded) > max_decoded_bytes or decoder.unconsumed_tail:
                return None
        remaining = max_decoded_bytes - len(decoded)
        decoded.extend(decoder.flush(remaining + 1))
    except zlib.error:
        return None
    if len(decoded) > max_decoded_bytes or not decoder.eof:
        return None
    return bytes(decoded)


async def safe_fetch_url(
    url: str,
    *,
    timeout: float,
    max_wire_bytes: int,
    max_decoded_bytes: int,
    headers: Optional[dict] = None,
    allowed_content_types: tuple[str, ...] = (),
    require_content_type: bool = False,
    max_redirects: int = 5,
    client_factory=None,
) -> SafeFetchResult | None:
    """Fetch with address pinning, redirect checks, and strict body limits."""
    current = url
    request_headers = dict(headers or {})
    request_headers.setdefault("Accept-Encoding", "gzip, deflate")

    for _ in range(max_redirects + 1):
        if not current or len(current) > MAX_URL_LENGTH:
            return None
        try:
            resolved = await asyncio.wait_for(
                _resolve_public_target(current),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            logger.warning("[Agent] DNS resolution timed out: %s", _url_for_log(current))
            return None
        if resolved is None and client_factory is not None:
            # Reserved .invalid hosts are for injected test transports; without
            # an injected factory this stays fail-closed.
            try:
                test_host = (urlsplit(current).hostname or "").rstrip(".")
            except Exception:
                test_host = ""
            if test_host.endswith(".invalid"):
                test_scheme = urlsplit(current).scheme.lower()
                test_port = urlsplit(current).port or (
                    443 if test_scheme == "https" else 80
                )
                resolved = (test_host, "93.184.216.34", test_port)
        if resolved is None:
            logger.warning("[Agent] refusing internal/unresolvable URL hop: %s",
                           _url_for_log(current))
            return None
        hostname, pinned_ip, _port = resolved
        transport = _PinnedAsyncHTTPTransport(hostname, pinned_ip)
        factory = client_factory or httpx.AsyncClient
        try:
            client_cm = factory(
                timeout=timeout,
                transport=transport,
                follow_redirects=False,
                trust_env=False,
            )
            async with client_cm as client:
                async with client.stream(
                    "GET",
                    current,
                    headers=request_headers,
                    follow_redirects=False,
                ) as response:
                    if response.status_code in (301, 302, 303, 307, 308):
                        location = response.headers.get("location", "")
                        if not location:
                            return None
                        current = str(httpx.URL(current).join(location))
                        continue
                    if response.status_code != 200:
                        return None

                    content_type = (
                        response.headers.get("content-type", "")
                        .split(";", 1)[0]
                        .strip()
                        .lower()
                    )
                    if require_content_type and not content_type:
                        return None
                    if allowed_content_types and not any(
                        content_type == allowed.rstrip("/")
                        or content_type.startswith(allowed)
                        for allowed in allowed_content_types
                    ):
                        return None

                    length = response.headers.get("content-length", "")
                    try:
                        if length and int(length) > max_wire_bytes:
                            return None
                    except (TypeError, ValueError):
                        pass

                    chunks: list[bytes] = []
                    wire_size = 0
                    iterator = (
                        response.aiter_raw()
                        if hasattr(response, "aiter_raw")
                        else response.aiter_bytes()
                    )
                    async for chunk in iterator:
                        wire_size += len(chunk)
                        if wire_size > max_wire_bytes:
                            return None
                        chunks.append(chunk)

                    encoding = (
                        response.headers.get("content-encoding", "")
                        .strip()
                        .lower()
                    )
                    body = _decode_body(chunks, encoding, max_decoded_bytes)
                    if body is None:
                        return None
                    return SafeFetchResult(
                        url=str(getattr(response, "url", current) or current),
                        status_code=response.status_code,
                        headers={str(k): str(v) for k, v in response.headers.items()},
                        content=body,
                    )
        except Exception as e:
            logger.debug("[Agent] safe fetch failed (%s): %s", _url_for_log(current), e)
            return None
        finally:
            # A fake client factory may ignore the transport; closing twice is
            # safe for httpx and ensures the transport never leaks a pool.
            try:
                await transport.aclose()
            except Exception:
                pass
    logger.warning("[Agent] redirect cap exceeded: %s", _url_for_log(url))
    return None


def _resolve_jailed_file_url(url: str, allowed_dir: str) -> Path | None:
    """Resolve a ``file://`` image URL inside QQ_ONEBOT_IMAGE_DIR, or None
    (also for a non-file or one over VISION_MAX_IMAGE_BYTES)."""
    from urllib.parse import urlparse, unquote

    local = unquote(urlparse(url).path)
    # "/C:/x" is how a Windows file:// URL parses; drop the slash for Path().
    if len(local) > 3 and local[0] == "/" and local[2] == ":":
        local = local[1:]
    try:
        path = Path(local).resolve()
    except Exception:
        return None
    allowed = (allowed_dir or "").strip()
    if not allowed:
        logger.warning(
            "[Agent] refusing file:// because QQ_ONEBOT_IMAGE_DIR is unset")
        return None
    try:
        allowed_path = Path(allowed).resolve(strict=True)
        if not path.is_relative_to(allowed_path):
            logger.warning(
                "[Agent] refusing file:// outside QQ_ONEBOT_IMAGE_DIR: %s", path)
            return None
        if not path.is_file() or path.stat().st_size > VISION_MAX_IMAGE_BYTES:
            return None
    except (OSError, ValueError):
        return None
    return path


class ContentIngestion:
    """Mixed into Agent; see agent.py."""

    _WBI_MIXIN_KEY_ENC_TAB = [
        46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35,
        27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13,
        37, 48, 7, 16, 24, 55, 40, 61, 26, 17, 0, 1, 60, 51, 30, 4,
        22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36, 20, 34, 44, 52,
    ]

    # ============ Generic URL understanding ============
    # Ends at whitespace, CJK punctuation/ideographs/full-width, or brackets.
    URL_PATTERN = re.compile(
        r'https?://[^\s　-〿一-鿿＀-￯<>{}|`\[\]]+'
    )
    #: Links described per message, message-wide: each is an outbound fetch
    #: before the message is buffered, so uncapped, one message of
    #: cache-busted URLs could stall intake.
    MAX_URLS_PER_MESSAGE = 3
    #: Wall clock for describing one message's links, which run concurrently:
    #: a slow or tarpit host costs its own descriptor, never the turn.
    LINK_ENRICHMENT_BUDGET_SEC = 10.0
    _URL_SKIP_EXT = (".zip", ".rar", ".7z", ".tar", ".gz", ".exe", ".msi", ".dmg",
                     ".apk", ".pdf", ".mp4", ".mp3", ".mov", ".avi", ".mkv",
                     ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp")

    _OG_TITLE_PAT = re.compile(
        r'<meta\s+(?:property|name)\s*=\s*["\'](?:og:title|twitter:title)["\'][^>]*content\s*=\s*["\']([^"\']+)["\']',
        re.IGNORECASE,
    )
    _OG_DESC_PAT = re.compile(
        r'<meta\s+(?:property|name)\s*=\s*["\'](?:og:description|twitter:description|description)["\'][^>]*content\s*=\s*["\']([^"\']+)["\']',
        re.IGNORECASE,
    )
    _OG_SITE_PAT = re.compile(
        r'<meta\s+(?:property|name)\s*=\s*["\']og:site_name["\'][^>]*content\s*=\s*["\']([^"\']+)["\']',
        re.IGNORECASE,
    )
    _TITLE_TAG_PAT = re.compile(r'<title[^>]*>(.*?)</title>', re.IGNORECASE | re.DOTALL)

    VISION_PROMPT = (
        "This image is most likely a **reaction sticker / meme** in a group chat "
        "(a conventional emotion symbol, not a real photo).\n"
        "**Task: name the emotion/meme it conveys, at most ~20 words.**\n"
        "\n"
        "Hard rules:\n"
        "1. If you can't make it out / can't open / fully black → reply \"can't see\". Never fabricate.\n"
        "2. **Report meaning, not pixels.** Bad: \"a shiba dog sitting at a desk\"  Good: \"doge — smug / mocking\". Bad: \"a panda\"  Good: \"speechless panda — out of words\".\n"
        "3. If there's **text on the image, quote it + describe the mood**. e.g. \"text 'you're right' — sarcastic agreement\" / \"text 'I'm about to lose it' — fake-angry\".\n"
        "4. Famous memes: name them directly — doge, speechless panda, salaryman crying, sobbing cat, distressed mouse, NPC thinking, etc.\n"
        "5. Real photo (not a sticker) → short subject description is fine. e.g. \"a real cat curled up on a couch\".\n"
        "6. Don't prefix with \"this image / the picture shows / in the image\" — just say it."
    )

    # The auto-tagger sees only a sticker's context; this looks at its pixels.
    VISION_AESTHETIC_PROMPT = (
        "Judge whether the visual aesthetic of this reaction sticker fits the kind "
        "of taste a **clean modern internet-savvy user** would actually post — vs. "
        "looking like content from an older family-group / chain-message subculture.\n"
        "**Output one JSON line only: {\"tacky\": true|false, \"reason\": \"≤6 words\"}**\n"
        "\n"
        "tacky=true (doesn't fit, should ban) criteria:\n"
        "- Older family-group / chain-message style: floral-script greetings (good morning / happy weekend / good fortune) + sparkle effects + roses / dancing cartoons\n"
        "- Loud printed fonts on saturated color blocks / low-resolution outlined stickers\n"
        "- Low-effort short-video-platform memes, visually crude\n"
        "- 2010s subculture aesthetic / heavy-filter photo-editor style\n"
        "- Stale cute style: crudely-rendered cartoon bears/dogs + hard subtitles\n"
        "- Anything that screams 'you'd only see this in a family-group chat'\n"
        "\n"
        "tacky=false (OK to send) criteria:\n"
        "- Clean modern design / classic doge / well-made sticker pack / film or TV screenshots / variety-show screencaps\n"
        "- Cartoon characters but with polished visuals / clean color blocks / minimal text\n"
        "- Real-person / celebrity / anime screencaps / contemporary popular memes\n"
        "- Widely-recognized modern memes (doge family, dancing cat, sobbing cat, etc.)\n"
        "\n"
        "When in doubt, return false (better to keep one through than to mis-ban a good one). Only ban what's obviously dated/crude at a glance."
    )

    # Bump when VISION_AESTHETIC_PROMPT changes, so every entry is re-judged.
    VISUAL_AESTHETIC_VERSION = 1

    # A caption containing any of these means the model couldn't see the image.
    _VISION_REJECT_TOKENS = (
        # English
        "can't see", "cannot see", "unable to see", "no image", "not visible",
        "can't read", "cannot read", "can't open", "cannot open",
        "unclear", "unrecognizable", "blank", "black screen", "empty image",
        "failed to load", "cannot access",
        # Chinese: some endpoints answer in Chinese whatever the prompt
        "不清楚", "不确定", "看不到", "看不了", "看不清", "打不开",
        "无法", "不存在", "无内容", "黑屏", "空白", "没看到",
        "图片为空", "加载失败", "无法访问", "无法识别",
    )

    async def _fetch_image_bytes(self, url: str) -> bytes | None:
        """Image bytes from a base64://, jailed file:// or SSRF-guarded http(s) URL."""
        if not url:
            return None
        if url.startswith("base64://"):
            # A connector image with no URL arrives inline.
            encoded = url[len("base64://"):]
            max_encoded = ((VISION_MAX_IMAGE_BYTES + 2) // 3) * 4 + 4
            if len(encoded) > max_encoded:
                logger.warning("[Agent] base64 image exceeds size limit")
                return None
            try:
                data = base64.b64decode(encoded, validate=True)
            except Exception as e:
                logger.debug("[Agent] base64 image decode failed: %s", e)
                return None
            if len(data) > VISION_MAX_IMAGE_BYTES or not _detect_image_mime(data):
                return None
            return data
        if url.startswith("file://"):
            path = _resolve_jailed_file_url(
                url, os.getenv("QQ_ONEBOT_IMAGE_DIR", ""))
            if path is None:
                return None
            local = str(path)
            try:
                with path.open("rb") as fh:
                    data = fh.read(VISION_MAX_IMAGE_BYTES + 1)
            except Exception as e:
                logger.debug("[Agent] file:// read failed (%s): %s", local, e)
                return None
            if len(data) > VISION_MAX_IMAGE_BYTES or not _detect_image_mime(data):
                return None
            return data
        if len(url) > MAX_URL_LENGTH:
            logger.warning("[Agent] image URL exceeds length limit")
            return None
        # SSRF guard: these bytes go to the vision provider and the sticker
        # library, and every redirect hop is re-checked.
        try:
            return await self._safe_get_bytes(
                url, timeout=15, headers={"User-Agent": "Mozilla/5.0"},
                max_bytes=VISION_MAX_IMAGE_BYTES)
        except Exception as e:
            logger.debug("[Agent] http fetch failed (%s): %s", _url_for_log(url), e)
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
        """Log another context sighting for a known sticker, without a download."""
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
        """Recent buffer lines as 'name: text' for sticker context, minus the bot."""
        buf = list(self.buffers.get(group_id, []))
        out: list[str] = []
        for m in buf[-n:]:
            if not m.get("user_id"):
                continue
            out.append(f"{m.get('name','?')}: "
                       f"{_truncate_framed(m.get('text', ''), 80)}")
        return out

    @staticmethod
    def _format_bili_line(info: dict, title_fallback: str = "") -> str:
        """The `[bilibili-video] "title" — by <up>, ...` line fed to the model."""
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
        """A share-card JSON segment as a line the LLM can read: Bilibili shares
        resolved, others via their URL or the card's own title and desc."""
        try:
            outer = json.loads(raw_json)
        except (TypeError, ValueError, json.JSONDecodeError):
            return ""
        if not isinstance(outer, dict):
            return ""

        # Every field is sender-controlled and any JSON type; non-strings count
        # as absent, so a crafted card degrades instead of dropping the message.
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

        # Other cards are thin; their jump URL often has richer OG metadata.
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
        """Bilibili title/uploader/desc (and AI summary) for a share URL, via
        b23.tv and the web view API; {} on any failure."""
        if not url or len(url) > MAX_URL_LENGTH:
            return {}

        cache_key = self._url_cache_key(url)
        if cache_key in self.bili_info_cache:
            return self.bili_info_cache[cache_key]

        real_url = url
        if "b23.tv" in url:
            # "contains b23.tv" is not "is a shortlink": never fetch internal hosts.
            if self._host_is_internal(url):
                logger.warning("[Agent] refusing internal-address b23 url: %s", url)
                self.bili_info_cache[cache_key] = {}
                return {}
            try:
                # _safe_get re-checks every redirect hop.
                r = await self._safe_get(url, timeout=5,
                                         headers={"User-Agent": "Mozilla/5.0"})
                if r is not None:
                    real_url = str(r.url)
            except Exception as e:
                logger.debug("[Agent] b23.tv resolve failed (%s): %s", url, e)

        m = re.search(r"BV[a-zA-Z0-9]{10}", real_url)
        if not m:
            self.bili_info_cache[cache_key] = {}
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
                    # "owner" is Bilibili's field for the uploader.
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

        self.bili_info_cache[cache_key] = info
        _cap_cache(self.bili_info_cache)
        logger.info("[Agent] bili view %s: %s", bvid, (info.get("title") or "(empty)")[:60])
        return info

    async def _fetch_wbi_keys(self) -> tuple[str, str]:
        """(img_key, sub_key) for WBI signing, cached 24h; ('', '') on failure."""
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
        """Bilibili AI summary via view/conclusion/get, or ""."""
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
        """Pull http(s) URLs out of text, deduped, order preserved, capped at
        ``MAX_URLS_PER_MESSAGE``."""
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
            if len(urls) >= cls.MAX_URLS_PER_MESSAGE:
                break
        return urls

    @classmethod
    def _host_is_internal(cls, url: str) -> bool:
        """Network-free SSRF pre-filter: an internal IP literal or reserved name.

        A fast reject, not the boundary (`_resolve_public_target` pins each
        connection). It never resolves: getaddrinfo would block the event loop,
        and a name resolved here says nothing about the address connected later."""
        try:
            host = (urlsplit(url).hostname or "").strip("[]").rstrip(".")
        except Exception:
            return True
        if not host:
            return True
        try:
            return _ip_obj_is_internal(ipaddress.ip_address(host))
        except ValueError:
            pass  # not an IP literal
        # Internal by definition; anything else is left to _resolve_public_target.
        low = host.lower()
        return low in _RESERVED_LOCAL_NAMES or low.endswith(".localhost")

    async def _safe_get(self, url: str, *, timeout: float,
                        headers: Optional[dict] = None,
                        max_redirects: int = 5) -> Optional[httpx.Response]:
        """GET with every redirect hop re-resolved, re-validated and pinned; None
        if a hop is internal or the redirect cap is exceeded."""
        result = await safe_fetch_url(
            url,
            timeout=timeout,
            max_wire_bytes=MAX_HTML_WIRE_BYTES,
            max_decoded_bytes=MAX_HTML_DECODED_BYTES,
            headers=headers,
            allowed_content_types=("text/html", "application/xhtml+xml"),
            require_content_type=True,
            max_redirects=max_redirects,
            client_factory=self.__dict__.get("_http"),
        )
        if result is None:
            return None
        request = httpx.Request("GET", result.url)
        # The body is already decoded, so drop the framing headers, or httpx
        # re-runs gzip over plaintext and every gzip-served link degrades.
        headers = {
            k: v for k, v in (result.headers or {}).items()
            if k.lower() not in ("content-encoding", "content-length",
                                 "transfer-encoding")
        }
        return httpx.Response(
            result.status_code,
            headers=headers,
            content=result.content,
            request=request,
        )

    async def _safe_get_bytes(self, url: str, *, timeout: float,
                              headers: Optional[dict] = None,
                              max_bytes: int,
                              max_redirects: int = 5) -> bytes | None:
        """Stream a bounded HTTP body while validating every redirect hop."""
        result = await safe_fetch_url(
            url,
            timeout=timeout,
            max_wire_bytes=max_bytes,
            max_decoded_bytes=max_bytes,
            headers=headers,
            max_redirects=max_redirects,
            client_factory=self.__dict__.get("_http"),
        )
        if result is None:
            return None
        return result.content if _detect_image_mime(result.content) else None

    @classmethod
    def _should_skip_url(cls, url: str) -> bool:
        u = url.lower()
        if any(u.split('?')[0].endswith(ext) for ext in cls._URL_SKIP_EXT):
            return True
        return cls._host_is_internal(url)

    async def _describe_url(self, url: str) -> str:
        """A descriptor for one URL: Bilibili API, YouTube oEmbed, or the page's
        OG tags. Cached; "[link]" on failure, so the model knows a URL was there."""
        if not url or len(url) > MAX_URL_LENGTH or self._should_skip_url(url):
            return ""
        cache_key = self._url_cache_key(url)
        if cache_key in self.url_info_cache:
            return self.url_info_cache[cache_key]
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
        self.url_info_cache[cache_key] = result
        return result

    async def _describe_urls(self, urls: list[str]) -> list[str]:
        """One descriptor per URL, aligned with `urls` ("" for a failure or a
        link still loading at ``LINK_ENRICHMENT_BUDGET_SEC``). Concurrent, so a
        straggler costs only its own descriptor."""
        if not urls:
            return []
        tasks = [asyncio.ensure_future(self._describe_url(u)) for u in urls]
        try:
            done, _ = await asyncio.wait(
                tasks, timeout=self.LINK_ENRICHMENT_BUDGET_SEC)
        finally:
            stragglers = [t for t in tasks if not t.done()]
            for t in stragglers:
                t.cancel()
        if stragglers:
            await asyncio.gather(*stragglers, return_exceptions=True)
            logger.info("[Agent] link enrichment: %d of %d links over the %gs "
                        "budget", len(stragglers), len(urls),
                        self.LINK_ENRICHMENT_BUDGET_SEC)
        out: list[str] = []
        for url, task in zip(urls, tasks):
            desc = ""
            if task in done:
                try:
                    desc = task.result()
                except Exception as e:
                    logger.debug("[Agent] link enrichment failed (%s): %s: %s",
                                 url, type(e).__name__, e)
            out.append(desc if desc and desc != "[link]" else "")
        return out

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
        """Open Graph / Twitter card scrape of a page, or "" on any failure."""
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
    def _url_cache_key(url: str) -> str:
        """Fixed-size key: URLs may contain credentials or megabytes of text."""
        return "url:" + hashlib.sha256(url.encode("utf-8", errors="replace")).hexdigest()

    @staticmethod
    def _image_cache_key(url: str) -> str:
        """Caption-cache key, hashed: base64:// pseudo-URLs can be megabytes."""
        prefix = "b64:" if url.startswith("base64://") else "url:"
        return prefix + hashlib.sha256(
            url.encode("utf-8", errors="replace"),
        ).hexdigest()

    def _accept_vision_caption(self, url: str, text: str, provider: str) -> str:
        # Truncated, not rejected: a long caption is still useful.
        text = (text or "").strip()[:150]
        hit = next((t for t in self._VISION_REJECT_TOKENS if t in text), "")
        if text and len(text) >= 4 and not hit:
            self.image_caption_cache[self._image_cache_key(url)] = text
            self._gc_image_cache()
            logger.info("[Agent] vision/%s (%s): %s", provider, _url_for_log(url),
                        text[:60])
            return text
        logger.info(
            "[Agent] vision/%s rejected (%s, hit=%r, len=%d): %s",
            provider, _url_for_log(url), hit, len(text), text[:80],
        )
        return ""

    @staticmethod
    def _gif_first_frame_png(gif_bytes: bytes) -> bytes:
        """A GIF's first frame as PNG, or b"" so the caller falls back to OCR."""
        class _BoundedBuffer(io.BytesIO):
            def write(self, data) -> int:
                if self.tell() + len(data) > VISION_MAX_IMAGE_BYTES:
                    raise ValueError("converted image exceeds byte limit")
                return super().write(data)

        im = None
        try:
            from PIL import Image
            Image.MAX_IMAGE_PIXELS = min(
                Image.MAX_IMAGE_PIXELS or MAX_IMAGE_PIXELS,
                MAX_IMAGE_PIXELS,
            )
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                im = Image.open(io.BytesIO(gif_bytes))
                width, height = im.size
                if (
                    width <= 0
                    or height <= 0
                    or width > MAX_IMAGE_DIMENSION
                    or height > MAX_IMAGE_DIMENSION
                    or width * height > MAX_IMAGE_PIXELS
                ):
                    return b""
                im.seek(0)
                out = _BoundedBuffer()
                converted = im.convert("RGB")
                try:
                    converted.save(out, format="PNG")
                finally:
                    close_converted = getattr(converted, "close", None)
                    if callable(close_converted) and converted is not im:
                        close_converted()
                return out.getvalue()
        except Exception as e:
            logger.debug("[Agent] GIF→PNG failed: %s: %s", type(e).__name__, e)
            return b""

        finally:
            close_image = getattr(im, "close", None)
            if callable(close_image):
                close_image()

    def _vision_configured(self) -> bool:
        """Model, key and base URL all set, so no image is uploaded by default."""
        return bool(self.vision_model and self.vision_api_key and self.vision_base_url)

    async def _vision_data_url(self, img_bytes: bytes, mime: str) -> str:
        """Base64 data URL for the vision endpoint (raw URLs trip some providers);
        a GIF goes as its first frame, decoded off the loop, or "" if that fails."""
        if mime == "image/gif":
            img_bytes = await asyncio.to_thread(self._gif_first_frame_png, img_bytes)
            if not img_bytes:
                return ""
            mime = "image/png"
        return f"data:{mime};base64,{base64.b64encode(img_bytes).decode()}"

    async def _vision_post(
        self, prompt: str, data_url: str, *, max_tokens: int, temperature: float,
        attempts: int, retryable: frozenset[int], backoff: float,
        retry_errors: bool,
    ) -> tuple[httpx.Response | None, Exception | None]:
        """POST one image prompt, retrying `retryable` statuses (and transport
        errors when `retry_errors`, else they raise) with exponential backoff.
        A 400 refusing a field is resent at once in the spelling the endpoint
        takes. Returns the last response (None if every try raised) and the
        last error."""
        payload = {
            "model": self.vision_model,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        apply_k2_quirks(payload, self.vision_model, self.vision_base_url)
        r = None
        last_exc = None
        async with self._http(timeout=30) as c:
            async def send() -> httpx.Response:
                return await c.post(
                    f"{self.vision_base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.vision_api_key}"},
                    json=dict(payload),
                )
            for attempt in range(attempts):
                try:
                    r = await send()
                    if (getattr(r, "status_code", 200) in (400, 422)
                            and adapt_rejected_payload(payload, str(getattr(r, "text", "") or ""))):
                        r = await send()
                except Exception as e:
                    if not retry_errors:
                        raise
                    r, last_exc = None, e
                else:
                    if r.status_code not in retryable:
                        break
                if attempt < attempts - 1:
                    await asyncio.sleep(backoff * 2 ** attempt)
        return r, last_exc

    @staticmethod
    def _vision_text(r: httpx.Response) -> str:
        return (r.json().get("choices", [{}])[0]
                .get("message", {})
                .get("content", "") or "")

    async def _judge_sticker_aesthetic(self, img_bytes: bytes) -> bool | None:
        """Whether the vision model finds a sticker tacky: True, False, or None
        when no verdict came back (the entry is left untouched)."""
        try:
            if not img_bytes or len(img_bytes) < 200 or len(img_bytes) > 5_000_000:
                return None
            mime = _detect_image_mime(img_bytes)
            if mime not in ("image/png", "image/jpeg", "image/gif", "image/webp"):
                return None
            data_url = await self._vision_data_url(img_bytes, mime)
            if not data_url:
                return None
            # Long 429 backoff: the recheck is a startup burst and free tiers
            # rate-limit hard, so without it most verdicts come back None.
            r, _ = await self._vision_post(
                self.VISION_AESTHETIC_PROMPT, data_url, max_tokens=60,
                temperature=0, attempts=4, retryable=frozenset({429}),
                backoff=3.0, retry_errors=False)
            if r is None or r.status_code != 200:
                return None
            raw = self._vision_text(r).strip()
            data = salvage_json_object(strip_json_fences(raw))
            if data is None or "tacky" not in data:
                return None
            return bool(data.get("tacky"))
        except Exception as e:
            logger.debug("[Agent] sticker aesthetic judge failed: %s: %s",
                         type(e).__name__, e)
            return None

    async def visual_recheck_aesthetic_all(self, limit: int = 200) -> int:
        """Demote visually tacky stickers to persona_fit=false; the text recheck
        sees only meaning, not style. Version-gated per entry, and a no-op
        without a configured vision model, so a default install uploads nothing."""
        if not self._vision_configured():
            return 0
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
            if tacky is not None:
                v["_visual_aesthetic_version"] = self.VISUAL_AESTHETIC_VERSION
            if tacky is True:
                v["persona_fit"] = False
                marked += 1
                logger.info("[stickers] visual-aesthetic ban %s: meaning=%r",
                            fn, v.get("meaning", ""))
            # Pacing for tight free-tier vision rate limits.
            await asyncio.sleep(5.0)
        # Forced: the version stamps record a paid call per sticker, and a
        # throttled write would lose them to a crash.
        self.stickers._save(force=True)
        logger.info("[Agent] visual aesthetic recheck: scanned=%d banned=%d",
                    len(todo), marked)
        return marked

    async def _describe_image_vision(self, url: str) -> str | None:
        """Caption an image through the OpenAI-compatible vision endpoint. None
        means the call failed and may succeed later; "" means no usable caption."""
        try:
            img_bytes = await self._fetch_image_bytes(url)
            if not img_bytes:
                return None
            if len(img_bytes) < 200:
                logger.debug("[Agent] vision: image too small (%d bytes), skipping", len(img_bytes))
                return ""
            if len(img_bytes) > VISION_MAX_IMAGE_BYTES:
                logger.warning("[Agent] vision: image too large (%d bytes), skipping", len(img_bytes))
                return ""
            mime = _detect_image_mime(img_bytes)
            if not mime:
                logger.debug("[Agent] vision: unknown image magic %s",
                             img_bytes[:12].hex())
                return ""
            # Vision endpoints commonly reject these; the caller falls back to OCR.
            if mime == "image/heic":
                logger.info("[Agent] vision: skip HEIC/HEIF, fallback to OCR")
                return ""
            if mime == "image/avif":
                logger.info("[Agent] vision: skip AVIF, fallback to OCR")
                return ""
            data_url = await self._vision_data_url(img_bytes, mime)
            if not data_url:
                logger.info("[Agent] vision: skip GIF (first-frame extract failed), fallback to OCR")
                return ""
            # Every group image comes through here: retry throttling, 5xx,
            # timeouts and the odd 400 some providers give a valid image, or
            # the bot silently stops seeing images.
            r, last_exc = await self._vision_post(
                self.VISION_PROMPT, data_url, max_tokens=120, temperature=0.3,
                attempts=3, retryable=frozenset({400, 429, 500, 502, 503, 504}),
                backoff=1.0, retry_errors=True)
            if r is None or r.status_code != 200:
                logger.warning("[Agent] vision HTTP %d: %s (exc=%s)",
                               r.status_code if r else 0,
                               (r.text if r else "")[:200], last_exc)
                return None
            return self._accept_vision_caption(url, self._vision_text(r), "api")
        except Exception as e:
            logger.debug("[Agent] vision failed: %s: %s",
                         type(e).__name__, e)
            return None

    async def _describe_image(self, url: str) -> str:
        """Vision caption, else OCR; garbage OCR (short fragments) is dropped."""
        if not url:
            return ""
        cache_key = self._image_cache_key(url)
        if cache_key in self.image_caption_cache:
            return self.image_caption_cache[cache_key]

        caption = ""
        if self._vision_configured():
            caption = await self._describe_image_vision(url)
        vision_failed = caption is None
        if caption:
            return caption

        # OCR is QQ-only: NapCat can't fetch a connector image's URL.
        if current_sink.get() is not None:
            return ""

        ocr_text = await self._ocr_image(url)
        if ocr_text and len(ocr_text) >= 4:
            tokens = ocr_text.split()
            avg_token_len = sum(len(t) for t in tokens) / max(len(tokens), 1)
            if avg_token_len >= 2:
                return ocr_text
        # Cache the miss only when both channels answered: a failed vision call
        # means "not now", and cached it would blind this image for good.
        if not vision_failed and cache_key in self.image_caption_cache:
            self.image_caption_cache[cache_key] = ""
            self._gc_image_cache()
        return ""

    def _gc_image_cache(self) -> None:
        _cap_cache(self.image_caption_cache)

    async def _ocr_image(self, url: str) -> str:
        """Text from NapCat's /ocr_image, or "".

        A delegated fetch with no SSRF controls of its own, reached exactly when
        the direct fetch refused a URL, so it is gated here (public http(s) only)."""
        if not url or not self.qq_onebot_url:
            return ""
        if not url.lower().startswith(("http://", "https://")):
            logger.warning("[Agent] refusing non-HTTP OCR delegation: %s",
                           _url_for_log(url))
            return ""
        if await _resolve_public_target(url) is None:
            logger.warning("[Agent] refusing OCR delegation for internal/"
                           "unresolvable url: %s", _url_for_log(url))
            return ""
        cache_key = self._image_cache_key(url)
        if cache_key in self.image_caption_cache:
            return self.image_caption_cache[cache_key]
        try:
            async with self._local_http(timeout=15) as client:
                r = await client.post(
                    f"{self.qq_onebot_url}/ocr_image",
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
                           _url_for_log(url), type(e).__name__,
                           str(e) or "(no message)")
            return ""
        self.image_caption_cache[cache_key] = text
        self._gc_image_cache()
        logger.info("[Agent] OCR (%s): %s", _url_for_log(url),
                    text[:60] or "(no text)")
        return text
