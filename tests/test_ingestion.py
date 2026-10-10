"""Security regression tests for URL and image ingestion.

Run from the repo root:

    python -m pytest tests/test_ingestion.py
"""
from __future__ import annotations

import asyncio
import base64
import gzip
import io
import os
import re
import socket
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from persona_agent.agent import Agent
from persona_agent.ingestion import ContentIngestion, safe_fetch_url
from tools.bootstrap_from_history import download_sticker

from helpers import CLOSED_ONEBOT_URL, check, isolated_agent


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


def test_url_fanout_is_capped() -> None:
    """agent.py awaits a describe call for every URL this returns, in sequence,
    before the message is buffered or its text truncated. Uncapped, one message
    of cache-busted links stalls the intake loop for every group, not just its
    own — so the cap belongs here, at the source of the list."""
    cap = ContentIngestion.MAX_URLS_PER_MESSAGE
    many = " ".join(f"https://example.com/a?i={i}" for i in range(20))
    got = ContentIngestion._extract_urls(many)
    check("urls: fanout is capped", len(got) == cap, str(len(got)))
    check("urls: the cap keeps the first links, in order",
          got == [f"https://example.com/a?i={i}" for i in range(cap)], str(got))
    check("urls: dedup still collapses repeats",
          ContentIngestion._extract_urls(
              " ".join(["https://example.com/same"] * 10))
          == ["https://example.com/same"])


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


TELEGRAM_FILE_URL = "https://api.telegram.org/file/bot123:SECRETSECRET/photos/x.jpg"


def test_a_fetched_url_is_logged_as_its_host_only(caplog) -> None:
    """Telegram file URLs carry the bot token in the path and AstrBot
    forwards them as is; a slice of the URL put the token in the log."""
    import asyncio
    import logging

    from persona_agent import ingestion
    from persona_agent.ingestion import _url_for_log

    shown = _url_for_log(TELEGRAM_FILE_URL)
    check("url log: the host is kept", "api.telegram.org" in shown, shown)
    check("url log: the path is not", "SECRET" not in shown, shown)
    check("url log: base64 payloads are not echoed",
          _url_for_log("base64://QUJDREVGRw==") == "base64://…")
    check("url log: garbage is named, not echoed",
          _url_for_log("not a url") == "<unparsable url>")

    async def stalled(url):
        await asyncio.sleep(1)

    async def refused(url):
        return None

    caplog.set_level(logging.DEBUG, logger="agent")
    Harness()._accept_vision_caption(TELEGRAM_FILE_URL, "a cat on a mat", "api")
    with patch.object(ingestion, "_resolve_public_target", stalled):
        asyncio.run(safe_fetch_url(
            TELEGRAM_FILE_URL, timeout=0.01, max_wire_bytes=10,
            max_decoded_bytes=10))
    with patch.object(ingestion, "_resolve_public_target", refused):
        asyncio.run(safe_fetch_url(
            TELEGRAM_FILE_URL, timeout=1, max_wire_bytes=10,
            max_decoded_bytes=10))
    lines = [record.getMessage() for record in caplog.records]
    check("url log: the three sites logged", len(lines) >= 3, repr(lines))
    check("url log: no line carries the token",
          not any("SECRET" in line for line in lines), repr(lines))


@pytest.mark.parametrize("address, internal", [
    ("100.64.0.1", True),               # CGNAT / Tailscale
    ("100.100.100.200", True),          # Alibaba Cloud ECS metadata
    ("::ffff:100.100.100.200", True),   # the same, IPv4-mapped
    ("::ffff:127.0.0.1", True),
    ("fec0::1", True),                  # deprecated site-local
    ("93.184.216.34", False),
    ("2606:4700::1111", False),
])
def test_every_non_global_address_is_internal(address, internal) -> None:
    from persona_agent.ingestion import _is_internal_ip

    check(f"ssrf: {address} internal={internal}",
          _is_internal_ip(address) is internal)


# --- Vision requests: the caption and the sticker-aesthetic verdict ----------

VISION_BASE = "https://vision.example/v1"
PNG = b"\x89PNG\r\n\x1a\n" + b"p" * 400
GIF = b"GIF89a" + b"g" * 400
FRAME = b"\x89PNG\r\n\x1a\n" + b"frame" * 80
BMP = b"BM" + b"b" * 400
HEIC = b"\x00\x00\x00\x18ftypheic" + b"h" * 400
AVIF = b"\x00\x00\x00\x18ftypavif" + b"a" * 400
UNKNOWN = b"\x00" * 400
IMAGE_URL = "https://img.example/a.png"


def _data_url(mime: str, body: bytes) -> str:
    return f"data:{mime};base64,{base64.b64encode(body).decode()}"


class VisionResponse:
    def __init__(self, status: int, content: str = "") -> None:
        self.status_code = status
        self.text = f"status {status} body"
        self._content = content

    def json(self):
        return {"choices": [{"message": {"content": self._content}}]}


class ScriptedVision:
    """Stands in for `agent._http`: each POST takes the next scripted outcome."""

    def __init__(self, *outcomes) -> None:
        self.outcomes = list(outcomes)
        self.posts: list[dict] = []
        self.client_kwargs: list[dict] = []

    def __call__(self, **kwargs):
        self.client_kwargs.append(kwargs)
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def post(self, url, headers=None, json=None):
        self.posts.append({"url": url, "headers": headers, "json": json})
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


class VisionHarness(Harness):
    vision_model = "vision-model"
    vision_api_key = "vision-key"
    vision_base_url = VISION_BASE

    def __init__(self, image: bytes | None = PNG, *outcomes) -> None:
        super().__init__()
        self.image = image
        self.vision = ScriptedVision(*outcomes)
        self._http = self.vision

    async def _fetch_image_bytes(self, url: str) -> bytes | None:
        return self.image


@pytest.fixture
def sleeps(monkeypatch) -> list:
    """Backoff delays the vision paths asked for; nothing actually waits."""
    from persona_agent import ingestion

    delays: list = []

    async def no_wait(delay):
        delays.append(delay)

    monkeypatch.setattr(ingestion.asyncio, "sleep", no_wait)
    return delays


def _expected_payload(prompt: str, data_url: str, max_tokens: int,
                      temperature: float) -> dict:
    return {
        "model": "vision-model",
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


async def test_vision_caption_request_shape(sleeps) -> None:
    agent = VisionHarness(PNG, VisionResponse(200, "doge - smug"))
    got = await agent._describe_image_vision(IMAGE_URL)
    check("caption: accepted text returned", got == "doge - smug", repr(got))
    check("caption: one client, 30 s timeout",
          agent.vision.client_kwargs == [{"timeout": 30}],
          repr(agent.vision.client_kwargs))
    post = agent.vision.posts[0]
    check("caption: posts to chat/completions",
          post["url"] == f"{VISION_BASE}/chat/completions", post["url"])
    check("caption: bearer key", post["headers"] == {
        "Authorization": "Bearer vision-key"}, repr(post["headers"]))
    expected = _expected_payload(ContentIngestion.VISION_PROMPT,
                                 _data_url("image/png", PNG), 120, 0.3)
    check("caption: payload shape", post["json"] == expected, repr(post["json"])[:300])
    check("caption: no backoff on success", sleeps == [], repr(sleeps))


@pytest.mark.parametrize("status", [400, 429, 500, 502, 503, 504])
async def test_vision_caption_retries_a_retryable_status(status, sleeps) -> None:
    agent = VisionHarness(PNG, *[VisionResponse(status)] * 3)
    got = await agent._describe_image_vision(IMAGE_URL)
    check(f"caption {status}: None after the last try", got is None, repr(got))
    check(f"caption {status}: three tries", len(agent.vision.posts) == 3,
          repr(len(agent.vision.posts)))
    check(f"caption {status}: 1 s then 2 s backoff", sleeps == [1, 2], repr(sleeps))

    agent = VisionHarness(PNG, VisionResponse(status), VisionResponse(200, "a cat on a mat"))
    sleeps.clear()
    got = await agent._describe_image_vision(IMAGE_URL)
    check(f"caption {status}: a later success is used", got == "a cat on a mat", repr(got))
    check(f"caption {status}: one backoff before it", sleeps == [1], repr(sleeps))


@pytest.mark.parametrize("status", [401, 403, 404, 422])
async def test_vision_caption_does_not_retry_other_statuses(status, sleeps) -> None:
    agent = VisionHarness(PNG, VisionResponse(status))
    got = await agent._describe_image_vision(IMAGE_URL)
    check(f"caption {status}: None", got is None, repr(got))
    check(f"caption {status}: a single try", len(agent.vision.posts) == 1)
    check(f"caption {status}: no backoff", sleeps == [], repr(sleeps))


async def test_vision_caption_retries_transport_errors(sleeps) -> None:
    import httpx

    agent = VisionHarness(PNG, *[httpx.ReadTimeout("slow")] * 3)
    got = await agent._describe_image_vision(IMAGE_URL)
    check("caption errors: None after three tries", got is None, repr(got))
    check("caption errors: three tries", len(agent.vision.posts) == 3)
    check("caption errors: 1 s then 2 s backoff", sleeps == [1, 2], repr(sleeps))

    agent = VisionHarness(PNG, httpx.ConnectError("refused"),
                          VisionResponse(200, "a cat on a mat"))
    sleeps.clear()
    got = await agent._describe_image_vision(IMAGE_URL)
    check("caption errors: a later success is used", got == "a cat on a mat", repr(got))
    check("caption errors: one backoff before it", sleeps == [1], repr(sleeps))


@pytest.mark.parametrize("image, expected", [
    (None, None),
    (b"", None),
    (PNG[:199], ""),
    (b"\x89PNG\r\n\x1a\n" + b"p" * 5_000_000, ""),
    (UNKNOWN, ""),
    (HEIC, ""),
    (AVIF, ""),
], ids=["none", "empty", "tiny", "huge", "unknown", "heic", "avif"])
async def test_vision_caption_skips_unusable_images(image, expected, sleeps) -> None:
    agent = VisionHarness(image)
    got = await agent._describe_image_vision(IMAGE_URL)
    check("caption skip: result", got == expected, repr(got))
    check("caption skip: nothing posted", agent.vision.posts == [])


async def test_vision_caption_sends_bmp_as_is(sleeps) -> None:
    agent = VisionHarness(BMP, VisionResponse(200, "a cat on a mat"))
    await agent._describe_image_vision(IMAGE_URL)
    sent = agent.vision.posts[0]["json"]["messages"][0]["content"][1]
    check("caption bmp: sent with its own mime",
          sent["image_url"]["url"] == _data_url("image/bmp", BMP))


async def test_vision_caption_sends_a_gif_as_its_first_frame(sleeps) -> None:
    import threading

    threads: list = []

    def first_frame(data: bytes) -> bytes:
        threads.append(threading.get_ident())
        return FRAME if data == GIF else b""

    agent = VisionHarness(GIF, VisionResponse(200, "a cat on a mat"))
    agent._gif_first_frame_png = first_frame
    got = await agent._describe_image_vision(IMAGE_URL)
    sent = agent.vision.posts[0]["json"]["messages"][0]["content"][1]
    check("caption gif: captioned", got == "a cat on a mat", repr(got))
    check("caption gif: first frame sent as PNG",
          sent["image_url"]["url"] == _data_url("image/png", FRAME))
    check("caption gif: decoded off the event loop thread",
          threads and threads[0] != threading.get_ident(), repr(threads))

    agent = VisionHarness(GIF)
    agent._gif_first_frame_png = lambda data: b""
    got = await agent._describe_image_vision(IMAGE_URL)
    check("caption gif: a failed decode is no caption", got == "", repr(got))
    check("caption gif: and nothing is posted", agent.vision.posts == [])


async def test_vision_aesthetic_request_shape(sleeps) -> None:
    agent = VisionHarness(None, VisionResponse(200, ' {"tacky": true, "reason": "x"} '))
    got = await agent._judge_sticker_aesthetic(PNG)
    check("aesthetic: verdict parsed", got is True, repr(got))
    check("aesthetic: one client, 30 s timeout",
          agent.vision.client_kwargs == [{"timeout": 30}],
          repr(agent.vision.client_kwargs))
    post = agent.vision.posts[0]
    check("aesthetic: posts to chat/completions",
          post["url"] == f"{VISION_BASE}/chat/completions", post["url"])
    check("aesthetic: bearer key", post["headers"] == {
        "Authorization": "Bearer vision-key"}, repr(post["headers"]))
    expected = _expected_payload(ContentIngestion.VISION_AESTHETIC_PROMPT,
                                 _data_url("image/png", PNG), 60, 0)
    check("aesthetic: payload shape", post["json"] == expected, repr(post["json"])[:300])
    check("aesthetic: no backoff on success", sleeps == [], repr(sleeps))


@pytest.mark.parametrize("content, expected", [
    ('{"tacky": false}', False),
    ('```json\n{"tacky": true}\n```', True),
    ('{"reason": "no verdict"}', None),
    ("no idea", None),
    ("", None),
], ids=["false", "fenced", "no-verdict", "prose", "blank"])
async def test_vision_aesthetic_verdict_parsing(content, expected, sleeps) -> None:
    agent = VisionHarness(None, VisionResponse(200, content))
    got = await agent._judge_sticker_aesthetic(PNG)
    check(f"aesthetic parse {content!r}", got is expected, repr(got))


async def test_vision_aesthetic_retries_429_only(sleeps) -> None:
    agent = VisionHarness(None, *[VisionResponse(429)] * 4)
    got = await agent._judge_sticker_aesthetic(PNG)
    check("aesthetic 429: None after the last try", got is None, repr(got))
    check("aesthetic 429: four tries", len(agent.vision.posts) == 4,
          repr(len(agent.vision.posts)))
    check("aesthetic 429: 3, 6, 12 s backoff", sleeps == [3.0, 6.0, 12.0], repr(sleeps))

    agent = VisionHarness(None, VisionResponse(429), VisionResponse(429),
                          VisionResponse(200, '{"tacky": false}'))
    sleeps.clear()
    got = await agent._judge_sticker_aesthetic(PNG)
    check("aesthetic 429: a later success is used", got is False, repr(got))
    check("aesthetic 429: two backoffs before it", sleeps == [3.0, 6.0], repr(sleeps))


@pytest.mark.parametrize("status", [400, 401, 500, 503])
async def test_vision_aesthetic_gives_up_on_other_statuses(status, sleeps) -> None:
    agent = VisionHarness(None, VisionResponse(status))
    got = await agent._judge_sticker_aesthetic(PNG)
    check(f"aesthetic {status}: None", got is None, repr(got))
    check(f"aesthetic {status}: a single try", len(agent.vision.posts) == 1)
    check(f"aesthetic {status}: no backoff", sleeps == [], repr(sleeps))


async def test_vision_aesthetic_does_not_retry_transport_errors(sleeps) -> None:
    import httpx

    agent = VisionHarness(None, httpx.ReadTimeout("slow"))
    got = await agent._judge_sticker_aesthetic(PNG)
    check("aesthetic error: None", got is None, repr(got))
    check("aesthetic error: a single try", len(agent.vision.posts) == 1)
    check("aesthetic error: no backoff", sleeps == [], repr(sleeps))


@pytest.mark.parametrize("image", [
    b"",
    PNG[:199],
    b"\x89PNG\r\n\x1a\n" + b"p" * 5_000_000,
    BMP,
    HEIC,
    AVIF,
    UNKNOWN,
], ids=["empty", "tiny", "huge", "bmp", "heic", "avif", "unknown"])
async def test_vision_aesthetic_skips_unusable_images(image, sleeps) -> None:
    agent = VisionHarness(None)
    got = await agent._judge_sticker_aesthetic(image)
    check("aesthetic skip: no verdict", got is None, repr(got))
    check("aesthetic skip: nothing posted", agent.vision.posts == [])


async def test_vision_aesthetic_sends_a_gif_as_its_first_frame(sleeps) -> None:
    agent = VisionHarness(None, VisionResponse(200, '{"tacky": false}'))
    agent._gif_first_frame_png = lambda data: FRAME if data == GIF else b""
    got = await agent._judge_sticker_aesthetic(GIF)
    sent = agent.vision.posts[0]["json"]["messages"][0]["content"][1]
    check("aesthetic gif: judged", got is False, repr(got))
    check("aesthetic gif: first frame sent as PNG",
          sent["image_url"]["url"] == _data_url("image/png", FRAME))

    agent = VisionHarness(None)
    agent._gif_first_frame_png = lambda data: b""
    got = await agent._judge_sticker_aesthetic(GIF)
    check("aesthetic gif: a failed decode is no verdict", got is None, repr(got))
    check("aesthetic gif: and nothing is posted", agent.vision.posts == [])


async def test_vision_real_gif_decodes_to_png(sleeps) -> None:
    from PIL import Image

    source = io.BytesIO()
    Image.new("P", (32, 32), color=1).save(source, format="GIF")
    gif = source.getvalue() + b"\x00" * 200
    agent = VisionHarness(gif, VisionResponse(200, "a cat on a mat"))
    await agent._describe_image_vision(IMAGE_URL)
    url = agent.vision.posts[0]["json"]["messages"][0]["content"][1]["image_url"]["url"]
    sent = base64.b64decode(url.split(",", 1)[1])
    check("real gif: sent as a PNG data URL",
          url.startswith("data:image/png;base64,") and sent.startswith(b"\x89PNG"))


@pytest.mark.parametrize("path", ["caption", "aesthetic"])
async def test_vision_requests_apply_the_reasoning_quirks(path, sleeps) -> None:
    agent = VisionHarness(PNG, VisionResponse(200, '{"tacky": false}'))
    agent.vision_base_url = "https://openrouter.ai/api/v1"
    if path == "caption":
        await agent._describe_image_vision(IMAGE_URL)
    else:
        await agent._judge_sticker_aesthetic(PNG)
    payload = agent.vision.posts[0]["json"]
    check(f"{path}: OpenRouter reasoning switched off",
          payload.get("reasoning") == {"enabled": False}, repr(payload.get("reasoning")))

    agent = VisionHarness(PNG, VisionResponse(200, '{"tacky": false}'))
    agent.vision_model = "kimi-k2.6"
    if path == "caption":
        await agent._describe_image_vision(IMAGE_URL)
    else:
        await agent._judge_sticker_aesthetic(PNG)
    payload = agent.vision.posts[0]["json"]
    check(f"{path}: K2 thinking off at its fixed temperature",
          payload.get("thinking") == {"type": "disabled"}
          and payload.get("temperature") == 0.6, repr(payload)[:200])


# ---------------------------------------------------------------------------
# Through the real agent
# ---------------------------------------------------------------------------

def make_agent(tmp: Path) -> Agent:
    # OCR is delegated to NapCat, so the agent needs an address for it.
    return isolated_agent(tmp, qq_onebot_url=CLOSED_ONEBOT_URL)


async def test_b64_image_fetch(tmp: Path) -> None:
    """base64:// pseudo-URLs (b64-only connector inbound images) decode to
    bytes locally instead of being routed through httpx."""
    agent = make_agent(tmp)
    raw = b"\x89PNG\r\n\x1a\nxx"
    data = await agent._fetch_image_bytes("base64://" + base64.b64encode(raw).decode())
    check("b64 fetch: decodes inline data", data == raw, repr(data))
    bad = await agent._fetch_image_bytes("base64://QQ")  # bad padding
    check("b64 fetch: invalid data returns None", bad is None, repr(bad))


async def test_bounded_image_inputs(tmp: Path) -> None:
    """Every image source is bounded, contained, and signature-validated."""
    agent = make_agent(tmp)
    png = b"\x89PNG\r\n\x1a\n" + b"x" * 32
    allowed_dir = tmp / "napcat-cache"
    allowed_dir.mkdir(parents=True)
    inside = allowed_dir / "inside.png"
    inside.write_bytes(png)
    outside = tmp / "outside.png"
    outside.write_bytes(png)

    old_dir = os.environ.pop("QQ_ONEBOT_IMAGE_DIR", None)
    try:
        data = await agent._fetch_image_bytes(outside.as_uri())
        check("file image: unset allowlist rejects",
              data is None, repr(data))

        os.environ["QQ_ONEBOT_IMAGE_DIR"] = str(allowed_dir)
        data = await agent._fetch_image_bytes(inside.as_uri())
        check("file image: configured directory accepted",
              data == png, repr(data))
        data = await agent._fetch_image_bytes(outside.as_uri())
        check("file image: outside configured directory rejected",
              data is None, repr(data))

        link = allowed_dir / "escape.png"
        try:
            link.symlink_to(outside)
        except OSError:
            link = None
        if link is not None:
            data = await agent._fetch_image_bytes(link.as_uri())
            check("file image: symlink escape rejected",
                  data is None, repr(data))
    finally:
        if old_dir is None:
            os.environ.pop("QQ_ONEBOT_IMAGE_DIR", None)
        else:
            os.environ["QQ_ONEBOT_IMAGE_DIR"] = old_dir

    oversized = b"\x89PNG\r\n\x1a\n" + b"x" * 5_000_000
    encoded = base64.b64encode(oversized).decode()
    data = await agent._fetch_image_bytes("base64://" + encoded)
    check("base64 image: oversized payload rejected",
          data is None, None if data is None else str(len(data)))

    text_data = base64.b64encode(b"this is not an image").decode()
    data = await agent._fetch_image_bytes("base64://" + text_data)
    check("base64 image: unknown format rejected", data is None, repr(data))

    class _StreamResponse:
        status_code = 200
        headers = {}

        async def aiter_bytes(self):
            yield b"\x89PNG\r\n\x1a\n"
            yield b"x" * 3_000_000
            yield b"x" * 3_000_000

    class _StreamContext:
        async def __aenter__(self):
            return _StreamResponse()

        async def __aexit__(self, *exc):
            return False

    class _FakeHTTP:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        def stream(self, *args, **kwargs):
            return _StreamContext()

        async def get(self, *args, **kwargs):
            response = _StreamResponse()
            response.content = (
                b"\x89PNG\r\n\x1a\n" + b"x" * 6_000_000)
            return response

    agent._http = lambda **kwargs: _FakeHTTP()
    data = await agent._fetch_image_bytes("https://image.invalid/large.png")
    check("http image: streamed overflow rejected",
          data is None, None if data is None else str(len(data)))


def test_host_is_internal() -> None:
    """SSRF guard: internal / cloud-metadata / RFC1918 (incl. 172.17-31 that a
    substring blacklist would miss) / IPv6 must be blocked; public hosts pass."""
    A = Agent
    for u in ("http://169.254.169.254/latest/meta-data/", "http://127.0.0.1:3000/x",
              "http://localhost/x", "http://192.168.1.10/x", "http://10.0.0.5/x",
              "http://172.17.0.1/x", "http://[::1]/x"):
        check(f"ssrf: blocks {u}", A._host_is_internal(u) is True, u)
    for u in ("https://example.com/page", "https://www.bilibili.com/video/BV1x"):
        check(f"ssrf: allows {u}", A._host_is_internal(u) is False, u)
    check("ssrf: ext skip still fires", A._should_skip_url("https://example.com/a.zip") is True)
    # Reserved names must be rejected by name, without a lookup.
    for u in ("http://LOCALHOST./x", "http://a.localhost/x",
              "http://ip6-localhost/x", "http://localhost.localdomain/x"):
        check(f"ssrf: blocks reserved name {u}", A._host_is_internal(u) is True, u)


def test_host_is_internal_never_resolves() -> None:
    """The pre-filter must not touch the resolver.

    It used to call socket.getaddrinfo synchronously inside a coroutine, so one
    posted URL whose nameserver blackholes froze the whole event loop for the
    resolver timeout. The security boundary is _resolve_public_target, which
    resolves off-thread, refuses any internal answer and pins the address —
    resolving here bought nothing and could not close the rebinding window.
    A side effect worth keeping: this test no longer depends on the network."""
    calls: list[str] = []
    real = socket.getaddrinfo

    def spy(host, *a, **k):
        calls.append(str(host))
        return real(host, *a, **k)

    socket.getaddrinfo = spy
    try:
        for u in ("https://example.com/page", "http://some-name.invalid/x",
                  "http://127.0.0.1/x", "http://localhost/x"):
            Agent._host_is_internal(u)
            Agent._should_skip_url(u)
    finally:
        socket.getaddrinfo = real
    check("ssrf pre-filter performs no DNS lookup", calls == [], repr(calls))


async def test_ocr_delegation_is_ssrf_gated(tmp: Path) -> None:
    """The OCR fallback hands a URL to the protocol client, which fetches it
    with no SSRF controls of its own — a delegated fetch, so it must be gated
    here. It runs exactly when the direct fetch failed, and for an internal URL
    that failure is guaranteed, so an ungated fallback converted every SSRF
    refusal into an SSRF success by proxy, with the fetched text reflected back
    into the group buffer and the prompt."""
    agent = make_agent(tmp)
    posts: list = []

    class _Resp:
        status_code = 200

        def raise_for_status(self) -> None:
            pass

        def json(self):
            return {"data": [{"text": "SECRET"}]}

    class _HTTP:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, **kw):
            posts.append((kw.get("json") or {}).get("image"))
            return _Resp()

    # NapCat is reached through _local_http; both clients are spied on.
    agent._http = agent._local_http = lambda **kw: _HTTP()
    for u in ("http://169.254.169.254/latest/meta-data/",
              "http://127.0.0.1:6099/api/token",
              "http://localhost/x",
              "file:///C:/Windows/win.ini"):
        out = await agent._ocr_image(u)
        check(f"ocr: refuses delegation for {u[:32]}", out == "", repr(out))
    check("ocr: nothing forwarded to the protocol client", posts == [], repr(posts))


def _link_payload(*segments: dict) -> dict:
    return {"post_type": "message", "message_type": "group",
            "group_id": "1", "user_id": "42",
            "sender": {"nickname": "Mallory"}, "message": list(segments)}


async def test_link_enrichment_capped_and_concurrent(tmp: Path) -> None:
    """A message packed with URLs is one bounded, concurrent fetch step, not
    one fetch per URL in sequence: each is an outbound request from the bot's
    own IP to a host the sender picks, and in sequence their timeouts add up
    into a stalled turn."""
    agent = make_agent(tmp)
    delay = 0.25
    calls: list[str] = []
    starts: list[float] = []

    async def slow_describe(url: str) -> str:
        calls.append(url)
        starts.append(time.monotonic())
        await asyncio.sleep(delay)
        # Distinct from the raw URL, which the text segment already carries.
        return f"[site] enriched-{url.rsplit('/', 1)[-1]}"

    agent._describe_url = slow_describe
    cap = agent.MAX_URLS_PER_MESSAGE
    urls = [f"https://example.com/{i}" for i in range(50)]
    t0 = time.monotonic()
    result = await agent._extract_text(_link_payload(
        {"type": "text", "data": {"text": " ".join(urls)}}))
    elapsed = time.monotonic() - t0

    check("link cap: only the first MAX_URLS_PER_MESSAGE URLs are fetched",
          calls == urls[:cap], repr(calls))
    found = [result.find(f"enriched-{i}") for i in range(cap)]
    check("link cap: their descriptors reach the model, in order",
          -1 not in found and found == sorted(found), repr(result))
    check("link cap: URLs beyond the cap get no descriptor",
          f"enriched-{cap}" not in result, repr(result))
    # In sequence the fetches take `cap` delays; concurrently about one.
    check("link cap: fetches run concurrently, not serially",
          elapsed < delay * cap * 0.6 and max(starts) - min(starts) < delay * 0.5,
          f"elapsed={elapsed:.3f}")


async def test_link_enrichment_cap_is_per_message_not_per_segment(
        tmp: Path) -> None:
    """An inline @mention splits one paste into two text segments; the cap
    must not multiply with the number of segments a sender produces."""
    agent = make_agent(tmp)
    calls: list[str] = []

    async def fake_describe(url: str) -> str:
        calls.append(url)
        return f"[site] {url}"

    agent._describe_url = fake_describe
    first = [f"https://a.example/{i}" for i in range(4)]
    second = [f"https://b.example/{i}" for i in range(4)]
    await agent._extract_text(_link_payload(
        {"type": "text", "data": {"text": " ".join(first)}},
        {"type": "at", "data": {"qq": "999"}},
        {"type": "text", "data": {"text": " ".join(second)}}))
    check("link cap: counted across every text segment of the message",
          calls == first[:agent.MAX_URLS_PER_MESSAGE], repr(calls))

    calls.clear()
    await agent._extract_text(_link_payload(
        {"type": "text", "data": {"text": first[0]}},
        {"type": "at", "data": {"qq": "999"}},
        {"type": "text", "data": {"text": " ".join(second)}}))
    check("link cap: a later segment gets what an earlier one left",
          calls == [first[0]] + second[:agent.MAX_URLS_PER_MESSAGE - 1],
          repr(calls))


async def test_link_enrichment_budget_caps_total_wait(tmp: Path) -> None:
    """A tarpit host cannot hold the turn past LINK_ENRICHMENT_BUDGET_SEC,
    and a link that did answer in time keeps its descriptor."""
    agent = make_agent(tmp)
    agent.LINK_ENRICHMENT_BUDGET_SEC = 0.2
    cancelled: list[str] = []

    async def describe(url: str) -> str:
        if "tarpit" not in url:
            return "[site] answered in time"
        try:
            await asyncio.sleep(30)
        except asyncio.CancelledError:
            cancelled.append(url)
            raise
        return "[site] should never surface"

    agent._describe_url = describe
    t0 = time.monotonic()
    result = await agent._extract_text(_link_payload({"type": "text", "data": {
        "text": "https://tarpit.example/x https://fast.example/y"}}))
    elapsed = time.monotonic() - t0
    check("link budget: the step gives up at the budget, not the fetch's delay",
          elapsed < 5.0, f"elapsed={elapsed:.3f}")
    check("link budget: no descriptor from the timed-out fetch",
          "should never surface" not in result, repr(result))
    check("link budget: the straggler is cancelled, not left running",
          cancelled == ["https://tarpit.example/x"], repr(cancelled))
    check("link budget: a link that answered in time keeps its descriptor",
          "answered in time" in result, repr(result))

    # An @mention splits one paste into several text segments. The budget
    # and the concurrency are the message's: described per segment, three
    # tarpits waited three budgets, one segment after another.
    agent.LINK_ENRICHMENT_BUDGET_SEC = 0.3
    cancelled.clear()
    starts: list[float] = []

    async def describe_split(url: str) -> str:
        starts.append(time.monotonic())
        return await describe(url)

    agent._describe_url = describe_split
    at = {"type": "at", "data": {"qq": "999"}}
    t0 = time.monotonic()
    result = await agent._extract_text(_link_payload(
        {"type": "text", "data": {"text": "one https://tarpit.example/1"}}, at,
        {"type": "text", "data": {"text": "two https://tarpit.example/2"}}, at,
        {"type": "text", "data": {"text": "three https://fast.example/3"}}))
    elapsed = time.monotonic() - t0
    check("link budget: one budget per message, however it is split",
          elapsed < agent.LINK_ENRICHMENT_BUDGET_SEC * 1.8,
          f"elapsed={elapsed:.3f}")
    check("link budget: links in different segments are fetched together",
          len(starts) == 3 and max(starts) - min(starts) < 0.1, repr(starts))
    check("link budget: every segment's straggler is cancelled",
          sorted(cancelled) == ["https://tarpit.example/1",
                                "https://tarpit.example/2"], repr(cancelled))
    check("link budget: a descriptor still follows its own segment",
          result.find("three") < result.find("answered in time")
          and result.find("two") < result.find("three"), repr(result))


async def test_link_enrichment_survives_a_failing_fetch(tmp: Path) -> None:
    """One link raising must not take the message or its siblings with it."""
    agent = make_agent(tmp)

    async def describe(url: str) -> str:
        if "broken" in url:
            raise RuntimeError("boom")
        return "[site] fine"

    agent._describe_url = describe
    result = await agent._extract_text(_link_payload({"type": "text", "data": {
        "text": "look https://broken.example/x https://ok.example/y"}}))
    check("link enrichment: a raising fetch is dropped, siblings kept",
          "look" in result and "[site] fine" in result, repr(result))


async def test_share_card_type_confusion(tmp: Path) -> None:
    """Share-card JSON is fully sender-controlled: non-string fields (int
    prompt, dict title, list url) must degrade to a placeholder instead of
    raising out of _extract_text and dropping the whole inbound message."""
    import json as _json
    agent = make_agent(tmp)
    bad_card = _json.dumps({
        "prompt": 123,
        "meta": {"news": {"title": {"a": 1}, "desc": 5, "qqdocurl": ["x"]}},
    })
    desc = await agent._describe_share(bad_card)
    check("share card: non-string fields degrade, no crash",
          isinstance(desc, str), repr(desc))
    # Non-dict detail with a non-string prompt (old code: 123[:80] TypeError).
    desc2 = await agent._describe_share(
        _json.dumps({"prompt": 123, "meta": {"news": "notadict"}}))
    check("share card: non-dict detail + int prompt degrades",
          desc2 == "", repr(desc2))
    # The whole message must survive: the text segment stays extractable.
    payload = {
        "post_type": "message", "message_type": "group", "group_id": "123",
        "user_id": "42", "sender": {"nickname": "Alice"},
        "message": [
            {"type": "text", "data": {"text": "look at this"}},
            {"type": "json", "data": {"data": bad_card}},
        ],
        "raw_message": "look at this",
    }
    text = await agent._extract_text(payload)
    check("share card: sibling text segment survives a malformed card",
          "look at this" in text, repr(text))


async def test_b64_caption_cache_key(tmp: Path) -> None:
    """Connector base64:// pseudo-URLs must be hashed before use as caption-cache
    keys — the raw string can be multiple MB of base64 per entry."""
    agent = make_agent(tmp)
    big = "base64://" + "A" * 100_000
    got = agent._accept_vision_caption(big, "a cute cat sticker", "test")
    check("b64 cache: caption accepted", got == "a cute cat sticker", repr(got))
    check("b64 cache: no raw base64 keys retained",
          all(not k.startswith("base64://") for k in agent.image_caption_cache),
          repr([k[:40] for k in agent.image_caption_cache]))
    check("b64 cache: keys stay small",
          all(len(k) < 200 for k in agent.image_caption_cache),
          repr([len(k) for k in agent.image_caption_cache]))
    # The hashed key must still round-trip as a cache hit.
    hit = await agent._describe_image(big)
    check("b64 cache: hashed key round-trips", hit == "a cute cat sticker", repr(hit))


async def test_a_failed_vision_call_is_not_cached_as_a_miss(tmp: Path) -> None:
    """A miss is cached only when vision and OCR both answered. A vision outage
    cached as "" would leave every image seen during it undescribed for good."""
    agent = make_agent(tmp)
    agent.vision_model, agent.vision_api_key, agent.vision_base_url = "v", "k", "http://v"
    url = "https://example.com/a.png"
    key = agent._image_cache_key(url)

    async def vision_down(_url):
        return None

    async def ocr_down(_url):
        return ""

    agent._describe_image_vision, agent._ocr_image = vision_down, ocr_down
    got = await agent._describe_image(url)
    check("vision cache: an outage yields no caption", got == "", repr(got))
    check("vision cache: an outage is not cached", key not in agent.image_caption_cache)

    async def vision_empty(_url):
        return ""

    async def ocr_garbage(_url):
        agent.image_caption_cache[key] = "a b"   # what _ocr_image caches on a reply
        return "a b"

    agent._describe_image_vision, agent._ocr_image = vision_empty, ocr_garbage
    await agent._describe_image(url)
    check("vision cache: a miss both channels answered is cached",
          agent.image_caption_cache.get(key) == "", repr(agent.image_caption_cache.get(key)))


async def test_ssrf_redirect_hops(tmp: Path) -> None:
    """A public URL that 302s to an internal address must be refused at the
    redirect hop (the initial-URL _host_is_internal check can't see it), while
    public->public redirects keep working."""
    agent = make_agent(tmp)
    fetched: list[str] = []

    class _Resp:
        def __init__(self, status, headers=None, content=b"", url=""):
            self.status_code = status
            self.headers = headers or {}
            self.content = content
            self.url = url
            self.text = ""

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def aiter_bytes(self):
            yield self.content

    class _FakeHTTP:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def get(self, url, headers=None):
            return self._response(url)

        def stream(self, method, url, headers=None, follow_redirects=False):
            return self._response(url)

        def _response(self, url):
            fetched.append(url)
            if url == "http://evil.invalid/img":  # public host, hostile redirect
                return _Resp(302, {"location": "http://127.0.0.1:3000/send_group_msg?group_id=1"})
            if url == "http://hop.invalid/a":  # public host, relative redirect
                return _Resp(302, {"location": "/b"})
            return _Resp(200, content=b"\x89PNG\r\n\x1a\nIMGDATA", url=url)

    agent._http = lambda **kw: _FakeHTTP()
    data = await agent._fetch_image_bytes("http://evil.invalid/img")
    check("ssrf redirect: 302->internal returns None", data is None, repr(data))
    check("ssrf redirect: internal target never fetched",
          all("127.0.0.1" not in u for u in fetched), repr(fetched))
    fetched.clear()
    data2 = await agent._fetch_image_bytes("http://hop.invalid/a")
    check("ssrf redirect: public relative redirect still followed",
          data2 == b"\x89PNG\r\n\x1a\nIMGDATA"
          and fetched == ["http://hop.invalid/a", "http://hop.invalid/b"],
          repr((data2, fetched)))
