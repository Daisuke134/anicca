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
    assert.equal(sent[0].options.idempotencyKey, "wake-20260807-001");
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

test("duplicate report uses stored created_at and rejects business-field drift", async () => {
  const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "connector-minimal-duplicate-"));
  let clock = Date.parse("2026-08-08T08:30:00.000Z"); const sent = [];
  const input = { status: "completed_no_effect", safe_reason: "providers_exhausted", consecutive_failure_count: 0 };
  const make = () => createMinimalProductionOperations({
    stateDir, wakeId: "wake-20260808-duplicate", telegramTarget: "private-target",
    now: () => new Date(clock += 1000), async sendMessage() { sent.push(true); return { messageId: 9201 }; },
  });
  try {
    const operations = make(); await operations.reportWake(input); await operations.reportWake(input);
    assert.equal(sent.length, 1);
    const row = JSON.parse(fs.readFileSync(path.join(stateDir, "wake-reports.jsonl"), "utf8").trim());
    assert.equal(row.created_at, "2026-08-08T08:30:01.000Z");
    await assert.rejects(() => operations.reportWake({ ...input, safe_reason: "consecutive_failure_limit" }));
    assert.equal(sent.length, 1);
  } finally { fs.rmSync(stateDir, { recursive: true, force: true }); }
});

test("reportWake fails closed before send on malformed delivery rows", async () => {
  const report = { schema_version: 1, wake_id: "wake-20260808-delivery", status: "completed_no_effect", safe_reason: "providers_exhausted", consecutive_failure_count: 0, created_at: "2026-08-08T08:30:00.000Z" };
  const valid = { schema_version: 1, wake_id: report.wake_id, telegram_provider_id: "9301", delivered_at: report.created_at };
  const variants = [
    { ...valid, schema_version: 2 }, { ...valid, telegram_provider_id: "0" }, { ...valid, telegram_provider_id: 9 },
    { ...valid, wake_id: "x" }, { ...valid, delivered_at: "not-an-instant" },
  ];
  for (const delivery of variants) {
    const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "connector-minimal-delivery-invalid-")); let sends = 0;
    try {
      fs.writeFileSync(path.join(stateDir, "wake-reports.jsonl"), `${JSON.stringify(report)}\n`, { mode: 0o600 });
      fs.writeFileSync(path.join(stateDir, "wake-report-deliveries.jsonl"), `${JSON.stringify(delivery)}\n`, { mode: 0o600 });
      const operations = createMinimalProductionOperations({ stateDir, wakeId: report.wake_id, telegramTarget: "private-target", now: () => new Date(report.created_at), async sendMessage() { sends += 1; return { messageId: 9302 }; } });
      await assert.rejects(() => operations.reportWake(report)); assert.equal(sends, 0);
    } finally { fs.rmSync(stateDir, { recursive: true, force: true }); }
  }
});

test("a later wake delivers current before one pending historical report", async () => {
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
    const reportFile = path.join(stateDir, "wake-reports.jsonl");
    const oldReport = fs.readFileSync(reportFile, "utf8").trim().split("\n")[0];

    const sent = [];
    const recovered = createMinimalProductionOperations({
      stateDir,
      wakeId: "wake-20260808-recovered",
      telegramTarget: "private-target",
      now: () => new Date("2026-08-08T08:30:00.000Z"),
      async sendMessage(message, options) {
        sent.push({ message, options });
        if (message.includes("providers_exhausted")) throw new Error("historical transport failure");
        return { messageId: 8001 };
      },
    });
    const result = await recovered.reportWake({
      status: "circuit_open",
      safe_reason: "consecutive_failure_limit",
      consecutive_failure_count: 3,
    });

    assert.equal(sent.length, 2);
    assert.equal(sent[0].message.includes("consecutive_failure_limit"), true);
    assert.equal(sent[1].message.includes("providers_exhausted"), true);
    assert.deepEqual(sent.map(({ options }) => options.idempotencyKey), [
      "wake-20260808-recovered", "wake-20260807-failed",
    ]);
    assert.deepEqual(result, { telegram_provider_id: "8001" });
    const deliveries = fs.readFileSync(
      path.join(stateDir, "wake-report-deliveries.jsonl"), "utf8",
    ).trim().split("\n").map(JSON.parse);
    assert.deepEqual(deliveries.map((row) => row.wake_id), ["wake-20260808-recovered"]);
    const reportLines = fs.readFileSync(reportFile, "utf8").trim().split("\n");
    assert.equal(reportLines[0], oldReport);
    assert.equal(reportLines.length, 2);
  } finally {
    fs.rmSync(stateDir, { recursive: true, force: true });
  }
});

test("reportWake bounds historical recovery and keeps current failure hard", async () => {
  const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "connector-minimal-priority-"));
  const report = { status: "completed_no_effect", safe_reason: "providers_exhausted", consecutive_failure_count: 0 };
  const make = (wakeId, sendMessage) => createMinimalProductionOperations({
    stateDir, wakeId, telegramTarget: "private-target", now: () => new Date("2026-08-08T08:30:00.000Z"), sendMessage,
  });
  try {
    for (const wakeId of ["wake-20260807-old-1", "wake-20260807-old-2"]) {
      await assert.rejects(() => make(wakeId, async () => { throw new Error("transport failure"); }).reportWake(report));
    }
    const sent = [];
    const current = make("wake-20260808-current", async (message) => {
      sent.push(message); return { messageId: 9000 + sent.length };
    });
    const first = await current.reportWake({ status: "circuit_open", safe_reason: "consecutive_failure_limit", consecutive_failure_count: 3 });
    assert.deepEqual(first, { telegram_provider_id: "9001" });
    assert.equal(sent.length, 2);

    const duplicateSent = [];
    const duplicate = make("wake-20260808-current", async (message) => {
      duplicateSent.push(message); return { messageId: 9100 + duplicateSent.length };
    });
    assert.deepEqual(await duplicate.reportWake({ status: "circuit_open", safe_reason: "consecutive_failure_limit", consecutive_failure_count: 3 }), first);
    assert.equal(duplicateSent.length, 1);

    const hard = make("wake-20260808-hard", async () => { throw new Error("current transport failure"); });
    await assert.rejects(() => hard.reportWake(report));
    const deliveries = fs.readFileSync(path.join(stateDir, "wake-report-deliveries.jsonl"), "utf8").trim().split("\n").map(JSON.parse);
    assert.equal(deliveries.some((row) => row.wake_id === "wake-20260808-hard"), false);
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

test("operations persist only safe Connpass discovery aggregate counts", async () => {
  const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "connector-minimal-connpass-discovery-"));
  try {
    const operations = createMinimalProductionOperations({
      stateDir,
      wakeId: "wake-20260810-connpass-discovery",
      telegramTarget: "private-target",
      now: () => new Date("2026-08-10T08:30:00.000Z"),
      async sendMessage() { return { messageId: 7001 }; },
    });
    await operations.recordConnpassDiscoveryAudit({
      observed_count: 41,
      normalized_count: 40,
      window_count: 11,
      free_open_count: 3,
      calendar_free_count: 1,
    });

    const file = path.join(stateDir, "connpass-discovery-audits.jsonl");
    const row = JSON.parse(fs.readFileSync(file, "utf8").trim());
    assert.deepEqual(Object.keys(row).sort(), [
      "calendar_free_count", "free_open_count", "normalized_count", "observed_count",
      "recorded_at", "schema_version", "wake_id", "window_count",
    ]);
    assert.equal(row.wake_id, "wake-20260810-connpass-discovery");
    assert.equal(fs.statSync(file).mode & 0o777, 0o600);
    assert.equal(JSON.stringify(row).includes("https://"), false);
  } finally {
    fs.rmSync(stateDir, { recursive: true, force: true });
  }
});

test("operations persist only safe Peatix discovery aggregate counts", async () => {
  const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "connector-minimal-peatix-discovery-"));
  try {
    const operations = createMinimalProductionOperations({
      stateDir, wakeId: "wake-20260810-peatix-discovery", telegramTarget: "private-target",
      now: () => new Date("2026-08-10T08:30:00.000Z"), async sendMessage() { return { messageId: 7001 }; },
    });
    await operations.recordPeatixDiscoveryAudit({
      observed_count: 41, normalized_count: 40, window_count: 11, free_open_count: 3, calendar_free_count: 1,
    });
    await assert.rejects(() => operations.recordPeatixDiscoveryAudit({
      observed_count: 1, normalized_count: 2, window_count: 1, free_open_count: 1, calendar_free_count: 1,
    }));

    const file = path.join(stateDir, "peatix-discovery-audits.jsonl");
    const lines = fs.readFileSync(file, "utf8").trim().split("\n");
    const row = JSON.parse(lines[0]);
    assert.equal(lines.length, 1);
    assert.deepEqual(Object.keys(row).sort(), [
      "calendar_free_count", "free_open_count", "normalized_count", "observed_count",
      "recorded_at", "schema_version", "wake_id", "window_count",
    ]);
    assert.equal(row.wake_id, "wake-20260810-peatix-discovery");
    assert.equal(row.recorded_at, "2026-08-10T08:30:00.000Z");
    assert.equal(fs.statSync(file).mode & 0o777, 0o600);
    assert.doesNotMatch(JSON.stringify(row), /https?:\/\/|5075819|title|ticket|profile/i);
  } finally {
    fs.rmSync(stateDir, { recursive: true, force: true });
  }
});
