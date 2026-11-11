"""The Agent: one persona, wired from one settings record. Its behaviour lives
in one mixin per concern; this module builds its state."""
from __future__ import annotations

import asyncio
import dataclasses
import hashlib
import json
import logging
import os
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Optional


from . import candidates as candidate_ledger_mod
from . import channels
from . import embeddings as embeddings_mod
from . import evidence as evidence_mod
from . import langs
from . import lineage as lineage_mod
from . import outbox as outbox_mod
from . import reactions
from . import recent as recent_mod
from .paths import (
    ROOT,
    resolve_runtime_lang_file,
    resolve_runtime_state_file,
    resolve_seed_lang_file,
)
from .consolidate import Consolidation
from .decision import ReplyDecision
from .dm import DirectMessages
from .ingestion import ContentIngestion
from .learning import Learning
from .llm import ModelCalls
from .memory import Memory
from .messages import MessageParsing
from .proactive import Proactive
from .prompt import PromptBuilder
from .prompts import (DEFAULT_PERSONA, parse_persona_style,
                      render_persona_template)
from .retrieval import Retrieval
from .search import WebSearch
from .settings import AgentSettings
from .stickers import StickerLibrary
from .storage import atomic_write_text
from .textproc import ReplyStyle
from .transport import _MAX_CONNECTOR_CONVS, Transport
from .turns import Turns
from .views import DataViews

logger = logging.getLogger("agent")


def _load_persona_card() -> Optional[dict]:
    """The optional persona card (PERSONA_CARD_FILE) with the `reply_style`
    policy."""
    card_path = ROOT / os.getenv("PERSONA_CARD_FILE", "persona.card.json")
    if not card_path.is_file():
        return None
    return json.loads(card_path.read_text(encoding="utf-8"))


def _card_aliases(card: Optional[dict]) -> tuple[str, ...]:
    """The card's optional `aliases`: nicknames that call the persona too."""
    raw = card.get("aliases") if isinstance(card, dict) else None
    if not isinstance(raw, list):
        return ()
    names = (" ".join(a.split()) for a in raw if isinstance(a, str))
    return tuple(dict.fromkeys(n for n in names if n))


_persona_sources_logged: set[str] = set()


def _note_persona_source(source: str) -> None:
    """Say once per process which persona document the agent runs on."""
    if source not in _persona_sources_logged:
        _persona_sources_logged.add(source)
        logger.info("[Agent] persona: %s", source)


def _load_persona(lang: str = "en") -> str:
    """PERSONA_FILE (default persona.txt), else the bundled
    persona.example.<lang>.txt, else DEFAULT_PERSONA."""
    persona_path = ROOT / os.getenv("PERSONA_FILE", "persona.txt")
    if persona_path.is_file():
        text = persona_path.read_text(encoding="utf-8").strip()
        _note_persona_source(str(persona_path) if text
                             else f"{persona_path} is empty, using the built-in one")
        return text or DEFAULT_PERSONA
    example = resolve_seed_lang_file("persona.example", "txt", lang)
    if example.is_file():
        _note_persona_source(f"{example} (no {persona_path.name} yet)")
        return example.read_text(encoding="utf-8").strip() or DEFAULT_PERSONA
    _note_persona_source("the built-in default")
    return DEFAULT_PERSONA


class _RecentBuffers(dict):
    """The rooms' windows: a room's deque is built on first use, from the
    lines kept on disk when there are any."""

    def __init__(self, maxlen: int, saved):
        super().__init__()
        self.maxlen = maxlen
        self._saved = saved

    def __missing__(self, key):
        buf = deque(self._saved(key) or (), maxlen=self.maxlen)
        self[key] = buf
        return buf

    def get(self, key, default=None):
        if key in self:
            return dict.__getitem__(self, key)
        return self[key] if self._saved(key) else default


_RECENT_FLUSH_S = 60.0


class Agent(Turns, DirectMessages, MessageParsing, ReplyDecision, PromptBuilder,
            Retrieval, ModelCalls, WebSearch, Proactive, Consolidation, Memory,
            DataViews, ContentIngestion, Transport, Learning):
    def __init__(self, settings: Optional[AgentSettings] = None, **overrides):
        """Wire one agent from one settings record: ``Agent(settings)``, or
        the settings fields as keywords (``Agent(api_key=..., ...)``)."""
        if settings is None:
            settings = AgentSettings(**overrides)
        #: As configured; the attributes below are the live values.
        self.settings = settings
        self._apply_settings(settings)
        self._init_runtime_state()
        self._init_learning_state()

        self.enabled = bool(self.api_key)
        if not self.enabled:
            logger.warning("[Agent] LLM_API_KEY is not set, so the agent answers "
                           "nothing; `personagent init` sets it up")
        if self.enabled and not self.persona_name:
            logger.warning("[Agent] PERSONA_NAME is empty; the bot will only respond to "
                           "explicit @-mentions (set PERSONA_NAME so it answers to its name)")

    def _apply_settings(self, s: AgentSettings) -> None:
        """Copy the configuration onto the agent, one field per attribute, so
        callers can read and reassign `self.model` and the rest directly."""
        self.api_key = s.api_key
        self.base_url = s.base_url
        self.model = s.model
        # The validator, data files, ledgers and lexicons read `agent_lang`, en or
        # zh; what the agent says itself reads `chat_lang`, the configured language.
        self.agent_lang = langs.content(s.agent_lang)
        self.chat_lang = s.agent_lang
        self.llm_fallback_model = s.llm_fallback_model
        self.llm_fallback_base_url = s.llm_fallback_base_url
        self.llm_fallback_api_key = s.llm_fallback_api_key
        self.llm_fallback_thinking = s.llm_fallback_thinking
        self.llm_judge_model = s.llm_judge_model
        self.llm_dm_model = s.llm_dm_model
        self.api_max_retries = s.api_max_retries
        self.llm_timeout_s = s.llm_timeout_s
        self.llm_rate_window_s = s.llm_rate_window_s
        self.llm_rate_threshold = s.llm_rate_threshold
        self.llm_fallback_duration_s = s.llm_fallback_duration_s
        self.llm_rate_limit_cooldown_s = s.llm_rate_limit_cooldown_s

        self.qq_bot_id = s.qq_bot_id
        self.persona_name = s.persona_name
        self.qq_onebot_url = s.qq_onebot_url
        self.admin_name = s.admin_name
        self.admin_relationship = s.admin_relationship
        self.on_reply = s.on_reply

        self.chat_trigger_count = s.chat_trigger_count
        self.chat_context_messages = s.chat_context_messages
        self.chat_followup_window_s = s.chat_followup_window_s
        self.message_debounce_sec = s.message_debounce_sec

        if s.persona is not None:
            raw_persona = s.persona
        else:
            # A copied template still carries placeholders and a note to the reader.
            loaded = _load_persona(self.chat_lang)
            raw_persona = render_persona_template(
                loaded, bot_name=s.persona_name, admin_name=s.admin_name,
                admin_relationship=s.admin_relationship, lang=self.chat_lang)
            if not raw_persona:
                raw_persona = DEFAULT_PERSONA
                _note_persona_source("the persona file holds only a template's "
                                     "note, using the built-in one")
            elif raw_persona != loaded:
                _note_persona_source(
                    "filled in the template's {placeholders} and dropped its "
                    "note to the reader")
        # A trailing [style] block is stripped from the prose and kept as knobs.
        self.persona_style, self.persona = parse_persona_style(raw_persona)
        card = _load_persona_card()
        self.persona_aliases = _card_aliases(card)
        self.reply_style = dataclasses.replace(
            ReplyStyle.from_card(card),
            # Its name, and the shipped character it was set up as: renamed or
            # not, the whale girl may say she is DeepSeek's.
            own_names=(s.persona_name, s.persona_avatar))
        # Both are evidence scope; lineage.py keeps edits of one document in it.
        self.persona_version = s.persona_version
        self.persona_hash = hashlib.sha256(
            self.persona.encode("utf-8")).hexdigest()[:12]

        # Sets: edited in place by the tests and the admin paths.
        self.admin_ids: set = set(s.admin_ids)
        self.access_groups: set = set(s.access_groups)
        self.access_dm_users: set = set(s.access_dm_users)
        self.connector_qq_platforms: set = set(s.connector_qq_platforms)
        self.connector_outbox_enabled = s.connector_outbox_enabled

        self.memory_file = resolve_runtime_state_file(s.memory_file)
        self.memory_max_per_conversation = s.memory_max_per_conversation
        self.memory_tidy_every = s.memory_tidy_every
        self.memory_share_rooms = s.memory_share_rooms

        self.eval_enabled = s.eval_enabled
        self.eval_model = s.eval_model
        self.eval_file = resolve_runtime_state_file(s.eval_file)

        self.vision_model = s.vision_model
        self.vision_api_key = s.vision_api_key
        self.vision_base_url = s.vision_base_url
        self.tavily_key = s.tavily_key
        self.embedding_model = s.embedding_model
        self.embedding_base_url = s.embedding_base_url
        self.embedding_api_key = s.embedding_api_key

        self.proactive_enabled = s.proactive_enabled
        self.proactive_interval_s = s.proactive_interval_s
        self.proactive_min_silence_s = s.proactive_min_silence_s
        self.proactive_cooldown_s = s.proactive_cooldown_s
        self.proactive_prob = s.proactive_prob
        self.proactive_dm_min_silence_s = s.proactive_dm_min_silence_s
        self.proactive_dm_cooldown_s = s.proactive_dm_cooldown_s
        self.proactive_dm_prob = s.proactive_dm_prob
        self.proactive_platforms: set = set(s.proactive_platforms)

        self.evolve_auto_enabled = s.evolve_auto_enabled
        self.evolve_interval = s.evolve_interval
        self.evolve_threshold = s.evolve_threshold
        self.evolve_batch = s.evolve_batch
        self.evolve_model = s.evolve_model

        self.react_learn_enabled = s.react_learn_enabled
        self.react_model = s.react_model
        self.react_elicit_enabled = s.react_elicit_enabled
        self.react_elicit_delay_s = s.react_elicit_delay_s
        self.react_elicit_cooldown_s = s.react_elicit_cooldown_s

        self.promote_max_examples = s.promote_max_examples
        self.promote_max_feedback = s.promote_max_feedback
        # Learning writes the ledger and promoted views, never examples_file
        # or feedback_file (see learning.py).
        self.promotion_policy = s.promotion_policy
        self.promote_judge_enabled = s.promote_judge_enabled
        self.promote_judge_model = s.promote_judge_model
        self.promote_judge_interval_s = s.promote_judge_interval_s
        self.promote_judge_batch = s.promote_judge_batch
        self.promote_observe_max_days = s.promote_observe_max_days

    def _init_runtime_state(self) -> None:
        """The empty per-process state: locks, windows, caches, de-dup rings.
        The only disk read is the seen-message ring."""
        self.model_calls: deque = deque()
        # Error-driven fallback, per model name, for every mode.
        self._fallback_until: dict[str, float] = {}
        # Armed only by throttling and outages, never by one refused request.
        self._unreachable_until: dict[str, float] = {}
        # Frequency self-throttle, self-initiated modes only.
        self._freq_fallback_until: float = 0.0
        self._http_pool: dict = {}
        # Strong refs: asyncio only weak-refs running tasks.
        self._bg_tasks: set[asyncio.Task] = set()
        # The character's judgements (learning.py): backoff per item, items in
        # flight, recent call times, one lock per ledger language.
        self._adoption_retry: dict[str, tuple[int, float]] = {}
        self._adoption_inflight: set[str] = set()
        self._adoption_calls: list[float] = []
        self._adoption_locks: dict[str, asyncio.Lock] = {}

        # See _throttle_send; the gate lock never holds another lock.
        self._send_gate = asyncio.Lock()
        self._last_send_mono: float = 0.0
        self._send_window: dict = defaultdict(deque)
        self._connector_conv_lru: dict[str, float] = {}
        self._connector_inflight: dict[str, int] = defaultdict(int)
        self._refusals_logged: dict[str, None] = {}
        self._no_route_logged: dict[str, None] = {}
        self._last_excuse_at: dict[str, float] = {}
        self._excuse_inflight: set[str] = set()

        # Bound once, so every conversation keeps the same depth.
        # The recent lines of every chat on disk (recent.py), so a restart
        # keeps the conversation; lines and turns carry `t` and `seq`.
        self._recent = recent_mod.RecentStore(self.memory_file.with_name("recent.json"))
        self._recent_dirty: set[str] = set()
        self._recent_flushed_at: Optional[float] = None
        self.window_seq: dict[str, int] = {}
        # Every line or turn numbered up to this is consolidated (consolidate.py).
        self.folded_upto: dict[str, int] = {}
        # Unconsolidated lines that left a room's window, and a reader's turns
        # the DM trim dropped.
        self._spill: dict[str, list] = {}
        self._dm_spill: dict[str, list] = {}
        self.buffers: dict[str, deque] = _RecentBuffers(
            self.chat_context_messages, self._saved_lines)
        self.counters: dict[str, int] = defaultdict(int)
        self.last_reply_at: dict[str, float] = defaultdict(float)
        self.locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        # Sends run outside the group lock (typing sleeps would block intake);
        # this lock keeps same-group sends from interleaving.
        self.send_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        # Each conversation's line (turns._TurnGate): the turn in flight and
        # what arrived behind it, so no reply lands after a message it never saw.
        self._pending_outbound: dict[str, asyncio.Event] = {}
        # Makes a DM send lock re-entrant for the task already holding it.
        self._dm_send_tasks: dict[str, asyncio.Task] = {}
        self.active_users: dict[str, deque] = defaultdict(lambda: deque(maxlen=20))

        self.image_caption_cache: dict[str, str] = {}
        self.bili_info_cache: dict[str, dict] = {}
        # url -> rendered descriptor, a bounded FIFO.
        self.url_info_cache: dict[str, str] = {}
        self._wbi_keys: tuple[str, str] = ("", "")
        self._wbi_keys_ts: float = 0.0
        self.dm_history: dict[str, list[dict]] = {}
        # A user's DM messages let in and not answered yet, merged into their
        # next turn; what fits 1500 characters once a turn committed nothing
        # (_dm_turn).
        self._dm_unanswered: dict[str, list[str]] = {}
        # A reader's last declined-draft retry, by DM routing key (dm.py).
        self._declined_retry_at: dict[str, float] = {}
        # Who passed in a room's follow-up window (turns.py).
        self._followup_passed: dict[str, tuple] = {}

        # Silence tracking, and the last proactive opener per group / "dm:<uid>".
        self.last_activity_at: dict[str, float] = defaultdict(float)
        self.last_dm_activity_at: dict[str, float] = defaultdict(float)
        self.last_proactive_at: dict[str, float] = defaultdict(float)
        self._last_elicit_at: dict[str, float] = defaultdict(float)
        # When an opener went out, by group / "dm:<uid>" (proactive.py).
        self._opener_sent_at: dict[str, float] = {}
        # Written under the send lock, read right after it.
        self._sent_mids: dict[str, list[str]] = {}

        self._msg_seq: dict[str, int] = defaultdict(int)
        # Callers answered together in the turn now running, per conversation.
        self._turn_callers: dict = {}
        self._sticky_call: dict[str, dict] = {}

        # De-dups the webhook against the catch-up sweep; persisted so a restart
        # does not re-answer recent mentions.
        self._seen_msg_ids: deque = deque(maxlen=2000)
        self._seen_msg_file = resolve_runtime_state_file("seen_msg_ids.json")
        self._load_seen_msg_ids()
        # Disk writes of the ring are batched (see _persist_seen).
        self._seen_dirty = 0
        self._seen_last_flush = 0.0

        # message_id -> "speaker: text", checked before a get_msg call when a
        # message quotes another.
        self._msg_index: dict[str, str] = {}
        self._msg_index_cap = 1000

        # Reply handles and the outbox queue (outbox.py), loaded on first use.
        self.connector_handles = outbox_mod.HandleStore(
            resolve_runtime_state_file("connector_handles.json"))
        self.outbox = outbox_mod.Outbox(self.connector_handles)
        self._restore_recent()

    # ---- the recent window on disk ----------------------------------------

    def _saved_lines(self, conv: str) -> list:
        """A room's lines kept on disk, for its window's first use."""
        if channels.is_dm(conv):
            return []
        return list((self._recent.snapshot(conv) or {}).get("lines") or [])

    def _restore_recent(self) -> None:
        """Load recent.json (or, with MEMORY_KEEP_RECENT off, delete it). A
        room's lines wait for its first use; the rest is filled now."""
        store = self._recent
        if not getattr(self.settings, "memory_keep_recent", True):
            store.delete()
            return
        store.load()
        store.trim()
        for conv, entry in store.convs.items():
            self._load_recent_entry(conv, entry)
        if store.convs:
            logger.info("[Agent] recent messages restored for %d chat(s)",
                        len(store.convs))

    def _load_recent_entry(self, conv: str, entry: dict) -> None:
        """A chat's saved entry into the running state; what is held wins."""
        self.window_seq[conv] = max(int(entry.get("seq") or 0),
                                    self.window_seq.get(conv, 0))
        self.folded_upto[conv] = max(int(entry.get("folded_upto") or 0),
                                     self.folded_upto.get(conv, 0))
        uid = channels.dm_user(conv)
        marks = entry.get("marks") or {}
        key = channels.dm_learning_key(uid) if uid else conv
        if marks.get("reply") and not self.last_reply_at.get(conv):
            self.last_reply_at[conv] = marks["reply"]
        if marks.get("opener"):
            self._opener_sent_at.setdefault(key, marks["opener"])
        if marks.get("proactive") and not self.last_proactive_at.get(key):
            self.last_proactive_at[key] = marks["proactive"]
        if uid:
            if entry.get("dm"):
                self.dm_history.setdefault(uid, list(entry["dm"]))
            if entry.get("dm_spill"):
                self._dm_spill.setdefault(uid, list(entry["dm_spill"]))
            if entry.get("unanswered"):
                self._dm_unanswered.setdefault(uid, list(entry["unanswered"]))
            if not self.last_dm_activity_at.get(uid):
                self.last_dm_activity_at[uid] = entry.get("last_at") or 0.0
        else:
            if entry.get("spill"):
                self._spill.setdefault(conv, list(entry["spill"]))
            if not self.last_activity_at.get(conv):
                self.last_activity_at[conv] = entry.get("last_at") or 0.0

    def _wake(self, conv: str) -> None:
        """A chat in use: what an eviction let go of comes back from disk."""
        if conv in self.window_seq:
            return
        snap = self._recent.snapshot(conv)
        if snap:
            self._load_recent_entry(conv, snap)
        self.window_seq.setdefault(conv, 0)

    def _recent_entry(self, conv: str) -> Optional[dict]:
        """A chat's entry for recent.json from what is held now; None when
        nothing of it is left."""
        snap = self._recent.snapshot(conv) or {}
        if conv not in self.window_seq:
            # Not held (evicted, or never woken): the copy on disk stands.
            return dict(snap) if snap else None
        uid = channels.dm_user(conv)
        folded = int(self.folded_upto.get(conv, snap.get("folded_upto", 0)) or 0)
        key = channels.dm_learning_key(uid) if uid else conv
        marks = dict(snap.get("marks") or {})
        for name, value in (("reply", self.last_reply_at.get(conv)),
                            ("opener", self._opener_sent_at.get(key)),
                            ("proactive", self.last_proactive_at.get(key))):
            if value:
                marks[name] = value
        if uid:
            turns = (self.dm_history[uid] if uid in self.dm_history
                     else snap.get("dm") or [])
            entry = {"lines": [], "spill": [], "dm": list(turns),
                     "dm_spill": list(self._dm_spill.get(uid) or []),
                     "unanswered": list(self._dm_unanswered.get(uid) or [])[
                         -recent_mod.UNANSWERED_MAX:]}
            activity, rows = self.last_dm_activity_at.get(uid, 0.0), entry["dm"]
        else:
            buf = dict.get(self.buffers, conv)
            if buf is None:
                lines, older = list(snap.get("lines") or []), []
            else:
                held = list(buf)
                lines = held[-recent_mod.LINES_MAX:]
                older = [r for r in held[:-recent_mod.LINES_MAX]
                         if int(r.get("seq") or 0) > folded]
            entry = {"lines": lines, "spill": list(self._spill.get(conv) or []) + older,
                     "dm": [], "dm_spill": [], "unanswered": []}
            activity, rows = self.last_activity_at.get(conv, 0.0), lines
        if not any(entry[k] for k in recent_mod.CAPS):
            return None
        newest = max((float(r.get("t1") or r.get("t") or 0.0) for r in rows), default=0.0)
        entry.update(seq=int(self.window_seq.get(conv, snap.get("seq", 0)) or 0),
                     folded_upto=folded, marks=marks,
                     last_at=max(float(activity or 0.0), newest,
                                 float(snap.get("last_at") or 0.0)))
        return entry

    def _maybe_flush_recent(self, force: bool = False, only: str = "") -> None:
        """Write the changed chats to recent.json: at most once a minute, or
        now with `force` (shutdown) or `only` (a chat about to be evicted)."""
        dirty = self._recent_dirty
        if not getattr(self.settings, "memory_keep_recent", True):
            dirty.clear()
            return
        mono = time.monotonic()
        if not (force or only) and (not dirty or (
                self._recent_flushed_at is not None
                and mono - self._recent_flushed_at < _RECENT_FLUSH_S)):
            return
        store = self._recent
        convs = [only] if only else list(dirty)
        for conv in convs:
            entry = self._recent_entry(conv)
            if entry is None:
                store.drop(conv)
            else:
                store.put(conv, entry)
            dirty.discard(conv)
        trimmed = store.trim()
        if not convs and not trimmed:
            return
        try:
            store.write()
        except OSError as e:
            logger.warning("[Agent] recent messages save failed: %s", e)
        if not only:
            self._recent_flushed_at = mono

    def _load_seen_msg_ids(self) -> None:
        """Refill the de-dup ring from disk."""
        if self._seen_msg_file.exists():
            loaded = json.loads(self._seen_msg_file.read_text(encoding="utf-8"))
            self._seen_msg_ids.extend(loaded[-2000:])
            logger.info("[Agent] loaded %d seen message_ids from disk",
                        len(self._seen_msg_ids))

    def _init_learning_state(self) -> None:
        """Open memory, reactions, stickers, the retrieval pools and the ledger
        views; after _apply_settings, since all of it hangs off the settings."""
        self.memories: dict[str, list[dict]] = self._load_memories()
        # Conversations with a consolidation under way (consolidate.py).
        self._folding: set[str] = set()
        # One short note per conversation, always in the prompt.
        self.core_memory_file = resolve_runtime_state_file("core_memory.json")
        self.core_memory: dict[str, str] = self._load_core_memory()
        # Resolved once: every group and DM prompt checks it (prompt.py).
        self.owner_profile_file = resolve_runtime_state_file("owner_profile.json")
        self.candidates_file = resolve_runtime_state_file("candidates.jsonl")

        self.pending_reactions = reactions.PendingReplies(
            max_per_conv=self.settings.react_max_pending,
            ttl_sec=self.settings.react_ttl_s,
            fix_window_sec=self.settings.react_fix_window_s,
            max_conversations=_MAX_CONNECTOR_CONVS,
            state_file=self.memory_file.with_name("pending_reactions.json"),
        )
        # Teaching reputation; bad teachers are blocked before any adjudicator call.
        self.teacher_stats = reactions.TeacherStats(
            resolve_runtime_state_file("teacher_stats.json"))

        stickers_path = Path(self.settings.stickers_dir)
        if not stickers_path.is_absolute():
            stickers_path = ROOT / stickers_path
        stickers_json = Path(self.settings.stickers_file)
        if not stickers_json.is_absolute():
            stickers_json = resolve_runtime_state_file(stickers_json)
        # For the tagger's persona-fit check, kept short.
        persona_brief = self.persona.replace("\n", " ").strip()[:200]
        self.stickers = StickerLibrary(
            stickers_dir=stickers_path,
            stickers_file=stickers_json,
            unknown_log=resolve_runtime_state_file("unknown_stickers.jsonl"),
            llm_caller=self._call_llm,
            tagger_model=self.llm_judge_model,
            persona_brief=persona_brief,
        )

        # Seed and hand-approved rows; promoted candidates have their own views.
        self.examples_seed_file = resolve_seed_lang_file(
            "examples", "jsonl", self.agent_lang)
        self.examples_file = resolve_runtime_lang_file(
            "examples", "jsonl", self.agent_lang)
        self._examples_cache: list = []
        # A stamp from _pool_stamp; `= 0.0` forces the next reload.
        self._examples_mtime: tuple = ()
        # Replies already pooled, so self-eval does not propose them again.
        self._auto_examples_seen: set[str] = set()

        self.feedback_seed_file = resolve_seed_lang_file(
            "feedback", "jsonl", self.agent_lang)
        self.feedback_file = resolve_runtime_lang_file(
            "feedback", "jsonl", self.agent_lang)
        self._pairs_cache: list = []
        self._pairs_mtime: tuple = ()

        self._lineage_registered_for: tuple | None = None
        self._view_examples_cache: list = []
        self._view_examples_stamp: tuple = ()
        self._view_pairs_cache: list = []
        self._view_pairs_stamp: tuple = ()
        self._scope_drop_warned = False
        # The embedding backfill in flight, retry time and warned flag (retrieval.py).
        self._embedding_backfill: asyncio.Task | None = None
        self._embedding_retry_at = 0.0
        self._embedding_warned = False

        # Pre-send regex filter.
        self.output_filter_file = resolve_seed_lang_file(
            "output_filter", "json", self.agent_lang)
        self._filters_cache: list = []
        self._filters_stamp: tuple = ()

        # Keyword-triggered context entries.
        self.lorebook_file = resolve_seed_lang_file(
            "lorebook", "json", self.agent_lang)
        self._lorebook_cache: list = []
        self._lorebook_stamp: tuple = ()

    def _sidecar(self, attr: str, cls, path: Path):
        """A lazy sidecar object, rebuilt whenever its path moves (harnesses
        repoint the pools after __init__)."""
        obj = getattr(self, attr, None)
        if obj is None or obj.path != path:
            obj = cls(path)
            setattr(self, attr, obj)
        return obj

    @property
    def embedding_cache(self) -> embeddings_mod.EmbeddingCache:
        """Retrieval's vectors, beside the pools they were computed from."""
        return self._sidecar("_embedding_cache", embeddings_mod.EmbeddingCache,
                             self.learning_dir / "embeddings.jsonl")

    # ---- Evidence ledger (sidecars of the learned example pool) ----------

    @property
    def learning_dir(self) -> Path:
        return self.examples_file.parent

    @property
    def evidence_file(self) -> Path:
        return self.learning_dir / f"evidence.{self.agent_lang}.jsonl"

    @property
    def candidate_ledger_file(self) -> Path:
        return self.learning_dir / f"candidate_ledger.{self.agent_lang}.jsonl"

    @property
    def promoted_examples_file(self) -> Path:
        return self.learning_dir / f"promoted.examples.{self.agent_lang}.jsonl"

    @property
    def promoted_feedback_file(self) -> Path:
        return self.learning_dir / f"promoted.feedback.{self.agent_lang}.jsonl"

    @property
    def persona_lineage(self) -> lineage_mod.PersonaLineage:
        """Lazy, like the ledgers. First access records the current revision
        and registers the lineage for scope comparison."""
        obj = self._sidecar("_persona_lineage", lineage_mod.PersonaLineage,
                            self.learning_dir / lineage_mod.FILE_NAME)
        key = (obj.path, self.persona_version, self.persona_hash)
        if self._lineage_registered_for != key:
            _root, extended = obj.extend(self.persona_version, self.persona_hash)
            hashes = obj.hashes(self.persona_version)
            # After a failed save the running hash still has to be in scope.
            if self.persona_hash and self.persona_hash not in hashes:
                hashes.append(self.persona_hash)
            evidence_mod.register_persona_lineage(self.persona_version, hashes)
            self._lineage_registered_for = key
            if extended:
                logger.info(
                    "[Agent] persona document changed (hash %s); %d earlier "
                    "revision(s) stay in learning scope. Set PERSONA_VERSION to "
                    "start a new character instead.",
                    self.persona_hash, len(hashes) - 1)
        return obj

    @property
    def persona_identity(self) -> str:
        return self.persona_lineage.root(self.persona_version) or self.persona_hash

    @property
    def evidence_log(self) -> evidence_mod.EvidenceLog:
        return self._sidecar("_evidence_log", evidence_mod.EvidenceLog,
                             self.evidence_file)

    @evidence_log.setter
    def evidence_log(self, log: evidence_mod.EvidenceLog) -> None:
        self._evidence_log = log

    @property
    def candidate_ledger(self) -> candidate_ledger_mod.CandidateLedger:
        return self._sidecar("_candidate_ledger", candidate_ledger_mod.CandidateLedger,
                             self.candidate_ledger_file)

    @candidate_ledger.setter
    def candidate_ledger(self, ledger: candidate_ledger_mod.CandidateLedger) -> None:
        self._candidate_ledger = ledger

    def _spawn(self, coro) -> asyncio.Task:
        """Launch a background task, held until it finishes; a crash is logged."""
        t = asyncio.create_task(coro, name=getattr(coro, "__qualname__", None))
        self._bg_tasks.add(t)
        t.add_done_callback(self._on_bg_task_done)
        return t

    def _on_bg_task_done(self, task: asyncio.Task) -> None:
        self._bg_tasks.discard(task)
        if task.cancelled():
            return
        exc = task.exception()
        if exc is not None:
            logger.error("[Agent] background task %s crashed: %s: %s",
                         task.get_name(), type(exc).__name__, exc, exc_info=exc)

    def _remember_msg_id(self, mid) -> None:
        """Bank a message_id in the de-dup ring (as str: producers disagree)."""
        self._seen_msg_ids.append(str(mid))
        self._seen_dirty += 1
        self._persist_seen()

    def _persist_seen(self, force: bool = False) -> None:
        """Flush the dedup ring to disk (throttled). force=True for shutdown."""
        now = time.monotonic()
        if not force and self._seen_dirty < 25 and (now - self._seen_last_flush) < 30.0:
            return
        atomic_write_text(
            self._seen_msg_file,
            json.dumps(
                list(self._seen_msg_ids), ensure_ascii=False,
                separators=(',', ':'),
            ) + "\n",
        )
        self._seen_dirty = 0
        self._seen_last_flush = now

    def flush_state(self) -> None:
        """Force out the throttled writes (de-dup ring, reactions, handles,
        stickers) before shutdown."""
        self._persist_seen(force=True)
        self.pending_reactions.flush()
        self.connector_handles.flush(force=True)
        self.stickers._save(force=True)
        self._maybe_flush_recent(force=True)
        self._flush_memory_counters(force=True)
        if self.memory_state._dirty:
            self._save_memory_state(force=True)
        book = self.__dict__.get("_usage_book")
        if book is not None:
            book.flush(time.time())

    async def aclose(self) -> None:
        """Stop owned work, close transports, then persist final state."""
        # Waiting deliveries end as not sent, and open long-polls return.
        await self.outbox.aclose()
        tasks = [task for task in self._bg_tasks
                 if task is not asyncio.current_task()]
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        await self.stickers.aclose()

        clients = list(self._http_pool.values())
        self._http_pool.clear()
        if clients:
            await asyncio.gather(
                *(client.aclose() for client in clients
                  if not client.is_closed),
                return_exceptions=True)
        self.flush_state()

    CORE_MEMORY_MAX_CHARS = 400
