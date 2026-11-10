"""The desk panel: desktop icon, start at sign-in, where the data is, backups,
and starting over."""
from __future__ import annotations

import asyncio
import contextlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

from dotenv import dotenv_values
from fastapi import Request

from .. import __version__, langs, shortcut
from .. import connections as conn
from .. import setup_wizard as sw
from ..astrbot_install import AstrBotInstallation
from ..direct import base as direct_base
from ..storage import LockUnavailable, RuntimeInstanceLock

ERRORS: frozenset[str] = frozenset({
    "desk_unsupported", "desk_uvx", "desk_shortcut_failed", "desk_invalid_place",
    "desk_missing", "desk_open_failed", "desk_backup_failed", "desk_invalid_backup",
    "desk_restore_failed", "desk_restore_undone", "desk_runtime_elsewhere", "desk_reset_failed",
    "desk_service_elsewhere"})

# Places the page may open; nothing from a request is ever a path.
PLACES = ("home", "persona", "logs", "memory", "stickers", "data")
TARGETS = ("desktop", "documents", "backups")
# "desktop;documents" in place of the real folders, for tests and trial runs.
DIRS_ENV = "PERSONAGENT_USER_DIRS"
PREFIX = "personagent-backup-"
BACKUP_NAME = re.compile(r"personagent-backup-[0-9A-Za-z_-]{1,64}\.zip")
MANIFEST = "personagent-backup.json"
# A backup's own layout; runtime/ and stickers/ map to wherever this home keeps them.
SINGLE_FILES = (".env", "persona.txt", "persona.card.json", "platforms/direct.json",
                "platforms/astrbot/data/cmd_config.json")
# Rebuilt by the service, or only meaningful to the process that wrote it.
SKIP_NAMES = {"dashboard.token", "gateway_nonces.json", "__pycache__"}
SKIP_SUFFIXES = (".lock", ".tmp", ".pyc", ".part")
# What "forget" leaves in the runtime folder: the sticker library is not memory.
KEEP_ON_FORGET = {"stickers.json", "unknown_stickers.jsonl", "dashboard.token"}
SERVICES = ("agent", "astrbot", "direct")
MAX_MEMBERS = 50_000
MAX_UNPACKED = 4 * 1024 ** 3


def open_path(path: Path) -> None:
    """Show `path` in the system's file manager or default app."""
    if os.name == "nt":
        os.startfile(str(path))  # type: ignore[attr-defined]
    else:
        subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", str(path)],
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _known_folder(kind: str) -> Path | None:
    override = os.environ.get(DIRS_ENV, "").strip()
    if override:
        parts = dict(zip(("desktop", "documents"), override.split(os.pathsep)))
        return Path(parts[kind]) if parts.get(kind) else None
    if os.name == "nt":
        import ctypes

        # CSIDL_DESKTOPDIRECTORY, CSIDL_PERSONAL: right even when OneDrive moved them.
        buffer = ctypes.create_unicode_buffer(260)
        csidl = {"desktop": 0x10, "documents": 0x05}[kind]
        if ctypes.windll.shell32.SHGetFolderPathW(None, csidl, None, 0, buffer) == 0 and buffer.value:
            return Path(buffer.value)
        return None
    path = Path.home() / ("Desktop" if kind == "desktop" else "Documents")
    return path if path.is_dir() else None


def _size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


class Desk:
    def __init__(self, workspace, closers: list | None = None):
        self.workspace = workspace
        self.home: Path = workspace.home
        # The panels' own children (the practice group), stopped with the services.
        self.closers = closers if closers is not None else []

    # ---- where things are

    def runtime(self) -> Path:
        # Read the way the service's own process reads it: .env over this process.
        configured = dotenv_values(self.home / ".env").get("AGENT_RUNTIME_DIR")
        if configured is None:
            configured = os.environ.get("AGENT_RUNTIME_DIR", "")
        path = Path(str(configured or "").strip() or "runtime").expanduser()
        path = (path if path.is_absolute() else self.home / path).resolve()
        if path == self.home or not path.is_relative_to(self.home):
            raise ValueError("desk_runtime_elsewhere")
        return path

    def _roots(self) -> dict[str, Path]:
        return {"data": self.home / "data", "runtime": self.runtime(), "stickers": self.home / "stickers"}

    def place(self, name: str) -> Path:
        if name not in PLACES:
            raise ValueError("desk_invalid_place")
        if name == "memory":
            return self.runtime()
        return {"home": self.home, "persona": self.home / "persona.txt",
                "logs": self.home / "runtime" / "desktop", "stickers": self.home / "stickers",
                "data": self.home / "data"}[name]

    def target(self, name: str) -> Path | None:
        if name not in TARGETS:
            raise ValueError("desk_invalid_place")
        return self.home / "backups" if name == "backups" else _known_folder(name)

    def overview(self) -> dict:
        places = []
        for name in PLACES:
            try:
                places.append({"id": name, "exists": self.place(name).exists()})
            except ValueError:
                continue
        targets = [{"id": name, "path": str(path)} for name in TARGETS
                   if (path := self.target(name)) is not None]
        return {"home": str(self.home), "places": places, "targets": targets, "backups": self.backups()}

    def open(self, name: str) -> dict:
        path = self.place(name)
        if name in ("logs", "stickers", "data", "memory"):
            # A folder the person is about to put files into may not exist yet.
            path.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            raise ValueError("desk_missing")
        try:
            open_path(path)
        except OSError:
            raise ValueError("desk_open_failed") from None
        return {"ok": True}

    # ---- shortcuts

    def shortcuts(self) -> dict:
        if not shortcut.WINDOWS:
            return {"supported": False, "uvx": False, "icon": "off", "login": "off"}
        try:
            found = shortcut.status(self.home)
        except (RuntimeError, ValueError):
            raise ValueError("desk_shortcut_failed") from None
        icon = [found[k] for k in shortcut.ICON]
        return {"supported": True, "uvx": langs.under_uvx(),
                "icon": "on" if all(s == "on" for s in icon) else
                        "off" if all(s == "off" for s in icon) else "other",
                "login": found["startup"]}

    def set_shortcut(self, which: str, on: bool) -> dict:
        if which not in ("icon", "login"):
            raise ValueError("desk_invalid_place")
        if not shortcut.WINDOWS:
            raise ValueError("desk_unsupported")
        if on and langs.under_uvx():
            raise ValueError("desk_uvx")
        kinds = shortcut.ICON if which == "icon" else shortcut.LOGIN
        try:
            failed = shortcut.run(shortcut.script(self.home, remove=not on, kinds=kinds))
        except ValueError:
            failed = "redirected folders"
        if failed:
            raise ValueError("desk_shortcut_failed")
        return self.shortcuts()

    # ---- backups

    def _busy(self) -> bool:
        future = self.workspace._future
        return future is not None and not future.done()

    def _members(self) -> list[tuple[Path, str]]:
        """(file on disk, name in the zip) for everything a backup holds."""
        found: list[tuple[Path, str]] = []
        for name in SINGLE_FILES:
            path = self.home / name
            if path.is_file():
                found.append((path, name))
        logs = (self.home / "runtime" / "desktop").resolve()
        for label, root in self._roots().items():
            if not root.is_dir():
                continue
            for path in sorted(root.rglob("*")):
                if not path.is_file() or path.is_symlink():
                    continue
                relative = path.relative_to(root)
                if (path.resolve().is_relative_to(logs) or SKIP_NAMES & set(relative.parts)
                        or path.name.endswith(SKIP_SUFFIXES)):
                    continue
                # The practice room is a throwaway copy.
                if label == "runtime" and relative.parts[0] == "trial":
                    continue
                found.append((path, f"{label}/{relative.as_posix()}"))
        return found

    def _write_backup(self, folder: Path, tag: str = "") -> Path:
        stamp = time.strftime("%Y%m%d-%H%M%S")
        path, n = folder / f"{PREFIX}{stamp}{tag}.zip", 1
        while path.exists():
            n += 1
            path = folder / f"{PREFIX}{stamp}{tag}-{n}.zip"
        partial = path.with_suffix(".zip.part")
        try:
            folder.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(partial, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.writestr(MANIFEST, json.dumps({"version": __version__, "created": int(time.time())}))
                for source, member in self._members():
                    try:
                        archive.write(source, member)
                    except FileNotFoundError:
                        # Replaced mid-walk by an atomic write; nothing to copy.
                        continue
            partial.replace(path)
        except OSError:
            partial.unlink(missing_ok=True)
            raise ValueError("desk_backup_failed") from None
        return path

    def backup(self, to: str) -> dict:
        folder = self.target(to)
        if folder is None:
            raise ValueError("desk_missing")
        path = self._write_backup(folder)
        return {"path": str(path), "name": path.name, "size": _size(path), "backups": self.backups()}

    def backups(self) -> list[dict]:
        found = []
        for where in TARGETS:
            folder = self.target(where)
            if folder is None or not folder.is_dir():
                continue
            for path in folder.glob(f"{PREFIX}*.zip"):
                if BACKUP_NAME.fullmatch(path.name) and path.is_file():
                    found.append({"place": where, "name": path.name, "size": _size(path),
                                  "when": int(path.stat().st_mtime)})
        return sorted(found, key=lambda item: -item["when"])[:20]

    def _destination(self, member: str) -> Path | None:
        """Where a member of a backup goes in this home; None if it may not."""
        if "\\" in member or member.startswith("/") or ":" in member:
            return None
        parts = member.split("/")
        if any(p in ("", ".", "..") for p in parts):
            return None
        if member in SINGLE_FILES:
            return self.home / member
        roots = self._roots()
        if parts[0] not in roots or len(parts) < 2:
            return None
        root = roots[parts[0]].resolve()
        path = root.joinpath(*parts[1:]).resolve()
        # Logs and the app's own records are never in a backup.
        if path.is_relative_to((self.home / "runtime" / "desktop").resolve()):
            return None
        return path if path.is_relative_to(root) and path != root else None

    def _check(self, path: Path) -> list[tuple[zipfile.ZipInfo, Path]]:
        try:
            with zipfile.ZipFile(path) as archive:
                infos = archive.infolist()
        except (OSError, zipfile.BadZipFile):
            raise ValueError("desk_invalid_backup") from None
        if (MANIFEST not in {i.filename for i in infos} or len(infos) > MAX_MEMBERS
                or sum(i.file_size for i in infos) > MAX_UNPACKED):
            raise ValueError("desk_invalid_backup")
        plan = []
        for info in infos:
            if info.is_dir() or info.filename == MANIFEST:
                continue
            target = self._destination(info.filename)
            if target is None:
                raise ValueError("desk_invalid_backup")
            plan.append((info, target))
        return plan

    def _stop(self) -> set[str]:
        """Stop the panels' children and every service before files change;
        the services that were running."""
        services = self.workspace.services
        was = {name for name in SERVICES if services.running(name)}
        for stop in list(self.closers):
            try:
                stop()
            except Exception:
                pass
        services.close()
        return was

    def _start_again(self, was: set[str]) -> None:
        """Bring back exactly the services that ran before, in the background."""
        if not was or not self.workspace.config().get("LLM_API_KEY"):
            return

        def start() -> None:
            services = self.workspace.services
            for name in SERVICES:
                if name not in was:
                    continue
                try:
                    if name == "agent":
                        services.start_agent()
                    elif name == "astrbot":
                        if conn.connected(AstrBotInstallation(self.home).root / "data"):
                            self.workspace._connect_plugin()
                            services.start_astrbot()
                    else:
                        services.start_direct()
                except Exception:
                    continue  # the page shows what is not running
        try:
            self.workspace._future = self.workspace.worker.submit(start)
        except RuntimeError:
            pass  # the app is closing

    @contextlib.contextmanager
    def _held(self):
        # Held while files change: a service started elsewhere, or starting now, cannot load them.
        lock = RuntimeInstanceLock(self.home)
        try:
            lock.acquire()
        except LockUnavailable:
            raise ValueError("desk_service_elsewhere") from None
        try:
            yield
        finally:
            lock.release()

    def _while_stopped(self, tag: str, work, *, restart: bool = True) -> Path:
        """Stop everything, save a safety backup, run work(runtime, safety); the backup's path.
        What ran is started again afterwards, and always after a failure."""
        runtime = self.runtime()  # before anything stops or is deleted
        with self.workspace._lock:
            if self._busy():
                raise ValueError("busy")
            was = self._stop()
            done = False
            try:
                with self._held():
                    safety = self._write_backup(self.home / "backups", tag)
                    work(runtime, safety)
                done = True
                self.workspace.reset_chat()
            finally:
                if restart or not done:
                    self._start_again(was)
        return safety

    def _clear_runtime(self, runtime: Path, keep: set[str]) -> None:
        logs = (self.home / "runtime" / "desktop").resolve()
        if not runtime.is_dir():
            return
        for path in runtime.iterdir():
            if path.resolve() == logs or path.name in keep:
                continue
            if path.is_dir() and not path.is_symlink():
                shutil.rmtree(path)
            else:
                path.unlink()

    def _unpack(self, path: Path, plan, runtime: Path) -> None:
        self._clear_runtime(runtime, keep=set())
        if (self.home / "stickers").is_dir():
            shutil.rmtree(self.home / "stickers")
        with zipfile.ZipFile(path) as archive:
            for info, target in plan:
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as source, open(target, "wb") as out:
                    shutil.copyfileobj(source, out)

    def restore(self, place: str, name: str) -> dict:
        folder = self.target(place) if place in TARGETS else None
        if folder is None or not BACKUP_NAME.fullmatch(name):
            raise ValueError("desk_invalid_backup")
        path = folder / name
        if not path.is_file():
            raise ValueError("desk_missing")
        plan = self._check(path)

        def work(runtime: Path, safety: Path) -> None:
            # Planned now: the restored .env may name another runtime folder.
            back = self._check(safety)
            try:
                self._unpack(path, plan, runtime)
            except (OSError, zipfile.BadZipFile):
                try:
                    self._unpack(safety, back, runtime)
                except (OSError, zipfile.BadZipFile):
                    raise ValueError("desk_restore_failed") from None
                raise ValueError("desk_restore_undone") from None
        safety = self._while_stopped("-before-restore", work)
        return {"files": len(plan), "safety": str(safety), "backups": self.backups()}

    # ---- starting over

    def forget(self) -> dict:
        def work(runtime: Path, safety: Path) -> None:
            try:
                self._clear_runtime(runtime, keep=KEEP_ON_FORGET)
            except OSError:
                raise ValueError("desk_reset_failed") from None
        safety = self._while_stopped("-before-forget", work)
        return {"safety": str(safety), "backups": self.backups()}

    def reset(self) -> dict:
        def work(runtime: Path, safety: Path) -> None:
            try:
                data = AstrBotInstallation(self.home).root / "data"
                for kind in conn.connected(data):
                    conn.remove_entry(data, kind)
                    sw.write_astrbot_config(data, conn.scope(sw.read_astrbot_config(data), kind, allow=False))
                direct_base.credentials_path(self.home).unlink(missing_ok=True)
                direct_base.status_path(self.home).unlink(missing_ok=True)
                for name in (".env", "persona.txt", "persona.card.json"):
                    (self.home / name).unlink(missing_ok=True)
                self._clear_runtime(runtime, keep=set())
            except (OSError, ValueError):
                raise ValueError("desk_reset_failed") from None
        # Nothing is set up afterwards, so nothing starts again.
        safety = self._while_stopped("-before-reset", work, restart=False)
        return {"safety": str(safety), "backups": self.backups()}


def mount(app, workspace, body) -> None:
    desk = Desk(workspace, app.state.closers)

    @app.get("/api/desk")
    async def overview():
        return await asyncio.to_thread(desk.overview)

    @app.get("/api/desk/shortcuts")
    async def shortcuts():
        return await asyncio.to_thread(desk.shortcuts)

    @app.post("/api/desk/shortcut")
    async def set_shortcut(request: Request):
        payload = await body(request)
        return await asyncio.to_thread(desk.set_shortcut, str(payload.get("which") or ""),
                                       payload.get("on") is True)

    @app.post("/api/desk/open")
    async def open_place(request: Request):
        payload = await body(request)
        return await asyncio.to_thread(desk.open, str(payload.get("place") or ""))

    @app.post("/api/desk/backup")
    async def backup(request: Request):
        payload = await body(request)
        return await asyncio.to_thread(desk.backup, str(payload.get("to") or ""))

    @app.post("/api/desk/restore")
    async def restore(request: Request):
        payload = await body(request)
        # The chat lock keeps the page's chat from starting the character mid-way.
        async with workspace._chat_lock:
            return await asyncio.to_thread(desk.restore, str(payload.get("place") or ""),
                                           str(payload.get("name") or ""))

    @app.post("/api/desk/forget")
    async def forget(request: Request):
        await body(request)
        async with workspace._chat_lock:
            return await asyncio.to_thread(desk.forget)

    @app.post("/api/desk/reset")
    async def reset(request: Request):
        await body(request)
        async with workspace._chat_lock:
            return await asyncio.to_thread(desk.reset)
