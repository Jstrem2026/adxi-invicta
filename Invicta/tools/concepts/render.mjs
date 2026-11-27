// Render concept images for buildings from their scenes (tools/concepts/scene.py).
//
//   cd Invicta/tools/concepts && npm i three@0.170.0 playwright   (once; not part of the site)
//   python ../concepts/scene.py D5/atrium-plaza /tmp/scenes
//   node render.mjs /tmp/scenes ../../data/renders/D5/atrium-plaza
//
// Serves this folder on a local port, opens render.html in headless Chromium, draws each scene and saves a
// 1280 x 800 PNG next to the WebP the site uses (the PNG is deleted after conversion by convert.py).
import { chromium } from "playwright";
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const [scenesDir, outDir, ...only] = process.argv.slice(2);
fs.mkdirSync(outDir, { recursive: true });
const types = { ".html": "text/html", ".js": "text/javascript", ".mjs": "text/javascript", ".json": "application/json" };
const server = http.createServer((req, res) => {
  const p = path.join(here, decodeURIComponent(req.url.split("?")[0]));
  if (!p.startsWith(here) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { "Content-Type": types[path.extname(p)] || "application/octet-stream" });
  fs.createReadStream(p).pipe(res);
});
await new Promise((r) => server.listen(0, "127.0.0.1", r));
const port = server.address().port;
const browser = await chromium.launch({ args: ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"] });
const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
page.on("pageerror", (e) => console.error("page error:", e.message));
const files = fs.readdirSync(scenesDir).filter((f) => f.endsWith(".json") && (!only.length || only.some((o) => f.includes(o))));
let n = 0;
for (const f of files) {
  const S = JSON.parse(fs.readFileSync(path.join(scenesDir, f), "utf8"));
  await page.goto(`http://127.0.0.1:${port}/render.html`);
  await page.waitForFunction(() => window.__ready === true, null, { timeout: 60000 });
  await page.evaluate((s) => window.renderScene(s), S);
  await page.screenshot({ path: path.join(outDir, S.id + ".png") });
  n++;
  if (n % 10 === 0) console.log(`${n}/${files.length}`);
}
await browser.close();
server.close();
console.log(`rendered ${n}`);
