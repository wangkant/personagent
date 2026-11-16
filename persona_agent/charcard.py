"""Tavern character cards (V1, V2 and V3, as PNG, JSON or CHARX): read into
what a home keeps, and written back out of it. Card text is untrusted: every
size is bounded, nothing a card names is fetched or run."""
from __future__ import annotations

import base64
import binascii
import hashlib
import io
import json
import re
import shutil
import struct
import time
import zipfile
import zlib
from dataclasses import dataclass, field
from pathlib import Path

from . import langs
from . import setup_wizard as sw
from .settings import content_lang
from .storage import atomic_write_text, dated_copy

MAX_FILE = 16 * 1024 * 1024
MAX_JSON = 2 * 1024 * 1024
MAX_CHUNKS = 4096
MAX_ZIP_ENTRIES = 512
MAX_ZIP_TOTAL = 64 * 1024 * 1024
# Above this many times its packed size, a member counts as a zip bomb.
MAX_ZIP_RATIO = 100
MAX_ICON = 8 * 1024 * 1024
MAX_PIXELS = 40_000_000
MAX_SIDE = 12_000
PICTURE_SIDE = 1024
MAX_GREETINGS = 100
MAX_EXAMPLES = 200
MAX_EXAMPLE_TEXT = 2000
# Lines of the dialogue before a reply that an example keeps.
EXAMPLE_CONTEXT = 6
NAME_LIMIT = 64
# Characters; cards often run past 4,000, and the engine itself sets no limit.
PERSONA_LIMIT = 16_000
PARTS = ("name", "persona", "examples", "lorebook", "picture")
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

ERRORS = frozenset({"card_too_large", "card_unknown", "card_broken", "card_no_data",
                    "card_unsafe", "card_no_name", "card_expired", "card_nothing",
                    "card_name", "card_persona", "card_aliases_unreadable"})

# What {{user}} becomes when no admin name is set, in the character's language.
USER_WORDS = {"en": "the user", "zh": "用户", "zh-TW": "使用者", "ja": "ユーザー", "ko": "사용자",
              "es": "el usuario", "fr": "l'utilisateur", "de": "der Nutzer", "pt-BR": "o usuário",
              "ru": "пользователь"}
# The speaker of the other side in an example dialogue; example files are en or zh.
USER_LABELS = {"en": "user", "zh": "用户"}
SCENARIO = {"en": "example dialogue from a character card", "zh": "角色卡中的示例对话"}
LABELS = {
    "en": ("Personality", "Situation", "Instructions from the card"),
    "zh": ("性格", "情境", "角色卡中的说明"),
    "zh-TW": ("性格", "情境", "角色卡中的說明"),
    "ja": ("性格", "状況", "キャラクターカードの指示"),
    "ko": ("성격", "상황", "캐릭터 카드의 지시"),
    "es": ("Personalidad", "Situación", "Instrucciones de la tarjeta"),
    "fr": ("Personnalité", "Situation", "Instructions de la carte"),
    "de": ("Persönlichkeit", "Situation", "Anweisungen der Karte"),
    "pt-BR": ("Personalidade", "Situação", "Instruções do cartão"),
    "ru": ("Характер", "Ситуация", "Указания из карточки"),
}

_COMMENT = re.compile(r"\{\{//.*?\}\}", re.S)
_CHAR = re.compile(r"\{\{\s*char\s*\}\}|<bot>", re.I)
_USER = re.compile(r"\{\{\s*user\s*\}\}|<user>", re.I)
_EMPTY_MACRO = re.compile(r"\{\{\s*(?:original|trim|noop)\s*\}\}", re.I)
_LEFT_MACRO = re.compile(r"\{\{\s*([^{}\n]{1,40}?)\s*\}\}")
_START = re.compile(r"^\s*<start>\s*$", re.I | re.M)
_SPEAKER = re.compile(r"^\s*(\{\{\s*char\s*\}\}|\{\{\s*user\s*\}\}|<bot>|<user>)\s*:\s?(.*)$", re.I)
# Tags of the prompt's own blocks: card text may not close or open one.
_BLOCK_TAG = re.compile(r"</?\s*(persona|lorebook|examples|tools)\s*>", re.I)
_DECORATOR = re.compile(r"^\s*@@.*$\n?", re.M)


class CardError(ValueError):
    pass


@dataclass
class Card:
    spec: str
    name: str
    nickname: str = ""
    description: str = ""
    personality: str = ""
    scenario: str = ""
    system_prompt: str = ""
    post_history_instructions: str = ""
    first_mes: str = ""
    alternate_greetings: list = field(default_factory=list)
    mes_example: str = ""
    creator_notes: str = ""
    creator: str = ""
    character_book: dict | None = None
    # A card this program wrote: its persona is `description` as it stands.
    personagent: dict | None = None
    picture: bytes | None = None
    picture_note: str = ""


# ---- reading


def _text(value) -> str:
    return value.replace("\r\n", "\n").strip() if isinstance(value, str) else ""


def _decode_json(raw: bytes):
    if len(raw) > MAX_JSON:
        raise CardError("card_too_large")
    try:
        return json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, ValueError, RecursionError):
        raise CardError("card_broken") from None


def _png_chunks(data: bytes) -> dict[str, bytes]:
    """The `chara` and `ccv3` text chunks of a PNG, keywords lowercased."""
    found: dict[str, bytes] = {}
    pos, count = len(PNG_MAGIC), 0
    while pos + 8 <= len(data):
        count += 1
        if count > MAX_CHUNKS:
            raise CardError("card_unsafe")
        length, kind = struct.unpack(">I4s", data[pos:pos + 8])
        start, end = pos + 8, pos + 8 + length
        if end + 4 > len(data):
            raise CardError("card_broken")
        body = data[start:end]
        if kind == b"tEXt":
            key, _, text = body.partition(b"\0")
            name = key.decode("latin-1").lower()
            if name in ("chara", "ccv3"):
                found.setdefault(name, text)
        elif kind == b"iTXt":
            key, _, rest = body.partition(b"\0")
            name = key.decode("latin-1").lower()
            if name in ("chara", "ccv3") and len(rest) >= 2:
                packed, rest = rest[0], rest[2:]
                _lang, _, rest = rest.partition(b"\0")
                _translated, _, text = rest.partition(b"\0")
                if packed:
                    inflate = zlib.decompressobj()
                    text = inflate.decompress(text, MAX_JSON * 2)
                    if inflate.unconsumed_tail:
                        raise CardError("card_too_large")
                found.setdefault(name, text)
        elif kind == b"IEND":
            break
        pos = end + 4
    return found


def _card_json_from_png(data: bytes):
    chunks = _png_chunks(data)
    raw = chunks.get("ccv3") or chunks.get("chara")
    if raw is None:
        raise CardError("card_no_data")
    if len(raw) > MAX_JSON * 4 // 3 + 4:
        raise CardError("card_too_large")
    try:
        decoded = base64.b64decode(b"".join(raw.split()), validate=True)
    except (binascii.Error, ValueError):
        # A few writers put the JSON in as it is.
        decoded = raw
    return _decode_json(decoded)


def _safe_member(name: str) -> bool:
    parts = name.split("/")
    return not ("\\" in name or name.startswith("/") or ":" in name
                or any(p in (".", "..") for p in parts))


def _read_member(archive: zipfile.ZipFile, info: zipfile.ZipInfo, limit: int) -> bytes:
    if info.flag_bits & 0x1:
        raise CardError("card_unsafe")
    if info.file_size > limit:
        raise CardError("card_too_large")
    if info.file_size > 1024 * 1024 and info.file_size > max(1, info.compress_size) * MAX_ZIP_RATIO:
        raise CardError("card_unsafe")
    with archive.open(info) as member:
        # The header may lie about the size; what is read is bounded all the same.
        raw = member.read(limit + 1)
    if len(raw) > limit:
        raise CardError("card_too_large")
    return raw


def _read_charx(data: bytes) -> tuple[dict, bytes | None]:
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
        infos = archive.infolist()
    except (zipfile.BadZipFile, OSError, ValueError):
        raise CardError("card_broken") from None
    with archive:
        if len(infos) > MAX_ZIP_ENTRIES or sum(i.file_size for i in infos) > MAX_ZIP_TOTAL:
            raise CardError("card_unsafe")
        if any(not _safe_member(i.filename) for i in infos):
            raise CardError("card_unsafe")
        members = {i.filename: i for i in infos if not i.is_dir()}
        if "card.json" not in members:
            raise CardError("card_unknown")
        try:
            obj = _decode_json(_read_member(archive, members["card.json"], MAX_JSON))
            icon = None
            path = _icon_path(obj, members)
            if path:
                icon = _read_member(archive, members[path], MAX_ICON)
        except (zipfile.BadZipFile, OSError, EOFError, NotImplementedError, zlib.error):
            raise CardError("card_broken") from None
    return obj, icon


def _icon_path(obj, members: dict) -> str:
    """The member holding the card's main icon, as its assets name it."""
    data = obj.get("data") if isinstance(obj, dict) else None
    assets = data.get("assets") if isinstance(data, dict) else None
    icons = [a for a in assets if isinstance(a, dict) and a.get("type") == "icon"] \
        if isinstance(assets, list) else []
    icons.sort(key=lambda a: a.get("name") != "main")
    for asset in icons:
        uri = str(asset.get("uri") or "")
        # Only a file inside the archive; a web address is never fetched.
        for prefix in ("embeded://", "embedded://"):
            if uri.startswith(prefix) and uri[len(prefix):] in members:
                return uri[len(prefix):]
    for name in sorted(members):
        if name.startswith("assets/icon/") and name.rsplit(".", 1)[-1].lower() in ("png", "jpg", "jpeg", "webp"):
            return name
    return ""


def _shape(obj) -> Card:
    if not isinstance(obj, dict):
        raise CardError("card_unknown")
    spec = obj.get("spec")
    if spec in ("chara_card_v2", "chara_card_v3") and isinstance(obj.get("data"), dict):
        data, version = obj["data"], "v3" if spec == "chara_card_v3" else "v2"
    elif "name" in obj and any(k in obj for k in ("description", "personality", "first_mes", "mes_example")):
        data, version = obj, "v1"
    else:
        raise CardError("card_unknown")
    name = " ".join(_text(data.get("name")).split())
    if not name:
        raise CardError("card_no_name")
    greetings = data.get("alternate_greetings")
    extensions = data.get("extensions") if isinstance(data.get("extensions"), dict) else {}
    own = extensions.get("personagent")
    book = data.get("character_book")
    return Card(
        spec=version, name=name, nickname=" ".join(_text(data.get("nickname")).split()),
        description=_text(data.get("description")), personality=_text(data.get("personality")),
        scenario=_text(data.get("scenario")), system_prompt=_text(data.get("system_prompt")),
        post_history_instructions=_text(data.get("post_history_instructions")),
        first_mes=_text(data.get("first_mes")),
        alternate_greetings=[_text(g) for g in greetings[:MAX_GREETINGS] if _text(g)]
        if isinstance(greetings, list) else [],
        mes_example=_text(data.get("mes_example")), creator_notes=_text(data.get("creator_notes")),
        creator=_text(data.get("creator")),
        character_book=book if isinstance(book, dict) else None,
        personagent=own if isinstance(own, dict) else None)


def read(data: bytes) -> Card:
    """A card from a file's bytes; a CardError names what is wrong with it."""
    if len(data) > MAX_FILE:
        raise CardError("card_too_large")
    icon = None
    if data.startswith(PNG_MAGIC):
        obj, icon = _card_json_from_png(data), data
    elif data.startswith(b"PK\x03\x04"):
        obj, icon = _read_charx(data)
    else:
        stripped = data.lstrip(b"\xef\xbb\xbf \t\r\n")
        if not stripped.startswith(b"{"):
            raise CardError("card_unknown")
        obj = _decode_json(data)
    card = _shape(obj)
    if icon is not None:
        card.picture, card.picture_note = picture(icon)
    return card


def picture(raw: bytes) -> tuple[bytes | None, str]:
    """`raw` as a picture the page may keep: at most PICTURE_SIDE pixels a side
    and within the custom picture's limit; (None, why) when it cannot be."""
    from PIL import Image

    try:
        with Image.open(io.BytesIO(raw)) as image:
            width, height = image.size
            if width * height > MAX_PIXELS or max(width, height) > MAX_SIDE:
                return None, "picture_too_big"
            image.seek(0)
            alpha = image.mode in ("RGBA", "LA", "PA") or "transparency" in image.info
            image = image.convert("RGBA" if alpha else "RGB")
            image.thumbnail((PICTURE_SIDE, PICTURE_SIDE))
            out = io.BytesIO()
            image.save(out, format="PNG", optimize=True)
            if out.tell() > sw.MAX_OWN_AVATAR:
                out = io.BytesIO()
                image.convert("RGB").save(out, format="JPEG", quality=88)
    except Exception:
        return None, "picture_unreadable"
    data = out.getvalue()
    return (data, "") if len(data) <= sw.MAX_OWN_AVATAR else (None, "picture_too_big")


# ---- what the card becomes


def resolve(text: str, name: str, user: str) -> str:
    """Macros filled in: {{char}} and <BOT> are the name, {{user}} and <USER>
    the person; comments and {{original}} go."""
    text = _COMMENT.sub("", text)
    text = _CHAR.sub(lambda _m: name, text)
    text = _USER.sub(lambda _m: user, text)
    return _EMPTY_MACRO.sub("", text)


def left_macros(*texts: str) -> list[str]:
    return sorted({m.strip() for t in texts for m in _LEFT_MACRO.findall(t)})[:20]


def user_word(lang: str, admin_name: str = "") -> str:
    return admin_name.strip() or USER_WORDS.get(lang, USER_WORDS["en"])


def _safe(text: str) -> str:
    return _BLOCK_TAG.sub(lambda m: m.group(0).replace("<", "(").replace(">", ")"), text)


def compose(card: Card, *, name: str, lang: str, admin_name: str = "") -> str:
    """The card's character as one persona document, in the shape of the shipped ones."""
    user = user_word(lang, admin_name)

    def fill(text: str) -> str:
        return _safe(resolve(text, name, user)).strip()

    personality, situation, instructions = LABELS.get(lang, LABELS["en"])
    blocks = []
    if card.personagent is not None:
        blocks.append(fill(card.description))
    else:
        head = sw.NAME_LINE.get(lang, sw.NAME_LINE["en"]).format(name=name)
        blocks.append("\n".join(p for p in (head, fill(card.description)) if p))
    colon = "：" if lang in ("zh", "zh-TW", "ja") else ":"
    for label, text in ((personality, card.personality), (situation, card.scenario)):
        text = fill(text)
        if text:
            gap = "\n" if "\n" in text else "" if colon == "：" else " "
            blocks.append(f"{label}{colon}{gap}{text}")
    told = [fill(t) for t in (card.system_prompt, card.post_history_instructions) if fill(t)]
    if told:
        blocks.append(f"{instructions}{colon}\n" + "\n\n".join(told))
    return "\n\n".join(b for b in blocks if b).strip()


def examples(card: Card, *, name: str, lang: str, admin_name: str = "") -> tuple[list[dict], int]:
    """(example rows in the format of data/examples.<lang>.jsonl, how many were left out)."""
    user = user_word(lang, admin_name)
    label = admin_name.strip() or USER_LABELS.get(content_lang(lang), USER_LABELS["en"])
    scenario = SCENARIO.get(content_lang(lang), SCENARIO["en"])
    named = re.compile(rf"^\s*{re.escape(card.name)}\s*:\s?(.*)$") if card.name else None
    stamp = time.strftime("%Y-%m-%dT%H:%M:%S")
    rows: list[dict] = []
    left = 0
    for block in _START.split(card.mes_example):
        turns: list[list[str]] = []
        for line in block.split("\n"):
            found = _SPEAKER.match(line)
            if found:
                who = "char" if re.search(r"char|bot", found.group(1), re.I) else "user"
                said = found.group(2)
            elif named and named.match(line):
                who, said = "char", named.match(line).group(1)
            elif turns:
                turns[-1][1] += "\n" + line
                continue
            else:
                continue
            if turns and turns[-1][0] == who:
                turns[-1][1] += "\n" + said
            else:
                turns.append([who, said])
        turns = [[who, _safe(resolve(text, name, user)).strip()] for who, text in turns]
        for i, (who, text) in enumerate(turns):
            if who != "char" or not text:
                continue
            before = [f"{name if w == 'char' else label}: {t}"
                      for w, t in turns[max(0, i - EXAMPLE_CONTEXT):i] if t]
            if len(text) > MAX_EXAMPLE_TEXT or any(len(c) > MAX_EXAMPLE_TEXT for c in before):
                left += 1
                continue
            if len(rows) >= MAX_EXAMPLES:
                left += 1
                continue
            rows.append({"scenario": scenario, "context": before, "reply": text, "ts": stamp})
    return rows, left


def lorebook(card: Card) -> tuple[list[dict], dict[str, int], dict[str, int]]:
    """(entries, skipped by reason, taken only in part), through the lorebook
    panel's own World Info import."""
    from .panels import lore

    if not card.character_book:
        return [], {}, {}
    raw = card.character_book.get("entries")
    raw = list(raw.values()) if isinstance(raw, dict) else raw if isinstance(raw, list) else []
    usable, regex, decorated = [], 0, 0
    for item in raw[:5000]:
        if isinstance(item, dict) and item.get("use_regex") is True:
            # Keys are patterns here; this lorebook matches words only.
            regex += 1
            continue
        if isinstance(item, dict) and isinstance(item.get("content"), str) and _DECORATOR.search(item["content"]):
            item = {**item, "content": _DECORATOR.sub("", item["content"])}
            decorated += 1
        if isinstance(item, dict) and isinstance(item.get("content"), str):
            item = {**item, "content": _safe(item["content"])}
        usable.append(item)
    entries, skipped, partly = lore.convert({"entries": usable})
    if len(entries) > lore.MAX_ENTRIES:
        skipped["too_many"] = len(entries) - lore.MAX_ENTRIES
        entries = entries[:lore.MAX_ENTRIES]
    if regex:
        skipped["regex"] = regex
    if decorated:
        partly["decorators"] = decorated
    return (entries, {k: n for k, n in skipped.items() if n}, {k: n for k, n in partly.items() if n})


# ---- the home's files


def data_path(home: Path, kind: str, lang: str) -> Path:
    stem, ext = {"examples": ("examples", "jsonl"), "lorebook": ("lorebook", "json")}[kind]
    return home / "data" / f"{stem}.{content_lang(lang)}.{ext}"


def back_up_persona(home: Path) -> Path | None:
    """Copy a persona.txt someone wrote to persona.txt.bak and a dated copy
    before it is replaced; a shipped one needs no copy."""
    path = home / "persona.txt"
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    if not text.strip() or sw.shipped_persona(text) is not None:
        return None
    kept = path.with_name("persona.txt.bak")
    atomic_write_text(kept, text)
    # The next replacement writes persona.txt.bak again: this one stays.
    return dated_copy(kept)


def _back_up(path: Path) -> Path | None:
    if not path.is_file():
        return None
    kept = path.with_name(path.name + ".bak")
    shutil.copy2(path, kept)
    return dated_copy(kept)


def card_file(home: Path, values: dict) -> Path:
    return home / (values.get("PERSONA_CARD_FILE") or "persona.card.json").strip()


def aliases(home: Path, values: dict) -> list[str]:
    try:
        card = json.loads(card_file(home, values).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    raw = card.get("aliases") if isinstance(card, dict) else None
    return [" ".join(a.split()) for a in raw if isinstance(a, str) and a.strip()] \
        if isinstance(raw, list) else []


def _add_aliases(home: Path, values: dict, names: list[str]) -> bool:
    """Add nicknames to the persona card's `aliases`, keeping its other keys;
    False when the file exists but cannot be read, so it is left alone."""
    path = card_file(home, values)
    card: dict = {}
    if path.is_file():
        try:
            card = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return False
        if not isinstance(card, dict):
            return False
    have = card.get("aliases") if isinstance(card.get("aliases"), list) else []
    merged = list(dict.fromkeys([*have, *(n for n in names if n)]))
    if merged == have:
        return True
    card["aliases"] = merged
    atomic_write_text(path, json.dumps(card, ensure_ascii=False, indent=2) + "\n")
    return True


def check_name(name: str) -> str:
    name = " ".join(str(name or "").split())
    if not name or len(name) > NAME_LIMIT or "${" in name:
        raise CardError("card_name")
    return name


def check_persona(text: str) -> str:
    text = str(text or "").replace("\r\n", "\n").strip()
    if not text or len(text) > PERSONA_LIMIT:
        raise CardError("card_persona")
    return text


def apply(home: Path, card: Card, parts, *, name: str, persona: str, values: dict) -> dict:
    """Write the chosen parts of `card` into the home: {done, backups, notes}.
    The caller restarts a running character."""
    parts = [p for p in PARTS if p in set(parts)]
    if not parts:
        raise CardError("card_nothing")
    lang = langs.normalize(values.get("AGENT_LANG")) or "en"
    admin = values.get("ADMIN_NAME", "")
    use_name = check_name(name) if "name" in parts else (values.get("PERSONA_NAME") or card.name)
    text = check_persona(persona) if "persona" in parts else ""
    done, backups, notes = [], [], []

    def kept(path: Path | None) -> None:
        if path is not None:
            backups.append(str(path))

    sw.copy_env_template(home)
    if "name" in parts:
        sw.write_env(home / ".env", {"PERSONA_NAME": use_name})
        nick = [card.nickname] + [str(a) for a in (card.personagent or {}).get("aliases") or []
                                  if isinstance(a, str)]
        nick = [" ".join(n.split())[:NAME_LIMIT] for n in nick if n and n.strip() and n.strip() != use_name]
        if nick and not _add_aliases(home, values, nick):
            notes.append("card_aliases_unreadable")
        done.append("name")
    if "persona" in parts:
        kept(back_up_persona(home))
        atomic_write_text(home / "persona.txt", text + "\n")
        done.append("persona")
    if "examples" in parts:
        rows, _left = examples(card, name=use_name, lang=lang, admin_name=admin)
        if rows:
            path = data_path(home, "examples", lang)
            kept(_back_up(path))
            path.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_text(path, "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
            done.append("examples")
    if "lorebook" in parts:
        entries, _skipped, _partly = lorebook(card)
        if entries:
            path = data_path(home, "lorebook", lang)
            kept(_back_up(path))
            path.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_text(path, json.dumps({"entries": entries}, ensure_ascii=False, indent=2) + "\n")
            done.append("lorebook")
    if "picture" in parts and card.picture:
        sw.write_own_avatar(home, card.picture)
        sw.write_env(home / ".env", {"PERSONA_AVATAR": sw.OWN_AVATAR})
        done.append("picture")
    return {"done": done, "backups": backups, "notes": notes}


# ---- writing a card


def _own_data(home: Path, kind: str, lang: str) -> Path | None:
    path = data_path(home, kind, lang)
    return path if path.is_file() else None


def _hide(text: str, admin: str) -> str:
    # The admin's name is the owner's own: shared, it reads as {{user}}.
    admin = admin.strip()
    return text.replace(admin, "{{user}}") if len(admin) >= 2 else text


def _mes_example(path: Path | None, name: str, admin: str) -> str:
    if path is None:
        return ""
    from .paths import parse_jsonl

    blocks = []
    try:
        rows = parse_jsonl(path.read_bytes())
    except OSError:
        return ""
    for row in rows:
        reply = str(row.get("reply") or "").strip()
        if not reply:
            continue
        lines = ["<START>"]
        for line in row.get("context") or []:
            who, _, said = str(line).partition(": ")
            if not _:
                who, said = "", str(line)
            # Speakers' names stay at home: every other side is {{user}}.
            lines.append(f"{'{{char}}' if who == name else '{{user}}'}: {_hide(said.strip(), admin)}")
        lines.append("{{char}}: " + _hide(reply, admin))
        blocks.append("\n".join(lines))
    return "\n".join(blocks)


def _book(path: Path | None, name: str, admin: str, *, v3: bool) -> dict | None:
    if path is None:
        return None
    from .views import parse_lorebook

    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        parse_lorebook(data)
    except (OSError, ValueError, AttributeError, TypeError):
        return None
    raw = data.get("entries", []) if isinstance(data, dict) else data
    entries = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict) or not item.get("keywords") or not item.get("content"):
            continue
        keys = item["keywords"] if isinstance(item["keywords"], list) else [item["keywords"]]
        entry = {"keys": [str(k) for k in keys], "content": _hide(str(item["content"]), admin),
                 "extensions": {}, "enabled": True, "insertion_order": int(item.get("priority", 100)),
                 "case_sensitive": False, "name": str(item.get("name") or ""),
                 "comment": str(item.get("name") or ""), "priority": int(item.get("priority", 100)),
                 "id": i, "selective": False, "secondary_keys": [], "constant": False}
        if v3:
            entry["use_regex"] = False
        entries.append(entry)
    return {"name": name, "extensions": {}, "entries": entries} if entries else None


def export(home: Path, values: dict) -> dict:
    """The home's character as a V2 card: the persona, its own example and
    lorebook files, its name and nicknames. No key, memory or learned item."""
    lang = langs.normalize(values.get("AGENT_LANG")) or "en"
    admin = values.get("ADMIN_NAME", "")
    name = (values.get("PERSONA_NAME") or "").strip() or sw.DEFAULT_NAMES.get(lang, "Nova")
    path = home / "persona.txt"
    try:
        persona = path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError):
        persona = sw.persona_text(sw.TEMPLATE, name=name, lang=lang).strip()
    data = {"name": name, "description": _hide(persona, admin), "personality": "", "scenario": "",
            "first_mes": "", "mes_example": _mes_example(_own_data(home, "examples", lang), name, admin),
            "creator_notes": "", "system_prompt": "", "post_history_instructions": "",
            "alternate_greetings": [], "tags": [], "creator": "", "character_version": "",
            "extensions": {"personagent": {"version": 1, "lang": lang, "aliases": aliases(home, values)}}}
    book = _book(_own_data(home, "lorebook", lang), name, admin, v3=False)
    if book:
        data["character_book"] = book
    return {"spec": "chara_card_v2", "spec_version": "2.0", "data": data}


def as_v3(card: dict, home: Path, values: dict) -> dict:
    data = dict(card["data"])
    lang = langs.normalize(values.get("AGENT_LANG")) or "en"
    book = _book(_own_data(home, "lorebook", lang), data["name"], values.get("ADMIN_NAME", ""), v3=True)
    if book:
        data["character_book"] = book
    data.update(group_only_greetings=[], creation_date=int(time.time()), modification_date=int(time.time()),
                assets=[{"type": "icon", "uri": "ccdefault:", "name": "main", "ext": "png"}])
    return {"spec": "chara_card_v3", "spec_version": "3.0", "data": data}


def _portrait_frame(path: Path):
    from PIL import Image

    with Image.open(path) as sheet:
        side = sheet.height
        # Four square frames side by side; the first is the face at rest.
        return sheet.crop((0, 0, side, side)).convert("RGBA")


def card_image(home: Path, values: dict, name: str):
    """The custom picture, else the chosen portrait, else a plain square."""
    from PIL import Image

    avatar = (values.get("PERSONA_AVATAR") or "").strip()
    own = sw.own_avatar(home)
    try:
        if avatar == sw.OWN_AVATAR and own:
            with Image.open(own) as image:
                image.seek(0)
                return image.convert("RGBA")
        persona = home / "persona.txt"
        origin = sw.shipped_persona(persona.read_text(encoding="utf-8")) if persona.is_file() else None
        for key in (avatar, origin[0] if origin else ""):
            if key and sw.portrait(key):
                return _portrait_frame(sw.portrait(key))
    except (OSError, ValueError):
        pass
    shade = hashlib.sha256(name.encode("utf-8")).digest()
    return Image.new("RGB", (512, 512), (90 + shade[0] % 120, 90 + shade[1] % 120, 90 + shade[2] % 120))


def png_card(home: Path, values: dict) -> bytes:
    from PIL.PngImagePlugin import PngInfo

    card = export(home, values)
    image = card_image(home, values, card["data"]["name"])
    image.thumbnail((PICTURE_SIDE, PICTURE_SIDE))
    info = PngInfo()

    def encoded(obj) -> str:
        return base64.b64encode(json.dumps(obj, ensure_ascii=False).encode("utf-8")).decode("ascii")

    info.add_text("chara", encoded(card))
    info.add_text("ccv3", encoded(as_v3(card, home, values)))
    out = io.BytesIO()
    image.save(out, format="PNG", pnginfo=info)
    return out.getvalue()


def json_card(home: Path, values: dict) -> bytes:
    return (json.dumps(export(home, values), ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def file_stem(name: str) -> str:
    stem = re.sub(r'[\\/:*?"<>|\x00-\x1f]+', "", name).strip(" .")
    return stem[:60] or "character"
