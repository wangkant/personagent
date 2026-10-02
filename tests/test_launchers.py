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
        (root / "repo with spaces" / "main.py").write_text(
            "import json, os, sys\n"
            "from pathlib import Path\n"
            "Path(os.environ['LAUNCHER_CAPTURE']).write_text(\n"
            "    json.dumps({'cwd': os.getcwd(), 'host': os.getenv('SERVER_HOST'), 'port': os.getenv('SERVER_PORT')}),\n"
            "    encoding='utf-8')\n",
            encoding="utf-8",
        )
        return modules

    def _windows_repo(self, *, configured: bool = True) -> tuple[Path, Path, dict]:
        """A copy of the Windows launchers in a path with spaces, plus the env
        that makes its dependency probe pass without installing anything."""
        if not (shutil.which("powershell") or shutil.which("pwsh")):
            self.skipTest("PowerShell is not installed")
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        base = Path(temp.name)
        repo = base / "repo with spaces"
        caller = base / "foreign cwd"
        repo.mkdir()
        caller.mkdir()
        shutil.copy2(ROOT / "start.ps1", repo / "start.ps1")
        shutil.copy2(ROOT / "start.bat", repo / "start.bat")
        (repo / "requirements.txt").write_text("", encoding="utf-8")
        if configured:
            (repo / ".env").write_text("LLM_API_KEY=sk-test\n", encoding="utf-8")
        modules = self._fake_python_modules(base)
        env = {k: v for k, v in os.environ.items() if k != "LLM_API_KEY"}
        env.update({"PYTHONPATH": str(modules),
                    "LAUNCHER_CAPTURE": str(base / "capture.json")})
        return repo, caller, env

    def _run(self, cmd: list[str], *, cwd: Path, env: dict) -> subprocess.CompletedProcess:
        # A GBK console must not break the reader: decode leniently.
        return subprocess.run(cmd, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                              capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=120)

    def _powershell(self, repo: Path) -> list[str]:
        powershell = shutil.which("powershell") or shutil.which("pwsh")
        return [powershell, "-NoLogo", "-NoProfile", "-NonInteractive",
                "-ExecutionPolicy", "Bypass", "-File", str(repo / "start.ps1")]

    def _run_powershell_launcher(self, host: str) -> tuple[dict, Path]:
        repo, caller, env = self._windows_repo()
        env.update({"SERVER_HOST": host, "SERVER_PORT": "8123"})
        result = self._run(self._powershell(repo), cwd=caller, env=env)
        capture = Path(env["LAUNCHER_CAPTURE"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(capture.is_file(), result.stdout + result.stderr)
        return json.loads(capture.read_text(encoding="utf-8")), repo

    def test_powershell_launcher_points_an_unconfigured_checkout_at_setup(self) -> None:
        repo, caller, env = self._windows_repo(configured=False)
        result = self._run(self._powershell(repo), cwd=caller, env=env)
        combined = result.stdout + result.stderr
        self.assertNotEqual(result.returncode, 0, combined)
        self.assertIn("quickstart.py", combined)
        self.assertFalse(Path(env["LAUNCHER_CAPTURE"]).exists(),
                         "a server without configuration must not start")

    @unittest.skipUnless(os.name == "nt", "cmd.exe launcher")
    def test_bat_launcher_runs_start_ps1(self) -> None:
        repo, caller, env = self._windows_repo()
        env.update({"SERVER_HOST": "127.0.0.3", "SERVER_PORT": "8124"})
        result = self._run(["cmd", "/c", str(repo / "start.bat")], cwd=caller, env=env)
        capture = Path(env["LAUNCHER_CAPTURE"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        recorded = json.loads(capture.read_text(encoding="utf-8"))
        self.assertEqual(Path(recorded["cwd"]).resolve(), repo.resolve())
        self.assertEqual((recorded["host"], recorded["port"]), ("127.0.0.3", "8124"))

    def test_windows_scripts_are_crlf(self) -> None:
        bat = (ROOT / "start.bat").read_bytes()
        self.assertNotIn(b"\n", bat.replace(b"\r\n", b""))
        self.assertIn(b"-ExecutionPolicy Bypass", bat)
        self.assertIn(b'"%~dp0start.ps1"', bat)
        attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")
        for pattern in ("*.bat", "*.cmd", "*.vbs"):
            self.assertIn(f"{pattern} text eol=crlf", attributes)

    def test_powershell_launcher_runs_from_repository_root(self) -> None:
        capture, repo = self._run_powershell_launcher("127.0.0.1")
        self.assertEqual(Path(capture["cwd"]).resolve(), repo.resolve())

    def test_powershell_launcher_honors_configured_host(self) -> None:
        capture, _ = self._run_powershell_launcher("127.0.0.2")
        self.assertEqual(
            (capture["host"], capture["port"]),
            ("127.0.0.2", "8123"),
        )

    @unittest.skipIf(os.name == "nt", "POSIX launcher behavior runs on Unix CI")
    def test_posix_launcher_is_executable_and_honors_configured_host(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp) / "repo with spaces"
            python = repo / ".venv" / "bin" / "python"
            python.parent.mkdir(parents=True)
            launcher = repo / "start.sh"
            shutil.copy2(ROOT / "start.sh", launcher)
            (repo / ".env").write_text("LLM_API_KEY=sk-test\n", encoding="utf-8")
            capture = repo / "capture.json"
            python.write_text(
                f"#!{sys.executable}\n"
                "import json, os, sys\n"
                "from pathlib import Path\n"
                "if sys.argv[1:] == ['main.py']:\n"
                "    Path(os.environ['LAUNCHER_CAPTURE']).write_text(\n"
                "        json.dumps({'cwd': os.getcwd(), 'argv': sys.argv[1:]}),\n"
                "        encoding='utf-8')\n",
                encoding="utf-8",
            )
            python.chmod(python.stat().st_mode | stat.S_IXUSR)
            env = os.environ.copy()
            env.update(
                {
                    "SERVER_HOST": "127.0.0.2",
                    "SERVER_PORT": "8123",
                    "LAUNCHER_CAPTURE": str(capture),
                }
            )
            result = subprocess.run(
                [str(launcher)],
                cwd=repo.parent,
                env=env,
                text=True,
                capture_output=True,
                timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            recorded = json.loads(capture.read_text(encoding="utf-8"))
            self.assertEqual(Path(recorded["cwd"]).resolve(), repo.resolve())
            self.assertEqual(
                recorded["argv"],
                ["main.py"],
            )

    def test_vbs_launcher_quotes_editable_directories(self) -> None:
        source = (ROOT / "launch.vbs").read_text(encoding="ascii")
        self.assertIn('cd /d """ & NAPCAT_DIR & """', source)
        self.assertIn('cd /d """ & AGENT_DIR & """', source)
