"""start.ps1 failure contracts, exercised on Windows.

`test_launchers.py` only drives start.ps1's happy path (repository root,
SERVER_HOST/SERVER_PORT). The refusals here — it will not touch an incomplete
`.venv`, it will not start the server after a failed dependency install, and
it will not build on a Python older than 3.10 — would otherwise be guaranteed
only by reading the script. So would its use of the `py` launcher.

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
#: C:\Windows stays out: an all-users Python install puts py.exe there.
_SYSTEM_PATH = os.pathsep.join([
    r"C:\Windows\System32",
    r"C:\Windows\System32\WindowsPowerShell\v1.0",
])

#: An interpreter that answers the version question as Python 3.9.7 and
#: refuses everything else, noting what it was asked.
_OLD_PYTHON = """\
import collections, sys
from pathlib import Path
Version = collections.namedtuple("version_info", "major minor micro releaselevel serial")
sys.version_info = Version(3, 9, 7, "final", 0)
sys.version = "3.9.7 (stand-in)"
args = sys.argv[1:]
with open(Path(__file__).with_name("old-python-calls.log"), "a", encoding="utf-8") as log:
    log.write(" ".join(args[:1]) + "\\n")
if args[:1] == ["-c"]:
    exec(args[1])
    sys.exit(0)
sys.exit(1)
"""

#: python.org's `py` launcher: takes `-3`, then hands the rest to a real Python.
_PY_LAUNCHER = """\
import subprocess, sys
from pathlib import Path
args = sys.argv[1:]
with open(Path(__file__).with_name("py-calls.log"), "a", encoding="utf-8") as log:
    log.write(" ".join(args[:3]) + "\\n")
if args[:1] != ["-3"]:
    sys.exit(64)
rest = args[1:]
if rest[:2] == ["-m", "venv"]:
    rest[2:2] = ["--without-pip"]  # pip is shadowed in these tests; skip its slow bootstrap
sys.exit(subprocess.call([sys.executable, *rest]))
"""


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
        env["STAND_IN_PYTHON"] = sys.executable
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

    def _fake_command(self, name: str, script: str) -> Path:
        """`name` on a PATH folder of its own: a .cmd that runs `script` with
        this interpreter. Returns that folder, where the script keeps its log."""
        folder = self.base / "fake bin"
        folder.mkdir(exist_ok=True)
        (folder / f"{name}_stand_in.py").write_text(script, encoding="utf-8")
        # ASCII only: cmd reads a batch file in the console code page, so no
        # path is written into it.
        (folder / f"{name}.cmd").write_text(
            f'@"%STAND_IN_PYTHON%" "%~dp0{name}_stand_in.py" %*\r\n@exit /b %ERRORLEVEL%\r\n',
            encoding="ascii", newline="")
        return folder

    def _path_with_fakes(self, folder: Path) -> str:
        return os.pathsep.join([str(folder), _SYSTEM_PATH])

    def _old_everywhere(self) -> Path:
        """A sitecustomize that makes every interpreter started with it on
        PYTHONPATH report Python 3.9.7, the venv's own included."""
        modules = self._fake_pip(exit_code=0)
        (modules / "sitecustomize.py").write_text(
            "import collections, sys\n"
            "sys.version_info = collections.namedtuple(\n"
            "    'version_info', 'major minor micro releaselevel serial')(3, 9, 7, 'final', 0)\n",
            encoding="utf-8")
        return modules

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
        a machine with both problems is told "python / python3 / py not found",
        and the .venv is left alone."""
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
            [sys.executable, "-m", "venv", "--without-pip", str(self.repo / ".venv")],
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
            [sys.executable, "-m", "venv", "--without-pip", str(self.repo / ".venv")],
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

    # -- which Python ------------------------------------------------------
    def _calls(self, folder: Path, log: str) -> list[str]:
        path = folder / log
        return path.read_text(encoding="utf-8").splitlines() if path.exists() else []

    def test_the_py_launcher_serves_a_machine_with_no_python_on_path(self) -> None:
        """python.org's installer leaves Python off PATH and installs `py`."""
        fakes = self._fake_command("py", _PY_LAUNCHER)

        result = self._run(path=self._path_with_fakes(fakes),
                           pythonpath=str(self._fake_pip(exit_code=0)))
        combined = result.stdout + result.stderr

        self.assertEqual(result.returncode, 0, combined)
        self.assertNotIn("not found", combined)
        self.assertIn("-3 -m venv", self._calls(fakes, "py-calls.log"), combined)
        self.assertTrue((self.repo / ".venv" / "Scripts" / "python.exe").is_file())
        self.assertTrue(self._server_started())

    def test_an_old_python_is_named_with_the_version_needed(self) -> None:
        """Python 3.9 used to run on into pip and read as a network failure."""
        fakes = self._fake_command("python", _OLD_PYTHON)

        result = self._run(path=self._path_with_fakes(fakes),
                           pythonpath=str(self._fake_pip(exit_code=8)))
        combined = result.stdout + result.stderr

        self.assertNotEqual(result.returncode, 0, combined)
        self.assertIn("Python 3.9.7", combined)
        self.assertIn("3.10 or newer", combined)
        self.assertNotIn("network", combined)
        self.assertNotIn("not found", combined)
        self.assertEqual(self._calls(fakes, "old-python-calls.log"), ["-c"],
                         "asked its version and nothing else")
        self.assertFalse((self.repo / ".venv").exists())
        self.assertFalse(self._server_started())

    def test_a_good_python_behind_the_launcher_wins_over_an_old_one_on_path(self) -> None:
        fakes = self._fake_command("python", _OLD_PYTHON)
        self._fake_command("py", _PY_LAUNCHER)

        result = self._run(path=self._path_with_fakes(fakes),
                           pythonpath=str(self._fake_pip(exit_code=0)))
        combined = result.stdout + result.stderr

        self.assertEqual(result.returncode, 0, combined)
        self.assertNotIn("3.9.7", combined)
        self.assertEqual(self._calls(fakes, "old-python-calls.log"), ["-c"])
        self.assertIn("-3 -m venv", self._calls(fakes, "py-calls.log"), combined)
        self.assertTrue(self._server_started())

    def test_a_venv_made_with_an_old_python_is_named_too(self) -> None:
        """What an earlier start left behind on a machine that had only 3.9."""
        stamp = self._venv_with_stamp("")
        marker = self.repo / ".venv" / "keep.txt"
        marker.write_text("existing user files", encoding="utf-8")

        result = self._run(path=self._path_with_real_python(),
                           pythonpath=str(self._old_everywhere()))
        combined = result.stdout + result.stderr

        self.assertNotEqual(result.returncode, 0, combined)
        self.assertIn(".venv", combined)
        self.assertIn("Python 3.9.7", combined)
        self.assertIn("3.10 or newer", combined)
        self.assertNotIn("network", combined)
        self.assertEqual(stamp.read_text(encoding="ascii"), "", "nothing was installed")
        self.assertEqual(marker.read_text(encoding="utf-8"), "existing user files")
        self.assertFalse(self._server_started())
