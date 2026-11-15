"""The lorebook panel: the background notes the character uses, edited and
imported on the page, and where its word filters and example dialogues come from."""
from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
from pathlib import Path

from fastapi import HTTPException, Request

from ..settings import content_lang
from ..storage import atomic_write_text
from ..views import DATA_FILES, data_file_status, parse_lorebook

# The loader has no limits of its own; these keep one file and one prompt sane.
MAX_ENTRIES = 200
MAX_KEYWORDS = 200
MAX_KEYWORD = 100
MAX_CONTENT = 4000
MAX_NAME = 80
PRIORITY_RANGE = (-9999, 9999)
DEFAULT_PRIORITY = 100
# A whole lorebook or an imported file is larger than the page's usual request.
MAX_REQUEST = 1_000_000
FIELDS = ("keywords", "content", "name", "priority")
_SPLIT = re.compile(r"[,，、\n]")

ERRORS: frozenset[str] = frozenset(
    {f"lore_invalid:{i}:{field}" for i in range(MAX_ENTRIES) for field in FIELDS}
    | {"lore_too_many", "lore_unknown", "lore_changed", "lore_import_unknown",
       "lore_import_empty"})


def _bad(index: int, field: str) -> ValueError:
    return ValueError(f"lore_invalid:{index}:{field}")


def _keywords(raw) -> list[str] | None:
    if isinstance(raw, str):
        raw = _SPLIT.split(raw)
    if not isinstance(raw, list):
        return None
    seen: list[str] = []
    for item in raw:
        if isinstance(item, (dict, list)) or item is None:
            return None
        word = " ".join(str(item).split())
        if word and word.lower() not in (s.lower() for s in seen):
            seen.append(word)
    return seen


def clean_entry(raw, index: int) -> dict:
    """One entry as it is written to the file, or a ValueError naming the field."""
    if not isinstance(raw, dict):
        raise _bad(index, "content")
    keywords = _keywords(raw.get("keywords"))
    if (not keywords or len(keywords) > MAX_KEYWORDS
            or any(len(k) > MAX_KEYWORD for k in keywords)):
        raise _bad(index, "keywords")
    content = str(raw.get("content") or "").replace("\r\n", "\n").strip()
    if not content or len(content) > MAX_CONTENT:
        raise _bad(index, "content")
    name = " ".join(str(raw.get("name") or "").split())
    if len(name) > MAX_NAME:
        raise _bad(index, "name")
    priority = raw.get("priority", DEFAULT_PRIORITY)
    if priority in ("", None):
        priority = DEFAULT_PRIORITY
    if isinstance(priority, bool):
        raise _bad(index, "priority")
    try:
        priority = int(str(priority).strip())
    except ValueError:
        raise _bad(index, "priority") from None
    if not PRIORITY_RANGE[0] <= priority <= PRIORITY_RANGE[1]:
        raise _bad(index, "priority")
    # The prompt shows the name; the loader's "?" says nothing.
    return {"name": name or keywords[0][:MAX_NAME], "keywords": keywords,
            "content": content, "priority": priority}


def _int_or(value, default: int) -> int:
    try:
        number = int(value) if not isinstance(value, bool) else default
    except (TypeError, ValueError):
        return default
    return max(PRIORITY_RANGE[0], min(PRIORITY_RANGE[1], number))


def convert(data) -> tuple[list[dict], int]:
    """(entries, skipped) from personagent's own lorebook or a SillyTavern World
    Info export; disabled entries and those without keywords or text are skipped."""
    if isinstance(data, dict) and isinstance(data.get("data"), dict) \
            and isinstance(data["data"].get("character_book"), dict):
        data = data["data"]["character_book"]  # a character card with its book inside
    if isinstance(data, list):
        raw = data
    elif isinstance(data, dict) and isinstance(data.get("entries"), (list, dict)):
        raw = data["entries"]
        raw = list(raw.values()) if isinstance(raw, dict) else raw
    else:
        raise ValueError("lore_import_unknown")
    entries, skipped = [], 0
    for item in raw:
        if not isinstance(item, dict) or item.get("disable") is True or item.get("enabled") is False:
            skipped += 1
            continue
        if "keywords" in item:
            shaped = item
        else:
            order = next((item[k] for k in ("order", "insertion_order", "priority") if k in item),
                         DEFAULT_PRIORITY)
            shaped = {"keywords": item.get("key", item.get("keys")),
                      "content": item.get("content"),
                      "name": item.get("comment") or item.get("name") or "",
                      "priority": _int_or(order, DEFAULT_PRIORITY)}
        try:
            entry = clean_entry(shaped, len(entries))
        except ValueError:
            skipped += 1
            continue
        if any(e["keywords"] == entry["keywords"] and e["content"] == entry["content"] for e in entries):
            skipped += 1
            continue
        entries.append(entry)
    return entries, skipped


def _stamp(path: Path) -> str:
    try:
        st = path.stat()
    except OSError:
        return "absent"
    return f"{st.st_mtime_ns}:{st.st_size}"


class Lore:
    def __init__(self, workspace):
        self.ws = workspace

    @property
    def home(self) -> Path:
        return self.ws.home

    def _lang(self) -> str:
        return content_lang(self.ws.config().get("AGENT_LANG"))

    def _editable(self, path: Path) -> tuple[dict, list[dict]]:
        """The file's other top-level keys and the entries the loader uses, in file order."""
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        parse_lorebook(data)  # raises on a shape the agent cannot read
        raw = data.get("entries", []) if isinstance(data, dict) else data
        rest = {k: v for k, v in data.items() if k != "entries"} if isinstance(data, dict) else {}
        entries = []
        for item in raw:
            if not item.get("keywords") or not item.get("content"):
                continue
            kws = item["keywords"]
            entries.append({"name": str(item.get("name") or ""),
                            "keywords": [str(k) for k in kws] if isinstance(kws, list) else [str(kws)],
                            "content": str(item["content"]),
                            "priority": int(item.get("priority", DEFAULT_PRIORITY))})
        return rest, entries

    def view(self) -> dict:
        lang = self._lang()
        lore = data_file_status(self.home, lang, "lorebook")
        path = Path(lore["path"])
        entries: list[dict] = []
        if not lore["error"]:
            try:
                entries = self._editable(path)[1]
            except Exception:
                lore["error"] = {"reason": "shape"}
        stem, ext = DATA_FILES["lorebook"]
        target = path if lore["own"] else self.home / "data" / f"{stem}.{lang}.{ext}"
        return {"lang": lang, "own": lore["own"], "path": str(path),
                "file": str(target), "error": lore["error"], "skipped": lore["skipped"],
                "entries": entries, "stamp": _stamp(path) + (":own" if lore["own"] else ":builtin"),
                "filters": data_file_status(self.home, lang, "filters"),
                "examples": data_file_status(self.home, lang, "examples"),
                "limits": {"entries": MAX_ENTRIES, "keywords": MAX_KEYWORDS, "keyword": MAX_KEYWORD,
                           "content": MAX_CONTENT, "name": MAX_NAME, "priority": list(PRIORITY_RANGE)},
                "agentRunning": self.ws.services.running("agent")}

    def _busy(self) -> None:
        future = self.ws._future
        if future is not None and not future.done():
            raise ValueError("busy")

    def _applied(self) -> dict:
        running = self.ws.services.running("agent")
        # The agent finds its lorebook file as it starts.
        self.ws._restart_agent()
        return {**self.view(), "changed": True, "restarted": running}

    def save(self, payload: dict) -> dict:
        wanted = payload.get("entries")
        if not isinstance(wanted, list):
            raise ValueError("lore_unknown")
        if len(wanted) > MAX_ENTRIES:
            raise ValueError("lore_too_many")
        entries = [clean_entry(raw, i) for i, raw in enumerate(wanted)]
        with self.ws._lock:
            self._busy()
            current = self.view()
            if payload.get("stamp") != current["stamp"]:
                raise ValueError("lore_changed")
            source, target = Path(current["path"]), Path(current["file"])
            try:
                rest = self._editable(source)[0]
            except Exception:
                rest = {}
            if target.exists():
                shutil.copy2(target, target.with_name(target.name + ".bak"))
            atomic_write_text(target, json.dumps({**rest, "entries": entries},
                                                 ensure_ascii=False, indent=2) + "\n")
            return self._applied()

    def reset(self, payload: dict) -> dict:
        """Back to the built-in set: the home's file becomes a .bak beside it."""
        with self.ws._lock:
            self._busy()
            current = self.view()
            if payload.get("stamp") != current["stamp"]:
                raise ValueError("lore_changed")
            if not current["own"]:
                return {**current, "changed": False, "restarted": False}
            path = Path(current["path"])
            os.replace(path, path.with_name(path.name + ".bak"))
            return self._applied()

    @staticmethod
    def import_file(payload: dict) -> dict:
        """Entries converted from an uploaded file; nothing is written until saved."""
        entries, skipped = convert(payload.get("data"))
        if not entries:
            raise ValueError("lore_import_empty")
        return {"entries": entries, "skipped": skipped}


async def _read(request: Request) -> dict:
    raw = bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw) > MAX_REQUEST:
            raise HTTPException(413, "too_large")
    try:
        value = json.loads(raw or b"{}")
    except ValueError:
        raise HTTPException(400, "invalid_json") from None
    if not isinstance(value, dict):
        raise HTTPException(400, "invalid_json")
    return value


def mount(app, workspace, body) -> None:
    lore = Lore(workspace)

    @app.get("/api/lore")
    async def lore_view():
        return await asyncio.to_thread(lore.view)

    @app.post("/api/lore")
    async def lore_save(request: Request):
        return await asyncio.to_thread(lore.save, await _read(request))

    @app.post("/api/lore/reset")
    async def lore_reset(request: Request):
        return await asyncio.to_thread(lore.reset, await body(request))

    @app.post("/api/lore/import")
    async def lore_import(request: Request):
        return await asyncio.to_thread(lore.import_file, await _read(request))
