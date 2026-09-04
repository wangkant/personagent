#!/usr/bin/env python3
"""One-shot health check for every external service the agent depends on.

Run:  python tools/healthcheck.py
Prints an OK/FAIL table and exits non-zero if any *critical* service is down.
Shares its probes with /health/details (see health.py). The config and ledger
sections are free; each service probe sends one tiny request to the provider
and spends a small amount of credit. Safe to run while the agent is live.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
try:
    from dotenv import load_dotenv
    load_dotenv(
        os.path.join(os.path.dirname(__file__), "..", ".env"),
        override=False,
    )
except Exception:
    pass

from persona_agent.health import run_checks, all_critical_ok
from persona_agent.preflight import check_config


USAGE = """\
usage: python tools/healthcheck.py

Checks the configuration and ledgers (free, local), then probes every external
service the agent depends on and prints an OK/FAIL table. Exits non-zero if a
service marked critical is down. Each service probe sends one tiny request
with your credentials and spends a small amount of credit — safe to run while
the agent is live, but not a no-op.
"""


def main():
    # `--help` used to be ignored, which meant asking what this does fired
    # live probes at every configured provider endpoint and the OneBot bridge.
    argv = sys.argv[1:]
    if argv:
        print(USAGE)
        return 0 if {"-h", "--help"} & set(argv) else 2
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
    results = run_checks()
    for r in results:
        mark = "  -  " if r["ok"] is None else ("  OK " if r["ok"] else " FAIL")
        tag = " [critical]" if r["critical"] else ""
        print(f"[{mark}] {r['name']:<28}{tag:<11} {r['ms']:5.0f}ms  {r['detail']}")
    print("=" * 64)
    ok = all_critical_ok(results)
    print("RESULT:", "all critical services OK." if ok else "a CRITICAL service is DOWN.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
