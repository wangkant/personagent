"""Tests for bounded webhook request-body reads.

Run from the repo root with no test framework required:

    python tests/test_http.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import RequestBodyTooLarge, _read_body_limited  # noqa: E402

_failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {name}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        _failures.append(name)


class FakeRequest:
    def __init__(self, chunks: list[bytes], headers: dict | None = None):
        self.chunks = chunks
        self.headers = headers or {}
        self.stream_reads = 0

    async def stream(self):
        for chunk in self.chunks:
            self.stream_reads += 1
            yield chunk


async def test_accepts_body_at_limit() -> None:
    body = await _read_body_limited(FakeRequest([b"ab", b"cd"]), 4)
    check("body at limit accepted", body == b"abcd", repr(body))


async def test_rejects_stream_over_limit_without_header() -> None:
    try:
        await _read_body_limited(FakeRequest([b"abc", b"de"]), 4)
    except RequestBodyTooLarge:
        check("stream over limit rejected", True)
    else:
        check("stream over limit rejected", False)


async def test_rejects_large_content_length_before_stream() -> None:
    request = FakeRequest([b"x"], headers={"content-length": "9"})
    try:
        await _read_body_limited(request, 8)
    except RequestBodyTooLarge:
        check("content-length over limit rejected", request.stream_reads == 0,
              repr(request.stream_reads))
    else:
        check("content-length over limit rejected", False)


async def test_invalid_content_length_still_streams_safely() -> None:
    request = FakeRequest([b"abc"], headers={"content-length": "not-a-number"})
    body = await _read_body_limited(request, 3)
    check("invalid content-length falls back to stream limit",
          body == b"abc" and request.stream_reads == 1,
          repr((body, request.stream_reads)))


async def main_async() -> None:
    await test_accepts_body_at_limit()
    await test_rejects_stream_over_limit_without_header()
    await test_rejects_large_content_length_before_stream()
    await test_invalid_content_length_still_streams_safely()


def main() -> int:
    asyncio.run(main_async())
    print()
    if _failures:
        print(f"{len(_failures)} test(s) FAILED: {', '.join(_failures)}")
        return 1
    print("all tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
