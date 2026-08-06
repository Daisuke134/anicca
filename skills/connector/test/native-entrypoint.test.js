"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const { runNativePass } = require("../native-pass.js");

const REPO_ROOT = path.resolve(__dirname, "../../..");

test("official native pass forwards only the bounded minimal wake contract", async () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "connector-native-minimal-"));
  const observed = [];
  try {
    const result = await runNativePass({
      repoRoot: REPO_ROOT,
      stateDir: path.join(directory, "state"),
      ownerToken: "native-pass-minimal-owner-123456",
      dependencies: Object.freeze({ boundary: "fixture" }),
      async runWake(input, dependencies) {
        observed.push({ input, dependencies });
        return Object.freeze({ status: "circuit_open", safe_reason: "fixture" });
      },
    });

    assert.deepEqual(result, { status: "circuit_open", safe_reason: "fixture" });
    assert.equal(observed.length, 1);
    assert.deepEqual(observed[0].input.providers, ["luma", "connpass"]);
    assert.equal(observed[0].input.maxConsecutiveFailures, 3);
    assert.equal(observed[0].input.maxWakeMs, 600_000);
    assert.equal(observed[0].input.maxAgentSteps, 10);
    assert.deepEqual(observed[0].dependencies, { boundary: "fixture" });
    assert.equal(fs.existsSync(path.join(directory, "state", "provider-cursor.json")), false);
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
});

test("official native pass rejects a missing production dependency boundary", async () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "connector-native-minimal-"));
  try {
    await assert.rejects(runNativePass({
      repoRoot: REPO_ROOT,
      stateDir: path.join(directory, "state"),
      ownerToken: "native-pass-minimal-owner-123456",
    }), /Connector minimal pass unavailable/);
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
});
