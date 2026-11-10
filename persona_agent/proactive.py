"""Speaking first: the proactive loops for groups and DMs."""
from __future__ import annotations

import asyncio
import logging
import random
import time

from . import access
from . import channels
from . import decision_log
from .decision import SEND
from .textproc import (
    TextProcessing,
)

logger = logging.getLogger("agent")


class Proactive:
    async def loop_proactive(self) -> None:
        """Opt-in loop (PROACTIVE_ENABLED): at most one unprompted group or DM
        message per tick, never in sleep hours."""
        if not self.enabled or not self.proactive_enabled:
            return
        logger.info(
            "[Agent] proactive loop ON (tick=%ds, group_silence=%ds, group_cooldown=%ds, p=%.2f)",
            self.proactive_interval_s, self.proactive_min_silence_s,
            self.proactive_cooldown_s, self.proactive_prob,
        )
        while True:
            try:
                await asyncio.sleep(self.proactive_interval_s)
                if TextProcessing._is_sleep_hour():
                    continue
                acted = await self._maybe_proactive_groups()
                if not acted:
                    await self._maybe_proactive_dms()
            except asyncio.CancelledError:
                return
            except Exception as e:
                logger.warning("[Agent] proactive loop iteration failed: %s", e)

    def _openers(self) -> dict[str, float]:
        """When the loop's last opener went out: group id, or "dm:<uid>"."""
        return vars(self).setdefault("_opener_sent_at", {})

    def _proactive_platform_ok(self, key: str) -> bool:
        """Whether PROACTIVE_PLATFORMS lets the loop speak first on the
        platform of `key` (a routing key or a user id); empty allows all."""
        return (not self.proactive_platforms
                or channels.platform_of(key) in self.proactive_platforms)

    async def _maybe_proactive_groups(self) -> bool:
        """At most one proactive group message per tick. Returns True if sent."""
        now = time.time()
        groups = list(self.buffers.keys()) or list(self._group_allowlist())
        random.shuffle(groups)
        for gid in groups:
            # DMs are the DM pass's; an unreachable room costs no model call.
            if (channels.is_dm(gid) or not self._proactive_platform_ok(gid)
                    or self._background_route(gid) is None):
                continue
            last_act = self.last_activity_at.get(gid, 0.0)
            # Only a group active this run, and quiet long enough.
            if not last_act or now - last_act < self.proactive_min_silence_s:
                continue
            # The last thing said there was an opener nobody answered.
            if self._openers().get(gid, 0.0) > last_act:
                continue
            if now - self.last_proactive_at.get(gid, 0.0) < self.proactive_cooldown_s:
                continue
            if now - self.last_reply_at.get(gid, 0.0) < self.proactive_cooldown_s:
                continue
            if random.random() > self.proactive_prob:
                continue
            # A turn in flight, or a message still being read: not quiet.
            if gid in self._pending_outbound:
                continue
            # A turn like any other: what arrives meanwhile waits behind it.
            gate = self._begin_turn(gid)
            try:
                if await self._proactive_group_turn(gid, now):
                    return True
            finally:
                self._end_turn(gid, gate)
        return False

    async def _proactive_group_turn(self, gid: str, now: float) -> bool:
        """Ask the model for an opener and send it. True if the room read
        any of it."""
        try:
            reply, intent, mem = await self._within_turn_budget(
                self._think(gid, mode="proactive"))
        except Exception as e:
            logger.warning("[Agent] proactive group think failed (%s): %s", gid, e)
            decision_log.record(gid, "proactive", False, "model failed")
            return False
        # Mark the attempt either way so a PASS doesn't re-roll every tick.
        self.last_proactive_at[gid] = now
        final = self._final_reply(reply, log_ctx=f"mode=proactive, group={gid}")
        if final.verdict != SEND:
            decision_log.record(gid, "proactive", False, "proactive")
            return False
        reply, at_uid = final.text, final.at_uid
        # Buffered below: NapCat does not echo the bot's own messages.
        async with self.send_locks[gid]:
            result = await self._send_background(
                gid, lambda: self._send_group(gid, reply, at_uid),
                reason="proactive")
        if not result.success:
            logger.warning(
                "[Agent] proactive group delivery failed (%s, partial=%s)",
                gid, result.partial)
            # The room read the delivered part, so it is on record.
            if result.partial and result.delivered:
                self.last_reply_at[gid] = now
                self._openers()[gid] = now
                self._append_buffer(gid, self.persona_name, result.delivered)
                decision_log.record(gid, "proactive", True, "proactive",
                                    result.delivered)
            else:
                decision_log.record(gid, "proactive", False, "delivery failed")
            return result.partial
        # Read before the opener joins the buffer: what it was said after.
        ctx_lines = [f"{m['name']}: {m['text']}"
                     for m in list(self.buffers[gid])[-5:]]
        self.last_reply_at[gid] = now
        self._openers()[gid] = now
        self._append_buffer(gid, self.persona_name, reply)
        self._commit_core_memory(gid, final.core_note)
        if mem:
            self._save_auto_memory(gid, mem)
        decision_log.record(gid, "proactive", True, "proactive", reply)
        # A quote or an @ in answer to it is a reaction like any other.
        if self.react_learn_enabled:
            self.pending_reactions.record(
                gid, reply=reply, ctx_lines=ctx_lines, mode="proactive",
                intent=intent, target_uid=at_uid or "", target_name="",
                mids=result.message_ids, ts=time.time())
        logger.info("[Agent] proactive group message (%s): %r", gid, reply[:60])
        return True

    async def _maybe_proactive_dms(self) -> bool:
        """At most one proactive DM per tick, to someone who DMed the bot this
        run and may be reached unprompted. True if sent."""
        now = time.time()
        admins = self._admins()
        allowed = self._dm_allowlist()
        # On QQ the lists name who may be DMed; elsewhere the connector
        # filtered who reached the DM, and admission is checked again below.
        targets = {uid for uid in allowed | admins if channels.is_native(uid)}
        targets.update(uid for uid in list(self.last_dm_activity_at)
                       if not channels.is_native(uid))
        # Sorted before the shuffle: a set's order differs from run to run,
        # and a seeded test must be able to replay the pick.
        targets = sorted(uid for uid in targets if self._proactive_platform_ok(uid))
        random.shuffle(targets)
        for uid in targets:
            pkey = channels.dm_routing_key(uid)
            route = self._background_route(pkey)
            if route is None:
                continue
            if route != "onebot" and access.dm_refusal(
                    uid, admins, allowed, via_connector=True,
                    prefiltered=route.get("prefiltered", True)):
                continue
            last_act = self.last_dm_activity_at.get(uid, 0.0)
            # Don't cold-DM someone who never messaged the bot.
            if not last_act or now - last_act < self.proactive_dm_min_silence_s:
                continue
            # The learning key, which eviction also pops.
            key = channels.dm_learning_key(uid)
            if now - self.last_proactive_at.get(key, 0.0) < self.proactive_dm_cooldown_s:
                continue
            # They have not answered the last opener.
            if self._openers().get(key, 0.0) > last_act:
                continue
            if random.random() > self.proactive_dm_prob:
                continue
            # Their own message is being read or answered: not the moment.
            if pkey in self._pending_outbound:
                continue
            # A turn like any other: what they write meanwhile waits behind
            # it, and no lock is held while the model is asked.
            gate = self._begin_turn(pkey)
            try:
                if await self._proactive_dm_turn(
                        uid, pkey, access.is_admin(uid, admins), now):
                    return True
            finally:
                self._end_turn(pkey, gate)
        return False

    async def _proactive_dm_turn(self, uid: str, pkey: str, is_admin: bool,
                                 now: float) -> bool:
        """Ask the model for an opener and send it. True if they read any
        of it."""
        history = list(self.dm_history.get(uid, []))[-10:]
        try:
            reply, mem = await self._within_turn_budget(self._chat_dm(
                history, is_admin=is_admin, proactive=True, pkey=pkey))
        except Exception as e:
            logger.warning("[Agent] proactive DM failed (%s): %s", uid, e)
            decision_log.record(pkey, "proactive", False, "model failed")
            return False
        # Marked either way so a PASS doesn't re-roll every tick; the
        # learning key, which eviction also pops.
        self.last_proactive_at[channels.dm_learning_key(uid)] = now

        final = self._final_reply(reply, log_ctx=f"proactive DM user={uid}")
        if final.verdict != SEND:
            decision_log.record(pkey, "proactive", False, "proactive")
            return False
        reply = final.text

        async with self._dm_sending(pkey):
            result = await self._send_background(
                pkey, lambda: self._send_dm(uid, reply), reason="proactive")
        if not result.success:
            logger.warning("[Agent] proactive DM delivery failed (%s, partial=%s)",
                           uid, result.partial)
            # They read the delivered part; keep it on record.
            if result.partial and result.delivered:
                self.dm_history.setdefault(uid, []).append(
                    {"role": "assistant", "content": result.delivered})
                self._openers()[channels.dm_learning_key(uid)] = now
                decision_log.record(pkey, "proactive", True, "proactive",
                                    result.delivered)
            else:
                decision_log.record(pkey, "proactive", False, "delivery failed")
            return result.partial
        self.dm_history.setdefault(uid, []).append(
            {"role": "assistant", "content": reply})
        self._openers()[channels.dm_learning_key(uid)] = now
        decision_log.record(pkey, "proactive", True, "proactive", reply)
        self._commit_core_memory(pkey, final.core_note)
        if mem:
            self._save_auto_memory(pkey, mem)
        logger.info("[Agent] proactive DM (%s): %r", uid, reply[:60])
        return True
