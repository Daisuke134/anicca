"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const {
  EXPECTED_SHADOW_RUNS,
  appendFinancialReportShadowHold,
  financialReportShadowConfig,
  financialReportShadowStatus,
} = require("./financial-report-shadow-runtime.js");

const TZ = "Asia/Tokyo";
// Wednesday 2026-08-05 23:00 JST. The expected grid walking back from here is:
//   daily 08-05, daily 08-04, daily 08-03, weekly 08-02 (Sunday 20:05),
//   daily 08-02, daily 08-01, daily 07-31  = exactly seven expected runs.
const NOW_MS = Date.parse("2026-08-05T14:00:00.000Z");
const GRID = Object.freeze([
  { report_kind: "daily", slot: "2026-07-31T11:00:00.000Z", period_key: "2026-07-31" },
  { report_kind: "daily", slot: "2026-08-01T11:00:00.000Z", period_key: "2026-08-01" },
  { report_kind: "daily", slot: "2026-08-02T11:00:00.000Z", period_key: "2026-08-02" },
  { report_kind: "weekly", slot: "2026-08-02T11:05:00.000Z", period_key: "2026-W31" },
  { report_kind: "daily", slot: "2026-08-03T11:00:00.000Z", period_key: "2026-08-03" },
  { report_kind: "daily", slot: "2026-08-04T11:00:00.000Z", period_key: "2026-08-04" },
  { report_kind: "daily", slot: "2026-08-05T11:00:00.000Z", period_key: "2026-08-05" },
]);

function run(entry, overrides = {}) {
  return {
    ...entry,
    snapshot_hash: "a".repeat(64),
    recorded_at: new Date(Date.parse(entry.slot) + 2000).toISOString(),
    verified: true,
    ...overrides,
  };
}

test("the shadow gate expects seven runs and is default off", () => {
  assert.equal(EXPECTED_SHADOW_RUNS, 7);
  const off = financialReportShadowConfig({});
  assert.equal(off.enabled, false);
  assert.equal(off.timeZone, "Asia/Tokyo");
  // Any value other than the exact string "true" leaves shadow off.
  assert.equal(financialReportShadowConfig({ LM_FINANCIAL_REPORT_SHADOW_ENABLED: "1" }).enabled, false);
  assert.equal(financialReportShadowConfig({ LM_FINANCIAL_REPORT_SHADOW_ENABLED: "off" }).enabled, false);
  assert.equal(financialReportShadowConfig({
    LM_FINANCIAL_REPORT_SHADOW_ENABLED: "TRUE",
    LM_RUNTIME_TENANT_ID: "dais-local",
    LM_DATA_DIR: "/tmp/life-manager-data",
  }).enabled, true);

  const on = financialReportShadowConfig({
    LM_FINANCIAL_REPORT_SHADOW_ENABLED: "true",
    LM_RUNTIME_TENANT_ID: "dais-local",
    LM_DATA_DIR: "/tmp/life-manager-data",
    LM_FINANCIAL_REPORT_TIME_ZONE: "Asia/Tokyo",
  });
  assert.equal(on.enabled, true);
  assert.equal(on.tenantId, "dais-local");
  assert.equal(on.dataDir, "/tmp/life-manager-data");
  assert.throws(
    () => financialReportShadowConfig({ LM_FINANCIAL_REPORT_SHADOW_ENABLED: "true" }),
    /LM_RUNTIME_TENANT_ID/,
  );
});

test("seven consecutive expected runs meet the gate", () => {
  const status = financialReportShadowStatus(GRID.map((entry) => run(entry)), {
    nowMs: NOW_MS,
    timeZone: TZ,
  });
  assert.equal(status.consecutive, 7);
  assert.equal(status.display, "7/7");
  assert.equal(status.gate_met, true);
  assert.deepEqual(status.missed_runs, []);
  assert.equal(status.runs.length, 7);
  assert.deepEqual(status.runs[0], {
    report_kind: "daily",
    period_key: "2026-07-31",
    slot: "2026-07-31T11:00:00.000Z",
    snapshot_hash: "a".repeat(64),
    recorded_at: "2026-07-31T11:00:02.000Z",
  });
});

test("a partial run counts only the trailing consecutive expected runs", () => {
  const status = financialReportShadowStatus(GRID.slice(5).map((entry) => run(entry)), {
    nowMs: NOW_MS,
    timeZone: TZ,
  });
  assert.equal(status.consecutive, 2);
  assert.equal(status.display, "2/7");
  assert.equal(status.gate_met, false);
  assert.deepEqual(status.missed_runs, []);
});

test("an expected run with no receipt is reported missed and resets the count", () => {
  // The weekly 2026-08-02 20:05 JST run left no row at all.
  const rows = GRID.filter((entry) => entry.report_kind !== "weekly").map((entry) => run(entry));
  const status = financialReportShadowStatus(rows, { nowMs: NOW_MS, timeZone: TZ });
  assert.equal(status.consecutive, 3);
  assert.equal(status.display, "3/7");
  assert.deepEqual(status.missed_runs, [{
    report_kind: "weekly",
    slot: "2026-08-02T11:05:00.000Z",
    period_key: "2026-W31",
  }]);
});

test("a duplicate receipt for one expected run is a gate violation", () => {
  const rows = GRID.map((entry) => run(entry));
  rows.push(run(GRID[6], { snapshot_hash: "b".repeat(64), recorded_at: "2026-08-05T11:00:09.000Z" }));
  const status = financialReportShadowStatus(rows, { nowMs: NOW_MS, timeZone: TZ });
  assert.equal(status.consecutive, 0);
  assert.equal(status.gate_met, false);
  assert.deepEqual(status.duplicate_runs, [{
    report_kind: "daily",
    period_key: "2026-08-05",
    count: 2,
  }]);
});

test("an unverifiable row truncates the count at that row", () => {
  const rows = GRID.map((entry, index) => run(entry, index === 4 ? { verified: false } : {}));
  const status = financialReportShadowStatus(rows, { nowMs: NOW_MS, timeZone: TZ });
  assert.equal(status.consecutive, 2);
  assert.equal(status.display, "2/7");
});

test("an off-grid receipt slot stops the count instead of counting", () => {
  const rows = GRID.slice(0, 6).map((entry) => run(entry));
  rows.push(run({
    report_kind: "daily",
    slot: "2026-08-05T05:00:00.000Z",
    period_key: "2026-08-05",
  }));
  const status = financialReportShadowStatus(rows, { nowMs: NOW_MS, timeZone: TZ });
  assert.equal(status.consecutive, 0);
});

test("a run that is not due yet is never counted as missed", () => {
  // 2026-08-05 19:00 JST: today's 20:00 daily run has not been released yet.
  const status = financialReportShadowStatus(GRID.slice(0, 6).map((entry) => run(entry)), {
    nowMs: Date.parse("2026-08-05T10:00:00.000Z"),
    timeZone: TZ,
  });
  assert.equal(status.consecutive, 6);
  assert.equal(status.display, "6/7");
  assert.deepEqual(status.missed_runs, []);
});

test("an empty history reads 0/7 instead of failing or faking", () => {
  const status = financialReportShadowStatus([], { nowMs: NOW_MS, timeZone: TZ });
  assert.equal(status.display, "0/7");
  assert.equal(status.gate_met, false);
  assert.deepEqual(status.runs, []);
  assert.deepEqual(status.missed_runs, []);
});

test("bad status inputs fail loudly", () => {
  assert.throws(() => financialReportShadowStatus(null, { nowMs: NOW_MS }), /receipts/i);
  assert.throws(() => financialReportShadowStatus([], { nowMs: "now" }), /time/i);
  assert.throws(() => financialReportShadowStatus([], { nowMs: NOW_MS, expected: 0 }), /expect/i);
});

test("the durable hold ledger appends once per hold and is idempotent on replay", () => {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), "lm-financial-shadow-"));
  const hold = {
    schema_version: 1,
    kind: "telegram_financial_report_hold",
    status: "shadow_held",
    tenant_id: "dais-local",
    report_kind: "daily",
    period_key: "2026-08-05",
    slot: "2026-08-05T11:00:00.000Z",
    job_id: "financial-report:abc",
    snapshot_hash: "a".repeat(64),
    chat_id_hash: "c".repeat(64),
    held_at: "2026-08-05T11:00:03.000Z",
  };
  const first = appendFinancialReportShadowHold(hold, { dataDir, tenantId: "dais-local" });
  const second = appendFinancialReportShadowHold(hold, { dataDir, tenantId: "dais-local" });
  assert.equal(first.ledger_path, second.ledger_path);
  assert.equal(first.recorded, true);
  assert.equal(second.recorded, false);
  const lines = fs.readFileSync(first.ledger_path, "utf8").trim().split("\n");
  assert.equal(lines.length, 1);
  assert.deepEqual(JSON.parse(lines[0]), hold);

  const next = appendFinancialReportShadowHold({
    ...hold,
    period_key: "2026-08-06",
    slot: "2026-08-06T11:00:00.000Z",
  }, { dataDir, tenantId: "dais-local" });
  assert.equal(next.recorded, true);
  assert.equal(fs.readFileSync(first.ledger_path, "utf8").trim().split("\n").length, 2);

  assert.throws(
    () => appendFinancialReportShadowHold(hold, { dataDir: "", tenantId: "dais-local" }),
    /data directory/i,
  );
  assert.throws(
    () => appendFinancialReportShadowHold(hold, { dataDir, tenantId: "" }),
    /scope/i,
  );
  assert.throws(
    () => appendFinancialReportShadowHold({ ...hold, status: "sent" }, { dataDir, tenantId: "dais-local" }),
    /hold/i,
  );
  fs.rmSync(dataDir, { recursive: true, force: true });
});
