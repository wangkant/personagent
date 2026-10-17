"""start.ps1 failure contracts, exercised on Windows.

`test_launchers.py` only drives start.ps1's happy path (repository root,
SERVER_HOST/SERVER_PORT). The refusals here — it will not touch an incomplete
`.venv`, and it will not start the server after a failed dependency install —
would otherwise be guaranteed only by reading the script.

No network and no real `pip install`: the interpreter is a genuine venv (a
copied `python.exe` is not viable on Windows, which needs the real PE plus its
DLLs and `pyvenv.cfg`), and `pip` is shadowed through `PYTHONPATH`, which sits
ahead of site-packages on `sys.path`.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

#: Enough of the system PATH for PowerShell itself to start, and deliberately
#: nothing else — the ordering test needs a machine with no global python.
_SYSTEM_PATH = os.pathsep.join([
    r"C:\Windows\System32", r"C:\Windows",
    r"C:\Windows\System32\WindowsPowerShell\v1.0",
])


@unittest.skipUnless(os.name == "nt", "Windows launcher")
class StartPs1IsolationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.powershell = shutil.which("powershell") or shutil.which("pwsh")
        if not self.powershell:
            self.skipTest("PowerShell is not installed")
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        # A space in the path: the launcher quotes its own paths, and an
        # unquoted one fails only here.
        self.repo = self.base / "repo with spaces"
        self.repo.mkdir()
        shutil.copy2(ROOT / "start.ps1", self.repo / "start.ps1")
        (self.repo / "pyproject.toml").write_text("[project]\nname = 'x'\n", encoding="utf-8")
        (self.repo / ".env").write_text("LLM_API_KEY=sk-test\n", encoding="utf-8")
        # Proves the server was never reached: start.ps1's last act is
        # `-m persona_agent`, so this file existing means it got that far.
        package = self.repo / "persona_agent"
        package.mkdir()
        (package / "__init__.py").write_text("", encoding="utf-8")
        (package / "__main__.py").write_text(
            "from pathlib import Path\n"
            "Path(__file__).parent.with_name('SERVER_STARTED').write_text('x')\n",
            encoding="utf-8",
        )

    # -- helpers ----------------------------------------------------------
    def _fake_pip(self, exit_code: int = 8) -> Path:
        """A `pip` package that fails instead of reaching the network."""
        modules = self.base / "fake_modules"
        package = modules / "pip"
        package.mkdir(parents=True, exist_ok=True)
        (package / "__init__.py").write_text("", encoding="utf-8")
        (package / "__main__.py").write_text(
            f"import sys\nsys.exit({exit_code})\n", encoding="utf-8")
        return modules

    def _run(self, *, path: str | None = None,
             pythonpath: str | None = None) -> subprocess.CompletedProcess:
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        env.pop("LLM_API_KEY", None)
        env["PATH"] = _SYSTEM_PATH if path is None else path
        if pythonpath is not None:
            env["PYTHONPATH"] = pythonpath
        return subprocess.run(
            [self.powershell, "-NoLogo", "-NoProfile", "-NonInteractive",
             "-ExecutionPolicy", "Bypass", "-File", str(self.repo / "start.ps1")],
            cwd=self.base, env=env, stdin=subprocess.DEVNULL, capture_output=True,
            # PowerShell writes in the console code page (GBK here): never crash on it.
            text=True, encoding="utf-8", errors="replace", timeout=180,
        )

    def _path_with_real_python(self) -> str:
        return os.pathsep.join([str(Path(sys.executable).parent), _SYSTEM_PATH])

    def _server_started(self) -> bool:
        return (self.repo / "SERVER_STARTED").exists()

    # -- the contracts ----------------------------------------------------
    def test_incomplete_venv_is_reported_without_overwriting_it(self) -> None:
        venv = self.repo / ".venv"
        venv.mkdir()
        marker = venv / "keep.txt"
        marker.write_text("existing user files", encoding="utf-8")

        result = self._run(path=self._path_with_real_python())

        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(".venv", result.stdout + result.stderr)
        self.assertEqual(marker.read_text(encoding="utf-8"), "existing user files")
        # The refusal is the point: a half-built .venv must be moved aside,
        # never silently rebuilt over.
        self.assertFalse((venv / "Scripts" / "python.exe").exists())
        self.assertFalse(self._server_started())

    def test_missing_python_is_reported_before_the_incomplete_venv(self) -> None:
        """start.ps1 checks for an interpreter BEFORE it checks the .venv, so
        a machine with both problems is told "python / python3 not found", and
        the .venv is left alone."""
        venv = self.repo / ".venv"
        venv.mkdir()
        marker = venv / "keep.txt"
        marker.write_text("existing user files", encoding="utf-8")

        result = self._run()  # system PATH only: no python anywhere
        combined = result.stdout + result.stderr

        self.assertNotEqual(result.returncode, 0, combined)
        self.assertIn("not found", combined)
        self.assertNotIn("Incomplete", combined)
        self.assertEqual(marker.read_text(encoding="utf-8"), "existing user files")
        self.assertFalse(self._server_started())

    def test_an_unconfigured_checkout_is_sent_to_setup(self) -> None:
        (self.repo / ".env").unlink()

        result = self._run(path=self._path_with_real_python())
        combined = result.stdout + result.stderr

        self.assertNotEqual(result.returncode, 0, combined)
        self.assertIn("start.bat", combined)
        self.assertFalse((self.repo / ".venv").exists(),
                         "nothing is installed before the setup has run")
        self.assertFalse(self._server_started())

    def test_install_failure_does_not_launch_the_server(self) -> None:
        # A real, empty venv: its interpreter runs, and nothing is installed
        # in it, so start.ps1's dependency probe fails exactly as it would on
        # a fresh checkout — then its `pip install` hits the stub below.
        subprocess.run(
            [sys.executable, "-m", "venv", str(self.repo / ".venv")],
            check=True, capture_output=True, timeout=180,
        )
        self.assertTrue((self.repo / ".venv" / "Scripts" / "python.exe").is_file())

        result = self._run(path=self._path_with_real_python(),
                           pythonpath=str(self._fake_pip(exit_code=8)))

        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(self._server_started(),
                         "a failed dependency install must not start the server")

    def _venv_with_stamp(self, stamp: str) -> Path:
        subprocess.run(
            [sys.executable, "-m", "venv", str(self.repo / ".venv")],
            check=True, capture_output=True, timeout=180,
        )
        path = self.repo / ".venv" / ".personagent-installed"
        path.write_text(stamp, encoding="ascii")
        return path

    def test_an_empty_stamp_installs_again_instead_of_failing(self) -> None:
        stamp = self._venv_with_stamp("")

        result = self._run(path=self._path_with_real_python(),
                           pythonpath=str(self._fake_pip(exit_code=0)))

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(self._server_started())
        self.assertTrue(stamp.read_text(encoding="ascii").strip())

    def test_a_failed_update_after_a_good_install_still_starts(self) -> None:
        """Offline after a pull: the dependencies installed before still run it."""
        self._venv_with_stamp("an-earlier-dependency-list")

        result = self._run(path=self._path_with_real_python(),
                           pythonpath=str(self._fake_pip(exit_code=8)))

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("could not update", result.stdout + result.stderr)
        self.assertTrue(self._server_started())
