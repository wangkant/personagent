"""Check a release tag against pyproject.toml and print its CHANGELOG section.

    python tools/release_notes.py v1.0.0 --out notes.md

Exits non-zero, saying why, when the tag and the version disagree or the
CHANGELOG has no `## [X.Y.Z]` section for it, so nothing gets published.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def project_version(pyproject: str) -> str:
    match = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.MULTILINE)
    if not match:
        raise ValueError("pyproject.toml has no version")
    return match.group(1)


def changelog_section(changelog: str, version: str) -> str:
    """The body under `## [version]`, up to the next `## [` heading or the link list."""
    lines = changelog.splitlines()
    heading = re.compile(rf"^## \[{re.escape(version)}\](\s|$)")
    try:
        start = next(i for i, ln in enumerate(lines) if heading.match(ln))
    except StopIteration:
        raise ValueError(f"CHANGELOG.md has no '## [{version}]' section") from None
    body = []
    for line in lines[start + 1:]:
        if line.startswith("## [") or re.match(r"^\[[^\]]+\]:\s*https?://", line):
            break
        body.append(line)
    text = "\n".join(body).strip()
    if not text:
        raise ValueError(f"the CHANGELOG.md section for {version} is empty")
    return text + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("tag", help="the release tag, e.g. v1.0.0")
    p.add_argument("--out", help="write the notes here instead of stdout")
    args = p.parse_args(argv)
    try:
        version = project_version((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        if args.tag != f"v{version}":
            raise ValueError(f"tag {args.tag} does not match pyproject.toml's version {version}")
        notes = changelog_section((ROOT / "CHANGELOG.md").read_text(encoding="utf-8"), version)
    except ValueError as exc:
        print(f"release_notes: {exc}", file=sys.stderr)
        return 1
    if args.out:
        Path(args.out).write_text(notes, encoding="utf-8")
    else:
        sys.stdout.write(notes)
    return 0


if __name__ == "__main__":
    sys.exit(main())
