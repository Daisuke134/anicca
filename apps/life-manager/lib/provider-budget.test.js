"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { evaluateProviderBudget, authorizeProviderOperation } = require("./provider-budget.js");

test("migration provides a unique atomic daily claim identity", () => {
  const sql = fs.readFileSync(path.join(__dirname, "../migrations/2026-08-08-lm-provider-cost.sql"), "utf8").toLowerCase();
  assert.match(sql, /lm_provider_budget_claims/);
  assert.match(sql, /primary key \(uid, budget_day, request_id\)/);
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
