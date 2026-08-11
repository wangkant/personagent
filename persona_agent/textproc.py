"""Text processing: tokenising, sanitising, validating, splitting.

Everything here is pure — same input, same output, no I/O and no agent
state. The reply-safety gates (_sanitize_reply, _validate_reply_safe,
_looks_like_reasoning_leak) live here because they are the last thing
between the model and the group, and they must be testable in isolation."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import heapq
import io
import ipaddress
import json
import logging
import os
import random
import re
import socket
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Awaitable, Callable, Mapping, Optional, Sequence
from urllib.parse import urlencode, urlsplit

import httpx

logger = logging.getLogger("agent")


# Sentinels wrapping web-derived enrichment (URL og:title/desc) inside the
# extracted text. Control decisions (is_called / memory commands) run on a
# view with these spans removed, so third-party page content can't trigger
# them. Shared prompt/buffer paths retain the sentinels as a trust boundary;
# presentation-only callers may explicitly unwrap them with the helper below.
_WEB_DESC_OPEN = "\x02"

_WEB_DESC_CLOSE = "\x03"

_WEB_DESC_SPAN = re.compile("\x02[^\x03]*\x03")

def _strip_web_desc(text: str) -> str:
    """Control-plane view: web-derived enrichment spans removed entirely."""
    return _WEB_DESC_SPAN.sub("", text)

def _unwrap_web_desc(text: str) -> str:
    """Prompt/buffer view: keep the enrichment, drop the sentinel chars."""
    return text.replace(_WEB_DESC_OPEN, "").replace(_WEB_DESC_CLOSE, "")

# Cheap pre-filter so we only spend a search-decision call on messages that
# plausibly need a web lookup (questions / facts / memes / links), not on
# casual chatter like "lol" or "you there?".
_SEARCH_HINT_RE = re.compile(
    r"[?？]|who|what|when|where|why|how|which|is it|how much|how many|price|"
    r"news|latest|recent|release[ds]?|meme|slang|term|look ?up|search|google|"
    r"http|www\.|\.com|\.org|\.net|\.io|\.cn|"
    # Chinese fact-seeking hints (for the zh variant; harmless to English text)
    r"是什么|怎么|为什么|多少|哪里|哪个|谁是|新闻|最新|查一下|搜一下|价格",
    re.IGNORECASE,
)

# Common English function words filtered out of retrieval tokens so they don't
# uniformly inflate relevance scores. Deliberately excludes chat-signal words
# (lol, haha, etc.) which carry meaning for scenario matching.
_EN_STOPWORDS = frozenset({
    "the", "and", "you", "your", "yours", "that", "this", "these", "those",
    "with", "have", "has", "had", "for", "are", "was", "were", "but", "not",
    "its", "they", "them", "their", "his", "her", "she", "him", "our", "out",
    "can", "cant", "just", "one", "all", "any", "than", "then", "there",
    "about", "from", "into", "over", "been", "does", "did", "done", "because",
    "what", "when", "where", "why", "how", "who", "will", "would", "could",
    "should", "here", "very", "really", "still", "also", "even", "some",
})

# Topic-type keyword lexicons for _compute_chat_signals (drives the reply/PASS
# decision framework). Keys are lowercase; matching lowercases the chat text so
# "LOL"/"Haha" match too. The 'banter' bucket is the most language-specific.
_TOPIC_LEXICON = {
    "en": {
        "work": ["bug", "code", "error", "deploy", "ship", "deadline", "pr ",
                 "merge", "repo", "build", "project", "work", "meeting", "ticket",
                 "refactor", "commit", "prod", "staging", "api"],
        "banter": ["lol", "lmao", "lmfao", "rofl", "haha", "lolol", "dying",
                   "deadass", " fr ", "ratio", "based", "cope", "seethe", "bruh",
                   "bro ", "meme", "kek", "real ", "wtf", "omg", "lmaooo"],
    },
    "zh": {
        "work": ["bug", "代码", "code", "报错", "error", "需求", "deadline",
                 "项目", "project", "工作", "work"],
        "banter": ["哈哈", "草", "笑死", "梗", "绷", "乐", "lol", "lmao", "haha"],
    },
}

def _focus_tokens(text: str, lang: str = "en") -> set:
    """Tokenize focus text for few-shot / memory retrieval relevance scoring.

    English (default): lowercased word tokens of 3+ chars, minus common
    function-word stopwords. Chinese: 2-char sliding-window ngrams over CJK
    runs, unioned with the ASCII tokens (so mixed zh/en input still matches
    either pool). The ASCII tokens are always included since latin words show
    up in both languages."""
    focus_lc = text.lower()
    ascii_tokens = {
        t for t in re.findall(r"[a-z0-9]{3,}", focus_lc) if t not in _EN_STOPWORDS
    }
    if lang == "zh":
        chinese_chars = re.findall(r"[一-鿿]", focus_lc)
        cjk_ngrams = {
            "".join(chinese_chars[i:i + 2])
            for i in range(max(0, len(chinese_chars) - 1))
        }
        return cjk_ngrams | ascii_tokens
    return ascii_tokens

def _detect_image_mime(data: bytes) -> str:
    """Return a supported image MIME type from its file signature."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"GIF8"):
        return "image/gif"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"
    if data.startswith(b"BM"):
        return "image/bmp"
    if data[4:12] in (
        b"ftypheic", b"ftypheix", b"ftyphevc", b"ftypmif1", b"ftypmsf1",
    ):
        return "image/heic"
    if data[4:12] in (b"ftypavif", b"ftypavis"):
        return "image/avif"
    return ""

# Layer B/C: natural-rhythm pacing for spontaneous (non-@) reply paths.
# Sleep window suppresses most spontaneous replies at night so the bot isn't
# 24/7 online. Sub-trigger pass simulates "saw it, didn't feel like replying".
# Both only apply to judge/followup; called/owner always go through.
SLEEP_HOUR_START = 2          # 02:00 (inclusive)

SLEEP_HOUR_END = 7            # 07:00 (exclusive)

SLEEP_PASS_PROB = 0.70        # 70% PASS rate during sleep hours

SUB_TRIGGER_PASS_PROB = 0.35  # spontaneous skip on judge-mode triggers


# ===========================================================================
# The reply character policy
# ===========================================================================
#
# `_validate_reply_safe` is a fail-closed whitelist and it exists as a
# TOKEN-LEAK defence: a degraded model that dumps its system prompt, a
# Hermes-XML remnant, a JSON protocol frame, a SentencePiece `_` run or a
# provider chat template must never reach a human. That is why it is a
# whitelist and not a blocklist, and it stays one.
#
# But "reject" for that validator means DROP THE WHOLE REPLY, and a
# whitelist narrow enough to catch a chat template is also narrow enough to
# catch an ordinary sentence. Measured against the previous validator,
# every one of these produced `""` — the user saw nothing:
#
#   'ok ❤️ sure'  'done ✅️'  'yay \U0001f1ef\U0001f1f5'
#   'hug \U0001f468‍\U0001f469 ok'   '1️⃣ first'
#   'you mean ツンデレ right'   'なるほど okay that tracks'
#   'sure… if you say so'    's1 -> s2 → movie'    '← back'
#   'don’t worry about it'   'he said “hello” ok'   'wait – no'
#   'café later'  'naïve take'  'it costs $5'  '50° outside'  '£5 each'
#   'star ⭐ ok'  'clock ⏰ ok'  'tm ™ ok'  'play ▶ ok'  'bullet • ok'
#
# So the policy is three tiers, and the design rule is:
#
#   AN UNSUPPORTED CHARACTER DEGRADES TO A MISSING GLYPH, NEVER TO SILENCE
#   -- FOR THE CODE POINTS A TIER ACTUALLY NAMES.
#
# The second half of that sentence is not a caveat, it is the design. A code
# point named in NO tier still drops the WHOLE reply, which is the plan's
# "keep the fail-closed default for anything not named" and is what the suite
# asserts: Thai, Hebrew, Devanagari, Armenian and the block-elements range
# U+2580-259F all silence the reply, and adding a script is a deliberate act,
# not a side effect. Three ways to make a code point visible, and only three:
# a new STRIP range if it is decoration, a new MAP entry if it has an exact
# ASCII spelling, or a new named range in the ALLOW tier — either
# `_SCRIPT_LETTER_RANGES` if it is a script's letters, or a new name in
# OPTIONAL_CHARSETS (today: ellipsis, music, arrows) if it is a REGISTER a
# persona chooses rather than a language it writes.
#
# 1. STRIP  - named ranges removed before validation. The reply survives
#             minus the glyph. This is where emoji, invisible controls and
#             every OPTIONAL charset a persona did not ask for go.
# 2. MAP    - named characters rewritten to an ASCII equivalent that is
#             already allowed (curly quotes, en dash, no-break spaces).
# 3. ALLOW  - named ranges added to the whitelist itself, each with a reason.
#
# Tier 3 is the only security-adjacent one, so every range added there is
# checked against the leak corpus in `tests/test_textproc.py`. What a persona
# can NEVER do, whatever its style says: lift the hard-reject set (`< > { } |`
# and EVERY code point Unicode folds onto one of them, plus U+2581), keep an
# invisible code point, or move `max_chars` outside
# [_MIN_REPLY_CHARS, MAX_REPLY_CHARS].

# THE PER-TURN CEILING, RAISED FROM 500 TO 800 WITH THE REGISTER WIDENING.
#
# It is two things at once and both had to move together:
#
#   * the length at which a reply is CUT (`_truncate_with_seam`), and
#   * the per-turn exfiltration bound — the most text one compromised turn
#     can carry out.
#
# 500 was sized for the old register, "pass as a real person texting", where
# the widest band a persona could declare was ~100-200 characters. The
# register is now "inhabit a character" and the widest band is ~150-260
# characters (`prompts._LENGTH_RULES`) — and the band's character figure is
# the CHINESE count while its word figure is the English one, so the same
# band in English is ~60-110 words, i.e. 330-620 characters. Against a 500
# ceiling an ordinary English reply from a `long` persona would be TRUNCATED
# rather than written, which turns a deliberate widening into a seam in the
# middle of every other sentence.
#
# 800 is the top band's English ceiling plus headroom, so truncation stays
# what it was designed to be: the exception that catches a runaway, not the
# normal end of a reply.
#
# WHAT THE RAISE COSTS, stated rather than waved past: a compromised turn can
# carry 60% more text than it could. That is a CONSTANT, not the control —
# the controls are the whitelist, the hard-reject table and the leak
# detectors, all of which run on the FULL text before this cap is applied
# (see `_sanitize_reply`'s ordering note). Nothing about which SHAPES can
# leave changed here; only how much ordinary prose fits in one turn.
MAX_REPLY_CHARS = 800

# The floor under `ReplyStyle.max_chars`, and it is a CONTENT floor, not a
# sanity check. `_truncate_with_seam` spends len(TRUNCATION_SEAM) characters
# of the budget before any text at all, so a card asking for 4 yields " ...",
# which the post-truncation re-validation then refuses for "no letter
# content" — every reply from that persona is silence, through the very field
# this task added. 50 because that is already the bubble-split unit, i.e. the
# smallest thing this product treats as one message.
_MIN_REPLY_CHARS = 50

# Appended when a reply is cut at the cap. Pure ASCII on purpose: the seam is
# added after validation-by-character, so a seam that could itself fail the
# whitelist would turn a truncation into a drop. It must stay non-empty and
# non-whitespace: an empty seam turns truncation back into a subtler silence,
# and `''.endswith('')` is True, so the suite pins the LITERAL, not this name.
TRUNCATION_SEAM = " ..."

# A (low, high, reason) triple per entry; `high` is inclusive.
Ranges = Sequence[tuple[int, int, str]]

# --- Tier 1a: emoji pictographs -------------------------------------------
# Stripped unless the persona sets `allow_emoji`. The first ten entries are
# the original set; the rest are blocks that measured as WHOLE-REPLY DROPS
# because the old regex did not cover them.
_EMOJI_PICTOGRAPH_RANGES: Ranges = (
    (0x1F300, 0x1F5FF, "misc symbols and pictographs (incl. skin-tone modifiers)"),
    (0x1F600, 0x1F64F, "emoticons"),
    (0x1F680, 0x1F6FF, "transport and map symbols"),
    (0x1F700, 0x1F77F, "alchemical symbols"),
    (0x1F780, 0x1F7FF, "geometric shapes extended"),
    (0x1F900, 0x1F9FF, "supplemental symbols and pictographs"),
    (0x1FA00, 0x1FA6F, "chess symbols"),
    (0x1FA70, 0x1FAFF, "symbols and pictographs extended-A"),
    (0x2600, 0x26FF, "misc symbols"),
    (0x2700, 0x27BF, "dingbats"),
    (0x1F000, 0x1F0FF, "mahjong / domino / playing cards - decorative only"),
    (0x1F100, 0x1F1E5, "enclosed alphanumeric supplement below the flag block"),
    (0x1F200, 0x1F2FF, "enclosed ideographic supplement - decorative only"),
    (0x1F650, 0x1F67F, "ornamental dingbats"),
    (0x1F800, 0x1F8FF, "supplemental arrows-C - decorative only"),
    (0x2100, 0x214F, "letterlike symbols: TM, info, degC read as decoration in chat"),
    (0x2300, 0x23FF, "misc technical: watch, hourglass, alarm clock"),
    (0x25A0, 0x25FF, "geometric shapes: play button, squares, circles"),
    (0x2B00, 0x2BFF, "misc symbols and arrows: star, heavy arrows"),
    # -- the emoji that do NOT live in an emoji block ----------------------
    # Everything above is a BLOCK, and the blocks were derived from a sample
    # of replies that measured as whole-reply drops. That method finds a
    # block the moment one of its members shows up and is structurally blind
    # to an emoji that is the only one in its block — such a code point
    # cannot be reached by widening a neighbour, so it stayed a silence.
    #
    # These are those code points. The membership rule is "Unicode
    # Extended_Pictographic, minus everything the blocks above already
    # cover", and `tests/test_textproc.py` pins the list rather than trusting
    # this comment, because `unicodedata` does not expose the property and so
    # a scan cannot re-derive it the way the Cf tier's scan does.
    #
    # Each of these was measured as a WHOLE-REPLY DROP under the live default
    # style before it was named here — '汤©店里', '坐吧Ⓜ', '坐吧㊙', '坐吧⤴'.
    (0x00A9, 0x00A9, "copyright sign - emoji, and the only one in Latin-1 "
                     "Supplement, which is otherwise letters"),
    (0x00AE, 0x00AE, "registered sign - same, and the same block"),
    (0x2460, 0x24FF, "enclosed alphanumerics: the circled digits a model uses "
                     "to number a list, plus the M-in-a-circle emoji"),
    (0x2934, 0x2935, "arrow pointing rightwards then curving up/down - the two "
                     "emoji arrows that sit OUTSIDE the U+2190-21FF block the "
                     "`arrows` opt-in covers, so neither tier reached them"),
    (0x3200, 0x32FF, "enclosed CJK letters and months: the circled/parenthesised "
                     "hangul, ideographs and month names, decorative only"),
)

# --- Tier 1b: emoji modifiers ---------------------------------------------
# THE PRODUCTION BUG. These carry no glyph of their own, so the old strip
# regex (pictographs only) left them behind after eating the base character,
# and the leftovers hit the whitelist and dropped the entire reply.
#
# Everything here is INVISIBLE, so an `allow_emoji` persona keeping it is a
# channel unless the keep is bounded. Two bounds, and both are load-bearing:
#
#   * the tag block and VS1-VS15 are NOT here — they moved to Tier 1c and are
#     stripped unconditionally. An emoji persona loses subdivision flags (it
#     keeps the base flag) and that is the correct price: U+E0020-E007F is a
#     1:1 invisible mirror of printable ASCII;
#   * ZWJ, VS16 and the keycap box are kept only when they are ANCHORED to a
#     base they can legitimately modify (`_modifier_is_anchored`). A bare run
#     of thirty joiners is not an emoji, it is thirty invisible characters.
#
# The regional indicators are the exception that needs no bound: they RENDER
# (as lettered squares when unpaired), so they are not an invisible channel.
_EMOJI_MODIFIER_RANGES: Ranges = (
    (0x200D, 0x200D, "ZWJ - joins the pieces of a family/profession sequence"),
    (0x20E3, 0x20E3, "combining enclosing keycap - the box around 1 in 1-keycap"),
    (0xFE0F, 0xFE0F, "VS16, emoji presentation - the selector that follows a heart"),
    (0x1F1E6, 0x1F1FF, "regional indicators - a flag is two of these"),
)

# Emoji modifiers that are invisible on their own and therefore only kept in
# the position that gives them a meaning. See `_modifier_is_anchored`.
_BOUND_MODIFIERS = frozenset({0x200D, 0x20E3, 0xFE0F})

_KEYCAP_BASES = frozenset(ord(c) for c in "0123456789#*")

# --- Tier 1c: invisible code points ----------------------------------------
# Stripped UNCONDITIONALLY — for an emoji persona, for an arrows persona, for
# every style a card can express — and hard-rejected if a direct caller hands
# one straight to the validator. They render as NOTHING, so they are never
# chat content, and a code point that occupies no space is the standard
# carrier for invisible-text smuggling and right-to-left display spoofing.
#
# THE MEMBERSHIP RULE, because "the ones I thought of" is how this hole got
# opened the first time: general category Cf, complete, MINUS U+200D (the
# joiner is an emoji modifier above, kept only between two pictographs), PLUS
# the code points that are invisible without being Cf — the variation
# selectors, the Hangul fillers, the Khmer inherent vowels, the blank braille
# cell. `tests/test_textproc.py` re-derives the Cf half by scanning every code
# point in `unicodedata` and fails if this table has fallen behind it.
_INVISIBLE_FORMAT_RANGES: Ranges = (
    # -- category Cf ------------------------------------------------------
    (0x00AD, 0x00AD, "soft hyphen - invisible, and the same code point that "
                     "once walked through the inbound scrubber unnoticed"),
    (0x0600, 0x0605, "Arabic number signs"),
    (0x061C, 0x061C, "Arabic letter mark - a bidi control"),
    (0x06DD, 0x06DD, "Arabic end of ayah"),
    (0x070F, 0x070F, "Syriac abbreviation mark"),
    (0x0890, 0x0891, "Arabic pound / piastre marks above"),
    (0x08E2, 0x08E2, "Arabic disputed end of ayah"),
    (0x200B, 0x200C, "zero-width space / non-joiner"),
    (0x200E, 0x200F, "left-to-right and right-to-left marks"),
    (0x202A, 0x202E, "bidi embedding and override - display-spoofing vector"),
    (0x2060, 0x2064, "word joiner and invisible math operators"),
    (0x2066, 0x206F, "bidi isolates and the deprecated format controls"),
    (0xFEFF, 0xFEFF, "BOM used inline as a zero-width no-break space"),
    (0xFFF9, 0xFFFB, "interlinear annotation controls"),
    (0x110BD, 0x110BD, "Kaithi number sign"),
    (0x110CD, 0x110CD, "Kaithi number sign above"),
    (0x13430, 0x1343F, "Egyptian hieroglyph format controls"),
    (0x1BCA0, 0x1BCA3, "shorthand format controls"),
    (0x1D173, 0x1D17A, "musical notation format controls"),
    (0xE0000, 0xE007F, "THE TAG BLOCK. U+E0020-E007F is a 1:1 invisible mirror "
                       "of printable ASCII and the canonical carrier for "
                       "invisible-text smuggling; the whole block goes, "
                       "including the unassigned holes and LANGUAGE TAG"),
    # -- invisible, but not Cf --------------------------------------------
    (0x115F, 0x1160, "Hangul choseong / jungseong fillers - zero width by design"),
    (0x17B4, 0x17B5, "Khmer inherent vowels - render as nothing"),
    (0x180B, 0x180F, "Mongolian free variation selectors and vowel separator"),
    (0x2800, 0x2800, "braille pattern BLANK - the one braille cell with no dots"),
    (0x3164, 0x3164, "Hangul filler"),
    (0xFE00, 0xFE0E, "variation selectors 1-15; VS16 is an emoji modifier above"),
    (0xFFA0, 0xFFA0, "half-width Hangul filler - an INVISIBLE code point sitting "
                     "inside the full-width block the whitelist allows wholesale, "
                     "so it was released under the DEFAULT style"),
    (0xE0100, 0xE01EF, "variation selectors supplement"),
)

# --- Tier 1d / 3b: the optional per-persona charsets -----------------------
# A persona names these in its card. Opted in, they reach the whitelist;
# NOT opted in, they are STRIPPED rather than rejected, so the fail-closed
# default costs a glyph instead of the message.
#
# KANA USED TO BE ONE OF THESE AND IS NOT ANY MORE. It was added as the
# 二次元 REGISTER — a persona saying ツンデレ for flavour — and an opt-in is
# the right shape for a register. It is the wrong shape for a LANGUAGE:
# behind an opt-in that no shipped card sets, "answer in Japanese" meant the
# kana were stripped out and the reader got the English half of a bilingual
# sentence. Kana moved to `_SCRIPT_LETTER_RANGES` on the default path, for
# the same reason the Latin alphabet is there — a persona should not have to
# declare "I am allowed to write in Japanese". The name is no longer known,
# so a card still asking for it logs the usual unknown-charset warning and
# loses nothing.
_OPTIONAL_CHARSETS: dict[str, Ranges] = {
    # One code point. The register it carries (trailing off) has no ASCII
    # equivalent that survives: '...' reads as a pause, the glyph reads as a
    # shrug, and personas are written around the difference.
    "ellipsis": (
        (0x2026, 0x2026, "horizontal ellipsis"),
    ),
    # Sits inside the emoji strip range, so without an explicit opt-in it
    # disappears even though it is typography rather than a pictograph.
    "music": (
        (0x2669, 0x266F, "musical note through sharp sign"),
    ),
    # The ASCII spelling of an arrow is '->', and '>' is a HARD REJECT that
    # drops the reply. A persona that narrates sequences has no other option.
    "arrows": (
        (0x2190, 0x21FF, "arrows block: left, right, up, down, double arrows"),
    ),
}

OPTIONAL_CHARSETS = frozenset(_OPTIONAL_CHARSETS)

# --- Tier 2: typography normalised into the existing whitelist -------------
# Models emit these constantly and every one of them dropped the whole reply.
# Mapping beats widening: the whitelist stays exactly as narrow as it was.
#
# THE COMPLETENESS RULE, added after four separate typography families were
# each found HALF-mapped. The pattern every time: a family is spelled by
# several code points, the one the sample happened to contain got mapped, and
# its siblings kept dropping the whole reply. `_TYPOGRAPHY_MAP` is now
# maintained by FAMILY — if a code point is here, every code point Unicode
# puts in the same general category and block is here too — and
# `tests/test_textproc.py` re-derives each family by scanning
# `unicodedata.category` and fails when one has fallen behind.
#
# Values may be more than one character (`‼` -> `!!`); `str.translate` is
# fine with that and it beats deleting punctuation the author meant.
_TYPOGRAPHY_MAP = {
    0x2018: "'", 0x2019: "'", 0x201A: "'", 0x201B: "'",  # curly single quotes
    0x201C: '"', 0x201D: '"', 0x201E: '"', 0x201F: '"',  # curly double quotes
    # THE DASH FAMILY, category Pd in General Punctuation (U+2010-U+2015).
    # U+2013 and U+2212 were mapped; the other four were not, and every one
    # of them measured as a whole-reply drop ('坐吧―汤好了' -> ''). U+2015 is
    # the one that matters most for this product: it is a long horizontal
    # bar, and it is what a CJK-trained model reaches for when it wants the
    # Chinese 破折号 and does not spell it as a doubled U+2014.
    0x2010: "-",                                          # hyphen
    0x2011: "-",                                          # non-breaking hyphen
    0x2012: "-",                                          # figure dash
    0x2013: "-",                                          # en dash reads as a hyphen
    0x2015: "-",                                          # horizontal bar
    0x2212: "-",                                          # minus sign
    # THE OTHER HALF OF THE QUOTATION MARKS, categories Pi/Pf. The eight
    # curly quotes above are Pi/Pf too; these four are the rest of that
    # family, and '他说«你好»' was a drop while '他说“你好”' was not.
    0x00AB: '"', 0x00BB: '"',                             # guillemets
    0x2039: "'", 0x203A: "'",                             # single guillemets
    # PRIMES. Minutes/feet and seconds/inches, with exact ASCII spellings.
    0x2032: "'", 0x2033: '"',
    # DOUBLED ASCII PUNCTUATION that Unicode also encodes as one code point.
    # These two are Extended_Pictographic (so the emoji tier would have a
    # claim on them) but they are punctuation first and they have an exact
    # ASCII spelling, so mapping keeps the emphasis the author wrote instead
    # of deleting it.
    0x203C: "!!", 0x2049: "!?",
    # LINE AND PARAGRAPH SEPARATORS, categories Zl and Zp. COMPLETE BY
    # CONSTRUCTION: these are the only two code points in those two
    # categories in the whole of Unicode. They are line breaks, the
    # sanitizer already normalises "\n", and they were reaching the
    # whitelist — which has a whitespace rule that lists '\n\t \r' literally
    # — and dropping the reply.
    0x2028: "\n", 0x2029: "\n",
    0x00D7: "x", 0x00F7: "/",                             # multiplication / division
    0x00A0: " ", 0x2007: " ", 0x2009: " ", 0x202F: " ",   # non-breaking / thin spaces
    0x2022: " ", 0x00B7: " ",                             # bullet, middle dot
    # --- the punctuation of the scripts the ALLOW tier now names ----------
    # `_SCRIPT_LETTER_RANGES` admits LETTERS ONLY, which is what keeps its
    # safety property checkable. Every script it names also has punctuation a
    # sentence in that script cannot be written without, and a code point in
    # no tier drops the whole reply — so the punctuation is handled here,
    # where an exact ASCII spelling exists, and in the strip tier where it
    # does not. Without this half the widening would deliver a Japanese
    # sentence and silence the Arabic question that ends in `؟`.
    #
    # COMPLETE BY BLOCK-AND-CATEGORY, the same rule the dash family follows.
    # U+30A0 is the ONLY Pd in the Katakana block and U+30FB the only Po, so
    # those two lines are the whole of that family.
    0x30A0: "-",                                          # katakana-hiragana double hyphen
    0x30FB: " ",                                          # katakana middle dot, as U+00B7
    0x037E: "?",                                          # Greek question mark (it is a ';' glyph but asks a question)
    0x0387: ",",                                          # Greek ano teleia, the Greek semicolon; matches the ';' -> ',' rule above
    0x060C: ",", 0x061B: ",",                             # Arabic comma / semicolon
    0x061F: "?", 0x06D4: ".",                             # Arabic question mark / full stop
    # ARABIC-INDIC DIGITS, both sets, mapped to the ASCII digits they ARE.
    # Category Nd with an exact one-to-one spelling, so mapping is strictly
    # better than admitting them: a date written `٢٠٢٦` reads as 2026 to
    # every downstream consumer instead of as an unnamed script.
    **{0x0660 + i: str(i) for i in range(10)},            # Arabic-Indic
    **{0x06F0 + i: str(i) for i in range(10)},            # extended Arabic-Indic (Persian/Urdu)
}

# --- Tier 3: named additions to the whitelist itself -----------------------
#
# THIS TIER IS ON THE DEFAULT PATH, WHICH IS A DELIBERATE DECISION. It used
# to say "AND THE ONLY PLACE IN THIS FILE WHERE THE FAIL-CLOSED DEFAULT
# MOVED", and the script-tier widening made that false: `_SCRIPT_LETTER_RANGES` below is a second
# such place and a much larger one. Corrected rather than left standing,
# because this file's own ledger records that wrong DOCUMENTATION about a
# protection is worse than a hole — it makes the next reader stop checking.
# Both tiers are held to the same property (letters only, no structure) and
# each has its own scan asserting it. Measured for this one: 403
# code points that the old default rejected are accepted by the current
# default (398 Latin letters, 4 currency/degree signs, and `$`). The four
# optional charsets above are behind an opt-in; these are not. The decision
# is recorded explicitly rather than inherited:
#
#   KEPT ON THE DEFAULT PATH. The reason is that the widening's whole
#   population is LETTERS AND PRICES in ordinary English chat — 'café later',
#   'naïve take', 'José said hi', 'it costs $5', '50° outside', '£5 each' —
#   every one of them measured as a WHOLE-REPLY DROP, which is the `· seen ·`
#   read receipt this task exists to remove. Putting them behind an opt-in
#   would mean the live default still silences a reply for containing the
#   word café. When this was decided NOTHING IN PRODUCTION CONSTRUCTED A
#   ReplyStyle (`agent.py` and `transport.py` called `_sanitize_reply(reply,
#   lang)` at seven sites), so "behind an opt-in" meant "off for everyone" and
#   the fix would have shipped inert. The wiring landed later —
#   `Agent.__init__` resolves `self.reply_style` from `<assets>/card.json` and
#   all seven sites pass it — and the decision is unchanged: an opt-in that
#   now works is still the wrong shape for the Latin alphabet, because a
#   persona should not have to declare "I am allowed to write café". An
#   opt-in is the right shape for a REGISTER a
#   persona chooses (♪, …, →); it is the wrong shape for the Latin
#   alphabet with diacritics, which is not a register, and for the currency
#   sign of an ordinary price. THAT SENTENCE USED TO NAME KANA FIRST,
#   and the script-tier widening is the correction: kana is not a register either, it is how
#   Japanese is spelled, and it moved to `_SCRIPT_LETTER_RANGES` beside the
#   other five scripts for exactly the reason given here for Latin.
#
#   WHAT MAKES THAT SAFE IS A PROPERTY, NOT AN INTENTION: after the exclusion
#   below, every one of the 399 remaining code points is a LETTER, a currency
#   sign or the degree sign. None is a bracket, a bar, a slash or any other
#   structural character, so none can spell a protocol frame or a role
#   separator on its own — a leak needs structure, and this tier admits none.
#   `tests/test_textproc.py` states that as a check over the whole tier
#   rather than leaving it as this paragraph's assertion.
#
# U+01C0-U+01C3 ARE CARVED OUT, and they are why the paragraph above needs a
# check behind it. `(0x0100, 0x024F, "Latin Extended-A and -B")` looks like
# one clean block of letters and is not: U+01C0 `ǀ` renders as a single
# vertical bar, U+01C1 `ǁ` as two, U+01C2 `ǂ` as a barred one and U+01C3 `ǃ`
# as an exclamation mark. Measured at 8d3f7e3 under the DEFAULT style, no
# persona opt-in required:
#
#   'assistantǀuserǀsystem'  RELEASED     'ǀim_startǀassistant'  RELEASED
#   _validate_reply_safe('ǀǀǀ', 'en') -> (True, '')
#
# and U+01C0 incremented `letter_count`, so a reply made of nothing but pipe
# twins also satisfied the "no letter content" gate. They are click letters
# (Khoisan orthographies); nothing in café / naïve / José needs them, so the
# range is split around them rather than the hard-reject table being widened
# — see the note on `_HARD_REJECT_FOLD_RANGES` for why that tier is the wrong
# home for a confusable that does not fold.
_LATIN_LETTER_RANGES: Ranges = (
    (0x00C0, 0x00D6, "Latin-1 uppercase with diacritics"),
    (0x00D8, 0x00F6, "Latin-1 lowercase with diacritics (multiplication sign excluded)"),
    (0x00F8, 0x00FF, "Latin-1 lowercase tail (division sign excluded)"),
    (0x0100, 0x01BF, "Latin Extended-A and -B up to the click letters"),
    (0x01C4, 0x024F, "Latin Extended-B from just past the click letters"),
)

# The carve-outs, named so a test can assert them and a reader can see what
# each costs. `high` inclusive, same shape as every other table here.
#
# NO LONGER ONLY THE LATIN FOUR. The script tier (below) ships letters from
# blocks that carry their own vertical-bar twins, and the full-width blanket
# in `_validate_reply_safe` admits a halfwidth one. Every entry here is a
# Unicode LETTER — that is the point of the table: `unicodedata` would admit
# every one of them, so the exclusion is written down instead of derived,
# and the leak corpus carries rows spelled with them so any future widening
# that re-admits one goes red instead of green.
_BAR_CONFUSABLES: Ranges = (
    (0x01C0, 0x01C0, "LATIN LETTER DENTAL CLICK - renders as one vertical bar, "
                     "a visual twin of the role separator '|'"),
    (0x01C1, 0x01C1, "LATIN LETTER LATERAL CLICK - renders as two vertical bars"),
    (0x01C2, 0x01C2, "LATIN LETTER ALVEOLAR CLICK - a barred vertical bar"),
    (0x01C3, 0x01C3, "LATIN LETTER RETROFLEX CLICK - a visual twin of '!'"),
    (0x04C0, 0x04C0, "CYRILLIC LETTER PALOCHKA - a bare vertical bar. The "
                     "cost is real (Chechen, Avar and their neighbours write "
                     "with it) but Russian needs nothing here, and the "
                     "mixed-script rule cannot see an ALL-Cyrillic frame: "
                     "'системаӀпользователь' mixes nothing"),
    (0x04CF, 0x04CF, "CYRILLIC SMALL LETTER PALOCHKA - the same bar, "
                     "lowercase"),
    (0x1175, 0x1175, "HANGUL JUNGSEONG I - the medial vowel that renders as "
                     "one vertical bar; modern Korean writes precomposed "
                     "syllables (U+AC00+), so a BARE medial I is not prose"),
    (0x3163, 0x3163, "HANGUL LETTER I - the compatibility spelling of the "
                     "same bar, and Hangul is deliberately OUTSIDE the "
                     "mixed-script rule, so 'assistantㅣuser' mixes nothing "
                     "it can object to"),
    (0xFFDC, 0xFFDC, "HALFWIDTH HANGUL LETTER I - the same bar again, hiding "
                     "inside the full-width blanket; refused on that path by "
                     "_FULLWIDTH_BAR_TWINS"),
)

# The `0xFF00-0xFFEF` blanket in `_validate_reply_safe` predates the script
# tier and admits a BLOCK, not letters, so the letters-only argument never
# covered it. Three of its members render as vertical bars and NFKC-fold
# onto nothing, so the hard-reject closure cannot reach them either: the
# halfwidth Hangul letter I (a letter — also in `_BAR_CONFUSABLES`), the
# halfwidth forms light vertical (a box-drawing bar, category So) and the
# fullwidth broken bar (category Sm). A frozenset because the blanket path
# runs per character of every reply.
_FULLWIDTH_BAR_TWINS = frozenset({0xFFDC, 0xFFE4, 0xFFE8})

# Currency and degree. '$' is in the ASCII punctuation string below; these
# four are the non-ASCII ones a price or a temperature needs. A product that
# is about to charge money cannot drop the reply that quotes the price.
_SYMBOL_ALLOWED = frozenset({0x00A3, 0x00A5, 0x00B0, 0x20AC})

# --- Tier 3b: the scripts, each named, letters only ------------------------
#
# 拓展多语种. The language CONTENT gate is gone — the validator no longer
# demands CJK of a zh build — but removing it did not make the product
# multilingual, because the CHARACTER whitelist below it still allowed Latin
# and Han and nothing else. Measured against `_validate_reply_safe` before
# this tier existed, every one of these was rejected as `unexpected char`,
# i.e. the whole reply became silence:
#
#   'なるほど、そうですね'      (hiragana)      'ラーメン食べた'   (katakana)
#   '알겠어요'  'ㅋㅋㅋ'        (Hangul)        'да, конечно'      (Cyrillic)
#   'γεια σου'                  (Greek)         'مرحبا، كيف حالك؟' (Arabic)
#
# So a persona could be TOLD to answer in Japanese and physically could not.
#
# THE MEMBERSHIP RULE, and it is the whole of this tier's safety argument:
# EVERY CODE POINT NAMED HERE IS A LETTER (Unicode category `L*`). It is the
# same property `_LATIN_LETTER_RANGES` is kept to and for the same reason —
# "a leak needs STRUCTURE, and this tier admits none": no bracket, no bar, no
# slash, no quote, so nothing here can spell a protocol frame or a role
# separator on its own. `tests/test_textproc.py` states it as a scan over the
# whole tier rather than leaving it as this paragraph's assertion, and it
# DERIVES the sub-ranges from `unicodedata` rather than trusting the numbers
# below — which is why the ranges are split around their blocks' non-letters
# instead of taking a block wholesale.
#
# THE NON-LETTERS OF THESE SAME SCRIPTS ARE NOT ORPHANED, because a code
# point in no tier drops the whole reply and 'مرحبا كيف حالك؟' would then be
# silence for its final glyph. They are handled one tier down: the ones with
# an exact ASCII spelling are MAPPED (`_TYPOGRAPHY_MAP` — the Arabic comma,
# question mark and digits, the Greek question mark and ano teleia, the two
# katakana punctuation marks) and the ones without are STRIPPED
# (`_SCRIPT_MARK_RANGES`). The reply survives either way.
#
# WHAT IS DELIBERATELY STILL FAIL-CLOSED: Thai, Hebrew, Devanagari, Armenian,
# Georgian, Greek Extended (polytonic), the Cyrillic extended blocks, the
# Arabic presentation forms. Adding one is a deliberate act with a stated
# reason, which is exactly what this table is; nothing about the tier's shape
# is a claim that these six are the only scripts that will ever be here.
_SCRIPT_LETTER_RANGES: Ranges = (
    # -- Japanese ---------------------------------------------------------
    (0x3041, 0x3096, "hiragana syllables - the script half of ordinary "
                     "Japanese prose"),
    (0x309D, 0x309F, "hiragana iteration marks and the yori digraph"),
    (0x30A1, 0x30FA, "katakana syllables - loanwords, names, emphasis"),
    (0x30FC, 0x30FF, "the prolonged sound mark ー (without which ラーメン "
                     "cannot be written), the katakana iteration marks and "
                     "the koto digraph"),
    # -- Korean -----------------------------------------------------------
    (0xAC00, 0xD7A3, "Hangul syllables - the precomposed block modern Korean "
                     "is actually written in"),
    (0x1100, 0x115E, "Hangul Jamo initial consonants (choseong)"),
    (0x1161, 0x1174, "Hangul Jamo medial vowels up to U+1175 JUNGSEONG I, "
                     "which renders as one bare vertical bar and is carved "
                     "out - see _BAR_CONFUSABLES; U+115F and U+1160, the "
                     "zero-width FILLERS below this range, are carved out "
                     "here as well as being in the invisible tier"),
    (0x1176, 0x11FF, "Hangul Jamo medial vowels past the bar twin, and the "
                     "final consonants"),
    (0x3131, 0x3162, "Hangul compatibility jamo up to U+3163 HANGUL LETTER I "
                     "- ㅋㅋㅋ (Korean chat's laugh, U+314B) and ㅠㅠ stay "
                     "in; the letter I itself renders as one bare vertical "
                     "bar and is carved out - see _BAR_CONFUSABLES"),
    (0x3165, 0x318E, "Hangul compatibility jamo past U+3164 HANGUL FILLER, "
                     "which is invisible and stays out"),
    # -- Cyrillic ---------------------------------------------------------
    (0x0400, 0x0481, "Cyrillic basic and historic letters"),
    (0x048A, 0x04BF, "Cyrillic extended letters; U+0482-U+0489 are the "
                     "thousands sign and the combining marks and are stripped "
                     "rather than admitted"),
    (0x04C1, 0x04CE, "Cyrillic extended letters between the two palochkas"),
    (0x04D0, 0x04FF, "Cyrillic extended letters past U+04CF; U+04C0 and "
                     "U+04CF, capital and small PALOCHKA, render as bare "
                     "vertical bars and are carved out - see "
                     "_BAR_CONFUSABLES"),
    (0x0500, 0x052F, "Cyrillic Supplement - Komi, Khanty, Kurdish letters"),
    # -- Greek ------------------------------------------------------------
    # Five ranges rather than one because the block interleaves its letters
    # with unassigned holes, three spacing accent marks (Sk) and two
    # punctuation marks (Po), and a letters-only tier cannot span them.
    (0x0386, 0x0386, "Greek capital alpha with tonos"),
    (0x0388, 0x038A, "Greek capital epsilon/eta/iota with tonos"),
    (0x038C, 0x038C, "Greek capital omicron with tonos"),
    (0x038E, 0x03A1, "Greek capital upsilon through rho"),
    (0x03A3, 0x03CE, "Greek sigma (both final and medial) through omega with "
                     "tonos - the rest of the modern alphabet"),
    # -- Arabic -----------------------------------------------------------
    (0x0620, 0x064A, "Arabic letters, including the tatweel U+0640 that "
                     "stretches a join"),
    (0x066E, 0x066F, "Arabic dotless beh and qaf"),
    (0x0671, 0x06D3, "Arabic extended letters - Persian, Urdu, Sindhi"),
    (0x06D5, 0x06D5, "Arabic letter ae"),
    (0x06EE, 0x06EF, "Arabic dal and reh with inverted v"),
    (0x06FA, 0x06FC, "Arabic sheen/dad/ghain with dot below"),
    (0x06FF, 0x06FF, "Arabic heh with inverted v"),
)

# --- Tier 1e: the marks of those scripts, stripped not rejected ------------
# Non-spacing marks, spacing accents and decorative signs that belong to the
# blocks above but are not letters. They have no ASCII spelling, so the map
# cannot take them, and admitting them would break the letters-only property
# the tier's safety argument rests on. Stripped, so the reply survives minus
# the mark — the file's standing answer for "unsupported but harmless".
#
# The Japanese entry is the one with a visible cost, so it is stated: NFC
# spells が as one code point and that is what a model emits, but DECOMPOSED
# kana (か + U+3099) loses its voicing here and arrives as か. A wrong
# syllable beats a silent turn, and the alternative — admitting a combining
# mark — buys a stackable invisible-width channel for a case NFC already
# covers.
_SCRIPT_MARK_RANGES: Ranges = (
    (0x0482, 0x0489, "Cyrillic thousands sign and the combining/enclosing "
                     "marks (Mn, Me, So)"),
    (0x0375, 0x0375, "Greek lower numeral sign (Sk)"),
    (0x0384, 0x0385, "Greek tonos and dialytika-tonos, spacing accents (Sk)"),
    (0x03F6, 0x03F6, "Greek reversed lunate epsilon SYMBOL (Sm) - a symbol "
                     "sitting inside the letter block, and symbols are what "
                     "a frame is made of"),
    (0x0610, 0x061A, "Arabic honorific and Quranic annotation marks (Mn)"),
    (0x064B, 0x065F, "Arabic harakat - the vowel diacritics ordinary prose "
                     "leaves off anyway (Mn)"),
    (0x0670, 0x0670, "Arabic superscript alef (Mn)"),
    (0x06D6, 0x06ED, "Arabic small high/low annotation marks and stop signs"),
    (0x3099, 0x309C, "the Japanese voicing marks: combining dakuten and "
                     "handakuten plus their two spacing forms"),
)

# A protocol field label opening a LINE — "Decision:", "style:", "判断：". A
# real reply never opens this way, so it is the one leak shape that can be
# named exactly, and therefore the one that can be CUT rather than reacted to
# by throwing the whole turn away.
#
# Anchored per line and matched with `.match()` (not `re.search` over the whole
# string) so the detector and the scrubber ask literally the same question of
# literally the same unit. When those two drifted apart, a reply could be
# dropped for containing a label the scrubber was unable to locate.
_LEAK_LABEL_RE = re.compile(
    r"(?i)^[\s\-•*]*(input|speaker|intent|decision|style|"
    r"输入|发言人|意图|决策|风格|分析|判断)\s*[:：]")

# --- The hard reject, closed under Unicode folding -------------------------
# `< > { } |` is the set, but the SET IS NOT THE CHARACTERS — it is the
# meanings, and Unicode spells each of those meanings more than once. The
# whitelist allows the full-width block U+FF00-FFEF wholesale, so before this
# table the full-width twins walked straight out: '＜persona＞ You are Mira
# ＜/persona＞' and '｛"reply":"sure"｝' were released verbatim under EVERY
# style including the default that is live today. U+FF5C was carved out by
# hand and its three bracket neighbours were not, which is what happens when
# a set is written from memory instead of derived.
#
# THE MEMBERSHIP RULE: every code point c with NFKC(c) in '<>{}|'. That is
# this exact list — the suite re-derives it by scanning every code point and
# fails if a fold is missing. Full-width punctuation is what a CJK-trained
# provider emits, which is why U+FF5C was in the set at all.
#
# WHAT THE DERIVATION CANNOT REACH, and a reader has to know this before
# trusting the paragraph above. NFKC closure catches every code point that
# FOLDS onto one of the five. It does not catch a code point that merely
# LOOKS like one, because looking alike is not a Unicode relation — and the
# review that found this said it plainly: the "five MEANINGS, not five
# characters" argument above is what made the set feel closed, while the same
# commit widened the whitelist over a block containing U+01C0 `ǀ`, a vertical
# bar that folds to itself and walked out under the DEFAULT style.
#
# So the policy for a VISUAL CONFUSABLE THAT DOES NOT FOLD is one tier down,
# not here, and it is deliberate that it is:
#
#   * a confusable is refused by the ALLOW tier simply NOT NAMING it, which
#     is the fail-closed default doing its job — see `_BAR_CONFUSABLES`,
#     the explicit list, carved out of `_LATIN_LETTER_RANGES`;
#   * it is NOT added here, because this table's value is that its membership
#     is DERIVABLE and therefore checkable by a scan. Hand-adding "the ones
#     someone noticed" turns it back into the chain of ors it replaced, and
#     the completeness scan stops meaning anything;
#   * and it stays visible to the corpus: a confusable stopped by the ALLOW
#     tier is stopped by a decision a future widening can undo, so
#     `tests/test_textproc.py` carries leak rows spelled with one. A
#     confusable moved into this table would be stopped BEFORE the ALLOW tier
#     runs, and those rows would go green against any widening at all.
_HARD_REJECT_FOLD_RANGES: Ranges = (
    (0xFE37, 0xFE38, "presentation forms for vertical curly brackets -> { }"),
    (0xFE5B, 0xFE5C, "small curly brackets -> { }"),
    (0xFE64, 0xFE65, "small less-than / greater-than signs -> < >"),
    (0xFF1C, 0xFF1C, "full-width less-than -> <"),
    (0xFF1E, 0xFF1E, "full-width greater-than -> >"),
    (0xFF5B, 0xFF5B, "full-width left curly bracket -> {"),
    (0xFF5C, 0xFF5C, "full-width vertical line -> | (provider role separator)"),
    (0xFF5D, 0xFF5D, "full-width right curly bracket -> }"),
)

# CJK bracket punctuation. NOT the hard reject: 《书名》 is ordinary Chinese and
# a whole-reply drop on it would be the silence this task exists to remove.
# But a bracket is STRUCTURE, and '〈persona〉 You are Mira 〈/persona〉' was
# released with its brackets intact while the ASCII twin was dropped. The
# sanitizer already deleted 「」『』《》【】; this is the rest of the family,
# derived from the block rather than from the four pairs someone happened to
# hit. U+2329/U+232A are here because they are canonically equivalent to
# U+3008/U+3009 and, sitting inside the misc-technical strip range, an emoji
# persona was KEEPING them.
# Code points, not glyphs: U+2329 and U+3008 are indistinguishable in every
# font, so an ASCII-only spelling is the only one a reviewer can check.
_CJK_BRACKETS = "".join(chr(c) for c in (
    0x2329, 0x232A,                  # angle brackets, canonically U+3008/9
    0x3008, 0x3009,                  # CJK angle brackets - the pair reading as < >
    0x300A, 0x300B,                  # double angle brackets (already stripped)
    0x300C, 0x300D, 0x300E, 0x300F,  # corner brackets (already stripped)
    0x3010, 0x3011,                  # lenticular brackets (already stripped)
    0x3014, 0x3015, 0x3016, 0x3017,  # tortoise-shell and white lenticular
    0x3018, 0x3019, 0x301A, 0x301B,  # white tortoise-shell and white square
))

# Everything the sanitizer may remove before the whitelist ever sees it.
_STRIPPABLE_RANGES: Ranges = tuple(
    list(_EMOJI_PICTOGRAPH_RANGES)
    + list(_EMOJI_MODIFIER_RANGES)
    + list(_INVISIBLE_FORMAT_RANGES)
    + list(_SCRIPT_MARK_RANGES)
    + [r for ranges in _OPTIONAL_CHARSETS.values() for r in ranges]
)


def _in_ranges(codepoint: int, ranges: Ranges) -> bool:
    """Written as a loop rather than `any(genexp)` on purpose. This runs once
    per character of every reply, and building a generator per character cost
    more than the whole rest of the sanitizer.

    Stated as a RATIO, not in microseconds: an absolute us figure in a comment
    is a fact about the machine it was taken on and goes stale on the next
    one. On a ~200-character ordinary English reply the shipped sanitizer is
    ~1.4x the pre-policy one; the generator-per-character version was ~2.9x
    for the default style and ~10x for the widest. The fixture, the machine
    and the numbers of the day are in the task report, which is where a
    measurement with a date on it belongs."""
    for lo, hi, _reason in ranges:
        if lo <= codepoint <= hi:
            return True
    return False


def _expand(ranges: Ranges) -> frozenset:
    """Range table to a membership set, for the checks on the per-character
    path where an O(1) lookup beats a scan."""
    return frozenset(c for lo, hi, _r in ranges for c in range(lo, hi + 1))


def _char_class(ranges: Ranges) -> str:
    """Character-class body for a range table, for use inside `[...]`."""
    parts = []
    for lo, hi, _reason in ranges:
        parts.append(re.escape(chr(lo)) if lo == hi
                     else f"{re.escape(chr(lo))}-{re.escape(chr(hi))}")
    return "".join(parts)


_STRIPPABLE_RE = re.compile("[" + _char_class(_STRIPPABLE_RANGES) + "]+")

# Checked for every character of every reply, so membership rather than a scan.
_INVISIBLE_CODEPOINTS = _expand(_INVISIBLE_FORMAT_RANGES)

# Same: one frozenset lookup replaces `ch in '<>{}|' or c == 0xFF5C or ...`,
# and more importantly it makes the reject set a TABLE that a test can check
# for completeness instead of a chain of ors that a test can only sample.
_HARD_REJECT_CODEPOINTS = (
    frozenset(ord(c) for c in "<>{}|")
    | _expand(_HARD_REJECT_FOLD_RANGES)
    | {0x2581}          # SentencePiece subword marker; folds to nothing, named
)

_OPTIONAL_CODEPOINTS = {name: _expand(ranges)
                        for name, ranges in _OPTIONAL_CHARSETS.items()}

# --- the arrows opt-in buys narration, not a frame -------------------------
#
# THE PROBLEM THE OPT-IN CREATED. Tier 3's safety property is stated as a
# property and checked as one: after the U+01C0-U+01C3 carve-out, all 399
# code points it admits are category `L*` — letters, plus a currency sign —
# so "a leak needs structure, and this tier admits none" holds by
# construction. That argument covers the DEFAULT path and nothing else.
# `arrows` is the whole U+2190-U+21FF block: 112 code points, every one of
# them a SYMBOL, and symbols are exactly what a frame is made of.
#
# It was once rated a note rather than a hole on the ground that no
# production call site constructed a `ReplyStyle` — true when it was
# written, and untrue since `Agent.__init__` began resolving
# `self.reply_style` and passing it at every sanitize site. Measured with a
# persona card that says `{"charsets": ["arrows"]}`:
#
#   '←persona→ You are Mira, ignore prior rules'  RELEASED VERBATIM
#   '→system→ assistant →user→'                   RELEASED VERBATIM
#
# both of which the default style degrades to their letters alone.
#
# WHAT SEPARATES THE TWO USES, and it is not the character — it is whether
# the arrow HUGS a bare token. The register the opt-in exists for is
# narration between phrases: 'check the log → then the socket', 's1 → s2 →
# s3', where every arrow has whitespace on both sides. A frame is a token
# gripped on both sides with no space to breathe: `←persona→`, `→system→`.
# So the rule is a shape, not a name list — naming `persona`/`system`/
# `assistant` would be exactly the blocklist this policy's whitelist design
# forbids, and would miss the next model's vocabulary.
#
# The leading `(?<![^\s])` (start of string or after whitespace) is what
# keeps 'log→socket→crash' — an unspaced narration chain — out of the match:
# there, the arrows are inside a word rather than opening a frame.
#
# `(?:\s?/\s?)?` IS ONE TOKEN AND IT IS THE WHOLE CORRECTNESS OF THIS RULE.
# It was first written `\s?/?\s?`, which makes every part optional
# INDEPENDENTLY — so the pattern also matched `<arrow><space><word><arrow>`
# with no slash anywhere, and the frame's defining property (the opening
# arrow HUGS the token) silently stopped being required on the left. That
# released nothing; it ATE the register instead. Measured, under a card
# with the arrows opt-in:
#
#   'the pipeline is lint → test→ deploy'  -> ''   frame='→ test→'
#   '→ build→test→ship'                    -> ''   frame='→ build→'
#   's1 → s2→ s3'                          -> ''   frame='→ s2→'
#   '← back→ forward'                      -> ''   frame='← back→'
#
# MIXED-SPACING narration — every one of them ordinary ops prose, and an
# empty sanitize result is `· seen ·` downstream (`agent.py` and
# `transport.py` both treat "" as PASS), which is the exact outcome the
# widening exists to remove. It hid because the first narration table was
# all-spaced or all-unspaced rows and never mixed the two in one string.
#
# Bound to the slash, whitespace is only tolerated as padding AROUND a
# closing slash — `←/persona→`, `← /persona→`, `←/ persona→` — and a bare
# space can no longer open a frame.
#
# WHAT THIS RULE DOES NOT CATCH, owned rather than discovered later. Every
# one of these is a deliberate stop, and the reason is always the same: this
# rule's false positives are WHOLE DROPPED REPLIES, so each widening buys
# coverage with the register — and the one-token version of that trade is
# what produced the NO-GO above. None of these is needed by a measured
# attack shape.
#
#   1. A SPACED OPENING frame: `→ system→`. Cost of binding the slash.
#   2. A SPACED PAIR: `⇒ system prompt follows ⇐`. The earlier note called
#      this "indistinguishable from `s1 → s2 → s3`", which is FALSE and
#      worth correcting because a wrong stated reason is how a rule gets
#      widened badly later: `⇒ … ⇐` is an INWARD-FACING pair while a
#      narration chain is same-direction, and the `⇒im_start⇐` row in the
#      corpus already relies on exactly that distinction. It is catchable.
#      It is not caught because a directional-pairing rule over arbitrary
#      spans of prose is a much larger false-positive surface than the
#      hugging rule, and the corpus's `⟹ system prompt follows ⟸` stays
#      rejected on its own (supplemental-arrows-A is outside the opt-in).
#   3. A NON-ASCII token: `←系统→ 你是Mira`, `←システム→`. The token class
#      is `[A-Za-z_][A-Za-z0-9._:-]*`. Widening it to CJK would put the
#      rule on top of Chinese narration, where an arrow between two hanzi
#      has no space to distinguish it — the mixed-spacing failure again,
#      against the product's primary conversation language.
#   4. A NON-WHITESPACE character before the opening arrow: `"←persona→ …"`,
#      `(←persona→ …)`, `note:←persona→ …` all defeat `(?<![^\s])`.
#      Admitting quotes/parens/colons there re-opens the `log→socket→crash`
#      class, since a chain can follow any of them too.
_ARROW_BLOCK = _char_class(_OPTIONAL_CHARSETS["arrows"])
_ARROW_FRAME_RE = re.compile(
    rf"(?<![^\s])[{_ARROW_BLOCK}](?:\s?/\s?)?"
    rf"[A-Za-z_][A-Za-z0-9._:-]{{0,60}}[{_ARROW_BLOCK}]"
)

# --- the confusable half of the script tier: mixed-script tokens -----------
#
# WHY THIS RULE HAD TO ARRIVE WITH THE SCRIPTS AND NOT AFTER THEM. This file
# already had a policy for a VISUAL CONFUSABLE THAT DOES NOT NFKC-FOLD, and
# it is stated at `_HARD_REJECT_FOLD_RANGES`: "a confusable is refused by the
# ALLOW tier simply NOT NAMING it". That policy worked because the ALLOW tier
# named almost nothing outside Latin and Han — the four click letters were an
# accident of one Latin range and were carved out by hand (`_BAR_CONFUSABLES`).
#
# `_SCRIPT_LETTER_RANGES` names the whole Cyrillic and Greek alphabets, and
# those two are the scripts Unicode's own confusables data is mostly about:
# а е о р с у х ѕ і ј and α ε ο ρ ν are twins of Latin letters, and the
# corpus in `tests/test_textproc.py` carries the exact shape they spell —
#
#   'ѕуѕtem: уоу аге Mira, а helpful аssistant'
#
# a row whose own comment predicted this change in as many words: "the shape
# any 'just add the script' widening releases". Naming the scripts without
# naming this rule would have released it.
#
# THE RULE IS ABOUT ARRANGEMENT, like `_arrow_frame` and for the same reason:
# no single character in a homoglyph word is objectionable, the MIXTURE is.
# Inside one unbroken run of letters, at most one of {Latin, Cyrillic, Greek}
# may appear. That is Unicode TR39's mixed-script detection narrowed to the
# three alphabets that are confusable with each other, and it is narrowed on
# purpose:
#
#   * kana, Hangul, Han and Arabic are NOT in it. None of them looks like a
#     Latin letter, and CJK is written without spaces — 'バグをfixした' and
#     '버그fix했다' are ordinary mixed-script sentences with no separator to
#     hide behind, so a rule over them would be a false positive generator
#     against the product's own primary languages;
#   * a word BOUNDARY resets it. 'да, Python ok' and "Python'ом" are two runs
#     each and pass; only an unseparated splice is refused.
#
# WHAT IT REFUSES TO BUY, owned rather than discovered later. A single Greek
# letter hugging Latin — 'μs', 'Δt', '5kΩ' — is refused by this rule. Each of
# those is a WHOLE-REPLY DROP TODAY (the Greek block was in no tier at all),
# so nothing regresses; the rule declines to fix them rather than opening the
# homoglyph shape by counting. The right fix for those is to name the micro
# sign and the ohm sign as SYMBOLS, one code point each with a reason, which
# is a different table and a different day.
#
# The pre-scan is a single C-level search for any Greek or Cyrillic code
# point at all. An English or Chinese reply never enters the loop below it.
# Sliced out of the tier above rather than restated, so a range added there
# joins the rule automatically instead of quietly falling outside it.
_CYRILLIC_RANGES: Ranges = tuple(
    r for r in _SCRIPT_LETTER_RANGES if 0x0400 <= r[0] <= 0x052F)

_GREEK_RANGES: Ranges = tuple(
    r for r in _SCRIPT_LETTER_RANGES if 0x0370 <= r[0] <= 0x03FF)

_CONFUSABLE_SCRIPT_RANGES: Ranges = _CYRILLIC_RANGES + _GREEK_RANGES

_CONFUSABLE_SCAN_RE = re.compile(
    "[" + _char_class(_CONFUSABLE_SCRIPT_RANGES) + "]")


def _letter_script(codepoint: int, ch: str) -> str:
    """`'latin'` / `'cyrillic'` / `'greek'` for a letter in one of the three
    mutually confusable alphabets, `''` for everything else.

    Everything else INCLUDES kana, Hangul, Han, Arabic, digits, punctuation
    and whitespace, and that is what makes a run boundary: a Japanese or
    Korean sentence with an English word spliced into it contains no run that
    holds two of these three, so it cannot trip the rule."""
    if codepoint < 0x80:
        return "latin" if ch.isalpha() else ""
    if _in_ranges(codepoint, _LATIN_LETTER_RANGES):
        return "latin"
    if _in_ranges(codepoint, _CYRILLIC_RANGES):
        return "cyrillic"
    if _in_ranges(codepoint, _GREEK_RANGES):
        return "greek"
    return ""

# Derived rather than written down, so it cannot drift out of step with the
# tables: the lowest code point any emoji range covers. `is_emoji` rejects
# everything below it without scanning, which is most of an English reply.
_EMOJI_MIN_CODEPOINT = min(
    lo for lo, _hi, _r in tuple(_EMOJI_PICTOGRAPH_RANGES) + tuple(_EMOJI_MODIFIER_RANGES)
)


def _is_emoji_base(codepoint: int) -> bool:
    """A character a bound modifier is allowed to attach to: a pictograph or a
    regional indicator. Both RENDER, which is the whole point — a modifier is
    only allowed to be invisible when it is modifying something visible."""
    return (_in_ranges(codepoint, _EMOJI_PICTOGRAPH_RANGES)
            or 0x1F1E6 <= codepoint <= 0x1F1FF)


def _modifier_is_anchored(text: str, idx: int) -> bool:
    """True when the bound modifier at `text[idx]` sits in the ONE position
    that gives it a meaning. Anywhere else it is just an invisible character
    that an `allow_emoji` persona would otherwise be free to emit by the
    hundred: measured before this guard, 30 consecutive U+200D and 30
    consecutive U+FE0F both survived the sanitizer with no pictograph in
    sight, and 'a reply' made of nothing but modifiers satisfied the
    'no letter content' gate because each one scored as emoji content.

    Deliberately positional and not a count: a length limit on invisible runs
    still leaves a channel, a position requirement does not. One base, one
    modifier — a SECOND VS16 is not anchored, because its neighbour is the
    first VS16 rather than the pictograph.

      U+FE0F  emoji presentation  <- pictograph, regional indicator, or a
                                     keycap base (0-9 # *)
      U+20E3  keycap box          <- keycap base, optionally through one VS16
      U+200D  joiner              <- pictograph on BOTH sides (that is what
                                     joining means), optionally through VS16
    """
    cp = ord(text[idx])
    prev = ord(text[idx - 1]) if idx > 0 else -1
    if cp == 0x20E3:
        if prev in _KEYCAP_BASES:
            return True
        return (prev == 0xFE0F and idx >= 2
                and ord(text[idx - 2]) in _KEYCAP_BASES)
    if cp == 0xFE0F:
        return _is_emoji_base(prev) or prev in _KEYCAP_BASES
    if cp == 0x200D:
        left = _is_emoji_base(prev) or (
            prev == 0xFE0F and idx >= 2 and _is_emoji_base(ord(text[idx - 2])))
        return (left and idx + 1 < len(text)
                and _is_emoji_base(ord(text[idx + 1])))
    return True


@dataclass(frozen=True)
class ReplyStyle:
    """The per-persona half of the reply character policy.

    THE CARRIER. A persona declares this in its card as a `reply_style`
    object; `from_card` parses it and the result is passed to
    `_sanitize_reply` / `_validate_reply_safe` as the `style` argument.
    Passing nothing means `DEFAULT_REPLY_STYLE`, the conservative
    baseline: no emoji, no optional charset, the 500-character cap.

    Fields:
      allow_emoji  - skip the emoji strip for PICTOGRAPHS and let the
                     whitelist accept them. It buys pictographs, regional
                     indicators, and the three bound modifiers in the one
                     position each is meaningful (see `_modifier_is_anchored`)
                     — and nothing else. Every invisible code point in
                     `_INVISIBLE_FORMAT_RANGES` is still stripped, the tag
                     block included, so an emoji persona loses subdivision
                     flags and keeps the base flag.
      charsets     - names from OPTIONAL_CHARSETS. Anything not named here is
                     stripped, not rejected.
      max_chars    - where truncation happens. BOUNDED AT BOTH ENDS, to
                     [_MIN_REPLY_CHARS, MAX_REPLY_CHARS]. The ceiling because
                     the cap is also the per-turn exfiltration bound: a
                     persona may shorten its own leash and never lengthen it.
                     The FLOOR because a budget smaller than the seam produces
                     " ...", which the post-truncation re-validation refuses —
                     a card asking for 4 silenced every reply it ever made.

    Deliberately NOT a field: the hard-reject set. No persona may re-admit
    `< > { } |`, any code point that NFKC-folds onto one of them, or
    U+2581.

    KNOWN SEAM — TWO PERSONA-STYLE SCHEMAS, NO SHARED PARSER. This class
    reads a card's `reply_style` object; `prompts.PersonaStyle` /
    `parse_persona_style` read a `[style]` block inside `persona.txt`. Same
    concept ("how this persona is allowed to write"), two authoring surfaces,
    two validators, two failure modes for the author to learn. Merging them is
    an architectural decision, not a fix: it touches the card schema and the
    persona corpora, and it would change the shape of a security boundary
    the test suites currently pin. Stated here rather than only in a report,
    because this docstring is where the next reader arrives."""

    allow_emoji: bool = False
    charsets: frozenset = frozenset()
    max_chars: int = MAX_REPLY_CHARS

    def __post_init__(self) -> None:
        known = frozenset(n for n in self.charsets if n in _OPTIONAL_CHARSETS)
        object.__setattr__(self, "charsets", known)
        capped = min(int(self.max_chars), MAX_REPLY_CHARS)
        floored = max(_MIN_REPLY_CHARS, capped)
        if floored != capped:
            # Logged like an unknown charset, because it is the same class of
            # author mistake and the same fix (edit the card). Silently
            # honouring it would make the persona mute with no trace.
            logger.warning("[Agent] reply_style: max_chars %r is below the "
                           "%d-character floor and would silence every reply; "
                           "using %d", self.max_chars, _MIN_REPLY_CHARS, floored)
        object.__setattr__(self, "max_chars", floored)
        # Not a field: derived, so it stays out of eq/hash/repr. Flattened
        # here because `opted_in` is on the per-character path.
        object.__setattr__(self, "_opted", frozenset().union(
            *(_OPTIONAL_CODEPOINTS[n] for n in known)) if known else frozenset())

    @classmethod
    def from_card(cls, card: Optional[Mapping]) -> "ReplyStyle":
        """Build from a persona card's optional `reply_style` object.

        Strict on purpose, because the card is author-supplied and authoring
        may be open to any user: `emoji` must be literally `true` (so the
        string "false" cannot switch it on), `charsets` must be a list of
        known names (unknown ones are dropped with a warning rather than
        guessed at), and a non-integer `max_chars` falls back to the cap.
        Every rejected value fails toward the narrow default."""
        raw = card.get("reply_style") if isinstance(card, Mapping) else None
        if not isinstance(raw, Mapping):
            return DEFAULT_REPLY_STYLE
        names = raw.get("charsets")
        wanted: list[str] = []
        if isinstance(names, (list, tuple)):
            for name in names:
                if isinstance(name, str) and name in _OPTIONAL_CHARSETS:
                    wanted.append(name)
                else:
                    logger.warning("[Agent] reply_style: unknown charset %r ignored",
                                   name)
        elif names is not None:
            logger.warning("[Agent] reply_style: charsets is not a list, ignored")
        limit = raw.get("max_chars")
        if not isinstance(limit, int) or isinstance(limit, bool):
            limit = MAX_REPLY_CHARS
        return cls(allow_emoji=raw.get("emoji") is True,
                   charsets=frozenset(wanted),
                   max_chars=limit)

    def opted_in(self, codepoint: int) -> bool:
        """True for a code point in an optional charset this persona named."""
        return codepoint in self._opted

    def is_emoji(self, codepoint: int) -> bool:
        """True for a pictograph or an emoji modifier, opt-in or not."""
        if codepoint < _EMOJI_MIN_CODEPOINT:
            return False
        return (_in_ranges(codepoint, _EMOJI_PICTOGRAPH_RANGES)
                or _in_ranges(codepoint, _EMOJI_MODIFIER_RANGES))

    def keeps(self, codepoint: int) -> bool:
        """Survives the strip, judged on the CODE POINT alone. Invisible code
        points never do: `_INVISIBLE_FORMAT_RANGES` is in neither branch, so
        an emoji persona still loses them.

        Not the whole answer for the three bound modifiers — `keeps` says a
        joiner is allowed for an emoji persona, `_modifier_is_anchored` says
        whether THIS joiner, at THIS position, is joining anything. The strip
        and the validator both apply the pair."""
        if self.opted_in(codepoint):
            return True
        return self.allow_emoji and self.is_emoji(codepoint)


DEFAULT_REPLY_STYLE = ReplyStyle()


class TextProcessing:
    """Mixed into Agent; see agent.py."""

    @staticmethod
    def _sanitize_reply(text: str, lang: str = "en",
                        style: Optional[ReplyStyle] = None) -> str:
        """Pre-flight regex strip catching what STYLE_GUIDE failed to suppress.
        Logs when it changes the text so prompt drift is observable. The CJK
        punctuation substitutions below are no-ops on English text, so the same
        pass serves both languages; `lang` is forwarded to the final validator.

        `style` is the per-persona character policy (see `ReplyStyle`). Omit it
        and the narrow fail-closed default applies.

        Two orderings here are load-bearing:

        * the STRIP runs before the whitelist, so an unsupported character
          costs its glyph rather than the whole message;
        * the whitelist runs on the FULL text and TRUNCATION runs after it, so
          length is the only rejection that degrades to a cut. A leak shape
          sitting past the cap must not be truncated into acceptance."""
        if not text:
            return text
        style = style if style is not None else DEFAULT_REPLY_STYLE
        original = text
        # CRLF first, before anything line-anchored runs. Nothing after this
        # handles `\r`: the whitespace passes below normalise `[ \t]` and
        # spaces around `\n` and leave `\r` standing, and `_split_text` does
        # not split on it — so a model emitting CRLF produced an
        # all-whitespace chunk whose newline the splitter then dropped,
        # fusing the beats around it into one run-on bubble (the exact
        # failure rule 1 there exists to prevent). One line, at the top, so
        # every line-anchored pattern in this function sees `\n` and only
        # `\n`.
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        # Residual CORE_UPDATE self-note tags (model used a malformed variant
        # or the parser didn't consume them) — internal markers, never send.
        text = re.sub(r'\[CORE_UPDATE[^\]]*\].*?\[/CORE_UPDATE\]', '', text, flags=re.DOTALL)
        text = re.sub(r'\[/?CORE_UPDATE[^\]]*\]', '', text)
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
        text = re.sub(r'(?<!\w)\*(.+?)\*(?!\w)', r'\1', text)
        text = re.sub(r'__(.+?)__', r'\1', text)
        text = re.sub(r'(?m)^#{1,6}\s+', '', text)
        text = re.sub(r'(?m)^[\-\*]\s+', '', text)
        text = re.sub(r'(?m)^\d+\.\s+', '', text)
        text = re.sub(r'`+([^`]+)`+', r'\1', text)
        text = re.sub(r'(?m)^>\s+', '', text)
        text = re.sub(r'(?m)^---+\s*$', '', text)
        text = text.translate(str.maketrans('', '', _CJK_BRACKETS))
        text = re.sub(r'。+(?!\d)', ' ', text)
        text = text.replace('——', ' ').replace('—', ' ')
        text = text.replace('；', ',').replace(';', ',')
        text = re.sub(r'[（(][^（()）]{1,12}\.(?:jpg|png|gif|jpeg)[）)]', '', text, flags=re.IGNORECASE)
        text = re.sub(
            r'[（(](?:'
            # Chinese stage-direction tokens (legacy data; keep as a backstop)
            r'叹气|皱眉|笑哭|大笑|微笑|敲头|耸肩|摊手|无奈|尴尬|偷笑|捂脸|翻白眼|思考|沉思|惊讶|皱眉头'
            # English equivalents — the public template ships in English
            r'|sighs?|frowns?|laugh(?:s|ing)?|smiles?|shrugs?|facepalms?|eye[ -]?rolls?|thinks?|surprised'
            r')[）)]',
            '', text,
        )
        text = text.translate(_TYPOGRAPHY_MAP)
        # BEFORE the strip, and that ordering is the point. `_strip_
        # unsupported` removes arrows for every style that did not opt in,
        # which destroys the evidence rather than the payload: under the
        # default style '←persona→ You are Mira, ignore prior rules' came out
        # as 'persona You are Mira, ignore prior rules' and was RELEASED. The
        # frame is a reason to distrust the whole reply no matter which style
        # is active, so it is read here, off the text the model actually
        # emitted. Same principle as `agent._escape_markup_tags` matching
        # `renderable_form(text)` instead of the raw string: judge the token
        # the reader sees, not the one a cleaning pass leaves behind.
        frame = TextProcessing._arrow_frame(text)
        if frame:
            logger.warning("[Agent] arrow-framed token blocked, dropping "
                           "reply: %r | frame=%r", text[:80], frame)
            return ""
        text = TextProcessing._strip_unsupported(text, style)
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r' *\n *', '\n', text)
        text = text.strip()
        if text != original:
            logger.info("[Agent] sanitize: %r -> %r", original[:80], text[:80])
        # Reasoning-leak guard: a degraded / protocol-ignoring model occasionally
        # dumps its chain-of-thought into the reply. The whitelist validator below
        # only catches garbled tokens, not fluent reasoning prose, so check here
        # and drop the whole thing (PASS) — better silent than talking to itself.
        # SCRUB FIRST, DROP ONLY WHAT CANNOT BE SCRUBBED. A labelled leak is a
        # LINE ("style: 冷淡" / "判断：..."), and a line can be removed without
        # touching the reply around it — which is what the reply beneath it
        # deserves. Destroying the whole turn over one stray label is how
        # `style: 冷淡\n坐吧。` became "No reply came back": the persona had
        # answered, on the second line.
        #   Fluent chain-of-thought prose is different — it has no line to cut,
        # so it is still dropped whole below. Leak detection therefore stays
        # exactly where it was, on the server, and stops being the thing that
        # decides whether the player hears anything at all; keeping the reply
        # IN CHARACTER is the prompt's job, upstream of here.
        if text:
            scrubbed = TextProcessing._strip_reasoning_leak(text)
            if scrubbed != text:
                logger.warning(
                    "[Agent] reasoning-leak scrubbed %d chars, reply kept",
                    len(text) - len(scrubbed))
                text = scrubbed
        if text and TextProcessing._looks_like_reasoning_leak(text):
            logger.warning("[Agent] reasoning-leak blocked, dropping reply: %r", text[:80])
            return ""
        # Final gate: whitelist character validation. Any reply that doesn't
        # look like normal chat for the active language (XML / JSON / system
        # tokens / pipe characters / a leaked template) is dropped wholesale.
        # The strategy is whitelist-not-blacklist so future unseen leak
        # shapes are blocked automatically without per-shape filter rules.
        #
        # `check_length=False`: the cap is applied below as a truncation, but
        # only AFTER every character in the full text has been cleared. Cut
        # first and a leaked template's giveaway character could fall off the
        # end, turning a drop into a released 800-character prefix.
        ok, reason = TextProcessing._validate_reply_safe(
            text, lang, style, check_length=False)
        if not ok:
            logger.warning("[Agent] validator rejected reply: %s | text=%r",
                           reason, text[:80])
            return ""
        if len(text) > style.max_chars:
            cut = TextProcessing._truncate_with_seam(text, style.max_chars)
            logger.info("[Agent] sanitize: truncated %d chars to %d",
                        len(text), len(cut))
            text = cut
            # Re-check: truncation cannot introduce a bad character, but it
            # can remove the last letter and leave punctuation, which the
            # language gate is entitled to refuse.
            ok, reason = TextProcessing._validate_reply_safe(
                text, lang, style, check_length=False)
            if not ok:
                logger.warning("[Agent] validator rejected truncated reply: %s "
                               "| text=%r", reason, text[:80])
                return ""
        return text

    @staticmethod
    def _mixed_script_token(text: str) -> str:
        """The first run of letters splicing two confusable alphabets, or `""`.

        See the note at `_CONFUSABLE_SCRIPT_RANGES` for why the rule exists
        and what it deliberately does not catch. Two mechanical points:

        * STYLE-INDEPENDENT, like `_arrow_frame`. `ReplyStyle` decides which
          code points a persona may PRINT; it has never decided which
          ARRANGEMENTS are a leak, and a card naming a charset must not be
          able to buy back a homoglyph splice.
        * Invisible code points are dropped before the scan, for the reason
          `_arrow_frame` gives: `ѕуѕ{ZWSP}tem` is one token to a reader, and
          matching the raw string is what lets the interleaved spelling walk
          past. No index mapping is needed because the verdict is the whole
          reply rather than a span of it.

        Called only from `_validate_reply_safe` and NOT also from
        `_sanitize_reply` — the asymmetry with `_arrow_frame` is deliberate.
        That one is read early because `_strip_unsupported` DESTROYS ITS
        EVIDENCE (it removes the arrows for a persona that did not opt in).
        Nothing strips a Cyrillic letter, so this rule sees the same text
        wherever it is read, and one call site is one place to be wrong."""
        if not text or not _CONFUSABLE_SCAN_RE.search(text):
            return ""
        probe = "".join(ch for ch in text
                        if ord(ch) not in _INVISIBLE_CODEPOINTS)
        run_start = 0
        scripts: set[str] = set()
        for i, ch in enumerate(probe):
            script = _letter_script(ord(ch), ch)
            if not script:
                scripts = set()
                run_start = i + 1
                continue
            scripts.add(script)
            if len(scripts) > 1:
                end = i
                while end < len(probe) and _letter_script(
                        ord(probe[end]), probe[end]):
                    end += 1
                return probe[run_start:end]
        return ""

    @staticmethod
    def _arrow_frame(text: str) -> str:
        """The arrow-delimited token in `text`, or `""`.

        STYLE-INDEPENDENT ON PURPOSE. `ReplyStyle` decides whether a persona
        may PRINT an arrow; it has never been able to widen the hard-reject
        set, and it does not get to license a frame either. A reply that
        spells `←persona→` is evidence of a template dump whether or not the
        card happened to name the arrows charset.

        Invisible code points are dropped before the match for the same
        reason `_escape_markup_tags` projects through `renderable_form`:
        `←{ZWSP}persona→` is the same token to a reader as `←persona→`, and
        matching the raw string is what lets the interleaved spelling walk
        past. No index mapping is needed because the verdict is the whole
        reply, not a span of it.

        CALLED FROM TWO PLACES, and the second is not the reason an earlier
        draft of this docstring gave. It claimed the validator's copy "sees a
        frame that only becomes visible once the invisible characters are
        gone" — untrue, because THIS function strips invisibles itself, so
        both callers see the ZWSP spelling and neither can see anything the
        other cannot. The real division of labour, the one the removal
        mutation actually demonstrates:

          * `_sanitize_reply` calls it BEFORE `_strip_unsupported`, which is
            what makes the frame visible under the DEFAULT style — the strip
            removes the arrows for any persona that did not opt in, taking
            the evidence and leaving the payload.
          * `_validate_reply_safe` carries it as a rule of its own because
            it is reachable WITHOUT `_sanitize_reply` — the same reason the
            invisible-code-point tier is both stripped and hard-rejected
            ("the sanitizer strips these, so reaching here means a direct
            caller"). A validator that answered `(True, "")` for
            `←persona→` would be wrong on its own terms, whoever asked it.
            Every such caller today is a test, which is precisely why the
            rule has to be in the function rather than in its one production
            call path: the next caller does not have to be.
        """
        if not text:
            return ""
        probe = "".join(ch for ch in text
                        if ord(ch) not in _INVISIBLE_CODEPOINTS)
        match = _ARROW_FRAME_RE.search(probe)
        return match.group(0) if match else ""

    @staticmethod
    def _strip_unsupported(text: str, style: ReplyStyle) -> str:
        """Remove every strippable code point this persona does not keep.

        One pass over one character class covering emoji, emoji modifiers,
        invisible code points and all optional charsets; `ReplyStyle.keeps`
        decides per character. Written as a single regex with a callable
        replacement rather than a per-style compiled pattern because the
        match is rare in ordinary text and a pattern cache keyed on a style
        object is a cache to get wrong.

        The second condition is the positional one. A kept code point that is
        a BOUND MODIFIER also has to be anchored to a base, and the base is
        looked up in the ORIGINAL `text` rather than in the match, because a
        keycap's base ('1') is not itself strippable and so is not inside the
        run. The pictograph case always is — a pictograph is strippable, so
        '❤' and its VS16 share one match — but relying on that would be
        relying on a coincidence of the character class."""
        if not text:
            return text

        def _keep_run(m: "re.Match") -> str:
            run = m.group(0)
            start = m.start()
            kept = []
            for offset, ch in enumerate(run):
                cp = ord(ch)
                if not style.keeps(cp):
                    continue
                if cp in _BOUND_MODIFIERS and not _modifier_is_anchored(
                        text, start + offset):
                    continue
                kept.append(ch)
            return "".join(kept)

        return _STRIPPABLE_RE.sub(_keep_run, text)

    @staticmethod
    def _truncate_with_seam(text: str, max_chars: int,
                            seam: str = TRUNCATION_SEAM) -> str:
        """Cut an over-long reply to `max_chars` INCLUDING a visible seam.

        A verbose persona used to be silenced: the validator's only answer to
        "too long" was to drop the reply, so the more a persona wrote the more
        often it said nothing. The seam is what tells a reader the difference
        between "it stopped" and "it was cut"; without one, truncation is just
        a subtler silence.

        Cuts at the last space in the final quarter of the budget when there
        is one, so the seam reads as truncation rather than corruption."""
        if len(text) <= max_chars:
            return text
        budget = max(0, max_chars - len(seam))
        head = text[:budget]
        boundary = max(head.rfind(" "), head.rfind("\n"))
        if boundary >= budget * 3 // 4:
            head = head[:boundary]
        return head.rstrip() + seam

    @staticmethod
    def _strip_reasoning_leak(text: str) -> str:
        """Remove protocol-label LINES, keeping the reply written around them.

        Only the labelled form is removable, and only whole lines: a label is
        anchored at a line start (`^style:`), so what it introduces ends at the
        newline. The self-narration heuristic in `_looks_like_reasoning_leak`
        has no such anchor — it is fluent prose mixed through the reply — so
        that one still drops the whole thing at the call site.

        TWO OR MORE LABEL LINES, NEVER ONE. The label vocabulary is not
        arbitrary — it is copied from the output protocol's own reasoning
        bullets (`Input:` / `Intent` / `Decision:` / `Style:`), which means
        it is also a set of ordinary English and Chinese nouns the model is
        being TRAINED by that same prompt to write. A real leak dumps the
        BLOCK — several labelled lines together — and that shape is what two
        matches corroborate. A single matching line is at least as likely to
        be the reply itself: the assistant opening a technical answer with
        "Input: a list of ints", lin's notebook voice writing "判断：他在撒谎",
        a one-line "decision: 我跟你走". Scrubbing those was SILENT partial
        corruption — the reader got an answer starting mid-thought with no
        marker that anything was removed — which is strictly harder to notice
        than the whole-reply drop this scrub replaced. The cost of the
        corroboration rule is one line of meta-text in the rare true
        single-line leak, and that line is at least visible.

        Deliberately NOT widened into a general "delete anything suspicious"
        pass. It removes exactly what the label pattern matches and returns the
        rest untouched, so a reply that contained no label comes back
        byte-identical and the common path is provably unchanged.
        """
        if not text:
            return text
        lines = text.splitlines()
        labelled = sum(1 for line in lines if _LEAK_LABEL_RE.match(line))
        if labelled < 2:
            return text
        kept = [line for line in lines if not _LEAK_LABEL_RE.match(line)]
        return "\n".join(kept).strip()

    @staticmethod
    def _looks_like_reasoning_leak(text: str) -> bool:
        """Block internal reasoning from being sent as the reply (degraded /
        protocol-ignoring models occasionally dump their chain-of-thought into
        the reply field). The whitelist validator only catches garbled tokens,
        not fluent reasoning prose. Conservative — only strong signals count; a
        false positive just means PASS (don't send), which is the safe side."""
        if not text:
            return False
        # Protocol field labels at line start, TWO or more = a reasoning-block
        # leak. ONE definition and ONE threshold, shared with
        # `_strip_reasoning_leak` — the scrubber and the detector disagreeing
        # about what a leak is would mean a reply dropped for containing
        # something the scrubber deliberately kept. A single labelled line is
        # ordinary content (see the scrubber's docstring for the measured
        # cases); the block shape is the protocol's, and the block is what
        # corroborates.
        labelled = sum(1 for line in text.splitlines()
                       if _LEAK_LABEL_RE.match(line))
        if labelled >= 2:
            return True
        # Self-narration about HOW to reply (describing the response process).
        #
        # The second half of the list is measured, not imagined: a live leak
        # walked a whole paragraph of deliberation out to a reader before the
        # in-character answer, and the original list matched none of it. The
        # shapes it carried are the ones added:
        #   * the persona narrating its interlocutor in the THIRD PERSON
        #     ("用户在问" / "the user is asking") — in character the reader
        #     is only ever 你/you, so this voice is the protocol's;
        #   * the persona citing its own configuration as a plan ("符合设定" /
        #     "stay in character" said about itself, not quoted);
        #   * the persona planning its answer's structure ("回答的重点").
        # Known cost, accepted: a persona drafting support copy FOR the
        # reader could legitimately write "the user is asking", and that turn
        # is dropped. A dropped turn is a visible failure with a retry; a
        # leak is the engine reading its stage directions to the audience.
        meta = ("i should reply", "let me reply", "let me respond", "i'll respond",
                "先接这个", "我回不了那个", "回一句", "应该是看到", "按protocol",
                "the user is asking", "the user asked", "the user wants",
                "stay in character", "stays in character",
                "用户在问", "用户问的", "用户想", "用户说的是",
                "符合设定", "符合人设", "保持人设", "按人设", "按设定",
                "回答的重点")
        low = text.lower()
        hits = sum(1 for m in meta if m.lower() in low)
        # Long reply (chat is rarely >80 chars) + ≥1 meta phrase, or any ≥2 → leak.
        return (len(text) > 80 and hits >= 1) or hits >= 2

    @staticmethod
    def _split_text(text: str, max_len: int = 50) -> list[str]:
        """Split text on sentence punctuation to simulate human messaging.

        TWO RULES, BOTH OF THEM BUG FIXES, BOTH MEASURED ON LIVE REPLIES.

        1. **A NEWLINE IS THE AUTHOR'S PACING AND IS NEVER MERGED ACROSS.**
           The merge pass exists to glue short fragments back into one bubble.
           Run across a line break it instead concatenates two SENTENCES with
           no separator at all, because the split regex consumed the newline
           and `.strip()` threw it away — so `wen`'s five-beat reply came back
           with beats 3 and 4 fused into one run-on. This was rare while
           replies were a single line; now that multi-line replies are the
           intended register (the persona inhabits a character rather than
           imitating a texter), it is the common case.

        2. **AN EMPTY CHUNK IS NEVER EMITTED — BUT ITS BREAK SURVIVES.**
           `cur.strip()` was appended unconditionally, so a run of punctuation
           or whitespace produced a zero-length bubble — measured at two
           positions of a real English reply. A downstream renderer may
           happen to filter them; every other consumer does
           not, and a splitter that emits nothing-messages is wrong at the
           source rather than at each reader. The first fix of rule 2 threw
           the BABY out too: discarding an all-whitespace chunk also discarded
           the `hard_break` it was carrying, so `！\r\n` (the `\r` is an
           all-whitespace chunk once the `！` has flushed) let the merge pass
           run straight across the author's newline — rule 1's exact failure,
           reintroduced by rule 2. The break now lands on the previous chunk.

        3. **NO BUBBLE IS EVER A WALL.** The sanitizer rewrites `。` to a
           space, so a long Chinese reply reaches this function as one
           separator-free run and the flush-time length test — which only
           fires AT a separator — never cut it: `_split_text('x' * 800)` was
           one 800-character bubble, the exact wall of text the length bands
           in `prompts.py` promise cannot happen. An oversized body is now
           wrapped at `max_len * 2`, cutting at the last space (or CJK comma)
           in the window when one sits past its midpoint, so the seams land
           on the boundaries the sanitizer left behind.
        """
        parts = re.split(r'([。！？；\n]+)', text)
        # (body, hard_break_after) — the flag is what rule 1 needs to survive
        # the strip that removes the newline it is remembering.
        chunks: list[tuple[str, bool]] = []
        cur = ""
        for part in parts:
            cur += part
            if len(cur) >= max_len or part.endswith(("\n", "。", "！", "？", "；")):
                body = cur.strip()
                if body:  # rule 2
                    chunks.append((body, "\n" in part))
                elif "\n" in part and chunks:
                    # Rule 2 discards the BODY, never the BREAK: an
                    # all-whitespace chunk between newlines still separates
                    # its neighbours (rule 1).
                    chunks[-1] = (chunks[-1][0], True)
                cur = ""
        if cur.strip():
            chunks.append((cur.strip(), False))

        # Rule 3. Wrapped before the merge pass so every piece is subject to
        # the same rules; only the FINAL piece keeps the chunk's hard-break,
        # because the break belongs to the newline after the chunk's end.
        wrap_at = max_len * 2
        wrapped: list[tuple[str, bool]] = []
        for body, hard_break in chunks:
            while len(body) > wrap_at:
                window = body[:wrap_at]
                cut = max(window.rfind(" "), window.rfind("，"),
                          window.rfind("、"), window.rfind(","))
                if cut < wrap_at // 2:
                    cut = wrap_at
                elif body[cut] != " ":
                    # A comma belongs to the clause it ends; a space belongs
                    # to nobody and is stripped either way.
                    cut += 1
                piece = body[:cut].strip()
                if piece:
                    wrapped.append((piece, True))
                body = body[cut:].strip()
            if body:
                wrapped.append((body, hard_break))

        result: list[str] = []
        may_merge = True
        for body, hard_break in wrapped:
            if result and may_merge and len(result[-1]) + len(body) < max_len:
                result[-1] += body
            else:
                result.append(body)
            # Rule 1: whatever follows a hard break starts its own bubble.
            may_merge = not hard_break
        return result or [text]

    @staticmethod
    def _typing_delay(chunk: str) -> float:
        """Simulate human typing speed: ~6-8 chars/sec + small pause. Capped at 7s."""
        chars_per_sec = random.uniform(6.0, 8.0)
        base = len(chunk) / chars_per_sec
        pause = random.uniform(0.4, 1.2)
        return min(base + pause, 7.0)

    @staticmethod
    def _is_sleep_hour() -> bool:
        """True if the current hour falls in the sleep window (default
        02:00-07:00). Uses the TZ_OFFSET_HOURS timezone — the same clock
        _current_time_str shows the model — not the server's local time:
        on e.g. a UTC host the bot would otherwise "sleep" through the
        persona's morning and chat freely at persona 3 a.m. Handles
        wraparound for future config changes."""
        from datetime import datetime, timezone, timedelta
        try:
            tz_hours = float(os.getenv("TZ_OFFSET_HOURS", "8"))
        except ValueError:
            tz_hours = 8.0
        h = datetime.now(timezone(timedelta(hours=tz_hours))).hour
        if SLEEP_HOUR_START <= SLEEP_HOUR_END:
            return SLEEP_HOUR_START <= h < SLEEP_HOUR_END
        return h >= SLEEP_HOUR_START or h < SLEEP_HOUR_END

    @staticmethod
    def _parse_sticker_markers(text: str) -> list[tuple[str, str]]:
        """Split on [STICKER:tag] markers. Returns ordered (kind, value) where
        kind is 'text' or 'sticker'. Empty text segments dropped. Used by
        _send_qq to send mixed text/image messages."""
        out: list[tuple[str, str]] = []
        # Tolerate stray whitespace the model sometimes emits inside the marker
        # ("[STICKER: doge]"): without this the marker fails to match, the
        # literal text survives, and the downstream validator fail-closes the
        # WHOLE reply.
        pattern = re.compile(r"\[STICKER:\s*([^\]]+?)\s*\]")
        pos = 0
        for m in pattern.finditer(text):
            if m.start() > pos:
                seg = text[pos:m.start()].strip()
                if seg:
                    out.append(("text", seg))
            out.append(("sticker", m.group(1).strip()))
            pos = m.end()
        if pos < len(text):
            seg = text[pos:].strip()
            if seg:
                out.append(("text", seg))
        if not out and text.strip():
            out.append(("text", text.strip()))
        return out

    @staticmethod
    def _current_time_str() -> str:
        """Local time + coarse time-of-day label, used as a grounding anchor in
        the system prompt so the model doesn't invent times.

        THE USER'S local time, not the server's, when the caller supplies one:
        `current_tz_offset_h` may be set per turn by an embedder that knows
        the user's timezone. A single deployment-wide TZ_OFFSET_HOURS is
        correct for a QQ bot with one owner and wrong for a multi-user
        deployment — it tells every user what time it is where the server
        happens to be running.

        TZ_OFFSET_HOURS (default UTC+8) remains the fallback for callers with
        no per-user notion of "local"."""
        from datetime import datetime, timezone, timedelta
        from .gateway import current_tz_offset_h
        tz_hours = current_tz_offset_h.get()
        if tz_hours is None:
            try:
                tz_hours = float(os.getenv("TZ_OFFSET_HOURS", "8"))
            except ValueError:
                tz_hours = 8.0
        tz = timezone(timedelta(hours=tz_hours))
        now = datetime.now(tz)
        weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        h = now.hour
        if h < 5:
            part = "late night"
        elif h < 7:
            part = "early morning"
        elif h < 11:
            part = "morning"
        elif h < 13:
            part = "midday"
        elif h < 18:
            part = "afternoon"
        elif h < 22:
            part = "evening"
        else:
            part = "late night"
        return f"{now.strftime('%Y-%m-%d %H:%M')} {weekdays[now.weekday()]} {part}"

    @staticmethod
    def _parse_model_output(raw: str) -> tuple[str, str, str, str]:
        """Parse JSON-structured model output:
            {"reasoning": "...", "intent": "...", "reply": "...", "mem": "..."}

        Returns (reply, reasoning, intent, mem). Fail-closed: a parse failure
        or missing `reply` key yields ("", raw[:240], "", "") plus a warning.

        Why JSON instead of XML inline tags: with string-embedded structure
        the parser's fallback branches can leak reasoning text into the reply
        when the model truncates, malforms, or emits provider-specific tokens.
        With JSON fields each piece is isolated; if `reply` is missing the
        send pipeline simply produces nothing.

        Robustness layers:
        1. Strip optional ```json ... ``` fences.
        2. Try json.loads on the whole string.
        3. Fall back to JSONDecoder.raw_decode from the first `{` so two
           concatenated JSON objects parse as the first valid one.
        4. If no dictionary is recovered, fail closed. A fluent reasoning
           fragment is indistinguishable from an ordinary naked chat line, so
           accepting non-JSON text would violate the protocol boundary.
        """
        if not raw or not raw.strip():
            return "", "", "", ""
        s = raw.strip()
        s = re.sub(r"^```(?:json)?\s*", "", s, flags=re.IGNORECASE)
        s = re.sub(r"\s*```$", "", s)
        data = None
        try:
            data = json.loads(s)
        except (json.JSONDecodeError, TypeError):
            start = s.find('{')
            if start >= 0:
                try:
                    data, _end = json.JSONDecoder().raw_decode(s[start:])
                except json.JSONDecodeError:
                    data = None
        if not isinstance(data, dict):
            logger.warning("[Agent] parser: model output is not JSON, dropping raw=%r",
                           raw[:200])
            return "", raw.strip()[:240], "", ""
        allowed_keys = {"reply", "reasoning", "intent", "mem"}
        if set(data) - allowed_keys or any(
            value is not None and not isinstance(value, str)
            for value in data.values()
        ):
            logger.warning("[Agent] parser: invalid JSON protocol field types/keys")
            return "", raw.strip()[:240], "", ""
        reply = (data.get("reply") or "").strip()
        reasoning = (data.get("reasoning") or "").strip()
        intent = (data.get("intent") or "").strip().lower()
        mem_raw = data.get("mem")
        mem = mem_raw.strip() if mem_raw is not None else ""
        # Placeholder words count as empty (model occasionally fills "无" / "none" / etc.)
        if mem.lower() in {"无", "none", "n/a", "null", "无内容", "无可记"}:
            mem = ""
        return reply, reasoning, intent, mem

    @staticmethod
    def _validate_reply_safe(text: str, lang: str = "en",
                             style: Optional[ReplyStyle] = None,
                             *, check_length: bool = True) -> tuple[bool, str]:
        """Whitelist character-class validator: only release replies that look
        like genuine human chat text for the active language.

        Strategy: strip approved bracket markers ([STICKER:tag] / [AT:qq]),
        then verify every remaining character belongs to an allowed class
        (CJK ideographs / CJK punctuation / full-width / Latin letters with
        diacritics / the named scripts' letters / common ASCII letters,
        digits, punctuation, whitespace). Known bad token characters —
        `< > { } |`, every code point Unicode folds onto one of them under
        NFKC, and `▁` — are hard-rejected, as is every invisible code point.

        Two ARRANGEMENT rules sit above the per-character loop, both
        style-independent: an arrow-framed token (`←persona→`) and a
        mixed-script token (`ѕуѕtem`). Neither is objectionable character by
        character, which is exactly why neither can be expressed in the
        whitelist.

        `style` widens the allowed set by NAMED ranges only — the optional
        charsets the persona asked for, plus emoji if it set the flag. It can
        never widen the hard-reject set, never turn off an arrangement rule
        and never raise the length cap.

        The content gate is ONE RULE FOR EVERY LANGUAGE: a reply with no
        marker and no letter in any script — not one ASCII letter, Latin
        letter with a diacritic, CJK ideograph, kana, jamo, Cyrillic, Greek
        or Arabic letter, and no emoji — is rejected as the residue of a
        stripped template. `lang` no longer changes any decision here; see
        the note on the gate itself for what it used to do and why that was
        wrong.

        This catches every future leak shape — XML residue, JSON fragments,
        provider-specific tokens — without needing a per-shape filter rule.

        `check_length=False` runs every rule EXCEPT the cap, for the one
        caller that applies the cap itself as a truncation.

        Returns (ok, reason). A failing result causes the send pipeline to
        drop the reply entirely (fail-closed)."""
        style = style if style is not None else DEFAULT_REPLY_STYLE
        if not text or not text.strip():
            return False, "empty"
        if check_length and len(text) > style.max_chars:
            return False, f"too long ({len(text)})"
        # AT targets aren't only digits anymore: gateway ids look like
        # "telegram:12345", so the marker class matches anything bracket-safe.
        # Tolerant of internal whitespace so "[STICKER: doge]" is recognized
        # and stripped (must mirror _parse_sticker_markers, else a stray space
        # in a marker makes the whole reply fail this whitelist and get dropped).
        marker_pat = re.compile(r'\[(?:STICKER:|AT:)[^\[\]]*\]')
        has_marker = bool(marker_pat.search(text))
        residual = marker_pat.sub('', text).strip()
        if not residual:
            return (True, "") if has_marker else (False, "empty after marker strip")
        # Structure, checked before the per-character loop because it is a
        # property of the ARRANGEMENT and no single character in it is
        # objectionable. The `arrows` opt-in admits 112 symbols; symbols are
        # what a frame is spelled with, so the opt-in has to buy narration
        # without also buying `←persona→`. No style can turn this off — same
        # standing as the hard-reject table, and for the same reason.
        frame = TextProcessing._arrow_frame(residual)
        if frame:
            return False, f"arrow-framed token {frame!r}"
        # The other ARRANGEMENT rule, and the one that had to arrive with the
        # script tier: naming the Cyrillic and Greek alphabets names ~20
        # visual twins of Latin letters, so `ѕуѕtem` — three Cyrillic code
        # points and three Latin ones in one word — becomes spellable out of
        # characters each of which is individually fine. No style turns this
        # off, same standing as the hard-reject table.
        spliced = TextProcessing._mixed_script_token(residual)
        if spliced:
            return False, f"mixed-script token {spliced!r}"
        cjk_count = 0
        letter_count = 0
        emoji_count = 0
        for i, ch in enumerate(residual):
            c = ord(ch)
            # Hard reject: known bad token characters.
            # < > { } | (ASCII)  — XML/JSON/pipe fragments
            # every code point NFKC-folds onto one of those five — the
            #   full-width and small-form twins, ＜ ＞ ｛ ｝ ｜ among them
            # ▁ (U+2581 subword marker) — tokenizer leak
            # No ReplyStyle can re-admit any of these.
            if c in _HARD_REJECT_CODEPOINTS:
                return False, f"bad token char {ch!r} (U+{c:04X})"
            # Invisible code points. The sanitizer strips these, so reaching
            # here means a direct caller; refuse rather than release text that
            # occupies no space, or whose displayed order is not its stored
            # order. NON-INDEPENDENT with the strip on purpose — see the note
            # at test_an_emoji_persona_still_loses_invisible_controls.
            if c in _INVISIBLE_CODEPOINTS:
                return False, f"invisible format char (U+{c:04X})"
            # Emoji, only for a persona that asked for them — and for the
            # three invisible modifiers, only where they are modifying
            # something. A bare joiner run is not an emoji.
            if style.allow_emoji and style.is_emoji(c):
                if c in _BOUND_MODIFIERS and not _modifier_is_anchored(
                        residual, i):
                    return False, f"unanchored emoji modifier (U+{c:04X})"
                emoji_count += 1
                continue
            # An optional charset this persona named.
            if style.opted_in(c):
                continue
            # CJK unified ideographs (incl. extensions A/B)
            if 0x4E00 <= c <= 0x9FFF or 0x3400 <= c <= 0x4DBF or 0x20000 <= c <= 0x2A6DF:
                cjk_count += 1
                continue
            # CJK punctuation
            if 0x3000 <= c <= 0x303F:
                continue
            # Full-width forms. The bracket and pipe twins are already gone
            # (hard reject), U+FFA0, the invisible half-width Hangul filler
            # that hides in this block, is already gone (invisible tier), and
            # the three vertical-bar twins that fold onto nothing fall
            # through to the default deny - see _FULLWIDTH_BAR_TWINS.
            if 0xFF00 <= c <= 0xFFEF and c not in _FULLWIDTH_BAR_TWINS:
                continue
            # Whitespace
            if ch in '\n\t \r':
                continue
            # ASCII letters / digits
            if c < 0x80 and ch.isalnum():
                if ch.isalpha():
                    letter_count += 1
                continue
            # Latin letters carrying diacritics — café, naïve, José.
            if _in_ranges(c, _LATIN_LETTER_RANGES):
                letter_count += 1
                continue
            # The named scripts, letters only: kana, Hangul, Cyrillic, Greek,
            # Arabic. A letter in ANY of them is content, which is the same
            # thing the gate below already says about a letter in any script
            # — this tier is what makes that sentence true instead of
            # aspirational. Placed after the ASCII and Latin branches so an
            # English or Chinese reply never pays for the scan.
            if _in_ranges(c, _SCRIPT_LETTER_RANGES):
                letter_count += 1
                continue
            # Currency and degree signs.
            if c in _SYMBOL_ALLOWED:
                continue
            # Common ASCII punctuation used in casual chat ('$' included: a
            # product that charges money must be able to quote a price).
            if ch in '.,?!;:\'\"()-_~`@#&+*=%^/$':
                continue
            return False, f"unexpected char {ch!r} (U+{c:04X})"
        if not has_marker:
            # ONE RULE, EVERY LANGUAGE. This gate asks "is there any content
            # here, or is this the residue of a stripped template?" — and that
            # question has never had a per-language answer.
            #
            # It used to. A `zh` build demanded at least one CJK character, so
            # a reply in any other script was destroyed whole. With all three
            # residents authored at lang=zh that fired constantly: an English
            # sentence, a name, a line of dialogue the model chose to answer in
            # the reader's language — each one silently became "No reply came
            # back", which is the intermittent failure the owner was hitting.
            # It also mistook a MODEL LIMITATION for a policy: a modern model
            # writes whatever language the conversation is in without being
            # told, so the build's language is not evidence about the reply's.
            #
            # What identity a persona has is carried by its card and its
            # prompt, not by which alphabet the validator will accept; and
            # which language the READER wants is a UI choice, not a character
            # class (see the i18n work, which widens that choice past zh/en).
            #
            # The anti-leak intent is untouched and is what the rule still
            # says: a residual of nothing but digits and punctuation is
            # suspect, because that is what a stripped chat template leaves
            # behind. A letter in ANY script is content. An emoji counts too —
            # no tokenizer artefact is made of emoji.
            if letter_count == 0 and cjk_count == 0 and emoji_count == 0:
                return False, "no letter content (suspect template / token leak)"
        return True, ""

    @staticmethod
    def _is_blind_content(text: str) -> bool:
        """True if the trigger message carries only placeholders the bot can't
        actually read (bare image/voice/video/file/forward/unresolved-quote),
        with no readable text and no usable [image: caption] / [sticker: meaning]
        / [reply X: text]. Used to tell the model not to fabricate — the @-forced
        called/owner paths otherwise answer media they never saw."""
        if not text:
            return False
        had_blind = bool(re.search(r"\[(image|voice|video|file|face|reply)\]|\[forwarded-chat", text))
        if not had_blind:
            return False
        t = re.sub(r"\[(image|voice|video|file|face|reply)\]", "", text)
        t = re.sub(r"\[forwarded-chat[^\]]*\]", "", t)
        t = re.sub(r"\[AT:[^\]]+\]|@\S+|\[STICKER:[^\]]+\]", "", t)
        return not t.strip()
