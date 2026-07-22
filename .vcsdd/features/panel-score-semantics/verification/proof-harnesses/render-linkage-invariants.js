"use strict";

const assert = require("node:assert/strict");
const path = require("node:path");

const REPO_ROOT = path.resolve(__dirname, "../../../../..");
const { buildScorePeriods, computePanelScores } = require(path.join(REPO_ROOT, "apps/life-call/lib/panel-score-semantics.js"));
const { renderScoreCards } = require(path.join(REPO_ROOT, "apps/life-call/lib/panel-ui.js"));

const TENANT = "proof-tenant";
const periods = buildScorePeriods(Date.parse("2026-07-15T12:00:00.000Z"), "UTC");

function uuid(index, prefix) {
  return `${prefix}-0000-4000-8000-${String(index).padStart(12, "0")}`;
}

function row(index, organ, entity, kind, status, extras = {}) {
  return {
    id: 9000 + index,
    provider_id: `provider-secret-${index}`,
    public_ref: uuid(index, "91000000"),
    revision_key: uuid(index, "92000000"),
    uid: TENANT,
    organ,
    entity_key: entity,
    outcome_kind: kind,
    outcome_status: status,
    occurred_at: "2026-07-14T09:00:00.000Z",
    resolved_at: extras.resolved_at || null,
    recorded_at: extras.recorded_at || "2026-07-14T09:00:00.000Z",
    amount_minor: extras.amount_minor == null ? null : extras.amount_minor,
    currency: extras.currency == null ? null : extras.currency,
    components: { raw_internal_id: `internal-${index}`, ...(extras.components || {}) },
  };
}

const rowsByOrgan = {
  uid: TENANT,
  daily: [
    row(1, "daily", "private-event-a", "daily_call", "required_succeeded"),
    row(2, "daily", "private-event-b", "daily_call", "required_failed"),
  ],
  physical: [
    row(3, "physical", "private-need-a", "physical_need", "confirmed_booking"),
    row(4, "physical", "private-need-b", "physical_need", "search"),
  ],
  mental: [
    row(5, "mental", "private-trigger-a", "mental_trigger", "suppression_honored", { components: { send_count: 0 } }),
    row(6, "mental", "private-trigger-b", "mental_trigger", "correction_persisted", { components: { context_persisted: true } }),
    row(7, "mental", "private-trigger-c", "mental_trigger", "unresolved"),
  ],
  financial: [
    row(8, "financial", "private-income", "financial_external_income", "verified", { amount_minor: 1000, currency: "USD" }),
    row(9, "financial", "private-loss", "financial_realized_loss", "realized", { amount_minor: 200, currency: "USD" }),
    row(10, "financial", "private-fee", "financial_fee", "charged", { amount_minor: 100, currency: "USD" }),
    row(11, "financial", "private-transfer", "financial_user_transfer", "confirmed", { amount_minor: 300, currency: "USD" }),
  ],
};

const scores = computePanelScores(rowsByOrgan, periods, "UTC");
const expectedRatios = {
  daily: [1, 2],
  physical: [1, 2],
  mental: [2, 3],
  financial: [700, 1000],
};
const expectedRefs = {
  daily: [1, 2],
  physical: [3, 4],
  mental: [5, 6, 7],
  financial: [8, 9, 10, 11],
};

function componentRatio(name, components) {
  if (name === "daily") return [components.resolved_events, components.eligible_events];
  if (name === "physical") return [components.confirmed_booking + components.confirmed_completion, components.detected_needs];
  if (name === "mental") return [components.delivered_within_cap + components.suppression_honored + components.correction_persisted, components.deduplicated_triggers];
  return [Math.max(0, components.gross_income_minor - components.realized_loss_minor - components.fee_minor), components.gross_income_minor];
}

for (const name of ["daily", "physical", "mental", "financial"]) {
  const organ = scores[name];
  assert.deepEqual([organ.numerator, organ.denominator], expectedRatios[name], `${name}.literal-ratio`);
  assert.deepEqual(componentRatio(name, organ.components), expectedRatios[name], `${name}.component-ratio`);
  assert.deepEqual(
    organ.source_outcome_ids,
    expectedRefs[name].map((index) => `outcome:${uuid(index, "91000000")}`).sort(),
    `${name}.winner-refs`,
  );
  assert.equal(organ.value, Math.round(organ.numerator / organ.denominator * 100), `${name}.value`);
  assert.ok(organ.reason.includes(String(organ.numerator)), `${name}.reason-numerator`);
  assert.ok(organ.reason.includes(String(organ.denominator)), `${name}.reason-denominator`);
}

const modelText = JSON.stringify(scores);
for (const forbidden of ["provider-secret", "raw_internal_id", "internal-", "private-event", "private-need", "private-trigger", "private-income", "private-loss", "private-fee", "private-transfer", "revision_key", `\"uid\":\"${TENANT}\"`]) {
  assert.ok(!modelText.includes(forbidden), `model excludes ${forbidden}`);
}

const html = renderScoreCards({ organs: scores });
assert.equal((html.match(/data-score-organ=/g) || []).length, 4);
for (const name of ["daily", "physical", "mental", "financial"]) {
  const [numerator, denominator] = expectedRatios[name];
  assert.match(html, new RegExp(`outcomes ${numerator} / ${denominator}`), `${name}.rendered-ratio`);
  assert.match(html, new RegExp(`根拠 ${expectedRefs[name].length}件`), `${name}.rendered-ref-count`);
  assert.ok(html.includes(scores[name].reason), `${name}.rendered-reason`);
}
for (const index of expectedRefs.financial.concat(expectedRefs.daily, expectedRefs.physical, expectedRefs.mental)) {
  assert.ok(!html.includes(uuid(index, "91000000")), `opaque ref ${index} is not rendered raw`);
}
assert.doesNotMatch(html, /provider-secret|raw_internal_id|internal-|private-(?:event|need|trigger|income|loss|fee|transfer)|revision_key/);

const contradictory = structuredClone(scores);
contradictory.daily.numerator = 0;
assert.throws(() => renderScoreCards({ organs: contradictory }), /invalid score payload/);

console.log("PROP-006 PASS organs=4 linkage_cases=4 exact_winner_ref_sets=4 raw_identifier_leaks=0 contradictory_models_rejected=1");
