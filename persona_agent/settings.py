"""Everything the agent is configured with: one record, built once, passed in.

``Agent`` has no parsing logic or defaults of its own; it copies these fields.

* ``AgentSettings(...)``: literal defaults for the deployment settings, the
  environment for the operational knobs (the loops, reaction learning, the
  retrieval caps). An embedder, tool or test gets the agent it configured,
  not one the surrounding ``.env`` configured.
* ``AgentSettings.from_env()``: also reads the deployment settings
  (``LLM_API_KEY``, ``PERSONA_NAME``, ``ADMIN_IDS``, ...). This is the bot
  process.

Both share the defaults ``.env.example`` documents, and every read goes
through :mod:`persona_agent.config_env`: a bad value means the default and a
warning.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field, fields
from typing import Awaitable, Callable, Optional

from . import access, channels, promotion
from .config_env import (DEFAULT_LLM_BASE_URL, DEFAULT_LLM_MODEL, env_bool,
                         env_float, env_int, env_str, vision_endpoint_from_env)

logger = logging.getLogger("agent")

#: Spellings of the two supported languages that mean one of them.
_LANG_ALIASES = {"cn": "zh", "chinese": "zh", "中文": "zh", "english": "en"}

#: The shortest EVOLVE_INTERVAL_HOURS the loop runs at; 0 runs it back to back.
MIN_EVOLVE_INTERVAL_HOURS = 0.1

_warned_langs: set[str] = set()


def _env(read):
    """A field whose default is ``read(None)`` (os.environ); ``from_env(env=...)``
    calls ``read(env)`` instead."""
    return field(default_factory=lambda: read(None), metadata={"env": read})


def normalize_lang(value: object) -> str:
    """AGENT_LANG as the agent uses it: "zh" for zh-CN, zh_cn, cn, chinese;
    "en" for en-US and blank. Anything else is kept (lowercased) with a
    warning, since it names data files and ledgers that may already exist."""
    raw = str(value or "").strip().lower().replace("_", "-")
    if not raw:
        return "en"
    lang = _LANG_ALIASES.get(raw) or raw.split("-", 1)[0]
    if lang in ("zh", "en"):
        return lang
    if raw not in _warned_langs:
        _warned_langs.add(raw)
        logger.warning("AGENT_LANG=%r is neither en nor zh; the prompts and "
                       "the shipped data are English and Chinese only", value)
    return raw


@dataclass
class AgentSettings:
    """One agent's configuration, fully resolved; the fields are the keywords
    ``Agent(...)`` accepts.

    ``__post_init__`` resolves every setting (empty-model fallbacks, URL
    trimming, coercions) and is idempotent, so ``dataclasses.replace`` is safe.
    """

    # ---- the LLM endpoint -------------------------------------------------
    api_key: str
    base_url: str = DEFAULT_LLM_BASE_URL
    model: str = DEFAULT_LLM_MODEL
    #: Model name for DMs, on the primary endpoint unless it is the fallback's
    #: name (``endpoints.endpoint_for``). Blank resolves to ``model``, never "".
    llm_dm_model: str = ""
    llm_fallback_model: str = ""
    #: The fallback model's own endpoint, so a primary outage is not also the
    #: fallback's. Blank = the primary's; only a fallback model distinct from
    #: ``model`` is sent there.
    llm_fallback_base_url: str = ""
    llm_fallback_api_key: str = ""
    #: Send DeepSeek's ``thinking`` field to the fallback's host unasked. Off:
    #: an unlisted host is probed first (``llm.ModelCalls._thinking_verdict``).
    llm_fallback_thinking: bool = False
    #: The cheap model that decides PASS or reply in self-initiated modes; the
    #: reply itself is always the main model's. Blank = the fallback model.
    llm_judge_model: str = _env(
        lambda env: env_str("LLM_JUDGE_MODEL", "", strip=True, env=env))
    #: LLM transient-error retry count (jittered backoff; 0 disables).
    api_max_retries: int = _env(
        lambda env: env_int("LLM_MAX_RETRIES", 2, minimum=0, env=env))
    #: Main LLM call timeout (seconds); reasoning models can be slow.
    llm_timeout_s: float = _env(
        lambda env: env_float("LLM_TIMEOUT_S", 120.0, minimum=1.0, env=env))

    # ---- identity ---------------------------------------------------------
    qq_bot_id: str = ""
    persona_name: str = ""
    #: NapCat's HTTP server. Blank = none: no missed-mention sweep, and QQ
    #: messages nobody asked for go out only through a connector's outbox.
    qq_onebot_url: str = ""
    admin_name: str = ""
    admin_relationship: str = ""
    #: 'en' or 'zh'; blank means whatever ``AGENT_LANG`` says.
    lang: str = ""
    #: The resolved language everything language-dependent reads.
    agent_lang: str = ""

    # ---- conversation -----------------------------------------------------
    chat_trigger_count: int = 30
    chat_context_messages: int = 120
    chat_followup_window_s: int = 120
    memory_file: str = "memory.json"
    memory_max_per_conversation: int = 50
    message_debounce_sec: float = 2.5
    #: Persona document; ``None`` means the agent loads ``PERSONA_FILE``, so
    #: file reads stay out of this record.
    persona: Optional[str] = None
    #: Operator label stored with the persona hash; both scope evidence, so old
    #: evidence cannot authorize changes to a rewritten persona.
    persona_version: str = _env(
        lambda env: env_str("PERSONA_VERSION", "", strip=True, env=env))
    on_reply: Optional[Callable[[str, str], Awaitable[None]]] = None

    # ---- who may talk to it -----------------------------------------------
    # Entries are "<platform>:<id>", a bare id being QQ (see access.py).
    #: The admin's accounts (``ADMIN_IDS``), one person on every platform.
    admin_ids: tuple[str, ...] = ()
    #: Groups the agent admits (``ACCESS_GROUPS``), per platform: a platform
    #: with no entries is not restricted here.
    access_groups: tuple[str, ...] = _env(
        lambda env: access.identity_from_env(env).written["ACCESS_GROUPS"])
    #: Who else may DM the bot (``ACCESS_DM_USERS``). Admins always may;
    #: these take the "ordinary friend" branch rather than the admin's.
    access_dm_users: tuple[str, ...] = _env(
        lambda env: access.identity_from_env(env).written["ACCESS_DM_USERS"])
    #: Connector platforms whose ids are minted bare, on NapCat's keys. The
    #: operator's call, never the connector's: a bare id carries QQ authority.
    connector_qq_platforms: tuple[str, ...] = ()
    #: Whether the outbox may carry messages nobody asked for (openers,
    #: follow-ups, excuses). Off, it answers 404 and those stay QQ-only.
    connector_outbox_enabled: bool = _env(
        lambda env: env_bool("CONNECTOR_OUTBOX_ENABLED", True, env=env))

    # ---- self-evaluation --------------------------------------------------
    eval_enabled: bool = False
    eval_model: str = ""
    eval_file: str = "eval.jsonl"

    # ---- vision, search, stickers -----------------------------------------
    vision_model: str = ""
    vision_api_key: str = ""
    vision_base_url: str = ""
    tavily_key: str = ""
    stickers_dir: str = "stickers"
    stickers_file: str = "stickers.json"

    # ---- retrieval embeddings (optional) ---------------------------------
    #: An OpenAI-compatible /embeddings model that adds a semantic signal to
    #: retrieval. Blank = off: rows are ranked on words, scope and recency.
    embedding_model: str = ""
    #: Blank = the primary's endpoint and key. A URL of its own is sent
    #: ``embedding_api_key`` only, never ``api_key``.
    embedding_base_url: str = ""
    embedding_api_key: str = ""

    # ---- model-error fallback ---------------------------------------------
    #: Shared by two clocks: the per-model error fallback (a failed model is
    #: skipped for ``llm_fallback_duration_s``) and the frequency self-throttle
    #: (self-initiated modes only).
    llm_rate_window_s: int = 120
    llm_rate_threshold: int = 30
    llm_fallback_duration_s: int = 180
    #: How long a model that answered 429 is skipped: metered, not broken, so
    #: only the next few turns avoid it.
    llm_rate_limit_cooldown_s: int = 20

    # ---- the proactive loop -----------------------------------------------
    #: Occasionally speak first. Off by default and heavily gated: chats seen
    #: before, outside sleep hours, after a quiet stretch, with cooldowns, a
    #: low per-tick probability and a model told to PASS. DMs go to the admin
    #: and the DM allowlist only.
    proactive_enabled: bool = _env(
        lambda env: env_bool("PROACTIVE_ENABLED", False, env=env))
    proactive_interval_s: int = _env(  # tick: 25 min
        lambda env: env_int("PROACTIVE_INTERVAL_S", 1500, minimum=1, env=env))
    proactive_min_silence_s: int = _env(  # group quiet >= 45 min
        lambda env: env_int("PROACTIVE_MIN_SILENCE_S", 2700, minimum=0, env=env))
    proactive_cooldown_s: int = _env(  # >= 3h between group initiations
        lambda env: env_int("PROACTIVE_COOLDOWN_S", 10800, minimum=0, env=env))
    proactive_prob: float = _env(  # per eligible tick
        lambda env: env_float("PROACTIVE_PROB", 0.25, minimum=0.0, maximum=1.0,
                              env=env))
    proactive_dm_min_silence_s: int = _env(  # DM quiet >= 4h
        lambda env: env_int("PROACTIVE_DM_MIN_SILENCE_S", 14400, minimum=0,
                            env=env))
    proactive_dm_cooldown_s: int = _env(  # >= 24h between DMs
        lambda env: env_int("PROACTIVE_DM_COOLDOWN_S", 86400, minimum=0,
                            env=env))
    proactive_dm_prob: float = _env(
        lambda env: env_float("PROACTIVE_DM_PROB", 0.2, minimum=0.0,
                              maximum=1.0, env=env))
    #: Platforms the loop may speak first on; empty is all it can reach. A
    #: CONNECTOR_QQ_PLATFORMS name means QQ, whose keys it mints.
    proactive_platforms: tuple[str, ...] = _env(
        lambda env: access.split_ids(
            env_str("PROACTIVE_PLATFORMS", "", strip=True, env=env)))

    # ---- the self-evolution loop ------------------------------------------
    #: Opt-in loop turning low-score eval entries into BAD/OK candidates, which
    #: still need corroborating evidence or a human promotion.
    evolve_auto_enabled: bool = _env(
        lambda env: env_bool("EVOLVE_AUTO_ENABLED", False, env=env))
    evolve_interval_hours: float = _env(
        lambda env: env_float("EVOLVE_INTERVAL_HOURS", 6.0, minimum=0.0, env=env))
    #: 3, not 2: on the evaluator's scale (learning.py) 3 is "drifting into
    #: assistant register", the failure the loop exists to correct.
    evolve_threshold: int = _env(
        lambda env: env_int("EVOLVE_THRESHOLD", 3, env=env))
    evolve_batch: int = _env(  # diagnoses per tick
        lambda env: env_int("EVOLVE_BATCH", 5, minimum=1, env=env))
    evolve_model: str = _env(
        lambda env: env_str("EVOLVE_MODEL", "", strip=True, env=env))

    # ---- reaction learning ------------------------------------------------
    #: The primary learning signal: a sent reply waits (bounded, TTL) for a
    #: directed reaction (a quote, an @/name call, the next DM), which one model
    #: call classifies. The verdict is evidence, never a pool write.
    react_learn_enabled: bool = _env(
        lambda env: env_bool("REACT_LEARN_ENABLED", True, env=env))
    react_model: str = _env(
        lambda env: env_str("REACT_MODEL", "", strip=True, env=env))
    react_max_pending: int = _env(
        lambda env: env_int("REACT_MAX_PENDING", 4, minimum=1, env=env))
    react_ttl_s: float = _env(
        lambda env: env_float("REACT_TTL_S", 900.0, minimum=0.0, env=env))
    react_fix_window_s: float = _env(
        lambda env: env_float("REACT_FIX_WINDOW_S", 600.0, minimum=0.0, env=env))
    #: After a rejection with no correction, ask what they meant: delayed, so
    #: never over its own reply, and cooldown-limited, so it never begs.
    react_elicit_enabled: bool = _env(
        lambda env: env_bool("REACT_ELICIT_ENABLED", True, env=env))
    react_elicit_delay_s: float = _env(
        lambda env: env_float("REACT_ELICIT_DELAY_S", 120.0, minimum=0.0, env=env))
    react_elicit_cooldown_s: float = _env(
        lambda env: env_float("REACT_ELICIT_COOLDOWN_S", 3600.0, minimum=0.0,
                              env=env))

    # ---- retrieval --------------------------------------------------------
    #: Caps on the promoted-candidate views (0 = none); the ``data/`` seeds are
    #: not counted. Unbounded, every reply scans longer and older entries dilute.
    promote_max_examples: int = _env(
        lambda env: env_int("PROMOTE_MAX_EXAMPLES", 500, minimum=0, env=env))
    promote_max_feedback: int = _env(
        lambda env: env_int("PROMOTE_MAX_FEEDBACK", 500, minimum=0, env=env))
    #: When evidence may grant a candidate authority.
    promotion_policy: promotion.Policy = _env(promotion.Policy.from_env)

    def __post_init__(self) -> None:
        self.base_url = self.base_url.rstrip("/")
        self.llm_fallback_base_url = self.llm_fallback_base_url.rstrip("/")
        self.qq_onebot_url = self.qq_onebot_url.rstrip("/")
        self.vision_base_url = self.vision_base_url.rstrip("/")
        self.qq_bot_id = str(self.qq_bot_id)
        self.vision_model = self.vision_model.strip()
        self.tavily_key = self.tavily_key.strip()
        self.embedding_model = self.embedding_model.strip()
        self.embedding_base_url = self.embedding_base_url.strip().rstrip("/")
        self.embedding_api_key = self.embedding_api_key.strip()
        self.message_debounce_sec = max(0.0, self.message_debounce_sec)
        if not self.agent_lang:
            self.agent_lang = self.lang or env_str("AGENT_LANG", "")
        self.agent_lang = normalize_lang(self.agent_lang)
        if self.evolve_interval_hours < MIN_EVOLVE_INTERVAL_HOURS:
            logger.warning(
                "EVOLVE_INTERVAL_HOURS=%s would run the evolve loop back to "
                "back; using %s", self.evolve_interval_hours,
                MIN_EVOLVE_INTERVAL_HOURS)
            self.evolve_interval_hours = MIN_EVOLVE_INTERVAL_HOURS
        # Empty-model fallbacks, in dependency order: a blank model name 400s.
        self.llm_fallback_model = self.llm_fallback_model or self.model
        self.llm_judge_model = (
            self.llm_judge_model or self.llm_fallback_model or self.model)
        self.llm_dm_model = self.llm_dm_model or self.model
        self.eval_model = self.eval_model or self.llm_fallback_model or self.model
        self.evolve_model = self.evolve_model or self.eval_model
        self.react_model = self.react_model or self.llm_judge_model
        # Canonical ids: "qq:1" and a native "aiocqhttp:1" both read as "1".
        natives = self.connector_qq_platforms = access.split_ids(
            self.connector_qq_platforms)
        for name in ("admin_ids", "access_groups", "access_dm_users"):
            setattr(self, name, access.canonical_ids(
                getattr(self, name), native_platforms=natives))
        self.proactive_platforms = tuple(dict.fromkeys(
            channels.NATIVE_PLATFORM if name in natives else name
            for name in (p.lower() for p in access.split_ids(
                self.proactive_platforms))))

    @property
    def admins(self) -> frozenset[str]:
        """Every admin account, canonical."""
        return access.parse_ids(
            self.admin_ids, native_platforms=self.connector_qq_platforms)

    @property
    def dm_users(self) -> frozenset[str]:
        """Everyone besides the admins who may DM the bot."""
        return access.parse_ids(
            self.access_dm_users,
            native_platforms=self.connector_qq_platforms)

    @property
    def evolve_interval(self) -> int:
        """``EVOLVE_INTERVAL_HOURS`` as the seconds the loop actually sleeps."""
        return int(self.evolve_interval_hours * 3600)

    @classmethod
    def from_env(cls, env=None, **overrides) -> "AgentSettings":
        """The bot process's configuration, deployment settings included.

        An out-of-range value falls back to the default and warns."""
        def _str(name: str, default: str = "", *, strip: bool = False) -> str:
            return env_str(name, default, strip=strip, env=env)

        vision_key, vision_base = vision_endpoint_from_env(env)
        identity = access.identity_from_env(env)
        defaults = dict(
            api_key=_str("LLM_API_KEY"),
            base_url=_str("LLM_BASE_URL", DEFAULT_LLM_BASE_URL),
            model=_str("LLM_MODEL", DEFAULT_LLM_MODEL),
            qq_bot_id=_str("QQ_BOT_ID"),
            persona_name=_str("PERSONA_NAME"),
            llm_dm_model=_str("LLM_DM_MODEL"),
            qq_onebot_url=_str("QQ_ONEBOT_URL", strip=True),
            chat_trigger_count=env_int(
                "CHAT_TRIGGER_COUNT", 30, minimum=1, maximum=10_000, env=env),
            chat_context_messages=env_int(
                "CHAT_CONTEXT_MESSAGES", 120, minimum=10, maximum=10_000, env=env),
            chat_followup_window_s=env_int(
                "CHAT_FOLLOWUP_WINDOW_S", 120, minimum=0, maximum=86_400, env=env),
            memory_file=_str("MEMORY_FILE", "memory.json"),
            memory_max_per_conversation=env_int(
                "MEMORY_MAX_PER_CONVERSATION", 50, minimum=1, maximum=10_000, env=env),
            admin_ids=identity.written["ADMIN_IDS"],
            admin_name=_str("ADMIN_NAME"),
            admin_relationship=_str("ADMIN_RELATIONSHIP"),
            llm_fallback_model=_str("LLM_FALLBACK_MODEL"),
            llm_fallback_base_url=_str("LLM_FALLBACK_BASE_URL"),
            llm_fallback_api_key=_str("LLM_FALLBACK_API_KEY"),
            llm_fallback_thinking=env_bool("LLM_FALLBACK_THINKING", False, env=env),
            llm_rate_window_s=env_int(
                "LLM_RATE_WINDOW_S", 120, minimum=1, maximum=86_400, env=env),
            llm_rate_threshold=env_int(
                "LLM_RATE_THRESHOLD", 30, minimum=1, maximum=100_000, env=env),
            llm_fallback_duration_s=env_int(
                "LLM_FALLBACK_DURATION_S", 180, minimum=1, maximum=86_400, env=env),
            llm_rate_limit_cooldown_s=env_int(
                "LLM_RATE_LIMIT_COOLDOWN_S", 20, minimum=1, maximum=86_400, env=env),
            eval_enabled=env_bool("EVAL_ENABLED", False, env=env),
            eval_model=_str("EVAL_MODEL"),
            eval_file=_str("EVAL_FILE", "eval.jsonl"),
            vision_model=_str("VISION_MODEL"),
            vision_api_key=vision_key,
            vision_base_url=vision_base,
            tavily_key=_str("TAVILY_API_KEY"),
            embedding_model=_str("EMBEDDING_MODEL"),
            embedding_base_url=_str("EMBEDDING_BASE_URL"),
            embedding_api_key=_str("EMBEDDING_API_KEY"),
            lang=normalize_lang(_str("AGENT_LANG", "en", strip=True)),
            connector_qq_platforms=identity.native_platforms,
        )
        # The operational knobs' field defaults read os.environ; apply ``env`` to them too.
        if env is not None:
            defaults.update((f.name, f.metadata["env"](env))
                            for f in fields(cls) if "env" in f.metadata)
        defaults.update(overrides)
        return cls(**defaults)
