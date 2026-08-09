"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { buildCfoDailyReportFromRecovery, validateCfoRecoverySnapshotBundle } = require("./cfo-recovery-snapshot.js");
const { validateFinancialSourceResult } = require("./cfo-financial-source.js");
const { deriveMoneytreeState, composeMoneytreeRead } = require("./cfo-moneytree-state.js");

const DATE = "2026-08-09";
const OBSERVED = "2026-08-09T08:00:00+09:00";
function read(amount = 1234) {
  const source = validateFinancialSourceResult({ schemaVersion: 1, sourceId: "moneytree_mufg", consent: "valid", freshness: "fresh", asOf: OBSERVED, accounts: [{ accountRef: "source_account:mt_test", label: "MUFG 普通預金", kind: "deposit", currency: "JPY", balanceMinor: amount, verificationStatus: "provider_reported" }], liabilities: [], evidenceRef: "evidence:mt_test", partial: true, actionRequired: null });
  const state = deriveMoneytreeState({ signal: "authorized", observedAt: OBSERVED, aggregationAsOf: null, aggregationFreshnessCutoff: null, liabilitiesExposed: false, liabilityCount: null });
  return composeMoneytreeRead({ source, state });
}
function recovery(overrides = {}) { return { reportingDate: DATE, observedAt: OBSERVED, status: "fresh", attempts: { reads: 1, repairs: 0, waits: [] }, failureKind: null, moneytreeRead: read(), repair: null, action: null, ...overrides }; }

test("builds the recovery snapshot bundle", () => {
  const result = buildCfoDailyReportFromRecovery({ revision: 3, recovery: recovery() });
  assert.deepEqual(result.report, { schemaVersion: 1, reportingDate: DATE, revision: 3, state: "partial", currency: "JPY", totals: { assetsMinor: 1234, liabilitiesMinor: null, netWorthMinor: null, changeMinor: null }, sources: [{ sourceId: "moneytree_mufg", label: "MUFG", status: "fresh", asOf: OBSERVED, amountMinor: 1234, verificationStatus: "provider_reported" }], excluded: [{ label: "負債", reason: "Moneytreeの接続範囲が不明" }], repair: null, action: null });
  assert.equal(Object.isFrozen(result.report), true);
  assert.equal(Object.isFrozen(result.sourceBundle.source), true);
});

test("recovered uses the fresh reread and exact repair proof", () => {
  const result = buildCfoDailyReportFromRecovery({ revision: 2, recovery: recovery({ status: "recovered", attempts: { reads: 2, repairs: 1, waits: [1000] }, moneytreeRead: read(9876), repair: { sourceLabel: "Moneytree", freshReread: true, reconciled: true } }) });
  assert.equal(result.report.state, "recovered");
  assert.equal(result.report.totals.assetsMinor, 9876);
  assert.deepEqual(result.report.repair, { sourceLabel: "Moneytree", freshReread: true, reconciled: true });
});

for (const [failureKind, consent] of [["unauthorized", "expired"], ["expired", "expired"], ["forbidden", "revoked"], ["revoked", "revoked"], ["provider_outage", "unknown"]]) {
  test(`action-required maps ${failureKind} to ${consent} without amounts`, () => {
    const kind = failureKind === "provider_outage" ? "provider_outage" : "reconsent";
    const result = buildCfoDailyReportFromRecovery({ revision: 1, recovery: recovery({ status: "action_required", attempts: { reads: 1, repairs: 0, waits: [] }, failureKind, moneytreeRead: null, action: { kind, sourceLabel: "Moneytree", nextRetryAt: "2026-08-09T08:30:00+09:00" } }) });
    assert.equal(result.sourceBundle.source.consent, consent);
    assert.deepEqual(result.sourceBundle.source.accounts, []);
    assert.equal(result.sourceBundle.source.asOf, OBSERVED);
    assert.equal(result.sourceBundle.source.evidenceRef, "evidence:moneytree_unavailable");
    assert.equal(result.report.totals.netWorthMinor, null);
    assert.equal(result.report.action.kind, kind);
    assert.equal("failureKind" in result.report, false);
  });
}

test("rejects stale injection, mismatched times, unproven recovery, revisions, and hostile shapes", () => {
  const cases = [
    () => buildCfoDailyReportFromRecovery({ revision: 0, recovery: recovery() }),
    () => buildCfoDailyReportFromRecovery({ revision: 1.5, recovery: recovery() }),
    () => buildCfoDailyReportFromRecovery({ revision: 1, recovery: recovery({ status: "recovered", attempts: { reads: 1, repairs: 0, waits: [] }, repair: { sourceLabel: "Moneytree", freshReread: true, reconciled: true } }) }),
    () => buildCfoDailyReportFromRecovery({ revision: 1, recovery: recovery({ status: "recovered", attempts: { reads: 2, repairs: 1, waits: [1000] }, failureKind: "timeout", repair: { sourceLabel: "Moneytree", freshReread: true, reconciled: true } }) }),
    () => buildCfoDailyReportFromRecovery({ revision: 1, recovery: { ...recovery(), extra: "secret" } }),
    () => validateCfoRecoverySnapshotBundle({ report: { ...buildCfoDailyReportFromRecovery({ revision: 1, recovery: recovery() }).report, totals: { assetsMinor: 999999, liabilitiesMinor: null, netWorthMinor: null, changeMinor: null } }, sourceBundle: read() }),
  ];
  for (const call of cases) assert.throws(call, /^Error: cfo_recovery_snapshot_invalid:/);
});
