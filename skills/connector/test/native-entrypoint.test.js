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

test("official native pass builds the production dependency boundary from allowlisted config", async () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "connector-native-minimal-"));
  const observed = [];
  try {
    const result = await runNativePass({
      repoRoot: REPO_ROOT,
      stateDir: path.join(directory, "state"),
      ownerToken: "native-pass-minimal-owner-123456",
      env: {
        GOG_ACCOUNT: "private-account",
        GOG_KEYRING_PASSWORD: "private-keyring",
        LM_CONNECTOR_TELEGRAM_TARGET: "private-target",
        LM_CONNECTOR_TENANT_ID: "dais-local",
        LM_CONNECTOR_CALENDAR_ID: "primary",
      },
      createDependencies(input) {
        observed.push(["factory", input]);
        return Object.freeze({ boundary: "production" });
      },
      async runWake(input, dependencies) {
        observed.push(["wake", input, dependencies]);
        return Object.freeze({ status: "completed_no_effect", safe_reason: "providers_exhausted" });
      },
    });
    assert.deepEqual(result, { status: "completed_no_effect", safe_reason: "providers_exhausted" });
    assert.equal(observed[0][0], "factory");
    assert.equal(observed[0][1].calendarAccount, "private-account");
    assert.equal(observed[0][1].gogKeyring, "private-keyring");
    assert.equal(observed[0][1].telegramTarget, "private-target");
    assert.match(observed[0][1].wakeId, /^wake-[0-9a-f]{24}$/);
    assert.equal(observed[0][1].wakeId.includes("native-pass-minimal-owner"), false);
    assert.deepEqual(observed[1][2], { boundary: "production" });
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
});

test("native config resolves the existing Telegram owner without an inline shell parser", async () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "connector-native-owner-"));
  const ownerFile = path.join(directory, ".openclaw", "credentials", "telegram-default-allowFrom.json");
  fs.mkdirSync(path.dirname(ownerFile), { recursive: true, mode: 0o700 });
  fs.writeFileSync(ownerFile, `${JSON.stringify({ allowFrom: ["123456789"] })}\n`, { mode: 0o600 });
  let factoryInput;
  try {
    await runNativePass({
      repoRoot: REPO_ROOT,
      stateDir: path.join(directory, "state"),
      ownerToken: "native-pass-minimal-owner-123456",
      env: {
        HOME: directory,
        GOG_ACCOUNT: "private-account",
        GOG_KEYRING_PASSWORD: "private-keyring",
      },
      createDependencies(input) {
        factoryInput = input;
        return Object.freeze({ boundary: "production" });
      },
      async runWake() { return { status: "completed_no_effect" }; },
    });
    assert.equal(factoryInput.telegramTarget, "123456789");
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
});
