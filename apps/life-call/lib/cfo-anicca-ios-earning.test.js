"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");
const { normalizeAniccaIosRevenueCatEvent, normalizeAniccaIosAppleFinanceRow } = require("./cfo-anicca-ios-earning.js");
assert.equal(typeof normalizeAniccaIosRevenueCatEvent, "function");
assert.equal(typeof normalizeAniccaIosAppleFinanceRow, "function");

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

const appleSale = {
  fiscal_month: "2026-10", row_ordinal: 1, transaction_date: "07/06/2026",
  settlement_date: "07/06/2026", apple_identifier: "6769264298",
  sku: "ai.anicca.app.ios.monthly.b", quantity: "1", partner_share_decimal: "425",
  extended_partner_share_decimal: "425", currency: "JPY", sale_or_return: "S"
};
const appleReturn = {
  fiscal_month: "2026-07", row_ordinal: 7, transaction_date: "04/01/2026",
  settlement_date: "04/02/2026", apple_identifier: "6755320744",
  sku: "ai.anicca.app.ios.annual", quantity: "-1", partner_share_decimal: "17.39",
  extended_partner_share_decimal: "-17.39", currency: "GBP", sale_or_return: "R"
};
const appleError = error => error.message === "cfo_anicca_ios_earning_invalid:apple_finance_row" && !/SECRET|6769264298|6755320744|monthly\.b|annual|vendor|customer/i.test(error.message);

test("normalizes signed Apple Finance rows without leaking raw identity", () => {
  const before = structuredClone(appleSale), returnBefore = structuredClone(appleReturn), sale = normalizeAniccaIosAppleFinanceRow(appleSale), refund = normalizeAniccaIosAppleFinanceRow(appleReturn);
  assert.deepEqual(sale, { schema_version: 1, financial_unit_id: "anicca_ios", source_ledger: "apple_finance_detail", source_event_id: "apple_finance_detail:0cb21fcae317766dd43dfb5c", channel_id: "apple_app_store_anicca", fiscal_month: "2026-10", transaction_date: "2026-07-06", settlement_date: "2026-07-06", receipt_kind: "sale", quantity: "1", unit_partner_share_decimal: "425", amount: { decimal: "425", currency: "JPY" }, recognition_status: "apple_finance_reported_partner_share", payout_status: "unknown", bank_landed_status: "unknown", evidence_status: "apple_finance_detail" });
  assert.deepEqual(refund, { ...sale, source_event_id: "apple_finance_detail:45b5a38ea1dfaebea1498b70", fiscal_month: "2026-07", transaction_date: "2026-04-01", settlement_date: "2026-04-02", receipt_kind: "return", quantity: "-1", unit_partner_share_decimal: "17.39", amount: { decimal: "-17.39", currency: "GBP" } });
  assert.deepEqual(appleSale, before); assert.deepEqual(appleReturn, returnBefore); assert.ok(Object.isFrozen(sale) && Object.isFrozen(sale.amount) && Object.isFrozen(refund) && Object.isFrozen(refund.amount)); assert.equal(normalizeAniccaIosAppleFinanceRow(appleSale).source_event_id, sale.source_event_id); assert.deepEqual(Object.keys(sale).sort(), ["amount", "bank_landed_status", "channel_id", "evidence_status", "financial_unit_id", "fiscal_month", "payout_status", "quantity", "receipt_kind", "recognition_status", "schema_version", "settlement_date", "source_event_id", "source_ledger", "transaction_date", "unit_partner_share_decimal"]); assert.doesNotMatch(JSON.stringify(sale), /6769264298|monthly\.b|SECRET/);
});

test("ignores wholly unregistered Apple identity and fails closed otherwise", () => {
  assert.equal(normalizeAniccaIosAppleFinanceRow({ ...appleSale, apple_identifier: "1111111111", sku: "other.sku" }), null);
  const cases = [{ apple_identifier: "6755320744" }, { sku: "ai.anicca.app.ios.annual" }, { apple_identifier: "6755320627", sku: "ai.anicca.app.ios.annual" }, { quantity: "0" }, { quantity: "-0" }, { quantity: "01" }, { quantity: "1".repeat(17) }, { quantity: "-1", extended_partner_share_decimal: "-425" }, { extended_partner_share_decimal: "0" }, { extended_partner_share_decimal: "-425" }, { extended_partner_share_decimal: "01" }, { extended_partner_share_decimal: "1".repeat(17) }, { extended_partner_share_decimal: "1.123456789" }, { extended_partner_share_decimal: "1e2" }, { partner_share_decimal: "0" }, { partner_share_decimal: "-1" }, { partner_share_decimal: "01" }, { partner_share_decimal: "1".repeat(17) }, { partner_share_decimal: "1.123456789" }, { partner_share_decimal: "1e2" }, { partner_share_decimal: "424" }, { fiscal_month: "2026-13" }, { transaction_date: "02/29/2025" }, { transaction_date: "7/06/2026" }, { transaction_date: "07/6/2026" }, { settlement_date: "07/05/2026" }, { row_ordinal: Number.MAX_SAFE_INTEGER + 1 }, { row_ordinal: Number.MAX_SAFE_INTEGER }, { row_ordinal: 1000001 }, { sale_or_return: "X" }, { currency: "JPY ", extra: "SECRET" }];
  const failure = (input, name) => { const before = structuredClone(input); assert.throws(() => normalizeAniccaIosAppleFinanceRow(input), appleError, name); assert.deepEqual(input, before, name); };
  const accessor = { ...appleSale }; Object.defineProperty(accessor, "sku", { enumerable: true, get() { throw Error("SECRET"); } });
  const logs = [], original = [console.log, console.warn, console.error]; console.log = console.warn = console.error = (...args) => logs.push(args);
  try {
    for (const [index, change] of cases.entries()) failure({ ...appleSale, ...change }, `case_${index}`);
    const missing = { ...appleSale }; delete missing.sku; failure(missing, "missing");
    failure({ ...appleReturn, extended_partner_share_decimal: "17.39" }, "return wrong sign");
    for (const input of [Object.assign(Object.create(null), appleSale), { ...appleSale, [Symbol("SECRET")]: "SECRET" }, new Proxy(appleSale, {}), new Proxy(appleSale, { getPrototypeOf() { throw Error("SECRET_PROXY"); } }), accessor]) assert.throws(() => normalizeAniccaIosAppleFinanceRow(input), appleError);
  } finally { [console.log, console.warn, console.error] = original; }
  assert.deepEqual(logs, []);
});
