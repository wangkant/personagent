"""The learned panel: everything the character learned, read from the ledger
files, so it works whether or not the character is running."""
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
TABS = {"in_use": candidates.STATE_PROMOTED, "waiting": candidates.STATE_PROPOSED,
        "discarded": candidates.STATE_REJECTED, "undone": candidates.STATE_ROLLED_BACK,
        "replaced": candidates.STATE_SUPERSEDED}
TAB_OF = {state: tab for tab, state in TABS.items()}
VERBS = {"keep": "promote", "discard": "reject", "undo": "rollback"}
CANDIDATE_ID = re.compile(r"[0-9A-Za-z_-]{1,64}")
POOL = re.compile(r"candidate_ledger\.([a-z]{2,3}(?:-[A-Za-z]{2,4})?)\.jsonl")
LANG = re.compile(r"[a-z]{2,3}(?:-[A-Za-z]{2,4})?")
MAX_LIMIT = 500
# Gaps Keep refuses: an earlier character or page chat. Another language's
# items are used again once the character speaks it.
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
    return {"id": cand.get("candidate_id", ""), "tab": TAB_OF.get(cand.get("state"), ""),
            "gap": _gap(cand, live),
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
    shown = sorted((c for c in rows if c.get("state") == TABS[tab]), key=_order, reverse=True)
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

def _waiting(pool: _Pool, cand: dict) -> dict:
    """Why a waiting item has not applied by itself: the promotion rules
    counted with the policy's own functions, as the terminal trial does."""
    policy, log = pool.policy, pool.log
    now = time.time()
    max_age = policy.max_evidence_age_days * 86400.0
    counting = [e for e in log.many(cand.get("evidence") or [])
                if promotion.supports_candidate(e, cand, policy=policy)]
    supporting = [e for e in counting
                  if not (max_age > 0 and now - promotion.epoch(e.get("ts")) > max_age)]
    strong = [e for e in supporting if promotion.anchors(e, cand)]
    speakers = {str(e.get("speaker_id") or "") for e in supporting} - {""}
    # As turns._admins: the page chat's sender counts as an admin too.
    admins = {str(a).strip()[:64] for a in access.identity_from_env(pool.env).admins
              | access.page_owner(pool.runtime)} - {""}
    related = promotion.related_events(cand, log.all())
    against = promotion.counter_evidence(cand, related, now=now, policy=policy)
    conflicts = promotion.find_conflicts(cand, pool.ledger.all(), policy=policy,
                                         related_events=related)
    speakers_ok = not speakers or bool(admins & speakers) or len(speakers) >= policy.min_speakers
    can_be_strong = evidence.can_be_strong(str(cand.get("type") or ""))
    if _gap(cand, pool.live):
        key = "scope"
    elif not policy.auto_promote:
        key = "off"
    elif against:
        key = "against"
    elif conflicts:
        key = "conflict"
    elif len(strong) < policy.min_strong:
        key = "strong" if can_be_strong else "person"
    elif len(supporting) < policy.min_events:
        key = "events"
    elif not speakers_ok:
        key = "speakers"
    else:
        key = "ready"
    return {"key": key, "events": len(supporting), "needEvents": policy.min_events,
            "strong": len(strong), "needStrong": policy.min_strong, "canBeStrong": can_be_strong,
            "speakers": len(speakers), "needSpeakers": policy.min_speakers, "speakersOk": speakers_ok,
            "stale": len(counting) - len(supporting),
            "maxAgeDays": policy.max_evidence_age_days, "auto": policy.auto_promote}


_REASONS = (
    (re.compile(r"(\d+) compatible events, \d+ strong"), "agreed"),
    (re.compile(r"answered by "), "answered"),
    (re.compile(r"replaced by |supersedes "), "replaced"),
    (re.compile(r"the person it was for disagreed"), "disagreed"),
)
_PLAIN = re.compile(r"local page|operator decision|(promote|reject|rollback|superseded) by operator")


def _reason(text, actor: str) -> dict:
    """A history reason as a key the page translates; the owner's own words
    from the terminal are kept as typed."""
    text = str(text or "").strip()
    for pattern, key in _REASONS:
        match = pattern.search(text)
        if match:
            return {"key": key, "n": match.group(1) if match.groups() else ""}
    if actor == "auto" or not text or _PLAIN.fullmatch(text):
        return {"key": "", "n": ""}
    return {"key": "note", "n": "", "text": dashboard._clip(text, 200)}


def _by(actor) -> str:
    return {"auto": "auto", ACTOR: "page"}.get(str(actor or ""), "terminal")


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
    """The page's verbs for this item, and the wording Keep would retire."""
    legal = dashboard._allowed_actions(str(cand.get("state") or ""))
    verbs = [verb for verb, action in VERBS.items() if action in legal]
    # Keeping an item the character would not use changes nothing it says.
    if _gap(cand, pool.live) in FINAL_GAPS:
        verbs = [verb for verb in verbs if verb != "keep"]
    replaces = ""
    if "keep" in verbs:
        rivals = dashboard._active_rivals(cand, pool.ledger.all(), pool.policy)
        if rivals:
            replaces = dashboard._clip(rivals[0].get("better"), 400)
    return verbs, replaces


def _detail(pool: _Pool, cand: dict) -> dict:
    events = {e.get("event_id"): e for e in pool.log.many(cand.get("evidence") or [])}
    linked = sorted((events[eid] for eid in cand.get("evidence") or [] if eid in events),
                    key=lambda ev: _when(ev.get("ts")))
    verbs, replaces = _actions(pool, cand)
    history = [{"tab": TAB_OF.get(h.get("state"), ""), "when": _when(h.get("ts")),
                "by": _by(h.get("actor")), "why": _reason(h.get("reason"), str(h.get("actor") or ""))}
               for h in cand.get("history") or []]
    successor = pool.ledger.get(cand.get("superseded_by") or "") if cand.get("superseded_by") else None
    context = (cand.get("payload") or {}).get("context") or []
    return {**_row(cand, pool.live), "lang": pool.lang,
            "context": [dashboard._clip(line, 300) for line in context if line][:6],
            "events": [_event(ev, cand, pool) for ev in linked[-MAX_EVIDENCE:]],
            "missing": len(cand.get("evidence") or []) - len(linked),
            "history": history, "actions": verbs, "replaces": replaces,
            "replacedBy": dashboard._clip(successor.get("better"), 400) if successor else "",
            "waiting": _waiting(pool, cand) if cand.get("state") == candidates.STATE_PROPOSED else None}


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
            target = dashboard._ACTIONS.get(action, candidates.STATE_PROMOTED)
            if cand is None or cand.get("state") not in candidates._ALLOWED_FROM[target]:
                raise ValueError("learned_changed")
            ts = datetime.now().isoformat(timespec="seconds")
            if target == candidates.STATE_PROMOTED:
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
    if verb == "keep" and _gap(cand, pool.live) in FINAL_GAPS:
        raise ValueError("learned_scope")
    if verb not in verbs:
        raise ValueError("learned_changed")
    action = "replace" if verb == "keep" and replaces else VERBS[verb]
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
