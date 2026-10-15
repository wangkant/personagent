"""Run the installed welcome page, save a key, chat, and exit, using only localhost."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import queue
import re
import shutil
import subprocess
import tempfile
import threading
import time
from urllib.parse import parse_qs, urlsplit
import urllib.request
from http.server import ThreadingHTTPServer

from package_smoke import FakeModel, REPLY, _env


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--personagent", required=True)
    args = parser.parse_args(argv)
    model = ThreadingHTTPServer(("127.0.0.1", 0), FakeModel)
    threading.Thread(target=model.serve_forever, daemon=True).start()
    process = None
    try:
        with tempfile.TemporaryDirectory(prefix="personagent-welcome-") as temporary:
            command = [shutil.which(args.personagent) or os.path.abspath(args.personagent), "--home", str(Path(temporary) / "home"),
                       "start", "--no-browser"]
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                       text=True, encoding="utf-8", errors="replace", env=_env())
            lines = queue.Queue()
            def read():
                for line in process.stdout:
                    lines.put(line)
            threading.Thread(target=read, daemon=True).start()
            deadline = time.monotonic() + 30
            url = ""
            while time.monotonic() < deadline:
                try:
                    line = lines.get(timeout=1)
                except queue.Empty:
                    if process.poll() is not None:
                        break
                    continue
                found = re.search(r"http://127\.0\.0\.1:\d+/#token=\S+", line)
                if found:
                    url = found.group()
                    break
            if not url:
                raise RuntimeError("welcome page did not print its local link")
            parsed = urlsplit(url)
            base = f"{parsed.scheme}://{parsed.netloc}"
            token = parse_qs(parsed.fragment)["token"][0]
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

            def request(path, payload=None):
                data = None if payload is None else json.dumps(payload).encode()
                req = urllib.request.Request(base + path, data=data, headers={
                    "Content-Type": "application/json", "X-Personagent-Setup-Token": token})
                with opener.open(req, timeout=45) as response:
                    return json.loads(response.read())

            # The link is printed just before the server starts accepting.
            while True:
                try:
                    state = request("/api/state")
                    break
                except OSError:
                    if time.monotonic() > deadline:
                        raise
                    time.sleep(0.1)
            assert not state["configured"]
            base_model = f"http://127.0.0.1:{model.server_address[1]}/v1"
            result = request("/api/config", {"provider": "other", "apiKey": "fake-local-key",
                                            "baseUrl": base_model, "model": "fake-model", "lang": "en"})
            assert result["configured"] and "fake-local-key" not in json.dumps(result)
            reply = request("/api/chat", {"text": "hello"})
            assert reply["reply"] == REPLY, reply
            # A second launch reuses the existing page rather than a second service.
            second = subprocess.run(command, capture_output=True, text=True, encoding="utf-8",
                                    errors="replace", env=_env(), timeout=15)
            assert second.returncode == 0 and url in second.stdout
            assert request("/api/exit", {}) == {"ok": True}
            assert process.wait(timeout=20) == 0
            print("PASS: installed welcome page → key setup → real character chat → reuse → clean exit")
            return 0
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            process.wait(timeout=10)
        model.shutdown()
        model.server_close()


if __name__ == "__main__":
    raise SystemExit(main())
