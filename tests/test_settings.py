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
   (`LLM_RATE_WINDOW_S`, `EVAL_ENABLED`) because `.env.example` says so.
3. The empty-model fallbacks resolve in dependency order. Each of these ships
   blank and has to end up as a name the endpoint actually serves; one of them
   resolving before its source is set means `{"model": ""}` on a live call.
"""
from __future__ import annotations

from pathlib import Path

from persona_agent.config_env import (DEFAULT_LLM_BASE_URL, DEFAULT_LLM_MODEL,
                                      vision_endpoint_from_env)
from persona_agent.settings import AgentSettings


def check(name: str, cond: bool, detail: str = "") -> None:
    """Assert `cond`, naming the property so a failure reads as English."""
    assert cond, name + (f" - {detail}" if detail else "")


#: A deployment `.env` with every setting set to something distinctive.
FULL_ENV = {
    "LLM_API_KEY": "sk-live", "LLM_BASE_URL": "https://llm.example/v1/",
    "LLM_MODEL": "live-model", "QQ_BOT_ID": "900", "PERSONA_NAME": "Live",
    "QQ_ONEBOT_URL": "http://napcat:3000/", "CHAT_TRIGGER_COUNT": "7",
    "CHAT_CONTEXT_MESSAGES": "40", "CHAT_FOLLOWUP_WINDOW_S": "11",
    "MEMORY_FILE": "m.json", "MEMORY_MAX_PER_CONVERSATION": "9",
    "ADMIN_IDS": "42", "ADMIN_NAME": "O", "ADMIN_RELATIONSHIP": "rel",
    "LLM_DM_MODEL": "dm-model", "LLM_FALLBACK_MODEL": "cheap-model",
    "LLM_FALLBACK_BASE_URL": "https://fb.example/v1/", "LLM_FALLBACK_API_KEY": "sk-fb",
    "LLM_FALLBACK_THINKING": "true",
    "LLM_RATE_WINDOW_S": "13", "LLM_RATE_THRESHOLD": "14", "LLM_FALLBACK_DURATION_S": "15",
    "LLM_RATE_LIMIT_COOLDOWN_S": "16",
    "EVAL_ENABLED": "true", "EVAL_MODEL": "eval-model", "EVAL_FILE": "e.jsonl",
    "VISION_MODEL": "v-model", "VISION_API_KEY": "vk", "TAVILY_API_KEY": " tav ",
    "VISION_BASE_URL": "https://vision.example/v4/", "AGENT_LANG": " ZH ",
    "CONNECTOR_QQ_PLATFORMS": "aiocqhttp",
    "ACCESS_GROUPS": "g1, g2 ,", "ACCESS_DM_USERS": "p1",
    "PROACTIVE_ENABLED": "yes", "EVOLVE_INTERVAL_HOURS": "0.5",
    "REACT_TTL_S": "30", "PROMOTE_MAX_EXAMPLES": "12",
}


def test_the_vision_endpoint_reads_its_names() -> None:
    """VISION_API_KEY / VISION_BASE_URL carry no vendor default: the model
    VISION_MODEL names decides the provider."""
    new = vision_endpoint_from_env({"VISION_API_KEY": "vk",
                                    "VISION_BASE_URL": "https://v.example/v4/"})
    check("vision: the names are read, trailing slash trimmed",
          new == ("vk", "https://v.example/v4"), repr(new))
    check("vision: no default endpoint",
          vision_endpoint_from_env({"VISION_API_KEY": "vk"}) == ("vk", ""))
    check("vision: nothing set is nothing configured",
          vision_endpoint_from_env({}) == ("", ""))
    s = AgentSettings.from_env(env={"LLM_API_KEY": "k", "VISION_API_KEY": "vk",
                                    "VISION_BASE_URL": "https://v.example/v4/"})
    check("vision: from_env reads them",
          (s.vision_api_key, s.vision_base_url) == ("vk", "https://v.example/v4"),
          repr((s.vision_api_key, s.vision_base_url)))


def test_the_identity_settings_are_read_per_platform(monkeypatch) -> None:
    """ADMIN_IDS, ACCESS_GROUPS and ACCESS_DM_USERS take "<platform>:<id>"
    entries on every platform."""
    import dataclasses

    new = AgentSettings.from_env(env={
        "LLM_API_KEY": "k", "ADMIN_IDS": "telegram:1, qq:10000,",
        "ACCESS_GROUPS": "telegram:-100,123", "ACCESS_DM_USERS": "slack:U1"})
    check("identity: the names are read and canonicalised",
          (new.admin_ids, new.allowed_groups, new.allowed_dm_users)
          == (("telegram:1", "10000"), ("telegram:-100", "123"), ("slack:U1",)),
          repr((new.admin_ids, new.allowed_groups, new.allowed_dm_users)))
    check("identity: owners and DM users are the canonical sets",
          new.owners == {"telegram:1", "10000"} and new.dm_users == {"slack:U1"})

    native = AgentSettings.from_env(env={
        "LLM_API_KEY": "k", "CONNECTOR_QQ_PLATFORMS": "aiocqhttp",
        "ADMIN_IDS": "aiocqhttp:10000", "ACCESS_GROUPS": "qq:123,aiocqhttp:456",
        "ACCESS_DM_USERS": "telegram:aiocqhttp"})
    check("identity: qq: and native prefixes become the bare keys events carry",
          native.owners == {"10000"} and native.allowed_groups == ("123", "456")
          and native.dm_users == {"telegram:aiocqhttp"},
          repr((native.owners, native.allowed_groups, native.dm_users)))
    check("identity: re-resolving changes nothing",
          dataclasses.replace(new) == new and dataclasses.replace(native) == native)

    monkeypatch.setenv("ACCESS_GROUPS", "telegram:-100,123")
    monkeypatch.setenv("ACCESS_DM_USERS", "telegram:42")
    monkeypatch.setenv("ADMIN_IDS", "telegram:1")
    ambient = AgentSettings(api_key="k")
    check("identity: the admission lists are operational knobs, read in both",
          ambient.allowed_groups == ("telegram:-100", "123")
          and ambient.allowed_dm_users == ("telegram:42",),
          repr((ambient.allowed_groups, ambient.allowed_dm_users)))
    check("identity: the owners are a deployment setting",
          not ambient.owners, repr(ambient.owners))


def test_plain_construction_ignores_deployment_settings() -> None:
    """The constructor's own defaults, not the `.env` around it."""
    plain = AgentSettings(api_key="k")
    check("plain: literal endpoint default",
          plain.model == DEFAULT_LLM_MODEL and plain.base_url == DEFAULT_LLM_BASE_URL,
          repr((plain.model, plain.base_url)))
    check("plain: constructor's rate window, not .env.example's",
          (plain.rate_window, plain.rate_threshold, plain.fallback_duration)
          == (60, 5, 300))
    check("plain: a 429 cools for seconds, not the failure window",
          plain.rate_limit_cooldown == 20, repr(plain.rate_limit_cooldown))
    check("plain: self-eval on by default in-process", plain.eval_enable is True)
    check("plain: no deployment identity", not plain.bot_qq and not plain.admin_ids)
    empty = AgentSettings.from_env(env={}, api_key="k")
    check("an empty environment gives the documented knob defaults",
          (empty.proactive_interval, empty.react_ttl_sec, empty.llm_timeout,
           empty.evolve_threshold) == (1500, 900.0, 120.0, 3))


def test_from_env_reads_the_deployment() -> None:
    s = AgentSettings.from_env(env=FULL_ENV)
    check("from_env: key, model, endpoint",
          (s.api_key, s.model) == ("sk-live", "live-model"))
    check("from_env: trailing slash trimmed off every base url",
          (s.base_url, s.napcat_api, s.vision_base_url, s.fallback_base_url)
          == ("https://llm.example/v1", "http://napcat:3000",
              "https://vision.example/v4", "https://fb.example/v1"), repr(s.base_url))
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
          s.admin_ids == ("42",) and s.allowed_groups == ("g1", "g2")
          and s.allowed_dm_users == ("p1",))
    check("from_env: the admin's name and relationship",
          (s.owner_name, s.owner_relationship) == ("O", "rel"))
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
        "LLM_API_KEY": "k", "SERVER_PORT": "nope", "CHAT_CONTEXT_MESSAGES": "1",
        "CHAT_TRIGGER_COUNT": "0", "REACT_TTL_S": "15m",
        "PROACTIVE_PROB": "2", "LLM_TIMEOUT_S": "0", "LLM_RATE_LIMIT_COOLDOWN_S": "0",
    })
    check("bad values: bounded ints fall back",
          (s.context_len, s.trigger_count) == (120, 30))
    check("bad values: unparseable float falls back", s.react_ttl_sec == 900.0)
    check("bad values: out-of-range probability falls back",
          s.proactive_prob == 0.25)
    check("bad values: out-of-range timeout falls back", s.llm_timeout == 120.0)
    check("bad values: out-of-range 429 cooldown falls back",
          s.rate_limit_cooldown == 20, repr(s.rate_limit_cooldown))


def test_the_outbox_settings() -> None:
    """CONNECTOR_OUTBOX_ENABLED defaults on; PROACTIVE_PLATFORMS is a lowercase list
    where a native forwarder's name means QQ, whose keys it mints."""
    default = AgentSettings.from_env(env={"LLM_API_KEY": "k"})
    check("outbox: on by default, every platform open",
          default.gateway_outbox is True and default.proactive_platforms == ())
    s = AgentSettings.from_env(env={
        "LLM_API_KEY": "k", "CONNECTOR_OUTBOX_ENABLED": "false",
        "PROACTIVE_PLATFORMS": " Telegram, aiocqhttp ,qq,",
        "CONNECTOR_QQ_PLATFORMS": "aiocqhttp"})
    check("outbox: false turns it off", s.gateway_outbox is False)
    check("proactive platforms: trimmed, lowercased, native read as qq",
          s.proactive_platforms == ("telegram", "qq"), repr(s.proactive_platforms))


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
