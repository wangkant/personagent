"""Update personagent after it has quit, then open it again.

Run as a file, from a copy outside the package, with one argument: a JSON plan
{"pid", "commands", "relaunch", "log", "result"}. Standard library only: the
packages around it are what the commands replace.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time

WAIT_S = 120
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def gone(pid: int, seconds: float) -> bool:
    """Wait for a process to end."""
    if os.name == "nt":
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.OpenProcess.restype = ctypes.c_void_p
        kernel32.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
        handle = kernel32.OpenProcess(0x00100000, False, pid)  # SYNCHRONIZE
        if not handle:
            return True
        try:
            return kernel32.WaitForSingleObject(handle, int(seconds * 1000)) == 0
        finally:
            kernel32.CloseHandle(handle)
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        except OSError:
            pass
        if _zombie(pid):
            return True
        time.sleep(0.3)
    return False


def _zombie(pid: int) -> bool:
    """Ended, but its parent has not collected it yet (Linux): it holds no file any more."""
    try:
        with open(f"/proc/{pid}/stat", encoding="utf-8", errors="replace") as stat:
            return stat.read().rpartition(")")[2].split()[:1] == ["Z"]
    except OSError:
        return False


def reopen(command: list[str]) -> None:
    # No streams handed over: pythonw then has none, and logs to its own file.
    subprocess.Popen(command, close_fds=True,
                     creationflags=NO_WINDOW | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))


def main(argv: list[str]) -> int:
    with open(argv[0], encoding="utf-8") as source:
        plan = json.load(source)
    code, failed = 0, ""
    with open(plan["log"], "w", encoding="utf-8", errors="replace") as log:
        if not gone(int(plan["pid"]), WAIT_S):
            code, failed = 1, "personagent did not quit"
            log.write(failed + "\n")
        for command in plan["commands"] if not code else ():
            log.write("> " + " ".join(command) + "\n")
            log.flush()
            try:
                code = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT,
                                      stdin=subprocess.DEVNULL, creationflags=NO_WINDOW).returncode
            except OSError as error:
                code = 1
                log.write(f"{error}\n")
            if code:
                failed = " ".join(command)
                break
    with open(plan["result"], "w", encoding="utf-8") as result:
        json.dump({"ok": not code, "failed": failed, "from": plan.get("from", ""), "at": time.time()}, result)
    # Whatever happened, the person gets their app back.
    reopen(plan["relaunch"])
    return code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
