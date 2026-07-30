"""Crash-conscious primitives for small local runtime stores.

The agent intentionally uses ordinary files instead of a database.  These
helpers centralize the guarantees those files need: one runtime owner, locked
append-only writes, durable same-directory replacement, private permissions,
and strict JSONL replay that reports invalid rows without deleting history.
"""
from __future__ import annotations

import errno
import json
import os
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

PRIVATE_FILE_MODE = 0o600
DEFAULT_LOCK_TIMEOUT_SEC = 30.0


class LockUnavailable(RuntimeError):
    """Raised when a file lock cannot be acquired within its timeout."""


def _set_private_permissions(path: Path) -> None:
    try:
        os.chmod(path, PRIVATE_FILE_MODE)
    except OSError:
        # Windows ACLs do not map cleanly to POSIX mode bits.  Creation still
        # uses 0600 where supported; deployment ACL policy remains authoritative.
        pass


def _sync_directory(directory: Path) -> None:
    """Persist a directory entry update where the platform supports it."""
    if os.name == "nt" or not hasattr(os, "O_DIRECTORY"):
        return
    fd = -1
    try:
        fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
        os.fsync(fd)
    except OSError:
        # Some filesystems reject directory fsync.  The file itself has already
        # been fsynced; lack of directory support must not turn a safe replace
        # into an application failure.
        pass
    finally:
        if fd >= 0:
            os.close(fd)


class FileLock:
    """Cross-platform advisory exclusive lock backed by a sidecar file."""

    def __init__(self, path: str | Path, *, timeout: float | None = None):
        self.path = Path(path)
        self.timeout = timeout
        self._fd = -1

    def acquire(self) -> "FileLock":
        if self._fd >= 0:
            return self
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.path, os.O_RDWR | os.O_CREAT, PRIVATE_FILE_MODE)
        _set_private_permissions(self.path)
        deadline = (
            None if self.timeout is None
            else time.monotonic() + max(0.0, float(self.timeout))
        )
        while True:
            try:
                self._try_lock(fd)
                self._fd = fd
                return self
            except OSError as exc:
                if not self._is_busy(exc):
                    os.close(fd)
                    raise
                if deadline is not None and time.monotonic() >= deadline:
                    os.close(fd)
                    raise LockUnavailable(
                        f"lock already held: {self.path}") from exc
                time.sleep(0.02)

    @staticmethod
    def _is_busy(exc: OSError) -> bool:
        return exc.errno in (
            errno.EACCES, errno.EAGAIN, errno.EDEADLK,
            getattr(errno, "EWOULDBLOCK", errno.EAGAIN),
        )

    @staticmethod
    def _try_lock(fd: int) -> None:
        if os.name == "nt":
            import msvcrt

            if os.fstat(fd).st_size == 0:
                os.write(fd, b"\0")
                os.fsync(fd)
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

    @staticmethod
    def _unlock(fd: int) -> None:
        if os.name == "nt":
            import msvcrt

            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(fd, fcntl.LOCK_UN)

    def release(self) -> None:
        if self._fd < 0:
            return
        fd, self._fd = self._fd, -1
        try:
            self._unlock(fd)
        finally:
            os.close(fd)

    def __enter__(self) -> "FileLock":
        return self.acquire()

    def __exit__(self, *_exc) -> None:
        self.release()


class RuntimeInstanceLock(FileLock):
    """Non-blocking single-owner lock for one resolved runtime directory."""

    def __init__(self, runtime_directory: str | Path):
        runtime_directory = Path(runtime_directory)
        super().__init__(
            runtime_directory / ".personagent.instance.lock", timeout=0.0)


def append_lock_path(path: str | Path) -> Path:
    path = Path(path)
    return path.with_name(f".{path.name}.append.lock")


def append_lock(path: str | Path, *,
                timeout: float | None = DEFAULT_LOCK_TIMEOUT_SEC) -> FileLock:
    return FileLock(append_lock_path(path), timeout=timeout)


def _write_all(fd: int, data: bytes) -> None:
    offset = 0
    while offset < len(data):
        offset += os.write(fd, data[offset:])


def append_jsonl_unlocked(path: str | Path, row: dict) -> int:
    """Append one complete JSON object; caller must hold ``append_lock(path)``."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(
        row, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    existed = path.exists()
    fd = os.open(
        path, os.O_RDWR | os.O_CREAT | os.O_APPEND, PRIVATE_FILE_MODE)
    try:
        _set_private_permissions(path)
        size = os.fstat(fd).st_size
        if size:
            os.lseek(fd, -1, os.SEEK_END)
            if os.read(fd, 1) != b"\n":
                _write_all(fd, b"\n")
        _write_all(fd, payload)
        os.fsync(fd)
    finally:
        os.close(fd)
    if not existed:
        _sync_directory(path.parent)
    return len(payload)


def append_jsonl(path: str | Path, row: dict, *,
                 lock_timeout: float | None = DEFAULT_LOCK_TIMEOUT_SEC) -> int:
    """Serialize and durably append one JSONL row under a process lock."""
    path = Path(path)
    # Serialize before taking the lock so a bad object cannot hold up writers.
    json.dumps(row, ensure_ascii=False)
    with append_lock(path, timeout=lock_timeout):
        return append_jsonl_unlocked(path, row)


def atomic_write_text(path: str | Path, text: str, *,
                      encoding: str = "utf-8") -> None:
    """Durably replace ``path`` using a unique same-directory temporary file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    tmp = Path(tmp_name)
    try:
        try:
            os.fchmod(fd, PRIVATE_FILE_MODE)
        except (AttributeError, OSError):
            pass
        with os.fdopen(fd, "w", encoding=encoding, newline="\n") as handle:
            fd = -1
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
        _set_private_permissions(path)
        _sync_directory(path.parent)
    except BaseException:
        if fd >= 0:
            os.close(fd)
        try:
            tmp.unlink()
        except OSError:
            pass
        raise


@dataclass(frozen=True)
class QuarantinedRow:
    """An invalid row excluded from replay while remaining in the source log."""

    line_number: int
    reason: str


@dataclass(frozen=True)
class ValidatedJsonl:
    rows: list[dict]
    quarantined: list[QuarantinedRow]


def read_validated_jsonl(
    path: str | Path,
    validate: Callable[[dict], str | None],
) -> ValidatedJsonl:
    """Read valid JSON-object rows and quarantine invalid rows in place.

    "In place" means invalid source bytes remain untouched in the append-only
    history but are excluded from replay and surfaced in metadata.
    """
    path = Path(path)
    try:
        lines = path.read_bytes().splitlines()
    except (FileNotFoundError, OSError):
        return ValidatedJsonl([], [])
    rows: list[dict] = []
    quarantined: list[QuarantinedRow] = []
    for line_number, raw in enumerate(lines, 1):
        if not raw.strip():
            continue
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            quarantined.append(QuarantinedRow(line_number, "invalid utf-8"))
            continue
        try:
            row = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            quarantined.append(QuarantinedRow(line_number, "invalid json"))
            continue
        if not isinstance(row, dict):
            quarantined.append(
                QuarantinedRow(line_number, "row is not an object"))
            continue
        try:
            reason = validate(row)
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            reason = f"validation failed: {type(exc).__name__}"
        if reason:
            quarantined.append(QuarantinedRow(line_number, reason))
            continue
        rows.append(row)
    return ValidatedJsonl(rows, quarantined)


def append_only_health(
    path: str | Path,
    *,
    warning_bytes: int,
    quarantined_rows: int = 0,
) -> dict:
    """Return non-destructive size/integrity metadata for health reporting."""
    path = Path(path)
    try:
        size = path.stat().st_size
    except OSError:
        size = 0
    threshold = max(0, int(warning_bytes))
    warning = threshold > 0 and size >= threshold
    return {
        "path": str(path),
        "size_bytes": size,
        "warning_bytes": threshold,
        "size_warning": warning,
        "quarantined_rows": max(0, int(quarantined_rows)),
        "append_only": True,
        "truncated": False,
    }
