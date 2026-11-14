"""What the persona remembers: memory commands, auto memory and core memory."""
from __future__ import annotations

import logging
import random
import re
import time
from datetime import datetime
from typing import Callable, Optional

from .storage import num as _num
from . import access
from . import channels
from . import chatlangs
from . import embeddings
from . import episodes as episodes_mod
from . import memstate
from . import memstore
from . import memtrash
from . import people
from . import ranking
from .addressing import _HAS_CJK, mentions_name, names_regex
from .textproc import _FULL_STOP_RE, _focus_tokens

logger = logging.getLogger("agent")

# Plain text: the reply crosses the character policy like any other. One
# table per chat language, kept with the rest of it in `chatlangs`.
_COMMAND_REPLIES = {code: spec.replies for code, spec in chatlangs.SPECS.items()}

# Trimmed off a forget query, in every language.
_QUERY_TRIM = " \t.!?,;:。！？，、~～…¡¿«»„“”"


def _is_question(content: str, spec: chatlangs.Spec) -> bool:
    return bool(re.search(spec.question_end, content.strip(), re.IGNORECASE))


def _forget_query(content: str, spec: chatlangs.Spec) -> str:
    query = content.strip()
    if spec.query_lead:
        query = re.sub(spec.query_lead, "", query, flags=re.IGNORECASE)
    return query.strip(_QUERY_TRIM)


# When a new auto-memory rewrites an older one (see `_restated_memory`): it may
# drop almost none of the old note's tokens, must share a few, and only within
# one sitting.
_MEMORY_MERGE_MAX_DROPPED = 0.05

_MEMORY_MERGE_MIN_SHARED = 4

_MEMORY_MERGE_WINDOW_S = 6 * 3600.0

# Where a core note may be cut by a forget; "3.5 hours" is one sentence.
_SENTENCE_END = re.compile(r"(?<=[.!?;])\s+|(?<=[。！？；\n])\s*")

# Beside memory.json, so a home moved by MEMORY_FILE keeps them together.
TRASH_FILE = "memory_trash.jsonl"
EPISODES_FILE = "episodes.json"
STATE_FILE = "memory_state.json"

# A core rewrite that keeps too little of a long note is a truncation.
_CORE_SHRINK_MIN_OLD = 120
_CORE_SHRINK_LEN = 0.5
_CORE_SHRINK_TOKENS = 0.4
_CORE_OPEN = re.compile(r"\[\s*CORE_UPDATE\s*\]", re.IGNORECASE)
_CORE_CLOSE = re.compile(r"\[\s*/\s*CORE_UPDATE\s*\]", re.IGNORECASE)

#: Events a recall lists after the facts.
_RECALL_EVENTS = 3

#: A reply's note about a member is another's claim when that one's last
#: lines carry at least this share of its words, and more than the member's own.
_CLAIM_LINES = 30
_CLAIM_SHARE = 0.5

_TEXT_KEY = re.compile(r"[0-9a-f]{32}")


def _shapes(*patterns: str) -> tuple[re.Pattern, ...]:
    return tuple(re.compile(p, re.IGNORECASE) for p in patterns)


# What `_validate_memory_candidate` refuses: narrow lexical gates for
# control-plane shapes (hijacking, role swaps, triggers, extraction,
# poisoning), not content moderation. Compiled once: every note, lesson and
# tidy step passes through them.
_POISON_SHAPES = _shapes(
    r"\b(?:ignore|disregard|override)\b.{0,40}\b(?:instruction|prompt|rule)s?\b",
    r"\b(?:system|developer)\s+(?:prompt|message|instruction)s?\b",
    r"\b(?:follow|obey)\b.{0,30}\b(?:command|instruction|prompt|rule)s?\b",
    r"\b(?:ignore|disregard|override|forget|reset|discard)\b.{0,60}"
    r"\b(?:everything|anything|instruction|prompt|rule|told|conversation|memory)\b",
    r"^(?:always|never|must|should)\b.{0,40}"
    r"\b(?:reply|respond|answer|say|output|reveal|expose|send|follow|"
    r"obey|ignore|stay|remain|act|pretend)\b",
    r"\b(?:you|the\s+assistant|assistant|chatbot|bot|model)\b.{0,20}"
    r"\b(?:always|never|must|should)\b.{0,40}"
    r"\b(?:reply|respond|answer|say|output|act|pretend|stay|remain)\b",
    r"\byou\b.{0,15}\b(?:need\s+to|will|shall|have\s+to)\b.{0,25}"
    r"\b(?:reply|respond|answer|say|output|speak|write|use)\b.{0,20}"
    r"\b(?:only|always|exclusively)\b",
    # Conditional triggers, each within one sentence and only with the
    # verb as consequence ("gets defensive when..." is a fact).
    # Opening a sentence: "when he says banana, answer ...".
    r"(?:^|[.;!?]\s*)(?:when|whenever|if)\b[^.;!?]{0,80}"
    r"\b(?:answer|reply|respond|say|output|reveal|expose|send|act)\b",
    # After a comma or "then": "if he types ping, reply pong".
    r"\b(?:when|whenever|if)\b[^.;!?]{0,80}(?:,|\bthen\b)\s*"
    r"(?:(?:you|the\s+assistant|assistant|chatbot|bot|model)\s+)?"
    r"(?:(?:must|should|will|shall|always|only|just|please)\s+)*"
    r"(?:answer|reply|respond|say|output|reveal|expose|send|act)\b",
    # The assistant as subject: "if he says banana you answer in haiku".
    r"\b(?:when|whenever|if)\s+\S[^.;!?]{0,80}?\s"
    r"(?:you|the\s+assistant|assistant|chatbot|bot|model)\s+"
    r"(?:(?:must|should|will|shall|always|only|just)\s+)*"
    r"(?:answer|reply|respond|say|output|reveal|expose|send|act)\b",
    r"\b(?:reveal|print|show|expose)\b.{0,30}"
    r"\b(?:secret|private|memory|prompt|instruction)s?\b",
    # Assistant/persona identity stated as a supposed fact.
    r"\byour\s+(?:(?:real|actual|true)\s+)?"
    r"(?:name|identity|persona|role)\s+(?:is|=)\b",
    # Within one sentence, like the triggers.
    r"\byou\s+(?:are|are\s+not|aren't|were)\b[^.;!?]{0,60}"
    r"\b(?:human|person|sentient|ai|bot|assistant|model|character|persona)\b",
    r"\byou\s+identify\s+as\b.{0,20}"
    r"\b(?:human|person|sentient|ai|bot|assistant|model|character|persona)\b",
    r"\b(?:the\s+)?(?:assistant|chatbot|bot|model|persona|character)"
    r"(?:'s)?\b.{0,35}\b(?:real\s+name|identity|persona|role)\b",
    r"^(?:the\s+)?(?:assistant|chatbot|bot|model|persona|character)'s\s+"
    r"(?:(?:real|actual|true)\s+)?name\s+(?:is|=)\b",
    r"\b(?:this|the)\s+(?:assistant|chatbot|bot|model)\b.{0,20}"
    r"\b(?:is|are|was|were)\b.{0,15}"
    r"\b(?:human|person|sentient|ai|assistant|bot|model|character)\b",
    r"\b(?:correct|right|required|expected)\s+answer\b.{0,80}"
    r"\b(?:ai|bot|assistant|model|human|identity)\b",
    r"\bno\s+(?:topic|subject)\b.{0,30}\boff[- ]limits\b",
    r"\b(?:promised|agreed|swore)\b.{0,50}"
    r"\b(?:stay|remain|act|pretend|reply|answer)\b",
    r"(?:\u5ffd\u7565|\u65e0\u89c6|\u8986\u76d6|\u5fd8\u6389).{0,30}"
    r"(?:\u6307\u4ee4|\u63d0\u793a|\u89c4\u5219|\u4e4b\u524d\u7684\u4e00\u5207)",
    r"^(?:\u4ece\u73b0\u5728\u5f00\u59cb|\u4ee5\u540e|\u4eca\u540e|\u6c38\u8fdc)?\s*(?:\u8bf7)?\s*"
    r"(?:\u626e\u6f14|\u5047\u88c5|\u5145\u5f53|\u4f5c\u4e3a)",
    r"^(?:\u4ee5\u540e|\u4eca\u540e|\u8bf7)?\s*(?:\u4e00\u76f4|\u53ea|\u6c38\u8fdc|\u5fc5\u987b|\u603b\u662f)"
    r".{0,18}(?:\u56de\u590d|\u56de\u7b54|\u8f93\u51fa|\u8bf4)",
    r"(?:\u52a9\u624b|\u804a\u5929\u673a\u5668\u4eba|\u673a\u5668\u4eba|\u6a21\u578b|\u89d2\u8272).{0,20}"
    r"(?:\u771f\u6b63\u7684\u540d\u5b57|\u771f\u5b9e\u59d3\u540d|\u771f\u540d)",
    r"\u4f60(?:\u7684)?(?:\u771f\u6b63\u7684\u540d\u5b57|\u771f\u5b9e\u59d3\u540d|\u771f\u540d).{0,8}"
    r"(?:\u662f|\u53eb)",
    r"^\u4f60\u53eb.{1,20}$",
    r"\u4f60.{0,4}(?:\u8981|\u5fc5\u987b|\u5e94\u8be5|\u603b\u662f|\u6c38\u8fdc|\u4f1a).{0,18}"
    r"(?:\u5047\u88c5|\u626e\u6f14|\u56de\u590d|\u56de\u7b54|\u53ea\u7528|\u8f93\u51fa|\u8bf4)",
    r"\u4f60.{0,4}(?:\u662f|\u4e0d\u662f).{0,12}"
    r"(?:\u4eba\u7c7b|\u771f\u4eba|AI|\u4eba\u5de5\u667a\u80fd|\u673a\u5668\u4eba|\u6a21\u578b)",
    r"(?:\u52a9\u624b|\u804a\u5929\u673a\u5668\u4eba|\u673a\u5668\u4eba|\u6a21\u578b).{0,15}"
    r"\u662f.{0,12}(?:\u4eba\u7c7b|\u771f\u4eba|AI|\u4eba\u5de5\u667a\u80fd|\u673a\u5668\u4eba)",
    r"(?:AI|\u4eba\u5de5\u667a\u80fd|\u673a\u5668\u4eba|\u4eba\u7c7b).{0,30}"
    r"(?:\u6b63\u786e\u7b54\u6848|\u6807\u51c6\u7b54\u6848)",
    r"(?:\u6b63\u786e\u7b54\u6848|\u6807\u51c6\u7b54\u6848).{0,30}"
    r"(?:AI|\u4eba\u5de5\u667a\u80fd|\u673a\u5668\u4eba|\u4eba\u7c7b)",
)

_ROLE_CONTROL = _shapes(
    r"^(?:please\s+)?act\s+(?:as|like)\b",
    r"^(?:please\s+)?behave\s+(?:as|like)\b",
    r"^(?:please\s+)?pretend\s+to\s+be\b",
    r"^(?:please\s+)?roleplay\s+(?:as|like)\b",
    r"^(?:please\s+)?(?:play|assume)\s+the\s+role\s+of\b",
    r"^(?:please\s+)?become\s+(?:an?\s+)?"
    r"(?:human|person|sentient|ai|bot|assistant|model|character|persona)\b",
    r"^(?:please\s+)?call\s+yourself\b",
    r"^(?:please\s+)?be\s+(?:an?\s+)?"
    r"(?:human|person|sentient|ai|bot|assistant|model|character|persona)\b",
    r"^(?:please\s+)?keep\s+(?:acting|pretending|behaving)\b.{0,30}"
    r"\b(?:human|person|sentient|ai|bot|assistant|model|character|persona)\b",
    r"^(?:please\s+)?(?:stay|remain)\s+(?:in\s+)?"
    r"(?:character|persona|role)\b",
    r"^(?:from\s+now\s+on|henceforth),?\s+(?:please\s+)?"
    r"(?:act\s+(?:as|like)|behave\s+(?:as|like)|pretend\s+to\s+be|"
    r"roleplay\s+(?:as|like)|(?:play|assume)\s+the\s+role\s+of|"
    r"become|call\s+yourself|stay\s+in\s+character|"
    r"remain\s+in\s+character)\b",
)

_OUTPUT_CONTROL = _shapes(
    r"^(?:please\s+)?(?:respond|reply|answer|say|output|speak|write)\s+"
    r"(?:only|always|exclusively|in\b|using\b)",
    r"^(?:please\s+)?(?:respond|reply|answer|say|output|speak|write|communicate)\s+"
    r".{1,30}\s+(?:from\s+now\s+on|henceforth)$",
    r"^(?:only|always)\s+"
    r"(?:respond|reply|answer|say|output|speak|write|communicate)\s+"
    r"(?:in|using|with)\b",
    r"^(?:please\s+)?use\s+only\b",
    r"^(?:please\s+)?use\s+(?:only\s+)?\S+(?:\s+\S+){0,3}\s+"
    r"for\s+(?:every|each|all)\s+(?:reply|response|answer|output)s?$",
    r"^(?:the|every|all)\s+"
    r"(?:repl(?:y|ies)|responses?|answers?|outputs?)\s+"
    r"(?:must|should|will|shall|has\s+to)(?:\s+always)?\s+"
    r"(?:be\s+(?:only\s+)?in|use|contain|start|end)\b",
    r"^(?:please\s+)?(?:respond|reply|answer|say|output|speak|write)\s+"
    r"every\s+(?:question|reply|response|answer)\s+(?:in|using)\b",
    r"^(?:\u8bf7)?\u7528.{1,16}(?:\u56de\u590d|\u56de\u7b54|\u8f93\u51fa|\u8bf4|\u8bf4\u8bdd)$",
    r"^(?:\u4ee5\u540e|\u4eca\u540e)\u7528.{1,16}(?:\u56de\u590d|\u56de\u7b54|\u8f93\u51fa|\u8bf4|\u8bf4\u8bdd)$",
    r"^\u6240\u6709(?:\u56de\u590d|\u56de\u7b54|\u8f93\u51fa)\u90fd\u7528.{1,16}$",
)


class Memory:
    # ---- the stores ---------------------------------------------------------

    @property
    def memory_trash(self) -> memtrash.MemoryTrash:
        return self._sidecar("_memory_trash", memtrash.MemoryTrash,
                             self.memory_file.with_name(TRASH_FILE))

    @property
    def memory_state(self) -> memstate.MemoryState:
        return self._sidecar("_memory_state", memstate.MemoryState,
                             self.memory_file.with_name(STATE_FILE))

    @property
    def episode_store(self) -> episodes_mod.EpisodeStore:
        """Loaded on first use; a damaged file raises MemoryFileDamaged, and
        rows that are not events go to the trash."""
        store = self._sidecar("_episode_store", episodes_mod.EpisodeStore,
                              self.memory_file.with_name(EPISODES_FILE))
        if store._data is None:
            store.load()
            dropped, store.unreadable = store.unreadable, []
            for conv, row in dropped:
                self._trash_put(conv, "episode", row, "unreadable", "load")
            if dropped:
                self._save_episodes()
        return store

    def _load_memories(self) -> dict:
        """memory.json, migrated once (memstore.migrate); a damaged file, or a
        damaged episodes.json, stops the start naming the daily copy."""
        memories = memstore.load_memory_file(self.memory_file)
        memstore.migrate(memories, self.memory_trash, self.memory_state,
                         self.memory_file)
        self.episode_store
        return memories

    def _backup_today(self, path) -> None:
        try:
            memstore.daily_backup(path, self.memory_state)
        except OSError as e:
            logger.warning("[Agent] daily copy of %s failed: %s", path.name, e)

    def _save_memories(self) -> None:
        self._backup_today(self.memory_file)
        self._save_json(self.memory_file, self.memories, "memory")

    def _save_episodes(self) -> None:
        self._backup_today(self.episode_store.path)
        try:
            self.episode_store.save()
        except OSError as e:
            logger.warning("[Agent] episodes save failed: %s", e)

    def _save_memory_state(self, force: bool = True) -> None:
        try:
            self.memory_state.save(force=force)
        except OSError as e:
            logger.warning("[Agent] memory state save failed: %s", e)

    def _trash_put(self, conv: str, kind: str, item: dict, why: str, by: str,
                   ref: str = "") -> str:
        """Keep a removed item restorable; appended before its store is
        rewritten. A failed append is logged and the removal goes on."""
        try:
            return self.memory_trash.put(conv, kind, dict(item), why, by, ref)
        except OSError as e:
            logger.warning("[Agent] memory trash append failed: %s", e)
            return ""

    def _memory_gen(self, conv: str) -> int:
        """How many forgets this chat has had since the start."""
        return self.__dict__.get("_forget_gens", {}).get(conv, 0)

    def _forgot(self, conv: str) -> None:
        """A consolidation of this chat already under way now keeps nothing."""
        gens = self.__dict__.setdefault("_forget_gens", {})
        gens[conv] = gens.get(conv, 0) + 1

    def _final_copies(self, keep: Callable[[str, dict], bool]) -> None:
        """After a final forget: the daily copies become the files as they are
        now, and the migration copy loses every note `keep` refuses."""
        for path in (self.memory_file, self.core_memory_file, self.episode_store.path):
            try:
                memstore.refresh_backup(path)
            except OSError as e:
                logger.warning("[Agent] daily copy of %s not refreshed: %s", path.name, e)
        try:
            memstore.scrub_migration_copy(self.memory_file, keep)
        except OSError as e:
            logger.warning("[Agent] migration copy not rewritten: %s", e)
        flush = getattr(self, "_maybe_flush_recent", None)
        if callable(flush) and getattr(self, "_recent", None) is not None:
            flush(force=True)

    def _note_ids(self, conv: str) -> set[str]:
        return {str(it["id"]) for it in self.memories.get(conv, []) if it.get("id")}

    def _append_memory(self, group_id: str, item: dict) -> None:
        items = self.memories.setdefault(group_id, [])
        if not item.get("id"):
            item["id"] = memstore.new_id("m", self._note_ids(group_id))
        items.append(item)
        if len(items) > self.memory_max_per_conversation:
            dropped = self._evict_memory(items)
            if dropped is not None:
                self._trash_put(group_id, "note", dropped, "evicted", "cap")
        self._save_memories()

    def _load_core_memory(self) -> dict[str, str]:
        return memstore.load_core_file(self.core_memory_file)

    def _save_core_memory(self) -> None:
        self._backup_today(self.core_memory_file)
        self._save_json(self.core_memory_file, self.core_memory, "core_memory")

    def _operator_ids(self) -> frozenset[str]:
        return people.operator_ids(self._admins(), self.memories)

    def _same_person(self, uid: str) -> frozenset[str]:
        return people.same_person(uid, self._operator_ids())

    # ---- hooks the turn and recall code fills in ---------------------------

    def _maybe_consolidate(self, conv: str, reason: str) -> None:
        """Start a consolidation of this chat when one is due (consolidate.py)."""
        return None

    def _mark_used(self, conv: str, reply_text: str) -> None:
        """Count the remembered items a sent reply drew on (retrieval.py)."""
        return None

    def _extract_core_update(self, reply: str) -> tuple[str, str]:
        """Split off [CORE_UPDATE]...[/CORE_UPDATE] notes: (reply, note). An
        unclosed block runs to the end; words after a closed one stay in the
        reply; the last non-empty note wins. Parse only, so a reply the filter
        blocks never commits its note."""
        if not _CORE_OPEN.search(reply):
            return reply, ""
        kept: list[str] = []
        new_note, rest = "", reply
        while (m := _CORE_OPEN.search(rest)) is not None:
            kept.append(rest[:m.start()])
            rest = rest[m.end():]
            close = _CORE_CLOSE.search(rest)
            body, rest = (rest[:close.start()], rest[close.end():]) if close else (rest, "")
            body = _CORE_CLOSE.sub("", _CORE_OPEN.sub("", body)).strip()
            if body:
                new_note = body
        kept.append(rest)
        reply = " ".join(p.strip() for p in kept if p.strip())
        if len(new_note) > self.CORE_MEMORY_MAX_CHARS:
            new_note = new_note[:self.CORE_MEMORY_MAX_CHARS] + "..."
        return reply, new_note

    def _commit_core_memory(self, group_id: str, new_note: str) -> None:
        """Persist a note extracted by _extract_core_update. Empty notes skip."""
        # At the core note's own cap (plus a capped note's "...").
        note = self._validate_memory_candidate(
            new_note, max_chars=self.CORE_MEMORY_MAX_CHARS + 3)
        if not note:
            return
        old = self.core_memory.get(group_id, "")
        if old == note:
            return
        if old and self._core_shrunk(old, note):
            logger.warning("[Agent] core_memory rewrite refused as a probable "
                           "truncation (group=%s, %d -> %d chars)",
                           group_id, len(old), len(note))
            return
        if old:
            self._trash_put(group_id, "core", {
                "text": old, "at": self.memory_state.core_at(group_id) or 0.0},
                "rewritten", "reply")
        self.core_memory[group_id] = note
        self._save_core_memory()
        self.memory_state.set_core_at(group_id, time.time())
        self._save_memory_state()
        logger.info("[Agent] core_memory updated (group=%s, %d chars)",
                    group_id, len(note))

    @staticmethod
    def _core_shrunk(old: str, new: str) -> bool:
        """A long note rewritten to under half its length that keeps few of
        its words: a cut-off reply, not a decision to forget."""
        if len(old) < _CORE_SHRINK_MIN_OLD or len(new) >= _CORE_SHRINK_LEN * len(old):
            return False
        old_tokens = _focus_tokens(old, "zh")
        if not old_tokens:
            return False
        kept = len(old_tokens & _focus_tokens(new, "zh")) / len(old_tokens)
        return kept < _CORE_SHRINK_TOKENS

    def _parse_memory_command(self, text: str) -> Optional[tuple[str, str, str]]:
        """(kind, what follows the keyword, chat language) when `text` is a
        memory command: learned, remember, forget or recall. None for
        conversation. Every language is tried; when two read it, the one the
        message looks written in wins."""
        table = self._memory_cmd_patterns()

        def pick(found: list[tuple[str, str]]) -> Optional[tuple[str, str]]:
            if len(found) < 2:
                return found[0] if found else None
            guess = chatlangs.detect(text, self.chat_lang)
            return next((f for f in found if f[0] == guess), found[0])

        hit = pick([(code, "") for code, _spec, pats in table
                    if pats["learned"].search(text)])
        if hit:
            return "learned", "", hit[0]
        found = []
        for code, spec, pats in table:
            for pat in pats["remember"]:
                m = pat.search(text)
                # A question is reminiscing ("Luna remember the party?").
                if m and not _is_question(m.group(1), spec):
                    found.append((code, m.group(1)))
                    break
        hit = pick(found)
        if hit:
            return "remember", hit[1], hit[0]
        found = []
        for code, spec, pats in table:
            for pat in pats["forget"]:
                m = pat.search(text)
                if (m and not _is_question(m.group(1), spec)
                        and not (spec.asking and re.search(spec.asking, m.group(1)))
                        and _forget_query(m.group(1), spec).lower() not in spec.deictic):
                    found.append((code, m.group(1)))
                    break
        hit = pick(found)
        if hit:
            return "forget", hit[1], hit[0]
        hit = pick([(code, "") for code, _spec, pats in table
                    if pats["recall"].search(text)])
        if hit:
            return "recall", "", hit[0]
        return None

    def _is_memory_command(self, text: str) -> bool:
        return self._parse_memory_command(text) is not None

    def _handle_memory_command(
        self,
        group_id: str,
        text: str,
        user_id: str = "",
        user_name: str = "",
    ) -> Optional[str]:
        parsed = self._parse_memory_command(text)
        if parsed is None:
            return None
        kind, arg, code = parsed
        spec = chatlangs.spec(code)
        is_admin = access.is_admin(user_id, self._admins())
        caller = str(user_id or "")
        reader = channels.dm_user(group_id)
        # Recall lists other chats' notes only in a DM: in a room it would
        # read one member's notes out to everyone. Deleting cannot leak.
        elsewhere = reader
        forget_elsewhere = reader or (caller if self.memory_share_rooms else "")

        def say(key: str) -> str:
            return self._memory_reply(key, code)
        if kind == "learned":
            return self._learned_summary(group_id, code)

        if kind == "remember":
            content = arg.strip()
            if spec.note_lead:
                content = re.sub(spec.note_lead, "", content, flags=re.IGNORECASE)
            # "Luna, remember!" names nothing to keep.
            if not content.strip(_QUERY_TRIM):
                return say("remember_what")
            content = self._validate_memory_candidate(content)
            if not content:
                return say("not_instructions")
            now = time.time()
            item: dict = {"text": content, "time": now, "born": now,
                          "imp": memstore.IMP_COMMAND, "uses": 0, "used": 0.0,
                          "src": "command"}
            if caller and not is_admin:
                # The saver may forget it; the subject's presence brings it into prompts.
                item["saved_by"] = caller
                if user_name:
                    item["saved_by_name"] = user_name
                uid, name = self._note_subject(group_id, content, caller, user_name,
                                               spec)
                if uid:
                    item["user_id"] = uid
                    if name:
                        item["user_name"] = name
                    if uid != caller:
                        # One member's word about another: reported speech,
                        # which never travels to another chat.
                        item["said_by"] = caller
                        if user_name:
                            item["said_by_name"] = user_name
            same = " ".join(content.split()).casefold()
            if any(" ".join(str(it.get("text") or "").split()).casefold() == same
                   for it in self.memories.get(group_id, [])):
                return say("noted")  # already kept: a second copy would only crowd out others
            self._append_memory(group_id, item)
            return say("noted")

        callers = self._same_person(caller) if caller else frozenset()

        def owns(it: dict) -> bool:
            if is_admin:
                return True
            if not caller:
                return not it.get("user_id") and not it.get("saved_by")
            return caller in (str(it.get("user_id") or ""), str(it.get("saved_by") or ""))

        if kind == "forget":
            query = _forget_query(arg, spec)
            # Short queries over-delete: a spaced script needs 3+ characters
            # and whole words ("tea" not "steak"), CJK a 2+ character substring.
            by_word = not _HAS_CJK.search(query)
            if len(query) < (3 if by_word else 2) or query.lower() in spec.everything:
                return say("forget_what")
            edge = "A-Za-z0-9_" if query.isascii() else r"\w"
            word = re.compile(rf"(?<![{edge}]){re.escape(query)}(?![{edge}])",
                              re.IGNORECASE)

            def hit(text: str) -> bool:
                return bool(word.search(text)) if by_word else query in text

            items = self.memories.get(group_id, [])
            elsewhere_about = self._about_elsewhere(forget_elsewhere, group_id)

            def note_gone(conv: str, it: dict) -> bool:
                # Query in text, never the reverse. Only the admin deletes
                # others' notes; an anonymous caller owns only unowned ones.
                text = it.get("text")
                if not isinstance(text, str) or not hit(text):
                    return False
                return owns(it) if conv == group_id else elsewhere_about(conv, it)

            removed = [it for it in items if note_gone(group_id, it)]
            if removed:
                self.memories[group_id] = [it for it in items
                                           if not any(it is r for r in removed)]
            rooms = {group_id} if removed else set()
            for room, it in self._room_notes_about(forget_elsewhere, group_id):
                if hit(it["text"]):
                    self.memories[room].remove(it)
                    removed.append(it)
                    rooms.add(room)
            changed = bool(removed)
            if changed:
                self._save_memories()

            # The core note has no owner line: it is the reader's in a DM, in a
            # room the admin's or that of whoever a sentence names.
            def mine(sentence: str) -> bool:
                return bool(is_admin or reader or not caller or (
                    len(user_name) >= 2 and user_name in sentence))

            def event_mine(ep: dict) -> bool:
                return bool(is_admin or reader or (
                    callers and ep.get("who")
                    and all(str(u) in callers for u in ep["who"])))

            if self._forget_in_core(group_id, hit, mine):
                changed = True
            # Final: nothing of it goes to the trash, and a tombstone keeps
            # old chat lines from bringing it back.
            gone_events = self._forget_events(group_id, hit, event_mine)
            thread_cut = self._forget_in_thread(group_id, hit, mine)
            lines_cut = self._purge_lines(group_id, hit, lambda row: bool(
                is_admin or reader or (callers and str(row.get("user_id") or "")
                                       in callers)))

            def trash_gone(row: dict) -> bool:
                # Older versions too: restore must not bring it back.
                item = row.get("item") or {}
                text = item.get("text")
                if not isinstance(text, str):
                    return False
                if row.get("kind") == "note":
                    return note_gone(str(row.get("conv") or ""), item)
                if row.get("conv") != group_id:
                    return False
                if row.get("kind") == "episode":
                    return hit(text) and event_mine(item)
                return any(hit(p) and mine(p) for p in _SENTENCE_END.split(text))
            try:
                trashed = self.memory_trash.drop_where(trash_gone)
            except OSError as e:
                logger.warning("[Agent] memory trash rewrite failed: %s", e)
                trashed = []
            changed = changed or bool(gone_events or thread_cut or lines_cut or trashed)
            if changed:
                hashes = set(memstore.token_hashes(query))
                for room in rooms | {group_id}:
                    for row in removed + gone_events:
                        self.memory_state.add_tombstone(
                            room, memstore.token_hashes(row.get("text", "")))
                    self.memory_state.add_tombstone(room, hashes)
                self._save_memory_state()
                for row in removed + gone_events + [r.get("item") or {} for r in trashed]:
                    self._drop_vector(row.get("text", ""))
                for room in rooms | {group_id}:
                    self._forgot(room)
                self._final_copies(lambda conv, row: not note_gone(conv, row))
            return say("forgotten" if changed else "nothing_to_forget")

        items = self.memories.get(group_id, [])
        if not is_admin:
            # A note about someone is shown only to them and its saver.
            items = [it for it in items if not it.get("user_id") or (
                caller and caller in (str(it.get("user_id")),
                                      str(it.get("saved_by") or "")))]
        items = items + [it for _, it in self._room_notes_about(elsewhere, group_id)]
        events = self._recall_events(group_id, callers, everyone=bool(reader))
        if not items and not events:
            return say("empty")
        # No brackets or list markers: the character policy refuses them.
        lines: list[str] = []
        for it in items:
            if it.get("user_id") and it.get("user_name"):
                tag = say("about").format(name=it["user_name"])
            elif it.get("saved_by_name"):
                tag = say("from").format(name=it["saved_by_name"])
            else:
                tag = ""
            lines.append(f"{tag}{it['text']}")
        lines += events
        # One note, one line: a full stop inside a note must not start a new message.
        lines = [_FULL_STOP_RE.sub(" ", line).strip() for line in lines]
        return say("recall_head") + "\n" + "\n".join(lines)

    def _recall_events(self, conv: str, callers: frozenset[str],
                       everyone: bool) -> list[str]:
        """Up to three events of this chat the caller took part in (every
        event of a DM), newest first, as "YYYY-MM-DD text"."""
        rows = [ep for ep in self.episode_store.episodes(conv)
                if everyone or (callers and callers & {str(u) for u in ep.get("who", [])})]
        rows.sort(key=lambda ep: _num(ep.get("t1")), reverse=True)
        tz = self._prompt_tz() if hasattr(self, "_prompt_tz") else None
        return [f"{datetime.fromtimestamp(_num(ep.get('t0')), tz):%Y-%m-%d} {ep['text']}"
                for ep in rows[:_RECALL_EVENTS]]

    def _room_notes_about(self, uid: str, besides: str = "") -> list[tuple[str, dict]]:
        """(chat, note) for each note another chat than `besides` keeps about
        `uid`'s person. A DM's notes never leave it, except among the
        operator's own DMs; reported speech never leaves its chat."""
        about = self._about_elsewhere(uid, besides)
        return [(key, it) for key, items in self.memories.items()
                for it in items if about(key, it)]

    def _about_elsewhere(self, uid: str, besides: str = "") -> Callable[[str, dict], bool]:
        """The test `_room_notes_about` puts each (chat, note) to."""
        if not uid:
            return lambda key, it: False
        operator = self._operator_ids()
        uids = people.same_person(uid, operator)
        among_operator = people.is_operator_dm(besides, operator)

        def about(key: str, it: dict) -> bool:
            if key == besides or not isinstance(it, dict) or it.get("said_by"):
                return False
            dm = channels.is_dm(key)
            if dm and not (among_operator and people.is_operator_dm(key, operator)):
                return False
            subject = str(it.get("user_id") or "")
            # An unattributed note of a DM is about that DM's reader.
            return subject in uids or (dm and not subject)
        return about

    def _notes_from_rooms(self, conv: str) -> list[tuple[str, dict]]:
        """What other rooms' notes reach `conv`: about a DM's reader always;
        in a room, about whoever talks there once MEMORY_SHARE_ROOMS is on."""
        reader = channels.dm_user(conv)
        if reader:
            uids = {reader}
        elif self.memory_share_rooms:
            uids = {str(m["user_id"]) for m in self.buffers.get(conv, [])
                    if m.get("user_id")}
        else:
            return []
        return [note for uid in uids for note in self._room_notes_about(uid, conv)]

    def _forget_in_core(self, group_id: str, hit: Callable[[str], bool],
                        mine: Callable[[str], bool]) -> bool:
        """Cut the sentences of the core note that match; did any go?"""
        parts = _SENTENCE_END.split(self.core_memory.get(group_id, ""))
        kept = [p for p in parts if not (hit(p) and mine(p))]
        if len(kept) == len(parts):
            return False
        if any(p.strip() for p in kept):
            self.core_memory[group_id] = " ".join(kept).strip()
        else:
            del self.core_memory[group_id]
        self._save_core_memory()
        return True

    def _forget_in_thread(self, conv: str, hit: Callable[[str], bool],
                          mine: Callable[[str], bool]) -> bool:
        """Cut the matching sentences of the chat's running summary."""
        store = self.episode_store
        thread = store.thread(conv)
        if not thread:
            return False
        parts = _SENTENCE_END.split(thread.get("text", ""))
        kept = [p for p in parts if not (hit(p) and mine(p))]
        if len(kept) == len(parts):
            return False
        text = " ".join(kept).strip()
        if text:
            thread["text"] = text
        else:
            store.drop_thread(conv)
        self._save_episodes()
        return True

    def _forget_events(self, conv: str, hit: Callable[[str], bool],
                       allowed: Callable[[dict], bool]) -> list[dict]:
        """Delete this chat's matching events the caller may delete."""
        store = self.episode_store
        rows = store.episodes(conv)
        gone = [ep for ep in rows if hit(ep.get("text", "")) and allowed(ep)]
        if gone:
            rows[:] = [ep for ep in rows if not any(ep is g for g in gone)]
            self._save_episodes()
        return gone

    def _purge_lines(self, conv: str, hit: Callable[[str], bool],
                     mine: Optional[Callable[[dict], bool]] = None) -> int:
        """Delete matching recent lines of this chat (the window, the DM turns,
        the spill and their copy on disk), so no later consolidation reads
        them again. `mine(row)` limits it to lines the caller may delete."""
        mine = mine or (lambda row: True)
        uid = channels.dm_user(conv)

        def keep(row) -> bool:
            if not isinstance(row, dict):
                return True
            text = row.get("text", row.get("content", ""))
            return not (isinstance(text, str) and hit(text) and mine(row))

        removed = 0

        def filtered(rows):
            nonlocal removed
            kept = [r for r in rows if keep(r)]
            removed += len(rows) - len(kept)
            return kept

        buffers = getattr(self, "buffers", {})
        if conv in buffers:
            buf = buffers[conv]
            kept = filtered(list(buf))
            if len(kept) != len(buf):
                buf.clear()
                buf.extend(kept)
        # DM state is keyed by the reader; a bare reader id is also a QQ
        # group's key, so room state is only ever looked up by `conv`.
        history = getattr(self, "dm_history", {})
        if uid and uid in history:
            history[uid] = filtered(history[uid])
        unanswered = getattr(self, "_dm_unanswered", {})
        if uid and uid in unanswered:
            lines = unanswered[uid]
            unanswered[uid] = [t for t in lines if not hit(t)]
            removed += len(lines) - len(unanswered[uid])
        by_reader = {uid, conv} if uid else set()
        for name, keys in (("_spill", {conv}), ("_dm_spill", by_reader)):
            spill = getattr(self, name, None) or {}
            for key in keys:
                if key in spill:
                    spill[key] = filtered(list(spill[key]))
        recent = getattr(self, "_recent", None)
        snap = recent.snapshot(conv) if recent is not None else None
        if snap:
            before = removed
            for key in ("lines", "spill", "dm", "dm_spill"):
                snap[key] = filtered(snap.get(key, []))
            if removed != before:
                recent.put(conv, snap)
        if removed:
            dirty = getattr(self, "_recent_dirty", None)
            if isinstance(dirty, set):
                dirty.add(conv)
        return removed

    def _drop_vector(self, text: str) -> None:
        if not getattr(self, "embedding_model", "") or not text:
            return
        try:
            self.embedding_cache.drop(self.embedding_model, embeddings.text_key(text))
        except OSError as e:
            logger.warning("[Agent] embedding drop failed: %s", e)

    def _forget_item(self, conv: str, kind: str, item_id: str = "",
                     by: str = "page") -> str:
        """The page's and the terminal's forget of one item: a note by id (or
        by the old `embeddings.text_key`, every note with that text), an event
        by id, the summary, or the core note. Restorable for a day; returns
        the trash id, "" when nothing matched."""
        item_id = str(item_id or "")
        texts: list[str] = []
        tids: list[str] = []
        if kind == "note":
            items = self.memories.get(conv, [])
            legacy = bool(_TEXT_KEY.fullmatch(item_id))
            hits = [it for it in items if item_id and (
                it.get("id") == item_id
                or (legacy and embeddings.text_key(it["text"]) == item_id))]
            if not hits:
                return ""
            tids = [self._trash_put(conv, "note", it, "forgotten_page", by)
                    for it in hits]
            self.memories[conv] = [it for it in items if not any(it is h for h in hits)]
            self._save_memories()
            texts = [it["text"] for it in hits]
        elif kind == "episode":
            store = self.episode_store
            row = store.get(conv, item_id) if item_id else None
            if row is None:
                return ""
            tids = [self._trash_put(conv, "episode", row, "forgotten_page", by)]
            store.remove(conv, item_id)
            self._save_episodes()
            texts = [row.get("text", "")]
        elif kind == "thread":
            store = self.episode_store
            thread = store.thread(conv)
            if not thread or (item_id and thread.get("id") != item_id):
                return ""
            tids = [self._trash_put(conv, "thread", thread, "forgotten_page", by)]
            store.drop_thread(conv)
            self._save_episodes()
            texts = [thread.get("text", "")]
        elif kind == "core":
            text = self.core_memory.get(conv)
            if text is None:
                return ""
            tids = [self._trash_put(conv, "core", {
                "text": text, "at": self.memory_state.core_at(conv) or 0.0},
                "forgotten_page", by)]
            del self.core_memory[conv]
            self._save_core_memory()
            texts = [text]
        else:
            return ""
        for text in texts:
            self.memory_state.add_tombstone(conv, memstore.token_hashes(text))
            self._drop_vector(text)
        self._forgot(conv)
        self._save_memory_state()
        return next((t for t in tids if t), "-")

    def _forget_note(self, conv: str, note_id: str) -> bool:
        """The local page's forget: one note, by id or `embeddings.text_key`."""
        return bool(self._forget_item(conv, "note", note_id))

    def _trash_live(self, row: dict) -> bool:
        """Is a trash row's item still in its store, unchanged: a crash came
        between the append and the store's rewrite."""
        conv, kind, item = row.get("conv"), row.get("kind"), row.get("item") or {}
        text = item.get("text")
        if kind == "note":
            return any(it.get("id") == item.get("id") and it.get("text") == text
                       for it in self.memories.get(conv, []) if item.get("id"))
        if kind == "episode":
            live = self.episode_store.get(conv, item.get("id", ""))
            return bool(live) and live.get("text") == text
        if kind == "thread":
            live = self.episode_store.thread(conv)
            return bool(live) and live.get("id") == item.get("id") \
                and live.get("text") == text
        if kind == "core":
            return self.core_memory.get(conv) == text
        return False

    def _removed_items(self, conv: Optional[str] = None,
                       now: Optional[float] = None) -> list[dict]:
        """What can still be restored, newest first, each with its text and
        the time it stops being restorable."""
        rows = self.memory_trash.list(conv, now, live=self._trash_live)
        return [dict(row, text=str((row.get("item") or {}).get("text", "")),
                     until=memtrash.restorable_until(row)) for row in rows]

    def _restore(self, tid: str, by: str = "page") -> str:
        """Bring a removed item back: "ok", "gone" (unknown, expired or already
        restored), "exists" (it is there already) or "invalid" (it no longer
        passes the memory checks). What it replaces goes to the trash."""
        now = time.time()
        row = self.memory_trash.get(str(tid or ""))
        if row is None or "restored_at" in row or memtrash.restorable_until(row) <= now:
            return "gone"
        conv, kind = row["conv"], row["kind"]
        item = dict(row["item"])
        # A person put it back: the character leaves it alone for a while.
        mark = {"restored": True, "restored_at": now}
        if kind == "note":
            text = self._validate_memory_candidate(item.get("text"))
            if not text or text != item.get("text"):
                return "invalid"
            items = self.memories.setdefault(conv, [])
            live = next((it for it in items
                         if item.get("id") and it.get("id") == item["id"]), None)
            if live is not None:
                if live.get("text") == text:
                    return "exists"
                self._trash_put(conv, "note", live, "replaced", by, ref=item["id"])
                live.clear()
                live.update(item, **mark)
                self._save_memories()
            elif any(it.get("text") == text for it in items):
                return "exists"
            else:
                self._append_memory(conv, dict(item, **mark))
        elif kind in ("episode", "thread"):
            limit = (episodes_mod.EPISODE_MAX_CHARS if kind == "episode"
                     else episodes_mod.THREAD_MAX_CHARS)
            text = self._validate_memory_text(item.get("text"), limit, markers=True)
            if not text:
                return "invalid"
            store = self.episode_store
            if kind == "episode":
                live = store.get(conv, item.get("id", "")) if item.get("id") else None
                if live is not None:
                    if live.get("text") == item["text"]:
                        return "exists"
                    self._trash_put(conv, "episode", live, "replaced", by, ref=item["id"])
                    live.clear()
                    live.update(item, **mark)
                else:
                    store.add(conv, dict(item, **mark))
            else:
                live = store.thread(conv)
                if live and live.get("text") == item["text"]:
                    return "exists"
                if live:
                    self._trash_put(conv, "thread", live, "rewritten", by)
                store._entry(conv)["thread"] = dict(item, **mark)
            self._save_episodes()
        elif kind == "core":
            text = self._validate_memory_candidate(
                item.get("text"), max_chars=self.CORE_MEMORY_MAX_CHARS + 3)
            if not text:
                return "invalid"
            live = self.core_memory.get(conv)
            if live == text:
                return "exists"
            if live:
                self._trash_put(conv, "core", {
                    "text": live, "at": self.memory_state.core_at(conv) or 0.0},
                    "rewritten", by)
            self.core_memory[conv] = text
            self._save_core_memory()
            self.memory_state.set_core_at(conv, now)
            self._save_memory_state()
        else:
            return "invalid"
        try:
            self.memory_trash.mark_restored(row["tid"], now)
        except OSError as e:
            logger.warning("[Agent] memory trash append failed: %s", e)
        return "ok"

    def _forget_chat(self, conv: str) -> bool:
        """Forget this chat: every fact, event, the summary, the core note,
        the recent lines and the chat's trash rows. Nothing is restorable."""
        changed = False
        rows = self.memories.pop(conv, None)
        if rows is not None:
            changed = True
            self._save_memories()
        store = self.episode_store
        old = store.data.get(conv) or {}
        if store.drop_conv(conv):
            changed = changed or bool(old.get("episodes") or old.get("thread"))
            self._save_episodes()
        if self.core_memory.pop(conv, None) is not None:
            changed = True
            self._save_core_memory()
        try:
            trashed = self.memory_trash.drop_where(lambda row: row["conv"] == conv)
        except OSError as e:
            logger.warning("[Agent] memory trash rewrite failed: %s", e)
            trashed = []
        changed = changed or bool(trashed)
        self._forgot(conv)
        self.memory_state.drop_conv(conv)
        self._save_memory_state()
        uid = channels.dm_user(conv)
        # A bare reader id is also a QQ group's key: DM state only by reader.
        by_reader = {uid, conv} - {""} if uid else set()
        for name, keys in (("buffers", {conv}), ("_spill", {conv}),
                           ("window_seq", {conv}), ("folded_upto", {conv}),
                           ("dm_history", by_reader), ("_dm_unanswered", by_reader),
                           ("_dm_spill", by_reader)):
            held = getattr(self, name, None)
            if isinstance(held, dict):
                for key in keys:
                    if key in held:
                        held.pop(key)
                        changed = True
        recent = getattr(self, "_recent", None)
        if recent is not None and recent.drop(conv):
            changed = True
            dirty = getattr(self, "_recent_dirty", None)
            if isinstance(dirty, set):
                dirty.add(conv)
        for row in (rows or []) + [r.get("item") or {} for r in trashed]:
            self._drop_vector(row.get("text", ""))
        for ep in old.get("episodes") or []:
            self._drop_vector(ep.get("text", ""))
        self._final_copies(lambda key, _row: key != conv)
        return changed

    def _validate_memory_text(self, text, max_chars: int, markers: bool = False) -> str:
        """The memory validator; with `markers`, the chat's own [image:...]
        and [sticker] markers are first written as plain words."""
        if markers:
            text = memstore.relax_markers(text)
        return self._validate_memory_candidate(text, max_chars=max_chars)

    def _note_subject(self, group_id: str, text: str, saver: str,
                      saver_name: str, spec: chatlangs.Spec) -> tuple[str, str]:
        """Who a saved note is about: the saver when it says "I" or names them,
        else a member it names, else nobody."""
        first_person = spec.first_person
        if (first_person and re.search(first_person, text, re.IGNORECASE)) or (
                saver_name and len(saver_name) >= 2 and saver_name in text):
            return saver, saver_name
        return self._memory_subject(group_id, text)

    def _memory_reply(self, key: str, code: str) -> str:
        return random.choice(_COMMAND_REPLIES[code][key])

    def _names_me(self, text: str) -> bool:
        """Is this persona named in `text`: one rule for name calls, the
        missed-mention catch-up and the memory commands."""
        return mentions_name(text, self.persona_name,
                             getattr(self, "persona_aliases", ()))

    def _memory_cmd_patterns(self) -> list:
        """[(code, spec, {kind: regex or [regexes]})] for every chat language,
        cached per persona_name and aliases."""
        names = (self.persona_name, tuple(getattr(self, "persona_aliases", ())))
        cached = getattr(self, "_mem_cmd_pats", None)
        if cached and cached[0] == names:
            return cached[1]
        # Anchored at the start, so "I don't remember..." stays conversation.
        lead = r"^\s*(?:\[reply\]\s*)?"
        name = names_regex(*names)
        sep = r"\s*[：:，,]?\s*"
        table = []
        for code, spec in chatlangs.SPECS.items():
            if name:
                vocative = f"(?:{spec.vocative})?" if spec.vocative else ""
                head = (lead + r"(?:@\S+\s*)*?@?" + name + vocative
                        + r"\s*[，,:：、]?\s*")
            else:
                head = lead + r"(?:@\S*\s*)?[，,]?\s*"
            remember = [re.compile(head + f"(?:{spec.remember})" + spec.not_a_note
                                   + sep + r"(.+)", re.IGNORECASE)]
            forget = [re.compile(head + f"(?:{spec.forget})" + spec.not_a_delete
                                 + sep + r"(.+)", re.IGNORECASE)]
            # The verb-last forms: everything between the name and the keyword.
            end = r"[\s!！.。~～]*$"
            if spec.remember_last:
                remember.append(re.compile(
                    head + r"(.+?)\s*" + f"(?:{spec.remember_last})" + end, re.IGNORECASE))
            if spec.forget_last:
                forget.append(re.compile(
                    head + r"(.+?)\s*" + f"(?:{spec.forget_last})" + end, re.IGNORECASE))
            # Recall must be the whole message: "小夏 记忆力真好" is a compliment.
            tail = r"\s*" + (f"(?:{spec.recall_tail})?" if spec.recall_tail else "")
            table.append((code, spec, {
                "remember": remember,
                "forget": forget,
                "recall": re.compile(head + f"(?:{spec.recall})" + tail
                                     + r"[\s?？!！.。~～]*$", re.IGNORECASE),
                "learned": re.compile(head + f"(?:{spec.learned})", re.IGNORECASE),
            }))
        self._mem_cmd_pats = (names, table)
        return table

    @staticmethod
    def _evict_memory(items: list[dict], now: Optional[float] = None) -> Optional[dict]:
        """Drop and return one entry for the cap: the auto memory least worth
        keeping (`ranking.retention`; on notes without importance or use, the
        oldest by `time`, which merges refresh), else the first entry."""
        if not items:
            return None
        autos = [i for i, it in enumerate(items) if it.get("auto")]
        if not autos:
            return items.pop(0)
        now = time.time() if now is None else now

        def worth(i: int) -> tuple:
            it = items[i]
            last = max(_num(it.get("time")), _num(it.get("used")))
            return (ranking.retention(it.get("imp"), it.get("uses"), last, now),
                    _num(it.get("time")), i)
        return items.pop(min(autos, key=worth))

    def _save_auto_memory(self, group_id: str, text: str) -> None:
        text = self._validate_memory_candidate(text)
        if not text:
            return
        items = self.memories.get(group_id, [])
        if any(it["text"] == text for it in items):
            return
        now = time.time()
        # Before the merge, which must not cross subjects.
        uid, name = self._memory_subject(group_id, text)
        said_by, said_name = ("", "") if channels.is_dm(group_id) else \
            self._claimed_by(group_id, text, uid)
        old = self._restated_memory(items, text, now, uid,
                                    room=not channels.is_dm(group_id), said_by=said_by)
        # A shorter restatement is added beside the note rather than dropped.
        if old is not None and len(text) >= len(old["text"]):
            # Before `time` is overwritten, or `born` would move on every merge.
            old.setdefault("born", float(old.get("time") or now))
            old["text"] = text
            old["time"] = now
            old.pop("tidied", None)
            # Only a DM gets here with a subject the note lacked.
            if uid and not old.get("user_id"):
                old["user_id"], old["user_name"] = uid, name
            if not old.get("id"):
                old["id"] = memstore.new_id("m", self._note_ids(group_id))
            self._save_memories()
            # Never the text: a forgotten note must not live on in the log.
            logger.info("[Agent] auto-memory updated (group=%s, %d chars)",
                        group_id, len(text))
            self._maybe_consolidate(group_id, "notes")
            return
        item: dict = {"text": text, "time": now, "born": now, "auto": True,
                      "imp": memstore.IMP_REPLY, "uses": 0, "used": 0.0,
                      "src": "reply"}
        if uid:
            item["user_id"] = uid
            item["user_name"] = name
        if said_by:
            # Another member's word about them: stays in this room.
            item["said_by"] = said_by
            if said_name:
                item["said_by_name"] = said_name
        self._append_memory(group_id, item)
        logger.info("[Agent] auto-memory (group=%s%s, %d chars)", group_id,
                    ", about a member" if "user_id" in item else "", len(text))
        self._maybe_consolidate(group_id, "notes")

    def _claimed_by(self, group_id: str, text: str, uid: str) -> tuple[str, str]:
        """(uid, name) of the member whose recent words carry a reply's note
        about `uid` better than `uid`'s own do, or ("", ""): then the note is
        their claim, not the subject's fact."""
        if not uid:
            return "", ""
        subject = self._same_person(uid)
        names = {str(m.get("name") or "") for m in self.buffers.get(group_id, [])
                 if str(m.get("user_id") or "") in subject}
        tokens = _focus_tokens(text, "zh") - _focus_tokens(" ".join(names), "zh")
        if not tokens:
            return "", ""
        said: dict[str, list[str]] = {}
        who: dict[str, str] = {}
        for m in list(self.buffers.get(group_id, []))[-_CLAIM_LINES:]:
            u = str(m.get("user_id") or "")
            if u:
                said.setdefault(u, []).append(f"{m.get('name', '')} {m.get('text', '')}")
                who[u] = str(m.get("name") or "")

        def share(u: str) -> float:
            hay = " ".join(said[u]).lower()
            return sum(1 for tok in tokens if tok in hay) / len(tokens)
        own = max((share(u) for u in said if u in subject), default=0.0)
        others = [(share(u), u) for u in said if u not in subject]
        best, by = max(others, default=(0.0, ""))
        if best >= _CLAIM_SHARE and best > own:
            return by, who[by]
        return "", ""

    def _memory_subject(self, group_id: str, text: str) -> tuple[str, str]:
        """Who `text` is about, as (user_id, user_name), or ("", ""): only names
        seen in the buffer (plus the admin), two characters minimum."""
        name_to_uid: dict[str, str] = {}
        for m in self.buffers.get(group_id, []):
            nm = m.get("name", "")
            uid = m.get("user_id", "")
            if nm and len(nm) >= 2 and uid:
                name_to_uid.setdefault(nm, uid)
        # The admin's account on this conversation's platform.
        admin_uid = access.admin_on(channels.platform_of(group_id),
                                    self._admins())
        if admin_uid and self.admin_name and len(self.admin_name) >= 2:
            name_to_uid.setdefault(self.admin_name, admin_uid)
        for nm, uid in name_to_uid.items():
            if nm in text:
                return uid, nm
        return "", ""

    @staticmethod
    def _restated_memory(items: list[dict], text: str, now: float,
                         subject: str = "", room: bool = False, said_by: str = ""
                         ) -> Optional[dict]:
        """The auto note `text` is a fuller telling of, or None.

        Only a note that keeps every old token and adds some ("dog" -> "cat"
        drops one, so it stays a second note); only auto notes, within the
        merge window, never across two named subjects, and in a `room` never
        an unattributed note into one that names somebody.
        """
        # "zh" also keeps a one-character Han run, whatever the agent speaks.
        fresh = _focus_tokens(text, "zh")
        if len(fresh) < _MEMORY_MERGE_MIN_SHARED:
            return None
        best: Optional[dict] = None
        best_dropped = 1.0
        for it in items:
            if not it.get("auto"):
                continue
            # From when it was written; `time` resets on every merge.
            born = float(it.get("born") or it.get("time") or 0.0)
            if now - born > _MEMORY_MERGE_WINDOW_S:
                continue
            if subject and it.get("user_id") and it["user_id"] != subject:
                continue
            # One member's word never rewrites another's, nor a fact of their own.
            if str(it.get("said_by") or "") != said_by:
                continue
            # Filing a room's shared note under one member would hide it.
            if room and subject and not it.get("user_id"):
                continue
            old_tokens = _focus_tokens(it.get("text", ""), "zh")
            shared = fresh & old_tokens
            if len(shared) < _MEMORY_MERGE_MIN_SHARED:
                continue
            dropped = len(old_tokens - fresh) / len(old_tokens)
            # It has to add something too; an equal set is a reordering.
            if (dropped <= _MEMORY_MERGE_MAX_DROPPED
                    and len(fresh) > len(old_tokens) and dropped < best_dropped):
                best, best_dropped = it, dropped
        return best

    @staticmethod
    def _validate_memory_candidate(text: str, *, max_chars: int = 200) -> str:
        """Accept short user facts; reject durable prompt or persona controls.
        Memory reaches every later prompt, so claims about the assistant's
        identity or permissions are refused like imperatives."""
        note = str(text or "").strip().replace("\r", " ").replace("\n", " ")
        note = re.sub(r"\s+", " ", note)[:max_chars]
        if not note or any(token in note for token in ("<", ">", "{", "}", "[", "]")):
            return ""

        low = note.lower()
        matches_poison_shape = any(
            shape.search(low) for shape in _POISON_SHAPES
        ) or any(
            re.search(spec.instruction, low, re.IGNORECASE)
            for spec in chatlangs.SPECS.values() if spec.instruction
        )

        # "Act as If is the title of..." describes a work, not a role.
        title_or_plot_declaration = bool(re.search(
            r"\bis\s+(?:the\s+)?(?:title|plot|name|theme)\s+of\b",
            low,
        ))
        role_control = any(
            shape.search(low) for shape in _ROLE_CONTROL
        ) and not title_or_plot_declaration

        output_control = any(shape.search(low) for shape in _OUTPUT_CONTROL)

        # Only claims of unrestricted access or waived content boundaries;
        # ordinary permissions stay memorable.
        grants_unrestricted_access = bool(re.search(
            r"(?:"
            r"\b(?:you|assistant|chatbot|bot|model)\b.{0,20}"
            r"\b(?:allowed|authorized|permitted)\s+to\s+"
            r"(?:hear|know|access|receive|see|read|be\s+told)\b.{0,35}"
            r"\b(?:anything|everything|content)\b"
            r"|"
            r"\b(?:allowed|authorized|permitted)\s+to\s+"
            r"(?:hear|know|access|receive|see|read|be\s+told)\b.{0,35}"
            r"\b(?:secret|private|unrestricted)\b"
            r")",
            low,
            re.IGNORECASE,
        ))
        explicit_consent = bool(re.search(
            r"\bconsent(?:ed|s|ing)?\b.{0,35}"
            r"\b(?:explicit|sexual|adult|unrestricted)\s+content\b",
            low,
            re.IGNORECASE,
        ))
        media_context = bool(re.search(
            r"\b(?:watch|view|read|film|movie|show|book|scene|play)\b",
            low,
            re.IGNORECASE,
        ))

        # An output modal before an output verb anywhere ("rule: always reply
        # in English"), unless that sentence's subject is a third person ("He
        # should reply to Alice tomorrow"), judged per occurrence. A capitalised
        # name counts only before must/should (case-sensitive); pronouns,
        # quantifiers and role nouns are not such a subject.
        subject = (r"(?:(?i:he|she|they)|(?!(?i:you|i|we|it|this|that|these|"
                   r"those|everyone|everybody|anyone|anybody|someone|somebody|"
                   r"nobody|all|each|every|people|members?|admins?|"
                   r"(?:persona|character|assistant|chatbot|bot|model|rule|"
                   r"note|user|owner)s?)\b)"
                   r"[A-Z][\w'-]*)")

        def _said_of_a_third_person(hit: re.Match) -> bool:
            before = re.split(r"[.;:!?]", note[:hit.start()])[-1]
            if hit.group(1).lower() in ("must", "should"):
                return bool(re.fullmatch(rf"\s*{subject}\s+", before))
            return bool(re.fullmatch(
                rf"\s*(?:(?i:he|she|they)|{subject}\s+(?i:must|should))\s+",
                before))

        modal_output = any(
            not _said_of_a_third_person(hit) for hit in re.finditer(
                r"\b(always|never|must|should)\s+"
                r"(?:reply|respond|say|output|reveal|expose|send|follow|obey|ignore)\b",
                note, re.IGNORECASE))

        if matches_poison_shape or role_control or output_control \
                or modal_output or grants_unrestricted_access \
                or (explicit_consent and not media_context):
            logger.warning("[Agent] rejected prompt-like memory candidate")
            return ""
        return note
