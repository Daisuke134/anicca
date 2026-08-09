"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { buildCfoDailyReportFromRecovery, validateCfoRecoverySnapshotBundle } = require("./cfo-recovery-snapshot.js");
const { validateFinancialSourceResult } = require("./cfo-financial-source.js");
const { deriveMoneytreeState, composeMoneytreeRead } = require("./cfo-moneytree-state.js");
const { recoverMoneytreeRead } = require("./cfo-moneytree-recovery.js");

const DATE = "2026-08-09";
const OBSERVED = "2026-08-09T08:00:00+09:00";
function read(amount = 1234) {
  const source = validateFinancialSourceResult({ schemaVersion: 1, sourceId: "moneytree_mufg", consent: "valid", freshness: "fresh", asOf: OBSERVED, accounts: [{ accountRef: "source_account:mt_test", label: "MUFG 普通預金", kind: "deposit", currency: "JPY", balanceMinor: amount, verificationStatus: "provider_reported" }], liabilities: [], evidenceRef: "evidence:mt_test", partial: true, actionRequired: null });
  const state = deriveMoneytreeState({ signal: "authorized", observedAt: OBSERVED, aggregationAsOf: null, aggregationFreshnessCutoff: null, liabilitiesExposed: false, liabilityCount: null });
  return composeMoneytreeRead({ source, state });
}
function recovery(overrides = {}) { return { reportingDate: DATE, observedAt: OBSERVED, status: "fresh", attempts: { reads: 1, repairs: 0, waits: [] }, failureKind: null, moneytreeRead: read(), repair: null, action: null, ...overrides }; }
function actionRecovery(failureKind, kind, attempts = { reads: 1, repairs: 0, waits: [] }) { return recovery({ status: "action_required", failureKind, attempts, moneytreeRead: null, action: { kind, sourceLabel: "Moneytree", retryLabel: kind === "reconsent" ? "Moneytreeを再接続してください" : "30分後に自動再試行します", nextRetryAt: "2026-08-09T08:30:00+09:00" } }); }
function recoveryEffects(read) { return { read, repair: async () => true, wait: async () => undefined }; }

function assertInvalid(call) { assert.throws(call, /^Error: cfo_recovery_snapshot_invalid:/); }

test("builds the recovery snapshot bundle", () => {
  const result = buildCfoDailyReportFromRecovery({ revision: 3, recovery: recovery() });
  assert.deepEqual(result.report, { schemaVersion: 1, reportingDate: DATE, revision: 3, state: "partial", currency: "JPY", totals: { assetsMinor: 1234, liabilitiesMinor: null, netWorthMinor: null, changeMinor: null }, sources: [{ sourceId: "moneytree_mufg", label: "MUFG", status: "fresh", asOf: OBSERVED, amountMinor: 1234, verificationStatus: "provider_reported" }], excluded: [{ label: "負債", reason: "Moneytreeの接続範囲が不明" }], repair: null, action: null });
  assert.equal(Object.isFrozen(result.report), true);
  assert.equal(Object.isFrozen(result.sourceBundle.source), true);
});

test("preserves a valid zero account balance as integer zero", () => {
  const result = buildCfoDailyReportFromRecovery({ revision: 1, recovery: recovery({ moneytreeRead: read(0) }) });
  assert.equal(result.report.totals.assetsMinor, 0);
  assert.equal(result.report.sources[0].amountMinor, 0);
  assert.equal(result.sourceBundle.source.accounts[0].balanceMinor, 0);
});

test("recovered uses the fresh reread and exact repair proof", () => {
  const result = buildCfoDailyReportFromRecovery({ revision: 2, recovery: recovery({ status: "recovered", attempts: { reads: 2, repairs: 1, waits: [1000] }, moneytreeRead: read(9876), repair: { sourceLabel: "Moneytree", freshReread: true, reconciled: true } }) });
  assert.equal(result.report.state, "recovered");
  assert.equal(result.report.totals.assetsMinor, 9876);
  assert.deepEqual(result.report.repair, { sourceLabel: "Moneytree", freshReread: true, reconciled: true });
});

test("consumes actual Task 1 action-required outcomes without reshaping the action", async () => {
  const reconsent = await recoverMoneytreeRead({ reportingDate: DATE, observedAt: OBSERVED }, recoveryEffects(async () => ({ ok: false, kind: "forbidden" })));
  const outage = await recoverMoneytreeRead({ reportingDate: DATE, observedAt: OBSERVED }, recoveryEffects(async () => ({ ok: false, kind: "timeout" })));
  const mixed = await recoverMoneytreeRead({ reportingDate: DATE, observedAt: OBSERVED }, recoveryEffects(async ({ attempt }) => attempt === 1 ? { ok: false, kind: "timeout" } : { ok: false, kind: "forbidden" }));
  for (const [actual, kind, failureKind] of [[reconsent, "reconsent", "forbidden"], [outage, "provider_outage", "timeout"], [mixed, "reconsent", "forbidden"]]) {
    const bundle = buildCfoDailyReportFromRecovery({ revision: 1, recovery: actual });
    assert.equal(bundle.report.action.kind, kind);
    assert.deepEqual(bundle.report.action, actual.action);
    assert.equal(actual.failureKind, failureKind);
  }
});

test("requires null failureKind for fresh and recovered outcomes", () => {
  assert.throws(() => buildCfoDailyReportFromRecovery({ revision: 1, recovery: recovery({ failureKind: "timeout" }) }), /^Error: cfo_recovery_snapshot_invalid:/);
});

test("requires nextRetryAt to be exactly observedAt plus thirty minutes", async () => {
  const actual = await recoverMoneytreeRead({ reportingDate: "2099-12-31", observedAt: "2099-12-31T23:45:00+09:00" }, recoveryEffects(async () => ({ ok: false, kind: "forbidden" })));
  const wrong = structuredClone(actual); wrong.action.nextRetryAt = "2100-01-01T00:16:00+09:00";
  assertInvalid(() => buildCfoDailyReportFromRecovery({ revision: 1, recovery: wrong }));
  const wrongUtc = structuredClone(actual); wrongUtc.action.nextRetryAt = "2099-12-31T14:15:00Z";
  assertInvalid(() => buildCfoDailyReportFromRecovery({ revision: 1, recovery: wrongUtc }));
});

test("accepts only reachable attempts states and exact wait prefixes", async () => {
  const fresh = recovery();
  assert.deepEqual(fresh.attempts, { reads: 1, repairs: 0, waits: [] });
  buildCfoDailyReportFromRecovery({ revision: 1, recovery: fresh });
  const recovered2 = recovery({ status: "recovered", attempts: { reads: 2, repairs: 1, waits: [1000] }, repair: { sourceLabel: "Moneytree", freshReread: true, reconciled: true } });
  const recovered3 = recovery({ status: "recovered", attempts: { reads: 3, repairs: 2, waits: [1000, 5000] }, repair: { sourceLabel: "Moneytree", freshReread: true, reconciled: true } });
  buildCfoDailyReportFromRecovery({ revision: 2, recovery: recovered2 });
  buildCfoDailyReportFromRecovery({ revision: 3, recovery: recovered3 });
  const directOutage = await recoverMoneytreeRead({ reportingDate: DATE, observedAt: OBSERVED }, recoveryEffects(async () => ({ ok: true, moneytreeRead: { schemaVersion: 1 } })));
  assert.equal(directOutage.failureKind, "provider_outage");
  assert.deepEqual(directOutage.attempts, { reads: 1, repairs: 0, waits: [] });
  buildCfoDailyReportFromRecovery({ revision: 1, recovery: directOutage });
  const transientOutage = await recoverMoneytreeRead({ reportingDate: DATE, observedAt: OBSERVED }, recoveryEffects(async () => ({ ok: false, kind: "timeout" })));
  assert.deepEqual(transientOutage.attempts, { reads: 3, repairs: 2, waits: [1000, 5000] });
  buildCfoDailyReportFromRecovery({ revision: 1, recovery: transientOutage });
  for (const overrides of [
    { attempts: { reads: 1, repairs: 1, waits: [] } },
    { attempts: { reads: 1, repairs: 0, waits: [1000] } },
    { attempts: { reads: 2, repairs: 0, waits: [1000] } },
    { attempts: { reads: 2, repairs: 1, waits: [5000] } },
    { attempts: { reads: 3, repairs: 2, waits: [1000, 5000, 9000] } },
    { attempts: { reads: 4, repairs: 3, waits: [1000, 5000, 9000] } },
  ]) assertInvalid(() => buildCfoDailyReportFromRecovery({ revision: 1, recovery: recovery(overrides) }));
  const recoveredBase = { status: "recovered", moneytreeRead: read(), repair: { sourceLabel: "Moneytree", freshReread: true, reconciled: true } };
  for (const attempts of [{ reads: 1, repairs: 0, waits: [] }, { reads: 4, repairs: 3, waits: [1000, 5000, 9000] }, { reads: 2, repairs: 0, waits: [1000] }]) assertInvalid(() => buildCfoDailyReportFromRecovery({ revision: 1, recovery: recovery({ ...recoveredBase, attempts }) }));
  const actionBase = await recoverMoneytreeRead({ reportingDate: DATE, observedAt: OBSERVED }, recoveryEffects(async () => ({ ok: false, kind: "timeout" })));
  for (const attempts of [{ reads: 3, repairs: 1, waits: [1000, 5000] }, { reads: 2, repairs: 1, waits: [5000] }]) assertInvalid(() => buildCfoDailyReportFromRecovery({ revision: 1, recovery: { ...actionBase, attempts } }));
});

test("fresh recovery cannot carry retry attempts", () => {
  for (const attempts of [{ reads: 2, repairs: 1, waits: [1000] }, { reads: 3, repairs: 2, waits: [1000, 5000] }]) {
    assertInvalid(() => buildCfoDailyReportFromRecovery({ revision: 1, recovery: recovery({ attempts }) }));
  }
});

test("direct provider outage cannot carry retry attempts", () => {
  assertInvalid(() => buildCfoDailyReportFromRecovery({ revision: 1, recovery: actionRecovery("provider_outage", "provider_outage", { reads: 2, repairs: 1, waits: [1000] }) }));
});

test("transient provider outage must include a reread attempt", () => {
  assertInvalid(() => buildCfoDailyReportFromRecovery({ revision: 1, recovery: actionRecovery("timeout", "provider_outage", { reads: 1, repairs: 0, waits: [] }) }));
});

test("public action retry time is bound to source observation", () => {
  const bundle = buildCfoDailyReportFromRecovery({ revision: 1, recovery: actionRecovery("provider_outage", "provider_outage") });
  const report = structuredClone(bundle.report);
  report.action.nextRetryAt = "2026-08-09T09:00:00+09:00";
  assertInvalid(() => validateCfoRecoverySnapshotBundle({ report, sourceBundle: bundle.sourceBundle }));
});

test("waits rejects hostile and non-dense array boundaries without leaking errors", () => {
  const hostileError = new Proxy({}, { get() { throw new Error("SECRET_MESSAGE_GETTER_LEAK"); } });
  const hostile = new Proxy([1000], { get() { throw hostileError; } });
  const symbolKey = [1000]; symbolKey[Symbol("extra")] = true;
  const hiddenKey = [1000]; Object.defineProperty(hiddenKey, "extra", { value: true });
  const accessorIndex = [1000]; Object.defineProperty(accessorIndex, "0", { enumerable: true, get: () => 1000 });
  const sparse = new Array(1);
  const customPrototype = [1000]; Object.setPrototypeOf(customPrototype, { custom: true });
  for (const waits of [hostile, symbolKey, hiddenKey, accessorIndex, sparse, customPrototype]) {
    assert.throws(() => buildCfoDailyReportFromRecovery({ revision: 1, recovery: recovery({ status: "recovered", attempts: { reads: 2, repairs: 1, waits }, repair: { sourceLabel: "Moneytree", freshReread: true, reconciled: true } }) }), (error) => {
      assert.match(error.message, /^cfo_recovery_snapshot_invalid:[a-z0-9_]+$/);
      assert.doesNotMatch(error.message, /SECRET/);
      return true;
    });
  }
});

test("report sources and exclusions reject Proxy and sparse arrays", () => {
  const bundle = buildCfoDailyReportFromRecovery({ revision: 1, recovery: recovery() });
  const proxySources = structuredClone(bundle.report); proxySources.sources = new Proxy(proxySources.sources, { get() { throw new Error("SECRET_SOURCES"); } });
  const proxyExcluded = structuredClone(bundle.report); proxyExcluded.excluded = new Proxy(proxyExcluded.excluded, { get() { throw new Error("SECRET_EXCLUDED"); } });
  const sparseSources = structuredClone(bundle.report); sparseSources.sources = new Array(1);
  const sparseExcluded = structuredClone(bundle.report); sparseExcluded.excluded = new Array(1);
  for (const report of [proxySources, proxyExcluded, sparseSources, sparseExcluded]) assertInvalid(() => validateCfoRecoverySnapshotBundle({ report, sourceBundle: bundle.sourceBundle }));
});

test("public validator never replays a caller-mutated internal Error", () => {
  const bundle = buildCfoDailyReportFromRecovery({ revision: 1, recovery: recovery() });
  let capturedError;
  try {
    validateCfoRecoverySnapshotBundle({ report: bundle.report, sourceBundle: { source: null, state: null } });
  } catch (error) {
    capturedError = error;
  }
  assert.ok(capturedError instanceof Error);
  capturedError.message = "SECRET_REPLAYED_INTERNAL_ERROR";
  const hostileSourceBundle = new Proxy({}, { get(_target, key) { if (key === "source") throw capturedError; return undefined; } });
  let replayedError;
  try {
    validateCfoRecoverySnapshotBundle({ report: bundle.report, sourceBundle: hostileSourceBundle });
  } catch (error) {
    replayedError = error;
  }
  assert.ok(replayedError instanceof Error);
  assert.notStrictEqual(replayedError, capturedError);
  assert.match(replayedError.message, /^cfo_recovery_snapshot_invalid:[a-z0-9_]+$/);
  assert.doesNotMatch(replayedError.message, /SECRET/);
});

test("binds fresh and recovered reads to recovery.observedAt exactly", () => {
  const stale = read();
  const freshWithStaleRead = recovery({ moneytreeRead: stale, observedAt: "2026-08-09T09:00:00+09:00" });
  assert.throws(() => buildCfoDailyReportFromRecovery({ revision: 1, recovery: freshWithStaleRead }), /^Error: cfo_recovery_snapshot_invalid:/);
  const recoveredWithStaleRead = recovery({ status: "recovered", attempts: { reads: 2, repairs: 1, waits: [1000] }, moneytreeRead: stale, repair: { sourceLabel: "Moneytree", freshReread: true, reconciled: true }, observedAt: "2026-08-09T09:00:00+09:00" });
  assert.throws(() => buildCfoDailyReportFromRecovery({ revision: 2, recovery: recoveredWithStaleRead }), /^Error: cfo_recovery_snapshot_invalid:/);
});

for (const [failureKind, consent] of [["unauthorized", "expired"], ["expired", "expired"], ["forbidden", "revoked"], ["revoked", "revoked"], ["provider_outage", "unknown"]]) {
  test(`action-required maps ${failureKind} to ${consent} without amounts`, () => {
    const kind = failureKind === "provider_outage" ? "provider_outage" : "reconsent";
    const result = buildCfoDailyReportFromRecovery({ revision: 1, recovery: actionRecovery(failureKind, kind) });
    assert.equal(result.sourceBundle.source.consent, consent);
    assert.deepEqual(result.sourceBundle.source.accounts, []);
    assert.equal(result.sourceBundle.source.asOf, OBSERVED);
    assert.equal(result.sourceBundle.source.evidenceRef, "evidence:moneytree_unavailable");
    assert.equal(result.report.totals.netWorthMinor, null);
    assert.equal(result.report.action.kind, kind);
    assert.equal("failureKind" in result.report, false);
  });
}

test("rejects both directions of failure/action mapping mismatch", () => {
  for (const [failureKind, wrongKind] of [["unauthorized", "provider_outage"], ["expired", "provider_outage"], ["forbidden", "provider_outage"], ["revoked", "provider_outage"], ["timeout", "reconsent"], ["network", "reconsent"], ["rate_limited", "reconsent"], ["provider_5xx", "reconsent"], ["provider_outage", "reconsent"]]) {
    assert.throws(() => buildCfoDailyReportFromRecovery({ revision: 1, recovery: actionRecovery(failureKind, wrongKind) }), /^Error: cfo_recovery_snapshot_invalid:/);
  }
});

test("revalidates state-specific report and source invariants", () => {
  const partial = buildCfoDailyReportFromRecovery({ revision: 1, recovery: recovery() });
  for (const mutate of [
    (report) => { report.repair = { sourceLabel: "Moneytree", freshReread: true, reconciled: true }; },
    (report) => { report.action = { kind: "reconsent", sourceLabel: "Moneytree", retryLabel: "再接続", nextRetryAt: "2026-08-09T08:30:00+09:00" }; },
    (report) => { report.sources[0].status = "unavailable"; },
  ]) {
    const report = structuredClone(partial.report); mutate(report);
    assert.throws(() => validateCfoRecoverySnapshotBundle({ report, sourceBundle: partial.sourceBundle }), /^Error: cfo_recovery_snapshot_invalid:/);
  }
  const recovered = buildCfoDailyReportFromRecovery({ revision: 2, recovery: recovery({ status: "recovered", attempts: { reads: 2, repairs: 1, waits: [1000] }, repair: { sourceLabel: "Moneytree", freshReread: true, reconciled: true } }) });
  for (const mutate of [
    (report) => { report.repair.extra = "hostile"; },
    (report) => { report.action = { kind: "provider_outage", sourceLabel: "Moneytree", retryLabel: "retry", nextRetryAt: "2026-08-09T08:30:00+09:00" }; },
  ]) {
    const report = structuredClone(recovered.report); mutate(report);
    assert.throws(() => validateCfoRecoverySnapshotBundle({ report, sourceBundle: recovered.sourceBundle }), /^Error: cfo_recovery_snapshot_invalid:/);
  }
});

test("revalidates action-required evidence, freshness, liabilities, and state consistency", () => {
  const bundle = buildCfoDailyReportFromRecovery({ revision: 1, recovery: actionRecovery("timeout", "provider_outage", { reads: 2, repairs: 1, waits: [1000] }) });
  const cases = [
    () => validateCfoRecoverySnapshotBundle({ report: bundle.report, sourceBundle: { source: { ...bundle.sourceBundle.source, evidenceRef: "evidence:wrong" }, state: bundle.sourceBundle.state } }),
    () => validateCfoRecoverySnapshotBundle({ report: bundle.report, sourceBundle: { source: { ...bundle.sourceBundle.source, freshness: "stale" }, state: bundle.sourceBundle.state } }),
    () => validateCfoRecoverySnapshotBundle({ report: bundle.report, sourceBundle: { source: { ...bundle.sourceBundle.source, liabilities: [{ accountRef: "source_account:liability", label: "Loan", currency: "JPY", balanceMinor: null, verificationStatus: "unavailable" }] }, state: bundle.sourceBundle.state } }),
    () => validateCfoRecoverySnapshotBundle({ report: { ...bundle.report, action: { ...bundle.report.action, kind: "reconsent" } }, sourceBundle: bundle.sourceBundle }),
    () => validateCfoRecoverySnapshotBundle({ report: { ...bundle.report, totals: { assetsMinor: 1, liabilitiesMinor: null, netWorthMinor: null, changeMinor: null } }, sourceBundle: bundle.sourceBundle }),
  ];
  for (const call of cases) assert.throws(call, /^Error: cfo_recovery_snapshot_invalid:/);
});

test("requires canonical exclusions and retry labels", async () => {
  const actual = await recoverMoneytreeRead({ reportingDate: DATE, observedAt: OBSERVED }, recoveryEffects(async () => ({ ok: false, kind: "forbidden" })));
  const bundle = buildCfoDailyReportFromRecovery({ revision: 1, recovery: actual });
  for (const mutate of [
    (report) => { report.excluded = []; },
    (report) => { report.excluded = [{ label: "anything", reason: "arbitrary" }]; },
    (report) => { report.action.retryLabel = "wrong"; },
  ]) {
    const report = structuredClone(bundle.report); mutate(report);
    assert.throws(() => validateCfoRecoverySnapshotBundle({ report, sourceBundle: bundle.sourceBundle }), /^Error: cfo_recovery_snapshot_invalid:/);
  }
  const outage = await recoverMoneytreeRead({ reportingDate: DATE, observedAt: OBSERVED }, recoveryEffects(async () => ({ ok: false, kind: "timeout" })));
  const outageBundle = buildCfoDailyReportFromRecovery({ revision: 1, recovery: outage });
  const wrongRetry = structuredClone(outageBundle.report); wrongRetry.action.retryLabel = "Moneytreeを再接続してください";
  assert.throws(() => validateCfoRecoverySnapshotBundle({ report: wrongRetry, sourceBundle: outageBundle.sourceBundle }), /^Error: cfo_recovery_snapshot_invalid:/);
});

test("rebuilds canonical non-action reports and rejects unsupported aggregation state", () => {
  const bundle = buildCfoDailyReportFromRecovery({ revision: 1, recovery: recovery() });
  const altered = structuredClone(bundle.report); altered.excluded = [{ label: "fake", reason: "fake" }];
  assert.throws(() => validateCfoRecoverySnapshotBundle({ report: altered, sourceBundle: bundle.sourceBundle }), /^Error: cfo_recovery_snapshot_invalid:/);
  const state = { ...bundle.sourceBundle.state, aggregationStatus: "fresh", aggregationAsOf: OBSERVED };
  assert.throws(() => validateCfoRecoverySnapshotBundle({ report: bundle.report, sourceBundle: { source: bundle.sourceBundle.source, state } }), /^Error: cfo_recovery_snapshot_invalid:/);
});

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
