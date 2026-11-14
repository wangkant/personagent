"""persona_agent/locales/: every language has every sentence it is asked for."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from persona_agent import langs
from tools import locale_gaps

from helpers import check

TERMINAL = Path(langs.__file__).resolve().parent / "locales" / "terminal"
#: English and Chinese sit next to the code; these read locales/<code>.json.
TRANSLATED = [code for code in langs.CODES if code not in ("en", "zh")]


@pytest.mark.parametrize("code", TRANSLATED)
def test_the_wizard_the_trial_and_the_demo_are_translated(code: str) -> None:
    missing = sorted(locale_gaps.keys() - set(langs.catalog(code)))
    check(f"locales/{code}.json has every sentence", not missing,
          f"{len(missing)} would show in English:\n" + "\n".join(missing))


def test_terminal_catalogs_share_one_key_set() -> None:
    files = sorted(TERMINAL.glob("*.json"))
    check("terminal catalogs: one per language but English",
          {path.stem for path in files} == set(langs.CODES) - {"en"},
          str([path.name for path in files]))
    catalogs = {}
    for path in files:
        try:
            catalogs[path.name] = json.loads(path.read_text(encoding="utf-8"))
        except ValueError as error:
            pytest.fail(f"locales/terminal/{path.name} does not parse: {error}")
        check(f"locales/terminal/{path.name} is an object of sentences",
              isinstance(catalogs[path.name], dict)
              and all(isinstance(there, str) and there for there in catalogs[path.name].values()))
    everything = set().union(*catalogs.values())
    for name, sentences in catalogs.items():
        missing = sorted(everything - set(sentences))
        check(f"locales/terminal/{name} has every sentence the others have", not missing,
              f"{len(missing)} missing:\n" + "\n".join(missing))


def test_the_terminal_language_follows_the_env_file(tmp_path, monkeypatch) -> None:
    """It is asked once per printed sentence and cached; a rewritten .env must
    still be read again, and so must another home."""
    monkeypatch.delenv("AGENT_LANG", raising=False)
    monkeypatch.setenv("AGENT_HOME", str(tmp_path))
    env = tmp_path / ".env"
    env.write_text("AGENT_LANG=ja", encoding="utf-8")
    check("read from the home's .env", langs.terminal_lang() == "ja", langs.terminal_lang())
    env.write_text("AGENT_LANG=de  # switched", encoding="utf-8")
    check("a rewritten file is read again", langs.terminal_lang() == "de", langs.terminal_lang())
    other = tmp_path / "other"
    other.mkdir()
    (other / ".env").write_text("AGENT_LANG=ko", encoding="utf-8")
    monkeypatch.setenv("AGENT_HOME", str(other))
    check("another home has its own answer", langs.terminal_lang() == "ko", langs.terminal_lang())


#: What `personagent memory` prints and the start-up refusal for a damaged memory file.
MEMORY_SENTENCES = (
    "Look at what it remembers, forget an item or bring one back",
    "Look at what the character remembers, forget an item, or bring one back.",
    "list what the character remembers (the default)",
    "list what was removed and can still be brought back",
    "only this chat, by its key as the list shows it", "print JSON instead of a table",
    "forget one item by its id", "the item's id, or the start of it",
    "bring back a removed item by its id", "the removed item's id, or the start of it",
    "Chat: {0}", "Chat: This page (key {0})",
    "What is said in `personagent chat` is practice, kept apart, and does not show here.",
    "Id", "Kind", "About", "First noted", "Last used", "Text", "Reason", "Removed",
    "Restorable until", "Always in mind", "Earlier in this chat", "Fact", "Event",
    "Replaced by a newer fact", "Merged with another fact", "No longer current",
    "Removed to make room", "Earlier version", "Could not be read", "Forgotten on the page",
    "Forgotten with this command", "said by {0}", "Nothing is remembered.",
    "Nothing removed can be brought back.", "No item has that id.",
    "Several chats have an always-present note; name one with --chat.",
    "That id matches more than one item; give more characters.", "Forgotten.",
    "To bring it back within 24 hours: {0}", "Restored.", "This item already exists.",
    "This item can no longer be restored.",
    "The service is running, but its activity data is turned off (DASHBOARD_ENABLED=false), "
    "so its memory cannot be reached from here. Turn activity data on, or stop the service first.",
    "The running service did not answer. Try again in a moment.",
    "The memory file {0} is damaged and was left untouched. A copy from {1} is at {2}; "
    "move it in place of the damaged file to start from it, or move the damaged file "
    "aside to start with an empty memory.",
    "The memory file {0} is damaged and was left untouched, and no earlier copy of it "
    "exists. Move the damaged file aside, for example by renaming it, to start with an "
    "empty memory.",
    "The practice chat's memory file {0} is damaged; the memory the character uses in its "
    "chats is not affected. Delete the folder {1} to start the practice chat with an "
    "empty memory.",
    "{0} could not start; see runtime/desktop/{1}.log",
)


def test_the_memory_command_is_translated_in_every_language() -> None:
    from persona_agent import memory_admin

    used = set(memory_admin.KINDS.values()) | set(memory_admin.REASONS.values())
    check("every kind and reason the command prints is in the list", used <= set(MEMORY_SENTENCES),
          repr(sorted(used - set(MEMORY_SENTENCES))))
    for path in sorted(TERMINAL.glob("*.json")):
        sentences = json.loads(path.read_text(encoding="utf-8"))
        missing = [s for s in MEMORY_SENTENCES if not sentences.get(s, "").strip()]
        check(f"locales/terminal/{path.name} has every memory sentence", not missing, repr(missing))
        for english in MEMORY_SENTENCES:
            slots = sorted(set(re.findall(r"\{\d\}", english)))
            check(f"{path.name}: {english!r} keeps its slots",
                  sorted(set(re.findall(r"\{\d\}", sentences[english]))) == slots)


def test_a_damaged_file_reads_as_one_translated_sentence(monkeypatch) -> None:
    monkeypatch.setenv("AGENT_LANG", "ja")
    text = langs.term("The memory file D:/home/runtime/memory.json is damaged and was left "
                      "untouched. A copy from 2026-11-10 is at D:/home/runtime/memory.json.bak; "
                      "move it in place of the damaged file to start from it, or move the "
                      "damaged file aside to start with an empty memory.")
    check("ja: the file, the day and the path are kept in the sentence",
          text.startswith("記憶ファイル D:/home/runtime/memory.json は破損") and "2026-11-10" in text
          and "D:/home/runtime/memory.json.bak" in text, text)

