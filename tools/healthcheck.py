#!/usr/bin/env python3
"""One-shot health check for every external service the agent depends on.

Run:  python tools/healthcheck.py
Prints an OK/FAIL table and exits non-zero if any *critical* service is down.
Shares its probes with the /health endpoint (see health.py). Probes are tiny
and read-only — safe to run while the agent is live.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"), override=True)
except Exception:
    pass

from health import run_checks, all_critical_ok


def main():
    print("=" * 64)
    print("  persona-llm-agent — API health check")
    print("=" * 64)
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
