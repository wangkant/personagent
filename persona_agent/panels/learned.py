"""The learned panel: everything the character learned, read from the ledger
files, so it works whether or not the character is running. The character
decides by itself; a person may step in here, never because anything waits."""
from __future__ import annotations

import asyncio
import os
import re
import threading
import time
from datetime import datetime
from pathlib import Path

from fastapi import Request

from .. import access, candidates, channels, dashboard, evidence, lineage, promotion
from .. import connections as conn
from ..config_env import env_int
from ..settings import content_lang
from ..storage import FileLock, LockUnavailable

# Error codes this panel raises as ValueError, which the page may show.
ERRORS: frozenset[str] = frozenset({
    "learned_invalid", "learned_unknown", "learned_changed", "learned_busy",
    "learned_unavailable", "learned_failed", "learned_scope"})

ACTOR = "dashboard"
REASON = "local page"
TABS = {"in_use": (candidates.STATE_PROMOTED,), "observing": (candidates.STATE_PROPOSED,),
        "set_aside": (candidates.STATE_REJECTED, candidates.STATE_ROLLED_BACK,
                      candidates.STATE_SUPERSEDED)}
TAB_OF = {state: tab for tab, states in TABS.items() for state in states}
# A person's optional actions, each the dashboard API's own action.
VERBS = {"use": "promote", "set_aside": "reject", "undo": "rollback", "bring_back": "restore"}
CANDIDATE_ID = re.compile(r"[0-9A-Za-z_-]{1,64}")
POOL = re.compile(r"candidate_ledger\.([a-z]{2,3}(?:-[A-Za-z]{2,4})?)\.jsonl")
LANG = re.compile(r"[a-z]{2,3}(?:-[A-Za-z]{2,4})?")
MAX_LIMIT = 500
# Gaps where putting an item into use is refused: an earlier character or page
# chat. Another language's items are used again once the character speaks it.
FINAL_GAPS = ("persona", "chat")
MAX_EVIDENCE = 40
_SECRET_SUFFIXES = ("_KEY", "_TOKEN", "_SECRET", "PASSWORD")
# One decision at a time from this page; the ledger's own lock covers each append.
_deciding = threading.Lock()


class _Pool:
    """One language's ledger, evidence log and policy, read from the files."""

    def __init__(self, runtime: Path, lang: str, env: dict) -> None:
        self.runtime, self.lang, self.env = runtime, lang, env
        self.ledger = candidates.CandidateLedger(runtime / f"candidate_ledger.{lang}.jsonl")
        self.log = evidence.EvidenceLog(runtime / f"evidence.{lang}.jsonl")
        self.policy = promotion.Policy.from_env(env)
        self.judge = dashboard.Judge.from_env(env, self.policy, access.page_owner(runtime))
        lin = lineage.PersonaLineage(runtime / lineage.FILE_NAME)
        for version, hashes in lin.versions().items():
            evidence.register_persona_lineage(version, hashes)
        self.live = _live(runtime, env, lin, lang)

    def rebuild(self) -> bool:
        try:
            candidates.rebuild_views(
                self.ledger, self.runtime / f"promoted.examples.{self.lang}.jsonl",
                self.runtime / f"promoted.feedback.{self.lang}.jsonl",
                max_examples=env_int("PROMOTE_MAX_EXAMPLES", 500, minimum=0, env=self.env),
                max_pairs=env_int("PROMOTE_MAX_FEEDBACK", 500, minimum=0, env=self.env))
        except OSError:
            return False
        return True


def _env(workspace) -> dict:
    # What the service process sees: .env over this process's environment.
    return {**os.environ, **workspace.config()}


def _runtime(workspace, env: dict) -> Path:
    home = workspace.home
    path = Path(str(env.get("AGENT_RUNTIME_DIR") or "").strip() or "runtime").expanduser()
    path = (path if path.is_absolute() else home / path).resolve()
    try:
        path.relative_to(home)
    except ValueError:
        # The service refuses such a folder too; never read outside the home.
        raise ValueError("learned_unavailable") from None
    return path


def _current(env: dict) -> str:
    return content_lang(env.get("AGENT_LANG", "en") or "en")


def _pools(runtime: Path) -> list[str]:
    try:
        names = [p.name for p in runtime.iterdir() if p.is_file()]
    except OSError:
        return []
    return sorted({m.group(1) for n in names if (m := POOL.fullmatch(n))})


def _open(workspace, lang: str = "") -> _Pool:
    env = _env(workspace)
    runtime = _runtime(workspace, env)
    lang = str(lang or "") or _current(env)
    if not LANG.fullmatch(lang):
        raise ValueError("learned_invalid")
    return _Pool(runtime, lang, env)


def _live(runtime: Path, env: dict, lin: lineage.PersonaLineage, pool: str) -> dict:
    """The scope the running character would use, as views._live_scope builds it."""
    version = str(env.get("PERSONA_VERSION") or "").strip()
    scope = evidence.normalize_scope({"lang": _current(env), "persona": env.get("PERSONA_NAME"),
                                      "persona_version": version})
    page = "".join(channels.learning_key(channels.DM_ROUTING_PREFIX + owner)
                   for owner in sorted(access.page_owner(runtime)))
    # The character reads only its own language's ledger.
    return {**scope, "root": lin.root(version), "page": page, "pool": pool}


def _gap(cand: dict, live: dict) -> str:
    """Why the character would not use this item now, as the agent's
    _scope_authorizes decides it; empty when it would."""
    scope = cand.get("scope") or {}
    if live["pool"] != live["lang"] or str(scope.get("lang") or "") != live["lang"]:
        return "lang"
    # Without a lineage for this version the current hash is unknown, so only the labels compare.
    if (any(str(scope.get(key) or "") != live[key] for key in ("persona", "persona_version"))
            or (live["root"] and evidence.persona_identity(scope) != live["root"])):
        return "persona"
    conv = str(scope.get("conv_id") or "")
    # A reset page chat never comes back; other chats may talk again.
    if live["page"] and channels.platform_of(conv) == access.PAGE_PLATFORM and conv != live["page"]:
        return "chat"
    return ""


def _secrets(env: dict) -> list[str]:
    values = {str(v or "").strip() for k, v in env.items() if k.upper().endswith(_SECRET_SUFFIXES)}
    return sorted((v for v in values if len(v) >= 8), key=len, reverse=True)


def _when(ts) -> float:
    return promotion.epoch(ts) if ts else 0.0


def _chat(conv: str) -> dict:
    """Where an item was learned, as the page names it; no persona keys."""
    key = dashboard._routing_key(conv)
    platform = channels.platform_of(key) if key else ""
    spec = conn.BY_KIND.get(platform)
    tail = key.split(":")[-1] if key else ""
    return {"id": key, "platform": platform, "name": list(spec.name) if spec else [platform, platform],
            "kind": "dm" if channels.is_dm(key) else "group",
            "tail": tail if len(tail) <= 8 else "…" + tail[-6:]}


def _row(cand: dict, live: dict) -> dict:
    history = cand.get("history") or []
    payload = cand.get("payload") or {}
    state = str(cand.get("state") or "")
    return {"id": cand.get("candidate_id", ""), "tab": TAB_OF.get(state, ""),
            "state": state, "gap": _gap(cand, live),
            # Who put it where it is; an observed item has no decider yet.
            "by": "" if state == candidates.STATE_PROPOSED or not history
            else dashboard.decided_by(history[-1])["by"],
            "kind": "wording" if cand.get("type") == candidates.TYPE_PAIR else "repeat",
            "said": dashboard._clip(cand.get("reply"), 400),
            "better": dashboard._clip(cand.get("better"), 400),
            "lesson": dashboard._clip(payload.get("lesson"), 300),
            "chat": _chat(str((cand.get("scope") or {}).get("conv_id") or "")),
            "when": _when(cand.get("created_at")),
            "changed": _when(history[-1].get("ts")) if history else 0.0,
            "evidence": len(cand.get("evidence") or [])}


def _order(cand: dict) -> tuple:
    history = cand.get("history") or [{}]
    return str(history[-1].get("ts") or ""), str(cand.get("created_at") or "")


def overview(workspace, lang: str = "", tab: str = "", limit: int = 30) -> dict:
    pool = _open(workspace, lang)
    if tab and tab not in TABS:
        raise ValueError("learned_invalid")
    tab = tab or "in_use"
    limit = max(1, min(int(limit or 30), MAX_LIMIT))
    rows = pool.ledger.all()
    totals = {name: 0 for name in TABS}
    # Per tab, the items the character would not use now (another scope).
    idle = {name: 0 for name in TABS}
    chats = set()
    for cand in rows:
        name = TAB_OF.get(cand.get("state"))
        if not name:
            continue
        totals[name] += 1
        if _gap(cand, pool.live):
            idle[name] += 1
        elif name == "in_use":
            chats.add(str((cand.get("scope") or {}).get("conv_id") or ""))
    # Newest change first, so what was just decided is on top.
    shown = sorted((c for c in rows if c.get("state") in TABS[tab]), key=_order, reverse=True)
    current = _current(pool.env)
    langs = []
    for code in sorted(set(_pools(pool.runtime)) | {current, pool.lang}):
        count = len(rows) if code == pool.lang else len(
            candidates.CandidateLedger(pool.runtime / f"candidate_ledger.{code}.jsonl").all())
        langs.append({"code": code, "count": count, "current": code == current})
    payload = {"lang": pool.lang, "current": current, "langs": langs, "tab": tab,
               "running": workspace.services.running("agent"),
               "totals": totals, "idle": idle, "chats": len(chats - {""}), "count": totals[tab],
               "items": [_row(c, pool.live) for c in shown[:limit]]}
    return dashboard._scrub(payload, _secrets(pool.env))


# ------------------------------------------------------------- one item ----

def _standing(pool: _Pool, cand: dict) -> dict:
    """Where an observed item stands, as the Activity view says it."""
    index = promotion.EvidenceIndex(pool.log.all(), pool.ledger.all())
    return dashboard.standing(cand, index, pool.policy, pool.judge, time.time())


_REASONS = (
    (re.compile(r"(\d+) compatible events, \d+ strong"), "agreed"),
    (re.compile(r"answered by "), "answered"),
    (re.compile(r"replaced by |supersedes "), "replaced"),
    (re.compile(r"the person it was for disagreed"), "disagreed"),
)
_PLAIN = re.compile(r"local page|operator decision|(promote|reject|rollback|superseded) by operator")


def _reason(text, actor: str, decided: dict | None = None) -> dict:
    """A history reason as a key the page translates; the character's own
    sentence and the owner's words from the terminal are kept as written."""
    decided = decided or dashboard.decided_by({"actor": actor, "reason": text})
    if decided["by"] == "time":
        return {"key": "expired", "n": decided["days"]}
    if decided["by"] == "rule":
        return {"key": f"rule_{decided['why']}", "n": ""}
    if decided["by"] == "character":
        return {"key": "said", "n": "", "text": decided["why"]}
    text = str(text or "").strip()
    for pattern, key in _REASONS:
        match = pattern.search(text)
        if match:
            return {"key": key, "n": match.group(1) if match.groups() else ""}
    if actor == candidates.ACTOR_AUTO or not text or _PLAIN.fullmatch(text):
        return {"key": "", "n": ""}
    return {"key": "note", "n": "", "text": dashboard._clip(text, 200)}


def _by(actor, decided: dict) -> str:
    """auto, character, rule, time, or for a person: page or terminal."""
    if decided["by"] in ("character", "rule", "time"):
        return decided["by"]
    return {candidates.ACTOR_AUTO: "auto", ACTOR: "page"}.get(str(actor or ""), "terminal")


def _step(entry: dict) -> dict:
    decided = dashboard.decided_by(entry)
    actor = str(entry.get("actor") or "")
    return {"state": str(entry.get("state") or ""), "when": _when(entry.get("ts")),
            "by": _by(actor, decided), "why": _reason(entry.get("reason"), actor, decided)}


def _event(ev: dict, cand: dict, pool: _Pool) -> dict:
    adj = ev.get("adjudication") or {}
    kind = str(ev.get("kind") or "")
    return {"who": dashboard._clip(ev.get("speaker_name") or "", 64),
            "what": str(ev.get("reaction_type") or "") if kind == evidence.KIND_REACTION else kind,
            "said": dashboard._clip(ev.get("reaction_text"), 500),
            "better": dashboard._clip(adj.get("better"), 300),
            "reading": dashboard._clip(adj.get("reason"), 200),
            "strong": evidence.classify_strength(ev) == evidence.STRONG,
            "counts": promotion.supports_candidate(ev, cand, policy=pool.policy),
            "when": _when(ev.get("ts"))}


def _actions(pool: _Pool, cand: dict) -> tuple[list[str], str]:
    """A person's optional verbs for this item, and the wording putting it
    into use would retire."""
    legal = dashboard._allowed_actions(str(cand.get("state") or ""), cand)
    verbs = [verb for verb, action in VERBS.items() if action in legal]
    # Using an item the character would not use changes nothing it says.
    if _gap(cand, pool.live) in FINAL_GAPS:
        verbs = [verb for verb in verbs if verb not in ("use", "bring_back")]
    replaces = ""
    if {"use", "bring_back"} & set(verbs):
        rivals = dashboard._active_rivals(cand, pool.ledger.all(), pool.policy)
        if rivals:
            replaces = dashboard._clip(rivals[0].get("better"), 400)
    return verbs, replaces


def _detail(pool: _Pool, cand: dict) -> dict:
    events = {e.get("event_id"): e for e in pool.log.many(cand.get("evidence") or [])}
    linked = sorted((events[eid] for eid in cand.get("evidence") or [] if eid in events),
                    key=lambda ev: _when(ev.get("ts")))
    verbs, replaces = _actions(pool, cand)
    steps = cand.get("history") or []
    history = [_step(h) for h in steps]
    review = cand.get("review") or {}
    if review:
        # The character's latest look, which changes no state.
        history.append({"state": "review", "when": _when(review.get("ts")),
                        "by": "character" if review.get("actor") == candidates.ACTOR_CHARACTER
                        else "rule", "why": _reason(review.get("reason"), str(review.get("actor") or ""))})
        history.sort(key=lambda h: h["when"])
    successor = pool.ledger.get(cand.get("superseded_by") or "") if cand.get("superseded_by") else None
    context = (cand.get("payload") or {}).get("context") or []
    observed = cand.get("state") == candidates.STATE_PROPOSED
    return {**_row(cand, pool.live), "lang": pool.lang,
            "context": [dashboard._clip(line, 300) for line in context if line][:6],
            "events": [_event(ev, cand, pool) for ev in linked[-MAX_EVIDENCE:]],
            "missing": len(cand.get("evidence") or []) - len(linked),
            "history": history, "actions": verbs, "replaces": replaces,
            "replacedBy": dashboard._clip(successor.get("better"), 400) if successor else "",
            "standing": _standing(pool, cand) if observed else None,
            "decided": None if observed or not steps else dashboard.decided_by(steps[-1])}


def item(workspace, cid: str, lang: str = "") -> dict:
    if not CANDIDATE_ID.fullmatch(str(cid or "")):
        raise ValueError("learned_invalid")
    pool = _open(workspace, lang)
    cand = pool.ledger.get(cid)
    if cand is None:
        raise ValueError("learned_unknown")
    return dashboard._scrub(_detail(pool, cand), _secrets(pool.env))


# --------------------------------------------------------------- decide ----

def _local(pool: _Pool, cid: str, action: str) -> None:
    """The decision written straight to the files, as `personagent learned` does."""
    ledger = pool.ledger
    with _deciding:
        try:
            lock = FileLock(pool.runtime / ".learned-page.lock", timeout=5).acquire()
        except LockUnavailable:
            raise ValueError("learned_busy") from None
        try:
            cand = ledger.get(cid)
            verb = "promote" if action == "replace" else action
            if cand is None or verb not in dashboard._allowed_actions(
                    str(cand.get("state") or ""), cand):
                raise ValueError("learned_changed")
            ts = datetime.now().isoformat(timespec="seconds")
            if action == "restore":
                if not dashboard._restore(pool, cid, ts, REASON):
                    raise ValueError("learned_changed")
            elif verb == "promote":
                if dashboard._promote(pool, cid, action, ts, REASON) is not None:
                    raise ValueError("learned_changed")
            elif not {"reject": ledger.reject, "rollback": ledger.rollback}[action](
                    cid, ts=ts, actor=ACTOR, reason=REASON):
                raise ValueError("learned_changed")
            if not pool.rebuild():
                raise ValueError("learned_failed")
        finally:
            lock.release()


async def decide(workspace, payload: dict) -> dict:
    cid, verb = str(payload.get("id") or ""), str(payload.get("action") or "")
    if verb not in VERBS or not CANDIDATE_ID.fullmatch(cid):
        raise ValueError("learned_invalid")
    pool = await asyncio.to_thread(_open, workspace, str(payload.get("lang") or ""))
    cand = pool.ledger.get(cid)
    if cand is None:
        raise ValueError("learned_unknown")
    verbs, replaces = _actions(pool, cand)
    if verb in ("use", "bring_back") and _gap(cand, pool.live) in FINAL_GAPS:
        raise ValueError("learned_scope")
    if verb not in verbs:
        raise ValueError("learned_changed")
    action = "replace" if verb == "use" and replaces else VERBS[verb]
    # The running character holds its own pool's state, so it decides there.
    remote = None
    if pool.lang == _current(pool.env) and workspace.services.running("agent"):
        try:
            remote = await workspace._activity_call(
                "POST", f"/api/dashboard/candidates/{cid}/{action}", json={"reason": REASON})
        except ValueError as exc:
            raise ValueError("learned_changed" if str(exc) == "activity_changed"
                             else "learned_unavailable") from None
    if remote is None or remote.get("off"):
        await asyncio.to_thread(_local, pool, cid, action)
    return await asyncio.to_thread(item, workspace, cid, pool.lang)


def mount(app, workspace, body) -> None:
    @app.get("/api/learned")
    async def learned_overview(lang: str = "", tab: str = "", limit: int = 30):
        return await asyncio.to_thread(overview, workspace, lang, tab, limit)

    @app.get("/api/learned/item")
    async def learned_item(id: str = "", lang: str = ""):
        return await asyncio.to_thread(item, workspace, id, lang)

    @app.post("/api/learned/decide")
    async def learned_decide(request: Request):
        return await decide(workspace, await body(request))
