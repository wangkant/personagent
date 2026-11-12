"""What every direct connector shares: stored credentials, the status file the
local page reads, text splitting, and the bridge between one platform and the
agent's connector protocol (docs/connectors.md)."""
from __future__ import annotations

import asyncio
import contextvars
import importlib.util
import json
import logging
import os
import random
import re
import time
import weakref
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional

from .. import home as homes
from ..storage import atomic_write_text

logger = logging.getLogger("personagent.direct")

# The agent refuses a request body over 8 MB, and base64 adds a third.
MAX_INLINE_IMAGE_BYTES = 4_000_000
MAX_CONCURRENT_TURNS = 16
# Waits after a dropped connection: doubling from the first, up to the second.
RETRY_S = (2.0, 120.0)
# A person reads a message before starting to answer it.
READ_S = (0.8, 2.0)
# A typing sign fades after about five seconds on the platforms that have one.
TYPING_REFRESH_S = 4.0
# The longest the sign stays up while the agent has not answered.
TYPING_WAIT_MAX_S = 60.0
# The longest one typing call may take, and how long a platform that slow
# with the sign is left without one.
TYPING_CALL_MAX_S = 2.0
TYPING_OFF_S = 30.0
# An outbox delivery: the most its pauses add up to, and the longest it waits
# behind replies to the same chat. The agent's outbox gives up on a connector
# whose next pull is 90 s late (outbox.LIVENESS_S), and one pull can carry
# ten, so a run of deliveries stops pausing and queuing after this long.
OUTBOX_PACE_MAX_S = 6.0
OUTBOX_QUEUE_MAX_S = 5.0
OUTBOX_RUN_MAX_S = 45.0

# Typing time the first item of a reply already spent waiting for the agent.
_spent: contextvars.ContextVar[float] = contextvars.ContextVar("personagent_direct_spent", default=0.0)
# What is left of the pauses a send may take; None for no limit.
_budget: contextvars.ContextVar[Optional[float]] = contextvars.ContextVar("personagent_direct_budget", default=None)

OnEvent = Callable[[dict, Any], Awaitable[None]]


class Refused(Exception):
    """The platform turned the credentials down; retrying will not help.
    The message is a short code for the page, never a credential."""


class Unsupported(Exception):
    """The platform cannot send unprompted to this conversation."""


def sdk():
    """The connector-protocol client bundled with the AstrBot plugin, which
    is the one copy every install carries."""
    from ..setup_wizard import PLUGIN_NAME

    source = homes.resource("integrations", "astrbot", PLUGIN_NAME, "personagent_connector.py")
    spec = importlib.util.spec_from_file_location("_personagent_connector_sdk", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------- storage

def credentials_path(home: Path) -> Path:
    return home / "platforms" / "direct.json"


def status_path(home: Path) -> Path:
    return home / "runtime" / "desktop" / "direct-status.json"


def _read(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_private(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    os.chmod(path, 0o600)


def load_credentials(home: Path) -> dict[str, dict]:
    """kind -> the values saved for it."""
    return _read(credentials_path(home))


def save_credentials(home: Path, kind: str, values: dict) -> None:
    stored = load_credentials(home)
    stored[kind] = dict(values)
    _write_private(credentials_path(home), stored)


def remove_credentials(home: Path, kind: str) -> None:
    stored = load_credentials(home)
    if stored.pop(kind, None) is not None:
        _write_private(credentials_path(home), stored)


def read_status(home: Path) -> dict[str, dict]:
    return _read(status_path(home))


class Status:
    """kind -> {"state": connecting|connected|refused|error, "detail": code,
    "since": unix seconds}, rewritten on every change for the page to poll."""

    def __init__(self, home: Path):
        self.path = status_path(home)
        self.states: dict[str, dict] = {}

    def set(self, kind: str, state: str, detail: str = "") -> None:
        current = self.states.get(kind, {})
        if current.get("state") == state and current.get("detail") == detail:
            return
        self.states[kind] = {"state": state, "detail": detail, "since": int(time.time())}
        _write_private(self.path, self.states)


# ---------------------------------------------------------------- text

def split_text(text: str, limit: int) -> list[str]:
    """Pieces of at most `limit` characters, cut at a line break or a space
    when one is near the end, so a long reply stays readable."""
    text = text.strip()
    pieces = []
    while len(text) > limit:
        cut = max(text.rfind("\n", 0, limit), text.rfind(" ", 0, limit))
        if cut < limit // 2:
            cut = limit
        pieces.append(text[:cut].rstrip())
        text = text[cut:].lstrip()
    if text:
        pieces.append(text)
    return pieces


def raw_id(prefixed: Any, platform: str) -> str:
    """A reply's `mention_user_id` is prefixed with the platform; the
    platform wants the bare id."""
    value = str(prefixed or "")
    prefix = platform + ":"
    return value[len(prefix):] if value.startswith(prefix) else ""


# ---------------------------------------------------------------- platform

class Platform:
    """One live connection. Subclasses fill in the platform side."""

    kind = ""                       # the event's `platform`, and the catalog id
    capabilities = ("outbox", "quote_text")

    def __init__(self, values: dict):
        self.values = values
        self.bot_id = ""

    def dropped(self) -> None:
        """Called when the connection is lost and being retried; the bridge
        replaces it to show the platform as connecting again."""

    async def check(self) -> str:
        """Prove the credentials work and learn the bot's own id; raises
        Refused when the platform turns them down."""
        raise NotImplementedError

    async def run(self, on_event: OnEvent, connected: Callable[[], None]) -> None:
        """Receive until cancelled, calling `connected` once the platform
        accepted the session and `on_event(event, target)` per message.
        Reconnects on its own; raises Refused if the platform locks it out."""
        raise NotImplementedError

    async def send(self, target: Any, items: list) -> int:
        """Send reply items in order to `target`; returns how many went out."""
        raise NotImplementedError

    def target(self, delivery: dict) -> Any:
        """Where an outbox delivery goes, from its reply_handle; raises
        Unsupported when it cannot be reached unprompted."""
        raise NotImplementedError

    def place(self, target: Any) -> str:
        """The chat `target` is in: replies to one chat go out one after another."""
        return str(target)

    async def typing(self, target: Any) -> None:
        """Show that a reply is being written, where the platform has such a
        sign. The sign fades by itself."""

    async def pace(self, target: Any, item: dict) -> None:
        """Awaited by `send` before each item goes out; the bridge replaces it."""

    async def close(self) -> None:
        pass


async def backoff_sleep(attempt: int) -> None:
    first, last = RETRY_S
    # Capped so a long outage cannot overflow the float.
    await asyncio.sleep(min(first * (2 ** min(attempt, 16)), last))


def typing_delay(text: str) -> float:
    """Seconds a person takes to type `text`: 6-8 characters a second and a
    short pause, at most 7. The pace transport.py keeps on QQ."""
    return min(len(text) / random.uniform(6.0, 8.0) + random.uniform(0.4, 1.2), 7.0)


def item_delay(item: dict) -> float:
    """How long a reply item takes to write; 0 for one no platform sends."""
    if item.get("type") == "text" and str(item.get("text") or "").strip():
        return typing_delay(str(item["text"]).strip())
    if item.get("type") == "image" and item.get("b64"):
        return random.uniform(0.6, 1.4)
    return 0.0


class Bridge:
    """Carries one platform's messages to the agent and the replies back.

    Replies go out the way a person sends them: one message at a time, each
    after the time it takes to type, with the platform's typing sign up
    meanwhile."""

    #: Off in tests that are not about the pace.
    paced = True

    def __init__(self, platform: Platform, agent: Any, status: Status):
        self.platform = platform
        self.agent = agent
        self.status = status
        self._turns = asyncio.Semaphore(MAX_CONCURRENT_TURNS)
        self._tasks: set[asyncio.Task] = set()
        self._sleep = asyncio.sleep
        self._sign_off_until = 0.0
        self._outbox_until = 0.0
        # One lock per chat, kept only while a reply to it is going out, and
        # how many replies hold or wait for it.
        self._order: weakref.WeakValueDictionary[str, asyncio.Lock] = weakref.WeakValueDictionary()
        self._queued: dict[str, int] = {}
        if self.paced:
            platform.pace = self._pace

    async def on_event(self, event: dict, target: Any) -> None:
        if not event.get("sender_id") or event.get("sender_id") == self.platform.bot_id:
            return
        event = {"kind": "event", "platform": self.platform.kind, "bot_id": self.platform.bot_id,
                 "capabilities": list(self.platform.capabilities), "prefiltered": True, **event}
        task = asyncio.create_task(self._turn(event, target))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _turn(self, event: dict, target: Any) -> None:
        started = time.monotonic()
        waiting: Optional[asyncio.Task] = None
        async with self._turns:
            # A message meant for the character gets an answer: the sign goes up while it is written.
            if self.paced and (event.get("addressed") or event.get("conversation_type") == "dm"):
                waiting = asyncio.create_task(self._typing_while_waiting(target))
            try:
                answer = await self.agent.send_event(event)
            except Exception as exc:
                logger.warning("%s: the agent did not take a message: %s",
                               self.platform.kind, type(exc).__name__)
                return
            finally:
                if waiting is not None:
                    waiting.cancel()
        items = answer.get("replies") or []
        if not items:
            return
        # Outside the turn limit: typing pauses must not hold up other chats.
        try:
            sent = await self._send(target, items, spent=time.monotonic() - started)
        except Exception as exc:
            logger.warning("%s: a reply was not sent: %s", self.platform.kind, type(exc).__name__)
            return
        if sent < len(items):
            logger.warning("%s: %d of %d reply items were not sent", self.platform.kind,
                           len(items) - sent, len(items))

    async def deliver(self, delivery: dict) -> tuple[str, int]:
        try:
            target = self.platform.target(delivery)
        except Unsupported:
            return "unsupported", 0
        items = delivery.get("items") or []
        # The agent counts a connector as gone when its next pull is late, so a
        # run of deliveries neither pauses long nor queues long behind replies.
        now = time.monotonic()
        if now >= self._outbox_until:
            self._outbox_until = now + OUTBOX_RUN_MAX_S
        left = self._outbox_until - now
        sent = await self._send(target, items, budget=min(OUTBOX_PACE_MAX_S, left),
                                queue_s=min(OUTBOX_QUEUE_MAX_S, left))
        return ("sent" if sent == len(items) else "partial" if sent else "failed"), sent

    async def _send(self, target: Any, items: list, *, spent: float = 0.0,
                    budget: Optional[float] = None, queue_s: Optional[float] = None) -> int:
        """Send `items` to one chat in order. `spent`: typing time the first
        item has had already. `budget`: the most the pauses may add up to.
        `queue_s`: the longest to wait behind other replies to the same chat;
        after that the items go out beside them."""
        if not self.paced:
            return await self.platform.send(target, items)
        key = self.platform.place(target)
        if queue_s is not None:
            deadline = time.monotonic() + queue_s
            while self._queued.get(key) and time.monotonic() < deadline:
                await asyncio.sleep(0.2)
            if self._queued.get(key):
                return await self._send_now(target, items, spent, budget)
        lock = self._order.get(key)
        if lock is None:
            lock = self._order[key] = asyncio.Lock()
        # Counted before the wait, so "nobody is queued" means the lock is free to take.
        self._queued[key] = self._queued.get(key, 0) + 1
        try:
            async with lock:
                return await self._send_now(target, items, spent, budget)
        finally:
            if self._queued[key] > 1:
                self._queued[key] -= 1
            else:
                del self._queued[key]

    async def _send_now(self, target: Any, items: list, spent: float, budget: Optional[float]) -> int:
        _spent.set(max(0.0, spent))
        _budget.set(budget)
        return await self.platform.send(target, items)

    async def _pace(self, target: Any, item: dict) -> None:
        """The time a person takes to type `item`, with the typing sign up;
        the first item of a reply has spent part of it waiting for the agent."""
        delay = item_delay(item) - _spent.get()
        _spent.set(0.0)
        budget = _budget.get()
        if budget is not None:
            delay = min(delay, budget)
            _budget.set(budget - max(delay, 0.0))
        await self._typing_for(target, delay)

    async def _typing_while_waiting(self, target: Any) -> None:
        await self._sleep(random.uniform(*READ_S))
        await self._typing_for(target, TYPING_WAIT_MAX_S)

    async def _typing_for(self, target: Any, seconds: float) -> None:
        left = seconds
        while left > 0:
            took = await self._sign(target)
            step = min(left, TYPING_REFRESH_S)
            # A slow sign has used part of the pause; a quick one is not counted.
            took = took if took >= 0.05 else 0.0
            if step > took:
                await self._sleep(step - took)
            left -= max(step, took)

    async def _sign(self, target: Any) -> float:
        """Put the typing sign up, and how long that took. A sign must never
        cost a reply: it gets two seconds, and a platform that is that slow
        with it (one limiting the calls) is left alone for a while."""
        started = time.monotonic()
        if started < self._sign_off_until:
            return 0.0
        call = asyncio.ensure_future(self.platform.typing(target))
        try:
            # Not wait_for: before Python 3.12 it can swallow the cancel that ends the sign.
            done, _ = await asyncio.wait({call}, timeout=TYPING_CALL_MAX_S)
            if not done:
                self._sign_off_until = time.monotonic() + TYPING_OFF_S
                logger.debug("%s: the typing sign took too long", self.platform.kind)
            elif not call.cancelled() and call.exception() is not None:
                logger.debug("%s: the typing sign failed: %s", self.platform.kind,
                             type(call.exception()).__name__)
        finally:
            if not call.done():
                call.cancel()
                # Whatever the cancelled call ends with has been dealt with here.
                call.add_done_callback(lambda done: done.cancelled() or done.exception())
        return time.monotonic() - started

    async def _receive(self, stop: asyncio.Event) -> None:
        """Run the platform until stopped, starting it again after anything
        but a refusal: a network blip at startup must not end it for good."""
        kind = self.platform.kind
        failures = 0

        def connected() -> None:
            nonlocal failures
            failures = 0
            self.status.set(kind, "connected")
        self.platform.dropped = lambda: self.status.set(kind, "connecting")
        while not stop.is_set():
            try:
                await self.platform.run(self.on_event, connected)
                return
            except Refused:
                raise
            except Exception as exc:
                logger.warning("%s: connection failed (%s); retrying", kind, type(exc).__name__)
                self.status.set(kind, "connecting", type(exc).__name__)
                await backoff_sleep(failures)
                failures += 1

    async def run(self, stop: asyncio.Event) -> None:
        kind = self.platform.kind
        self.status.set(kind, "connecting")
        receiving = asyncio.create_task(self._receive(stop))
        outbox = asyncio.create_task(self.agent.run_outbox(self.deliver, stop=stop))
        stopping = asyncio.create_task(stop.wait())
        try:
            done, _ = await asyncio.wait({receiving, stopping}, return_when=asyncio.FIRST_COMPLETED)
            if receiving in done:
                receiving.result()      # raises what ended it
        except Refused as exc:
            logger.error("%s: the platform refused the connection (%s)", kind, exc)
            self.status.set(kind, "refused", str(exc))
        except Exception as exc:
            logger.exception("%s stopped", kind)
            self.status.set(kind, "error", type(exc).__name__)
        finally:
            for task in (receiving, outbox, stopping, *self._tasks):
                if not task.done():
                    task.cancel()
            await self.platform.close()


def plain_name(*parts: Optional[str]) -> str:
    return next((str(p).strip() for p in parts if p and str(p).strip()), "")


def media(kind: str, **fields: Any) -> dict:
    """A connector `media` segment: something sent that the agent cannot see."""
    return {"type": "media", "kind": kind, **{k: str(v) for k, v in fields.items() if v}}


def has_content(segments: list, bot_id: str) -> bool:
    """Whether a message holds more than a quote and the bot's own mention."""
    return any(s["type"] != "reply" and not (s["type"] == "mention" and s.get("user_id") == bot_id)
               for s in segments)


# <@id> and <@!id> are people, <@&id> and <%id> roles, <#id> channels.
_TAG = re.compile(r"<(@[!&]?|%|#)([0-9A-Za-z]+)>")


def tagged_segments(text: str, names: dict[str, str]) -> list[dict]:
    """Text whose inline tags become mention segments, named from `names`,
    and readable words, so the model never reads a raw id."""
    segments: list[dict] = []
    words = ""
    at = 0
    for match in _TAG.finditer(text):
        words += text[at:match.start()]
        at = match.end()
        sigil, ident = match.groups()
        if sigil in ("@", "@!"):
            if words:
                segments.append({"type": "text", "text": words})
                words = ""
            segments.append({"type": "mention", "user_id": ident, "name": names.get(ident, "")})
        else:
            words += "#channel" if sigil == "#" else "@role"
    words += text[at:]
    if words.strip():
        segments.append({"type": "text", "text": words})
    return segments
