"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const { createMinimalProductionOperations } = require("./connector-minimal-operations.js");

test("operations persist safe history and a positive every-wake Telegram receipt", async () => {
  const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "connector-minimal-operations-"));
  const sent = [];
  try {
    const operations = createMinimalProductionOperations({
      stateDir,
      wakeId: "wake-20260807-001",
      telegramTarget: "private-target",
      now: () => new Date("2026-08-07T08:30:00.000Z"),
      async sendMessage(message, options) {
        sent.push({ message, options });
        return { messageId: 7001 };
      },
    });

    await operations.recordAction({
      purpose: "readback",
      method: "provider_state",
      timestamp: "2026-08-07T08:29:59.000Z",
      result: "success",
      duration_ms: 25,
    });
    const first = await operations.reportWake({
      status: "circuit_open",
      safe_reason: "consecutive_failure_limit",
      consecutive_failure_count: 3,
    });
    const duplicate = await operations.reportWake({
      status: "circuit_open",
      safe_reason: "consecutive_failure_limit",
      consecutive_failure_count: 3,
    });

    assert.deepEqual(first, { telegram_provider_id: "7001" });
    assert.deepEqual(duplicate, first);
    assert.equal(sent.length, 1);
    assert.equal(sent[0].options.telegramTarget, "private-target");
    assert.match(sent[0].message, /^Connector:::/);
    assert.match(sent[0].message, /circuit_open/);
    assert.doesNotMatch(sent[0].message, /private-target/);

    const historyFile = path.join(stateDir, "action-history.jsonl");
    const reportFile = path.join(stateDir, "wake-reports.jsonl");
    const deliveryFile = path.join(stateDir, "wake-report-deliveries.jsonl");
    const history = JSON.parse(fs.readFileSync(historyFile, "utf8").trim());
    const report = JSON.parse(fs.readFileSync(reportFile, "utf8").trim());
    const delivery = JSON.parse(fs.readFileSync(deliveryFile, "utf8").trim());
    assert.deepEqual(Object.keys(history).sort(), [
      "duration_ms", "method", "purpose", "result", "schema_version", "timestamp", "wake_id",
    ]);
    assert.deepEqual(Object.keys(report).sort(), [
      "consecutive_failure_count", "created_at", "safe_reason", "schema_version", "status", "wake_id",
    ]);
    assert.deepEqual(Object.keys(delivery).sort(), [
      "delivered_at", "schema_version", "telegram_provider_id", "wake_id",
    ]);
    assert.equal(JSON.stringify({ history, report, delivery }).includes("private-target"), false);
    assert.equal(fs.statSync(historyFile).mode & 0o777, 0o600);
    assert.equal(fs.statSync(reportFile).mode & 0o777, 0o600);
    assert.equal(fs.statSync(deliveryFile).mode & 0o777, 0o600);
  } finally {
    fs.rmSync(stateDir, { recursive: true, force: true });
  }
});

test("a later wake retries a durable Telegram report left pending by send failure", async () => {
  const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "connector-minimal-retry-"));
  try {
    const failed = createMinimalProductionOperations({
      stateDir,
      wakeId: "wake-20260807-failed",
      telegramTarget: "private-target",
      now: () => new Date("2026-08-07T08:30:00.000Z"),
      async sendMessage() { throw new Error("temporary transport failure"); },
    });
    await assert.rejects(() => failed.reportWake({
      status: "completed_no_effect",
      safe_reason: "providers_exhausted",
      consecutive_failure_count: 0,
    }));

    const sent = [];
    const recovered = createMinimalProductionOperations({
      stateDir,
      wakeId: "wake-20260808-recovered",
      telegramTarget: "private-target",
      now: () => new Date("2026-08-08T08:30:00.000Z"),
      async sendMessage(message) {
        sent.push(message);
        return { messageId: 8000 + sent.length };
      },
    });
    const result = await recovered.reportWake({
      status: "completed_no_effect",
      safe_reason: "providers_exhausted",
      consecutive_failure_count: 0,
    });

    assert.equal(sent.length, 2);
    assert.deepEqual(result, { telegram_provider_id: "8002" });
    const deliveries = fs.readFileSync(
      path.join(stateDir, "wake-report-deliveries.jsonl"), "utf8",
    ).trim().split("\n").map(JSON.parse);
    assert.deepEqual(deliveries.map((row) => row.wake_id), [
      "wake-20260807-failed",
      "wake-20260808-recovered",
    ]);
  } finally {
    fs.rmSync(stateDir, { recursive: true, force: true });
  }
});

test("operations persist only safe Luma discovery aggregate counts", async () => {
  const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "connector-minimal-discovery-"));
  try {
    const operations = createMinimalProductionOperations({
      stateDir,
      wakeId: "wake-20260807-discovery",
      telegramTarget: "private-target",
      now: () => new Date("2026-08-07T08:30:00.000Z"),
      async sendMessage() { return { messageId: 7001 }; },
    });
    await operations.recordDiscoveryAudit({
      observed_count: 37,
      normalized_count: 36,
      window_count: 12,
      free_open_count: 4,
      calendar_free_count: 2,
    });

    const file = path.join(stateDir, "luma-discovery-audits.jsonl");
    const row = JSON.parse(fs.readFileSync(file, "utf8").trim());
    assert.deepEqual(Object.keys(row).sort(), [
      "calendar_free_count", "free_open_count", "normalized_count", "observed_count",
      "recorded_at", "schema_version", "wake_id", "window_count",
    ]);
    assert.equal(fs.statSync(file).mode & 0o777, 0o600);
    assert.equal(JSON.stringify(row).includes("https://"), false);
  } finally {
    fs.rmSync(stateDir, { recursive: true, force: true });
  }
});
