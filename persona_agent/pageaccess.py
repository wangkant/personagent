"""The local page from another device: where it listens, the password that
guards it there, and the sessions of the callers that signed in."""
from __future__ import annotations

import base64
import hashlib
import ipaddress
import os
import secrets
import socket
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

LOOPBACK_NAMES = ("localhost", "127.0.0.1", "::1")
# The port the page takes beyond loopback when PAGE_PORT is blank: a phone needs one it can keep.
REMOTE_PORT = 8090
MIN_LENGTH = 12
MIN_DISTINCT = 5
MAX_LENGTH = 1024
SESSION_S = 7 * 24 * 3600
COOKIE = "personagent_session"
# Sent by the page's own script: a cross-site form or <img> cannot add a header.
SESSION_HEADER = "x-personagent-session"
MAX_SESSIONS = 32
FAIL_LIMIT = 5
FAIL_WINDOW_S = 15 * 60
LOCK_S = 15 * 60
FAIL_DELAY_S = 1.0
MAX_ADDRESSES = 4096
HASH_PREFIX = "scrypt:"
# n, r, p: about 16 MiB and a few dozen milliseconds per attempt.
SCRYPT = (2 ** 14, 8, 1)
# Set by the image: a first start with no password makes and prints one.
CONTAINER_ENV = "PERSONAGENT_IN_CONTAINER"
SETTINGS = ("PAGE_HOST", "PAGE_PORT", "PAGE_PASSWORD", "PAGE_ALLOWED_HOSTS")


def in_container() -> bool:
    return os.environ.get(CONTAINER_ENV, "").strip() == "1"


def _ip(text: str):
    try:
        ip = ipaddress.ip_address(str(text or "").strip().strip("[]"))
    except ValueError:
        return None
    if ip.version == 6 and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    return ip


def is_loopback(host: str) -> bool:
    name = str(host or "").strip().strip("[]").lower()
    if name == "localhost":
        return True
    ip = _ip(name)
    return bool(ip and ip.is_loopback)


def is_wildcard(host: str) -> bool:
    ip = _ip(host)
    return bool(ip and ip.is_unspecified)


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    password: str
    allowed: tuple[str, ...]
    # Names of the settings that could not be read, for the refusal to say.
    invalid: tuple[str, ...] = ()
    # Where the password came from: "environment", ".env" or "".
    password_from: str = ""

    @property
    def remote(self) -> bool:
        return not is_loopback(self.host)

    @property
    def wanted(self) -> bool:
        """Any page setting given: `up` serves the page too."""
        return bool(self.remote or self.port or self.password or "PAGE_PORT" in self.invalid)

    def port_or(self, chosen: int = 0) -> int:
        """The port to listen on: the one asked for, else PAGE_PORT, else a
        free one on loopback and REMOTE_PORT beyond it."""
        return chosen or self.port or (REMOTE_PORT if self.remote else 0)


def read(home: Path, environ: dict | None = None) -> Settings:
    """The page settings, the environment over the home's .env as elsewhere."""
    from dotenv import dotenv_values

    try:
        written = {k: str(v or "") for k, v in dotenv_values(home / ".env").items()}
    except OSError:
        written = {}
    return from_values(written, os.environ if environ is None else environ)


def from_values(written: dict, env: dict) -> Settings:
    """The page settings from a .env's values and an environment, the second winning."""
    written = {k: str(v or "") for k, v in written.items()}

    def get(name: str) -> tuple[str, str]:
        if str(env.get(name) or "").strip():
            return str(env[name]).strip(), "environment"
        if written.get(name, "").strip():
            return written[name].strip(), ".env"
        return "", ""

    invalid = []
    host = get("PAGE_HOST")[0] or "127.0.0.1"
    if host.lower() != "localhost" and _ip(host) is None:
        invalid.append("PAGE_HOST")
    raw_port = get("PAGE_PORT")[0]
    port = 0
    if raw_port:
        if raw_port.isdigit() and 0 < int(raw_port) < 65536:
            port = int(raw_port)
        else:
            invalid.append("PAGE_PORT")
    password, source = get("PAGE_PASSWORD")
    allowed = tuple(dict.fromkeys(
        name.strip().lower().rstrip(".") for name in get("PAGE_ALLOWED_HOSTS")[0].split(",") if name.strip()))
    if any(not _plain_name(name) for name in allowed):
        invalid.append("PAGE_ALLOWED_HOSTS")
        allowed = tuple(name for name in allowed if _plain_name(name))
    return Settings(host, port, password, allowed, tuple(invalid), source)


def _plain_name(name: str) -> bool:
    """A host name without scheme, port, path or wildcard."""
    return bool(name) and all(c.isalnum() or c in "-._" for c in name) and not name.startswith(".")


def weakness(password: str) -> str:
    """Why a password is too weak to guard the page, as a code; '' when it will do."""
    if len(password) < MIN_LENGTH:
        return "short"
    if len(set(password)) < MIN_DISTINCT:
        return "repetitive"
    if len(password) > MAX_LENGTH or any(c.isspace() and c != " " for c in password):
        return "unusable"
    return ""


def is_hashed(stored: str) -> bool:
    return stored.startswith(HASH_PREFIX)


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def hash_password(password: str) -> str:
    """The form `personagent page password` saves: scrypt with a salt of its own."""
    n, r, p = SCRYPT
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=n, r=r, p=p, dklen=32)
    return f"{HASH_PREFIX}{n}:{r}:{p}:{_b64(salt)}:{_b64(digest)}"


def verify(stored: str, attempt: str) -> bool:
    """Whether `attempt` is the password `stored` holds, compared in constant time."""
    if not stored or not attempt or len(attempt) > MAX_LENGTH:
        return False
    given = attempt.encode("utf-8")
    if is_hashed(stored):
        try:
            n, r, p, salt, digest = stored[len(HASH_PREFIX):].split(":")
            n, r, p = int(n), int(r), int(p)
            if not (2 ** 10 <= n <= 2 ** 20 and 1 <= r <= 32 and 1 <= p <= 4):
                return False
            expected = _unb64(digest)
            found = hashlib.scrypt(given, salt=_unb64(salt), n=n, r=r, p=p, dklen=len(expected),
                                   maxmem=256 * 1024 * 1024)
        except (ValueError, TypeError, MemoryError):
            return False
        return secrets.compare_digest(found, expected)
    # Hashed first, so the comparison takes the same time whatever the lengths.
    return secrets.compare_digest(hashlib.sha256(given).digest(), hashlib.sha256(stored.encode("utf-8")).digest())


def fingerprint(stored: str) -> str:
    """Changes with the password, which ends every session made under the old one."""
    return hashlib.sha256(("personagent-page:" + stored).encode("utf-8")).hexdigest()


def problems(settings: Settings) -> list[tuple[str, str, str]]:
    """(level, setting, sentence) for every reason the page cannot listen as configured."""
    found = []
    if "PAGE_HOST" in settings.invalid:
        found.append(("ERROR", "PAGE_HOST",
                      "is not an IP address. Set it to 127.0.0.1 (this computer only), 0.0.0.0 (every "
                      "network of this computer) or one of its addresses"))
    if "PAGE_PORT" in settings.invalid:
        found.append(("ERROR", "PAGE_PORT", "is not a port number from 1 to 65535"))
    if "PAGE_ALLOWED_HOSTS" in settings.invalid:
        found.append(("WARN", "PAGE_ALLOWED_HOSTS",
                      "has an entry that is not a plain host name, so it is ignored. Write names "
                      "such as nas.local, separated by commas, without http:// or a port"))
    if settings.remote and "PAGE_HOST" not in settings.invalid:
        if not settings.password:
            found.append(("ERROR", "PAGE_PASSWORD",
                          "is blank while PAGE_HOST lets other devices reach the page, so the page will "
                          "not start. Run `personagent page password` to set one"))
        elif not is_hashed(settings.password) and weakness(settings.password):
            found.append(("ERROR", "PAGE_PASSWORD",
                          f"is too weak to guard the page from other devices: it needs at least "
                          f"{MIN_LENGTH} characters and {MIN_DISTINCT} different ones. Run "
                          f"`personagent page password` to set a stronger one"))
    return found


def own_names() -> tuple[str, ...]:
    """This computer's own name, which a browser on the network may use for it."""
    try:
        name = socket.gethostname().strip().lower().rstrip(".")
    except OSError:
        return ()
    return (name, f"{name}.local") if _plain_name(name) else ()


def _split_host(value: str) -> tuple[str, int | None] | None:
    try:
        parts = urlsplit("//" + value)
        return (parts.hostname or "").rstrip("."), parts.port
    except ValueError:
        return None


def host_allowed(header: str, allowed: tuple[str, ...]) -> bool:
    """Whether a request addressed to Host `header` is one the owner configured.
    An address typed as numbers cannot be rebound by a name someone else
    controls; a name must be this computer's own or one in PAGE_ALLOWED_HOSTS."""
    split = _split_host(header)
    if not split or not split[0]:
        return False
    name = split[0].lower()
    if _ip(name) is not None or name == "localhost":
        return True
    return name in allowed or name in own_names()


def same_origin(origin: str, host_header: str) -> bool:
    """An Origin header names the address the request was sent to. Its scheme
    is not compared: a proxy may end TLS before the page."""
    if not origin:
        return True
    try:
        parts = urlsplit(origin)
        origin_port = parts.port
    except ValueError:
        return False
    if parts.scheme not in ("http", "https") or not parts.hostname:
        return False
    target = _split_host(host_header)
    if not target:
        return False
    default = 443 if parts.scheme == "https" else 80
    host_port = target[1]
    port = origin_port or default
    return (parts.hostname.rstrip(".").lower() == target[0].lower()
            and (host_port == port or (host_port is None and port == default)))


class Sessions:
    """Signed-in callers, kept in memory: a restart signs everyone out."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._items: dict[str, tuple[float, str]] = {}

    @staticmethod
    def _key(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def create(self, mark: str) -> str:
        token = secrets.token_urlsafe(32)
        now = time.time()
        with self._lock:
            self._items = {k: v for k, v in self._items.items() if v[0] > now}
            while len(self._items) >= MAX_SESSIONS:
                self._items.pop(min(self._items, key=lambda k: self._items[k][0]))
            self._items[self._key(token)] = (now + SESSION_S, mark)
        return token

    def valid(self, token: str, mark: str) -> bool:
        if not token or len(token) > 128:
            return False
        with self._lock:
            found = self._items.get(self._key(token))
            if found is None:
                return False
            if found[0] <= time.time() or not secrets.compare_digest(found[1], mark):
                self._items.pop(self._key(token), None)
                return False
            return True

    def end(self, token: str) -> None:
        with self._lock:
            self._items.pop(self._key(token or ""), None)


class Limiter:
    """Failed sign-ins per address: each is slowed, and FAIL_LIMIT of them
    within FAIL_WINDOW_S shut that address out for LOCK_S."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._failures: dict[str, list[float]] = {}
        self._locked: dict[str, float] = {}

    def wait(self, address: str) -> int:
        """Seconds until `address` may try again; 0 when it may now."""
        with self._lock:
            until = self._locked.get(address, 0.0)
            left = until - time.monotonic()
            if left <= 0:
                self._locked.pop(address, None)
                return 0
            return int(left) + 1

    def failed(self, address: str) -> int:
        """Record a failure; the attempts left before the address is shut out."""
        now = time.monotonic()
        with self._lock:
            if len(self._failures) >= MAX_ADDRESSES:
                self._failures = {a: [t for t in times if now - t < FAIL_WINDOW_S]
                                  for a, times in self._failures.items()}
                self._failures = {a: times for a, times in self._failures.items() if times}
                if len(self._failures) >= MAX_ADDRESSES:
                    self._failures.pop(next(iter(self._failures)))
            recent = [t for t in self._failures.get(address, []) if now - t < FAIL_WINDOW_S] + [now]
            self._failures[address] = recent
            if len(recent) >= FAIL_LIMIT:
                self._locked[address] = now + LOCK_S
                self._failures.pop(address, None)
                return 0
            return FAIL_LIMIT - len(recent)

    def succeeded(self, address: str) -> None:
        with self._lock:
            self._failures.pop(address, None)


class Gate:
    """What the page needs to admit callers from other devices."""

    def __init__(self, home: Path) -> None:
        self.home = home
        self.sessions = Sessions()
        self.limiter = Limiter()
        self._cache: tuple = ()

    def settings(self) -> Settings:
        # Read again when .env or the environment changes: a new password ends the old sessions.
        env = self.home / ".env"
        try:
            stamp = env.stat().st_mtime_ns
        except OSError:
            stamp = None
        key = (stamp, tuple(os.environ.get(name) for name in SETTINGS))
        if not self._cache or self._cache[0] != key:
            self._cache = (key, read(self.home))
        return self._cache[1]

    def mark(self) -> str:
        return fingerprint(self.settings().password)

    def session(self, token: str | None) -> bool:
        stored = self.settings().password
        return bool(stored) and self.sessions.valid(token or "", fingerprint(stored))


def _ask_password() -> str:
    """Typed twice without echo at a terminal; one line from standard input otherwise."""
    import getpass

    from . import langs
    if not langs.interactive():
        return sys.stdin.readline().rstrip("\r\n")
    first = getpass.getpass(langs.term("New page password: "))
    if getpass.getpass(langs.term("Type it again: ")) != first:
        raise ValueError("mismatch")
    return first


def main(argv: list[str] | None = None, prog: str = "personagent page") -> int:
    import argparse

    from . import home as homes, langs
    from .setup_wizard import copy_env_template, write_env
    parser = argparse.ArgumentParser(prog=prog, description=langs.term(
        "The password that lets other devices sign in to the page (PAGE_PASSWORD)"))
    actions = parser.add_subparsers(dest="action", metavar="password", required=True)
    password = actions.add_parser("password", help=langs.term("set or change the page password"),
                                  description=langs.term(
                                      "Set or change the page password. It is typed twice and not shown; "
                                      "without a terminal it is read from one line of standard input. Only "
                                      "its hash is saved, and every signed-in device must sign in again."))
    password.add_argument("--random", action="store_true",
                          help=langs.term("make a random one and print it once, for a server without a display"))
    args = parser.parse_args(argv)
    home = homes.find_home()
    if args.random:
        chosen = secrets.token_urlsafe(18)
    else:
        try:
            chosen = _ask_password()
        except ValueError:
            print(langs.term("The two passwords differ; nothing was saved."), file=sys.stderr)
            return 1
        except (EOFError, KeyboardInterrupt):
            return 1
        why = weakness(chosen)
        if why:
            print(langs.term(f"This password is too weak to guard the page: it needs at least {MIN_LENGTH} "
                             f"characters and {MIN_DISTINCT} different ones. Nothing was saved.")
                  if why != "unusable" else
                  langs.term("This password cannot be saved: it may not contain line breaks or tabs, "
                             "or be longer than 1024 characters. Nothing was saved."), file=sys.stderr)
            return 1
    copy_env_template(home)
    write_env(home / ".env", {"PAGE_PASSWORD": hash_password(chosen)})
    if args.random:
        print(langs.term(f"The new page password, shown only this once: {chosen}", keep=(chosen,)))
    print(langs.term("Saved. Devices that were signed in to the page must sign in again."))
    if os.environ.get("PAGE_PASSWORD", "").strip():
        print(langs.term("PAGE_PASSWORD is also set in the environment, which takes precedence over .env: "
                         "change it there, or remove it there for this one to count."), file=sys.stderr)
    if not read(home).remote:
        print(langs.term("The page listens on this computer only. Set PAGE_HOST=0.0.0.0 in .env for other "
                         "devices to reach it, then start personagent again."))
    return 0


def gate_for(home: Path, settings: Settings) -> "Gate | None":
    """Sign-in for other devices: beyond loopback, or on loopback behind a
    proxy once a password is set. Without either the page is this computer's alone."""
    return Gate(home) if settings.remote or settings.password else None


def local_link_host(settings: Settings) -> str:
    """The address the token link on this computer uses."""
    ip = _ip(settings.host)
    if ip is not None and ip.version == 6 and (ip.is_loopback or ip.is_unspecified):
        return "[::1]"
    return "127.0.0.1"


def guess_address() -> str:
    """This computer's address on its main network, without sending anything; '' if unknown."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        try:
            # A datagram socket's connect only picks a route.
            probe.connect(("192.0.2.1", 9))
            address = probe.getsockname()[0]
        except OSError:
            return ""
    return "" if is_loopback(address) or is_wildcard(address) else address


def listen(settings: Settings, port: int) -> list[socket.socket]:
    """Sockets for the page: the configured address, and loopback beside a
    specific one so the token link keeps working. OSError when one cannot bind."""
    hosts = [settings.host]
    if settings.remote and not is_wildcard(settings.host):
        hosts.insert(0, "127.0.0.1")
    if hosts[0].lower() == "localhost":
        hosts[0] = "127.0.0.1"
    sockets: list[socket.socket] = []
    try:
        for host in hosts:
            ip = _ip(host)
            family = socket.AF_INET6 if ip is not None and ip.version == 6 else socket.AF_INET
            sock = socket.socket(family, socket.SOCK_STREAM)
            sockets.append(sock)
            if family == socket.AF_INET6 and hasattr(socket, "IPV6_V6ONLY") and is_wildcard(host):
                # :: takes IPv4 callers too, where the system allows it.
                try:
                    sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
                except OSError:
                    pass
            if os.name != "nt":
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((host.strip("[]"), port))
            # A free port picked for the first socket is the one the others take.
            port = sock.getsockname()[1]
        for sock in sockets:
            sock.listen(128)
    except (OSError, OverflowError):
        for sock in sockets:
            sock.close()
        raise OSError("bind")
    return sockets
