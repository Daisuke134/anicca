"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { evaluateProviderBudget, aggregateCostRows, readDailySpend, authorizeProviderOperation, settleProviderVoice } = require("./provider-budget.js");

test("migration provides a unique atomic daily claim identity", () => {
  const sql = fs.readFileSync(path.join(__dirname, "../migrations/2026-08-08-lm-provider-cost.sql"), "utf8").toLowerCase();
  assert.match(sql, /lm_provider_budget_claims/);
  assert.match(sql, /primary key \(uid, budget_day, request_id\)/);
  assert.match(sql, /create table if not exists public\.lm_provider_voice_buckets/);
  assert.match(sql, /create or replace function public\.lm_claim_provider_budget/);
  assert.match(sql, /for update/);
  assert.match(sql, /reserved_usd/);
  assert.match(sql, /settled_usd/);
  assert.match(sql, /lm_settle_provider_voice/);
});

test("security-definer budget RPCs are callable only by service_role", () => {
  const sql = fs.readFileSync(path.join(__dirname, "../migrations/2026-08-08-lm-provider-cost.sql"), "utf8").toLowerCase();
  assert.match(sql, /revoke all on function public\.lm_claim_provider_budget\([^)]*\)\s+from public, anon, authenticated/);
  assert.match(sql, /grant execute on function public\.lm_claim_provider_budget\([^)]*\)\s+to service_role/);
  assert.match(sql, /revoke all on function public\.lm_settle_provider_voice\([^)]*\)\s+from public, anon, authenticated/);
  assert.match(sql, /grant execute on function public\.lm_settle_provider_voice\([^)]*\)\s+to service_role/);
});

test("the transactional claim contract includes the daily cap and settled ledger", () => {
  const sql = fs.readFileSync(path.join(__dirname, "../migrations/2026-08-08-lm-provider-cost.sql"), "utf8").toLowerCase();
  assert.match(sql, /p_daily_cap\s+numeric/);
  assert.match(sql, /from lm_api_cost/);
  assert.match(sql, /actual_billed_usd/);
  assert.match(sql, /estimated_usd/);
  assert.match(sql, /lm_provider_budget_claims/);
  assert.match(sql, /for update/);
});

test("provider claims use conflict replay semantics for the original receipt", () => {
  const sql = fs.readFileSync(path.join(__dirname, "../migrations/2026-08-08-lm-provider-cost.sql"), "utf8").toLowerCase();
  assert.match(sql, /insert into lm_provider_budget_claims[\s\S]*on conflict \(uid, budget_day, request_id\) do nothing/);
  assert.match(sql, /returning request_id/);
  assert.match(sql, /duplicate/);
});

test("daily provider budget boundaries are normal, warning, degraded, then stopped", () => {
  assert.equal(evaluateProviderBudget({ measuredUsd: 0.49, estimatedUsd: 0 }).state, "normal");
  assert.equal(evaluateProviderBudget({ measuredUsd: 0.50, estimatedUsd: 0 }).state, "warning");
  assert.equal(evaluateProviderBudget({ measuredUsd: 0.99, estimatedUsd: 0.01 }).state, "degraded");
  assert.equal(evaluateProviderBudget({ measuredUsd: 2, estimatedUsd: 0 }).state, "stopped");
});

test("unknown billing is visible in reasons and never contributes numeric zero as measured spend", () => {
  const budget = evaluateProviderBudget({ measuredUsd: null, estimatedUsd: null, unknownCount: 2 });
  assert.equal(budget.totalUsd, 0);
  assert.equal(budget.state, "normal");
  assert.ok(budget.reasons.some((reason) => /unknown/i.test(reason)));
});

test("row aggregation keeps unknown null estimates out of numeric spend", () => {
  const result = aggregateCostRows([
    { provider: "google", operation: "geocoding", actual_status: "unknown", actual_billed_usd: null, estimated_usd: null, est_usd: null },
    { provider: "google", operation: "routes", actual_status: "unknown", actual_billed_usd: null, estimated_usd: 0.01 },
    { provider: "telnyx", operation: "call_cdr", actual_status: "known", actual_billed_usd: 0.03, estimated_usd: null },
  ]);
  assert.equal(result.unknownCount, 1);
  assert.equal(result.estimatedUsd, 0.01);
  assert.equal(result.measuredUsd, 0.03);
});

test("voice-only aggregation excludes non-voice provider rows", () => {
  const result = aggregateCostRows([
    { provider: "google", operation: "routes", actual_status: "unknown", estimated_usd: 0.5 },
    { provider: "telnyx", operation: "call_cdr", actual_status: "known", actual_billed_usd: 0.03 },
  ], { voiceOnly: true });
  assert.equal(result.measuredUsd, 0.03);
  assert.equal(result.estimatedUsd, 0);
});

test("default voice spend reader requests only voice operations", async () => {
  let requested;
  await readDailySpend({ uid: "u1", voiceOnly: true }, {
    supaUrl: "https://db.example", supaKey: "service",
    fetchImpl: async (url) => { requested = String(url); return { ok: true, json: async () => [] }; },
  });
  assert.match(requested, /provider\.eq\.telnyx/);
  assert.match(requested, /provider\.eq\.gemini/);
  assert.match(requested, /operation\.ilike/);
});

test("paid fallback is disabled at one dollar while essential work remains available", async () => {
  const deps = { readDailySpend: async () => ({ measuredUsd: 1, estimatedUsd: 0, unknownCount: 0 }) };
  const fallback = await authorizeProviderOperation({ uid: "u1", provider: "google", operation: "fallback", essential: false }, deps);
  const essential = await authorizeProviderOperation({ uid: "u1", provider: "transit", operation: "plan", essential: true }, deps);
  assert.equal(fallback.allowed, false);
  assert.equal(fallback.reason, "paid_fallback_disabled");
  assert.equal(essential.allowed, true);
});

test("nonessential provider work stops at two dollars", async () => {
  const result = await authorizeProviderOperation({ uid: "u1", provider: "composio", operation: "refresh", essential: false }, {
    readDailySpend: async () => ({ measuredUsd: 2, estimatedUsd: 0, unknownCount: 0 }),
  });
  assert.equal(result.allowed, false);
  assert.equal(result.reason, "budget_stopped");
});

test("cached reads are always allowed even when spend lookup fails", async () => {
  const result = await authorizeProviderOperation({ uid: "u1", provider: "google", operation: "routes", cacheHit: true }, {
    readDailySpend: async () => { throw new Error("ledger unavailable"); },
  });
  assert.equal(result.allowed, true);
  assert.equal(result.reason, "cache_hit");
});

test("voice caps are enforced independently for one user and globally", async () => {
  const userBlocked = await authorizeProviderOperation({ uid: "u1", provider: "telnyx", operation: "call_session", essential: true, projectedUsd: 0.2 }, {
    readDailySpend: async () => ({ measuredUsd: 0, estimatedUsd: 0, unknownCount: 0 }),
    readVoiceSpend: async ({ scope }) => scope === "user"
      ? { measuredUsd: 0.9, estimatedUsd: 0, unknownCount: 0 }
      : { measuredUsd: 0, estimatedUsd: 0, unknownCount: 0 },
    thresholds: { voiceUserCapUsd: 1, voiceGlobalCapUsd: 5 },
  });
  assert.equal(userBlocked.allowed, false);
  assert.equal(userBlocked.reason, "voice_user_cap");

  const globalBlocked = await authorizeProviderOperation({ uid: "u1", provider: "gemini", operation: "session", essential: true, projectedUsd: 0.2 }, {
    readDailySpend: async () => ({ measuredUsd: 0, estimatedUsd: 0, unknownCount: 0 }),
    readVoiceSpend: async ({ scope }) => scope === "user"
      ? { measuredUsd: 0, estimatedUsd: 0, unknownCount: 0 }
      : { measuredUsd: 4.9, estimatedUsd: 0, unknownCount: 0 },
    thresholds: { voiceUserCapUsd: 5, voiceGlobalCapUsd: 5 },
  });
  assert.equal(globalBlocked.allowed, false);
  assert.equal(globalBlocked.reason, "voice_global_cap");
});

test("a failed budget read fails closed for non-cache work", async () => {
  const result = await authorizeProviderOperation({ uid: "u1", provider: "google", operation: "routes", essential: false }, {
    readDailySpend: async () => { throw new Error("ledger unavailable"); },
  });
  assert.equal(result.allowed, false);
  assert.equal(result.reason, "budget_unavailable");
});

test("production authorization atomically claims a nonzero projection through the Postgres RPC", async () => {
  const calls = [];
  const result = await authorizeProviderOperation({
    uid: "u1", provider: "telnyx", operation: "call_session", essential: true,
    requestId: "call-attempt-1", projectedUsd: 0,
  }, {
    supaUrl: "https://db.example", supaKey: "service",
    readDailySpend: async () => ({ measuredUsd: 0, estimatedUsd: 0, unknownCount: 0 }),
    readVoiceSpend: async () => ({ measuredUsd: 0, estimatedUsd: 0, unknownCount: 0 }),
    fetchImpl: async (url, init = {}) => {
      calls.push({ url: String(url), init });
      if (String(url).includes("/rpc/lm_claim_provider_budget")) {
        return { ok: true, status: 200, json: async () => ({ allowed: true, request_id: "call-attempt-1" }) };
      }
      return { ok: true, status: 200, json: async () => [] };
    },
  });
  assert.equal(result.allowed, true);
  const rpc = calls.find((call) => call.url.includes("/rpc/lm_claim_provider_budget"));
  assert.ok(rpc, "the production path must use the transactional RPC");
  const body = JSON.parse(rpc.init.body);
  assert.equal(body.p_request_id, "call-attempt-1");
  assert.ok(body.p_projected_usd > 0, "voice claims must never reserve a zero projection");
  assert.equal(body.p_is_voice, true);
  assert.equal(body.p_daily_cap, 2);
});

test("cached reads bypass both budget reads and the atomic claim RPC", async () => {
  let calls = 0;
  const result = await authorizeProviderOperation({ uid: "u1", provider: "google", operation: "routes", cacheHit: true }, {
    supaUrl: "https://db.example", supaKey: "service", fetchImpl: async () => { calls += 1; return { ok: true }; },
    readDailySpend: async () => { calls += 1; return { measuredUsd: 99, estimatedUsd: 0, unknownCount: 0 }; },
  });
  assert.equal(result.allowed, true);
  assert.equal(calls, 0);
});

test("known Telnyx CDR settlement uses the transactional voice settlement RPC", async () => {
  const calls = [];
  const ok = await settleProviderVoice({ uid: "u1", requestId: "cdr-1", actualBilledUsd: 0.037, reservationRequestId: "call-1" }, {
    supaUrl: "https://db.example", supaKey: "service",
    fetchImpl: async (url, init = {}) => {
      calls.push({ url: String(url), init });
      return { ok: true, status: 200, json: async () => ({ settled: true }) };
    },
  });
  assert.equal(ok, true);
  const body = JSON.parse(calls[0].init.body);
  assert.equal(body.p_request_id, "cdr-1");
  assert.equal(body.p_actual_usd, 0.037);
  assert.equal(body.p_reservation_request_id, "call-1");
});

test("a provider claim replay after a conflict is an allowed duplicate receipt", async () => {
  const result = await authorizeProviderOperation({
    uid: "u1", provider: "google", operation: "routes", essential: false,
    requestId: "route-replay", projectedUsd: 0.01,
  }, {
    supaUrl: "https://db.example", supaKey: "service",
    readDailySpend: async () => ({ measuredUsd: 0, estimatedUsd: 0, unknownCount: 0 }),
    fetchImpl: async (url) => String(url).includes("lm_claim_provider_budget")
      ? { ok: false, status: 409, json: async () => ({ code: "23505", message: "duplicate key" }) }
      : { ok: true, status: 200, json: async () => [] },
  });
  assert.equal(result.allowed, true);
  assert.equal(result.reason, "budget_claim_duplicate");
});
