"""`personagent doctor`: check the setup, then probe every external service.

The probes are shared with /health/details (health.py).
"""
import argparse
import json
import sys
from pathlib import Path

from persona_agent import langs
from persona_agent import home

home.load_env()

from persona_agent import preflight
from persona_agent.health import run_checks, all_critical_ok
from persona_agent.paths import ROOT
from persona_agent.preflight import check_config

def _parser(prog: str) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog=prog,
        description=langs.term(
            "Checks the configuration and ledgers (free, local), then probes every external service "
            "the agent depends on and prints an OK/FAIL table. Exits non-zero if a service marked "
            "critical is down. Each service probe sends one tiny request with your credentials and "
            "spends a small amount of credit."),
        epilog=langs.term(
            "When the last answer is a day old, it also asks pypi.org whether a newer personagent "
            "is out (UPDATE_CHECK_ENABLED=false skips that)."))
    way = p.add_mutually_exclusive_group()
    way.add_argument("--json", action="store_true",
                     help=langs.term("same checks, one JSON object on stdout instead of the table"))
    way.add_argument("--fix", action="store_true",
                     help=langs.term("rename retired settings in .env to their new names (saves .env.bak)"))
    return p


def fix_command() -> str:
    """How this install spells the fix."""
    from persona_agent.setup_wizard import Launcher

    return Launcher(sys.executable, ROOT).shown("doctor --fix")[-1]


def _fix() -> int:
    env_file = ROOT / ".env"
    changes = preflight.migrate_env_file(env_file)
    for old, new, action in changes:
        if action == "renamed":
            print(langs.term(f"renamed {old} -> {new}"))
        else:
            print(langs.term(f"left {old} out: {new} is already set (the old line is now a comment)"))
    if changes:
        print(langs.term(f"Saved the previous file as {env_file.name}.bak next to it."))
    for old, new, where in preflight.retired_settings():
        if where != ".env":
            print(langs.term(f"{old} is set in the environment, not .env: rename it to {new} where you set it."))
    if not changes:
        print(langs.term(f"Nothing to rename in {env_file}."))
    return 0


def _pad(text: str, width: int) -> str:
    """`text` filled to `width` terminal columns."""
    return text + " " * (width - langs.width(text))


def main(argv: list[str] | None = None, prog: str | None = None) -> int:
    args = _parser(prog or "personagent doctor").parse_args(sys.argv[1:] if argv is None else argv)
    if args.fix:
        return _fix()
    retired = preflight.retired_settings()
    if args.json:
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
            "services": [json_row(r) for r in results],
            "direct_platforms": direct_platforms(home.find_home()),
            "chat_api": chat_api_state(),
            "approvals": approvals_state(home.find_home()),
            "tools": tools_state(home.find_home()),
            "page": page_state(),
            "update": update_notice(),
            "model_use": _snake_case_use(model_use()),
        }, ensure_ascii=False, indent=2))
        return 0 if ok else 1
    print("=" * 64)
    print(langs.term("  personagent — config + API health check"))
    print("=" * 64)
    # Config first: a probe that fails because a key is misspelled reads like
    # the service being down, and the two have very different fixes.
    findings = check_config()
    if findings:
        for finding in findings:
            print(f"  {finding.line(langs.term)}")
        print("-" * 64)
    else:
        print(langs.term("[  OK ] configuration                    no unknown or missing keys"))
        print("-" * 64)
    if any(f.key == "LLM_API_KEY" and f.level == "ERROR" for f in findings):
        from persona_agent.setup_wizard import command

        print(langs.term(f"  No model key yet: `{command('init')}` sets up the model and key."))
        print("-" * 64)
    if retired:
        print(langs.term(f"  The service will not start while these settings are in use; "
              f"run `{fix_command()}` to rename them."))
        print("-" * 64)
    results = run_checks()
    first_with: dict[str, str] = {}
    for r in results:
        mark = {"skipped": "  -  ", "ok": "  OK ", "failed": " FAIL"}[row_status(r)]
        tag = langs.term(" [critical]") if r["critical"] else ""
        advice = r.get("advice") or ""
        text = (langs.term(f"The same problem as the row {first_with[advice]}.")
                if advice in first_with else langs.term(advice or r["detail"]))
        if advice:
            first_with.setdefault(advice, r["name"])
        print(f"[{mark}] {_pad(langs.term(r['name']), 34)}{_pad(tag, 11)} {r['ms']:5.0f}ms  {text}")
    mark, detail = direct_row(direct_platforms(home.find_home()))
    print(f"[{mark}] {_pad(langs.term('Directly connected platforms'), 34)}{_pad('', 11)} {'':7}  {detail}")
    mark, detail = chat_api_row(chat_api_state())
    print(f"[{mark}] {_pad(langs.term('OpenAI-compatible API'), 34)}{_pad('', 11)} {'':7}  {langs.term(detail)}")
    mark, detail = approvals_row(approvals_state(home.find_home()))
    print(f"[{mark}] {_pad(langs.term('Approval of new chats'), 34)}{_pad('', 11)} {'':7}  {detail}")
    mark, detail = tools_row(tools_state(home.find_home()))
    print(f"[{mark}] {_pad(langs.term('Tools (MCP servers)'), 34)}{_pad('', 11)} {'':7}  {detail}")
    mark, detail = page_row(page_state())
    print(f"[{mark}] {_pad(langs.term('The page'), 34)}{_pad('', 11)} {'':7}  {detail}")
    print("-" * 64)
    print("  " + langs.term(model_use_line(model_use())))
    print("=" * 64)
    services_ok = all_critical_ok(results)
    if not services_ok:
        print(langs.term("RESULT: a CRITICAL service is DOWN."))
    elif retired:
        print(langs.term("RESULT: services OK, but retired settings must be renamed."))
    else:
        print(langs.term("RESULT: all critical services OK."))
    urgent, first = first_fix(findings, results)
    if first:
        print(langs.term(f"Fix first: {first}" if urgent else f"Not critical, but failing: {first}",
                         keep=(first,)))
    off = activity_off()
    if off:
        print(langs.term(off))
    from persona_agent.updates import line
    notice = line(update_notice())
    if notice:
        print(langs.term(notice))
    return 0 if services_ok and not retired else 1


def row_status(r: dict) -> str:
    """ok, failed, or skipped: a row not asked because its model already failed is skipped."""
    if r["ok"] is None or (r.get("same_as") and r["ok"] is False):
        return "skipped"
    return "ok" if r["ok"] else "failed"


def json_row(r: dict) -> dict:
    """A row for `doctor --json`: the table's readable sentence as `detail`, the raw text as `error`."""
    out = dict(r)
    out["status"] = row_status(r)
    if out["status"] == "skipped":
        out["ok"] = None
    advice = r.get("advice") or ""
    if advice and advice != r["detail"]:
        out["detail"], out["error"] = advice, r["detail"]
    return out


def _snake_case_use(found: dict) -> dict:
    # todayPurposes stays for readers of the old key.
    if "todayPurposes" in found:
        found = {**found, "today_purposes": found["todayPurposes"]}
    return found


def first_fix(findings, results) -> tuple[bool, str]:
    """(urgent, the first thing to fix) in the terminal's language: a configuration
    error or a critical row that did not pass is urgent; else a row that failed."""
    def said(r) -> str:
        return f"{langs.term(r['name'])}: {langs.term(r.get('advice') or r['detail'])}"
    for finding in findings:
        if finding.level == "ERROR":
            return True, f"{finding.key}: {langs.term(finding.detail)}"
    for r in results:
        if r["critical"] and r["ok"] is not True and not r.get("same_as"):
            return True, said(r)
    for r in results:
        if r["ok"] is False and not r.get("same_as"):
            return False, said(r)
    return False, ""


def model_use() -> dict:
    """What the character's model calls used today and in the last 7 days."""
    import os

    from persona_agent import paths, usage

    memory = Path(os.getenv("MEMORY_FILE") or "memory.json")
    memory = memory if memory.is_absolute() else paths.runtime_dir() / memory
    return usage.read_summary(memory.with_name(usage.USAGE_FILE))


def model_use_line(found: dict) -> str:
    def cost(total: dict) -> str:
        return "not reported" if total["cost"] is None else f"${total['cost']:.4f}"

    today, week = found["today"], found["week"]
    if not week["calls"]:
        return "model use: nothing recorded yet"
    return (f"model use — today: requests {today['calls']}, tokens {today['tokens']}, "
            f"cost {cost(today)}; last 7 days: requests {week['calls']}, "
            f"tokens {week['tokens']}, cost {cost(week)}")


def update_notice() -> dict | None:
    """A newer release on PyPI, asked now only when the last answer is stale;
    None without one or with the check off."""
    from persona_agent import updates

    found = home.find_home()
    if not updates.enabled(found):
        return None
    return updates.notice(found, updates.check(found, timeout=10.0) if updates.stale(found) else None)


def _direct_running(found: Path) -> bool:
    """Whether the process serving the directly connected platforms for
    `found` runs, as the records the app keeps of its children say."""
    from persona_agent import services

    for path in (found / "runtime" / "desktop").glob("children-*.json"):
        try:
            child = (json.loads(path.read_text(encoding="utf-8")).get("children") or {}).get("direct")
            pid, argv = int(child["pid"]), list(child["argv"])
        except (OSError, ValueError, TypeError, KeyError, AttributeError):
            continue
        if services._still_child(services._command_line(pid), argv, str(found), services._leads_group(pid)):
            return True
    return False


def direct_platforms(found: Path) -> dict:
    """The platforms personagent connects itself and, while it runs, the state
    each one reports. Nothing is asked of a platform."""
    from persona_agent.direct import base
    from persona_agent.direct_setup import NAMED_REFUSALS, stored

    found = found.resolve()
    running = _direct_running(found)
    try:
        states = base.read_status(found) if running else {}
    except (OSError, ValueError):
        states = {}
    rows = []
    for kind in stored(found):
        state = states.get(kind) if isinstance(states.get(kind), dict) else {}
        detail = str(state.get("detail") or "")
        # Only the named codes: any other detail may quote the platform's own text.
        rows.append({"id": kind, "state": str(state.get("state") or ""),
                     "detail": detail if detail in NAMED_REFUSALS else ""})
    return {"running": running, "platforms": rows}


def direct_row(found: dict) -> tuple[str, str]:
    """The table's mark and words for `direct_platforms`."""
    from persona_agent import connections

    lang = langs.terminal_lang()
    if not found["platforms"]:
        return "  -  ", langs.term("none connected")
    named = [(connections.say(connections.platform(p["id"]).name, lang), p) for p in found["platforms"]]
    if not found["running"]:
        return "  -  ", langs.term(f"{', '.join(name for name, _ in named)} (state unknown: personagent is not running)")
    words = {"connected": "{0}: connected", "connecting": "{0}: connecting",
             "refused": "{0}: refused the connection", "error": "{0}: stopped by an error"}
    parts = []
    for name, platform in named:
        if platform["detail"] and platform["state"] == "retrying":
            # The sentence `personagent connect` prints for the same cause.
            from persona_agent import setup_wizard

            parts.append(f"{name}: " + setup_wizard.refusal(platform["detail"], connections.platform(platform["id"]),
                                                            name, lang=lang))
            continue
        if platform["detail"] and platform["state"] == "refused":
            sentence = f"{name}: refused the connection ({platform['detail']})"
        else:
            sentence = words.get(platform["state"], "{0}: not started yet").replace("{0}", name)
        parts.append(langs.term(sentence))
    failed = any(p["state"] in ("refused", "error") for _, p in named)
    ok = all(p["state"] == "connected" for _, p in named)
    return (" FAIL" if failed else "  OK " if ok else "  -  "), "; ".join(parts)


def chat_api_state() -> dict:
    """Whether the OpenAI-compatible API is on and a key guards it, as the service reads them."""
    from persona_agent.config_env import env_bool, env_str

    return {"enabled": env_bool("CHAT_API_ENABLED", False), "key": bool(env_str("CHAT_API_KEY"))}


def chat_api_row(state: dict) -> tuple[str, str]:
    """The table's mark and words for `chat_api_state`; never the key itself."""
    if not state["enabled"]:
        return "  -  ", "off (CHAT_API_ENABLED=false); `personagent connect api` turns it on"
    if state["key"]:
        return "  OK ", "on, guarded by CHAT_API_KEY"
    return "  OK ", "on, without a key: only programs on this computer may call it"


def approvals_state(found: Path) -> dict:
    """Which platforms ask for approval of new chats, and how many requests wait on each."""
    from persona_agent import approvals
    from persona_agent.config_env import env_str

    try:
        waiting = approvals.waiting_counts(found)
        approved = len(approvals.Store(approvals.store_path(found)).snapshot()["approved"])
    except OSError:
        waiting, approved = {}, 0
    return {"platforms": sorted(approvals.policy({"ACCESS_APPROVAL_PLATFORMS": env_str("ACCESS_APPROVAL_PLATFORMS")})),
            "waiting": waiting, "approved": approved}


def approvals_row(state: dict) -> tuple[str, str]:
    """The table's mark and words for `approvals_state`."""
    from persona_agent import connections
    from persona_agent.setup_wizard import command

    if not state["platforms"]:
        return "  -  ", langs.term("off: no platform asks; the reply settings alone decide who is answered")
    lang = langs.terminal_lang()

    def name(kind: str) -> str:
        try:
            return connections.say(connections.platform(kind).name, lang)
        except ValueError:
            return kind
    names = ", ".join(name(p) for p in state["platforms"])
    count = str(sum(state["waiting"].values()))
    listing = command("access")
    if count == "0":
        return "  OK ", langs.term(f"on for {names}; no request is waiting", keep=(names,))
    return "  OK ", langs.term(f"on for {names}; {count} waiting, see `{listing}`", keep=(names, count, listing))
def tools_state(found: Path) -> dict:
    """The tool servers in the home, the tools switched on, and, while the
    service runs, the servers it could not start. No server is started."""
    from persona_agent import mcp_tools, services

    counts = mcp_tools.enabled_counts(found)
    status = mcp_tools.read_status(found)
    pid = status.get("pid")
    line = services._command_line(pid) if isinstance(pid, int) and pid > 0 else ""
    running = "persona" in line
    configured = set(mcp_tools.load_config(found)["mcpServers"])
    servers = status.get("servers") if isinstance(status.get("servers"), dict) else {}
    failing = sorted(name for name, row in servers.items()
                     if running and name in configured and isinstance(row, dict) and row.get("state") == "failed")
    return {**counts, "running": running, "failing": failing}


def tools_row(state: dict) -> tuple[str, str]:
    """The table's mark and words for `tools_state`."""
    if not state["servers"]:
        return "  -  ", langs.term("none added; `personagent tools add` adds a server")
    counted = langs.term(f"servers: {state['servers']}, tools on: {state['tools_on']}")
    if state["failing"]:
        names = ", ".join(state["failing"])
        return " FAIL", counted + langs.term(f"; not starting: {names}", keep=(names,))
    if not state["running"]:
        return "  -  ", counted + langs.term("; state unknown: personagent is not running")
    return "  OK ", counted
def page_state() -> dict:
    """Where the page listens and whether a password guards it there; never the password."""
    from persona_agent import pageaccess

    settings = pageaccess.read(home.find_home())
    return {"host": settings.host, "port": settings.port or None, "remote": settings.remote,
            "password": bool(settings.password),
            "hashed": pageaccess.is_hashed(settings.password),
            "problems": [key for level, key, _ in pageaccess.problems(settings) if level == "ERROR"]}


def page_row(state: dict) -> tuple[str, str]:
    """The table's mark and words for `page_state`."""
    if not state["remote"]:
        return "  -  ", langs.term("this computer only (PAGE_HOST); other devices cannot reach it")
    where = state["host"] + (f":{state['port']}" if state["port"] else "")
    if not state["password"]:
        return " FAIL", langs.term(f"listens on {where} without a password, so it will not start; "
                                   f"run `personagent page password`")
    if state["problems"]:
        return " FAIL", langs.term(f"{', '.join(state['problems'])} must be corrected before it can listen "
                                   f"on {where}; see the configuration lines above")
    return "  OK ", langs.term(f"listens on {where} for other devices, guarded by the page password")


def activity_off() -> str:
    """Why the local page's Activity view is empty, '' while it is on."""
    from persona_agent.config_env import env_bool

    if env_bool("DASHBOARD_ENABLED", True):
        return ""
    return ("activity: off (DASHBOARD_ENABLED=false), so the local page's "
            "Activity view shows nothing")


if __name__ == "__main__":
    sys.exit(main())
