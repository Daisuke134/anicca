"use strict";

const assert = require("node:assert/strict");
const { spawnSync } = require("node:child_process");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const {
  appendObservation,
  buildObservation,
} = require("../lib/observer-envelope.js");

const BASE = Object.freeze({
  wake_id: "connector-wake-200",
  run_id: "connector-run-200",
  stage: "provider_discovery",
  safe_action: "browser_read",
  expected_effect: "provider_inventory",
  owner_generation: 1,
  code_commit: "27506a703",
  cursor: "connpass:2026-08-07:0:2",
  observed_at: "2026-08-06T13:36:51.928Z",
});

test("observer normalizes every terminal class into one privacy-safe schema", () => {
  for (const [observedEffect, incidentClass] of [
    ["success", "none"],
    ["tool_failure", "tool_failure"],
    ["timeout", "timeout"],
    ["process_crash", "process_crash"],
  ]) {
    const observation = buildObservation({
      ...BASE,
      observed_effect: observedEffect,
      incident_class: incidentClass,
    });
    assert.deepEqual(Object.keys(observation).sort(), [
      "code_commit", "cursor", "expected_effect", "fingerprint", "incident_class",
      "observed_at", "observed_effect", "owner_generation", "provider_readback", "run_id",
      "safe_action", "schema_version", "screenshot_sha", "stage", "wake_id",
    ]);
    assert.equal(observation.observed_effect, observedEffect);
    assert.match(observation.fingerprint, /^sha256:[0-9a-f]{64}$/);
    assert.equal(observation.screenshot_sha, "none");
    assert.equal(observation.provider_readback, "none");
  }
});

test("observer rejects raw URLs, email addresses, and secrets", () => {
  for (const privateValue of [
    "https://example.com/event/private",
    "person@example.com",
    "Bearer abcdefghijklmnopqrstuvwxyz",
  ]) {
    assert.throws(() => buildObservation({
      ...BASE,
      observed_effect: "tool_failure",
      incident_class: "tool_failure",
      cursor: privateValue,
    }), /privacy-safe/);
  }
});

test("observer appends one replay fixture per stable failure fingerprint", () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "connector-observer-"));
  const file = path.join(directory, "observer-replay.jsonl");
  try {
    const observation = buildObservation({
      ...BASE,
      observed_effect: "timeout",
      incident_class: "timeout",
    });
    assert.equal(appendObservation(file, observation), true);
    assert.equal(appendObservation(file, { ...observation, wake_id: "connector-wake-201" }), false);
    const rows = fs.readFileSync(file, "utf8").trim().split("\n").map(JSON.parse);
    assert.equal(rows.length, 1);
    assert.equal(rows[0].observed_effect, "timeout");
    assert.equal(fs.statSync(file).mode & 0o777, 0o600);
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
});

test("observer CLI persists a process crash when the shell parent survives", () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "connector-observer-crash-"));
  const file = path.join(directory, "observer-replay.jsonl");
  try {
    const result = spawnSync(process.execPath, [
      path.resolve(__dirname, "../lib/observer-envelope.js"),
      "process-crash", file, "wake:connector-202", "run:connector-202", "27506a703",
    ], { encoding: "utf8" });
    assert.equal(result.status, 0, result.stderr);
    const row = JSON.parse(fs.readFileSync(file, "utf8").trim());
    assert.equal(row.observed_effect, "process_crash");
    assert.equal(row.incident_class, "process_crash");
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
});
