"use strict";

const assert = require("node:assert/strict");
const path = require("node:path");

const REPO_ROOT = path.resolve(__dirname, "../../../../..");
const { buildScorePeriods, computePanelScores } = require(path.join(REPO_ROOT, "apps/life-call/lib/panel-score-semantics.js"));
const TENANT = "proof-tenant";

const periodCases = [
  {
    name: "utc",
    now: "2026-07-15T12:00:00.000Z",
    zone: "UTC",
    expectedZone: "UTC",
    expected: { daily: "2026-07-08T12:00:00.000Z", physical: "2026-06-15T12:00:00.000Z", mental: "2026-07-08T12:00:00.000Z", financial: "2026-07-01T00:00:00.000Z" },
  },
  {
    name: "invalid-zone",
    now: "2026-07-15T12:00:00.000Z",
    zone: "Invalid/Proof_Zone",
    expectedZone: "UTC",
    expected: { daily: "2026-07-08T12:00:00.000Z", physical: "2026-06-15T12:00:00.000Z", mental: "2026-07-08T12:00:00.000Z", financial: "2026-07-01T00:00:00.000Z" },
  },
  {
    name: "spring-gap",
    now: "2026-03-15T06:30:00.000Z",
    zone: "America/New_York",
    expectedZone: "America/New_York",
    expected: { daily: "2026-03-08T07:30:00.000Z", mental: "2026-03-08T07:30:00.000Z", financial: "2026-03-01T05:00:00.000Z" },
  },
  {
    name: "fall-overlap",
    now: "2026-11-08T06:30:00.000Z",
    zone: "America/New_York",
    expectedZone: "America/New_York",
    expected: { daily: "2026-11-01T05:30:00.000Z", mental: "2026-11-01T05:30:00.000Z", financial: "2026-11-01T04:00:00.000Z" },
  },
  {
    name: "month-edge-tokyo",
    now: "2026-08-01T00:00:00.000Z",
    zone: "Asia/Tokyo",
    expectedZone: "Asia/Tokyo",
    expected: { financial: "2026-07-31T15:00:00.000Z" },
  },
  {
    name: "leap-month-edge",
    now: "2028-03-01T00:15:00.000Z",
    zone: "UTC",
    expectedZone: "UTC",
    expected: { financial: "2028-03-01T00:00:00.000Z" },
  },
];

for (const fixture of periodCases) {
  const periods = buildScorePeriods(Date.parse(fixture.now), fixture.zone);
  assert.equal(periods.timezone, fixture.expectedZone, `${fixture.name}.timezone`);
  for (const [organ, startAt] of Object.entries(fixture.expected)) assert.equal(periods[organ].start_at, startAt, `${fixture.name}.${organ}.start_at`);
  for (const organ of ["daily", "physical", "mental", "financial"]) assert.equal(periods[organ].end_at, fixture.now, `${fixture.name}.${organ}.end_at`);
}
assert.throws(() => buildScorePeriods(Number.NaN, "UTC"), (error) => error && error.code === "period_resolution_failed");

function uuid(index, prefix) {
  return `${prefix}-0000-4000-8000-${String(index).padStart(12, "0")}`;
}

function boundaryRow(index, organ, occurredAt) {
  const details = {
    daily: ["daily_call", "required_succeeded", null, null, {}],
    physical: ["physical_need", "confirmed_booking", null, null, {}],
    mental: ["mental_trigger", "suppression_honored", null, null, { send_count: 0 }],
    financial: ["financial_external_income", "verified", 10, "USD", {}],
  }[organ];
  return {
    public_ref: uuid(index, "73000000"),
    revision_key: uuid(index, "74000000"),
    uid: TENANT,
    organ,
    entity_key: `${organ}-${index}`,
    outcome_kind: details[0],
    outcome_status: details[1],
    occurred_at: occurredAt,
    resolved_at: null,
    recorded_at: occurredAt,
    amount_minor: details[2],
    currency: details[3],
    components: details[4],
  };
}

const inclusionPeriods = buildScorePeriods(Date.parse("2026-07-15T12:00:00.000Z"), "UTC");
let inclusionCases = 0;
for (const organ of ["daily", "physical", "mental", "financial"]) {
  const period = inclusionPeriods[organ];
  const startMs = Date.parse(period.start_at);
  const endMs = Date.parse(period.end_at);
  const rows = [
    boundaryRow(1, organ, new Date(startMs - 1).toISOString()),
    boundaryRow(2, organ, period.start_at),
    boundaryRow(3, organ, new Date(endMs - 1).toISOString()),
    boundaryRow(4, organ, period.end_at),
  ];
  const grouped = { uid: TENANT, daily: [], physical: [], mental: [], financial: [] };
  grouped[organ] = rows;
  const actual = computePanelScores(grouped, inclusionPeriods, "UTC")[organ];
  const expectedDenominator = organ === "financial" ? 20 : 2;
  assert.equal(actual.denominator, expectedDenominator, `${organ}.half-open.denominator`);
  assert.equal(actual.numerator, expectedDenominator, `${organ}.half-open.numerator`);
  assert.deepEqual(actual.source_outcome_ids, [
    `outcome:${uuid(2, "73000000")}`,
    `outcome:${uuid(3, "73000000")}`,
  ], `${organ}.half-open.refs`);
  inclusionCases += 1;
}

console.log(`PROP-003 PASS period_cases=${periodCases.length} inclusion_cases=${inclusionCases} invalid_clock_cases=1 intervals=[start,end)`);
