from pathlib import Path
from subprocess import run
from sys import executable

from pandoc_wheel import __version__
from pandoc_wheel.cli import get_pandoc_path


def test_version():
    assert __version__ == "0.1.0"


def test_bundled_version():
    result = run([get_pandoc_path(), "--version"], check=True, capture_output=True, text=True)
    assert result.stdout.splitlines()[0] == "pandoc 3.13"


def test_markdown_to_html():
    result = run([get_pandoc_path(), "-f", "markdown", "-t", "html"], input="**Hello**", check=True, capture_output=True, text=True)
    assert result.stdout.strip() == "<p><strong>Hello</strong></p>"


def test_module_cli():
    result = run([executable, "-m", "pandoc_wheel", "--version"], check=True, capture_output=True, text=True)
    assert result.stdout.startswith("pandoc 3.13\n")


def test_cli_exit_code():
    result = run([executable, "-m", "pandoc_wheel", "--invalid-option"], check=False, capture_output=True, text=True)
    assert result.returncode != 0
    assert "Unknown option" in result.stderr


def test_docx_roundtrip(tmp_path):
    document = tmp_path / "document.docx"
    run([get_pandoc_path(), "-f", "markdown", "-o", str(document)], input="**Hello**", check=True, text=True)
    result = run([get_pandoc_path(), str(document), "-t", "html"], check=True, capture_output=True, text=True)
    assert "<strong>Hello</strong>" in result.stdout


def test_bundled_license():
    payload = Path(get_pandoc_path()).parent
    assert "GNU GENERAL PUBLIC LICENSE" in (payload / "COPYING.md").read_text()
    assert "John MacFarlane" in (payload / "COPYRIGHT").read_text()
