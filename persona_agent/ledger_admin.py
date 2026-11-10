"""Inspect and control what the agent is allowed to learn.

Candidates the promotion policy will not promote on its own (a single
correction, laughter only, contradicting suggestions) wait here for a human.

    personagent learned                       # the same as `list`
    personagent learned list                  # pending proposals
    personagent learned list --state promoted # what is live now
    personagent learned show <id>             # with its evidence
    personagent learned promote <id>          # grant authority
    personagent learned reject <id>           # refuse it
    personagent learned rollback <id>         # revoke authority
    personagent learned supersede <old> <new> # replace a live rewrite
    personagent learned rebuild               # re-derive the views

Ids may be abbreviated to any unique prefix. A reply has at most one live
rewrite: `promote` refuses a second one and names the `supersede` to run.

Every action appends a lifecycle event and re-derives the retrieval views, so
the running agent picks the change up on its next turn.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from . import langs
from persona_agent import home

home.load_env()

from persona_agent import access, candidates, evidence, lineage, promotion  # noqa: E402
from persona_agent.config_env import env_int  # noqa: E402
from persona_agent.paths import resolve_runtime_lang_file  # noqa: E402
from persona_agent.settings import content_lang  # noqa: E402

AGENT_LANG = content_lang(os.getenv("AGENT_LANG", "en"))
# The caps the agent applies when it rebuilds a view.
PROMOTE_MAX_EXAMPLES = env_int("PROMOTE_MAX_EXAMPLES", 500, minimum=0)
PROMOTE_MAX_FEEDBACK = env_int("PROMOTE_MAX_FEEDBACK", 500, minimum=0)

for _stream in (sys.stdout, sys.stderr):
    _stream.reconfigure(encoding="utf-8", errors="replace")


def _paths(lang: str) -> dict:
    return {
        "evidence": resolve_runtime_lang_file("evidence", "jsonl", lang),
        "ledger": resolve_runtime_lang_file("candidate_ledger", "jsonl", lang),
        "examples_view": resolve_runtime_lang_file("promoted.examples", "jsonl", lang),
        "feedback_view": resolve_runtime_lang_file("promoted.feedback", "jsonl", lang),
    }


def _say(text: str) -> None:
    print(langs.term(text))


def _command(sub: str) -> str:
    """How this install spells `personagent learned <sub>`."""
    from persona_agent.setup_wizard import command

    return command(f"learned {sub}")


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
        _say(f"No candidate matches {wanted!r}.")
    else:
        _say(f"{wanted!r} matches more than one candidate: {', '.join(h[:12] for h in hits[:6])}")
    return None


def _decide(ledger, log, cand, policy) -> promotion.Decision:
    """What the policy would say, from the same inputs (related events,
    ADMIN_IDS) the agent uses."""
    return promotion.decide(
        cand, linked_events=log.many(cand.get("evidence") or []),
        related_events=promotion.related_events(cand, log.all()),
        peers=ledger.all(), now=time.time(), policy=policy,
        admin_ids=access.identity_from_env().admins)


def _short(text, width: int = 60) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= width else text[: width - 1] + "…"


def _pad(text: str, width: int) -> str:
    """`text` filled to `width` terminal columns, and at least one space after it."""
    return text + " " * max(1, width - langs.width(text))


def _field(label: str, value) -> None:
    print(f"{_pad(langs.term(label), 11)}{value}")


def cmd_list(args, ledger, log, policy) -> int:
    rows = [c for c in ledger.all()
            if (not args.state or c.get("state") == args.state)
            and (not args.type or c.get("type") == args.type)]
    rows.sort(key=lambda c: str(c.get("created_at") or ""))
    if args.limit > 0:
        rows = rows[-args.limit:]
    if not rows:
        _say(f"No candidates are in the state {args.state}." if args.state else "There are no candidates.")
        return 0
    print(f"{_pad(langs.term('id'), 14)}{_pad(langs.term('type'), 18)}{_pad(langs.term('state'), 12)}"
          f"{_pad(langs.term('ev'), 4)}{langs.term('reply -> better')}")
    for cand in rows:
        line = _short(cand.get("reply"), 40)
        if cand.get("better"):
            line += "  ->  " + _short(cand.get("better"), 40)
        print(f"{cand['candidate_id'][:12]:14} {str(cand.get('type') or '?'):17} "
              f"{str(cand.get('state') or '?'):11} "
              f"{len(cand.get('evidence') or []):<3} {line}")
        if cand.get("state") == candidates.STATE_PROPOSED:
            decision = _decide(ledger, log, cand, policy)
            print(f"{'':14}{langs.term(f'Not promoted yet: {decision.reason}')}")
    print()
    _say(f"Candidates shown: {len(rows)}. Run `{_command('show <id>')}` to see the evidence behind one.")
    return 0


def cmd_lineage(args, lineages, paths) -> int:
    if args.action == "adopt":
        if not args.persona_hash:
            _say("Adopting needs the persona hash to fold in; a candidate's scope shows it.")
            return 1
        if lineages.adopt(args.version, args.persona_hash):
            version = args.version or langs.term("(not set)")
            _say(f"Adopted {args.persona_hash} into PERSONA_VERSION={version}. "
                 f"Run `{_command('rebuild')}` so that the views include it.")
        else:
            _say("That hash is already in the lineage.")
        return 0
    versions = lineages.versions()
    if not versions:
        _say("No lineage has been recorded yet. It is written on the agent's first learning turn.")
        return 0
    for version, hashes in versions.items():
        print(f"PERSONA_VERSION={version or langs.term('(not set)')}")
        for i, h in enumerate(hashes):
            print(f"  {h}  {langs.term('root') if i == 0 else langs.term(f'revision {i}')}")
    return 0


def cmd_show(args, ledger, log, policy) -> int:
    cid = _resolve_id(ledger, args.candidate_id)
    if cid is None:
        return 1
    cand = ledger.get(cid)
    _field("candidate", cid)
    _field("type", cand.get("type"))
    _field("state", cand.get("state"))
    _field("created", cand.get("created_at"))
    _field("adjudicated by", cand.get("adjudication_version") or "?")
    scope = cand.get("scope") or {}
    _field("scope", ", ".join(
        f"{k}={scope.get(k) or '-'}" for k in
        ("lang", "platform", "conv_id", "persona", "persona_hash",
         "persona_version", "scenario", "mode")))
    print()
    _field("reply", cand.get("reply"))
    if cand.get("better"):
        _field("better", cand.get("better"))
    if (cand.get("payload") or {}).get("lesson"):
        _field("lesson", cand["payload"]["lesson"])
    for line in (cand.get("payload") or {}).get("context") or []:
        _field("context", line)

    print()
    _say("evidence")
    linked = {e["event_id"]: e for e in log.many(cand.get("evidence") or [])}
    for eid in cand.get("evidence") or []:
        ev = linked.get(eid)
        if ev is None:
            print(f"  {eid[:12]}  {langs.term('(not in the evidence log)')}")
            continue
        counts = langs.term("(supports this proposal)" if promotion.supports_candidate(
            ev, cand, policy=policy) else "(does not support this proposal)")
        print(f"  {eid[:12]}  {ev.get('ts')}  {ev.get('kind')}/"
              f"{ev.get('reaction_type') or '-'}  {ev.get('strength')}  {counts}")
        who = ev.get("speaker_name") or ev.get("speaker_id") or "-"
        recipient = ev.get("recipient_id") or "-"
        direction = ev.get("direction")
        print("    " + langs.term(f"From {who} (recipient {recipient}, matched by {direction})" if direction
                                  else f"From {who} (recipient {recipient}, undirected)"))
        if ev.get("reaction_text"):
            print("    " + langs.term(f"Said: {_short(ev.get('reaction_text'), 100)}"))
        reason = (ev.get("adjudication") or {}).get("reason")
        if reason:
            print("    " + langs.term(f"Verdict: {_short(reason, 100)}"))
        if ev.get("parent_event_id"):
            print("    " + langs.term(f"Follows: {ev['parent_event_id'][:12]}"))

    if cand.get("history"):
        print()
        _say("lifecycle")
        for h in cand["history"]:
            print(f"  {h.get('ts') or '?':20} {h.get('state'):11} "
                  f"{h.get('actor') or '?':6} {_short(h.get('reason'), 70)}")
    if cand.get("superseded_by"):
        print()
        _field("superseded by", cand["superseded_by"])
    if cand.get("supersedes"):
        print()
        _field("supersedes", cand["supersedes"])

    if cand.get("state") == candidates.STATE_PROPOSED:
        decision = _decide(ledger, log, cand, policy)
        print()
        _say(f"Policy: would promote: {decision.reason}" if decision.promote
             else f"Policy: holding: {decision.reason}")
        if decision.blocked_by:
            _say(f"Blocked by {decision.blocked_by}")
    return 0


def _rebuild(paths: dict, ledger) -> None:
    n_ex, n_fb = candidates.rebuild_views(
        ledger, paths["examples_view"], paths["feedback_view"],
        max_examples=PROMOTE_MAX_EXAMPLES, max_pairs=PROMOTE_MAX_FEEDBACK)
    _say(f"Views rebuilt. Example rows in {paths['examples_view'].name}: {n_ex}. "
         f"Pairs in {paths['feedback_view'].name}: {n_fb}.")


def cmd_transition(args, ledger, log, policy, paths, action: str) -> int:
    cid = _resolve_id(ledger, args.candidate_id)
    if cid is None:
        return 1
    now = datetime.now().isoformat(timespec="seconds")
    reason = args.reason or f"{action} by operator"
    fn = {"promote": ledger.promote, "reject": ledger.reject,
          "rollback": ledger.rollback}[action]
    cand = ledger.get(cid)
    before = cand.get("state")
    rivals = (promotion.active_rivals(cand, ledger.all(), policy=policy)
              if action == "promote" else [])
    if rivals:
        rival = rivals[0]["candidate_id"]
        _say(f"Refused: {rival[:12]} already rewrites this reply, as "
             f"{_short(rivals[0].get('better'), 50)!r}. A reply keeps one rewrite; to replace it, run:")
        print(f"  {_command(f'supersede {rival[:12]} {cid[:12]}')}")
        return 1
    if not fn(cid, ts=now, actor=args.actor, reason=reason):
        _say({"promote": f"Refused: a candidate in the state {before} cannot be promoted.",
              "reject": f"Refused: a candidate in the state {before} cannot be rejected.",
              "rollback": f"Refused: a candidate in the state {before} cannot be rolled back."}[action])
        return 1
    print(f"{cid}: {before} -> {ledger.get(cid).get('state')}")
    if action == "promote":
        # Drafts of the complaint this pair answers have nothing left for them.
        for other in promotion.answered_drafts(ledger.get(cid), ledger.all(),
                                               policy=policy):
            if ledger.reject(other, ts=now, actor=args.actor,
                             reason=f"answered by {cid}"):
                print(f"{other}: proposed -> rejected " + langs.term(f"(answered by {cid[:12]})"))
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
        _say(f"Refused: {old[:12]} is {ledger.get(old).get('state')} and "
             f"{new[:12]} is {ledger.get(new).get('state')}.")
        return 1
    _say(f"{old[:12]} was superseded, and {new[:12]} was promoted.")
    _rebuild(paths, ledger)
    return 0


def cmd_rebuild(args, ledger, log, policy, paths) -> int:
    _rebuild(paths, ledger)
    _say(f"Active candidates: {len(ledger.active())} of {len(ledger.all())} in {paths['ledger'].name}.")
    return 0


def main(argv: list[str] | None = None, prog: str | None = None) -> int:
    p = argparse.ArgumentParser(prog=prog, description=langs.term(__doc__.splitlines()[0]))
    # How this install spells the command, for the hints it prints.
    p.set_defaults(prog=p.prog)
    p.add_argument("--lang", default=AGENT_LANG,
                   help=langs.term("language pool to operate on (default AGENT_LANG)"))
    p.add_argument("--actor", default="admin",
                   help=langs.term("recorded as the actor on lifecycle events"))
    sub = p.add_subparsers(dest="cmd")

    lst = sub.add_parser("list", help=langs.term("list candidates (default: pending)"))
    lst.add_argument("--state", default=candidates.STATE_PROPOSED,
                     choices=("",) + candidates.STATES)
    lst.add_argument("--type", default="", choices=("",) + candidates.TYPES)
    lst.add_argument("--limit", type=int, default=20)

    show = sub.add_parser("show", help=langs.term("one candidate with its evidence"))
    show.add_argument("candidate_id")

    for name, helptext in (("promote", "grant authority to affect replies"),
                           ("reject", "refuse a proposal"),
                           ("rollback", "revoke a promoted candidate")):
        sp = sub.add_parser(name, help=langs.term(helptext))
        sp.add_argument("candidate_id")
        sp.add_argument("--reason", default="")

    sup = sub.add_parser("supersede", help=langs.term("replace one candidate with another"))
    sup.add_argument("old_id")
    sup.add_argument("new_id")
    sup.add_argument("--reason", default="")

    sub.add_parser("rebuild", help=langs.term("re-derive the retrieval views from the log"))

    lin = sub.add_parser("lineage", help=langs.term("persona revisions that share one learning scope"))
    lin.add_argument("action", nargs="?", default="show", choices=("show", "adopt"))
    lin.add_argument("persona_hash", nargs="?", default="",
                     help=langs.term("with adopt: a pre-lineage hash to fold into the current character"))
    lin.add_argument("--version", default=os.getenv("PERSONA_VERSION", "").strip(),
                     help=langs.term("PERSONA_VERSION the hash belongs to (default: current)"))

    args = p.parse_args(argv)
    if args.cmd is None:
        # `personagent learned` alone lists, as `personagent chat` suggests.
        args = p.parse_args([*(sys.argv[1:] if argv is None else argv), "list"])
    paths = _paths(args.lang.strip().lower())
    ledger = candidates.CandidateLedger(paths["ledger"])
    log = evidence.EvidenceLog(paths["evidence"])
    policy = promotion.Policy.from_env()
    lineages = lineage.PersonaLineage(Path(paths["evidence"]).parent / lineage.FILE_NAME)
    for version, hashes in lineages.versions().items():
        evidence.register_persona_lineage(version, hashes)

    if args.cmd == "lineage":
        return cmd_lineage(args, lineages, paths)

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
