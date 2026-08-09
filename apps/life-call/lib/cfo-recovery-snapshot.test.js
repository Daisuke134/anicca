"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { buildCfoDailyReportFromRecovery, validateCfoRecoverySnapshotBundle } = require("./cfo-recovery-snapshot.js");
const { validateFinancialSourceResult } = require("./cfo-financial-source.js");
const { deriveMoneytreeState, composeMoneytreeRead } = require("./cfo-moneytree-state.js");

const DATE = "2026-08-09";
const OBSERVED = "2026-08-09T08:00:00+09:00";
const RETRY = "2026-08-09T08:30:00+09:00";
const RETRY_LABELS = { reconsent: "接続後に自動再確認", provider_outage: "30分後に自動再確認" };

function read(amount = 1234, asOf = OBSERVED) {
  const source = validateFinancialSourceResult({
    schemaVersion: 1, sourceId: "moneytree_mufg", consent: "valid", freshness: "fresh", asOf,
    accounts: [{ accountRef: "source_account:mt_test", label: "MUFG 普通預金", kind: "deposit", currency: "JPY", balanceMinor: amount, verificationStatus: "provider_reported" }],
    liabilities: [], evidenceRef: "evidence:mt_test", partial: true, actionRequired: null,
  });
  const state = deriveMoneytreeState({ signal: "authorized", observedAt: asOf, aggregationAsOf: null, aggregationFreshnessCutoff: null, liabilitiesExposed: false, liabilityCount: null });
  return composeMoneytreeRead({ source, state });
}

function fresh(overrides = {}) {
  return { reportingDate: DATE, observedAt: OBSERVED, status: "fresh", attempts: 1, failureKind: null, moneytreeRead: read(), repair: null, action: null, ...overrides };
}
function actionRecovery(failureKind, kind, overrides = {}) {
  return fresh({
    status: "action_required", attempts: failureKind === "timeout" ? 3 : 1, failureKind, moneytreeRead: null, repair: null,
    action: { kind, sourceLabel: "Moneytree", retryLabel: RETRY_LABELS[kind], nextRetryAt: RETRY }, ...overrides,
  });
}
function invalid(call) { assert.throws(call, /^Error: cfo_recovery_snapshot_invalid:[a-z0-9_]+$/); }

test("fresh bundle is exact, native-JPY, revisioned, and deeply frozen", () => {
  const bundle = buildCfoDailyReportFromRecovery({ revision: 3, recovery: fresh() });
  assert.deepEqual(bundle.report.totals, { assetsMinor: 1234, liabilitiesMinor: null, netWorthMinor: null, changeMinor: null });
  assert.equal(bundle.report.reportingDate, DATE); assert.equal(bundle.report.revision, 3); assert.equal(bundle.report.state, "partial");
  assert.deepEqual(bundle.sourceBundle.source.accounts[0].balanceMinor, 1234);
  assert.deepEqual(Object.keys(bundle), ["report", "sourceBundle"]);
  assert.equal(Object.isFrozen(bundle), true); assert.equal(Object.isFrozen(bundle.report), true);
  assert.equal(Object.isFrozen(bundle.sourceBundle.source.accounts), true);
});

test("recovered bundle uses only the fresh reread and exact repair proof", () => {
  const bundle = buildCfoDailyReportFromRecovery({ revision: 2, recovery: fresh({
    status: "recovered", attempts: 2, moneytreeRead: read(9876),
    repair: { sourceLabel: "Moneytree", freshReread: true, reconciled: true },
  }) });
  assert.equal(bundle.report.state, "recovered"); assert.equal(bundle.report.totals.assetsMinor, 9876);
  assert.deepEqual(bundle.report.repair, { sourceLabel: "Moneytree", freshReread: true, reconciled: true });
  assert.equal(bundle.report.action, null);
});

for (const [failureKind, kind, consent] of [
  ["unauthorized", "reconsent", "expired"], ["expired", "reconsent", "expired"],
  ["forbidden", "reconsent", "revoked"], ["revoked", "reconsent", "revoked"], ["provider_outage", "provider_outage", "unknown"],
]) test(`action-required maps ${failureKind} to ${consent} without an amount`, () => {
  const bundle = buildCfoDailyReportFromRecovery({ revision: 1, recovery: actionRecovery(failureKind, kind) });
  assert.equal(bundle.sourceBundle.source.consent, consent); assert.deepEqual(bundle.sourceBundle.source.accounts, []);
  assert.equal(bundle.sourceBundle.source.asOf, OBSERVED); assert.equal(bundle.sourceBundle.source.evidenceRef, "evidence:moneytree_unavailable");
  assert.deepEqual(bundle.report.totals, { assetsMinor: null, liabilitiesMinor: null, netWorthMinor: null, changeMinor: null });
  assert.deepEqual(bundle.report.action, actionRecovery(failureKind, kind).action);
  assert.equal("failureKind" in bundle.report, false);
});

test("rejects stale amount injection, time mismatch, unproven recovery, and bad revisions", () => {
  invalid(() => buildCfoDailyReportFromRecovery({ revision: 0, recovery: fresh() }));
  invalid(() => buildCfoDailyReportFromRecovery({ revision: 1.5, recovery: fresh() }));
  invalid(() => buildCfoDailyReportFromRecovery({ revision: 1, recovery: fresh({ observedAt: "2026-08-09T09:00:00+09:00" }) }));
  invalid(() => buildCfoDailyReportFromRecovery({ revision: 1, recovery: fresh({ status: "recovered", attempts: 1, repair: { sourceLabel: "Moneytree", freshReread: true, reconciled: true } }) }));
  invalid(() => buildCfoDailyReportFromRecovery({ revision: 1, recovery: fresh({ status: "recovered", attempts: 2, failureKind: "timeout", repair: { sourceLabel: "Moneytree", freshReread: true, reconciled: true } }) }));
  invalid(() => buildCfoDailyReportFromRecovery({ revision: 1, recovery: { ...fresh(), secret: "old balance" } }));
  const bundle = buildCfoDailyReportFromRecovery({ revision: 1, recovery: fresh() });
  const tampered = structuredClone(bundle.report); tampered.totals.assetsMinor = 999999;
  invalid(() => validateCfoRecoverySnapshotBundle({ report: tampered, sourceBundle: bundle.sourceBundle }));
});

test("action-required validator rejects net worth, stale source, and mismatched action", () => {
  const bundle = buildCfoDailyReportFromRecovery({ revision: 1, recovery: actionRecovery("timeout", "provider_outage") });
  const netWorth = structuredClone(bundle.report); netWorth.totals.netWorthMinor = 1;
  const stale = structuredClone(bundle.sourceBundle.source); stale.evidenceRef = "evidence:mt_test";
  const wrongAction = structuredClone(bundle.report); wrongAction.action.kind = "reconsent";
  invalid(() => validateCfoRecoverySnapshotBundle({ report: netWorth, sourceBundle: bundle.sourceBundle }));
  invalid(() => validateCfoRecoverySnapshotBundle({ report: bundle.report, sourceBundle: { source: stale, state: bundle.sourceBundle.state } }));
  invalid(() => validateCfoRecoverySnapshotBundle({ report: wrongAction, sourceBundle: bundle.sourceBundle }));
});

test("shared validator binds current Task1 labels, Gregorian date, and schema", () => {
  const action = buildCfoDailyReportFromRecovery({ revision: 1, recovery: actionRecovery("forbidden", "reconsent") });
  const cases = [
    ["date", () => { const report = structuredClone(action.report); report.reportingDate = "2026-02-30"; return { report, sourceBundle: action.sourceBundle }; }],
    ["sourceLabel", () => { const report = structuredClone(action.report); report.action.sourceLabel = "Other"; return { report, sourceBundle: action.sourceBundle }; }],
    ["retryLabel", () => { const report = structuredClone(action.report); report.action.retryLabel = "retry"; return { report, sourceBundle: action.sourceBundle }; }],
    ["schema", () => { const sourceBundle = structuredClone(action.sourceBundle); sourceBundle.schemaVersion = 2; return { report: action.report, sourceBundle }; }],
  ];
  for (const [, make] of cases) invalid(() => validateCfoRecoverySnapshotBundle(make()));
  const terminal = buildCfoDailyReportFromRecovery({ revision: 2, recovery: actionRecovery("forbidden", "reconsent", { attempts: 2 }) });
  assert.equal(terminal.report.action.kind, "reconsent"); assert.equal(terminal.sourceBundle.source.consent, "revoked");
});

test("hostile envelopes and caller mutation fail closed", () => {
  const bundle = buildCfoDailyReportFromRecovery({ revision: 1, recovery: fresh() });
  const proxy = new Proxy(bundle.report, {});
  invalid(() => validateCfoRecoverySnapshotBundle({ report: proxy, sourceBundle: bundle.sourceBundle }));
  const unknown = structuredClone(bundle.report); unknown.totals.extra = "secret";
  invalid(() => validateCfoRecoverySnapshotBundle({ report: unknown, sourceBundle: bundle.sourceBundle }));
  assert.throws(() => { bundle.report.totals.assetsMinor = 1; }, TypeError);
  assert.equal(bundle.report.totals.assetsMinor, 1234);
});
