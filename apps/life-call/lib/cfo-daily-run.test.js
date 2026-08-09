"use strict";

const assert = require("node:assert/strict");
const { test } = require("node:test");
const { resolveCfoDailyRun } = require("./cfo-daily-run.js");

const UID = "tenant-a";
const URL = "https://project.supabase.co";
const KEY = "service-role-secret";
const SENSITIVE = /UID_SENTINEL|CREDENTIAL_SENTINEL|RAW_BODY_SENTINEL|tenant-a|service-role-secret|secret|raw/i;
const RECEIPT = {
  public_ref: "30000000-0000-4000-8000-000000000001",
  reporting_date: "2026-08-09", run_id: "20000000-0000-4000-8000-000000000001",
  time_zone: "Asia/Tokyo", created_at: "2026-08-09T06:00:01.000Z",
};

function input(overrides = {}) { return { uid: UID, ...overrides }; }
function response(body = RECEIPT, status = 200) { return { ok: status >= 200 && status < 300, status, json: async () => body }; }
async function rejected(call, pattern = /^cfo_daily_run_failed:[a-z0-9_]+$/, counter = null) {
  let caught;
  await assert.rejects(call, error => { caught = error; return true; });
  assert.match(caught.message, pattern); assert.doesNotMatch(caught.message, SENSITIVE);
  if (counter) assert.equal(counter.value, 1);
}

test("claims one RPC with exact uid and returns a closed frozen five-key receipt", async () => {
  const calls = []; const providerReceipt = { ...RECEIPT };
  const fetchImpl = async (url, init) => { calls.push({ url, init }); return response(providerReceipt); };
  const receipt = await resolveCfoDailyRun(input(), { supaUrl: URL, supaKey: KEY, fetchImpl });
  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, `${URL}/rest/v1/rpc/lm_claim_cfo_daily_run`);
  assert.doesNotMatch(calls[0].url, /lm_panel_preferences/);
  assert.equal(calls[0].init.method, "POST");
  assert.deepEqual(calls[0].init.headers, { apikey: KEY, Authorization: `Bearer ${KEY}`, "Content-Type": "application/json" });
  assert.deepEqual(JSON.parse(calls[0].init.body), { p_uid: UID });
  assert.deepEqual(Object.keys(receipt).sort(), ["created_at", "public_ref", "reporting_date", "run_id", "time_zone"]);
  providerReceipt.run_id = "40000000-0000-4000-8000-000000000001";
  assert.deepEqual(receipt, RECEIPT);
  assert.equal(Object.isFrozen(receipt), true);
});

test("returns the identical retry receipt on same-date retry without a second network call", async () => {
  const calls = []; const fetchImpl = async (url, init) => { calls.push({ url, init }); return response(); };
  const first = await resolveCfoDailyRun(input(), { supaUrl: URL, supaKey: KEY, fetchImpl });
  const second = await resolveCfoDailyRun(input(), { supaUrl: URL, supaKey: KEY, fetchImpl });
  assert.equal(calls.length, 2, "each call makes exactly one RPC request, no internal retry loop");
  assert.deepEqual(first, second);
});

test("rejects malformed identity before network and rejects hostile input shapes", async () => {
  const calls = []; const fetchImpl = async () => { calls.push(true); return response(); };
  for (const bad of [
    null, undefined, "tenant-a", 42, [], { ...input(), extra: "secret" }, { uid: 42 }, { uid: "" },
    { uid: "bad\nuid" }, { uid: " tenant-a" }, { uid: "a".repeat(256) },
  ]) await rejected(() => resolveCfoDailyRun(bad, { supaUrl: URL, supaKey: KEY, fetchImpl }));
  const custom = Object.assign(Object.create({ hostile: true }), input());
  await rejected(() => resolveCfoDailyRun(custom, { supaUrl: URL, supaKey: KEY, fetchImpl }));
  await rejected(() => resolveCfoDailyRun(new Proxy(input(), {}), { supaUrl: URL, supaKey: KEY, fetchImpl }));
  const accessor = input(); Object.defineProperty(accessor, "uid", { enumerable: true, get: () => "secret" });
  await rejected(() => resolveCfoDailyRun(accessor, { supaUrl: URL, supaKey: KEY, fetchImpl }));
  await rejected(() => resolveCfoDailyRun(input(), { supaUrl: "", supaKey: KEY, fetchImpl }));
  await rejected(() => resolveCfoDailyRun(input(), { supaUrl: URL, supaKey: "", fetchImpl }));
  await rejected(() => resolveCfoDailyRun(input(), { supaUrl: URL, supaKey: KEY, fetchImpl: "not-a-function" }));
  assert.equal(calls.length, 0);
});

test("fails closed on every invalid receipt shape and never retries", async () => {
  for (const mutate of [
    value => { delete value.time_zone; }, value => { value.extra = "raw secret"; },
    value => { value.public_ref = "not-a-uuid"; },
    value => { value.public_ref = "00000000-0000-0000-0000-000000000000"; },
    value => { value.run_id = "00000000-0000-0000-0000-000000000000"; },
    value => { value.reporting_date = "2026-02-30"; },
    value => { value.time_zone = "Not/AZone"; }, value => { value.time_zone = ""; },
    value => { value.created_at = "not-a-timestamp"; },
  ]) {
    const value = { ...RECEIPT }; mutate(value); const counter = { value: 0 };
    await rejected(() => resolveCfoDailyRun(input(), { supaUrl: URL, supaKey: KEY, fetchImpl: async () => { counter.value += 1; return response(value); } }), /^cfo_daily_run_failed:invalid_receipt$/, counter);
  }
  for (const body of ["not-an-object", null, 7, []]) {
    const counter = { value: 0 };
    await rejected(() => resolveCfoDailyRun(input(), { supaUrl: URL, supaKey: KEY, fetchImpl: async () => { counter.value += 1; return response(body); } }), /^cfo_daily_run_failed:invalid_receipt$/, counter);
  }
});

test("fails closed on hostile network/response paths, never retries, and never logs", async () => {
  const sinks = [console.log, console.error, console.warn]; let sinkCalls = 0;
  console.log = console.error = console.warn = () => { sinkCalls += 1; };
  try {
    for (const thrown of ["RAW_BODY_SENTINEL", 7, null, { message: "CREDENTIAL_SENTINEL" }, new Proxy({}, { get: () => { throw new Error("UID_SENTINEL"); } })]) {
      const counter = { value: 0 };
      await rejected(() => resolveCfoDailyRun(input(), { supaUrl: URL, supaKey: KEY, fetchImpl: async () => { counter.value += 1; throw thrown; } }), /^cfo_daily_run_failed:network$/, counter);
    }
    const failures = [
      () => new Proxy({}, { get: () => { throw new Error("RAW_BODY_SENTINEL"); } }),
      () => ({ get ok() { throw new Error("CREDENTIAL_SENTINEL"); }, status: 500 }),
      () => ({ ok: true, status: 200, json: "not-a-function" }),
      () => ({ ok: true, status: 200, json: async () => { throw new Error("secret raw body"); } }),
      () => ({ ok: false, status: 409, json: () => { throw new Error("must not read"); } }),
      () => response(new Proxy({}, { ownKeys: () => { throw new Error("RAW_BODY_SENTINEL"); } })),
    ];
    for (const makeFailure of failures) {
      const counter = { value: 0 };
      await rejected(() => resolveCfoDailyRun(input(), { supaUrl: URL, supaKey: KEY, fetchImpl: async () => { counter.value += 1; return makeFailure(); } }));
    }
  } finally { [console.log, console.error, console.warn] = sinks; }
  assert.equal(sinkCalls, 0);
});
