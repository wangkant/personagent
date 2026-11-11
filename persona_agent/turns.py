"""How a message becomes a turn: intake, admission, a conversation's line
and the group turn."""
from __future__ import annotations

import asyncio
import contextvars
import logging
import random
import time
from typing import Callable, Optional

from . import access
from .decision import (BLOCKED, EMPTY_DRAFT_RETRY_NOTE, PASS, SEND,
                       SLEEP_WINDOW, STICKY_CALL, choose_group_mode, pacing_skip)
from . import channels
from . import paths
from . import chatlangs
from . import decision_log
from .connector import (ConnectorSink, current_sink,
                      event_connector, event_prefiltered,
                      synthesize_onebot_payload)
from .messages import message_time
from .prompt import BUFFERED_LINE_CHARS
from .textproc import (
    TextProcessing,
    _clean_prompt_source,
    _strip_web_desc,
    _truncate_framed,
)

logger = logging.getLogger("agent")

# Bounded: connector-chosen ids would otherwise grow the set with every room.
_MAX_REFUSALS_LOGGED = 4096

# How often one conversation may hear that the model is not answering.
_EXCUSE_COOLDOWN_S = 300.0

# A bare call ("@Bot", "Bot?") waits this long for the message that follows it.
BARE_CALL_DEBOUNCE_S = 5.0

# A connector message older than this (a backlog handed over after a restart)
# joins the window but opens no turn: it is not answered as if just said.
STALE_MESSAGE_S = 600.0

# A turn's whole model time, in LLM_TIMEOUT_S: one full-length call and half
# of another, however many calls, retries and models it goes through.
_TURN_BUDGET_CALLS = 1.5

# Arrivals one conversation holds back; a flood past it loses its oldest.
_MAX_HELD = 256

# Held memory commands that keep their handler, where an answer can only
# travel in a response; a later one's answer rides in the last keeper's.
_MAX_COMMAND_WAITERS = 2

# Callers since the last turn that one reply answers together.
_MAX_CALLERS = 4

# How long a turn waits for a picture still being read in its line.
_UNREAD_WAIT_S = 20.0


class _Held:
    """One arrival in a conversation's line. `absorb` is its intake, run in
    arrival order (None while the message is still being read); `waiter` then
    carries what it returned, or None once its handler has no reason to stay.
    `message`: a chat message, of which only the newest keeps its handler.
    `turn`: its handler runs the next turn as soon as it is let in.
    `say`: sends a memory command's answer (`absorb` returned it)."""

    __slots__ = ("absorb", "message", "turn", "say", "waiter", "context",
                 "ticket", "carrier", "carried", "owing", "outcome",
                 "absorbed", "granted", "dropped")

    def __init__(self) -> None:
        self.absorb: Optional[Callable[[], object]] = None
        self.message = self.turn = False
        self.say: Optional[Callable] = None
        self.waiter: asyncio.Future = asyncio.get_running_loop().create_future()
        # Intake runs as its own request, whichever task lets it in.
        self.context = contextvars.copy_context()
        self.ticket = 0
        # The waiting command whose response carries this one's answer.
        self.carrier: Optional[_Held] = None
        # (say, answer) of the commands this one carries, and how many more.
        self.carried: list[tuple] = []
        self.owing = 0
        self.outcome: object = None
        self.absorbed = self.granted = self.dropped = False

    def release(self, outcome) -> None:
        if not self.waiter.done():
            self.waiter.set_result(outcome)

    def carried_one(self) -> None:
        """One carried answer is settled; the last lets the handler go."""
        self.owing -= 1
        if self.owing == 0 and self.absorbed:
            self.release(self.outcome)


class _TurnGate(asyncio.Event):
    """A conversation's line: the turn in flight, from its model call to its
    commit, and what arrived meanwhile or is still being read, in order. It
    is let in when the turn ends, so a reply is never placed after a message
    it did not see. An Event, set once the line is empty again."""

    def __init__(self) -> None:
        super().__init__()
        self.held: list[_Held] = []
        # A turn is in flight: nothing behind it is let in.
        self.busy = False
        # The one chat message whose handler still waits to run a turn.
        self.newest: Optional[_Held] = None
        # Held commands that kept their handler (see _MAX_COMMAND_WAITERS).
        self.keepers: list[_Held] = []
        self.tickets = 0
        self.overflowed = False


class Turns:
    async def handle_onebot(self, payload: dict, *,
                            proactive: bool = False) -> bool:
        # One OneBot-shaped payload (/v1/onebot, the catch-up sweep or
        # handle_event); `proactive` text is the caller's cue (see _handle_dm).
        return await self._handle_inner(payload, proactive=proactive)

    # ---- a conversation's line ---------------------------------------------

    def _begin_turn(self, key: str) -> _TurnGate:
        """Reserve `key`'s next reply before the model is asked: what arrives
        from here on is held behind it."""
        gate = self._pending_outbound.get(key)
        if gate is None:
            gate = self._pending_outbound[key] = _TurnGate()
        gate.busy = True
        return gate

    def _end_turn(self, key: str, gate: _TurnGate) -> None:
        """Close a turn and let in what was held behind it. Synchronous, so
        nothing can come between a commit and this."""
        gate.busy = False
        self._drain(key, gate)

    def _enter_line(self, key: str) -> tuple[_TurnGate, _Held]:
        """Take the next place in `key`'s line for a message not read yet, so
        it keeps its arrival order however long reading it takes."""
        gate = self._pending_outbound.get(key)
        if gate is None:
            gate = self._pending_outbound[key] = _TurnGate()
        item = _Held()
        if self._place(gate, item):
            self._drain(key, gate)
        return gate, item

    def _leave_line(self, key: str, gate: _TurnGate, item: _Held) -> None:
        """Give up a place taken with `_enter_line`: nothing came of it."""
        if item in gate.held:
            gate.held.remove(item)
        item.release(None)
        self._drain(key, gate)

    @staticmethod
    def _place(gate: _TurnGate, item: _Held) -> bool:
        """Append `item`; True when the bound made the line drop an arrival."""
        gate.tickets += 1
        item.ticket = gate.tickets
        gate.held.append(item)
        if len(gate.held) <= _MAX_HELD:
            return False
        gate.overflowed = True
        # Chatter first: a command changes what is remembered. Then one that
        # carries no other's answer, which would run and never be answered.
        victim = next(
            (held for held in gate.held if held.message and held is not item),
            next((held for held in gate.held
                  if not held.owing and held is not item), gate.held[0]))
        gate.held.remove(victim)
        victim.dropped = True
        if gate.newest is victim:
            gate.newest = None
        victim.release(None)
        if victim.carrier is not None:
            victim.carrier.carried_one()
        return True

    def _ready(self, key: str, gate: _TurnGate, item: _Held,
               absorb: Callable[[], object], *, message: bool,
               turn: bool = False, say: Optional[Callable] = None) -> None:
        """`item` has been read: decide whether its handler stays, then let
        in whatever the line can now let in."""
        if item.dropped:
            return
        item.absorb, item.message, item.turn, item.say = absorb, message, turn, say
        if message:
            # Only the newest message can still become a turn (the debounce
            # rule), so the others' handlers leave, and with them their slots.
            if gate.newest is not None and gate.newest.ticket > item.ticket:
                item.release(None)
            else:
                if gate.newest is not None:
                    gate.newest.release(None)
                gate.newest = item
        elif say is not None and (gate.busy or gate.held[0] is not item):
            self._settle_held_command(key, gate, item)
        self._drain(key, gate)

    def _settle_held_command(self, key: str, gate: _TurnGate,
                             item: _Held) -> None:
        """A memory command that must wait its turn in line: does its handler
        wait too? Only where the answer has no other way out."""
        # NapCat, or a connector that pulls the outbox: answered from a
        # background task once the command has run.
        if current_sink.get() is None or self._background_route(key) is not None:
            item.release(None)
            return
        gate.keepers = [k for k in gate.keepers if not k.waiter.done()]
        if len(gate.keepers) < _MAX_COMMAND_WAITERS:
            gate.keepers.append(item)
            return
        item.carrier = gate.keepers[-1]
        item.carrier.owing += 1
        item.release(None)

    def _drain(self, key: str, gate: _TurnGate) -> None:
        """Let in, in order, what the line holds: up to the first message
        still being read, or the one whose handler takes the next turn."""
        later: list[tuple] = []
        while gate.held and not gate.busy:
            item = gate.held[0]
            if item.absorb is None:
                break
            del gate.held[0]
            if gate.newest is item:
                gate.newest = None
            staying = not item.waiter.done()
            try:
                outcome = item.context.run(item.absorb)
            except Exception as e:
                # The handler that would have raised it still does.
                if staying:
                    item.waiter.set_exception(e)
                else:
                    logger.warning("[Agent] held message intake failed "
                                   "(conversation=%s): %s", key, e)
                if item.carrier is not None:
                    item.carrier.carried_one()
                continue
            item.outcome, item.absorbed = outcome, True
            if staying:
                # Its handler runs the next turn: the rest stays behind it.
                gate.busy = item.granted = item.turn
                if not item.owing:
                    item.release(outcome)
            elif item.say is not None:
                carrier = item.carrier
                if carrier is not None and not carrier.waiter.done():
                    carrier.carried.append((item.say, outcome))
                    carrier.carried_one()
                else:
                    later.append((item.say, outcome))
        if later:
            self._spawn(self._say_later(key, later))
        if gate.overflowed:
            gate.overflowed = False
            logger.warning("[Agent] over %d messages waited in one line "
                           "(conversation=%s); the oldest were dropped",
                           _MAX_HELD, key)
        if not gate.busy and not gate.held:
            if self._pending_outbound.get(key) is gate:
                del self._pending_outbound[key]
            gate.set()

    async def _say_later(self, key: str, answers: list[tuple]) -> None:
        """Answer, in order, the held commands whose handlers have left."""
        for say, answer in answers:
            try:
                await say(answer, background=True)
            except Exception as e:
                logger.warning("[Agent] memory command answer failed "
                               "(conversation=%s): %s", key, e)

    async def _say_carried(self, key: str, answers: list[tuple]) -> None:
        """Answer, in this request's response, the commands it carries."""
        for say, answer in answers:
            try:
                await say(answer)
            except Exception as e:
                logger.warning("[Agent] memory command answer failed "
                               "(conversation=%s): %s", key, e)

    async def _group_intake(self, group_id: str, absorb: Callable[[], tuple],
                            say: Optional[Callable]) -> tuple[Optional[tuple], list]:
        """Run `absorb`, one message's intake, in arrival order: now, or when
        the turn in flight ends. Returns what it returned, None when the
        handler has no reason to stay, and the answers it carries for others.
        `say`: set for a memory command, and sends its answer."""
        async with self.locks[group_id]:
            gate = self._pending_outbound.get(group_id)
            if gate is None:
                return absorb(), []
            item = _Held()
            self._place(gate, item)
            self._ready(group_id, gate, item, absorb,
                        message=say is None, say=say)
        # Cancelled only at shutdown, so what it displaced needs no other turn.
        return await item.waiter, item.carried

    async def _read_in_line(self, group_id: str, gate: _TurnGate, item: _Held,
                            absorb: Callable[[], tuple],
                            say: Optional[Callable]) -> tuple[Optional[tuple], list]:
        """`_group_intake` for a message that took its place in line before
        it was read (`_enter_line`)."""
        try:
            async with self.locks[group_id]:
                self._ready(group_id, gate, item, absorb,
                            message=say is None, say=say)
        except BaseException:
            if item.absorb is None:
                self._leave_line(group_id, gate, item)
            raise
        return await item.waiter, item.carried

    async def _say_memory_answer(self, group_id: str, answer: str,
                                 at_uid: str, *, background: bool = False) -> bool:
        """Send a memory command's answer to a group and put it on record.
        `background`: no request of the conversation is open to carry it."""
        async with self.send_locks[group_id]:
            if background:
                send_result = await self._send_background(
                    group_id,
                    lambda: self._send_group(group_id, answer, at_uid),
                    reason="follow_up")
            else:
                send_result = await self._send_group(group_id, answer, at_uid)
        if not send_result.success:
            logger.warning("[Agent] memory command delivery failed (group=%s)",
                           group_id)
            return send_result.partial
        async with self.locks[group_id]:
            self._spoke_in(group_id)
            self._append_buffer(group_id, self.persona_name, answer)
        self._index_own(send_result.message_ids, answer)
        if self.on_reply:
            await self.on_reply(group_id, answer)
        logger.info("[Agent] memory command (group=%s): %s", group_id, answer[:60])
        return True

    async def handle_event(self, event: dict) -> dict:
        """Handle one connector event synchronously: a ConnectorSink contextvar
        collects the sends, and the replies go back in the HTTP response."""
        sender, bot = (str(event.get(k, "") or "") for k in ("sender_id", "bot_id"))
        if sender and sender == bot:
            # The bot's own echo: owned, so the connector's model stays quiet too.
            logger.debug("[Agent] dropped the bot's own message (%s)",
                         event.get("platform", "?"))
            return {"handled": False, "owned": True, "replies": []}
        payload = synthesize_onebot_payload(
            event, self._self_mention_id(), self.connector_qq_platforms)
        # When it was said, in OneBot's field, for the window and for a backlog.
        if message_time({"time": event.get("sent_at")}) is not None:
            payload["time"] = message_time({"time": event.get("sent_at")})
        if payload.get("message_type") == "private":
            route_key = channels.dm_routing_key(payload.get("user_id", ""))
        else:
            route_key = str(payload.get("group_id", ""))
        if route_key:
            self._connector_inflight[route_key] += 1
        # A native platform's ids are bare inside; outbound mentions are
        # namespaced again (see message_to_reply_item).
        sink_platform = str(payload.get("_platform", "") or "")
        sink = ConnectorSink(
            platform=sink_platform,
            native=sink_platform in self.connector_qq_platforms,
            bot_id=self._self_mention_id(),
            prefiltered=event_prefiltered(event),
        )
        tok = current_sink.set(sink)
        # An argument, not a payload flag: /v1/onebot accepts arbitrary JSON.
        proactive = bool(event.get("proactive"))
        try:
            handled = await self.handle_onebot(payload, proactive=proactive)
        finally:
            # Closed first: background tasks inherit this sink and must not
            # collect into a response that is gone.
            sink.closed = True
            current_sink.reset(tok)
            if route_key:
                remaining = self._connector_inflight.get(route_key, 0) - 1
                if remaining > 0:
                    self._connector_inflight[route_key] = remaining
                else:
                    self._connector_inflight.pop(route_key, None)
                self._trim_connector_convs()
        # Only an admitted turn may leave a handle behind.
        connector = event_connector(event)
        if (route_key and sink.owned
                and (connector["reply_handle"] or connector["connector_id"])):
            dm = payload.get("message_type") == "private"
            self.connector_handles.record(
                route_key, **connector, platform=sink.platform,
                native=sink.native,
                conversation_type="dm" if dm else "group",
                conversation_id=str(event.get(
                    "sender_id" if dm else "conversation_id") or ""),
                prefiltered=sink.prefiltered)
        # `owned`, not `handled`, tells a connector to suppress its own model:
        # silence is often the persona's answer.
        return {"handled": bool(handled), "owned": sink.owned,
                "replies": sink.items}

    def _claim_connector_turn(self) -> None:
        """Mark the connector turn as ours once admission passes, whatever it says."""
        sink = current_sink.get()
        if sink is not None:
            sink.owned = True

    def _admins(self) -> frozenset[str]:
        """Every admin account (ADMIN_IDS), canonical; re-read since it is edited live."""
        return access.parse_ids(
            self.admin_ids, native_platforms=self.connector_qq_platforms,
        ) | access.page_owner(paths.runtime_dir())

    def _dm_allowlist(self) -> frozenset[str]:
        """ACCESS_DM_USERS, canonical."""
        return access.parse_ids(
            self.access_dm_users,
            native_platforms=self.connector_qq_platforms)

    def _group_allowlist(self) -> frozenset[str]:
        """ACCESS_GROUPS, canonical."""
        return access.parse_ids(
            self.access_groups, native_platforms=self.connector_qq_platforms)

    def _log_refusal(self, conv_key: str, reason: str) -> None:
        """Say once per conversation why it is not answered."""
        key = f"{conv_key}\x00{reason}"
        if key in self._refusals_logged:
            return
        self._refusals_logged[key] = None
        if len(self._refusals_logged) > _MAX_REFUSALS_LOGGED:
            self._refusals_logged.pop(next(iter(self._refusals_logged)))
        logger.info("[Agent] not answering %s: %s", conv_key, reason)

    def _excuse_begin(self, conv_key: str) -> bool:
        """May this conversation be told the model is not answering: once per
        `_EXCUSE_COOLDOWN_S`, counted from a delivered excuse (`_excuse_end`)."""
        if conv_key in self._excuse_inflight:
            return False
        last = self._last_excuse_at.get(conv_key)
        if last is not None and time.monotonic() - last < _EXCUSE_COOLDOWN_S:
            return False
        self._excuse_inflight.add(conv_key)
        return True

    def _excuse_end(self, conv_key: str, delivered: bool) -> None:
        self._excuse_inflight.discard(conv_key)
        if not delivered:
            return
        self._last_excuse_at[conv_key] = time.monotonic()
        if len(self._last_excuse_at) > _MAX_REFUSALS_LOGGED:
            self._last_excuse_at.pop(next(iter(self._last_excuse_at)))

    # ---- the follow-up window ------------------------------------------------

    def _followup_table(self) -> dict:
        """conv -> (last_reply_at when they passed, who passed)."""
        return self.__dict__.setdefault("_followup_passed", {})

    def _followup_open(self, conv: str, user_id: str) -> bool:
        """Is `user_id`'s line in `conv` inside the follow-up window? Not once
        a follow-up turn on their line passed, until the character speaks."""
        last = self.last_reply_at[conv]
        if time.time() - last >= self.chat_followup_window_s:
            return False
        stamp, passers = self._followup_table().get(conv, (None, ()))
        # The stamp catches a send that did not go through `_spoke_in`.
        return stamp != last or user_id not in passers

    def _followup_pass(self, conv: str, user_id: str) -> None:
        """A follow-up turn on `user_id`'s line passed: close the window for
        them alone, so a bystander's PASS does not end the conversation."""
        table, last = self._followup_table(), self.last_reply_at[conv]
        stamp, passers = table.pop(conv, (None, set()))
        table[conv] = (last, (passers if stamp == last else set()) | {user_id})
        if len(table) > _MAX_REFUSALS_LOGGED:
            table.pop(next(iter(table)))

    def _spoke_in(self, conv: str) -> None:
        """The character spoke in `conv`: the window opens again for everyone."""
        self.last_reply_at[conv] = time.time()
        self._followup_table().pop(conv, None)

    def _index_own(self, mids, text: str) -> None:
        """Index what the character sent, so a quote of it reads as a call."""
        for sent_mid in mids or ():
            self._index_msg(sent_mid, f"{self.persona_name}: {text[:200]}")

    def _quotes_me(self, payload: dict) -> bool:
        """Does the message quote one of the character's own messages?"""
        own = self.persona_name + ": "
        for seg in payload.get("message", []) or []:
            if isinstance(seg, dict) and seg.get("type") == "reply":
                data = seg.get("data") or {}
                if data.get("quote_self") is True:
                    return True
                quoted = data.get("id")
                return (quoted is not None
                        and self._msg_index.get(str(quoted), "").startswith(own))
        return False

    def _model_failure_excuse(self, text: str = "") -> str:
        """A line for when the model call failed, in the language `text`, the
        message waiting for an answer, was written in."""
        code = chatlangs.detect(text, self.chat_lang) if text else self.chat_lang
        return random.choice(chatlangs.spec(code).failure_excuses)

    async def _within_turn_budget(self, model_work):
        """Await a turn's model work (`_think`, `_chat_dm`) under its one time
        budget; past it the work is abandoned and the turn fails like any
        other model failure."""
        budget = self.llm_timeout_s * _TURN_BUDGET_CALLS
        try:
            return await asyncio.wait_for(model_work, budget)
        except asyncio.TimeoutError:
            raise TimeoutError(
                f"no answer within the turn's {budget:g} s budget") from None

    async def _handle_inner(self, payload: dict, *,
                            proactive: bool = False) -> bool:
        if not self.enabled:
            return False
        if payload.get("post_type") and payload.get("post_type") != "message":
            return False

        # Remembered only after admission, so refused ids don't churn the ring;
        # str() because the catch-up sweep passes ints.
        mid = payload.get("message_id")
        if mid is not None and str(mid) in self._seen_msg_ids:
            return False

        message_type = payload.get("message_type", "group")
        user_id = str(payload.get("user_id", ""))

        # Only handle_event sets a sink, so /v1/onebot cannot pose as a connector.
        sink = current_sink.get()
        via_connector = sink is not None
        prefiltered = getattr(sink, "prefiltered", True)
        if message_type == "private":
            admins = self._admins()
            refusal = access.dm_refusal(
                user_id, admins, self._dm_allowlist(),
                via_connector=via_connector, prefiltered=prefiltered)
            if refusal:
                self._log_refusal(channels.dm_routing_key(user_id), refusal)
                return False
            is_admin = access.is_admin(user_id, admins)
            self._claim_connector_turn()
            if mid is not None:
                self._remember_msg_id(mid)
            # Connector-chosen keys go through the LRU cap.
            if via_connector and not channels.is_native(user_id):
                self._touch_connector_conv(channels.dm_routing_key(user_id))
            # Only the DM path can carry a proactive cue.
            return await self._handle_dm(user_id, payload,
                                              is_admin=is_admin,
                                              proactive=proactive)

        group_id = str(payload.get("group_id", "")).strip()
        if not group_id:
            return False
        refusal = access.group_refusal(
            group_id, self._group_allowlist(),
            via_connector=via_connector, prefiltered=prefiltered,
            user_id=user_id)
        if refusal:
            self._log_refusal(group_id, refusal)
            return False
        self._claim_connector_turn()
        if mid is not None:
            self._remember_msg_id(mid)
        # A group turn would buffer the cue as the sender's line; claimed and dropped.
        if proactive:
            logger.info("[Agent] proactive cue on a group conversation is not "
                        "supported; dropped (group=%s)", group_id)
            return False
        if via_connector and not channels.is_native(group_id):
            self._touch_connector_conv(group_id)

        has_image = any(
            isinstance(seg, dict) and seg.get("type") == "image"
            for seg in payload.get("message", [])
        )
        # A picture takes its place in line before it is read, as in a DM, so
        # a slow caption keeps arrival order and joins the turn after it.
        place = self._enter_line(group_id) if has_image else None
        try:
            text = await self._extract_text(payload)
            if not text:
                if place:
                    self._leave_line(group_id, *place)
                return False
            # ctrl_text drops link enrichment, so a fetched page cannot call the
            # bot or run memory commands; text keeps it, marked, for the prompt.
            ctrl_text = _strip_web_desc(text)

            sender = payload.get("sender") or {}  # may be present but null
            # Cleaned here: the name reaches prompts that bypass `_fmt_line`.
            nickname = (_clean_prompt_source(
                sender.get("card") or sender.get("nickname")) or "?")[:8]

            is_at = self._is_at_me(payload)
            is_called = self._names_me(ctrl_text)
            # Quoting its message is how people answer it on QQ.
            addressed = is_at or is_called or self._quotes_me(payload)
            is_noise = len(text.strip()) < 4 and not addressed

            is_admin_msg = access.is_admin(user_id, self._admins())
            is_command = addressed and self._is_memory_command(ctrl_text)

            # A directed reaction to a recent reply is adjudicated off the hot
            # path. A memory command is not one and must not consume the
            # pending reply.
            if self.react_learn_enabled and not is_command:
                _quote_mid, _quote_by_bot = "", None
                for _seg in payload.get("message", []) or []:
                    if isinstance(_seg, dict) and _seg.get("type") == "reply":
                        _qdata = _seg.get("data") or {}
                        _qid = _qdata.get("id")
                        if _qid is not None:
                            _quote_mid = str(_qid)
                        if _qdata.get("quote_self"):
                            _quote_by_bot = True
                        elif _qdata.get("quote_name") not in (None, "", self.persona_name):
                            _quote_by_bot = False
                        break
                _r_entry = self.pending_reactions.match(
                    group_id, sender_uid=user_id, quote_mid=_quote_mid,
                    at_bot=addressed, now=time.time(), quote_by_bot=_quote_by_bot)
                if _r_entry:
                    self._spawn(self._process_reaction(
                        _r_entry, text, nickname, user_id, is_admin_msg,
                        conv_id=group_id, is_dm=False))
        except BaseException:
            # An unread place left in line would hold the group forever.
            if place and place[1].absorb is None:
                self._leave_line(group_id, *place)
            raise

        def absorb() -> tuple[int, Optional[str]]:
            """Phase 1: buffer the message, run a memory command, stamp the
            seq. Returns (seq, the command's answer)."""
            # The cut must not leave an enrichment span open, and is marked.
            line = _truncate_framed(text, BUFFERED_LINE_CHARS)
            if len(text) > BUFFERED_LINE_CHARS:
                line += "…"
            self._append_buffer(group_id, nickname, line, user_id, at=sent_at)
            if mid is not None:
                self._index_msg(mid, f"{nickname}: {text[:200]}")
            self.last_activity_at[group_id] = time.time()
            self.active_users[group_id].append((user_id, nickname))
            self._maybe_consolidate(group_id, "lines")
            if stale and not is_command:
                # Context only: it neither counts toward a turn nor calls one.
                return 0, None
            if not is_noise:
                self.counters[group_id] += 1

            # A memory command answers at once: state settles here, the send
            # happens outside the lock.
            if addressed:
                answer = self._handle_memory_command(
                    group_id, ctrl_text, user_id, nickname)
                if answer is not None:
                    return 0, answer
                now = time.time()
                earlier = self._sticky_call.get(group_id)
                # Everyone who called since the last turn, which answers them all.
                callers = list(earlier.get("callers", ())) if (
                    earlier and now - earlier["ts"] < self.message_debounce_sec + 5.0
                ) else []
                self._sticky_call[group_id] = {
                    "user_id": user_id,
                    "nickname": nickname,
                    "ts": now,
                    "callers": (callers + [(nickname, user_id, ctrl_text[:200])]
                                )[-_MAX_CALLERS:],
                }
            self._msg_seq[group_id] += 1
            return self._msg_seq[group_id], None

        caller = user_id  # a sticky call rebinds user_id further down
        sent_at = message_time(payload)
        stale = (via_connector and sent_at is not None
                 and time.time() - sent_at > STALE_MESSAGE_S)

        async def say(outcome: tuple, *, background: bool = False) -> bool:
            return await self._say_memory_answer(
                group_id, outcome[1], caller, background=background)

        if place is None:
            absorbed, carried = await self._group_intake(
                group_id, absorb, say if is_command else None)
        else:
            absorbed, carried = await self._read_in_line(
                group_id, *place, absorb, say if is_command else None)
        if absorbed is None:
            # A message overtaken behind a turn, which the debounce would
            # drop, or a command that is answered once the turn is over.
            return False
        my_seq, mem_reply = absorbed

        if mem_reply is not None:
            try:
                handled = await say(absorbed)
            except Exception as e:
                if not carried:
                    raise
                # The response must still be given: others' answers ride in it.
                logger.warning("[Agent] memory command answer failed "
                               "(conversation=%s): %s", group_id, e)
                handled = False
            # Later commands whose answers had no way out but this response.
            await self._say_carried(group_id, carried)
            return handled
        if stale:
            logger.info("[Agent] a message from %d min ago was kept as context, "
                        "not answered (group=%s)",
                        int((time.time() - sent_at) // 60), group_id)
            return False

        # Debounce outside the lock so a burst batches into one turn.
        bare_after_strip = (
            text.replace(f"@{self.persona_name}", "").replace(self.persona_name, "").strip()
        )
        is_bare_call = addressed and len(bare_after_strip) <= 4
        debounce_sec = BARE_CALL_DEBOUNCE_S if is_bare_call else self.message_debounce_sec
        if debounce_sec > 0:
            try:
                await asyncio.sleep(debounce_sec)
            except asyncio.CancelledError:
                return False

        # A turn begun meanwhile without a newer message (a proactive one) is
        # waited out: two turns of one group never run side by side. So, for a
        # while, is a picture still being read in the line, which joins this
        # burst once read.
        unread_waited = 0.0
        while (self._msg_seq.get(group_id, 0) == my_seq
               and (running := self._pending_outbound.get(group_id)) is not None):
            if running.busy:
                await running.wait()
            elif (unread_waited < _UNREAD_WAIT_S
                  and any(held.absorb is None for held in running.held)):
                await asyncio.sleep(0.3)
                unread_waited += 0.3
            else:
                break
        if unread_waited:
            logger.debug("[Agent] waited %.1fs for a picture in group=%s",
                         unread_waited, group_id)

        # Phase 2: only the latest message of the burst reaches the model.
        async with self.locks[group_id]:
            if self._msg_seq.get(group_id, 0) != my_seq:
                logger.debug("[Agent] debounce drop (group=%s seq=%d latest=%d)",
                             group_id, my_seq, self._msg_seq.get(group_id, 0))
                return False

            sticky = self._sticky_call.get(group_id)
            sticky_active = (
                sticky is not None
                and time.time() - sticky["ts"] < self.message_debounce_sec + 5.0
            )
            never_replied = self.last_reply_at[group_id] == 0.0
            mode, why = choose_group_mode(
                addressed=addressed, is_admin=is_admin_msg,
                sticky_admin=(access.is_admin(sticky["user_id"], self._admins())
                              if sticky_active else None),
                in_followup=self._followup_open(group_id, user_id),
                counter=self.counters[group_id],
                trigger_count=self.chat_trigger_count,
                never_replied=never_replied)
            if mode == "followup" and is_noise:
                # A "lol" in the window takes no turn and no gate call.
                mode, why = "", "below the trigger count"
            if not mode:
                decision_log.record(group_id, mode, False, why, ctrl_text,
                                    sender=nickname)
                return False
            caller_override = None
            sender_name = nickname  # before a sticky call swaps in its caller
            if why == STICKY_CALL:
                user_id = sticky["user_id"]
                nickname = sticky["nickname"]
                caller_override = (nickname, user_id)
                logger.info(
                    "[Agent] sticky-call upgrade (group=%s caller=%s nick=%s age=%.1fs)",
                    group_id, user_id, nickname, time.time() - sticky["ts"],
                )

            self.counters[group_id] = 0
            self._sticky_call.pop(group_id, None)
            # Several people called within one debounce: one reply for all,
            # each one's latest words, the @ to the latest caller.
            by_uid: dict = {}
            if sticky is not None and mode in ("called", access.ADMIN_MODE):
                for entry in sticky.get("callers", ()):
                    by_uid.pop(entry[1], None)
                    by_uid[entry[1]] = entry
            together = list(by_uid.values()) if len(by_uid) > 1 else []

            skip = pacing_skip(mode, first_appearance=never_replied,
                               sleep_hour=TextProcessing._is_sleep_hour())
            if skip == SLEEP_WINDOW:
                logger.info("[Agent] PASS via sleep window (mode=%s, hour=%d, group=%s)",
                            mode, time.localtime().tm_hour, group_id)
                decision_log.record(group_id, mode, False, skip, ctrl_text,
                                    sender=sender_name)
                return False
            if skip:
                logger.info("[Agent] PASS via spontaneous skip (mode=judge, group=%s)", group_id)
                decision_log.record(group_id, mode, False, skip, ctrl_text,
                                    sender=sender_name)
                return False

            # The reply reserves its place before the model is asked: what
            # arrives from here on is held behind it.
            gate = self._begin_turn(group_id)

        asked = mode in ("called", access.ADMIN_MODE)
        log_ctx = f"mode={mode}, group={group_id}"

        async def draft() -> tuple:
            reply, intent, mem = await self._think(
                group_id, mode, text, caller_override=caller_override)
            # Asked and answered with nothing: a failure, not a decision.
            if asked and not (reply or "").strip():
                raise RuntimeError("the model answered nothing")
            final = self._final_reply(reply, log_ctx=log_ctx)
            if final.verdict == BLOCKED and asked:
                logger.info("[Agent] called draft blocked, retrying once (%s)", log_ctx)
                reply, retry_intent, retry_mem = await self._think(
                    group_id, mode, text, caller_override=caller_override,
                    retry_note=EMPTY_DRAFT_RETRY_NOTE)
                retried = self._final_reply(reply, log_ctx=log_ctx)
                if retried.verdict == SEND:
                    final, intent, mem = retried, retry_intent, retry_mem or mem
            return final, intent, mem

        # Read by the prompt (`_build_group_prompt`); `_think` keeps its shape.
        turn_callers = self.__dict__.setdefault("_turn_callers", {})
        if together:
            turn_callers[group_id] = together
        # Outside the group lock: no handler queues on it for the length of a
        # model call or of a send, each holding a webhook admission slot.
        try:
            try:
                final, _intent, auto_mem = await self._within_turn_budget(draft())
            except Exception as e:
                logger.warning("[Agent] LLM call failed (mode=%s): %s", mode, e)
                decision_log.record(group_id, mode, False, "model failed",
                                    ctrl_text, sender=sender_name)
                # Sent from a background task under the send lock, like a reply.
                if mode in ("called", access.ADMIN_MODE) and self._excuse_begin(group_id):
                    fallback = self._model_failure_excuse(text)

                    # Outlives the connector response, hence _send_background.
                    async def _send_fallback() -> None:
                        delivered = False
                        try:
                            async with self.send_locks[group_id]:
                                result = await self._send_background(
                                    group_id,
                                    lambda: self._send_group(
                                        group_id, fallback, user_id),
                                    reason="excuse")
                            if result.success:
                                delivered = True
                                async with self.locks[group_id]:
                                    self._spoke_in(group_id)
                                    self._append_buffer(
                                        group_id, self.persona_name, fallback)
                            else:
                                logger.warning(
                                    "[Agent] fallback delivery failed (group=%s)",
                                    group_id)
                        finally:
                            self._excuse_end(group_id, delivered)

                    self._spawn(_send_fallback())
                return False

            # A PASS commits nothing, neither core note nor auto-memory: both
            # describe a reply that was never sent.
            # Blocked is not a PASS: no follow-up reset.
            if final.verdict == BLOCKED:
                decision_log.record(group_id, mode, False, "blocked", ctrl_text,
                                    sender=sender_name)
                return False
            if final.verdict == PASS:
                logger.info("[Agent] PASS (mode=%s, group=%s)", mode, group_id)
                decision_log.record(group_id, mode, False, "passed", ctrl_text,
                                    sender=sender_name)
                if mode == "followup":
                    self._followup_pass(group_id, user_id)
                return False
            reply, at_uid = final.text, final.at_uid
            if not at_uid and asked:
                at_uid = user_id
            # Snapshot now: after the send the buffer has moved on.
            eval_ctx = [f"{m['name']}: {m['text']}" for m in list(self.buffers[group_id])[-5:]]

            async with self.send_locks[group_id]:
                send_result = await self._send_group(group_id, reply, at_uid)
            if not send_result.success and not send_result.partial:
                logger.warning("[Agent] reply delivery failed (mode=%s, group=%s)",
                               mode, group_id)
                decision_log.record(group_id, mode, False, "delivery failed",
                                    ctrl_text, sender=sender_name)
                return False

            # A partial send is committed as delivered; core note, auto-memory
            # and self-eval describe the whole answer and are withheld.
            committed = reply if send_result.success else send_result.delivered
            async with self.locks[group_id]:
                self._spoke_in(group_id)
                if committed:
                    self._append_buffer(group_id, self.persona_name, committed)
                    self._index_own(send_result.message_ids, committed)
                if send_result.success:
                    self._commit_core_memory(group_id, final.core_note)
                    if auto_mem:
                        self._save_auto_memory(group_id, auto_mem)
                    self._mark_used(group_id, committed)
            if not send_result.success:
                logger.warning(
                    "[Agent] reply PARTIALLY delivered (mode=%s, group=%s): "
                    "committed %d of %d chars",
                    mode, group_id, len(committed), len(reply))
        finally:
            turn_callers.pop(group_id, None)
            self._end_turn(group_id, gate)
        logger.info("[Agent] reply (mode=%s, group=%s): %s", mode, group_id, reply[:60])
        decision_log.record(group_id, mode, True, why, committed,
                            answered=ctrl_text, sender=sender_name)
        for caller_nick, caller_uid, said in together:
            if caller_uid != user_id:
                decision_log.record(group_id, mode, False, "answered together",
                                    said, sender=caller_nick)

        # Reactions are judged against what was actually delivered.
        if self.react_learn_enabled and committed:
            self.pending_reactions.record(
                group_id, reply=committed, ctx_lines=eval_ctx, mode=mode,
                intent=_intent,
                target_uid=self._reaction_recipient(group_id, mode, at_uid, user_id),
                target_name=nickname, mids=send_result.message_ids,
                ts=time.time(),
            )

        if self.on_reply and committed:
            await self.on_reply(group_id, committed)

        # Self-eval only for a complete reply.
        if self.eval_enabled and send_result.success:
            self._spawn(self._evaluate_reply(
                group_id, mode, text, reply, send_result.sticker_files,
                _intent, eval_ctx,
            ))

        return send_result.success
