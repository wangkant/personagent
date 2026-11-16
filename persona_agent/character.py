"""`personagent character`: import a character card, save the character as
one, or draft a persona, without the page."""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from dotenv import dotenv_values

from . import charcard, drafting, langs
from . import home as homes
from .settings import content_lang
from .views import data_file_status


def _values(home: Path) -> dict:
    return {k: str(v or "") for k, v in dotenv_values(home / ".env").items()}


def _import(args, home: Path) -> int:
    path = Path(args.file).expanduser()
    try:
        if path.stat().st_size > charcard.MAX_FILE:
            raise charcard.CardError("card_too_large")
        card = charcard.read(path.read_bytes())
    except OSError:
        print(langs.term(f"The card file {path} cannot be opened."), file=sys.stderr)
        return 2
    except charcard.CardError as error:
        print(langs.term(REFUSALS.get(str(error), REFUSALS["card_unknown"])), file=sys.stderr)
        return 2
    values = _values(home)
    lang = langs.normalize(values.get("AGENT_LANG")) or "en"
    admin = values.get("ADMIN_NAME", "")
    name = card.name[:charcard.NAME_LIMIT]
    parts = [p.strip() for p in args.only.split(",")] if args.only else list(charcard.PARTS)
    unknown = [p for p in parts if p not in charcard.PARTS]
    if unknown:
        print(langs.term(f"Unknown part: {', '.join(unknown)}. The parts are {', '.join(charcard.PARTS)}."),
              file=sys.stderr)
        return 2
    persona = charcard.compose(card, name=name, lang=lang, admin_name=admin)
    rows, _left = charcard.examples(card, name=name, lang=lang, admin_name=admin)
    entries, skipped, _partly = charcard.lorebook(card)
    old = (values.get("PERSONA_NAME") or "").strip()
    print(langs.term(f"Character card: {name}"))
    print(langs.term(f"Persona: {len(persona)} characters. Every reply sends the whole persona to the model."))
    print(langs.term(f"Example dialogues: {len(rows)}. They replace the example dialogues in use as a whole."))
    print(langs.term(f"Lorebook entries: {len(entries)}, {sum(skipped.values())} skipped. "
                     "They replace the lorebook in use as a whole."))
    print(langs.term("Picture: taken from the card." if card.picture else "Picture: none in the card."))
    if card.first_mes:
        print(langs.term("The card's greeting is not used: the character opens conversations in its own way."))
    if "name" in parts and old and old != name:
        print(langs.term(f"What the character learned as {old} is kept, but applies only under that name."))
    if "persona" in parts:
        print("\n" + persona + "\n")
    if not args.yes:
        if not langs.interactive():
            print(langs.term("Nothing was changed. Add --yes to use this character without a question."),
                  file=sys.stderr)
            return 2
        answer = input(langs.term("Use this character? [y/N] ")).strip().lower()
        if answer not in ("y", "yes", "是", "j", "ja", "s", "sí", "si", "o", "oui", "д", "да"):
            print(langs.term("Nothing was changed."))
            return 1
    try:
        if "persona" in parts and len(persona) > charcard.PERSONA_LIMIT:
            raise charcard.CardError("card_persona")
        done = charcard.apply(home, card, parts, name=name, persona=persona, values=values)
    except charcard.CardError as error:
        print(langs.term(REFUSALS.get(str(error), REFUSALS["card_unknown"])), file=sys.stderr)
        return 2
    print(langs.term(f"Imported: {', '.join(done['done']) or '-'}."))
    for kept in done["backups"]:
        print(langs.term(f"The previous file was kept as {kept}."))
    print(langs.term("Restart personagent for the character to use it."))
    return 0


def _export(args, home: Path) -> int:
    path = Path(args.file).expanduser()
    kind = path.suffix.lower().lstrip(".")
    if kind not in ("png", "json"):
        print(langs.term("The file name must end in .png or .json."), file=sys.stderr)
        return 2
    values = _values(home)
    data = (charcard.png_card if kind == "png" else charcard.json_card)(home, values)
    try:
        with open(path, "xb") as out:
            out.write(data)
    except FileExistsError:
        print(langs.term(f"{path} already exists. Choose another name."), file=sys.stderr)
        return 2
    except OSError:
        print(langs.term(f"The card cannot be written to {path}."), file=sys.stderr)
        return 2
    lang = content_lang(langs.normalize(values.get("AGENT_LANG")) or "en")
    print(langs.term(f"Saved the character card to {path}."))
    if not data_file_status(home, lang, "examples")["own"]:
        print(langs.term("The built-in example dialogues are not in the card; only a file of your own would be."))
    if not data_file_status(home, lang, "lorebook")["own"]:
        print(langs.term("The built-in lorebook is not in the card; only a file of your own would be."))
    return 0


def _draft(args, home: Path) -> int:
    try:
        text = asyncio.run(drafting.draft(home, _values(home), " ".join(args.text)))
    except ValueError as error:
        print(langs.term(REFUSALS.get(str(error), REFUSALS["model_unreachable"])), file=sys.stderr)
        return 2
    print(text)
    print(langs.term("\nNot saved. Put it in persona.txt or the page's Persona box to use it."), file=sys.stderr)
    return 0


REFUSALS = {
    "card_too_large": "The file is larger than 16 MB, or a part inside it is too large.",
    "card_unknown": "The file is not a character card: a PNG or JSON card, or a CHARX file.",
    "card_broken": "The file is damaged or cannot be read as a character card.",
    "card_no_data": "The picture holds no character card.",
    "card_unsafe": "The file is built in a way that is not safe to open, so it was not read.",
    "card_no_name": "The card has no name for the character.",
    "card_name": "The name must have 1 to 64 characters.",
    "card_persona": "The persona is longer than 16,000 characters. Shorten it on the page and import again.",
    "card_nothing": "Choose at least one part to import.",
    "draft_idea": "Describe the character in one to 500 characters.",
    "draft_empty": "The model returned no text. Try again, or describe the character differently.",
    "key_required": "No model is set up. Run `personagent init` first.",
    "key_rejected": "The model service did not accept the key. Check LLM_API_KEY.",
    "model_limited": "The model service reports too many requests or an exhausted quota. Try again later.",
    "model_unreachable": "The model could not be reached. Check the network, the model name and the API address.",
}


def main(argv: list[str], prog: str) -> int:
    parser = argparse.ArgumentParser(prog=prog, description=langs.term(
        "Import a character card, save the character as one, or draft a persona"))
    sub = parser.add_subparsers(dest="action", required=True)
    one = sub.add_parser("import", help=langs.term("use a PNG, JSON or CHARX character card"))
    one.add_argument("file")
    one.add_argument("--only", metavar="PARTS",
                     help=langs.term("comma-separated parts to take: name, persona, examples, lorebook, picture"))
    one.add_argument("--yes", action="store_true", help=langs.term("use it without asking"))
    out = sub.add_parser("export", help=langs.term("save the character as a card; .png or .json"))
    out.add_argument("file")
    draft = sub.add_parser("draft", help=langs.term("print a persona drafted from a description; nothing is saved"))
    draft.add_argument("text", nargs="+")
    args = parser.parse_args(argv)
    home = homes.find_home()
    return {"import": _import, "export": _export, "draft": _draft}[args.action](args, home)
