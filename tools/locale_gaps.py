"""What each language in persona_agent/locales/ still lacks: the sentences of the
setup wizard, the terminal trial and the demo that would show in English.

    python tools/locale_gaps.py
    python tools/locale_gaps.py ja    # the sentences themselves
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from persona_agent import chat, demo, langs  # noqa: E402
from persona_agent import setup_wizard as sw  # noqa: E402

#: Stay as written in every language: brand names, commands, speakers.
SAME = {"Y/n", "y/N", "OpenRouter", "DeepSeek", "SiliconFlow", "Zhipu GLM", "Moonshot / Kimi",
        "OpenAI", "Google Gemini", "Alibaba Bailian / Qwen", "Volcengine Ark / Doubao",
        "/why", "/learned", "/reset", "/quit", "{who}: {text}", "; ", " - ", ": "}


def sentences(tree, out: set[str]) -> None:
    if isinstance(tree, str):
        if re.search(r"[^\W\d_]", tree):
            out.add(tree)
    elif isinstance(tree, dict):
        for value in tree.values():
            sentences(value, out)
    elif isinstance(tree, (list, tuple)):
        for value in tree:
            sentences(value, out)


def keys() -> set[str]:
    out: set[str] = set()
    sentences([en for en, _ in sw._TEXT.values()], out)
    sentences([p.name[0] for p in sw.PROVIDERS] + [p.note[0] for p in sw.PROVIDERS], out)
    sentences([c.title[0] for c in sw.CHARACTERS], out)
    sentences([prompt[0] for fields in sw.PLATFORMS.values() for _, prompt in fields], out)
    sentences([chat._TEXT["en"], demo._TEXT["en"], demo.PERSONA["en"], demo._RETRY["en"],
               demo._PROBE["en"][1:], list(demo._ZH_LEDGER_REASONS)], out)
    for beats in demo.SCRIPTS["en"].values():
        for beat in beats:
            verdict = {k: v for k, v in (beat.verdict or {}).items() if k != "reaction"}
            sentences([beat.text, beat.reply, verdict], out)
    return out - SAME


def main() -> None:
    wanted = sys.argv[1] if len(sys.argv) > 1 else ""
    everything = keys()
    for code in langs.CODES:
        if code in ("en", "zh"):
            continue
        missing = sorted(everything - set(langs.catalog(code)))
        if code == wanted:
            print("\n".join(missing))
        elif not wanted:
            print(f"{code}: {len(everything) - len(missing)}/{len(everything)}")


if __name__ == "__main__":
    main()
