"""The learning loops: self-eval, reaction adjudication, evolution.

Everything that turns a sent reply into training material for the next
one. All of it runs off the hot path and must never raise into the
reply pipeline."""

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

from . import evolution, reactions
from .pools import _needs_leading_newline

logger = logging.getLogger("agent")




class Learning:
    """Mixed into Agent; see agent.py."""

    async def _evaluate_reply(
        self, group_id: str, mode: str, user_msg: str, reply: str,
        sticker_files: list[str] | None = None,
        intent: str = "",
        ctx_msgs: list[str] | None = None,
    ) -> None:
        """Background quality eval. Scores 1-5 via the eval model, appends
        to eval.jsonl. Never raises — eval failures must not affect main
        reply flow.

        If the reply contained [STICKER:tag] markers and stickers were
        actually sent, ask the eval model for an extra sticker_score (1-5)
        and route it back to stickers.record_quality. Real conversation
        signal beats a one-shot LLM judgment for catching off-persona
        stickers.

        High-scoring replies (score >= 4) are also auto-appended to
        examples.jsonl with dedup, so the dynamic few-shot retrieval pool
        grows from real successes rather than staying frozen at bootstrap
        size."""
        try:
            # Context snapshotted at reply time (inside the group lock),
            # EXCLUDING the bot reply. Fall back to a live buffer read only if
            # the caller didn't pass a snapshot (older call sites / safety net).
            # ctx_lines is normalized to a list of "name: text" strings — the
            # example auto-append below reuses it; never index the strings as
            # dicts again.
            if ctx_msgs is not None:
                ctx_lines = list(ctx_msgs)
            else:
                ctx_lines = [
                    f"{m['name']}: {m['text']}"
                    for m in list(self.buffers[group_id])[-6:-1]
                ]
            ctx_text = "\n".join(ctx_lines)

            has_sticker = bool(sticker_files)
            sticker_clause = (
                "\nThis reply included a sticker. Also rate sticker_score (1-5):"
                " 5 = perfectly matches the mood/joke, 3 = neutral, 1 = entirely"
                " off (wrong emotion / tacky aesthetic / breaks character)."
            ) if has_sticker else ""
            json_schema = (
                '{"score": int 1-5, "reason": "one short sentence", "sticker_score": int 1-5}'
                if has_sticker else
                '{"score": int 1-5, "reason": "one short sentence"}'
            )

            eval_prompt = (
                f"Rate the quality of this group-chat reply. 1-5 scale: "
                f"5 = perfectly natural, 4 = solid, 3 = a bit off, "
                f"2 = clearly wrong, 1 = disaster.\n\n"
                f"Group chat context:\n---\n{ctx_text}\n---\n"
                f"{self.bot_name or 'bot'}'s reply: \"{reply}\"\n"
                f"{sticker_clause}\n"
                f"Persona: {self.bot_name or 'bot'} is a regular member of the "
                f"group, casual spoken style, has opinions, never customer-service "
                f"polite, picks up jokes where appropriate.\n"
                f"Judge by: 1) does the reply fit the context 2) does it match the "
                f"persona 3) does it sound natural rather than AI-flavored 4) is "
                f"the length reasonable.\n"
                f"Output JSON only: {json_schema}"
            )

            # Cross-vendor eval to avoid the main-model and judge-model sharing
            # the same RLHF reward lineage ("grading my own homework"). If the
            # configured eval_model name names a Moonshot/Kimi family model and
            # GLM_* credentials are populated, route through that endpoint; the
            # GLM_* config is OpenAI-compatible and is also used by the vision
            # path. Otherwise fall through to the main base_url/api_key.
            em = self.eval_model.lower()
            if ("moonshot" in em or "kimi" in em) and self.glm_api_key and self.glm_base_url:
                eval_url = f"{self.glm_base_url}/chat/completions"
                eval_auth = self.glm_api_key
            else:
                # /v1 prefix matches the main call path (_call_anthropic):
                # DeepSeek accepts both aliases, but other OpenAI-compatible
                # endpoints only serve /v1 — without it evals silently 404.
                eval_url = f"{self.base_url}/v1/chat/completions"
                eval_auth = self.api_key
            eval_payload = {
                "model": self.eval_model,
                "messages": [
                    {"role": "system", "content": "You are a strict reply quality evaluator. Output JSON only, no markdown."},
                    {"role": "user", "content": eval_prompt},
                ],
                "temperature": 0,
                # Evaluators (esp. kimi-k2.6) still emit chain-of-thought prose
                # before the JSON even with thinking disabled; too few tokens cut
                # the trailing JSON in half and the parse fails. 800 leaves room
                # for prose + JSON; the parser also salvages a truncated object.
                "max_tokens": 800,
                "response_format": {"type": "json_object"},
            }
            # K2-family reasoning models burn the budget on reasoning_content;
            # short-JSON evals need thinking disabled (same as vision path).
            # K2.6 also only accepts temperature=0.6.
            if "k2" in em:
                eval_payload["thinking"] = {"type": "disabled"}
                eval_payload["temperature"] = 0.6
            async with self._http(timeout=15) as client:
                r = await client.post(
                    eval_url,
                    headers={"Authorization": f"Bearer {eval_auth}"},
                    json=eval_payload,
                )
                r.raise_for_status()
                # Some reasoning models on OpenAI-compatible endpoints route
                # output into `reasoning_content` and leave `content` empty.
                # Fall back to either so we don't drop eval samples.
                _msg = r.json()["choices"][0]["message"]
                raw = (_msg.get("content") or _msg.get("reasoning_content") or "")

            # Robust parse: model may wrap JSON in ```json fences or prose.
            data = None
            try:
                data = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                m = re.search(r"\{.*\}", raw, re.S)
                if m:
                    try:
                        data = json.loads(m.group(0))
                    except json.JSONDecodeError:
                        data = None
            if not isinstance(data, dict):
                # Last-ditch salvage: pull the score straight out of truncated or
                # prose-wrapped output (K2.6 emits CoT prose then a possibly
                # cut-off JSON). Don't drop the whole eval just because the
                # closing brace never arrived.
                m_score = re.search(r'"score"\s*:\s*([1-5])', raw)
                if m_score:
                    data = {"score": int(m_score.group(1))}
                    m_reason = re.search(r'"reason"\s*:\s*"([^"]*)"', raw)
                    if m_reason:
                        data["reason"] = m_reason.group(1)
                    m_sticker = re.search(r'"sticker_score"\s*:\s*([1-5])', raw)
                    if m_sticker:
                        data["sticker_score"] = int(m_sticker.group(1))
                else:
                    logger.warning("[Agent] eval response not JSON mode=%s: %r", mode, raw[:200])
                    return
            score = int(data.get("score", 0))
            reason = str(data.get("reason", ""))[:200]
            sticker_score = data.get("sticker_score")
            try:
                sticker_score = int(sticker_score) if sticker_score is not None else None
            except (TypeError, ValueError):
                sticker_score = None

            record = {
                "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "group_id": group_id,
                "mode": mode,
                "user_msg": user_msg[:200],
                "reply": reply[:300],
                "score": score,
                "reason": reason,
            }
            if sticker_score is not None and sticker_files:
                record["sticker_score"] = sticker_score
                record["sticker_files"] = sticker_files
                for fn in sticker_files:
                    self.stickers.record_quality(fn, sticker_score)
            self._append_with_rotation(
                self.eval_file,
                json.dumps(record, ensure_ascii=False) + "\n",
            )

            if score <= 2:
                logger.warning("[Agent] LOW-SCORE reply (%d/5) mode=%s: %s | reason=%s",
                               score, mode, reply[:60], reason)
            else:
                logger.debug("[Agent] eval %d/5 mode=%s: %s", score, mode, reason)

            # High-score replies feed back into examples.jsonl so the dynamic
            # few-shot retrieval pool grows from real successes. Without this,
            # examples.jsonl is frozen at bootstrap and "dynamic retrieval" is
            # a scaffold over a static dataset. PASS (skip-reply marker) and
            # already-seen replies are filtered to keep the pool clean.
            #
            # Threshold is 5 (not 4) by default. Production audit showed many
            # eval models score generously — 97% of replies landing at >=4 in
            # one observation — which lets reply patterns the user explicitly
            # disliked sneak into the example pool and reinforce themselves
            # through retrieval. Requiring a top score keeps the bar high; if
            # your eval model scores conservatively you can lower this.
            reply_clean = reply.strip()
            if (score >= 5 and reply_clean and reply_clean.upper() != "PASS"
                    and reply_clean not in self._auto_examples_seen):
                ex = {
                    "ts": record["ts"],
                    "scenario": f"{mode}:{intent}" if intent else mode,
                    "mode": mode,
                    "intent": intent,
                    "context": ctx_lines,
                    "reply": reply_clean,
                    "score": score,
                }
                self._append_example_with_trim(
                    json.dumps(ex, ensure_ascii=False) + "\n",
                )
                self._auto_examples_seen.add(reply_clean)
                # Cap the in-memory dedup set; on reload from disk the full
                # set is rebuilt, so light pruning here is harmless.
                if len(self._auto_examples_seen) > 2000:
                    self._auto_examples_seen = set(
                        list(self._auto_examples_seen)[-1000:]
                    )
        except Exception as e:
            logger.warning("[Agent] reply evaluation failed: %s: %s",
                           type(e).__name__, e)

    def _append_example_with_trim(self, line: str, max_bytes: int = 5_000_000) -> None:
        """Append an auto-harvested example to the runtime pool, keeping it
        bounded.

        Two caps, and **neither ever drops a hand-approved entry**. The data/
        seed is a separate read-only file and is never touched at all, but the
        runtime file is not purely machine-written either: prompt_lab.py writes
        replies you approved into it, without the "score" the self-eval and
        reaction channels stamp on theirs. That field is what tells the two
        apart here — and it is why this trims rather than rotating the way
        _append_with_rotation does.

        - EXAMPLES_MAX_AUTO (primary): keep the newest N auto-banked entries.
          Retrieval surfaces 4 per turn no matter how many are on disk, so a
          bigger pool only lengthens the per-turn relevance scan and lets
          entries written under an older prompt outvote recent ones.
        - max_bytes (backstop): if the pool is somehow still over the byte
          ceiling — no count cap configured, or pathologically long entries —
          drop the oldest auto entries until back under half the budget, so
          appends don't rewrite the file every time.

        Both rewrites are atomic (.tmp + replace)."""
        path = self.examples_file
        path.parent.mkdir(parents=True, exist_ok=True)
        if self.examples_max_auto > 0:
            try:
                trimmed = evolution.trim_pool(
                    path, max_auto=self.examples_max_auto,
                    is_auto=lambda r: "score" in r,
                )
                if trimmed:
                    logger.info("[Agent] examples.jsonl auto-pool trimmed: "
                                "%d -> %d entries (cap=%d)",
                                trimmed[0], trimmed[1], self.examples_max_auto)
            except OSError as e:
                logger.warning("[Agent] examples auto-pool trim failed: %s", e)
        try:
            sz = path.stat().st_size if path.exists() else 0
        except OSError:
            sz = 0
        if path.exists() and sz + len(line.encode("utf-8")) > max_bytes:
            try:
                lines = [l for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
                curated = [l for l in lines if '"score"' not in l]
                auto = [l for l in lines if '"score"' in l]
                budget = max_bytes // 2  # trim to half budget so appends don't rewrite every time
                kept: list[str] = []
                used = sum(len(l.encode("utf-8")) + 1 for l in curated)
                for l in reversed(auto):  # newest first
                    b = len(l.encode("utf-8")) + 1
                    if used + b > budget:
                        break
                    kept.append(l)
                    used += b
                new_lines = curated + list(reversed(kept))
                tmp = path.with_suffix(path.suffix + ".tmp")
                tmp.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
                tmp.replace(path)
                logger.info("[Agent] examples.jsonl trimmed: %d -> %d lines (%d curated kept)",
                            len(lines), len(new_lines), len(curated))
            except OSError as e:
                logger.warning("[Agent] examples trim failed: %s", e)
        try:
            with path.open("a", encoding="utf-8") as f:
                if _needs_leading_newline(path):
                    f.write("\n")
                f.write(line)
        except OSError as e:
            logger.warning("[Agent] examples append failed: %s", e)

    def _append_feedback_pair(self, pair: dict) -> int:
        """Append one preference pair to the runtime feedback pool. Returns 1
        if written.

        Wraps evolution.append_jsonl with the same auto-pool cap examples get
        (FEEDBACK_MAX_AUTO; machine pairs carry a "src", pairs you rated
        through prompt_lab.py don't and are never dropped — nor is the data/
        seed, which nothing writes to). Trimming first also removes a real
        failure mode: append_jsonl REFUSES to write past FEEDBACK_MAX_BYTES,
        so an unattended deployment would silently stop learning the day the
        file filled up — with reaction learning as the primary signal, that is
        the whole loop going quiet with nothing in the log to say so."""
        self.feedback_file.parent.mkdir(parents=True, exist_ok=True)
        if self.feedback_max_auto > 0:
            try:
                trimmed = evolution.trim_pool(
                    self.feedback_file, max_auto=self.feedback_max_auto,
                    is_auto=lambda r: bool(r.get("src")),
                )
                if trimmed:
                    logger.info("[Agent] feedback.jsonl auto-pool trimmed: "
                                "%d -> %d pairs (cap=%d)",
                                trimmed[0], trimmed[1], self.feedback_max_auto)
            except OSError as e:
                logger.warning("[Agent] feedback auto-pool trim failed: %s", e)
        written = evolution.append_jsonl(self.feedback_file, [pair])
        if not written:
            logger.warning("[Agent] feedback pair NOT written — %s is at its "
                           "byte ceiling and every remaining entry is "
                           "hand-approved", self.feedback_file.name)
        return written

    @staticmethod
    def _append_with_rotation(path: Path, line: str, max_bytes: int = 5_000_000) -> None:
        """Append a line; rotate path to path.old when it would exceed max_bytes."""
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            sz = path.stat().st_size if path.exists() else 0
        except OSError:
            sz = 0
        if sz > max_bytes:
            old = path.with_suffix(path.suffix + ".old")
            try:
                if old.exists():
                    old.unlink()
                path.rename(old)
            except OSError as e:
                logger.warning("[Agent] log rotation failed for %s: %s", path, e)
        try:
            with path.open("a", encoding="utf-8") as f:
                if _needs_leading_newline(path):
                    f.write("\n")
                f.write(line)
        except OSError as e:
            logger.warning("[Agent] log write failed for %s: %s", path, e)

    async def _process_reaction(self, entry: dict, reaction_text: str,
                                reactor_name: str, reactor_uid: str,
                                is_owner: bool, conv_id: str = "",
                                is_private: bool = False) -> None:
        """Adjudicate a directed user reaction to a pending bot reply and
        learn from it. Accepted corrections become feedback pairs; genuine
        positives bank the reply as an example; accepted rejections arm two
        recovery paths — retry-completion (the bot's next reply, if the user
        then accepts it, closes a BAD->OK pair on its own) and a delayed,
        cooldown-limited elicitation ask. Every adjudication is audited in
        candidates.jsonl. Never raises."""
        try:
            # Hard poison shield: users whose teachings are consistently
            # dismissed stop costing adjudicator calls at all (BB3x lesson).
            if not is_owner and self.teacher_stats.hard_block(reactor_uid):
                evolution.append_jsonl(self.candidates_file, [{
                    "src": "user_reaction",
                    "ts": datetime.now().isoformat(timespec="seconds"),
                    "reactor": reactor_name, "is_owner": False,
                    "reaction_text": (reaction_text or "")[:120],
                    "applied": "blocked", "reason": "hard-blocked teacher",
                }], max_bytes=20_000_000)
                return
            history_line = ("" if is_owner else
                            self.teacher_stats.history_line(reactor_uid,
                                                            self.agent_lang))
            prompt = reactions.build_adjudicator_prompt(
                entry, reaction_text, reactor_name, is_owner,
                self.bot_name, self.agent_lang, reactor_history=history_line)
            raw = await self._call_anthropic(
                "", [{"role": "user", "content": prompt}],
                model=self.react_model, max_tokens=400, enable_search=False)
            adj = reactions.parse_adjudication(raw)
            if not adj:
                return
            now = datetime.now().isoformat(timespec="seconds")
            wrote = False

            # Dedup keys mean parsing the seed AND runtime feedback files,
            # which are allowed to reach 5 MB — tens of milliseconds on the
            # event loop. Load them at most once per adjudication (both
            # branches below can need them), and only when a write is
            # actually on the table.
            fb_keys: set | None = None

            def _fresh_pair(p: dict) -> bool:
                nonlocal fb_keys
                if fb_keys is None:
                    fb_keys = evolution.load_feedback_keys(
                        [self.feedback_seed_file, self.feedback_file])
                key = (p["reply"], p["better"])
                if key in fb_keys:
                    return False
                fb_keys.add(key)
                return True

            # Retry-completion: this reply was the bot's second attempt after
            # a rejection. The user reacting positively — or just moving on —
            # accepts the fix, closing (rejected -> retry) into a pair with
            # zero user effort.
            if entry.get("fixes") and adj["reaction"] in ("positive", "neutral"):
                fpair = reactions.fix_pair(entry["fixes"], entry["reply"], now)
                if fpair is not None and _fresh_pair(fpair):
                    if self._append_feedback_pair(fpair) > 0:
                        wrote = True
                        logger.info(
                            "[Agent] reaction learn (retry-completion): "
                            "BAD %r -> OK %r",
                            fpair["reply"][:50], fpair["better"][:50])

            if adj["accept"]:
                pair = reactions.to_feedback_pair(entry, adj, now, reactor_name)
                if pair is not None and _fresh_pair(pair):
                    if self._append_feedback_pair(pair) > 0:
                        wrote = True
                        logger.info(
                            "[Agent] reaction learn (%s by %s): BAD %r -> OK %r",
                            adj["reaction"], reactor_name,
                            pair["reply"][:50], pair["better"][:50])
                ex = reactions.to_example(entry, adj, now)
                if ex is not None and ex["reply"] not in self._auto_examples_seen:
                    self._append_example_with_trim(
                        json.dumps(ex, ensure_ascii=False) + "\n")
                    self._auto_examples_seen.add(ex["reply"])
                    wrote = True
                    logger.info("[Agent] reaction learn: reply banked as example (%s)",
                                adj.get("scenario") or entry.get("mode", ""))
                # Accepted rejection with nothing concrete learned: arm both
                # recovery paths.
                if adj["reaction"] == "rejection" and conv_id:
                    self.pending_reactions.note_rejection(
                        conv_id, entry, time.time())
                    if self.react_elicit and adj.get("ask"):
                        self._spawn(self._maybe_elicit(
                            conv_id, entry, adj.get("ask", ""),
                            reactor_uid, is_private))

            # Teaching reputation: count corrective acts only (not positives),
            # never the owner.
            if not is_owner and adj["reaction"] in ("correction", "rejection"):
                self.teacher_stats.update(reactor_uid, reactor_name,
                                          accepted=adj["accept"])

            audit = {
                "src": "user_reaction", "ts": now,
                "reaction": adj["reaction"], "reactor": reactor_name,
                "is_owner": bool(is_owner), "reason": adj["reason"],
                "bot_reply": str(entry.get("reply") or "")[:120],
                "reaction_text": (reaction_text or "")[:120],
                "applied": "auto" if wrote else "rejected",
            }
            if entry.get("fixes"):
                audit["via"] = "retry-completion-candidate"
            evolution.append_jsonl(self.candidates_file, [audit],
                                   max_bytes=20_000_000)
        except Exception as e:
            logger.warning("[Agent] reaction processing failed: %s: %s",
                           type(e).__name__, e)

    async def _maybe_elicit(self, conv_id: str, entry: dict, ask: str,
                            reactor_uid: str, is_private: bool) -> None:
        """Delayed elicitation: wait out the bot's own normal reply to the
        rejection, then — if the user still hasn't supplied a correction and
        the per-conversation cooldown allows — ask in the bot's voice what
        they actually meant. The rejector's next message (even without an @)
        is then attributed to the ORIGINAL rejected reply, so their answer
        adjudicates as a proper correction. Never raises."""
        try:
            if not ask:
                return
            await asyncio.sleep(max(0.0, self.react_elicit_delay))
            now_mono = time.time()
            if now_mono - self._last_elicit_at[conv_id] < self.react_elicit_cooldown:
                return
            self._last_elicit_at[conv_id] = now_mono
            if is_private:
                uid = conv_id.split(":", 1)[1] if ":" in conv_id else reactor_uid
                result = await self._send_private_qq(uid, ask)
                if result.success:
                    self.private_history.setdefault(uid, []).append(
                        {"role": "assistant", "content": ask})
            else:
                async with self.send_locks[conv_id]:
                    result = await self._send_qq(conv_id, ask, reactor_uid)
                if result.success:
                    self._append_buffer(conv_id, self.bot_name, ask)
            if not result.success:
                logger.warning("[Agent] elicitation delivery failed (conv=%s, partial=%s)",
                               conv_id, result.partial)
                return
            # Register the ORIGINAL rejected reply as an elicited pending
            # entry: the rejector's answer will adjudicate against it.
            self.pending_reactions.record(
                conv_id, reply=entry["reply"], ctx_lines=entry.get("ctx_lines", []),
                mode=entry.get("mode", "called"), intent=entry.get("intent", ""),
                target_uid=reactor_uid, elicited_uid=reactor_uid, ts=time.time())
            logger.info("[Agent] elicitation sent (conv=%s): %s", conv_id, ask[:60])
        except Exception as e:
            logger.warning("[Agent] elicitation failed: %s: %s",
                           type(e).__name__, e)

    # ---------------- Self-evolution (eval -> feedback, unattended) ----------------
    async def loop_evolve(self) -> None:
        """Background loop that turns the agent's own low-score evals into
        BAD/OK preference pairs in feedback.<lang>.jsonl. Opt-in (EVOLVE_AUTO).
        The positive half (high scores -> examples.jsonl) already runs inline
        in _evaluate_reply; this loop closes the negative half."""
        if not self.enabled or not self.evolve_auto:
            return
        if not self.eval_enable:
            logger.warning("[Agent] EVOLVE_AUTO=true but EVAL_ENABLE=false — "
                           "no scores are being produced, evolve loop idle")
        logger.info("[Agent] evolve loop ON (every %.1fh, score<=%d, batch=%d, model=%s)",
                    self.evolve_interval / 3600, self.evolve_threshold,
                    self.evolve_batch, self.evolve_model)
        while True:
            try:
                await asyncio.sleep(self.evolve_interval)
                await self._evolve_tick()
            except asyncio.CancelledError:
                return
            except Exception as e:
                logger.warning("[Agent] evolve tick failed: %s: %s",
                               type(e).__name__, e)

    async def _evolve_tick(self) -> int:
        """One pass: diagnose up to evolve_batch new low-score evals, append
        usable pairs to feedback. Returns the number of pairs added."""
        evals = evolution.load_evals(self.eval_file, self.evolve_threshold)
        reviewed = evolution.load_reviewed_ts(self.candidates_file)
        pending = [e for e in evals if e.get("ts") not in reviewed][: self.evolve_batch]
        if not pending:
            return 0
        existing = evolution.load_feedback_keys(
            [self.feedback_seed_file, self.feedback_file])
        now = datetime.now().isoformat(timespec="seconds")
        added = 0
        for ev in pending:
            prompt = evolution.build_review_prompt(ev, self.agent_lang)
            raw = await self._call_anthropic(
                "", [{"role": "user", "content": prompt}],
                model=self.evolve_model, max_tokens=600, enable_search=False,
            )
            diag = evolution.parse_review(raw)
            if not diag:
                continue
            pair = evolution.pair_from_candidate(
                evolution.candidate_record(ev, diag), now)
            usable = pair is not None and (pair["reply"], pair["better"]) not in existing
            # Audit trail first, so a crash between the two writes re-reviews
            # nothing (the entry is marked reviewed) rather than double-appends.
            evolution.append_jsonl(
                self.candidates_file,
                [evolution.candidate_record(ev, diag,
                                            applied="auto" if usable else "rejected")],
                max_bytes=20_000_000,
            )
            if usable:
                added += self._append_feedback_pair(pair)
                existing.add((pair["reply"], pair["better"]))
        if added:
            logger.info("[Agent] evolve: +%d feedback pairs from %d low-score evals",
                        added, len(pending))
        return added
