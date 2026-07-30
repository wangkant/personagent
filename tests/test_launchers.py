"""Cross-platform behavior checks for the repository launchers."""
from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class LauncherTests(unittest.TestCase):
    def _fake_python_modules(self, root: Path) -> Path:
        modules = root / "fake_modules"
        for name in ("fastapi", "dotenv", "httpx", "PIL", "ddgs", "uvicorn"):
            package = modules / name
            package.mkdir(parents=True)
            (package / "__init__.py").write_text("", encoding="utf-8")
        (modules / "uvicorn" / "__main__.py").write_text(
            "import json, os, sys\n"
            "from pathlib import Path\n"
            "Path(os.environ['LAUNCHER_CAPTURE']).write_text(\n"
            "    json.dumps({'cwd': os.getcwd(), 'argv': sys.argv[1:]}),\n"
            "    encoding='utf-8')\n",
            encoding="utf-8",
        )
        return modules

    def _run_powershell_launcher(self, host: str) -> tuple[dict, Path]:
        powershell = shutil.which("powershell") or shutil.which("pwsh")
        if not powershell:
            self.skipTest("PowerShell is not installed")

        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        base = Path(temp.name)
        repo = base / "repo with spaces"
        caller = base / "foreign cwd"
        repo.mkdir()
        caller.mkdir()
        shutil.copy2(ROOT / "start.ps1", repo / "start.ps1")
        (repo / "requirements.txt").write_text("", encoding="utf-8")
        modules = self._fake_python_modules(base)
        capture = base / "capture.json"
        env = os.environ.copy()
        env.update(
            {
                "HOST": host,
                "PORT": "8123",
                "PYTHONPATH": str(modules),
                "LAUNCHER_CAPTURE": str(capture),
            }
        )
        result = subprocess.run(
            [
                powershell,
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(repo / "start.ps1"),
            ],
            cwd=caller,
            env=env,
            text=True,
            capture_output=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(capture.is_file(), result.stdout + result.stderr)
        return json.loads(capture.read_text(encoding="utf-8")), repo

    def test_powershell_launcher_runs_from_repository_root(self) -> None:
        capture, repo = self._run_powershell_launcher("127.0.0.1")
        self.assertEqual(Path(capture["cwd"]).resolve(), repo.resolve())

    def test_powershell_launcher_honors_configured_host(self) -> None:
        capture, _ = self._run_powershell_launcher("127.0.0.2")
        self.assertEqual(
            capture["argv"],
            ["main:app", "--host", "127.0.0.2", "--port", "8123"],
        )

    @unittest.skipIf(os.name == "nt", "POSIX launcher behavior runs on Unix CI")
    def test_posix_launcher_is_executable_and_honors_configured_host(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp) / "repo with spaces"
            python = repo / ".venv" / "bin" / "python"
            python.parent.mkdir(parents=True)
            launcher = repo / "start.sh"
            shutil.copy2(ROOT / "start.sh", launcher)
            capture = repo / "capture.json"
            python.write_text(
                f"#!{sys.executable}\n"
                "import json, os, sys\n"
                "from pathlib import Path\n"
                "if sys.argv[1:3] == ['-m', 'uvicorn']:\n"
                "    Path(os.environ['LAUNCHER_CAPTURE']).write_text(\n"
                "        json.dumps({'cwd': os.getcwd(), 'argv': sys.argv[3:]}),\n"
                "        encoding='utf-8')\n",
                encoding="utf-8",
            )
            python.chmod(python.stat().st_mode | stat.S_IXUSR)
            env = os.environ.copy()
            env.update(
                {
                    "HOST": "127.0.0.2",
                    "PORT": "8123",
                    "LAUNCHER_CAPTURE": str(capture),
                }
            )
            result = subprocess.run(
                [str(launcher)],
                cwd=repo.parent,
                env=env,
                text=True,
                capture_output=True,
                timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            recorded = json.loads(capture.read_text(encoding="utf-8"))
            self.assertEqual(Path(recorded["cwd"]).resolve(), repo.resolve())
            self.assertEqual(
                recorded["argv"],
                ["main:app", "--host", "127.0.0.2", "--port", "8123"],
            )

    def test_vbs_launcher_quotes_editable_directories(self) -> None:
        source = (ROOT / "launch.vbs").read_text(encoding="ascii")
        self.assertIn('cd /d """ & NAPCAT_DIR & """', source)
        self.assertIn('cd /d """ & AGENT_DIR & """', source)


if __name__ == "__main__":
    unittest.main()
