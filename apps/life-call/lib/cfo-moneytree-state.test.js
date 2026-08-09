"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");
const { adaptMoneytreeAccounts } = require("./cfo-moneytree.js");
const { validateFinancialSourceResult } = require("./cfo-financial-source.js");
const { deriveMoneytreeState, composeMoneytreeRead } = require("./cfo-moneytree-state.js");

const OBSERVED_AT = "2026-08-09T06:00:00+09:00";
const CUTOFF = "2026-08-08T06:00:00+09:00";
const FRESH_AS_OF = "2026-08-09T05:00:00+09:00";
const STALE_AS_OF = "2026-08-07T05:00:00+09:00";
const INPUT_KEYS = ["aggregationAsOf", "aggregationFreshnessCutoff", "liabilitiesExposed", "liabilityCount", "observedAt", "signal"];
const STATE_KEYS = ["aggregationAsOf", "aggregationStatus", "consentEvidence", "consentStatus", "liabilityCount", "liabilityCoverage", "observedAt", "partial", "retrievalStatus", "schemaVersion", "sourceId", "actionRequired"];

function input(signal, overrides = {}) {
  return { signal, observedAt: OBSERVED_AT, aggregationAsOf: null, aggregationFreshnessCutoff: null, liabilitiesExposed: false, liabilityCount: null, ...overrides };
}
function expected(signal, overrides = {}) {
  const base = {
    schemaVersion: 1, sourceId: "moneytree_mufg", retrievalStatus: "succeeded", consentStatus: "valid",
    consentEvidence: signal === "interactive_success" ? "interactive_session" : "provider_metadata", observedAt: OBSERVED_AT,
    aggregationStatus: "unknown", aggregationAsOf: null, liabilityCoverage: "unknown", liabilityCount: null, partial: true, actionRequired: null,
  };
  if (signal === "expired" || signal === "revoked") Object.assign(base, { retrievalStatus: "unavailable", consentStatus: signal, aggregationStatus: "unknown", consentEvidence: "provider_metadata", actionRequired: { kind: "reconsent", actionRef: "action:moneytree_reconsent" } });
  if (signal === "provider_outage") Object.assign(base, { retrievalStatus: "unavailable", consentStatus: "unknown", consentEvidence: "provider_error", actionRequired: { kind: "provider_outage", actionRef: "action:moneytree_outage" } });
  return { ...base, ...overrides };
}
function assertFrozen(value) {
  assert.equal(Object.isFrozen(value), true);
  for (const child of Object.values(value)) if (child && typeof child === "object") assertFrozen(child);
}
function assertInvalid(call) {
  assert.throws(call, (error) => {
    assert.match(error.message, /^moneytree_state_invalid:[a-z_]+$/);
    assert.doesNotMatch(error.message, /secret|private|raw|9999999/i);
    return true;
  });
}

test("interactive success is explicit about unknown aggregation and liabilities", () => {
  const sourceInput = input("interactive_success");
  const result = deriveMoneytreeState(sourceInput);
  assert.deepEqual(Object.keys(sourceInput).sort(), INPUT_KEYS.sort());
  assert.deepEqual(result, expected("interactive_success"));
  assert.deepEqual(Object.keys(result).sort(), STATE_KEYS.sort());
  assert.equal(result.actionRequired, null);
  assertFrozen(result);
});

for (const signal of ["interactive_success", "expired", "revoked", "provider_outage"]) test(`rejects exposed liabilities on ${signal}`, () => assertInvalid(() => deriveMoneytreeState(input(signal, { liabilitiesExposed: true, liabilityCount: 0 }))));

for (const [count, name] of [[0, "zero"], [2, "positive"]]) {
  test(`authorized ${name} liabilities are fresh and complete`, () => {
    const result = deriveMoneytreeState(input("authorized", { aggregationAsOf: FRESH_AS_OF, aggregationFreshnessCutoff: CUTOFF, liabilitiesExposed: true, liabilityCount: count }));
    assert.deepEqual(result, expected("authorized", { aggregationStatus: "fresh", aggregationAsOf: FRESH_AS_OF, liabilityCoverage: "complete", liabilityCount: count, partial: false }));
    assertFrozen(result);
  });
}

test("authorized older aggregation is stale", () => {
  assert.deepEqual(deriveMoneytreeState(input("authorized", { aggregationAsOf: STALE_AS_OF, aggregationFreshnessCutoff: CUTOFF, liabilitiesExposed: true, liabilityCount: 0 })), expected("authorized", { aggregationStatus: "stale", aggregationAsOf: STALE_AS_OF, liabilityCoverage: "complete", liabilityCount: 0, partial: true }));
});

test("authorized without provider metadata stays unknown and partial", () => {
  assert.deepEqual(deriveMoneytreeState(input("authorized")), expected("authorized"));
});

for (const signal of ["expired", "revoked", "provider_outage"]) {
  test(`${signal} is unavailable with its fixed action`, () => {
    const result = deriveMoneytreeState(input(signal));
    assert.deepEqual(result, expected(signal));
    assert.deepEqual(Object.keys(result.actionRequired).sort(), ["actionRef", "kind"]);
    assertFrozen(result);
  });
}

const invalidInputs = [
  ["unknown key", (value) => { value.rawPayload = "secret"; }],
  ["unknown signal", (value) => { value.signal = "pending"; }],
  ["invalid observed timestamp", (value) => { value.observedAt = "2026-02-30T06:00:00+09:00"; }],
  ["invalid cutoff timestamp", (value) => { value.aggregationAsOf = FRESH_AS_OF; value.aggregationFreshnessCutoff = "2026-08-08T06:00:00"; }],
  ["only aggregation timestamp", (value) => { value.aggregationAsOf = FRESH_AS_OF; }],
  ["metadata without authorization", (value) => { value.signal = "interactive_success"; value.aggregationAsOf = FRESH_AS_OF; value.aggregationFreshnessCutoff = CUTOFF; }],
  ["numeric count while unexposed", (value) => { value.liabilityCount = 0; }],
  ["exposed null count", (value) => { value.signal = "authorized"; value.liabilitiesExposed = true; }],
  ["exposed negative count", (value) => { value.signal = "authorized"; value.liabilitiesExposed = true; value.liabilityCount = -1; }],
  ["exposed float count", (value) => { value.signal = "authorized"; value.liabilitiesExposed = true; value.liabilityCount = 1.5; }],
  ["exposed unsafe count", (value) => { value.signal = "authorized"; value.liabilitiesExposed = true; value.liabilityCount = Number.MAX_SAFE_INTEGER + 1; }],
  ["exposed non-authorized liabilities", (value) => { value.signal = "revoked"; value.liabilitiesExposed = true; value.liabilityCount = 0; }],
];
for (const [name, mutate] of invalidInputs) test(`rejects ${name} with a stable redacted error`, () => { const value = input("authorized"); mutate(value); assertInvalid(() => deriveMoneytreeState(value)); });

function accountsPayload() {
  return { type: "accounts", data: { baseCurrency: "JPY", accountGroups: { banks: [{ institutionKey: "mufg_bank", accounts: [{ id: 42, account_subtype: "savings", current_balance: 100, currency: "JPY" }] }] } } };
}
const ADAPTER_INPUT = { accountsJson: JSON.stringify(accountsPayload()), observedAt: OBSERVED_AT, referenceKey: "synthetic-reference-key-32-bytes-long" };
function sourceLiteral(overrides = {}) {
  return validateFinancialSourceResult({
    schemaVersion: 1, sourceId: "moneytree_mufg", consent: "valid", freshness: "fresh", asOf: OBSERVED_AT,
    accounts: [{ accountRef: "source_account:synthetic_deposit", label: "サンプル銀行", kind: "deposit", currency: "JPY", balanceMinor: 100, verificationStatus: "provider_reported" }],
    liabilities: [], evidenceRef: "evidence:synthetic_moneytree_read", partial: true, actionRequired: null, ...overrides,
  });
}
function sourceFor(signal, state) {
  if (signal === "interactive_success") return adaptMoneytreeAccounts(ADAPTER_INPUT);
  if (signal === "authorized") return sourceLiteral({ partial: state.partial, liabilities: state.liabilityCount === 0 ? [] : [{ accountRef: "source_account:synthetic_loan", label: "サンプルローン", currency: "JPY", balanceMinor: 50, verificationStatus: "provider_reported" }] });
  const unavailable = { accountRef: "source_account:synthetic_deposit", label: "サンプル銀行", kind: "deposit", currency: "JPY", balanceMinor: null, verificationStatus: "unavailable" };
  return validateFinancialSourceResult({ schemaVersion: 1, sourceId: "moneytree_mufg", consent: signal === "provider_outage" ? "unknown" : signal, freshness: "unavailable", asOf: OBSERVED_AT, accounts: [unavailable], liabilities: [], evidenceRef: "evidence:synthetic_moneytree_outage", partial: true, actionRequired: { kind: signal === "provider_outage" ? "provider_outage" : "reconsent", sourceLabel: "Moneytree", actionRef: signal === "provider_outage" ? "action:moneytree_outage" : "action:moneytree_reconsent" } });
}

for (const signal of ["interactive_success", "authorized", "expired", "revoked", "provider_outage"]) {
  test(`composes validated ${signal} source and state`, () => {
    const state = deriveMoneytreeState(input(signal, signal === "authorized" ? { aggregationAsOf: FRESH_AS_OF, aggregationFreshnessCutoff: CUTOFF, liabilitiesExposed: true, liabilityCount: 0 } : {}));
    const bundle = composeMoneytreeRead({ source: sourceFor(signal, state), state });
    assert.deepEqual(Object.keys(bundle).sort(), ["schemaVersion", "source", "state"]);
    assert.equal(bundle.source.sourceId, bundle.state.sourceId);
    assert.equal(bundle.source.asOf, bundle.state.observedAt);
    assert.equal(bundle.state.consentStatus, bundle.source.consent);
    assert.equal(bundle.state.retrievalStatus === "succeeded", bundle.source.freshness !== "unavailable");
    assert.equal(bundle.state.partial, bundle.source.partial);
    if (bundle.state.liabilityCoverage === "complete") assert.equal(bundle.source.liabilities.length, bundle.state.liabilityCount);
    assert.deepEqual(bundle.state.actionRequired && { kind: bundle.state.actionRequired.kind, actionRef: bundle.state.actionRequired.actionRef }, bundle.source.actionRequired && { kind: bundle.source.actionRequired.kind, actionRef: bundle.source.actionRequired.actionRef });
    assertFrozen(bundle);
  });
}

test("composition rejects availability, action, consent, partial, and liability mismatches", () => {
  const authorized = deriveMoneytreeState(input("authorized", { aggregationAsOf: FRESH_AS_OF, aggregationFreshnessCutoff: CUTOFF, liabilitiesExposed: true, liabilityCount: 0 }));
  const source = sourceLiteral({ partial: false });
  for (const mutate of [
    (value) => { value.freshness = "unavailable"; value.accounts[0].balanceMinor = null; value.accounts[0].verificationStatus = "unavailable"; value.partial = true; },
    (value) => { value.actionRequired = { kind: "provider_outage", sourceLabel: "Moneytree", actionRef: "action:moneytree_outage" }; },
    (value) => { value.consent = "expired"; value.freshness = "unavailable"; value.accounts[0].balanceMinor = null; value.accounts[0].verificationStatus = "unavailable"; value.partial = true; value.actionRequired = { kind: "reconsent", sourceLabel: "Moneytree", actionRef: "action:moneytree_reconsent" }; },
    (value) => { value.partial = true; },
    (value) => { value.liabilities = [{ accountRef: "source_account:synthetic_loan", label: "サンプルローン", currency: "JPY", balanceMinor: 50, verificationStatus: "provider_reported" }]; },
  ]) { const candidate = structuredClone(source); mutate(candidate); assertInvalid(() => composeMoneytreeRead({ source: validateFinancialSourceResult(candidate), state: authorized })); }
});

test("composition rejects invalid source/state and secret-shaped extras without leaking them", () => {
  const state = deriveMoneytreeState(input("interactive_success"));
  const source = adaptMoneytreeAccounts(ADAPTER_INPUT);
  const invalidState = structuredClone(state); invalidState.rawPayload = "secret";
  assertInvalid(() => composeMoneytreeRead({ source, state: invalidState }));
  const invalidBundle = { source, state, rawPayload: "secret" };
  assertInvalid(() => composeMoneytreeRead(invalidBundle));
});
