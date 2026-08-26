"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const { deliverPendingWakeReports, enqueueWakeReport } = require("../lib/wake-report-outbox.js");

const WAKE_ID = "wake-test-outbox";

test("wake report outbox keys Gateway delivery by the exact wake ID", async () => {
  const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "connector-wake-outbox-"));
  const sent = [];
  try {
    enqueueWakeReport(stateDir, {
      wake_id: WAKE_ID,
      report_kind: "continuing",
      safe_reason: "providers_exhausted",
      cursor: "provider:luma",
      open_count: 1,
      attempt_count: 2,
      created_at: "2026-08-10T08:30:00.000Z",
    });
    await deliverPendingWakeReports(stateDir, {
      telegramTarget: "123456789",
      async send(message, options) {
        sent.push({ message, options });
        return { messageId: "42" };
      },
    });
    assert.equal(sent.length, 1);
    assert.equal(sent[0].options.idempotencyKey, WAKE_ID);
    await deliverPendingWakeReports(stateDir, {
      telegramTarget: "123456789",
      async send() { throw new Error("duplicate send"); },
    });
    assert.equal(sent.length, 1);
  } finally {
    fs.rmSync(stateDir, { recursive: true, force: true });
  }
});

test("wake report outbox accepts the full 28-day horizon and rejects larger counts", () => {
  const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "connector-wake-horizon-"));
  const row = {
    wake_id: "wake-test-horizon", report_kind: "continuing", safe_reason: "providers_exhausted",
    cursor: "provider:luma", open_count: 28, attempt_count: 0, created_at: "2026-08-10T08:30:00.000Z",
  };
  try {
    enqueueWakeReport(stateDir, row);
    assert.throws(() => enqueueWakeReport(stateDir, { ...row, wake_id: "wake-test-too-large", open_count: 29 }));
  } finally {
    fs.rmSync(stateDir, { recursive: true, force: true });
  }
});
