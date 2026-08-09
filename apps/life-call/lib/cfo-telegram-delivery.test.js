"use strict";

const assert = require("node:assert/strict");
const { test } = require("node:test");
const { claimCfoTelegramDelivery, recordCfoTelegramDelivery } = require("./cfo-telegram-delivery.js");

const UID = "tenant-a";
const DATE = "2026-08-09";
const SNAPSHOT = "30000000-0000-4000-8000-000000000001";
const CLAIM = "40000000-0000-4000-8000-000000000001";
const URL = "https://project.supabase.co";
const KEY = "service-role-secret";
const SENSITIVE = /UID_SENTINEL|REF_SENTINEL|MESSAGE_SENTINEL|CREDENTIAL_SENTINEL|RAW_BODY_SENTINEL|tenant-a|service-role-secret|secret|raw/i;
const CLAIM_RECEIPT = { public_ref: CLAIM, decision: "send", reporting_date: DATE, revision: 1, created_at: "2026-08-09T06:00:01.000Z" };
const RECORD_RECEIPT = { public_ref: "50000000-0000-4000-8000-000000000001", claim_public_ref: CLAIM, message_id: 123, created_at: "2026-08-09T06:00:02.000Z" };

function claimInput(overrides = {}) { return { uid: UID, snapshotPublicRef: SNAPSHOT, reportKind: "assets_liabilities", reportingDate: DATE, revision: 1, ...overrides }; }
function recordInput(overrides = {}) { return { claimPublicRef: CLAIM, messageId: 123, ...overrides }; }
function response(body, status = 200) { return { ok: status >= 200 && status < 300, status, json: async () => body }; }
async function rejected(call, reason = null, counter = null) {
  await assert.rejects(call, error => {
    assert.match(error.message, /^cfo_telegram_delivery_failed:[a-z0-9_]+$/);
    assert.doesNotMatch(error.message, SENSITIVE);
    if (reason) assert.equal(error.message, `cfo_telegram_delivery_failed:${reason}`);
    return true;
  });
  if (counter) assert.equal(counter.value, 1);
}

// Mutation map: request/receipt field loss or direct-table URL changes break the exact RPC contract;
// accepting non-assets_liabilities or non-positive IDs breaks domain gating; returning provider objects
// directly breaks isolation; retry/logging/provider diagnostics break reliability and privacy; missing
// echo checks allow a receipt for a different snapshot/date/revision/message to be accepted.
test("claims one exact RPC and returns an isolated frozen five-key receipt", async () => {
  const calls = []; const provider = { ...CLAIM_RECEIPT };
  const receipt = await claimCfoTelegramDelivery(claimInput(), { supaUrl: URL, supaKey: KEY, fetchImpl: async (url, init) => { calls.push({ url, init }); return response(provider); } });
  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, `${URL}/rest/v1/rpc/lm_claim_cfo_telegram_delivery`);
  assert.doesNotMatch(calls[0].url, /lm_cfo_telegram_delivery_(claims|receipts)/);
  assert.deepEqual(calls[0].init.headers, { apikey: KEY, Authorization: `Bearer ${KEY}`, "Content-Type": "application/json" });
  assert.deepEqual(JSON.parse(calls[0].init.body), { p_uid: UID, p_snapshot_public_ref: SNAPSHOT, p_report_kind: "assets_liabilities", p_reporting_date: DATE, p_revision: 1 });
  assert.deepEqual(receipt, CLAIM_RECEIPT); assert.equal(Object.isFrozen(receipt), true);
  provider.decision = "reconcile"; assert.equal(receipt.decision, "send");
});

test("records one exact RPC and returns an isolated frozen four-key receipt", async () => {
  const calls = []; const provider = { ...RECORD_RECEIPT };
  const receipt = await recordCfoTelegramDelivery(recordInput(), { supaUrl: URL, supaKey: KEY, fetchImpl: async (url, init) => { calls.push({ url, init }); return response(provider); } });
  assert.equal(calls.length, 1); assert.equal(calls[0].url, `${URL}/rest/v1/rpc/lm_record_cfo_telegram_delivery`);
  assert.doesNotMatch(calls[0].url, /lm_cfo_telegram_delivery_(claims|receipts)/);
  assert.deepEqual(JSON.parse(calls[0].init.body), { p_claim_public_ref: CLAIM, p_message_id: 123 });
  assert.deepEqual(receipt, RECORD_RECEIPT); assert.equal(Object.isFrozen(receipt), true);
  provider.message_id = 999; assert.equal(receipt.message_id, 123);
});

test("rejects closed, typed inputs before network and gates report kind/IDs", async () => {
  const calls = []; const opts = { supaUrl: URL, supaKey: KEY, fetchImpl: async () => { calls.push(true); return response(CLAIM_RECEIPT); } };
  for (const bad of [null, [], { ...claimInput(), extra: "secret" }, { ...claimInput(), uid: "" }, { ...claimInput(), snapshotPublicRef: "not-a-uuid" }, { ...claimInput(), reportKind: "cash" }, { ...claimInput(), reportingDate: "2026-02-30" }, { ...claimInput(), revision: 0 }, { ...claimInput(), revision: 1.5 }, { ...claimInput(), revision: Number.MAX_SAFE_INTEGER + 1 }]) await rejected(() => claimCfoTelegramDelivery(bad, opts));
  for (const bad of [null, [], { ...recordInput(), extra: "secret" }, { ...recordInput(), claimPublicRef: "not-a-uuid" }, { ...recordInput(), messageId: 0 }, { ...recordInput(), messageId: 1.5 }, { ...recordInput(), messageId: Number.MAX_SAFE_INTEGER + 1 }]) await rejected(() => recordCfoTelegramDelivery(bad, opts));
  const custom = Object.assign(Object.create({ hostile: true }), claimInput()); await rejected(() => claimCfoTelegramDelivery(custom, opts));
  await rejected(() => claimCfoTelegramDelivery(new Proxy(claimInput(), {}), opts));
  const accessor = claimInput(); Object.defineProperty(accessor, "uid", { enumerable: true, get: () => "UID_SENTINEL" }); await rejected(() => claimCfoTelegramDelivery(accessor, opts));
  assert.equal(calls.length, 0);
});

test("fails closed on exact echo/receipt validation, hostile provider paths, and never retries or logs", async () => {
  for (const mutate of [v => { v.public_ref = "not-a-uuid"; }, v => { v.public_ref = "00000000-0000-0000-0000-000000000000"; }, v => { v.decision = "SEND"; }, v => { v.reporting_date = "2026-08-08"; }, v => { v.revision = 2; }, v => { v.created_at = "not-a-timestamp"; }, v => { delete v.decision; }, v => { v.extra = "RAW_BODY_SENTINEL"; }]) {
    const value = { ...CLAIM_RECEIPT }; mutate(value); const counter = { value: 0 };
    await rejected(() => claimCfoTelegramDelivery(claimInput(), { supaUrl: URL, supaKey: KEY, fetchImpl: async () => { counter.value += 1; return response(value); } }), null, counter);
  }
  for (const mutate of [v => { v.public_ref = "not-a-uuid"; }, v => { v.claim_public_ref = "00000000-0000-0000-0000-000000000000"; }, v => { v.message_id = 0; }, v => { v.message_id = 124; }, v => { v.created_at = "not-a-timestamp"; }, v => { delete v.claim_public_ref; }]) {
    const value = { ...RECORD_RECEIPT }; mutate(value); const counter = { value: 0 };
    await rejected(() => recordCfoTelegramDelivery(recordInput(), { supaUrl: URL, supaKey: KEY, fetchImpl: async () => { counter.value += 1; return response(value); } }), null, counter);
  }
  const sinks = [console.log, console.error, console.warn]; let sinkCalls = 0; console.log = console.error = console.warn = () => { sinkCalls += 1; };
  try {
    for (const thrown of ["RAW_BODY_SENTINEL", 7, null, { message: "CREDENTIAL_SENTINEL" }, new Proxy({}, { get: () => { throw new Error("REF_SENTINEL"); } })]) {
      const counter = { value: 0 }; await rejected(() => claimCfoTelegramDelivery(claimInput(), { supaUrl: URL, supaKey: KEY, fetchImpl: async () => { counter.value += 1; throw thrown; } }), "network", counter);
    }
    for (const makeResponse of [() => new Proxy({}, { get: () => { throw new Error("RAW_BODY_SENTINEL"); } }), () => ({ get ok() { throw new Error("CREDENTIAL_SENTINEL"); }, status: 500 }), () => ({ ok: true, status: 200, json: "not-a-function" }), () => ({ ok: true, status: 200, json: async () => { throw new Error("RAW_BODY_SENTINEL"); } })]) {
      const counter = { value: 0 }; await rejected(() => recordCfoTelegramDelivery(recordInput(), { supaUrl: URL, supaKey: KEY, fetchImpl: async () => { counter.value += 1; return makeResponse(); } }), null, counter);
    }
    const counter = { value: 0 }; await rejected(() => claimCfoTelegramDelivery(claimInput(), { supaUrl: URL, supaKey: KEY, fetchImpl: async () => { counter.value += 1; return { ok: false, status: 409, json: () => { throw new Error("RAW_BODY_SENTINEL"); } }; } }), "provider_409", counter);
  } finally { [console.log, console.error, console.warn] = sinks; }
  assert.equal(sinkCalls, 0);
});
