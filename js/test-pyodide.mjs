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
const test = `
from pandoc_wheel.pyodide import convert, query

assert await query({"query": "version"}) == "3.13"
for text in ("Hello", "Héllo 世界", "Hello again"):
    result = await convert({"from": "markdown", "to": "html"}, "**" + text + "**")
    assert result["stdout"].strip() == "<p><strong>" + text + "</strong></p>", result

result = await convert(
    {"from": "markdown", "to": "docx", "output-file": "document.docx"}, "**Hello**"
)
document = result["files"]["document.docx"]
assert document.startswith(b"PK"), result
result = await convert(
    {"from": "docx", "to": "html", "input-files": ["document.docx"]},
    files={"document.docx": document},
)
assert "<strong>Hello</strong>" in result["stdout"], result
`;

try {
  const pyodide = await loadPyodide();
  await pyodide.loadPackage("micropip");
  await pyodide.runPythonAsync(`import micropip\nawait micropip.install(${JSON.stringify(wheelUrl)})`);
  await pyodide.runPythonAsync(test);
  console.log("Pyodide Node conversion tests passed");

  if (process.env.PANDOC_TEST_BROWSER === "1") {
    const {chromium} = await import("playwright");
    const browser = await chromium.launch({headless: true});
    try {
      const page = await browser.newPage();
      page.on("console", message => console.log("browser:", message.text()));
      await page.goto(`http://127.0.0.1:${server.address().port}/`);
      await page.addScriptTag({url: "https://cdn.jsdelivr.net/pyodide/v314.0.7/full/pyodide.js"});
      assert.equal(await page.evaluate(async ({wheelUrl, test}) => {
        const pyodide = await loadPyodide();
        await pyodide.loadPackage("micropip");
        await pyodide.runPythonAsync(`import micropip\nawait micropip.install(${JSON.stringify(wheelUrl)})`);
        await pyodide.runPythonAsync(test);
        return true;
      }, {wheelUrl, test}), true);
      console.log("Pyodide browser conversion tests passed");
    } finally {
      await browser.close();
    }
  }
} finally {
  server.close();
}
