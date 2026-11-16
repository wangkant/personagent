"""install.ps1 and install.sh, as far as they can be checked without a network.

The real runs (uv, a managed Python, the package itself) are CI's `installer`
job, on Linux, macOS and Windows.
"""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PS1 = ROOT / "install.ps1"
SH = ROOT / "install.sh"
RAW = "https://raw.githubusercontent.com/wangkant/personagent/main/"


def _powershell() -> str | None:
    return shutil.which("powershell") or shutil.which("pwsh")


class InstallerTextTests(unittest.TestCase):
    def test_the_windows_installer_is_ascii(self) -> None:
        """Windows PowerShell 5.1 reads a file without a BOM in the system
        code page, where one Chinese character can swallow a closing quote."""
        PS1.read_bytes().decode("ascii")

    def test_its_chinese_sentences_are_chinese(self) -> None:
        escaped = re.findall(r"'((?:\\u[0-9a-f]{4}|[^'\n])*\\u[0-9a-f]{4}[^'\n]*)'",
                             PS1.read_text(encoding="ascii"))
        self.assertGreater(len(escaped), 8)
        for sentence in escaped:
            text = re.sub(r"\\u([0-9a-f]{4})", lambda m: chr(int(m.group(1), 16)), sentence)
            self.assertNotIn("\\u", text)
            self.assertRegex(text, r"[一-鿿]")

    def test_the_shell_installer_has_unix_line_ends_and_a_shebang(self) -> None:
        raw = SH.read_bytes()
        self.assertTrue(raw.startswith(b"#!/bin/sh\n"))
        self.assertNotIn(b"\r", raw)

    def test_both_use_the_same_python_and_mirrors(self) -> None:
        ps1 = PS1.read_text(encoding="ascii")
        sh = SH.read_text(encoding="utf-8")
        python = re.search(r"\$PersonagentPython = '([\d.]+)'", ps1).group(1)
        self.assertIn(f'PYTHON_VERSION="{python}"', sh)
        for url in re.findall(r"'(https://[^']+)'", ps1.split("function Write-PaLine")[0]):
            self.assertIn(url, sh)
        probes = set(re.findall(r"https://[\w./-]+SHA256SUMS", ps1))
        self.assertEqual(probes, set(re.findall(r"https://[\w./-]+SHA256SUMS", sh)))
        self.assertEqual(len(probes), 1)

    def test_the_app_s_own_downloads_use_the_same_mirrors(self) -> None:
        from persona_agent import mirrors

        ps1 = PS1.read_text(encoding="ascii")
        for url in (*mirrors.INDEX_MIRRORS, mirrors.PYTHON_MIRROR, mirrors.PYPI_PROBE, mirrors.GITHUB_PROBE):
            self.assertIn(url, ps1)

    def test_both_take_the_same_settings(self) -> None:
        ps1 = set(re.findall(r"PERSONAGENT_[A-Z_]+", PS1.read_text(encoding="ascii")))
        sh = set(re.findall(r"PERSONAGENT_[A-Z_]+", SH.read_text(encoding="utf-8")))
        # The launcher folder is Python's to redirect on Windows (shortcut.DIRS_ENV).
        self.assertEqual(ps1, sh - {"PERSONAGENT_SHORTCUT_DIR"})

    def test_the_docs_give_the_commands_the_scripts_name(self) -> None:
        for script, name in ((PS1.read_text(encoding="ascii"), "install.ps1"),
                             (SH.read_text(encoding="utf-8"), "install.sh")):
            self.assertIn(RAW + name, script)
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn(f"irm {RAW}install.ps1 | iex", readme)
        self.assertIn(f"curl -LsSf {RAW}install.sh | sh", readme)

    def test_the_source_archive_carries_the_installer_start_ps1_loads(self) -> None:
        start = (ROOT / "start.ps1").read_text(encoding="utf-8")
        self.assertIn("'install.ps1'", start)
        for name in ("Get-PaUv", "Invoke-PaNative", "$PersonagentIndexMirrors",
                     "$PersonagentPythonMirror", "$PersonagentPython"):
            self.assertIn(name, start)
            self.assertIn(name, PS1.read_text(encoding="ascii"))


class InstallerSyntaxTests(unittest.TestCase):
    def test_powershell_parses_the_windows_installer(self) -> None:
        powershell = _powershell()
        if not powershell:
            self.skipTest("PowerShell is not installed")
        source = (
            "$errors = $null; $tokens = $null; "
            "[void][System.Management.Automation.Language.Parser]::ParseFile("
            f"'{PS1}', [ref]$tokens, [ref]$errors); "
            "if ($errors) { $errors | ForEach-Object { $_.Extent.StartLineNumber }; exit 1 }")
        done = subprocess.run([powershell, "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", source],
                              capture_output=True, text=True, encoding="utf-8", errors="replace",
                              stdin=subprocess.DEVNULL, timeout=120)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    def test_loading_it_as_a_library_installs_nothing(self) -> None:
        """start.ps1 loads the functions; nothing may run or reach the network."""
        powershell = _powershell()
        if not powershell:
            self.skipTest("PowerShell is not installed")
        source = (f"$PersonagentInstallLib = $true; . '{PS1}'; "
                  "if (-not (Get-Command Get-PaUv -ErrorAction SilentlyContinue)) { exit 3 }; "
                  "Write-Output \"python=$PersonagentPython\"")
        done = subprocess.run([powershell, "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", source],
                              capture_output=True, text=True, encoding="utf-8", errors="replace",
                              stdin=subprocess.DEVNULL, timeout=120)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(done.stdout.strip(), "python=3.12")

    @unittest.skipUnless(os.name == "nt", "the Windows installer's own checks")
    def test_an_old_uv_is_not_used_and_a_copy_from_pip_is_seen(self) -> None:
        powershell = _powershell()
        if not powershell:
            self.skipTest("PowerShell is not installed")
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            bin_dir = folder / "bin"
            bin_dir.mkdir()
            for name, version, listed in (("old", "0.7.3", ""), ("new", "0.13.8", ""),
                                          ("ours", "0.13.8", "personagent v1.5.0")):
                (folder / f"{name}.cmd").write_text(
                    "@echo off\r\n"
                    f"if \"%1\"==\"--version\" echo uv {version} (stand-in)\r\n"
                    # Its own folder, so no path is written into a file cmd reads in its code page.
                    "if \"%1 %2 %3\"==\"tool dir --bin\" echo %~dp0bin\r\n"
                    + (f"if \"%1 %2\"==\"tool list\" echo {listed}\r\n" if listed else ""),
                    encoding="ascii", newline="")
            source = (f"$PersonagentInstallLib = $true; . '{PS1}'; "
                      f"$old = Test-PaUvRecent '{folder / 'old.cmd'}'; $new = Test-PaUvRecent '{folder / 'new.cmd'}'; "
                      f"$none = Test-PaForeignCopy '{folder / 'new.cmd'}'; "
                      f"Set-Content -LiteralPath '{bin_dir / 'personagent.exe'}' -Value x; "
                      f"$pip = Test-PaForeignCopy '{folder / 'new.cmd'}'; $uv = Test-PaForeignCopy '{folder / 'ours.cmd'}'; "
                      "Write-Output \"$old $new $none $pip $uv\"")
            done = subprocess.run([powershell, "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", source],
                                  capture_output=True, text=True, encoding="utf-8", errors="replace",
                                  stdin=subprocess.DEVNULL, timeout=120)
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
            # An old uv: no. A recent one: yes. No personagent there: nothing to replace.
            # One that uv does not list: replace it. One uv installed: leave it to the upgrade.
            self.assertEqual(done.stdout.strip(), "False True False True False")

    def test_a_shell_parses_the_unix_installer(self) -> None:
        shell = shutil.which("sh")
        if not shell:
            self.skipTest("no sh here")
        done = subprocess.run([shell, "-n", str(SH)], capture_output=True, text=True, timeout=60)
        self.assertEqual(done.returncode, 0, done.stderr)


@unittest.skipIf(os.name == "nt", "the shell installer runs on macOS and Linux")
class ShellInstallerPartsTests(unittest.TestCase):
    """Its functions, loaded without `main`, on files made here."""

    def _run(self, body: str, cwd: Path) -> subprocess.CompletedProcess:
        library = cwd / "lib.sh"
        library.write_text(SH.read_text(encoding="utf-8").rsplit("\nmain \"$@\"", 1)[0] + "\n",
                           encoding="utf-8")
        return subprocess.run(["sh", "-c", f'. "{library}"; TMP="{cwd}"; {body}'],
                              cwd=cwd, capture_output=True, text=True, timeout=60)

    def test_the_newest_wheel_of_this_system_is_picked_from_an_index_page(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            cwd = Path(temp)
            done = self._run("wheel_pattern", cwd)
            self.assertEqual(done.returncode, 0, done.stderr)
            pattern = done.stdout.strip()
            tag = {"macosx_[0-9_]*_arm64": "macosx_11_0_arm64",
                   "macosx_[0-9_]*_x86_64": "macosx_10_12_x86_64",
                   "manylinux[a-z0-9_.]*_x86_64": "manylinux_2_17_x86_64.manylinux2014_x86_64",
                   "musllinux_[0-9_]*_x86_64": "musllinux_1_1_x86_64",
                   "[a-z0-9_.]*musllinux_[0-9_]*_aarch64":
                       "manylinux_2_17_aarch64.manylinux2014_aarch64.musllinux_1_1_aarch64"}[pattern]
            rows = [f'<a href="../../packages/aa/uv-{v}-py3-none-{t}.whl#sha256={"0" * 63}{i}">x</a>'
                    for i, (v, t) in enumerate([("0.9.30", tag), ("0.13.8", tag), ("0.13.10", tag),
                                                ("0.14.0rc1", tag), ("0.99.0", "win_amd64")])]
            (cwd / "page.html").write_text("\n".join(rows), encoding="utf-8")
            pick = f"pick_wheel https://index.example/simple/uv/ '{pattern}' \"$TMP/page.html\""
            done = self._run(pick, cwd)
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertEqual(done.stdout.strip(),
                             "https://index.example/simple/uv/../../packages/aa/"
                             f"uv-0.13.10-py3-none-{tag}.whl {'0' * 63}2")
            absolute = f'<a href="https://files.example/uv-1.0.0-py3-none-{tag}.whl">x</a>'
            (cwd / "page.html").write_text(absolute, encoding="utf-8")
            done = self._run(pick, cwd)
            self.assertEqual(done.stdout.strip(), f"https://files.example/uv-1.0.0-py3-none-{tag}.whl")

    def _stand_in_uv(self, cwd: Path, name: str, version: str, listed: str = "") -> Path:
        made = cwd / name
        made.write_text("#!/bin/sh\n"
                        f'[ "$1" = --version ] && echo "uv {version} (stand-in)"\n'
                        f'[ "$1 $2 $3" = "tool dir --bin" ] && echo "{cwd}/bin"\n'
                        f'[ "$1 $2" = "tool list" ] && echo "{listed}"\n'
                        "exit 0\n", encoding="utf-8")
        made.chmod(0o755)
        return made

    def test_an_old_uv_is_not_used(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            cwd = Path(temp)
            for name, version, recent in (("a", "0.7.30", False), ("b", "0.8.0", True),
                                          ("c", "0.13.8", True), ("d", "1.0.2", True)):
                uv = self._stand_in_uv(cwd, name, version)
                done = self._run(f'uv_recent "{uv}"', cwd)
                self.assertEqual(done.returncode == 0, recent, (version, done.stderr))
            self.assertNotEqual(self._run(f'uv_recent "{cwd}/missing"', cwd).returncode, 0)

    def test_a_copy_installed_another_way_is_seen(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            cwd = Path(temp)
            (cwd / "bin").mkdir()
            uv = self._stand_in_uv(cwd, "uv", "0.13.8")
            self.assertNotEqual(self._run(f'foreign_copy "{uv}"', cwd).returncode, 0, "nothing there")
            (cwd / "bin" / "personagent").write_text("#!/bin/sh\n", encoding="utf-8")
            self.assertEqual(self._run(f'foreign_copy "{uv}"', cwd).returncode, 0, "from pip or pipx")
            ours = self._stand_in_uv(cwd, "uv2", "0.13.8", "personagent v1.5.0")
            self.assertNotEqual(self._run(f'foreign_copy "{ours}"', cwd).returncode, 0, "uv's own")

    def test_a_checksum_that_differs_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            cwd = Path(temp)
            (cwd / "file").write_bytes(b"personagent")
            good = hashlib.sha256(b"personagent").hexdigest()
            self.assertEqual(self._run(f'checksum_ok "$TMP/file" {good}', cwd).returncode, 0)
            self.assertNotEqual(self._run(f'checksum_ok "$TMP/file" {"0" * 64}', cwd).returncode, 0)
            self.assertEqual(self._run('checksum_ok "$TMP/file" ""', cwd).returncode, 0)

    def test_uv_is_taken_out_of_a_wheel(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            cwd = Path(temp)
            with zipfile.ZipFile(cwd / "uv.whl", "w") as wheel:
                wheel.writestr("uv-0.13.8.data/scripts/uv", "#!/bin/sh\necho uv-stand-in\n")
                wheel.writestr("uv-0.13.8.data/scripts/uvx", "#!/bin/sh\n")
                wheel.writestr("uv-0.13.8.dist-info/METADATA", "Name: uv\n")
            done = self._run('mkdir -p "$TMP/bin" && unpack_uv "$TMP/uv.whl" "$TMP/bin" && "$TMP/bin/uv"', cwd)
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertEqual(done.stdout.strip(), "uv-stand-in")
            self.assertTrue(os.access(cwd / "bin" / "uvx", os.X_OK))
            self.assertFalse((cwd / "bin" / ".personagent-unpack").exists())

    def test_a_launcher_is_made_for_this_system(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            cwd = Path(temp)
            done = self._run(f'PERSONAGENT_SHORTCUT_DIR="{cwd}" make_launcher "/opt/a b/personagent"', cwd)
            self.assertEqual(done.returncode, 0, done.stderr)
            made = cwd / ("personagent.command" if sys.platform == "darwin" else "personagent.desktop")
            self.assertIn('"/opt/a b/personagent" start', made.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
