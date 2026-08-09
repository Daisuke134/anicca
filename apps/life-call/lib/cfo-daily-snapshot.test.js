"use strict";

const assert = require("node:assert/strict");
const { test } = require("node:test");
const { renderCfoTelegram } = require("./cfo-telegram.js");
const { validateFinancialSourceResult } = require("./cfo-financial-source.js");
const { deriveMoneytreeState, composeMoneytreeRead } = require("./cfo-moneytree-state.js");
const { buildCfoDailyReport } = require("./cfo-daily-snapshot.js");

const OBSERVED_AT = "2026-08-09T06:00:00+09:00";
const CUTOFF = "2026-08-08T06:00:00+09:00";
const STALE_AS_OF = "2026-08-07T05:00:00+09:00";
const ROOT_KEYS = ["schemaVersion", "reportingDate", "revision", "state", "currency", "totals", "sources", "excluded", "repair", "action"];

function accounts(values = [220000, 116594]) {
  return values.map((balanceMinor, index) => ({ accountRef: `source_account:synthetic_${index + 1}`, label: `MUFG 口座 ${index + 1}`, kind: "deposit", currency: "JPY", balanceMinor, verificationStatus: "provider_reported" }));
}
function rawSource(values = [220000, 116594], overrides = {}) {
  return {
    schemaVersion: 1, sourceId: "moneytree_mufg", consent: "valid", freshness: "fresh", asOf: OBSERVED_AT,
    accounts: accounts(values), liabilities: [], evidenceRef: "evidence:synthetic_moneytree_read", partial: true, actionRequired: null, ...overrides,
  };
}
function rawState(overrides = {}) {
  return { schemaVersion: 1, sourceId: "moneytree_mufg", retrievalStatus: "succeeded", consentStatus: "valid", consentEvidence: "interactive_session", observedAt: OBSERVED_AT, aggregationStatus: "unknown", aggregationAsOf: null, liabilityCoverage: "unknown", liabilityCount: null, partial: true, actionRequired: null, ...overrides };
}
function read(values, sourceOverrides = {}, stateOverrides = {}) {
  const source = validateFinancialSourceResult(rawSource(values, sourceOverrides));
  const state = deriveMoneytreeState({ signal: "interactive_success", observedAt: OBSERVED_AT, aggregationAsOf: null, aggregationFreshnessCutoff: null, liabilitiesExposed: false, liabilityCount: null });
  return composeMoneytreeRead({ source, state: { ...state, ...stateOverrides } });
}
function rawRead(values = [220000, 116594], sourceOverrides = {}, stateOverrides = {}) {
  return { schemaVersion: 1, source: rawSource(values, sourceOverrides), state: rawState(stateOverrides) };
}
function invalid(call) { assert.throws(call, /^Error: cfo_daily_snapshot_invalid:/); }
function frozen(value) {
  assert.equal(Object.isFrozen(value), true);
  if (value && typeof value === "object") Object.values(value).forEach(frozen);
}

test("builds the exact partial native-JPY Telegram report", () => {
  const moneytreeRead = read();
  const report = buildCfoDailyReport({ reportingDate: "2026-08-09", moneytreeRead });
  assert.deepEqual(report.totals, { assetsMinor: 336594, liabilitiesMinor: null, netWorthMinor: null, changeMinor: null });
  assert.equal(report.state, "partial");
  assert.deepEqual(report.excluded, [{ label: "負債", reason: "Moneytreeの接続範囲が不明" }]);
  assert.deepEqual(Object.keys(report).sort(), ROOT_KEYS.slice().sort());
  assert.deepEqual(Object.keys(report.sources[0]).sort(), ["sourceId", "label", "status", "asOf", "amountMinor", "verificationStatus"].sort());
  assert.deepEqual(report.sources[0], { sourceId: "moneytree_mufg", label: "MUFG", status: "fresh", asOf: OBSERVED_AT, amountMinor: 336594, verificationStatus: "provider_reported" });
  assert.equal(report.schemaVersion, 1);
  assert.equal(report.revision, 1);
  assert.equal(report.currency, "JPY");
  assert.equal(report.repair, null);
  assert.equal(report.action, null);
  assert.doesNotThrow(() => renderCfoTelegram({ locale: "ja", view: "summary", snapshot: report }));
  frozen(report);
});

test("clones and isolates the input, and never emits Fleet or private fields", () => {
  const input = rawRead();
  const report = buildCfoDailyReport({ reportingDate: "2026-08-09", moneytreeRead: input });
  input.source.accounts[0].label = "changed";
  input.source.rawPayload = "secret";
  assert.equal(report.sources[0].label, "MUFG");
  const serialized = JSON.stringify(report);
  assert.doesNotMatch(serialized, /Fleet|fleet|accountNumber|123456|rawPayload|secret|token|credential|password/i);
});

test("rejects unsafe dates, sums that leave the safe integer range, stale or unavailable reads, and known liabilities", () => {
  const valid = read();
  for (const reportingDate of ["2026-8-09", "2026-02-30", "2026-08-09T00:00:00Z"]) invalid(() => buildCfoDailyReport({ reportingDate, moneytreeRead: valid }));
  invalid(() => buildCfoDailyReport({ reportingDate: "2026-08-09", moneytreeRead: read([Number.MAX_SAFE_INTEGER, 1]) }));
  const staleState = deriveMoneytreeState({ signal: "authorized", observedAt: OBSERVED_AT, aggregationAsOf: STALE_AS_OF, aggregationFreshnessCutoff: CUTOFF, liabilitiesExposed: false, liabilityCount: null });
  const staleSource = validateFinancialSourceResult(rawSource([100], { freshness: "stale" }));
  invalid(() => buildCfoDailyReport({ reportingDate: "2026-08-09", moneytreeRead: composeMoneytreeRead({ source: staleSource, state: staleState }) }));
  const unavailableSource = validateFinancialSourceResult({ ...rawSource([100]), consent: "unknown", freshness: "unavailable", accounts: [{ ...accounts([100])[0], balanceMinor: null, verificationStatus: "unavailable" }], partial: true, actionRequired: { kind: "provider_outage", sourceLabel: "Moneytree", actionRef: "action:moneytree_outage" } });
  const unavailableState = deriveMoneytreeState({ signal: "provider_outage", observedAt: OBSERVED_AT, aggregationAsOf: null, aggregationFreshnessCutoff: null, liabilitiesExposed: false, liabilityCount: null });
  invalid(() => buildCfoDailyReport({ reportingDate: "2026-08-09", moneytreeRead: composeMoneytreeRead({ source: unavailableSource, state: unavailableState }) }));
  const completeSource = validateFinancialSourceResult({ ...rawSource([100]), partial: false });
  const completeState = deriveMoneytreeState({ signal: "authorized", observedAt: OBSERVED_AT, aggregationAsOf: OBSERVED_AT, aggregationFreshnessCutoff: CUTOFF, liabilitiesExposed: true, liabilityCount: 0 });
  invalid(() => buildCfoDailyReport({ reportingDate: "2026-08-09", moneytreeRead: composeMoneytreeRead({ source: completeSource, state: completeState }) }));
});

test("revalidation rejects unknown keys, accessors, custom prototypes, proxies, cycles, and non-JPY evidence", () => {
  const cases = [];
  cases.push(() => buildCfoDailyReport({ reportingDate: "2026-08-09", moneytreeRead: { ...read(), rawPayload: "secret" } }));
  const transparentProxy = new Proxy(rawRead(), {});
  cases.push(() => buildCfoDailyReport({ reportingDate: "2026-08-09", moneytreeRead: transparentProxy }));
  const accessor = rawRead(); Object.defineProperty(accessor.source, "sourceId", { enumerable: true, get: () => "secret" });
  cases.push(() => buildCfoDailyReport({ reportingDate: "2026-08-09", moneytreeRead: accessor }));
  const prototype = rawRead(); Object.setPrototypeOf(prototype.source, { hostile: true });
  cases.push(() => buildCfoDailyReport({ reportingDate: "2026-08-09", moneytreeRead: prototype }));
  const proxy = new Proxy(rawRead(), { ownKeys: () => { throw new Error("secret raw payload"); } });
  cases.push(() => buildCfoDailyReport({ reportingDate: "2026-08-09", moneytreeRead: proxy }));
  const cycle = rawRead(); cycle.source.accounts[0].label = cycle.source.accounts[0];
  cases.push(() => buildCfoDailyReport({ reportingDate: "2026-08-09", moneytreeRead: cycle }));
  const nonJpy = rawRead(); nonJpy.source.accounts[0].currency = "USD";
  cases.push(() => buildCfoDailyReport({ reportingDate: "2026-08-09", moneytreeRead: nonJpy }));
  cases.forEach(invalid);
});

test("redacts thrown errors without reading a hostile message getter", () => {
  const thrown = new Proxy({}, { get: () => { throw new Error("message getter accessed"); } });
  const statePath = require.resolve("./cfo-moneytree-state.js");
  const builderPath = require.resolve("./cfo-daily-snapshot.js");
  const stateModule = require(statePath);
  const originalCompose = stateModule.composeMoneytreeRead;
  stateModule.composeMoneytreeRead = () => { throw thrown; };
  delete require.cache[builderPath];
  try {
    const { buildCfoDailyReport: injectedBuilder } = require(builderPath);
    assert.throws(
      () => injectedBuilder({ reportingDate: "2026-08-09", moneytreeRead: rawRead() }),
      new Error("cfo_daily_snapshot_invalid:invalid_input"),
    );
  } finally {
    stateModule.composeMoneytreeRead = originalCompose;
    delete require.cache[builderPath];
    require(builderPath);
  }
});
