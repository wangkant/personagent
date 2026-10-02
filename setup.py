"""Build hook: ship the checkout's shared files inside the package as persona_agent/_bundled.

home.resource() finds them there in an installed copy and at the repository
root in a checkout, so the tree stays single-source. Metadata is in pyproject.toml.
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
BUNDLED = ("data", ".env.example", "integrations/astrbot/astrbot_plugin_personagent")


def bundled_files(root: Path = HERE):
    """(source, path under _bundled) for every shipped file; no bytecode caches."""
    for entry in BUNDLED:
        source = root / entry
        candidates = [source] if source.is_file() else sorted(source.rglob("*"))
        for path in candidates:
            relative = path.relative_to(root)
            if (path.is_file() and "__pycache__" not in relative.parts
                    and path.suffix not in (".pyc", ".pyo")):
                yield path, relative


def build_py_with_bundle():
    # Imported here so the file list above can be read without setuptools.
    from setuptools.command.build_py import build_py

    class BuildPyWithBundle(build_py):
        def run(self):
            super().run()
            target = Path(self.build_lib) / "persona_agent" / "_bundled"
            for source, relative in bundled_files():
                destination = target / relative
                self.mkpath(str(destination.parent))
                self.copy_file(str(source), str(destination), preserve_mode=False)

    return BuildPyWithBundle


if __name__ == "__main__":
    from setuptools import setup

    setup(cmdclass={"build_py": build_py_with_bundle()})
