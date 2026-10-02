"""One-shot health check for every external service the agent depends on.

Run:  personagent doctor
Prints an OK/FAIL table and exits non-zero if any *critical* service is down.
Shares its probes with /health/details (see health.py). The config and ledger
sections are free; each service probe sends one tiny request to the provider
and spends a small amount of credit. Safe to run while the agent is live.

Run:  personagent doctor --json
Same checks, machine-readable: the config findings, the retired settings and
the service probes in one object.

Run:  personagent doctor --fix
Renames settings that 1.0 retired to their new names in <home>/.env.
"""
import json
import sys

from persona_agent import home

home.load_env()

from persona_agent import preflight
from persona_agent.health import run_checks, all_critical_ok
from persona_agent.paths import ROOT
from persona_agent.preflight import check_config

USAGE = """\
usage: {prog} [--json | --fix]

Checks the configuration and ledgers (free, local), then probes every external
service the agent depends on and prints an OK/FAIL table. Exits non-zero if a
service marked critical is down. Each service probe sends one tiny request
with your credentials and spends a small amount of credit: safe to run while
the agent is live, but not a no-op.

  --json    same checks, one JSON object on stdout instead of the table
  --fix     rename retired settings in .env to their new names (saves .env.bak)
"""


def fix_command() -> str:
    """How this install spells the fix."""
    from persona_agent.setup_wizard import Launcher

    return Launcher(sys.executable, ROOT).shown("doctor --fix")[-1]


def _fix() -> int:
    env_file = ROOT / ".env"
    changes = preflight.migrate_env_file(env_file)
    for old, new, action in changes:
        if action == "renamed":
            print(f"renamed {old} -> {new}")
        else:
            print(f"left {old} out: {new} is already set (the old line is now a comment)")
    if changes:
        print(f"Saved the previous file as {env_file.name}.bak next to it.")
    for old, new, where in preflight.retired_settings():
        if where != ".env":
            print(f"{old} is set in the environment, not .env: rename it to {new} where you set it.")
    if not changes:
        print(f"Nothing to rename in {env_file}.")
    return 0


def main(argv: list[str] | None = None, prog: str | None = None) -> int:
    prog = prog or "python tools/healthcheck.py"
    argv = sys.argv[1:] if argv is None else list(argv)
    if argv == ["--fix"]:
        return _fix()
    if argv and argv != ["--json"]:
        print(USAGE.format(prog=prog))
        return 0 if {"-h", "--help"} & set(argv) else 2
    retired = preflight.retired_settings()
    if argv == ["--json"]:
        findings = check_config()
        results = run_checks()
        ok = all_critical_ok(results) and not retired
        print(json.dumps({
            "ok": ok,
            "config_findings": [
                {"level": f.level, "key": f.key, "detail": f.detail}
                for f in findings
            ],
            "retired_settings": [{"old": o, "new": n, "where": w} for o, n, w in retired],
            "services": results,
            "dashboard": dashboard_link(),
        }, ensure_ascii=False, indent=2))
        return 0 if ok else 1
    print("=" * 64)
    print("  personagent — config + API health check")
    print("=" * 64)
    # Config first: a probe that fails because a key is misspelled reads like
    # the service being down, and the two have very different fixes.
    findings = check_config()
    if findings:
        for finding in findings:
            print(f"  {finding.line()}")
        print("-" * 64)
    else:
        print("[  OK ] configuration                    no unknown or missing keys")
        print("-" * 64)
    if any(f.key == "LLM_API_KEY" and f.level == "ERROR" for f in findings):
        print("  No model key yet: `personagent init` sets up the model and key.")
        print("-" * 64)
    if retired:
        print(f"  The service will not start while these settings are in use; "
              f"run `{fix_command()}` to rename them.")
        print("-" * 64)
    results = run_checks()
    for r in results:
        mark = "  -  " if r["ok"] is None else ("  OK " if r["ok"] else " FAIL")
        tag = " [critical]" if r["critical"] else ""
        print(f"[{mark}] {r['name']:<28}{tag:<11} {r['ms']:5.0f}ms  {r['detail']}")
    print("=" * 64)
    services_ok = all_critical_ok(results)
    if not services_ok:
        print("RESULT: a CRITICAL service is DOWN.")
    elif retired:
        print("RESULT: services OK, but retired settings must be renamed.")
    else:
        print("RESULT: all critical services OK.")
    link = dashboard_link()
    if link:
        print(f"dashboard: {link}")
    return 0 if services_ok and not retired else 1


def dashboard_link() -> str:
    """The dashboard's URL with its token, '' when the dashboard is off."""
    from persona_agent import dashboard
    from persona_agent.config_env import env_bool, env_int, env_str

    if not env_bool("DASHBOARD_ENABLED", True):
        return ""
    # Created here too, so the link works from the service's first start on.
    dashboard.load_token(create=True)
    return dashboard.link(env_str("SERVER_HOST", "127.0.0.1"),
                          env_int("SERVER_PORT", 8080, minimum=1, maximum=65535))


if __name__ == "__main__":
    sys.exit(main())
