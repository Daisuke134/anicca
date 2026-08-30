"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const { reportMinimalCrash } = require("../minimal-crash-report.js");

test("process crash reports through minimal operations without restarting the Connector", async () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "connector-minimal-crash-"));
  const observed = [];
  try {
    const result = await reportMinimalCrash({
      repoRoot: path.resolve(__dirname, "../../.."),
      stateDir: path.join(directory, "state"),
      ownerToken: "crash-owner-token-123456789",
      env: {
        LM_CONNECTOR_TELEGRAM_TARGET: "private-target",
      },
      createOperations(input) {
        observed.push(["operations", input]);
        return {
          async reportWake(report) {
            observed.push(["report", report]);
            return { telegram_provider_id: "9201" };
          },
        };
      },
    });
    assert.deepEqual(result, { telegram_provider_id: "9201" });
    assert.deepEqual(observed[1], ["report", {
      status: "circuit_open",
      safe_reason: "process_crash",
      consecutive_failure_count: 0,
    }]);
    assert.equal(observed.some(([name]) => name === "browser" || name === "calendar" || name === "submit"), false);
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
});

test("production-like crash report sends directly, persists claim and delivery, and replays zero times", async () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "connector-minimal-crash-production-"));
  const stateDir = path.join(directory, "state");
  const sharedEnvFile = path.join(directory, "life-manager.env");
  fs.writeFileSync(sharedEnvFile, "TELEGRAM_BOT_TOKEN=fixture-telegram-token\n", { mode: 0o600 });
  const originalFetch = globalThis.fetch;
  const originalTimeout = AbortSignal.timeout;
  const timeoutCalls = [];
  const requests = [];
  AbortSignal.timeout = (milliseconds) => {
    timeoutCalls.push(milliseconds);
    return originalTimeout(milliseconds);
  };
  globalThis.fetch = async (url, options) => {
    requests.push({ url, options });
    return { async json() { return { ok: true, result: { message_id: 9301 } }; } };
  };
  const env = {
    LM_CONNECTOR_SHARED_ENV_FILE: sharedEnvFile,
    LM_CONNECTOR_TELEGRAM_TARGET: "123456789",
  };
  try {
    const input = {
      repoRoot: path.resolve(__dirname, "../../.."), stateDir,
      ownerToken: "crash-production-owner-token-123456",
      env,
    };
    assert.deepEqual(await reportMinimalCrash(input), { telegram_provider_id: "9301" });
    assert.deepEqual(await reportMinimalCrash(input), { telegram_provider_id: "9301" });
    assert.equal(requests.length, 1);
    assert.equal(requests[0].url, "https://api.telegram.org/botfixture-telegram-token/sendMessage");
    assert.equal(requests[0].options.signal instanceof AbortSignal, true);
    assert.deepEqual(timeoutCalls, [20_000]);

    const deliveryRows = fs.readFileSync(path.join(stateDir, "wake-report-deliveries.jsonl"), "utf8").trim().split("\n").map(JSON.parse);
    const claimRows = fs.readFileSync(path.join(stateDir, "wake-report-send-claims.jsonl"), "utf8").trim().split("\n").map(JSON.parse);
    assert.deepEqual(deliveryRows.map((row) => row.telegram_provider_id), ["9301"]);
    assert.equal(claimRows.length, 1);
    assert.doesNotMatch(JSON.stringify({ deliveryRows, claimRows }), /fixture-telegram-token|123456789/);
  } finally {
    globalThis.fetch = originalFetch;
    AbortSignal.timeout = originalTimeout;
    fs.rmSync(directory, { recursive: true, force: true });
  }
});
