"""The tuning panel: who the character listens to, when and how much it
talks, backup models, learning, and the remaining user-facing settings."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
import json
import math
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import Request

from .. import access, channels, langs
from .. import setup_wizard as sw
from ..config_env import TZ_OFFSET_RANGE, parse_tz_offset
from ..storage import atomic_write_text

# Reply length bounds and charsets, as textproc.ReplyStyle clamps them.
MIN_REPLY_CHARS, MAX_REPLY_CHARS = 50, 800
CHARSETS = ("ellipsis", "music", "arrows")
SECTIONS = ("who", "talk", "models", "learning", "memory", "more")
DAY = 86_400
_TRUE, _FALSE = ("1", "true", "yes", "on"), ("0", "false", "no", "off")


@dataclass(frozen=True)
class Field:
    key: str
    section: str
    kind: str  # text, ids, model, url, secret, int, float, bool, choice, tz
    default: object = ""
    low: float | None = None
    high: float | None = None
    options: tuple = ()
    # Read again on every call, so no restart is needed.
    live: bool = False


# Bounds follow settings.py / promotion.py floors; the ceilings only refuse nonsense.
FIELDS: tuple[Field, ...] = (
    Field("ADMIN_NAME", "who", "text", "", high=64),
    Field("ADMIN_RELATIONSHIP", "who", "text", "", high=64),
    Field("ADMIN_IDS", "who", "ids"),
    Field("ACCESS_GROUPS", "who", "ids"),
    Field("ACCESS_DM_USERS", "who", "ids"),
    Field("PERSONA_TZ_OFFSET_HOURS", "talk", "tz"),
    Field("CHAT_TRIGGER_COUNT", "talk", "int", 30, 1, 10_000),
    Field("LLM_FALLBACK_MODEL", "models", "model"),
    Field("LLM_FALLBACK_BASE_URL", "models", "url"),
    Field("LLM_FALLBACK_API_KEY", "models", "secret"),
    Field("LLM_JUDGE_MODEL", "models", "model"),
    Field("LLM_DM_MODEL", "models", "model"),
    Field("REACT_LEARN_ENABLED", "learning", "bool", True),
    Field("REACT_ELICIT_ENABLED", "learning", "bool", True),
    Field("PROMOTE_AUTO_ENABLED", "learning", "bool", True),
    Field("PROMOTE_MIN_SPEAKERS", "learning", "choice", "1", options=("1", "2")),
    Field("PROMOTE_JUDGE_ENABLED", "learning", "bool", True),
    Field("PROMOTE_OBSERVE_MAX_DAYS", "learning", "float", 30, 0, 3650),
    # MEMORY_TIDY_EVERY and CHAT_CONTEXT_MESSAGES kept their names with a new meaning.
    Field("MEMORY_CALLS_PER_DAY", "memory", "int", 40, 0, 10_000),
    Field("MEMORY_TIDY_EVERY", "memory", "int", 8, 0, 10_000),
    Field("CHAT_CONTEXT_MESSAGES", "memory", "int", 120, 10, 10_000),
    Field("MEMORY_PROMPT_CHARS", "memory", "int", 2400, 200, 100_000),
    Field("MEMORY_EPISODES_MAX", "memory", "int", 120, 1, 10_000),
    Field("MEMORY_KEEP_RECENT", "memory", "bool", True),
    Field("AGENT_ENABLED", "more", "bool", True),
    Field("DASHBOARD_ENABLED", "more", "bool", True),
    Field("UPDATE_CHECK_ENABLED", "more", "bool", True, live=True),
    Field("PROACTIVE_INTERVAL_S", "more", "int", 1500, 60, DAY),
    Field("PROACTIVE_MIN_SILENCE_S", "more", "int", 2700, 0, 30 * DAY),
    Field("PROACTIVE_COOLDOWN_S", "more", "int", 10800, 0, 30 * DAY),
    Field("PROACTIVE_PROB", "more", "float", 0.25, 0, 1),
    Field("PROACTIVE_DM_MIN_SILENCE_S", "more", "int", 14400, 0, 30 * DAY),
    Field("PROACTIVE_DM_COOLDOWN_S", "more", "int", 86400, 0, 30 * DAY),
    Field("PROACTIVE_DM_PROB", "more", "float", 0.2, 0, 1),
    Field("CHAT_FOLLOWUP_WINDOW_S", "more", "int", 120, 0, DAY),
    Field("REACT_TTL_S", "more", "float", 900, 0, 7 * DAY),
    Field("REACT_MAX_PENDING", "more", "int", 4, 1, 100),
    Field("REACT_MODEL", "more", "model"),
    Field("REACT_FIX_WINDOW_S", "more", "float", 600, 0, 7 * DAY),
    Field("REACT_ELICIT_DELAY_S", "more", "float", 120, 0, DAY),
    Field("REACT_ELICIT_COOLDOWN_S", "more", "float", 3600, 0, 30 * DAY),
    Field("PROMOTE_MIN_EVENTS", "more", "int", 2, 2, 100),
    Field("PROMOTE_MIN_STRONG", "more", "int", 1, 1, 100),
    Field("PROMOTE_EVIDENCE_MAX_AGE_DAYS", "more", "float", 30, 0, 3650),
    Field("PROMOTE_REQUIRE_SAME_CONVERSATION", "more", "bool", True),
    Field("PROMOTE_MAX_EXAMPLES", "more", "int", 500, 0, 100_000),
    Field("PROMOTE_MAX_FEEDBACK", "more", "int", 500, 0, 100_000),
    Field("PROMOTE_JUDGE_MODEL", "more", "model"),
    Field("PROMOTE_JUDGE_INTERVAL_S", "more", "float", 900, 60, DAY),
    Field("PROMOTE_JUDGE_BATCH", "more", "int", 5, 1, 100),
    Field("PERSONA_VERSION", "more", "text", "", high=64),
)
BY_KEY = {f.key: f for f in FIELDS}
SECRETS = frozenset(f.key for f in FIELDS if f.kind == "secret")

ERRORS: frozenset[str] = frozenset(
    {f"tuning_invalid:{f.key}" for f in FIELDS}
    | {"tuning_invalid:card", "tuning_unknown", "tuning_key_needed", "tuning_https",
       "tuning_fallback_rejected", "tuning_fallback_limited", "tuning_fallback_unreachable",
       "tuning_card_broken", "tuning_card_outside", "tuning_not_configured"})


def _bad(key: str) -> ValueError:
    return ValueError(f"tuning_invalid:{key}")


def _flag(raw: str, default: bool) -> bool:
    text = str(raw or "").strip().lower()
    return True if text in _TRUE else False if text in _FALSE else default


def _plain(key: str, value, limit: int) -> str:
    """One line of text dotenv reads back unchanged."""
    text = str(value if value is not None else "").strip()
    if (len(text) > limit or "${" in text
            or any(not c.isprintable() for c in text)):
        raise _bad(key)
    return text


def _number(field: Field, value) -> str:
    text = str(value if value is not None else "").strip()
    if not text:
        return ""
    try:
        number = int(text) if field.kind == "int" else float(text)
    except ValueError:
        raise _bad(field.key) from None
    if (isinstance(number, float) and not math.isfinite(number)
            or field.low is not None and number < field.low
            or field.high is not None and number > field.high):
        raise _bad(field.key)
    return text


def _ids(key: str, value, natives) -> str:
    entries = access.split_ids(str(value or "").replace("，", ","))
    if len(entries) > 500 or any(
            len(e) > 160 or access.is_malformed(e) or "${" in e
            or any(c.isspace() or not c.isprintable() or c in "#'\"" for c in e) for e in entries):
        raise _bad(key)
    return ",".join(access.canonical_ids(entries, native_platforms=natives))


def _url(key: str, value) -> str:
    base = str(value or "").strip().rstrip("/")
    if not base:
        return ""
    parsed = urlsplit(base)
    if (parsed.scheme not in ("https", "http") or not parsed.hostname or parsed.username
            or parsed.password or "${" in base or len(base) > 512
            or any(c.isspace() for c in base)):
        raise _bad(key)
    if parsed.scheme == "http" and parsed.hostname not in ("127.0.0.1", "localhost", "::1"):
        raise ValueError("tuning_https")
    return base


def clean(field: Field, value, natives=()) -> str:
    """`value` as it would be written to .env, or a ValueError naming the field."""
    kind = field.kind
    if kind == "bool":
        if isinstance(value, bool):
            return "true" if value else "false"
        text = str(value or "").strip().lower()
        if text in _TRUE:
            return "true"
        if text in _FALSE:
            return "false"
        raise _bad(field.key)
    if kind in ("int", "float"):
        return _number(field, value)
    if kind == "choice":
        text = str(value or "").strip()
        if text and text not in field.options:
            raise _bad(field.key)
        return text
    if kind == "tz":
        text = str(value if value is not None else "").strip()
        if text and parse_tz_offset(text) is None:
            raise _bad(field.key)
        return text
    if kind == "ids":
        return _ids(field.key, value, natives)
    if kind == "url":
        return _url(field.key, value)
    if kind in ("model", "secret"):
        text = _plain(field.key, value, 4096 if kind == "secret" else 256)
        if any(c.isspace() for c in text):
            raise _bad(field.key)
        return text
    return _plain(field.key, value, int(field.high or 256))


def _same(field: Field, old: str, new: str) -> bool:
    """Would the agent read `old` and `new` the same?"""
    if field.kind == "bool":
        return _flag(old, bool(field.default)) == _flag(new, bool(field.default))
    if field.kind in ("int", "float", "tz") and old.strip() and new.strip():
        try:
            return float(old) == float(new)
        except ValueError:
            return False
    return old.strip() == new.strip()


def _host(url: str) -> str:
    return (urlsplit(url).hostname or "").lower() if url else ""


def _auto_tz(values: dict) -> float:
    if langs.content(langs.normalize(values.get("AGENT_LANG")) or "en") == "zh":
        return 8.0
    offset = datetime.now().astimezone().utcoffset()
    return offset.total_seconds() / 3600 if offset is not None else 0.0


class Tuning:
    def __init__(self, workspace):
        self.ws = workspace

    @property
    def home(self) -> Path:
        return self.ws.home

    def _card_path(self, values: dict) -> Path:
        name = (values.get("PERSONA_CARD_FILE") or "persona.card.json").strip()
        path = (self.home / name).resolve()
        if not path.is_relative_to(self.home):
            raise ValueError("tuning_card_outside")
        return path

    def _read_card(self, values: dict) -> dict:
        path = self._card_path(values)
        if not path.is_file():
            return {}
        try:
            card = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            raise ValueError("tuning_card_broken") from None
        if not isinstance(card, dict):
            raise ValueError("tuning_card_broken")
        return card

    def _card_view(self, values: dict) -> dict:
        try:
            style = self._read_card(values).get("reply_style")
            broken = ""
        except ValueError as exc:
            style, broken = None, str(exc)
        style = style if isinstance(style, dict) else {}
        limit = style.get("max_chars")
        names = style.get("charsets") if isinstance(style.get("charsets"), list) else []
        return {"emoji": style.get("emoji") is True,
                "charsets": [n for n in CHARSETS if n in names],
                "maxChars": limit if isinstance(limit, int) and not isinstance(limit, bool) else None,
                "min": MIN_REPLY_CHARS, "max": MAX_REPLY_CHARS, "broken": broken}

    def view(self) -> dict:
        values = self.ws.config()
        shown = {f.key: values.get(f.key, "") for f in FIELDS if f.kind != "secret"}
        hints = {k: sw.mask_secret(values[k]) for k in SECRETS if values.get(k)}
        return {"values": shown, "secrets": hints,
                "fields": [{"key": f.key, "section": f.section, "kind": f.kind,
                            "default": f.default, "min": f.low, "max": f.high,
                            "options": list(f.options)} for f in FIELDS],
                "card": self._card_view(values),
                "tzAuto": round(_auto_tz(values), 2),
                "tzRange": list(TZ_OFFSET_RANGE),
                "llmBaseUrl": values.get("LLM_BASE_URL", ""),
                "agentRunning": self.ws.services.running("agent")}

    def _busy(self) -> None:
        future = self.ws._future
        if future is not None and not future.done():
            raise ValueError("busy")

    def _card_update(self, values: dict, wanted) -> tuple[Path, str] | None:
        """The card file's new text, or None when the style did not change."""
        if not isinstance(wanted, dict):
            raise _bad("card")
        charsets = wanted.get("charsets") or []
        limit = wanted.get("maxChars")
        if (not isinstance(charsets, list) or any(c not in CHARSETS for c in charsets)
                or not isinstance(wanted.get("emoji", False), bool)):
            raise _bad("card")
        if limit in ("", None):
            limit = None
        else:
            try:
                limit = int(str(limit).strip())
            except ValueError:
                raise _bad("card") from None
            if not MIN_REPLY_CHARS <= limit <= MAX_REPLY_CHARS:
                raise _bad("card")
        current = self._card_view(values)
        if current["broken"]:
            raise ValueError(current["broken"])
        style = {"emoji": bool(wanted.get("emoji")),
                 "charsets": [c for c in CHARSETS if c in charsets]}
        if limit is not None:
            style["max_chars"] = limit
        if (current["emoji"] == style["emoji"] and current["charsets"] == style["charsets"]
                and current["maxChars"] == limit):
            return None
        card = self._read_card(values)
        # Other keys of a hand-written card are kept.
        old = card.get("reply_style") if isinstance(card.get("reply_style"), dict) else {}
        merged = {k: v for k, v in old.items() if k not in ("emoji", "charsets", "max_chars")}
        merged.update(style)
        card["reply_style"] = merged
        return self._card_path(values), json.dumps(card, ensure_ascii=False, indent=2) + "\n"

    def _fallback(self, old: dict, changes: dict, typed_key: str) -> None:
        """Keep the backup model's key with its address and check the model answers."""
        def now(key):
            return changes.get(key, old.get(key, ""))

        base, model = now("LLM_FALLBACK_BASE_URL"), now("LLM_FALLBACK_MODEL")
        base_moved = "LLM_FALLBACK_BASE_URL" in changes
        if typed_key:
            changes["LLM_FALLBACK_API_KEY"] = typed_key
        elif base_moved:
            # A key is never forwarded to an address it was not saved for.
            changes["LLM_FALLBACK_API_KEY"] = ""
        key = now("LLM_FALLBACK_API_KEY")
        primary = old.get("LLM_BASE_URL", "")
        if base and _host(base) != _host(primary) and not key:
            raise ValueError("tuning_key_needed")
        touched = {"LLM_FALLBACK_MODEL", "LLM_FALLBACK_BASE_URL", "LLM_FALLBACK_API_KEY"} & set(changes)
        if not model or not touched:
            return
        try:
            probe = sw.probe_key(base or primary, key or old.get("LLM_API_KEY", ""), model, timeout=20)
        except Exception:
            raise ValueError("tuning_fallback_unreachable") from None
        if not probe.ok:
            # Never return an upstream body: it may echo a key.
            raise ValueError("tuning_fallback_rejected" if probe.status in (401, 403)
                             else "tuning_fallback_limited" if probe.status == 429
                             else "tuning_fallback_unreachable")

    def _persona_for_admin(self, old: dict, changes: dict) -> bool:
        """Re-render a shipped persona that names the owner; a custom one stays."""
        if not {"ADMIN_NAME", "ADMIN_RELATIONSHIP"} & set(changes):
            return False
        path = self.home / "persona.txt"
        if not path.is_file():
            return False
        text = sw._normal(path.read_text(encoding="utf-8"))
        lang = langs.normalize(old.get("AGENT_LANG")) or "en"
        name = old.get("PERSONA_NAME") or sw.DEFAULT_NAMES.get(lang, "")
        for key in sw.PERSONA_KEYS:
            was = sw.persona_text(key, name=name, lang=lang, admin_name=old.get("ADMIN_NAME", ""),
                                  admin_relationship=old.get("ADMIN_RELATIONSHIP", ""))
            if sw._normal(was) == text:
                return sw.write_persona(
                    self.home, key, name=name, lang=lang,
                    admin_name=changes.get("ADMIN_NAME", old.get("ADMIN_NAME", "")),
                    admin_relationship=changes.get("ADMIN_RELATIONSHIP", old.get("ADMIN_RELATIONSHIP", "")))
        return False

    def save(self, payload: dict) -> dict:
        values = payload.get("values") or {}
        if not isinstance(values, dict) or any(k not in BY_KEY for k in values):
            raise ValueError("tuning_unknown")
        with self.ws._lock:
            self._busy()
            old = self.ws.config()
            if not old.get("LLM_API_KEY"):
                raise ValueError("tuning_not_configured")
            natives = access.split_ids(old.get("CONNECTOR_QQ_PLATFORMS", ""))
            changes: dict[str, str] = {}
            typed_key = ""
            for key, raw in values.items():
                field = BY_KEY[key]
                new = clean(field, raw, natives)
                if field.kind == "secret":
                    typed_key = new
                elif not _same(field, old.get(key, ""), new):
                    changes[key] = new
            if typed_key == old.get("LLM_FALLBACK_API_KEY", ""):
                typed_key = ""
            if typed_key or {"LLM_FALLBACK_MODEL", "LLM_FALLBACK_BASE_URL"} & set(changes):
                self._fallback(old, changes, typed_key)
            card = self._card_update(old, payload["card"]) if "card" in payload else None
            if not changes and card is None:
                return {**self.view(), "changed": False, "restarted": False, "personaUpdated": False}
            if changes:
                sw.write_env(self.ws.env, changes)
            if card is not None:
                atomic_write_text(*card)
            persona = self._persona_for_admin(old, changes)
            return self._applied(changes, card is not None, persona)

    def _applied(self, changes: dict, card: bool, persona: bool) -> dict:
        restart = card or persona or any(not BY_KEY[k].live for k in changes)
        running = self.ws.services.running("agent")
        if restart:
            self.ws._restart_agent()
        return {**self.view(), "changed": True, "restarted": bool(restart and running),
                "personaUpdated": persona}

    def fresh(self) -> dict:
        """A new PERSONA_VERSION: learning starts over; the old label brings it back."""
        with self.ws._lock:
            self._busy()
            old = self.ws.config()
            if not old.get("LLM_API_KEY"):
                raise ValueError("tuning_not_configured")
            previous = old.get("PERSONA_VERSION", "").strip()
            label = "fresh-" + datetime.now().strftime("%Y%m%d-%H%M%S")
            if label == previous:
                label += "-2"
            sw.write_env(self.ws.env, {"PERSONA_VERSION": label})
            result = self._applied({"PERSONA_VERSION": label}, False, False)
            return {**result, "previous": previous}

    async def people(self) -> dict:
        """Who and which groups it has seen lately, as ids the settings take."""
        seen = await self.ws.activity()
        people, groups = [], []
        for chat in seen.get("chats", []):
            key, platform = chat.get("id", ""), chat.get("platform", "")
            if platform == "browser" or not key:
                continue
            item = {"platform": platform, "last": chat.get("last", 0)}
            if chat.get("kind") == "dm":
                user = channels.dm_user(key)
                if user:
                    people.append({**item, "id": user})
            else:
                groups.append({**item, "id": key})
        return {"running": seen.get("running", False), "off": seen.get("off", False),
                "people": people[:60], "groups": groups[:60]}


def mount(app, workspace, body) -> None:
    tuning = Tuning(workspace)

    @app.get("/api/tuning")
    async def tuning_view():
        return await asyncio.to_thread(tuning.view)

    @app.post("/api/tuning")
    async def tuning_save(request: Request):
        return await asyncio.to_thread(tuning.save, await body(request))

    @app.post("/api/tuning/fresh")
    async def tuning_fresh(request: Request):
        await body(request)
        return await asyncio.to_thread(tuning.fresh)

    @app.get("/api/tuning/people")
    async def tuning_people():
        return await tuning.people()
