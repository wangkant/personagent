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

from persona_agent.config_env import (DEFAULT_LLM_BASE_URL, DEFAULT_LLM_MODEL,
                                      LEGACY_VISION_BASE_URL, vision_endpoint_from_env)
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
    "VISION_MODEL": "v-model", "VISION_API_KEY": "vk", "TAVILY_API_KEY": " tav ",
    "VISION_BASE_URL": "https://vision.example/v4/", "AGENT_LANG": " ZH ",
    "GATEWAY_OWNER_IDS": "telegram:1, discord:2 ,",
    "GATEWAY_NATIVE_PLATFORMS": "aiocqhttp",
    "QQ_GROUPS": "g1,g2", "PRIVATE_ALLOWED_QQS": "p1",
    "PROACTIVE_ENABLE": "yes", "EVOLVE_INTERVAL_HOURS": "0.5",
    "REACT_TTL_SEC": "30", "EXAMPLES_MAX_AUTO": "12",
}


def test_the_vision_endpoint_reads_new_names_and_honours_the_old() -> None:
    """VISION_API_KEY / VISION_BASE_URL replace GLM_API_KEY / GLM_BASE_URL.
    A deployment on the old names must behave exactly as before, default
    included; the new names carry no vendor default."""
    new = vision_endpoint_from_env({"VISION_API_KEY": "vk",
                                    "VISION_BASE_URL": "https://v.example/v4/"})
    check("vision: the new names are read, trailing slash trimmed",
          new == ("vk", "https://v.example/v4"), repr(new))
    check("vision: the new names have no default endpoint",
          vision_endpoint_from_env({"VISION_API_KEY": "vk"}) == ("vk", ""))
    check("vision: nothing set is nothing configured",
          vision_endpoint_from_env({}) == ("", ""))
    old = vision_endpoint_from_env({"GLM_API_KEY": "gk"})
    check("vision: the old key alone still gets the old default endpoint",
          old == ("gk", LEGACY_VISION_BASE_URL), repr(old))
    check("vision: an old base URL set blank still reads blank, as before",
          vision_endpoint_from_env({"GLM_API_KEY": "gk", "GLM_BASE_URL": ""})
          == ("gk", ""))
    both = vision_endpoint_from_env({
        "VISION_API_KEY": "vk", "VISION_BASE_URL": "https://v.example/v4",
        "GLM_API_KEY": "gk", "GLM_BASE_URL": "https://g.example/v4"})
    check("vision: a set new name wins over the old one",
          both == ("vk", "https://v.example/v4"), repr(both))
    mixed = vision_endpoint_from_env({"VISION_API_KEY": "vk",
                                      "GLM_BASE_URL": "https://g.example/v4"})
    check("vision: a half-migrated .env keeps its old base URL",
          mixed == ("vk", "https://g.example/v4"), repr(mixed))
    s = AgentSettings.from_env(env={"LLM_API_KEY": "k", "GLM_API_KEY": "gk",
                                    "GLM_BASE_URL": "https://g.example/v4/"})
    check("vision: from_env still honours the old names",
          (s.vision_api_key, s.vision_base_url) == ("gk", "https://g.example/v4"),
          repr((s.vision_api_key, s.vision_base_url)))


def test_the_identity_settings_read_new_names_and_honour_the_old(
        monkeypatch) -> None:
    """OWNER_IDS, ALLOWED_GROUPS and ALLOWED_DM_USERS take "<platform>:<id>"
    entries on every platform. The QQ-only names they replace still work and
    are folded in by union, so a half-migrated .env loses nobody."""
    import dataclasses

    new = AgentSettings.from_env(env={
        "LLM_API_KEY": "k", "OWNER_IDS": "telegram:1, qq:10000,",
        "ALLOWED_GROUPS": "telegram:-100,123", "ALLOWED_DM_USERS": "slack:U1"})
    check("identity: the new names are read and canonicalised",
          (new.owner_ids, new.allowed_groups, new.allowed_dm_users)
          == (("telegram:1", "10000"), ("telegram:-100", "123"), ("slack:U1",)),
          repr((new.owner_ids, new.allowed_groups, new.allowed_dm_users)))
    check("identity: owners and DM users are the merged views",
          new.owners == {"telegram:1", "10000"} and new.dm_users == {"slack:U1"})

    old = AgentSettings.from_env(env={
        "LLM_API_KEY": "k", "OWNER_QQ": "42", "GATEWAY_OWNER_IDS": "telegram:1",
        "QQ_GROUPS": "g1,g2", "PRIVATE_ALLOWED_QQS": "p1"})
    check("identity: the old names alone mean what they always meant",
          (old.owners, old.allowed_groups, old.dm_users)
          == ({"42", "telegram:1"}, ("g1", "g2"), {"p1"}),
          repr((old.owners, old.allowed_groups, old.dm_users)))

    both = AgentSettings.from_env(env={
        "LLM_API_KEY": "k", "OWNER_IDS": "telegram:1", "OWNER_QQ": "10000",
        "GATEWAY_OWNER_IDS": "discord:2", "ALLOWED_GROUPS": "telegram:-100",
        "QQ_GROUPS": "123", "ALLOWED_DM_USERS": "telegram:42",
        "PRIVATE_ALLOWED_QQS": "888"})
    check("identity: new and old are a union, not new-wins",
          both.owners == {"telegram:1", "10000", "discord:2"}
          and set(both.allowed_groups) == {"telegram:-100", "123"}
          and both.dm_users == {"telegram:42", "888"},
          repr((both.owners, both.allowed_groups, both.dm_users)))
    blank_new = AgentSettings.from_env(env={
        "LLM_API_KEY": "k", "OWNER_IDS": "", "OWNER_QQ": "42"})
    check("identity: a blank new name keeps the old one",
          blank_new.owners == {"42"}, repr(blank_new.owners))

    native = AgentSettings.from_env(env={
        "LLM_API_KEY": "k", "GATEWAY_NATIVE_PLATFORMS": "aiocqhttp",
        "OWNER_IDS": "aiocqhttp:10000", "ALLOWED_GROUPS": "qq:123,aiocqhttp:456",
        "ALLOWED_DM_USERS": "telegram:aiocqhttp"})
    check("identity: qq: and native prefixes become the bare keys events carry",
          native.owners == {"10000"} and native.allowed_groups == ("123", "456")
          and native.dm_users == {"telegram:aiocqhttp"},
          repr((native.owners, native.allowed_groups, native.dm_users)))

    plain = AgentSettings(api_key="k", owner_qq=10000,
                          gateway_owner_ids=["telegram:1"],
                          private_allowed_qqs={"888"}, allowed_groups=("1",))
    check("identity: the old keywords still work on a plain record",
          plain.owners == {"10000", "telegram:1"} and plain.dm_users == {"888"}
          and plain.allowed_groups == ("1",), repr(plain.owners))
    check("identity: replace() removes an owner given by an old keyword",
          dataclasses.replace(plain, owner_qq="").owners == {"telegram:1"})
    check("identity: re-resolving changes nothing",
          dataclasses.replace(both) == both and dataclasses.replace(native) == native)

    monkeypatch.setenv("ALLOWED_GROUPS", "telegram:-100")
    monkeypatch.setenv("QQ_GROUPS", "123")
    monkeypatch.setenv("ALLOWED_DM_USERS", "telegram:42")
    monkeypatch.setenv("OWNER_IDS", "telegram:1")
    ambient = AgentSettings(api_key="k")
    check("identity: the admission lists are operational knobs, read in both",
          ambient.allowed_groups == ("telegram:-100", "123")
          and ambient.allowed_dm_users == ("telegram:42",),
          repr((ambient.allowed_groups, ambient.allowed_dm_users)))
    check("identity: the owners are a deployment setting, as OWNER_QQ was",
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


def test_the_outbox_settings() -> None:
    """GATEWAY_OUTBOX defaults on; PROACTIVE_PLATFORMS is a lowercase list
    where a native forwarder's name means QQ, whose keys it mints."""
    default = AgentSettings.from_env(env={"LLM_API_KEY": "k"})
    check("outbox: on by default, every platform open",
          default.gateway_outbox is True and default.proactive_platforms == ())
    s = AgentSettings.from_env(env={
        "LLM_API_KEY": "k", "GATEWAY_OUTBOX": "false",
        "PROACTIVE_PLATFORMS": " Telegram, aiocqhttp ,qq,",
        "GATEWAY_NATIVE_PLATFORMS": "aiocqhttp"})
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
