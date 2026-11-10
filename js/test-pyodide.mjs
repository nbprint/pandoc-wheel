import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
import {createServer} from "node:http";
import {basename, resolve} from "node:path";
import {loadPyodide} from "pyodide";

const wheel = resolve(process.argv[2]);
const server = createServer(async (request, response) => {
  response.setHeader("Access-Control-Allow-Origin", "*");
  if (request.url === "/") {
    response.setHeader("Content-Type", "text/html");
    response.end("<!doctype html><title>Pandoc wheel test</title>");
  } else {
    response.end(await readFile(wheel));
  }
});
await new Promise(resolve => server.listen(0, "127.0.0.1", resolve));
const wheelUrl = `http://127.0.0.1:${server.address().port}/${basename(wheel)}`;
async function testWheel(wheelUrl) {
  const pyodide = await loadPyodide();
  await pyodide.loadPackage("micropip");
  await pyodide.runPythonAsync(`import micropip\nawait micropip.install(${JSON.stringify(wheelUrl)})`);
  const payload = pyodide.runPython(`from importlib.resources import files\nstr(files("pandoc_wheel") / "bin")`);
  const source = pyodide.FS.readFile(`${payload}/pandoc.mjs`, {encoding: "utf8"});
  const {createPandoc} = await import(`data:text/javascript;charset=utf-8,${encodeURIComponent(source)}`);
  const pandoc = await createPandoc(pyodide.FS.readFile(`${payload}/pandoc.wasm`));
  if (await pandoc.query({query: "version"}) !== "3.13") {
    throw new Error("Unexpected Pandoc version");
  }
  for (const text of ["Hello", "Héllo 世界", "Hello again"]) {
    const result = await pandoc.convert({from: "markdown", to: "html"}, `**${text}**`, {});
    if (result.stdout.trim() !== `<p><strong>${text}</strong></p>`) {
      throw new Error(`Unexpected HTML: ${result.stdout}`);
    }
  }
  const documentFiles = {};
  await pandoc.convert({from: "markdown", to: "docx", "output-file": "document.docx"}, "**Hello**", documentFiles);
  const document = documentFiles["document.docx"];
  const signature = new Uint8Array(await document.arrayBuffer());
  if (signature[0] !== 80 || signature[1] !== 75) {
    throw new Error("Invalid DOCX output");
  }
  const result = await pandoc.convert(
    {from: "docx", to: "html", "input-files": ["document.docx"]},
    null,
    {"document.docx": document},
  );
  if (!result.stdout.includes("<strong>Hello</strong>")) {
    throw new Error(`Unexpected DOCX conversion: ${result.stdout}`);
  }
  return true;
}

try {
  assert.equal(await testWheel(wheelUrl), true);
  console.log("Pyodide Node conversion tests passed");

  if (process.env.PANDOC_TEST_BROWSER === "1") {
    const {chromium} = await import("playwright");
    const browser = await chromium.launch({headless: true});
    try {
      const page = await browser.newPage();
      page.on("console", message => console.log("browser:", message.text()));
      await page.goto(`http://127.0.0.1:${server.address().port}/`);
      await page.addScriptTag({url: "https://cdn.jsdelivr.net/pyodide/v314.0.7/full/pyodide.js"});
      assert.equal(await page.evaluate(testWheel, wheelUrl), true);
      console.log("Pyodide browser conversion tests passed");
    } finally {
      await browser.close();
    }
  }
} finally {
  server.close();
}
