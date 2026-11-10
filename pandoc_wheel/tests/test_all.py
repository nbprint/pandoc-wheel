from importlib.resources import files
from pathlib import Path
from shutil import which
from subprocess import run
from sys import platform
from sysconfig import get_path

import pypandoc
import pytest

from pandoc_wheel import __version__


@pytest.fixture
def pandoc():
    executable = "pandoc.exe" if platform == "win32" else "pandoc"
    path = Path(get_path("scripts")) / executable
    assert path.is_file()
    discovered = which("pandoc")
    assert discovered is not None
    assert Path(discovered).resolve() == path.resolve()
    return str(path)


def test_version():
    assert __version__ == "3.13.0"


def test_bundled_version(pandoc):
    result = run([pandoc, "--version"], check=True, capture_output=True, text=True)
    assert result.stdout.splitlines()[0] == "pandoc 3.13"


def test_markdown_to_html(pandoc):
    result = run([pandoc, "-f", "markdown", "-t", "html"], input="**Hello**", check=True, capture_output=True, text=True)
    assert result.stdout.strip() == "<p><strong>Hello</strong></p>"


def test_native_executable(pandoc):
    with open(pandoc, "rb") as binary:
        magic = binary.read(4)
    assert magic in (b"\x7fELF", b"\xcf\xfa\xed\xfe") or magic.startswith(b"MZ")


def test_cli_exit_code(pandoc):
    result = run([pandoc, "--invalid-option"], check=False, capture_output=True, text=True)
    assert result.returncode != 0
    assert "Unknown option" in result.stderr


def test_docx_roundtrip(pandoc, tmp_path):
    document = tmp_path / "document.docx"
    run([pandoc, "-f", "markdown", "-o", str(document)], input="**Hello**", check=True, text=True)
    result = run([pandoc, str(document), "-t", "html"], check=True, capture_output=True, text=True)
    assert "<strong>Hello</strong>" in result.stdout


def test_bundled_license():
    payload = files("pandoc_wheel") / "bin"
    assert "GNU GENERAL PUBLIC LICENSE" in (payload / "COPYING.md").read_text()
    assert "John MacFarlane" in (payload / "COPYRIGHT").read_text()


def test_pypandoc(pandoc):
    assert pypandoc.convert_text("**Hello**", "html", format="markdown").strip() == "<p><strong>Hello</strong></p>"
