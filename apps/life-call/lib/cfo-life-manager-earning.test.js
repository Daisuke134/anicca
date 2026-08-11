"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");
const { normalizeLifeManagerEarningReceipt } = require("./cfo-life-manager-earning.js");

const REF = "10000000-0000-4000-8000-000000000001", TX = `0x${"a".repeat(64)}`;
function row(overrides = {}) { return { public_ref: REF, entry_key: "taskmarket:SECRET_ENTRY", wallet_address: "0xSECRET_WALLET", kind: "financial_external_income", amount_minor: null, amount_atomic: "2500000", amount_decimals: 6, currency: "USD", occurred_at: "2026-08-11T10:02:03+09:00", tx_hash: TX, source: "taskmarket_work", meta: { finalized: true, external: true, payer: "SECRET_PAYER", prompt: "SECRET_PROMPT", metadata: "SECRET_METADATA" }, secret_sentinel: "SECRET_SENTINEL", ...overrides }; }
const forbidden = /SECRET_|0xSECRET_WALLET|taskmarket:SECRET_ENTRY|transaction|metadata/i;

test("normalizes finalized TaskMarket earnings to a closed frozen receipt", () => {
  const input = row(), before = structuredClone(input), result = normalizeLifeManagerEarningReceipt(input);
  assert.deepEqual(result, { schema_version: 1, financial_unit_id: "life_manager_saas", source_ledger: "lm_agent_earnings", source_event_id: `lm_agent_earnings:${REF}`, channel_id: "taskmarket_life_manager", occurred_at: "2026-08-11T01:02:03.000Z", amount: { atomic: "2500000", decimals: 6, currency: "USD" }, landed_cash_status: "confirmed_agent_wallet", evidence_status: "onchain_finalized_external_settlement" });
  assert.deepEqual(input, before); assert.equal(Object.isFrozen(result), true); assert.equal(Object.isFrozen(result.amount), true); assert.deepEqual(Object.keys(result).sort(), ["amount", "channel_id", "evidence_status", "financial_unit_id", "landed_cash_status", "occurred_at", "schema_version", "source_event_id", "source_ledger"]); assert.doesNotMatch(JSON.stringify(result), forbidden);
});

test("maps uGig and normalizes a safe integer amount", () => {
  const result = normalizeLifeManagerEarningReceipt(row({ public_ref: "20000000-0000-4000-8000-000000000002", source: "ugig_work", amount_atomic: 1250000, occurred_at: "2026-08-11T01:02:03Z", tx_hash: `5${"b".repeat(86)}Z` }));
  assert.equal(result.channel_id, "ugig_life_manager"); assert.deepEqual(result.amount, { atomic: "1250000", decimals: 6, currency: "USD" }); assert.equal(result.occurred_at, "2026-08-11T01:02:03.000Z");
});

test("rejects money-truth and privacy failures with fixed redacted errors", () => {
  const invalid = [["other source", { source: "x402_services" }], ["wrong kind", { kind: "financial_realized_loss" }], ["not finalized", { meta: { finalized: false, external: true } }], ["not external", { meta: { finalized: true, external: false } }], ["zero", { amount_atomic: "0" }], ["unsafe number", { amount_atomic: Number.MAX_SAFE_INTEGER + 1 }], ["too large string", { amount_atomic: "90071992547409910001" }], ["decimals too high", { amount_decimals: 7 }], ["minor plus atomic", { amount_minor: 1 }], ["bad ref", { public_ref: "not-a-uuid" }], ["bad receipt", { tx_hash: "not-a-chain-receipt" }]];
  for (const [name, mutation] of invalid) { const input = row(mutation); assert.throws(() => normalizeLifeManagerEarningReceipt(input), error => /^cfo_life_manager_earning_invalid:[a-z_]+$/.test(error.message) && !forbidden.test(JSON.stringify(error)), name); }
});

test("redacts unexpected proxy failures", () => {
  const secondary = new Proxy({}, { getPrototypeOf() { throw new Error("SECONDARY_SECRET"); } });
  const input = new Proxy(row(), { getPrototypeOf() { throw secondary; } });
  assert.throws(() => normalizeLifeManagerEarningReceipt(input), error => error.message === "cfo_life_manager_earning_invalid:invalid_input" && !/SECRET_SENTINEL|SECONDARY_SECRET/.test(error.message));
});
