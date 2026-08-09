"use strict";

const assert = require("node:assert/strict");
const { test } = require("node:test");
const { validateFinancialSourceResult } = require("./cfo-financial-source.js");
const { deriveMoneytreeState, composeMoneytreeRead } = require("./cfo-moneytree-state.js");
const { buildCfoDailyReportFromRecovery } = require("./cfo-recovery-snapshot.js");
const { appendCfoDailySnapshotRevision } = require("./cfo-daily-snapshot-revision-store.js");

const DATE = "2026-08-09";
const RUN = "2a000000-0000-4000-8000-000000000001";
const UID = "tenant-a";
const URL = "https://project.supabase.co";
const KEY = "service-role-secret";
const AS_OF = "2026-08-09T06:00:00+09:00";
const RECEIPT = {
  public_ref: "30000000-0000-4000-8000-000000000001", reporting_date: DATE, run_id: RUN,
  revision: 2, supersedes_revision: 1, created_at: "2026-08-09T06:00:01.000Z",
};
const SENSITIVE = /UID_SENTINEL|AMOUNT_SENTINEL|ACCOUNT_REF_SENTINEL|CREDENTIAL_SENTINEL|RAW_BODY_SENTINEL|tenant-a|220|service-role-secret|secret|raw|account_ref|amount/i;

function moneytreeRead(balanceMinor = 0) {
  const source = validateFinancialSourceResult({
    schemaVersion: 1, sourceId: "moneytree_mufg", consent: "valid", freshness: "fresh", asOf: AS_OF,
    accounts: [{ accountRef: "source_account:synthetic", label: "MUFG 口座", kind: "deposit", currency: "JPY", balanceMinor, verificationStatus: "provider_reported" }],
    liabilities: [], evidenceRef: "evidence:synthetic_moneytree", partial: true, actionRequired: null,
  });
  const state = deriveMoneytreeState({ signal: "interactive_success", observedAt: AS_OF, aggregationAsOf: null, aggregationFreshnessCutoff: null, liabilitiesExposed: false, liabilityCount: null });
  return composeMoneytreeRead({ source, state });
}
function bundle(revision = 2, balanceMinor = 0) {
  return buildCfoDailyReportFromRecovery({ revision, recovery: {
    reportingDate: DATE, observedAt: AS_OF, status: "fresh",
    attempts: { reads: 1, repairs: 0, waits: [] }, failureKind: null,
    moneytreeRead: moneytreeRead(balanceMinor), repair: null, action: null,
  }});
}
function input(overrides = {}) {
  const value = bundle();
  return { uid: UID, reportingDate: DATE, runId: RUN, revision: 2, supersedesRevision: 1,
    report: value.report, sourceBundle: value.sourceBundle, ...overrides };
}
function response(body = RECEIPT, status = 200) { return { ok: status >= 200 && status < 300, status, json: async () => body }; }
async function rejected(call, pattern = /^cfo_snapshot_revision_store_failed:[a-z0-9_]+$/, counter = null) {
  await assert.rejects(call, error => { assert.match(error.message, pattern); assert.doesNotMatch(error.message, SENSITIVE); return true; });
  if (counter) assert.equal(counter.value, 0);
}

test("appends one exact correction RPC and returns a closed frozen receipt", async () => {
  const calls = []; const value = input();
  const providerReceipt = { ...RECEIPT };
  const fetchImpl = async (url, init) => { calls.push({ url, init }); return response(providerReceipt); };
  const receipt = await appendCfoDailySnapshotRevision(value, { supaUrl: URL, supaKey: KEY, fetchImpl });
  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, `${URL}/rest/v1/rpc/lm_append_cfo_daily_snapshot_revision`);
  assert.deepEqual(calls[0].init.headers, { apikey: KEY, Authorization: `Bearer ${KEY}`, "Content-Type": "application/json" });
  assert.equal(calls[0].init.method, "POST");
  assert.deepEqual(JSON.parse(calls[0].init.body), {
    p_uid: UID, p_reporting_date: DATE, p_run_id: RUN, p_revision: 2, p_supersedes_revision: 1,
    p_report_payload: value.report, p_source_bundle: value.sourceBundle,
  });
  assert.deepEqual(receipt, RECEIPT);
  assert.deepEqual(Object.keys(receipt).sort(), ["created_at", "public_ref", "reporting_date", "revision", "run_id", "supersedes_revision"]);
  assert.equal(Object.isFrozen(receipt), true);
  providerReceipt.revision = 99; providerReceipt.public_ref = "40000000-0000-4000-8000-000000000001";
  assert.deepEqual(receipt, RECEIPT);
});

test("validates exact identity, revision predecessor, and bundle before network", async () => {
  const calls = []; const fetchImpl = async () => { calls.push(true); return response(); };
  const badInputs = [null, { ...input(), extra: "secret" }, { ...input(), revision: 1 }, { ...input(), revision: 2.5 },
    { ...input(), revision: Number.MAX_SAFE_INTEGER + 1 }, { ...input(), supersedesRevision: 0 }, { ...input(), supersedesRevision: 2 },
    { ...input(), uid: "" }, { ...input(), uid: " bad" }, { ...input(), uid: 42 }, { ...input(), reportingDate: "2026-02-29" },
    { ...input(), runId: "00000000-0000-0000-0000-000000000000" }, { ...input(), report: { ...input().report, revision: 1 } },
  ];
  for (const bad of badInputs) await rejected(() => appendCfoDailySnapshotRevision(bad, { supaUrl: URL, supaKey: KEY, fetchImpl }));
  const custom = Object.assign(Object.create({ hostile: true }), input());
  const accessor = input(); Object.defineProperty(accessor, "uid", { enumerable: true, get: () => "secret" });
  const symbol = input(); symbol[Symbol("extra")] = true;
  for (const bad of [custom, new Proxy(input(), {}), accessor, symbol]) await rejected(() => appendCfoDailySnapshotRevision(bad, { supaUrl: URL, supaKey: KEY, fetchImpl }));
  const hidden = input(); Object.defineProperty(hidden, "hidden", { value: true });
  await rejected(() => appendCfoDailySnapshotRevision(hidden, { supaUrl: URL, supaKey: KEY, fetchImpl }));
  assert.equal(calls.length, 0);
});

test("rejects malformed options before fetch, including hidden, accessor, Proxy, and custom-prototype shapes", async () => {
  const calls = { value: 0 }; const fetchImpl = async () => { calls.value += 1; return response(); };
  const options = () => ({ supaUrl: URL, supaKey: KEY, fetchImpl });
  const extra = options(); extra.log = () => {};
  const symbol = options(); symbol[Symbol("extra")] = true;
  const hidden = options(); Object.defineProperty(hidden, "hidden", { value: true });
  let getterCalls = 0; const accessor = options(); Object.defineProperty(accessor, "log", { enumerable: true, get: () => { getterCalls += 1; return () => {}; } });
  const custom = Object.assign(Object.create({ hostile: true }), options());
  const invalidFetch = options(); invalidFetch.fetchImpl = 42;
  for (const opts of [extra, symbol, hidden, accessor, new Proxy(options(), {}), custom, invalidFetch]) {
    await rejected(() => appendCfoDailySnapshotRevision(input(), opts), /^cfo_snapshot_revision_store_failed:(?:invalid_options|invalid_input|invalid_fetch)$/);
  }
  assert.equal(getterCalls, 0);
  assert.equal(calls.value, 0);
});

test("rejects canonical Task 2 bundle tampering before fetch while identity remains valid", async () => {
  const calls = { value: 0 }; const fetchImpl = async () => { calls.value += 1; return response(); };
  const tamper = [];
  const excluded = structuredClone(input()); excluded.report.excluded[0].reason = "tampered"; tamper.push(excluded);
  const evidence = structuredClone(input()); evidence.sourceBundle.source.consent = "expired"; tamper.push(evidence);
  const state = structuredClone(input()); state.sourceBundle.state.consentStatus = "expired"; tamper.push(state);
  const actionBundle = buildCfoDailyReportFromRecovery({ revision: 2, recovery: {
    reportingDate: DATE, observedAt: AS_OF, status: "action_required", attempts: { reads: 2, repairs: 1, waits: [1000] },
    failureKind: "timeout", moneytreeRead: null, repair: null,
    action: { kind: "provider_outage", sourceLabel: "Moneytree", retryLabel: "30分後に自動再試行します", nextRetryAt: "2026-08-09T06:30:00+09:00" },
  }});
  const action = { ...input(), ...structuredClone(actionBundle) }; action.report.action.retryLabel = "tampered"; tamper.push(action);
  for (const [index, value] of tamper.entries()) {
    await assert.rejects(() => appendCfoDailySnapshotRevision(value, { supaUrl: URL, supaKey: KEY, fetchImpl }), error => {
      assert.match(error.message, /^cfo_snapshot_revision_store_failed:[a-z0-9_]+$/);
      assert.doesNotMatch(error.message, SENSITIVE);
      return true;
    }, `tamper case ${index}`);
  }
  assert.equal(calls.value, 0);
});

test("rejects hostile provider failures without retrying, logging, or reading non-2xx bodies", async () => {
  const sinks = [console.log, console.error, console.warn]; let sinkCalls = 0;
  console.log = console.error = console.warn = () => { sinkCalls += 1; };
  try {
    for (const thrown of ["RAW_BODY_SENTINEL", 7, null, { message: "CREDENTIAL_SENTINEL" }, new Proxy({}, { get: () => { throw new Error("UID_SENTINEL"); } })]) {
      let calls = 0;
      await rejected(() => appendCfoDailySnapshotRevision(input(), { supaUrl: URL, supaKey: KEY, fetchImpl: async () => { calls += 1; throw thrown; } }), /^cfo_snapshot_revision_store_failed:network$/);
      assert.equal(calls, 1);
    }
    let jsonCalls = 0; let calls = 0;
    await rejected(() => appendCfoDailySnapshotRevision(input(), { supaUrl: URL, supaKey: KEY, fetchImpl: async () => { calls += 1; return { ok: false, status: 409, json: () => { jsonCalls += 1; throw new Error("RAW_BODY_SENTINEL"); } }; } }), /^cfo_snapshot_revision_store_failed:provider_409$/);
    assert.equal(calls, 1); assert.equal(jsonCalls, 0);
    await rejected(() => appendCfoDailySnapshotRevision(input(), { supaUrl: URL, supaKey: KEY, fetchImpl: async () => response(new Proxy({}, { ownKeys: () => { throw new Error("RAW_BODY_SENTINEL"); } })) }), /^cfo_snapshot_revision_store_failed:invalid_receipt$/);
  } finally { [console.log, console.error, console.warn] = sinks; }
  assert.equal(sinkCalls, 0);
});

test("requires exact receipt echo and strict receipt fields", async () => {
  for (const mutate of [value => { value.reporting_date = "2026-08-08"; }, value => { value.run_id = RUN.toUpperCase(); }, value => { value.run_id = "2a000000-0000-4000-8000-000000000002"; }, value => { value.revision = 3; }, value => { value.supersedes_revision = 2; }, value => { value.public_ref = "00000000-0000-0000-0000-000000000000"; }, value => { value.extra = "raw"; }, value => { value.created_at = "not-a-timestamp"; }]) {
    const value = { ...RECEIPT }; mutate(value); const calls = { value: 0 };
    await rejected(() => appendCfoDailySnapshotRevision(input(), { supaUrl: URL, supaKey: KEY, fetchImpl: async () => { calls.value += 1; return response(value); } }), /^cfo_snapshot_revision_store_failed:(?:receipt_mismatch|invalid_receipt)$/);
    assert.equal(calls.value, 1);
  }
});

test("rejects hostile response envelopes and parsed receipts with fixed redacted errors", async () => {
  const responseShapes = [
    new Proxy({}, { get: (_target, key) => key === "then" ? undefined : (() => { throw new Error("RAW_BODY_SENTINEL"); })() }),
    Object.defineProperty({ status: 200, json: async () => RECEIPT }, "ok", { enumerable: true, get: () => { throw new Error("CREDENTIAL_SENTINEL"); } }),
  ];
  for (const shape of responseShapes) await rejected(() => appendCfoDailySnapshotRevision(input(), { supaUrl: URL, supaKey: KEY, fetchImpl: async () => shape }), /^cfo_snapshot_revision_store_failed:invalid_response$/);
  const parsedShapes = [
    new Proxy({}, { get: (_target, key) => key === "then" ? undefined : undefined, ownKeys: () => { throw new Error("RAW_BODY_SENTINEL"); } }),
    Object.defineProperty({ ...RECEIPT }, "public_ref", { enumerable: true, get: () => { throw new Error("ACCOUNT_REF_SENTINEL"); } }),
    Object.defineProperty({ ...RECEIPT }, "hidden", { value: true }),
    Object.assign({ ...RECEIPT }, { [Symbol("extra")]: true }),
  ];
  for (const parsed of parsedShapes) await rejected(() => appendCfoDailySnapshotRevision(input(), { supaUrl: URL, supaKey: KEY, fetchImpl: async () => response(parsed) }), /^cfo_snapshot_revision_store_failed:invalid_receipt$/);
});

test("does not replay a mutated public Error through a later hostile response getter", async () => {
  let publicError;
  await assert.rejects(() => appendCfoDailySnapshotRevision(input(), {
    supaUrl: URL, supaKey: KEY, fetchImpl: async () => null,
  }), error => {
    publicError = error;
    assert.equal(error.message, "cfo_snapshot_revision_store_failed:invalid_response");
    return true;
  });
  publicError.message = "RAW_BODY_SENTINEL";

  const hostileResponse = {};
  Object.defineProperty(hostileResponse, "ok", {
    enumerable: true,
    get: () => { throw publicError; },
  });
  Object.defineProperty(hostileResponse, "status", { enumerable: true, value: 200 });
  await assert.rejects(() => appendCfoDailySnapshotRevision(input(), {
    supaUrl: URL, supaKey: KEY, fetchImpl: async () => hostileResponse,
  }), error => {
    assert.notEqual(error, publicError);
    assert.equal(error.message, "cfo_snapshot_revision_store_failed:invalid_response");
    assert.doesNotMatch(error.message, /RAW_BODY_SENTINEL/);
    return true;
  });
});

test("does not replay a nested public Error through the outer response getter", async () => {
  let innerError;
  const outerFetch = async () => {
    await assert.rejects(() => appendCfoDailySnapshotRevision(input(), {
      supaUrl: URL, supaKey: KEY, fetchImpl: async () => null,
    }), error => {
      innerError = error;
      error.message = "INNER_BODY_SENTINEL";
      return true;
    });

    const hostileResponse = {};
    Object.defineProperty(hostileResponse, "ok", {
      enumerable: true,
      get: () => { throw innerError; },
    });
    Object.defineProperty(hostileResponse, "status", { enumerable: true, value: 200 });
    return hostileResponse;
  };

  await assert.rejects(() => appendCfoDailySnapshotRevision(input(), {
    supaUrl: URL, supaKey: KEY, fetchImpl: outerFetch,
  }), error => {
    assert.notEqual(error, innerError);
    assert.equal(error.message, "cfo_snapshot_revision_store_failed:invalid_response");
    assert.doesNotMatch(error.message, /INNER_BODY_SENTINEL/);
    return true;
  });
});

test("never logs on success or representative validation, network, and provider failures", async () => {
  const names = ["log", "info", "debug", "warn", "error"]; const originals = Object.fromEntries(names.map(name => [name, console[name]])); let calls = 0;
  try {
    for (const name of names) console[name] = () => { calls += 1; };
    await appendCfoDailySnapshotRevision(input(), { supaUrl: URL, supaKey: KEY, fetchImpl: async () => response() });
    await rejected(() => appendCfoDailySnapshotRevision({ ...input(), revision: 1 }, { supaUrl: URL, supaKey: KEY, fetchImpl: async () => response() }));
    await rejected(() => appendCfoDailySnapshotRevision(input(), { supaUrl: URL, supaKey: KEY, fetchImpl: async () => { throw new Error("RAW_BODY_SENTINEL"); } }), /^cfo_snapshot_revision_store_failed:network$/);
    await rejected(() => appendCfoDailySnapshotRevision(input(), { supaUrl: URL, supaKey: KEY, fetchImpl: async () => response({}, 503) }), /^cfo_snapshot_revision_store_failed:provider_503$/);
    assert.equal(calls, 0);
  } finally { for (const name of names) console[name] = originals[name]; }
});

test("persists actual recovered and action-required Task 2 bundles without reshaping them", async () => {
  const recovered = buildCfoDailyReportFromRecovery({ revision: 2, recovery: {
    reportingDate: DATE, observedAt: AS_OF, status: "recovered", attempts: { reads: 2, repairs: 1, waits: [1000] },
    failureKind: null, moneytreeRead: moneytreeRead(0), repair: { sourceLabel: "Moneytree", freshReread: true, reconciled: true }, action: null,
  }});
  const actionRequired = buildCfoDailyReportFromRecovery({ revision: 2, recovery: {
    reportingDate: DATE, observedAt: AS_OF, status: "action_required", attempts: { reads: 2, repairs: 1, waits: [1000] },
    failureKind: "timeout", moneytreeRead: null, repair: null,
    action: { kind: "provider_outage", sourceLabel: "Moneytree", retryLabel: "30分後に自動再試行します", nextRetryAt: "2026-08-09T06:30:00+09:00" },
  }});
  const bodies = []; const fetchImpl = async (_url, init) => { bodies.push(JSON.parse(init.body)); return response(); };
  await appendCfoDailySnapshotRevision({ ...input(), ...recovered }, { supaUrl: URL, supaKey: KEY, fetchImpl });
  await appendCfoDailySnapshotRevision({ ...input(), ...actionRequired }, { supaUrl: URL, supaKey: KEY, fetchImpl });
  assert.equal(bodies.length, 2);
  assert.equal(bodies[0].p_report_payload.state, "recovered");
  assert.equal(bodies[0].p_report_payload.totals.assetsMinor, 0);
  assert.equal(bodies[1].p_report_payload.state, "action_required");
  assert.equal(bodies[1].p_report_payload.totals.assetsMinor, null);
  assert.equal(bodies[1].p_source_bundle.source.accounts.length, 0);
});
