"""Inspect and control what the agent is allowed to learn.

The automatic path proposes; this is where a human decides. Candidates the
promotion policy would not promote on its own — a single correction, anything
backed only by laughter, two suggestions that contradict each other — sit in
`proposed` until someone looks at them here.

    python tools/candidates_admin.py list                 # pending proposals
    python tools/candidates_admin.py list --state promoted # what is live now
    python tools/candidates_admin.py show <id>            # with its evidence
    python tools/candidates_admin.py promote <id>         # grant authority
    python tools/candidates_admin.py reject <id>          # refuse it
    python tools/candidates_admin.py rollback <id>        # revoke authority
    python tools/candidates_admin.py supersede <old> <new>
    python tools/candidates_admin.py rebuild              # re-derive the views

Ids may be abbreviated to any unique prefix.

Every action appends a lifecycle event; nothing in the log is ever edited or
removed. Promotion, rejection, rollback and supersession all re-derive the
materialized retrieval views afterwards, so the running agent picks the change
up on its next turn — no restart.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=True)

from persona_agent import candidates, evidence, promotion
from persona_agent.paths import resolve_runtime_lang_file

AGENT_LANG = os.getenv("AGENT_LANG", "en").strip().lower()
# Same caps the agent applies when it rebuilds a view (see
# candidates.rebuild_views), so both writers converge on one pool size.
EXAMPLES_MAX_AUTO = int(os.getenv("EXAMPLES_MAX_AUTO", 500) or 0)
FEEDBACK_MAX_AUTO = int(os.getenv("FEEDBACK_MAX_AUTO", 500) or 0)

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass


def _paths(lang: str) -> dict:
    return {
        "evidence": resolve_runtime_lang_file("evidence", "jsonl", lang),
        "ledger": resolve_runtime_lang_file("candidate_ledger", "jsonl", lang),
        "examples_view": resolve_runtime_lang_file("promoted.examples", "jsonl", lang),
        "feedback_view": resolve_runtime_lang_file("promoted.feedback", "jsonl", lang),
    }


def _resolve_id(ledger: candidates.CandidateLedger, wanted: str) -> str | None:
    """Exact id, or the single candidate whose id starts with `wanted`."""
    wanted = (wanted or "").strip()
    if not wanted:
        return None
    if ledger.get(wanted) is not None:
        return wanted
    hits = [c["candidate_id"] for c in ledger.all()
            if c["candidate_id"].startswith(wanted)]
    if len(hits) == 1:
        return hits[0]
    if not hits:
        print(f"no candidate matches {wanted!r}")
    else:
        print(f"{wanted!r} is ambiguous: {', '.join(h[:12] for h in hits[:6])}")
    return None


def _decide(ledger, log, cand, policy) -> promotion.Decision:
    reply = str(cand.get("reply") or "").strip()
    related = [e for e in log.all() if str(e.get("reply") or "").strip() == reply]
    return promotion.decide(
        cand, linked_events=log.many(cand.get("evidence") or []),
        related_events=related, peers=ledger.all(), now=time.time(),
        policy=policy)


def _short(text, width: int = 60) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= width else text[: width - 1] + "…"


def cmd_list(args, ledger, log, policy) -> int:
    rows = [c for c in ledger.all()
            if (not args.state or c.get("state") == args.state)
            and (not args.type or c.get("type") == args.type)]
    rows.sort(key=lambda c: str(c.get("created_at") or ""))
    if args.limit > 0:
        rows = rows[-args.limit:]
    if not rows:
        print("no candidates" + (f" in state {args.state}" if args.state else ""))
        return 0
    print(f"{'id':14} {'type':17} {'state':11} {'ev':3} reply -> better")
    for cand in rows:
        line = _short(cand.get("reply"), 40)
        if cand.get("better"):
            line += "  ->  " + _short(cand.get("better"), 40)
        print(f"{cand['candidate_id'][:12]:14} {str(cand.get('type') or '?'):17} "
              f"{str(cand.get('state') or '?'):11} "
              f"{len(cand.get('evidence') or []):<3} {line}")
        if cand.get("state") == candidates.STATE_PROPOSED:
            decision = _decide(ledger, log, cand, policy)
            print(f"{'':14} why not: {decision.reason}")
    print(f"\n{len(rows)} candidate(s). "
          f"'show <id>' for the evidence behind one.")
    return 0


def cmd_show(args, ledger, log, policy) -> int:
    cid = _resolve_id(ledger, args.candidate_id)
    if cid is None:
        return 1
    cand = ledger.get(cid)
    print(f"candidate  {cid}")
    print(f"type       {cand.get('type')}")
    print(f"state      {cand.get('state')}")
    print(f"created    {cand.get('created_at')}")
    print(f"adjudicated by  {cand.get('adjudication_version') or '?'}")
    scope = cand.get("scope") or {}
    print("scope      " + ", ".join(
        f"{k}={scope.get(k) or '-'}" for k in
        ("lang", "platform", "conv_id", "persona", "persona_hash",
         "persona_version", "scenario", "mode")))
    print(f"\nreply      {cand.get('reply')}")
    if cand.get("better"):
        print(f"better     {cand.get('better')}")
    for line in (cand.get("payload") or {}).get("context") or []:
        print(f"context    {line}")

    print("\nevidence")
    linked = {e["event_id"]: e for e in log.many(cand.get("evidence") or [])}
    for eid in cand.get("evidence") or []:
        ev = linked.get(eid)
        if ev is None:
            print(f"  {eid[:12]}  (not in the evidence log)")
            continue
        counts = "supports" if promotion.supports_candidate(
            ev, cand, policy=policy) else "does not support this proposal"
        print(f"  {eid[:12]}  {ev.get('ts')}  {ev.get('kind')}/"
              f"{ev.get('reaction_type') or '-'}  {ev.get('strength')}  ({counts})")
        who = ev.get("speaker_name") or ev.get("speaker_id") or "-"
        print(f"    from {who} (recipient {ev.get('recipient_id') or '-'}, "
              f"{ev.get('direction') or 'undirected'})")
        if ev.get("reaction_text"):
            print(f"    said: {_short(ev.get('reaction_text'), 100)}")
        reason = (ev.get("adjudication") or {}).get("reason")
        if reason:
            print(f"    verdict: {_short(reason, 100)}")
        if ev.get("parent_event_id"):
            print(f"    follows: {ev['parent_event_id'][:12]}")

    if cand.get("history"):
        print("\nlifecycle")
        for h in cand["history"]:
            print(f"  {h.get('ts') or '?':20} {h.get('state'):11} "
                  f"{h.get('actor') or '?':6} {_short(h.get('reason'), 70)}")
    if cand.get("superseded_by"):
        print(f"\nsuperseded by {cand['superseded_by']}")
    if cand.get("supersedes"):
        print(f"\nsupersedes    {cand['supersedes']}")

    if cand.get("state") == candidates.STATE_PROPOSED:
        decision = _decide(ledger, log, cand, policy)
        print(f"\npolicy: {'would promote' if decision.promote else 'holding'} "
              f"— {decision.reason}")
        if decision.blocked_by:
            print(f"        blocked by {decision.blocked_by}")
    return 0


def _rebuild(paths: dict, ledger) -> None:
    n_ex, n_fb = candidates.rebuild_views(
        ledger, paths["examples_view"], paths["feedback_view"],
        max_examples=EXAMPLES_MAX_AUTO, max_pairs=FEEDBACK_MAX_AUTO)
    print(f"views rebuilt: {n_ex} example row(s) -> {paths['examples_view'].name}, "
          f"{n_fb} pair(s) -> {paths['feedback_view'].name}")


def cmd_transition(args, ledger, log, policy, paths, action: str) -> int:
    cid = _resolve_id(ledger, args.candidate_id)
    if cid is None:
        return 1
    now = datetime.now().isoformat(timespec="seconds")
    reason = args.reason or f"{action} by operator"
    fn = {"promote": ledger.promote, "reject": ledger.reject,
          "rollback": ledger.rollback}[action]
    before = ledger.get(cid).get("state")
    if not fn(cid, ts=now, actor=args.actor, reason=reason):
        print(f"refused: cannot {action} a candidate in state {before!r}")
        return 1
    print(f"{cid}: {before} -> {ledger.get(cid).get('state')}")
    _rebuild(paths, ledger)
    return 0


def cmd_supersede(args, ledger, log, policy, paths) -> int:
    old = _resolve_id(ledger, args.old_id)
    new = _resolve_id(ledger, args.new_id)
    if old is None or new is None:
        return 1
    now = datetime.now().isoformat(timespec="seconds")
    if not ledger.supersede(old, new, ts=now, actor=args.actor,
                            reason=args.reason or "superseded by operator"):
        print(f"refused: {old[:12]} is {ledger.get(old).get('state')} and "
              f"{new[:12]} is {ledger.get(new).get('state')}")
        return 1
    print(f"{old[:12]} superseded; {new[:12]} promoted")
    _rebuild(paths, ledger)
    return 0


def cmd_rebuild(args, ledger, log, policy, paths) -> int:
    _rebuild(paths, ledger)
    active = ledger.active()
    print(f"{len(active)} active candidate(s) from "
          f"{len(ledger.all())} in {paths['ledger'].name}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--lang", default=AGENT_LANG,
                   help="language pool to operate on (default AGENT_LANG)")
    p.add_argument("--actor", default="admin",
                   help="recorded as the actor on lifecycle events")
    sub = p.add_subparsers(dest="cmd", required=True)

    lst = sub.add_parser("list", help="list candidates (default: pending)")
    lst.add_argument("--state", default=candidates.STATE_PROPOSED,
                     choices=("",) + candidates.STATES)
    lst.add_argument("--type", default="", choices=("",) + candidates.TYPES)
    lst.add_argument("--limit", type=int, default=20)

    show = sub.add_parser("show", help="one candidate with its evidence")
    show.add_argument("candidate_id")

    for name, helptext in (("promote", "grant authority to affect replies"),
                           ("reject", "refuse a proposal"),
                           ("rollback", "revoke a promoted candidate")):
        sp = sub.add_parser(name, help=helptext)
        sp.add_argument("candidate_id")
        sp.add_argument("--reason", default="")

    sup = sub.add_parser("supersede", help="replace one candidate with another")
    sup.add_argument("old_id")
    sup.add_argument("new_id")
    sup.add_argument("--reason", default="")

    sub.add_parser("rebuild", help="re-derive the retrieval views from the log")

    args = p.parse_args()
    paths = _paths(args.lang.strip().lower())
    ledger = candidates.CandidateLedger(paths["ledger"])
    log = evidence.EvidenceLog(paths["evidence"])
    policy = promotion.Policy.from_env()

    if args.cmd == "list":
        return cmd_list(args, ledger, log, policy)
    if args.cmd == "show":
        return cmd_show(args, ledger, log, policy)
    if args.cmd in ("promote", "reject", "rollback"):
        return cmd_transition(args, ledger, log, policy, paths, args.cmd)
    if args.cmd == "supersede":
        return cmd_supersede(args, ledger, log, policy, paths)
    return cmd_rebuild(args, ledger, log, policy, paths)


if __name__ == "__main__":
    sys.exit(main())
