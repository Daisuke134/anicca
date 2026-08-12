"use strict";

const assert = require("node:assert/strict");
const { spawnSync } = require("node:child_process");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const REPO_ROOT = path.resolve(__dirname, "../../..");
const RENDERER = path.join(REPO_ROOT, "skills/connector/render-launchd.sh");

test("production renderer emits one daily Connector owner and no retry sidecars", () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "connector-minimal-launchd-"));
  try {
    const outputDir = path.join(directory, "rendered");
    const result = spawnSync("bash", [
      RENDERER,
      "--output-dir", outputDir,
      "--repo-root", REPO_ROOT,
      "--life-manager-home", path.join(directory, "life-manager-home"),
    ], { encoding: "utf8", env: { ...process.env, HOME: directory } });

    assert.equal(result.status, 0, result.stderr);
    assert.deepEqual(fs.readdirSync(outputDir), [
      "ai.anicca.life-manager-connector-native.plist",
    ]);
    const plist = fs.readFileSync(path.join(
      outputDir, "ai.anicca.life-manager-connector-native.plist",
    ), "utf8");
    assert.match(plist, /<key>StartCalendarInterval<\/key>/);
    assert.doesNotMatch(plist, /<key>StartInterval<\/key>/);
    assert.doesNotMatch(plist, /healthcheck|healer|host-bridge|:9223/i);
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
});
