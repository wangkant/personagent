"""Persistence primitive tests.

Run from the repository root:

    python tests/test_storage.py
"""
from __future__ import annotations

import json
import multiprocessing
import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    from persona_agent import paths, storage
except ImportError:
    paths = None
    storage = None

_failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {name}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        _failures.append(name)


def _append_worker(path: str, worker: int, count: int) -> None:
    from persona_agent.storage import append_jsonl

    for index in range(count):
        append_jsonl(Path(path), {"worker": worker, "index": index})


def test_runtime_instance_lock(tmp: Path) -> None:
    first = storage.RuntimeInstanceLock(tmp)
    second = storage.RuntimeInstanceLock(tmp)
    first.acquire()
    try:
        denied = False
        try:
            second.acquire()
        except storage.LockUnavailable:
            denied = True
        check("runtime lock rejects a second live instance", denied)
    finally:
        first.release()

    second.acquire()
    second.release()
    check("runtime lock is reusable after release", True)


def test_cross_process_append(tmp: Path) -> None:
    path = tmp / "events.jsonl"
    workers, per_worker = 4, 40
    processes = [
        multiprocessing.Process(
            target=_append_worker, args=(str(path), worker, per_worker))
        for worker in range(workers)
    ]
    for process in processes:
        process.start()
    for process in processes:
        process.join(20)
    check("append workers exit cleanly",
          all(process.exitcode == 0 for process in processes),
          str([process.exitcode for process in processes]))

    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    observed = {(row["worker"], row["index"]) for row in rows}
    expected = {
        (worker, index)
        for worker in range(workers)
        for index in range(per_worker)
    }
    check("cross-process appends preserve every complete JSON row",
          len(rows) == workers * per_worker and observed == expected,
          f"rows={len(rows)} unique={len(observed)}")


def test_atomic_write(tmp: Path) -> None:
    path = tmp / "state.json"
    storage.atomic_write_text(path, '{"version":1}\n')
    storage.atomic_write_text(path, '{"version":2}\n')
    check("atomic replacement publishes the complete new value",
          path.read_text(encoding="utf-8") == '{"version":2}\n')
    check("atomic replacement leaves no temporary files",
          list(tmp.glob(f".{path.name}.*.tmp")) == [],
          str(list(tmp.iterdir())))
    if os.name != "nt":
        mode = stat.S_IMODE(path.stat().st_mode)
        check("atomic replacement applies restrictive permissions",
              mode == 0o600, oct(mode))


def test_validated_jsonl_quarantines_in_place(tmp: Path) -> None:
    tmp.mkdir(parents=True, exist_ok=True)
    path = tmp / "records.jsonl"
    path.write_text(
        '{"schema":1,"value":"ok"}\n'
        'not json\n'
        '{"schema":99,"value":"future"}\n'
        '["not","an","object"]\n',
        encoding="utf-8",
    )

    def validate(row: dict) -> str | None:
        if row.get("schema") != 1:
            return "unsupported schema"
        if not isinstance(row.get("value"), str):
            return "value must be a string"
        return None

    result = storage.read_validated_jsonl(path, validate)
    check("validated JSONL returns only accepted rows",
          result.rows == [{"schema": 1, "value": "ok"}], str(result.rows))
    check("invalid rows are quarantined from replay with reasons",
          len(result.quarantined) == 3
          and {item.reason for item in result.quarantined}
          == {"invalid json", "unsupported schema", "row is not an object"},
          str(result.quarantined))
    check("quarantine does not rewrite or compact the source history",
          len(path.read_text(encoding="utf-8").splitlines()) == 4)


def test_runtime_dir_stays_under_agent_home(tmp: Path) -> None:
    old_root = paths.ROOT
    old_value = os.environ.get("AGENT_RUNTIME_DIR")
    try:
        paths.ROOT = tmp.resolve()
        os.environ["AGENT_RUNTIME_DIR"] = "state/runtime"
        check("relative runtime dir resolves under AGENT_HOME",
              paths.runtime_dir() == (tmp / "state" / "runtime").resolve())

        inside = (tmp / "absolute-runtime").resolve()
        os.environ["AGENT_RUNTIME_DIR"] = str(inside)
        check("absolute runtime dir under AGENT_HOME is accepted",
              paths.runtime_dir() == inside)

        os.environ["AGENT_RUNTIME_DIR"] = str((tmp.parent / "outside").resolve())
        rejected = False
        try:
            paths.runtime_dir()
        except ValueError:
            rejected = True
        check("absolute runtime dir outside AGENT_HOME is rejected", rejected)

        os.environ["AGENT_RUNTIME_DIR"] = "../escape"
        rejected = False
        try:
            paths.runtime_dir()
        except ValueError:
            rejected = True
        check("relative runtime traversal outside AGENT_HOME is rejected", rejected)

        os.environ["AGENT_RUNTIME_DIR"] = "runtime"
        rejected = False
        try:
            paths.resolve_runtime_state_file("../../outside.json")
        except ValueError:
            rejected = True
        check("relative state-file traversal outside runtime is rejected",
              rejected)
    finally:
        paths.ROOT = old_root
        if old_value is None:
            os.environ.pop("AGENT_RUNTIME_DIR", None)
        else:
            os.environ["AGENT_RUNTIME_DIR"] = old_value


def test_cli_tools_follow_runtime_dir() -> None:
    runtime_rel = "runtime/tool-contract-test"
    code = (
        "from pathlib import Path\n"
        "from tools import auto_reviewer as a\n"
        "from tools import bootstrap_from_history as b\n"
        "from tools import import_stickers_folder as i\n"
        f"expected=(Path({str(ROOT)!r})/{runtime_rel!r}).resolve()\n"
        "assert a.EVAL_FILE == expected/'eval.jsonl', a.EVAL_FILE\n"
        "assert a.CANDIDATES_FILE == expected/'candidates.jsonl', a.CANDIDATES_FILE\n"
        "assert b.STICKERS_JSON == expected/'stickers.json', b.STICKERS_JSON\n"
        "assert b.OWNER_PROFILE == expected/'owner_profile.json', b.OWNER_PROFILE\n"
        "assert i.STICKERS_JSON == expected/'stickers.json', i.STICKERS_JSON\n"
        "assert b.STICKERS_DIR == Path(" + repr(str(ROOT / "stickers" / "auto")) + ")\n"
    )
    env = os.environ.copy()
    env["AGENT_RUNTIME_DIR"] = runtime_rel
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
    )
    check(
        "CLI tools honor a non-default runtime directory",
        completed.returncode == 0,
        completed.stdout + completed.stderr,
    )


def test_cli_tools_migrate_legacy_state_when_run_first(tmp: Path) -> None:
    tmp.mkdir(parents=True, exist_ok=True)
    legacy = {
        "eval.jsonl": '{"score":2}\n',
        "candidates.jsonl": '{"candidate":"old"}\n',
        "stickers.json": '{"old.png":{"md5":"abc"}}',
        "owner_profile.json": '{"total_msgs":42}',
    }
    for name, content in legacy.items():
        (tmp / name).write_text(content, encoding="utf-8")
    runtime_rel = "state/tool-first"
    code = (
        "from pathlib import Path\n"
        "from tools import auto_reviewer as a\n"
        "from tools import bootstrap_from_history as b\n"
        "from tools import import_stickers_folder as i\n"
        f"root=Path({str(tmp)!r})\n"
        f"expected=(root/{runtime_rel!r}).resolve()\n"
        "checks={\n"
        " a.EVAL_FILE: root/'eval.jsonl',\n"
        " a.CANDIDATES_FILE: root/'candidates.jsonl',\n"
        " b.STICKERS_JSON: root/'stickers.json',\n"
        " b.OWNER_PROFILE: root/'owner_profile.json',\n"
        " i.STICKERS_JSON: root/'stickers.json',\n"
        "}\n"
        "assert all(path.parent == expected for path in checks), checks\n"
        "mismatches=[(str(path), path.read_text(encoding='utf-8'), "
        "old.read_text(encoding='utf-8')) "
        "for path, old in checks.items() "
        "if path.read_text(encoding='utf-8') "
        "!= old.read_text(encoding='utf-8')]\n"
        "assert not mismatches, mismatches\n"
    )
    env = os.environ.copy()
    env["AGENT_HOME"] = str(tmp)
    env["AGENT_RUNTIME_DIR"] = runtime_rel
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
    )
    check(
        "CLI-first startup migrates legacy state before loading it",
        completed.returncode == 0,
        completed.stdout + completed.stderr,
    )


def test_appended_rows_are_byte_exact(tmp: Path) -> None:
    """Appends must land byte-for-byte, with LF endings on every platform.

    os.open without O_BINARY leaves the descriptor in text mode on Windows, so
    every newline was written as CRLF: the file gained endings no other writer
    here produces, and append_jsonl_unlocked's returned length was one byte
    short per row. Asserted with read_bytes rather than splitlines, because
    splitlines treats CRLF as a line break and hides the very corruption under
    test."""
    tmp.mkdir(parents=True, exist_ok=True)
    path = tmp / "rows.jsonl"
    lf = chr(10).encode()
    cr = chr(13).encode()
    written = storage.append_jsonl(path, {"x": 1})
    raw = path.read_bytes()
    check("append: row is byte-exact LF", raw == b'{"x":1}' + lf, repr(raw))
    check("append: returned length matches what hit disk",
          written == len(raw), f"{written} vs {len(raw)}")
    storage.append_jsonl(path, {"y": 2})
    raw2 = path.read_bytes()
    check("append: no CR anywhere in the file", cr not in raw2, repr(raw2))
    check("append: second row appended cleanly",
          raw2 == b'{"x":1}' + lf + b'{"y":2}' + lf, repr(raw2))


def main() -> int:
    if storage is None or paths is None:
        check("storage module is importable", False,
              "persona_agent.storage does not exist")
    else:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            test_runtime_instance_lock(tmp / "instance")
            test_cross_process_append(tmp / "append")
            test_atomic_write(tmp / "atomic")
            test_appended_rows_are_byte_exact(tmp / "bytes")
            test_validated_jsonl_quarantines_in_place(tmp / "validation")
            test_runtime_dir_stays_under_agent_home(tmp / "home")
            test_cli_tools_follow_runtime_dir()
            test_cli_tools_migrate_legacy_state_when_run_first(
                tmp / "legacy-home")
    if _failures:
        print(f"\n{len(_failures)} test(s) failed")
        return 1
    print("\nall tests passed")
    return 0


if __name__ == "__main__":
    multiprocessing.freeze_support()
    raise SystemExit(main())
