"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawnSync } = require("node:child_process");
const test = require("node:test");

const appDir = path.resolve(__dirname, "..");

test("installer renders a secret-free launchd plist and owner-only bridge token", () => {
  const home = fs.mkdtempSync(path.join(os.tmpdir(), "lm-connector-bridge-"));
  const result = spawnSync("/bin/bash", [path.join(__dirname, "install-connector-host-bridge-launchd.sh")], {
    cwd: appDir,
    env: { ...process.env, HOME: home, LM_CONNECTOR_BRIDGE_RENDER_ONLY: "1" },
    encoding: "utf8",
  });
  assert.equal(result.status, 0, result.stderr);
  const plistPath = path.join(home, "Library/LaunchAgents/ai.anicca.life-manager-connector-host-bridge.plist");
  const tokenPath = path.join(home, ".local/state/life-manager/connector-host-bridge/token");
  const plist = fs.readFileSync(plistPath, "utf8");
  const token = fs.readFileSync(tokenPath, "utf8").trim();
  assert.match(token, /^[0-9a-f]{64}$/);
  assert.equal(fs.statSync(tokenPath).mode & 0o777, 0o600);
  assert.equal(fs.statSync(path.dirname(tokenPath)).mode & 0o777, 0o700);
  assert.match(plist, /connector-host-bridge-boot\.sh/);
  assert.match(plist, new RegExp(home.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
  assert.doesNotMatch(plist, new RegExp(token));
  assert.doesNotMatch(plist, /GOG_KEYRING_PASSWORD|GOOGLE_API_KEY_DIRECTIONS|LM_CONNECTOR_BRIDGE_TOKEN<\/key>/);
});

test("boot entrypoint reads the existing env and token files without embedding values", () => {
  const boot = fs.readFileSync(path.join(__dirname, "connector-host-bridge-boot.sh"), "utf8");
  assert.match(boot, /\.openclaw\/\.env/);
  assert.match(boot, /connector-host-bridge\/token/);
  assert.match(boot, /LM_CONNECTOR_BRIDGE_TOKEN/);
  assert.match(boot, /connector-host-bridge-server\.js/);
  assert.doesNotMatch(boot, /postgresql:\/\/|keiodaisuke@|AIza|[0-9a-f]{64}/i);
});
