"use strict";

const assert = require("node:assert/strict");
const { test } = require("node:test");
const { validateFinancialSourceResult } = require("./cfo-financial-source.js");
const { deriveMoneytreeState, composeMoneytreeRead } = require("./cfo-moneytree-state.js");
const { appendCfoDailySnapshot } = require("./cfo-daily-snapshot-store.js");

const DATE = "2026-08-09";
const RUN = "20000000-0000-4000-8000-000000000001";
const UID = "tenant-a";
const URL = "https://project.supabase.co";
const KEY = "service-role-secret";
const AS_OF = "2026-08-09T06:00:00+09:00";
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
async function rejected(call, pattern = /^cfo_snapshot_store_failed:[a-z0-9_]+$/) {
  await assert.rejects(call, error => { assert.match(error.message, pattern); return true; });
}

test("appends exactly one RPC request and returns a frozen five-key receipt", async () => {
  const calls = []; let logs = 0;
  const fetchImpl = async (url, init) => { calls.push({ url, init }); return response(); };
  const receipt = await appendCfoDailySnapshot(input(), { supaUrl: URL, supaKey: KEY, fetchImpl, log: () => { logs += 1; } });
  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, `${URL}/rest/v1/rpc/lm_append_cfo_daily_snapshot`);
  assert.equal(calls[0].init.method, "POST");
  assert.deepEqual(Object.keys(JSON.parse(calls[0].init.body)).sort(), ["p_report_payload", "p_reporting_date", "p_run_id", "p_source_bundle", "p_uid"]);
  assert.deepEqual(Object.keys(receipt).sort(), ["created_at", "public_ref", "reporting_date", "revision", "run_id"]);
  assert.equal(receipt.revision, 1); assert.equal(Object.isFrozen(receipt), true); assert.equal(logs, 0);
  assert.match(calls[0].url, /\/rpc\/lm_append_cfo_daily_snapshot$/);
  assert.doesNotMatch(calls[0].url, /lm_cfo_daily_snapshots/);
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
    let value = { ...RECEIPT }; mutate(value);
    await rejected(() => appendCfoDailySnapshot(input(), { supaUrl: URL, supaKey: KEY, fetchImpl: async () => response(value) }), /cfo_snapshot_store_failed:(?:invalid_receipt|receipt_mismatch)/);
  }
  let calls = 0, jsonCalls = 0;
  await rejected(() => appendCfoDailySnapshot(input(), { supaUrl: URL, supaKey: KEY, fetchImpl: async () => { calls += 1; return { ok: false, status: 409, json: () => { jsonCalls += 1; throw new Error("raw response secret"); } }; } }), /cfo_snapshot_store_failed:provider_409/);
  assert.equal(calls, 1); assert.equal(jsonCalls, 0);
  await rejected(() => appendCfoDailySnapshot(input(), { supaUrl: URL, supaKey: KEY, fetchImpl: async () => response("not-an-object") }), /cfo_snapshot_store_failed:invalid_receipt/);
  await rejected(() => appendCfoDailySnapshot(input(), { supaUrl: URL, supaKey: KEY, fetchImpl: async () => ({ ok: true, status: 200, json: async () => { throw new Error("secret raw body"); } }) }), /cfo_snapshot_store_failed:invalid_json/);
  await rejected(() => appendCfoDailySnapshot(input(), { supaUrl: URL, supaKey: KEY, fetchImpl: async () => ({ ok: true, status: 503, json: () => { throw new Error("must not read"); } }) }), /cfo_snapshot_store_failed:provider_503/);
  const hostile = new Proxy({}, { get: () => { throw new Error("secret UID 220 account_ref"); } });
  await rejected(() => appendCfoDailySnapshot(input(), { supaUrl: URL, supaKey: KEY, fetchImpl: async () => { throw hostile; } }));
  await assert.rejects(() => appendCfoDailySnapshot(input(), { supaUrl: URL, supaKey: KEY, fetchImpl: async () => response({}) }), error => {
    assert.doesNotMatch(error.message, /secret|tenant-a|220|account_ref|amount|raw response/i); return true;
  });
});
