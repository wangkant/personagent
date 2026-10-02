"""What an installed copy needs: one version, the shipped files, the seed resolver, the CLI."""
from __future__ import annotations

import re
import runpy
import subprocess
import sys
from pathlib import Path

import pytest

import persona_agent
from persona_agent import cli, home, paths

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "integrations" / "astrbot" / "astrbot_plugin_personagent"


def _pyproject() -> str:
    return (ROOT / "pyproject.toml").read_text(encoding="utf-8")


def test_one_version_for_the_package_the_metadata_and_the_plugin() -> None:
    declared = re.search(r'^version = "([^"]+)"', _pyproject(), re.MULTILINE).group(1)
    plugin = re.search(r"^version:\s*(\S+)",
                       (PLUGIN / "metadata.yaml").read_text(encoding="utf-8"),
                       re.MULTILINE).group(1)
    assert declared == persona_agent.__version__ == plugin, (
        declared, persona_agent.__version__, plugin)


def test_the_classifiers_match_a_stable_release() -> None:
    text = _pyproject()
    assert "Development Status :: 5 - Production/Stable" in text
    for minor in range(10, 15):
        assert f"Programming Language :: Python :: 3.{minor}" in text
    assert 'requires-python = ">=3.10"' in text


def test_requirements_txt_is_the_single_dependency_list() -> None:
    assert 'dependencies = { file = ["requirements.txt"] }' in _pyproject()
    lines = [ln.strip() for ln in (ROOT / "requirements.txt").read_text(
        encoding="utf-8").splitlines() if ln.strip()]
    # setuptools reads full-line comments only; a trailing one breaks the build.
    assert all(ln.startswith("#") or "#" not in ln for ln in lines), lines
    requirements = [ln for ln in lines if not ln.startswith("#")]
    assert any(re.fullmatch(r"pydantic>=2[.\d]*,<3", ln) for ln in requirements), requirements
    assert all(">=" in ln for ln in requirements), "every dependency has a floor"


def _bundled_by_setup(root: Path = ROOT) -> set[str]:
    hook = runpy.run_path(str(ROOT / "setup.py"), run_name="setup_under_test")
    return {rel.as_posix() for _src, rel in hook["bundled_files"](root)}


def test_the_wheel_bundles_every_tracked_shared_file() -> None:
    bundled = _bundled_by_setup()
    tracked = subprocess.run(
        ["git", "ls-files", "data", ".env.example", PLUGIN.relative_to(ROOT).as_posix()],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    if tracked.returncode != 0:
        pytest.skip("not a git checkout")
    expected = set(tracked.stdout.split())
    assert expected and expected <= bundled, sorted(expected - bundled)
    for wanted in (".env.example", "data/persona.example.en.txt",
                   "data/evals/speak.en.jsonl", "data/benchmark/scenarios.train.en.jsonl",
                   "integrations/astrbot/astrbot_plugin_personagent/main.py",
                   "integrations/astrbot/astrbot_plugin_personagent/metadata.yaml"):
        assert wanted in bundled, wanted


def test_the_wheel_leaves_bytecode_caches_out(tmp_path: Path) -> None:
    plugin = tmp_path / "integrations" / "astrbot" / "astrbot_plugin_personagent"
    (plugin / "__pycache__").mkdir(parents=True)
    (plugin / "main.py").write_text("", encoding="utf-8")
    (plugin / "__pycache__" / "main.cpython-312.pyc").write_bytes(b"x")
    (plugin / "stale.pyc").write_bytes(b"x")
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "seed.jsonl").write_text("{}\n", encoding="utf-8")
    assert _bundled_by_setup(tmp_path) == {
        "data/seed.jsonl", "integrations/astrbot/astrbot_plugin_personagent/main.py"}


def test_resource_reads_the_checkout_here_and_the_bundle_when_installed(
        monkeypatch) -> None:
    assert home.is_checkout()
    assert home.resource("data", "x") == ROOT / "data" / "x"
    monkeypatch.setattr(home, "is_checkout", lambda path=home.CHECKOUT: False)
    assert home.resource("data", "x") == home.PACKAGE_DIR / "_bundled" / "data" / "x"


def test_a_folder_is_a_home_only_with_its_own_settings(tmp_path: Path) -> None:
    (tmp_path / "data").mkdir()
    assert not home.looks_like_home(tmp_path), "a stray data/ folder is not a home"
    (tmp_path / ".env").write_text("", encoding="utf-8")
    (tmp_path / "persona.txt").write_text("", encoding="utf-8")
    assert home.looks_like_home(tmp_path)
    assert home.looks_like_home(ROOT)


def test_seeds_prefer_the_home_then_fall_back_to_the_shipped_copy(
        monkeypatch, tmp_path: Path) -> None:
    shipped = tmp_path / "shipped"
    (shipped / "data" / "evals").mkdir(parents=True)
    (shipped / "data" / "lorebook.en.json").write_text("shipped", encoding="utf-8")
    (shipped / "data" / "examples.jsonl").write_text("shipped", encoding="utf-8")
    (shipped / "data" / "evals" / "speak.en.jsonl").write_text("", encoding="utf-8")
    deployment = tmp_path / "home"
    (deployment / "data").mkdir(parents=True)
    monkeypatch.setattr(paths, "ROOT", deployment)
    monkeypatch.setattr(paths, "resource", lambda *parts: shipped.joinpath(*parts))

    assert paths.seed_file("lorebook.en.json") == shipped / "data" / "lorebook.en.json"
    assert paths.seed_file("evals") == shipped / "data" / "evals"
    assert (paths.resolve_seed_lang_file("lorebook", "json", "en")
            == shipped / "data" / "lorebook.en.json")
    assert (paths.resolve_seed_lang_file("examples", "jsonl", "zh")
            == shipped / "data" / "examples.jsonl")

    (deployment / "data" / "lorebook.json").write_text("mine", encoding="utf-8")
    assert (paths.resolve_seed_lang_file("lorebook", "json", "en")
            == deployment / "data" / "lorebook.json"), "the home's own copy wins"
    (deployment / "data" / "lorebook.en.json").write_text("mine", encoding="utf-8")
    assert paths.seed_file("lorebook.en.json") == deployment / "data" / "lorebook.en.json"
    assert (paths.resolve_seed_lang_file("missing", "json", "en")
            == deployment / "data" / "missing.json")


def test_runtime_state_stays_under_the_home(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(paths, "ROOT", tmp_path)
    monkeypatch.delenv("AGENT_RUNTIME_DIR", raising=False)
    assert paths.runtime_dir() == (tmp_path / "runtime").resolve()


def test_the_cli_prints_its_version(capsys) -> None:
    with pytest.raises(SystemExit) as stop:
        cli.main(["--version"])
    assert stop.value.code == 0
    assert capsys.readouterr().out.strip() == f"personagent {persona_agent.__version__}"


def test_the_subcommands_this_package_serves_resolve() -> None:
    import importlib

    for name in ("run", "doctor", "learned", "chat", "eval"):
        module, func, _help = cli.COMMANDS[name]
        assert callable(getattr(importlib.import_module(module), func)), name


def test_eval_runs_as_a_subcommand(capsys) -> None:
    with pytest.raises(SystemExit) as stop:
        cli.main(["eval", "--help"])
    assert stop.value.code == 0
    out = capsys.readouterr().out
    assert out.startswith("usage: personagent eval")
    assert "--suite" in out


def test_the_eval_shim_still_runs_from_a_checkout() -> None:
    result = subprocess.run([sys.executable, str(ROOT / "tools" / "behavior_eval.py"), "--help"],
                            capture_output=True, text=True, encoding="utf-8",
                            errors="replace", timeout=120)
    assert result.returncode == 0, result.stderr
    assert "--allow-same-judge" in result.stdout


def test_release_notes_come_from_the_changelog_section_of_the_tag() -> None:
    notes = runpy.run_path(str(ROOT / "tools" / "release_notes.py"), run_name="notes_under_test")
    changelog = "\n".join([
        "# Changelog", "", "## [Unreleased]", "", "- next", "",
        "## [1.0.0] - 2026-10-10", "", "### Added", "", "- `personagent` command", "",
        "## [0.4.0] - 2026-09-24", "", "- older", "",
        "[1.0.0]: https://github.com/wangkant/personagent/releases/tag/v1.0.0", ""])
    assert notes["changelog_section"](changelog, "1.0.0") == (
        "### Added\n\n- `personagent` command\n")
    with pytest.raises(ValueError, match="no '## .2.0.0.' section"):
        notes["changelog_section"](changelog, "2.0.0")
    assert notes["project_version"](_pyproject()) == persona_agent.__version__
    assert notes["main"](["v0.0.0-not-this"]) == 1


def test_the_package_smoke_script_names_real_health_checks() -> None:
    from persona_agent import health
    smoke = runpy.run_path(str(ROOT / "tools" / "package_smoke.py"))
    assert set(smoke["CHAT_PROBES"]) <= {name for name, _fn, _crit in health.CHECKS}
