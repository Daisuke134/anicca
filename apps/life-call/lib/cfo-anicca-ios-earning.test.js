"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");
const { normalizeAniccaIosRevenueCatEvent } = require("./cfo-anicca-ios-earning.js");
assert.equal(typeof normalizeAniccaIosRevenueCatEvent, "function");

const initial = { provider_event_id: "evt_initial_123", event_type: "INITIAL_PURCHASE", environment: "PRODUCTION", store: "APP_STORE", product_id: "ai.anicca.app.ios.monthly.b", price_decimal: "500", currency: "JPY", purchased_at_ms: "1786410123000" };
const renewal = { provider_event_id: "evt_renewal_456", event_type: "RENEWAL", environment: "PRODUCTION", store: "APP_STORE", product_id: "ai.anicca.app.ios.monthly", price_decimal: "4.99", currency: "GBP", purchased_at_ms: "1786507506000" };
const invalidError = error => error.message === "cfo_anicca_ios_earning_invalid:invalid_input" && !/SECRET|provider|product|customer|transaction|subscriber/i.test(error.message);

test("normalizes positive production App Store receipts without leaking provider data", () => {
  const before = structuredClone(initial), renewalBefore = structuredClone(renewal), result = normalizeAniccaIosRevenueCatEvent(initial);
  assert.deepEqual(result, { schema_version: 1, financial_unit_id: "anicca_ios", source_ledger: "revenuecat_subscription_events", source_event_id: "revenuecat_subscription:3ee7ac0b2376a0d43980bd2d", channel_id: "apple_app_store_anicca", occurred_at: "2026-08-11T01:02:03.000Z", receipt_kind: "initial_purchase", amount: { decimal: "500", currency: "JPY" }, recognition_status: "provider_reported_gross", cash_status: "unknown", apple_payout_status: "unavailable", refund_coverage: "unknown", evidence_status: "provider_reported" });
  const next = normalizeAniccaIosRevenueCatEvent(renewal);
  assert.deepEqual(next, { ...result, source_event_id: "revenuecat_subscription:4c24eff4d12d76ecbe028ef3", occurred_at: "2026-08-12T04:05:06.000Z", receipt_kind: "renewal", amount: { decimal: "4.99", currency: "GBP" } });
  assert.deepEqual(initial, before); assert.deepEqual(renewal, renewalBefore); assert.ok(Object.isFrozen(result) && Object.isFrozen(result.amount) && Object.isFrozen(next) && Object.isFrozen(next.amount));
  assert.equal(normalizeAniccaIosRevenueCatEvent(initial).source_event_id, result.source_event_id); assert.deepEqual(Object.keys(result).sort(), ["amount", "apple_payout_status", "cash_status", "channel_id", "evidence_status", "financial_unit_id", "occurred_at", "receipt_kind", "recognition_status", "refund_coverage", "schema_version", "source_event_id", "source_ledger"]); assert.doesNotMatch(JSON.stringify(result), /evt_initial_123|monthly\.b|SECRET/);
});

test("ignores known non-revenue observations", () => {
  for (const change of [{ price_decimal: "0" }, { price_decimal: "0.0" }, { environment: "SANDBOX" }, { store: "TEST_STORE" }, { event_type: "CANCELLATION" }, { product_id: "other.product" }]) assert.equal(normalizeAniccaIosRevenueCatEvent({ ...initial, ...change }), null);
});

test("fails closed for money, time, identity, shape, and hostile reflection inputs", () => {
  const cases = [["negative", { price_decimal: "-1" }], ["exponent", { price_decimal: "1e2" }], ["numeric", { price_decimal: 1 }], ["overlong", { price_decimal: "1".repeat(33) }], ["lowercase currency", { currency: "jpy" }], ["bad currency", { currency: "JP" }], ["unsafe time", { purchased_at_ms: "9007199254740992" }], ["noncanonical time", { purchased_at_ms: "01786410123000" }], ["missing", Object.fromEntries(Object.entries(initial).slice(0, 7))], ["extra", { ...initial, secret_sentinel: "SECRET_SENTINEL" }], ["bad provider", { provider_event_id: "evt/secret" }]];
  const nonPlain = Object.assign(Object.create(null), initial), accessor = { ...initial }; Object.defineProperty(accessor, "price_decimal", { enumerable: true, get() { throw Error("SECRET_SENTINEL"); } });
  cases.push(["non-plain", nonPlain], ["accessor", accessor], ["symbol", { ...initial, [Symbol("SECRET")]: "SECRET" }], ["transparent proxy", new Proxy(initial, {})], ["proxy", new Proxy(initial, { getPrototypeOf() { throw Error("SECRET_PROXY"); } })]);
  const logs = [], original = [console.log, console.warn, console.error]; console.log = console.warn = console.error = (...args) => logs.push(args);
  try { for (const [name, input] of cases) assert.throws(() => normalizeAniccaIosRevenueCatEvent(input), invalidError, name); } finally { [console.log, console.warn, console.error] = original; }
  assert.deepEqual(logs, []); assert.doesNotMatch(JSON.stringify(normalizeAniccaIosRevenueCatEvent(initial)), /SECRET_SENTINEL|provider_event_id|product_id/);
});
