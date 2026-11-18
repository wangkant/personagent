"""Connecting a platform worked in a browser, from the page and the terminal:
the risk accepted first, a window the owner signs in in (here a sign-in on a
stand-in site), the account read and kept, every new reason named, and the
sign-in deleted with the platform."""
from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from persona_agent import connections as conn
from persona_agent import direct, direct_setup, doctor, updates, welcome
from persona_agent import setup_wizard as sw
from persona_agent.direct import base as direct_base
from persona_agent.direct import browser as web

from web_standin import Site

DRIVER = importlib.util.find_spec("playwright") is not None
needs_browser = pytest.mark.skipif(not DRIVER or web.find_browser() is None,
                                   reason="needs Playwright and an installed Chromium-family browser")
TOKEN = "test-local-capability"
HEADERS = {welcome.TOKEN_HEADER: TOKEN}
KIND = "bilibili"


def standin_class(site: Site) -> type:
    class Standin(web.WebPlatform):
        kind = KIND
        sign_in_url = site.url + "/"
        home_url = site.url + "/inbox"

        async def signed_in(self, page):
            await page.goto(site.url + "/")
            me = page.locator("#me")
            if not await me.count():
                return None
            return await me.get_attribute("data-id"), await me.inner_text()

        async def inbox(self, page):
            return []
    return Standin


@pytest.fixture(autouse=True)
def headless(monkeypatch):
    monkeypatch.setenv(web.HEADLESS_ENV, "1")


@pytest.fixture
def site(monkeypatch):
    made = Site()
    cls = standin_class(made)
    monkeypatch.setattr(direct, "web_class", lambda kind: cls)
    yield made
    made.close()


def signing_in(site: Site, account: str = "42", opened: list | None = None):
    """What the owner does in the sign-in window: sign in, close it."""
    def opener(profile: Path, url: str):
        if opened is not None:
            opened.append(url)

        async def run() -> None:
            browser = web.Browser(profile)
            context = await browser.start()
            page = context.pages[0] if context.pages else await context.new_page()
            if account:
                await page.goto(f"{site.url}/login?as={account}")
            await browser.stop()
        asyncio.run(run())
        return None
    return opener


def leftovers(profile: Path) -> bool:
    """Whether any process still has `profile` open."""
    return direct_setup.profile_open(profile)


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    value = welcome.Workspace(tmp_path)
    sw.write_env(value.env, {"LLM_API_KEY": "key"})
    monkeypatch.setattr(value.services, "start_agent", lambda: None)
    monkeypatch.setattr(value.services, "restart_direct", lambda between=None: between() if between else None)
    monkeypatch.setattr(value.services, "running", lambda name: name == "direct")
    monkeypatch.setattr(direct_base, "read_status", lambda home: {KIND: {"state": "connected"}})
    yield value
    value.close()


@pytest.fixture
def client(workspace):
    with TestClient(welcome.create_app(workspace.home, TOKEN, workspace=workspace),
                    base_url="http://127.0.0.1") as value:
        yield value


# ---------------------------------------------------------------- without a browser

def test_bilibili_and_youtube_are_browser_platforms_with_no_fields():
    for kind in ("bilibili", "youtube"):
        spec = conn.platform(kind)
        assert spec.group == conn.BROWSER and direct_setup.is_browser(spec) and not spec.fields
        assert conn.is_direct(kind) and kind in direct.KINDS and kind in direct.WEB
        assert spec.note[0] and spec.note[1]
    listed = {p["id"]: p for p in conn.catalog()}
    assert listed["youtube"]["signIn"] == "browser" and listed["youtube"]["fields"] == []
    assert sw.direct_targets()["bilibili"] == "bilibili"


def test_a_sign_in_url_is_read_without_starting_a_browser(site):
    assert direct.sign_in_url(KIND) == site.url + "/"
    made = direct.platform_for(KIND, {"account": "Robin"}, Path("home"))
    assert made.home == Path("home") and made.browser.profile == web.profile_path(Path("home"), KIND)
    assert made.seen.path == direct.state_path(Path("home"), KIND) and made.browser.process is None


def test_every_new_reason_is_named_and_explained_on_the_page_and_in_the_terminal():
    js = (welcome.ASSETS / "welcome.js").read_text(encoding="utf-8")
    codes = (web.VERIFICATION, web.PAGE_CHANGED, web.NO_BROWSER, web.NO_DRIVER, web.DAILY_LIMIT)
    spec = conn.platform(KIND)
    for code in codes + ("sign_in_missing", "sign_in_expired"):
        assert code in direct_setup.NAMED_REFUSALS
        page_key = code if code in codes else f"{code}_web"
        assert js.count(f"\n    {page_key}: ") == 2, page_key      # English and Chinese
        for lang in ("en", "zh"):
            said = sw.refusal(code, spec, "Bilibili", lang=lang)
            assert "Bilibili" in said and "{" not in said, said
    # A browser platform's own wording of a code Matrix uses too; Matrix keeps its own.
    assert "window" in sw.refusal("sign_in_missing", spec, "Bilibili", lang="en")
    assert "access token" in sw.refusal("sign_in_missing", conn.platform("matrix"), "Matrix", lang="en")
    assert "translations.en[`${key}_web`]" in js


def test_the_page_routes_that_open_a_window_are_for_this_computer_only():
    assert ("POST", "/api/platforms/browser") in welcome.LOCAL_ONLY
    assert ("POST", "/api/platforms/signed-in") in welcome.LOCAL_ONLY


def test_the_window_opens_only_once_the_risk_is_accepted(client, workspace, monkeypatch):
    started = []
    monkeypatch.setattr(workspace, "start_job", lambda *a, **k: started.append(a))
    url = "/api/platforms/browser"
    for payload in ({"platform": KIND, "allowConversations": True},
                    {"platform": KIND, "acceptRisk": True},
                    {"platform": KIND, "allowConversations": True, "acceptRisk": "yes"}):
        answer = client.post(url, headers=HEADERS, json=payload)
        assert answer.status_code == 400 and answer.json()["error"] == "permission_required"
    assert started == []
    answer = client.post(url, headers=HEADERS, json={"platform": KIND, "allowConversations": True,
                                                     "acceptRisk": True})
    assert answer.status_code == 200 and started == [("browser", KIND)]


def test_only_a_browser_platform_opens_a_window_and_only_while_one_is_open(client, workspace):
    with pytest.raises(ValueError, match="invalid_platform"):
        workspace.start_job("browser", "telegram")
    with pytest.raises(ValueError, match="invalid_platform"):
        workspace.start_job("connect", KIND, {})
    answer = client.post("/api/platforms/signed-in", headers=HEADERS, json={"platform": KIND})
    assert answer.status_code == 400 and answer.json()["error"] == "invalid_platform"


def test_missing_browser_support_is_named_with_this_copys_command(workspace, monkeypatch):
    real = importlib.util.find_spec
    monkeypatch.setattr(importlib.util, "find_spec", lambda name, *a: None if name == "playwright" else real(name, *a))
    opened = []
    monkeypatch.setattr(direct_setup, "open_window", lambda profile, url: opened.append(url))
    monkeypatch.setattr(direct_setup, "support_command", lambda: "pip install the-support")
    workspace.start_job("browser", KIND)
    workspace._future.result(timeout=10)
    assert workspace.job["error"] == web.NO_DRIVER and workspace.job["command"] == "pip install the-support"
    assert opened == [], "nothing opens that could not be checked"
    assert direct_base.load_credentials(workspace.home) == {}


def test_no_browser_is_named_before_anything_opens(workspace, monkeypatch, tmp_path):
    monkeypatch.setenv(web.BROWSER_ENV, str(tmp_path / "missing.exe"))
    workspace.start_job("browser", KIND)
    workspace._future.result(timeout=10)
    assert workspace.job["error"] == web.NO_BROWSER and "command" not in workspace.job


@pytest.mark.parametrize("marker, expected", [
    ("pipx_metadata.json", 'pipx inject personagent "playwright>=1.49,<2"'),
    ("uv-receipt.toml", 'uv tool install --reinstall "personagent[web]"'),
])
def test_the_command_that_adds_browser_support_follows_the_install_method(tmp_path, monkeypatch, marker, expected):
    monkeypatch.setattr("persona_agent.pageaccess.in_container", lambda: False)
    monkeypatch.setattr(updates.homes, "is_checkout", lambda: False)
    monkeypatch.setattr(updates.langs, "under_uvx", lambda: False)
    monkeypatch.setattr(sys, "prefix", str(tmp_path))
    (tmp_path / marker).write_text("", encoding="utf-8")
    assert updates.how_to_add_browser_support() == expected


def test_a_plain_pip_install_adds_playwright_with_its_own_python(tmp_path, monkeypatch):
    monkeypatch.setattr("persona_agent.pageaccess.in_container", lambda: False)
    monkeypatch.setattr(updates.homes, "is_checkout", lambda: False)
    monkeypatch.setattr(updates.langs, "under_uvx", lambda: False)
    monkeypatch.setattr(sys, "prefix", str(tmp_path))
    assert updates.how_to_add_browser_support().endswith('-m pip install "playwright>=1.49,<2"')
    (tmp_path / "pyvenv.cfg").write_text("uv = 0.9.0\n", encoding="utf-8")
    assert updates.how_to_add_browser_support().startswith('uv pip install "playwright>=1.49,<2" --python')
    monkeypatch.setattr(updates.langs, "under_uvx", lambda: True)
    assert updates.how_to_add_browser_support() == 'uvx --from "personagent[web]" personagent'
    monkeypatch.setattr(updates.homes, "is_checkout", lambda: True)
    assert updates.how_to_add_browser_support().endswith(f'-m pip install -e "{updates.homes.CHECKOUT}[web]"')


def test_disconnecting_deletes_the_sign_in_once_nothing_runs(workspace):
    profile = web.profile_path(workspace.home, KIND)
    (profile / "Default").mkdir(parents=True)
    (profile / "Default" / "Cookies").write_bytes(b"x")
    learned = profile.with_suffix(".learned.json")
    learned.write_text("{}", encoding="utf-8")
    direct_base.save_credentials(workspace.home, KIND, {"account": "Robin", "account_id": "42"})
    assert workspace.summary()["platformAccount"] == {KIND: "Robin"}
    workspace.start_job("disconnect", KIND)
    workspace._future.result(timeout=30)
    assert workspace.job["state"] == "ready", workspace.job
    assert direct_base.load_credentials(workspace.home) == {}
    assert not profile.exists() and not learned.exists()


def test_reconnecting_keeps_the_sign_in(workspace, monkeypatch):
    profile = web.profile_path(workspace.home, KIND)
    profile.mkdir(parents=True)
    monkeypatch.setattr(direct_setup, "browser_sign_in", lambda home, spec, **k: {"account": "Robin",
                                                                                 "account_id": "42"})
    workspace.start_job("browser", KIND)
    workspace._future.result(timeout=30)
    assert workspace.job["state"] == "ready" and workspace.job["account"] == "Robin", workspace.job
    assert profile.exists(), "a new sign-in clears what was seen, never the profile"


def test_the_terminal_asks_for_the_acceptance_and_says_why_without_it(tmp_path, monkeypatch, capsys):
    opened = []
    monkeypatch.setattr(direct_setup, "open_window", lambda profile, url: opened.append(url))
    monkeypatch.setattr(direct_setup, "browser_support", lambda: "")
    sw.set_lang("en")
    assert sw.connect_platform(tmp_path, KIND, {}, no_input=True) == 2
    captured = capsys.readouterr()
    assert "--accept-risk" in captured.err and "personal account" in captured.out
    assert "never sees or stores your password" in captured.out
    assert str(web.profile_path(tmp_path, KIND)) in captured.out
    assert opened == [] and direct_base.load_credentials(tmp_path) == {}

    # Asked in a terminal: anything but yes opens nothing.
    monkeypatch.setattr(sw.langs, "interactive", lambda: True)
    monkeypatch.setattr("builtins.input", lambda prompt="": "n")
    assert sw.connect_platform(tmp_path, KIND, {}) == 1
    assert opened == [] and "not accepted" in capsys.readouterr().out


def test_accept_risk_belongs_to_a_browser_platform(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENT_HOME", str(tmp_path))
    with pytest.raises(SystemExit) as exit_:
        sw.connect_main(["telegram", "--accept-risk"])
    assert "--accept-risk" in str(exit_.value.code)
    assert sw.connect_parser("personagent connect").parse_args(["youtube", "--accept-risk"]).accept_risk


def test_doctor_names_missing_browser_support_with_the_command(tmp_path, monkeypatch):
    direct_base.save_credentials(tmp_path, KIND, {"account": "Robin"})
    monkeypatch.setattr(direct_setup, "browser_support", lambda: web.NO_DRIVER)
    monkeypatch.setattr(direct_setup, "support_command", lambda: "pip install the-support")
    found = doctor.direct_platforms(tmp_path)
    assert found["platforms"][0]["missing"] == web.NO_DRIVER
    mark, words = doctor.direct_row(found)
    assert mark == " FAIL" and "pip install the-support" in words and "Playwright" in words
    monkeypatch.setattr(direct_setup, "browser_support", lambda: web.NO_BROWSER)
    mark, words = doctor.direct_row(doctor.direct_platforms(tmp_path))
    assert mark == " FAIL" and "PERSONA_BROWSER_PATH" in words
    monkeypatch.setattr(direct_setup, "browser_support", lambda: "")
    assert doctor.direct_row(doctor.direct_platforms(tmp_path))[0] == "  -  "


def test_doctor_explains_a_verification_the_running_platform_waits_for(tmp_path):
    mark, words = doctor.direct_row({"running": True, "platforms": [
        {"id": KIND, "state": "retrying", "detail": web.VERIFICATION, "missing": ""}]})
    assert "taskbar" in words and mark == "  -  "


# ---------------------------------------------------------------- with one

@needs_browser
def test_the_page_opens_the_window_reads_the_account_and_keeps_it(site, workspace, monkeypatch):
    opened = []
    monkeypatch.setattr(direct_setup, "open_window", signing_in(site, opened=opened))
    stages = []
    real = direct_setup.check

    def check(home, spec, values, **kwargs):
        stages.append(workspace.job["stage"])
        return real(home, spec, values, **kwargs)
    monkeypatch.setattr(direct_setup, "check", check)
    workspace.start_job("browser", KIND)
    assert workspace.job["stage"] == "window"
    workspace._future.result(timeout=120)
    assert workspace.job["state"] == "ready", workspace.job
    assert opened == [site.url + "/"] and stages == ["check"]
    assert workspace.job["account"] == "Robin"
    assert direct_base.load_credentials(workspace.home) == {KIND: {"account": "Robin", "account_id": "42"}}
    summary = workspace.summary()
    assert summary["platforms"] == [KIND] and summary["platformAccount"] == {KIND: "Robin"}
    assert not leftovers(web.profile_path(workspace.home, KIND))


@needs_browser
def test_a_window_closed_with_nobody_signed_in_saves_nothing(site, workspace, monkeypatch):
    monkeypatch.setattr(direct_setup, "open_window", signing_in(site, account=""))
    workspace.start_job("browser", KIND)
    workspace._future.result(timeout=120)
    assert workspace.job["state"] == "error" and workspace.job["error"] == "sign_in_missing", workspace.job
    assert direct_base.load_credentials(workspace.home) == {}


@needs_browser
def test_signed_in_continue_closes_a_window_still_open_and_goes_on(site, workspace, monkeypatch):
    profile = web.profile_path(workspace.home, KIND)

    def opener(profile: Path, url: str):
        signing_in(site)(profile, url)
        # The window the owner leaves open.
        return web._launch([str(web.find_browser()), f"--user-data-dir={profile}", "--headless=new",
                            "--no-first-run", "--no-default-browser-check", url])
    monkeypatch.setattr(direct_setup, "open_window", opener)
    workspace.start_job("browser", KIND)
    deadline = time.monotonic() + 60
    while not leftovers(profile) and time.monotonic() < deadline:
        time.sleep(0.2)
    assert leftovers(profile), "the window holds the profile"
    time.sleep(1.0)
    assert workspace.job["stage"] == "window" and not workspace._future.done(), "it waits for the owner"
    workspace.signed_in(KIND)
    workspace._future.result(timeout=120)
    assert workspace.job["state"] == "ready" and workspace.job["account"] == "Robin", workspace.job
    assert not leftovers(profile)


@needs_browser
def test_the_terminal_connects_with_the_acceptance_given(site, tmp_path, monkeypatch, capsys):
    opened = []
    monkeypatch.setattr(direct_setup, "open_window", signing_in(site, opened=opened))
    sw.set_lang("en")
    assert sw.connect_platform(tmp_path, KIND, {}, no_input=True, accept_risk=True) == 0
    out = capsys.readouterr().out
    assert opened == [site.url + "/"]
    assert "Signed in to Bilibili as Robin." in out and "close the window" in out
    assert direct_base.load_credentials(tmp_path) == {KIND: {"account": "Robin", "account_id": "42"}}

    profile = web.profile_path(tmp_path, KIND)
    assert profile.is_dir()
    assert sw.connect_platform(tmp_path, KIND, {}, remove=True) == 0
    assert "deleted" in capsys.readouterr().out
    assert not profile.exists() and direct_base.load_credentials(tmp_path) == {}


@needs_browser
def test_the_runner_builds_a_browser_platform_on_its_home(site, tmp_path):
    direct_base.save_credentials(tmp_path, KIND, {"account": "Robin", "account_id": "42"})
    asyncio.run(signing_in_async(site, web.profile_path(tmp_path, KIND)))
    made = direct.platform_for(KIND, direct_base.load_credentials(tmp_path)[KIND], tmp_path)
    assert asyncio.run(made.check()) == "Robin"
    assert made.browser.process is None and not leftovers(web.profile_path(tmp_path, KIND))
    assert json.loads(json.dumps(made.keep())) == {"account": "Robin", "account_id": "42"}


async def signing_in_async(site: Site, profile: Path) -> None:
    browser = web.Browser(profile)
    context = await browser.start()
    page = context.pages[0] if context.pages else await context.new_page()
    await page.goto(f"{site.url}/login?as=42")
    await browser.stop()
