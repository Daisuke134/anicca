"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

const { buildRollingEventCoverage } = require("./rolling-event-coverage.js");
const {
  isVerifiedConnectorCoverageContinuation,
  planConnectorCoverageContinuation,
} = require("./connector-coverage-continuation.js");

function coverage(resolvedDays = []) {
  return buildRollingEventCoverage({
    tenantId: "dais-local",
    timeZone: "Asia/Tokyo",
    now: "2026-08-01T16:00:00.000Z",
    resolvedDays,
  });
}

test("search exhaustion, one operation failure, and one source failure all schedule continuation", () => {
  for (const observed_status of ["search_exhausted", "operation_failed", "source_failed"]) {
    const result = planConnectorCoverageContinuation({
      coverage: coverage(),
      observedOutcomes: [{ observed_status, date: "2026-08-02" }],
      now: "2026-08-02T01:00:00.000Z",
    });
    assert.equal(result.status, "continue");
    assert.equal(result.open_date_count, 21);
    assert.equal(result.next_action, "refresh_inventory");
    assert.equal(result.next_run_at, "2026-08-02T01:05:00.000Z");
    assert.equal(isVerifiedConnectorCoverageContinuation(result), true);
    assert.equal(isVerifiedConnectorCoverageContinuation(structuredClone(result)), false);
  }
});

test("reconciliation and recovery take priority without ending the coverage loop", () => {
  const reconcile = planConnectorCoverageContinuation({
    coverage: coverage(),
    observedOutcomes: [
      { observed_status: "source_failed", date: "2026-08-02" },
      { observed_status: "reconciliation_required", date: "2026-08-03" },
    ],
    now: "2026-08-02T01:00:00.000Z",
  });
  assert.equal(reconcile.status, "continue");
  assert.equal(reconcile.next_action, "reconcile_effect");

  const recover = planConnectorCoverageContinuation({
    coverage: coverage(),
    observedOutcomes: [{ observed_status: "recovery_required", date: "2026-08-02" }],
    now: "2026-08-02T01:00:00.000Z",
  });
  assert.equal(recover.status, "continue");
  assert.equal(recover.next_action, "recover_source");
});

test("only zero open dates completes the rolling loop", () => {
  const statuses = ["covered_existing", "covered_new", "unavailable"];
  const resolved = Array.from({ length: 21 }, (_, index) => ({
    date: new Date(Date.UTC(2026, 7, 2 + index)).toISOString().slice(0, 10),
    status: statuses[index % statuses.length],
    evidence_refs: [`evidence://coverage/${index}/${"a".repeat(64)}`],
  }));
  const result = planConnectorCoverageContinuation({
    coverage: coverage(resolved), observedOutcomes: [], now: "2026-08-02T01:00:00.000Z",
  });
  assert.deepEqual(result, {
    continuation_id: result.continuation_id,
    coverage_snapshot_id: result.coverage_snapshot_id,
    status: "complete",
    open_date_count: 0,
    next_action: null,
    next_run_at: null,
  });
});

test("plain coverage, unknown outcomes, dates outside the window, and malformed time fail closed", () => {
  const verified = coverage();
  assert.throws(() => planConnectorCoverageContinuation({
    coverage: structuredClone(verified), observedOutcomes: [], now: "2026-08-02T01:00:00.000Z",
  }), /coverage continuation invalid/i);
  for (const observedOutcomes of [
    [{ observed_status: "gave_up", date: "2026-08-02" }],
    [{ observed_status: "source_failed", date: "2026-09-01" }],
  ]) assert.throws(() => planConnectorCoverageContinuation({
    coverage: verified, observedOutcomes, now: "2026-08-02T01:00:00.000Z",
  }), /coverage continuation invalid/i);
  assert.throws(() => planConnectorCoverageContinuation({
    coverage: verified, observedOutcomes: [], now: "tomorrow",
  }), /coverage continuation invalid/i);
});
