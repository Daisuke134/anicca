"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const migrationPath = path.join(__dirname, "../migrations/2026-08-29-lm-wake-telnyx-receipt.sql");
const SQL = fs.existsSync(migrationPath) ? fs.readFileSync(migrationPath, "utf8") : "";

let recordTelnyxWakeReceipt;
let requireError = null;
try {
  ({ recordTelnyxWakeReceipt } = require("./telnyx-receipt.js"));
} catch (error) {
  requireError = error;
  recordTelnyxWakeReceipt = async () => ({ ok: false, matched: 0, error: "module_missing" });
}

const BASE_INPUT = {
  uid: "tenant-a",
  eventKey: "tenant-a|2026-08-29T09:00:00+09:00|10",
  claimToken: "claim-token-a",
  callControlId: "v2:call-control-a",
  callSessionId: "session-a",
  callLegId: "leg-a",
  webhookEventId: "event-a",
  amdResult: "human",
};
const DEPS = { supaUrl: "https://supa.example", supaKey: "service-role-secret" };

function response(status, body) {
  return { status, ok: status >= 200 && status < 300, json: async () => body };
}

test("the receipt migration adds only nullable bounded fields to the existing wake ledger", () => {
  assert.equal(requireError, null, "the receipt client module must load");
  for (const column of [
    "telnyx_call_control_id",
    "telnyx_call_session_id",
    "telnyx_call_leg_id",
    "telnyx_webhook_event_id",
  ]) {
    assert.match(SQL, new RegExp(`ADD COLUMN IF NOT EXISTS ${column}\\s+text`, "i"));
    assert.match(SQL, new RegExp(`${column}[^;]*char_length\\([^)]*\\) BETWEEN 1 AND 512`, "i"));
  }
  assert.match(SQL, /ADD COLUMN IF NOT EXISTS telnyx_webhook_received_at\s+timestamptz/i);
  assert.doesNotMatch(SQL, /CREATE TABLE\s+(?:IF NOT EXISTS\s+)?public\.lm_.*telnyx/i);
});

test("the RPC has the exact eight text arguments, scalar integer result, and service-only ACL", () => {
  assert.match(SQL, /CREATE OR REPLACE FUNCTION public\.record_lm_wake_telnyx_receipt\(/i);
  assert.match(SQL, /p_uid\s+text[\s\S]*p_event_key\s+text[\s\S]*p_claim_token\s+text[\s\S]*p_telnyx_call_control_id\s+text/i);
  assert.match(SQL, /p_telnyx_call_session_id\s+text\s+DEFAULT\s+NULL/i);
  assert.match(SQL, /p_telnyx_call_leg_id\s+text\s+DEFAULT\s+NULL/i);
  assert.match(SQL, /p_telnyx_webhook_event_id\s+text\s+DEFAULT\s+NULL/i);
  assert.match(SQL, /p_amd_result\s+text\s+DEFAULT\s+NULL/i);
  assert.match(SQL, /RETURNS\s+integer/i);
  assert.match(SQL, /REVOKE ALL ON FUNCTION public\.record_lm_wake_telnyx_receipt\(text,text,text,text,text,text,text,text\)\s+FROM PUBLIC, anon, authenticated/i);
  assert.match(SQL, /GRANT EXECUTE ON FUNCTION public\.record_lm_wake_telnyx_receipt\(text,text,text,text,text,text,text,text\)\s+TO service_role/i);
});

test("the RPC validates before one atomic UPDATE and returns its exact row count", () => {
  const body = SQL.match(/CREATE OR REPLACE FUNCTION public\.record_lm_wake_telnyx_receipt[\s\S]*?\$\$;/i)?.[0] || "";
  assert.match(body, /RAISE EXCEPTION/i);
  assert.match(body, /UPDATE\s+public\.lm_wake_log/i);
  assert.match(body, /GET DIAGNOSTICS\s+[^;]*ROW_COUNT/i);
  assert.match(body, /RETURN\s+[^;]*matched/i);
  assert.doesNotMatch(body, /SELECT\s+\*?\s*INTO|FOR UPDATE/i);
  assert.match(body, /p_amd_result\s+NOT\s+IN\s*\('human',\s*'machine',\s*'not_sure'\)/i);
});

test("the RPC latches provider identity and first-write webhook time without changing old wake fields", () => {
  assert.match(SQL, /telnyx_call_control_id\s*=\s*CASE[\s\S]*IS NULL[\s\S]*p_telnyx_call_control_id/i);
  assert.match(SQL, /telnyx_call_session_id\s*=\s*CASE[\s\S]*IS NULL[\s\S]*p_telnyx_call_session_id/i);
  assert.match(SQL, /telnyx_call_leg_id\s*=\s*CASE[\s\S]*IS NULL[\s\S]*p_telnyx_call_leg_id/i);
  assert.match(SQL, /telnyx_webhook_event_id\s*=\s*CASE[\s\S]*IS NULL[\s\S]*p_telnyx_webhook_event_id/i);
  assert.match(SQL, /telnyx_webhook_received_at\s*=\s*CASE[\s\S]*p_telnyx_webhook_event_id IS NOT NULL[\s\S]*IS NULL[\s\S]*clock_timestamp\(\)/i);
  assert.match(SQL, /amd_result\s*=\s*CASE[\s\S]*IS NULL[\s\S]*p_amd_result/i);
  assert.match(SQL, /telnyx_call_control_id\s+IS NULL\s+OR\s+telnyx_call_control_id\s*=\s+p_telnyx_call_control_id/i);
  assert.match(SQL, /telnyx_call_session_id\s+IS NULL\s+OR\s+p_telnyx_call_session_id\s+IS NULL\s+OR\s+telnyx_call_session_id\s*=\s+p_telnyx_call_session_id/i);
  assert.match(SQL, /WHERE\s+uid\s*=\s+p_uid[\s\S]*event_key\s*=\s+p_event_key[\s\S]*claim_token\s*=\s+p_claim_token/i);
  assert.doesNotMatch(SQL, /SET\s+[^;]*(?:called_at|answered_at)\s*=/i);
});

test("provider call and webhook identities are unique across wake rows with a unique-violation backstop", () => {
  assert.match(SQL, /CREATE UNIQUE INDEX IF NOT EXISTS lm_wake_log_telnyx_call_control_id_key[\s\S]*ON public\.lm_wake_log\s*\(telnyx_call_control_id\)[\s\S]*WHERE telnyx_call_control_id IS NOT NULL/i);
  assert.match(SQL, /CREATE UNIQUE INDEX IF NOT EXISTS lm_wake_log_telnyx_webhook_event_id_key[\s\S]*ON public\.lm_wake_log\s*\(telnyx_webhook_event_id\)[\s\S]*WHERE telnyx_webhook_event_id IS NOT NULL/i);
  const body = SQL.match(/CREATE OR REPLACE FUNCTION public\.record_lm_wake_telnyx_receipt[\s\S]*?\$\$;/i)?.[0] || "";
  assert.match(body, /NOT EXISTS\s*\([\s\S]*telnyx_call_control_id\s*=\s*p_telnyx_call_control_id/i);
  assert.match(body, /NOT EXISTS\s*\([\s\S]*telnyx_webhook_event_id\s*=\s*p_telnyx_webhook_event_id/i);
  assert.match(body, /EXCEPTION\s+WHEN\s+unique_violation[\s\S]*RETURN\s+0/i);
});

test("a later valid AMD observation replaces the earlier one while null preserves it", () => {
  assert.match(SQL, /amd_result\s*=\s*CASE[\s\S]*p_amd_result IS NULL[\s\S]*ELSE p_amd_result/i);
});

test("the client posts the exact RPC body with service headers and returns matched=1", async () => {
  const calls = [];
  const result = await recordTelnyxWakeReceipt(BASE_INPUT, {
    ...DEPS,
    fetchImpl: async (url, init) => {
      calls.push({ url: String(url), init });
      return response(200, 1);
    },
  });
  assert.deepEqual(result, { ok: true, matched: 1 });
  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, "https://supa.example/rest/v1/rpc/record_lm_wake_telnyx_receipt");
  assert.equal(calls[0].init.method, "POST");
  assert.deepEqual(calls[0].init.headers, {
    "Content-Type": "application/json",
    apikey: DEPS.supaKey,
    Authorization: `Bearer ${DEPS.supaKey}`,
  });
  assert.deepEqual(JSON.parse(calls[0].init.body), {
    p_uid: BASE_INPUT.uid,
    p_event_key: BASE_INPUT.eventKey,
    p_claim_token: BASE_INPUT.claimToken,
    p_telnyx_call_control_id: BASE_INPUT.callControlId,
    p_telnyx_call_session_id: BASE_INPUT.callSessionId,
    p_telnyx_call_leg_id: BASE_INPUT.callLegId,
    p_telnyx_webhook_event_id: BASE_INPUT.webhookEventId,
    p_amd_result: BASE_INPUT.amdResult,
  });
});

test("the client accepts only verified non-negative integer scalar results, including zero", async () => {
  for (const [status, body, matched] of [[200, 1, 1], [201, 0, 0]]) {
    const result = await recordTelnyxWakeReceipt(BASE_INPUT, {
      ...DEPS, fetchImpl: async () => response(status, body),
    });
    assert.deepEqual(result, { ok: true, matched });
  }
});

test("missing mandatory identity or invalid AMD performs no fetch", async () => {
  for (const key of ["uid", "eventKey", "claimToken", "callControlId"]) {
    let fetches = 0;
    const result = await recordTelnyxWakeReceipt({ ...BASE_INPUT, [key]: "   " }, {
      ...DEPS, fetchImpl: async () => { fetches += 1; throw new Error("must not fetch"); },
    });
    assert.deepEqual(result, { ok: false, matched: 0, error: "missing_args" });
    assert.equal(fetches, 0);
  }
  let fetches = 0;
  const invalid = await recordTelnyxWakeReceipt({ ...BASE_INPUT, amdResult: "robot" }, {
    ...DEPS, fetchImpl: async () => { fetches += 1; throw new Error("must not fetch"); },
  });
  assert.deepEqual(invalid, { ok: false, matched: 0, error: "invalid_amd_result" });
  assert.equal(fetches, 0);
});

test("omitted optional provider fields are explicit nulls in the RPC body", async () => {
  let body;
  const result = await recordTelnyxWakeReceipt({
    uid: BASE_INPUT.uid, eventKey: BASE_INPUT.eventKey,
    claimToken: BASE_INPUT.claimToken, callControlId: BASE_INPUT.callControlId,
  }, { ...DEPS, fetchImpl: async (_url, init) => {
    body = JSON.parse(init.body);
    return response(200, 0);
  } });
  assert.deepEqual(result, { ok: true, matched: 0 });
  assert.deepEqual(body, {
    p_uid: BASE_INPUT.uid, p_event_key: BASE_INPUT.eventKey,
    p_claim_token: BASE_INPUT.claimToken, p_telnyx_call_control_id: BASE_INPUT.callControlId,
    p_telnyx_call_session_id: null, p_telnyx_call_leg_id: null,
    p_telnyx_webhook_event_id: null, p_amd_result: null,
  });
});

test("null input and null dependencies fail closed without fetching", async () => {
  let fetches = 0;
  const fetchImpl = async () => { fetches += 1; throw new Error("must not fetch"); };
  assert.deepEqual(await recordTelnyxWakeReceipt(null, { ...DEPS, fetchImpl }), {
    ok: false, matched: 0, error: "missing_args",
  });
  assert.deepEqual(await recordTelnyxWakeReceipt(BASE_INPUT, null), {
    ok: false, matched: 0, error: "missing_config",
  });
  assert.equal(fetches, 0);
});

test("malformed result, HTTP failure, unreadable response, and thrown fetch fail closed generically", async () => {
  const cases = [
    [200, "1", "invalid_result"],
    [200, 1.5, "invalid_result"],
    [200, -1, "invalid_result"],
    [500, { error: "provider-secret-body" }, "http_error"],
    [200, { matched: 1 }, "invalid_result"],
  ];
  for (const [status, body, error] of cases) {
    const result = await recordTelnyxWakeReceipt(BASE_INPUT, {
      ...DEPS, fetchImpl: async () => response(status, body),
    });
    assert.deepEqual(result, { ok: false, matched: 0, error });
    assert.doesNotMatch(JSON.stringify(result), /provider-secret-body|v2:call-control-a|claim-token-a|supa\.example/i);
  }
  const unreadable = await recordTelnyxWakeReceipt(BASE_INPUT, {
    ...DEPS, fetchImpl: async () => ({ ok: true, status: 200, json: async () => { throw new Error("raw-provider-secret"); } }),
  });
  assert.deepEqual(unreadable, { ok: false, matched: 0, error: "unreadable_response" });
  const thrown = await recordTelnyxWakeReceipt(BASE_INPUT, {
    ...DEPS, fetchImpl: async () => { throw new Error("raw-network-secret"); },
  });
  assert.deepEqual(thrown, { ok: false, matched: 0, error: "network_error" });
  assert.doesNotMatch(JSON.stringify(thrown), /raw-network-secret/i);
});

test("the client has no logging side effect on a rejected provider response", async () => {
  const originalError = console.error;
  let logs = 0;
  console.error = () => { logs += 1; };
  try {
    await recordTelnyxWakeReceipt(BASE_INPUT, {
      ...DEPS, fetchImpl: async () => response(503, { error: "secret" }),
    });
  } finally {
    console.error = originalError;
  }
  assert.equal(logs, 0);
});
