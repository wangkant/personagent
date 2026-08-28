"""Tests for bounded webhook request-body reads.

Run from the repo root with no test framework required:

    python tests/test_http.py
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import logging.handlers
import tempfile
import time
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import main as main_module  # noqa: E402
import httpx  # noqa: E402
from main import RequestBodyTooLarge, _read_body_limited  # noqa: E402
from persona_agent import learning as learning_module  # noqa: E402

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


def test_exposure_guard_fails_closed() -> None:
    guard = getattr(main_module, "_validate_exposure_config", None)
    check("exposure guard exists", callable(guard))
    if not callable(guard):
        return
    try:
        guard("0.0.0.0", "", "")
    except ValueError:
        rejected = True
    else:
        rejected = False
    check("public bind without both secrets rejected", rejected)
    try:
        guard("127.0.0.1", "", "")
        loopback_ok = True
    except ValueError:
        loopback_ok = False
    check("loopback bind permits local unauthenticated deployment", loopback_ok)
    peer_guard = getattr(main_module, "_request_peer_is_allowed", None)
    check("request peer guard exists", callable(peer_guard))
    if callable(peer_guard):
        check("request peer: loopback may use empty secret",
              peer_guard("127.0.0.1", "") is True)
        check("request peer: remote may not use empty secret",
              peer_guard("203.0.113.10", "") is False)
        check("request peer: authenticated remote is allowed",
              peer_guard("203.0.113.10", "secret") is True)


def test_numeric_config_parser_is_bounded() -> None:
    parser = getattr(main_module, "_parse_int_config", None)
    check("numeric config parser exists", callable(parser))
    if not callable(parser):
        return
    check("numeric config: invalid value uses default",
          parser("PORT", "not-a-number", 8080, minimum=1, maximum=65535) == 8080)
    check("numeric config: out-of-range value uses default",
          parser("PORT", "70000", 8080, minimum=1, maximum=65535) == 8080)
    check("numeric config: valid value accepted",
          parser("PORT", "9000", 8080, minimum=1, maximum=65535) == 9000)


def test_import_has_no_file_logging_side_effect() -> None:
    handlers = logging.getLogger().handlers
    check("main import does not open a repository log file",
          not any(isinstance(h, logging.handlers.RotatingFileHandler)
                  for h in handlers),
          repr(handlers))


async def test_admission_limiter_is_bounded() -> None:
    limiter_cls = getattr(main_module, "AdmissionLimiter", None)
    check("admission limiter exists", limiter_cls is not None)
    if limiter_cls is None:
        return
    limiter = limiter_cls(2)
    first = await limiter.try_acquire()
    second = await limiter.try_acquire()
    third = await limiter.try_acquire()
    check("admission limiter rejects overflow",
          first and second and not third, repr((first, second, third)))
    await limiter.release()
    check("admission limiter admits after release",
          await limiter.try_acquire())


async def test_public_health_is_a_cheap_liveness_check() -> None:
    original = main_module.run_checks

    def fail_if_called():
        raise AssertionError("public health must not run paid probes")

    main_module.run_checks = fail_if_called
    try:
        response = await main_module.health()
        check("public health avoids paid diagnostics",
              isinstance(response, dict)
              and response.get("status") == "ok",
              repr(response))
    finally:
        main_module.run_checks = original


async def test_asgi_webhook_auth_and_schema() -> None:
    original_secret = main_module.WEBHOOK_SECRET
    original_token = main_module.GATEWAY_TOKEN
    original_agent = main_module.agent
    original_replay = main_module._gateway_replay
    main_module.WEBHOOK_SECRET = "qq-secret"
    main_module.GATEWAY_TOKEN = "gateway-secret"
    main_module.agent = None
    main_module._gateway_replay = main_module.ReplayGuard()
    transport = httpx.ASGITransport(app=main_module.app)
    try:
        async with httpx.AsyncClient(
                transport=transport, base_url="http://test") as client:
            qq_event = {
                "post_type": "message", "message_type": "group",
                "group_id": "g", "user_id": "u", "message_id": "m1",
                "message": [], "time": int(time.time()),
            }
            qq_body = json.dumps(
                qq_event, separators=(",", ":")).encode()
            bad = await client.post(
                "/webhook/qq", content=qq_body,
                headers={"x-signature": "sha1=bad"})
            qq_sig = "sha1=" + hmac.new(
                b"qq-secret", qq_body, hashlib.sha1).hexdigest()
            good = await client.post(
                "/webhook/qq", content=qq_body,
                headers={"x-signature": qq_sig})

            gateway_event = {
                "platform": "telegram", "message_type": "group",
                "conversation_id": "g", "user_id": "u",
                "message_id": "m2", "segments": [],
                "source_timestamp": int(time.time()),
            }
            gateway_body = json.dumps(
                gateway_event, separators=(",", ":")).encode()
            stamp = str(int(time.time()))
            nonce = "asgi-nonce"
            gateway_sig = "sha256=" + hmac.new(
                b"gateway-secret",
                stamp.encode() + b"." + nonce.encode() + b"." + gateway_body,
                hashlib.sha256,
            ).hexdigest()
            gw = await client.post(
                "/webhook/gateway", content=gateway_body,
                headers={
                    "x-gateway-token": "gateway-secret",
                    "x-gateway-timestamp": stamp,
                    "x-gateway-nonce": nonce,
                    "x-gateway-signature": gateway_sig,
                })
        check("ASGI auth: invalid QQ signature rejected", bad.status_code == 403)
        check("ASGI auth: valid QQ envelope accepted", good.status_code == 200)
        check("ASGI auth: valid gateway envelope accepted",
              gw.status_code == 200 and gw.json() == {
                  "handled": False, "replies": []}, repr(gw.text))
    finally:
        main_module.WEBHOOK_SECRET = original_secret
        main_module.GATEWAY_TOKEN = original_token
        main_module.agent = original_agent
        main_module._gateway_replay = original_replay


def test_gateway_envelope_rejects_replay_and_stale_requests() -> None:
    verifier = getattr(main_module, "_verify_gateway_envelope", None)
    guard_cls = getattr(main_module, "ReplayGuard", None)
    check("gateway signed-envelope verifier exists",
          callable(verifier) and guard_cls is not None)
    if not callable(verifier) or guard_cls is None:
        return
    token = "shared-secret"
    body = b'{"message_id":"m1"}'
    now = int(time.time())
    nonce = "nonce-1"
    stamp = str(now)
    digest = hmac.new(
        token.encode(),
        stamp.encode() + b"." + nonce.encode() + b"." + body,
        hashlib.sha256,
    ).hexdigest()
    headers = {
        "x-gateway-token": token,
        "x-gateway-timestamp": stamp,
        "x-gateway-nonce": nonce,
        "x-gateway-signature": "sha256=" + digest,
    }
    replay = guard_cls(ttl_seconds=300, max_entries=16)
    first = verifier(body, headers, token, now=now, replay_guard=replay)
    second = verifier(body, headers, token, now=now, replay_guard=replay)
    stale_headers = dict(headers)
    stale_headers["x-gateway-nonce"] = "nonce-2"
    stale_headers["x-gateway-timestamp"] = str(now - 301)
    stale_digest = hmac.new(
        token.encode(),
        stale_headers["x-gateway-timestamp"].encode()
        + b"." + stale_headers["x-gateway-nonce"].encode() + b"." + body,
        hashlib.sha256,
    ).hexdigest()
    stale_headers["x-gateway-signature"] = "sha256=" + stale_digest
    stale = verifier(
        body, stale_headers, token, now=now, replay_guard=replay)
    check("gateway signed envelope: first request accepted", first is True, repr(first))
    check("gateway signed envelope: nonce replay rejected", second is False, repr(second))
    check("gateway signed envelope: stale request rejected", stale is False, repr(stale))

    with tempfile.TemporaryDirectory() as td:
        state_file = Path(td) / "gateway_nonces.json"
        persisted = guard_cls(
            ttl_seconds=300, max_entries=2, state_file=state_file)
        first_persisted = verifier(
            body, headers, token, now=now, replay_guard=persisted)
        reloaded = guard_cls(
            ttl_seconds=300, max_entries=2, state_file=state_file)
        after_restart = verifier(
            body, headers, token, now=now, replay_guard=reloaded)
        check("gateway replay cache persists across restart",
              first_persisted is True and after_restart is False,
              repr((first_persisted, after_restart)))

        full = guard_cls(ttl_seconds=300, max_entries=1)
        first_full = verifier(body, headers, token, now=now, replay_guard=full)
        second_headers = dict(headers)
        second_headers["x-gateway-nonce"] = "nonce-full-2"
        second_digest = hmac.new(
            token.encode(),
            stamp.encode() + b"." + b"nonce-full-2" + b"." + body,
            hashlib.sha256,
        ).hexdigest()
        second_headers["x-gateway-signature"] = "sha256=" + second_digest
        second_full = verifier(
            body, second_headers, token, now=now, replay_guard=full)
        check("gateway replay cache sheds new work instead of evicting fresh nonce",
              first_full is True and second_full is False,
              repr((first_full, second_full)))


#: Read by the code on purpose and kept OUT of the template. Every entry
#: weakens the typo check, so each one states why it is worth that.
_UNDOCUMENTED_SETTINGS = {
    # A pre-0.1.2 alias kept working for existing deployments and
    # deliberately not advertised to new ones.
    "ANTHROPIC_PRIVATE_MODEL",
}


def test_every_setting_the_code_reads_is_in_the_template() -> None:
    """`.env.example` is the authority on what a key may be CALLED.

    `preflight.check_config` reports anything in `.env` that the template does
    not list, because a misspelled key is otherwise completely silent — the
    value is ignored, the default is used, and the bot runs and misbehaves
    with no clue anywhere. That check is only honest while the template
    actually covers what the code reads: a setting the code reads and the
    template omits would be reported to its operator as a typo.

    Scanned rather than listed, so the two cannot drift apart again. `os.getenv`
    and `os.environ.get` only — `Policy.from_env` reads through a dict
    parameter and is out of reach of a syntactic scan, which is a gap worth
    naming rather than pretending away."""
    import ast

    # `tools/` AND the root entry points, not just the package. Scanning only
    # `main.py` and `persona_agent/` left nine real settings undocumented —
    # `ANTHROPIC_API_KEY` and `PROMPT_LAB_MODEL` among them, which
    # `tools/prompt_lab.py` explicitly tells the operator to put in `.env` —
    # and the preflight then reported every one of them as a misspelling.
    root = Path(__file__).resolve().parents[1]
    sources = [
        root / "main.py", root / "try_chat.py", root / "quickstart.py",
        *sorted((root / "persona_agent").glob("*.py")),
        *sorted((root / "tools").glob("*.py")),
    ]

    def is_env_read(call: ast.Call) -> bool:
        fn = call.func
        if not isinstance(fn, ast.Attribute):
            return False
        if fn.attr == "getenv":
            return isinstance(fn.value, ast.Name) and fn.value.id == "os"
        if fn.attr == "get":
            inner = fn.value
            return (isinstance(inner, ast.Attribute) and inner.attr == "environ"
                    and isinstance(inner.value, ast.Name)
                    and inner.value.id == "os")
        return False

    read: dict[str, str] = {}
    for path in sources:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and is_env_read(node)):
                continue
            if not node.args or not isinstance(node.args[0], ast.Constant):
                continue
            key = node.args[0].value
            if isinstance(key, str) and key.isupper():
                read.setdefault(key, f"{path.name}:{node.lineno}")

    check("template scan found the settings at all", len(read) > 20, str(len(read)))

    template = (root / ".env.example").read_text(encoding="utf-8")
    documented = {
        line.split("=", 1)[0].strip()
        for line in template.splitlines()
        if "=" in line and not line.lstrip().startswith("#")
    }
    missing = sorted(
        f"{key} ({where})" for key, where in read.items()
        if key not in documented and key not in _UNDOCUMENTED_SETTINGS)
    check("every setting the code reads is documented in .env.example",
          not missing,
          "; ".join(missing))


def test_gateway_envelope_refuses_a_bad_signature() -> None:
    """The signature is what binds the BODY to the token. Nothing tested it.

    Every other envelope test supplies a correctly computed signature and
    varies something else — replay, staleness, persistence, cache pressure —
    so `if not hmac.compare_digest(supplied_signature, expected)` could be
    replaced with `if False:` and the whole suite stayed green. Measured, by
    mutation. The QQ webhook has its negative case (`ASGI auth: invalid QQ
    signature rejected`); this one did not, and without the binding a bearer
    token seen once in a log or a proxy is enough to inject arbitrary chat
    events with no tie to the payload at all.

    EVERY CASE GETS A FRESH NONCE AND A FRESH GUARD, and the control below
    proves why that matters: reuse either and the refusal comes from the
    replay guard instead, which is a test that passes for the wrong reason —
    the failure mode this suite has already been bitten by twice."""
    verifier = main_module._verify_gateway_envelope
    guard_cls = main_module.ReplayGuard
    token = "shared-secret"
    body = b'{"message_id":"m1","text":"hello"}'
    now = int(time.time())

    def sign(payload: bytes, nonce: str, stamp: str, key: str = token) -> str:
        return "sha256=" + hmac.new(
            key.encode("utf-8"),
            stamp.encode("ascii") + b"." + nonce.encode("utf-8") + b"." + payload,
            hashlib.sha256).hexdigest()

    def envelope(nonce: str, *, sig: str | None = None, stamp: str | None = None):
        stamp = stamp or str(now)
        return {
            "x-gateway-token": token,
            "x-gateway-timestamp": stamp,
            "x-gateway-nonce": nonce,
            "x-gateway-signature": (sign(body, nonce, stamp) if sig is None
                                    else sig),
        }

    def verdict(headers, payload=body) -> bool:
        # A guard per call: a shared one would let a replay refusal stand in
        # for a signature refusal and every case below would "pass".
        return verifier(payload, headers, token, now=now,
                        replay_guard=guard_cls(ttl_seconds=300, max_entries=16))

    # The control. If this is not True the rest proves nothing.
    check("gateway signature: a correct envelope is accepted",
          verdict(envelope("ctl")) is True)

    cases = {
        "a forged signature": envelope("n1", sig="sha256=" + "0" * 64),
        "an absent signature": {k: v for k, v in envelope("n2").items()
                                if k != "x-gateway-signature"},
        "an empty signature": envelope("n3", sig=""),
        "the digest without its prefix":
            envelope("n4", sig=sign(body, "n4", str(now))[len("sha256="):]),
        "a signature made with the wrong key":
            envelope("n5", sig=sign(body, "n5", str(now), key="not-the-token")),
    }
    for label, headers in cases.items():
        check(f"gateway signature: {label} is refused",
              verdict(headers) is False, repr(headers.get("x-gateway-signature")))

    # The BINDING, one field at a time: a signature that is valid for some
    # other request must not travel. These are the shapes an attacker who can
    # see one signed request actually has.
    check("gateway signature: does not travel to a different body",
          verdict(envelope("n6"), payload=b'{"message_id":"m1","text":"drop table"}')
          is False)
    tampered_nonce = envelope("n7")
    tampered_nonce["x-gateway-nonce"] = "n7-swapped"
    check("gateway signature: does not survive a swapped nonce",
          verdict(tampered_nonce) is False)
    tampered_stamp = envelope("n8")
    tampered_stamp["x-gateway-timestamp"] = str(now - 1)
    check("gateway signature: does not survive a swapped timestamp",
          verdict(tampered_stamp) is False)

    # And the token check is still its own gate, not a side effect of the
    # signature matching.
    wrong_token = envelope("n9")
    wrong_token["x-gateway-token"] = "wrong"
    check("gateway signature: the bearer token is checked separately",
          verdict(wrong_token) is False)


def test_event_schema_requires_stable_message_ids() -> None:
    validator = getattr(main_module, "_validate_event_payload", None)
    check("event schema validator exists", callable(validator))
    if not callable(validator):
        return
    qq_missing = {
        "post_type": "message", "message_type": "group",
        "group_id": "1", "user_id": "2", "message": [],
    }
    qq_valid = dict(qq_missing, message_id="m1")
    gateway_missing = {
        "platform": "telegram", "message_type": "group",
        "conversation_id": "g", "user_id": "u", "segments": [],
    }
    gateway_valid = dict(
        gateway_missing, message_id="m2", source_timestamp=int(time.time()))
    check("event schema: QQ message without id rejected",
          validator(qq_missing, gateway=False) is False)
    check("event schema: QQ message with id accepted",
          validator(qq_valid, gateway=False) is True)
    check("event schema: gateway message without id rejected",
          validator(gateway_missing, gateway=True) is False)
    check("event schema: gateway message with id accepted",
          validator(gateway_valid, gateway=True) is True)
    check("event schema: gateway source timestamp required",
          validator(dict(gateway_valid, source_timestamp=None), gateway=True)
          is False)
    gateway_freshness = getattr(
        main_module, "_gateway_event_is_fresh", None)
    check("gateway source freshness validator exists",
          callable(gateway_freshness))
    if callable(gateway_freshness):
        now = int(time.time())
        check("gateway source freshness: current event accepted",
              gateway_freshness(
                  {"source_timestamp": now}, now=now,
                  max_age_seconds=300) is True)
        check("gateway source freshness: stale event rejected",
              gateway_freshness(
                  {"source_timestamp": now - 301}, now=now,
                  max_age_seconds=300) is False)
    freshness = getattr(main_module, "_onebot_event_is_fresh", None)
    check("OneBot freshness validator exists", callable(freshness))
    if callable(freshness):
        now = int(time.time())
        check("OneBot freshness: current event accepted",
              freshness({"time": now}, now=now) is True)
        check("OneBot freshness: missing timestamp rejected",
              freshness({}, now=now) is False)
        check("OneBot freshness: stale event rejected",
              freshness({"time": now - 301}, now=now) is False)


def test_startup_view_rebuild_can_fail_closed() -> None:
    dummy = SimpleNamespace(
        candidate_ledger=object(),
        promoted_examples_file=Path("unused-examples"),
        promoted_feedback_file=Path("unused-feedback"),
        examples_max_auto=10,
        feedback_max_auto=10,
    )
    original = learning_module.candidates.rebuild_views

    def fail(*_args, **_kwargs):
        raise OSError("disk unavailable")

    learning_module.candidates.rebuild_views = fail
    try:
        soft = learning_module.Learning._rebuild_promoted_views(dummy)
        raised = False
        try:
            learning_module.Learning._rebuild_promoted_views(
                dummy, strict=True)
        except OSError:
            raised = True
    finally:
        learning_module.candidates.rebuild_views = original
    check("promoted-view rebuild retains non-strict maintenance mode",
          soft == (-1, -1), repr(soft))
    check("startup promoted-view rebuild fails closed", raised)


async def main_async() -> None:
    await test_accepts_body_at_limit()
    await test_rejects_stream_over_limit_without_header()
    await test_rejects_large_content_length_before_stream()
    await test_invalid_content_length_still_streams_safely()
    test_exposure_guard_fails_closed()
    test_numeric_config_parser_is_bounded()
    test_import_has_no_file_logging_side_effect()
    await test_admission_limiter_is_bounded()
    await test_public_health_is_a_cheap_liveness_check()
    await test_asgi_webhook_auth_and_schema()
    test_gateway_envelope_rejects_replay_and_stale_requests()
    test_gateway_envelope_refuses_a_bad_signature()
    test_every_setting_the_code_reads_is_in_the_template()
    test_event_schema_requires_stable_message_ids()
    test_startup_view_rebuild_can_fail_closed()


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
