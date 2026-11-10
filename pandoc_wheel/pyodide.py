from asyncio import Lock
from base64 import b64encode
from importlib import import_module
from pathlib import Path
from typing import Any

_instance = None
_lock = Lock()


async def _get_instance():
    global _instance
    js: Any = import_module("js")
    to_js = import_module("pyodide.ffi").to_js
    if _instance is None:
        payload = Path(__file__).parent / "bin"
        source = b64encode((payload / "pandoc.mjs").read_bytes()).decode()
        module = await js.eval("url => import(url)")(f"data:text/javascript;base64,{source}")
        _instance = await module.createPandoc(to_js((payload / "pandoc.wasm").read_bytes()))
    return _instance, js, to_js


async def query(options: dict):
    """Query Pandoc using its WASM options interface."""
    async with _lock:
        instance, js, to_js = await _get_instance()
        result = await instance.query(to_js(options, dict_converter=js.Object.fromEntries))
        return result.to_py() if hasattr(result, "to_py") else result


async def convert(options: dict, stdin: str | None = None, files: dict[str, bytes] | None = None) -> dict:
    """Convert a document with Pandoc's WASM API, returning output and files."""
    async with _lock:
        instance, js, to_js = await _get_instance()
        js_files = js.Object.new()
        for name, data in (files or {}).items():
            js.Reflect.set(js_files, name, js.Blob.new(to_js([data])))
        result = await instance.convert(to_js(options, dict_converter=js.Object.fromEntries), stdin, js_files)
        output = result.to_py()
        output["files"] = {}
        for name in js.Object.keys(js_files).to_py():
            blob = js.Reflect.get(js_files, name)
            output["files"][name] = bytes(js.Uint8Array.new(await blob.arrayBuffer()).to_py())
        return output
