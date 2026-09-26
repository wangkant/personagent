"""Everything the agent is configured with, as one object.

WHY THIS MODULE EXISTS. The agent's configuration used to live in three places
that had to be kept in step by hand:

* ``Agent.__init__`` took 34 keyword parameters and read a further two dozen
  settings straight out of ``os.environ`` in its own body, interleaved with the
  runtime state it was also building;
* ``main.py`` read the same deployment settings into module globals at import
  time, each through its own bounds check, then copied roughly thirty of them
  back out as keyword arguments;
* every other entry point (``try_chat.py``, the two tools, the test suites)
  spelled its own subset of those keywords again.

Adding one knob meant touching all three, and forgetting the third was silent:
the setting simply never reached the agent. So the rule here is **one record,
built once, passed in.** ``Agent`` holds no parsing logic and no defaults of
its own; it copies this object's fields onto itself.

Two ways in, and the difference between them is deliberate:

* ``AgentSettings(...)`` — literal defaults for the deployment settings, the
  environment for the operational knobs. This is what an embedder, a tool or a
  test suite wants: an agent it configured, not one the surrounding ``.env``
  configured behind its back.
* ``AgentSettings.from_env()`` — additionally reads the deployment settings
  (``LLM_API_KEY``, ``PERSONA_NAME``, ``ADMIN_IDS``, …) out of the environment. This
  is the bot process, and nothing but ``main.py`` should want it.

The operational knobs — the proactive loop, the evolution loop, reaction
learning, the retrieval caps — read the environment in BOTH, because that is
where they have always been read from and no call site has ever passed them.

Every read goes through :mod:`persona_agent.config_env`, so a typo in one
setting behaves like a typo in any other: the declared default, and a warning
that says so.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Awaitable, Callable, Optional

from . import access, channels, promotion
from .config_env import (DEFAULT_LLM_BASE_URL, DEFAULT_LLM_MODEL, env_bool,
                         env_float, env_int, env_str, vision_endpoint_from_env)


@dataclass
class AgentSettings:
    """One agent's configuration, fully resolved.

    Field order follows the constructor this replaced, so a call site that used
    to pass keywords to ``Agent`` passes the same keywords here.

    ``__post_init__`` resolves every setting that used to be resolved inside
    the constructor — the empty-model fallbacks, the URL trimming, the string
    coercions — so the object handed to ``Agent`` is what ``Agent`` will use.
    It is idempotent: re-running it (``dataclasses.replace``) changes nothing.
    """

    # ---- the LLM endpoint -------------------------------------------------
    api_key: str
    base_url: str = DEFAULT_LLM_BASE_URL
    model: str = DEFAULT_LLM_MODEL
    #: Alternate model name for private chats, served by the same
    #: OpenAI-compatible primary endpoint — not a second provider, unless it
    #: is also ``llm_fallback_model``'s name, which is served on the fallback's
    #: endpoint (``endpoints.endpoint_for`` routes by name). A blank
    #: ``LLM_DM_MODEL`` in ``.env`` would otherwise send ``{"model": ""}`` on
    #: every DM: a guaranteed 400 per DM. Resolved to ``model`` when empty.
    llm_dm_model: str = ""
    llm_fallback_model: str = ""
    #: The fallback model's own endpoint, so the primary provider's outage is
    #: not also the fallback's. Blank = the primary's ``base_url`` /
    #: ``api_key``, read at call time. Only a ``llm_fallback_model``
    #: distinct from ``model`` is sent there (see ``endpoints.endpoint_for``).
    llm_fallback_base_url: str = ""
    llm_fallback_api_key: str = ""
    #: Whether a ``llm_fallback_base_url`` on another host than ``base_url``
    #: accepts DeepSeek's ``thinking`` field. Off by default because the
    #: field is not ignored elsewhere — Groq answers ``400 property
    #: 'thinking' is unsupported``, OpenAI rejects unknown arguments — and the
    #: gate, search decision and sticker tagger run on the judge model, which
    #: defaults to the fallback, so a 400 there silences them on every turn.
    llm_fallback_thinking: bool = False
    #: The "judgment" model: cheapest available, used only to gate
    #: self-initiated modes (judge / followup / proactive) — decide PASS vs
    #: reply. The reply that actually gets sent is always written by the main
    #: model. Defaults to the fallback (cheap) model; set ``LLM_JUDGE_MODEL`` to
    #: point at an even cheaper one.
    llm_judge_model: str = field(
        default_factory=lambda: env_str("LLM_JUDGE_MODEL", "", strip=True))
    #: LLM transient-error retry count (jittered backoff; 0 disables).
    api_max_retries: int = field(
        default_factory=lambda: env_int("LLM_MAX_RETRIES", 2, minimum=0))
    #: Main LLM call timeout (seconds); reasoning models can be slow.
    llm_timeout_s: float = field(
        default_factory=lambda: env_float("LLM_TIMEOUT_S", 120.0, minimum=1.0))

    # ---- identity ---------------------------------------------------------
    qq_bot_id: str = ""
    persona_name: str = ""
    qq_onebot_url: str = "http://127.0.0.1:3000"
    admin_name: str = ""
    admin_relationship: str = ""
    #: Process-wide language. 'en' (default) is the primary build; 'zh' selects
    #: the Chinese variant. Blank means "whatever ``AGENT_LANG`` says".
    lang: str = ""
    #: The resolved language, which everything language-dependent reads:
    #: the reply validator, the per-language data files, the control-flow
    #: lexicons. Derived from ``lang``/``AGENT_LANG`` unless set outright.
    agent_lang: str = ""

    # ---- conversation -----------------------------------------------------
    chat_trigger_count: int = 30
    chat_context_messages: int = 120
    chat_followup_window_s: int = 120
    memory_file: str = "memory.json"
    memory_max_per_conversation: int = 50
    message_debounce_sec: float = 2.5
    #: Persona document. ``None`` means "load it from ``PERSONA_FILE``", which
    #: the agent does at construction — file reads stay out of this record.
    persona: Optional[str] = None
    #: Optional operator-set label recorded alongside the persona hash. Both
    #: are part of evidence-combination scope, so a persona rewrite stops old
    #: evidence from authorizing changes to the new character.
    persona_version: str = field(
        default_factory=lambda: env_str("PERSONA_VERSION", "", strip=True))
    on_reply: Optional[Callable[[str, str], Awaitable[None]]] = None

    # ---- who may talk to it -----------------------------------------------
    # Entries are "<platform>:<id>", a bare id being QQ (see access.py).
    #: The admin's accounts (``ADMIN_IDS``), one person on every platform.
    admin_ids: tuple[str, ...] = ()
    #: Groups the agent admits (``ACCESS_GROUPS``), per platform: a platform
    #: with no entries is not restricted here.
    #: Without an in-code gate a bot invited into N groups replies in all of
    #: them regardless of the setting.
    access_groups: tuple[str, ...] = field(
        default_factory=lambda: access.identity_from_env().written[
            "ACCESS_GROUPS"])
    #: Who else may DM the bot (``ACCESS_DM_USERS``). Admins always may;
    #: these take the "ordinary friend" branch rather than the admin's.
    access_dm_users: tuple[str, ...] = field(
        default_factory=lambda: access.identity_from_env().written[
            "ACCESS_DM_USERS"])
    #: Connector platforms whose ids are minted BARE instead of namespaced, so
    #: a QQ message relayed by a connector lands on the same keys NapCat would
    #: have produced. Empty by default, and an operator setting rather than
    #: something the connector asserts: a bare id carries QQ authority — it is
    #: what the QQ entries of the lists above are compared against.
    connector_qq_platforms: tuple[str, ...] = ()
    #: Whether a connector that pulls the outbox may be sent messages nobody
    #: asked for: openers, the follow-up question, the excuse for a failed
    #: model call (``CONNECTOR_OUTBOX_ENABLED``). Off, the outbox endpoint answers 404
    #: and those stay QQ-only, as they were before the outbox existed.
    connector_outbox_enabled: bool = field(
        default_factory=lambda: env_bool("CONNECTOR_OUTBOX_ENABLED", True))

    # ---- self-evaluation --------------------------------------------------
    eval_enabled: bool = True
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
    #: Two independent fallback clocks share these numbers: the error-driven
    #: one, kept per model (a failed model is skipped in every mode, for
    #: ``llm_fallback_duration_s``, or ``llm_rate_limit_cooldown_s`` after a
    #: 429) and the frequency-driven self-throttle (self-initiated modes only;
    #: called/admin are exempt).
    llm_rate_window_s: int = 60
    llm_rate_threshold: int = 5
    llm_fallback_duration_s: int = 300
    #: How long a model that answered 429 is skipped. Its own clock because a
    #: throttled model is metered, not broken: one 429 under the 300s window
    #: routed every turn for five minutes to the fallback, though the primary
    #: answered most calls. The call that hit the 429 has already failed over;
    #: this only has to keep the next few turns off the same wall.
    llm_rate_limit_cooldown_s: int = 20

    # ---- the proactive loop -----------------------------------------------
    #: A background loop that occasionally self-initiates a message (no
    #: incoming trigger) so the bot reads more like a real person who sometimes
    #: breaks the silence — not a 24/7 responder. Off by default. Heavily
    #: gated: only chats it has already seen activity in, only outside sleep
    #: hours, only after a quiet stretch, with per-target cooldowns and a low
    #: per-tick probability, and the model is told to PASS unless it genuinely
    #: has something to say. DMs go to the admin + the private whitelist only.
    proactive_enabled: bool = field(
        default_factory=lambda: env_bool("PROACTIVE_ENABLED", False))
    proactive_interval_s: int = field(  # tick: 25 min
        default_factory=lambda: env_int("PROACTIVE_INTERVAL_S", 1500, minimum=1))
    proactive_min_silence_s: int = field(  # group quiet >= 45 min
        default_factory=lambda: env_int("PROACTIVE_MIN_SILENCE_S", 2700, minimum=0))
    proactive_cooldown_s: int = field(  # >= 3h between group initiations
        default_factory=lambda: env_int("PROACTIVE_COOLDOWN_S", 10800, minimum=0))
    proactive_prob: float = field(  # per eligible tick
        default_factory=lambda: env_float(
            "PROACTIVE_PROB", 0.25, minimum=0.0, maximum=1.0))
    proactive_dm_min_silence_s: int = field(  # DM quiet >= 4h
        default_factory=lambda: env_int(
            "PROACTIVE_DM_MIN_SILENCE_S", 14400, minimum=0))
    proactive_dm_cooldown_s: int = field(  # >= 24h between DMs
        default_factory=lambda: env_int(
            "PROACTIVE_DM_COOLDOWN_S", 86400, minimum=0))
    proactive_dm_prob: float = field(
        default_factory=lambda: env_float(
            "PROACTIVE_DM_PROB", 0.2, minimum=0.0, maximum=1.0))
    #: Which platforms the loop may speak first on (``PROACTIVE_PLATFORMS``,
    #: e.g. "qq,telegram"); empty is every platform it can reach. A
    #: CONNECTOR_QQ_PLATFORMS name means QQ, whose keys it mints.
    proactive_platforms: tuple[str, ...] = field(
        default_factory=lambda: access.split_ids(
            env_str("PROACTIVE_PLATFORMS", "", strip=True)))

    # ---- the self-evolution loop ------------------------------------------
    #: Opt-in background task that closes the negative half of the learning
    #: loop unattended. Low-score eval entries become BAD/OK candidates, but
    #: never enter retrieval without compatible corroborating evidence or an
    #: explicit human promotion.
    evolve_auto_enabled: bool = field(
        default_factory=lambda: env_bool("EVOLVE_AUTO_ENABLED", False))
    evolve_interval_hours: float = field(
        default_factory=lambda: env_float(
            "EVOLVE_INTERVAL_HOURS", 6.0, minimum=0.0))
    #: 3, not 2: on the evaluator's register scale (learning.py), 3 means
    #: "human-plausible but drifting into helpful-assistant register" —
    #: precisely the failure mode the loop exists to correct. Validated on 8
    #: known-label replies: every known tell (drafted letter, mini tutorials)
    #: scored exactly 3, every casual line scored 5, so a threshold of 2 would
    #: leave the loop with nothing to learn from.
    evolve_threshold: int = field(
        default_factory=lambda: env_int("EVOLVE_THRESHOLD", 3))
    evolve_batch: int = field(  # diagnoses per tick
        default_factory=lambda: env_int("EVOLVE_BATCH", 5, minimum=1))
    evolve_model: str = field(
        default_factory=lambda: env_str("EVOLVE_MODEL", "", strip=True))

    # ---- reaction learning ------------------------------------------------
    #: The PRIMARY self-evolution signal. Every sent reply waits (bounded, TTL)
    #: for a directed user reaction — a quote of the bot's message, an @/name
    #: call, or the interlocutor's next DM. An in-process adjudicator (single
    #: LLM call) classifies it and filters banter and trolling. The verdict is
    #: recorded as evidence and may propose a candidate; it does not write a
    #: retrieval pool. LLM self-eval remains the fallback channel for replies
    #: that never get a directed reaction.
    react_learn_enabled: bool = field(
        default_factory=lambda: env_bool("REACT_LEARN_ENABLED", True))
    react_model: str = field(
        default_factory=lambda: env_str("REACT_MODEL", "", strip=True))
    react_max_pending: int = field(
        default_factory=lambda: env_int("REACT_MAX_PENDING", 4, minimum=1))
    react_ttl_s: float = field(
        default_factory=lambda: env_float("REACT_TTL_S", 900.0, minimum=0.0))
    react_fix_window_s: float = field(
        default_factory=lambda: env_float("REACT_FIX_WINDOW_S", 600.0, minimum=0.0))
    #: Elicitation: after an accepted rejection with no correction content, the
    #: bot may ask what the user actually meant — delayed, so it never talks
    #: over its own normal reply, and cooldown-limited, so it never begs.
    react_elicit_enabled: bool = field(
        default_factory=lambda: env_bool("REACT_ELICIT_ENABLED", True))
    react_elicit_delay_s: float = field(
        default_factory=lambda: env_float(
            "REACT_ELICIT_DELAY_S", 120.0, minimum=0.0))
    react_elicit_cooldown_s: float = field(
        default_factory=lambda: env_float(
            "REACT_ELICIT_COOLDOWN_S", 3600.0, minimum=0.0))

    # ---- retrieval --------------------------------------------------------
    #: Retrieval pool caps. Both pools are scanned on every LLM turn but only
    #: ever surface 4 examples + 6 pairs, so an unbounded pool costs a longer
    #: scan per reply and dilutes retrieval with entries written under an older
    #: prompt. These bound the materialized views of promoted candidates — the
    #: only rows the automatic path can add. The ``data/`` seeds and the
    #: pre-ledger learned pools are left exactly as they are. 0 = no cap.
    promote_max_examples: int = field(
        default_factory=lambda: env_int("PROMOTE_MAX_EXAMPLES", 500, minimum=0))
    promote_max_feedback: int = field(
        default_factory=lambda: env_int("PROMOTE_MAX_FEEDBACK", 500, minimum=0))
    #: When evidence may grant a candidate authority. Its own record, read the
    #: same way this one is.
    promotion_policy: promotion.Policy = field(
        default_factory=promotion.Policy.from_env)

    def __post_init__(self) -> None:
        self.base_url = str(self.base_url or "").rstrip("/")
        self.llm_fallback_base_url = str(self.llm_fallback_base_url or "").rstrip("/")
        self.qq_onebot_url = str(self.qq_onebot_url or "").rstrip("/")
        self.vision_base_url = (
            str(self.vision_base_url).rstrip("/") if self.vision_base_url else "")
        self.qq_bot_id = str(self.qq_bot_id)
        self.vision_model = (self.vision_model or "").strip()
        self.tavily_key = (self.tavily_key or "").strip()
        self.embedding_model = (self.embedding_model or "").strip()
        self.embedding_base_url = str(self.embedding_base_url or "").strip().rstrip("/")
        self.embedding_api_key = (self.embedding_api_key or "").strip()
        self.message_debounce_sec = max(0.0, self.message_debounce_sec)
        if not self.agent_lang:
            self.agent_lang = self.lang or env_str("AGENT_LANG", "")
        self.agent_lang = (self.agent_lang or "en").strip().lower()
        # Empty-model fallbacks, in dependency order: each of these is a model
        # name that ships blank and has to resolve to something the endpoint
        # actually serves, or the call it gates 400s.
        self.llm_fallback_model = self.llm_fallback_model or self.model
        self.llm_judge_model = (
            self.llm_judge_model or self.llm_fallback_model or self.model)
        self.llm_dm_model = self.llm_dm_model or self.model
        self.eval_model = self.eval_model or self.llm_fallback_model or self.model
        self.evolve_model = self.evolve_model or self.eval_model
        self.react_model = self.react_model or self.llm_judge_model
        # Accept any iterable of ids from a caller; store the canonical form,
        # so "qq:1" and a native connector's "aiocqhttp:1" both read as "1".
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
        """The bot process's configuration: deployment settings included.

        Every bound here was previously spelled in ``main.py``, one
        ``_parse_int_config`` call per setting. They are floors and ceilings on
        what a deployment may ask for, not the defaults — an out-of-range value
        falls back to the default and warns, like any other bad setting.

        Defaults match ``.env.example`` exactly, so behaviour is identical
        whether or not a ``.env`` is present.
        """
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
            qq_onebot_url=_str("QQ_ONEBOT_URL", "http://127.0.0.1:3000"),
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
            lang=_str("AGENT_LANG", "en", strip=True).lower(),
            connector_qq_platforms=identity.native_platforms,
        )
        # The operational knobs are read by the field defaults, which go
        # through `os.environ` directly. An explicit `env` mapping has to reach
        # them too, or `from_env(env=...)` would be half-honoured.
        if env is not None:
            defaults.update(cls._operational_from_env(env))
        defaults.update(overrides)
        return cls(**defaults)

    @staticmethod
    def _access_from_env(env) -> dict:
        """The admission lists, which are operational knobs too."""
        identity = access.identity_from_env(env)
        return dict(
            access_groups=identity.written["ACCESS_GROUPS"],
            access_dm_users=identity.written["ACCESS_DM_USERS"],
        )

    @classmethod
    def _operational_from_env(cls, env) -> dict:
        """The knobs whose defaults come from the environment, read from
        ``env`` instead of ``os.environ``."""
        return dict(
            llm_judge_model=env_str("LLM_JUDGE_MODEL", "", strip=True, env=env),
            api_max_retries=env_int("LLM_MAX_RETRIES", 2, minimum=0, env=env),
            llm_timeout_s=env_float("LLM_TIMEOUT_S", 120.0, minimum=1.0, env=env),
            persona_version=env_str("PERSONA_VERSION", "", strip=True, env=env),
            **cls._access_from_env(env),
            proactive_enabled=env_bool("PROACTIVE_ENABLED", False, env=env),
            proactive_interval_s=env_int(
                "PROACTIVE_INTERVAL_S", 1500, minimum=1, env=env),
            proactive_min_silence_s=env_int(
                "PROACTIVE_MIN_SILENCE_S", 2700, minimum=0, env=env),
            proactive_cooldown_s=env_int(
                "PROACTIVE_COOLDOWN_S", 10800, minimum=0, env=env),
            proactive_prob=env_float(
                "PROACTIVE_PROB", 0.25, minimum=0.0, maximum=1.0, env=env),
            proactive_dm_min_silence_s=env_int(
                "PROACTIVE_DM_MIN_SILENCE_S", 14400, minimum=0, env=env),
            proactive_dm_cooldown_s=env_int(
                "PROACTIVE_DM_COOLDOWN_S", 86400, minimum=0, env=env),
            proactive_dm_prob=env_float(
                "PROACTIVE_DM_PROB", 0.2, minimum=0.0, maximum=1.0, env=env),
            proactive_platforms=access.split_ids(
                env_str("PROACTIVE_PLATFORMS", "", strip=True, env=env)),
            connector_outbox_enabled=env_bool(
                "CONNECTOR_OUTBOX_ENABLED", True, env=env),
            evolve_auto_enabled=env_bool("EVOLVE_AUTO_ENABLED", False, env=env),
            evolve_interval_hours=env_float(
                "EVOLVE_INTERVAL_HOURS", 6.0, minimum=0.0, env=env),
            evolve_threshold=env_int("EVOLVE_THRESHOLD", 3, env=env),
            evolve_batch=env_int("EVOLVE_BATCH", 5, minimum=1, env=env),
            evolve_model=env_str("EVOLVE_MODEL", "", strip=True, env=env),
            react_learn_enabled=env_bool("REACT_LEARN_ENABLED", True, env=env),
            react_model=env_str("REACT_MODEL", "", strip=True, env=env),
            react_max_pending=env_int("REACT_MAX_PENDING", 4, minimum=1, env=env),
            react_ttl_s=env_float("REACT_TTL_S", 900.0, minimum=0.0, env=env),
            react_fix_window_s=env_float(
                "REACT_FIX_WINDOW_S", 600.0, minimum=0.0, env=env),
            react_elicit_enabled=env_bool("REACT_ELICIT_ENABLED", True, env=env),
            react_elicit_delay_s=env_float(
                "REACT_ELICIT_DELAY_S", 120.0, minimum=0.0, env=env),
            react_elicit_cooldown_s=env_float(
                "REACT_ELICIT_COOLDOWN_S", 3600.0, minimum=0.0, env=env),
            promote_max_examples=env_int(
                "PROMOTE_MAX_EXAMPLES", 500, minimum=0, env=env),
            promote_max_feedback=env_int(
                "PROMOTE_MAX_FEEDBACK", 500, minimum=0, env=env),
            promotion_policy=promotion.Policy.from_env(env),
        )
