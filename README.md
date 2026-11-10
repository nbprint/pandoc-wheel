# pandoc-wheel

[Pandoc 3.13](https://github.com/jgm/pandoc/releases/tag/3.13) binaries distributed as Python wheels.

[![Build Status](https://github.com/nbprint/pandoc-wheel/actions/workflows/build.yaml/badge.svg?branch=main&event=push)](https://github.com/nbprint/pandoc-wheel/actions/workflows/build.yaml)
[![License](https://img.shields.io/github/license/nbprint/pandoc-wheel)](https://github.com/nbprint/pandoc-wheel)

## Run Pandoc

Download the matching wheel from the [build artifacts](https://github.com/nbprint/pandoc-wheel/actions/workflows/build.yaml), extract the artifact, and install it:

```bash
python -m pip install ./pandoc_wheel-*.whl
pandoc --version
pandoc input.md -o output.docx
```

Native wheels install the upstream executable directly into the environment's scripts directory (`bin` or `Scripts`). Supported platforms: macOS 15+ arm64, glibc Linux x86_64 and aarch64 (manylinux2014), and Windows x64. Wheels require Python 3.11+.

For a Python API, install [pandoc](https://pypi.org/project/pandoc/) or [pypandoc](https://pypi.org/project/pypandoc/) separately. For example:

```bash
python -m pip install pypandoc
```

```python
import pypandoc

html = pypandoc.convert_text("**Hello**", "html", format="markdown")
```

The binary distribution has no runtime dependencies. Applications can depend on both it and their chosen Python wrapper.

## Load Pandoc in Pyodide

The `pyemscripten_2026_0_wasm32` wheel contains `pandoc.wasm`, the upstream JavaScript interface bundled as `pandoc.mjs`, and its WASI shim. Install it in Pyodide 314.0.7, then load those assets from JavaScript using an initialized `pyodide` instance:

```javascript
await pyodide.loadPackage("micropip");
await pyodide.runPythonAsync(`
import micropip
await micropip.install("https://your-host/pandoc_wheel-0.1.0-py3-none-pyemscripten_2026_0_wasm32.whl")
`);
const payload = pyodide.runPython(`
from importlib.resources import files
str(files("pandoc_wheel") / "bin")
`);
const source = pyodide.FS.readFile(`${payload}/pandoc.mjs`, {encoding: "utf8"});
const {createPandoc} = await import(`data:text/javascript;charset=utf-8,${encodeURIComponent(source)}`);
const pandoc = await createPandoc(pyodide.FS.readFile(`${payload}/pandoc.wasm`));
const result = await pandoc.convert({from: "markdown", to: "html"}, "**Hello**", {});
console.log(result.stdout);
```

Use [Pandoc's WASM interface](https://github.com/jgm/pandoc/blob/3.13/wasm/pandoc.js) for options, queries, and binary files. Conversion uses the bundled assets without further downloads. Native Python wrappers use subprocesses and cannot execute this WASI module in Pyodide. The WASM sandbox cannot run external filters or PDF engines.

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

CI builds and tests all five platforms. Native tests verify the installed executable and pypandoc compatibility. Pyodide tests install the wheel and exercise the upstream WASM interface in Node.js and Chromium. The bundled Pandoc version is pinned in `hatch_build.py`.

## License

Packaging code uses Apache-2.0; see [LICENSE](LICENSE). Bundled Pandoc uses GPL-2.0-or-later; its [source](https://github.com/jgm/pandoc/tree/3.13), [build instructions](https://github.com/jgm/pandoc/blob/3.13/INSTALL.md), copyright notice, and license are available upstream. Wheels include Pandoc's `COPYING.md` and `COPYRIGHT`. The WASM interface and WASI shim use MIT licenses, also included in the Pyodide wheel.

> [!NOTE]
> This library was generated using [copier](https://copier.readthedocs.io/en/stable/) from the [Base Python Project Template repository](https://github.com/python-project-templates/base).
