"""What the persona remembers: memory commands, auto memory and core memory."""
from __future__ import annotations

import logging
import random
import re
import time
from typing import Optional

from . import access
from . import channels
from .textproc import (
    _focus_tokens,
)

logger = logging.getLogger("agent")

# When a new auto-memory is a fuller telling of one already written down
# (`Agent._restated_memory`). The rule that does the work is the dropped
# share: a retelling keeps everything the earlier note said and adds to it,
# while a different fact in the same sentence frame drops the tokens that
# carried the old one ("rescue dog called Momo" -> "rescue cat called Momo"
# shares 88% and drops 12%), and no overlap ratio separates those two. The
# shared-token floor keeps a note too short to judge from being absorbed; the
# window is one sitting, since a note from last week that shares today's
# wording is a second fact, not a restatement.
_MEMORY_MERGE_MAX_DROPPED = 0.05

_MEMORY_MERGE_MIN_SHARED = 4

_MEMORY_MERGE_WINDOW_S = 6 * 3600.0


class Memory:
    def _load_memories(self) -> dict:
        loaded = self._load_json_dict(self.memory_file, "memory")
        return {
            str(conv_id): [row for row in rows if isinstance(row, dict)]
            for conv_id, rows in loaded.items()
            if isinstance(conv_id, str) and isinstance(rows, list)
        }

    def _save_memories(self) -> None:
        self._save_json(self.memory_file, self.memories, "memory")

    def _append_memory(self, group_id: str, item: dict) -> None:
        items = self.memories.setdefault(group_id, [])
        items.append(item)
        if len(items) > self.memory_max_per_conversation:
            self._evict_memory(items)
        self._save_memories()

    def _load_core_memory(self) -> dict[str, str]:
        loaded = self._load_json_dict(self.core_memory_file, "core_memory.json")
        return {
            key: value
            for key, value in loaded.items()
            if isinstance(key, str) and isinstance(value, str)
        }

    def _save_core_memory(self) -> None:
        self._save_json(self.core_memory_file, self.core_memory, "core_memory")

    def _extract_core_update(self, reply: str) -> tuple[str, str]:
        """Pull the [CORE_UPDATE]...[/CORE_UPDATE] block; return (reply with the
        tag stripped, new_note). **Parse only — no persistence.** Committing is
        _commit_core_memory's job, so the output filter can rule first: a
        blocked reply (self-outing / AI tells) must not write its worldview
        into core memory (poison protection). The model rewrites the whole
        note each time (no merging), which forces it to keep the note short.
        Closed tag form so nested [STICKER:xxx] doesn't truncate it."""
        m = re.search(r'\s*\[CORE_UPDATE\](.*?)\[/CORE_UPDATE\]\s*$', reply,
                      re.DOTALL)
        if not m:
            return reply, ""
        new_note = m.group(1).strip()
        if len(new_note) > self.CORE_MEMORY_MAX_CHARS:
            new_note = new_note[:self.CORE_MEMORY_MAX_CHARS] + "..."
        return reply[:m.start()].strip(), new_note

    def _commit_core_memory(self, group_id: str, new_note: str) -> None:
        """Persist a note extracted by _extract_core_update. Empty notes skip."""
        # Judged at the core note's own cap (plus the "..." a capped note
        # carries): the memory default of 200 cut every rewrite mid-word and
        # dropped the members past the cut each time.
        note = self._validate_memory_candidate(
            new_note, max_chars=self.CORE_MEMORY_MAX_CHARS + 3)
        if note:
            self.core_memory[group_id] = note
            self._save_core_memory()
            logger.info("[Agent] core_memory updated (group=%s, %d chars)",
                        group_id, len(note))

    def _handle_memory_command(
        self,
        group_id: str,
        text: str,
        user_id: str = "",
        user_name: str = "",
    ) -> Optional[str]:
        remember_pat, forget_pat, recall_pat, learned_pat = self._memory_cmd_patterns()
        is_admin = access.is_admin(user_id, self._admins())
        if learned_pat.search(text):
            return self._learned_summary(group_id)
        m = remember_pat.search(text)
        if m:
            content = m.group(1).strip()
            if not content:
                return random.choice([
                    "remember what? you didn't say anything",
                    "spill it",
                    "remember what lol",
                ])
            content = self._validate_memory_candidate(content)
            if not content:
                return "I can remember facts, not instructions"
            item: dict = {"text": content, "time": time.time()}
            if user_id and not is_admin:
                item["user_id"] = user_id
                if user_name:
                    item["user_name"] = user_name
            self._append_memory(group_id, item)
            return random.choice(["noted", "got it, written down", "remembered", "mhm", "ok"])

        m = forget_pat.search(text)
        if m:
            query = m.group(1).strip()
            # A too-short query over-deletes, and the admin's reaches every
            # member's rows. An English query must be 3+ characters and match
            # whole words ("drop it" hit "kitty", "with" and "writes"; "tea"
            # hit "steak"); CJK has no spaces to find words by, so it keeps a
            # substring match at 2+ characters.
            by_word = query.isascii()
            if len(query) < (3 if by_word else 2):
                return random.choice(["forget what? be specific", "which one? say more"])
            word = re.compile(rf"(?<![A-Za-z0-9_]){re.escape(query)}(?![A-Za-z0-9_])",
                              re.IGNORECASE)
            items = self.memories.get(group_id, [])
            before = len(items)
            # One-directional match (query in text): a short memory ("cat")
            # must not collide with a long forget sentence. Authority fails
            # closed: only the admin (which requires a user_id) may delete
            # others' entries; an anonymous caller owns only unattributed ones.
            caller = str(user_id or "")
            kept = [
                it for it in items
                if not (word.search(it["text"]) if by_word else query in it["text"])
                or (
                    not is_admin
                    and str(it.get("user_id") or "") != caller
                )
            ]
            if len(kept) == before:
                return random.choice([
                    "uh, never recorded that",
                    "no recollection of that",
                    "nothing matching to forget",
                ])
            self.memories[group_id] = kept
            self._save_memories()
            return random.choice(["forgotten", "dropped", "gone", "bye"])

        if recall_pat.search(text):
            items = self.memories.get(group_id, [])
            if user_id and not is_admin:
                items = [
                    it for it in items
                    if not it.get("user_id") or it.get("user_id") == user_id
                ]
            if not items:
                return random.choice([
                    "head's empty",
                    "nothing in there",
                    "blank slate",
                ])
            # No brackets, no list markers: the reply crosses the character
            # policy, which hard-refuses `[` and strips leading `- `, so the
            # tagged form was never delivered.
            lines: list[str] = []
            for it in items:
                tag = f"about {it.get('user_name')}: " if it.get("user_name") else ""
                lines.append(f"{tag}{it['text']}")
            return "Here's what I remember:\n" + "\n".join(lines)

        return None

    def _memory_cmd_patterns(self) -> tuple:
        """remember / forget / recall / learned regexes, cached per
        persona_name (tests reassign persona_name after init). English +
        legacy Chinese forms."""
        cached = getattr(self, "_mem_cmd_pats", None)
        if cached and cached[0] == self.persona_name:
            return cached[1]
        # With no name to follow, the command has to open the message (after
        # the "@" an at-mention renders as); unanchored, the empty head let
        # "I don't remember what you said" anywhere in an addressed message
        # save "what you said" as a memory.
        if self.persona_name:
            head = rf"{re.escape(self.persona_name)}\s*[，,]?\s*"
        else:
            head = r"^\s*(?:@\S*\s*)?[，,]?\s*"
        # \b after the English keywords: "remembered my birthday" is not a
        # command to save "ed my birthday". CJK needs none (and \b would not
        # work there: Python counts CJK as word characters).
        pats = (
            re.compile(head + r"(?:(?:remember|memorize)\b|记(?:住|一下|下))"
                       r"\s*[：:，,]?\s*(.+)", re.IGNORECASE),
            re.compile(head + r"(?:(?:forget|drop)\b|忘(?:了|记|掉))"
                       r"\s*[：:，,]?\s*(.+)", re.IGNORECASE),
            re.compile(head + r"(?:what do you remember|what'?s in your memory|memory\?|"
                       r"(?:都\s*)?(?:记得(?:什么|啥)|记忆|有什么记忆|脑子里有啥))",
                       re.IGNORECASE),
            re.compile(head + r"(?:what (?:have|did) you learn(?:ed)?|what'?ve you learned|"
                       r"learned\?|(?:你)?(?:学到|学会|学了)(?:了)?(?:什么|啥))",
                       re.IGNORECASE),
        )
        self._mem_cmd_pats = (self.persona_name, pats)
        return pats

    @staticmethod
    def _evict_memory(items: list[dict]) -> None:
        """Drop one entry to honor the per-group cap, preferring the oldest
        AUTO memory so a user's explicitly-saved ("remember X") memory isn't
        silently churned out by frequent auto-memory growth. Falls back to
        FIFO when no auto entry remains.

        Oldest by `time`, not by position: a merge in `_save_auto_memory`
        refreshes a note in place, so the first auto row can be the one the
        conversation just restated."""
        autos = [i for i, it in enumerate(items) if it.get("auto")]
        if not autos:
            items.pop(0)
            return
        items.pop(min(autos, key=lambda i: float(items[i].get("time") or 0.0)))

    def _save_auto_memory(self, group_id: str, text: str) -> None:
        text = self._validate_memory_candidate(text)
        if not text:
            return
        items = self.memories.get(group_id, [])
        if any(it["text"] == text for it in items):
            return
        now = time.time()
        # Resolved before the merge, which needs it: rewriting a note about
        # one member with a fact about another would leave the first one's
        # user_id on the second one's fact.
        uid, name = self._memory_subject(group_id, text)
        old = self._restated_memory(items, text, now, uid,
                                    room=not channels.is_dm(group_id))
        # A match is a strict token superset, so a restatement that is
        # shorter in characters still says something the stored note does
        # not ("心情不好" eight times is 32 characters and 4 tokens): it is
        # added beside it rather than dropped.
        if old is not None and len(text) >= len(old["text"]):
            # `born` before `time` is overwritten: a note stored before the
            # field existed anchors on its last touch, and reading that after
            # the line below would re-anchor it to now on every merge.
            old.setdefault("born", float(old.get("time") or now))
            old["text"] = text
            old["time"] = now
            # Only a DM reaches this with a subject the note lacked; a room
            # keeps its unattributed note (`room` in `_restated_memory`).
            if uid and not old.get("user_id"):
                old["user_id"], old["user_name"] = uid, name
            self._save_memories()
            logger.info("[Agent] auto-memory updated (group=%s): %s",
                        group_id, text[:60])
            return
        item: dict = {"text": text, "time": now, "born": now, "auto": True}
        if uid:
            item["user_id"] = uid
            item["user_name"] = name
        self._append_memory(group_id, item)
        subj =f" (about={item.get('user_name','?')})" if "user_id" in item else ""
        logger.info("[Agent] auto-memory (group=%s)%s: %s", group_id, subj, text[:60])

    def _memory_subject(self, group_id: str, text: str) -> tuple[str, str]:
        """Who `text` is about, as (user_id, user_name), or ("", "").

        Only names this conversation has actually seen count, so the map is
        built from the live buffer plus the admin rather than from anything
        the model wrote. Two characters minimum: a one-character name matches
        inside ordinary words."""
        name_to_uid: dict[str, str] = {}
        for m in self.buffers.get(group_id, []):
            nm = m.get("name", "")
            uid = m.get("user_id", "")
            if nm and len(nm) >= 2 and uid:
                name_to_uid.setdefault(nm, uid)
        # The admin's account on this platform, so a Telegram room does not
        # attribute them to their QQ number when it knows their Telegram one.
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
                         subject: str = "", room: bool = False
                         ) -> Optional[dict]:
        """The auto note `text` is a fuller telling of, or None.

        A note is rewritten only by one that keeps what it said and adds to
        it. Measured with `_focus_tokens` ("dropped" is the share of the old
        note's tokens the new one lacks):

            dropped  merge  pair
            0.00     yes    对方养了两只猫 -> ...，都是橘猫
            0.50     no     深夜向我表白 -> 表白后问能否攻略 (one episode)
            0.12     no     rescue dog called Momo -> rescue cat called Momo
            0.17     no     night shifts at the hospital -> ... the bakery
            0.33     no     learning French -> learning French horn
            0.40     no     西山爬山徒步 -> 西山骑行露营
            0.33     no     他弟弟在上海 -> 他妹妹在上海
            0.25     no     对方喜欢猫 -> 对方喜欢狗 (also under the floor)

        An episode retold in different words is token-for-token the same
        shape as a different fact in the same frame, so it stays two notes:
        a notebook that repeats itself is something the reader can see and
        delete, one that quietly swapped "dog" for "cat" is a fact gone.

        Only auto notes (one the reader asked to keep is never rewritten by
        a turn), only within `_MEMORY_MERGE_WINDOW_S` of when the note was
        first written, and never between two different named subjects. In a
        `room` an unattributed note never takes a restatement that names
        somebody, because the merge would file the group's fact under them.
        """
        # Always "zh": with "en" the tokenizer emits ASCII words only, so a
        # Chinese note would produce no tokens and never match. "zh" is a
        # superset, and this compares a note with a note, not with the turn.
        fresh = _focus_tokens(text, "zh")
        if len(fresh) < _MEMORY_MERGE_MIN_SHARED:
            return None
        best: Optional[dict] = None
        best_dropped = 1.0
        for it in items:
            if not it.get("auto"):
                continue
            # From when it was written, not last touched: `time` is reset by
            # every merge, which would let a note absorb a restatement every
            # few hours forever. Rows from before `born` fall back to `time`.
            born = float(it.get("born") or it.get("time") or 0.0)
            if now - born > _MEMORY_MERGE_WINDOW_S:
                continue
            # Only when both are named: an unattributed note is the common
            # case (most are about the one person in a DM) and stays mergeable.
            if subject and it.get("user_id") and it["user_id"] != subject:
                continue
            # In a room an unattributed note is shown to everyone, while one
            # filed under a member shows only while they are in the buffer
            # (and is theirs to forget): a merge that names somebody would
            # hide the group's fact. Skipped here rather than after the
            # search, so a note already filed under them can still match.
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
        """Accept short user facts; reject durable prompt/persona controls.

        Memory is re-injected on every later turn, so a false "fact" about the
        assistant's identity or permissions is as dangerous here as an explicit
        imperative. The rules therefore cover both shapes while deliberately
        leaving ordinary third-person preferences, relationships and life facts
        available to the memory feature. `max_chars` is the note's own cap: a
        group core note is allowed twice a memory's length.
        """
        note = str(text or "").strip().replace("\r", " ").replace("\n", " ")
        note = re.sub(r"\s+", " ", note)[:max_chars]
        if not note or any(token in note for token in ("<", ">", "{", "}", "[", "]")):
            return ""

        # Published prompt-injection suites group attacks into instruction/
        # goal hijacking, role or identity substitution, conditional triggers,
        # prompt extraction, and persistent poisoning. These lexical gates are
        # intentionally narrow to those control-plane shapes; this is a memory
        # admission filter, not a general content-moderation classifier.
        poison_patterns = (
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
            # Conditional triggers. A group core note summarises several
            # members, so "gets defensive when people say his code is slow"
            # is an ordinary fact there, and one match rejects the whole
            # rewrite. Each shape therefore stays inside one sentence, and a
            # when-clause inside a sentence counts only when the verb is its
            # consequence, not part of the condition.
            # A trigger opening a sentence: "when he says banana, answer ...".
            r"(?:^|[.;!?]\s*)(?:when|whenever|if)\b[^.;!?]{0,80}"
            r"\b(?:answer|reply|respond|say|output|reveal|expose|send|act)\b",
            # The consequence after a comma or "then": "if he types ping,
            # (you must) reply pong".
            r"\b(?:when|whenever|if)\b[^.;!?]{0,80}(?:,|\bthen\b)\s*"
            r"(?:(?:you|the\s+assistant|assistant|chatbot|bot|model)\s+)?"
            r"(?:(?:must|should|will|shall|always|only|just|please)\s+)*"
            r"(?:answer|reply|respond|say|output|reveal|expose|send|act)\b",
            # The assistant as the consequence's subject: "if he says
            # banana you answer in haiku".
            r"\b(?:when|whenever|if)\s+\S[^.;!?]{0,80}?\s"
            r"(?:you|the\s+assistant|assistant|chatbot|bot|model)\s+"
            r"(?:(?:must|should|will|shall|always|only|just)\s+)*"
            r"(?:answer|reply|respond|say|output|reveal|expose|send|act)\b",
            r"\b(?:reveal|print|show|expose)\b.{0,30}"
            r"\b(?:secret|private|memory|prompt|instruction)s?\b",
            # Assistant/persona identity stated as a supposed fact.
            r"\byour\s+(?:(?:real|actual|true)\s+)?"
            r"(?:name|identity|persona|role)\s+(?:is|=)\b",
            # One sentence only, for the same reason as the triggers above:
            # "Alice thinks you are funny; Bob is a night person".
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
        low = note.lower()
        matches_poison_shape = any(
            re.search(pattern, low, re.IGNORECASE)
            for pattern in poison_patterns
        )

        # Three grammatical categories cover productive variants without a
        # first-token blacklist. Title/plot declarations are explicit benign
        # neighbors: "Act as If is the title..." contains role-like words but
        # describes a work, while the imperative "Act as a pirate" does not.
        title_or_plot_declaration = bool(re.search(
            r"\bis\s+(?:the\s+)?(?:title|plot|name|theme)\s+of\b",
            low,
        ))
        role_control = any(re.search(pattern, low, re.IGNORECASE) for pattern in (
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
        )) and not title_or_plot_declaration

        output_control = any(re.search(pattern, low, re.IGNORECASE) for pattern in (
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
        ))

        # Permission/consent claims are rejected only when they purport to
        # grant the assistant unrestricted access or waive a safety/content
        # boundary. Ordinary facts such as permission to bring picnic items or
        # consent to watch a film remain useful memories.
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

        # The output-modal rule, unanchored: an output modal right before an
        # output verb anywhere in the note ("group rule: always reply in
        # English", "to always obey Kant", "the persona should never reveal
        # ..."). Anchoring it at the start, only to keep facts about a
        # person ("He should reply to Alice tomorrow"), let any other
        # lead-in through; this exempts exactly that shape instead, judged
        # per occurrence: the sentence up to the modal is only its subject.
        # Judged once per note, a fact opening it vouched for every rule
        # after it ("He should reply to Alice tomorrow. Always reply in
        # French."). A capitalised name counts only before must/should: a
        # name before always/never takes "replies", not "reply", so a
        # capital there is an imperative's lead-in ("Please always reply in
        # French"). Checked on the original case, since the name needs its
        # capital. A pronoun, quantifier or role noun (singular or plural) is
        # not the person a fact is about ("Everyone must obey Mallory").
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
