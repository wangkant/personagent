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
from datetime import datetime
from pathlib import Path
from typing import Awaitable, Callable, Optional
from urllib.parse import urlencode, urlsplit

import httpx

logger = logging.getLogger("agent")


# Sentinels wrapping web-derived enrichment (URL og:title/desc) inside the
# extracted text. Control decisions (is_called / memory commands) run on a
# view with these spans removed, so third-party page content can't trigger
# them; the prompt/buffer view keeps the enrichment (sentinels stripped).
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


class TextProcessing:
    """Mixed into Agent; see agent.py."""

    @staticmethod
    def _sanitize_reply(text: str, lang: str = "en") -> str:
        """Pre-flight regex strip catching what STYLE_GUIDE failed to suppress.
        Logs when it changes the text so prompt drift is observable. The CJK
        punctuation substitutions below are no-ops on English text, so the same
        pass serves both languages; `lang` is forwarded to the final validator."""
        if not text:
            return text
        original = text
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
        text = text.translate(str.maketrans('', '', '「」『』《》【】'))
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
        text = re.sub(
            r'['
            r'\U0001F300-\U0001F5FF'
            r'\U0001F600-\U0001F64F'
            r'\U0001F680-\U0001F6FF'
            r'\U0001F700-\U0001F77F'
            r'\U0001F780-\U0001F7FF'
            r'\U0001F900-\U0001F9FF'
            r'\U0001FA00-\U0001FA6F'
            r'\U0001FA70-\U0001FAFF'
            r'\U00002600-\U000026FF'
            r'\U00002700-\U000027BF'
            r']+',
            '', text,
        )
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r' *\n *', '\n', text)
        text = text.strip()
        if text != original:
            logger.info("[Agent] sanitize: %r -> %r", original[:80], text[:80])
        # Reasoning-leak guard: a degraded / protocol-ignoring model occasionally
        # dumps its chain-of-thought into the reply. The whitelist validator below
        # only catches garbled tokens, not fluent reasoning prose, so check here
        # and drop the whole thing (PASS) — better silent than talking to itself.
        if text and TextProcessing._looks_like_reasoning_leak(text):
            logger.warning("[Agent] reasoning-leak blocked, dropping reply: %r", text[:80])
            return ""
        # Final gate: whitelist character validation. Any reply that doesn't
        # look like normal chat for the active language (XML / JSON / system
        # tokens / pipe characters / a leaked template) is dropped wholesale.
        # The strategy is whitelist-not-blacklist so future unseen leak
        # shapes are blocked automatically without per-shape filter rules.
        ok, reason = TextProcessing._validate_reply_safe(text, lang)
        if not ok:
            logger.warning("[Agent] validator rejected reply: %s | text=%r",
                           reason, text[:80])
            return ""
        return text

    @staticmethod
    def _looks_like_reasoning_leak(text: str) -> bool:
        """Block internal reasoning from being sent as the reply (degraded /
        protocol-ignoring models occasionally dump their chain-of-thought into
        the reply field). The whitelist validator only catches garbled tokens,
        not fluent reasoning prose. Conservative — only strong signals count; a
        false positive just means PASS (don't send), which is the safe side."""
        if not text:
            return False
        # Protocol field labels at line start = almost certainly a reasoning leak
        # (a real reply never opens with "Decision:" / "Speaker:" / "决策:").
        if re.search(r"(?im)^[\s\-•*]*(input|speaker|intent|decision|style|"
                     r"输入|发言人|意图|决策|风格|分析|判断)\s*[:：]", text):
            return True
        # Self-narration about HOW to reply (describing the response process).
        meta = ("i should reply", "let me reply", "let me respond", "i'll respond",
                "先接这个", "我回不了那个", "回一句", "应该是看到", "按protocol")
        low = text.lower()
        hits = sum(1 for m in meta if m.lower() in low)
        # Long reply (chat is rarely >80 chars) + ≥1 meta phrase, or any ≥2 → leak.
        return (len(text) > 80 and hits >= 1) or hits >= 2

    @staticmethod
    def _split_text(text: str, max_len: int = 50) -> list[str]:
        """Split text on sentence punctuation to simulate human messaging."""
        parts = re.split(r'([。！？；\n]+)', text)
        chunks: list[str] = []
        cur = ""
        for part in parts:
            cur += part
            if len(cur) >= max_len or part.endswith(("\n", "。", "！", "？", "；")):
                chunks.append(cur.strip())
                cur = ""
        if cur.strip():
            chunks.append(cur.strip())

        result: list[str] = []
        for c in chunks:
            if result and len(result[-1]) + len(c) < max_len:
                result[-1] += c
            else:
                result.append(c)
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
        the system prompt so the model doesn't invent times. Reads TZ_OFFSET_HOURS
        from env (defaults to UTC+8 for backward compatibility); set this to
        your deployment's timezone."""
        from datetime import datetime, timezone, timedelta
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
        4. If still no dict, last-ditch chat-shape heuristic: short chat text
           (English or CJK) without XML/JSON/pipe characters and not a
           reasoning-style prefix is treated as a naked reply. The downstream
           whitelist validator (_validate_reply_safe) is the final gate.
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
            # Naked-text rescue: occasionally a model just emits the reply text
            # directly without the JSON wrapper. If it looks like a normal
            # short chat line (English OR CJK), ship it and let the validator gate.
            cleaned = raw.strip()[:300]
            has_letters = any(c.isalpha() for c in cleaned)
            looks_like_reply = (
                3 <= len(cleaned) <= 200
                and has_letters
                and not re.search(r'[<>{}|｜▁]', cleaned)
                # Reasoning-channel prefixes that occasionally leak through —
                # match both English and Chinese forms so neither locale can
                # smuggle reasoning into the reply field.
                and not re.match(
                    r'^[\s\-•]*('
                    r'input|speaker|intent|decision|style|analysis|judgment|'
                    r'thinking|scenario|reply strategy|context|background|mode'
                    r'|输入|发言人|意图|决策|风格|分析|判断|思考|场景|回复策略|上下文|背景|模式'
                    r')[:：]',
                    cleaned, re.IGNORECASE,
                )
            )
            if looks_like_reply:
                logger.warning("[Agent] parser: non-JSON but raw looks like a valid reply, passing through: %r",
                               cleaned[:80])
                return cleaned, "", "", ""
            logger.warning("[Agent] parser: model output is not JSON, dropping raw=%r",
                           raw[:200])
            return "", raw.strip()[:240], "", ""
        reply = str(data.get("reply") or "").strip()
        reasoning = str(data.get("reasoning") or "").strip()
        intent = str(data.get("intent") or "").strip().lower()
        mem_raw = data.get("mem")
        mem = str(mem_raw).strip() if mem_raw is not None else ""
        # Placeholder words count as empty (model occasionally fills "无" / "none" / etc.)
        if mem.lower() in {"无", "none", "n/a", "null", "无内容", "无可记"}:
            mem = ""
        return reply, reasoning, intent, mem

    @staticmethod
    def _validate_reply_safe(text: str, lang: str = "en") -> tuple[bool, str]:
        """Whitelist character-class validator: only release replies that look
        like genuine human chat text for the active language.

        Strategy: strip approved bracket markers ([STICKER:tag] / [AT:qq]),
        then verify every remaining character belongs to an allowed class
        (CJK ideographs / CJK punctuation / full-width / common ASCII letters,
        digits, punctuation, whitespace). Known bad token characters
        (`< > { } | ｜ ▁`) are hard-rejected.

        Language gate (the only language-dependent rule):
          - zh: a reply with no CJK and no marker is rejected (a Chinese bot
            emitting pure ASCII is a suspected template / token leak).
          - en (default) and any other lang: a reply with no letter at all
            (no ASCII letter and no CJK) and no marker is rejected. Mixed
            zh/en code-switching always passes since the CJK classes stay
            allowed.

        This catches every future leak shape — XML residue, JSON fragments,
        provider-specific tokens — without needing a per-shape filter rule.

        Returns (ok, reason). A failing result causes the send pipeline to
        drop the reply entirely (fail-closed)."""
        if not text or not text.strip():
            return False, "empty"
        if len(text) > 500:
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
        cjk_count = 0
        letter_count = 0
        for ch in residual:
            c = ord(ch)
            # Hard reject: known bad token characters
            # < > { } | (ASCII)  — XML/JSON/pipe fragments
            # ｜ (U+FF5C full-width pipe) — provider internal separators
            # ▁ (U+2581 subword marker) — tokenizer leak
            if ch in '<>{}|' or c == 0xFF5C or c == 0x2581:
                return False, f"bad token char {ch!r} (U+{c:04X})"
            # CJK unified ideographs (incl. extensions A/B)
            if 0x4E00 <= c <= 0x9FFF or 0x3400 <= c <= 0x4DBF or 0x20000 <= c <= 0x2A6DF:
                cjk_count += 1
                continue
            # CJK punctuation
            if 0x3000 <= c <= 0x303F:
                continue
            # Full-width forms (｜ already rejected above)
            if 0xFF00 <= c <= 0xFFEF:
                continue
            # Whitespace
            if ch in '\n\t \r':
                continue
            # ASCII letters / digits
            if c < 0x80 and ch.isalnum():
                if ch.isalpha():
                    letter_count += 1
                continue
            # Common ASCII punctuation used in casual chat
            if ch in '.,?!;:\'\"()-_~`@#&+*=%^/':
                continue
            return False, f"unexpected char {ch!r} (U+{c:04X})"
        if not has_marker:
            if lang == "zh":
                # Chinese build: no CJK → suspected template / token leak.
                if cjk_count == 0:
                    return False, "no CJK content (suspect template / token leak)"
            else:
                # English (default) build: needs at least one letter (ASCII or
                # CJK); a residual of only digits/punctuation is suspect.
                if letter_count == 0 and cjk_count == 0:
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
