"""The page from another device: the password, sign-in, sessions and the boundary."""
from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from helpers import check
from persona_agent import doctor, pageaccess, preflight
from persona_agent import services as svc
from persona_agent import setup_wizard as sw
from persona_agent import updates
from persona_agent import welcome

TOKEN = "test-local-capability"
PASSWORD = "plum-orchard-41-lantern"
PHONE = ("192.168.1.20", 50000)
SERVER = "http://192.168.1.5:8090"
SESSION = {pageaccess.SESSION_HEADER: "1"}


@pytest.fixture(autouse=True)
def _no_page_settings(monkeypatch):
    for name in (*pageaccess.SETTINGS, pageaccess.CONTAINER_ENV):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(pageaccess, "FAIL_DELAY_S", 0.0)


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    monkeypatch.setattr(sw, "probe_key", lambda *a, **kw: sw.Probe("http://127.0.0.1", 200, ""))
    sw.write_env(tmp_path / ".env", {"PAGE_HOST": "0.0.0.0",
                                     "PAGE_PASSWORD": pageaccess.hash_password(PASSWORD)})
    value = welcome.Workspace(tmp_path)
    yield value
    value.close()


@pytest.fixture
def app(workspace):
    return welcome.create_app(workspace.home, TOKEN, workspace=workspace, gate=pageaccess.Gate(workspace.home))


@pytest.fixture
def phone(app):
    with TestClient(app, base_url=SERVER, client=PHONE) as value:
        yield value


def sign_in(client, password=PASSWORD, **headers):
    return client.post("/auth/signin", json={"password": password}, headers=headers)


# ---- the password and the settings

def test_a_saved_password_is_a_salted_hash_compared_in_full():
    stored = pageaccess.hash_password(PASSWORD)
    check("the hash is not the password", PASSWORD not in stored and stored.startswith("scrypt:"))
    check("each hash has its own salt", stored != pageaccess.hash_password(PASSWORD))
    check("the password matches", pageaccess.verify(stored, PASSWORD))
    for wrong in ("", PASSWORD[:-1], PASSWORD + "x", PASSWORD.upper()):
        check(f"{wrong!r} does not", not pageaccess.verify(stored, wrong))
    check("a damaged hash admits nobody", not pageaccess.verify("scrypt:1:1:1:x:y", PASSWORD))
    check("a plain password from the environment works too", pageaccess.verify(PASSWORD, PASSWORD))
    check("but nothing else", not pageaccess.verify(PASSWORD, PASSWORD[:-1]) and not pageaccess.verify("", ""))


@pytest.mark.parametrize("password, why", [
    ("short1", "short"), ("aaaaaaaaaaaaaaaa", "repetitive"), ("abababab1212", "repetitive"),
    ("line\nbreak-password", "unusable"), ("x" * 1025 + "abcde", "unusable"), (PASSWORD, ""),
])
def test_a_weak_password_is_named(password, why):
    assert pageaccess.weakness(password) == why


def test_beyond_loopback_the_page_needs_a_password_of_reasonable_strength(tmp_path):
    def errors(**values):
        return [key for level, key, _ in pageaccess.problems(pageaccess.from_values(values, {}))
                if level == "ERROR"]
    check("loopback needs nothing", errors() == [] and errors(PAGE_HOST="127.0.0.1") == [])
    check("a network address needs a password", errors(PAGE_HOST="0.0.0.0") == ["PAGE_PASSWORD"])
    check("a weak one is refused", errors(PAGE_HOST="0.0.0.0", PAGE_PASSWORD="hunter2") == ["PAGE_PASSWORD"])
    check("a strong one will do", errors(PAGE_HOST="::", PAGE_PASSWORD=PASSWORD) == [])
    check("a saved hash will do", errors(PAGE_HOST="0.0.0.0",
                                         PAGE_PASSWORD=pageaccess.hash_password(PASSWORD)) == [])
    check("a name is not an address to bind", errors(PAGE_HOST="nas.local", PAGE_PASSWORD=PASSWORD) == ["PAGE_HOST"])
    check("a port must be one", errors(PAGE_PORT="80a") == ["PAGE_PORT"])
    settings = pageaccess.from_values({"PAGE_HOST": "0.0.0.0", "PAGE_PASSWORD": "from-the-file-123"},
                                      {"PAGE_PASSWORD": PASSWORD})
    check("the environment wins over .env, as elsewhere",
          settings.password == PASSWORD and settings.password_from == "environment")
    check("names are kept plain", pageaccess.from_values(
        {"PAGE_ALLOWED_HOSTS": "NAS.local, http://x, pi.tailnet.ts.net."}, {}).allowed
        == ("nas.local", "pi.tailnet.ts.net"))


def test_preflight_and_doctor_say_where_the_page_listens(tmp_path, monkeypatch):
    findings = preflight.check_config(tmp_path, env={"LLM_API_KEY": "k", "PAGE_HOST": "0.0.0.0"})
    check("preflight refuses a network bind without a password",
          any(f.level == "ERROR" and f.key == "PAGE_PASSWORD" for f in findings))
    findings = preflight.check_config(tmp_path, env={"LLM_API_KEY": "k", "PAGE_HOST": "0.0.0.0",
                                                     "PAGE_PASSWORD": PASSWORD})
    check("and is quiet with one", not [f for f in findings if f.key.startswith("PAGE_")])
    monkeypatch.setenv("AGENT_HOME", str(tmp_path))
    state = doctor.page_state()
    check("doctor: this computer only by default", not state["remote"] and doctor.page_row(state)[0] == "  -  ")
    sw.write_env(tmp_path / ".env", {"PAGE_HOST": "0.0.0.0", "PAGE_PORT": "18871"})
    mark, words = doctor.page_row(doctor.page_state())
    check("doctor: a network bind without a password fails", mark == " FAIL" and "0.0.0.0:18871" in words)
    sw.write_env(tmp_path / ".env", {"PAGE_PASSWORD": pageaccess.hash_password(PASSWORD)})
    state = doctor.page_state()
    mark, words = doctor.page_row(state)
    check("doctor: guarded", mark == "  OK " and "password" in words and state["hashed"])
    check("the state carries no password", PASSWORD not in repr(state) and "scrypt" not in repr(state))


# ---- signing in from another device

def test_another_device_gets_the_sign_in_page_and_no_api(phone):
    page = phone.get("/")
    check("the sign-in page", page.status_code == 200 and 'id="signin-form"' in page.text)
    check("its script and style", phone.get("/assets/signin.js").status_code == 200
          and phone.get("/assets/signin.css").status_code == 200)
    check("no API without a session", phone.get("/api/state", headers=SESSION).status_code == 401)
    check("not with the token either", phone.get("/api/state", headers={welcome.TOKEN_HEADER: TOKEN}).status_code == 401)
    check("a container may ask whether it is up", phone.get("/health").json() == {"ok": True})


def test_signing_in_gives_a_strict_http_only_session(phone):
    answer = sign_in(phone)
    assert answer.status_code == 200, answer.text
    cookie = answer.headers["set-cookie"]
    for flag in ("HttpOnly", "SameSite=strict", "Path=/", f"Max-Age={pageaccess.SESSION_S}"):
        check(f"the cookie is {flag}", flag.lower() in cookie.lower(), cookie)
    check("plain HTTP gets no Secure flag it could not keep", "secure" not in cookie.lower())
    check("the password is never in the answer", PASSWORD not in answer.text and PASSWORD not in cookie)
    page = phone.get("/")
    check("the page itself now", 'id="signin-form"' not in page.text and "/assets/welcome.js" in page.text)
    state = phone.get("/api/state", headers=SESSION)
    check("the API answers", state.status_code == 200 and state.json()["remote"] is True)
    check("only with the page's own header", phone.get("/api/state").status_code == 401)


def test_a_session_behind_https_is_secure(phone):
    cookie = sign_in(phone, **{"X-Forwarded-Proto": "https"}).headers["set-cookie"]
    check("Secure behind a TLS proxy", "secure" in cookie.lower(), cookie)


def test_failed_sign_ins_are_slowed_and_capped_per_address(app, monkeypatch):
    slept = []

    async def wait():
        slept.append(pageaccess.FAIL_DELAY_S)
    monkeypatch.setattr(pageaccess, "FAIL_DELAY_S", 1.0)
    monkeypatch.setattr(welcome, "_fail_wait", wait)
    with TestClient(app, base_url=SERVER, client=PHONE) as phone, \
            TestClient(app, base_url=SERVER, client=("192.168.1.21", 50000)) as laptop:
        answers = [sign_in(phone, "wrong-password-0000") for _ in range(pageaccess.FAIL_LIMIT)]
        check("each failure is refused", [a.status_code for a in answers[:-1]] == [401] * (pageaccess.FAIL_LIMIT - 1))
        check("and says how many are left", answers[0].json() == {"error": "signin_wrong", "left": pageaccess.FAIL_LIMIT - 1})
        check("each failure waits", slept == [1.0] * pageaccess.FAIL_LIMIT)
        check("the last one shuts the address out", answers[-1].status_code == 429)
        locked = sign_in(phone)
        check("then even the right password waits", locked.status_code == 429
              and locked.json()["error"] == "signin_locked" and locked.json()["seconds"] > 0)
        check("another address is not affected", sign_in(laptop).status_code == 200)


def test_signing_out_ends_the_session(phone):
    sign_in(phone)
    check("signed in", phone.get("/api/state", headers=SESSION).status_code == 200)
    out = phone.post("/auth/signout", json={}, headers=SESSION)
    check("signed out", out.status_code == 200 and "max-age=0" in out.headers["set-cookie"].lower())
    check("the session is gone", phone.get("/api/state", headers=SESSION).status_code == 401)


def test_a_session_kept_from_before_does_not_survive_a_sign_out(app):
    with TestClient(app, base_url=SERVER, client=PHONE) as phone:
        sign_in(phone)
        kept = phone.cookies.get(pageaccess.COOKIE)
        phone.post("/auth/signout", json={}, headers=SESSION)
        phone.cookies.set(pageaccess.COOKIE, kept)
        check("a copied cookie is refused after sign-out",
              phone.get("/api/state", headers=SESSION).status_code == 401)


def test_a_new_password_ends_every_session(phone, workspace):
    sign_in(phone)
    sw.write_env(workspace.env, {"PAGE_PASSWORD": pageaccess.hash_password("another-long-secret-77")})
    check("the old session is refused", phone.get("/api/state", headers=SESSION).status_code == 401)
    check("the old password too", sign_in(phone).status_code == 401)
    check("the new one works", sign_in(phone, "another-long-secret-77").status_code == 200)


def test_a_removed_password_admits_nobody(phone, workspace):
    sign_in(phone)
    sw.write_env(workspace.env, {"PAGE_PASSWORD": ""})
    check("sessions end", phone.get("/api/state", headers=SESSION).status_code == 401)
    check("and nobody signs in", sign_in(phone, "").status_code == 401)


@pytest.mark.parametrize("headers", [
    {"Origin": "http://evil.example"}, {"Origin": "http://192.168.1.5:9999"}, {"Origin": "null"},
    {"Sec-Fetch-Site": "cross-site"}, {"Sec-Fetch-Site": "same-site"}, {"Host": "evil.example:8090"},
])
def test_cross_site_and_rebound_requests_are_refused(phone, headers):
    sign_in(phone)
    check("the API refuses", phone.get("/api/state", headers={**SESSION, **headers}).status_code == 403)
    check("a sign-in too", sign_in(phone, **headers).status_code == 403)


def test_same_origin_requests_pass_whatever_the_proxy_ends(phone):
    sign_in(phone)
    for headers in ({"Origin": SERVER}, {"Sec-Fetch-Site": "same-origin"},
                    {"Origin": "https://192.168.1.5", "Host": "192.168.1.5"}):
        check(f"{headers}", phone.get("/api/state", headers={**SESSION, **headers}).status_code == 200)


def test_a_name_is_answered_only_when_the_owner_listed_it(app, workspace):
    with TestClient(app, base_url="http://nas.example:8090", client=PHONE) as named:
        check("an unlisted name is refused", named.get("/").status_code == 403)
        sw.write_env(workspace.env, {"PAGE_ALLOWED_HOSTS": "nas.example"})
        check("a listed one is served", named.get("/").status_code == 200)
        check("and signs in", sign_in(named).status_code == 200)


def test_what_acts_on_the_computer_itself_is_refused_to_another_device(phone):
    sign_in(phone)
    for method, path in sorted(welcome.LOCAL_ONLY):
        answer = phone.request(method, path, json={}, headers=SESSION)
        check(f"{method} {path}", answer.status_code == 403 and answer.json()["error"] == "local_only")
    check("the rest of the app panel answers", phone.get("/api/desk", headers=SESSION).status_code == 200)
    runtime = phone.get("/api/runtime", headers=SESSION).json()
    check("the runtime panel knows", runtime["remote"] is True and runtime["headless"] is False)


def test_on_this_computer_nothing_changes(app):
    with TestClient(app, base_url="http://127.0.0.1:8090", client=("127.0.0.1", 50000)) as here:
        check("the page needs no password", 'id="signin-form"' not in here.get("/").text)
        check("the token admits", here.get("/api/state", headers={welcome.TOKEN_HEADER: TOKEN}).status_code == 200)
        check("nothing else does", here.get("/api/state", headers=SESSION).status_code == 403)
        check("no sign-in here", sign_in(here).status_code == 404)
        state = here.get("/api/state", headers={welcome.TOKEN_HEADER: TOKEN}).json()
        check("and the page is not told it is remote", state["remote"] is False)
        proxied = here.get("/api/state", headers={welcome.TOKEN_HEADER: TOKEN, "X-Forwarded-For": "203.0.113.9"})
        check("a proxy on this computer counts as another device", proxied.status_code == 401)


def test_a_password_on_loopback_signs_in_through_a_proxy_on_this_computer(tmp_path, monkeypatch):
    sw.write_env(tmp_path / ".env", {"PAGE_PASSWORD": pageaccess.hash_password(PASSWORD),
                                     "PAGE_ALLOWED_HOSTS": "nas.example"})
    settings = pageaccess.read(tmp_path)
    check("loopback, yet a gate", not settings.remote and settings.wanted
          and pageaccess.gate_for(tmp_path, settings) is not None)
    check("no gate without a password", pageaccess.gate_for(tmp_path, pageaccess.from_values({}, {})) is None)
    space = welcome.Workspace(tmp_path)
    try:
        app = welcome.create_app(tmp_path, TOKEN, workspace=space, gate=pageaccess.gate_for(tmp_path, settings))
        proxied = {"X-Forwarded-For": "203.0.113.9", "X-Forwarded-Proto": "https"}
        with TestClient(app, base_url="https://nas.example", client=("127.0.0.1", 50000),
                        headers=proxied) as proxy:
            check("the proxy's callers get the sign-in page", 'id="signin-form"' in proxy.get("/").text)
            cookie = sign_in(proxy).headers["set-cookie"].lower()
            check("and a Secure session behind HTTPS", "secure" in cookie)
            check("which reaches the API", proxy.get("/api/state", headers=SESSION).status_code == 200)
        with TestClient(app, base_url="http://127.0.0.1", client=("127.0.0.1", 50000)) as here:
            check("this computer keeps its link", here.get("/api/state",
                                                           headers={welcome.TOKEN_HEADER: TOKEN}).status_code == 200)
    finally:
        space.close()


def test_without_a_network_bind_there_is_no_sign_in_at_all(workspace):
    app = welcome.create_app(workspace.home, TOKEN, workspace=workspace)
    with TestClient(app, base_url="http://127.0.0.1") as here, \
            TestClient(app, base_url=SERVER, client=PHONE) as phone:
        check("no sign-in route", sign_in(here).status_code == 404)
        check("another address is refused outright", phone.get("/").status_code == 403)
        check("the token still works", here.get("/api/state", headers={welcome.TOKEN_HEADER: TOKEN}).status_code == 200)


# ---- starting the page

def _can_bind(address: str) -> bool:
    import socket
    with socket.socket() as sock:
        try:
            sock.bind((address, 0))
        except OSError:
            return False
    return True


def _home(tmp_path, monkeypatch, **values):
    monkeypatch.setenv("AGENT_HOME", str(tmp_path))
    if values:
        sw.write_env(tmp_path / ".env", values)
    return tmp_path


def test_start_refuses_a_network_bind_without_a_password(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch, PAGE_HOST="0.0.0.0", PAGE_PORT="18872")
    bound = []
    monkeypatch.setattr(pageaccess, "listen", lambda *a: bound.append(a) or [])
    assert welcome.main(["--no-browser"]) == 1
    said = capsys.readouterr().out
    check("it says why and how", "PAGE_PASSWORD" in said and "personagent page password" in said, said)
    check("nothing listened", not bound)
    check("and nothing is left running", not (tmp_path / "runtime" / "desktop" / "welcome.json").exists())


class _Server:
    """uvicorn.Server without the serving: what it was given."""
    seen: list = []

    def __init__(self, config):
        self.config = config

    def run(self, sockets):
        _Server.seen.append((self.config.app, [s.getsockname() for s in sockets]))


@pytest.fixture
def no_serving(monkeypatch):
    import uvicorn
    _Server.seen = []
    monkeypatch.setattr(uvicorn, "Server", _Server)
    monkeypatch.setattr(pageaccess, "guess_address", lambda: "192.168.1.5")
    return _Server.seen


def test_up_serves_the_page_beyond_loopback_without_a_key(tmp_path, monkeypatch, capsys, no_serving):
    if not _can_bind("127.0.0.2"):
        pytest.skip("127.0.0.2 is not on this system's loopback")
    _home(tmp_path, monkeypatch, PAGE_HOST="127.0.0.2", PAGE_PORT="0",
          PAGE_PASSWORD=pageaccess.hash_password(PASSWORD))
    # 127.0.0.2 stands for a network address: the rules are the same, nothing leaves this computer.
    monkeypatch.setattr(pageaccess, "is_loopback", lambda host: str(host).strip("[]") in ("127.0.0.1", "::1", "localhost"))
    sw.write_env(tmp_path / ".env", {"PAGE_PORT": ""})
    monkeypatch.setattr(pageaccess.Settings, "port_or", lambda self, chosen=0: chosen or 0)
    assert svc.main([]) == 0
    said = capsys.readouterr().out
    (app, addresses), = no_serving
    check("the page was served headless", app.state.headless and app.state.gate is not None)
    check("on the address and on loopback for the link",
          {a[0] for a in addresses} == {"127.0.0.1", "127.0.0.2"} and len({a[1] for a in addresses}) == 1)
    check("it prints the link and where other devices go",
          "#token=" in said and "http://127.0.0.2:" in said and "sign in with the page password" in said, said)
    check("plain HTTP is named once", said.count("plain HTTP") == 1)
    check("no key yet is said", "No model key yet" in said)


def test_up_with_page_on_loopback_and_start_no_browser_keep_their_meaning(tmp_path, monkeypatch, capsys, no_serving):
    _home(tmp_path, monkeypatch, LLM_API_KEY="k")
    monkeypatch.setattr(pageaccess.Settings, "port_or", lambda self, chosen=0: chosen or 0)
    assert svc.main(["--page"]) == 0
    (app, addresses), = no_serving
    check("served on loopback only, with no sign-in", app.state.gate is None and app.state.headless
          and [a[0] for a in addresses] == ["127.0.0.1"])
    check("no line for other devices", "another device" not in capsys.readouterr().out)
    no_serving.clear()
    assert welcome.main(["--no-browser"]) == 0
    (app, addresses), = no_serving
    check("start --no-browser: the window's page, not the headless one", not app.state.headless
          and app.state.gate is None)


def test_up_without_a_key_or_page_still_asks_to_finish_setup(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    assert svc.main([]) == 2
    said = capsys.readouterr().out
    check("it names both ways", "Finish the setup first" in said and "up --page" in said, said)


def test_a_container_makes_a_password_on_its_first_start_and_prints_it_once(tmp_path, monkeypatch, capsys,
                                                                            no_serving):
    _home(tmp_path, monkeypatch)
    monkeypatch.setenv(pageaccess.CONTAINER_ENV, "1")
    monkeypatch.setenv("PAGE_HOST", "0.0.0.0")
    monkeypatch.setattr(pageaccess, "listen", lambda settings, port: [_FakeSocket()])
    assert svc.main([]) == 0
    said = capsys.readouterr().out
    line = next(l for l in said.splitlines() if "shown only this once" in l)
    password = line.rsplit(" ", 1)[-1]
    stored = sw.env_get(tmp_path / ".env", "PAGE_PASSWORD")
    check("only its hash is kept", pageaccess.is_hashed(stored) and password not in stored)
    check("and it is the password", pageaccess.verify(stored, password) and not pageaccess.weakness(password))
    check("the container's way in is named", "this container publishes" in said)
    assert svc.main([]) == 0
    again = capsys.readouterr().out
    check("a second start prints none", "shown only this once" not in again and password not in again)
    check("and keeps the first", sw.env_get(tmp_path / ".env", "PAGE_PASSWORD") == stored)


def test_a_given_password_is_not_replaced_in_a_container(tmp_path, monkeypatch, capsys, no_serving):
    _home(tmp_path, monkeypatch)
    monkeypatch.setenv(pageaccess.CONTAINER_ENV, "1")
    monkeypatch.setenv("PAGE_HOST", "0.0.0.0")
    monkeypatch.setenv("PAGE_PASSWORD", PASSWORD)
    monkeypatch.setattr(pageaccess, "listen", lambda settings, port: [_FakeSocket()])
    assert svc.main([]) == 0
    check("nothing printed or saved", "shown only this once" not in capsys.readouterr().out
          and not sw.env_get(tmp_path / ".env", "PAGE_PASSWORD"))


class _FakeSocket:
    def getsockname(self):
        return ("0.0.0.0", 8090)

    def close(self):
        pass


def test_the_page_password_command_saves_a_hash_and_ends_sessions(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    monkeypatch.setattr(pageaccess, "_ask_password", lambda: "short")
    assert pageaccess.main(["password"]) == 1
    check("a weak one is refused", not sw.env_get(tmp_path / ".env", "PAGE_PASSWORD"))
    monkeypatch.setattr(pageaccess, "_ask_password", lambda: PASSWORD)
    assert pageaccess.main(["password"]) == 0
    stored = sw.env_get(tmp_path / ".env", "PAGE_PASSWORD")
    said = capsys.readouterr()
    check("saved as a hash", pageaccess.verify(stored, PASSWORD) and PASSWORD not in (tmp_path / ".env").read_text())
    check("never echoed", PASSWORD not in said.out + said.err)
    check("it says the page is on loopback", "PAGE_HOST=0.0.0.0" in said.out)
    assert pageaccess.main(["password", "--random"]) == 0
    printed = capsys.readouterr().out
    fresh = next(l for l in printed.splitlines() if "shown only this once" in l).rsplit(" ", 1)[-1]
    check("a random one is printed once and saved",
          pageaccess.verify(sw.env_get(tmp_path / ".env", "PAGE_PASSWORD"), fresh) and fresh not in stored)


def test_two_different_passwords_typed_are_refused(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)

    def differ():
        raise ValueError("mismatch")
    monkeypatch.setattr(pageaccess, "_ask_password", differ)
    assert pageaccess.main(["password"]) == 1
    check("nothing saved", not (tmp_path / ".env").exists() or not sw.env_get(tmp_path / ".env", "PAGE_PASSWORD"))


# ---- the headless page keeps the character running

class _Services:
    def __init__(self):
        self.up = False

    def running(self, name):
        return self.up


class _Workspace:
    def __init__(self, key="k"):
        self._closed = False
        self._future = None
        self.held = False
        self.key = key
        self.services = _Services()
        self.job = {"state": "idle"}
        self.started = 0

    def config(self):
        return {"LLM_API_KEY": self.key}

    def start_job(self, action):
        self.started += 1


async def test_the_headless_page_starts_the_character_once_it_is_set_up(monkeypatch):
    monkeypatch.setattr(welcome, "KEEP_RUNNING_S", 0.01)
    monkeypatch.setattr(welcome, "KEEP_RUNNING_MAX_S", 0.05)
    space = _Workspace(key="")
    task = asyncio.create_task(welcome.keep_running(space))
    await asyncio.sleep(0.05)
    check("nothing starts before a key is saved", space.started == 0)
    space.key = "k"
    await asyncio.sleep(0.05)
    check("then it starts", space.started >= 1)
    space.services.up = True
    seen = space.started
    await asyncio.sleep(0.05)
    check("a running character is left alone", space.started == seen)
    space.held, space.services.up = True, False
    await asyncio.sleep(0.05)
    check("a stop from the page holds", space.started == seen)
    space._closed = True
    await asyncio.wait_for(task, 1)


async def test_a_failing_start_is_tried_again_less_and_less_often(monkeypatch):
    monkeypatch.setattr(welcome, "KEEP_RUNNING_S", 0.01)
    monkeypatch.setattr(welcome, "KEEP_RUNNING_MAX_S", 10.0)
    space = _Workspace()
    task = asyncio.create_task(welcome.keep_running(space))
    await asyncio.sleep(0.4)
    space._closed = True
    await asyncio.wait_for(task, 2)
    # Waits of 0.02, 0.04, 0.08, 0.16 s between tries: a handful, not one per tick.
    check("it backs off", 2 <= space.started <= 7, str(space.started))


# ---- updates where the app cannot update itself

def test_a_container_is_updated_by_pulling_the_image(tmp_path, monkeypatch):
    monkeypatch.setenv(pageaccess.CONTAINER_ENV, "1")
    check("no command runs inside", updates.plan() == ("container", []))
    check("the way is pulling", updates.how_to_update() == (updates.CONTAINER_UPDATE, False))
    found = {"version": "9.9.9", "command": updates.CONTAINER_UPDATE, "opens": False, "url": "u", "container": True}
    check("the terminal says so", "container" in updates.line(found) and "docker compose pull" in updates.line(found))


def test_the_headless_page_does_not_update_itself(workspace, monkeypatch):
    monkeypatch.setattr(updates, "notice", lambda home, latest=None, always=False: {
        "version": "9.9.9", "command": "pip install -U personagent", "opens": False, "url": "u"})
    monkeypatch.setattr(updates, "plan", lambda: ("pip", [["pip", "install", "-U", "personagent"]]))
    monkeypatch.setattr(updates, "blocked", lambda kind, commands: "")
    app = welcome.create_app(workspace.home, TOKEN, workspace=workspace, headless=True)
    app.router.lifespan_context = _no_lifespan
    with TestClient(app, base_url="http://127.0.0.1") as here:
        headers = {welcome.TOKEN_HEADER: TOKEN}
        runtime = here.get("/api/runtime", headers=headers).json()
        check("the panel says to update by hand", runtime["updateBlocked"] == "update_service" and runtime["headless"])
        answer = here.post("/api/runtime/update", json={}, headers=headers)
        check("and the route refuses", answer.status_code == 400 and answer.json()["error"] == "update_service")


class _NoLifespan:
    async def __aenter__(self):
        return None

    async def __aexit__(self, *exc):
        return False


def _no_lifespan(app):
    return _NoLifespan()


def test_listen_takes_loopback_beside_a_specific_address(monkeypatch):
    settings = pageaccess.from_values({"PAGE_HOST": "127.0.0.1"}, {})
    sockets = pageaccess.listen(settings, 0)
    try:
        check("loopback alone", [s.getsockname()[0] for s in sockets] == ["127.0.0.1"])
    finally:
        for sock in sockets:
            sock.close()
    if not _can_bind("127.0.0.3"):
        pytest.skip("127.0.0.3 is not on this system's loopback")
    monkeypatch.setattr(pageaccess, "is_loopback", lambda host: str(host) in ("127.0.0.1", "localhost"))
    settings = pageaccess.from_values({"PAGE_HOST": "127.0.0.3"}, {})
    sockets = pageaccess.listen(settings, 0)
    try:
        names = [s.getsockname() for s in sockets]
        check("the address and loopback, one port", [n[0] for n in names] == ["127.0.0.1", "127.0.0.3"]
              and names[0][1] == names[1][1])
        check("the link stays on loopback", pageaccess.local_link_host(settings) == "127.0.0.1")
    finally:
        for sock in sockets:
            sock.close()


def test_ip_addresses_and_loopback(monkeypatch):
    check("loopback names", all(pageaccess.is_loopback(h) for h in ("127.0.0.1", "::1", "[::1]", "localhost",
                                                                     "::ffff:127.0.0.1", "127.8.9.1")))
    check("others are not", not any(pageaccess.is_loopback(h) for h in ("0.0.0.0", "192.168.1.2", "testclient", "")))
    monkeypatch.setattr(pageaccess, "own_names", lambda: ("myserver", "myserver.local"))
    for host, ok in (("192.168.1.5:8090", True), ("[fe80::1]:8090", True), ("myserver.local:8090", True),
                     ("myserver", True), ("evil.example", False), ("", False), ("a b", False)):
        check(f"Host {host!r}", pageaccess.host_allowed(host, ()) is ok)


def test_the_page_password_never_reaches_a_log_or_an_answer(phone, workspace, capsys):
    sign_in(phone, "wrong-password-0000")
    sign_in(phone)
    state = phone.get("/api/state", headers=SESSION).text
    said = capsys.readouterr()
    for text in (state, said.out, said.err):
        check("not the password", PASSWORD not in text)
        check("nor its hash", "scrypt:" not in text)
    check("the page's settings are not in its state", "PAGE_PASSWORD" not in state)


def test_the_sign_in_page_assets_are_whole():
    root = Path(welcome.ASSETS)
    html = (root / "signin.html").read_text(encoding="utf-8")
    script = (root / "signin.js").read_text(encoding="utf-8")
    check("no inline script for the CSP to block", "<script>" not in html and 'src="/assets/signin.js"' in html)
    for key in ("signin_title", "signin_submit", "signin_wrong", "signin_locked", "signin_http", "signin_forgot"):
        check(f"{key} in both languages", script.count(f"{key}:") == 2)
