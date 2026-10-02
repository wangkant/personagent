"""Smoke-test an installed `personagent` command end to end, offline.

A stand-in OpenAI-compatible server answers every model call, so nothing
leaves this machine. Steps: --version, init --no-input, chat, run + GET
/health, doctor --json, each in a throwaway home.

    python tools/package_smoke.py --personagent .venv/bin/personagent --version 1.0.0
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPLY = "hey there"
STEPS = ("version", "init", "chat", "run", "doctor")
# Settings a developer's shell may carry that would override the test home's .env.
_SCRUBBED_PREFIXES = ("LLM_", "AGENT_", "PERSONA_", "CONNECTOR_", "SERVER_", "QQ_",
                      "ADMIN_", "EMBEDDING_", "VISION_", "TAVILY_", "BENCH_",
                      "DASHBOARD_", "EVAL_")


class FakeModel(BaseHTTPRequestHandler):
    calls: list[str] = []

    def log_message(self, *args) -> None:
        pass

    def _send(self, body: dict) -> None:
        data = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        self.calls.append(self.path)
        self._send({"object": "list", "data": [{"id": "fake-model", "object": "model"}]})

    def do_POST(self) -> None:
        self.rfile.read(int(self.headers.get("Content-Length") or 0))
        self.calls.append(self.path)
        if self.path.endswith("/embeddings"):
            self._send({"data": [{"embedding": [0.1] * 8, "index": 0}]})
            return
        content = json.dumps({"reasoning": "", "intent": "chat", "reply": REPLY, "mem": ""})
        self._send({"choices": [{"index": 0, "finish_reason": "stop",
                                 "message": {"role": "assistant", "content": content}}],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1}})


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _env() -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith(_SCRUBBED_PREFIXES)}
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def _set_env_values(path: Path, values: dict) -> None:
    lines = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []
    kept = [ln for ln in lines if ln.split("=", 1)[0].strip() not in values]
    kept += [f"{key}={value}" for key, value in values.items()]
    path.write_text("\n".join(kept) + "\n", encoding="utf-8")


def _run(cmd: list[str], *, stdin: str = "", timeout: int = 120) -> subprocess.CompletedProcess:
    print("$", " ".join(cmd), flush=True)
    result = subprocess.run(cmd, input=stdin, capture_output=True, text=True,
                            encoding="utf-8", errors="replace", env=_env(),
                            timeout=timeout)
    output = (result.stdout + result.stderr).strip()
    if output:
        print("  " + output.replace("\n", "\n  ")[:4000])
    return result


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--personagent", default=shutil.which("personagent") or "",
                   help="the installed command (default: personagent on PATH)")
    p.add_argument("--version", dest="expect_version", default="",
                   help="the version `personagent --version` must print")
    p.add_argument("--skip", action="append", default=[], choices=STEPS,
                   help="leave out a step (repeatable)")
    args = p.parse_args(argv)
    if not args.personagent:
        p.error("no personagent command found; pass --personagent")
    exe = shutil.which(args.personagent) or args.personagent
    failures: list[str] = []

    def expect(step: str, ok: bool, detail: str = "") -> None:
        print(f"[{'PASS' if ok else 'FAIL'}] {step}" + (f": {detail}" if detail and not ok else ""))
        if not ok:
            failures.append(step)

    server = ThreadingHTTPServer(("127.0.0.1", _free_port()), FakeModel)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    model_url = f"http://127.0.0.1:{server.server_address[1]}/v1"
    work = Path(tempfile.mkdtemp(prefix="personagent-smoke-"))
    home = work / "home"
    served = None
    try:
        if "version" not in args.skip:
            r = _run([exe, "--version"])
            want = f"personagent {args.expect_version}".strip()
            expect("version", r.returncode == 0 and r.stdout.strip().startswith(want),
                   r.stdout.strip())

        if "init" not in args.skip:
            r = _run([exe, "--home", str(home), "init", "--no-input"])
            expect("init --no-input", r.returncode == 0 and (home / ".env").is_file(),
                   f"exit {r.returncode}")
        home.mkdir(parents=True, exist_ok=True)
        _set_env_values(home / ".env", {
            "LLM_BASE_URL": model_url, "LLM_API_KEY": "sk-smoke",
            "LLM_MODEL": "fake-model", "PERSONA_NAME": "Nova", "AGENT_LANG": "en",
            "QQ_BOT_ID": "", "QQ_ONEBOT_URL": "", "EMBEDDING_MODEL": "",
            "VISION_MODEL": ""})

        if "chat" not in args.skip:
            before = len(FakeModel.calls)
            r = _run([exe, "--home", str(home), "chat"],
                     stdin="Nova, are you there?\n/quit\n")
            expect("chat", r.returncode == 0 and REPLY in r.stdout
                   and len(FakeModel.calls) > before, f"exit {r.returncode}")

        if "run" not in args.skip:
            port = _free_port()
            cmd = [exe, "--home", str(home), "run", "--port", str(port)]
            print("$", " ".join(cmd), flush=True)
            log = open(work / "run.log", "w+", encoding="utf-8", errors="replace")
            served = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, env=_env())
            health = None
            deadline = time.time() + 90
            while time.time() < deadline and served.poll() is None:
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{port}/health",
                                                timeout=2) as resp:
                        health = json.load(resp)
                    break
                except OSError:
                    time.sleep(0.5)
            expect("run + GET /health",
                   bool(health) and health.get("status") == "ok"
                   and health.get("agent_enabled") is True, repr(health))
            served.terminate()
            served.wait(timeout=30)
            served = None
            log.seek(0)
            print("  " + log.read().strip().replace("\n", "\n  ")[:4000])
            log.close()

        if "doctor" not in args.skip:
            r = _run([exe, "--home", str(home), "doctor", "--json"])
            try:
                report = json.loads(r.stdout)
            except json.JSONDecodeError:
                report = {}
            chat_probes = [s for s in report.get("services", [])
                           if s.get("name", "").startswith(("Private chat", "Primary chat"))]
            expect("doctor --json", len(chat_probes) == 2
                   and all(s.get("ok") is True for s in chat_probes),
                   repr(chat_probes or r.stdout[:300]))
    finally:
        if served is not None:
            served.kill()
            served.wait(timeout=30)
        server.shutdown()
        server.server_close()
        shutil.rmtree(work, ignore_errors=True)
    print("smoke:", "FAILED " + ", ".join(failures) if failures else "all steps passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
