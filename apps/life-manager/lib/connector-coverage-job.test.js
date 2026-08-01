"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

const { buildRollingEventCoverage } = require("./rolling-event-coverage.js");
const { planConnectorCoverageContinuation } = require("./connector-coverage-continuation.js");
const {
  CAPABILITY,
  LOOP_ID,
  buildConnectorCoverageJob,
  enqueueConnectorCoverageContinuation,
} = require("./connector-coverage-job.js");

function input() {
  const coverage = buildRollingEventCoverage({
    tenantId: "dais-local", timeZone: "Asia/Tokyo",
    now: "2026-08-01T16:00:00.000Z", resolvedDays: [],
  });
  const continuation = planConnectorCoverageContinuation({
    coverage, observedOutcomes: [], now: "2026-08-02T01:00:00.000Z",
  });
  return {
    tenantId: "dais-local", coverage, continuation,
    identityRef: "identity://dais-local/luma",
    browserProfileRef: "browser-profile://cloakbrowser/daily-driver",
    calendarRef: "calendar://google/primary",
  };
}

test("open coverage becomes one reference-only scheduled refresh job", () => {
  const source = input();
  const job = buildConnectorCoverageJob(source);
  assert.equal(job.capability, CAPABILITY);
  assert.equal(job.loop_id, LOOP_ID);
  assert.equal(job.effect_class, "none");
  assert.equal(job.effect_key, null);
  assert.match(job.job_id, /^connector-coverage:[0-9a-f]{64}$/);
  assert.deepEqual(Object.keys(job.input_refs).sort(), [
    "browser_profile_ref", "calendar_ref", "continuation_ref",
    "coverage_snapshot_ref", "identity_ref",
  ]);
  assert.match(job.input_refs.coverage_snapshot_ref, /^event-coverage:\/\/dais-local\/[0-9a-f]{64}$/);
  assert.match(job.input_refs.continuation_ref, /^connector-continuation:\/\/dais-local\/[0-9a-f]{64}$/);
  assert.doesNotMatch(JSON.stringify(job), /@|password|token|cookie/i);
});

test("scheduled enqueue uses the continuation next_run_at and exact canonical job", async () => {
  const source = input();
  const calls = [];
  const result = await enqueueConnectorCoverageContinuation(source, { query: "store" }, {
    async enqueueJobAt(job, availableAt, storeOptions) {
      calls.push({ job, availableAt, storeOptions });
      return { created: true, job };
    },
  });
  assert.equal(result.created, true);
  assert.equal(calls.length, 1);
  assert.deepEqual(calls[0], {
    job: buildConnectorCoverageJob(source),
    availableAt: source.continuation.next_run_at,
    storeOptions: { query: "store" },
  });
});

test("complete, cloned, mismatched, or secret-bearing inputs cannot enqueue", async () => {
  const source = input();
  assert.throws(() => buildConnectorCoverageJob({
    ...source, coverage: structuredClone(source.coverage),
  }), /Connector coverage job invalid/i);
  assert.throws(() => buildConnectorCoverageJob({
    ...source, continuation: structuredClone(source.continuation),
  }), /Connector coverage job invalid/i);
  assert.throws(() => buildConnectorCoverageJob({
    ...source, identityRef: "raw@example.com",
  }), /Connector coverage job invalid/i);
  const completeCoverage = buildRollingEventCoverage({
    tenantId: "dais-local", timeZone: "Asia/Tokyo", now: "2026-08-01T16:00:00.000Z",
    resolvedDays: Array.from({ length: 21 }, (_, index) => ({
      date: new Date(Date.UTC(2026, 7, 2 + index)).toISOString().slice(0, 10),
      status: "unavailable",
      evidence_refs: [`calendar-evidence://google/event/${String(index).padStart(64, "a")}`],
    })),
  });
  const completeContinuation = planConnectorCoverageContinuation({
    coverage: completeCoverage, observedOutcomes: [], now: "2026-08-02T01:00:00.000Z",
  });
  assert.throws(() => buildConnectorCoverageJob({
    ...source, coverage: completeCoverage, continuation: completeContinuation,
  }), /Connector coverage job complete/i);
});
