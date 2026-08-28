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
from pathlib import Path

from .paths import ROOT

logger = logging.getLogger("agent")

#: Without this there is no model to call and nothing works at all.
REQUIRED = ("DEEPSEEK_API_KEY",)

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
})


class Finding:
    """One problem, at one level, about one key."""

    __slots__ = ("level", "key", "detail")

    def __init__(self, level: str, key: str, detail: str) -> None:
        self.level, self.key, self.detail = level, key, detail

    def __repr__(self) -> str:  # pragma: no cover - diagnostics only
        return f"<{self.level} {self.key}: {self.detail}>"

    def line(self) -> str:
        return f"[{self.level:>5}] {self.key}: {self.detail}"


def _parse(path: Path) -> dict:
    """Key -> value for one dotenv file; `{}` when it is missing or unreadable.

    Uses python-dotenv's own parser rather than a local one: the agent loads
    these files through it, so anything this disagrees with the agent about
    would be a second bug wearing the first one's clothes."""
    try:
        if not path.is_file():
            return {}
        from dotenv import dotenv_values
        return {k: v for k, v in dotenv_values(path).items() if k}
    except Exception:  # a preflight must not be the thing that breaks
        return {}


def check_config(root: Path | None = None, env: dict | None = None) -> list[Finding]:
    """Everything wrong with the configuration, worst first.

    `env` defaults to the parsed `.env`, not to `os.environ`, because the
    question is "what did the operator write down" — a value exported in the
    shell is not a typo anyone is hunting for."""
    base = Path(root) if root is not None else ROOT
    template = _parse(base / ".env.example")
    configured = _parse(base / ".env") if env is None else dict(env)

    findings: list[Finding] = []

    for key in REQUIRED:
        if not str(configured.get(key) or "").strip():
            findings.append(Finding(
                "ERROR", key,
                "not set — there is no model endpoint to call, so every turn "
                "will fail"))

    unknown = sorted(
        key for key in configured
        if key not in template and key not in TEMPLATE_EXEMPT)
    for key in unknown:
        findings.append(Finding(
            "ERROR", key,
            "is not a setting this project reads. A misspelled key is silent: "
            "the value is ignored and the default is used instead. Check it "
            "against .env.example"))

    for key, why in WANTED.items():
        if key in configured and not str(configured.get(key) or "").strip():
            findings.append(Finding("WARN", key, f"is empty — {why}"))

    home = str(configured.get("AGENT_HOME") or "").strip()
    if home and not Path(home).expanduser().is_dir():
        findings.append(Finding(
            "ERROR", "AGENT_HOME",
            f"points at {home!r}, which is not a directory — every runtime "
            f"path is resolved under it"))

    if str(configured.get("BOT_QQ") or "").strip() and "QQ_GROUPS" not in configured:
        findings.append(Finding(
            "INFO", "QQ_GROUPS",
            "is unset, so the bot listens in every group it is a member of"))

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
