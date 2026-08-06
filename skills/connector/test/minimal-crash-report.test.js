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
        HOME: directory,
        GOG_ACCOUNT: "private-account",
        GOG_KEYRING_PASSWORD: "private-keyring",
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
