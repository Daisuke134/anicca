"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");
const {
  normalizeAniccaIosRevenueCatEvent,
  normalizeAniccaIosAppleFinanceRow,
  parseAniccaIosAppleFinanceReport,
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
  const oversizedReceipt = normalizeAniccaIosRevenueCatEvent({ provider_event_id: "evt_safe", event_type: "INITIAL_PURCHASE", environment: "PRODUCTION", store: "APP_STORE", product_id: "ai.anicca.app.ios.monthly", price_decimal: "1", currency: "JPY", purchased_at_ms: "1786410123000" });
  const oversizedAmount = { ...oversizedReceipt, amount: { ...oversizedReceipt.amount, decimal: "1".repeat(33) } };
  assert.throws(() => parseAniccaIosAppleFinanceReport(raw, { revenueCatReceipts: [oversizedAmount] }), invalidReport);
  const missingReceiptKey = { ...normalizeAniccaIosRevenueCatEvent({ provider_event_id: "evt_safe", event_type: "INITIAL_PURCHASE", environment: "PRODUCTION", store: "APP_STORE", product_id: "ai.anicca.app.ios.monthly", price_decimal: "1", currency: "JPY", purchased_at_ms: "1786410123000" }) };
  delete missingReceiptKey.source_event_id;
  assert.throws(() => parseAniccaIosAppleFinanceReport(raw, { revenueCatReceipts: [missingReceiptKey] }), invalidReport);
});
