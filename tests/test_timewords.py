"""Time words in the ten chat languages, read without a model call.

    python -m pytest tests/test_timewords.py
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from persona_agent import chatlangs, ranking, timewords

from helpers import check

TZ = timezone(timedelta(hours=8))
#: Wednesday 11 November 2026, 21:40.
NOW = datetime(2026, 11, 11, 21, 40, tzinfo=TZ).timestamp()


def _day(month: int, day: int) -> float:
    return datetime(2026, month, day, tzinfo=TZ).timestamp()


EXPECTED = {
    "yesterday": (_day(11, 10), _day(11, 11)),
    "last_week": (_day(11, 2), _day(11, 9)),
    "last_month": (_day(10, 1), _day(11, 1)),
    "days_ago": (_day(11, 8), _day(11, 9)),
    "last_weekend": (_day(11, 7), _day(11, 9)),
}

PHRASES = {
    "en": ("what happened yesterday?", "what did we do last week",
           "back last month", "she said it 3 days ago", "how was last weekend"),
    "zh": ("昨天聊了什么", "上周干嘛了", "上个月的事", "3天前说的", "上周末去哪了"),
    "zh-TW": ("昨天聊了什麼", "上週做了什麼", "上個月的事", "三天前說的", "上週末去哪了"),
    "ja": ("昨日何話した", "先週何した", "先月のこと", "3日前に言った", "先週末どこ行った"),
    "ko": ("어제 무슨 얘기", "지난주에 뭐 했지", "지난달 일", "3일 전에 말했어", "지난 주말 어디 갔어"),
    "es": ("qué pasó ayer", "qué hicimos la semana pasada", "el mes pasado",
           "lo dijo hace 3 días", "el fin de semana pasado"),
    "fr": ("hier on a parlé", "la semaine dernière", "le mois dernier",
           "il y a 3 jours", "le week-end dernier"),
    "de": ("was war gestern", "letzte Woche", "letzten Monat", "vor 3 Tagen",
           "letztes Wochenende"),
    "pt-BR": ("o que houve ontem", "semana passada", "mês passado", "há 3 dias",
              "fim de semana passado"),
    "ru": ("что было вчера", "на прошлой неделе", "в прошлом месяце",
           "3 дня назад", "в прошлые выходные"),
}


def test_the_table_covers_every_chat_language() -> None:
    check("one table per chat language", set(timewords.TABLE) == set(chatlangs.SPECS),
          repr(sorted(timewords.TABLE)))
    check("and the test covers them all", set(PHRASES) == set(chatlangs.SPECS))


def test_each_language_resolves_the_common_ranges() -> None:
    kinds = ("yesterday", "last_week", "last_month", "days_ago", "last_weekend")
    for lang, phrases in PHRASES.items():
        for kind, text in zip(kinds, phrases):
            got = timewords.resolve(text, NOW, TZ, [lang])
            check(f"{lang}: {text!r} is {kind}", got == EXPECTED[kind], repr(got))
            check(f"{lang}: {text!r} without a language hint",
                  timewords.resolve(text, NOW, TZ) == EXPECTED[kind])


def test_more_ranges() -> None:
    sat = (_day(11, 7), _day(11, 8))
    for text in ("last saturday", "上周六", "先週の土曜日", "el sábado pasado",
                 "letzten Samstag", "в прошлую субботу"):
        check(f"{text!r} is last week's Saturday",
              timewords.resolve(text, NOW, TZ) == sat, repr(timewords.resolve(text, NOW, TZ)))
    check("today runs to now", timewords.resolve("today", NOW, TZ) == (_day(11, 11), NOW))
    check("this week from Monday", timewords.resolve("本周", NOW, TZ) == (_day(11, 9), NOW))
    check("the day before yesterday", timewords.resolve("前天", NOW, TZ)
          == (_day(11, 9), _day(11, 10)))
    check("a few days ago", timewords.resolve("a few days ago", NOW, TZ)
          == (_day(11, 5), _day(11, 10)))
    check("the earliest time words win", timewords.resolve(
        "yesterday, not last week", NOW, TZ) == EXPECTED["yesterday"])
    check("last night spans the evening and the small hours",
          timewords.resolve("昨晚", NOW, TZ)
          == (_day(11, 10) + 18 * 3600, _day(11, 11) + 6 * 3600))


def test_lookalikes_are_not_time_words() -> None:
    for text in ("I last saw it in March", "our weekly call", "上周期的数据",
                 "lastly, the weekend", "on Saturday", "todays", "hierarchy", "",
                 "we meet every week"):
        check(f"{text!r} names no time", timewords.resolve(text, NOW, TZ) is None,
              repr(timewords.resolve(text, NOW, TZ)))


def test_negation_in_every_language() -> None:
    for text in ("I don't eat meat", "I do not eat meat", "我不吃肉", "我沒有車",
                 "肉は食べない", "고기를 안 먹어", "no como carne", "je ne mange pas",
                 "ich esse kein Fleisch", "não como carne", "я не ем мясо"):
        check(f"{text!r} is negated", timewords.has_negation(text))
    for text in ("I eat meat", "我吃肉", "肉を食べる", "como carne", "ich esse Fleisch"):
        check(f"{text!r} is not", not timewords.has_negation(text))


def test_the_prompt_phrase_of_a_range() -> None:
    check("one day", timewords.phrase(EXPECTED["yesterday"], tz=TZ) == "Tue 10 Nov",
          timewords.phrase(EXPECTED["yesterday"], tz=TZ))
    check("a week", timewords.phrase(EXPECTED["last_week"], tz=TZ)
          == "Mon 2 Nov to Sun 8 Nov", timewords.phrase(EXPECTED["last_week"], tz=TZ))
    span = ranking.date_span(_day(11, 10) + 19 * 3600, _day(11, 10) + 20.5 * 3600,
                             NOW, tz=TZ)
    check("an event within a day", span == "Tue 10 Nov, 19:00–20:30", span)
    check("an event over days", ranking.date_span(_day(11, 10), _day(11, 12), NOW, tz=TZ)
          == "10 to 12 Nov")
    check("a roll-up's month", ranking.month_label(_day(9, 3), tz=TZ) == "September 2026")
