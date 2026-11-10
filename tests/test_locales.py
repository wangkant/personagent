"""persona_agent/locales/: every language has every sentence it is asked for."""
from __future__ import annotations

import json
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

