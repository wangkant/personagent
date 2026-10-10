"""Security regression tests for URL and image ingestion.

Run from the repo root:

    python -m pytest tests/test_ingestion.py
"""
from __future__ import annotations

import base64
import gzip
import io
import re
import socket
import time
from unittest.mock import patch

import pytest

from persona_agent.ingestion import ContentIngestion, safe_fetch_url
from tools.bootstrap_from_history import download_sticker


def check(name: str, cond: bool, detail: str = "") -> None:
    """Assert `cond`, naming the property so a failure reads as English.

    The suites state a property per line rather than one per function, and
    they keep saying it that way; this turns each statement into the assert
    pytest reports on."""
    assert cond, name + (f" - {detail}" if detail else "")


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
