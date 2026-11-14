"""Inspect what the character has learned, and step in when you choose.

Nothing here waits for anyone. An item is put in use once enough agreeing
reactions arrive; where no further reaction can settle it, the character
decides itself; an item with no new reaction for PROMOTE_OBSERVE_MAX_DAYS is
set aside. These commands only show that record, or step in.

    personagent learned                       # the same as `list`
    personagent learned list                  # what the character is observing
    personagent learned list --state promoted # what is in use now
    personagent learned list --all            # everything, in any state
    personagent learned show <id>             # with its evidence and the character's record
    personagent learned promote <id>          # put an observing item in use now
    personagent learned reject <id>           # set an observing item aside
    personagent learned rollback <id>         # stop using an item in use
    personagent learned restore <id>          # bring back what the character or the time limit set aside
    personagent learned supersede <old> <new> # replace a rewrite in use
    personagent learned rebuild               # re-derive the views

Ids may be abbreviated to any unique prefix. A reply has at most one live
rewrite: `promote` refuses a second one and names the `supersede` to run.
What a person set aside stays set aside.

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
from persona_agent.config_env import env_bool, env_float, env_int  # noqa: E402
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
        _say(f"Run `{_command('list --all')}` to see every candidate and its id.")
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


#: How a reaction was tied to the reply, each a whole phrase so that every
#: language can give it the form its sentence needs.
MATCHED = {"quote": "matched by a quotation of the reply",
           "at": "matched by a mention of the character",
           "dm": "matched as the next message in a private chat",
           "elicited": "matched as the answer to the character's question",
           "self": "the character's own review of its reply"}


#: What a person reads for each state; `--state` still takes the names.
STATES = {candidates.STATE_PROPOSED: "observing", candidates.STATE_PROMOTED: "in use",
          candidates.STATE_REJECTED: "set aside", candidates.STATE_ROLLED_BACK: "taken out of use",
          candidates.STATE_SUPERSEDED: "replaced by another"}


def _state(name) -> str:
    return langs.term(STATES.get(str(name or ""), str(name or "?")))


def _moved(cid: str, before, after) -> str:
    return f"{cid}: {_state(before)} -> {_state(after)}"


def _short(text, width: int = 60) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= width else text[: width - 1] + "…"


def _pad(text: str, width: int) -> str:
    """`text` filled to `width` terminal columns, and at least one space after it."""
    return text + " " * max(1, width - langs.width(text))


def _field(label: str, value) -> None:
    print(f"{_pad(langs.term(label), 11)}{value}")


def _when(ts) -> str:
    return str(ts or "?")[:16].replace("T", " ")


def _judged_on_now(index: promotion.EvidenceIndex, cand: dict, policy) -> bool:
    """Did the character look at exactly the evidence and rivals there are now."""
    review = cand.get("review") or {}
    if not review:
        return False
    related = index.related(cand)
    seen = list(promotion.judged_ids(cand, index.linked(cand), related, now=time.time(),
                                     policy=policy))
    group = promotion.conflict_group(cand, index.peers(cand), policy=policy,
                                     related_events=related)
    peers = sorted(str(c.get("candidate_id") or "") for c in group[1:])
    return (sorted(review.get("seen") or []) == seen
            and sorted(review.get("peers") or []) == peers)


def _standing(index: promotion.EvidenceIndex, cand: dict, decision, policy) -> list[str]:
    """Where an observing item stands, in sentences for langs.term."""
    if not policy.auto_promote:
        return ["Not in use. Automatic learning is switched off (PROMOTE_AUTO_ENABLED), "
                "so nothing new is put in use."]
    judging = env_bool("PROMOTE_JUDGE_ENABLED", True)
    if promotion.needs_character(decision, cand):
        if not judging:
            out = ["Observing. No further reaction can settle it, and the character's own "
                   "decisions are switched off (PROMOTE_JUDGE_ENABLED)."]
        elif _judged_on_now(index, cand, policy):
            review = cand["review"]
            out = [f"Observing. The character looked at it on {_when(review.get('ts'))} "
                   f"and keeps observing: {review.get('reason')}"]
        else:
            out = ["Observing. The character is deciding it itself."]
    elif decision.promote:
        out = ["Every condition for use is met."]
    else:
        out = [_count(index, cand, decision, policy)]
    days = env_float("PROMOTE_OBSERVE_MAX_DAYS", 30.0, minimum=0.0)
    if judging and days > 0:
        newest = promotion.newest_reaction(cand, index.linked(cand), index.related(cand),
                                           policy=policy)
        if newest:
            on = datetime.fromtimestamp(newest + days * 86400.0).strftime("%Y-%m-%d")
            out.append(f"If no new reaction arrives, it will be set aside on {on}.")
    return out


def _count(index: promotion.EvidenceIndex, cand: dict, decision, policy) -> str:
    """The first count more reactions must reach, in the policy's order."""
    if (evidence.can_be_strong(str(cand.get("type") or ""))
            and decision.strong < policy.min_strong):
        return (f"Observing. Strong reactions: {decision.strong} of "
                f"{policy.min_strong} needed.")
    if decision.supporting < policy.min_events:
        return (f"Observing. Agreeing reactions: {decision.supporting} of "
                f"{policy.min_events} needed.")
    if decision.gate == promotion.GATE_PERSON:
        return "Observing. An approving reaction from someone in the chat is still needed."
    speakers = {str(e.get("speaker_id") or "") for e in index.linked(cand)
                if promotion.supports_candidate(e, cand, policy=policy)} - {""}
    return (f"Observing. Different people: {len(speakers)} of "
            f"{policy.min_speakers} needed.")


def _settled(cand: dict, *, objection: bool = True) -> list[str]:
    """Who decided an item that is no longer observing, and why."""
    history = cand.get("history") or []
    if not history:
        return []
    last = history[-1]
    actor, when = str(last.get("actor") or ""), _when(last.get("ts"))
    reason = str(last.get("reason") or "")
    state = cand.get("state")
    out: list[str] = []
    if actor == candidates.ACTOR_CHARACTER:
        out.append({candidates.STATE_PROMOTED: f"Put in use by the character on {when}: {reason}",
                    candidates.STATE_REJECTED: f"Set aside by the character on {when}: {reason}",
                    candidates.STATE_ROLLED_BACK:
                        f"Taken out of use by the character on {when}: {reason}",
                    candidates.STATE_SUPERSEDED:
                        f"Replaced by the character's choice on {when}: {reason}",
                    }.get(state, ""))
    elif state == candidates.STATE_PROMOTED and actor == candidates.ACTOR_AUTO:
        out.append(f"Put in use by agreeing reactions on {when}.")
    elif state == candidates.STATE_PROMOTED and actor:
        out.append(f"Put in use by a person ({actor}) on {when}: {reason}")
    elif state == candidates.STATE_REJECTED and actor == candidates.ACTOR_AUTO:
        if last.get("judge") == candidates.JUDGE_EXPIRY:
            out.append(f"Set aside by the time limit on {when} "
                       f"(PROMOTE_OBSERVE_MAX_DAYS).")
        else:
            out.append(f"Set aside by rule on {when}: {reason}")
    elif state == candidates.STATE_REJECTED and actor:
        out.append(f"Set aside by a person ({actor}) on {when}: {reason}")
        out.append("A person set it aside, and a person's decision stays final.")
    if candidates.restorable(cand):
        out.append(f"To bring it back, run: {_command('restore ' + cand['candidate_id'][:12])}")
    review = cand.get("review") or {}
    if objection and state == candidates.STATE_PROMOTED and review:
        out.append(f"Kept in use after an objection, decided on {_when(review.get('ts'))}: "
                   f"{review.get('reason')}")
    return [line for line in out if line]


#: The empty list in the words the page uses for each state.
NONE_IN = {candidates.STATE_PROPOSED: "Nothing is being observed right now.",
           candidates.STATE_PROMOTED: "Nothing learned is in use yet.",
           candidates.STATE_REJECTED: "Nothing has been set aside.",
           candidates.STATE_ROLLED_BACK: "Nothing has been taken out of use.",
           candidates.STATE_SUPERSEDED: "Nothing has been replaced by another."}


def cmd_list(args, ledger, log, policy) -> int:
    state = "" if args.all else args.state
    rows = [c for c in ledger.all()
            if (not state or c.get("state") == state)
            and (not args.type or c.get("type") == args.type)]
    rows.sort(key=lambda c: str(c.get("created_at") or ""))
    if args.limit > 0:
        rows = rows[-args.limit:]
    if not rows:
        _say(NONE_IN.get(state, "Nothing has been learned yet."))
        if ledger.all():
            _say(f"Run `{_command('list --all')}` to see everything it learned.")
        else:
            _say("It learns from reactions in real chats; practice in `personagent chat` is kept "
                 "apart and does not show here.")
        return 0
    states = [_state(c.get("state")) for c in rows]
    wide = max(langs.width(s) for s in [langs.term("state"), *states]) + 1
    print(f"{_pad(langs.term('id'), 14)}{_pad(langs.term('type'), 18)}{_pad(langs.term('state'), wide)}"
          f"{_pad(langs.term('ev'), 4)}{langs.term('reply -> better')}")
    index = promotion.EvidenceIndex(log.all(), ledger.all())
    for cand, state in zip(rows, states):
        line = _short(cand.get("reply"), 40)
        if cand.get("better"):
            line += "  ->  " + _short(cand.get("better"), 40)
        print(f"{_pad(cand['candidate_id'][:12], 14)}{_pad(str(cand.get('type') or '?'), 18)}"
              f"{_pad(state, wide)}{_pad(str(len(cand.get('evidence') or [])), 4)}{line}")
        if cand.get("state") == candidates.STATE_PROPOSED:
            notes = _standing(index, cand, _decide(ledger, log, cand, policy), policy)
        else:
            notes = _settled(cand)
        for note in notes:
            print(f"{'':14}{langs.term(note)}")
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
    _field("state", _state(cand.get("state")))
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
        direction = str(ev.get("direction") or "")
        how = MATCHED.get(direction, "matching method: {direction}" if direction else "undirected")
        print("    " + langs.term(f"From {who} (recipient {recipient}, "
                                  + how.format(direction=direction) + ")",
                                  keep=(who, recipient, direction)))
        if ev.get("reaction_text"):
            said = _short(ev.get("reaction_text"), 100)
            print("    " + langs.term(f"Said: {said}", keep=(said,)))
        reason = (ev.get("adjudication") or {}).get("reason")
        if reason:
            verdict = _short(reason, 100)
            print("    " + langs.term(f"Verdict: {verdict}", keep=(verdict,)))
        if ev.get("parent_event_id"):
            print("    " + langs.term(f"Follows: {ev['parent_event_id'][:12]}"))

    if cand.get("history"):
        print()
        _say("lifecycle")
        for h in cand["history"]:
            stamp = " ".join(str(h.get(k)) for k in ("judge", "model") if h.get(k))
            print(f"  {h.get('ts') or '?':20} {h.get('state'):11} "
                  f"{h.get('actor') or '?':9} {_short(h.get('reason'), 70)}"
                  + (f"  [{stamp}]" if stamp else ""))
    review = cand.get("review") or {}
    if review:
        print()
        _say("the character's record")
        _say(f"The character last looked on {_when(review.get('ts'))} and kept "
             f"observing: {review.get('reason')}"
             if cand.get("state") == candidates.STATE_PROPOSED else
             f"Kept in use after an objection, decided on {_when(review.get('ts'))}: "
             f"{review.get('reason')}")
        _say(f"Reactions it judged: {len(review.get('seen') or [])}; "
             f"rival rewrites: {len(review.get('peers') or [])}.")
        if review.get("judge"):
            _say(f"Judgement: {review['judge']}")
        if review.get("model"):
            _say(f"Model: {review['model']}")
    if cand.get("superseded_by"):
        print()
        _field("superseded by", cand["superseded_by"])
    if cand.get("supersedes"):
        print()
        _field("supersedes", cand["supersedes"])

    print()
    if cand.get("state") == candidates.STATE_PROPOSED:
        decision = _decide(ledger, log, cand, policy)
        index = promotion.EvidenceIndex(log.all(), ledger.all())
        for note in _standing(index, cand, decision, policy):
            _say(note)
        if decision.blocked_by:
            _say(f"Disagreeing reactions or rival rewrites: {decision.blocked_by}")
    else:
        # The objection review is already printed with the record above.
        for note in _settled(cand, objection=False):
            _say(note)
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
        state = STATES.get(str(before or ""), str(before or "?"))
        _say({"promote": f"Refused: this candidate cannot be put in use. Its state: {state}.",
              "reject": f"Refused: this candidate cannot be set aside. Its state: {state}.",
              "rollback": f"Refused: this candidate cannot be taken out of use. Its state: {state}."
              }[action])
        return 1
    print(_moved(cid, before, ledger.get(cid).get("state")))
    if action == "promote":
        # Drafts of the complaint this pair answers have nothing left for them.
        for other in promotion.answered_drafts(ledger.get(cid), ledger.all(),
                                               policy=policy):
            if ledger.reject(other, ts=now, actor=args.actor,
                             reason=f"answered by {cid}"):
                print(_moved(other, candidates.STATE_PROPOSED, candidates.STATE_REJECTED)
                      + " " + langs.term(f"(answered by {cid[:12]})"))
    _rebuild(paths, ledger)
    return 0


def cmd_restore(args, ledger, log, policy, paths) -> int:
    """Bring back what the character or the time limit set aside, or what the
    character or a rule took out of use, through the ledger's own restore; a
    person's decision or a content rule's discard stays."""
    cid = _resolve_id(ledger, args.candidate_id)
    if cid is None:
        return 1
    cand = ledger.get(cid)
    before = cand.get("state")
    if not candidates.restorable(cand):
        last = (cand.get("history") or [{}])[-1]
        actor = str(last.get("actor") or "")
        if before != candidates.STATE_REJECTED:
            _say("Refused: this candidate cannot be brought back. Its state: "
                 f"{STATES.get(str(before or ''), str(before or '?'))}.")
        elif actor in (candidates.ACTOR_AUTO, candidates.ACTOR_CHARACTER, ""):
            _say(f"Refused: {cid[:12]} was set aside by rule, so it cannot be brought back.")
        else:
            _say(f"Refused: {cid[:12]} was set aside by a person ({actor}), "
                 f"and a person's decision stays final.")
        return 1
    rivals = promotion.active_rivals(cand, ledger.all(), policy=policy)
    if rivals:
        rival = rivals[0]["candidate_id"]
        _say(f"Refused: {rival[:12]} already rewrites this reply, as "
             f"{_short(rivals[0].get('better'), 50)!r}. A reply keeps one rewrite; to replace it, run:")
        print(f"  {_command(f'supersede {rival[:12]} {cid[:12]}')}")
        return 1
    now = datetime.now().isoformat(timespec="seconds")
    if not ledger.restore(cid, ts=now, actor=args.actor,
                          reason=args.reason or "restore by operator"):
        _say("Refused: this candidate cannot be brought back. Its state: "
             f"{STATES.get(str(before or ''), str(before or '?'))}.")
        return 1
    print(_moved(cid, before, ledger.get(cid).get("state")))
    for other in promotion.answered_drafts(ledger.get(cid), ledger.all(), policy=policy):
        if ledger.reject(other, ts=now, actor=args.actor, reason=f"answered by {cid}"):
            print(_moved(other, candidates.STATE_PROPOSED, candidates.STATE_REJECTED)
                  + " " + langs.term(f"(answered by {cid[:12]})"))
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

    lst = sub.add_parser("list", help=langs.term("list candidates (default: observing)"))
    lst.add_argument("--state", default=candidates.STATE_PROPOSED, choices=candidates.STATES,
                     help=langs.term("proposed (observing, the default), promoted (in use), rejected "
                                     "(set aside), rolled_back (taken out of use) or superseded "
                                     "(replaced by another)"))
    lst.add_argument("--all", action="store_true", help=langs.term("list every item, in any state"))
    lst.add_argument("--type", default="", choices=candidates.TYPES,
                     help=langs.term("preference_pair (a better wording for a reply) or "
                                     "positive_example (a reply worth keeping); default: both"))
    lst.add_argument("--limit", type=int, default=20,
                     help=langs.term("show at most this many, the newest (default 20; 0: no limit)"))
    id_help = langs.term("the id that `list` shows, or any unique start of it")

    show = sub.add_parser("show", help=langs.term("one candidate with its evidence"))
    show.add_argument("candidate_id", help=id_help)

    for name, helptext in (("promote", "put an observing item in use now"),
                           ("reject", "set an observing item aside"),
                           ("rollback", "stop using an item in use"),
                           ("restore", "bring back an item the character or the time limit set aside")):
        sp = sub.add_parser(name, help=langs.term(helptext))
        sp.add_argument("candidate_id", help=id_help)
        sp.add_argument("--reason", default="")

    sup = sub.add_parser("supersede", help=langs.term("replace one candidate with another"))
    sup.add_argument("old_id")
    sup.add_argument("new_id")
    sup.add_argument("--reason", default="")

    sub.add_parser("rebuild", help=langs.term("rewrite the files the running agent reads from the "
                                              "learning record, after it was changed by hand"))

    lin = sub.add_parser("lineage", help=langs.term("the character versions (PERSONA_VERSION) whose "
                                                    "learning is shared"))
    lin.add_argument("action", nargs="?", default="show", choices=("show", "adopt"),
                     help=langs.term("show the versions (the default), or adopt an earlier character's "
                                     "hash into the current one"))
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
    if args.cmd == "restore":
        return cmd_restore(args, ledger, log, policy, paths)
    if args.cmd == "supersede":
        return cmd_supersede(args, ledger, log, policy, paths)
    return cmd_rebuild(args, ledger, log, policy, paths)


if __name__ == "__main__":
    sys.exit(main())
