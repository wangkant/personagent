"""Tests for bounded webhook request-body reads.

Run from the repo root:

    python -m pytest tests/test_http.py
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import logging.handlers
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace

import main as main_module
from persona_agent.config_env import DEFAULT_LLM_BASE_URL, DEFAULT_LLM_MODEL
import httpx
from main import RequestBodyTooLarge, _read_body_limited
from persona_agent import learning as learning_module


def check(name: str, cond: bool, detail: str = "") -> None:
    """Assert `cond`, naming the property so a failure reads as English.

    The suites state a property per line rather than one per function, and
    they keep saying it that way; this turns each statement into the assert
    pytest reports on."""
    assert cond, name + (f" - {detail}" if detail else "")


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
    """main.py used to carry its own copy of this; the package's reader is now
    the only one, so the bounds it enforces are the bounds every setting in
    every module gets."""
    from persona_agent.config_env import env_int

    def parser(name, raw, default, **kw):
        return env_int(name, default, env={name: raw}, **kw)

    check("numeric config: invalid value uses default",
          parser("SERVER_PORT", "not-a-number", 8080, minimum=1, maximum=65535) == 8080)
    check("numeric config: out-of-range value uses default",
          parser("SERVER_PORT", "70000", 8080, minimum=1, maximum=65535) == 8080)
    check("numeric config: valid value accepted",
          parser("SERVER_PORT", "9000", 8080, minimum=1, maximum=65535) == 9000)
    check("numeric config: main.py no longer has a second copy",
          not hasattr(main_module, "_parse_int_config"))


def test_error_bodies_carry_a_stable_code() -> None:
    """`error` is prose for a human and free to be reworded; `code` is the
    half a client may branch on. /v1/events answers 403 for three
    unrelated causes whose fixes differ (allowlist / token / clock), so the
    status alone is not actionable."""
    builder = getattr(main_module, "_error", None)
    check("error builder exists", callable(builder))
    if not callable(builder):
        return

    resp = builder(403, "unauthenticated", "authentication required")
    body = json.loads(bytes(resp.body).decode())
    check("error body keeps the human sentence",
          body.get("error") == "authentication required", repr(body))
    check("error body carries the machine code",
          body.get("code") == "unauthenticated", repr(body))
    check("error without retry_after sends no Retry-After",
          "retry-after" not in {k.lower() for k in resp.headers.keys()},
          repr(dict(resp.headers)))

    resp = builder(429, "capacity_exceeded", "webhook capacity exceeded",
                   retry_after=3)
    check("429 advertises Retry-After",
          resp.headers.get("Retry-After") == "3", repr(dict(resp.headers)))

    marker = getattr(main_module, "_mark_deprecated", None)
    check("deprecation stamp exists", callable(marker))
    if callable(marker):
        stamped = marker(builder(400, "invalid_schema", "invalid event schema"))
        check("the deprecated ingress stamps Deprecation on errors too",
              stamped.headers.get("Deprecation") == "true",
              repr(dict(stamped.headers)))


def test_webhook_routes_are_documented_for_openapi() -> None:
    """FastAPI builds each route's OpenAPI description from the decorated
    function's docstring. Both POST routes were bare, so the one asymmetry a
    third-party integrator most needs — /v1/onebot is fire-and-forget while
    /v1/events answers synchronously — appeared nowhere in /docs."""
    for name in ("onebot_webhook", "connector_events"):
        fn = getattr(main_module, name, None)
        doc = (getattr(fn, "__doc__", "") or "").strip()
        check(f"{name} has a docstring for OpenAPI", bool(doc), repr(doc[:40]))
    gw_doc = (getattr(main_module, "connector_events").__doc__ or "").lower()
    check("the connector docstring states the synchronous contract",
          "synchronous" in gw_doc, repr(gw_doc[:80]))
    qq_doc = (getattr(main_module, "onebot_webhook").__doc__ or "").lower()
    check("the qq docstring states the deprecation",
          "deprecated" in qq_doc, repr(qq_doc[:80]))


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


def test_a_skipped_critical_probe_is_not_a_pass() -> None:
    """`ok` is tri-state: True passed, False failed, None never ran ("not
    configured"). One blank LLM_API_KEY makes BOTH critical chat probes report
    None, so counting None as a pass is exactly how a botched key rotation
    keeps /health green while the agent cannot answer a single message."""
    from persona_agent import health

    def r(name: str, ok, critical: bool = True) -> dict:
        return {"name": name, "ok": ok, "critical": critical,
                "detail": "", "ms": 0}

    check("health: all green is ok",
          health.all_critical_ok([r("a", True), r("b", True)]) is True)
    check("health: a failed critical probe is not ok",
          health.all_critical_ok([r("a", True), r("b", False)]) is False)
    check("health: a SKIPPED critical probe is not ok either",
          health.all_critical_ok([r("a", True), r("b", None)]) is False)
    check("health: a skipped non-critical probe is still ok",
          health.all_critical_ok(
              [r("a", True), r("b", None, critical=False)]) is True)
    # The shape a missing LLM_API_KEY actually produces.
    check("health: an unconfigured LLM does not report healthy",
          health.all_critical_ok([
              r("Private chat (openai)", None),
              r("Primary chat (/v1 tools)", None),
              r("OneBot bridge", True),
              r("Vision", None, critical=False)]) is False)


async def test_asgi_webhook_auth_and_schema() -> None:
    original_secret = main_module.QQ_ONEBOT_SECRET
    original_token = main_module.CONNECTOR_TOKEN
    original_agent = main_module.agent
    original_replay = main_module._connector_replay
    main_module.QQ_ONEBOT_SECRET = "qq-secret"
    main_module.CONNECTOR_TOKEN = "connector-secret"
    main_module.agent = None
    main_module._connector_replay = main_module.ReplayGuard()
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
                "/v1/onebot", content=qq_body,
                headers={"x-signature": "sha1=bad"})
            qq_sig = "sha1=" + hmac.new(
                b"qq-secret", qq_body, hashlib.sha1).hexdigest()
            good = await client.post(
                "/v1/onebot", content=qq_body,
                headers={"x-signature": qq_sig})

            connector_event = {
                "platform": "telegram", "conversation_type": "group",
                "conversation_id": "g", "sender_id": "u",
                "message_id": "m2", "segments": [],
                "sent_at": int(time.time()),
            }
            connector_body = json.dumps(
                connector_event, separators=(",", ":")).encode()
            stamp = str(int(time.time()))
            nonce = "asgi-nonce"
            connector_sig = "sha256=" + hmac.new(
                b"connector-secret",
                stamp.encode() + b"." + nonce.encode() + b"." + connector_body,
                hashlib.sha256,
            ).hexdigest()
            gw = await client.post(
                "/v1/events", content=connector_body,
                headers={
                    "x-personagent-token": "connector-secret",
                    "x-personagent-timestamp": stamp,
                    "x-personagent-nonce": nonce,
                    "x-personagent-signature": connector_sig,
                })

            # A fresh envelope around an event the platform sent long ago.
            old_body = json.dumps(
                dict(connector_event, message_id="m3",
                     sent_at=int(time.time()) - 10 * 86_400),
                separators=(",", ":")).encode()
            old_sig = "sha256=" + hmac.new(
                b"connector-secret",
                stamp.encode() + b".old-nonce." + old_body,
                hashlib.sha256,
            ).hexdigest()
            old = await client.post(
                "/v1/events", content=old_body,
                headers={
                    "x-personagent-token": "connector-secret",
                    "x-personagent-timestamp": stamp,
                    "x-personagent-nonce": "old-nonce",
                    "x-personagent-signature": old_sig,
                })
        check("ASGI auth: invalid QQ signature rejected", bad.status_code == 403)
        check("ASGI auth: valid QQ envelope accepted", good.status_code == 200)
        check("ASGI auth: valid connector envelope accepted",
              gw.status_code == 200 and gw.json() == {
                  "handled": False, "replies": []}, repr(gw.text))
        check("ASGI: an old sent_at is refused as stale_event",
              old.status_code == 403 and old.json()["code"] == "stale_event",
              repr(old.text))
    finally:
        main_module.QQ_ONEBOT_SECRET = original_secret
        main_module.CONNECTOR_TOKEN = original_token
        main_module.agent = original_agent
        main_module._connector_replay = original_replay


def test_connector_envelope_rejects_replay_and_stale_requests() -> None:
    verifier = getattr(main_module, "_verify_envelope", None)
    guard_cls = getattr(main_module, "ReplayGuard", None)
    check("connector signed-envelope verifier exists",
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
        "x-personagent-token": token,
        "x-personagent-timestamp": stamp,
        "x-personagent-nonce": nonce,
        "x-personagent-signature": "sha256=" + digest,
    }
    replay = guard_cls(ttl_seconds=300, max_entries=16)
    first = verifier(body, headers, token, now=now, replay_guard=replay)
    second = verifier(body, headers, token, now=now, replay_guard=replay)
    stale_headers = dict(headers)
    stale_headers["x-personagent-nonce"] = "nonce-2"
    stale_headers["x-personagent-timestamp"] = str(now - 301)
    stale_digest = hmac.new(
        token.encode(),
        stale_headers["x-personagent-timestamp"].encode()
        + b"." + stale_headers["x-personagent-nonce"].encode() + b"." + body,
        hashlib.sha256,
    ).hexdigest()
    stale_headers["x-personagent-signature"] = "sha256=" + stale_digest
    stale = verifier(
        body, stale_headers, token, now=now, replay_guard=replay)
    check("connector signed envelope: first request accepted", first is True, repr(first))
    check("connector signed envelope: nonce replay rejected", second is False, repr(second))
    check("connector signed envelope: stale request rejected", stale is False, repr(stale))

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
        check("connector replay cache persists across restart",
              first_persisted is True and after_restart is False,
              repr((first_persisted, after_restart)))

        full = guard_cls(ttl_seconds=300, max_entries=1)
        first_full = verifier(body, headers, token, now=now, replay_guard=full)
        second_headers = dict(headers)
        second_headers["x-personagent-nonce"] = "nonce-full-2"
        second_digest = hmac.new(
            token.encode(),
            stamp.encode() + b"." + b"nonce-full-2" + b"." + body,
            hashlib.sha256,
        ).hexdigest()
        second_headers["x-personagent-signature"] = "sha256=" + second_digest
        second_full = verifier(
            body, second_headers, token, now=now, replay_guard=full)
        check("connector replay cache sheds new work instead of evicting fresh nonce",
              first_full is True and second_full is False,
              repr((first_full, second_full)))


def test_every_setting_the_code_reads_is_in_the_template() -> None:
    """`.env.example` is the authority on what a key may be CALLED.

    `preflight.check_config` reports anything in `.env` that the template does
    not list, because a misspelled key is otherwise completely silent — the
    value is ignored, the default is used, and the bot runs and misbehaves
    with no clue anywhere. That check is only honest while the template
    actually covers what the code reads: a setting the code reads and the
    template omits would be reported to its operator as a typo.

    Scanned rather than listed, so the two cannot drift apart again.
    `os.getenv`, `os.environ.get` and the `config_env` readers, which are how
    most settings are read now — a key that moved from a bare `os.getenv` onto
    `env_int`/`env_str` must not drop out of this scan, or the template check
    silently stops covering it. `Policy.from_env` reads through a dict
    parameter and is out of reach of a syntactic scan, which is a gap worth
    naming rather than pretending away."""
    import ast

    # `tools/` AND the root entry points, not just the package. Scanning only
    # `main.py` and `persona_agent/` left nine real settings undocumented —
    # `ANTHROPIC_API_KEY` and `LAB_MODEL` among them, which
    # `tools/prompt_lab.py` explicitly tells the operator to put in `.env` —
    # and the preflight then reported every one of them as a misspelling.
    root = Path(__file__).resolve().parents[1]
    sources = [
        root / "main.py", root / "try_chat.py", root / "quickstart.py",
        *sorted((root / "persona_agent").glob("*.py")),
        *sorted((root / "tools").glob("*.py")),
    ]

    readers = {"env_int", "env_float", "env_bool", "env_str", "env_csv"}

    def is_env_read(call: ast.Call) -> bool:
        fn = call.func
        if isinstance(fn, ast.Name):
            return fn.id in readers
        if not isinstance(fn, ast.Attribute):
            return False
        if fn.attr in readers:
            return True
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
    # access.identity_from_env reads its names in a loop, out of reach of the
    # scan; they are settings all the same.
    from persona_agent import access
    for name in access.IDENTITY_SETTINGS:
        read.setdefault(name, "access.py")

    template = (root / ".env.example").read_text(encoding="utf-8")
    documented = {
        line.split("=", 1)[0].strip()
        for line in template.splitlines()
        if "=" in line and not line.lstrip().startswith("#")
    }
    missing = sorted(
        f"{key} ({where})" for key, where in read.items()
        if key not in documented)
    check("every setting the code reads is documented in .env.example",
          not missing,
          "; ".join(missing))


def test_preflight_reports_the_right_deployments(monkeypatch) -> None:
    """134 lines wired into `lifespan` had no behavioural test at all.

    The thing it has to get right is not the true positives — those are easy —
    but the FALSE ones. A checker that fires at a working deployment teaches
    the operator to skip its output, and then the real report goes unread too.
    Four of these were live: settings the shipped tools read, a container
    passing config in the environment, a persona home with no template, and a
    BOM on the template."""
    from persona_agent import preflight

    # Without an explicit env the check reads the process environment for
    # retired names; a PORT in the runner's shell is not what this tests.
    for old in preflight.RENAMED:
        monkeypatch.delenv(old, raising=False)

    def levels(**kwargs):
        return {(f.level, f.key) for f in preflight.check_config(**kwargs)}

    # --- must stay quiet ---------------------------------------------------
    check("preflight: a minimal working config is silent",
          not levels(env={"LLM_API_KEY": "sk-x"}))
    check("preflight: settings the offline tools read are not typos",
          not levels(env={"LLM_API_KEY": "sk-x", "ANTHROPIC_API_KEY": "y",
                          "LAB_MODEL": "m", "REVIEWER_MODEL": "r",
                          "BENCH_JUDGE_MODEL": "b", "BENCH_EVAL_DELAY_S": "1"}))
    check("preflight: proxy variables are not typos",
          not levels(env={"LLM_API_KEY": "sk-x", "HTTP_PROXY": "p",
                          "HTTPS_PROXY": "p", "NO_PROXY": "localhost"}))

    import os as _os
    _os.environ["LLM_API_KEY"] = "sk-from-the-environment"
    try:
        # A container, a systemd unit and a CI runner all configure this way
        # and ship no `.env`. Reading only the file told them every turn
        # would fail while they answered correctly.
        check("preflight: configuration in the environment counts as set",
              not levels(env={}))
    finally:
        del _os.environ["LLM_API_KEY"]

    # --- must still fire ---------------------------------------------------
    check("preflight: a missing required setting is an error",
          ("ERROR", "LLM_API_KEY") in levels(env={}))
    check("preflight: a misspelling is named as one",
          ("ERROR", "DEEPSEK_API_KEY") in levels(env={"DEEPSEK_API_KEY": "x"}))
    check("preflight: an empty QQ_BOT_ID on a QQ config is a warning",
          ("WARN", "QQ_BOT_ID") in levels(env={
              "LLM_API_KEY": "x", "QQ_ONEBOT_URL": "http://127.0.0.1:3000"}))

    # --- and it must never raise, which is its own docstring's promise -----
    for hostile in ({"AGENT_HOME": "~nosuchuser/x"}, {"AGENT_HOME": "\x00"},
                    {"": "x"}, {"LLM_API_KEY": None}):
        try:
            preflight.check_config(env=hostile)
            raised = ""
        except Exception as exc:  # noqa: BLE001 - the point is that none escape
            raised = f"{type(exc).__name__}: {exc}"
        check(f"preflight: does not raise on {hostile!r}", not raised, raised)

    with tempfile.TemporaryDirectory() as d:
        home = Path(d)
        (home / ".env").write_text("LLM_API_KEY=x\nPERSONA_NAME=Mira\n",
                                   encoding="utf-8")
        # The multi-persona layout `.env.example` itself recommends: a home
        # with its own `.env` and no template. This used to report EVERY
        # configured key as unknown, including `AGENT_HOME`, by the code that
        # reads `AGENT_HOME`.
        found = levels(root=home)
        check("preflight: a missing template warns once, it does not accuse",
              found == {("WARN", ".env.example")}, repr(found))

        # A BOM on `.env`. Whether it survives the dotenv parser is a property
        # of that parser and the platform — measured: it does on Windows and
        # does not on the Linux CI runners — so asserting the MECHANISM here
        # passed locally and failed in CI. What has to hold on both is that
        # the deployment is never SILENTLY broken: either the key arrives and
        # there is nothing to say, or it does not and the BOM is named. A
        # report that lists findings without explaining the invisible
        # character is the failure this is guarding against.
        (home / ".env.example").write_text("LLM_API_KEY=\n",
                                           encoding="utf-8")
        (home / ".env").write_bytes(b"\xef\xbb\xbfLLM_API_KEY=x\n")
        with_bom = levels(root=home)
        check("preflight: a BOM on .env is either harmless or named as one",
              not with_bom or ("ERROR", ".env") in with_bom, repr(with_bom))
        # ...while a BOM on the TEMPLATE must not accuse a real key.
        (home / ".env.example").write_bytes(b"\xef\xbb\xbfLLM_API_KEY=\n")
        (home / ".env").write_text("LLM_API_KEY=x\n", encoding="utf-8")
        check("preflight: a BOM on the template accuses nobody",
              not levels(root=home), repr(levels(root=home)))


def test_preflight_names_what_a_retired_setting_became(
        monkeypatch, tmp_path) -> None:
    """0.5 renamed most settings and reads none of the old names. One left in
    `.env` or the environment would otherwise be silently ignored, or called a
    typo when it is a setting that moved: it is a WARN naming its new name."""
    from persona_agent import preflight
    from persona_agent.settings import AgentSettings

    for old in preflight.RENAMED:
        monkeypatch.delenv(old, raising=False)

    found = preflight.check_config(
        env={"LLM_API_KEY": "x", "PORT": "9000", "OWNER_QQ": "42"})
    check("retired: a WARN naming the new name, and nothing else",
          {(f.level, f.key, f.detail) for f in found}
          == {("WARN", "PORT",
               "was renamed to SERVER_PORT in 0.5 and is no longer read"),
              ("WARN", "OWNER_QQ",
               "was renamed to ADMIN_IDS in 0.5 and is no longer read")},
          repr(found))
    every = preflight.check_config(
        env={"LLM_API_KEY": "x", **{old: "1" for old in preflight.RENAMED}})
    check("retired: every name in the table, each once, never as a typo",
          sorted((f.level, f.key) for f in every)
          == sorted(("WARN", old) for old in preflight.RENAMED), repr(every))

    template = (Path(__file__).resolve().parents[1] / ".env.example").read_text(
        encoding="utf-8")
    keys = {line.split("=", 1)[0].strip() for line in template.splitlines()
            if "=" in line and not line.lstrip().startswith("#")}
    check("retired: every new name is a setting the template lists",
          set(preflight.RENAMED.values()) <= keys,
          repr(set(preflight.RENAMED.values()) - keys))
    check("retired: no old name is still in the template",
          not keys & preflight.RENAMED.keys(), repr(keys & preflight.RENAMED.keys()))

    (tmp_path / ".env.example").write_text(template, encoding="utf-8")
    (tmp_path / ".env").write_text("LLM_API_KEY=x\nBOT_NAME=Mira\n",
                                   encoding="utf-8")
    monkeypatch.setenv("REACT_TTL_SEC", "60")
    found = {(f.level, f.key) for f in preflight.check_config(root=tmp_path)}
    check("retired: found in .env and in the process environment",
          found == {("WARN", "BOT_NAME"), ("WARN", "REACT_TTL_SEC")}, repr(found))
    found = {(f.level, f.key) for f in preflight.check_config(
        root=tmp_path, env={"LLM_API_KEY": "x"})}
    check("retired: an explicit env is the only place looked", not found,
          repr(found))

    s = AgentSettings.from_env(env={"LLM_API_KEY": "k", "BOT_NAME": "Mira",
                                    "OWNER_QQ": "42", "REACT_TTL_SEC": "60"})
    check("retired: the value under an old name is not used",
          (s.persona_name, s.admin_ids, s.react_ttl_s) == ("", (), 900.0),
          repr((s.persona_name, s.admin_ids, s.react_ttl_s)))


def test_preflight_reads_the_identity_settings_as_the_agent_does() -> None:
    """ADMIN_IDS, ACCESS_GROUPS and ACCESS_DM_USERS take ids on every
    platform, and the ways to get them wrong are silent:
    another platform's id pasted without its prefix reads as a QQ id (and in
    ACCESS_GROUPS closes every QQ group), a capitalised platform never
    matches, and one entry takes a whole platform away from the connector."""
    from persona_agent import preflight

    def findings(**env):
        return preflight.check_config(env={"LLM_API_KEY": "sk-x", **env})

    def levels(**env):
        return {(f.level, f.key) for f in findings(**env)}

    check("identity: the new names are settings",
          not levels(ADMIN_IDS="telegram:1,10000", ACCESS_GROUPS="123",
                     ACCESS_DM_USERS="456", QQ_BOT_ID="9"),
          repr(levels(ADMIN_IDS="telegram:1,10000", ACCESS_GROUPS="123",
                      ACCESS_DM_USERS="456", QQ_BOT_ID="9")))
    pasted = findings(ACCESS_GROUPS="-1001234,telegram:-100")
    check("identity: an id pasted without its prefix is a warning",
          any(f.level == "WARN" and f.key == "ACCESS_GROUPS"
              and "-1001234" in f.detail and "closes every QQ group" in f.detail
              for f in pasted), repr(pasted))
    check("identity: ...in any of the lists",
          ("WARN", "ADMIN_IDS") in levels(ADMIN_IDS="U0ABC")
          and ("WARN", "ACCESS_DM_USERS") in levels(ACCESS_DM_USERS="alice"))
    check("identity: qq: and bare QQ numbers are fine",
          not levels(ACCESS_GROUPS="qq:123,456", QQ_BOT_ID="9"))
    check("identity: an entry naming no platform or no id is a warning",
          ("WARN", "ACCESS_DM_USERS") in levels(ACCESS_DM_USERS=":42")
          and ("WARN", "ACCESS_DM_USERS") in levels(ACCESS_DM_USERS="slack:"))
    check("identity: a capitalised platform never matches, and says so",
          ("WARN", "ADMIN_IDS") in levels(ADMIN_IDS="Telegram:1"))

    opted = findings(ACCESS_GROUPS="telegram:-100", ACCESS_DM_USERS="slack:U1")
    check("identity: one entry gating a whole platform is pointed out",
          {(f.level, f.key) for f in opted if "only the listed" in f.detail}
          == {("INFO", "ACCESS_GROUPS"), ("INFO", "ACCESS_DM_USERS")},
          repr(opted))
    check("identity: ...and only when a forwarded platform has entries",
          not levels(ACCESS_GROUPS="123", QQ_BOT_ID="9"))

    check("identity: a bare QQ admin is a QQ config that needs QQ_BOT_ID",
          ("WARN", "QQ_BOT_ID") in levels(ADMIN_IDS="42"))
    check("identity: a Telegram-only admin is not",
          not levels(ADMIN_IDS="telegram:42"))
    check("identity: QQ's own adapter is the native platform to name",
          not levels(CONNECTOR_QQ_PLATFORMS="aiocqhttp"))
    check("identity: another native platform would read its ids as QQ ones",
          ("WARN", "CONNECTOR_QQ_PLATFORMS") in levels(
              CONNECTOR_QQ_PLATFORMS="aiocqhttp,wecom"))


def test_preflight_names_a_fallback_endpoint_that_cannot_work_as_meant() -> None:
    """The fallback endpoint serves the fallback MODEL, and both ways to get it
    wrong are silent: set up for a fallback that is the primary's own name, it
    is never called; pointed at another provider without its own key, it is
    handed the primary's."""
    from persona_agent import preflight

    def levels(**env):
        return {(f.level, f.key) for f in preflight.check_config(
            env={"LLM_API_KEY": "sk-x", **env})}

    check("fallback endpoint: a complete one is silent",
          not levels(LLM_FALLBACK_MODEL="cheap", LLM_FALLBACK_API_KEY="sk-o",
                     LLM_FALLBACK_BASE_URL="https://other.example/v1"))
    check("fallback endpoint: the primary's host sharing its key is silent",
          not levels(LLM_FALLBACK_MODEL="cheap",
                     LLM_FALLBACK_BASE_URL=DEFAULT_LLM_BASE_URL + "/beta"))
    check("fallback endpoint: another host handed the primary's key is named",
          ("WARN", "LLM_FALLBACK_API_KEY") in levels(
              LLM_FALLBACK_MODEL="cheap", LLM_FALLBACK_BASE_URL="https://other.example/v1"))
    found = levels(LLM_FALLBACK_BASE_URL="https://other.example/v1",
                   LLM_FALLBACK_API_KEY="sk-o")
    check("fallback endpoint: without a distinct LLM_FALLBACK_MODEL it says it does nothing",
          found == {("WARN", "LLM_FALLBACK_BASE_URL")}, repr(found))
    check("fallback endpoint: a custom version path is named like the primary's",
          ("WARN", "LLM_FALLBACK_BASE_URL") in levels(
              LLM_FALLBACK_MODEL="cheap", LLM_FALLBACK_API_KEY="k",
              LLM_FALLBACK_BASE_URL="https://llm.example/api/v4"))


def test_the_health_probes_follow_the_fallback_to_its_endpoint(monkeypatch) -> None:
    """The tools probe asks for LLM_FALLBACK_MODEL and the eval probe for
    EVAL_MODEL. With a fallback endpoint configured, the agent sends that
    model there; a probe that still asked the primary for it would report
    an outage that is not happening, and miss the one that is."""
    from persona_agent import health

    posted: list = []

    def fake_post(url, payload, headers, timeout=30):
        posted.append((url, headers["Authorization"], payload["model"]))
        return {"choices": [{"message": {"content": "ok"}}]}

    monkeypatch.setattr(health, "_post_json", fake_post)
    for name in ("LLM_FALLBACK_BASE_URL", "LLM_FALLBACK_API_KEY", "VISION_API_KEY",
                 "VISION_BASE_URL"):
        monkeypatch.delenv(name, raising=False)
    for name, value in (("LLM_API_KEY", "sk-primary"), ("LLM_MODEL", "main"),
                        ("LLM_BASE_URL", "https://primary.example"),
                        ("LLM_FALLBACK_MODEL", "cheap"), ("EVAL_MODEL", "cheap")):
        monkeypatch.setenv(name, value)

    health.check_primary_chat_tools()
    health.check_eval()
    primary = ("https://primary.example/v1/chat/completions", "Bearer sk-primary", "cheap")
    check("health: unset, the fallback is probed on the primary's endpoint",
          posted == [primary, primary], repr(posted))

    monkeypatch.setenv("LLM_FALLBACK_BASE_URL", "https://fallback.example/v1")
    monkeypatch.setenv("LLM_FALLBACK_API_KEY", "sk-fallback")
    posted.clear()
    health.check_primary_chat_tools()
    health.check_eval()
    fallback = ("https://fallback.example/v1/chat/completions", "Bearer sk-fallback",
                "cheap")
    check("health: set, both probes follow the fallback model to its endpoint",
          posted == [fallback, fallback], repr(posted))

    # LLM_DM_MODEL is routed by name like every other: the fallback's name
    # sends DMs to the fallback's endpoint, so that is where it is probed.
    monkeypatch.setenv("LLM_DM_MODEL", "cheap")
    posted.clear()
    health.check_private_chat()
    check("health: a private model that is the fallback's is probed where DMs go",
          posted == [fallback], repr(posted))
    monkeypatch.setenv("LLM_DM_MODEL", "dm-model")
    posted.clear()
    health.check_private_chat()
    check("health: any other private model is probed on the primary's endpoint",
          posted == [("https://primary.example/v1/chat/completions",
                      "Bearer sk-primary", "dm-model")], repr(posted))


def test_the_private_chat_probe_uses_the_agents_default_model(monkeypatch) -> None:
    """With LLM_MODEL unset the agent runs its default model; the probe must
    too, or a skipped critical probe fails /health on a working agent. An
    explicit blank stays blank, as it does for the agent."""
    from persona_agent import health

    sent: list = []

    def fake_post(url, payload, headers, timeout=30):
        sent.append(payload["model"])
        return {"choices": [{"message": {"content": "ok"}}]}

    monkeypatch.setattr(health, "_post_json", fake_post)
    for name in ("LLM_MODEL", "LLM_DM_MODEL",
                 "LLM_FALLBACK_MODEL", "LLM_FALLBACK_BASE_URL", "LLM_FALLBACK_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("LLM_API_KEY", "k")
    ok, detail = health.check_private_chat()
    check("health: the private probe runs with LLM_MODEL unset", ok is True, detail)
    check("health: the private probe asks for the agent's default model",
          sent == [DEFAULT_LLM_MODEL], repr(sent))

    monkeypatch.setenv("LLM_MODEL", "")
    sent.clear()
    ok, detail = health.check_private_chat()
    check("health: an explicit blank LLM_MODEL is still not configured",
          ok is None and sent == [], f"{ok} {detail} {sent}")


def test_connector_envelope_refuses_a_bad_signature() -> None:
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
    verifier = main_module._verify_envelope
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
            "x-personagent-token": token,
            "x-personagent-timestamp": stamp,
            "x-personagent-nonce": nonce,
            "x-personagent-signature": (sign(body, nonce, stamp) if sig is None
                                    else sig),
        }

    def verdict(headers, payload=body) -> bool:
        # A guard per call: a shared one would let a replay refusal stand in
        # for a signature refusal and every case below would "pass".
        return verifier(payload, headers, token, now=now,
                        replay_guard=guard_cls(ttl_seconds=300, max_entries=16))

    # The control. If this is not True the rest proves nothing.
    check("connector signature: a correct envelope is accepted",
          verdict(envelope("ctl")) is True)

    cases = {
        "a forged signature": envelope("n1", sig="sha256=" + "0" * 64),
        "an absent signature": {k: v for k, v in envelope("n2").items()
                                if k != "x-personagent-signature"},
        "an empty signature": envelope("n3", sig=""),
        "the digest without its prefix":
            envelope("n4", sig=sign(body, "n4", str(now))[len("sha256="):]),
        "a signature made with the wrong key":
            envelope("n5", sig=sign(body, "n5", str(now), key="not-the-token")),
    }
    for label, headers in cases.items():
        check(f"connector signature: {label} is refused",
              verdict(headers) is False, repr(headers.get("x-personagent-signature")))

    # The BINDING, one field at a time: a signature that is valid for some
    # other request must not travel. These are the shapes an attacker who can
    # see one signed request actually has.
    check("connector signature: does not travel to a different body",
          verdict(envelope("n6"), payload=b'{"message_id":"m1","text":"drop table"}')
          is False)
    tampered_nonce = envelope("n7")
    tampered_nonce["x-personagent-nonce"] = "n7-swapped"
    check("connector signature: does not survive a swapped nonce",
          verdict(tampered_nonce) is False)
    tampered_stamp = envelope("n8")
    tampered_stamp["x-personagent-timestamp"] = str(now - 1)
    check("connector signature: does not survive a swapped timestamp",
          verdict(tampered_stamp) is False)

    # And the token check is still its own gate, not a side effect of the
    # signature matching.
    wrong_token = envelope("n9")
    wrong_token["x-personagent-token"] = "wrong"
    check("connector signature: the bearer token is checked separately",
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
    connector_missing = {
        "platform": "telegram", "conversation_type": "group",
        "conversation_id": "g", "sender_id": "u", "segments": [],
    }
    connector_valid = dict(
        connector_missing, message_id="m2", sent_at=int(time.time()))
    check("event schema: QQ message without id rejected",
          validator(qq_missing, connector=False) is False)
    check("event schema: QQ message with id accepted",
          validator(qq_valid, connector=False) is True)
    check("event schema: connector message without id rejected",
          validator(connector_missing, connector=True) is False)
    check("event schema: connector message with id accepted",
          validator(connector_valid, connector=True) is True)
    check("event schema: sent_at required",
          validator(dict(connector_valid, sent_at=None), connector=True)
          is False)
    dm = dict(connector_valid, conversation_type="dm", conversation_id=None)
    check("event schema: a DM needs no conversation_id",
          validator(dm, connector=True) is True)
    for kind in ("private", "Group", "", None):
        check(f"event schema: conversation_type {kind!r} rejected",
              validator(dict(connector_valid, conversation_type=kind),
                        connector=True) is False)
    connector_freshness = getattr(
        main_module, "_connector_event_is_fresh", None)
    check("sent_at freshness validator exists",
          callable(connector_freshness))
    if callable(connector_freshness):
        now = int(time.time())
        check("sent_at freshness: current event accepted",
              connector_freshness(
                  {"sent_at": now}, now=now,
                  max_age_seconds=300) is True)
        check("sent_at freshness: stale event rejected",
              connector_freshness(
                  {"sent_at": now - 301}, now=now,
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
        promote_max_examples=10,
        promote_max_feedback=10,
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


def test_a_failed_log_rotation_does_not_swallow_the_record() -> None:
    """A rollover that cannot happen must not take the log line with it.

    Windows refuses `os.rename` on a file another handle holds open, and a
    leftover uvicorn is a normal state here. `RotatingFileHandler.emit` calls
    `doRollover` inside its own try, so the failure is not "rotation skipped"
    — it is `handleError`, and the record is gone. The log starts losing lines
    exactly when the file gets big enough to be worth rotating.

    The bare handler runs alongside so the test shows the loss rather than
    asserting an absence: if the stock class ever stopped dropping records,
    this would stop being a fix worth having and the second check would say
    so."""
    def emit_three(handler):
        for i in range(3):
            handler.emit(logging.LogRecord(
                "t", logging.INFO, __file__, 1, f"line-{i}", None, None))

    original = logging.handlers.RotatingFileHandler.doRollover

    def refuse(self):
        raise OSError(32, "another process holds the file")

    with tempfile.TemporaryDirectory() as td:
        fixed_path = Path(td) / "fixed.log"
        bare_path = Path(td) / "bare.log"
        fixed = main_module.RollingLogThatSurvivesAFailedRotation(
            str(fixed_path), maxBytes=1, backupCount=1, encoding="utf-8")
        bare = logging.handlers.RotatingFileHandler(
            str(bare_path), maxBytes=1, backupCount=1, encoding="utf-8")
        raising = logging.raiseExceptions
        logging.raiseExceptions = False  # handleError would print a traceback
        logging.handlers.RotatingFileHandler.doRollover = refuse
        try:
            emit_three(fixed)
            emit_three(bare)
        finally:
            logging.handlers.RotatingFileHandler.doRollover = original
            logging.raiseExceptions = raising
            fixed.close()
            bare.close()

        kept = fixed_path.read_text(encoding="utf-8")
        lost = bare_path.read_text(encoding="utf-8")

    check("failed rotation: every record still reaches the file",
          all(f"line-{i}" in kept for i in range(3)), repr(kept[:160]))
    check("failed rotation: the stock handler is the thing being fixed",
          "line-2" not in lost, repr(lost[:160]))


def _loopback_client(**kwargs) -> httpx.AsyncClient:
    transport = httpx.ASGITransport(
        app=main_module.app, client=("127.0.0.1", 1234), **kwargs)
    return httpx.AsyncClient(
        transport=transport, base_url="http://127.0.0.1:8080")


async def test_a_caller_without_the_token_cannot_hold_an_admission_slot() -> None:
    """The token is checked before a slot is taken, so a peer that has none
    is refused as unauthenticated instead of filling the slots and 429ing
    the real connector for as long as it keeps its sockets open."""
    original_token = main_module.CONNECTOR_TOKEN
    main_module.CONNECTOR_TOKEN = "abc"
    limiter = main_module._connector_admission
    taken = 0
    try:
        while await limiter.try_acquire():
            taken += 1
        async with _loopback_client() as client:
            response = await client.post(
                "/v1/events", content=b"{}",
                headers={"content-type": "application/json"})
    finally:
        for _ in range(taken):
            await limiter.release()
        main_module.CONNECTOR_TOKEN = original_token
    check("admission: a tokenless caller is refused before admission",
          response.status_code == 403, repr((response.status_code, response.text)))


async def test_a_non_ascii_token_header_is_refused_not_a_crash() -> None:
    original_token = main_module.CONNECTOR_TOKEN
    main_module.CONNECTOR_TOKEN = "abc"
    try:
        async with _loopback_client(raise_app_exceptions=False) as client:
            connector = await client.post(
                "/v1/events", content=b"{}",
                headers={"x-personagent-token": b"\xff"})
            details = await client.get(
                "/health/details", headers={"x-personagent-token": b"\xff"})
    finally:
        main_module.CONNECTOR_TOKEN = original_token
    check("auth: a non-ASCII token on the connector is a 403",
          connector.status_code == 403, repr(connector.status_code))
    check("auth: a non-ASCII token on health details is a 403",
          details.status_code == 403, repr(details.status_code))
    check("auth: a non-ASCII configured secret compares instead of raising",
          main_module._ct_equal("\xc3\xa9", "é")
          and not main_module._ct_equal("é", "é"))


async def _drive_events(receive) -> list[dict]:
    """Run one raw ASGI request against /v1/events and collect what
    the app sends. The token is set and supplied so the request gets past
    every check that runs before the body is read."""
    sent: list[dict] = []

    async def send(message):
        sent.append(message)

    scope = {
        "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
        "method": "POST", "scheme": "http", "path": "/v1/events",
        "raw_path": b"/v1/events", "root_path": "", "query_string": b"",
        "headers": [
            (b"host", b"127.0.0.1:8080"),
            (b"content-type", b"application/json"),
            (b"content-length", b"100"),
            (b"x-personagent-token", b"abc"),
        ],
        "client": ("127.0.0.1", 1234), "server": ("127.0.0.1", 8080),
    }
    original_token = main_module.CONNECTOR_TOKEN
    main_module.CONNECTOR_TOKEN = "abc"
    try:
        await main_module.app(scope, receive, send)
    finally:
        main_module.CONNECTOR_TOKEN = original_token
    return sent


async def test_a_stalled_body_times_out_and_frees_its_slot() -> None:
    import asyncio

    calls = 0

    async def receive():
        nonlocal calls
        calls += 1
        if calls == 1:
            return {"type": "http.request", "body": b"{", "more_body": True}
        await asyncio.Event().wait()

    original_timeout = getattr(main_module, "BODY_READ_TIMEOUT_S", None)
    main_module.BODY_READ_TIMEOUT_S = 0.1
    try:
        sent = await asyncio.wait_for(_drive_events(receive), 3)
    finally:
        main_module.BODY_READ_TIMEOUT_S = original_timeout
    start = next((m for m in sent if m["type"] == "http.response.start"), {})
    check("body read: a stalled body is answered 408",
          start.get("status") == 408, repr(sent[:1]))
    check("body read: the admission slot is released",
          main_module._connector_admission.inflight == 0,
          repr(main_module._connector_admission.inflight))


async def test_a_client_that_hangs_up_mid_body_raises_nothing() -> None:
    messages = [
        {"type": "http.request", "body": b"{", "more_body": True},
        {"type": "http.disconnect"},
    ]

    async def receive():
        return messages.pop(0) if messages else {"type": "http.disconnect"}

    error = None
    try:
        await _drive_events(receive)
    except Exception as exc:  # the property is that nothing escapes
        error = exc
    check("body read: a mid-body disconnect is not an app exception",
          error is None, repr(error))
    check("body read: the admission slot is released after a disconnect",
          main_module._connector_admission.inflight == 0)


def _event_body(message_id: str) -> bytes:
    return json.dumps({
        "platform": "telegram", "conversation_type": "group",
        "conversation_id": "g", "sender_id": "u", "message_id": message_id,
        "segments": [], "sent_at": int(time.time()),
    }, separators=(",", ":")).encode()


def _qq_event_body(message_id: str) -> bytes:
    return json.dumps({
        "post_type": "message", "message_type": "group", "group_id": "g",
        "user_id": "u", "message_id": message_id, "message": [],
        "time": int(time.time()),
    }, separators=(",", ":")).encode()


async def test_without_a_credential_only_local_programs_are_accepted() -> None:
    """With no secret set, a loopback peer alone is not enough: a browser
    tab (Origin, Sec-Fetch-Site), a rebound host name (Host) and a tunnel on
    the same machine (X-Forwarded-For) all arrive from 127.0.0.1 too, and
    each would otherwise post events as anyone, the admin included."""
    saved = (main_module.QQ_ONEBOT_SECRET, main_module.CONNECTOR_TOKEN,
             main_module.agent, main_module.run_checks,
             dict(main_module._health_cache))
    main_module.QQ_ONEBOT_SECRET = ""
    main_module.CONNECTOR_TOKEN = ""
    main_module.agent = None
    main_module.run_checks = lambda: []
    main_module._health_cache.update({"ts": 0.0, "data": None})
    json_type = {"content-type": "application/json"}
    browser_like = {
        "origin": {"origin": "https://evil.example"},
        "sec-fetch-site": {"sec-fetch-site": "cross-site"},
        "host": {"host": "evil.example:8080"},
        "x-forwarded-for": {"x-forwarded-for": "203.0.113.9"},
    }
    try:
        async with _loopback_client() as client:
            plain_gw = await client.post(
                "/v1/events", content=_event_body("ok-1"),
                headers=json_type)
            plain_qq = await client.post(
                "/v1/onebot", content=_qq_event_body("ok-2"),
                headers=json_type)
            plain_details = await client.get("/health/details")
            refused = {}
            for name, extra in browser_like.items():
                refused[name] = (
                    await client.post(
                        "/v1/events",
                        content=_event_body("x-" + name),
                        headers={**json_type, **extra}),
                    await client.post(
                        "/v1/onebot", content=_qq_event_body("x-" + name),
                        headers={"content-type": "text/plain", **extra}),
                    await client.get("/health/details", headers=extra),
                )
    finally:
        (main_module.QQ_ONEBOT_SECRET, main_module.CONNECTOR_TOKEN,
         main_module.agent, main_module.run_checks) = saved[:4]
        main_module._health_cache.clear()
        main_module._health_cache.update(saved[4])
    check("local: a plain loopback connector POST is accepted",
          plain_gw.status_code == 200, repr(plain_gw.text))
    check("local: a plain loopback QQ POST is accepted",
          plain_qq.status_code == 200, repr(plain_qq.text))
    check("local: plain loopback health details are answered",
          plain_details.status_code in (200, 503), repr(plain_details.text))
    for name, responses in refused.items():
        for route, response in zip(
                ("connector", "qq", "health/details"), responses):
            check(f"local: {name} is refused on {route}",
                  response.status_code == 403
                  and response.json().get("code") == "non_local_request",
                  repr((response.status_code, response.text)))


async def test_a_signed_request_with_an_origin_is_unaffected() -> None:
    """The locality rule stands in for a credential; with a token set, the
    envelope is the check and a browser-shaped header changes nothing."""
    saved = (main_module.CONNECTOR_TOKEN, main_module.agent,
             main_module._connector_replay)
    main_module.CONNECTOR_TOKEN = "connector-secret"
    main_module.agent = None
    main_module._connector_replay = main_module.ReplayGuard()
    body = _event_body("signed-origin")
    stamp = str(int(time.time()))
    nonce = "origin-nonce"
    signature = "sha256=" + hmac.new(
        b"connector-secret", stamp.encode() + b"." + nonce.encode() + b"." + body,
        hashlib.sha256).hexdigest()
    try:
        async with _loopback_client() as client:
            response = await client.post(
                "/v1/events", content=body, headers={
                    "origin": "https://evil.example",
                    "x-personagent-token": "connector-secret",
                    "x-personagent-timestamp": stamp,
                    "x-personagent-nonce": nonce,
                    "x-personagent-signature": signature,
                })
    finally:
        (main_module.CONNECTOR_TOKEN, main_module.agent,
         main_module._connector_replay) = saved
    check("local: a signed connector request is not judged by its headers",
          response.status_code == 200, repr(response.text))


def test_the_host_header_name_handles_ports_and_ipv6() -> None:
    name = main_module._host_header_name
    check("host: port stripped", name("127.0.0.1:8080") == "127.0.0.1")
    check("host: bracketed IPv6", name("[::1]:8080") == "::1")
    check("host: bare name", name("LocalHost") == "localhost")
    check("host: foreign name", name("evil.example:8080") == "evil.example")


def test_log_files_stay_private_across_rotation() -> None:
    """Rotation recreates the base file under the process umask, so a
    one-time chmod at setup left every file after the first rollover
    world-readable, message excerpts and user ids included."""
    import os

    import pytest

    if os.name == "nt":
        pytest.skip("POSIX file modes")
    previous = os.umask(0o022)
    try:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td) / "bot.log"
            handler = main_module.RollingLogThatSurvivesAFailedRotation(
                str(base), maxBytes=200, backupCount=2, encoding="utf-8")
            try:
                for i in range(30):
                    handler.emit(logging.LogRecord(
                        "t", logging.INFO, __file__, 1,
                        f"line-{i} " + "x" * 40, None, None))
            finally:
                handler.close()
            backup = Path(str(base) + ".1")
            modes = {p.name: p.stat().st_mode & 0o777 for p in (base, backup)}
    finally:
        os.umask(previous)
    check("log files: base and backup are 0600 after rotation",
          all(mode == 0o600 for mode in modes.values()),
          repr({k: oct(v) for k, v in modes.items()}))
