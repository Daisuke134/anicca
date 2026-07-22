"use strict";

const assert = require("node:assert/strict");
const path = require("node:path");

const REPO_ROOT = path.resolve(__dirname, "../../../../..");
const { buildScorePeriods, computePanelScores } = require(path.join(REPO_ROOT, "apps/life-call/lib/panel-score-semantics.js"));

const SEED = 0x8a17c0de;
const SET_COUNT = 500;
const PERMUTATIONS_PER_SET = 21;
const TENANT = "proof-tenant";
const periods = buildScorePeriods(Date.parse("2026-07-15T12:00:00.000Z"), "UTC");

const CATALOG = Object.freeze({
  daily: Object.freeze({
    daily_travel: Object.freeze(["required_succeeded", "required_failed", "required_pending", "context_unnecessary", "optional"]),
    daily_call: Object.freeze(["required_succeeded", "required_failed", "required_pending", "context_unnecessary", "optional"]),
    daily_late: Object.freeze(["required_succeeded", "required_failed", "required_pending", "context_unnecessary", "optional"]),
  }),
  physical: Object.freeze({ physical_need: Object.freeze(["detected", "candidate", "search", "unconfirmed_request", "confirmed_booking", "confirmed_completion", "unresolved"]) }),
  mental: Object.freeze({ mental_trigger: Object.freeze(["delivered", "suppression_honored", "correction_persisted", "cap_overflow", "unresolved"]) }),
  financial: Object.freeze({
    financial_external_income: Object.freeze(["verified"]),
    financial_realized_loss: Object.freeze(["realized"]),
    financial_fee: Object.freeze(["charged"]),
    financial_user_transfer: Object.freeze(["confirmed"]),
    financial_self_funding: Object.freeze(["excluded"]),
    financial_deposit: Object.freeze(["excluded"]),
    financial_internal_move: Object.freeze(["excluded"]),
    financial_unverified: Object.freeze(["excluded"]),
  }),
});

function createPrng(seed) {
  let state = seed >>> 0;
  return () => {
    state ^= state << 13;
    state ^= state >>> 17;
    state ^= state << 5;
    return state >>> 0;
  };
}

function uuid(index, prefix) {
  return `${prefix}-0000-4000-8000-${String(index).padStart(12, "0")}`;
}

function rowFacts(organ, status) {
  if (organ === "mental" && status === "delivered") return { resolved_at: "2026-07-14T09:01:00.000Z", components: { intervention_valid: true } };
  if (organ === "mental" && status === "suppression_honored") return { components: { send_count: 0 } };
  if (organ === "mental" && status === "correction_persisted") return { components: { context_persisted: true } };
  return { components: {} };
}

function makeGeneratedSet(setIndex, next, coverage) {
  const organs = ["daily", "physical", "mental", "financial"];
  const organ = organs[setIndex % organs.length];
  const kinds = Object.keys(CATALOG[organ]);
  const entityCount = 1 + (next() % 7);
  const rows = [];
  for (let entityIndex = 0; entityIndex < entityCount; entityIndex += 1) {
    const kind = kinds[(setIndex + entityIndex) % kinds.length];
    const statuses = CATALOG[organ][kind];
    const revisionCount = 1 + (next() % 4);
    for (let revisionIndex = 0; revisionIndex < revisionCount; revisionIndex += 1) {
      const status = statuses[(setIndex + entityIndex + revisionIndex) % statuses.length];
      coverage.add(`${organ}:${kind}:${status}`);
      const identity = setIndex * 100 + entityIndex * 10 + revisionIndex + 1;
      const tieSecond = revisionIndex > 0 && revisionIndex % 2 === 1;
      const recordedAt = tieSecond ? "2026-07-14T10:00:00.000Z" : `2026-07-14T${String(9 + (revisionIndex % 2)).padStart(2, "0")}:00:00.000Z`;
      const facts = rowFacts(organ, status);
      rows.push({
        public_ref: uuid(identity, "61000000"),
        revision_key: uuid(identity, "62000000"),
        uid: TENANT,
        organ,
        entity_key: `set-${setIndex}-entity-${entityIndex}`,
        outcome_kind: kind,
        outcome_status: status,
        occurred_at: "2026-07-14T09:00:00.000Z",
        resolved_at: facts.resolved_at || null,
        recorded_at: recordedAt,
        amount_minor: organ === "financial" ? String(1 + (next() % 10000)) : null,
        currency: organ === "financial" ? "USD" : null,
        components: facts.components,
      });
    }
  }
  const retry = { ...rows[0], components: { ...rows[0].components } };
  rows.push(retry);
  return { organ, rows, entityCount };
}

function grouped(organ, rows) {
  const value = { uid: TENANT, daily: [], physical: [], mental: [], financial: [] };
  value[organ] = rows;
  return value;
}

function rotate(rows, count) {
  if (rows.length < 2) return rows.slice();
  const offset = count % rows.length;
  return rows.slice(offset).concat(rows.slice(0, offset));
}

function shuffle(rows, next) {
  const copy = rows.slice();
  for (let index = copy.length - 1; index > 0; index -= 1) {
    const swap = next() % (index + 1);
    [copy[index], copy[swap]] = [copy[swap], copy[index]];
  }
  return copy;
}

function project(organ) {
  return ({
    status: organ.status,
    value: organ.value,
    numerator: organ.numerator,
    denominator: organ.denominator,
    source_outcome_ids: organ.source_outcome_ids,
    components: organ.components,
  });
}

function literalRow(publicRef, revisionKey, organ, entity, kind, status, recordedAt, extras = {}) {
  return {
    public_ref: publicRef,
    revision_key: revisionKey,
    uid: TENANT,
    organ,
    entity_key: entity,
    outcome_kind: kind,
    outcome_status: status,
    occurred_at: "2026-07-14T09:00:00.000Z",
    resolved_at: extras.resolved_at || null,
    recorded_at: recordedAt,
    amount_minor: extras.amount_minor == null ? null : extras.amount_minor,
    currency: extras.currency == null ? null : extras.currency,
    components: extras.components || {},
  };
}

const fixedFixtures = [
  {
    organ: "daily",
    rows: [
      literalRow("71000000-0000-4000-8000-000000000001", "72000000-0000-4000-8000-000000000001", "daily", "event", "daily_call", "required_succeeded", "2026-07-14T09:00:00.000Z"),
      literalRow("71000000-0000-4000-8000-000000000002", "72000000-0000-4000-8000-000000000002", "daily", "event", "daily_call", "required_failed", "2026-07-14T10:00:00.000Z"),
    ],
    expected: { status: "measured", value: 0, numerator: 0, denominator: 1, source_outcome_ids: ["outcome:71000000-0000-4000-8000-000000000002"] },
  },
  {
    organ: "physical",
    rows: [
      literalRow("71000000-0000-4000-8000-000000000003", "72000000-0000-4000-8000-000000000003", "physical", "need", "physical_need", "confirmed_booking", "2026-07-14T09:00:00.000Z"),
      literalRow("71000000-0000-4000-8000-000000000004", "72000000-0000-4000-8000-000000000004", "physical", "need", "physical_need", "candidate", "2026-07-14T11:00:00.000Z"),
    ],
    expected: { status: "measured", value: 100, numerator: 1, denominator: 1, source_outcome_ids: ["outcome:71000000-0000-4000-8000-000000000003"] },
  },
  {
    organ: "mental",
    rows: [literalRow("71000000-0000-4000-8000-000000000005", "72000000-0000-4000-8000-000000000005", "mental", "trigger", "mental_trigger", "suppression_honored", "2026-07-14T09:00:00.000Z", { components: { send_count: 0 } })],
    expected: { status: "measured", value: 100, numerator: 1, denominator: 1, source_outcome_ids: ["outcome:71000000-0000-4000-8000-000000000005"] },
  },
  {
    organ: "financial",
    rows: [
      literalRow("71000000-0000-4000-8000-000000000006", "72000000-0000-4000-8000-000000000006", "financial", "income", "financial_external_income", "verified", "2026-07-14T09:00:00.000Z", { amount_minor: 100, currency: "USD" }),
      literalRow("71000000-0000-4000-8000-000000000007", "72000000-0000-4000-8000-000000000007", "financial", "fee", "financial_fee", "charged", "2026-07-14T10:00:00.000Z", { amount_minor: 25, currency: "USD" }),
    ],
    expected: { status: "measured", value: 75, numerator: 75, denominator: 100, source_outcome_ids: ["outcome:71000000-0000-4000-8000-000000000006", "outcome:71000000-0000-4000-8000-000000000007"] },
  },
];

for (const fixture of fixedFixtures) {
  const actual = project(computePanelScores(grouped(fixture.organ, fixture.rows), periods, "UTC")[fixture.organ]);
  for (const [key, value] of Object.entries(fixture.expected)) assert.deepEqual(actual[key], value, `fixed.${fixture.organ}.${key}`);
}

const next = createPrng(SEED);
const coverage = new Set();
let permutationCases = 0;
let minEntities = Infinity;
let maxEntities = -Infinity;
for (let setIndex = 0; setIndex < SET_COUNT; setIndex += 1) {
  const generated = makeGeneratedSet(setIndex, next, coverage);
  minEntities = Math.min(minEntities, generated.entityCount);
  maxEntities = Math.max(maxEntities, generated.entityCount);
  const baseline = computePanelScores(grouped(generated.organ, generated.rows), periods, "UTC");
  permutationCases += 1;
  const variants = [
    generated.rows.slice().reverse(),
    rotate(generated.rows, 1 + (setIndex % generated.rows.length)),
  ];
  for (let permutation = 0; permutation < PERMUTATIONS_PER_SET; permutation += 1) variants.push(shuffle(generated.rows, next));
  for (const variant of variants) {
    assert.deepEqual(computePanelScores(grouped(generated.organ, variant), periods, "UTC"), baseline, `set.${setIndex}.order`);
    permutationCases += 1;
  }
}

const expectedCoverage = new Set();
for (const [organ, kinds] of Object.entries(CATALOG)) {
  for (const [kind, statuses] of Object.entries(kinds)) {
    for (const status of statuses) expectedCoverage.add(`${organ}:${kind}:${status}`);
  }
}
assert.deepEqual([...coverage].sort(), [...expectedCoverage].sort(), "all typed organ kind/state pairs are covered");
assert.equal(permutationCases, 12000);
assert.equal(minEntities, 1);
assert.equal(maxEntities, 7);

console.log(`PROP-002 PASS seed=0x${SEED.toString(16).toUpperCase()} row_sets=${SET_COUNT} cases=${permutationCases} shuffles_per_set=${PERMUTATIONS_PER_SET} fixed_fixtures=${fixedFixtures.length} typed_pairs=${coverage.size} entity_range=${minEntities}..${maxEntities}`);
