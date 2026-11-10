from pathlib import Path
from subprocess import run
from sys import argv, platform


def get_pandoc_path() -> str:
    """Return the bundled Pandoc executable."""
    if platform == "emscripten":
        raise RuntimeError("Use pandoc_wheel.pyodide.convert in Pyodide")
    executable = "pandoc.exe" if platform == "win32" else "pandoc"
    return str(Path(__file__).resolve().parent / "bin" / executable)


def main():
    raise SystemExit(run([get_pandoc_path(), *argv[1:]], check=False).returncode)
