"""The character's life as its home page shows it: what it is doing now, how
long it has lived here, what it has gathered, and its days.

Everything here is read from what already exists (the library of its walks,
its notes about the owner, what it learned), so the page can show it while
the service is stopped too. Nothing here ever goes down or punishes absence.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urlsplit

from . import access, candidates, channels, memstore, people, promotion
from .library import DISMISSED, KEPT, KINDS, Item, Library
from .storage import atomic_write_text

# Replaced in tests: every "now" here comes from this.
clock = time.time

BORN_FILE = Path("desktop") / "born.json"
# How long "back from a walk" stays on the home after one that brought something.
BACK_S = 600
# What it kept for the owner and was never asked about stays in the days only after this.
TELL_DAYS = 7
LEVEL_DAYS = (1, 7, 30, 100, 365)
DAYS_LIMIT = 30
DAYS_MAX = 100
# The only hosts whose players a card may embed; the page's frame-src lists the same.
PLAYER_HOSTS = ("www.youtube-nocookie.com", "www.youtube.com", "player.bilibili.com")
STATES = ("home", "answering", "out", "asleep", "back", "off")
_PICTURE = re.compile(r"/api/library/picture/[0-9a-f]{16}")
_TEXT_MAX = 300


# ------------------------------------------------------------------ sources --

@dataclass
class Sources:
    """What the days and the growth facts are read from: the running agent's
    own state, or the files it keeps when it is stopped."""
    runtime: Path
    memories: dict = field(default_factory=dict)
    admins: frozenset = frozenset()
    ledger: list = field(default_factory=list)
    # A model is set, so the first start can be marked.
    configured: bool = False

    @property
    def library(self) -> Library:
        return Library(self.runtime)

    @classmethod
    def of_agent(cls, agent, runtime: Path) -> "Sources":
        try:
            ledger = agent.candidate_ledger.all()
        except Exception:
            ledger = []
        return cls(Path(runtime), dict(agent.memories), frozenset(agent._admins()), ledger, True)

    @classmethod
    def from_files(cls, runtime: Path, values: dict) -> "Sources":
        """The files of a stopped service; `values` are its settings (.env)."""
        from .approvals import approved_admins
        from .settings import content_lang
        runtime = Path(runtime)
        lang = content_lang(values.get("AGENT_LANG", "") or "en")
        memory = Path(values.get("MEMORY_FILE") or "memory.json")
        try:
            memories = memstore.load_memory_file(memory if memory.is_absolute() else runtime / memory)
        except Exception:
            memories = {}
        ledger_path = runtime / f"candidate_ledger.{lang}.jsonl"
        try:
            ledger = candidates.CandidateLedger(ledger_path).all() if ledger_path.is_file() else []
        except Exception:
            ledger = []
        admins = (access.parse_ids(values.get("ADMIN_IDS", "")) | access.page_owner(runtime)
                  | approved_admins(runtime))
        return cls(runtime, memories, frozenset(admins), ledger, bool(values.get("LLM_API_KEY")))


# -------------------------------------------------------------------- birth --

def born(src: Sources, now: Optional[float] = None) -> int:
    """When it moved in: the marker written once at the first configured
    start; 0 before that. A home older than the marker dates from its first note."""
    path = src.runtime / BORN_FILE
    try:
        at = int(json.loads(path.read_text(encoding="utf-8"))["at"])
        if at > 0:
            return at
    except (OSError, ValueError, KeyError, TypeError):
        pass
    if not src.configured:
        return 0
    now = int(clock() if now is None else now)
    first = [t for t in (_note_time(row) for _, row in _all_notes(src)) if 0 < t < now]
    at = int(min(first, default=now))
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(path, json.dumps({"at": at}))
    except OSError:
        pass
    return at


def day_count(born_at: int, now: float) -> int:
    """Day 1 is the day it moved in, counted in calendar days on this computer."""
    if born_at <= 0:
        return 0
    return max(1, (date.fromtimestamp(now) - date.fromtimestamp(born_at)).days + 1)


def level(day: int) -> int:
    return sum(1 for band in LEVEL_DAYS if day >= band)


# -------------------------------------------------------------------- facts --

def _all_notes(src: Sources):
    for conv, rows in src.memories.items():
        for row in rows if isinstance(rows, list) else []:
            if isinstance(row, dict) and str(row.get("text") or "").strip():
                yield str(conv), row


def _note_time(row: dict) -> int:
    for key in ("born", "time"):
        try:
            value = float(row.get(key) or 0)
        except (TypeError, ValueError):
            value = promotion.epoch(row.get(key))
        if value > 0:
            return int(value)
    return 0


def owner_notes(src: Sources) -> list[dict]:
    """Notes about the owner only: said of an owner id anywhere, or with no
    other subject in the owner's own chat. Notes about anyone else never show."""
    operator = people.operator_ids(src.admins, src.memories)
    found = []
    for conv, row in _all_notes(src):
        uid = str(row.get("user_id") or "")
        if uid in operator or people.is_page_id(uid) or (not uid and people.is_operator_dm(conv, operator)):
            found.append(row)
    return found


def _promoted(src: Sources) -> list[dict]:
    return [c for c in src.ledger if isinstance(c, dict) and c.get("state") == candidates.STATE_PROMOTED]


def _learned_in_private(cand: dict, operator: frozenset) -> bool:
    """Shown in the days only when learned with the owner or everywhere: a
    group's lesson may carry other people's names."""
    conv = str((cand.get("scope") or {}).get("conv_id") or "")
    if not conv:
        return True
    if not conv.startswith(channels.DM_LEARNING_PREFIX):
        return False
    uid = conv[len(channels.DM_LEARNING_PREFIX):]
    return uid in operator or people.is_page_id(uid)


def _learned_at(cand: dict) -> int:
    steps = [promotion.epoch(h.get("ts")) for h in cand.get("history") or []
             if isinstance(h, dict) and h.get("state") == candidates.STATE_PROMOTED]
    return int(max(steps, default=0) or promotion.epoch(cand.get("created_at")) or 0)


def growth(src: Sources, now: Optional[float] = None) -> dict:
    now = clock() if now is None else now
    library = src.library
    day = day_count(born(src, now), now)
    return {"day": day, "level": level(day), "remembers": len(owner_notes(src)),
            "learned": len(_promoted(src)), "sites": len(library.outing().sites),
            "kept": sum(1 for item in library.items() if item.state == KEPT)}


def tell_queue(library: Library, now: Optional[float] = None) -> list[Item]:
    """What it kept for the owner and has not said, oldest first; older than a
    week it stays in the days only."""
    now = clock() if now is None else now
    return [item for item in library.to_tell() if item.seen_at >= now - TELL_DAYS * 86400]


# ---------------------------------------------------------------------- now --

def asleep_until(now: float, offset_hours: float) -> Optional[int]:
    """The waking time when `now` is inside the sleep hours on the persona's clock, else None."""
    from .textproc import SLEEP_HOUR_END, SLEEP_HOUR_START
    local = datetime.fromtimestamp(now, timezone(timedelta(hours=offset_hours)))
    start, end, hour = SLEEP_HOUR_START, SLEEP_HOUR_END, local.hour
    inside = start <= hour < end if start <= end else (hour >= start or hour < end)
    if not inside:
        return None
    wake = local.replace(hour=end, minute=0, second=0, microsecond=0)
    if wake <= local:
        wake += timedelta(days=1)
    return int(wake.timestamp())


def busy_chat(agent) -> Optional[tuple[str, str]]:
    """(platform, "group"|"dm") of a chat whose reply is in flight, or None."""
    for key, gate in list(getattr(agent, "_pending_outbound", {}).items()):
        if getattr(gate, "busy", False):
            return channels.platform_of(key), "dm" if channels.is_dm(key) else "group"
    return None


def now_state(library: Library, now: float, *, running: bool,
              busy: Optional[tuple[str, str]] = None, sleep_until: Optional[int] = None) -> dict:
    if not running:
        return {"state": "off", "where": "", "since": 0, "until": None, "count": 0}
    outing = library.outing()
    if outing.state == "out":
        return {"state": "out", "where": outing.site, "since": int(outing.since), "until": None, "count": 0}
    if busy:
        return {"state": "answering", "where": busy[0], "chat": busy[1], "since": int(now),
                "until": None, "count": 0}
    if sleep_until:
        return {"state": "asleep", "where": "", "since": int(now), "until": int(sleep_until), "count": 0}
    if outing.last_count > 0 and 0 <= now - outing.last_end < BACK_S:
        return {"state": "back", "where": "", "since": int(outing.last_end),
                "until": int(outing.last_end + BACK_S), "count": int(outing.last_count)}
    return {"state": "home", "where": "", "since": int(outing.last_end or 0), "until": None, "count": 0}


def can_go_out(agent) -> tuple[bool, str]:
    """Whether a walk may start now and, if not, the code why. Walking is the
    roam part's own: without it the character only stays home."""
    roam = getattr(agent, "roam", None) if agent is not None else None
    if roam is None:
        return False, "off"
    try:
        missing = str(roam.available() or "")
        if missing:
            return False, missing
        allowed, code = roam.can_go_out()
    except Exception:
        return False, "off"
    return (True, "") if allowed else (False, str(code or "off"))


def home(src: Sources, *, agent=None, running: bool = False, busy=None, sleep_until=None,
         now: Optional[float] = None) -> dict:
    now = clock() if now is None else now
    library = src.library
    allowed, why = can_go_out(agent) if running else (False, "off")
    return {"now": now_state(library, now, running=running, busy=busy, sleep_until=sleep_until),
            "growth": growth(src, now), "tell": len(tell_queue(library, now)),
            "canGoOut": allowed, "whyNot": why}


def of_agent(agent, runtime: Path, now: Optional[float] = None) -> dict:
    """The home of a running character."""
    from .textproc import _env_tz_offset
    now = clock() if now is None else now
    return home(Sources.of_agent(agent, runtime), agent=agent, running=True, busy=busy_chat(agent),
                sleep_until=asleep_until(now, _env_tz_offset()), now=now)


# --------------------------------------------------------------------- days --

def _clip(text, limit: int = _TEXT_MAX) -> str:
    value = " ".join(str(text or "").split())
    return value if len(value) <= limit else value[:limit - 1] + "…"


def entries(src: Sources, now: Optional[float] = None, *, kept_only: bool = False) -> list[dict]:
    """Every entry of its days, newest first."""
    now = clock() if now is None else now
    found = []
    for item in src.library.items():
        if item.state == DISMISSED:
            continue
        if kept_only and item.state != KEPT:
            continue
        found.append({"id": item.id, "at": int(item.seen_at), "kind": "saw", "text": _clip(item.why),
                      "card": clean_card(item.card()), "kept": item.state == KEPT})
    if kept_only:
        return found
    operator = people.operator_ids(src.admins, src.memories)
    for cand in _promoted(src):
        if not _learned_in_private(cand, operator):
            continue
        better, said = _clip(cand.get("better")), _clip(cand.get("reply"))
        found.append({"id": "learned:" + str(cand.get("candidate_id") or ""), "at": _learned_at(cand),
                      "kind": "learned", "text": better or said, "instead": said if better else "",
                      "card": None, "kept": False})
    for row in owner_notes(src):
        ident = str(row.get("id") or hashlib.sha256(str(row.get("text")).encode("utf-8")).hexdigest()[:12])
        found.append({"id": "remembered:" + ident, "at": _note_time(row), "kind": "remembered",
                      "text": _clip(row.get("text")), "card": None, "kept": False})
    at = born(src, now)
    if at:
        found.append({"id": "arrived", "at": at, "kind": "arrived", "text": "", "card": None, "kept": False})
    found.sort(key=lambda e: (e["at"], e["id"]), reverse=True)
    return found


def page(found: list[dict], before: str = "", limit: int = DAYS_LIMIT) -> dict:
    """One page of `found`, starting after the entry `before`."""
    limit = max(1, min(DAYS_MAX, int(limit or DAYS_LIMIT)))
    start = 0
    if before:
        ids = [e["id"] for e in found]
        if before not in ids:
            return {"items": [], "more": False}
        start = ids.index(before) + 1
    shown = found[start:start + limit]
    return {"items": shown, "more": start + limit < len(found)}


def days(src: Sources, before: str = "", limit: int = DAYS_LIMIT, *, kept_only: bool = False,
         now: Optional[float] = None) -> dict:
    return page(entries(src, now, kept_only=kept_only), before, limit)


def mark(library: Library, ident: str, action: str, kept: bool = True) -> Optional[Item]:
    """The owner's choice about one thing it saw: keep (or un-keep), or not for me."""
    item = library.get(ident)
    if item is None:
        return None
    if action == "keep":
        return library.change(ident, state=KEPT if kept else "")
    if action == "dismiss":
        return library.change(ident, state=DISMISSED)
    if action == "told":
        return library.change(ident, told=True)
    return None


# -------------------------------------------------------------------- cards --

def _https_player(url: str) -> str:
    try:
        parts = urlsplit(url)
    except ValueError:
        return ""
    return url if parts.scheme == "https" and parts.hostname in PLAYER_HOSTS else ""


def _web(url: str) -> str:
    try:
        return url if urlsplit(url).scheme in ("http", "https") else ""
    except ValueError:
        return ""


def clean_card(card) -> Optional[dict]:
    """A card a chat message may carry, with only what the page may draw:
    a player only from a listed host, a picture only from the library."""
    if not isinstance(card, dict):
        return None
    url = _web(str(card.get("url") or "")[:2000])
    if not url:
        return None
    length = card.get("length")
    picture = str(card.get("picture") or "")
    return {"kind": card.get("kind") if card.get("kind") in KINDS else "page",
            "title": _clip(card.get("title"), 300), "site": _clip(card.get("site"), 80),
            "author": _clip(card.get("author"), 120),
            "length": int(length) if isinstance(length, (int, float)) and not isinstance(length, bool)
            and 0 <= length < 10 ** 7 else None,
            "picture": picture if _PICTURE.fullmatch(picture) else "",
            "embed": _https_player(str(card.get("embed") or "")[:2000]), "url": url,
            "excerpt": _clip(card.get("excerpt"), 400), "readable": card.get("readable") is True}


def said(item: Item) -> dict:
    """The page chat message that brings one thing it saw to the owner."""
    card = clean_card(item.card())
    return {"role": "assistant", "text": item.why or item.title or item.url, **({"card": card} if card else {})}
