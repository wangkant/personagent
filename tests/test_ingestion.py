"""Security regression tests for URL and image ingestion.

Run directly:
    python tests/test_ingestion.py
"""
from __future__ import annotations

import asyncio
import gzip
import io
import re
import socket
import sys
import time
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from persona_agent.ingestion import ContentIngestion, safe_fetch_url
from tools.bootstrap_from_history import download_sticker


FAILURES: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"[PASS] {name}")
        return
    FAILURES.append(name)
    print(f"[FAIL] {name}: {detail}")


class Harness(ContentIngestion):
    _URL_SKIP_EXT = (
        ".zip", ".rar", ".7z", ".tar", ".gz", ".exe", ".pdf",
        ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp",
    )
    _OG_TITLE_PAT = re.compile(
        r'<meta\s+(?:property|name)\s*=\s*["\'](?:og:title|twitter:title)'
        r'["\'][^>]*content\s*=\s*["\']([^"\']+)["\']',
        re.IGNORECASE,
    )
    _OG_DESC_PAT = re.compile(
        r'<meta\s+(?:property|name)\s*=\s*["\']'
        r'(?:og:description|twitter:description|description)'
        r'["\'][^>]*content\s*=\s*["\']([^"\']+)["\']',
        re.IGNORECASE,
    )
    _OG_SITE_PAT = re.compile(
        r'<meta\s+(?:property|name)\s*=\s*["\']og:site_name'
        r'["\'][^>]*content\s*=\s*["\']([^"\']+)["\']',
        re.IGNORECASE,
    )
    _TITLE_TAG_PAT = re.compile(
        r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL,
    )

    def __init__(self) -> None:
        self.url_info_cache: dict[str, str] = {}
        self.image_caption_cache: dict[str, str] = {}
        self.bili_info_cache: dict[str, dict] = {}


class FakeResponse:
    def __init__(
        self,
        body: bytes,
        *,
        content_type: str = "text/html; charset=utf-8",
        content_encoding: str = "",
        status_code: int = 200,
        location: str = "",
        url: str = "https://example.com/page",
        eager_text: str | None = None,
    ) -> None:
        self.status_code = status_code
        self.url = url
        self.content = body
        self.text = (
            eager_text
            if eager_text is not None
            else body.decode("utf-8", errors="replace")
        )
        self.headers = {"content-type": content_type}
        if content_encoding:
            self.headers["content-encoding"] = content_encoding
        if location:
            self.headers["location"] = location

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def aiter_raw(self):
        midpoint = max(1, len(self.content) // 2)
        yield self.content[:midpoint]
        yield self.content[midpoint:]

    async def aiter_bytes(self):
        async for chunk in self.aiter_raw():
            yield chunk


class FakeClient:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def get(self, url, headers=None):
        self.response.url = url
        return self.response

    def stream(self, method, url, headers=None, follow_redirects=False):
        self.response.url = url
        return self.response


async def test_html_wire_cap() -> None:
    agent = Harness()
    body = (
        b'<meta property="og:title" content="must-not-parse">'
        + b"x" * 200_000
    )
    fake = FakeClient(FakeResponse(body))
    agent._http = lambda **kwargs: fake
    got = await agent._fetch_og_meta("https://example.com/huge")
    check("html: wire body over cap rejected", got == "", repr(got))


async def test_html_decoded_cap() -> None:
    agent = Harness()
    decoded = (
        b'<meta property="og:title" content="must-not-parse">'
        + b"x" * 200_000
    )
    encoded = gzip.compress(decoded)
    fake = FakeClient(FakeResponse(
        encoded,
        content_encoding="gzip",
        eager_text=decoded.decode(),
    ))
    agent._http = lambda **kwargs: fake
    got = await agent._fetch_og_meta("https://example.com/bomb")
    check("html: decoded gzip body over cap rejected", got == "", repr(got))


async def test_gzip_site_og_tags_are_actually_parsed() -> None:
    """A gzip-served page must yield its OG tags.

    safe_fetch_url returns a DECODED body, and _safe_get used to rebuild an
    httpx.Response from it while keeping the original `content-encoding: gzip`
    header — so httpx re-ran its decompressor over plaintext and raised
    DecodingError from the constructor. That was swallowed upstream and every
    shared link from a gzip-serving site (i.e. most of them) degraded to
    "[link]". The only gzip test asserted "" for an oversized body, and "" is
    also what this bug produced, so it masked the failure rather than catching
    it. This asserts the positive case."""
    agent = Harness()
    decoded = (b'<html><head>'
               b'<meta property="og:title" content="Real Title">'
               b'<meta property="og:description" content="Real description">'
               b'</head></html>')
    fake = FakeClient(FakeResponse(
        gzip.compress(decoded),
        content_encoding="gzip",
        eager_text=decoded.decode(),
    ))
    agent._http = lambda **kwargs: fake
    got = await agent._fetch_og_meta("https://example.com/gzipped")
    check("html: gzip page yields its og:title", "Real Title" in got, repr(got))


async def test_html_content_type() -> None:
    agent = Harness()
    body = b'<meta property="og:title" content="not-html">'
    fake = FakeClient(
        FakeResponse(body, content_type="application/octet-stream"),
    )
    agent._http = lambda **kwargs: fake
    got = await agent._fetch_og_meta("https://example.com/not-html")
    check("html: non-HTML content type rejected", got == "", repr(got))


async def test_url_limits_and_cache_keys() -> None:
    agent = Harness()

    async def fake_meta(url: str) -> str:
        return '[example] "ok"'

    agent._fetch_og_meta = fake_meta
    normal = "https://example.com/path?token=secret"
    got = await agent._describe_url(normal)
    keys = list(agent.url_info_cache)
    check("url cache: valid URL still described", got == '[example] "ok"', repr(got))
    check(
        "url cache: raw URL is not retained",
        normal not in agent.url_info_cache,
        repr(keys),
    )
    check(
        "url cache: key is fixed-size",
        len(keys) == 1 and len(keys[0]) < 100,
        repr(keys),
    )

    too_long = "https://example.com/" + "a" * 5000
    got_long = await agent._describe_url(too_long)
    check("url: oversized URL rejected before fetch", got_long == "", repr(got_long))
    check("url: oversized URL not cached", len(agent.url_info_cache) == 1, repr(keys))

    image_key = agent._image_cache_key(
        "https://example.com/image?" + "b" * 5000,
    )
    check("image cache: URL key is fixed-size", len(image_key) < 100, image_key[:120])


async def test_dns_resolution_is_pinned_once() -> None:
    agent = Harness()
    png = b"\x89PNG\r\n\x1a\n" + b"x" * 32
    fake = FakeClient(FakeResponse(png, content_type="image/png"))
    kwargs_seen: list[dict] = []
    resolutions = [
        [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))],
        [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))],
    ]

    def fake_factory(**kwargs):
        kwargs_seen.append(kwargs)
        return fake

    def fake_getaddrinfo(*args, **kwargs):
        return resolutions.pop(0)

    agent._http = fake_factory
    with patch("persona_agent.ingestion.socket.getaddrinfo", fake_getaddrinfo):
        got = await agent._fetch_image_bytes("https://rebind.example/image")

    transport = kwargs_seen[0].get("transport") if kwargs_seen else None
    pinned_ip = getattr(transport, "pinned_ip", "")
    check("dns: image fetch succeeds through pinned transport", got == png, repr(got))
    check("dns: hostname resolved exactly once", len(resolutions) == 1, repr(resolutions))
    check("dns: validated address is pinned", pinned_ip == "93.184.216.34", pinned_ip)


async def test_dns_resolution_obeys_timeout() -> None:
    def slow_getaddrinfo(*args, **kwargs):
        time.sleep(0.15)
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443)),
        ]

    started = time.monotonic()
    with patch("persona_agent.ingestion.socket.getaddrinfo", slow_getaddrinfo):
        result = await safe_fetch_url(
            "https://slow-dns.example/image",
            timeout=0.02,
            max_wire_bytes=1024,
            max_decoded_bytes=1024,
        )
    elapsed = time.monotonic() - started
    check("dns: resolution timeout fails closed", result is None, repr(result))
    check("dns: resolution timeout is prompt", elapsed < 0.12, f"{elapsed:.3f}s")


def test_gif_pixel_bomb_rejected_before_convert() -> None:
    converted = False

    class FakeImage:
        size = (50_000, 50_000)

        def seek(self, frame):
            return None

        def convert(self, mode):
            nonlocal converted
            converted = True
            return self

        def save(self, out, format):
            out.write(b"unsafe")

    with patch("PIL.Image.open", return_value=FakeImage()):
        got = ContentIngestion._gif_first_frame_png(b"GIF89a" + b"x" * 32)
    check("gif: pixel bomb rejected", got == b"", repr(got))
    check("gif: rejected before pixel conversion", converted is False, repr(converted))


def test_small_gif_still_converts() -> None:
    from PIL import Image

    source = io.BytesIO()
    Image.new("P", (2, 2), color=1).save(source, format="GIF")
    got = ContentIngestion._gif_first_frame_png(source.getvalue())
    check("gif: normal small image converts", got.startswith(b"\x89PNG\r\n\x1a\n"))


async def test_bootstrap_uses_guarded_bounded_fetch() -> None:
    calls = 0

    class BootstrapClient(FakeClient):
        def stream(self, *args, **kwargs):
            nonlocal calls
            calls += 1
            return super().stream(*args, **kwargs)

    client = BootstrapClient(FakeResponse(
        b"\x89PNG\r\n\x1a\n" + b"x" * 900_000,
        content_type="image/png",
    ))

    got_internal = await download_sticker(
        client, "http://127.0.0.1/private.png",
    )
    check(
        "bootstrap: internal URL rejected",
        got_internal is None,
        f"{len(got_internal)} bytes" if got_internal is not None else "",
    )
    check("bootstrap: internal URL never requested", calls == 0, repr(calls))

    got_large = await download_sticker(
        client, "https://example.com/large.png",
    )
    check(
        "bootstrap: oversized body rejected",
        got_large is None,
        f"{len(got_large)} bytes" if got_large is not None else "",
    )
    check("bootstrap: public URL reached bounded stream", calls == 1, repr(calls))


async def main() -> int:
    await test_html_wire_cap()
    await test_html_decoded_cap()
    await test_gzip_site_og_tags_are_actually_parsed()
    await test_html_content_type()
    await test_url_limits_and_cache_keys()
    await test_dns_resolution_is_pinned_once()
    await test_dns_resolution_obeys_timeout()
    test_gif_pixel_bomb_rejected_before_convert()
    test_small_gif_still_converts()
    await test_bootstrap_uses_guarded_bounded_fetch()
    if FAILURES:
        print(f"\n{len(FAILURES)} test(s) failed")
        return 1
    print("\nall tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
