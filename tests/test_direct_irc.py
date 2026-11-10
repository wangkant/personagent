"""The IRC connector against a scripted stand-in server: no network, no accounts."""
from __future__ import annotations

import asyncio
import base64
import json
import logging

import pytest

from persona_agent.direct import base, irc

PASSWORD = "hunter2-secret"
SECRET_B64 = base64.b64encode(f"Nova\0Nova\0{PASSWORD}".encode()).decode()


def run(coro):
    return asyncio.run(coro)


class Writer:
    def __init__(self, server):
        self.server = server
        self.closed = False

    def write(self, data: bytes):
        for line in data.decode("utf-8").split("\r\n"):
            if line:
                self.server.lines.append(line)
                self.server.script(self.server, line)

    async def drain(self):
        pass

    def close(self):
        self.closed = True

    async def wait_closed(self):
        pass


class Server:
    """One accepted connection: answers each client line through `script`."""

    def __init__(self, script):
        self.script = script
        self.lines: list[str] = []
        self.reader = None

    def say(self, *lines):
        for line in lines:
            self.reader.feed_data((line + "\r\n").encode("utf-8"))

    def hang_up(self):
        self.reader.feed_eof()


def network(sasl="PLAIN,EXTERNAL", password=PASSWORD, after_join=(), nick_taken=False, on_end=None):
    """A Libera-like server: CAP LS 302, SASL PLAIN, 001, then the JOIN echo."""
    def script(server, line):
        if line == "CAP LS 302":
            server.say(f":srv CAP * LS :multi-prefix{' sasl=' + sasl if sasl is not None else ''}")
        elif line.startswith("NICK ") and nick_taken:
            server.say(":srv 433 * Nova :Nickname is already in use.")
        elif line == "CAP REQ :sasl":
            server.say(":srv CAP * ACK :sasl")
        elif line == "AUTHENTICATE PLAIN":
            server.say("AUTHENTICATE +")
        elif line.startswith("AUTHENTICATE "):
            blob = base64.b64decode(line.split(" ", 1)[1]).decode()
            if blob.split("\0")[2] == password:
                server.say(":srv 900 Nova Nova!n@h Nova :You are now logged in", ":srv 903 Nova :SASL ok")
            else:
                server.say(":srv 904 Nova :SASL authentication failed")
        elif line == "CAP END":
            server.say(":srv 001 Nova :Welcome to the network, Nova",
                       ":srv 005 Nova CASEMAPPING=rfc1459 CHANTYPES=# :are supported by this server")
        elif line.startswith("JOIN "):
            for channel in line[5:].split(","):
                server.say(f":Nova!~nova@user/nova JOIN {channel}")
            server.say(*after_join)
            if on_end:
                on_end(server)
    return script


def connector(*scripts):
    """A connect= hook handing out one scripted server per connection."""
    servers = [Server(s) for s in scripts]
    opened = []

    async def connect(host, port):
        server = servers[len(opened)]
        opened.append((host, port))
        server.reader = asyncio.StreamReader()
        return server.reader, Writer(server)
    connect.servers, connect.opened = servers, opened
    return connect


def values(**extra):
    return {"irc_server": "irc.libera.chat", "irc_port": 6697, "irc_nick": "Nova",
            "irc_channels": "#room, lounge", **extra}


def instant(monkeypatch):
    async def no_wait(*args):
        await asyncio.sleep(0)
    monkeypatch.setattr(irc, "backoff_sleep", no_wait)
    monkeypatch.setattr(irc, "_pause", no_wait)
    monkeypatch.setattr(irc, "NICK_WAIT_S", 0)


# ---------------------------------------------------------------- check

def test_check_logs_in_with_sasl_plain_and_returns_the_nick():
    connect = connector(network())
    bot = irc.IRC(values(irc_password=PASSWORD), connect=connect)
    assert run(bot.check()) == "Nova" and bot.bot_id == "nova"
    lines = connect.servers[0].lines
    assert lines[:3] == ["CAP LS 302", "NICK Nova", "USER Nova 0 * :personagent"]
    assert "CAP REQ :sasl" in lines and f"AUTHENTICATE {SECRET_B64}" in lines
    assert lines.index("CAP END") > lines.index(f"AUTHENTICATE {SECRET_B64}")
    assert lines[-1].startswith("QUIT") and connect.opened == [("irc.libera.chat", 6697)]


def test_check_without_a_password_skips_sasl():
    connect = connector(network())
    assert run(irc.IRC(values(), connect=connect).check()) == "Nova"
    assert not any(line.startswith(("AUTHENTICATE", "CAP REQ")) for line in connect.servers[0].lines)


@pytest.mark.parametrize("script, code", [
    (network(password="other"), "password_rejected"),
    (network(nick_taken=True), "nick_in_use"),
    (lambda s, line: line.startswith("NICK") and s.say(":srv 432 * Nova :Erroneous Nickname"), "nick_invalid"),
    (lambda s, line: line.startswith("USER") and s.say(":srv 465 * :You are banned from this server"), "bot_banned"),
    (lambda s, line: line.startswith("USER") and s.say("ERROR :Closing Link: 1.2.3.4 (K-Lined)"), "bot_banned"),
    (lambda s, line: line.startswith("USER") and s.say("ERROR :Closing Link: (SASL access only)"), "sasl_required"),
])
def test_check_turns_each_rejection_into_a_named_refusal(script, code):
    password = PASSWORD if code == "password_rejected" else ""
    bot = irc.IRC(values(irc_password=password), connect=connector(script))
    with pytest.raises(base.Refused, match=code):
        run(bot.check())


def test_check_reports_an_unreachable_server_as_a_connection_error(monkeypatch):
    async def refused(host, port):
        raise ConnectionError("connect: ConnectionRefusedError")
    with pytest.raises(ConnectionError):
        run(irc.IRC(values(), connect=refused).check())

    async def unreachable(*args, **kwargs):
        raise OSError("no route")
    monkeypatch.setattr(irc.asyncio, "open_connection", unreachable)
    with pytest.raises(ConnectionError):
        run(irc.IRC(values()).check())

    async def hangs_up(host, port):
        reader = asyncio.StreamReader()
        reader.feed_eof()
        return reader, Writer(Server(lambda s, line: None))
    with pytest.raises(ConnectionError):
        run(irc.IRC(values(), connect=hangs_up).check())


# ---------------------------------------------------------------- run

def test_run_hands_channel_messages_and_dms_over_and_reconnects_after_a_drop(monkeypatch, caplog):
    instant(monkeypatch)
    caplog.set_level(logging.DEBUG, logger="personagent")
    first = network(after_join=(
        ":Alex!~a@host PRIVMSG #Room :just chatting",
        ":Alex!~a@host PRIVMSG #room :nova: how are you?",
        ":Alex!~a@host PRIVMSG #room :I think \x02Nova\x02 knows",
        ":Alex!~a@host PRIVMSG Nova :hi in private",
        ":Alex!~a@host PRIVMSG #elsewhere :pulled in somewhere else",
        ":Nova!~nova@user/nova PRIVMSG #room :my own echo",
        ":Alex!~a@host NOTICE #room :a notice",
        ":Alex!~a@host PRIVMSG Nova :\x01VERSION\x01",
        ":Alex!~a@host INVITE Nova #trap",
        "PING :tick",
    ), on_end=lambda s: s.hang_up(), password=PASSWORD)
    second = network(after_join=("ERROR :Closing Link: host (K-Lined)",), password=PASSWORD)
    connect = connector(first, second)
    bot = irc.IRC(values(irc_password=PASSWORD), connect=connect)
    seen, states = [], []
    bot.dropped = lambda: states.append("connecting")

    async def on_event(event, target):
        seen.append((event, target))
    with pytest.raises(base.Refused, match="bot_banned"):
        run(bot.run(on_event, lambda: states.append("connected")))

    assert states == ["connected", "connecting", "connected"]
    assert "JOIN #room,#lounge" in connect.servers[0].lines
    assert "PONG :tick" in connect.servers[0].lines
    assert not any("#trap" in line for line in connect.servers[0].lines)
    assert [t for _, t in seen] == ["#room", "#room", "#room", "alex"]
    plain, called, named, dm = (e for e, _ in seen)
    assert plain["conversation_type"] == "group" and plain["conversation_id"] == "#room"
    assert plain["addressed"] is False and plain["sender_id"] == "alex" and plain["sender_name"] == "Alex"
    assert plain["segments"] == [{"type": "text", "text": "just chatting"}]
    assert called["addressed"] is True and called["text"] == "how are you?"
    assert called["segments"][-1] == {"type": "mention", "user_id": "nova", "name": "Nova"}
    assert named["addressed"] is True and named["text"] == "I think Nova knows"
    assert dm["conversation_type"] == "dm" and "conversation_id" not in dm and dm["addressed"] is True
    assert dm["reply_handle"] == "alex" and dm["sent_at"] > 0
    assert len({e["message_id"] for e, _ in seen}) == 4

    # No credential in any event, or in any log line.
    dumped = json.dumps([e for e, _ in seen])
    for secret in (PASSWORD, SECRET_B64):
        assert secret not in dumped and secret not in caplog.text


def test_a_taken_nick_is_waited_out_while_running_and_then_refused(monkeypatch):
    instant(monkeypatch)
    monkeypatch.setattr(irc, "NICK_TRIES", 2)
    connect = connector(*[network(nick_taken=True)] * 3)
    states = []
    bot = irc.IRC(values(), connect=connect)
    bot.dropped = lambda: states.append("connecting")
    with pytest.raises(base.Refused, match="nick_in_use"):
        run(bot.run(None, lambda: states.append("connected")))
    assert len(connect.opened) == 3 and states == ["connecting", "connecting"]


def test_nickserv_gets_the_password_only_from_the_services_host(monkeypatch):
    instant(monkeypatch)
    after = (":NickServ!~evil@1.2.3.4 NOTICE Nova :This nickname is registered",
             ":NickServ!services@services.oftc.net NOTICE Nova :This nickname is registered",
             "ERROR :Closing Link: (Banned)")
    connect = connector(network(sasl=None, after_join=after))
    with pytest.raises(base.Refused):
        run(irc.IRC(values(irc_password=PASSWORD), connect=connect).run(None, lambda: None))
    identify = [line for line in connect.servers[0].lines if "IDENTIFY" in line]
    assert identify == [f"PRIVMSG NickServ :IDENTIFY {PASSWORD}"]


# ---------------------------------------------------------------- send

class Collect:
    def __init__(self):
        self.lines = []

    def write(self, data):
        self.lines += [line for line in data.decode("utf-8").split("\r\n") if line]

    async def drain(self):
        pass


def live_bot(monkeypatch):
    instant(monkeypatch)
    bot = irc.IRC(values(), connect=connector())
    bot.nick, bot.bot_id = "Nova", "nova"
    bot._writer = Collect()
    return bot


def test_send_writes_text_mentions_and_skips_images(monkeypatch):
    bot = live_bot(monkeypatch)
    bot.names["alex"] = "Alex"
    items = [{"type": "text", "text": "hi there", "mention_user_id": "irc:alex"},
             {"type": "text", "text": "two\nlines\r\nJOIN #evil"},
             {"type": "image", "b64": "aGk="},
             {"type": "text", "text": "   "}]
    assert run(bot.send("#room", items)) == 2
    assert bot._writer.lines == ["PRIVMSG #room :Alex: hi there", "PRIVMSG #room :two",
                                 "PRIVMSG #room :lines", "PRIVMSG #room :JOIN #evil"]
    bot._writer.lines.clear()
    assert run(bot.send("alex", [{"type": "text", "text": "psst", "mention_user_id": "irc:alex"}])) == 1
    assert bot._writer.lines == ["PRIVMSG alex :psst"]


def test_long_text_is_split_by_bytes_under_the_line_limit(monkeypatch):
    bot = live_bot(monkeypatch)
    text = "说" * 700 + " " + "word " * 200
    assert run(bot.send("#room", [{"type": "text", "text": text}])) == 1
    worst_prefix = len(":Nova!") + irc.PREFIX_GUESS
    assert len(bot._writer.lines) > 3
    for line in bot._writer.lines:
        assert len(line.encode("utf-8")) + 2 + worst_prefix <= irc.MAX_LINE
        assert "�" not in line
    sent = "".join(line.split(" :", 1)[1] for line in bot._writer.lines)
    assert sent.replace(" ", "") == text.replace(" ", "")
    assert all(len(p.encode()) <= 10 for p in irc.split_bytes("é" * 30, 10))


def test_sending_is_paced_and_stops_when_disconnected(monkeypatch):
    bot = live_bot(monkeypatch)
    waits = []

    async def record(seconds):
        waits.append(seconds)
    monkeypatch.setattr(irc, "_pause", record)
    run(bot.send("#room", [{"type": "text", "text": "a\nb\nc"}]))
    assert len(waits) == 2 and all(0 < w <= irc.PACE_S for w in waits)
    bot._writer = None
    assert run(bot.send("#room", [{"type": "text", "text": "x"}])) == 0


def test_target_reaches_only_the_listed_channels_and_nicks():
    bot = irc.IRC(values(), connect=connector())
    assert bot.channels == ["#room", "#lounge"]
    assert bot.target({"reply_handle": "#ROOM"}) == "#ROOM"
    assert bot.target({"reply_handle": "alex"}) == "alex"
    for handle in ("#trap", "", "bad nick", "x\r\nQUIT"):
        with pytest.raises(base.Unsupported):
            bot.target({"reply_handle": handle})
    assert run(bot.send("#trap", [{"type": "text", "text": "x"}])) == 0


def test_rfc1459_casemapping_folds_brackets_in_ids():
    bot = irc.IRC(values(irc_nick="Nova[m]"), connect=connector())
    bot.nick, bot.bot_id = "Nova[m]", bot.lower("Nova[m]")
    event = bot.event("Al[x]!~a@h", "#room", "nova{M}: hello")
    assert event["sender_id"] == "al{x}" and event["addressed"] is True and event["text"] == "hello"
    assert irc.parse("@time=x :a!b@c PRIVMSG #r :hi there") == ("a!b@c", "PRIVMSG", ["#r", "hi there"])
