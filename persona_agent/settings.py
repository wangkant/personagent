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
  (``LLM_API_KEY``, ``BOT_QQ``, ``OWNER_QQ``, …) out of the environment. This
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

from . import promotion
from .config_env import env_bool, env_csv, env_float, env_int, env_str
from .preflight import private_model_from_env


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
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-chat"
    #: Alternate model name for private chats, served by the same
    #: OpenAI-compatible primary endpoint — not a second provider, unless it
    #: is also ``fallback_model``'s name, which is served on the fallback's
    #: endpoint (``endpoints.endpoint_for`` routes by name). A blank
    #: ``PRIVATE_MODEL`` in ``.env`` would otherwise send ``{"model": ""}`` on
    #: every DM: a guaranteed 400 per DM. Resolved to ``model`` when empty.
    private_model: str = ""
    fallback_model: str = ""
    #: The fallback model's own endpoint, so the primary provider's outage is
    #: not also the fallback's. Blank = the primary's ``base_url`` /
    #: ``api_key``, read at call time. Only a ``fallback_model`` distinct from
    #: ``model`` is sent there (see ``endpoints.endpoint_for``).
    fallback_base_url: str = ""
    fallback_api_key: str = ""
    #: Whether a ``fallback_base_url`` on another host than ``base_url``
    #: accepts DeepSeek's ``thinking`` field. Off by default because the
    #: field is not ignored elsewhere — Groq answers ``400 property
    #: 'thinking' is unsupported``, OpenAI rejects unknown arguments — and the
    #: gate, search decision and sticker tagger run on the judge model, which
    #: defaults to the fallback, so a 400 there silences them on every turn.
    fallback_thinking: bool = False
    #: The "judgment" model: cheapest available, used only to gate
    #: self-initiated modes (judge / followup / proactive) — decide PASS vs
    #: reply. The reply that actually gets sent is always written by the main
    #: model. Defaults to the fallback (cheap) model; set ``JUDGE_MODEL`` to
    #: point at an even cheaper one.
    judge_model: str = field(
        default_factory=lambda: env_str("JUDGE_MODEL", "", strip=True))
    #: LLM transient-error retry count (jittered backoff; 0 disables).
    api_max_retries: int = field(
        default_factory=lambda: env_int("LLM_MAX_RETRIES", 2, minimum=0))
    #: Main LLM call timeout (seconds); reasoning models can be slow.
    llm_timeout: float = field(
        default_factory=lambda: env_float("LLM_TIMEOUT", 120.0, minimum=1.0))

    # ---- identity ---------------------------------------------------------
    bot_qq: str = ""
    bot_name: str = ""
    napcat_api: str = "http://127.0.0.1:3000"
    owner_qq: str = ""
    owner_name: str = ""
    owner_relationship: str = ""
    #: Process-wide language. 'en' (default) is the primary build; 'zh' selects
    #: the Chinese variant. Blank means "whatever ``AGENT_LANG`` says".
    lang: str = ""
    #: The resolved language, which everything language-dependent reads:
    #: the reply validator, the per-language data files, the control-flow
    #: lexicons. Derived from ``lang``/``AGENT_LANG`` unless set outright.
    agent_lang: str = ""

    # ---- conversation -----------------------------------------------------
    trigger_count: int = 30
    context_len: int = 120
    followup_window: int = 120
    memory_file: str = "memory.json"
    memory_max_per_group: int = 50
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
    #: Group listen whitelist (``QQ_GROUPS``); empty = listen everywhere.
    #: Without an in-code gate a bot invited into N groups replies in all of
    #: them regardless of the setting.
    allowed_groups: tuple[str, ...] = field(
        default_factory=lambda: env_csv("QQ_GROUPS"))
    #: Private-chat whitelist. ``owner_qq`` is always allowed; these are the
    #: additional QQs that may DM the bot, and they take the "ordinary friend"
    #: branch rather than the closer owner override.
    private_allowed_qqs: tuple[str, ...] = field(
        default_factory=lambda: env_csv("PRIVATE_ALLOWED_QQS"))
    #: Gateway DM owners: platform-prefixed ids (e.g. ``telegram:12345``) that
    #: get the owner branch. The gateway path itself is open — the forwarding
    #: plugin's config is the access filter — so this only selects the persona.
    gateway_owner_ids: tuple[str, ...] = ()
    #: Forwarder platforms whose ids are minted BARE instead of namespaced, so
    #: a QQ message relayed by a gateway lands on the same keys NapCat would
    #: have produced. Empty by default, and an operator setting rather than
    #: something the forwarder asserts: a bare id carries QQ authority — it is
    #: what ``owner_qq``, ``allowed_groups`` and ``private_allowed_qqs`` are
    #: compared against.
    gateway_native_platforms: tuple[str, ...] = ()

    # ---- self-evaluation --------------------------------------------------
    eval_enable: bool = True
    eval_model: str = ""
    eval_file: str = "eval.jsonl"

    # ---- vision, search, stickers -----------------------------------------
    vision_model: str = ""
    glm_api_key: str = ""
    glm_base_url: str = "https://open.bigmodel.cn/api/paas/v4"
    tavily_key: str = ""
    stickers_dir: str = "stickers"
    stickers_file: str = "stickers.json"

    # ---- model-error fallback ---------------------------------------------
    #: Two independent fallback clocks share these numbers: the error-driven
    #: one, kept per model (a failed model is skipped in every mode, for
    #: ``fallback_duration``, or ``rate_limit_cooldown`` after a 429) and the
    #: frequency-driven self-throttle (self-initiated modes only; called/owner
    #: are exempt).
    rate_window: int = 60
    rate_threshold: int = 5
    fallback_duration: int = 300
    #: How long a model that answered 429 is skipped. Its own clock because a
    #: throttled model is metered, not broken: one 429 under the 300s window
    #: routed every turn for five minutes to the fallback, though the primary
    #: answered most calls. The call that hit the 429 has already failed over;
    #: this only has to keep the next few turns off the same wall.
    rate_limit_cooldown: int = 20

    # ---- the proactive loop -----------------------------------------------
    #: A background loop that occasionally self-initiates a message (no
    #: incoming trigger) so the bot reads more like a real person who sometimes
    #: breaks the silence — not a 24/7 responder. Off by default. Heavily
    #: gated: only chats it has already seen activity in, only outside sleep
    #: hours, only after a quiet stretch, with per-target cooldowns and a low
    #: per-tick probability, and the model is told to PASS unless it genuinely
    #: has something to say. DMs go to the owner + the private whitelist only.
    proactive_enable: bool = field(
        default_factory=lambda: env_bool("PROACTIVE_ENABLE", False))
    proactive_interval: int = field(  # tick: 25 min
        default_factory=lambda: env_int("PROACTIVE_INTERVAL", 1500, minimum=1))
    proactive_min_silence: int = field(  # group quiet >= 45 min
        default_factory=lambda: env_int("PROACTIVE_MIN_SILENCE", 2700, minimum=0))
    proactive_cooldown: int = field(  # >= 3h between group initiations
        default_factory=lambda: env_int("PROACTIVE_COOLDOWN", 10800, minimum=0))
    proactive_prob: float = field(  # per eligible tick
        default_factory=lambda: env_float(
            "PROACTIVE_PROB", 0.25, minimum=0.0, maximum=1.0))
    proactive_dm_min_silence: int = field(  # DM quiet >= 4h
        default_factory=lambda: env_int(
            "PROACTIVE_DM_MIN_SILENCE", 14400, minimum=0))
    proactive_dm_cooldown: int = field(  # >= 24h between DMs
        default_factory=lambda: env_int(
            "PROACTIVE_DM_COOLDOWN", 86400, minimum=0))
    proactive_dm_prob: float = field(
        default_factory=lambda: env_float(
            "PROACTIVE_DM_PROB", 0.2, minimum=0.0, maximum=1.0))

    # ---- the self-evolution loop ------------------------------------------
    #: Opt-in background task that closes the negative half of the learning
    #: loop unattended. Low-score eval entries become BAD/OK candidates, but
    #: never enter retrieval without compatible corroborating evidence or an
    #: explicit human promotion.
    evolve_auto: bool = field(
        default_factory=lambda: env_bool("EVOLVE_AUTO", False))
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
    react_learn: bool = field(
        default_factory=lambda: env_bool("REACT_LEARN", True))
    react_model: str = field(
        default_factory=lambda: env_str("REACT_MODEL", "", strip=True))
    react_max_pending: int = field(
        default_factory=lambda: env_int("REACT_MAX_PENDING", 4, minimum=1))
    react_ttl_sec: float = field(
        default_factory=lambda: env_float("REACT_TTL_SEC", 900.0, minimum=0.0))
    react_fix_window: float = field(
        default_factory=lambda: env_float("REACT_FIX_WINDOW", 600.0, minimum=0.0))
    #: Elicitation: after an accepted rejection with no correction content, the
    #: bot may ask what the user actually meant — delayed, so it never talks
    #: over its own normal reply, and cooldown-limited, so it never begs.
    react_elicit: bool = field(
        default_factory=lambda: env_bool("REACT_ELICIT", True))
    react_elicit_delay: float = field(
        default_factory=lambda: env_float(
            "REACT_ELICIT_DELAY", 120.0, minimum=0.0))
    react_elicit_cooldown: float = field(
        default_factory=lambda: env_float(
            "REACT_ELICIT_COOLDOWN", 3600.0, minimum=0.0))

    # ---- retrieval --------------------------------------------------------
    #: Retrieval pool caps. Both pools are scanned on every LLM turn but only
    #: ever surface 4 examples + 6 pairs, so an unbounded pool costs a longer
    #: scan per reply and dilutes retrieval with entries written under an older
    #: prompt. These bound the materialized views of promoted candidates — the
    #: only rows the automatic path can add. The ``data/`` seeds and the
    #: pre-ledger learned pools are left exactly as they are. 0 = no cap.
    examples_max_auto: int = field(
        default_factory=lambda: env_int("EXAMPLES_MAX_AUTO", 500, minimum=0))
    feedback_max_auto: int = field(
        default_factory=lambda: env_int("FEEDBACK_MAX_AUTO", 500, minimum=0))
    #: When evidence may grant a candidate authority. Its own record, read the
    #: same way this one is.
    promotion_policy: promotion.Policy = field(
        default_factory=promotion.Policy.from_env)

    def __post_init__(self) -> None:
        self.base_url = str(self.base_url or "").rstrip("/")
        self.fallback_base_url = str(self.fallback_base_url or "").rstrip("/")
        self.napcat_api = str(self.napcat_api or "").rstrip("/")
        self.glm_base_url = (
            str(self.glm_base_url).rstrip("/") if self.glm_base_url else "")
        self.bot_qq = str(self.bot_qq)
        self.owner_qq = str(self.owner_qq) if self.owner_qq else ""
        self.vision_model = (self.vision_model or "").strip()
        self.tavily_key = (self.tavily_key or "").strip()
        self.message_debounce_sec = max(0.0, self.message_debounce_sec)
        if not self.agent_lang:
            self.agent_lang = self.lang or env_str("AGENT_LANG", "")
        self.agent_lang = (self.agent_lang or "en").strip().lower()
        # Empty-model fallbacks, in dependency order: each of these is a model
        # name that ships blank and has to resolve to something the endpoint
        # actually serves, or the call it gates 400s.
        self.fallback_model = self.fallback_model or self.model
        self.judge_model = (
            self.judge_model or self.fallback_model or self.model)
        self.private_model = self.private_model or self.model
        self.eval_model = self.eval_model or self.fallback_model or self.model
        self.evolve_model = self.evolve_model or self.eval_model
        self.react_model = self.react_model or self.judge_model
        # Accept any iterable of ids from a caller; store the canonical form.
        self.allowed_groups = self._ids(self.allowed_groups)
        self.private_allowed_qqs = self._ids(self.private_allowed_qqs)
        self.gateway_owner_ids = self._ids(self.gateway_owner_ids)
        self.gateway_native_platforms = self._ids(self.gateway_native_platforms)

    @staticmethod
    def _ids(values) -> tuple[str, ...]:
        """One id list, as trimmed non-empty strings."""
        return tuple(
            str(value).strip() for value in (values or ()) if str(value).strip())

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

        defaults = dict(
            api_key=_str("LLM_API_KEY"),
            base_url=_str("LLM_BASE_URL", "https://api.deepseek.com"),
            model=_str("LLM_MODEL", "deepseek-chat"),
            bot_qq=_str("BOT_QQ"),
            bot_name=_str("BOT_NAME"),
            private_model=private_model_from_env(env),
            napcat_api=_str("NAPCAT_API", "http://127.0.0.1:3000"),
            trigger_count=env_int(
                "AGENT_TRIGGER_COUNT", 30, minimum=1, maximum=10_000, env=env),
            context_len=env_int(
                "AGENT_CONTEXT_LEN", 120, minimum=10, maximum=10_000, env=env),
            followup_window=env_int(
                "AGENT_FOLLOWUP_WINDOW", 120, minimum=0, maximum=86_400, env=env),
            memory_file=_str("AGENT_MEMORY_FILE", "memory.json"),
            memory_max_per_group=env_int(
                "AGENT_MEMORY_MAX", 50, minimum=1, maximum=10_000, env=env),
            owner_qq=_str("OWNER_QQ"),
            owner_name=_str("OWNER_NAME"),
            owner_relationship=_str("OWNER_RELATIONSHIP"),
            fallback_model=_str("FALLBACK_MODEL"),
            fallback_base_url=_str("FALLBACK_BASE_URL"),
            fallback_api_key=_str("FALLBACK_API_KEY"),
            fallback_thinking=env_bool("FALLBACK_THINKING", False, env=env),
            rate_window=env_int(
                "RATE_WINDOW", 120, minimum=1, maximum=86_400, env=env),
            rate_threshold=env_int(
                "RATE_THRESHOLD", 30, minimum=1, maximum=100_000, env=env),
            fallback_duration=env_int(
                "FALLBACK_DURATION", 180, minimum=1, maximum=86_400, env=env),
            rate_limit_cooldown=env_int(
                "RATE_LIMIT_COOLDOWN", 20, minimum=1, maximum=86_400, env=env),
            eval_enable=env_bool("EVAL_ENABLE", False, env=env),
            eval_model=_str("EVAL_MODEL"),
            eval_file=_str("EVAL_FILE", "eval.jsonl"),
            vision_model=_str("VISION_MODEL"),
            glm_api_key=_str("GLM_API_KEY"),
            glm_base_url=_str(
                "GLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4"),
            tavily_key=_str("TAVILY_API_KEY"),
            lang=_str("AGENT_LANG", "en", strip=True).lower(),
            gateway_owner_ids=env_csv("GATEWAY_OWNER_IDS", env=env),
            gateway_native_platforms=env_csv(
                "GATEWAY_NATIVE_PLATFORMS", env=env),
        )
        # The operational knobs are read by the field defaults, which go
        # through `os.environ` directly. An explicit `env` mapping has to reach
        # them too, or `from_env(env=...)` would be half-honoured.
        if env is not None:
            defaults.update(cls._operational_from_env(env))
        defaults.update(overrides)
        return cls(**defaults)

    @classmethod
    def _operational_from_env(cls, env) -> dict:
        """The knobs whose defaults come from the environment, read from
        ``env`` instead of ``os.environ``."""
        return dict(
            judge_model=env_str("JUDGE_MODEL", "", strip=True, env=env),
            api_max_retries=env_int("LLM_MAX_RETRIES", 2, minimum=0, env=env),
            llm_timeout=env_float("LLM_TIMEOUT", 120.0, minimum=1.0, env=env),
            persona_version=env_str("PERSONA_VERSION", "", strip=True, env=env),
            allowed_groups=env_csv("QQ_GROUPS", env=env),
            private_allowed_qqs=env_csv("PRIVATE_ALLOWED_QQS", env=env),
            proactive_enable=env_bool("PROACTIVE_ENABLE", False, env=env),
            proactive_interval=env_int(
                "PROACTIVE_INTERVAL", 1500, minimum=1, env=env),
            proactive_min_silence=env_int(
                "PROACTIVE_MIN_SILENCE", 2700, minimum=0, env=env),
            proactive_cooldown=env_int(
                "PROACTIVE_COOLDOWN", 10800, minimum=0, env=env),
            proactive_prob=env_float(
                "PROACTIVE_PROB", 0.25, minimum=0.0, maximum=1.0, env=env),
            proactive_dm_min_silence=env_int(
                "PROACTIVE_DM_MIN_SILENCE", 14400, minimum=0, env=env),
            proactive_dm_cooldown=env_int(
                "PROACTIVE_DM_COOLDOWN", 86400, minimum=0, env=env),
            proactive_dm_prob=env_float(
                "PROACTIVE_DM_PROB", 0.2, minimum=0.0, maximum=1.0, env=env),
            evolve_auto=env_bool("EVOLVE_AUTO", False, env=env),
            evolve_interval_hours=env_float(
                "EVOLVE_INTERVAL_HOURS", 6.0, minimum=0.0, env=env),
            evolve_threshold=env_int("EVOLVE_THRESHOLD", 3, env=env),
            evolve_batch=env_int("EVOLVE_BATCH", 5, minimum=1, env=env),
            evolve_model=env_str("EVOLVE_MODEL", "", strip=True, env=env),
            react_learn=env_bool("REACT_LEARN", True, env=env),
            react_model=env_str("REACT_MODEL", "", strip=True, env=env),
            react_max_pending=env_int("REACT_MAX_PENDING", 4, minimum=1, env=env),
            react_ttl_sec=env_float("REACT_TTL_SEC", 900.0, minimum=0.0, env=env),
            react_fix_window=env_float(
                "REACT_FIX_WINDOW", 600.0, minimum=0.0, env=env),
            react_elicit=env_bool("REACT_ELICIT", True, env=env),
            react_elicit_delay=env_float(
                "REACT_ELICIT_DELAY", 120.0, minimum=0.0, env=env),
            react_elicit_cooldown=env_float(
                "REACT_ELICIT_COOLDOWN", 3600.0, minimum=0.0, env=env),
            examples_max_auto=env_int(
                "EXAMPLES_MAX_AUTO", 500, minimum=0, env=env),
            feedback_max_auto=env_int(
                "FEEDBACK_MAX_AUTO", 500, minimum=0, env=env),
            promotion_policy=promotion.Policy.from_env(env),
        )
