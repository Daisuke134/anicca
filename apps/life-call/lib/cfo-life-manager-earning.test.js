"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");
const { normalizeLifeManagerEarningReceipt, collectLifeManagerStripeReceipts } = require("./cfo-life-manager-earning.js");
assert.equal(typeof collectLifeManagerStripeReceipts, "function");

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

test("collects paginated live Stripe gross receipts without private fields", async () => {
  const calls = [], link = { id: "plink", url: "https://buy.stripe.com/lm", livemode: true, active: true };
  const pages = {
    "payment_links": [{ data: [{ id: "other", url: "https://buy.stripe.com/other", livemode: true, active: true }], has_more: true }],
    "payment_links&starting_after=": [{ data: [link], has_more: false }]
  };
  const sessions = [{ id: "s1", payment_link: "plink", livemode: true, payment_status: "paid", status: "complete", created: 1775821323, amount_total: 2000, currency: "usd", customer_email: "SECRET" }, { id: "s0", payment_link: "plink", livemode: true, payment_status: "paid", status: "complete", created: 1775821324, amount_total: 0, currency: "usd" }, { id: "su", payment_link: "plink", livemode: true, payment_status: "unpaid", status: "open", amount_total: null, currency: null }, { id: "sn", payment_link: "plink", livemode: true, payment_status: "no_payment_required", status: "complete", amount_total: null, currency: null }];
  const fetchImpl = async (url, init) => { calls.push([url, init]); const u = new URL(url); if (u.pathname.endsWith("payment_links")) return { ok: true, json: async () => u.searchParams.has("starting_after") ? { data: [link], has_more: false } : pages.payment_links[0] }; return { ok: true, json: async () => u.searchParams.has("starting_after") ? { data: sessions.slice(1), has_more: false } : { data: [sessions[0]], has_more: true } }; };
  const result = await collectLifeManagerStripeReceipts({ stripeKey: "sk_live_SECRET", paymentLinkUrl: link.url, fetchImpl });
  assert.deepEqual(result, { schema_version: 1, financial_unit_id: "life_manager_saas", channel_id: "stripe_life_manager", status: "covered", receipt_count: 1, zero_value_paid_count: 1, reversal_coverage_status: "unknown", receipts: [{ source_event_id: "stripe_checkout:s1", occurred_at: "2026-04-10T11:42:03.000Z", amount: { minor: "2000", currency: "USD" }, recognition_status: "gross_inflow_unreconciled", landed_cash_status: "confirmed_stripe_balance", bank_landed_status: "unknown", evidence_status: "provider_reported" }], evidence_status: "provider_reported" }); assert.deepEqual(calls.map(([url]) => url), ["https://api.stripe.com/v1/payment_links?limit=100", "https://api.stripe.com/v1/payment_links?limit=100&starting_after=other", "https://api.stripe.com/v1/checkout/sessions?limit=100&payment_link=plink", "https://api.stripe.com/v1/checkout/sessions?limit=100&payment_link=plink&starting_after=s1"]); assert.equal(calls[0][1].headers.Authorization, "Bearer sk_live_SECRET"); assert.doesNotMatch(JSON.stringify(result), /SECRET|customer_email/); assert.ok(Object.isFrozen(result)); assert.ok(Object.isFrozen(result.receipts)); assert.ok(Object.isFrozen(result.receipts[0].amount));
});

test("rejects Stripe failure table with redacted fixed errors and stops", async () => {
  const base = { id: "s1", payment_link: "plink", livemode: true, payment_status: "paid", status: "complete", created: 1, amount_total: 1, currency: "usd" }, link = { id: "plink", url: "https://buy.stripe.com/lm", livemode: true, active: true };
  const cases = [["duplicate ID", () => ({ data: [base, base], has_more: false })], ["negative amount", () => ({ data: [{ ...base, amount_total: -1 }], has_more: false })], ["unsafe amount", () => ({ data: [{ ...base, amount_total: Number.MAX_SAFE_INTEGER + 1 }], has_more: false })], ["paid incomplete", () => ({ data: [{ ...base, status: "open" }], has_more: false })], ["wrong link", () => ({ data: [{ ...base, payment_link: "other" }], has_more: false })], ["test mode", () => ({ data: [{ ...base, livemode: false }], has_more: false })], ["malformed page", () => ({ data: null, has_more: false })], ["JSON throw", () => { throw Error("stripe_SECRET"); }], ["network throw", () => { throw Error("stripe_SECRET"); }], ["missing canonical link", () => ({ data: [{ ...link, url: "https://buy.stripe.com/other" }], has_more: false })], ["101-page feed", () => ({ data: [{ id: "x" }], has_more: true })]];
  for (const [name, response] of cases) { let calls = 0; const fetchImpl = async url => { calls++; if (name === "network throw") throw Error("stripe_SECRET"); if (name === "JSON throw") return { ok: true, json: response }; const session = new URL(url).pathname.endsWith("sessions"); const payload = name === "101-page feed" ? { data: [{ id: `x${calls}` }], has_more: true } : session ? response() : name === "missing canonical link" ? response() : { data: [link], has_more: false }; return { ok: true, json: async () => payload }; }; const opts = { stripeKey: "sk_live_x", paymentLinkUrl: link.url, fetchImpl }; await assert.rejects(collectLifeManagerStripeReceipts(opts), error => /^cfo_life_manager_earning_invalid:stripe_/.test(error.message) && !/SECRET/.test(error.message), name); assert.equal(calls, name === "test mode" || name === "missing canonical link" || name === "JSON throw" || name === "network throw" ? (name === "test mode" ? 2 : 1) : name === "101-page feed" ? 100 : 2, name); }
});
