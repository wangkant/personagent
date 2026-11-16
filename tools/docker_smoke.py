"""Run the personagent image as a server would and check it from outside.

    python tools/docker_smoke.py --image personagent:ci

Two containers in turn: one given PAGE_PASSWORD, one that makes its own on
the first start. Each must become healthy, show the sign-in page, refuse a
wrong password and let the right one reach /api/state. Needs docker and the
standard library only; nothing is sent beyond this computer."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

PASSWORD = "ci-page-password-4817"
PORT = 18090
NAME = "personagent-smoke"
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def docker(*args: str, check: bool = True) -> str:
    done = subprocess.run(["docker", *args], capture_output=True, text=True)
    if check and done.returncode:
        raise SystemExit(f"docker {' '.join(args)} failed:\n{done.stdout}{done.stderr}")
    return done.stdout + done.stderr


def _headers(message) -> dict:
    # Names as sent differ in case from one server to the next.
    return {name.lower(): value for name, value in message.items()}


def request(path: str, payload: dict | None = None, cookie: str = "", session: bool = False) -> tuple[int, dict, str]:
    headers = {"Content-Type": "application/json"} if payload is not None else {}
    if cookie:
        headers["Cookie"] = cookie
    if session:
        headers["X-Personagent-Session"] = "1"
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}{path}", data=data, headers=headers,
                                 method="POST" if data is not None else "GET")
    try:
        with OPENER.open(req, timeout=10) as answer:
            return answer.status, _headers(answer.headers), answer.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as error:
        return error.code, _headers(error.headers), error.read().decode("utf-8", "replace")


def expect(what: str, ok: bool, detail: str = "") -> None:
    print(("ok    " if ok else "FAIL  ") + what, flush=True)
    if not ok:
        print(docker("logs", NAME, check=False))
        docker("rm", "-f", NAME, check=False)
        raise SystemExit(f"{what}: {detail}")


def wait_healthy(seconds: float = 150) -> None:
    deadline = time.monotonic() + seconds
    state = ""
    while time.monotonic() < deadline:
        state = docker("inspect", "-f", "{{.State.Health.Status}}", NAME, check=False).strip()
        if state == "healthy":
            break
        time.sleep(2)
    expect("the container becomes healthy", state == "healthy", state)


def sign_in_checks(password: str) -> None:
    status, _, page = request("/")
    expect("another device gets the sign-in page", status == 200 and 'id="signin-form"' in page, page[:200])
    status, _, _ = request("/api/state", session=True)
    expect("no API without signing in", status == 401, str(status))
    status, _, said = request("/auth/signin", {"password": password + "x"})
    expect("a wrong password is refused", status == 401 and "signin_wrong" in said, f"{status} {said}")
    status, headers, said = request("/auth/signin", {"password": password})
    cookie = headers.get("set-cookie", "").split(";")[0]
    expect("the right one signs in", status == 200 and cookie.startswith("personagent_session="), f"{status} {said}")
    flags = headers.get("set-cookie", "").lower()
    expect("with an HttpOnly, SameSite=Strict cookie", "httponly" in flags and "samesite=strict" in flags, flags)
    status, _, said = request("/api/state", cookie=cookie, session=True)
    state = json.loads(said) if status == 200 else {}
    expect("and reaches /api/state", status == 200 and state.get("remote") is True and state.get("container") is True,
           f"{status} {said[:200]}")
    status, _, page = request("/", cookie=cookie)
    expect("the page itself after signing in", status == 200 and "/assets/welcome.js" in page)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--image", required=True)
    image = parser.parse_args().image
    docker("rm", "-f", NAME, check=False)
    docker("volume", "rm", "-f", f"{NAME}-data", check=False)
    try:
        docker("run", "-d", "--init", "--name", NAME, "-p", f"127.0.0.1:{PORT}:8090",
               "-e", f"PAGE_PASSWORD={PASSWORD}", image)
        wait_healthy()
        sign_in_checks(PASSWORD)
        user = docker("exec", NAME, "id", "-u").strip()
        expect("it runs as a user, not root", user not in ("", "0"), user)
        docker("rm", "-f", NAME)

        docker("run", "-d", "--init", "--name", NAME, "-p", f"127.0.0.1:{PORT}:8090",
               "-v", f"{NAME}-data:/data", image)
        wait_healthy()
        found = re.search(r"shown only this once: (\S+)", docker("logs", NAME))
        expect("a first start without a password prints one", bool(found))
        sign_in_checks(found.group(1))
        stored = docker("exec", NAME, "sh", "-c", "grep '^PAGE_PASSWORD=' /data/.env").strip()
        expect("only its hash is kept", "scrypt:" in stored and found.group(1) not in stored, stored)
        docker("restart", NAME)
        wait_healthy()
        printed = len(re.findall(r"shown only this once", docker("logs", NAME)))
        expect("a second start prints none", printed == 1, str(printed))
        sign_in_checks(found.group(1))
    finally:
        docker("rm", "-f", NAME, check=False)
        docker("volume", "rm", "-f", f"{NAME}-data", check=False)
    print("the image passed", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
