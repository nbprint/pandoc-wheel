# pandoc-wheel

Python wheels bundling [Pandoc 3.13](https://github.com/jgm/pandoc/releases/tag/3.13).

[![Build Status](https://github.com/nbprint/pandoc-wheel/actions/workflows/build.yaml/badge.svg?branch=main&event=push)](https://github.com/nbprint/pandoc-wheel/actions/workflows/build.yaml)
[![License](https://img.shields.io/github/license/nbprint/pandoc-wheel)](https://github.com/nbprint/pandoc-wheel)

## Run Pandoc

Download the matching wheel from the [build artifacts](https://github.com/nbprint/pandoc-wheel/actions/workflows/build.yaml), extract the artifact, and install it:

```bash
python -m pip install ./pandoc_wheel-*.whl
pandoc --version
pandoc input.md -o output.docx
python -m pandoc_wheel input.md -t html
```

`pandoc-cli` also passes arguments through to the bundled executable. To use the executable from Python:

```python
from subprocess import run

from pandoc_wheel.cli import get_pandoc_path

run([get_pandoc_path(), "input.md", "-o", "output.docx"], check=True)
```

Native wheels support Python 3.11+ on macOS 15+ arm64, glibc Linux x86_64 and aarch64 (manylinux2014), and Windows x64.

## Convert in Pyodide

Install the `pyemscripten_2026_0_wasm32` wheel in Pyodide 314.0.7 using its hosted URL:

```python
import micropip

await micropip.install("https://your-host/pandoc_wheel-0.1.0-py3-none-pyemscripten_2026_0_wasm32.whl")

from pandoc_wheel.pyodide import convert, query

print(await query({"query": "version"}))
result = await convert({"from": "markdown", "to": "html"}, "**Hello**")
print(result["stdout"])
```

Pass binary resources through `files`, and read output files from the result:

```python
result = await convert(
    {"from": "markdown", "to": "docx", "output-file": "document.docx"},
    "**Hello**",
)
document = result["files"]["document.docx"]  # bytes

result = await convert(
    {"from": "docx", "to": "html", "input-files": ["document.docx"]},
    files={"document.docx": document},
)
```

Options follow [Pandoc's WASM interface](https://github.com/jgm/pandoc/blob/3.13/wasm/pandoc.js). Results contain `stdout`, `stderr`, `warnings`, and `files`. Pandoc and its WASI shim are bundled; conversion needs no further downloads. The WASM sandbox cannot run external filters or PDF engines.

## Build wheels

```bash
uv venv --python 3.11
source .venv/bin/activate
make develop
make lint checks coverage build
```

Native builds download checksum-pinned upstream binaries. To build the Pyodide wheel, install Node.js and npm, then run:

```bash
PANDOC_WHEEL_PLATFORM=pyemscripten_2026_0_wasm32 python -m build -w
cd js
npm install --no-save --package-lock=false pyodide@314.0.7 playwright@1.64.1
npx playwright install chromium
PANDOC_TEST_BROWSER=1 node test-pyodide.mjs ../dist/*pyemscripten*.whl
```

CI builds and tests all five platforms. Pyodide tests run in Node.js and Chromium. Package version starts at the template's `0.1.0`; the bundled Pandoc version is pinned independently in `hatch_build.py`.

## License

The Python wrapper uses Apache-2.0; see [LICENSE](LICENSE). Bundled Pandoc uses GPL-2.0-or-later; its [source](https://github.com/jgm/pandoc/tree/3.13), [build instructions](https://github.com/jgm/pandoc/blob/3.13/INSTALL.md), copyright notice, and license are available upstream. Wheels include Pandoc's `COPYING.md` and `COPYRIGHT`. The WASM interface and WASI shim use MIT licenses, also included in the Pyodide wheel.

> [!NOTE]
> Generated with [Copier](https://copier.readthedocs.io/en/stable/) from the [Base Python Project Template](https://github.com/python-project-templates/base), following [verilator-python](https://github.com/dau-dev/verilator-python). The initial commit contains the unmodified template output.
