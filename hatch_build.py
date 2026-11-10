from hashlib import sha256
from io import BytesIO
from os import environ
from pathlib import Path
from platform import machine
from shutil import rmtree
from subprocess import run
from sys import platform
from tarfile import open as open_tar
from urllib.request import urlopen
from zipfile import ZipFile

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

PANDOC_VERSION = "3.13"
TARGETS = {
    "macosx_15_0_arm64": ("arm64-macOS.zip", "f436d18bebbfb3ddd326597686dacab9fac5dc23bd060495020f35a28a43a7c3"),
    "manylinux_2_17_x86_64.manylinux2014_x86_64": ("linux-amd64.tar.gz", "38aa33b325a2bc96a4c39409631212db55702f564250bcdbead180b3bf646389"),
    "manylinux_2_17_aarch64.manylinux2014_aarch64": ("linux-arm64.tar.gz", "21e1d4ba09bd0b334590d204580fd4f6629b21be4ab6a32b26cc98982e9e0c68"),
    "win_amd64": ("windows-x86_64.zip", "23e1f2e978a3df80db8bf65c9c59534f41a23140480cfb4f783a882ab7dc6a4e"),
    "pyemscripten_2026_0_wasm32": ("wasm.zip", "234d2020a7f3a9aab387bd35df3c17ca2ba0078a82490e2b3ede890d648d64fe"),
}
SOURCE_FILES = {
    "COPYING.md": "3ebfbf9235b049d384cdba5a66a1a3434bb544391e720b76faa8e1b3ee61a4e5",
    "COPYRIGHT": "842e33ef01625e93f85bebb8bac83aa570186b7aa77a09971257cc29f8f60740",
    "wasm/LICENSE": "17fe0a85f4cbe8ceceaa069f1a89f376cdea385b7f4d4ff3c42a797005429ebd",
    "wasm/pandoc.js": "6b07bca137feee170bffa2aefd0e5e067135a86a0b8aa4ec6da31049e6c5a36b",
}


def download(url, digest):
    cache = Path("build/downloads") / digest
    cache.parent.mkdir(parents=True, exist_ok=True)
    if not cache.exists():
        with urlopen(url) as response:
            cache.write_bytes(response.read())
    data = cache.read_bytes()
    if sha256(data).hexdigest() != digest:
        raise ValueError(f"SHA256 mismatch: {url}")
    return data


def target_platform():
    if target := environ.get("PANDOC_WHEEL_PLATFORM"):
        if target not in TARGETS:
            raise ValueError(f"Unsupported wheel platform: {target}")
        return target
    arch = environ.get("AUDITWHEEL_ARCH", machine()).lower()
    if platform == "darwin" and arch == "arm64":
        return "macosx_15_0_arm64"
    if platform == "linux" and arch in ("x86_64", "aarch64", "arm64"):
        arch = "aarch64" if arch == "arm64" else arch
        return f"manylinux_2_17_{arch}.manylinux2014_{arch}"
    if platform == "win32" and arch in ("amd64", "x86_64"):
        return "win_amd64"
    raise ValueError(f"Unsupported platform: {platform}/{arch}")


class CustomHook(BuildHookInterface):
    def initialize(self, version, build_data):
        target = target_platform()
        asset, digest = TARGETS[target]
        url = f"https://github.com/jgm/pandoc/releases/download/{PANDOC_VERSION}/pandoc-{PANDOC_VERSION}-{asset}"
        archive = download(url, digest)
        payload = Path("pandoc_wheel/bin")
        rmtree(payload, ignore_errors=True)
        payload.mkdir(parents=True)
        executable = "pandoc.wasm" if asset == "wasm.zip" else "pandoc.exe" if asset.startswith("windows") else "pandoc"
        if asset.endswith(".zip"):
            with ZipFile(BytesIO(archive)) as package:
                member = next(name for name in package.namelist() if name.rsplit("/", 1)[-1] == executable)
                (payload / executable).write_bytes(package.read(member))
        else:
            with open_tar(fileobj=BytesIO(archive), mode="r:gz") as package:
                member = next(item for item in package.getmembers() if item.name.endswith("/bin/pandoc"))
                binary = package.extractfile(member)
                assert binary is not None
                with binary:
                    (payload / executable).write_bytes(binary.read())
        (payload / executable).chmod(0o755)
        for name in ("COPYING.md", "COPYRIGHT"):
            url = f"https://raw.githubusercontent.com/jgm/pandoc/{PANDOC_VERSION}/{name}"
            (payload / name).write_bytes(download(url, SOURCE_FILES[name]))
        if asset == "wasm.zip":
            self.build_wasm(payload)
        else:
            scripts = Path("build/scripts")
            scripts.mkdir(parents=True, exist_ok=True)
            (payload / executable).replace(scripts / executable)
            build_data["shared_scripts"][str(scripts / executable)] = executable
        build_data["pure_python"] = False
        build_data["tag"] = f"py3-none-{target}"

    def build_wasm(self, payload):
        source_url = f"https://raw.githubusercontent.com/jgm/pandoc/{PANDOC_VERSION}/wasm"
        source = download(f"{source_url}/pandoc.js", SOURCE_FILES["wasm/pandoc.js"]).decode()
        source = source.replace("https://cdn.jsdelivr.net/npm/@bjorn3/browser_wasi_shim@0.3.0/dist/index.js", "@bjorn3/browser_wasi_shim")
        imports, body = source.split('const args = ["pandoc.wasm"', 1)
        body = 'const args = ["pandoc.wasm"' + body
        body = body.replace("WebAssembly.instantiateStreaming", "WebAssembly.instantiate")
        body = body.replace('fetch("./pandoc.wasm?sha1=SHA1_PANDOC_WASM")', "wasm")
        body = body.replace("export async function", "async function")
        source = imports + "export async function createPandoc(wasm) {\n" + body + "\nreturn {convert, query};\n}\n"
        Path("js/pandoc.js").write_text(source)
        npm = "npm.cmd" if platform == "win32" else "npm"
        run([npm, "ci", "--ignore-scripts"], cwd="js", check=True)
        run([npm, "run", "build"], cwd="js", check=True)
        (payload / "WASM-LICENSE").write_bytes(download(f"{source_url}/LICENSE", SOURCE_FILES["wasm/LICENSE"]))
        (payload / "WASI-LICENSE").write_bytes(Path("js/node_modules/@bjorn3/browser_wasi_shim/LICENSE-MIT").read_bytes())
