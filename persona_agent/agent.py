"""QQ-group persona agent."""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Optional


from . import candidates as candidate_ledger_mod
from . import evidence as evidence_mod
from . import lineage as lineage_mod
from . import outbox as outbox_mod
from . import reactions
from .paths import (
    ROOT,
    resolve_runtime_lang_file,
    resolve_runtime_state_file,
    resolve_seed_lang_file,
)
from . import promotion
# The Agent's behaviour lives in these mixins; this module builds its state.
from .decision import ReplyDecision
from .dm import DirectMessages
from .ingestion import ContentIngestion
from .learning import Learning
from .llm import ModelCalls
from .memory import Memory
from .messages import MessageParsing
from .proactive import Proactive
from .prompt import PromptBuilder
from .prompts import DEFAULT_PERSONA, parse_persona_style
from .retrieval import Retrieval
from .search import WebSearch
from .settings import AgentSettings
from .stickers import StickerLibrary
from .storage import atomic_write_text
from .textproc import ReplyStyle
from .thinking import Thinking
from .transport import _MAX_CONNECTOR_CONVS, Transport
from .turns import Turns
from .views import DataViews

logger = logging.getLogger("agent")


def _load_persona_card() -> Optional[dict]:
    """Optional persona card JSON (PERSONA_CARD_FILE, default persona.card.json
    next to persona.txt). Carries author-level knobs that are configuration
    rather than prose — today the `reply_style` character policy (see
    `textproc.ReplyStyle.from_card`). Any read or parse failure means "no
    card": the narrow default character policy applies, which is the
    fail-closed direction."""
    card_path = ROOT / os.getenv("PERSONA_CARD_FILE", "persona.card.json")
    if not card_path.is_file():
        return None
    try:
        data = json.loads(card_path.read_text(encoding="utf-8"))
    except Exception:
        logger.warning("read persona card failed; using the default reply style")
        return None
    return data if isinstance(data, dict) else None


def _load_persona(lang: str = "en") -> str:
    """Load persona text from PERSONA_FILE (default persona.txt); fall back to
    the bundled persona.example.<lang>.txt, then DEFAULT_PERSONA. Falling back
    to the language-appropriate example keeps a fresh checkout coherent before
    the user writes their own persona.txt."""
    persona_path = ROOT / os.getenv("PERSONA_FILE", "persona.txt")
    if persona_path.is_file():
        try:
            return persona_path.read_text(encoding="utf-8").strip() or DEFAULT_PERSONA
        except Exception:
            logger.warning("read persona file failed, falling back to bundled example")
    example = ROOT / "data" / f"persona.example.{lang}.txt"
    if example.is_file():
        try:
            return example.read_text(encoding="utf-8").strip() or DEFAULT_PERSONA
        except Exception:
            pass
    return DEFAULT_PERSONA













class Agent(Turns, DirectMessages, MessageParsing, ReplyDecision, PromptBuilder,
            Retrieval, Thinking, ModelCalls, WebSearch, Proactive, Memory,
            DataViews, ContentIngestion, Transport, Learning):
    def __init__(self, settings: Optional[AgentSettings] = None, **overrides):
        """Wire one agent from one settings record.

        ``Agent(settings)`` is how the bot process builds it — see
        ``AgentSettings.from_env``. ``Agent(api_key=..., qq_bot_id=...)`` is the
        same act spelled shorter, for embedders, tools and the test suites:
        those keywords ARE the settings fields, and they build the record here.

        Nothing is parsed, defaulted or resolved below this line — that happens
        once, in settings.py. What is left is the three things wiring an agent
        actually is: put the configuration on it, create the empty runtime
        state, and open the learning layer.
        """
        if settings is None:
            settings = AgentSettings(**overrides)
        else:
            if not isinstance(settings, AgentSettings):
                raise TypeError(
                    "Agent() takes an AgentSettings, or its fields as "
                    f"keywords, not {type(settings).__name__}")
            if overrides:
                # Silently merging them would make which of the two won a
                # question about argument order rather than about the record.
                raise TypeError(
                    "Agent() takes a settings record or its fields as "
                    "keywords, not both — use dataclasses.replace(settings, "
                    "...) to vary one: " + ", ".join(sorted(overrides)))
        #: What this agent was configured with, kept whole. The attributes
        #: below are the live values, which a caller may change afterwards;
        #: this stays the record of what was asked for.
        self.settings = settings
        self._apply_settings(settings)
        self._init_runtime_state()
        self._init_learning_state()

        self.enabled = bool(self.api_key)
        if not self.enabled:
            logger.warning("[Agent] LLM_API_KEY not configured; %s disabled",
                           self.persona_name)
        if self.enabled and not self.persona_name:
            logger.warning("[Agent] PERSONA_NAME is empty; the bot will only respond to "
                           "explicit @-mentions (set PERSONA_NAME so it answers to its name)")

    def _apply_settings(self, s: AgentSettings) -> None:
        """Put the configuration on the agent, one field per attribute.

        A flat copy on purpose rather than reads through ``self.settings``:
        every layer of this package and every tool reads ``self.model``,
        ``self.llm_judge_model``, ``self.proactive_enabled`` and the rest
        directly, and a test that assigns one of them expects the agent to behave
        differently from the next call on.
        """
        self.api_key = s.api_key
        self.base_url = s.base_url
        self.model = s.model
        # Process-wide language. 'en' (default) is the primary build; 'zh'
        # selects the Chinese variant. Drives the reply validator, the
        # per-language data files, and the control-flow lexicons. Single
        # source of truth — everything language-dependent reads self.agent_lang.
        self.agent_lang = s.agent_lang
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

        raw_persona = (
            s.persona if s.persona is not None else _load_persona(self.agent_lang))
        # A persona document may end with a [style] declaration block. Parsing
        # strips it from the prose (so the model never reads raw knob config as
        # persona text) and keeps the knobs for prompt variants that use them.
        self.persona_style, self.persona = parse_persona_style(raw_persona)
        # The per-persona character policy. Without a card (or with a broken
        # one) this is the narrow fail-closed default.
        self.reply_style = ReplyStyle.from_card(_load_persona_card())
        # Scope identity of the current persona. The hash is always available;
        # persona_version is an optional operator-set label recorded alongside
        # it. Both are part of evidence-combination scope, so a persona rewrite
        # stops old evidence from authorizing changes to the new character.
        self.persona_version = s.persona_version
        self.persona_hash = hashlib.sha256(
            (self.persona or "").encode("utf-8")).hexdigest()[:12]

        # Sets, not the settings' tuples: these are read on every inbound
        # message and edited in place by the tests and the admin paths.
        self.admin_ids: set = set(s.admin_ids)
        self.access_groups: set = set(s.access_groups)
        self.access_dm_users: set = set(s.access_dm_users)
        self.connector_qq_platforms: set = set(s.connector_qq_platforms)
        self.connector_outbox_enabled = s.connector_outbox_enabled

        self.memory_file = resolve_runtime_state_file(s.memory_file)
        self.memory_max_per_conversation = s.memory_max_per_conversation

        self.eval_enabled = s.eval_enabled
        self.eval_model = s.eval_model
        self.eval_file = resolve_runtime_state_file(s.eval_file)

        self.vision_model = s.vision_model
        self.vision_api_key = s.vision_api_key
        self.vision_base_url = s.vision_base_url
        self.tavily_key = s.tavily_key

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
        # Evidence -> candidate -> promotion. A reaction is recorded as
        # evidence (append-only, immutable); adjudicating it proposes a
        # versioned candidate; only a promoted candidate is materialized into
        # the views retrieval reads. Nothing here writes examples_file or
        # feedback_file: those hold the seed-era and hand-approved rows, which
        # stay exactly as they are. See evidence.py / candidates.py /
        # promotion.py, and tools/candidates_admin.py for the human controls.
        self.promotion_policy = s.promotion_policy

    def _init_runtime_state(self) -> None:
        """The empty mutable state every agent starts with.

        Everything here is per-process bookkeeping — locks, windows, caches,
        de-dup rings. None of it is configuration, and the only disk read is
        the seen-message ring, which exists precisely to survive a restart.
        """
        self.model_calls: deque = deque()
        # Two independent fallback clocks:
        # _fallback_until = error-driven (real 429/5xx), applies to every mode
        # (provider throttling leaves no choice). Keyed by MODEL NAME, so a
        # failing judge or private model cools only itself instead of sending
        # every group reply to the fallback; with one configured model it is
        # a single entry and behaves like the scalar clock it replaced.
        # _freq_fallback_until = frequency-driven self-throttle, applies only
        # to self-initiated modes — called/admin are exempt. One per agent:
        # it throttles the persona's own chatter, not a model.
        self._fallback_until: dict[str, float] = {}
        self._freq_fallback_until: float = 0.0
        # Shared httpx connection pool, bucketed by (timeout, follow_redirects, ...).
        self._http_pool: dict = {}
        # Strong refs to fire-and-forget tasks. asyncio only weak-refs running
        # tasks, so a detached create_task() can be GC'd mid-flight; mirror the
        # _spawn pattern main.py already uses for webhook tasks.
        self._bg_tasks: set[asyncio.Task] = set()
        # Set by aclose(); read by _http so a use-after-close is visible
        # rather than silently leaking a fresh, never-closed pool.
        self._closed = False
        self._warned_use_after_close = False

        # Outbound throttle state: one small global gate lock (holds only
        # itself, never the group locks / send locks) + a per-target sliding
        # window. See _throttle_send.
        self._send_gate = asyncio.Lock()
        self._last_send_mono: float = 0.0
        self._send_window: dict = defaultdict(deque)
        # Connector conversation LRU (key -> last-touch monotonic). See
        # _touch_connector_conv.
        self._connector_conv_lru: dict[str, float] = {}
        self._connector_inflight: dict[str, int] = defaultdict(int)
        # Admission refusals already logged; see _log_refusal.
        self._refusals_logged: dict[str, None] = {}
        # Conversations already reported as unreachable; see _log_no_route.
        self._no_route_logged: dict[str, None] = {}

        # Bound at construction, like the rest of the buffer's shape: a later
        # change to self.chat_context_messages must not silently give new
        # conversations a different depth from the ones already running.
        chat_context_messages = self.chat_context_messages
        self.buffers: dict[str, deque] = defaultdict(
            lambda: deque(maxlen=chat_context_messages))
        self.counters: dict[str, int] = defaultdict(int)
        self.last_reply_at: dict[str, float] = defaultdict(float)
        self.locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        # Separate per-group send locks: _send_group sleeps through its typing
        # simulation, so it runs OUTSIDE the group lock (which would otherwise
        # block message intake for the whole send). The send lock still
        # serializes same-group sends so two replies can't interleave.
        self.send_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        # A group reply reserves its place before releasing the intake lock.
        # Later inbound tasks wait on this event before mutating the buffer, so
        # the reply cannot be committed behind messages it never saw.
        self._pending_outbound: dict[str, asyncio.Event] = {}
        # Private send locks are deliberately re-used by Transport's public
        # standalone-send wrapper. This task marker makes that lock re-entrant
        # for conversation paths which hold it through state commit.
        self._dm_send_tasks: dict[str, asyncio.Task] = {}
        self.active_users: dict[str, deque] = defaultdict(lambda: deque(maxlen=20))

        self.image_caption_cache: dict[str, str] = {}
        self.bili_info_cache: dict[str, dict] = {}
        # Generic URL metadata cache (key=url, value=preformatted descriptor
        # like `[bilibili-video] ...` / `[YouTube] "title" — author` /
        # `[site] "title" desc`).
        # Bounded FIFO at 200 entries — the same URL reposted across a
        # group only hits the network once.
        self.url_info_cache: dict[str, str] = {}
        self._wbi_keys: tuple[str, str] = ("", "")
        self._wbi_keys_ts: float = 0.0
        self.dm_history: dict[str, list[dict]] = {}
        # A DM message whose turn committed nothing (the model failed or
        # PASSed, the reply was blocked or never delivered), per user, the
        # last three. Kept out of dm_history, where a lone user turn
        # would break role alternation and silence the proactive cue, and
        # merged into the reader's next turn instead. See _handle_dm.
        self._dm_unanswered: dict[str, list[str]] = {}

        # Last time any human message landed in a group / DM (silence tracking),
        # and the last time the bot proactively initiated (per group and "dm:<uid>").
        self.last_activity_at: dict[str, float] = defaultdict(float)
        self.last_dm_activity_at: dict[str, float] = defaultdict(float)
        self.last_proactive_at: dict[str, float] = defaultdict(float)
        self._last_elicit_at: dict[str, float] = defaultdict(float)
        # Outbound message_ids of the current _send_group call, per group —
        # written under the per-group send lock, consumed right after it.
        self._sent_mids: dict[str, list[str]] = {}

        self._msg_seq: dict[str, int] = defaultdict(int)
        self._vision_in_flight: dict[str, int] = defaultdict(int)
        self._sticky_call: dict[str, dict] = {}

        # message_id ring for de-duping between webhook and periodic catch-up
        # paths. Persisted to disk so a restart doesn't accidentally re-handle
        # messages the bot already responded to before going down — without
        # this, the startup check_missed_mentions sees an empty ring and may
        # treat a still-recent @ mention as new.
        self._seen_msg_ids: deque = deque(maxlen=2000)
        self._seen_msg_file = resolve_runtime_state_file("seen_msg_ids.json")
        self._load_seen_msg_ids()
        # seen_msg_ids flush-throttle counters: the in-memory ring updates on
        # every message; disk writes are batched (see _remember_msg_id).
        self._seen_dirty = 0
        self._seen_last_flush = 0.0

        # Quote-reply resolution index: message_id -> "speaker: text". When a
        # later message quotes an earlier one, _extract_text looks it up here
        # (zero cost) before falling back to a NapCat get_msg call. Without it the
        # quoted content never reaches the model and it has to guess who/what it
        # is replying to → wrong-person / crossed-thread replies (off-topic).
        self._msg_index: dict[str, str] = {}
        self._msg_index_cap = 1000

        # How to reach each connector conversation unprompted, and the queue
        # its connector pulls from (outbox.py). Loaded on first use.
        self.connector_handles = outbox_mod.HandleStore(
            resolve_runtime_state_file("connector_handles.json"))
        self.outbox = outbox_mod.Outbox(self.connector_handles)

    def _load_seen_msg_ids(self) -> None:
        """Refill the de-dup ring from disk; a missing or broken file is fine."""
        try:
            if self._seen_msg_file.exists():
                with self._seen_msg_file.open("r", encoding="utf-8") as f:
                    loaded = json.load(f)
                if isinstance(loaded, list):
                    self._seen_msg_ids.extend(
                        str(value) for value in loaded[-2000:]
                        if isinstance(value, (str, int))
                    )
                    logger.info("[Agent] loaded %d seen message_ids from disk",
                                len(self._seen_msg_ids))
        except Exception as e:
            logger.warning("[Agent] seen_msg_ids load failed: %s: %s",
                           type(e).__name__, e)

    def _init_learning_state(self) -> None:
        """Open everything the agent remembers with: memory, reactions, the
        sticker library, the retrieval pools and the ledger views.

        Runs after :meth:`_apply_settings` because all of it hangs off the
        configured paths, the persona and the judgment model.
        """
        self.memories: dict[str, list[dict]] = self._load_memories()
        # letta-style core memory (per-group short note, always in prompt)
        self.core_memory_file = resolve_runtime_state_file("core_memory.json")
        self.core_memory: dict[str, str] = self._load_core_memory()
        self.candidates_file = resolve_runtime_state_file("candidates.jsonl")

        self.pending_reactions = reactions.PendingReplies(
            max_per_conv=self.settings.react_max_pending,
            ttl_sec=self.settings.react_ttl_s,
            fix_window_sec=self.settings.react_fix_window_s,
            max_conversations=_MAX_CONNECTOR_CONVS,
            state_file=self.memory_file.with_name("pending_reactions.json"),
        )
        # Per-user teaching reputation (never the admin); consistently bad
        # teachers are hard-blocked before any adjudicator call.
        self.teacher_stats = reactions.TeacherStats(
            resolve_runtime_state_file("teacher_stats.json"))

        stickers_path = Path(self.settings.stickers_dir)
        if not stickers_path.is_absolute():
            stickers_path = ROOT / stickers_path
        stickers_json = Path(self.settings.stickers_file)
        if not stickers_json.is_absolute():
            stickers_json = resolve_runtime_state_file(stickers_json)
        # Pass a one-line persona digest down to the sticker library; it uses
        # this to ask the tagger whether each sticker fits the persona (so
        # off-character stickers get persona_fit=false and aren't picked).
        # Truncated so it stays well under the tagger's prompt budget.
        persona_brief = (self.persona or "").replace("\n", " ").strip()[:200]
        self.stickers = StickerLibrary(
            stickers_dir=stickers_path,
            stickers_file=stickers_json,
            unknown_log=resolve_runtime_state_file("unknown_stickers.jsonl"),
            llm_caller=self._call_llm,
            # Cheap judgment model configured for THIS endpoint — a hardcoded
            # model name here would 404 on every other provider.
            tagger_model=self.llm_judge_model,
            persona_brief=persona_brief,
        )

        # Few-shot examples: curated seed/runtime rows plus a separate
        # ledger-derived view containing only promoted automatic candidates.
        self.examples_seed_file = resolve_seed_lang_file(
            "examples", "jsonl", self.agent_lang)
        self.examples_file = resolve_runtime_lang_file(
            "examples", "jsonl", self.agent_lang)
        self._examples_cache: list = []
        self._examples_mtime: tuple = ()  # see _pool_stamp
        # Append-aware reload bookkeeping for the RUNTIME file (see
        # _read_jsonl_appended): its size and consumed-byte offset at the last
        # read, plus a signature of the tail of that consumed prefix. The seed
        # is read-only, so only the runtime side can grow incrementally.
        # Setting _examples_mtime to anything that isn't the recorded tuple
        # (the `= 0.0` idiom the tools and tests use) still forces a full
        # reparse — the fast path is gated on a previous successful load.
        self._examples_eof: int = 0
        self._examples_offset: int = 0
        self._examples_sig: bytes = b""
        # In-memory dedup for runtime-appended examples: a frequent stock
        # phrase should only land in the pool once.
        self._auto_examples_seen: set[str] = set()

        self.feedback_seed_file = resolve_seed_lang_file(
            "feedback", "jsonl", self.agent_lang)
        self.feedback_file = resolve_runtime_lang_file(
            "feedback", "jsonl", self.agent_lang)
        self._pairs_cache: list = []
        self._pairs_mtime: tuple = ()  # see _pool_stamp
        self._pairs_eof: int = 0
        self._pairs_offset: int = 0
        self._pairs_sig: bytes = b""

        self._lineage_registered_for: tuple | None = None
        self._view_examples_cache: list = []
        self._view_examples_stamp: tuple = ()
        self._view_pairs_cache: list = []
        self._view_pairs_stamp: tuple = ()
        # Edge-triggered "every promoted row refused by scope" warning.
        self._scope_drop_warned = False

        # SillyTavern-style pre-send regex filter (rejects/replaces known bad patterns)
        self.output_filter_file = resolve_seed_lang_file(
            "output_filter", "json", self.agent_lang)
        self._filters_cache: list = []
        self._filters_stamp: tuple = ()

        # SillyTavern-style lorebook (keyword-triggered context entries)
        self.lorebook_file = resolve_seed_lang_file(
            "lorebook", "json", self.agent_lang)
        self._lorebook_cache: list = []
        self._lorebook_stamp: tuple = ()

    def _sidecar(self, attr: str, cls, path: Path):
        """Lazy sidecar of examples_file, rebuilt whenever the pool is repointed
        (test harness, benchmark arm, AGENT_RUNTIME_DIR) so evidence never
        accumulates against the wrong pool."""
        obj = getattr(self, attr, None)
        if obj is None or obj.path != path:
            obj = cls(path)
            setattr(self, attr, obj)
        return obj

    @property
    def example_candidates(self) -> promotion.CandidatePool:
        """Evidence gate in front of the example pool (see promotion.py)."""
        return self._sidecar("_example_candidates", promotion.CandidatePool,
                             self.examples_file.parent / "example_candidates.json")

    @example_candidates.setter
    def example_candidates(self, pool: promotion.CandidatePool) -> None:
        self._example_candidates = pool

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
        """Lazy like the ledgers: harnesses redirect the learning dir after
        __init__, and the file has to follow it. First access records the
        current revision and registers the lineage for scope comparison."""
        obj = self._sidecar("_persona_lineage", lineage_mod.PersonaLineage,
                            self.learning_dir / lineage_mod.FILE_NAME)
        key = (obj.path, self.persona_version, self.persona_hash)
        if self._lineage_registered_for != key:
            _root, extended = obj.extend(self.persona_version, self.persona_hash)
            hashes = obj.hashes(self.persona_version)
            # A failed save rolls the hash back out of the lineage, but this
            # process still runs as it: scope it in, or every earlier revision
            # falls out of scope until a restart manages to save.
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
        """Launch a background task and keep a strong reference to it until it
        finishes, so it can't be garbage-collected mid-flight."""
        t = asyncio.create_task(coro)
        self._bg_tasks.add(t)
        t.add_done_callback(self._bg_tasks.discard)
        return t



    def _validator_lang(self) -> str:
        """The language `_validate_reply_safe` reads its rules in.

        The only language-dependent rule in that validator is the zh one: a
        reply with no CJK and no marker is REJECTED, because a Chinese bot
        emitting pure ASCII is a suspected template or token leak. That rule
        is safe here because this deployment has a single language for both
        the persona and its readers — `agent_lang` — so ASCII from a zh agent
        really is anomalous. A deployment that ever grows a per-reader
        language must stop passing `agent_lang` unconditionally and apply the
        zh rule only where persona and reader language agree."""
        return self.agent_lang




















    # Every LLM call in this file goes through the provider's OpenAI-compatible
    # endpoint (/v1/chat/completions) over plain httpx — no vendor SDK. That is
    # what keeps every OpenAI-compatible provider interchangeable.















    def _remember_msg_id(self, mid) -> None:
        """Bank a message_id in the dedup ring and persist (throttled), so a
        restart doesn't re-answer @s already handled. Always str: the two
        producers disagree on int vs str."""
        self._seen_msg_ids.append(str(mid))
        self._seen_dirty += 1
        self._persist_seen()

    def _persist_seen(self, force: bool = False) -> None:
        """Flush the dedup ring to disk (throttled). force=True for shutdown."""
        now = time.monotonic()
        if not force and self._seen_dirty < 25 and (now - self._seen_last_flush) < 30.0:
            return
        try:
            atomic_write_text(
                self._seen_msg_file,
                json.dumps(
                    list(self._seen_msg_ids), ensure_ascii=False,
                    separators=(',', ':'),
                ) + "\n",
            )
            self._seen_dirty = 0
            self._seen_last_flush = now
        except Exception as e:
            # Disk full / read-only fs shouldn't fail message handling
            logger.debug("[Agent] seen_msg_ids persist failed: %s", e)

    def flush_state(self) -> None:
        """Force out writes still held by the throttles (dedup ring + sticker
        library) so catch-up dedup and sticker use_count/context updates aren't
        lost across a restart. Called from the lifespan shutdown hook."""
        self._persist_seen(force=True)
        self.pending_reactions.flush()
        self.connector_handles.flush(force=True)
        try:
            self.stickers._save(force=True)
        except Exception as e:
            logger.debug("[Agent] sticker flush on shutdown failed: %s", e)

    async def aclose(self) -> None:
        """Stop owned work, close transports, then persist final state.

        One-way: after this returns the Agent is spent. `_http` builds its
        pool lazily and rebuilds any entry whose client `is_closed`, so a
        `handle()` on a closed Agent does not fail — it quietly mints a fresh
        connection pool that nothing will ever close again. Two ways to get
        there: a forced uvicorn shutdown that lands while a synchronous
        `/v1/events` turn is still running, and any host that embeds
        `persona_agent.Agent` directly (it is a public, importable class) and
        reuses the object after closing it. Neither is loud today; the flag
        below makes both say so once.
        """
        self._closed = True
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




























    # -------- Core memory (letta style) --------
    CORE_MEMORY_MAX_CHARS = 400



















