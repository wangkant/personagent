"""Tests for the one record the agent is configured from.

What matters here is not that a field round-trips — a dataclass does that on
its own — but the three promises `settings.py` makes, each of which was a real
failure mode while the configuration lived in three places:

1. `AgentSettings()` reads the environment for the OPERATIONAL knobs and
   nothing else. An embedder, a benchmark arm or a test suite that passes its
   own `model=` must not have the surrounding `.env`'s `LLM_MODEL` applied
   behind its back — the benchmark tool in particular exists to compare two
   configurations, and a leaked deployment setting would silently be in both.
2. `from_env()` reproduces exactly what `main.py` used to spell by hand,
   bounds included, down to the defaults that differ from the constructor's
   (`RATE_WINDOW`, `EVAL_ENABLE`) because `.env.example` says so.
3. The empty-model fallbacks resolve in dependency order. Each of these ships
   blank and has to end up as a name the endpoint actually serves; one of them
   resolving before its source is set means `{"model": ""}` on a live call.
"""
from __future__ import annotations

from pathlib import Path

from persona_agent.settings import AgentSettings


def check(name: str, cond: bool, detail: str = "") -> None:
    """Assert `cond`, naming the property so a failure reads as English."""
    assert cond, name + (f" - {detail}" if detail else "")


#: A deployment `.env` with every setting set to something distinctive.
FULL_ENV = {
    "LLM_API_KEY": "sk-live", "LLM_BASE_URL": "https://llm.example/v1/",
    "LLM_MODEL": "live-model", "BOT_QQ": "900", "BOT_NAME": "Live",
    "NAPCAT_API": "http://napcat:3000/", "AGENT_TRIGGER_COUNT": "7",
    "AGENT_CONTEXT_LEN": "40", "AGENT_FOLLOWUP_WINDOW": "11",
    "AGENT_MEMORY_FILE": "m.json", "AGENT_MEMORY_MAX": "9",
    "OWNER_QQ": "42", "OWNER_NAME": "O", "OWNER_RELATIONSHIP": "rel",
    "PRIVATE_MODEL": "dm-model", "FALLBACK_MODEL": "cheap-model",
    "FALLBACK_BASE_URL": "https://fb.example/v1/", "FALLBACK_API_KEY": "sk-fb",
    "FALLBACK_THINKING": "true",
    "RATE_WINDOW": "13", "RATE_THRESHOLD": "14", "FALLBACK_DURATION": "15",
    "RATE_LIMIT_COOLDOWN": "16",
    "EVAL_ENABLE": "true", "EVAL_MODEL": "eval-model", "EVAL_FILE": "e.jsonl",
    "VISION_MODEL": "v-model", "GLM_API_KEY": "glm", "TAVILY_API_KEY": " tav ",
    "GLM_BASE_URL": "https://glm.example/v4/", "AGENT_LANG": " ZH ",
    "GATEWAY_OWNER_IDS": "telegram:1, discord:2 ,",
    "GATEWAY_NATIVE_PLATFORMS": "aiocqhttp",
    "QQ_GROUPS": "g1,g2", "PRIVATE_ALLOWED_QQS": "p1",
    "PROACTIVE_ENABLE": "yes", "EVOLVE_INTERVAL_HOURS": "0.5",
    "REACT_TTL_SEC": "30", "EXAMPLES_MAX_AUTO": "12",
}


def test_plain_construction_ignores_deployment_settings() -> None:
    """The constructor's own defaults, not the `.env` around it."""
    plain = AgentSettings(api_key="k")
    check("plain: literal endpoint default",
          plain.model == "deepseek-chat" and plain.base_url.endswith("deepseek.com"),
          repr((plain.model, plain.base_url)))
    check("plain: constructor's rate window, not .env.example's",
          (plain.rate_window, plain.rate_threshold, plain.fallback_duration)
          == (60, 5, 300))
    check("plain: a 429 cools for seconds, not the failure window",
          plain.rate_limit_cooldown == 20, repr(plain.rate_limit_cooldown))
    check("plain: self-eval on by default in-process", plain.eval_enable is True)
    check("plain: no deployment identity", not plain.bot_qq and not plain.owner_qq)
    empty = AgentSettings.from_env(env={}, api_key="k")
    check("an empty environment gives the documented knob defaults",
          (empty.proactive_interval, empty.react_ttl_sec, empty.llm_timeout,
           empty.evolve_threshold) == (1500, 900.0, 120.0, 3))


def test_from_env_reads_the_deployment() -> None:
    s = AgentSettings.from_env(env=FULL_ENV)
    check("from_env: key, model, endpoint",
          (s.api_key, s.model) == ("sk-live", "live-model"))
    check("from_env: trailing slash trimmed off every base url",
          (s.base_url, s.napcat_api, s.glm_base_url, s.fallback_base_url)
          == ("https://llm.example/v1", "http://napcat:3000",
              "https://glm.example/v4", "https://fb.example/v1"), repr(s.base_url))
    check("from_env: the fallback's own key", s.fallback_api_key == "sk-fb")
    unset = AgentSettings.from_env(env={"LLM_API_KEY": "k"})
    check("from_env: an unset fallback endpoint stays blank, meaning the primary's",
          (unset.fallback_base_url, unset.fallback_api_key) == ("", ""),
          repr((unset.fallback_base_url, unset.fallback_api_key)))
    check("from_env: a fallback endpoint is sent `thinking` only when told it takes it",
          s.fallback_thinking is True and unset.fallback_thinking is False)
    check("from_env: bounded integers", (s.trigger_count, s.context_len,
          s.followup_window, s.memory_max_per_group) == (7, 40, 11, 9))
    check("from_env: the two cooldowns are read separately",
          (s.fallback_duration, s.rate_limit_cooldown) == (15, 16),
          repr((s.fallback_duration, s.rate_limit_cooldown)))
    check("from_env: .env.example's defaults are the ones that apply",
          AgentSettings.from_env(env={}).rate_window == 120
          and AgentSettings.from_env(env={}).eval_enable is False)
    check("from_env: language normalised", s.agent_lang == "zh", s.agent_lang)
    check("from_env: id lists split, trimmed, emptied entries dropped",
          s.gateway_owner_ids == ("telegram:1", "discord:2")
          and s.allowed_groups == ("g1", "g2")
          and s.private_allowed_qqs == ("p1",))
    check("from_env: an explicit env reaches the operational knobs too",
          s.proactive_enable is True and s.react_ttl_sec == 30.0
          and s.examples_max_auto == 12, repr(s.proactive_enable))
    check("from_env: EVOLVE_INTERVAL_HOURS is seconds where it is used",
          s.evolve_interval == 1800, repr(s.evolve_interval))
    check("from_env: overrides beat the environment",
          AgentSettings.from_env(env=FULL_ENV, bot_name="Override").bot_name
          == "Override")


def test_an_out_of_range_setting_falls_back_rather_than_raising() -> None:
    """A typo in one setting has to behave like a typo in any other: the
    documented default, and the process still starts."""
    s = AgentSettings.from_env(env={
        "LLM_API_KEY": "k", "PORT": "nope", "AGENT_CONTEXT_LEN": "1",
        "AGENT_TRIGGER_COUNT": "0", "REACT_TTL_SEC": "15m",
        "PROACTIVE_PROB": "2", "LLM_TIMEOUT": "0", "RATE_LIMIT_COOLDOWN": "0",
    })
    check("bad values: bounded ints fall back",
          (s.context_len, s.trigger_count) == (120, 30))
    check("bad values: unparseable float falls back", s.react_ttl_sec == 900.0)
    check("bad values: out-of-range probability falls back",
          s.proactive_prob == 0.25)
    check("bad values: out-of-range timeout falls back", s.llm_timeout == 120.0)
    check("bad values: out-of-range 429 cooldown falls back",
          s.rate_limit_cooldown == 20, repr(s.rate_limit_cooldown))


def test_the_empty_model_fallbacks_resolve_in_order() -> None:
    bare = AgentSettings(api_key="k", model="main")
    check("blank fallback model becomes the main model",
          bare.fallback_model == "main")
    check("blank private model becomes the main model",
          bare.private_model == "main")
    check("judge model follows the cheap model",
          AgentSettings(api_key="k", model="main",
                        fallback_model="cheap").judge_model == "cheap")
    chain = AgentSettings(api_key="k", model="main", fallback_model="cheap",
                          judge_model="judge")
    check("eval model follows the cheap model, not the judge",
          chain.eval_model == "cheap")
    check("evolve model follows the eval model", chain.evolve_model == "cheap")
    check("react model follows the judge model", chain.react_model == "judge")
    check("an explicit eval model wins",
          AgentSettings(api_key="k", model="main",
                        eval_model="scorer").eval_model == "scorer")


def test_post_init_is_idempotent() -> None:
    """`dataclasses.replace` re-runs it, and so does anything that rebuilds a
    record from another one's fields. Resolving twice must change nothing."""
    import dataclasses

    s = AgentSettings.from_env(env=FULL_ENV)
    again = dataclasses.replace(s)
    differing = [f.name for f in dataclasses.fields(s)
                 if getattr(s, f.name) != getattr(again, f.name)]
    check("re-resolving a resolved record changes nothing",
          not differing, repr(differing))


def test_the_agent_accepts_the_record_and_its_fields() -> None:
    """Both doors, and no ambiguous third one."""
    import tempfile
    import os

    from persona_agent.agent import Agent

    previous_home = os.environ.get("AGENT_HOME")
    with tempfile.TemporaryDirectory() as d:
        os.environ["AGENT_HOME"] = d
        paths = dict(memory_file=str(Path(d) / "memory.json"),
                     stickers_dir=str(Path(d) / "stickers"),
                     stickers_file=str(Path(d) / "stickers.json"),
                     eval_file=str(Path(d) / "eval.jsonl"))
        settings = AgentSettings(api_key="k", bot_qq="1", bot_name="B",
                                 model="m", lang="en", **paths)
        from_record = Agent(settings)
        from_kwargs = Agent(api_key="k", bot_qq="1", bot_name="B", model="m",
                            lang="en", **paths)
        check("a record and its keywords build the same agent",
              from_record.settings == from_kwargs.settings)
        check("the record is kept whole on the agent",
              from_record.settings is settings)
        try:
            Agent(settings, bot_name="other")
            both = False
        except TypeError:
            both = True
        check("a record AND keywords is refused rather than half-applied", both)
        try:
            Agent("sk-not-a-record")
            wrong = False
        except TypeError:
            wrong = True
        check("a stray positional is refused", wrong)
    if previous_home is None:
        os.environ.pop("AGENT_HOME", None)
    else:
        os.environ["AGENT_HOME"] = previous_home


def test_settings_named_in_log_messages_exist() -> None:
    """A log line that tells the operator to change a setting must name one
    that exists. The empty-reply warning used to say "raise LLM_MAX_TOKENS",
    which no code reads and which preflight reports as an ERROR once added."""
    import ast
    import re

    root = Path(__file__).resolve().parent.parent
    env_example = (root / ".env.example").read_text(encoding="utf-8")
    known = set(re.findall(r"^#?\s*([A-Z][A-Z0-9_]*)=", env_example, re.MULTILINE))
    name = re.compile(r"\b[A-Z][A-Z0-9]*_[A-Z0-9_]*[A-Z0-9]\b")
    unknown = []
    for path in sorted((root / "persona_agent").glob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if not (isinstance(node, ast.Call) and node.args
                    and isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "logger"):
                continue
            for part in ast.walk(node.args[0]):
                if isinstance(part, ast.Constant) and isinstance(part.value, str):
                    unknown += [f"{path.name}:{node.lineno} {setting}"
                                for setting in name.findall(part.value)
                                if setting not in known]
    check("log messages name only real settings", not unknown, repr(unknown))
