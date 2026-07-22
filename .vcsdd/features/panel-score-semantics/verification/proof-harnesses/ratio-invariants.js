"use strict";

const assert = require("node:assert/strict");
const path = require("node:path");

const REPO_ROOT = path.resolve(__dirname, "../../../../..");
const { buildScorePeriods, computePanelScores } = require(path.join(REPO_ROOT, "apps/life-call/lib/panel-score-semantics.js"));

const NOW_MS = Date.parse("2026-07-15T12:00:00.000Z");
const TENANT = "proof-tenant";
const GENERATED_SEED = 0x51c0a7e1;
const MAX_SAFE = BigInt(Number.MAX_SAFE_INTEGER);
const periods = buildScorePeriods(NOW_MS, "UTC");

function uuid(index, prefix) {
  return `${prefix}-0000-4000-8000-${String(index).padStart(12, "0")}`;
}

function baseRow(index, organ, status, extras = {}) {
  return {
    public_ref: uuid(index, "51000000"),
    revision_key: uuid(index, "52000000"),
    uid: TENANT,
    organ,
    entity_key: `entity-${index}`,
    outcome_kind: organ === "daily" ? "daily_call" : organ === "physical" ? "physical_need" : "mental_trigger",
    outcome_status: status,
    occurred_at: "2026-07-14T09:00:00.000Z",
    resolved_at: null,
    recorded_at: "2026-07-14T09:00:00.000Z",
    amount_minor: null,
    currency: null,
    components: organ === "mental" && status === "suppression_honored" ? { send_count: 0 } : {},
    ...extras,
  };
}

function computeNonFinancial(organ, requestedNumerator, denominator) {
  const numerator = Math.min(requestedNumerator, denominator);
  const rows = [];
  for (let index = 0; index < denominator; index += 1) {
    const success = index < numerator;
    const status = organ === "daily"
      ? (success ? "required_succeeded" : "required_failed")
      : organ === "physical"
        ? (success ? "confirmed_booking" : "detected")
        : (success ? "suppression_honored" : "unresolved");
    rows.push(baseRow(index + 1, organ, status));
  }
  const grouped = { uid: TENANT, daily: [], physical: [], mental: [], financial: [] };
  grouped[organ] = rows;
  return computePanelScores(grouped, periods, "UTC")[organ];
}

function financialRow(index, kind, status, amount) {
  return {
    public_ref: uuid(index, "53000000"),
    revision_key: uuid(index, "54000000"),
    uid: TENANT,
    organ: "financial",
    entity_key: `financial-${index}`,
    outcome_kind: kind,
    outcome_status: status,
    occurred_at: "2026-07-10T09:00:00.000Z",
    resolved_at: null,
    recorded_at: "2026-07-10T09:00:00.000Z",
    amount_minor: amount.toString(),
    currency: "USD",
    components: {},
  };
}

function computeFinancial(numerator, denominator) {
  const rows = [financialRow(1, "financial_external_income", "verified", denominator)];
  const loss = denominator - numerator;
  if (loss > 0n) rows.push(financialRow(2, "financial_realized_loss", "realized", loss));
  const grouped = { uid: TENANT, daily: [], physical: [], mental: [], financial: rows };
  return computePanelScores(grouped, periods, "UTC").financial;
}

function expectedPercent(numerator, denominator) {
  if (denominator === 0n) return null;
  return Number((numerator * 200n + denominator) / (denominator * 2n));
}

function assertRatio(actual, numerator, denominator, label) {
  if (denominator === 0n) {
    assert.deepEqual(
      { status: actual.status, value: actual.value, numerator: actual.numerator, denominator: actual.denominator },
      { status: "insufficient_data", value: null, numerator: 0, denominator: 0 },
      label,
    );
    return;
  }
  assert.equal(actual.status, "measured", `${label}.status`);
  assert.equal(actual.numerator, Number(numerator), `${label}.numerator`);
  assert.equal(actual.denominator, Number(denominator), `${label}.denominator`);
  assert.equal(actual.value, expectedPercent(numerator, denominator), `${label}.value`);
  assert.ok(actual.value >= 0 && actual.value <= 100, `${label}.clamped`);
}

function createPrng(seed) {
  let state = seed >>> 0;
  return () => {
    state ^= state << 13;
    state ^= state >>> 17;
    state ^= state << 5;
    return state >>> 0;
  };
}

function nextSafeInteger(next) {
  const high = BigInt(next() & 0x1fffff);
  const low = BigInt(next());
  return (high << 32n) | low;
}

let boundedPairs = 0;
let nonFinancialEvaluations = 0;
for (let denominator = 0; denominator <= 256; denominator += 1) {
  for (let requestedNumerator = 0; requestedNumerator <= 256; requestedNumerator += 1) {
    const expectedNumerator = Math.min(requestedNumerator, denominator);
    for (const organ of ["daily", "physical", "mental"]) {
      const actual = computeNonFinancial(organ, requestedNumerator, denominator);
      assert.ok(actual.numerator >= 0 && actual.numerator <= actual.denominator, `${organ}.${requestedNumerator}.${denominator}.bounded`);
      assertRatio(actual, BigInt(expectedNumerator), BigInt(denominator), `${organ}.${requestedNumerator}.${denominator}`);
      nonFinancialEvaluations += 1;
    }
    boundedPairs += 1;
  }
}

const boundaryPairs = [
  [0n, 0n],
  [0n, 1n],
  [1n, 1n],
  [0n, MAX_SAFE],
  [1n, MAX_SAFE],
  [MAX_SAFE / 2n, MAX_SAFE],
  [MAX_SAFE / 2n + 1n, MAX_SAFE],
  [MAX_SAFE - 1n, MAX_SAFE],
  [MAX_SAFE, MAX_SAFE],
  [MAX_SAFE - 2n, MAX_SAFE - 1n],
  [4503599627370495n, 9007199254740990n],
  [4503599627370496n, 9007199254740991n],
];
for (const [numerator, denominator] of boundaryPairs) {
  assertRatio(computeFinancial(numerator, denominator), numerator, denominator, `boundary.${numerator}.${denominator}`);
}

const next = createPrng(GENERATED_SEED);
const generatedPairs = 10000;
for (let index = 0; index < generatedPairs; index += 1) {
  const denominator = nextSafeInteger(next);
  const numerator = denominator === 0n ? 0n : nextSafeInteger(next) % (denominator + 1n);
  assertRatio(computeFinancial(numerator, denominator), numerator, denominator, `generated.${index}`);
}

console.log(
  `PROP-001 PASS bounded_pairs=${boundedPairs} non_financial_evaluations=${nonFinancialEvaluations} boundary_pairs=${boundaryPairs.length} generated_pairs=${generatedPairs} seed=0x${GENERATED_SEED.toString(16)}`,
);
