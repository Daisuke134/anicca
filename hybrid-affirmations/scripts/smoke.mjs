import { spawnSync } from "node:child_process";
import { readdirSync, readFileSync, statSync } from "node:fs";

const test = spawnSync(process.execPath, ["--test", "test/logic.test.mjs"], {
  stdio: "inherit",
});
if (test.status !== 0) process.exit(test.status ?? 1);

const build = spawnSync(process.execPath, ["node_modules/vite/bin/vite.js", "build"], {
  stdio: "inherit",
});
if (build.status !== 0) process.exit(build.status ?? 1);

const assets = readdirSync("dist/assets").filter((name) => name.endsWith(".js"));
const bundle = assets.map((name) => readFileSync(`dist/assets/${name}`, "utf8")).join("\n");
for (const needle of [
  "prefer_on_device",
  "gemini-3.5-flash-lite",
  "initializeDeviceModel",
  "inferenceSource",
  "FIREBASE_APPCHECK_DEBUG_TOKEN",
]) {
  if (!bundle.includes(needle)) {
    console.error(`smoke: built bundle is missing ${needle}`);
    process.exit(1);
  }
}

const html = readFileSync("dist/index.html", "utf8");
if (!html.includes("firebase-config.js")) {
  console.error("smoke: built page is missing firebase-config.js");
  process.exit(1);
}
if (!statSync("dist/firebase-config.js").isFile()) {
  console.error("smoke: dist is missing firebase-config.js");
  process.exit(1);
}

console.log(`smoke ok (${assets.length} js assets, index ${statSync("dist/index.html").size} bytes)`);
