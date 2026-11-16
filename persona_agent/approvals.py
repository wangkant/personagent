"""New chats waiting for the admin's approval, on the platforms listed in
ACCESS_APPROVAL_PLATFORMS (access.py).

A direct message from someone in neither ADMIN_IDS nor ACCESS_DM_USERS, or a
group not in ACCESS_GROUPS, gets no model turn there. It becomes a request in
runtime/approvals.json: who, where, when, a few first words and a short code.
Approving adds the id to that list in .env, which the running service reads
again when the file changes; declining keeps the id so it is not offered or
answered again. The service, the page and `personagent access` all edit the
file under one lock.

    personagent access                         # the same as `list`
    personagent access list                    # requests, declined chats, which platforms ask
    personagent access approve CODE            # answer this chat from now on
    personagent access admin CODE              # approve, and make the sender an admin
    personagent access decline CODE            # never answer, never ask again
    personagent access undo ID                 # forget a decline, so the chat may ask again
    personagent access policy PLATFORM approve|open
"""
from __future__ import annotations

import argparse
import hmac
import json
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
# Per platform, so a flood on one cannot crowd out the others or the page.
MAX_WAITING = 20
# The fixed answer to one waiting chat, at most this often.
TELL_EVERY_S = DAY
WORDS_CHARS = 80
NAME_CHARS = 48
MAX_DECLINED = 1000
LOCK_TIMEOUT_S = 10.0
LISTS = {"dm": "ACCESS_DM_USERS", "group": "ACCESS_GROUPS", "admin": "ADMIN_IDS"}
ACTIONS = ("approve", "admin", "decline")
_UNSTORABLE = set(",#'\"\\")


def path_in(runtime: Path) -> Path:
    return Path(runtime) / FILE_NAME


def home_path(home: Path) -> Path:
    return path_in(Path(home) / "runtime")


def clean_text(value, limit: int) -> str:
    """One printable line of at most `limit` characters: no control, format
    or bidi characters, which could reorder or hide text on the page or in a terminal."""
    text = " ".join(str(value or "").split())
    kept = "".join(ch for ch in text if unicodedata.category(ch)[0] != "C")
    return kept[:limit].rstrip() + ("…" if len(kept) > limit else "")


def storable(chat_id: str) -> bool:
    """An id the comma lists in .env can hold and give back unchanged."""
    return (0 < len(chat_id) <= 160 and not access.is_malformed(chat_id)
            and not any(ch in _UNSTORABLE or ch.isspace() or not ch.isprintable() for ch in chat_id))


def normal_code(code) -> str:
    return "".join(ch for ch in str(code or "").upper() if ch.isalnum())


def _new_code(taken: set[str]) -> str:
    while True:
        code = "".join(secrets.choice(ALPHABET) for _ in range(CODE_LENGTH))
        if code not in taken:
            return code


class Store:
    """runtime/approvals.json: {"waiting": [...], "declined": [...]}."""

    def __init__(self, path: Path, *, clock=time.time):
        self.path = Path(path)
        self.lock = FileLock(self.path.with_name("." + self.path.name + ".lock"), timeout=LOCK_TIMEOUT_S)
        self.clock = clock

    def _load(self) -> dict:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        if not isinstance(data, dict):
            data = {}
        waiting = [w for w in data.get("waiting") or [] if isinstance(w, dict) and w.get("code") and w.get("id")]
        declined = [d for d in data.get("declined") or [] if isinstance(d, dict) and d.get("id")]
        now = self.clock()
        return {"waiting": [w for w in waiting if float(w.get("expires") or 0) > now],
                "declined": declined[-MAX_DECLINED:]}

    def _save(self, data: dict) -> None:
        atomic_write_text(self.path, json.dumps(data, ensure_ascii=False, indent=1) + "\n", fsync=False)

    def snapshot(self) -> dict:
        """What waits and what was declined, as stored; no lock needed to read."""
        return self._load()

    def note(self, *, platform: str, kind: str, chat_id: str, name: str = "", words: str = "") -> tuple[str, bool]:
        """A message from a chat that is not approved: (its code, whether to
        send the fixed answer now). No code for a declined chat, an id the
        settings cannot hold, or a platform whose waiting list is full."""
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
            if sum(1 for w in data["waiting"] if w.get("platform") == platform) >= MAX_WAITING:
                return "", False
            code = _new_code({w["code"] for w in data["waiting"]})
            data["waiting"].append({
                "code": code, "platform": platform, "kind": kind, "id": chat_id,
                "name": clean_text(name, NAME_CHARS), "words": clean_text(words, WORDS_CHARS),
                "at": now, "told": now, "expires": now + CODE_TTL_S})
            self._save(data)
            return code, True

    def _find(self, data: dict, code: str) -> Optional[dict]:
        wanted = normal_code(code).encode()
        found = None
        for entry in data["waiting"]:
            # Every entry is compared, so the time taken does not tell how close a guess was.
            if hmac.compare_digest(str(entry["code"]).encode(), wanted):
                found = entry
        return found

    def decide(self, code: str, action: str, home: Path) -> dict:
        """Approve, approve as admin, or decline the request `code` names; the
        entry as it was. Raises LookupError when no request has that code."""
        if action not in ACTIONS:
            raise ValueError(action)
        with self.lock:
            data = self._load()
            entry = self._find(data, code)
            if entry is None:
                raise LookupError(code)
            if action == "admin" and entry["kind"] != "dm":
                raise ValueError(action)
            if action == "decline":
                data["declined"].append({k: entry.get(k, "") for k in ("id", "platform", "kind", "name")}
                                        | {"at": self.clock()})
                data["declined"] = data["declined"][-MAX_DECLINED:]
            else:
                add_to_list(home, LISTS["admin" if action == "admin" else entry["kind"]], entry["id"])
            # Single use: the code and the first words go with the request.
            data["waiting"] = [w for w in data["waiting"] if w is not entry]
            self._save(data)
            return entry

    def undo(self, chat_id: str) -> bool:
        """Forget a decline, so the chat may ask again."""
        with self.lock:
            data = self._load()
            kept = [d for d in data["declined"] if d["id"] != chat_id]
            if len(kept) == len(data["declined"]):
                return False
            data["declined"] = kept
            self._save(data)
            return True


# ---------------------------------------------------------------- settings

def _env(home: Path) -> dict:
    from dotenv import dotenv_values
    return {k: str(v or "") for k, v in dotenv_values(Path(home) / ".env").items()}


def add_to_list(home: Path, name: str, chat_id: str) -> None:
    from .setup_wizard import write_env

    values = _env(home)
    natives = access.split_ids(values.get("CONNECTOR_QQ_PLATFORMS"))
    merged = access.canonical_ids(values.get(name, ""), [chat_id], native_platforms=natives)
    write_env(Path(home) / ".env", {name: ",".join(merged)})


def policy(values: dict) -> frozenset[str]:
    return access.approval_platforms(values.get(access.APPROVAL_SETTING, ""))


def set_policy(home: Path, platform: str, approve: bool) -> bool:
    """Ask for approval on `platform`, or stop asking; whether it changed."""
    from .setup_wizard import write_env

    platform = platform.strip().lower()
    current = list(access.split_ids(_env(home).get(access.APPROVAL_SETTING, "")))
    has = platform in (p.lower() for p in current)
    if has == approve or platform in access.NEVER_APPROVED:
        return False
    kept = [*current, platform] if approve else [p for p in current if p.lower() != platform]
    write_env(Path(home) / ".env", {access.APPROVAL_SETTING: ",".join(kept)})
    return True


def has_admin_on(platform_of_id: str, values: dict) -> bool:
    identity = access.identity_from_env(values)
    return bool(access.entries_on(platform_of_id, identity.admins))


class LiveEnv:
    """The few settings the running service takes from .env as soon as they
    change there (the lists an approval adds to, and the policy). A key the
    file has not changed since the start keeps its startup value, which may
    have come from the environment instead."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self._raw: Optional[bytes] = b""
        self._values: dict = {}
        self._started = self._read()

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
        return None if value is None or value == self._started.get(key) else value


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


def cmd_list(args, home: Path, store: Store) -> int:
    values = _env(home)
    data = store.snapshot()
    asking = sorted(policy(values))
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
                  f"{w.get('name') or w['id']}  {w.get('words') or ''}".rstrip())
        approve, decline, admin = _command("approve CODE"), _command("decline CODE"), _command("admin CODE")
        print(langs.term(f"Approve with `{approve}`, or decline with `{decline}`. "
                         f"`{admin}` also makes the sender an admin.", keep=(approve, decline, admin)))
    if data["declined"]:
        _say("Declined (no answer, no new request):")
        for d in data["declined"]:
            print(f"  {d['id']}  {_platform_name(d.get('platform', ''))}  {d.get('name') or ''}".rstrip())
        undo = _command("undo ID")
        print(langs.term(f"`{undo}` lets one ask again.", keep=(undo,)))
    return 0


def cmd_decide(args, home: Path, store: Store) -> int:
    try:
        entry = store.decide(args.code, args.cmd, home)
    except LookupError:
        _say("No waiting request has that code; it may have expired or been decided already.")
        listing = _command("list")
        print(langs.term(f"Run `{listing}` to see the codes.", keep=(listing,)))
        return 1
    except ValueError:
        _say("Only the sender of a direct message can be made an admin.")
        return 1
    who = entry.get("name") or entry["id"]
    print(langs.term({"approve": f"Approved: {who}. The character answers this chat from now on.",
                      "admin": f"Approved: {who}, now also an admin.",
                      "decline": f"Declined: {who}. This chat gets no answer and makes no new request."
                      }[args.cmd], keep=(who,)))
    return 0


def cmd_undo(args, home: Path, store: Store) -> int:
    if store.undo(args.chat_id.strip()):
        _say("The decline is undone; the chat can ask for approval again.")
        return 0
    listing = _command("list")
    print(langs.term(f"Nothing declined has that id. Run `{listing}` to see the ids.", keep=(listing,)))
    return 1


def cmd_policy(args, home: Path, store: Store) -> int:
    from . import connections
    platform = args.platform.strip().lower()
    known = {p.kind for p in connections.PLATFORMS} | {channels.NATIVE_PLATFORM}
    if platform not in known:
        print(langs.term(f"{platform} is not a platform personagent knows.", keep=(platform,)))
        return 2
    set_policy(home, platform, args.mode == "approve")
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
    undo = sub.add_parser("undo", help=langs.term("forget a decline, so the chat may ask again"))
    undo.add_argument("chat_id", help=langs.term("the declined chat's id, as the list shows it"))
    pol = sub.add_parser("policy", help=langs.term("whether new chats on a platform wait for approval"))
    pol.add_argument("platform", help=langs.term("the platform, such as telegram or discord"))
    pol.add_argument("mode", choices=("approve", "open"))
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
    return COMMANDS[args.cmd](args, home, Store(home_path(home)))


def waiting_counts(home: Path) -> dict[str, int]:
    """platform -> requests waiting there, for the page and doctor."""
    counts: dict[str, int] = {}
    for entry in Store(home_path(home)).snapshot()["waiting"]:
        counts[entry["platform"]] = counts.get(entry["platform"], 0) + 1
    return counts


if __name__ == "__main__":
    sys.exit(main())
