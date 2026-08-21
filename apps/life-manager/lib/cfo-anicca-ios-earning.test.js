"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");
const {
  normalizeAniccaIosRevenueCatEvent,
  normalizeAniccaIosAppleFinanceRow,
  parseAniccaIosAppleFinanceReport,
  composeAniccaIosBusinessFact,
} = require("./cfo-anicca-ios-earning.js");

const REPORT_HEADER = [
  "Start Date", "End Date", "Transaction Date", "Settlement Date", "Apple Identifier", "SKU", "Quantity", "Partner Share", "Extended Partner Share", "Partner Share Currency", "Sale or Return", "Provider Note",
];

function report({ footerRows = 3, header = REPORT_HEADER, rows = null, metadata = ["fiscal_month\t2026-10", "report_type\tFINANCE_DETAIL", "report_status\tCOMPLETE"] } = {}) {
  const data = rows || [
    ["07/01/2026", "07/31/2026", "07/06/2026", "07/06/2026", "6769264298", "ai.anicca.app.ios.monthly.b", "1", "425", "425", "JPY", "S", "safe"],
    ["07/01/2026", "07/31/2026", "07/07/2026", "07/07/2026", "1234567890", "other.sku", "1", "1", "1", "USD", "S", "SECRET_PROVIDER_ID"],
    ["07/01/2026", "07/31/2026", "04/01/2026", "04/02/2026", "6755320744", "ai.anicca.app.ios.annual", "-1", "17.39", "-17.39", "GBP", "R", "safe"],
  ];
  return [...metadata, header.join("\t"), ...data.map(row => row.join("\t")), `Total_Rows\t${footerRows}`, "Total_Amount\t409.61", "Total_Units\t1"].join("\n");
}

const invalidReport = error => error.message === "cfo_anicca_ios_earning_invalid:finance_report" && !/SECRET|provider|1234567890|other\.sku/i.test(error.message);

test("parses complete Apple Finance TSV and ignores another app", () => {
  const raw = report();
  const result = parseAniccaIosAppleFinanceReport(raw, { revenueCatReceipts: null });
  assert.deepEqual(result, {
    schema_version: 1,
    financial_unit_id: "anicca_ios",
    source_ledger: "apple_finance_detail",
    fiscal_month: "2026-10",
    report_status: "COMPLETE",
    boundary: { metadata_line_count: 3, header_verified: true, data_row_count: 3, footer_line_count: 3, footer_row_count: 3 },
    apple_partner_share_totals: [
      { currency: "GBP", row_count: 1, amount_decimal: "-17.39" },
      { currency: "JPY", row_count: 1, amount_decimal: "425" },
    ],
    revenuecat_coverage_status: "unavailable",
    revenuecat_gross_totals: null,
    reconciliation_status: "revenuecat_unavailable",
    payout_status: "unknown",
    bank_landed_status: "unknown",
    evidence_status: "apple_finance_detail_complete",
  });
  assert.ok(Object.isFrozen(result));
  assert.ok(Object.isFrozen(result.boundary));
  assert.ok(Object.isFrozen(result.apple_partner_share_totals));
  assert.ok(Object.isFrozen(result.apple_partner_share_totals[0]));
  assert.doesNotMatch(JSON.stringify(result), /SECRET|1234567890|other\.sku/);
});

test("distinguishes unavailable, observed-empty, and supplied RevenueCat coverage", () => {
  const raw = report();
  const initial = normalizeAniccaIosRevenueCatEvent({ provider_event_id: "evt_initial_123", event_type: "INITIAL_PURCHASE", environment: "PRODUCTION", store: "APP_STORE", product_id: "ai.anicca.app.ios.monthly.b", price_decimal: "500", currency: "JPY", purchased_at_ms: "1786410123000" });
  const omitted = parseAniccaIosAppleFinanceReport(raw, {});
  assert.equal(omitted.revenuecat_coverage_status, "unavailable");
  assert.equal(omitted.revenuecat_gross_totals, null);
  assert.equal(omitted.reconciliation_status, "revenuecat_unavailable");
  const empty = parseAniccaIosAppleFinanceReport(raw, { revenueCatReceipts: [] });
  assert.deepEqual(empty.revenuecat_gross_totals, []);
  assert.equal(empty.revenuecat_coverage_status, "observed_empty");
  assert.equal(empty.reconciliation_status, "gross_vs_partner_share_separate");
  const supplied = parseAniccaIosAppleFinanceReport(raw, { revenueCatReceipts: [initial] });
  assert.deepEqual(supplied.revenuecat_gross_totals, [{ currency: "JPY", receipt_count: 1, amount_decimal: "500" }]);
  assert.equal(supplied.revenuecat_coverage_status, "provider_reported");
  assert.equal(supplied.reconciliation_status, "gross_vs_partner_share_separate");
  assert.doesNotMatch(JSON.stringify(supplied), /evt_initial_123|monthly\.b/);
});

test("normalizers remain pure and preserve fixed privacy-safe errors", () => {
  const row = { fiscal_month: "2026-10", row_ordinal: 1, transaction_date: "07/06/2026", settlement_date: "07/06/2026", apple_identifier: "6769264298", sku: "ai.anicca.app.ios.monthly.b", quantity: "1", partner_share_decimal: "425", extended_partner_share_decimal: "425", currency: "JPY", sale_or_return: "S" };
  const before = structuredClone(row);
  const normalized = normalizeAniccaIosAppleFinanceRow(row);
  assert.equal(normalized.amount.decimal, "425");
  assert.deepEqual(row, before);
  assert.throws(() => normalizeAniccaIosAppleFinanceRow({ ...row, sku: "SECRET_PROVIDER_SKU" }), error => error.message === "cfo_anicca_ios_earning_invalid:apple_finance_row" && !/SECRET|provider/i.test(error.message));
  assert.throws(() => normalizeAniccaIosRevenueCatEvent({ provider_event_id: "evt/SECRET", event_type: "INITIAL_PURCHASE", environment: "PRODUCTION", store: "APP_STORE", product_id: "ai.anicca.app.ios.monthly", price_decimal: "1", currency: "JPY", purchased_at_ms: "1786410123000" }), error => error.message === "cfo_anicca_ios_earning_invalid:invalid_input" && !/SECRET|provider/i.test(error.message));
});

test("rejects malformed boundaries, ragged rows, and unsafe report input", () => {
  const cases = [
    ["missing footer", report().split("\n").slice(0, -1).join("\n")],
    ["count mismatch", report({ footerRows: 2 })],
    ["ragged row", report({ rows: [report().split("\n")[4].split("\t").slice(0, -1)] })],
    ["duplicate required header", report({ header: [...REPORT_HEADER.slice(0, -1), "SKU"] })],
    ["metadata boundary", report({ metadata: ["fiscal_month\t2026-10", "report_type\tWRONG", "report_status\tCOMPLETE"] })],
    ["invalid start date", report({ footerRows: 1, rows: [["SECRET_NOT_A_DATE", "07/31/2026", "07/06/2026", "07/06/2026", "6769264298", "ai.anicca.app.ios.monthly.b", "1", "425", "425", "JPY", "S", "ignored"]] })],
    ["reversed report boundary", report({ footerRows: 1, rows: [["08/01/2026", "07/31/2026", "07/06/2026", "07/06/2026", "6769264298", "ai.anicca.app.ios.monthly.b", "1", "425", "425", "JPY", "S", "ignored"]] })],
  ];
  for (const [name, input] of cases) assert.throws(() => parseAniccaIosAppleFinanceReport(input, { revenueCatReceipts: null }), invalidReport, name);
  const raw = report();
  const hostileReceipts = [{ ...normalizeAniccaIosRevenueCatEvent({ provider_event_id: "evt_safe", event_type: "INITIAL_PURCHASE", environment: "PRODUCTION", store: "APP_STORE", product_id: "ai.anicca.app.ios.monthly", price_decimal: "1", currency: "JPY", purchased_at_ms: "1786410123000" }), provider_event_id: "SECRET_PROVIDER_ID" }];
  assert.throws(() => parseAniccaIosAppleFinanceReport(raw, { revenueCatReceipts: [{ amount: { decimal: "1e2", currency: "JPY" }, provider_event_id: "SECRET_PROVIDER_ID" }] }), invalidReport);
  assert.throws(() => parseAniccaIosAppleFinanceReport(raw, { revenueCatReceipts: hostileReceipts }), invalidReport);
  const oversizedRawReceipt = normalizeAniccaIosRevenueCatEvent({ provider_event_id: "evt_oversized", event_type: "INITIAL_PURCHASE", environment: "PRODUCTION", store: "APP_STORE", product_id: "ai.anicca.app.ios.monthly", price_decimal: "1", currency: "JPY", purchased_at_ms: "1786410123000" });
  assert.throws(() => parseAniccaIosAppleFinanceReport(raw, { revenueCatReceipts: [{ ...oversizedRawReceipt, amount: { ...oversizedRawReceipt.amount, decimal: "1".repeat(33) } }] }), invalidReport);
  const oversizedReceipt = normalizeAniccaIosRevenueCatEvent({ provider_event_id: "evt_safe", event_type: "INITIAL_PURCHASE", environment: "PRODUCTION", store: "APP_STORE", product_id: "ai.anicca.app.ios.monthly", price_decimal: "1", currency: "JPY", purchased_at_ms: "1786410123000" });
  const oversizedAmount = { ...oversizedReceipt, amount: { ...oversizedReceipt.amount, decimal: "1".repeat(129) } };
  assert.throws(() => parseAniccaIosAppleFinanceReport(raw, { revenueCatReceipts: [oversizedAmount] }), invalidReport);
  const missingReceiptKey = { ...normalizeAniccaIosRevenueCatEvent({ provider_event_id: "evt_safe", event_type: "INITIAL_PURCHASE", environment: "PRODUCTION", store: "APP_STORE", product_id: "ai.anicca.app.ios.monthly", price_decimal: "1", currency: "JPY", purchased_at_ms: "1786410123000" }) };
  delete missingReceiptKey.source_event_id;
  assert.throws(() => parseAniccaIosAppleFinanceReport(raw, { revenueCatReceipts: [missingReceiptKey] }), invalidReport);
});

function businessInput(overrides = {}) {
  return {
    earning: {
      status: "complete", fiscal_month: "2026-10",
      apple_partner_share_totals: [{ currency: "JPY", row_count: 2, amount_decimal: "850" }],
      revenuecat_coverage_status: "provider_reported", revenuecat_gross_totals: [{ currency: "JPY", receipt_count: 1, amount_decimal: "500" }],
      reconciliation_status: "gross_vs_partner_share_separate", payout_status: "unknown", bank_landed_status: "unknown",
    },
    token_usage: { status: "partial", event_count: 33, total_tokens: 50448879, coverage_exceptions: ["missing_usage", "runner_identity_collision"] },
    direct_api_cost: { status: "covered", event_count: 20408, estimated_usd: "0.04064343" },
    ...overrides,
  };
}

function assertFrozen(value) {
  assert.ok(Object.isFrozen(value));
  if (value && typeof value === "object") for (const child of Object.values(value)) assertFrozen(child);
}

test("composes complete Anicca iOS business fact with separate Apple and RevenueCat evidence", () => {
  const input = businessInput();
  const before = structuredClone(input);
  const result = composeAniccaIosBusinessFact(input);
  assert.deepEqual(result, {
    schema_version: 1, financial_unit_id: "anicca_ios", period: { fiscal_month: "2026-10" }, status: "partial",
    revenue: {
      apple_partner_share: { coverage_status: "complete", totals: [{ currency: "JPY", row_count: 2, amount_decimal: "850" }] },
      revenuecat_gross: { coverage_status: "provider_reported", totals: [{ currency: "JPY", receipt_count: 1, amount_decimal: "500" }] },
      reconciliation_status: "gross_vs_partner_share_separate", payout_status: "unknown", bank_landed_status: "unknown",
    },
    cost: {
      direct_api: { coverage_status: "covered", event_count: 20408, estimated_usd: "0.04064343", evidence_status: "locally_estimated" },
      token_usage: { coverage_status: "partial", event_count: 33, total_tokens: 50448879, evidence_status: "runtime_reported_subtotal" },
      human: { coverage_status: "unknown", amount: null },
    },
    capital: { coverage_status: "unknown", amount: null }, profit: null, roi: null,
    coverage_exceptions: ["apple_payout_unknown", "bank_landed_unknown", "capital_unknown", "human_cost_unknown", "missing_usage", "profit_disabled_until_reconciliation", "runner_identity_collision", "token_usage_partial"],
  });
  assert.deepEqual(input, before);
  assertFrozen(result);
  assert.doesNotMatch(JSON.stringify(result), /SECRET|source_event_id|customer|prompt|wallet|email|https?:\/\//i);
});

test("preserves unavailable evidence as null and rejects malformed or private business facts", () => {
  const unavailable = businessInput({
    earning: { status: "unavailable", fiscal_month: null, apple_partner_share_totals: null, revenuecat_coverage_status: "unavailable", revenuecat_gross_totals: null, reconciliation_status: "revenuecat_unavailable", payout_status: "unknown", bank_landed_status: "unknown" },
    token_usage: { status: "unavailable", event_count: null, total_tokens: null, coverage_exceptions: [] },
    direct_api_cost: { status: "unavailable", event_count: null, estimated_usd: null },
  });
  const unavailableResult = composeAniccaIosBusinessFact(unavailable);
  assert.equal(unavailableResult.period.fiscal_month, null);
  assert.deepEqual(unavailableResult.revenue.apple_partner_share, { coverage_status: "unavailable", totals: null });
  assert.deepEqual(unavailableResult.revenue.revenuecat_gross, { coverage_status: "unavailable", totals: null });
  assert.deepEqual(unavailableResult.cost.direct_api, { coverage_status: "unavailable", event_count: null, estimated_usd: null, evidence_status: "unavailable" });
  assert.deepEqual(unavailableResult.cost.token_usage, { coverage_status: "unavailable", event_count: null, total_tokens: null, evidence_status: "unavailable" });
  assert.ok(unavailableResult.coverage_exceptions.includes("apple_report_unavailable"));
  assert.ok(unavailableResult.coverage_exceptions.includes("revenuecat_unavailable"));
  assert.ok(unavailableResult.coverage_exceptions.includes("direct_api_cost_unavailable"));
  assert.ok(unavailableResult.coverage_exceptions.includes("token_usage_unavailable"));
  const cases = [
    input => ({ ...input, SECRET_SENTINEL: "SECRET_SENTINEL" }),
    input => ({ ...input, earning: { ...input.earning, revenuecat_coverage_status: "provider_reported", revenuecat_gross_totals: [] } }),
    input => ({ ...input, token_usage: { ...input.token_usage, coverage_exceptions: ["runner_identity_collision", "missing_usage"] } }),
    input => ({ ...input, token_usage: { ...input.token_usage, status: "covered", coverage_exceptions: ["missing_usage"] } }),
    input => ({ ...input, token_usage: { ...input.token_usage, status: "unavailable", event_count: null, total_tokens: null, coverage_exceptions: ["missing_usage"] } }),
    input => ({ ...input, direct_api_cost: { ...input.direct_api_cost, estimated_usd: "01.0" } }),
    input => ({ ...input, earning: { ...input.earning, apple_partner_share_totals: [{ currency: "JPY", row_count: 1, amount_decimal: "1".repeat(129) }] } }),
    input => ({ ...input, earning: { ...input.earning, revenuecat_gross_totals: [{ currency: "JPY", receipt_count: 1, amount_decimal: "1".repeat(129) }] } }),
    input => ({ ...input, direct_api_cost: { ...input.direct_api_cost, estimated_usd: "1".repeat(33) } }),
  ];
  for (const mutate of cases) assert.throws(() => composeAniccaIosBusinessFact(mutate(businessInput())), error => error.message === "cfo_anicca_ios_earning_invalid:business_fact" && !/SECRET|provider|customer|prompt/i.test(error.message));
});

test("accepts a parser-shaped gross aggregate wider than one RevenueCat event", () => {
  const event = fields => normalizeAniccaIosRevenueCatEvent({ provider_event_id: fields, event_type: "INITIAL_PURCHASE", environment: "PRODUCTION", store: "APP_STORE", product_id: "ai.anicca.app.ios.monthly", price_decimal: "9".repeat(32), currency: "JPY", purchased_at_ms: "1786410123000" });
  const parsed = parseAniccaIosAppleFinanceReport(report(), { revenueCatReceipts: [event("evt_large_a"), event("evt_large_b")] });
  assert.equal(parsed.revenuecat_gross_totals[0].amount_decimal.length, 33);
  const composed = composeAniccaIosBusinessFact(businessInput({
    earning: {
      status: "complete", fiscal_month: parsed.fiscal_month, apple_partner_share_totals: parsed.apple_partner_share_totals,
      revenuecat_coverage_status: parsed.revenuecat_coverage_status, revenuecat_gross_totals: parsed.revenuecat_gross_totals,
      reconciliation_status: parsed.reconciliation_status, payout_status: parsed.payout_status, bank_landed_status: parsed.bank_landed_status,
    },
  }));
  assert.equal(composed.revenue.revenuecat_gross.totals[0].amount_decimal.length, 33);
});
