"""Look at what the character remembers, forget an item, or bring one back.

    personagent memory                        # the same as `list`
    personagent memory list [--chat KEY]      # facts, events, summaries, always-present notes
    personagent memory removed [--chat KEY]   # what was removed and can still come back
    personagent memory forget <id>            # forget one item; it can come back for a day
    personagent memory restore <id>           # bring a removed item back

Ids may be abbreviated to any unique prefix; `--json` prints the data instead
of a table. While the service runs it holds the home, so the commands go
through its local API (the token in runtime/dashboard.token); otherwise they
edit the files themselves, with the same functions the service uses.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from . import langs

KINDS = {"core": "Always in mind", "thread": "Earlier in this chat",
         "note": "Fact", "episode": "Event"}
REASONS = {"replaced": "Replaced by a newer fact", "merged": "Merged with another fact",
           "ended": "No longer current", "evicted": "Removed to make room",
           "rolled_up": "Removed to make room", "rewritten": "Earlier version",
           "unreadable": "Could not be read"}
CORE_ID = "core"
PRACTICE_APART = "What is said in `personagent chat` is practice, kept apart, and does not show here."
TEXT_WIDTH = 60


class Unreachable(RuntimeError):
    """The running service did not give an answer this command can use."""


def _say(text: str) -> None:
    print(langs.term(text))


def _root() -> Path:
    from .paths import ROOT
    return ROOT


def _day(epoch) -> str:
    return datetime.fromtimestamp(float(epoch)).strftime("%Y-%m-%d") if epoch else "—"


def _minute(epoch) -> str:
    return datetime.fromtimestamp(float(epoch)).strftime("%Y-%m-%d %H:%M") if epoch else "—"


def _short(text, width: int = TEXT_WIDTH) -> str:
    text = " ".join(str(text or "").split())
    out = ""
    for ch in text:
        if langs.width(out + ch) > width - 1:
            return out + "…"
        out += ch
    return out


def _restore_command(tid: str) -> str:
    from .setup_wizard import command
    return command(f"memory restore {tid}")


def _memory_command(sub: str = "") -> str:
    from .setup_wizard import command
    return command(f"memory {sub}".strip())


def _no_such_id(removed: bool = False) -> None:
    _say("No item has that id.")
    _say(f"Run `{_memory_command('removed' if removed else '')}` to see the ids.")


# ------------------------------------------------------------ the stores ----

def _files_class():
    """The memory stores alone, as the stopped character opens them."""
    from . import access, embeddings
    from .agent import Agent
    from .memory import Memory
    from .views import DataViews

    class Files(Memory):
        CORE_MEMORY_MAX_CHARS = Agent.CORE_MEMORY_MAX_CHARS
        _sidecar = Agent._sidecar
        _save_json = staticmethod(DataViews._save_json)

        def __init__(self, memory_file: Path, core_file: Path, runtime: Path, settings) -> None:
            self.memory_file, self.core_memory_file, self.runtime = memory_file, core_file, runtime
            self.memory_max_per_conversation = settings.memory_max_per_conversation
            self.memory_share_rooms = settings.memory_share_rooms
            self.embedding_model = settings.embedding_model
            self.admin_ids = set(settings.admin_ids)
            self.connector_qq_platforms = set(settings.connector_qq_platforms)
            self.buffers: dict = {}
            self.memories = self._load_memories()
            self.core_memory = self._load_core_memory()

        @property
        def embedding_cache(self):
            return self._sidecar("_embedding_cache", embeddings.EmbeddingCache,
                                 self.runtime / "embeddings.jsonl")

        def _admins(self) -> frozenset[str]:
            return access.parse_ids(self.admin_ids, native_platforms=self.connector_qq_platforms) \
                | access.page_owner(self.runtime)

    return Files


class FileBackend:
    """Reads and edits the files; only while this command holds the home."""

    def __init__(self, memory_file: Path, core_file: Path, runtime: Path, settings) -> None:
        self.files = _files_class()(memory_file, core_file, runtime, settings)

    def listing(self, chat: str) -> dict:
        from .dashboard import memory_listing
        return memory_listing(self.files, chat)

    def forget(self, conv: str, kind: str, item: str) -> str:
        """The trash id; "-" when it could not be kept, "" when nothing matched."""
        return self.files._forget_item(conv, kind, item, by="terminal")

    def restore(self, tid: str) -> str:
        return self.files._restore(tid, by="terminal")


class ServiceBackend:
    """The running service's local API, as the page uses it."""

    def __init__(self, client) -> None:
        self.client = client

    def _answer(self, response) -> dict:
        try:
            value = response.json()
        except ValueError:
            raise Unreachable("not JSON") from None
        if response.status_code == 404 and value.get("detail") == "Not Found":
            raise Unreachable("activity off")
        return value

    def _call(self, method: str, path: str, **kwargs):
        import httpx
        try:
            response = self.client.request(method, path, **kwargs)
        except httpx.HTTPError as error:
            raise Unreachable(type(error).__name__) from None
        return response, self._answer(response)

    def listing(self, chat: str) -> dict:
        response, value = self._call("GET", "/api/dashboard/memory/list",
                                     params={"conv": chat} if chat else None)
        if response.status_code != 200:
            raise Unreachable(str(value.get("code") or response.status_code))
        return value

    def _write(self, path: str, body: dict):
        return self._call("POST", path, json=body,
                          headers={"X-Personagent-Dashboard": "1"})

    def forget(self, conv: str, kind: str, item: str) -> str:
        response, value = self._write("/api/dashboard/memory/forget",
                                      {"conv": conv, "kind": kind, "id": item, "by": "terminal"})
        if response.status_code == 409:
            return ""
        if response.status_code != 200:
            raise Unreachable(str(value.get("code") or response.status_code))
        return str(value.get("tid") or "-")

    def restore(self, tid: str) -> str:
        response, value = self._write("/api/dashboard/memory/restore",
                                      {"tid": tid, "by": "terminal"})
        if response.status_code == 200:
            return "ok"
        if response.status_code == 409:
            return "exists"
        if response.status_code == 404 and value.get("code") == "restore_gone":
            return "gone"
        raise Unreachable(str(value.get("code") or response.status_code))


def _service_client():
    """An HTTP client for the service on this computer, with its dashboard token."""
    import httpx

    from .config_env import env_int
    from .paths import runtime_dir
    try:
        token = (runtime_dir() / "dashboard.token").read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError):
        token = ""
    port = env_int("SERVER_PORT", 8080, minimum=1, maximum=65535)
    return httpx.Client(base_url=f"http://127.0.0.1:{port}", trust_env=False, timeout=15,
                        headers={"X-Personagent-Dashboard-Token": token})


def _file_backend() -> FileBackend:
    from .paths import resolve_runtime_state_file, runtime_dir
    from .settings import AgentSettings
    settings = AgentSettings.from_env()
    return FileBackend(resolve_runtime_state_file(settings.memory_file),
                       resolve_runtime_state_file("core_memory.json"), runtime_dir(), settings)


# --------------------------------------------------------------- printing ----

def _table(rows: list[list[str]], head: list[str]) -> None:
    head = [langs.term(h) for h in head]
    widths = [max(langs.width(r[i]) for r in [head, *rows]) for i in range(len(head))]

    def line(cells) -> str:
        return "  " + "  ".join(c + " " * (w - langs.width(c))
                                for c, w in zip(cells[:-1], widths)) + "  " + cells[-1]
    print(line(head).rstrip())
    for row in rows:
        print(line(row).rstrip())


def _about(fact: dict) -> str:
    about = fact.get("about") or ""
    said = fact.get("said_by_name") or ""
    if said:
        named = langs.term(f"said by {said}", keep=(said,))
        return f"{about} ({named})" if about else named
    return about


def _memory_rows(chat: dict) -> list[list[str]]:
    rows = []
    core, thread = chat.get("core"), chat.get("thread")
    if core:
        rows.append([CORE_ID, langs.term(KINDS["core"]), "", _day(core.get("at")), "—",
                     _short(core.get("text"))])
    if thread:
        rows.append([thread["id"], langs.term(KINDS["thread"]), "", _day(thread.get("from_t")), "—",
                     _short(thread.get("text"))])
    for fact in chat.get("facts", []):
        rows.append([fact["id"], langs.term(KINDS["note"]), _about(fact), _day(fact.get("born")),
                     _day(fact.get("used")), _short(fact.get("text"))])
    for event in chat.get("events", []):
        rows.append([event["id"], langs.term(KINDS["episode"]),
                     ", ".join(event.get("names") or []), _day(event.get("t0")), "—",
                     _short(event.get("text"))])
    return rows


def _chat_line(conv: str) -> str:
    """The heading of one chat; the page's own chat as the page names it, key kept for --chat."""
    from .access import PAGE_PLATFORM
    from .channels import platform_of

    if platform_of(conv) == PAGE_PLATFORM:
        return langs.term(f"Chat: This page (key {conv})", keep=(conv,))
    return langs.term(f"Chat: {conv}", keep=(conv,))


def _reason(row: dict) -> str:
    if row.get("why") == "forgotten_page":
        return langs.term("Forgotten with this command" if row.get("by") == "terminal"
                          else "Forgotten on the page")
    return langs.term(REASONS.get(row.get("why", ""), row.get("why", "")))


def cmd_list(args, backend) -> int:
    listing = backend.listing(args.chat)
    if args.json:
        print(json.dumps(listing["chats"], ensure_ascii=False, indent=2))
        return 0
    if not listing["chats"]:
        if args.chat:
            _say(f"No chat with the key {args.chat} holds anything remembered. "
                 f"Run `{_memory_command()}` to see the chats and their keys.")
            return 0
        _say("Nothing is remembered.")
        _say(PRACTICE_APART)
        return 0
    for i, chat in enumerate(listing["chats"]):
        if i:
            print()
        print(_chat_line(chat["conv"]))
        _table(_memory_rows(chat), ["Id", "Kind", "About", "First noted", "Last used", "Text"])
    return 0


def cmd_removed(args, backend) -> int:
    removed = backend.listing(args.chat)["removed"]
    if args.json:
        print(json.dumps(removed, ensure_ascii=False, indent=2))
        return 0
    if not removed:
        _say(f"Nothing removed in the chat {args.chat} can be brought back." if args.chat
             else "Nothing removed can be brought back.")
        return 0
    by_chat: dict[str, list[dict]] = {}
    for row in removed:
        by_chat.setdefault(row.get("conv", ""), []).append(row)
    for i, (conv, rows) in enumerate(by_chat.items()):
        if i:
            print()
        print(_chat_line(conv))
        _table([[r["tid"], langs.term(KINDS.get(r["kind"], r["kind"])), _reason(r),
                 _minute(r.get("at")), _minute(r.get("until")), _short(r.get("text"))]
                for r in rows],
               ["Id", "Kind", "Reason", "Removed", "Restorable until", "Text"])
    return 0


def _items(listing: dict) -> list[tuple[str, str, str]]:
    """(chat, kind, id) of everything a forget can name."""
    out = []
    for chat in listing["chats"]:
        conv = chat["conv"]
        if chat.get("core"):
            out.append((conv, "core", CORE_ID))
        if chat.get("thread"):
            out.append((conv, "thread", chat["thread"]["id"]))
        out += [(conv, "note", f["id"]) for f in chat.get("facts", [])]
        out += [(conv, "episode", e["id"]) for e in chat.get("events", [])]
    return out


def _pick(ids: list[str], wanted: str) -> list[int]:
    """The rows `wanted` names: exactly, else as the start of an id."""
    exact = [i for i, value in enumerate(ids) if value == wanted]
    return exact or [i for i, value in enumerate(ids) if value.startswith(wanted)]


def cmd_forget(args, backend) -> int:
    wanted = args.item_id.strip()
    items = _items(backend.listing(args.chat)) if wanted else []
    found = _pick([item[2] for item in items], wanted) if wanted else []
    if not found:
        _no_such_id()
        return 1
    if len(found) > 1:
        _say("Several chats have an always-present note; name one with --chat."
             if wanted == CORE_ID else
             "That id matches more than one item; give more characters.")
        return 1
    conv, kind, item = items[found[0]]
    tid = backend.forget(conv, kind, "" if kind == "core" else item)
    if not tid:
        _no_such_id()
        return 1
    _say("Forgotten.")
    if tid != "-":
        _say(f"To bring it back within 24 hours: {_restore_command(tid)}")
    return 0


def cmd_restore(args, backend) -> int:
    wanted = args.removed_id.strip()
    removed = backend.listing("")["removed"] if wanted else []
    found = _pick([row["tid"] for row in removed], wanted) if wanted else []
    if len(found) > 1:
        _say("That id matches more than one item; give more characters.")
        return 1
    if found:
        tid = removed[found[0]]["tid"]
    elif len(wanted) == 11 and wanted.startswith("r"):
        tid = wanted  # a whole id no longer listed: the store says why
    else:
        _no_such_id(removed=True)
        return 1
    result = backend.restore(tid)
    if result == "ok":
        _say("Restored.")
        return 0
    _say("This item already exists." if result == "exists"
         else "This item can no longer be restored.")
    return 1


# ---------------------------------------------------------------- running ----

def damaged_sentence(error, trial: Path | None = None) -> str:
    """memstore.MemoryFileDamaged as one translated sentence; `trial` is the
    practice chat's folder when the damaged file is its own copy."""
    if trial is not None:
        return langs.term(
            f"The practice chat's memory file {error.path} is damaged; the memory the "
            f"character uses in its chats is not affected. Delete the folder {trial} "
            "to start the practice chat with an empty memory.")
    return langs.term(str(error))


def memory_problem():
    """The MemoryFileDamaged a start would stop on, or None. Reads only."""
    from . import episodes, memstore
    from .paths import resolve_runtime_state_file
    from .settings import AgentSettings

    memory_file = resolve_runtime_state_file(AgentSettings.from_env().memory_file)
    try:
        memstore.load_memory_file(memory_file)
        memstore.load_core_file(resolve_runtime_state_file("core_memory.json"))
        episodes.EpisodeStore(memory_file.with_name("episodes.json")).load()
    except memstore.MemoryFileDamaged as error:
        return error
    return None


def _parser(prog: str | None) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog=prog, description=langs.term(__doc__.splitlines()[0]),
                                epilog=langs.term(PRACTICE_APART))
    sub = p.add_subparsers(dest="cmd")
    for name, helptext in (("list", "list what the character remembers (the default)"),
                           ("removed", "list what was removed and can still be brought back")):
        sp = sub.add_parser(name, help=langs.term(helptext))
        sp.add_argument("--chat", default="", help=langs.term("only this chat, by its key as the list shows it"))
        sp.add_argument("--json", action="store_true", help=langs.term("print JSON instead of a table"))
    forget = sub.add_parser("forget", help=langs.term("forget one item by its id"))
    forget.add_argument("item_id", help=langs.term("the item's id, or the start of it"))
    forget.add_argument("--chat", default="", help=langs.term("only this chat, by its key as the list shows it"))
    restore = sub.add_parser("restore", help=langs.term("bring back a removed item by its id"))
    restore.add_argument("removed_id", help=langs.term("the removed item's id, or the start of it"))
    return p


COMMANDS = {"list": cmd_list, "removed": cmd_removed, "forget": cmd_forget, "restore": cmd_restore}


def main(argv: list[str] | None = None, prog: str | None = None) -> int:
    from . import home
    from .memstore import MemoryFileDamaged
    from .storage import LockUnavailable, RuntimeInstanceLock

    home.load_env()
    langs.utf8_console()
    argv = list(sys.argv[1:] if argv is None else argv)
    p = _parser(prog)
    args = p.parse_args(argv)
    if args.cmd is None:
        args = p.parse_args([*argv, "list"])
    lock = RuntimeInstanceLock(_root())
    try:
        lock.acquire()
        held = True
    except LockUnavailable:
        held = False
    try:
        if held:
            backend = _file_backend()
        else:
            backend = ServiceBackend(_service_client())
        return COMMANDS[args.cmd](args, backend)
    except MemoryFileDamaged as error:
        print(damaged_sentence(error), file=sys.stderr)
        return 1
    except Unreachable as error:
        if str(error) == "activity off":
            _say("The service is running, but its activity data is turned off "
                 "(DASHBOARD_ENABLED=false), so its memory cannot be reached from here. "
                 "Turn activity data on, or stop the service first.")
        else:
            _say("The running service did not answer. Try again in a moment.")
        return 1
    finally:
        if held:
            lock.release()


if __name__ == "__main__":
    sys.exit(main())
