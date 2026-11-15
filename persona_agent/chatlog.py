"""The chat log (runtime/log/): per chat, an append-only record of the lines
the character took in and sent, with the recent window's row shape and
sequence numbers. The ground truth notes cite and the review checks them
against. Kept MEMORY_LOG_DAYS days; never copied, never shared across chats.
No model call here."""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable, Optional

from . import ranking
from .storage import LockUnavailable, append_lock, atomic_write_text
from .textproc import _focus_tokens

__all__ = ["ChatLog", "LockUnavailable", "clean_row", "file_name", "merge_refs", "quote",
           "refs_of"]

logger = logging.getLogger("agent")

DAY_S = 86400.0
#: A second bound beside the days: a chat's newest lines kept.
MAX_LINES = 5000
#: How long a write waits for another writer before trying next time.
LOCK_WAIT_S = 2.0
#: The most lines one search returns.
SEARCH_MAX = 20
TEXT_MAX = 2000
#: The log lines a note cites, at most.
REFS_MAX = 6


def file_name(conv: str) -> str:
    """A chat key never names a path: its hash does."""
    return hashlib.sha256(str(conv).encode("utf-8")).hexdigest()[:32] + ".jsonl"


def _num(value, kind=float):
    try:
        return kind(value)
    except (TypeError, ValueError, OverflowError):
        return kind(0)


def refs_of(item) -> list[int]:
    """The log lines a note or event cites (its `refs`); [] when none."""
    refs = item.get("refs") if isinstance(item, dict) else None
    if not isinstance(refs, list):
        return []
    out = [r for r in refs if isinstance(r, int) and not isinstance(r, bool) and r > 0]
    return list(dict.fromkeys(out))[:REFS_MAX]


def merge_refs(*groups: Iterable[int]) -> list[int]:
    """Several notes' or lines' refs as one: the newest REFS_MAX, in order."""
    seqs = {s for group in groups for s in group
            if isinstance(s, int) and not isinstance(s, bool) and s > 0}
    return sorted(seqs)[-REFS_MAX:]


def clean_row(row) -> Optional[dict]:
    """A log row from a recent-window row (room line or DM turn), or None."""
    if not isinstance(row, dict):
        return None
    seq = _num(row.get("seq"), int)
    if seq <= 0:
        return None
    out = {"seq": seq, "t": _num(row.get("t")),
           "user_id": str(row.get("user_id") or ""),
           "name": str(row.get("name") or ""),
           "text": str(row.get("text") or "")[:TEXT_MAX]}
    if _num(row.get("t1")) > out["t"]:
        out["t1"] = _num(row.get("t1"))
    for flag in ("self", "gone"):
        if row.get(flag):
            out[flag] = True
    if row.get("mid"):
        out["mid"] = str(row["mid"])[:80]
    return out


def _end(row: dict) -> float:
    return row.get("t1") or row["t"]


def _dump(rows: Iterable[dict]) -> str:
    return "".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n"
                   for r in rows)


class ChatLog:
    """One file per chat in `folder`; each row one line of JSON. A row read
    twice with one seq is a line that grew (a merge): the later wins. A
    `gone` row only holds the place of a forgotten newest line, so it is
    not logged again."""

    def __init__(self, folder: Path, days: float = 30, max_lines: int = MAX_LINES):
        self.folder = Path(folder)
        self.days = float(days or 0)
        self.max_lines = int(max_lines)
        #: {conv: (newest seq logged, its text's length)}
        self._marks: dict[str, tuple[int, int]] = {}

    @property
    def on(self) -> bool:
        return self.days > 0

    def path(self, conv: str) -> Path:
        return self.folder / file_name(conv)

    # ---- reading --------------------------------------------------------------

    def _read_path(self, path: Path) -> list[dict]:
        """Every row of a file in seq order, place-holders too; a damaged
        line (a write cut short) is skipped."""
        try:
            blob = path.read_bytes()
        except FileNotFoundError:
            return []
        except OSError as e:
            logger.warning("[Agent] chat log read failed: %s", e)
            return []
        by_seq: dict[int, dict] = {}
        for raw in blob.split(b"\n"):
            if not raw.strip():
                continue
            try:
                row = clean_row(json.loads(raw.decode("utf-8")))
            except (UnicodeDecodeError, ValueError):
                continue
            if row is not None:
                by_seq[row["seq"]] = row
        return [by_seq[s] for s in sorted(by_seq)]

    def read(self, conv: str) -> list[dict]:
        """The chat's lines in seq order."""
        return [r for r in self._read_path(self.path(conv)) if not r.get("gone")]

    def lines(self, conv: str, seqs: Iterable[int]) -> list[dict]:
        want = {_num(s, int) for s in seqs}
        return [row for row in self.read(conv) if row["seq"] in want]

    def last_seq(self, conv: str) -> int:
        return self._mark(conv)[0]

    def search(self, conv: str, words: str = "", *, speakers: Iterable[str] = (),
               since: float = 0.0, until: float = 0.0, limit: int = SEARCH_MAX,
               lang: str = "zh", skip: Iterable[int] = (),
               rows: Optional[list[dict]] = None) -> list[dict]:
        """Lines by words (BM25 over focus tokens), by speaker ids, by time
        range: best first when `words` is given, else newest first. Words
        that make no token find nothing."""
        uids = {str(u) for u in speakers if u}
        skipped = {_num(s, int) for s in skip}
        rows = [row for row in (self.read(conv) if rows is None else rows)
                if row["seq"] not in skipped and row["text"].strip()
                and (not uids or row["user_id"] in uids)
                and (not since or _end(row) >= since)
                and (not until or row["t"] <= until)]
        limit = max(0, min(int(limit), SEARCH_MAX))
        if not words:
            return rows[::-1][:limit]
        query = _focus_tokens(words, lang)
        if not query or not rows:
            return []
        docs = [(row["text"].lower(),) for row in rows]
        lex = ranking.Lexicon(query, docs)
        hits = [(lex.score(doc, (1.0,)), row["seq"], row) for doc, row in zip(docs, rows)]
        hits = sorted((h for h in hits if h[0] > 0), key=lambda h: (-h[0], -h[1]))
        return [row for _s, _q, row in hits[:limit]]

    def status(self, conv: Optional[str] = None) -> dict:
        """What the page shows: on or off, the days kept, and for one chat
        how many lines and from when to when."""
        out: dict = {"on": self.on, "days": int(self.days)}
        if conv is not None:
            rows = self.read(conv)
            out.update(lines=len(rows),
                       first_at=rows[0]["t"] if rows else 0.0,
                       last_at=_end(rows[-1]) if rows else 0.0)
        else:
            out["chats"] = len(self._files())
        return out

    # ---- writing --------------------------------------------------------------

    def _mark(self, conv: str) -> tuple[int, int]:
        if conv not in self._marks:
            rows = self._read_path(self.path(conv))
            last = rows[-1] if rows else None
            # A forgotten line's place takes no grown copy of it either.
            self._marks[conv] = (0, 0) if last is None else (
                last["seq"], TEXT_MAX + 1 if last.get("gone") else len(last["text"]))
        return self._marks[conv]

    def take(self, conv: str, rows: Iterable[dict]) -> int:
        """Append the rows not logged yet, and a grown copy of the newest one
        logged; returns how many were taken. Never raises."""
        if not self.on:
            return 0
        try:
            seq, size = self._mark(conv)
            fresh = []
            for row in sorted(filter(None, map(clean_row, rows)), key=lambda r: r["seq"]):
                if row["seq"] > seq or (row["seq"] == seq and len(row["text"]) > size):
                    fresh.append(row)
                    seq, size = row["seq"], len(row["text"])
            if not fresh:
                return 0
            # A line without a time (a page chat read back) cannot be dated,
            # and one older than the kept days would only be pruned again.
            cutoff = time.time() - self.days * DAY_S
            self._append(conv, [r for r in fresh if r["t"] > 0 and _end(r) >= cutoff])
            self._marks[conv] = (seq, size)
            return len(fresh)
        except (OSError, LockUnavailable) as e:
            # The mark did not move: tried again on the next write.
            logger.warning("[Agent] chat log append failed: %s", e)
            return 0

    def _append(self, conv: str, rows: list[dict]) -> None:
        if not rows:
            return
        path = self.path(conv)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = _dump(rows).encode("utf-8")
        with append_lock(path, timeout=LOCK_WAIT_S):
            fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_APPEND
                         | getattr(os, "O_BINARY", 0), 0o600)
            try:
                if os.fstat(fd).st_size:
                    os.lseek(fd, -1, os.SEEK_END)
                    if os.read(fd, 1) != b"\n":
                        # After a write cut short: its fragment is skipped on read.
                        payload = b"\n" + payload
                view = memoryview(payload)
                while view:
                    view = view[os.write(fd, view):]
                os.fsync(fd)
            finally:
                os.close(fd)

    def _replace(self, path: Path, rows: list[dict], kept: list[dict]) -> None:
        """Write `kept` in place of `rows`; a gone newest line leaves its place."""
        if rows and (not kept or kept[-1]["seq"] < rows[-1]["seq"]):
            last = rows[-1]
            kept = kept + [{"seq": last["seq"], "t": last["t"], "user_id": "",
                            "name": "", "text": "", "gone": True}]
        atomic_write_text(path, _dump(kept))

    def forget(self, conv: str, gone: Callable[[dict], bool]) -> int:
        """Remove the lines `gone` matches; how many went."""
        path = self.path(conv)
        if not path.is_file():
            return 0
        with append_lock(path, timeout=LOCK_WAIT_S):
            rows = self._read_path(path)
            kept = [r for r in rows if r.get("gone") or not gone(r)]
            if len(kept) == len(rows):
                return 0
            self._replace(path, rows, kept)
        self._marks.pop(conv, None)
        return len(rows) - len(kept)

    def drop(self, conv: str) -> bool:
        """Forget this chat: its file goes."""
        path = self.path(conv)
        self._marks.pop(conv, None)
        try:
            with append_lock(path, timeout=LOCK_WAIT_S):
                path.unlink()
        except FileNotFoundError:
            return False
        finally:
            self._marks.pop(conv, None)
            try:
                path.with_name(f".{path.name}.append.lock").unlink()
            except OSError:
                pass
        return True

    def _files(self) -> list[Path]:
        try:
            return sorted(self.folder.glob("*.jsonl"))
        except OSError:
            return []

    def clear(self) -> int:
        """Every chat's log goes (the log turned off, a reset)."""
        gone = 0
        for path in self._files():
            try:
                path.unlink()
                gone += 1
            except OSError as e:
                logger.warning("[Agent] chat log not removed: %s", e)
        self._marks.clear()
        return gone

    def prune(self, now: Optional[float] = None) -> int:
        """Drop lines older than the kept days and past the per-chat cap;
        returns how many went."""
        now = time.time() if now is None else now
        cutoff = now - self.days * DAY_S
        gone = 0

        def keep(rows: list[dict]) -> list[dict]:
            return [r for r in rows if _end(r) >= cutoff][-self.max_lines:]

        for path in self._files():
            rows = self._read_path(path)
            if len(keep(rows)) == len(rows):
                continue
            try:
                with append_lock(path, timeout=LOCK_WAIT_S):
                    rows = self._read_path(path)
                    kept = keep(rows)
                    if kept:
                        atomic_write_text(path, _dump(kept))
                    else:
                        path.unlink()
                if not kept:
                    # The lock of a log that is gone would otherwise stay for good.
                    path.with_name(f".{path.name}.append.lock").unlink(missing_ok=True)
                gone += sum(1 for r in rows if not r.get("gone")) - sum(
                    1 for r in kept if not r.get("gone"))
            except (OSError, LockUnavailable) as e:
                logger.warning("[Agent] chat log prune failed: %s", e)
        # Marks of files that went are read again; the window keeps seq ahead.
        self._marks.clear()
        return gone


def quote(row: dict, tz=None) -> str:
    """One logged line as "YYYY-MM-DD HH:MM name: text"."""
    t = row.get("t") or 0.0
    when = datetime.fromtimestamp(t, tz).strftime("%Y-%m-%d %H:%M") if t else ""
    return f"{when} {row.get('name') or '?'}: {row.get('text', '')}".strip()
