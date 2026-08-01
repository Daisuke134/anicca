"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const { buildFunderWeeklyReflection, isVerifiedFunderWeeklyReflection } = require("./funder-weekly-reflection.js");
const { appendFunderWeeklyReflection, loadLatestFunderWeeklyReflection } = require("./funder-weekly-reflection-store.js");

const MIGRATION = fs.readFileSync(path.join(__dirname, "../migrations/2026-08-02-lm-funder-weekly-reflection-ledger.sql"), "utf8");

function reflection() {
  return buildFunderWeeklyReflection({
    tenantId: "dais-local",
    reflectedAt: "2026-08-02T12:00:00.000Z",
    exposures: [{
      exposure_id: "funder-outreach:alpha",
      candidate_id: "alpha",
      exposure_kind: "outreach",
      occurred_at: "2026-07-28T01:00:00.000Z",
      subject_sha256: "a".repeat(64),
      body_sha256: "b".repeat(64),
    }],
    results: [],
    candidates: ["alpha"],
  });
}

function changedReflection() {
  return buildFunderWeeklyReflection({
    tenantId: "dais-local",
    reflectedAt: "2026-08-02T12:00:00.000Z",
    exposures: [{
      exposure_id: "funder-outreach:alpha", candidate_id: "alpha", exposure_kind: "outreach",
      occurred_at: "2026-07-28T01:00:00.000Z", subject_sha256: "a".repeat(64), body_sha256: "b".repeat(64),
    }],
    results: [{
      result_id: "funder-result:meeting", exposure_id: "funder-outreach:alpha",
      candidate_id: "alpha", status: "meeting_requested", observed_at: "2026-07-31T02:00:00.000Z",
    }],
    candidates: ["alpha"],
    judgment: {
      kind: "agent_judgment", decision: "change", summary: "The pitch produced a meeting.",
      rationale: "Carry the verified workflow into the next pitch.",
      used_result_ids: ["funder-result:meeting"], ranked_candidate_ids: ["alpha"],
      pitch_directives: [{ candidate_id: "alpha", directive: "Lead with the verified workflow.",
        outcome_result_ids: ["funder-result:meeting"] }],
    },
  });
}

test("migration creates tenant/week append-only service-role ledger", () => {
  assert.match(MIGRATION, /CREATE TABLE IF NOT EXISTS public\.lm_funder_weekly_reflection_ledger/i);
  assert.match(MIGRATION, /UNIQUE \(tenant_id, week_key\)/i);
  assert.match(MIGRATION, /BEFORE UPDATE OR DELETE/i);
  assert.match(MIGRATION, /BEFORE TRUNCATE/i);
  assert.match(MIGRATION, /ENABLE ROW LEVEL SECURITY/i);
  assert.match(MIGRATION, /GRANT SELECT, INSERT[^;]+service_role/is);
  assert.match(MIGRATION, /lm_validate_funder_outreach_reflection_application/i);
  assert.match(MIGRATION, /DEFERRABLE INITIALLY DEFERRED/i);
  assert.match(MIGRATION, /current funder outreach reflection application required/i);
  assert.doesNotMatch(MIGRATION, /GRANT[^;]+(?:UPDATE|DELETE|TRUNCATE)[^;]+service_role/is);
});

test("store only appends verified reflections and supports exact replay", async () => {
  const value = reflection();
  const calls = [];
  const result = await appendFunderWeeklyReflection(value, {
    query: async (sql, params) => {
      calls.push({ sql, params });
      return { rows: [{ reflection_id: value.reflection_id, inserted: true }] };
    },
  });
  assert.deepEqual(result, { reflection_id: value.reflection_id, inserted: true });
  assert.match(calls[0].sql, /ON CONFLICT DO NOTHING/i);
  assert.doesNotMatch(calls[0].sql, /UPDATE/i);
  await assert.rejects(() => appendFunderWeeklyReflection(JSON.parse(JSON.stringify(value)), {
    query: async () => ({ rows: [] }),
  }), /invalid/);
});

test("latest DB row is structurally reverified and branded before planner use", async () => {
  const value = changedReflection();
  const row = {
    ...value,
    outcome_result_ids: [...value.outcome_result_ids],
    ranked_candidate_ids: [...value.ranked_candidate_ids],
    pitch_directives: [...value.pitch_directives],
  };
  const loaded = await loadLatestFunderWeeklyReflection({
    tenantId: "dais-local",
    before: "2026-08-03T00:00:00.000Z",
  }, { query: async (sql) => {
    assert.match(sql, /decision='change'/i);
    assert.match(sql, /NOT EXISTS[\s\S]+lm_funder_outreach_reflection_application/i);
    return { rows: [row] };
  } });
  assert.equal(loaded.reflection_id, value.reflection_id);
  assert.equal(isVerifiedFunderWeeklyReflection(loaded), true);

  await assert.rejects(() => loadLatestFunderWeeklyReflection({
    tenantId: "dais-local",
    before: "2026-08-03T00:00:00.000Z",
  }, { query: async () => ({ rows: [{ ...row, reason: "tampered" }] }) }), /invalid/);
});
