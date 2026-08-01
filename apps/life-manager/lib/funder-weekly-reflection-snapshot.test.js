"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { collectFunderWeeklyReflectionSnapshot } = require("./funder-weekly-reflection-snapshot.js");

test("one tenant-bound SQL snapshot joins submission/outreach exposures to typed results", async () => {
  const calls = [];
  const value = await collectFunderWeeklyReflectionSnapshot({
    tenantId: "dais-local",
    week_start: "2026-07-26T15:00:00.000Z",
    week_end: "2026-08-02T11:15:00.000Z",
    candidateIds: ["next-alpha"],
  }, { query: async (sql, params) => {
    calls.push({ sql, params });
    return { rows: [
      {
        record_kind: "exposure", exposure_id: "funder-outreach:alpha", candidate_id: "alpha",
        exposure_kind: "outreach", occurred_at: new Date("2026-07-28T01:00:00.000Z"),
        subject_sha256: "a".repeat(64), body_sha256: "b".repeat(64),
        result_id: null, status: null, observed_at: null,
      },
      {
        record_kind: "result", exposure_id: "funder-outreach:alpha", candidate_id: "alpha",
        exposure_kind: null, occurred_at: null, subject_sha256: null, body_sha256: null,
        result_id: "funder-result:meeting", status: "meeting_requested",
        observed_at: new Date("2026-07-31T02:00:00.000Z"),
      },
    ] };
  } });
  assert.equal(calls.length, 1);
  assert.match(calls[0].sql, /lm_funder_submission_ledger/);
  assert.match(calls[0].sql, /lm_funder_outreach_ledger/);
  assert.match(calls[0].sql, /lm_outbound_result_ledger/);
  assert.match(calls[0].sql, /lm_funder_inbound_status_ledger/);
  assert.match(calls[0].sql, /outcome_result_ids \? result_id/);
  assert.match(calls[0].sql, /outcome_result_ids \? observation_id/);
  assert.doesNotMatch(calls[0].sql, /lm_funder_registry_snapshots/);
  assert.deepEqual(calls[0].params, [
    "dais-local", "2026-07-26T15:00:00.000Z", "2026-08-02T11:15:00.000Z",
  ]);
  assert.deepEqual(value.candidates, ["next-alpha"]);
  assert.equal(value.results[0].exposure_id, "funder-outreach:alpha");
});

test("a late-committed learnable result is carried into the next unreflected week", async () => {
  const value = await collectFunderWeeklyReflectionSnapshot({
    tenantId: "dais-local",
    week_start: "2026-08-02T15:00:00.000Z",
    week_end: "2026-08-09T11:15:00.000Z",
    candidateIds: ["next-alpha"],
  }, { query: async () => ({ rows: [{
    record_kind: "exposure", exposure_id: "funder-outreach:alpha", candidate_id: "alpha",
    exposure_kind: "outreach", occurred_at: "2026-07-28T01:00:00.000Z",
    subject_sha256: "a".repeat(64), body_sha256: "b".repeat(64),
  }, {
    record_kind: "result", exposure_id: "funder-outreach:alpha", candidate_id: "alpha",
    result_id: "funder-result:late-meeting", status: "meeting_requested",
    observed_at: "2026-08-01T02:00:00.000Z",
  }] }) });
  assert.equal(value.results[0].result_id, "funder-result:late-meeting");
});

test("orphan result and duplicated supplied candidate set fail closed", async () => {
  await assert.rejects(() => collectFunderWeeklyReflectionSnapshot({
    tenantId: "dais-local",
    week_start: "2026-07-26T15:00:00.000Z",
    week_end: "2026-08-02T11:15:00.000Z",
  }, { query: async () => ({ rows: [{
    record_kind: "result", exposure_id: "funder-outreach:missing", candidate_id: "alpha",
    result_id: "funder-result:meeting", status: "meeting_requested",
    observed_at: "2026-07-31T02:00:00.000Z",
  }] }) }), /invalid/);

  await assert.rejects(() => collectFunderWeeklyReflectionSnapshot({
    tenantId: "dais-local", week_start: "2026-07-26T15:00:00.000Z",
    week_end: "2026-08-02T11:15:00.000Z", candidateIds: ["alpha", "alpha"],
  }, { query: async () => ({ rows: [] }) }), /invalid/);
});
