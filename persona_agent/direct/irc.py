"""IRC networks (Libera.Chat, OFTC and others) over TLS, as a plain client
(https://modern.ircdocs.horse/, https://ircv3.net/specs/extensions/sasl-3.1):
PRIVMSG in from the configured channels and from DMs, PRIVMSG out."""
from __future__ import annotations

import asyncio
import base64
import itertools
import logging
import re
import ssl
import time
from typing import Any

from .base import Platform, Refused, Unsupported, backoff_sleep, raw_id

logger = logging.getLogger("personagent.direct.irc")

DEFAULT_SERVER = "irc.libera.chat"
DEFAULT_PORT = 6697
CONNECT_TIMEOUT_S = 30
REGISTER_TIMEOUT_S = 60
# Silence this long gets a PING of our own; the same again drops the link.
IDLE_S = 180
# One line per this many seconds keeps the server's flood limit away.
PACE_S = 1.5
# A nick still held by our own dropped connection frees up within minutes.
NICK_WAIT_S = 30
NICK_TRIES = 10
# 512 bytes per line including CRLF; the relayed copy also carries our prefix.
MAX_LINE = 512
# :nick!~user@host with USERLEN 10 and a 63-byte host, used until we see our own.
PREFIX_GUESS = 1 + 1 + 1 + 10 + 1 + 63 + 1
SASL_CHUNK = 400
JOIN_FAILED = {"403", "405", "471", "473", "474", "475", "477", "489"}
BANNED_WORDS = ("k-lined", "g-lined", "z-lined", "d-lined", "k-line", "g-line", "banned", "akill")
FORMATTING = re.compile(r"\x03(\d{1,2}(,\d{1,2})?)?|\x04([0-9a-fA-F]{6}(,[0-9a-fA-F]{6})?)?|[\x02\x0f\x11\x16\x1d\x1e\x1f]")
NICK_CHARS = r"[\w\[\]\\`^{}|-]"

_ASCII = {c: c + 32 for c in range(ord("A"), ord("Z") + 1)}
CASEMAPS = {"ascii": _ASCII,
            "strict-rfc1459": {**_ASCII, ord("["): ord("{"), ord("]"): ord("}"), ord("\\"): ord("|")},
            "rfc1459": {**_ASCII, ord("["): ord("{"), ord("]"): ord("}"), ord("\\"): ord("|"),
                        ord("^"): ord("~")}}

# Swapped out by tests; pacing must not slow them down.
_pause = asyncio.sleep


def parse(line: str) -> tuple[str, str, list[str]]:
    """(source, COMMAND, params) of one line; message tags are dropped."""
    if line.startswith("@"):
        line = line.partition(" ")[2]
    source = ""
    if line.startswith(":"):
        source, _, line = line[1:].partition(" ")
    params: list[str] = []
    line = line.lstrip(" ")
    while line:
        if line.startswith(":"):
            params.append(line[1:])
            break
        part, _, line = line.partition(" ")
        params.append(part)
        line = line.lstrip(" ")
    command = params.pop(0).upper() if params else ""
    return source, command, params


def split_bytes(text: str, limit: int) -> list[str]:
    """Pieces of at most `limit` UTF-8 bytes, never inside a character, cut
    at a space when one is near the end."""
    text = text.strip()
    pieces = []
    while len(text.encode("utf-8", "replace")) > limit:
        size, cut = 0, len(text)
        for i, char in enumerate(text):
            size += len(char.encode("utf-8", "replace"))
            if size > limit:
                cut = i
                break
        space = text.rfind(" ", 0, cut)
        if space >= max(cut // 2, 1):
            cut = space
        cut = max(cut, 1)
        pieces.append(text[:cut].rstrip())
        text = text[cut:].lstrip()
    if text:
        pieces.append(text)
    return [p for p in pieces if p]


def parse_channels(value: Any, chantypes: str = "#&") -> list[str]:
    channels = []
    for name in re.split(r"[,\s]+", str(value or "")):
        if not name:
            continue
        if name[0] not in chantypes:
            name = "#" + name
        if any(c in name for c in "\x00\x07\r\n:") or len(name) < 2:
            continue
        if name not in channels:
            channels.append(name)
    return channels


class IRC(Platform):
    kind = "irc"
    capabilities = ("outbox",)

    def __init__(self, values: dict, *, client=None, connect=None):
        # `client` is unused: IRC has no HTTP side, the hook is kept for symmetry.
        super().__init__(values)
        self.server = str(values.get("irc_server") or DEFAULT_SERVER).strip()
        try:
            self.port = int(values.get("irc_port") or DEFAULT_PORT)
        except (TypeError, ValueError):
            self.port = DEFAULT_PORT
        self.wanted_nick = str(values.get("irc_nick") or "").strip()
        self.nick = self.wanted_nick
        self._password = str(values.get("irc_password") or "")
        self.channels = parse_channels(values.get("irc_channels"))
        self._connect = connect
        self.casemap = CASEMAPS["rfc1459"]
        self.chantypes = "#&"
        self.mask = ""
        self.names: dict[str, str] = {}
        self._writer = None
        self._write_lock = asyncio.Lock()
        self._pace_lock = asyncio.Lock()
        self._next_line_at = 0.0
        self._authed = False
        self._identified = False
        self._pinged = False
        self._ids = itertools.count(1)
        self._tag = str(int(time.time()))

    # ------------------------------------------------------------ helpers

    def lower(self, text: str) -> str:
        return text.translate(self.casemap)

    def _is_channel(self, name: str) -> bool:
        return bool(name) and name[0] in self.chantypes

    def _wanted(self) -> set[str]:
        return {self.lower(c) for c in self.channels}

    async def _open(self):
        if self._connect is not None:
            return await self._connect(self.server, self.port)
        context = ssl.create_default_context()
        try:
            return await asyncio.wait_for(asyncio.open_connection(
                self.server, self.port, ssl=context, server_hostname=self.server), CONNECT_TIMEOUT_S)
        except (OSError, asyncio.TimeoutError, ssl.SSLError) as exc:
            raise ConnectionError(f"connect: {type(exc).__name__}") from None

    async def _write(self, writer, line: str) -> None:
        if any(c in line for c in "\r\n\0"):
            raise ValueError("a line may not hold a line break")
        async with self._write_lock:
            try:
                writer.write(line.encode("utf-8", "replace") + b"\r\n")
                await writer.drain()
            except (OSError, RuntimeError) as exc:
                raise ConnectionError(f"write: {type(exc).__name__}") from None

    async def _read(self, reader, writer) -> str:
        while True:
            try:
                raw = await asyncio.wait_for(reader.readline(), IDLE_S)
            except asyncio.TimeoutError:
                if self._pinged:
                    raise ConnectionError("ping timeout") from None
                self._pinged = True
                await self._write(writer, "PING :personagent")
                continue
            except (OSError, ValueError, asyncio.LimitOverrunError) as exc:
                raise ConnectionError(f"read: {type(exc).__name__}") from None
            if not raw:
                raise ConnectionError("closed")
            self._pinged = False
            try:
                line = raw.decode("utf-8")
            except UnicodeDecodeError:
                line = raw.decode("latin-1")    # older clients still send it
            line = line.rstrip("\r\n")
            if line:
                return line

    @staticmethod
    async def _hang_up(writer) -> None:
        try:
            writer.close()
            await writer.wait_closed()
        except (OSError, RuntimeError, ssl.SSLError):
            pass                        # already gone is fine

    def _refusal(self, command: str, params: list[str]) -> Refused | None:
        if command in ("432",):
            return Refused("nick_invalid")
        if command in ("433", "436", "437"):
            return Refused("nick_in_use")
        if command in ("464", "902", "904", "905"):
            return Refused("password_rejected")
        if command == "465":
            return Refused("bot_banned")
        if command == "ERROR":
            reason = (params[-1] if params else "").lower()
            if any(word in reason for word in BANNED_WORDS):
                return Refused("bot_banned")
            if "sasl" in reason and not self._authed:
                return Refused("password_rejected" if self._password else "sasl_required")
        return None

    # ------------------------------------------------------------ session

    async def _register(self, reader, writer) -> None:
        """CAP, optional SASL PLAIN, NICK/USER, until 001 names our nick."""
        if not self.wanted_nick or any(c in self.wanted_nick for c in " ,:!@*?#&\x00\x07"):
            raise Refused("nick_invalid")
        self._authed, self._pinged, self._identified = False, False, False
        self.nick = self.wanted_nick
        caps: dict[str, str] = {}
        await self._write(writer, "CAP LS 302")
        await self._write(writer, f"NICK {self.nick}")
        await self._write(writer, f"USER {self.nick} 0 * :personagent")
        while True:
            line = await self._read(reader, writer)
            _, command, params = parse(line)
            refusal = self._refusal(command, params)
            if refusal is not None:
                raise refusal
            if command == "PING":
                await self._write(writer, f"PONG :{params[-1] if params else ''}")
            elif command == "ERROR":
                raise ConnectionError("closed by the server")
            elif command == "CAP" and len(params) >= 3:
                sub = params[1].upper()
                if sub == "LS":
                    more = len(params) >= 4 and params[2] == "*"
                    for token in params[-1].split():
                        name, _, value = token.partition("=")
                        caps[name] = value
                    if more:
                        continue
                    mechanisms = caps.get("sasl", "").upper().split(",")
                    if self._password and "sasl" in caps and (not caps["sasl"] or "PLAIN" in mechanisms):
                        await self._write(writer, "CAP REQ :sasl")
                    else:
                        await self._write(writer, "CAP END")
                elif sub == "ACK" and "sasl" in params[-1].split():
                    await self._write(writer, "AUTHENTICATE PLAIN")
                elif sub == "NAK":
                    await self._write(writer, "CAP END")
            elif command == "AUTHENTICATE" and params and params[0] == "+":
                for chunk in self._sasl_chunks():
                    await self._write(writer, f"AUTHENTICATE {chunk}")
            elif command == "903":
                self._authed = True
                await self._write(writer, "CAP END")
            elif command == "906":
                await self._write(writer, "CAP END")
            elif command == "001":
                self.nick = params[0] if params else self.nick
                self.bot_id = self.lower(self.nick)
                return

    def _sasl_chunks(self) -> list[str]:
        account = self.wanted_nick
        blob = base64.b64encode(f"{account}\0{account}\0{self._password}".encode()).decode()
        chunks = [blob[i:i + SASL_CHUNK] for i in range(0, len(blob), SASL_CHUNK)] or ["+"]
        if len(chunks[-1]) == SASL_CHUNK:
            chunks.append("+")
        return chunks

    async def check(self) -> str:
        reader, writer = await self._open()
        try:
            try:
                await asyncio.wait_for(self._register(reader, writer), REGISTER_TIMEOUT_S)
            except asyncio.TimeoutError:
                raise ConnectionError("registration timed out") from None
            try:
                await self._write(writer, "QUIT :checked")
            except ConnectionError:
                pass
            return self.nick
        finally:
            await self._hang_up(writer)

    async def run(self, on_event, connected) -> None:
        failures, nick_tries = 0, 0
        while True:
            def up() -> None:
                nonlocal failures, nick_tries
                failures, nick_tries = 0, 0
                connected()
            try:
                await self._session(on_event, up)
            except Refused as exc:
                # Usually our own previous connection, still timing out.
                if str(exc) != "nick_in_use" or nick_tries >= NICK_TRIES:
                    raise
                nick_tries += 1
                logger.warning("irc: the nickname is taken; trying again (%d)", nick_tries)
                self.dropped()
                await asyncio.sleep(NICK_WAIT_S)
                continue
            except (ConnectionError, OSError, asyncio.IncompleteReadError) as exc:
                logger.warning("irc: connection dropped (%s)", exc if isinstance(exc, ConnectionError)
                               else type(exc).__name__)
            self.dropped()
            await backoff_sleep(failures)
            failures += 1

    async def _session(self, on_event, connected) -> None:
        reader, writer = await self._open()
        try:
            try:
                await asyncio.wait_for(self._register(reader, writer), REGISTER_TIMEOUT_S)
            except asyncio.TimeoutError:
                raise ConnectionError("registration timed out") from None
            if self.channels:
                await self._write(writer, "JOIN " + ",".join(self.channels))
            self._writer = writer
            connected()
            while True:
                line = await self._read(reader, writer)
                await self._handle(line, writer, on_event)
        finally:
            self._writer = None
            await self._hang_up(writer)

    async def _handle(self, line: str, writer, on_event) -> None:
        source, command, params = parse(line)
        nick = source.partition("!")[0]
        mine = bool(nick) and self.lower(nick) == self.bot_id
        if command == "PING":
            await self._write(writer, f"PONG :{params[-1] if params else ''}")
        elif command in ("ERROR", "465"):
            refusal = self._refusal(command, params)
            if refusal is not None:
                raise refusal
            raise ConnectionError("closed by the server")
        elif command == "005":
            for token in params[1:-1]:
                key, _, value = token.partition("=")
                if key == "CASEMAPPING" and value in CASEMAPS:
                    self.casemap = CASEMAPS[value]
                    self.bot_id = self.lower(self.nick)
                elif key == "CHANTYPES" and value:
                    self.chantypes = value
        elif command == "NICK" and mine and params:
            self.nick = params[-1]
            self.bot_id = self.lower(self.nick)
        elif command == "JOIN" and mine:
            self.mask = source
            if params:
                logger.info("irc: joined %s", params[0])
        elif command == "396" and len(params) >= 2 and self.mask:
            self.mask = self.mask.partition("@")[0] + "@" + params[1]
        elif command == "KICK" and len(params) >= 2 and self.lower(params[1]) == self.bot_id:
            logger.warning("irc: kicked from %s; not rejoining until the next connection", params[0])
        elif (command == "NOTICE" and self.lower(nick) == "nickserv" and self._password
              and not self._authed and not self._identified
              and source.partition("@")[2].lower().startswith("services.")):
            # Networks without SASL (OFTC) take the password from NickServ; only
            # the real services host gets it, never a user who took the nick.
            self._identified = True
            await self._write(writer, f"PRIVMSG NickServ :IDENTIFY {self._password}")
        elif command == "INVITE":
            logger.info("irc: ignored an invite; only the configured channels are joined")
        elif command in JOIN_FAILED and len(params) >= 2:
            logger.warning("irc: could not join %s (%s)", params[1], command)
        elif command == "PRIVMSG" and len(params) >= 2 and nick and not mine:
            event = self.event(source, params[0], params[1])
            if event:
                await on_event(event, event["reply_handle"])

    # ------------------------------------------------------------ events

    def event(self, source: str, to: str, text: str) -> dict | None:
        nick, _, host = source.partition("!")
        if not nick or not host or self.lower(nick) == self.bot_id:
            return None                 # servers and services, or our own echo
        is_dm = not self._is_channel(to)
        if is_dm and self.lower(to) != self.bot_id:
            return None
        if not is_dm and self.lower(to) not in self._wanted():
            return None                 # only the channels the owner listed
        if text.startswith("\x01"):
            command, _, rest = text.strip("\x01").partition(" ")
            if command.upper() != "ACTION":
                return None             # CTCP VERSION and the like get no answer
            text = f"* {nick} {rest}"
        text = FORMATTING.sub("", text).strip()
        if not text:
            return None
        uid = self.lower(nick)
        self.names[uid] = nick
        addressed = is_dm
        own = self.lower(self.nick)
        folded = self.lower(text)
        lead = re.match(rf"\s*{re.escape(own)}\s*[,:]\s*", folded) if own else None
        if lead:
            addressed = True
            text = text[lead.end():].strip() or text
        elif own and re.search(rf"(?<!{NICK_CHARS}){re.escape(own)}(?!{NICK_CHARS})", folded):
            addressed = True
        segments: list[dict] = [{"type": "text", "text": text}]
        if addressed and not is_dm:
            segments.append({"type": "mention", "user_id": self.bot_id, "name": self.nick})
        handle = uid if is_dm else self.lower(to)
        return {"conversation_type": "dm" if is_dm else "group",
                **({} if is_dm else {"conversation_id": handle}),
                "sender_id": uid, "sender_name": nick,
                "message_id": f"{self._tag}-{next(self._ids)}", "sent_at": int(time.time()),
                "addressed": addressed, "text": text, "segments": segments,
                "reply_handle": handle}

    # ------------------------------------------------------------ sending

    def _reachable(self, handle: str) -> bool:
        if not handle or any(c in handle for c in " ,:\r\n\0\x07*?!@"):
            return False
        if self._is_channel(handle):
            return self.lower(handle) in self._wanted()
        return True

    def target(self, delivery: dict) -> str:
        handle = str(delivery.get("reply_handle") or delivery.get("conversation_id") or "")
        if not self._reachable(handle):
            raise Unsupported()
        return handle

    def _budget(self, target: str) -> int:
        prefix = len(self.mask.encode()) + 2 if self.mask else len(self.nick.encode()) + PREFIX_GUESS
        return MAX_LINE - 2 - len(f"PRIVMSG {target} :".encode()) - prefix

    async def _say(self, target: str, text: str) -> None:
        writer = self._writer
        if writer is None:
            raise ConnectionError("not connected")
        async with self._pace_lock:
            wait = self._next_line_at - time.monotonic()
            if wait > 0:
                await _pause(wait)
            await self._write(writer, f"PRIVMSG {target} :{text}")
            self._next_line_at = time.monotonic() + PACE_S

    async def send(self, target: str, items: list) -> int:
        if not self._reachable(target):
            return 0
        sent, skipped = 0, 0
        for item in items:
            try:
                if item.get("type") == "image":
                    skipped += 1
                    continue
                if item.get("type") != "text" or not str(item.get("text") or "").strip():
                    continue
                await self.pace(target, item)
                mention = raw_id(item.get("mention_user_id"), self.kind)
                name = self.names.get(mention, mention) if self._is_channel(target) else ""
                if re.search(r"[\s\x00-\x1f,:]", name):
                    name = ""
                text = re.sub(r"[\x00\x01]", "", str(item["text"]).replace("\r", "\n"))
                lines = [line for line in text.split("\n") if line.strip()]
                if name and lines:
                    lines[0] = f"{name}: {lines[0].strip()}"
                for line in lines:
                    for piece in split_bytes(line, self._budget(target)):
                        await self._say(target, piece)
            except ConnectionError as exc:
                logger.warning("irc: sending stopped after %d item(s) (%s)", sent, exc)
                break
            sent += 1
        if skipped:
            logger.info("irc: %d image(s) not sent; IRC carries text only", skipped)
        return sent

    async def close(self) -> None:
        writer, self._writer = self._writer, None
        if writer is not None:
            try:
                await self._write(writer, "QUIT :bye")
            except ConnectionError:
                pass
            await self._hang_up(writer)
