"""Config preflight: say what is wrong before the bot pretends to work.

A misspelled key is otherwise silent: the bot starts cleanly and never
answers. `.env.example` is the authority on key names (a test keeps it in
step with the code), so a key in `.env` it does not list is a typo or a
removed setting.

check_config only reports and never raises; migrate_env_file, behind
`doctor --fix`, is the one writer.
"""
from __future__ import annotations

import logging
import os
import re
import shutil
from pathlib import Path
from urllib.parse import urlsplit

from . import access, channels, endpoints
from .config_env import (DEFAULT_LLM_BASE_URL, DEFAULT_LLM_MODEL, TZ_OFFSET_RANGE,
                         parse_tz_offset)
from .home import FROM_ENV_FILE, resource
from .paths import ROOT

logger = logging.getLogger("agent")

#: Without this there is no model to call and nothing works at all.
REQUIRED = ("LLM_API_KEY",)

#: Set, but empty, is a different thing from unset for these: the agent runs
#: and behaves oddly rather than not running.
WANTED = {
    "PERSONA_NAME": "the persona has no name, so it cannot notice being called",
    # Unlike LLM_DM_MODEL, the primary model has no runtime fallback for "".
    "LLM_MODEL": "every chat completion will be sent with model='' and fail",
}

#: Names a live `.env` may legitimately carry that the template does not.
#: Deliberately tiny — every entry is a hole in the typo check.
TEMPLATE_EXEMPT = frozenset({
    # Set by the shell or process manager, not the file.
    "PYTHONUTF8", "PYTHONPATH", "TZ",
    # Proxy settings, which httpx honours from os.environ.
    "HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY", "ALL_PROXY",
    "http_proxy", "https_proxy", "no_proxy", "all_proxy",
})

#: Every setting name retired in 1.0 -> its replacement. None is read: a start
#: with one is refused, and `doctor --fix` renames them.
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
    # Older aliases of the same settings.
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

#: What older templates shipped as QQ_ONEBOT_URL; left in a copied .env it
#: says nothing about whether QQ is in use.
_FORMER_ONEBOT_URL = "http://127.0.0.1:3000"


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


def _lang_family(value: str) -> str:
    """en or zh for a language the agent reads (zh-CN, en_US, ...), else ''."""
    tag = value.strip().lower().replace("_", "-")
    if tag in ("zh", "cn", "chinese") or tag.startswith("zh-"):
        return "zh"
    if tag == "en" or tag.startswith("en-"):
        return "en"
    return ""


class Finding:
    """One problem, at one level, about one key."""

    __slots__ = ("level", "key", "detail")

    def __init__(self, level: str, key: str, detail: str) -> None:
        self.level, self.key, self.detail = level, key, detail

    def __repr__(self) -> str:  # pragma: no cover - diagnostics only
        return f"<{self.level} {self.key}: {self.detail}>"

    def line(self) -> str:
        # repr a key with an invisible character (a BOM, a stray space), or
        # it prints exactly like the real one.
        shown = self.key if self.key.isprintable() else repr(self.key)
        return f"[{self.level:>5}] {shown}: {self.detail}"


def _parse(path: Path, *, strip_bom: bool = False) -> dict | None:
    """Key -> value for one dotenv file, or None when it is absent.

    None, not {}: a missing template read as empty would report every key as
    a typo. Parsed by python-dotenv, which is how the agent loads it."""
    try:
        if not path.is_file():
            return None
        from dotenv import dotenv_values
        values = {k: v for k, v in dotenv_values(path).items() if k}
        # A BOM lands on the first key. Strip it from the template only: the
        # agent's load_dotenv keeps it on `.env`, so that setting never arrives.
        if strip_bom:
            values = {k.lstrip("﻿"): v for k, v in values.items()}
        return values
    except Exception:  # a preflight must not be the thing that breaks
        return None


def check_config(root: Path | None = None, env: dict | None = None) -> list[Finding]:
    """Everything wrong with the configuration, worst first.

    `env` defaults to the parsed `.env`, not os.environ: the question is what
    the operator wrote. Retired names are then searched for in os.environ
    too, since a container passes its settings there."""
    base = Path(root) if root is not None else ROOT
    template = _parse(base / ".env.example", strip_bom=True)
    if template is None:
        # A home made by `personagent init` has no template of its own.
        template = _parse(resource(".env.example"), strip_bom=True)
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
        # Or the environment: a container or systemd unit ships no `.env`.
        if not (str(configured.get(key) or "").strip()
                or os.environ.get(key, "").strip()):
            findings.append(Finding(
                "ERROR", key,
                "not set in .env or the environment — there is no model "
                "endpoint to call, so every turn will fail"))

    if template is None:
        # No authority on key names: say so once instead of accusing every key.
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
            f"was renamed to {RENAMED[old]} in 1.0 and is no longer read"))

    for key, why in WANTED.items():
        if key in configured and not str(configured.get(key) or "").strip():
            findings.append(Finding("WARN", key, f"is empty — {why}"))

    # `KEY=   # note` reads as the value "# note", as older templates had it for
    # REACT_MODEL and EVOLVE_MODEL. Not echoed: the value may be a secret.
    commented = (k for k, v in configured.items() if str(v or "").lstrip().startswith("#"))
    for key in sorted(commented):
        findings.append(Finding(
            "WARN", key,
            "starts with '#': a comment after an empty value is read as the value."
            " Put the comment on its own line and leave the value blank"))

    home = str(configured.get("AGENT_HOME") or "").strip()
    if home:
        try:
            resolved = Path(home).expanduser()
            bad = not resolved.is_dir()
        except (OSError, RuntimeError) as exc:
            # expanduser() raises without a home directory, and lifespan calls
            # this unguarded.
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
    # A QQ @ carries the account number, so without QQ_BOT_ID a QQ deployment
    # never answers a mention. Only QQ intent counts: QQ ids, or a OneBot
    # setting other than the former template default.
    onebot_url = str(configured.get("QQ_ONEBOT_URL") or "").strip().rstrip("/")
    looks_like_qq = (bool(qq_ids)
                     or (bool(onebot_url) and onebot_url != _FORMER_ONEBOT_URL)
                     or any(str(configured.get(k) or "").strip()
                            for k in ("QQ_ONEBOT_SECRET", "QQ_ONEBOT_IMAGE_DIR")))
    if looks_like_qq and not qq_bot_id:
        findings.append(Finding(
            "WARN", "QQ_BOT_ID",
            "is empty while the rest of the QQ configuration is set — the bot "
            "cannot recognise being @-mentioned and will never reply in a "
            "group, without logging anything"))
    direct_qq = qq_bot_id or str(configured.get("QQ_ONEBOT_SECRET") or "").strip()
    if (direct_qq and not onebot_url
            and not str(configured.get("CONNECTOR_QQ_PLATFORMS") or "").strip()):
        findings.append(Finding(
            "WARN", "QQ_ONEBOT_URL",
            "is blank while QQ is set up without AstrBot (CONNECTOR_QQ_PLATFORMS"
            " is empty), so replies on the direct NapCat route are dropped. Set"
            " it to NapCat's HTTP server, such as http://127.0.0.1:3000, or set"
            " CONNECTOR_QQ_PLATFORMS=aiocqhttp if QQ comes through AstrBot"))

    for key in ("LLM_BASE_URL", "LLM_FALLBACK_BASE_URL", "VISION_BASE_URL",
                "EMBEDDING_BASE_URL"):
        url = str(configured.get(key) or "").strip()
        if url and not endpoints.has_scheme(url):
            findings.append(Finding(
                "ERROR" if key == "LLM_BASE_URL" else "WARN", key,
                f"({url}) does not start with https:// or http://, so no request"
                f" can reach it. Write it with one, such as https://{url}"))
            continue
        wrong = endpoints.misjoined_chat_url(url) if key.startswith("LLM_") else ""
        if wrong:
            gemini = ("; Gemini's OpenAI-compatible base is " + url.rstrip("/") + "/openai"
                      if re.search(r"/v\d+beta/?$", url) else "")
            findings.append(Finding(
                "WARN", key,
                f"({url}) is turned into {wrong}, which no provider serves."
                f" Give the complete /chat/completions endpoint instead{gemini}"))

    lang = str(configured.get("AGENT_LANG") or "").strip()
    if lang and not _lang_family(lang):
        findings.append(Finding(
            "WARN", "AGENT_LANG",
            f"is {lang!r}, but the examples, filters and checks exist only in"
            " English and Chinese. Set AGENT_LANG=en or AGENT_LANG=zh"))

    tz = str(configured.get("PERSONA_TZ_OFFSET_HOURS") or "").strip()
    if tz and parse_tz_offset(tz) is None:
        low, high = TZ_OFFSET_RANGE
        findings.append(Finding(
            "WARN", "PERSONA_TZ_OFFSET_HOURS",
            f"is {tz!r}, which is not a UTC offset. Use hours from {low:g} to"
            f" {high:g}, such as 8 or -5, or leave it blank for UTC+8 with"
            " AGENT_LANG=zh and this machine's offset otherwise"))

    # Both fallback-endpoint mistakes are silent: only a distinct fallback
    # model is sent there, and without its own key it gets the primary's.
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
    """Log each finding at its level; nothing is raised."""
    for finding in findings:
        if finding.level == "ERROR":
            logger.error("[preflight] %s", finding.line())
        elif finding.level == "WARN":
            logger.warning("[preflight] %s", finding.line())
        else:
            logger.info("[preflight] %s", finding.line())


# ---------------------------------------------------------------------------
# Retired setting names: refuse to start on them, rewrite them on request
# ---------------------------------------------------------------------------

#: Names the shell or a hosting platform sets for unrelated reasons; they count
#: as retired only when they are written in `.env`.
_AMBIENT_NAMES = frozenset({"HOST", "PORT", "LOG_FILE"})

_ENV_LINE = re.compile(r"^(\s*(?:export\s+)?)([A-Za-z_][A-Za-z0-9_.]*)(\s*=)")


def retired_settings(root: Path | None = None, environ: dict | None = None) -> list[tuple[str, str, str]]:
    """(old name, new name, where) for every retired setting that is set;
    `where` is ".env" or "environment"."""
    base = Path(root) if root is not None else ROOT
    written = _parse(base / ".env") or {}
    live = os.environ if environ is None else environ
    found = {old: ".env" for old in written if old in RENAMED}
    for old in live:
        if old in RENAMED and old not in found and old not in _AMBIENT_NAMES:
            if environ is None and old in FROM_ENV_FILE:
                continue  # read from .env earlier, and since renamed there
            found[old] = "environment"
    return [(old, RENAMED[old], where) for old, where in sorted(found.items())]


def retired_problem(fix_command: str, root: Path | None = None,
                    environ: dict | None = None) -> str | None:
    """One sentence per retired setting, or None. Ignoring them would silently
    drop allowlists, admins and tokens, so a start with any of them is refused."""
    found = retired_settings(root, environ)
    if not found:
        return None
    lines = [f"the setting {old} was renamed {old} -> {new} and is no longer read"
             + ("" if where == ".env" else " (it is set in the environment, not .env)")
             for old, new, where in found]
    lines.append(f"Run `{fix_command}` to rename them in .env, then start again.")
    return "\n".join(lines)


def migrate_env_file(path: Path) -> list[tuple[str, str, str]]:
    """Rewrite retired names in a .env file in place; returns (old, new, action)
    with action "renamed" or "dropped" (the new name was already set, so the old
    line is commented out). Keeps values and comments, saves `<path>.bak` first."""
    path = Path(path)
    if not path.is_file():
        return []
    raw = path.read_bytes().decode("utf-8")
    from dotenv import dotenv_values
    taken = {k for k in dotenv_values(path) if k not in RENAMED}
    changes: list[tuple[str, str, str]] = []
    out: list[str] = []
    for line in raw.splitlines(keepends=True):
        match = _ENV_LINE.match(line)
        old = match.group(2) if match else None
        if old not in RENAMED:
            out.append(line)
            continue
        new = RENAMED[old]
        if new in taken:
            out.append(f"# retired, {new} is already set: {line.lstrip()}")
            changes.append((old, new, "dropped"))
        else:
            out.append(match.group(1) + new + line[match.end(2):])
            taken.add(new)
            changes.append((old, new, "renamed"))
    if changes:
        shutil.copy2(path, path.with_name(path.name + ".bak"))
        path.write_bytes("".join(out).encode("utf-8"))
    return changes
