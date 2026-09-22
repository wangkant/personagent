"""start.ps1 failure contracts, exercised on Windows.

`test_start_sh_isolation.py` covers the POSIX launcher's refusal paths, but it
is skipped on `nt`, and `test_launchers.py` only drives start.ps1's happy path
(repository root, HOST/PORT). So the Windows launcher's two refusals — it will
not touch an incomplete `.venv`, and it will not start the server after a
failed dependency install — were guaranteed by reading the script, on the one
platform where the script is the only one that runs.

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
        (self.repo / "requirements.txt").write_text("", encoding="utf-8")
        # Proves the server was never reached: start.ps1's last act is
        # `& $pySource main.py`, so this file existing means it got that far.
        (self.repo / "main.py").write_text(
            "from pathlib import Path\n"
            "Path(__file__).with_name('SERVER_STARTED').write_text('x')\n",
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
        env["PATH"] = _SYSTEM_PATH if path is None else path
        if pythonpath is not None:
            env["PYTHONPATH"] = pythonpath
        return subprocess.run(
            [self.powershell, "-NoLogo", "-NoProfile", "-NonInteractive",
             "-ExecutionPolicy", "Bypass", "-File", str(self.repo / "start.ps1")],
            cwd=self.base, env=env, text=True, capture_output=True, timeout=180,
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
        # The refusal is the point: a half-built .venv must be repaired by
        # quickstart.py or moved aside, never silently rebuilt over.
        self.assertFalse((venv / "Scripts" / "python.exe").exists())
        self.assertFalse(self._server_started())

    def test_missing_python_is_reported_before_the_incomplete_venv(self) -> None:
        """start.ps1 checks for an interpreter BEFORE it checks the .venv;
        start.sh checks them the other way round. Both refuse, and neither
        touches the .venv, but the message a Windows operator gets for a
        machine with both problems is "python / python3 not found". The two
        launchers differ here on purpose — do not "fix" this to match."""
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


def main() -> int:
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(
        StartPs1IsolationTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
