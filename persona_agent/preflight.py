"""Config preflight: say what is wrong before the bot pretends to work.

The deployment surface is 80 settings and four of them matter for a first
reply. That asymmetry is fine — everything else has a default — but it has a
sharp edge: **a misspelled key is completely silent.** `.env` with
`DEEPSEK_API_KEY=sk-...` produces a bot that starts cleanly, logs nothing
unusual, and never answers, and the only way to find out is to read the code.

`.env.example` is the authority for what a key is allowed to be called. It is
kept in step with the code by a test (`test_http.py`), so anything in `.env`
that is not in the template is a typo or a setting that was removed — and
either way the operator believes it is doing something.

Read-only and total: this reports, it never edits `.env`, and it never raises.
A preflight that can fail is a preflight nobody runs.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from urllib.parse import urlsplit

from . import access, channels
from .config_env import DEFAULT_LLM_BASE_URL, DEFAULT_LLM_MODEL
from .paths import ROOT

logger = logging.getLogger("agent")

#: Without this there is no model to call and nothing works at all.
REQUIRED = ("LLM_API_KEY",)

#: Set, but empty, is a different thing from unset for these: the agent runs
#: and behaves oddly rather than not running.
WANTED = {
    "PERSONA_NAME": "the persona has no name, so it cannot notice being called",
    # Emptied rather than unset is the whole point: `os.getenv` only applies
    # its default when the key is ABSENT, so `LLM_MODEL=` in a hand-edited
    # `.env` sends `{"model": ""}` on every completion — a guaranteed 400 that
    # also arms the fallback cooldown. `LLM_DM_MODEL` was given a runtime
    # fallback for exactly this (see settings.py); the primary model has none.
    "LLM_MODEL": "every chat completion will be sent with model='' and fail",
}

#: Names a live `.env` may legitimately carry that the template does not.
#: Deliberately tiny — every entry is a hole in the typo check.
TEMPLATE_EXEMPT = frozenset({
    # Set by the process manager / shell rather than by the file, and
    # documented in the deployment notes rather than as a knob.
    "PYTHONUTF8", "PYTHONPATH", "TZ",
    # Proxy configuration. `load_dotenv` puts these in `os.environ` and httpx
    # honours them — the suite has a whole test built around an `HTTP_PROXY`
    # in the launching shell — so reporting them as typos was telling an
    # operator their working proxy setting was being ignored.
    "HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY", "ALL_PROXY",
    "http_proxy", "https_proxy", "no_proxy", "all_proxy",
})

#: Every setting name retired in 0.5 -> the name that replaced it. A hint and
#: nothing more: none of these is read, so a value under one is ignored.
RENAMED = {
    "LLM_TIMEOUT": "LLM_TIMEOUT_S",
    "PRIVATE_MODEL": "LLM_DM_MODEL",
    "JUDGE_MODEL": "LLM_JUDGE_MODEL",
    "FALLBACK_MODEL": "LLM_FALLBACK_MODEL",
    "FALLBACK_BASE_URL": "LLM_FALLBACK_BASE_URL",
    "FALLBACK_API_KEY": "LLM_FALLBACK_API_KEY",
    "FALLBACK_THINKING": "LLM_FALLBACK_THINKING",
    "FALLBACK_DURATION": "LLM_FALLBACK_DURATION_S",
    "RATE_WINDOW": "LLM_RATE_WINDOW_S",
    "RATE_THRESHOLD": "LLM_RATE_THRESHOLD",
    "RATE_LIMIT_COOLDOWN": "LLM_RATE_LIMIT_COOLDOWN_S",
    "MAX_IMAGE_BYTES": "VISION_MAX_IMAGE_BYTES",
    "BOT_NAME": "PERSONA_NAME",
    "TZ_OFFSET_HOURS": "PERSONA_TZ_OFFSET_HOURS",
    "ALLOWED_GROUPS": "ACCESS_GROUPS",
    "ALLOWED_DM_USERS": "ACCESS_DM_USERS",
    "AGENT_TRIGGER_COUNT": "CHAT_TRIGGER_COUNT",
    "AGENT_CONTEXT_LEN": "CHAT_CONTEXT_MESSAGES",
    "AGENT_FOLLOWUP_WINDOW": "CHAT_FOLLOWUP_WINDOW_S",
    "AGENT_MEMORY_FILE": "MEMORY_FILE",
    "AGENT_MEMORY_MAX": "MEMORY_MAX_PER_CONVERSATION",
    "AGENT_ENABLE": "AGENT_ENABLED",
    "HOST": "SERVER_HOST",
    "PORT": "SERVER_PORT",
    "MAX_WEBHOOK_BODY_BYTES": "SERVER_MAX_BODY_BYTES",
    "LOG_FILE": "SERVER_LOG_FILE",
    "GATEWAY_TOKEN": "CONNECTOR_TOKEN",
    "GATEWAY_SOURCE_MAX_AGE_SECONDS": "CONNECTOR_MAX_EVENT_AGE_S",
    "GATEWAY_NATIVE_PLATFORMS": "CONNECTOR_QQ_PLATFORMS",
    "GATEWAY_OUTBOX": "CONNECTOR_OUTBOX_ENABLED",
    "MAX_INFLIGHT_GATEWAY": "CONNECTOR_MAX_INFLIGHT",
    "BOT_QQ": "QQ_BOT_ID",
    "NAPCAT_API": "QQ_ONEBOT_URL",
    "NAPCAT_IMAGE_DIR": "QQ_ONEBOT_IMAGE_DIR",
    "WEBHOOK_SECRET": "QQ_ONEBOT_SECRET",
    "MAX_INFLIGHT_WEBHOOKS": "QQ_ONEBOT_MAX_INFLIGHT",
    "PROACTIVE_ENABLE": "PROACTIVE_ENABLED",
    "PROACTIVE_INTERVAL": "PROACTIVE_INTERVAL_S",
    "PROACTIVE_MIN_SILENCE": "PROACTIVE_MIN_SILENCE_S",
    "PROACTIVE_COOLDOWN": "PROACTIVE_COOLDOWN_S",
    "PROACTIVE_DM_MIN_SILENCE": "PROACTIVE_DM_MIN_SILENCE_S",
    "PROACTIVE_DM_COOLDOWN": "PROACTIVE_DM_COOLDOWN_S",
    "REACT_LEARN": "REACT_LEARN_ENABLED",
    "REACT_TTL_SEC": "REACT_TTL_S",
    "REACT_FIX_WINDOW": "REACT_FIX_WINDOW_S",
    "REACT_ELICIT": "REACT_ELICIT_ENABLED",
    "REACT_ELICIT_DELAY": "REACT_ELICIT_DELAY_S",
    "REACT_ELICIT_COOLDOWN": "REACT_ELICIT_COOLDOWN_S",
    "PROMOTE_AUTO": "PROMOTE_AUTO_ENABLED",
    "EXAMPLES_MAX_AUTO": "PROMOTE_MAX_EXAMPLES",
    "FEEDBACK_MAX_AUTO": "PROMOTE_MAX_FEEDBACK",
    "EVOLVE_AUTO": "EVOLVE_AUTO_ENABLED",
    "EVAL_ENABLE": "EVAL_ENABLED",
    "AGENT_EVIDENCE_WARN_BYTES": "LEDGER_EVIDENCE_WARN_BYTES",
    "AGENT_CANDIDATE_LEDGER_WARN_BYTES": "LEDGER_CANDIDATES_WARN_BYTES",
    "PROMPT_LAB_MODEL": "LAB_MODEL",
    "BENCH_EVAL_DELAY": "BENCH_EVAL_DELAY_S",
    # Aliases that kept even older names working until 0.5.
    "GLM_API_KEY": "VISION_API_KEY",
    "GLM_BASE_URL": "VISION_BASE_URL",
    "ANTHROPIC_PRIVATE_MODEL": "LLM_DM_MODEL",
    "OWNER_QQ": "ADMIN_IDS",
    "GATEWAY_OWNER_IDS": "ADMIN_IDS",
    "OWNER_NAME": "ADMIN_NAME",
    "OWNER_RELATIONSHIP": "ADMIN_RELATIONSHIP",
    "QQ_GROUPS": "ACCESS_GROUPS",
    "PRIVATE_ALLOWED_QQS": "ACCESS_DM_USERS",
}

#: The one connector platform whose ids are QQ numbers (AstrBot's OneBot
#: adapter). Any other native platform mints bare ids the agent reads as QQ.
_QQ_ADAPTER = "aiocqhttp"


def _shown(entries) -> str:
    entries = list(entries)
    head = ", ".join(entries[:3])
    return head + (f" and {len(entries) - 3} more" if len(entries) > 3 else "")


def _identity_findings(identity: access.Identity) -> list["Finding"]:
    """What the admin and allowlist settings will not do as written.

    `identity` comes from access.identity_from_env, the reader the agent uses,
    so a finding here describes what the agent actually does with the value."""
    natives = identity.native_platforms
    findings: list[Finding] = []

    for name in access.IDENTITY_SETTINGS:
        written = identity.written[name]
        malformed = [e for e in written if access.is_malformed(e)]
        if malformed:
            findings.append(Finding(
                "WARN", name,
                f"has {_shown(malformed)}, which names no platform or no id, "
                f"so it is ignored. Write entries as <platform>:<id>"))
        ids = [access.canonical_id(e, natives) for e in written
               if not access.is_malformed(e)]
        # A bare id is QQ's, and QQ numbers are digits. Anything else is almost
        # always another platform's id pasted without its prefix, and in a
        # group list it restricts QQ to groups that cannot exist.
        bare = [i for i in ids if ":" not in i and not i.isdigit()]
        if bare:
            closes = (", and as a QQ entry it closes every QQ group not listed"
                      if name == "ACCESS_GROUPS" else "")
            findings.append(Finding(
                "WARN", name,
                f"has {_shown(bare)} with no platform prefix, so it is read as "
                f"a QQ id and matches no one{closes}. Prefix it with its "
                f"platform, e.g. telegram:{bare[0]}"))
        prefixes = {i.split(":", 1)[0] for i in ids if ":" in i}
        cased = sorted(p for p in prefixes if p != p.lower())
        if cased:
            findings.append(Finding(
                "WARN", name,
                f"names the platform {_shown(cased)}, but platform names are "
                f"lowercase (telegram, discord, ...), so these entries never "
                f"match"))

    # Listing one entry for a platform takes that platform away from the
    # connector's allowlist. Documented, but easy to trip over.
    for name, what in (("ACCESS_GROUPS", "groups"),
                       ("ACCESS_DM_USERS", "users besides the admin")):
        platforms = sorted({channels.platform_of(i) for i in identity.ids(name)
                            if channels.platform_of(i).islower()}
                           - {channels.NATIVE_PLATFORM})
        if platforms:
            findings.append(Finding(
                "INFO", name,
                f"lists {_shown(platforms)} entries, so only the listed "
                f"{what} there are answered and the rest are refused; the "
                f"connector's own model may answer those. Platforms without "
                f"entries, QQ included, are not affected"))

    odd = [p for p in natives if p != _QQ_ADAPTER]
    if odd:
        findings.append(Finding(
            "WARN", "CONNECTOR_QQ_PLATFORMS",
            f"names {_shown(odd)}. A native platform's ids are stored bare, "
            f"which is how QQ numbers are stored, so they are compared against "
            f"the QQ admins and allowlists. Only {_QQ_ADAPTER} carries QQ ids"))
    return findings


def _base_url_needs_full_path(base: str) -> bool:
    """Does this base URL hit the gap `chat_completions_url` documents?

    `endpoints.chat_completions_url` accepts a provider root or a `/v1` base
    and asks callers on a custom version path (`/api/paas/v4`, say) to
    supply the complete endpoint themselves. Nothing enforces that: give it a
    `/v4` base and it silently returns `.../v4/v1/chat/completions`, which no
    provider serves, and the first sign is a 404 on every reply.

    Checked here rather than in `chat_completions_url` because that function
    is on the per-turn hot path, where a warning per call would flood the log.
    A startup finding says it once, before the first turn.

    Deliberately narrow: only a trailing `/vN` segment that is not `/v1`. The
    general fallback branch exists to serve multi-segment provider roots
    behind a reverse proxy (`https://proxy.corp/llm-proxy`), so segment
    counting would report those as broken when they are fine.
    """
    if not base:
        return False
    path = urlsplit(base.strip().rstrip("/")).path.rstrip("/")
    if not path or path.endswith("/chat/completions"):
        return False
    last = path.rsplit("/", 1)[-1]
    return (len(last) > 1 and last[0] == "v" and last[1:].isdigit()
            and last != "v1")


class Finding:
    """One problem, at one level, about one key."""

    __slots__ = ("level", "key", "detail")

    def __init__(self, level: str, key: str, detail: str) -> None:
        self.level, self.key, self.detail = level, key, detail

    def __repr__(self) -> str:  # pragma: no cover - diagnostics only
        return f"<{self.level} {self.key}: {self.detail}>"

    def line(self) -> str:
        # `!r` on the key, because a name that differs only by an invisible
        # character — a BOM, a stray space — otherwise prints identically to
        # the real one and the operator reads the report as nonsense.
        shown = self.key if self.key.isprintable() else repr(self.key)
        return f"[{self.level:>5}] {shown}: {self.detail}"


def _parse(path: Path, *, strip_bom: bool = False) -> dict | None:
    """Key -> value for one dotenv file; **None** when it is absent.

    `None` and `{}` are different answers and conflating them was a bug: a
    missing `.env.example` came back empty, the unknown-key check read that as
    "the authority lists nothing", and every configured key was reported as a
    typo. Any layout that ships `.env` without the template — including the
    multi-persona `AGENT_HOME` arrangement the template itself recommends —
    got one ERROR per setting, which is how a checker teaches people to ignore
    it.

    Uses python-dotenv's own parser rather than a local one: the agent loads
    these files through it, so anything this disagreed with the agent about
    would be a second bug wearing the first one's clothes."""
    try:
        if not path.is_file():
            return None
        from dotenv import dotenv_values
        values = {k: v for k, v in dotenv_values(path).items() if k}
        # A BOM survives dotenv and lands on the first key. For the TEMPLATE
        # that only produces a false "unknown key" report, so strip it. For
        # `.env` it must NOT be stripped: the agent's own `load_dotenv` does
        # not strip it either, so the setting genuinely never arrives, and a
        # preflight that tidied it away would call a broken deployment fine.
        if strip_bom:
            values = {k.lstrip("﻿"): v for k, v in values.items()}
        return values
    except Exception:  # a preflight must not be the thing that breaks
        return None


def check_config(root: Path | None = None, env: dict | None = None) -> list[Finding]:
    """Everything wrong with the configuration, worst first.

    `env` defaults to the parsed `.env`, not to `os.environ`, because the
    question is "what did the operator write down" — a value exported in the
    shell is not a typo anyone is hunting for. A retired name is the
    exception: a container passes its settings in the environment, so without
    an explicit `env` that is searched for them too."""
    base = Path(root) if root is not None else ROOT
    template = _parse(base / ".env.example", strip_bom=True)
    configured = _parse(base / ".env") if env is None else dict(env)
    if configured is None:
        configured = {}

    findings: list[Finding] = []

    bom_keys = [key for key in configured if key.startswith("﻿")]
    if bom_keys:
        findings.append(Finding(
            "ERROR", ".env",
            "starts with a UTF-8 BOM, so the first setting's name carries it "
            f"({bom_keys[0]!r}) and never reaches the process — the default is "
            "used instead, and the file looks correct in every editor. "
            "Re-save it as UTF-8 without a BOM"))

    for key in REQUIRED:
        # `.env` OR the process environment. A container, a systemd unit and a
        # CI runner all pass configuration in the environment and ship no
        # `.env` at all — reading only the file told a correctly-running
        # deployment that every turn would fail.
        if not (str(configured.get(key) or "").strip()
                or os.environ.get(key, "").strip()):
            findings.append(Finding(
                "ERROR", key,
                "not set in .env or the environment — there is no model "
                "endpoint to call, so every turn will fail"))

    if template is None:
        # Without the template there is no authority on what a key may be
        # called, so the typo check is not merely wrong here, it is
        # unanswerable. Say that once instead of accusing every key.
        findings.append(Finding(
            "WARN", ".env.example",
            "is missing, so misspelled settings cannot be detected. Copy it "
            "from the repository if you want that check"))
    else:
        unknown = sorted(
            key for key in configured
            if key not in template and key not in TEMPLATE_EXEMPT
            and key not in RENAMED)
        for key in unknown:
            findings.append(Finding(
                "ERROR", key,
                "is not a setting this project reads. A misspelled key is "
                "silent: the value is ignored and the default is used "
                "instead. Check it against .env.example"))

    retired = set(configured) | (set(os.environ) if env is None else set())
    for old in sorted(retired & RENAMED.keys()):
        findings.append(Finding(
            "WARN", old,
            f"was renamed to {RENAMED[old]} in 0.5 and is no longer read"))

    for key, why in WANTED.items():
        if key in configured and not str(configured.get(key) or "").strip():
            findings.append(Finding("WARN", key, f"is empty — {why}"))

    home = str(configured.get("AGENT_HOME") or "").strip()
    if home:
        try:
            resolved = Path(home).expanduser()
            bad = not resolved.is_dir()
        except (OSError, RuntimeError) as exc:
            # `expanduser()` on `~/...` RAISES when no home directory can be
            # determined, and this function's contract is that it never does:
            # `main.lifespan` calls it unguarded, so a `~` in AGENT_HOME on a
            # host without HOME set took the whole process down at startup.
            resolved, bad = home, True
            findings.append(Finding(
                "ERROR", "AGENT_HOME",
                f"cannot be resolved ({type(exc).__name__}: {exc}) — every "
                f"runtime path is resolved under it"))
        else:
            if bad:
                findings.append(Finding(
                    "ERROR", "AGENT_HOME",
                    f"points at {resolved}, which is not a directory — every "
                    f"runtime path is resolved under it"))

    identity = access.identity_from_env(configured)
    findings.extend(_identity_findings(identity))
    qq_ids = {i for i in identity.admins | identity.groups | identity.dm_users
              if i.isdigit()}

    qq_bot_id = str(configured.get("QQ_BOT_ID") or "").strip()
    if qq_bot_id and "ACCESS_GROUPS" not in configured:
        findings.append(Finding(
            "INFO", "ACCESS_GROUPS",
            "is unset, so the bot listens in every QQ group it is a member of"))
    # QQ_BOT_ID is silently load-bearing on QQ: a QQ @ carries the account's
    # number and `_is_at_me` has nothing else to match it against, so a QQ
    # deployment that is otherwise complete starts cleanly, logs nothing, and
    # never answers a mention. Exactly the failure class this module exists
    # for — and only a warning, because `try_chat.py` supplies its own
    # placeholder and needs none of this.
    looks_like_qq = (bool(str(configured.get("QQ_ONEBOT_URL") or "").strip())
                     or bool(qq_ids))
    if looks_like_qq and not qq_bot_id:
        findings.append(Finding(
            "WARN", "QQ_BOT_ID",
            "is empty while the rest of the QQ configuration is set — the bot "
            "cannot recognise being @-mentioned and will never reply in a "
            "group, without logging anything"))

    for key in ("LLM_BASE_URL", "LLM_FALLBACK_BASE_URL"):
        url = str(configured.get(key) or "").strip()
        if _base_url_needs_full_path(url):
            findings.append(Finding(
                "WARN", key,
                f"ends in a custom version path ({url}) — `chat_completions_url`"
                " only recognises a bare root or a /v1 base, so it will append"
                " /v1/chat/completions and produce a URL the provider does not"
                " serve. Give the complete /chat/completions endpoint instead"))

    # The fallback endpoint serves the fallback MODEL (endpoints.endpoint_for),
    # so both of its failure modes are silent: configured for a fallback that
    # is the primary's own name, it is never called; pointed at another host
    # without its own key, it is handed the primary's.
    fallback_url = str(configured.get("LLM_FALLBACK_BASE_URL") or "").strip()
    fallback_key = str(configured.get("LLM_FALLBACK_API_KEY") or "").strip()
    fallback_model = str(configured.get("LLM_FALLBACK_MODEL") or "").strip()
    primary_model = str(configured.get("LLM_MODEL") or DEFAULT_LLM_MODEL).strip()
    if (fallback_url or fallback_key) and fallback_model in ("", primary_model):
        findings.append(Finding(
            "WARN", "LLM_FALLBACK_BASE_URL" if fallback_url else "LLM_FALLBACK_API_KEY",
            "is set, but LLM_FALLBACK_MODEL is blank or the same as LLM_MODEL — only"
            " a distinct fallback model is sent to the fallback endpoint, so"
            " this has no effect"))
    elif fallback_url and not fallback_key:
        fallback_host = urlsplit(fallback_url).hostname
        primary_url = str(configured.get("LLM_BASE_URL") or "").strip()
        if fallback_host != urlsplit(primary_url or DEFAULT_LLM_BASE_URL).hostname:
            findings.append(Finding(
                "WARN", "LLM_FALLBACK_API_KEY",
                f"is blank while LLM_FALLBACK_BASE_URL points at another host"
                f" ({fallback_host}), so LLM_API_KEY is sent there. Give the"
                " fallback provider its own key"))

    # Embeddings are off until a model is named, so an endpoint without one
    # looks configured and does nothing. Reachability is probed at startup.
    if not str(configured.get("EMBEDDING_MODEL") or "").strip():
        for key in ("EMBEDDING_BASE_URL", "EMBEDDING_API_KEY"):
            if str(configured.get(key) or "").strip():
                findings.append(Finding(
                    "WARN", key,
                    "is set, but EMBEDDING_MODEL is blank, so retrieval ranks"
                    " without embeddings and this has no effect"))
                break

    order = {"ERROR": 0, "WARN": 1, "INFO": 2}
    findings.sort(key=lambda f: (order.get(f.level, 3), f.key))
    return findings


def log_findings(findings: list[Finding]) -> None:
    """Report at startup. Errors are logged as errors; nothing is raised —
    a deployment that is 90% configured should still start and say what is
    missing, not refuse and say nothing."""
    for finding in findings:
        if finding.level == "ERROR":
            logger.error("[preflight] %s", finding.line())
        elif finding.level == "WARN":
            logger.warning("[preflight] %s", finding.line())
        else:
            logger.info("[preflight] %s", finding.line())
