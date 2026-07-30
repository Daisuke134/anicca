"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  FINANCIAL_REPORT_SLOTS,
  dueFinancialReportKinds,
  dueFinancialReportSlots,
  financialReportSlotInstant,
  isFinancialReportSlotInstant,
  latestFinancialReportRun,
  latestFinancialReportSlot,
} = require("./financial-report-schedule.js");

const TZ = "Asia/Tokyo";
// 2026-07-30 is a Thursday; 2026-08-02 is a Sunday. JST = UTC+9 all year.
const THU_1959_JST = Date.parse("2026-07-30T10:59:59.000Z");
const THU_2000_JST = Date.parse("2026-07-30T11:00:00.000Z");
const THU_2330_JST = Date.parse("2026-07-30T14:30:00.000Z");
const SUN_2000_JST = Date.parse("2026-08-02T11:00:00.000Z");
const SUN_2005_JST = Date.parse("2026-08-02T11:05:00.000Z");

test("the cadence is the legacy due window, not the 300s poll interval", () => {
  assert.deepEqual(FINANCIAL_REPORT_SLOTS.map(({ kind, time, weekday }) => ({
    kind,
    time,
    weekday,
  })), [
    { kind: "daily", time: "20:00", weekday: null },
    { kind: "weekly", time: "20:05", weekday: 0 },
  ]);
});

test("due kinds match the report runtime's own release window", () => {
  assert.deepEqual(dueFinancialReportKinds(THU_1959_JST, TZ), []);
  assert.deepEqual(dueFinancialReportKinds(THU_2000_JST, TZ), ["daily"]);
  assert.deepEqual(dueFinancialReportKinds(SUN_2000_JST, TZ), ["daily"]);
  assert.deepEqual(dueFinancialReportKinds(SUN_2005_JST, TZ), ["daily", "weekly"]);
});

test("a due slot is the exact local wall-clock instant, stable across polls", () => {
  assert.deepEqual(dueFinancialReportSlots(THU_2000_JST, TZ), [
    { kind: "daily", slot: "2026-07-30T11:00:00.000Z" },
  ]);
  // Every poll inside the same due window resolves to the SAME slot instant, so
  // the derived job identity is idempotent instead of minting one job per poll.
  assert.deepEqual(dueFinancialReportSlots(THU_2000_JST + 1, TZ), [
    { kind: "daily", slot: "2026-07-30T11:00:00.000Z" },
  ]);
  assert.deepEqual(dueFinancialReportSlots(THU_2330_JST, TZ), [
    { kind: "daily", slot: "2026-07-30T11:00:00.000Z" },
  ]);
  assert.deepEqual(dueFinancialReportSlots(SUN_2005_JST, TZ), [
    { kind: "daily", slot: "2026-08-02T11:00:00.000Z" },
    { kind: "weekly", slot: "2026-08-02T11:05:00.000Z" },
  ]);
  assert.deepEqual(dueFinancialReportSlots(THU_1959_JST, TZ), []);
});

test("slot instants resolve per local calendar day and per kind", () => {
  assert.equal(
    financialReportSlotInstant("daily", { year: 2026, month: 7, day: 30 }, TZ),
    "2026-07-30T11:00:00.000Z",
  );
  assert.equal(
    financialReportSlotInstant("weekly", { year: 2026, month: 8, day: 2 }, TZ),
    "2026-08-02T11:05:00.000Z",
  );
  assert.throws(
    () => financialReportSlotInstant("weekly", { year: 2026, month: 7, day: 30 }, TZ),
    /weekly/i,
  );
  assert.throws(() => financialReportSlotInstant("monthly", { year: 2026, month: 7, day: 30 }, TZ), /kind/i);
});

test("the latest slot at or before an instant walks back to earlier local days", () => {
  assert.equal(latestFinancialReportSlot("daily", THU_1959_JST, TZ), "2026-07-29T11:00:00.000Z");
  assert.equal(latestFinancialReportSlot("daily", THU_2000_JST, TZ), "2026-07-30T11:00:00.000Z");
  // The previous weekly slot from Thursday is the prior Sunday, 2026-07-26.
  assert.equal(latestFinancialReportSlot("weekly", THU_2000_JST, TZ), "2026-07-26T11:05:00.000Z");
});

test("the expected-run grid interleaves daily and weekly slots newest first", () => {
  let run = latestFinancialReportRun(SUN_2005_JST, TZ);
  assert.deepEqual(run, {
    kind: "weekly",
    slot: "2026-08-02T11:05:00.000Z",
    period_key: "2026-W31",
  });
  run = latestFinancialReportRun(Date.parse(run.slot) - 1, TZ);
  assert.deepEqual(run, {
    kind: "daily",
    slot: "2026-08-02T11:00:00.000Z",
    period_key: "2026-08-02",
  });
  run = latestFinancialReportRun(Date.parse(run.slot) - 1, TZ);
  assert.deepEqual(run, {
    kind: "daily",
    slot: "2026-08-01T11:00:00.000Z",
    period_key: "2026-08-01",
  });
});

test("only exact cadence instants are recognised as slots", () => {
  assert.equal(isFinancialReportSlotInstant("daily", THU_2000_JST, TZ), true);
  assert.equal(isFinancialReportSlotInstant("daily", THU_2000_JST + 1000, TZ), false);
  // The 5-minute poll buckets the broken enqueue loop used are NOT slots.
  assert.equal(
    isFinancialReportSlotInstant("daily", Date.parse("2026-07-30T04:30:00.000Z"), TZ),
    false,
  );
  assert.equal(isFinancialReportSlotInstant("weekly", SUN_2005_JST, TZ), true);
  assert.equal(isFinancialReportSlotInstant("weekly", THU_2000_JST, TZ), false);
});

test("an invalid time zone or instant fails loudly", () => {
  assert.throws(() => dueFinancialReportKinds(Number.NaN, TZ), /time/i);
  assert.throws(() => dueFinancialReportKinds(THU_2000_JST, "Mars/Olympus"), /time zone/i);
});

test("a period key resolves back to its own cadence slot instant", () => {
  const { financialReportSlotForPeriodKey } = require("./financial-report-schedule.js");
  const { periodBounds } = require("./financial-report-snapshot.js");

  assert.equal(
    financialReportSlotForPeriodKey("daily", "2026-08-05", TZ),
    "2026-08-05T11:00:00.000Z",
  );
  assert.equal(financialReportSlotForPeriodKey("weekly", "2026-W31", TZ), "2026-08-02T11:05:00.000Z");
  // Round trip against the snapshot module's own key derivation.
  for (const slot of ["2026-08-02T11:05:00.000Z", "2026-12-27T11:05:00.000Z", "2027-01-03T11:05:00.000Z"]) {
    const key = periodBounds({ kind: "weekly", nowMs: Date.parse(slot), timezone: TZ }).period_key;
    assert.equal(financialReportSlotForPeriodKey("weekly", key, TZ), slot);
  }
  assert.throws(() => financialReportSlotForPeriodKey("weekly", "2026-08-02", TZ), /period key/i);
  assert.throws(() => financialReportSlotForPeriodKey("daily", "2026-W31", TZ), /period key/i);
});
