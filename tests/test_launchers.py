"""Cross-platform behavior checks for the repository launchers."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class LauncherTests(unittest.TestCase):
    def _fake_python_modules(self, root: Path) -> Path:
        """A `pip` that installs nothing, and a `persona_agent` in the
        checkout that records how the launcher started it."""
        modules = root / "fake_modules"
        pip = modules / "pip"
        pip.mkdir(parents=True)
        (pip / "__init__.py").write_text("", encoding="utf-8")
        (pip / "__main__.py").write_text("", encoding="utf-8")
        package = root / "repo with spaces" / "persona_agent"
        package.mkdir()
        (package / "__init__.py").write_text("", encoding="utf-8")
        (package / "__main__.py").write_text(
            "import json, os, sys\n"
            "from pathlib import Path\n"
            "Path(os.environ['LAUNCHER_CAPTURE']).write_text(\n"
            "    json.dumps({'cwd': os.getcwd(), 'host': os.getenv('SERVER_HOST'),\n"
            "                'port': os.getenv('SERVER_PORT'), 'argv': sys.argv[1:]}),\n"
            "    encoding='utf-8')\n",
            encoding="utf-8",
        )
        return modules

    def _windows_repo(self, *, configured: bool = True) -> tuple[Path, Path, dict]:
        """A copy of the Windows launchers in a path with spaces, plus the env
        that makes its dependency install succeed without installing anything."""
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
        (repo / "pyproject.toml").write_text("[project]\nname = 'x'\n", encoding="utf-8")
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

    def test_powershell_launcher_points_an_unconfigured_checkout_at_setup(self) -> None:
        repo, caller, env = self._windows_repo(configured=False)
        result = self._run(self._powershell(repo), cwd=caller, env=env)
        combined = result.stdout + result.stderr
        self.assertNotEqual(result.returncode, 0, combined)
        self.assertIn("start.bat", combined)
        self.assertFalse(Path(env["LAUNCHER_CAPTURE"]).exists(),
                         "a server without configuration must not start")

    def test_start_ps1_runs_from_the_repository_root_on_the_configured_address(
            self) -> None:
        """One PowerShell start: through start.bat on Windows, which runs
        start.ps1, and start.ps1 directly elsewhere."""
        repo, caller, env = self._windows_repo()
        env.update({"SERVER_HOST": "127.0.0.2", "SERVER_PORT": "8123"})
        if os.name == "nt":
            cmd = ["cmd", "/c", str(repo / "start.bat")]
        else:
            cmd = self._powershell(repo)
        result = self._run(cmd, cwd=caller, env=env)
        capture = Path(env["LAUNCHER_CAPTURE"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(capture.is_file(), result.stdout + result.stderr)
        recorded = json.loads(capture.read_text(encoding="utf-8"))
        self.assertEqual(Path(recorded["cwd"]).resolve(), repo.resolve())
        self.assertEqual((recorded["host"], recorded["port"]), ("127.0.0.2", "8123"))
        # Without a console it runs the service, as `personagent run`.
        self.assertEqual(recorded["argv"], ["run"])
        self.assertTrue((repo / ".venv" / ".personagent-installed").is_file())

    def test_windows_scripts_are_crlf(self) -> None:
        bat = (ROOT / "start.bat").read_bytes()
        self.assertNotIn(b"\n", bat.replace(b"\r\n", b""))
        self.assertIn(b"-ExecutionPolicy Bypass", bat)
        self.assertIn(b'"%~dp0start.ps1"', bat)
        attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")
        for pattern in ("*.bat", "*.cmd"):
            self.assertIn(f"{pattern} text eol=crlf", attributes)
