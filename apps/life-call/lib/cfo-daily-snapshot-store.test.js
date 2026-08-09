"use strict";

const assert = require("node:assert/strict");
const { test } = require("node:test");
const { validateFinancialSourceResult } = require("./cfo-financial-source.js");
const { deriveMoneytreeState, composeMoneytreeRead } = require("./cfo-moneytree-state.js");
const { buildCfoDailyReport } = require("./cfo-daily-snapshot.js");
const { appendCfoDailySnapshot } = require("./cfo-daily-snapshot-store.js");

const DATE = "2026-08-09";
const RUN = "2a000000-0000-4000-8000-000000000001";
const UID = "tenant-a";
const URL = "https://project.supabase.co";
const KEY = "service-role-secret";
const AS_OF = "2026-08-09T06:00:00+09:00";
const SENSITIVE = /UID_SENTINEL|AMOUNT_SENTINEL|ACCOUNT_REF_SENTINEL|CREDENTIAL_SENTINEL|RAW_BODY_SENTINEL|tenant-a|220|service-role-secret|secret|raw|account_ref|amount/i;
const RECEIPT = {
  public_ref: "30000000-0000-4000-8000-000000000001",
  reporting_date: DATE, run_id: RUN, revision: 1, created_at: "2026-08-09T06:00:01.000Z",
};

function moneytreeRead() {
  const source = validateFinancialSourceResult({
    schemaVersion: 1, sourceId: "moneytree_mufg", consent: "valid", freshness: "fresh", asOf: AS_OF,
    accounts: [
      { accountRef: "source_account:synthetic_one", label: "MUFG 口座 1", kind: "deposit", currency: "JPY", balanceMinor: 220, verificationStatus: "provider_reported" },
      { accountRef: "source_account:synthetic_two", label: "MUFG 口座 2", kind: "deposit", currency: "JPY", balanceMinor: 116, verificationStatus: "provider_reported" },
    ], liabilities: [], evidenceRef: "evidence:synthetic_moneytree", partial: true, actionRequired: null,
  });
  const state = deriveMoneytreeState({ signal: "interactive_success", observedAt: AS_OF, aggregationAsOf: null, aggregationFreshnessCutoff: null, liabilitiesExposed: false, liabilityCount: null });
  return composeMoneytreeRead({ source, state });
}
function input(overrides = {}) { return { uid: UID, reportingDate: DATE, runId: RUN, moneytreeRead: moneytreeRead(), ...overrides }; }
function response(body = RECEIPT, status = 200) { return { ok: status >= 200 && status < 300, status, json: async () => body }; }
async function rejected(call, pattern = /^cfo_snapshot_store_failed:[a-z0-9_]+$/, counter = null) {
  let caught;
  await assert.rejects(call, error => { caught = error; return true; });
  assert.match(caught.message, pattern); assert.doesNotMatch(caught.message, SENSITIVE);
  if (counter) assert.equal(counter.value, 1);
}

test("appends one RPC request with exact credentials and normalized bodies", async () => {
  const calls = []; let logs = 0; const providerReceipt = { ...RECEIPT };
  const value = input({ moneytreeRead: moneytreeRead() });
  const expectedReport = buildCfoDailyReport({ reportingDate: DATE, moneytreeRead: value.moneytreeRead });
  const expectedBundle = composeMoneytreeRead({ source: value.moneytreeRead.source, state: value.moneytreeRead.state });
  const fetchImpl = async (url, init) => { calls.push({ url, init }); return response(providerReceipt); };
  const receipt = await appendCfoDailySnapshot(value, { supaUrl: URL, supaKey: KEY, fetchImpl, log: () => { logs += 1; } });
  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, `${URL}/rest/v1/rpc/lm_append_cfo_daily_snapshot`);
  assert.equal(calls[0].init.method, "POST");
  assert.deepEqual(calls[0].init.headers, { apikey: KEY, Authorization: `Bearer ${KEY}`, "Content-Type": "application/json" });
  const request = JSON.parse(calls[0].init.body);
  assert.deepEqual(Object.keys(request).sort(), ["p_report_payload", "p_reporting_date", "p_run_id", "p_source_bundle", "p_uid"]);
  assert.deepEqual(request.p_report_payload, expectedReport);
  assert.deepEqual(request.p_source_bundle, expectedBundle);
  assert.deepEqual(Object.keys(receipt).sort(), ["created_at", "public_ref", "reporting_date", "revision", "run_id"]);
  providerReceipt.revision = 99; providerReceipt.public_ref = "40000000-0000-4000-8000-000000000001";
  assert.deepEqual(receipt, RECEIPT);
  assert.equal(receipt.revision, 1); assert.equal(Object.isFrozen(receipt), true); assert.equal(logs, 0);
  assert.match(calls[0].url, /\/rpc\/lm_append_cfo_daily_snapshot$/);
  assert.doesNotMatch(calls[0].url, /lm_cfo_daily_snapshots/);
});

test("requires exact run echo and keeps hostile failures closed, single-call, and silent", async () => {
  const sinks = [console.log, console.error, console.warn]; let sinkCalls = 0;
  console.log = console.error = console.warn = () => { sinkCalls += 1; };
  try {
  const upperReceipt = { ...RECEIPT, run_id: RUN.toUpperCase() };
  let upperCalls = 0;
  await assert.rejects(() => appendCfoDailySnapshot(input(), { supaUrl: URL, supaKey: KEY, fetchImpl: async () => { upperCalls += 1; return response(upperReceipt); } }), error => {
    assert.match(error.message, /cfo_snapshot_store_failed:receipt_mismatch/); assert.doesNotMatch(error.message, SENSITIVE); assert.equal(upperCalls, 1); return true;
  });
  const failures = [
    ["response proxy", () => new Proxy({}, { get: () => { throw new Error("RAW_BODY_SENTINEL"); } })],
    ["receipt proxy", () => response(new Proxy({}, { ownKeys: () => { throw new Error("RAW_BODY_SENTINEL"); } }))],
    ["response accessor", () => ({ get ok() { throw new Error("CREDENTIAL_SENTINEL"); }, status: 500 })],
    ["receipt accessor", () => response(Object.defineProperty({ ...RECEIPT }, "public_ref", { enumerable: true, get: () => { throw new Error("ACCOUNT_REF_SENTINEL"); } }))],
  ];
  for (const [name, makeFailure] of failures) {
    let calls = 0; const fetchImpl = async () => { calls += 1; return makeFailure(); };
    await assert.rejects(() => appendCfoDailySnapshot(input(), { supaUrl: URL, supaKey: KEY, fetchImpl }), error => {
      assert.match(error.message, /^cfo_snapshot_store_failed:[a-z0-9_]+$/); assert.doesNotMatch(error.message, SENSITIVE); assert.equal(calls, 1, name); return true;
    });
  }
  for (const thrown of ["RAW_BODY_SENTINEL", 7, null, { message: "CREDENTIAL_SENTINEL" }, new Proxy({}, { get: () => { throw new Error("UID_SENTINEL"); } })]) {
    let calls = 0; const fetchImpl = async () => { calls += 1; throw thrown; };
    await assert.rejects(() => appendCfoDailySnapshot(input(), { supaUrl: URL, supaKey: KEY, fetchImpl }), error => {
      assert.match(error.message, /^cfo_snapshot_store_failed:network$/); assert.doesNotMatch(error.message, SENSITIVE); assert.equal(calls, 1); return true;
    });
  }
  } finally { [console.log, console.error, console.warn] = sinks; }
  assert.equal(sinkCalls, 0);
});

test("rejects malformed identity before network and rejects hostile input shapes", async () => {
  const calls = []; const fetchImpl = async () => { calls.push(true); return response(); };
  for (const bad of [
    null, { ...input(), extra: "secret" }, { ...input(), uid: 42 }, { ...input(), uid: "" }, { ...input(), uid: "bad\nuid" },
    { ...input(), reportingDate: "2026-02-30" }, { ...input(), runId: "not-a-uuid" },
    { ...input(), runId: "00000000-0000-0000-0000-000000000000" },
  ]) await rejected(() => appendCfoDailySnapshot(bad, { supaUrl: URL, supaKey: KEY, fetchImpl }));
  const custom = Object.assign(Object.create({ hostile: true }), input());
  await rejected(() => appendCfoDailySnapshot(custom, { supaUrl: URL, supaKey: KEY, fetchImpl }));
  await rejected(() => appendCfoDailySnapshot(new Proxy(input(), {}), { supaUrl: URL, supaKey: KEY, fetchImpl }));
  const accessor = input(); Object.defineProperty(accessor, "uid", { enumerable: true, get: () => "secret" });
  await rejected(() => appendCfoDailySnapshot(accessor, { supaUrl: URL, supaKey: KEY, fetchImpl }));
  assert.equal(calls.length, 0);
});

test("fails closed on receipt mismatch, invalid JSON, non-2xx, and never retries", async () => {
  for (const mutate of [
    value => { value.reporting_date = "2026-08-08"; }, value => { value.run_id = "40000000-0000-4000-8000-000000000001"; },
    value => { value.revision = 2; }, value => { value.extra = "raw response secret account_ref amount_minor"; },
  ]) {
    let value = { ...RECEIPT }; mutate(value); const counter = { value: 0 };
    await rejected(() => appendCfoDailySnapshot(input(), { supaUrl: URL, supaKey: KEY, fetchImpl: async () => { counter.value += 1; return response(value); } }), /cfo_snapshot_store_failed:(?:invalid_receipt|receipt_mismatch)/, counter);
  }
  let calls = 0, jsonCalls = 0;
  const conflictCounter = { value: 0 };
  await rejected(() => appendCfoDailySnapshot(input(), { supaUrl: URL, supaKey: KEY, fetchImpl: async () => { calls += 1; conflictCounter.value += 1; return { ok: false, status: 409, json: () => { jsonCalls += 1; throw new Error("raw response secret"); } }; } }), /cfo_snapshot_store_failed:provider_409/, conflictCounter);
  assert.equal(calls, 1); assert.equal(jsonCalls, 0);
  for (const [body, pattern] of [["not-an-object", /cfo_snapshot_store_failed:invalid_receipt/], [null, /cfo_snapshot_store_failed:invalid_json/]]) {
    const counter = { value: 0 }; const fetchImpl = async () => { counter.value += 1; return body === null ? { ok: true, status: 200, json: async () => { throw new Error("secret raw body"); } } : response(body); };
    await rejected(() => appendCfoDailySnapshot(input(), { supaUrl: URL, supaKey: KEY, fetchImpl }), pattern, counter);
  }
  const unavailableCounter = { value: 0 };
  await rejected(() => appendCfoDailySnapshot(input(), { supaUrl: URL, supaKey: KEY, fetchImpl: async () => { unavailableCounter.value += 1; return { ok: true, status: 503, json: () => { throw new Error("must not read"); } }; } }), /cfo_snapshot_store_failed:provider_503/, unavailableCounter);
  const hostile = new Proxy({}, { get: () => { throw new Error("secret UID 220 account_ref"); } }); const networkCounter = { value: 0 };
  await rejected(() => appendCfoDailySnapshot(input(), { supaUrl: URL, supaKey: KEY, fetchImpl: async () => { networkCounter.value += 1; throw hostile; } }), /^cfo_snapshot_store_failed:network$/, networkCounter);
  const shapeCounter = { value: 0 };
  await rejected(() => appendCfoDailySnapshot(input(), { supaUrl: URL, supaKey: KEY, fetchImpl: async () => { shapeCounter.value += 1; return response({}); } }), /^cfo_snapshot_store_failed:invalid_receipt$/, shapeCounter);
});
