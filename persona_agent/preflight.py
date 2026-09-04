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

from .paths import ROOT

logger = logging.getLogger("agent")

#: Without this there is no model to call and nothing works at all.
REQUIRED = ("LLM_API_KEY",)

#: Set, but empty, is a different thing from unset for these: the agent runs
#: and behaves oddly rather than not running.
WANTED = {
    "BOT_NAME": "the persona has no name, so it cannot notice being called",
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
    # A pre-0.1.2 alias kept working for existing deployments and deliberately
    # not advertised to new ones. `tests/test_http.py` exempts it from the
    # template scan for the same reason; both lists have to agree or a
    # deployment that legitimately sets it gets told it is a typo.
    "ANTHROPIC_PRIVATE_MODEL",
})


def private_model_from_env(env=None) -> str:
    """PRIVATE_MODEL, honouring the pre-0.1.2 ANTHROPIC_PRIVATE_MODEL alias."""
    env = os.environ if env is None else env
    return env.get("PRIVATE_MODEL", "") or env.get("ANTHROPIC_PRIVATE_MODEL", "")


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
    shell is not a typo anyone is hunting for."""
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
            if key not in template and key not in TEMPLATE_EXEMPT)
        for key in unknown:
            findings.append(Finding(
                "ERROR", key,
                "is not a setting this project reads. A misspelled key is "
                "silent: the value is ignored and the default is used "
                "instead. Check it against .env.example"))

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

    bot_qq = str(configured.get("BOT_QQ") or "").strip()
    if bot_qq and "QQ_GROUPS" not in configured:
        findings.append(Finding(
            "INFO", "QQ_GROUPS",
            "is unset, so the bot listens in every group it is a member of"))
    # BOT_QQ is silently load-bearing: `_is_at_me` returns False the moment it
    # is empty, so a deployment that is otherwise complete starts cleanly,
    # logs nothing, and never answers a mention. Exactly the failure class
    # this module exists for — and only a warning, because `try_chat.py`
    # supplies its own placeholder and needs none of this.
    looks_like_qq = any(str(configured.get(key) or "").strip()
                        for key in ("NAPCAT_API", "QQ_GROUPS", "OWNER_QQ",
                                    "PRIVATE_ALLOWED_QQS"))
    if looks_like_qq and not bot_qq:
        findings.append(Finding(
            "WARN", "BOT_QQ",
            "is empty while the rest of the QQ configuration is set — the bot "
            "cannot recognise being @-mentioned and will never reply in a "
            "group, without logging anything"))

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
