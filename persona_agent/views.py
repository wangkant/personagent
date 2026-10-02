"""Seed and learned data kept fresh on disk: pools, promoted views, filters, lorebook."""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from . import candidates as candidates_mod
from . import evidence as evidence_mod
from . import promotion as promotion_mod
from .paths import (
    read_jsonl,
)
from .pools import (
    _read_jsonl_appended,
    _retrieval_fields,
)
from .storage import atomic_write_text

logger = logging.getLogger("agent")

# Refused outright by the reply's character policy, or rewritten by it.
_UNSAFE = str.maketrans({c: " " for c in "[]<>{}|*`·→…"}
                        | {";": ",", "；": "，", "。": " ", "—": " "})


def _clip(text, limit: int = 30) -> str:
    """Chat text for one summary line: one line, policy-safe, at most
    `limit` characters."""
    s = " ".join(str(text or "").translate(_UNSAFE).split())
    return s if len(s) <= limit else s[:limit - 3].rstrip() + "..."


class DataViews:
    @staticmethod
    def _load_json_dict(path: Path, label: str) -> dict:
        """JSON object from disk; missing or malformed → {}."""
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(loaded, dict):
                raise ValueError("root must be an object")
            return loaded
        except FileNotFoundError:
            return {}
        except Exception as e:
            logger.warning("[Agent] %s load failed: %s", label, e)
            return {}

    @staticmethod
    def _save_json(path: Path, obj, label: str) -> None:
        try:
            atomic_write_text(path, json.dumps(obj, ensure_ascii=False, indent=2))
        except Exception as e:
            logger.warning("[Agent] %s save failed: %s", label, e)

    def _reload_examples_if_stale(self) -> None:
        """Hot-reload the seed + runtime example pools.

        The seed is read-only and the runtime file only ever grows, so the
        common case (the agent just banked one of its own replies) parses the
        appended tail alone instead of re-reading both files whole — see
        _read_jsonl_appended. Any other shape, including a seed edit or the
        pool-cap rewrite, falls back to a full reload."""
        paths = (self.examples_seed_file, self.examples_file)
        stamp = self._pool_stamp(paths)
        if stamp == self._examples_mtime:
            return
        try:
            records, appended = self._read_pool_delta(
                paths, "_examples", self._examples_mtime, stamp)
            replies = {
                r.get("reply", "").strip() for r in records
                if isinstance(r.get("reply"), str) and r.get("reply", "").strip()
            }
            if appended:
                self._examples_cache.extend(records)
                # Runtime dedup set: appends only add, so update in place.
                self._auto_examples_seen.update(replies)
            else:
                self._examples_cache = records
                # Rebuild runtime auto-append dedup set from on-disk replies so
                # a restart doesn't forget which replies are already in the pool.
                self._auto_examples_seen = replies
            self._examples_mtime = stamp
        except Exception as e:
            logger.warning("[Agent] examples.jsonl reload failed: %s", e)

    def _reload_pairs_if_stale(self) -> None:
        """Load preference pairs from the seed + runtime feedback pools
        (rating=better only). Append-aware, same as _reload_examples_if_stale."""
        paths = (self.feedback_seed_file, self.feedback_file)
        stamp = self._pool_stamp(paths)
        if stamp == self._pairs_mtime:
            return
        try:
            records, appended = self._read_pool_delta(
                paths, "_pairs", self._pairs_mtime, stamp)
            pairs = [r for r in records if self._is_better_pair(r)]
            if appended:
                self._pairs_cache.extend(pairs)
            else:
                self._pairs_cache = pairs
            self._pairs_mtime = stamp
        except Exception as e:
            logger.warning("[Agent] feedback.jsonl reload failed: %s", e)

    def _live_scope(self, conv_id: str) -> dict:
        """This turn's scope, normalised the way the ledger stores one."""
        return evidence_mod.normalize_scope({
            "lang": self.agent_lang,
            "platform": self._conv_platform(conv_id) if conv_id else "",
            "conv_id": conv_id,
            "persona": self.persona_name,
            "persona_hash": self.persona_hash,
            "persona_version": self.persona_version,
        })

    def _scope_authorizes(self, scope, current_scope: dict) -> bool:
        """May a promoted row with ``scope`` reach a prompt in ``current_scope``?
        Persona is compared through its lineage, everything else exactly."""
        if not isinstance(scope, dict):
            return False
        # Read first: reading it registers the lineage the lookup below uses.
        identity = self.persona_identity
        return (all(str(scope.get(key) or "") == str(value or "")
                    for key, value in current_scope.items() if key != "persona_hash")
                and evidence_mod.persona_identity(scope) == identity)

    def _learned_summary(self, group_id: str) -> str:
        """What this room has taught the bot, in chat-sized form: memories,
        promoted material, proposals still waiting (for a second voice, or
        for the admin), the latest promotion and why it passed, and the
        recent self-scores. Reads state only; no model call."""
        zh = self.agent_lang == "zh"
        current_scope = self._live_scope(group_id)
        self._reload_views_if_stale()
        examples = [r for r in self._view_examples_cache
                    if self._scope_authorizes(r.get("scope"), current_scope)]
        pairs = [r for r in self._view_pairs_cache
                 if self._scope_authorizes(r.get("scope"), current_scope)]
        voice, admin, latest = self._learning_status(group_id, current_scope)
        scores = []
        if self.eval_enabled:
            scores = [int(r["score"]) for r in read_jsonl((self.eval_file,))
                      if r.get("group_id") == group_id and isinstance(r.get("score"), int)][-10:]
        memories = len(self.memories.get(group_id, []))

        # Plain lines, ASCII separators: the reply crosses the character policy
        # like any other, which strips middle dots, arrows, the ellipsis and
        # list markers, and refuses brackets and pipes outright.
        n_ex, n_pr = len(examples), len(pairs)
        if zh:
            head = (f"记忆 {memories} 条，学到 {n_ex} 条回复和 {n_pr} 组纠正，"
                    f"{voice} 条等第二个人佐证，{admin} 条等管理员处理")
        else:
            head = (f"{memories} memor{'y' if memories == 1 else 'ies'}, "
                    f"{n_ex} repl{'y' if n_ex == 1 else 'ies'} and {n_pr} fix{'' if n_pr == 1 else 'es'} learned, "
                    f"{voice} awaiting a second voice, {admin} awaiting the admin")
        if scores:
            head += ("，最近自评 {:.1f}/5" if zh else ", recent self-score {:.1f}/5").format(
                sum(scores) / len(scores))

        def pair_line(r: dict) -> str:
            was, better = _clip(r.get("reply")), _clip(r.get("better"))
            return f"原来：{was}，改成：{better}" if zh else f"was: {was}, better: {better}"

        lines = [head]
        shown = ""
        if latest is not None:
            shown = str(latest.get("type") or "")
            row = latest.get("payload") or {}
            lines.append(pair_line(row) if shown == "preference_pair"
                         else _clip(row.get("reply")))
            chain = self._promotion_chain(latest, zh)
            if chain:
                lines.append(chain)
        if shown != "preference_pair":
            lines.extend(pair_line(r) for r in pairs[-1:])
        if shown != "positive_example":
            lines.extend(_clip(r.get("reply")) for r in examples[-1:])
        return "\n".join(lines)

    def _learning_status(self, group_id: str, current_scope: dict):
        """(waiting for a second voice, waiting for the admin, latest active
        candidate) for this conversation. A proposal no further event can
        promote (a positive example, or one blocked by a conflict or by
        disagreeing evidence) waits for the admin, not for a voice."""
        try:
            cands = self.candidate_ledger.all()
            events = self.evidence_log.all()
        except Exception as e:
            logger.warning("[Agent] learned summary: ledger unreadable: %s", e)
            return 0, 0, None
        voice = admin = 0
        for c in cands:
            if (c.get("state") != candidates_mod.STATE_PROPOSED
                    or (c.get("scope") or {}).get("conv_id") != group_id):
                continue
            decision = self._decide_promotion(c["candidate_id"], events=events,
                                              peers=cands)
            if (decision.blocked_by or not self.promotion_policy.auto_promote
                    or not evidence_mod.can_be_strong(str(c.get("type") or ""))):
                admin += 1
            else:
                voice += 1
        active = [c for c in cands
                  if c.get("state") == candidates_mod.STATE_PROMOTED
                  and self._scope_authorizes(c.get("scope"), current_scope)]

        def promoted_at(c: dict) -> str:
            return max((str(h.get("ts") or "") for h in c.get("history") or ()
                        if h.get("state") == candidates_mod.STATE_PROMOTED),
                       default="")

        latest = max(active, key=promoted_at) if active else None
        return voice, admin, latest

    def _promotion_chain(self, cand: dict, zh: bool) -> str:
        """One line: who argued for `cand`, how, and why it passed."""
        try:
            linked = self.evidence_log.many(cand.get("evidence") or [])
        except Exception:
            return ""
        steps: list[str] = []
        strong = 0
        supporting = [e for e in linked if promotion_mod.supports_candidate(
            e, cand, policy=self.promotion_policy)]
        for e in supporting:
            who = _clip(e.get("speaker_name"), 16) or ("有人" if zh else "someone")
            kind, rtype = e.get("kind"), e.get("reaction_type")
            if kind == evidence_mod.KIND_RETRY_ACCEPTANCE:
                step = f"{who} 接受了重答" if zh else f"{who} accepted the retry"
            elif kind == evidence_mod.KIND_SELF_REVIEW:
                step = "自我复盘" if zh else "a self-review"
            elif kind == evidence_mod.KIND_SELF_EVAL:
                step = "自评满分" if zh else "a top self-score"
            elif rtype == "correction":
                step = f"{who} 纠正了" if zh else f"{who} corrected it"
            elif rtype == "rejection":
                step = f"{who} 说没答对" if zh else f"{who} said it missed"
            else:
                step = f"{who} 觉得好" if zh else f"{who} liked it"
            steps.append(step)
            if promotion_mod.anchors(e, cand):
                strong += 1
        history = [h for h in cand.get("history") or ()
                   if h.get("state") == candidates_mod.STATE_PROMOTED]
        if history and history[-1].get("actor") != "auto":
            steps.append("管理员通过" if zh else "promoted by the admin")
        elif zh:
            steps.append(f"{len(supporting)} 条证据其中 {strong} 条强，通过")
        else:
            steps.append(f"passed with {len(supporting)} events, {strong} strong")
        return ("原因：" + "，".join(steps)) if zh else ("why: " + ", ".join(steps))

    def _reload_views_if_stale(self) -> None:
        """Hot-reload the materialized views of promoted candidates.

        These are the *only* rows the automatic learning path can put in front
        of the model. They are small (capped), derived, and rewritten whole on
        every promotion or rollback, so there is no append-only fast path to
        preserve here — a plain mtime+size check and a full reparse is both
        correct and cheap. A rollback therefore takes effect on the next turn
        without a restart, which is the point of keeping the view separate."""
        for path, attr, pairs_only in (
            (self.promoted_examples_file, "_view_examples", False),
            (self.promoted_feedback_file, "_view_pairs", True),
        ):
            stamp = self._pool_stamp((path,))
            if stamp == getattr(self, attr + "_stamp"):
                continue
            try:
                rows = read_jsonl((path,))
                if pairs_only:
                    rows = [r for r in rows if self._is_better_pair(r)]
                setattr(self, attr + "_cache", self._tag_rows(rows))
                setattr(self, attr + "_stamp", stamp)
            except Exception as e:
                logger.warning("[Agent] %s reload failed: %s", path.name, e)

    @staticmethod
    def _is_better_pair(r: dict) -> bool:
        return bool(r.get("rating") == "better" and r.get("better") and r.get("reply"))

    @staticmethod
    def _tag_rows(rows: list) -> list:
        """Precompute the per-row retrieval fields once at load, not per turn."""
        for rec in rows:
            rec["_rt"] = _retrieval_fields(rec)
        return rows

    @staticmethod
    def _read_seed(path: Path) -> list:
        rows = read_jsonl((path,))
        for rec in rows:
            rec["_seed"] = True  # ranked below what this deployment learned
        return rows

    def _set_pool_pos(self, attr: str, eof: int, offset: int, sig: bytes) -> None:
        setattr(self, attr + "_eof", eof)
        setattr(self, attr + "_offset", offset)
        setattr(self, attr + "_sig", sig)

    @staticmethod
    def _pool_stamp(paths, *, strict: bool = False) -> tuple:
        """Identity, nanosecond mtime and size per file, including replacements.

        Strict callers distinguish an unreadable file from an absent one.
        """
        out: list = []
        for p in paths:
            try:
                st = p.stat()
                out.append((st.st_dev, st.st_ino, st.st_mtime_ns, st.st_size))
            except FileNotFoundError:
                out.append((0, 0, 0, 0))
            except OSError:
                if strict:
                    raise
                out.append((0, 0, 0, 0))
        return tuple(out)

    def _read_pool_delta(self, paths: tuple[Path, Path], attr: str,
                         prev_stamp, stamp: tuple) -> tuple[list[dict], bool]:
        """Read a (seed, runtime) retrieval pool, appended-tail-only when possible.

        Returns ``(records, appended_only)``. When appended_only is True the
        records are strictly new rows to be concatenated onto the existing
        cache — safe because the cache is ordered seed-then-runtime and every
        writer appends to the runtime file's tail.

        The fast path needs a previous successful load whose seed is still
        untouched; `prev_stamp` set to anything that isn't such a stamp (the
        `= 0.0` force-reload idiom the tools and tests use) drops back to a
        full read of both files. _read_jsonl_appended re-checks the runtime
        prefix itself and falls back on its own if it has been rewritten.
        """
        seed_path, runtime_path = paths
        can_append = (
            isinstance(prev_stamp, tuple) and len(prev_stamp) == len(stamp)
            and prev_stamp[0] == stamp[0]         # seed untouched
            and prev_stamp[1][:2] == stamp[1][:2]  # same runtime file
            and getattr(self, attr + "_sig")      # a prefix was consumed before
            and runtime_path.exists()
        )
        if can_append:
            records, appended, eof, offset, sig = _read_jsonl_appended(
                runtime_path,
                getattr(self, attr + "_eof"),
                getattr(self, attr + "_offset"),
                getattr(self, attr + "_sig"),
                identity=prev_stamp[1][:2],
            )
            self._set_pool_pos(attr, eof, offset, sig)
            if appended:
                return self._tag_rows(records), True
            # _read_jsonl_appended rejected the prefix and re-read the runtime
            # file whole; the seed still has to be prepended.
            return self._tag_rows(self._read_seed(seed_path) + records), False

        seed_records = self._read_seed(seed_path)
        if runtime_path.exists():
            runtime_records, _, eof, offset, sig = _read_jsonl_appended(
                runtime_path, 0, 0, b"")
        else:
            runtime_records, eof, offset, sig = [], 0, 0, b""
        self._set_pool_pos(attr, eof, offset, sig)
        return self._tag_rows(seed_records + runtime_records), False

    def _reload_json_if_stale(self, path: Path, attr: str, parse,
                              name: str, unit: str) -> None:
        """Re-read a changed JSON config; a missing file empties
        the cache. `parse(data)` returns the entries to cache."""
        try:
            stamp = self._pool_stamp((path,), strict=True)
        except OSError as exc:
            logger.warning("[Agent] %s stat failed: %s", name, exc)
            return
        if stamp == ((0, 0, 0, 0),):
            setattr(self, attr + "_cache", [])
            setattr(self, attr + "_stamp", stamp)
            return
        if stamp == getattr(self, attr + "_stamp"):
            return
        try:
            entries = parse(json.loads(path.read_text(encoding="utf-8")))
            setattr(self, attr + "_cache", entries)
            setattr(self, attr + "_stamp", stamp)
            logger.info("[Agent] %s loaded %d %s", name, len(entries), unit)
        except Exception as e:
            logger.warning("[Agent] %s.json load failed: %s", name, e)

    # -------- Output filter (SillyTavern regex-extension style) --------
    def _reload_filters_if_stale(self) -> None:
        def parse(data) -> list:
            raw = data.get("filters", []) if isinstance(data, dict) else data
            compiled = []
            for f in raw:
                pat = f.get("pattern")
                if not pat:
                    continue
                try:
                    compiled.append({
                        "name": f.get("name", "?"),
                        "regex": re.compile(pat, re.IGNORECASE | re.DOTALL),
                        "action": f.get("action", "reject"),
                        "replacement": f.get("replacement", ""),
                        "reason": f.get("reason", ""),
                    })
                except re.error as e:
                    logger.warning("[Agent] output_filter '%s' regex compile failed: %s",
                                   f.get("name"), e)
            return compiled

        self._reload_json_if_stale(self.output_filter_file, "_filters", parse,
                                   "output_filter", "rules")

    def _apply_output_filter(self, reply: str) -> tuple[str, str]:
        """Pre-send regex sanity net. Returns (filtered_reply, blocked_reason).
        Non-empty blocked_reason → drop the whole reply, take the PASS path."""
        self._reload_filters_if_stale()
        if not self._filters_cache or not reply:
            return reply, ""
        for f in self._filters_cache:
            m = f["regex"].search(reply)
            if not m:
                continue
            if f["action"] == "reject":
                return "", f"{f['name']} ({f['reason']})"
            if f["action"] == "replace":
                reply = f["regex"].sub(f.get("replacement", ""), reply)
        return reply.strip(), ""

    # -------- Lorebook (SillyTavern World Info style) --------
    def _reload_lorebook_if_stale(self) -> None:
        def parse(data) -> list:
            raw = data.get("entries", []) if isinstance(data, dict) else data
            entries = []
            for e in raw:
                kws = e.get("keywords", [])
                if not kws or not e.get("content"):
                    continue
                entries.append({
                    "name": e.get("name", "?"),
                    "keywords": [str(k).lower() for k in kws],
                    "content": e["content"],
                    "priority": int(e.get("priority", 100)),
                    "scan_depth": int(e.get("scan_depth", 5)),
                })
            entries.sort(key=lambda x: -x["priority"])
            return entries

        self._reload_json_if_stale(self.lorebook_file, "_lorebook", parse,
                                   "lorebook", "entries")
