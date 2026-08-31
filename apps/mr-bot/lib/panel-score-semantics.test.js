"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { buildScorePeriods, computePanelScores } = require("./panel-score-semantics.js");

const NOW = Date.parse("2026-07-15T12:00:00.000Z");
const TENANT = "tenant-a";

function uuid(n, prefix = "30000000") {
  return `${prefix}-0000-4000-8000-${String(n).padStart(12, "0")}`;
}

function row(n, organ, entity, kind, status, extras = {}) {
  return {
    public_ref: uuid(n, "30000000"), revision_key: uuid(n, "40000000"), uid: extras.uid || TENANT,
    organ, entity_key: entity, outcome_kind: kind, outcome_status: status,
    occurred_at: extras.occurred_at || "2026-07-14T09:00:00.000Z",
    resolved_at: extras.resolved_at == null ? null : extras.resolved_at,
    recorded_at: extras.recorded_at || extras.occurred_at || "2026-07-14T09:00:00.000Z",
    amount_minor: extras.amount_minor == null ? null : extras.amount_minor,
    currency: extras.currency == null ? null : extras.currency,
    components: extras.components || {},
  };
}

function compute(organ, rows, timeZone = "UTC", nowMs = NOW) {
  const grouped = { uid: TENANT, daily: [], physical: [], mental: [], financial: [] };
  grouped[organ] = rows;
  return computePanelScores(grouped, buildScorePeriods(nowMs, timeZone), timeZone)[organ];
}

test("score periods use user-wall-clock days, exact month start, and half-open timestamps", () => {
  const utc = buildScorePeriods(NOW, "UTC");
  assert.deepEqual(utc.daily, { kind: "rolling_7_days", start_at: "2026-07-08T12:00:00.000Z", end_at: "2026-07-15T12:00:00.000Z" });
  assert.deepEqual(utc.physical, { kind: "rolling_30_days", start_at: "2026-06-15T12:00:00.000Z", end_at: "2026-07-15T12:00:00.000Z" });
  assert.deepEqual(utc.financial, { kind: "calendar_month", start_at: "2026-07-01T00:00:00.000Z", end_at: "2026-07-15T12:00:00.000Z" });
  assert.equal(buildScorePeriods(Date.parse("2026-03-15T06:30:00Z"), "America/New_York").daily.start_at, "2026-03-08T07:30:00.000Z");
  assert.equal(buildScorePeriods(Date.parse("2026-11-08T06:30:00Z"), "America/New_York").daily.start_at, "2026-11-01T05:30:00.000Z");
  assert.equal(buildScorePeriods(NOW, "No/Such_Zone").timezone, "UTC");
});

test("DAILY deduplicates immutable revisions and resists retries, activity inflation, bounds, and other tenants", () => {
  const rows = [
    row(1, "daily", "event", "daily_call", "required_succeeded", { recorded_at: "2026-07-14T10:00:00Z" }),
    row(2, "daily", "event", "daily_call", "required_failed", { recorded_at: "2026-07-14T11:00:00Z" }),
    row(2, "daily", "event", "daily_call", "required_failed", { recorded_at: "2026-07-14T11:00:00Z" }),
    row(3, "daily", "optional", "daily_travel", "optional"),
    row(4, "daily", "start", "daily_late", "context_unnecessary", { occurred_at: "2026-07-08T12:00:00.000Z" }),
    row(5, "daily", "end", "daily_late", "required_succeeded", { occurred_at: "2026-07-15T12:00:00.000Z" }),
    row(6, "daily", "other", "daily_late", "required_succeeded", { uid: "tenant-b" }),
    { ...row(7, "daily", "unknown", "api_call", "succeeded"), outcome_kind: "api_call" },
  ];
  const actual = compute("daily", rows);
  assert.equal(actual.denominator, 2);
  assert.equal(actual.numerator, 1);
  assert.equal(actual.value, 50);
  assert.equal(actual.components.optional_ignored, 1);
  assert.equal(actual.components.excluded_unknown_count, 1);
  assert.equal(actual.source_outcome_ids.length, 3);
});

test("same-status correction and status re-entry select the deterministic latest revision", () => {
  const rows = [
    row(10, "daily", "event", "daily_call", "required_pending", { recorded_at: "2026-07-14T09:00:00Z" }),
    row(11, "daily", "event", "daily_call", "required_failed", { recorded_at: "2026-07-14T10:00:00Z" }),
    row(12, "daily", "event", "daily_call", "required_pending", { recorded_at: "2026-07-14T11:00:00Z" }),
    row(13, "daily", "event", "daily_call", "required_succeeded", { recorded_at: "2026-07-14T12:00:00Z" }),
    row(14, "daily", "event", "daily_call", "required_succeeded", { recorded_at: "2026-07-14T13:00:00Z", components: { correction: true } }),
  ];
  const forward = compute("daily", rows);
  const reverse = compute("daily", rows.slice().reverse());
  assert.deepEqual(reverse, forward);
  assert.equal(forward.value, 100);
  assert.deepEqual(forward.source_outcome_ids, [`outcome:${uuid(14, "30000000")}`]);
});

test("PHYSICAL confirmation precedence beats later candidates and counts each need once", () => {
  const actual = compute("physical", [
    row(20, "physical", "need-1", "physical_need", "confirmed_booking", { recorded_at: "2026-07-10T09:00:00Z" }),
    row(21, "physical", "need-1", "physical_need", "candidate", { recorded_at: "2026-07-11T09:00:00Z" }),
    row(22, "physical", "need-2", "physical_need", "detected"),
  ]);
  assert.deepEqual({ value: actual.value, numerator: actual.numerator, denominator: actual.denominator }, { value: 50, numerator: 1, denominator: 2 });
  assert.equal(actual.components.confirmed_booking, 1);
  assert.equal(actual.components.unresolved_needs, 1);
});

test("MENTAL validates delivery timestamps and enforces three deliveries per local day deterministically", () => {
  const rows = [1, 2, 3, 4].map((n) => row(30 + n, "mental", `trigger-${n}`, "mental_trigger", "delivered", {
    occurred_at: `2026-07-14T${String(n + 6).padStart(2, "0")}:00:00.000Z`, resolved_at: `2026-07-14T${String(n + 6).padStart(2, "0")}:01:00.000Z`, components: { intervention_valid: true },
  }));
  rows.push(row(35, "mental", "bad-time", "mental_trigger", "delivered", { resolved_at: "2026-07-15T12:00:00.000Z", components: { intervention_valid: true } }));
  rows.push(row(36, "mental", "suppressed", "mental_trigger", "suppression_honored", { components: { send_count: 0 } }));
  rows.push(row(37, "mental", "corrected", "mental_trigger", "correction_persisted", { components: { context_persisted: true } }));
  const actual = compute("mental", rows);
  assert.deepEqual({ numerator: actual.numerator, denominator: actual.denominator, value: actual.value }, { numerator: 5, denominator: 7, value: 71 });
  assert.equal(actual.components.delivered_within_cap, 3);
  assert.equal(actual.components.cap_overflow, 1);
  assert.equal(actual.components.unresolved_triggers, 1);
});

test("FINANCIAL uses integer-safe verified net, keeps transfers separate, and clamps negative net", () => {
  const actual = compute("financial", [
    row(40, "financial", "income", "financial_external_income", "verified", { amount_minor: 1000, currency: "USD" }),
    row(41, "financial", "loss", "financial_realized_loss", "realized", { amount_minor: 200, currency: "USD" }),
    row(42, "financial", "fee", "financial_fee", "charged", { amount_minor: 100, currency: "USD" }),
    row(43, "financial", "transfer", "financial_user_transfer", "confirmed", { amount_minor: 300, currency: "USD" }),
    row(44, "financial", "deposit", "financial_deposit", "excluded", { amount_minor: 999, currency: "USD" }),
  ]);
  assert.deepEqual({ numerator: actual.numerator, denominator: actual.denominator, value: actual.value }, { numerator: 700, denominator: 1000, value: 70 });
  assert.equal(actual.components.user_transfer_minor, 300);
  assert.equal(actual.components.excluded_rows, 1);
  assert.equal(actual.components.net_clamped, false);
});

test("FINANCIAL fails closed for mixed currency and unsafe integer, never faking zero performance", () => {
  const mixed = compute("financial", [
    row(50, "financial", "income", "financial_external_income", "verified", { amount_minor: 100, currency: "USD" }),
    row(51, "financial", "fee", "financial_fee", "charged", { amount_minor: 1, currency: "EUR" }),
  ]);
  assert.deepEqual({ status: mixed.status, value: mixed.value, numerator: mixed.numerator, denominator: mixed.denominator }, { status: "invalid_data", value: null, numerator: null, denominator: null });
  assert.equal(mixed.reason, "Financial outcomes use more than one currency.");
  const unsafe = compute("financial", [row(52, "financial", "income", "financial_external_income", "verified", { amount_minor: "9007199254740992", currency: "USD" })]);
  assert.equal(unsafe.status, "invalid_data");
  assert.equal(unsafe.reason, "Financial outcome amount is outside the supported range.");
  for (const organ of ["daily", "physical", "mental", "financial"]) assert.equal(compute(organ, []).status, "insufficient_data");
});

test("all organ envelopes use the closed schema and privacy-safe sorted references", () => {
  const periods = buildScorePeriods(NOW, "UTC");
  const result = computePanelScores({ uid: TENANT, daily: [], physical: [], mental: [], financial: [] }, periods, "UTC");
  assert.deepEqual(Object.keys(result), ["daily", "physical", "mental", "financial"]);
  for (const [name, organ] of Object.entries(result)) {
    assert.deepEqual(Object.keys(organ), ["status", "value", "period", "numerator", "denominator", "reason", "source_outcome_ids", "components"], name);
    assert.equal(organ.status, "insufficient_data");
    assert.equal(organ.value, null);
  }

  const daily = compute("daily", Array.from({ length: 40 }, (_, index) => row(100 + index, "daily", `event-${index}`, "daily_call", index < 23 ? "required_succeeded" : "required_failed")));
  const physical = compute("physical", Array.from({ length: 40 }, (_, index) => row(200 + index, "physical", `need-${index}`, "physical_need", index < 23 ? "confirmed_booking" : "detected")));
  const mental = compute("mental", Array.from({ length: 40 }, (_, index) => row(300 + index, "mental", `trigger-${index}`, "mental_trigger", index < 23 ? "suppression_honored" : "unresolved", { components: index < 23 ? { send_count: 0 } : {} })));
  for (const actual of [daily, physical, mental]) {
    assert.deepEqual({ numerator: actual.numerator, denominator: actual.denominator, value: actual.value }, { numerator: 23, denominator: 40, value: 58 });
  }
});
