"""Offline launcher regression tests: no server, network, or real pip calls."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


@unittest.skipUnless(shutil.which("bash") and os.name != "nt", "POSIX launcher")
class StartIsolationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "project with spaces"
        self.root.mkdir()
        shutil.copyfile(Path(__file__).resolve().parents[1] / "start.sh", self.root / "start.sh")
        self.bin = Path(self.temp.name) / "bin"
        self.bin.mkdir()
        (self.bin / "dirname").symlink_to(shutil.which("dirname"))
        self.log = Path(self.temp.name) / "calls.jsonl"
        self.stub = f"#!{sys.executable}\n" + r'''
import json, os, pathlib, sys
with open(os.environ["CALL_LOG"], "a") as stream:
    stream.write(json.dumps([sys.argv[0], *sys.argv[1:]]) + "\n")
if sys.argv[1:3] == ["-m", "venv"]:
    if os.environ.get("BOOTSTRAP_FAIL"):
        sys.exit(7)
    target = pathlib.Path(sys.argv[3]) / "bin" / "python"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(pathlib.Path(__file__).read_text())
    target.chmod(0o755)
elif sys.argv[1:2] == ["-c"]:
    sys.exit(0 if os.environ.get("DEPS_PRESENT") else 1)
elif sys.argv[1:3] == ["-m", "pip"]:
    sys.exit(8 if os.environ.get("INSTALL_FAIL") else 0)
'''
        self.write_python(self.bin / "python3")

    def write_python(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.stub, encoding="utf-8")
        path.chmod(0o755)

    def run_start(self, **options):
        env = {**os.environ, "PATH": str(self.bin), "CALL_LOG": str(self.log),
               "HOST": "127.0.0.1", "PORT": "8123"}
        for key in ("BOOTSTRAP_FAIL", "DEPS_PRESENT", "INSTALL_FAIL"):
            env.pop(key, None)
        env.update(options)
        result = subprocess.run([shutil.which("bash"), str(self.root / "start.sh")],
                                cwd=self.temp.name, env=env, capture_output=True,
                                text=True, timeout=15)
        calls = [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []
        return result, calls

    def test_fresh_checkout_installs_only_inside_project_venv(self):
        result, calls = self.run_start()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(any(c[1:3] == ["-m", "venv"] for c in calls), calls)
        installs = [c for c in calls if c[1:3] == ["-m", "pip"]]
        self.assertEqual(len(installs), 1)
        self.assertTrue(installs[0][0].endswith(".venv/bin/python"), installs)
        self.assertTrue((self.root / ".venv/bin/python").is_file())

    def test_existing_venv_is_reused_without_bootstrap_or_install(self):
        self.write_python(self.root / ".venv/bin/python")
        result, calls = self.run_start(DEPS_PRESENT="1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(any(c[1:3] in (["-m", "venv"], ["-m", "pip"]) for c in calls))
        self.assertTrue(all(c[0].endswith(".venv/bin/python") for c in calls))

    def test_install_failure_does_not_launch_server(self):
        self.write_python(self.root / ".venv/bin/python")
        result, calls = self.run_start(INSTALL_FAIL="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any(c[1:3] == ["-m", "uvicorn"] for c in calls))

    def test_failed_bootstrap_never_falls_back_to_global_install(self):
        result, calls = self.run_start(BOOTSTRAP_FAIL="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any(c[1:3] in (["-m", "pip"], ["-m", "uvicorn"]) for c in calls))

    def test_incomplete_venv_is_reported_without_overwriting_it(self):
        venv = self.root / ".venv"
        venv.mkdir()
        marker = venv / "keep.txt"
        marker.write_text("existing user files")
        result, calls = self.run_start()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(".venv", result.stderr)
        self.assertEqual(marker.read_text(), "existing user files")
        self.assertFalse(any(c[1:3] in (["-m", "pip"], ["-m", "venv"]) for c in calls))

    def test_host_port_and_foreign_working_directory_are_preserved(self):
        self.write_python(self.root / ".venv/bin/python")
        result, calls = self.run_start(DEPS_PRESENT="1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls[-1][1:], ["-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8123"])


if __name__ == "__main__":
    unittest.main()
