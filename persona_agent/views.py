"""Seed and learned data kept fresh on disk: pools, promoted views, filters, lorebook."""
from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path

from . import candidates as candidates_mod
from . import channels
from . import chatlangs
from . import evidence as evidence_mod
from . import promotion as promotion_mod
from .paths import parse_jsonl, read_jsonl
from .ranking import row_fields
from .storage import atomic_write_text
from .textproc import _TYPOGRAPHY_MAP, TextProcessing

logger = logging.getLogger("agent")

# Refused outright by the reply's character policy, or rewritten by it.
_UNSAFE = str.maketrans({c: " " for c in "[]<>{}|*`·→…"}
                        | {";": ",", "；": "，", "。": " ", "—": " "})


# The English promotion chain; the other chat languages bring theirs.
_LEARNED_EN = {
    "someone_else": "someone in another chat",
    "someone": "someone",
    "retry": "{who} accepted the retry",
    "self_review": "a self-review",
    "self_eval": "a top self-score",
    "corrected": "{who} corrected it",
    "missed": "{who} said it missed",
    "liked": "{who} liked it",
    "by_admin": "promoted by the admin",
    "passed": "passed with {events} events, {strong} strong",
    "why": "why: {steps}",
    "sep": ", ",
}


def _clip(text, limit: int = 30) -> str:
    """Chat text for one summary line: one line, policy-safe, at most
    `limit` characters."""
    s = " ".join(str(text or "").translate(_TYPOGRAPHY_MAP).translate(_UNSAFE).split())
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
        """Hot-reload the seed + runtime example pools when either file changes."""
        stamp = self._pool_stamp((self.examples_seed_file, self.examples_file))
        if stamp == self._examples_mtime:
            return
        try:
            records = self._read_pool(self.examples_seed_file, self.examples_file)
            self._examples_cache = records
            # Rebuilt from disk so a restart remembers which replies are pooled.
            self._auto_examples_seen = {
                r.get("reply", "").strip() for r in records
                if isinstance(r.get("reply"), str) and r.get("reply", "").strip()
            }
            self._examples_mtime = stamp
        except Exception as e:
            logger.warning("[Agent] examples.jsonl reload failed: %s", e)

    def _reload_pairs_if_stale(self) -> None:
        """Hot-reload the seed + runtime preference pairs (rating=better only)."""
        stamp = self._pool_stamp((self.feedback_seed_file, self.feedback_file))
        if stamp == self._pairs_mtime:
            return
        try:
            records = self._read_pool(self.feedback_seed_file, self.feedback_file)
            self._pairs_cache = [r for r in records if self._is_better_pair(r)]
            self._pairs_mtime = stamp
        except Exception as e:
            logger.warning("[Agent] feedback.jsonl reload failed: %s", e)

    def _live_scope(self, conv_id: str) -> dict:
        """This turn's scope, normalised the way the ledger stores one."""
        return evidence_mod.normalize_scope({
            "lang": self.agent_lang,
            "platform": channels.platform_of(conv_id) if conv_id else "",
            "conv_id": conv_id,
            "persona": self.persona_name,
            "persona_hash": self.persona_hash,
            "persona_version": self.persona_version,
        })

    def _scope_authorizes(self, scope, current_scope: dict,
                          identity: str | None = None) -> bool:
        """May a promoted row with ``scope`` reach a prompt in ``current_scope``?
        Persona is compared through its lineage, everything else exactly.
        Pass ``identity`` (self.persona_identity) when checking many rows."""
        if not isinstance(scope, dict):
            return False
        if identity is None:
            # Read first: reading it registers the lineage the lookup below uses.
            identity = self.persona_identity
        return (all(str(scope.get(key) or "") == str(value or "")
                    for key, value in current_scope.items() if key != "persona_hash")
                and evidence_mod.persona_identity(scope) == identity)

    def _learned_summary(self, group_id: str, lang: str = "") -> str:
        """What this room has taught the bot, chat-sized: counts, what waits,
        the latest promotion and why, in chat language `lang` (default: the
        agent's). Reads state only."""
        code = lang or self.agent_lang
        # English builds its own lines, plurals and all; the rest fill templates.
        text = {} if code == "en" else chatlangs.spec(code).learned_text
        current_scope = self._live_scope(group_id)
        identity = self.persona_identity
        self._reload_views_if_stale()
        examples = [r for r in self._view_examples_cache
                    if self._scope_authorizes(r.get("scope"), current_scope, identity)]
        pairs = [r for r in self._view_pairs_cache
                 if self._scope_authorizes(r.get("scope"), current_scope, identity)]
        voice, admin, latest = self._learning_status(current_scope)
        scores = []
        if self.eval_enabled:
            scores = [int(r["score"]) for r in read_jsonl((self.eval_file,))
                      if r.get("group_id") == group_id and isinstance(r.get("score"), int)][-10:]
        memories = len(self.memories.get(group_id, []))

        # Plain lines: the reply crosses the character policy like any other.
        n_ex, n_pr = len(examples), len(pairs)
        if text:
            head = text["head"].format(memories=memories, examples=n_ex, fixes=n_pr,
                                       voice=voice, admin=admin)
        else:
            head = (f"{memories} memor{'y' if memories == 1 else 'ies'}, "
                    f"{n_ex} repl{'y' if n_ex == 1 else 'ies'} and {n_pr} fix{'' if n_pr == 1 else 'es'} learned, "
                    f"{voice} awaiting a second voice, {admin} awaiting the admin")
        if scores:
            score = f"{sum(scores) / len(scores):.1f}"
            head += (text["score"].format(score=score) if text
                     else f", recent self-score {score}/5")

        def pair_line(r: dict) -> str:
            was, better = _clip(r.get("reply")), _clip(r.get("better"))
            return (text["pair"].format(was=was, better=better) if text
                    else f"was: {was}, better: {better}")

        lines = []
        shown = ""
        if latest is not None:
            shown = str(latest.get("type") or "")
            row = latest.get("payload") or {}
            lines.append(pair_line(row) if shown == "preference_pair"
                         else _clip(row.get("reply")))
            chain = self._promotion_chain(latest, text, current_scope["conv_id"])
            if chain:
                lines.append(chain)
        if shown != "preference_pair":
            lines.extend(pair_line(r) for r in pairs[-1:])
        if shown != "positive_example":
            lines.extend(_clip(r.get("reply")) for r in examples[-1:])
        return self._policy_safe(head, lines)

    def _policy_safe(self, head: str, lines: list[str]) -> str:
        """`head` plus each learned line the character policy passes whole, so
        one bad line cannot refuse the summary."""
        def passes(text: str) -> bool:
            return TextProcessing._sanitize_reply(
                text, self.agent_lang, self.reply_style) == text

        kept = [head]
        for line in lines:
            if passes("\n".join(kept + [line])):
                kept.append(line)
        return "\n".join(kept)

    def _learning_status(self, current_scope: dict):
        """(waiting for a second voice, waiting for the admin, latest active
        candidate) for this conversation, in one pass over each ledger. Liked
        replies are not counted: only a person can promote them."""
        try:
            cands = self.candidate_ledger.all()
            events = self.evidence_log.all()
        except Exception as e:
            logger.warning("[Agent] learned summary: ledger unreadable: %s", e)
            return 0, 0, None
        waiting = [c for c in cands
                   if c.get("state") == candidates_mod.STATE_PROPOSED
                   and evidence_mod.can_be_strong(str(c.get("type") or ""))
                   and self._scope_authorizes(c.get("scope"), current_scope)]
        voice = admin = 0
        if waiting and not self.promotion_policy.auto_promote:
            admin = len(waiting)
        elif waiting:
            index = promotion_mod.EvidenceIndex(events, cands)
            now, admins = time.time(), self._admins()
            for c in waiting:
                decision = promotion_mod.decide(
                    c, linked_events=index.linked(c), related_events=index.related(c),
                    peers=index.peers(c), now=now,
                    policy=self.promotion_policy, admin_ids=admins)
                if decision.blocked_by:
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

    def _promotion_chain(self, cand: dict, text: dict, conv_id: str) -> str:
        """One line: who argued for `cand`, how, and why it passed (only people
        in `conv_id` are named). `text` is a chat language's learned-summary
        templates; empty means English."""
        say = text or _LEARNED_EN
        try:
            linked = self.evidence_log.many(cand.get("evidence") or [])
        except Exception:
            return ""
        steps: list[str] = []
        strong = 0
        supporting = [e for e in linked if promotion_mod.supports_candidate(
            e, cand, policy=self.promotion_policy)]
        for e in supporting:
            if str(e.get("conv_id") or "") != conv_id:
                who = say["someone_else"]
            else:
                who = _clip(e.get("speaker_name"), 16) or say["someone"]
            kind, rtype = e.get("kind"), e.get("reaction_type")
            if kind == evidence_mod.KIND_RETRY_ACCEPTANCE:
                step = say["retry"].format(who=who)
            elif kind == evidence_mod.KIND_SELF_REVIEW:
                step = say["self_review"]
            elif kind == evidence_mod.KIND_SELF_EVAL:
                step = say["self_eval"]
            elif rtype == "correction":
                step = say["corrected"].format(who=who)
            elif rtype == "rejection":
                step = say["missed"].format(who=who)
            else:
                step = say["liked"].format(who=who)
            steps.append(step)
            if promotion_mod.anchors(e, cand):
                strong += 1
        history = [h for h in cand.get("history") or ()
                   if h.get("state") == candidates_mod.STATE_PROMOTED]
        if history and history[-1].get("actor") != "auto":
            steps.append(say["by_admin"])
        else:
            steps.append(say["passed"].format(events=len(supporting), strong=strong))
        return say["why"].format(steps=say["sep"].join(steps))

    def _reload_views_if_stale(self) -> None:
        """Hot-reload the promoted views, the only rows automatic learning can
        put in a prompt; a rollback takes effect on the next turn."""
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
            rec["_rt"] = row_fields(rec)
        return rows

    @staticmethod
    def _read_seed(path: Path) -> list:
        rows = read_jsonl((path,))
        for rec in rows:
            rec["_seed"] = True  # ranked below what this deployment learned
        return rows

    @staticmethod
    def _pool_stamp(paths, *, strict: bool = False) -> tuple:
        """Identity, nanosecond mtime and size per file; `strict` raises on an
        unreadable (not absent) file."""
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

    @classmethod
    def _read_pool(cls, seed: Path, runtime: Path) -> list:
        """Seed rows then runtime rows, tagged. A runtime read error raises,
        so the caller keeps its cache and retries on the next turn."""
        try:
            blob = runtime.read_bytes()
        except FileNotFoundError:
            blob = b""
        return cls._tag_rows(cls._read_seed(seed) + parse_jsonl(blob))

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
        """Pre-send regex net: (filtered_reply, blocked_reason); a reason drops
        the whole reply."""
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
                })
            entries.sort(key=lambda x: -x["priority"])
            return entries

        self._reload_json_if_stale(self.lorebook_file, "_lorebook", parse,
                                   "lorebook", "entries")
