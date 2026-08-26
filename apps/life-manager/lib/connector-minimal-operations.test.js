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

test("recordAction persists provider and stage safe_reason for a failed discovery action", async () => {
  const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "connector-minimal-action-context-"));
  try {
    const operations = createMinimalProductionOperations({
      stateDir,
      wakeId: "wake-20260816-connpass",
      telegramTarget: "private-target",
      now: () => new Date("2026-08-16T14:03:56.454Z"),
      async sendMessage() { return { messageId: 7002 }; },
    });

    await operations.recordAction({
      purpose: "observe",
      method: "provider_discovery",
      timestamp: "2026-08-16T14:03:56.454Z",
      result: "failed",
      duration_ms: 45971,
      provider: "connpass",
      safe_reason: "connpass_calendar_navigation_failed",
    });

    const historyFile = path.join(stateDir, "action-history.jsonl");
    const row = JSON.parse(fs.readFileSync(historyFile, "utf8").trim());
    assert.deepEqual(row, {
      schema_version: 1,
      wake_id: "wake-20260816-connpass",
      purpose: "observe",
      method: "provider_discovery",
      timestamp: "2026-08-16T14:03:56.454Z",
      result: "failed",
      duration_ms: 45971,
      provider: "connpass",
      safe_reason: "connpass_calendar_navigation_failed",
    });

    await assert.rejects(() => operations.recordAction({
      purpose: "observe",
      method: "provider_discovery",
      timestamp: "2026-08-16T14:03:56.454Z",
      result: "success",
      duration_ms: 100,
      provider: "connpass",
      safe_reason: "connpass_calendar_navigation_failed",
    }), "a success row must not carry provider/safe_reason context");

    await assert.rejects(() => operations.recordAction({
      purpose: "observe",
      method: "provider_discovery",
      timestamp: "2026-08-16T14:03:56.454Z",
      result: "failed",
      duration_ms: 100,
      provider: "Connpass",
      safe_reason: "connpass_calendar_navigation_failed",
    }), "an uppercase provider must be rejected");
  } finally {
    fs.rmSync(stateDir, { recursive: true, force: true });
  }
});

test("recordAction persists a bounded error_class and rejects malformed or oversized values", async () => {
  const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "connector-minimal-error-class-"));
  try {
    const operations = createMinimalProductionOperations({
      stateDir,
      wakeId: "wake-20260817-connpass-class",
      telegramTarget: "private-target",
      now: () => new Date("2026-08-17T09:00:00.000Z"),
      async sendMessage() { return { messageId: 7003 }; },
    });

    await operations.recordAction({
      purpose: "observe",
      method: "provider_discovery",
      timestamp: "2026-08-17T09:00:00.000Z",
      result: "failed",
      duration_ms: 30021,
      provider: "connpass",
      safe_reason: "provider_discovery_failed",
      error_class: "TimeoutError",
    });

    const historyFile = path.join(stateDir, "action-history.jsonl");
    const row = JSON.parse(fs.readFileSync(historyFile, "utf8").trim());
    assert.deepEqual(row, {
      schema_version: 1,
      wake_id: "wake-20260817-connpass-class",
      purpose: "observe",
      method: "provider_discovery",
      timestamp: "2026-08-17T09:00:00.000Z",
      result: "failed",
      duration_ms: 30021,
      provider: "connpass",
      safe_reason: "provider_discovery_failed",
      error_class: "TimeoutError",
    });

    await assert.rejects(() => operations.recordAction({
      purpose: "observe",
      method: "provider_discovery",
      timestamp: "2026-08-17T09:00:01.000Z",
      result: "failed",
      duration_ms: 100,
      provider: "connpass",
      safe_reason: "provider_discovery_failed",
      error_class: "Type Error: boom",
    }), "an error_class containing spaces or a colon must be rejected");

    await assert.rejects(() => operations.recordAction({
      purpose: "observe",
      method: "provider_discovery",
      timestamp: "2026-08-17T09:00:02.000Z",
      result: "failed",
      duration_ms: 100,
      provider: "connpass",
      safe_reason: "provider_discovery_failed",
      error_class: "A".repeat(65),
    }), "an oversized error_class must be rejected");

    await assert.rejects(() => operations.recordAction({
      purpose: "observe",
      method: "provider_discovery",
      timestamp: "2026-08-17T09:00:03.000Z",
      result: "success",
      duration_ms: 100,
      error_class: "TimeoutError",
    }), "error_class must not appear on a success row");

    const rows = fs.readFileSync(historyFile, "utf8").trim().split("\n");
    assert.equal(rows.length, 1, "rejected rows must never be appended");
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

test("operations persist only bounded ranking timing aggregates", async () => {
  const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "connector-ranking-audit-"));
  try {
    const operations = createMinimalProductionOperations({
      stateDir, wakeId: "wake-ranking-audit", telegramTarget: "private-target",
      now: () => new Date("2026-08-27T05:00:00.000Z"),
      async sendMessage() { return { messageId: 7001 }; },
    });
    const input = {
      schema_version: 1, request_count: 31, retry_count: 8, bisect_count: 4,
      total_request_ms: 571_020, max_request_ms: 45_000, elapsed_ms: 589_180,
    };
    await operations.recordRankingAudit(input);
    const file = path.join(stateDir, "ranking-audits.jsonl");
    const row = JSON.parse(fs.readFileSync(file, "utf8").trim());
    assert.deepEqual(row, {
      schema_version: 1, wake_id: "wake-ranking-audit", ...input,
      recorded_at: "2026-08-27T05:00:00.000Z",
    });
    assert.equal(fs.statSync(file).mode & 0o777, 0o600);
    for (const malformed of [
      { ...input, prompt: "private" },
      { ...input, request_count: -1 },
      { ...input, retry_count: 32 },
      { ...input, max_request_ms: input.total_request_ms + 1 },
    ]) await assert.rejects(() => operations.recordRankingAudit(malformed));
  } finally { fs.rmSync(stateDir, { recursive: true, force: true }); }
});

test("Connpass discovery audit accepts a busy Tokyo listing and still bounds the count", async () => {
  const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "connector-minimal-connpass-busy-"));
  try {
    const operations = createMinimalProductionOperations({
      stateDir,
      wakeId: "wake-20260816-connpass-busy",
      telegramTarget: "private-target",
      now: () => new Date("2026-08-16T14:04:21.714Z"),
      async sendMessage() { return { messageId: 7001 }; },
    });
    const busy = { observed_count: 767, normalized_count: 40, window_count: 40, free_open_count: 29, calendar_free_count: 7 };
    await operations.recordConnpassDiscoveryAudit(busy);

    const file = path.join(stateDir, "connpass-discovery-audits.jsonl");
    const row = JSON.parse(fs.readFileSync(file, "utf8").trim());
    assert.deepEqual(
      [row.observed_count, row.normalized_count, row.window_count, row.free_open_count, row.calendar_free_count],
      [767, 40, 40, 29, 7],
      "a real, measured 767-observed listing must be accepted and written",
    );

    await assert.rejects(() => operations.recordConnpassDiscoveryAudit({
      ...busy, window_count: 41,
    }), "window_count exceeding normalized_count must still be rejected");

    await assert.rejects(() => operations.recordConnpassDiscoveryAudit({
      ...busy, observed_count: 5_001,
    }), "a count above the new ceiling must still be rejected");
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

test("operations persist only safe Meetup discovery aggregate counts", async () => {
  const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "connector-minimal-meetup-discovery-"));
  try {
    const operations = createMinimalProductionOperations({
      stateDir, wakeId: "wake-20260811-meetup-discovery", telegramTarget: "private-target",
      now: () => new Date("2026-08-11T08:30:00.000Z"), async sendMessage() { return { messageId: 7001 }; },
    });
    await operations.recordMeetupDiscoveryAudit({
      observed_count: 48, normalized_count: 47, window_count: 14, free_open_count: 12, calendar_free_count: 0,
    });
    await assert.rejects(() => operations.recordMeetupDiscoveryAudit({
      observed_count: 48, normalized_count: 49, window_count: 14, free_open_count: 12, calendar_free_count: 0,
    }));

    const file = path.join(stateDir, "meetup-discovery-audits.jsonl");
    const lines = fs.readFileSync(file, "utf8").trim().split("\n");
    const row = JSON.parse(lines[0]);
    assert.equal(lines.length, 1);
    assert.deepEqual(Object.keys(row).sort(), [
      "calendar_free_count", "free_open_count", "normalized_count", "observed_count",
      "recorded_at", "schema_version", "wake_id", "window_count",
    ]);
    assert.equal(row.schema_version, 1);
    assert.equal(row.wake_id, "wake-20260811-meetup-discovery");
    assert.deepEqual([row.observed_count, row.normalized_count, row.window_count, row.free_open_count, row.calendar_free_count], [48, 47, 14, 12, 0]);
    assert.equal(row.recorded_at, "2026-08-11T08:30:00.000Z");
    assert.equal(fs.statSync(file).mode & 0o777, 0o600);
    assert.doesNotMatch(JSON.stringify(row), /https?:\/\/|event|title|profile|ticket|auth|private|attendee/i);
  } finally {
    fs.rmSync(stateDir, { recursive: true, force: true });
  }
});

test("operations persist only safe Doorkeeper discovery aggregate counts", async () => {
  const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "connector-minimal-doorkeeper-discovery-"));
  const valid = {
    discovered_count: 100,
    within_window_count: 12,
    eligible_count: 8,
    calendar_free_count: 0,
    selected_count: 0,
  };
  try {
    const operations = createMinimalProductionOperations({
      stateDir, wakeId: "wake-20260811-doorkeeper-discovery", telegramTarget: "private-target",
      now: () => new Date("2026-08-11T08:30:00.000Z"), async sendMessage() { return { messageId: 7001 }; },
    });
    assert.equal(Object.isFrozen(operations), true);
    await operations.recordDoorkeeperDiscoveryAudit(valid);

    const file = path.join(stateDir, "doorkeeper-discovery-audits.jsonl");
    const lines = fs.readFileSync(file, "utf8").trim().split("\n");
    const row = JSON.parse(lines[0]);
    assert.equal(lines.length, 1);
    assert.deepEqual(Object.keys(row).sort(), [
      "calendar_free_count", "discovered_count", "eligible_count", "recorded_at", "schema_version",
      "selected_count", "wake_id", "within_window_count",
    ]);
    assert.deepEqual(row, {
      schema_version: 1,
      wake_id: "wake-20260811-doorkeeper-discovery",
      discovered_count: 100,
      within_window_count: 12,
      eligible_count: 8,
      calendar_free_count: 0,
      selected_count: 0,
      recorded_at: "2026-08-11T08:30:00.000Z",
    });
    assert.equal(fs.statSync(file).mode & 0o777, 0o600);
    assert.doesNotMatch(JSON.stringify(row), /https?:\/\/|private-target|attendee|email|title/i);

    const { selected_count: _selectedCount, ...missingKey } = valid;
    const invalidInputs = [
      { ...valid, calendar_free_count: 9 },
      { ...valid, private_url: "https://private.example/fixture" },
      missingKey,
      { ...valid, selected_count: 0.5 },
      { ...valid, discovered_count: -1 },
      { ...valid, discovered_count: 801 },
      { ...valid, selected_count: "0" },
      [],
      null,
    ];
    for (const input of invalidInputs) {
      await assert.rejects(() => operations.recordDoorkeeperDiscoveryAudit(input));
    }
    assert.equal(fs.readFileSync(file, "utf8").trim().split("\n").length, 1);
  } finally {
    fs.rmSync(stateDir, { recursive: true, force: true });
  }
});

test("operations persist only safe Eventbrite discovery aggregate counts", async () => {
  const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "connector-minimal-eventbrite-discovery-"));
  const valid = { discovered_count: 100, within_window_count: 12, eligible_count: 8, calendar_free_count: 2, selected_count: 1 };
  try {
    const operations = createMinimalProductionOperations({
      stateDir, wakeId: "wake-20260811-eventbrite-discovery", telegramTarget: "private-target",
      now: () => new Date("2026-08-11T08:30:00.000Z"), async sendMessage() { return { messageId: 7001 }; },
    });
    assert.equal(typeof operations.recordEventbriteDiscoveryAudit, "function");
    await operations.recordEventbriteDiscoveryAudit(valid);
    const file = path.join(stateDir, "eventbrite-discovery-audits.jsonl");
    const lines = fs.readFileSync(file, "utf8").trim().split("\n");
    const row = JSON.parse(lines[0]);
    assert.equal(lines.length, 1);
    assert.deepEqual(Object.keys(row).sort(), ["calendar_free_count", "discovered_count", "eligible_count", "recorded_at", "schema_version", "selected_count", "wake_id", "within_window_count"]);
    assert.deepEqual(row, { schema_version: 1, wake_id: "wake-20260811-eventbrite-discovery", ...valid, recorded_at: "2026-08-11T08:30:00.000Z" });
    assert.equal(row.schema_version, 1);
    assert.equal(fs.statSync(file).mode & 0o777, 0o600);
    assert.doesNotMatch(JSON.stringify(row), /https?:\/\/|private-target|attendee|email|title/i);

    const { selected_count: _selectedCount, ...missingKey } = valid;
    for (const input of [
      { ...valid, calendar_free_count: 9 }, { ...valid, private_url: "https://private.example/fixture" }, missingKey,
      { ...valid, selected_count: 0.5 }, { ...valid, discovered_count: -1 }, { ...valid, discovered_count: 801 },
      { ...valid, selected_count: "1" }, [], null,
    ]) await assert.rejects(() => operations.recordEventbriteDiscoveryAudit(input));
    assert.equal(fs.readFileSync(file, "utf8").trim().split("\n").length, 1);
  } finally { fs.rmSync(stateDir, { recursive: true, force: true }); }
});

test("operations persist only safe TECH PLAY discovery aggregate counts", async () => {
  const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "connector-minimal-techplay-discovery-"));
  const valid = { discovered_count: 50, within_window_count: 12, eligible_count: 8, calendar_free_count: 2, selected_count: 1 };
  try {
    const operations = createMinimalProductionOperations({
      stateDir, wakeId: "wake-20260812-techplay-discovery", telegramTarget: "private-target",
      now: () => new Date("2026-08-12T08:30:00.000Z"), async sendMessage() { return { messageId: 7001 }; },
    });
    assert.equal(Object.isFrozen(operations), true);
    assert.equal(typeof operations.recordTechPlayDiscoveryAudit, "function");
    await operations.recordTechPlayDiscoveryAudit(valid);
    const file = path.join(stateDir, "techplay-discovery-audits.jsonl");
    const lines = fs.readFileSync(file, "utf8").trim().split("\n");
    const row = JSON.parse(lines[0]);
    assert.equal(lines.length, 1);
    assert.deepEqual(row, { schema_version: 1, wake_id: "wake-20260812-techplay-discovery", ...valid, recorded_at: "2026-08-12T08:30:00.000Z" });
    assert.deepEqual(Object.keys(row).sort(), ["calendar_free_count", "discovered_count", "eligible_count", "recorded_at", "schema_version", "selected_count", "wake_id", "within_window_count"]);
    assert.equal(fs.statSync(file).mode & 0o777, 0o600);
    assert.doesNotMatch(JSON.stringify(row), /https?:\/\/|private-target|title|ticket|profile|auth|email/i);

    const { selected_count: _selectedCount, ...missingKey } = valid;
    for (const input of [
      { ...valid, private_url: "https://private.example/fixture" }, missingKey,
      { ...valid, selected_count: 0.5 }, { ...valid, discovered_count: -1 }, { ...valid, discovered_count: 801 },
      { ...valid, calendar_free_count: 9 }, { ...valid, within_window_count: 51 }, [], null,
    ]) await assert.rejects(() => operations.recordTechPlayDiscoveryAudit(input));
    assert.equal(fs.readFileSync(file, "utf8").trim().split("\n").length, 1);
  } finally { fs.rmSync(stateDir, { recursive: true, force: true }); }
});

test("operations persist only safe KokuchPro discovery aggregate counts", async () => {
  const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "connector-minimal-kokuchpro-discovery-"));
  const valid = { discovered_count: 100, within_window_count: 12, eligible_count: 8, calendar_free_count: 2, selected_count: 1 };
  try {
    const operations = createMinimalProductionOperations({
      stateDir, wakeId: "wake-20260812-kokuchpro-discovery", telegramTarget: "private-target",
      now: () => new Date("2026-08-12T06:00:00.000Z"), async sendMessage() { return { messageId: 7001 }; },
    });
    assert.equal(Object.isFrozen(operations), true);
    assert.equal(typeof operations.recordKokuchProDiscoveryAudit, "function");
    await operations.recordKokuchProDiscoveryAudit(valid);
    const file = path.join(stateDir, "kokuchpro-discovery-audits.jsonl");
    const lines = fs.readFileSync(file, "utf8").trim().split("\n");
    const row = JSON.parse(lines[0]);
    assert.equal(lines.length, 1);
    assert.deepEqual(row, { schema_version: 1, wake_id: "wake-20260812-kokuchpro-discovery", ...valid, recorded_at: "2026-08-12T06:00:00.000Z" });
    assert.deepEqual(Object.keys(row).sort(), ["calendar_free_count", "discovered_count", "eligible_count", "recorded_at", "schema_version", "selected_count", "wake_id", "within_window_count"]);
    assert.equal(fs.statSync(file).mode & 0o777, 0o600);
    assert.doesNotMatch(JSON.stringify(row), /https?:\/\/|private-target|title|ticket|profile|auth|email/i);

    const { selected_count: _selectedCount, ...missingKey } = valid;
    for (const input of [
      { ...valid, private_url: "https://private.example/fixture" }, missingKey,
      { ...valid, selected_count: 0.5 }, { ...valid, discovered_count: -1 }, { ...valid, discovered_count: 801 },
      { ...valid, selected_count: "1" }, { ...valid, calendar_free_count: 9 }, { ...valid, eligible_count: 13 },
      { ...valid, within_window_count: 101 }, [], null,
    ]) await assert.rejects(() => operations.recordKokuchProDiscoveryAudit(input));
    assert.equal(fs.readFileSync(file, "utf8").trim().split("\n").length, 1);
  } finally { fs.rmSync(stateDir, { recursive: true, force: true }); }
});
