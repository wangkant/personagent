"""What the persona remembers: memory commands, auto memory and core memory."""
from __future__ import annotations

import logging
import random
import re
import time
from typing import Optional

from . import access
from . import channels
from . import chatlangs
from .addressing import _HAS_CJK, mentions_name, name_regex
from .textproc import (
    _focus_tokens,
)

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


class Memory:
    def _load_memories(self) -> dict:
        return self._load_json_dict(self.memory_file)

    def _save_memories(self) -> None:
        self._save_json(self.memory_file, self.memories, "memory")

    def _append_memory(self, group_id: str, item: dict) -> None:
        items = self.memories.setdefault(group_id, [])
        items.append(item)
        if len(items) > self.memory_max_per_conversation:
            self._evict_memory(items)
        self._save_memories()

    def _load_core_memory(self) -> dict[str, str]:
        return self._load_json_dict(self.core_memory_file)

    def _save_core_memory(self) -> None:
        self._save_json(self.core_memory_file, self.core_memory, "core_memory")

    def _extract_core_update(self, reply: str) -> tuple[str, str]:
        """Split off a trailing [CORE_UPDATE]...[/CORE_UPDATE] note: (reply,
        note). Parse only, so a reply the filter blocks never commits its note."""
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
        # At the core note's own cap (plus a capped note's "...").
        note = self._validate_memory_candidate(
            new_note, max_chars=self.CORE_MEMORY_MAX_CHARS + 3)
        if note:
            self.core_memory[group_id] = note
            self._save_core_memory()
            logger.info("[Agent] core_memory updated (group=%s, %d chars)",
                        group_id, len(note))

    def _parse_memory_command(self, text: str) -> Optional[tuple[str, str, str]]:
        """(kind, what follows the keyword, chat language) when `text` is a
        memory command: learned, remember, forget or recall. None for
        conversation. Every language is tried; when two read it, the one the
        message looks written in wins."""
        table = self._memory_cmd_patterns()

        def pick(found: list[tuple[str, str]]) -> Optional[tuple[str, str]]:
            if len(found) < 2:
                return found[0] if found else None
            guess = chatlangs.detect(text, self.agent_lang)
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
            item: dict = {"text": content, "time": time.time()}
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
            self._append_memory(group_id, item)
            return say("noted")

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
            items = self.memories.get(group_id, [])
            before = len(items)
            # Query in text, never the reverse. Only the admin deletes others'
            # notes; an anonymous caller owns only unowned ones.
            kept = [
                it for it in items
                if not (word.search(it["text"]) if by_word else query in it["text"])
                or not owns(it)
            ]
            if len(kept) == before:
                return say("nothing_to_forget")
            self.memories[group_id] = kept
            self._save_memories()
            return say("forgotten")

        items = self.memories.get(group_id, [])
        if not is_admin:
            # A note about someone is shown only to them and its saver.
            items = [it for it in items if not it.get("user_id") or (
                caller and caller in (str(it.get("user_id")),
                                      str(it.get("saved_by") or "")))]
        if not items:
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
        return say("recall_head") + "\n" + "\n".join(lines)

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
        return mentions_name(text, self.persona_name)

    def _memory_cmd_patterns(self) -> list:
        """[(code, spec, {kind: regex or [regexes]})] for every chat language,
        cached per persona_name."""
        cached = getattr(self, "_mem_cmd_pats", None)
        if cached and cached[0] == self.persona_name:
            return cached[1]
        # Anchored at the start, so "I don't remember..." stays conversation.
        lead = r"^\s*(?:\[reply\]\s*)?"
        name = name_regex(self.persona_name) if self.persona_name else ""
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
        self._mem_cmd_pats = (self.persona_name, table)
        return table

    @staticmethod
    def _evict_memory(items: list[dict]) -> None:
        """Drop one entry for the cap: the oldest auto memory by `time` (merges
        refresh in place), else the first entry."""
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
        # Before the merge, which must not cross subjects.
        uid, name = self._memory_subject(group_id, text)
        old = self._restated_memory(items, text, now, uid,
                                    room=not channels.is_dm(group_id))
        # A shorter restatement is added beside the note rather than dropped.
        if old is not None and len(text) >= len(old["text"]):
            # Before `time` is overwritten, or `born` would move on every merge.
            old.setdefault("born", float(old.get("time") or now))
            old["text"] = text
            old["time"] = now
            # Only a DM gets here with a subject the note lacked.
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
                         subject: str = "", room: bool = False
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

        # Narrow lexical gates for control-plane shapes (hijacking, role swaps,
        # triggers, extraction, poisoning), not content moderation.
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
        low = note.lower()
        matches_poison_shape = any(
            re.search(pattern, low, re.IGNORECASE)
            for pattern in poison_patterns
        )

        # "Act as If is the title of..." describes a work, not a role.
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
