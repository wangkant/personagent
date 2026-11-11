"""A long reply wraps at a sentence end, never after a title or a date's
ordinal; the German date at a line start keeps its day."""
from __future__ import annotations

import pytest

from persona_agent.textproc import TextProcessing as TP


@pytest.mark.parametrize("text,glued", [
    ("Am 3. Oktober ist Feiertag, und am 24. Dezember bin ich bei meinen Eltern. "
     "Danach fahre ich am 2. Januar zurück.", "2. Januar"),
    ("Ich war gestern beim Arzt und habe dort lange gewartet, bis endlich Dr. Müller kam "
     "und mich untersucht hat, das war echt anstrengend.", "Dr. Müller"),
    ("So I went to the clinic yesterday and waited for ages in that tiny room until "
     "finally Mr. Smith came in and checked me over, which took forever.", "Mr. Smith"),
    ("Мы долго ждали врача в этой маленькой комнате, пока наконец не пришёл "
     "т.е. наш доктор и всё не объяснил нам подробно.", "т.е. наш"),
])
def test_a_wrap_keeps_a_title_or_ordinal_with_its_word(text: str, glued: str) -> None:
    parts = TP._split_text(text)
    assert " ".join(parts) == text, parts
    assert any(glued in p for p in parts), parts


def test_a_real_sentence_end_still_wraps() -> None:
    text = ("Am 3. Oktober ist Feiertag, und am 24. Dezember bin ich bei meinen Eltern. "
            "Danach fahre ich am 2. Januar zurück.")
    parts = TP._split_text(text)
    assert len(parts) == 2 and parts[0].endswith("Eltern."), parts


@pytest.mark.parametrize("text", [
    "Termine:\n1. Mai Grillen\n3. Juni Konzert",
    "Ich wurde am\n12. März geboren",
    "na klar\n24. Dezember bin ich bei meinen Eltern\n31. Dezember auch",
])
def test_dates_at_line_starts_keep_their_days(text: str) -> None:
    assert TP._sanitize_reply(text, "en") == text


def test_a_counted_list_still_loses_its_numbers() -> None:
    assert TP._sanitize_reply("three things\n1. rice\n2. eggs\n3. tea", "en") == \
        "three things\nrice\neggs\ntea"
    assert TP._sanitize_reply("steps:\n1. open it", "en") == "steps:\nopen it"
