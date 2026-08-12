"use strict";

const assert = require("node:assert/strict");
const { spawnSync } = require("node:child_process");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const CHILD = path.join(__dirname, "connector-minimal-restart-child.js");
const FORBIDDEN_OUTPUT = [
  /https:\/\/peatix\.com\/event\/5075819/,
  /peatix-event:\/\/event\/5075819/,
  /Restart Fixture Event/,
  /private-target/,
  /dais-local/,
];

function runChild(stateDir, stage) {
  return spawnSync(process.execPath, [CHILD, stateDir, stage], {
    encoding: "utf8",
    maxBuffer: 1_024 * 1_024,
  });
}

function assertSilentAndPrivate(result, stage, { allowStdout = false } = {}) {
  assert.equal(result.error, undefined, `${stage}: child process should spawn`);
  const output = `${result.stdout}\n${result.stderr}`;
  if (!allowStdout) assert.equal(result.stdout, "", `${stage}: stdout must be silent`);
  assert.equal(result.stderr, "", `${stage}: stderr must be silent`);
  for (const forbidden of FORBIDDEN_OUTPUT) {
    assert.doesNotMatch(output, forbidden, `${stage}: child output leaked ${forbidden}`);
  }
}

function mode(file) {
  return fs.statSync(file).mode & 0o777;
}

test("minimal connector effects survive restart without duplicate side effects", () => {
  const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "connector-minimal-restart-"));
  const actionHistoryFile = path.join(stateDir, "action-history.jsonl");
  const actionHistory = Buffer.from(
    '{"event":"restart_test","stage":"seed","recorded_at":"2026-08-12T00:00:00.000Z"}\n',
    "utf8",
  );
  try {
    fs.writeFileSync(actionHistoryFile, actionHistory, { flag: "wx", mode: 0o600 });
    fs.chmodSync(actionHistoryFile, 0o600);
    const effects = [
      ["evidence_effect", 42],
      ["calendar_effect", 43],
      ["message_effect", 44],
      ["photo_effect", 45],
    ];
    for (const [stage, exitCode] of effects) {
      const result = runChild(stateDir, stage);
      assertSilentAndPrivate(result, stage);
      assert.equal(result.status, exitCode, `${stage}: expected injected interruption exit code`);
    }

    fs.chmodSync(stateDir, 0o700);
    const bundleDir = path.join(stateDir, "applied-bundles");
    fs.mkdirSync(bundleDir, { recursive: true, mode: 0o700 });
    fs.chmodSync(bundleDir, 0o700);
    try {
      fs.chmodSync(bundleDir, 0o500);
      const permissionFailure = runChild(stateDir, "none");
      assertSilentAndPrivate(permissionFailure, "none (bundle permission failure)");
      assert.notEqual(permissionFailure.status, 0, "bundle permission failure must not succeed");

      const failedLedger = JSON.parse(fs.readFileSync(path.join(stateDir, "restart-ledger.json"), "utf8"));
      for (const key of ["provider_count", "evidence_count", "calendar_count", "message_count", "photo_count"]) {
        assert.equal(failedLedger[key], 1, `${key}: permission failure must not duplicate effects`);
      }
      assert.equal(failedLedger.bundle_count, 0, "permission failure must not create a bundle");
    } finally {
      fs.chmodSync(bundleDir, 0o700);
    }

    const created = runChild(stateDir, "none");
    assertSilentAndPrivate(created, "none (created)", { allowStdout: true });
    assert.equal(created.status, 0);
    const createdJson = JSON.parse(created.stdout);
    assert.deepEqual(Object.keys(createdJson).sort(), ["disposition", "pid"]);
    assert.equal(createdJson.disposition, "created");
    assert.ok(Number.isInteger(createdJson.pid) && createdJson.pid > 0);

    const reused = runChild(stateDir, "none");
    assertSilentAndPrivate(reused, "none (reused)", { allowStdout: true });
    assert.equal(reused.status, 0);
    const reusedJson = JSON.parse(reused.stdout);
    assert.deepEqual(Object.keys(reusedJson).sort(), ["disposition", "pid"]);
    assert.equal(reusedJson.disposition, "reused");
    assert.ok(Number.isInteger(reusedJson.pid) && reusedJson.pid > 0);

    const ledgerFile = path.join(stateDir, "restart-ledger.json");
    assert.equal(mode(ledgerFile), 0o600);
    const ledger = JSON.parse(fs.readFileSync(ledgerFile, "utf8"));
    for (const key of ["provider_count", "evidence_count", "calendar_count", "message_count", "photo_count", "bundle_count"]) {
      assert.equal(ledger[key], 1, `${key}: exactly one effect must be recorded`);
    }
    for (const key of ["submit_count", "cache_count", "direct_count", "harness_count"]) {
      assert.equal(ledger[key], 0, `${key}: non-native side effects must remain unused`);
    }

    const messageKeys = Object.keys(ledger.message_identities || {});
    const photoKeys = Object.keys(ledger.photo_identities || {});
    assert.equal(messageKeys.length, 1);
    assert.equal(photoKeys.length, 1);
    assert.notEqual(messageKeys[0], photoKeys[0], "message and photo idempotency keys must be distinct");

    const checkpointDir = path.join(stateDir, "evidence", "checkpoints");
    const checkpointFiles = fs.readdirSync(checkpointDir)
      .filter((name) => name.endsWith(".json"))
      .map((name) => path.join(checkpointDir, name));
    assert.equal(checkpointFiles.length, 3, "evidence, message, and photo checkpoints must be present");
    for (const file of checkpointFiles) assert.equal(mode(file), 0o600, `${file}: checkpoint must be private`);

    const bundleFiles = fs.readdirSync(bundleDir)
      .filter((name) => /^[0-9a-f]{64}\.json$/.test(name))
      .map((name) => path.join(bundleDir, name));
    assert.equal(bundleFiles.length, 1, "exactly one applied bundle must exist");
    assert.equal(mode(bundleFiles[0]), 0o600, "applied bundle must be private");

    assert.equal(mode(actionHistoryFile), 0o600, "action history must be private");
    assert.deepEqual(fs.readFileSync(actionHistoryFile), actionHistory, "action history must remain byte-identical");

    const pidRuns = ledger.pid_runs;
    assert.ok(Array.isArray(pidRuns), "ledger must record child process runs");
    assert.equal(pidRuns.length, 7, "all crash, failure, create, and reuse invocations must be recorded");
    const expectedStages = [
      "evidence_effect",
      "calendar_effect",
      "message_effect",
      "photo_effect",
      "none",
      "none",
      "none",
    ];
    assert.deepEqual(pidRuns.map((run) => run.stage), expectedStages);
    assert.ok(pidRuns.every((run) => Object.keys(run).sort().join(",") === "pid,stage"));
    assert.ok(pidRuns.every((run) => Number.isInteger(run.pid) && run.pid > 0));
    assert.equal(createdJson.pid, pidRuns[5].pid, "created result must identify its child process");
    assert.equal(reusedJson.pid, pidRuns[6].pid, "reused result must identify its child process");
    assert.equal(new Set(pidRuns.map((run) => run.pid)).size, pidRuns.length, "each invocation must be a separate OS process");

    const tamperedLedger = { ...ledger, provider_identities: {
      ...ledger.provider_identities,
      "peatix-event://event/5075819": {
        ...ledger.provider_identities["peatix-event://event/5075819"],
        status: "absent",
      },
    } };
    fs.writeFileSync(ledgerFile, `${JSON.stringify(tamperedLedger, null, 2)}\n`, { flag: "w", mode: 0o600 });
    fs.chmodSync(ledgerFile, 0o600);
    const corruptedProvider = runChild(stateDir, "none");
    assertSilentAndPrivate(corruptedProvider, "none (corrupted provider ledger)");
    assert.notEqual(corruptedProvider.status, 0, "corrupted provider readback must fail closed");

    const afterCorruption = JSON.parse(fs.readFileSync(ledgerFile, "utf8"));
    assert.equal(mode(ledgerFile), 0o600);
    assert.equal(afterCorruption.provider_identities["peatix-event://event/5075819"].status, "absent");
    assert.equal(afterCorruption.pid_runs.length, 7, "invalid provider readback must not append a process run");
    for (const key of ["provider_count", "evidence_count", "calendar_count", "message_count", "photo_count", "bundle_count"]) {
      assert.equal(afterCorruption[key], 1, `${key}: invalid provider readback must not duplicate effects`);
    }
  } finally {
    fs.rmSync(stateDir, { recursive: true, force: true });
  }
});
