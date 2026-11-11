"""Time words in the ten chat languages, read without a model call.

`resolve("what did we do last week", now)` is the local-time range the
words name, or None. A wrong match only moves a ranking bonus; it never
writes anything. Bare weekday names ("on Saturday") are not read: too many
false positives. `NEGATION` serves the consolidation's negation check, where
a false hit can only refuse a change."""
from __future__ import annotations

import re
from datetime import datetime, timedelta, tzinfo
from typing import Iterable, Optional

from .ranking import day_label

Range = tuple[float, float]

_CJK_NUM = {"一": 1, "二": 2, "两": 2, "兩": 2, "三": 3, "四": 4, "五": 5,
            "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
_WORD_NUM = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
             "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "deux": 2, "trois": 3,
             "quatre": 4, "zwei": 2, "drei": 3, "vier": 4, "fünf": 5, "dois": 2,
             "duas": 2, "três": 3, "два": 2, "две": 2, "три": 3, "четыре": 4,
             "пять": 5}

#: Weekday words, Monday first.
_WEEKDAYS = {
    "en": ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday",
           "sunday"),
    "zh": ("一", "二", "三", "四", "五", "六", "日|天"),
    "ja": ("月", "火", "水", "木", "金", "土", "日"),
    "ko": ("월", "화", "수", "목", "금", "토", "일"),
    "es": ("lunes", "martes", "miércoles|miercoles", "jueves", "viernes",
           "sábado|sabado", "domingo"),
    "fr": ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi",
           "dimanche"),
    "de": ("montag", "dienstag", "mittwoch", "donnerstag", "freitag",
           "samstag|sonnabend", "sonntag"),
    "pt-BR": ("segunda(?:-feira)?", "terça(?:-feira)?|terca(?:-feira)?",
              "quarta(?:-feira)?", "quinta(?:-feira)?", "sexta(?:-feira)?",
              "sábado|sabado", "domingo"),
    "ru": ("понедельник", "вторник", "среду", "четверг", "пятницу", "субботу",
           "воскресенье"),
}
_WEEKDAYS["zh-TW"] = _WEEKDAYS["zh"]


def _wd(lang: str) -> str:
    return "(" + "|".join(_WEEKDAYS[lang]) + ")"


_N = r"(\d{1,2}|[一二两兩三四五六七八九十]{1,2})"
_EN_N = r"(\d{1,2}|two|three|four|five|six|seven)"

#: Per chat language: (pattern, kind). Kinds: today, morning, yesterday,
#: last_night, day_before, days_ago (group 1 = N), few_days, this_week,
#: last_week, last_weekend, last_weekday (group 1 = weekday), this_month,
#: last_month.
_RULES: dict[str, list[tuple[str, str]]] = {
    "en": [
        (r"\btoday\b", "today"),
        (r"\b(?:this morning|earlier today)\b", "morning"),
        (r"\byesterday\b", "yesterday"),
        (r"\blast night\b", "last_night"),
        (r"\bthe day before yesterday\b", "day_before"),
        (rf"\b{_EN_N} days ago\b", "days_ago"),
        (r"\b(?:a few|a couple of|several) days ago\b", "few_days"),
        (r"\bthis week\b", "this_week"),
        (r"\blast week\b", "last_week"),
        (r"\blast weekend\b", "last_weekend"),
        (rf"\blast {_wd('en')}\b", "last_weekday"),
        (r"\bthis month\b", "this_month"),
        (r"\blast month\b", "last_month"),
    ],
    "zh": [
        (r"今天|今日", "today"),
        (r"今早|今天早上|(?<![明后昨每])早上", "morning"),
        (r"昨天|昨日", "yesterday"),
        (r"昨晚|昨夜|昨天晚上", "last_night"),
        (r"前天", "day_before"),
        (rf"{_N}天(?:以)?前", "days_ago"),
        (r"前几天|前些天|几天前", "few_days"),
        (r"这周|这星期|这个星期|这礼拜|这个礼拜|本周", "this_week"),
        (r"上周(?![期末一二三四五六日天])|上个?星期(?![一二三四五六日天])"
         r"|上个?礼拜(?![一二三四五六日天])", "last_week"),
        (r"上周末|上个周末", "last_weekend"),
        (rf"(?:上周|上个?星期|上个?礼拜){_wd('zh')}", "last_weekday"),
        (r"这个月|这月|本月", "this_month"),
        (r"上个月|上月", "last_month"),
    ],
    "zh-TW": [
        (r"今天|今日", "today"),
        (r"今早|今天早上", "morning"),
        (r"昨天|昨日", "yesterday"),
        (r"昨晚|昨夜|昨天晚上", "last_night"),
        (r"前天", "day_before"),
        (rf"{_N}天(?:以)?前", "days_ago"),
        (r"前幾天|前些天|幾天前", "few_days"),
        (r"這週|這周|這星期|這個星期|這禮拜|本週|本周", "this_week"),
        (r"上[週周](?![期末一二三四五六日天])|上個?星期(?![一二三四五六日天])"
         r"|上個?禮拜(?![一二三四五六日天])", "last_week"),
        (r"上[週周]末|上個週末", "last_weekend"),
        (rf"(?:上[週周]|上個?星期|上個?禮拜){_wd('zh-TW')}", "last_weekday"),
        (r"這個月|本月", "this_month"),
        (r"上個月|上月", "last_month"),
    ],
    "ja": [
        (r"今日|きょう", "today"),
        (r"今朝", "morning"),
        (r"(?<!一)昨日|きのう", "yesterday"),
        (r"昨夜|昨晩|ゆうべ", "last_night"),
        (r"一昨日|おととい", "day_before"),
        (rf"{_N}日前", "days_ago"),
        (r"数日前|何日か前", "few_days"),
        (r"今週", "this_week"),
        (r"先週(?!末|の?[月火水木金土日]曜)", "last_week"),
        (r"先週末", "last_weekend"),
        (rf"先週の?{_wd('ja')}曜", "last_weekday"),
        (r"今月", "this_month"),
        (r"先月", "last_month"),
    ],
    "ko": [
        (r"오늘", "today"),
        (r"오늘\s*아침", "morning"),
        (r"어제(?!밤)", "yesterday"),
        (r"어젯밤|어제\s*밤", "last_night"),
        (r"그저께|그제", "day_before"),
        (r"(\d{1,2})\s*일\s*전", "days_ago"),
        (r"며칠\s*전", "few_days"),
        (r"이번\s*주(?!말)", "this_week"),
        (r"지난\s*주(?!말)", "last_week"),
        (r"지난\s*주말", "last_weekend"),
        (rf"지난\s*주?\s*{_wd('ko')}요일", "last_weekday"),
        (r"이번\s*달", "this_month"),
        (r"지난\s*달", "last_month"),
    ],
    "es": [
        (r"\bhoy\b", "today"),
        (r"\besta mañana\b", "morning"),
        (r"\bayer\b", "yesterday"),
        (r"\banoche\b", "last_night"),
        (r"\b(?:anteayer|antier|antes de ayer)\b", "day_before"),
        (r"\bhace (\d{1,2}|dos|tres|cuatro|cinco) días\b", "days_ago"),
        (r"\bhace (?:unos|unos pocos|algunos) días\b", "few_days"),
        (r"\besta semana\b", "this_week"),
        (r"\bla semana pasada\b", "last_week"),
        (r"\bel fin de semana pasado\b", "last_weekend"),
        (rf"\bel {_wd('es')} pasado\b", "last_weekday"),
        (r"\beste mes\b", "this_month"),
        (r"\bel mes pasado\b", "last_month"),
    ],
    "fr": [
        (r"\baujourd'hui\b|\baujourd’hui\b", "today"),
        (r"\bce matin\b", "morning"),
        (r"(?<![-\w])hier(?! soir)\b", "yesterday"),
        (r"\bhier soir\b", "last_night"),
        (r"\bavant-hier\b", "day_before"),
        (r"\bil y a (\d{1,2}|deux|trois|quatre) jours\b", "days_ago"),
        (r"\bil y a quelques jours\b", "few_days"),
        (r"\bcette semaine\b", "this_week"),
        (r"\bla semaine dernière\b", "last_week"),
        (r"\b(?:le )?week-?end dernier\b", "last_weekend"),
        (rf"\b{_wd('fr')} dernier\b", "last_weekday"),
        (r"\bce mois-ci\b", "this_month"),
        (r"\ble mois dernier\b", "last_month"),
    ],
    "de": [
        (r"\bheute\b(?! morgen)", "today"),
        (r"\bheute morgen\b|\bheute früh\b", "morning"),
        (r"\bgestern\b(?! abend)", "yesterday"),
        (r"\bgestern abend\b", "last_night"),
        (r"\bvorgestern\b", "day_before"),
        (r"\bvor (\d{1,2}|zwei|drei|vier|fünf) tagen\b", "days_ago"),
        (r"\bvor (?:ein paar|einigen) tagen\b", "few_days"),
        (r"\bdiese woche\b", "this_week"),
        (r"\bletzte woche\b", "last_week"),
        (r"\bletztes wochenende\b", "last_weekend"),
        (rf"\bletzten {_wd('de')}\b", "last_weekday"),
        (r"\bdiesen monat\b", "this_month"),
        (r"\bletzten monat\b", "last_month"),
    ],
    "pt-BR": [
        (r"\bhoje\b(?! de manhã| cedo)", "today"),
        (r"\bhoje de manhã\b|\bhoje cedo\b", "morning"),
        (r"\bontem\b(?! à noite| a noite)", "yesterday"),
        (r"\bontem à noite\b|\bontem a noite\b", "last_night"),
        (r"\banteontem\b", "day_before"),
        (r"\bhá (\d{1,2}|dois|duas|três) dias\b|\b(\d{1,2}) dias atrás\b", "days_ago"),
        (r"\bhá (?:alguns|uns) dias\b|\balguns dias atrás\b", "few_days"),
        (r"\b(?:esta|essa) semana\b", "this_week"),
        (r"\bsemana passada\b", "last_week"),
        (r"\bfim de semana passado\b", "last_weekend"),
        (rf"\b{_wd('pt-BR')} passad[ao]\b", "last_weekday"),
        (r"\b(?:este|esse) mês\b", "this_month"),
        (r"\bmês passado\b", "last_month"),
    ],
    "ru": [
        (r"\bсегодня\b(?! утром)", "today"),
        (r"\bсегодня утром\b", "morning"),
        (r"\bвчера\b(?! вечером)", "yesterday"),
        (r"\bвчера вечером\b", "last_night"),
        (r"\bпозавчера\b", "day_before"),
        (r"\b(\d{1,2}|два|две|три|четыре|пять) (?:дня|дней) назад\b", "days_ago"),
        (r"\bнесколько дней назад\b", "few_days"),
        (r"\bна этой неделе\b", "this_week"),
        (r"\bна прошлой неделе\b", "last_week"),
        (r"\bв прошлые выходные\b", "last_weekend"),
        (rf"\bв прошл(?:ый|ую|ое) {_wd('ru')}\b", "last_weekday"),
        (r"\bв этом месяце\b", "this_month"),
        (r"\bв прошлом месяце\b", "last_month"),
    ],
}

#: Compiled per language; the keys are chatlangs.SPECS's.
TABLE: dict[str, list[tuple[re.Pattern, str]]] = {
    lang: [(re.compile(p, re.IGNORECASE), kind) for p, kind in rules]
    for lang, rules in _RULES.items()}

NEGATION = re.compile(
    r"\b(?:not|never|no longer|nobody|nothing)\b|n['’]t\b"
    r"|[不没沒别別未非]"
    r"|ない|ません|じゃない"
    r"|(?:^|\s)안(?=\s)|않|못"
    r"|\b(?:no|nunca|ya no|jamás|ni)\b"
    r"|\b(?:ne|n['’]|pas|jamais|plus|aucun|aucune)\b"
    r"|\b(?:nicht|kein\w*|nie|niemals)\b"
    r"|\b(?:não|nem)\b"
    r"|\b(?:не|нет|никогда|ни)\b",
    re.IGNORECASE)


def has_negation(text: str) -> bool:
    return bool(NEGATION.search(str(text or "")))


def _number(raw: str) -> Optional[int]:
    raw = raw.strip().lower()
    if raw.isdigit():
        return int(raw)
    if raw in _WORD_NUM:
        return _WORD_NUM[raw]
    if raw and all(ch in _CJK_NUM for ch in raw):
        if raw == "十":
            return 10
        if raw.startswith("十"):
            return 10 + _CJK_NUM[raw[1]]
        if len(raw) == 2 and raw[1] == "十":
            return _CJK_NUM[raw[0]] * 10
        return _CJK_NUM[raw[0]] if len(raw) == 1 else None
    return None


def _weekday(lang: str, word: str) -> Optional[int]:
    for i, alts in enumerate(_WEEKDAYS.get(lang, ())):
        if re.fullmatch(alts, word, re.IGNORECASE):
            return i
    return None


def _range(kind: str, m: re.Match, lang: str, now_dt: datetime) -> Optional[tuple[datetime, datetime]]:
    day0 = now_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    day = timedelta(days=1)
    monday = day0 - timedelta(days=day0.weekday())
    if kind == "today":
        return day0, now_dt
    if kind == "morning":
        return day0, min(day0 + timedelta(hours=12), now_dt)
    if kind == "yesterday":
        return day0 - day, day0
    if kind == "last_night":
        return day0 - day + timedelta(hours=18), day0 + timedelta(hours=6)
    if kind == "day_before":
        return day0 - 2 * day, day0 - day
    if kind == "days_ago":
        raw = next((g for g in m.groups() if g), "")
        n = _number(raw)
        if not n or n > 60:
            return None
        return day0 - n * day, day0 - (n - 1) * day
    if kind == "few_days":
        return day0 - 6 * day, day0 - day
    if kind == "this_week":
        return monday, now_dt
    if kind == "last_week":
        return monday - 7 * day, monday
    if kind == "last_weekend":
        return monday - 2 * day, monday
    if kind == "last_weekday":
        wd = _weekday(lang, m.group(1) or "")
        if wd is None:
            return None
        start = monday - 7 * day + wd * day
        return start, start + day
    if kind == "this_month":
        return day0.replace(day=1), now_dt
    if kind == "last_month":
        first = day0.replace(day=1)
        prev = (first - day).replace(day=1)
        return prev, first
    return None


def resolve(text: str, now: float, tz: Optional[tzinfo] = None,
            langs: Optional[Iterable[str]] = None) -> Optional[Range]:
    """(start, end) epoch seconds of the first time words in `text`, read in
    `langs` first and then in every language; None when there are none.
    Days are local to `tz` (the system's when None)."""
    text = str(text or "")
    if not text.strip():
        return None
    now_dt = datetime.fromtimestamp(now, tz)
    wanted = [lang for lang in (langs or ()) if lang in TABLE]
    for group in ([wanted] if wanted else []) + [list(TABLE)]:
        hits = []
        for lang in group:
            for pat, kind in TABLE[lang]:
                for m in pat.finditer(text):
                    hits.append((m.start(), -(m.end() - m.start()), lang, kind, m))
        for _start, _neg, lang, kind, m in sorted(hits, key=lambda h: h[:2]):
            span = _range(kind, m, lang, now_dt)
            if span:
                return span[0].timestamp(), span[1].timestamp()
    return None


def phrase(span: Range, lang: str = "en", tz: Optional[tzinfo] = None) -> str:
    """The range in the prompt's internal English: "Mon 3 Nov" or
    "Mon 3 Nov to Sun 9 Nov"."""
    start, end = span
    last = max(start, end - 1)
    if day_label(start, tz) == day_label(last, tz):
        return day_label(start, tz)
    return f"{day_label(start, tz)} to {day_label(last, tz)}"
