"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const fixture = require("../eval/score-semantics-cases.json");
const { buildPeriodsIndependent, recomputeIndependent } = require("./independent-panel-score-readback.js");

const sourcePath = path.join(__dirname, "independent-panel-score-readback.js");

function uuid(n, prefix) {
  return `${prefix}-0000-4000-8000-${String(n).padStart(12, "0")}`;
}

function expand(row, organ) {
  return {
    public_ref: uuid(row.n, "10000000"), revision_key: uuid(row.n, "20000000"), uid: row.uid || fixture.tenant,
    organ, entity_key: row.entity, outcome_kind: row.kind, outcome_status: row.status,
    occurred_at: row.at, resolved_at: row.resolved == null ? null : row.resolved, recorded_at: row.recorded || row.at,
    amount_minor: row.amount == null ? null : row.amount, currency: row.currency == null ? null : row.currency, components: row.components || {},
  };
}

test("independent production oracle has no production scorer/API/UI imports", () => {
  const source = fs.readFileSync(sourcePath, "utf8");
  assert.doesNotMatch(source, /require\([^)]*(panel-score-semantics|panel-api|panel-ui)/);
  assert.doesNotMatch(source, /from\s+["'][^"']*(panel-score-semantics|panel-api|panel-ui)/);
});

test("independent production oracle matches every literal period and score case in the closed matrix", () => {
  let passed = 0;
  for (const periodCase of fixture.periodCases) {
    const periods = buildPeriodsIndependent(Date.parse(periodCase.now), periodCase.timeZone);
    for (const [organ, expected] of Object.entries(periodCase.expected)) assert.deepEqual([periods[organ].start_at, periods[organ].end_at], expected, `${periodCase.id}.${organ}`);
    if (periodCase.effectiveTimeZone) assert.equal(periods.timezone, periodCase.effectiveTimeZone);
    passed += 1;
  }
  const periods = buildPeriodsIndependent(Date.parse(fixture.defaultNow), fixture.defaultTimeZone);
  for (const scoreCase of fixture.scoreCases) {
    for (const variant of [scoreCase, ...(scoreCase.variants || []).map((item) => ({ ...item, organ: scoreCase.organ }))]) {
      const rowsByOrgan = { uid: fixture.tenant, daily: [], physical: [], mental: [], financial: [] };
      rowsByOrgan[variant.organ] = variant.rows.map((row) => expand(row, variant.organ));
      const actual = recomputeIndependent(rowsByOrgan, periods, fixture.defaultTimeZone)[variant.organ];
      for (const key of ["status", "value", "numerator", "denominator"]) assert.deepEqual(actual[key], variant.expected[key], `${variant.id}.${key}`);
      if (variant.expected.reason) assert.equal(actual.reason, variant.expected.reason, `${variant.id}.reason`);
      assert.equal(actual.source_outcome_ids.length, variant.expected.sourceCount, `${variant.id}.sourceCount`);
      for (const [key, value] of Object.entries(variant.expected.components || {})) assert.deepEqual(actual.components[key], value, `${variant.id}.components.${key}`);
    }
    passed += 1;
  }
  assert.equal(passed, fixture.periodCases.length + fixture.scoreCases.length);
});
