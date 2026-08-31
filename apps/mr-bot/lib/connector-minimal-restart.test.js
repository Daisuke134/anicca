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

test("minimal connector claim-only uncertainty survives restart without duplicate side effects", () => {
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
      ["photo_effect", 1],
    ];
    for (const [stage, exitCode] of effects) {
      const result = runChild(stateDir, stage);
      assertSilentAndPrivate(result, stage);
      assert.equal(result.status, exitCode, `${stage}: expected injected interruption exit code`);
    }

    const uncertainLedger = JSON.parse(fs.readFileSync(path.join(stateDir, "restart-ledger.json"), "utf8"));
    assert.deepEqual(
      [uncertainLedger.evidence_count, uncertainLedger.calendar_count, uncertainLedger.message_count, uncertainLedger.photo_count, uncertainLedger.bundle_count],
      [1, 1, 1, 0, 0],
      "message claim must fence the photo-stage restart before any duplicate delivery",
    );
    assert.equal(uncertainLedger.pid_runs.length, 4);

  } finally {
    fs.rmSync(stateDir, { recursive: true, force: true });
  }
});

test("checkpointed connector restart reuses without duplicate side effects", () => {
  const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "connector-minimal-restart-reuse-"));
  const actionHistoryFile = path.join(stateDir, "action-history.jsonl");
  const actionHistory = Buffer.from(
    '{"event":"restart_test","stage":"seed","recorded_at":"2026-08-12T00:00:00.000Z"}\n',
    "utf8",
  );
  try {
    fs.writeFileSync(actionHistoryFile, actionHistory, { flag: "wx", mode: 0o600 });
    const created = runChild(stateDir, "none");
    assertSilentAndPrivate(created, "none (created)", { allowStdout: true });
    assert.equal(created.status, 0);
    assert.equal(JSON.parse(created.stdout).disposition, "created");

    const bundleDir = path.join(stateDir, "applied-bundles");
    const bundleFile = fs.readdirSync(bundleDir)
      .filter((name) => /^[0-9a-f]{64}\.json$/.test(name))
      .map((name) => path.join(bundleDir, name))[0];
    fs.unlinkSync(bundleFile);
    fs.chmodSync(bundleDir, 0o500);
    const permissionFailure = runChild(stateDir, "none");
    assertSilentAndPrivate(permissionFailure, "none (bundle permission failure)");
    assert.notEqual(permissionFailure.status, 0);
    const failedLedger = JSON.parse(fs.readFileSync(path.join(stateDir, "restart-ledger.json"), "utf8"));
    for (const key of ["provider_count", "evidence_count", "calendar_count", "message_count", "photo_count"]) {
      assert.equal(failedLedger[key], 1, `${key}: permission failure must not duplicate effects`);
    }
    assert.equal(fs.readdirSync(bundleDir).filter((name) => /^[0-9a-f]{64}\.json$/.test(name)).length, 0);
    fs.chmodSync(bundleDir, 0o700);

    const recreated = runChild(stateDir, "none");
    assertSilentAndPrivate(recreated, "none (recreated)", { allowStdout: true });
    assert.equal(recreated.status, 0);
    assert.equal(JSON.parse(recreated.stdout).disposition, "created");
    const reused = runChild(stateDir, "none");
    assertSilentAndPrivate(reused, "none (reused)", { allowStdout: true });
    assert.equal(reused.status, 0);
    assert.equal(JSON.parse(reused.stdout).disposition, "reused");

    const ledgerFile = path.join(stateDir, "restart-ledger.json");
    assert.equal(mode(ledgerFile), 0o600);
    const ledger = JSON.parse(fs.readFileSync(ledgerFile, "utf8"));
    for (const key of ["provider_count", "evidence_count", "calendar_count", "message_count", "photo_count", "bundle_count"]) {
      assert.equal(ledger[key], 1, `${key}: exactly one effect must be recorded`);
    }
    for (const key of ["submit_count", "cache_count", "direct_count", "harness_count"]) assert.equal(ledger[key], 0);
    const messageKeys = Object.keys(ledger.message_identities || {});
    const photoKeys = Object.keys(ledger.photo_identities || {});
    assert.equal(messageKeys.length, 1);
    assert.equal(photoKeys.length, 1);
    assert.notEqual(messageKeys[0], photoKeys[0]);
    const checkpointDir = path.join(stateDir, "evidence", "checkpoints");
    const checkpointFiles = fs.readdirSync(checkpointDir)
      .filter((name) => name.endsWith(".json"))
      .map((name) => path.join(checkpointDir, name));
    assert.equal(checkpointFiles.length, 3);
    for (const file of checkpointFiles) assert.equal(mode(file), 0o600);
    const bundleFiles = fs.readdirSync(bundleDir)
      .filter((name) => /^[0-9a-f]{64}\.json$/.test(name))
      .map((name) => path.join(bundleDir, name));
    assert.equal(bundleFiles.length, 1);
    assert.equal(mode(bundleFiles[0]), 0o600);
    assert.equal(mode(actionHistoryFile), 0o600);
    assert.deepEqual(fs.readFileSync(actionHistoryFile), actionHistory);
    assert.equal(ledger.pid_runs.length, 4);
    assert.deepEqual(ledger.pid_runs.map((run) => run.stage), ["none", "none", "none", "none"]);
    assert.ok(ledger.pid_runs.every((run) => Object.keys(run).sort().join(",") === "pid,stage"));
    assert.ok(new Set(ledger.pid_runs.map((run) => run.pid)).size === ledger.pid_runs.length);

    const tamperedLedger = { ...ledger, provider_identities: {
      ...ledger.provider_identities,
      "peatix-event://event/5075819": {
        ...ledger.provider_identities["peatix-event://event/5075819"], status: "absent",
      },
    } };
    fs.writeFileSync(ledgerFile, `${JSON.stringify(tamperedLedger, null, 2)}\n`, { flag: "w", mode: 0o600 });
    const corruptedProvider = runChild(stateDir, "none");
    assertSilentAndPrivate(corruptedProvider, "none (corrupted provider ledger)");
    assert.notEqual(corruptedProvider.status, 0);
    const afterCorruption = JSON.parse(fs.readFileSync(ledgerFile, "utf8"));
    assert.equal(afterCorruption.pid_runs.length, 4);
    for (const key of ["provider_count", "evidence_count", "calendar_count", "message_count", "photo_count", "bundle_count"]) {
      assert.equal(afterCorruption[key], 1);
    }
  } finally { fs.rmSync(stateDir, { recursive: true, force: true }); }
});
