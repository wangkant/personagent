"""New chats waiting for the admin's approval, on the platforms listed in
ACCESS_APPROVAL_PLATFORMS (access.py).

A direct message from someone who is neither an admin nor listed, or a group
that is not listed, gets no model turn there. It becomes a request in
<runtime>/approvals.json: who, where, when, a few first words and a short code.

Approved chats are kept in the same file, apart from the settings: the
service adds them to ADMIN_IDS, ACCESS_DM_USERS and ACCESS_GROUPS as it
started with them, whether those came from .env or the environment, so an
approval neither replaces a configured list nor is lost when one is set
elsewhere. Approved chats do not restrict a platform the way a listed entry
does: with approval off, the configured lists alone decide. A declined chat
stays unanswered whatever the policy. The service, the page and
`personagent access` all edit the file under one lock.

    personagent access                         # the same as `list`
    personagent access list                    # requests, approved and declined chats, which platforms ask
    personagent access approve CODE            # answer this chat from now on
    personagent access admin CODE              # approve, and make the sender an admin
    personagent access decline CODE            # never answer, never ask again
    personagent access undo ID                 # forget an approval or a decline
    personagent access policy PLATFORM approve|open
"""
from __future__ import annotations

import argparse
import hmac
import json
import os
import secrets
import sys
import time
import unicodedata
from pathlib import Path
from typing import Optional

from . import access, channels, langs
from .storage import FileLock, atomic_write_text

FILE_NAME = "approvals.json"
# No 0/O, 1/I/L, 2/Z, 5/S, 8/B: read aloud or retyped without a mix-up.
ALPHABET = "ACDEFGHJKMNPQRTUVWXY34679"
CODE_LENGTH = 6
DAY = 86_400
CODE_TTL_S = 3 * DAY
# Per platform and kind, so a flood of groups cannot crowd out direct messages.
MAX_WAITING = {"dm": 20, "group": 10}
# A full list with no admin yet still takes a direct message (the owner's
# may be among them), evicting the oldest; this many fixed answers an hour
# at most come of that.
FULL_TELLS_PER_HOUR = 20
# The fixed answer to one waiting chat, at most this often.
TELL_EVERY_S = DAY
WORDS_CHARS = 80
NAME_CHARS = 48
ID_CHARS = 200
MAX_DECLINED = 1000
MAX_APPROVED = 5000
LOCK_TIMEOUT_S = 10.0
ACTIONS = ("approve", "admin", "decline")
DECISIONS = ("approve", "open")
# Conversation records in the runtime folder that show a platform was used before.
HISTORY_FILES = ("connector_handles.json", "memory.json", "recent.json")


class Refused(ValueError):
    """A decision the request does not allow; the message is a page error code."""


class PolicyLocked(RuntimeError):
    """ACCESS_APPROVAL_PLATFORMS comes from the environment, which .env cannot override."""


# ---------------------------------------------------------------- where

def path_in(runtime: Path) -> Path:
    return Path(runtime) / FILE_NAME


def runtime_of(home: Path) -> Path:
    """The home's runtime folder as the service resolves it (paths.runtime_dir):
    AGENT_RUNTIME_DIR from the environment, else from the home's .env."""
    from . import paths

    configured = os.environ.get("AGENT_RUNTIME_DIR")
    if configured is None:
        configured = _env(home).get("AGENT_RUNTIME_DIR", "")
    return paths.runtime_dir_for(Path(home), configured)


def store_path(home: Path) -> Path:
    """The one approvals file of a home, for the service, the page and the terminal."""
    return path_in(runtime_of(home))


# ---------------------------------------------------------------- what is kept

def clean_text(value, limit: int) -> str:
    """One printable line of at most `limit` characters: no control, format
    or bidi characters, which could reorder or hide text on the page or in a terminal."""
    text = " ".join(str(value or "").split())
    kept = "".join(ch for ch in text if unicodedata.category(ch)[0] != "C")
    return kept[:limit].rstrip() + ("…" if len(kept) > limit else "")


def storable(chat_id: str) -> bool:
    """An id the file can hold and give back unchanged."""
    return (0 < len(chat_id) <= ID_CHARS and not access.is_malformed(chat_id)
            and all(ch.isprintable() and not ch.isspace() for ch in chat_id))


def unverified(chat_id: str) -> bool:
    """An id the platform could not tie to an account (an IRC nick, which
    anyone may take): never made an admin."""
    platform, _, rest = str(chat_id).partition(":")
    return platform == "irc" and rest.startswith("~")


def normal_code(code) -> str:
    return "".join(ch for ch in str(code or "").upper() if ch.isalnum())


def _new_code(taken: set[str]) -> str:
    while True:
        code = "".join(secrets.choice(ALPHABET) for _ in range(CODE_LENGTH))
        if code not in taken:
            return code


class Store:
    """<runtime>/approvals.json: {"waiting", "approved", "declined": [...],
    "decided": {platform: "approve"|"open"}, "full_tells": {platform: [times]}}."""

    def __init__(self, path: Path, *, clock=time.time):
        self.path = Path(path)
        self.lock = FileLock(self.path.with_name("." + self.path.name + ".lock"), timeout=LOCK_TIMEOUT_S)
        self.clock = clock
        self._cache: tuple = (None, {})

    def _raw(self) -> Optional[bytes]:
        """The file's bytes; None when there is no file. Any other failure
        to read it is raised: an empty list saved over it would lose it."""
        try:
            return self.path.read_bytes()
        except FileNotFoundError:
            return None

    def _parse(self, raw: Optional[bytes]) -> dict:
        data: object = {}
        if raw is not None:
            try:
                data = json.loads(raw.decode("utf-8"))
            except ValueError:
                # Damaged: kept beside it, and the lists start empty.
                atomic_write_text(self.path.with_name(self.path.name + ".damaged"),
                                  raw.decode("utf-8", "replace"), fsync=False)
                data = {}
        if not isinstance(data, dict):
            data = {}

        def rows(name: str, *needed: str) -> list[dict]:
            return [r for r in data.get(name) or [] if isinstance(r, dict) and all(r.get(k) for k in needed)]
        now = self.clock()
        decided = data.get("decided") if isinstance(data.get("decided"), dict) else {}
        tells = data.get("full_tells") if isinstance(data.get("full_tells"), dict) else {}
        return {"waiting": [w for w in rows("waiting", "code", "id") if float(w.get("expires") or 0) > now],
                "approved": rows("approved", "id")[-MAX_APPROVED:],
                "declined": rows("declined", "id")[-MAX_DECLINED:],
                "decided": {str(k): v for k, v in decided.items() if v in DECISIONS},
                "full_tells": {str(k): [t for t in v if isinstance(t, (int, float)) and now - t < 3600]
                               for k, v in tells.items() if isinstance(v, list)}}

    def _load(self) -> dict:
        return self._parse(self._raw())

    def _save(self, data: dict) -> None:
        atomic_write_text(self.path, json.dumps(data, ensure_ascii=False, indent=1) + "\n", fsync=False)

    def snapshot(self) -> dict:
        """Everything as stored; no lock needed to read."""
        return self._load()

    def view(self) -> dict:
        """The sets the service admits by, read again only when the file changed."""
        raw = self._raw()
        if raw != self._cache[0] or not self._cache[1]:
            data = self._parse(raw)
            approved = data["approved"]
            self._cache = (raw, {
                "dm": frozenset(a["id"] for a in approved if a.get("kind") == "dm"),
                "group": frozenset(a["id"] for a in approved if a.get("kind") == "group"),
                "admins": frozenset(a["id"] for a in approved if a.get("admin")),
                "declined": frozenset(d["id"] for d in data["declined"])})
        return self._cache[1]

    def note(self, *, platform: str, kind: str, chat_id: str, name: str = "", words: str = "",
             has_admin: bool = True) -> tuple[str, bool]:
        """A message from a chat that is not approved: (its code, whether to
        send the fixed answer now). No code for a declined chat or an id the
        file cannot hold. A full list takes no new group, and a new direct
        message only while the platform has no admin (`has_admin`)."""
        if kind not in ("dm", "group") or not storable(chat_id):
            return "", False
        with self.lock:
            data = self._load()
            if any(d["id"] == chat_id for d in data["declined"]):
                return "", False
            now = self.clock()
            for entry in data["waiting"]:
                if entry["id"] == chat_id:
                    if now - float(entry.get("told") or 0) < TELL_EVERY_S:
                        return entry["code"], False
                    entry["told"] = now
                    self._save(data)
                    return entry["code"], True
            same = [w for w in data["waiting"] if w.get("platform") == platform and w.get("kind") == kind]
            tell = True
            if len(same) >= MAX_WAITING[kind]:
                if kind == "group" or has_admin:
                    return "", False
                oldest = min(same, key=lambda w: float(w.get("at") or 0))
                data["waiting"] = [w for w in data["waiting"] if w is not oldest]
                tells = data["full_tells"].setdefault(platform, [])
                tell = len(tells) < FULL_TELLS_PER_HOUR
                if tell:
                    tells.append(now)
            code = _new_code({w["code"] for w in data["waiting"]})
            data["waiting"].append({
                "code": code, "platform": platform, "kind": kind, "id": chat_id,
                "name": clean_text(name, NAME_CHARS), "words": clean_text(words, WORDS_CHARS),
                "at": now, "told": now if tell else 0, "expires": now + CODE_TTL_S})
            self._save(data)
            return code, tell

    def _find(self, data: dict, code: str) -> Optional[dict]:
        wanted = normal_code(code).encode()
        found = None
        for entry in data["waiting"]:
            # Every entry is compared, so the time taken does not tell how close a guess was.
            if hmac.compare_digest(str(entry["code"]).encode(), wanted):
                found = entry
        return found

    def decide(self, action: str, *, code: str = "", chat_id: str = "", typed: str = "") -> dict:
        """Approve, approve as admin, or decline one request, named by its
        `code` (the terminal) or by its `chat_id` (the page); the entry as it
        was. Making an admin by `chat_id` needs the code the chat received,
        `typed`, so that only someone who reads that chat can do it. Raises
        LookupError when nothing waits there, Refused when the action is not allowed."""
        if action not in ACTIONS:
            raise Refused("approvals_bad_request")
        with self.lock:
            data = self._load()
            if code:
                entry = self._find(data, code)
            else:
                entry = next((w for w in data["waiting"] if w["id"] == chat_id), None)
            if entry is None:
                raise LookupError(code or chat_id)
            if action == "admin":
                if entry["kind"] != "dm":
                    raise Refused("approvals_not_dm")
                if unverified(entry["id"]):
                    raise Refused("approvals_unverified")
                if not code and not hmac.compare_digest(normal_code(typed).encode(),
                                                        str(entry["code"]).encode()):
                    raise Refused("approvals_code_mismatch")
            keep = {k: entry.get(k, "") for k in ("id", "platform", "kind", "name")} | {"at": self.clock()}
            if action == "decline":
                data["declined"] = [*data["declined"], keep][-MAX_DECLINED:]
            else:
                approved = [a for a in data["approved"] if a["id"] != entry["id"]]
                data["approved"] = [*approved, keep | {"admin": action == "admin"}][-MAX_APPROVED:]
            # Single use: the code and the first words go with the request.
            data["waiting"] = [w for w in data["waiting"] if w is not entry]
            self._save(data)
            return entry

    def undo(self, chat_id: str) -> str:
        """Forget an approval or a decline of `chat_id`: "approved",
        "declined", or "" when there was neither. The chat may ask again."""
        with self.lock:
            data = self._load()
            for name in ("approved", "declined"):
                kept = [r for r in data[name] if r["id"] != chat_id]
                if len(kept) != len(data[name]):
                    data[name] = kept
                    self._save(data)
                    return name
            return ""

    def decided(self, platform: str) -> str:
        return self._load()["decided"].get(platform, "")

    def decide_policy(self, platform: str, decision: str) -> None:
        with self.lock:
            data = self._load()
            data["decided"][platform] = decision
            self._save(data)


def approved_admins(runtime: Path) -> frozenset[str]:
    """Accounts made admin with This is me, for the readers outside the service."""
    try:
        return Store(path_in(runtime)).view()["admins"]
    except OSError:
        return frozenset()


# ---------------------------------------------------------------- settings

def _env(home: Path) -> dict:
    from dotenv import dotenv_values
    return {k: str(v or "") for k, v in dotenv_values(Path(home) / ".env").items()}


def policy(values: dict) -> frozenset[str]:
    return access.approval_platforms(values.get(access.APPROVAL_SETTING, ""))


def policy_locked() -> bool:
    """Set in this process's environment and not read from .env: a change
    written to .env would not hold once the service starts again."""
    from . import home as homes
    return access.APPROVAL_SETTING in os.environ and access.APPROVAL_SETTING not in homes.FROM_ENV_FILE


def current_policy(home: Path) -> frozenset[str]:
    """The platforms that ask, as the service reads them."""
    if policy_locked():
        return policy(os.environ)
    return policy(_env(home))


def set_policy(home: Path, platform: str, approve: bool) -> bool:
    """Ask for approval on `platform`, or stop asking, and remember that the
    owner decided; whether the setting changed. Raises PolicyLocked."""
    from .setup_wizard import write_env

    platform = platform.strip().lower()
    if platform in access.NEVER_APPROVED:
        return False
    if policy_locked():
        raise PolicyLocked(access.APPROVAL_SETTING)
    Store(store_path(home)).decide_policy(platform, "approve" if approve else "open")
    current = list(access.split_ids(_env(home).get(access.APPROVAL_SETTING, "")))
    has = platform in (p.lower() for p in current)
    if has == approve:
        return False
    kept = [*current, platform] if approve else [p for p in current if p.lower() != platform]
    write_env(Path(home) / ".env", {access.APPROVAL_SETTING: ",".join(kept)})
    return True


def used_before(home: Path, platform: str) -> bool:
    """Whether this home has chats, history or entries on `platform`."""
    values = _env(home)
    identity = access.identity_from_env({**os.environ, **values})
    for name in access.IDENTITY_SETTINGS:
        if access.entries_on(platform, identity.ids(name)):
            return True
    data = Store(store_path(home)).snapshot()
    if any(r.get("platform") == platform for r in data["approved"] + data["declined"]):
        return True
    runtime = runtime_of(home)
    for name in HISTORY_FILES:
        try:
            found = json.loads((runtime / name).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        keys = found.get("convs", found) if isinstance(found, dict) else {}
        if isinstance(keys, dict) and any(channels.platform_of(k) == platform for k in keys):
            return True
    return False


def adopt(home: Path, platform: str, *, connected: bool = False) -> bool:
    """A platform just connected: ask for approval only when this home has
    never had a decision for it and never used it; whether it now asks. A
    platform connected or used before counts as decided "open" and keeps answering."""
    if platform in access.NOTHING_TO_APPROVE or platform in access.NEVER_APPROVED:
        return False
    store = Store(store_path(home))
    if store.decided(platform) or platform in current_policy(home):
        return False
    if connected or used_before(home, platform):
        store.decide_policy(platform, "open")
        return False
    try:
        set_policy(home, platform, True)
    except PolicyLocked:
        return False
    return True


class LiveEnv:
    """ACCESS_APPROVAL_PLATFORMS as the running service takes it from .env as
    soon as it changes there. A key the file has not changed since the start
    keeps its startup value, which may have come from the environment; a key
    the file had at the start and has lost reads as empty."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self._raw: Optional[bytes] = b""
        self._values: dict = {}
        self._started = dict(self._read())

    def _read(self) -> dict:
        import io

        from dotenv import dotenv_values
        # By content: the file's time cannot tell two writes inside one clock tick apart.
        try:
            raw = self.path.read_bytes()
        except OSError:
            raw = None
        if raw != self._raw:
            self._raw = raw
            try:
                text = raw.decode("utf-8-sig") if raw is not None else ""
            except UnicodeDecodeError:
                text = ""
            self._values = {k: str(v or "") for k, v in dotenv_values(stream=io.StringIO(text)).items()}
        return self._values

    def get(self, key: str) -> Optional[str]:
        """The value written since the start, or None."""
        value = self._read().get(key)
        if value is None:
            return "" if self._started.get(key) else None
        return None if value == self._started.get(key) else value


# ---------------------------------------------------------------- terminal

def _say(text: str) -> None:
    print(langs.term(text))


def _minute(epoch) -> str:
    from datetime import datetime
    return datetime.fromtimestamp(float(epoch)).strftime("%Y-%m-%d %H:%M") if epoch else "—"


def _platform_name(kind: str) -> str:
    from . import connections
    try:
        return connections.say(connections.platform(kind).name, langs.terminal_lang())
    except ValueError:
        return kind


def _command(sub: str) -> str:
    from .setup_wizard import command
    return command(f"access {sub}".strip())


def _who(row: dict) -> str:
    name = row.get("name") or ""
    return f"{name} ({row['id']})" if name else row["id"]


def cmd_list(args, home: Path, store: Store) -> int:
    data = store.snapshot()
    asking = sorted(current_policy(home))
    if args.json:
        print(json.dumps({"policy": asking, **data}, ensure_ascii=False, indent=2))
        return 0
    if asking:
        names = ", ".join(_platform_name(p) for p in asking)
        print(langs.term(f"New chats wait for approval on: {names}.", keep=(names,)))
    else:
        _say("No platform asks for approval: the reply settings alone decide who is answered.")
    if not data["waiting"]:
        _say("No chat is waiting for approval.")
    else:
        _say("Waiting for approval:")
        for w in data["waiting"]:
            where = langs.term("direct message" if w["kind"] == "dm" else "group")
            print(f"  {w['code']}  {_platform_name(w['platform'])}  {where}  {_minute(w.get('at'))}  "
                  f"{_who(w)}  {w.get('words') or ''}".rstrip())
        approve, decline, admin = _command("approve CODE"), _command("decline CODE"), _command("admin CODE")
        print(langs.term(f"Approve with `{approve}`, or decline with `{decline}`. "
                         f"`{admin}` also makes the sender an admin.", keep=(approve, decline, admin)))
    if data["approved"]:
        _say("Approved (answered, besides the reply settings):")
        for a in data["approved"]:
            admin = "  " + langs.term("admin") if a.get("admin") else ""
            print(f"  {a['id']}  {_platform_name(a.get('platform', ''))}  {a.get('name') or ''}{admin}".rstrip())
    if data["declined"]:
        _say("Declined (no answer, no new request):")
        for d in data["declined"]:
            print(f"  {d['id']}  {_platform_name(d.get('platform', ''))}  {d.get('name') or ''}".rstrip())
    if data["approved"] or data["declined"]:
        undo = _command("undo ID")
        print(langs.term(f"`{undo}` forgets an approval or a decline, so the chat asks again.", keep=(undo,)))
    return 0


def cmd_decide(args, home: Path, store: Store) -> int:
    try:
        entry = store.decide(args.cmd, code=args.code)
    except LookupError:
        _say("No waiting request has that code; it may have expired or been decided already.")
        listing = _command("list")
        print(langs.term(f"Run `{listing}` to see the codes.", keep=(listing,)))
        return 1
    except Refused as refused:
        _say({"approvals_not_dm": "Only the sender of a direct message can be made an admin.",
              "approvals_unverified": UNVERIFIED_TERM}.get(str(refused), "This request cannot be decided so."))
        return 1
    who = _who(entry)
    print(langs.term({"approve": f"Approved: {who}. The character answers this chat from now on.",
                      "admin": f"Approved: {who}, now also an admin.",
                      "decline": f"Declined: {who}. This chat gets no answer and makes no new request."
                      }[args.cmd], keep=(who,)))
    if args.cmd == "approve" and unverified(entry["id"]):
        _say(UNVERIFIED_APPROVED_TERM)
    return 0


UNVERIFIED_TERM = ("This IRC sender is not identified with the network's services, so anyone may use "
                   "the nick and it cannot be made an admin. Identify with NickServ, then write again.")
UNVERIFIED_APPROVED_TERM = ("This IRC sender is not identified with the network's services: whoever takes "
                            "the nick next is answered too.")


def cmd_undo(args, home: Path, store: Store) -> int:
    if store.undo(args.chat_id.strip()):
        _say("Done: the chat can ask for approval again.")
        return 0
    listing = _command("list")
    print(langs.term(f"Nothing approved or declined has that id. Run `{listing}` to see the ids.",
                     keep=(listing,)))
    return 1


def cmd_policy(args, home: Path, store: Store) -> int:
    from . import connections
    platform = args.platform.strip().lower()
    known = {p.kind for p in connections.PLATFORMS} | {channels.NATIVE_PLATFORM}
    if platform not in known:
        print(langs.term(f"{platform} is not a platform personagent knows.", keep=(platform,)))
        return 2
    try:
        set_policy(home, platform, args.mode == "approve")
    except PolicyLocked:
        _say("ACCESS_APPROVAL_PLATFORMS is set in the environment, which overrides .env; change it there.")
        return 1
    name = _platform_name(platform)
    print(langs.term(f"New chats on {name} now wait for your approval." if args.mode == "approve"
                     else f"New chats on {name} are answered without approval; the reply settings still apply.",
                     keep=(name,)))
    return 0


def _parser(prog: Optional[str]) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog=prog, description=langs.term(
        "Approve or decline new chats on the platforms that ask for approval"))
    sub = p.add_subparsers(dest="cmd")
    listing = sub.add_parser("list", help=langs.term("list waiting requests and declined chats (the default)"))
    listing.add_argument("--json", action="store_true", help=langs.term("print JSON instead of a table"))
    for name, helptext in (("approve", "answer this chat from now on"),
                           ("admin", "approve, and make the sender an admin"),
                           ("decline", "never answer this chat and never ask again")):
        sp = sub.add_parser(name, help=langs.term(helptext))
        sp.add_argument("code", help=langs.term("the request's code, as the list shows it"))
    undo = sub.add_parser("undo", help=langs.term("forget an approval or a decline, so the chat asks again"))
    undo.add_argument("chat_id", help=langs.term("the chat's id, as the list shows it"))
    pol = sub.add_parser("policy", help=langs.term("whether new chats on a platform wait for approval"))
    pol.add_argument("platform", help=langs.term("the platform, such as telegram or discord"))
    pol.add_argument("mode", choices=DECISIONS)
    return p


COMMANDS = {"list": cmd_list, "approve": cmd_decide, "admin": cmd_decide, "decline": cmd_decide,
            "undo": cmd_undo, "policy": cmd_policy}


def main(argv: Optional[list[str]] = None, prog: Optional[str] = None) -> int:
    from . import home as homes

    langs.utf8_console()
    argv = list(sys.argv[1:] if argv is None else argv)
    p = _parser(prog)
    args = p.parse_args(argv)
    if args.cmd is None:
        args = p.parse_args([*argv, "list"])
    home = homes.find_home()
    return COMMANDS[args.cmd](args, home, Store(store_path(home)))


def waiting_counts(home: Path) -> dict[str, int]:
    """platform -> requests waiting there, for the page and doctor."""
    counts: dict[str, int] = {}
    for entry in Store(store_path(home)).snapshot()["waiting"]:
        counts[entry["platform"]] = counts.get(entry["platform"], 0) + 1
    return counts


if __name__ == "__main__":
    sys.exit(main())
