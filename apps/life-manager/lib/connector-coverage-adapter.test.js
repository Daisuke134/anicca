"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

const { buildRollingEventCoverage } = require("./rolling-event-coverage.js");
const { planConnectorCoverageContinuation } = require("./connector-coverage-continuation.js");
const { buildConnectorCoverageJob } = require("./connector-coverage-job.js");
const {
  createConnectorCoverageLoopAdapter,
} = require("./connector-coverage-adapter.js");

function sourceCoverage(resolvedDays = []) {
  return buildRollingEventCoverage({
    tenantId: "dais-local", timeZone: "Asia/Tokyo",
    now: "2026-08-01T16:00:00.000Z", resolvedDays,
  });
}

function claimedJob(coverage) {
  const continuation = planConnectorCoverageContinuation({
    coverage, observedOutcomes: [], now: "2026-08-02T01:00:00.000Z",
  });
  return {
    ...buildConnectorCoverageJob({
      tenantId: "dais-local", coverage, continuation,
      identityRef: "identity://dais-local/luma",
      browserProfileRef: "browser-profile://cloakbrowser/daily-driver",
      calendarRef: "calendar://google/primary",
    }),
    attempt: 1,
  };
}

function allUnavailable() {
  return Array.from({ length: 21 }, (_, index) => ({
    date: new Date(Date.UTC(2026, 7, 2 + index)).toISOString().slice(0, 10),
    status: "unavailable",
    evidence_refs: [`calendar-evidence://google/event/${String(index).padStart(64, "a")}`],
  }));
}

test("refresh worker reads, saves, and schedules the next durable coverage job while open remains", async () => {
  const current = sourceCoverage();
  const next = sourceCoverage([allUnavailable()[0]]);
  const calls = [];
  const adapter = createConnectorCoverageLoopAdapter({
    coverageStore: {
      async read(ref) { calls.push(["read", ref]); return current; },
      async save(value) { calls.push(["save", value]); return value; },
    },
    async refreshCoverage(input) {
      calls.push(["refresh", input]);
      return {
        coverage: next,
        observedOutcomes: [{ date: "2026-08-02", observed_status: "search_exhausted" }],
      };
    },
    async enqueueContinuation(input) { calls.push(["enqueue", input]); return { created: true }; },
    now: () => "2026-08-02T01:10:00.000Z",
  });
  const job = claimedJob(current);
  const execution = await adapter.execute(job);
  assert.equal(execution.receipt.status, "continue");
  assert.equal(execution.receipt.open_date_count, 20);
  assert.equal(adapter.verify(execution.receipt, job), true);
  assert.deepEqual(calls.map(([name]) => name), ["read", "refresh", "save", "enqueue"]);
  assert.equal(calls[0][1], job.input_refs.coverage_snapshot_ref);
  assert.equal(calls[2][1], next);
  assert.equal(calls[3][1].coverage, next);
  assert.equal(calls[3][1].continuation.next_run_at, "2026-08-02T01:15:00.000Z");
});

test("open zero completes without another enqueue", async () => {
  const current = sourceCoverage();
  const complete = sourceCoverage(allUnavailable());
  let enqueues = 0;
  const adapter = createConnectorCoverageLoopAdapter({
    coverageStore: { async read() { return current; }, async save(value) { return value; } },
    async refreshCoverage() { return { coverage: complete, observedOutcomes: [] }; },
    async enqueueContinuation() { enqueues += 1; },
    now: () => "2026-08-02T01:10:00.000Z",
  });
  const job = claimedJob(current);
  const execution = await adapter.execute(job);
  assert.equal(execution.receipt.status, "complete");
  assert.equal(execution.receipt.open_date_count, 0);
  assert.equal(enqueues, 0);
});

test("fake jobs, fake refreshed coverage, tenant drift, and malformed outcomes fail closed", async () => {
  const current = sourceCoverage();
  const job = claimedJob(current);
  const make = (refreshCoverage) => createConnectorCoverageLoopAdapter({
    coverageStore: { async read() { return current; }, async save(value) { return value; } },
    refreshCoverage,
    async enqueueContinuation() {},
    now: () => "2026-08-02T01:10:00.000Z",
  });
  await assert.rejects(make(async () => ({ coverage: structuredClone(current), observedOutcomes: [] })).execute(job), /coverage adapter invalid/i);
  await assert.rejects(make(async () => ({ coverage: current, observedOutcomes: [{ date: "bad", observed_status: "booked" }] })).execute(job), /coverage continuation invalid/i);
  await assert.rejects(make(async () => ({ coverage: current, observedOutcomes: [] })).execute({ ...job, tenant_id: "other" }), /coverage adapter invalid/i);
  await assert.rejects(make(async () => ({ coverage: current, observedOutcomes: [] })).execute({ ...job, input_refs: { ...job.input_refs, password_ref: "secret" } }), /coverage adapter invalid/i);
});

test("adapter exposes plan, execute, reconcile, verify, and report", async () => {
  const current = sourceCoverage();
  const adapter = createConnectorCoverageLoopAdapter({
    coverageStore: { async read() { return current; }, async save(value) { return value; } },
    async refreshCoverage() { return { coverage: current, observedOutcomes: [] }; },
    async enqueueContinuation() {},
    now: () => "2026-08-02T01:10:00.000Z",
  });
  for (const method of ["plan", "execute", "reconcile", "verify", "report"]) {
    assert.equal(typeof adapter[method], "function");
  }
  const planned = await adapter.plan({
    tenantId: "dais-local", coverage: current,
    continuation: planConnectorCoverageContinuation({ coverage: current, observedOutcomes: [], now: "2026-08-02T01:00:00.000Z" }),
    identityRef: "identity://dais-local/luma",
    browserProfileRef: "browser-profile://cloakbrowser/daily-driver",
    calendarRef: "calendar://google/primary",
  });
  assert.equal(planned.length, 1);
  assert.equal((await adapter.reconcile({})).state, "absent");
  assert.deepEqual(adapter.report({ kind: "connector_coverage_refresh", status: "continue", open_date_count: 21 }), {
    status: "continue", open_date_count: 21,
  });
});
