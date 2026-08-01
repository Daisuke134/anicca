"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const { runEventCoverageRound } = require("./event-coverage-orchestrator.js");

function coverage(openDates) {
  const open = new Set(openDates);
  const days = Array.from({ length: 21 }, (_, index) => {
    const date = new Date(Date.UTC(2026, 7, 2 + index)).toISOString().slice(0, 10);
    return { date, status: open.has(date) ? "open" : "covered_existing", evidence_ref: open.has(date) ? null : `calendar-event://tokyo/${date}` };
  });
  return {
    schema_version: 1,
    window_start: days[0].date,
    window_end: days.at(-1).date,
    days,
    open_count: open.size,
    complete: open.size === 0,
  };
}

test("one operation and one source failure do not stop later open days", async () => {
  const dates = ["2026-08-02", "2026-08-03", "2026-08-04"];
  const calls = [];
  const result = await runEventCoverageRound({
    coverage: coverage(dates),
    runDay: async ({ date }) => {
      calls.push(date);
      if (date === dates[0]) throw new Error("source unavailable");
      if (date === dates[1]) return { status: "recovery_required", reason: "transport_unavailable" };
      return { status: "booked", provider: "luma", date, receipt_ref: "provider-receipt://luma/day-3" };
    },
  });
  assert.deepEqual(calls, dates);
  assert.equal(result.status, "continue_required");
  assert.equal(result.processed_count, 3);
  assert.equal(result.booked_count, 1);
  assert.equal(result.remaining_open_count, 2);
  assert.equal(result.next_run_required, true);
});

test("one complete search round with no booking is continuation, never completion", async () => {
  const dates = ["2026-08-02", "2026-08-03"];
  const result = await runEventCoverageRound({
    coverage: coverage(dates),
    runDay: async ({ date }) => ({ status: "coverage_open", date, reason: "provider_candidates_exhausted" }),
  });
  assert.equal(result.status, "continue_required");
  assert.equal(result.round_completed, true);
  assert.equal(result.remaining_open_count, 2);
  assert.equal(result.completed_falsely, undefined);
});

test("only open zero is complete and causes no provider operations", async () => {
  let calls = 0;
  const result = await runEventCoverageRound({
    coverage: coverage([]),
    runDay: async () => { calls += 1; },
  });
  assert.equal(calls, 0);
  assert.equal(result.status, "complete");
  assert.equal(result.remaining_open_count, 0);
  assert.equal(result.next_run_required, false);
});

test("invalid booked receipt does not close the day and later days still run", async () => {
  const dates = ["2026-08-02", "2026-08-03"];
  let calls = 0;
  const result = await runEventCoverageRound({
    coverage: coverage(dates),
    runDay: async ({ date }) => {
      calls += 1;
      return calls === 1
        ? { status: "booked", provider: "luma", date, receipt_ref: "missing" }
        : { status: "booked", provider: "connpass", date, receipt_ref: "provider-receipt://connpass/day-2" };
    },
  });
  assert.equal(calls, 2);
  assert.equal(result.booked_count, 1);
  assert.equal(result.remaining_open_count, 1);
  assert.equal(result.open_days[0].reason, "unverified_result");
});
