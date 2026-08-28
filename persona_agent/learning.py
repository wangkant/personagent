"""The learning loops: self-eval, reaction adjudication, evolution.

Everything that turns a sent reply into training material for the next one. All
of it runs off the hot path and must never raise into the reply pipeline.

Nothing in here writes a retrieval pool directly. Every automatic signal takes
the same three steps, and the order is the point:

    1. record what happened          -> evidence.py   (append-only, immutable)
    2. propose what should change     -> candidates.py (versioned, inert)
    3. ask whether it may             -> promotion.py  (corroboration required)

Only step 3 succeeding materializes anything a future reply can see. A reaction
on its own is testimony, not instruction."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from datetime import datetime
from pathlib import Path


from . import candidates, channels, evidence, evolution, promotion, reactions
from .pools import _needs_leading_newline
from .storage import append_jsonl_unlocked, append_lock

logger = logging.getLogger("agent")




class Learning:
    """Mixed into Agent; see agent.py."""

    # ---------------- Evidence -> candidate -> promotion ----------------

    @staticmethod
    def _conv_platform(conv_id: str) -> str:
        """Platform namespace of a conversation id.

        Gateway conversations are namespaced ``<platform>:<id>`` (gateway.py);
        QQ group ids are bare numbers and QQ DMs are ``dm:<uid>``. Evidence from
        two platforms is never combined, so this has to be right rather than
        merely plausible."""
        # `channels` owns the key vocabulary. `dm:` and `private:` are DM
        # MARKERS, not platforms, and reading the whole prefix as QQ stamped
        # every Telegram and Discord DM `platform="qq"` — see the module
        # docstring for what that let `scope_compatible` combine.
        return channels.platform_of(conv_id)

    def _scope_fields(self, conv_id: str) -> dict:
        """The scope every evidence event carries: which character, which
        language, which room. Two events may only corroborate each other when
        these agree (see promotion.scope_compatible)."""
        return {
            "lang": self.agent_lang,
            "platform": self._conv_platform(conv_id),
            "conv_id": str(conv_id or ""),
            "persona": self.bot_name or "",
            "persona_hash": self.persona_hash,
            "persona_version": self.persona_version,
        }

    def _record_evidence(self, event: dict) -> bool:
        """Append one immutable evidence event. False when already recorded.

        Called for every adjudicated reaction, accepted or not: the log is a
        record of what happened, and "a stranger tried to teach the bot
        something and was dismissed" is exactly the kind of thing worth being
        able to look up later."""
        try:
            return self.evidence_log.append(event)
        except Exception as e:
            logger.warning("[Agent] evidence append failed: %s: %s",
                           type(e).__name__, e)
            return False

    def _corroborate_existing(self, event: dict, ts: str) -> list[str]:
        """Offer a new event to every proposal already waiting for a second voice.

        Without this, corroboration would only ever be noticed by the call that
        *proposes* something — so a rejection arriving after a correction, which
        is the ordinary shape of "no. no, still wrong", would be recorded and
        then ignored. The event is linked to each pending candidate it supports
        and the policy is re-run. Returns the ids promoted as a result."""
        ledger = self.candidate_ledger
        promoted: list[str] = []
        try:
            for cand in ledger.pending():
                if not promotion.supports_candidate(event, cand,
                                                   policy=self.promotion_policy):
                    continue
                cid = cand["candidate_id"]
                if not ledger.link_evidence(cid, [event["event_id"]], ts=ts,
                                            note="late corroboration"):
                    continue
                decision = self._decide_promotion(cid)
                if decision.promote and ledger.promote(
                        cid, ts=ts, actor="auto", reason=decision.reason,
                        evidence=[event["event_id"]]):
                    promoted.append(cid)
                    logger.info("[Agent] candidate PROMOTED %s (corroborated): "
                                "%s", cid, decision.reason)
            if promoted:
                self._rebuild_promoted_views()
        except Exception as e:
            logger.warning("[Agent] corroboration scan failed: %s: %s",
                           type(e).__name__, e)
        return promoted

    #: The audit trail's byte ceiling. `candidates.jsonl` has no rotation,
    #: unlike `eval.jsonl`, so reaching this is terminal rather than a wrap.
    CANDIDATE_AUDIT_MAX_BYTES = 20_000_000

    def _audit_candidate(self, ev: dict, diag: dict, applied: str) -> None:
        """Write one review audit row — and SAY SO when the file refuses it.

        `src_eval_ts` in this file is the only review-dedup key, so a row that
        does not land means the same eval is re-diagnosed on every tick,
        forever, at one model call each. `evolution.append_jsonl` refuses
        silently past its byte cap and returns 0, and nobody read that return
        — so the loop kept spending and the audit trail, which is the only
        record of WHY the agent talks the way it does, went quiet at the same
        moment and for the same reason."""
        try:
            written = evolution.append_jsonl(
                self.candidates_file,
                [evolution.candidate_record(ev, diag, applied=applied)],
                max_bytes=self.CANDIDATE_AUDIT_MAX_BYTES,
            )
        except Exception as e:
            logger.warning("[Agent] candidate audit append failed: %s: %s",
                           type(e).__name__, e)
            return
        if not written:
            logger.error(
                "[Agent] candidates.jsonl has hit its %d-byte cap — the audit "
                "row for %s was DROPPED, so that eval will be re-diagnosed on "
                "every evolve tick and the audit trail is no longer being "
                "written. Archive or truncate the file.",
                self.CANDIDATE_AUDIT_MAX_BYTES, str(ev.get("ts", "?"))[:19])

    def _record_and_corroborate(self, event: dict, ts: str) -> bool:
        """Record an event, then let it speak for whatever is already waiting."""
        fresh = self._record_evidence(event)
        if fresh:
            self._corroborate_existing(event, ts)
        return fresh

    def _propose_candidate(self, event: dict, ctype: str, payload: dict,
                           ts: str) -> str:
        """Propose (or refresh) a candidate for `event`, then let the policy
        decide whether it may take effect. Returns a short outcome label:
        ``promoted`` / ``proposed`` / ``held`` / ``blocked`` / ``error``.

        Corroboration is *discovered*, not threaded through call sites: every
        compatible event already in the log that argues for this same proposal
        is linked here. That is what lets an explicit correction be backed by
        the rejection that preceded it two messages earlier — the two arrived in
        different adjudicator calls and neither knew about the other."""
        try:
            ledger = self.candidate_ledger
            scope = candidates.scope_from_event(event)
            cand = candidates.make_candidate(
                ctype=ctype, scope=scope, payload=payload,
                evidence=[event["event_id"]], created_at=ts,
                adjudication_version=event.get("adjudicator_prompt_version", ""))
            cid = cand["candidate_id"]
            before = ledger.get(cid)
            already = bool(before) and event["event_id"] in (before.get("evidence") or [])
            projected, created = ledger.propose(cand)
            if already and not created:
                return "held"  # nothing new to weigh
            support = [
                e["event_id"] for e in self.evidence_log.all()
                if promotion.supports_candidate(e, projected,
                                                policy=self.promotion_policy)
            ]
            ledger.link_evidence(cid, support, ts=ts, note="corroboration scan")
            decision = self._decide_promotion(cid)
            label = "proposed" if created else "held"
            if decision.promote:
                if ledger.promote(cid, ts=ts, actor="auto",
                                  reason=decision.reason,
                                  evidence=[event["event_id"]]):
                    self._rebuild_promoted_views()
                    logger.info("[Agent] candidate PROMOTED %s (%s): %s — %r",
                                cid, ctype, decision.reason,
                                str(payload.get("reply") or "")[:50])
                    return "promoted"
                return label
            if decision.blocked_by:
                logger.info("[Agent] candidate %s BLOCKED (%s): %s [%s]",
                            cid, ctype, decision.reason, decision.blocked_by)
                return "blocked"
            logger.info("[Agent] candidate %s %s (%s): %s",
                        cid, label, ctype, decision.reason)
            return label
        except Exception as e:
            logger.warning("[Agent] candidate proposal failed: %s: %s",
                           type(e).__name__, e)
            return "error"

    def _decide_promotion(self, cid: str) -> promotion.Decision:
        """Run the promotion policy against everything currently known."""
        ledger = self.candidate_ledger
        cand = ledger.get(cid)
        if cand is None:
            return promotion.Decision(False, "unknown candidate")
        log = self.evidence_log
        return promotion.decide(
            cand,
            linked_events=log.many(cand.get("evidence") or []),
            # Built by `promotion`, not here: the operator CLI needs the same
            # list and a second copy of the filter is what let the two drift.
            related_events=promotion.related_events(cand, log.all()),
            peers=ledger.all(),
            now=time.time(),
            policy=self.promotion_policy,
            owner_id=str(getattr(self, "owner_qq", "") or ""),
        )

    def _rebuild_promoted_views(
        self, *, strict: bool = False,
    ) -> tuple[int, int]:
        """Re-materialize the retrieval views from the ledger.

        Derived state, so a whole-file atomic rewrite is safe — and it is the
        only write in the learning path that is not an append."""
        try:
            counts = candidates.rebuild_views(
                self.candidate_ledger, self.promoted_examples_file,
                self.promoted_feedback_file,
                max_examples=self.examples_max_auto,
                max_pairs=self.feedback_max_auto)
            logger.info("[Agent] promoted views rebuilt: %d examples, %d pairs",
                        counts[0], counts[1])
            return counts
        except OSError as e:
            logger.warning("[Agent] promoted view rebuild failed: %s", e)
            if strict:
                raise
            return (-1, -1)

    def _rollback_promoted_for(self, reply: str, ts: str, event_id: str = "",
                               reason: str = "") -> int:
        """A human disagreed with `reply`: revoke every promoted candidate that
        teaches it. The records stay; only their authority is withdrawn, and it
        is withdrawn from retrieval on the next turn.

        Both directions count. A promoted example *of* the reply obviously has
        to go, and so does a promoted rewrite that proposed this reply as the
        improvement — continuing to teach a fix the user just rejected is the
        same mistake wearing the opposite sign."""
        ledger = self.candidate_ledger
        reply = (reply or "").strip()
        rolled = 0
        for cand in ledger.active():
            teaches = (
                (cand.get("type") == candidates.TYPE_EXAMPLE
                 and str(cand.get("reply") or "").strip() == reply)
                or (cand.get("type") == candidates.TYPE_PAIR
                    and str(cand.get("better") or "").strip() == reply)
            )
            if not teaches:
                continue
            if ledger.rollback(cand["candidate_id"], ts=ts, actor="auto",
                               reason=reason or "recipient disagreed",
                               evidence=[event_id] if event_id else ()):
                rolled += 1
                logger.info("[Agent] candidate ROLLED BACK %s: %r",
                            cand["candidate_id"], reply[:50])
        if rolled:
            self._rebuild_promoted_views()
        return rolled

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

        A top score is recorded as *evidence* and proposes a candidate; it can
        no longer append anything to a retrieval pool by itself. This evaluator
        is documented below as generous, and a generous grader marking its own
        homework is the weakest signal in the system — see promotion.py."""
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

            # Register framing, not "quality" framing. Measured on the same
            # model (deepseek-v4-pro) and the same drafted-letter reply:
            # "Rate the quality of this reply" returned 5/5 ("casual, helpful
            # suggestion ... without AI tells") while the register rubric below
            # returned 3 -- a quality frame rewards helpfulness, which is
            # exactly the assistant register this evaluator exists to catch.
            # An earlier bolt-on anchor ("a blatant tell caps the score at 2")
            # did not survive either: the model classified every tell it liked
            # as "not blatant". The scale itself has to define the register.
            eval_prompt = (
                f"The reply below is from {self.bot_name or 'bot'} -- meant to "
                f"pass as a REGULAR MEMBER of a casual group chat: spoken "
                f"style, short, has opinions, picks up jokes, never "
                f"customer-service polite, never delivers formatted "
                f"work-products.\n"
                f"Rate 1-5 how well the reply passes as that register -- NOT "
                f"merely whether a human could have typed it. A fluent human "
                f"could type a drafted letter or a tutorial; that still fails "
                f"this register.\n"
                f"5 = exactly the register: one or two short casual lines, "
                f"natural, fits the context.\n"
                f"4 = the register, with a small flaw (slightly stiff line, "
                f"slightly long).\n"
                f"3 = human-plausible but drifting into helpful-assistant "
                f"register: structured advice, a mini-tutorial, a drafted text "
                f"with placeholders, options laid out evenly.\n"
                f"2 = clear assistant register: a polished deliverable, "
                f"step-by-step structure, markdown/bullets, service "
                f"politeness, lecture length.\n"
                f"1 = disaster: answered the wrong person, broke character, "
                f"incoherent, ignored the context.\n\n"
                f"Group chat context:\n---\n{ctx_text}\n---\n"
                f"{self.bot_name or 'bot'}'s reply: \"{reply}\"\n"
                f"{sticker_clause}\n"
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
                # /v1 prefix matches the main call path (_call_llm):
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
                "max_tokens": 1500,
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
                # Microseconds, because this stamp is not just a timestamp:
                # `evolution.load_reviewed_ts` uses `src_eval_ts` as the ONLY
                # review-dedup key, so two low-score replies landing in the
                # same second were one key — the evolve loop reviewed the
                # first, wrote that key, and the second was invisible
                # forever. `auto_reviewer`'s verdict landed on both rows for
                # the same reason.
                "ts": datetime.now().isoformat(timespec="microseconds"),
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

            # A top self-score becomes evidence about the reply, and proposes a
            # positive-example candidate that will sit in `proposed` until
            # something stronger corroborates it. Threshold is 5 (not 4): a
            # production audit had 97% of replies landing at >=4, so anything
            # looser would file a candidate for nearly every reply sent.
            #
            # PASS (the skip-reply marker) and replies already retrievable from
            # a pool are skipped — there is nothing to propose.
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
                    "src": "self_eval",
                }
                ev = evidence.make_event(
                    kind=evidence.KIND_SELF_EVAL,
                    ts=record["ts"],
                    **self._scope_fields(group_id),
                    reply=reply_clean,
                    context=ctx_lines,
                    adjudication={"accept": True, "score": score,
                                  "scenario": ex["scenario"], "mode": mode,
                                  "intent": intent, "reason": reason},
                    adjudicator_model=self.eval_model,
                    adjudicator_prompt_version="self-eval/1",
                    source_event_id=f"eval:{group_id}:{record['ts']}",
                )
                if self._record_and_corroborate(ev, record["ts"]):
                    self._propose_candidate(ev, candidates.TYPE_EXAMPLE, ex,
                                            record["ts"])
        except Exception as e:
            logger.warning("[Agent] reply evaluation failed: %s: %s",
                           type(e).__name__, e)

    def _retract_reply(self, reply: str, ts: str = "",
                       event_id: str = "") -> None:
        """A human disagreed with this reply — stop imitating it, everywhere.

        Two eras have to be handled, because a deployment that has been running
        for months contains both:

        - **Ledger era.** Promoted candidates lose their authority (append-only
          rollback) and drop out of the materialized views. Nothing is erased.
        - **Pre-ledger era.** Rows banked directly into the learned pool by an
          older build, and whatever weight the old candidate pool had
          accumulated, are still live retrieval material — so the row is
          removed and the weight withdrawn. That deletion is the pre-ledger
          design's only way to revoke, which is precisely why the ledger
          replaced it."""
        reply = (reply or "").strip()
        if not reply:
            return
        ts = ts or datetime.now().isoformat(timespec="seconds")
        try:
            self._rollback_promoted_for(reply, ts, event_id=event_id)
        except Exception as e:
            logger.warning("[Agent] candidate rollback failed: %s: %s",
                           type(e).__name__, e)
        try:
            if self.example_candidates.withdraw(reply):
                logger.info("[Agent] legacy example candidate withdrawn: %r",
                            reply[:50])
            removed = promotion.retract_example(self.examples_file, reply)
            if removed:
                self._auto_examples_seen.discard(reply)
                self._examples_mtime = 0.0  # force a full reload
                logger.info("[Agent] retracted %d legacy banked example(s): %r",
                            removed, reply[:50])
        except Exception as e:
            logger.warning("[Agent] retraction failed: %s: %s",
                           type(e).__name__, e)

    @staticmethod
    def _append_with_rotation(path: Path, line: str, max_bytes: int = 5_000_000) -> None:
        """Append one JSONL row, rotating to path.old past max_bytes.

        Rotation and write happen under the same lock every other writer of
        this file takes, and the row goes through storage.append_jsonl_unlocked
        so it is fsynced and a missing trailing newline is repaired. This was a
        bare open("a") with an unlocked rename: eval.jsonl lost its tail on
        power loss, and a rotation racing an append could drop the row into the
        file that had just been moved aside."""
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            row = json.loads(line)
        except (json.JSONDecodeError, TypeError):
            row = None
        try:
            with append_lock(path):
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
                        logger.warning("[Agent] log rotation failed for %s: %s",
                                       path, e)
                if isinstance(row, dict):
                    append_jsonl_unlocked(path, row)
                else:
                    # Not a JSON object; callers always pass one, but keep the
                    # old behaviour rather than silently dropping the line.
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
        """Adjudicate a directed user reaction and record what it proves.

        The reaction is written to the evidence log first, and unconditionally:
        accepted or dismissed, it happened, and a dismissed teaching attempt is
        worth being able to look up. Only then is anything *proposed* —
        corrections and accepted retries as BAD->OK candidates, genuine
        positives as example candidates — and a proposal changes nothing until
        the promotion policy finds a second compatible event with at least one
        strong among them.

        Accepted rejections still arm both recovery paths (retry-completion and
        the delayed elicitation ask), and an accepted rejection or correction
        rolls back whatever the reply had previously been promoted for.

        Every adjudication is audited in candidates.jsonl. Never raises."""
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
            raw = await self._call_llm(
                "", [{"role": "user", "content": prompt}],
                model=self.react_model, max_tokens=1000, enable_search=False,
                json_object=True)
            adj = reactions.parse_adjudication(raw)
            if not adj:
                return
            now = datetime.now().isoformat(timespec="seconds")
            mode = entry.get("mode", "called")
            outcomes: list[str] = []

            # Shared scope + provenance for every event this adjudication
            # produces. recipient_id is who the reply was aimed at: it is what
            # decides whether a correction is strong, and it is deliberately not
            # "whoever is most trusted" (see evidence.classify_strength).
            base = dict(
                self._scope_fields(conv_id),
                speaker_id=str(reactor_uid or ""),
                speaker_name=reactor_name or "",
                recipient_id=str(entry.get("target_uid") or ""),
                context=entry.get("ctx_lines"),
                reaction_text=reaction_text,
                directed=True,
                direction=str(entry.get("matched_by") or ("dm" if is_private else "at")),
                adjudicator_model=self.react_model,
                adjudicator_prompt_version=reactions.ADJUDICATOR_VERSION,
                source_event_id=str(
                    entry.get("source_event_id")
                    or entry.get("reaction_mid")
                    or ((entry.get("mids") or [""])[0])),
            )

            # The reaction happened. Record it before deciding what it means:
            # `accept` is the adjudicator's verdict about *learning*, not a
            # filter on what is worth remembering.
            reaction_ev = evidence.make_event(
                kind=evidence.KIND_REACTION, ts=now, **base,
                reply=str(entry.get("reply") or ""),
                reaction_type=adj["reaction"],
                adjudication={**adj, "mode": mode,
                              "intent": entry.get("intent", "")},
                parent_event_id=str(entry.get("parent_evidence_id") or ""),
            )
            # KEEP THE ANSWER. Evidence identity is content-addressed and
            # `adjudication` is deliberately NOT one of `_ID_FIELDS`, so the
            # same reaction re-adjudicated — a retried background task, a
            # replayed webhook, exactly what that dedup exists to absorb —
            # is one evidence row and, if the second verdict differs, a
            # SECOND candidate proposing a different rewrite. The two then
            # block each other through `find_conflicts`, permanently, with
            # the view empty and nothing to retire either of them.
            reaction_is_new = self._record_and_corroborate(reaction_ev, now)

            # Dedup keys mean parsing the seed AND learned feedback pools, which
            # are allowed to reach 5 MB — tens of milliseconds on the event
            # loop. Load them at most once per adjudication, and only when a
            # proposal is actually on the table. The promoted view is included:
            # a pair already carrying authority needs no second candidate.
            fb_keys: set | None = None

            def _fresh_pair(p: dict) -> bool:
                nonlocal fb_keys
                if fb_keys is None:
                    fb_keys = evolution.load_feedback_keys(
                        [self.feedback_seed_file, self.feedback_file,
                         self.promoted_feedback_file])
                key = (p["reply"], p["better"])
                if key in fb_keys:
                    return False
                fb_keys.add(key)
                return True

            # Retry-completion: this reply was the bot's second attempt after a
            # rejection. The user reacting positively — or just moving on —
            # accepts the fix, which is strong evidence for (rejected -> retry)
            # with zero user effort. Strong, but still one event.
            # A `positive` verdict only counts when the adjudicator accepted it;
            # `neutral` is recorded but classifies as weaker, since the "better"
            # side of the pair is the agent's own retry text (see
            # evidence.classify_strength). Without both guards, a user changing
            # the subject minted STRONG evidence for the agent's own wording and
            # overrode an adjudicator verdict of accept=false.
            if entry.get("fixes") and (
                    (adj["reaction"] == "positive" and adj["accept"])
                    or adj["reaction"] == "neutral"):
                fix = entry["fixes"]
                fpair = reactions.fix_pair(fix, entry["reply"], now)
                if fpair is not None and _fresh_pair(fpair):
                    retry_ev = evidence.make_event(
                        kind=evidence.KIND_RETRY_ACCEPTANCE, ts=now,
                        **{**base, "context": fix.get("ctx_lines")},
                        reply=fpair["reply"],
                        reaction_type=adj["reaction"],
                        adjudication={
                            "accept": adj["reaction"] == "positive",
                            "better": fpair["better"],
                            "scenario": fpair.get("scenario", ""),
                            "mode": fix.get("mode", mode),
                            "reason": "user accepted the bot's retry",
                        },
                        # The complaint this answers, so the chain reads
                        # rejection -> retry -> acceptance.
                        parent_event_id=str(fix.get("evidence_id")
                                            or reaction_ev["event_id"]),
                    )
                    if self._record_and_corroborate(retry_ev, now):
                        outcomes.append("retry:" + self._propose_candidate(
                            retry_ev, candidates.TYPE_PAIR, fpair, now))

            if adj["accept"]:
                # `reaction_is_new` gates the two PROPOSALS and nothing else.
                # The retraction and the recovery paths below stay
                # unconditional: they are idempotent, and they describe what
                # the user did rather than what a model said about it.
                pair = reactions.to_feedback_pair(entry, adj, now, reactor_name)
                if reaction_is_new and pair is not None and _fresh_pair(pair):
                    outcomes.append("pair:" + self._propose_candidate(
                        reaction_ev, candidates.TYPE_PAIR, pair, now))
                ex = reactions.to_example(entry, adj, now)
                if reaction_is_new and ex is not None:
                    # One laugh is not proof, and no quantity of laughter is:
                    # positive reactions are weak evidence, so an example
                    # candidate waits for a strong event or a human.
                    outcomes.append("example:" + self._propose_candidate(
                        reaction_ev, candidates.TYPE_EXAMPLE, ex, now))

                # A rejected or corrected reply must stop being imitated.
                if adj["reaction"] in ("rejection", "correction"):
                    self._retract_reply(str(entry.get("reply") or ""), ts=now,
                                        event_id=reaction_ev["event_id"])

                # Accepted rejection with nothing concrete learned: arm both
                # recovery paths.
                if adj["reaction"] == "rejection" and conv_id:
                    self.pending_reactions.note_rejection(
                        conv_id, entry, time.time(),
                        evidence_id=reaction_ev["event_id"])
                    if self.react_elicit and adj.get("ask"):
                        self._spawn(self._maybe_elicit(
                            conv_id, entry, adj.get("ask", ""),
                            reactor_uid, is_private,
                            parent_evidence_id=reaction_ev["event_id"]))

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
                "applied": ",".join(outcomes) if outcomes else "rejected",
                "evidence_id": reaction_ev["event_id"],
                "strength": reaction_ev["strength"],
            }
            if entry.get("fixes"):
                audit["via"] = "retry-completion-candidate"
            evolution.append_jsonl(self.candidates_file, [audit],
                                   max_bytes=20_000_000)
        except Exception as e:
            logger.warning("[Agent] reaction processing failed: %s: %s",
                           type(e).__name__, e)

    async def _maybe_elicit(self, conv_id: str, entry: dict, ask: str,
                            reactor_uid: str, is_private: bool,
                            parent_evidence_id: str = "") -> None:
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
            # entry: the rejector's answer will adjudicate against it, and is
            # recorded as a child of the rejection that prompted the ask.
            self.pending_reactions.record(
                conv_id, reply=entry["reply"], ctx_lines=entry.get("ctx_lines", []),
                mode=entry.get("mode", "called"), intent=entry.get("intent", ""),
                target_uid=reactor_uid, elicited_uid=reactor_uid, ts=time.time(),
                parent_evidence_id=parent_evidence_id)
            logger.info("[Agent] elicitation sent (conv=%s): %s", conv_id, ask[:60])
        except Exception as e:
            logger.warning("[Agent] elicitation failed: %s: %s",
                           type(e).__name__, e)

    # ---------------- Self-evolution (eval -> gated candidates) ----------------
    async def loop_evolve(self) -> None:
        """Background loop that turns the agent's own low-score evals into
        BAD/OK preference *candidates*. Opt-in (EVOLVE_AUTO).

        A self-diagnosis is one automatic signal that nobody witnessed, so it
        proposes and waits like everything else: promotion needs a real user
        event to corroborate it, or a human at tools/candidates_admin.py. What
        used to be an unattended writer is now an unattended *proposer*."""
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
        """One pass: diagnose up to evolve_batch new low-score evals into
        preference candidates. Returns the number of candidates proposed."""
        evals = evolution.load_evals(self.eval_file, self.evolve_threshold)
        reviewed = evolution.load_reviewed_ts(self.candidates_file)
        pending = [e for e in evals if e.get("ts") not in reviewed][: self.evolve_batch]
        if not pending:
            return 0
        existing = evolution.load_feedback_keys(
            [self.feedback_seed_file, self.feedback_file,
             self.promoted_feedback_file])
        now = datetime.now().isoformat(timespec="seconds")
        proposed = 0
        for ev in pending:
            prompt = evolution.build_review_prompt(ev, self.agent_lang)
            raw = await self._call_llm(
                "", [{"role": "user", "content": prompt}],
                model=self.evolve_model, max_tokens=2000, enable_search=False,
                json_object=True,
            )
            diag = evolution.parse_review(raw)
            if not diag:
                # AUDIT THE FAILURE, then move on. `src_eval_ts` in
                # candidates.jsonl is the ONLY review-dedup key, so skipping
                # the row left this eval permanently pending: re-diagnosed on
                # every tick, one model call each, forever — and
                # `EVOLVE_BATCH` of them pin the window so nothing else is
                # ever reviewed either.
                logger.warning(
                    "[Agent] evolve: reviewer output not JSON for %s, marking "
                    "reviewed so it is not retried forever: %s",
                    str(ev.get("ts", "?"))[:19], str(raw)[:120])
                self._audit_candidate(ev, {}, "unparseable")
                continue
            pair = evolution.pair_from_candidate(
                evolution.candidate_record(ev, diag), now)
            usable = pair is not None and (pair["reply"], pair["better"]) not in existing
            outcome = "rejected"
            if usable:
                event = evidence.make_event(
                    kind=evidence.KIND_SELF_REVIEW, ts=now,
                    **self._scope_fields(str(ev.get("group_id") or "")),
                    reply=pair["reply"],
                    context=pair.get("context"),
                    directed=False, direction="self",
                    adjudication={
                        "accept": True, "better": pair["better"],
                        "scenario": pair.get("scenario", ""),
                        "mode": pair.get("mode", ""),
                        "score": ev.get("score") if isinstance(ev.get("score"), int) else None,
                        # The diagnosis, not the reasoning that produced it.
                        "reason": str(diag.get("bad_diagnosis") or "")[:200],
                    },
                    adjudicator_model=self.evolve_model,
                    adjudicator_prompt_version=evolution.REVIEWER_VERSION,
                    source_event_id=(
                        f"eval:{ev.get('group_id') or ''}:{ev.get('ts') or ''}"),
                )
                outcome = ("held" if not self._record_and_corroborate(event, now)
                           else self._propose_candidate(
                               event, candidates.TYPE_PAIR, pair, now))
                if outcome in ("proposed", "promoted"):
                    proposed += 1
                existing.add((pair["reply"], pair["better"]))
            # Audit trail after the proposal, but keyed so a crash in between
            # re-reviews the entry rather than losing it: the ledger's own
            # dedup makes a repeated proposal a no-op.
            self._audit_candidate(ev, diag, outcome)
        if proposed:
            logger.info("[Agent] evolve: +%d preference candidates from %d "
                        "low-score evals (awaiting corroboration)",
                        proposed, len(pending))
        return proposed
