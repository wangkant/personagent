"""What each AstrBot adapter can and cannot do, read from AstrBot 4.25.5.

Everything here is plain data or a pure function over an adapter's raw
message object, so it can be tested without AstrBot. main.py applies it.
Raw objects differ per adapter and between AstrBot versions, so every read
goes through _get and tolerates a missing field.
"""
from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Rules:
    """How one adapter renders what the plugin sends."""

    # context.send_message reaches a conversation with no incoming message.
    outbox: bool = False
    # How a reply names someone: "at" (At component, then a space),
    # "at_spaced" (the adapter adds the space), "telegram", "slack", "kook",
    # "name" (At with a username the plugin has seen), or "none".
    mention: str = "at"
    # A Reply component makes the adapter quote the message.
    quote: bool = False
    # Longest text one message may carry, as the platform counts it: the
    # mention and the escapes included. 0 is no limit.
    max_chars: int = 0
    max_bytes: int = 0
    # Characters the adapter may put in front of a message on its own.
    reserve: int = 0
    # Text escaping the adapter's renderer needs to show the text as typed.
    escape: str = ""
    # The escapes count toward max_chars (not so for markup the platform
    # parses away).
    escape_counts: bool = True
    # The adapter delivers one message per turn: send the turn as one.
    merge: bool = False
    # The adapter sends up to this many components as one API call.
    batch: int = 0
    # Ask for plain text instead of the adapter's default markdown.
    plain_text: bool = False


RULES: dict[str, Rules] = {
    # Long texts become a merged-forward card above forward_threshold; main.py
    # reads that limit from AstrBot's config.
    "aiocqhttp": Rules(outbox=True, mention="at_spaced", quote=True),
    # Telegram counts the text its markdown shows, so the escapes are free;
    # the adapter splits at 4096 counting them, and 2000 keeps a chunk whole.
    "telegram": Rules(outbox=True, mention="telegram", quote=True,
                      max_chars=2000, escape="telegram", escape_counts=False),
    # The adapter cuts at 2000.
    "discord": Rules(outbox=True, mention="at", quote=True,
                     max_chars=2000, escape="discord"),
    # Slack refuses a section over 3000.
    "slack": Rules(outbox=True, mention="slack", max_chars=3000, escape="slack"),
    "mattermost": Rules(outbox=True, mention="name", max_chars=4000, escape="mattermost"),
    # The adapter cuts at 3000, after starting a message without a mention
    # with "@<username>\n" (Misskey usernames run to 128 characters).
    "misskey": Rules(outbox=True, mention="name", max_chars=3000, reserve=130,
                     escape="misskey"),
    "kook": Rules(outbox=True, mention="kook", quote=True,
                  max_chars=4000, escape="kook"),
    "lark": Rules(outbox=True, mention="at"),
    "dingtalk": Rules(outbox=True, mention="none"),
    "line": Rules(outbox=True, mention="none", max_chars=5000, batch=5),
    "satori": Rules(outbox=True, mention="at"),
    "webchat": Rules(outbox=True, mention="none"),
    # App mode only; main.py refuses customer-service (KF) mode.
    "wecom": Rules(outbox=True, mention="none", max_bytes=2048),
    "weixin_oc": Rules(outbox=True, mention="none", max_chars=2000),
    # Replies only inside a 5-minute passive window.
    "qq_official": Rules(mention="none", max_chars=2000, plain_text=True),
    "qq_official_webhook": Rules(mention="none", max_chars=2000, plain_text=True),
    # One streamed answer per message, finished by its first send.
    "wecom_ai_bot": Rules(mention="none", merge=True),
    # Passive mode keeps only the last send of a turn.
    "weixin_official_account": Rules(mention="none", merge=True),
}

# An adapter this table does not know: mention as AstrBot does, and never
# claim it can speak first.
DEFAULT_RULES = Rules()


def rules_for(platform: str) -> Rules:
    return RULES.get(platform, DEFAULT_RULES)


def _get(obj, *path):
    """obj[a][b]... or obj.a.b..., None as soon as a step is missing."""
    for key in path:
        if obj is None:
            return None
        if isinstance(obj, dict):
            obj = obj.get(key)
        else:
            try:
                obj = getattr(obj, key, None)
            except Exception:
                return None
    return obj


# ---------- timestamps ----------

def _iso_seconds(value) -> int | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp())
    except ValueError:
        return None


def _datetime_seconds(value) -> int | None:
    try:
        return int(value.timestamp())
    except Exception:
        return None


def source_timestamp(platform: str, raw) -> int | None:
    """When the platform stamped the message, where the adapter left it as
    the time AstrBot received it (aiocqhttp, telegram, discord, kook, QQ
    official, misskey, WeCom customer service)."""
    if raw is None:
        return None
    ts = None
    if platform == "aiocqhttp":
        ts = _get(raw, "time")
    elif platform == "telegram":
        ts = _datetime_seconds(_get(raw, "message", "date"))
    elif platform == "discord":
        ts = _datetime_seconds(_get(raw, "created_at"))
    elif platform == "kook":
        ms = _get(raw, "msg_timestamp")
        ts = ms // 1000 if isinstance(ms, int) else None
    elif platform in ("qq_official", "qq_official_webhook"):
        ts = _iso_seconds(_get(raw, "timestamp"))
    elif platform == "misskey":
        ts = _iso_seconds(_get(raw, "createdAt"))
    elif platform == "wecom" and isinstance(raw, dict):
        ts = raw.get("send_time")
    try:
        ts = int(ts) if ts is not None else None
    except (TypeError, ValueError, OverflowError):
        return None
    return ts if ts and ts > 0 else None


def seconds(ts: int) -> int:
    """Satori and some bridges stamp in milliseconds."""
    return ts // 1000 if ts > 10**11 else ts


# ---------- ids ----------

def native_message_id(platform: str, raw) -> str | None:
    """The platform's own message id where the adapter mints a random one."""
    if platform == "slack":
        ts = _get(raw, "ts")
        return str(ts) if ts else None
    if platform == "wecom_ai_bot":
        mid = _get(raw, "message_data", "msgid")
        return str(mid) if mid else None
    return None


# ---------- text: inbound ----------

_KOOK_EMOJI = re.compile(r"\(emj\)(.*?)\(emj\)\[([^\]]*)\]")
_KOOK_CHANNEL = re.compile(r"\(chn\)(\d+)\(chn\)")
_KOOK_WRAP = re.compile(r"\((spl|ins|del|u)\)(.*?)\(\1\)", re.S)
_KOOK_ESCAPE = re.compile(r"\\([\\*~\[\]()>\-_`:])")


def kook_segments(text: str) -> list[dict]:
    """KOOK Plain text is the KMarkdown source: turn (emj) tags into emoji
    segments and unwrap the rest, so the agent reads what people see."""
    text = _KOOK_WRAP.sub(lambda m: m.group(2), text)
    text = _KOOK_CHANNEL.sub("#channel", text)
    out: list[dict] = []
    pos = 0
    for m in _KOOK_EMOJI.finditer(text):
        before = _KOOK_ESCAPE.sub(r"\1", text[pos:m.start()])
        if before:
            out.append({"type": "text", "text": before})
        out.append({"type": "emoji", "name": m.group(1), "id": m.group(2)})
        pos = m.end()
    tail = _KOOK_ESCAPE.sub(r"\1", text[pos:])
    if tail or not out:
        out.append({"type": "text", "text": tail})
    return out


# Long-connection WeCom smart bots turn media into these texts.
WECOM_AI_PLACEHOLDERS = {
    "[voice消息]": "(sent a voice message)",
    "[video消息]": "(sent a video)",
    "[file消息]": "(sent a file)",
    "[image消息]": "(sent an image)",
}

# LINE writes "[<type>]" when it cannot fetch a message's content.
LINE_PLACEHOLDERS = {
    "audio": "(sent a voice message)",
    "video": "(sent a video)",
    "file": "(sent a file)",
    "image": "(sent an image)",
}


def media_note(mime: str) -> str | None:
    """Voice and video that an adapter hands over as a generic File."""
    mime = (mime or "").lower()
    if mime.startswith("audio/"):
        return "(sent a voice message)"
    if mime.startswith("video/"):
        return "(sent a video)"
    return None


# ---------- text: outbound ----------

_TELEGRAM_SPECIAL = re.compile(r"([\\`*_{}\[\]()#+\-.!|~<>=])")
_ZWSP = "\u200b"


def escape(text: str, kind: str) -> str:
    """Make the adapter's renderer show the text as typed.

    telegram: the adapter runs every Plain through a Markdown converter, so
      '*sighs*' turned italic and '2*3*4' lost its stars; a backslash keeps
      each one literal.
    slack: '&', '<' and '>' are mrkdwn control characters ('<!channel>').
    kook: KMarkdown tags like (met)all(met) would ping or render.
    discord/mattermost/misskey: keep channel-wide or federated pings inert.
    """
    if not text or not kind:
        return text
    if kind == "telegram":
        return _TELEGRAM_SPECIAL.sub(r"\\\1", text)
    if kind == "slack":
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    if kind == "kook":
        return re.sub(r"\((met|rol|chn|emj|spl|ins|del|u)\)", r"\\(\1\\)", text)
    if kind == "discord":
        return re.sub(r"@(everyone|here)\b", "@" + _ZWSP + r"\1", text)
    if kind == "mattermost":
        return re.sub(r"@(channel|all|here)\b", "@" + _ZWSP + r"\1", text, flags=re.I)
    if kind == "misskey":
        return re.sub(r"@(?=\w)", "@" + _ZWSP, text)
    return text


_SPLIT_AT = (re.compile(r"\n\s*\n"), re.compile(r"\n"),
             re.compile(r"(?<=[.!?。！？…])\s*"), re.compile(r"\s+"))


def split_text(text: str, max_chars: int = 0, max_bytes: int = 0,
               kind: str = "", reserve: int = 0) -> list[str]:
    """Cut text into pieces that fit one message once escaped for `kind`,
    with `reserve` to spare, preferring paragraph, line, sentence and word
    boundaries over a hard cut. The pieces come back unescaped."""
    def size(s: str) -> int:
        s = escape(s, kind)
        return len(s.encode("utf-8")) if max_bytes else len(s)

    if not text:
        return []
    limit = max_bytes or max_chars
    if limit:
        limit = max(1, limit - reserve)
    if not limit or size(text) <= limit:
        return [text]
    out: list[str] = []
    rest = text
    while size(rest) > limit:
        lo, hi = 1, len(rest)  # the longest prefix that fits
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if size(rest[:mid]) <= limit:
                lo = mid
            else:
                hi = mid - 1
        cut = lo
        window = rest[:lo]
        for pattern in _SPLIT_AT:
            ends = [m.end() for m in pattern.finditer(window) if m.start() > 0]
            if ends and ends[-1] >= lo // 3:
                cut = ends[-1]
                break
        piece = rest[:cut].rstrip()
        if piece:
            out.append(piece)
        rest = rest[cut:].lstrip()
    if rest:
        out.append(rest)
    return out


# ---------- images ----------

def is_private_url(url: str) -> bool:
    """A URL the agent could not fetch: a loopback or private-network host
    (the agent's fetcher refuses those too)."""
    try:
        host = (urlsplit(url).hostname or "").lower()
    except ValueError:
        return True
    if not host or host == "localhost" or host.endswith(".localhost"):
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved


def image_suffix(data: bytes) -> str:
    if data.startswith(b"\x89PNG"):
        return ".png"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return ".gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    return ".jpg"
