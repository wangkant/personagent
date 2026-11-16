"""The character card panel: a Tavern character card brought in after a
preview, the character saved as one, and a persona drafted from one sentence."""
from __future__ import annotations

import asyncio
import base64
import secrets
from pathlib import Path

from fastapi import HTTPException, Request

from .. import charcard, drafting, langs
from .. import setup_wizard as sw
from ..settings import content_lang
from ..views import data_file_status
from .desk import _known_folder

ERRORS: frozenset[str] = charcard.ERRORS | drafting.ERRORS | frozenset(
    {"card_invalid_place", "card_save_failed"})
# Where a saved card goes; nothing from a request is ever a path.
TARGETS = ("desktop", "documents")
PICTURE_TYPES = {b"\x89PNG": "image/png", b"\xff\xd8\xff": "image/jpeg"}


class Cards:
    def __init__(self, workspace):
        self.ws = workspace
        # The one card being previewed: read once, applied by its id.
        self._pending: tuple[str, charcard.Card] | None = None

    @property
    def home(self) -> Path:
        return self.ws.home

    def _busy(self) -> None:
        future = self.ws._future
        if future is not None and not future.done():
            raise ValueError("busy")

    def overview(self) -> dict:
        targets = [{"id": name, "path": str(path)} for name in TARGETS
                   if (path := _known_folder(name)) is not None]
        return {"targets": targets, "personaLimit": charcard.PERSONA_LIMIT,
                "fileLimit": charcard.MAX_FILE, "ideaLimit": drafting.MAX_IDEA}

    def read(self, data: bytes) -> dict:
        card = charcard.read(data)
        values = self.ws.config()
        lang = langs.normalize(values.get("AGENT_LANG")) or "en"
        admin = values.get("ADMIN_NAME", "")
        name = card.name[:charcard.NAME_LIMIT]
        persona = charcard.compose(card, name=name, lang=lang, admin_name=admin)
        rows, left = charcard.examples(card, name=name, lang=lang, admin_name=admin)
        entries, skipped, partly = charcard.lorebook(card)
        content = content_lang(lang)
        examples_now = data_file_status(self.home, content, "examples")
        lore_now = data_file_status(self.home, content, "lorebook")
        current = self.ws.persona()["text"] if (self.home / "persona.txt").is_file() else ""
        mime = next((m for magic, m in PICTURE_TYPES.items() if (card.picture or b"").startswith(magic)), "")
        token = secrets.token_hex(8)
        self._pending = (token, card)
        old_name = (values.get("PERSONA_NAME") or "").strip()
        return {
            "id": token, "spec": card.spec, "name": name, "nameCut": len(card.name) > charcard.NAME_LIMIT,
            "nickname": card.nickname, "oldName": old_name,
            "persona": persona, "personaChars": len(persona), "personaLimit": charcard.PERSONA_LIMIT,
            "personaOwn": bool(current.strip()) and sw.shipped_persona(current) is None,
            "fromPersonagent": card.personagent is not None,
            "instructions": bool(card.system_prompt or card.post_history_instructions),
            "macros": charcard.left_macros(persona, *(r["reply"] for r in rows)),
            "examples": len(rows), "examplesLeft": left,
            "examplesPath": str(charcard.data_path(self.home, "examples", lang)),
            "examplesOwn": bool(examples_now["own"]),
            "lore": len(entries), "loreSkipped": skipped, "lorePartly": partly,
            "lorePath": str(charcard.data_path(self.home, "lorebook", lang)), "loreOwn": bool(lore_now["own"]),
            "picture": f"data:{mime};base64," + base64.b64encode(card.picture).decode() if mime else None,
            "pictureNote": card.picture_note,
            "greeting": card.first_mes, "alternates": len(card.alternate_greetings),
            "creatorNotes": card.creator_notes[:4000], "creator": card.creator[:200],
        }

    def cancel(self) -> dict:
        self._pending = None
        return {"ok": True}

    def apply(self, payload: dict) -> dict:
        pending = self._pending
        if pending is None or payload.get("id") != pending[0]:
            raise ValueError("card_expired")
        parts = payload.get("parts")
        if not isinstance(parts, list):
            raise ValueError("card_nothing")
        with self.ws._lock:
            self._busy()
            result = charcard.apply(self.home, pending[1], [str(p) for p in parts],
                                    name=str(payload.get("name") or ""),
                                    persona=str(payload.get("persona") or ""), values=self.ws.config())
            self._pending = None
            running = self.ws.services.running("agent")
            # The character reads its name, persona and data files only as it starts.
            self.ws._restart_agent()
            return {**result, "restarted": running, "state": self.ws.summary()}

    def export(self, payload: dict) -> dict:
        where, kind = str(payload.get("to") or ""), str(payload.get("format") or "")
        folder = _known_folder(where) if where in TARGETS else None
        if folder is None or kind not in ("png", "json"):
            raise ValueError("card_invalid_place")
        values = self.ws.config()
        data = (charcard.png_card if kind == "png" else charcard.json_card)(self.home, values)
        stem = charcard.file_stem((values.get("PERSONA_NAME") or "").strip() or "character")
        path, n = folder / f"{stem}.card.{kind}", 1
        while path.exists():
            n += 1
            path = folder / f"{stem}.card-{n}.{kind}"
        try:
            folder.mkdir(parents=True, exist_ok=True)
            with open(path, "xb") as out:
                out.write(data)
        except OSError:
            raise ValueError("card_save_failed") from None
        return {"path": str(path), "name": path.name, "size": len(data)}

    async def draft(self, payload: dict) -> dict:
        text = await drafting.draft(self.home, self.ws.config(), str(payload.get("idea") or ""))
        return {"text": text, "chars": len(text)}


async def _raw(request: Request, limit: int) -> bytes:
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > limit:
        raise ValueError("card_too_large")
    raw = bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw) > limit:
            raise ValueError("card_too_large")
    return bytes(raw)


def mount(app, workspace, body) -> None:
    cards = Cards(workspace)

    @app.get("/api/cards")
    async def cards_overview():
        return await asyncio.to_thread(cards.overview)

    @app.post("/api/cards/read")
    async def cards_read(request: Request):
        data = await _raw(request, charcard.MAX_FILE)
        if not data:
            raise HTTPException(400, "invalid_json")
        return await asyncio.to_thread(cards.read, data)

    @app.post("/api/cards/cancel")
    async def cards_cancel(request: Request):
        await body(request)
        return cards.cancel()

    @app.post("/api/cards/apply")
    async def cards_apply(request: Request):
        payload = await body(request, charcard.PERSONA_LIMIT * 4 + 4096)
        return await asyncio.to_thread(cards.apply, payload)

    @app.post("/api/cards/export")
    async def cards_export(request: Request):
        return await asyncio.to_thread(cards.export, await body(request))

    @app.post("/api/cards/draft")
    async def cards_draft(request: Request):
        return await cards.draft(await body(request))
