"""What every direct connector shares: stored credentials, the status file the
local page reads, text splitting, and the bridge between one platform and the
agent's connector protocol (docs/connectors.md)."""
from __future__ import annotations

import asyncio
import importlib.util
import json
import logging
import os
import time
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
    spec = importlib.util.spec_from_file_location("_personagent_direct_sdk", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------- storage

def credentials_path(home: Path) -> Path:
    return home / "platforms" / "direct.json"


def status_path(home: Path) -> Path:
    return home / "runtime" / "desktop" / "direct-status.json"


def _read(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def _write_private(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def load_credentials(home: Path) -> dict[str, dict]:
    """kind -> the values saved for it."""
    stored = _read(credentials_path(home))
    return {k: v for k, v in stored.items() if isinstance(v, dict)}


def save_credentials(home: Path, kind: str, values: dict) -> None:
    stored = load_credentials(home)
    stored[kind] = dict(values)
    _write_private(credentials_path(home), stored)


def remove_credentials(home: Path, kind: str) -> None:
    stored = load_credentials(home)
    if stored.pop(kind, None) is not None:
        _write_private(credentials_path(home), stored)


def read_status(home: Path) -> dict[str, dict]:
    return {k: v for k, v in _read(status_path(home)).items() if isinstance(v, dict)}


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
        try:
            _write_private(self.path, self.states)
        except OSError:
            logger.warning("could not write %s", self.path)


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

    async def close(self) -> None:
        pass


async def backoff_sleep(attempt: int) -> None:
    first, last = RETRY_S
    # The exponent is capped: a long outage would otherwise overflow the float.
    await asyncio.sleep(min(first * (2 ** min(attempt, 16)), last))


class Bridge:
    """Carries one platform's messages to the agent and the replies back."""

    def __init__(self, platform: Platform, agent: Any, status: Status):
        self.platform = platform
        self.agent = agent
        self.status = status
        self._turns = asyncio.Semaphore(MAX_CONCURRENT_TURNS)
        self._tasks: set[asyncio.Task] = set()

    async def on_event(self, event: dict, target: Any) -> None:
        if not event.get("sender_id") or event.get("sender_id") == self.platform.bot_id:
            return
        event = {"kind": "event", "platform": self.platform.kind, "bot_id": self.platform.bot_id,
                 "capabilities": list(self.platform.capabilities), "prefiltered": True, **event}
        task = asyncio.create_task(self._turn(event, target))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _turn(self, event: dict, target: Any) -> None:
        async with self._turns:
            try:
                answer = await self.agent.send_event(event)
            except Exception as exc:
                logger.warning("%s: the agent did not take a message: %s",
                               self.platform.kind, type(exc).__name__)
                return
            items = [item for item in answer.get("replies") or [] if isinstance(item, dict)]
            if not items:
                return
            try:
                sent = await self.platform.send(target, items)
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
        items = [item for item in delivery.get("items") or [] if isinstance(item, dict)]
        sent = await self.platform.send(target, items)
        return ("sent" if sent == len(items) else "partial" if sent else "failed"), sent

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
