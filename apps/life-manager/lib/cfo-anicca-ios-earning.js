"use strict";

const crypto = require("node:crypto");
const { isProxy } = require("node:util").types;

const KEYS = ["provider_event_id", "event_type", "environment", "store", "product_id", "price_decimal", "currency", "purchased_at_ms"];
const APPLE_KEYS = ["fiscal_month", "row_ordinal", "transaction_date", "settlement_date", "apple_identifier", "sku", "quantity", "partner_share_decimal", "extended_partner_share_decimal", "currency", "sale_or_return"];
const APPLE_PAIRS = Object.freeze({ "6755129214": "anicca-ios-001", "6755320744": "ai.anicca.app.ios.annual", "6755320627": "ai.anicca.app.ios.monthly", "6762049696": "ai.anicca.app.ios.yearly.b", "6769264298": "ai.anicca.app.ios.monthly.b", "6762049888": "ai.anicca.app.ios.weekly.b", "6762320930": "ai.anicca.app.ios.yearly.retention", "6758591116": "Anicca" });

const REPORT_METADATA = [
  ["fiscal_month", /^[0-9]{4}-(0[1-9]|1[0-2])$/],
  ["report_type", /^FINANCE_DETAIL$/],
  ["report_status", /^COMPLETE$/],
];
const REPORT_HEADERS = ["Start Date", "End Date", "Transaction Date", "Settlement Date", "Apple Identifier", "SKU", "Quantity", "Partner Share", "Extended Partner Share", "Partner Share Currency", "Sale or Return"];
const REPORT_FOOTERS = ["Total_Rows", "Total_Amount", "Total_Units"];
const REVENUECAT_KEYS = ["schema_version", "financial_unit_id", "source_ledger", "source_event_id", "channel_id", "occurred_at", "receipt_kind", "amount", "recognition_status", "cash_status", "apple_payout_status", "refund_coverage", "evidence_status"];
const REVENUECAT_AMOUNT_KEYS = ["decimal", "currency"];

function normalizeAniccaIosRevenueCatEvent(row) {
  try {
    if (row === null || typeof row !== "object" || Array.isArray(row) || isProxy(row) || Object.getPrototypeOf(row) !== Object.prototype) throw Error();
    const keys = Reflect.ownKeys(row), descriptors = Object.getOwnPropertyDescriptors(row);
    if (keys.length !== KEYS.length || keys.some(key => typeof key !== "string" || !KEYS.includes(key)) || Object.keys(descriptors).length !== KEYS.length || KEYS.some(key => !Object.prototype.hasOwnProperty.call(descriptors, key) || !Object.prototype.hasOwnProperty.call(descriptors[key], "value") || !descriptors[key].enumerable || Object.prototype.hasOwnProperty.call(descriptors[key], "get") || Object.prototype.hasOwnProperty.call(descriptors[key], "set"))) throw Error();
    const values = KEYS.map(key => descriptors[key].value), [providerEventId, eventType, environment, store, productId, price, currency, purchasedAt] = values;
    const limits = [128, 32, 32, 32, 128, 32, 32, 16];
    if (values.some((value, index) => typeof value !== "string" || value.length < (index === 0 || index === 4 || index === 5 || index === 7 ? 1 : 0) || value.length > limits[index]) || !/^[A-Za-z0-9_-]{1,128}$/.test(providerEventId) || !/^[A-Za-z0-9._-]{1,128}$/.test(productId)) throw Error();
    if (environment !== "PRODUCTION" || store !== "APP_STORE" || !["INITIAL_PURCHASE", "RENEWAL"].includes(eventType) || !productId.startsWith("ai.anicca.app.ios.")) return null;
    if (!/^(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$/.test(price)) throw Error();
    if (/^0(?:\.0*)?$/.test(price)) return null;
    if (!/^[A-Z]{3}$/.test(currency) || !/^[1-9][0-9]*$/.test(purchasedAt)) throw Error();
    const milliseconds = Number(purchasedAt);
    if (!Number.isSafeInteger(milliseconds)) throw Error();
    const date = new Date(milliseconds);
    if (!Number.isFinite(date.getTime())) throw Error();
    const sourceEventId = `revenuecat_subscription:${crypto.createHash("sha256").update(`revenuecat_subscription:${providerEventId}`).digest("hex").slice(0, 24)}`;
    const amount = Object.freeze({ decimal: price, currency });
    return Object.freeze({ schema_version: 1, financial_unit_id: "anicca_ios", source_ledger: "revenuecat_subscription_events", source_event_id: sourceEventId, channel_id: "apple_app_store_anicca", occurred_at: date.toISOString(), receipt_kind: eventType === "INITIAL_PURCHASE" ? "initial_purchase" : "renewal", amount, recognition_status: "provider_reported_gross", cash_status: "unknown", apple_payout_status: "unavailable", refund_coverage: "unknown", evidence_status: "provider_reported" });
  } catch {
    throw new Error("cfo_anicca_ios_earning_invalid:invalid_input");
  }
}

function normalizeAniccaIosAppleFinanceRow(row) {
  try {
    if (row === null || typeof row !== "object" || Array.isArray(row) || isProxy(row) || Object.getPrototypeOf(row) !== Object.prototype) throw Error();
    const keys = Reflect.ownKeys(row), descriptors = Object.getOwnPropertyDescriptors(row);
    if (keys.length !== APPLE_KEYS.length || keys.some(key => typeof key !== "string" || !APPLE_KEYS.includes(key)) || Object.keys(descriptors).length !== APPLE_KEYS.length || APPLE_KEYS.some(key => { const descriptor = descriptors[key]; return !descriptor || !descriptor.enumerable || !Object.prototype.hasOwnProperty.call(descriptor, "value") || Object.prototype.hasOwnProperty.call(descriptor, "get") || Object.prototype.hasOwnProperty.call(descriptor, "set"); })) throw Error();
    const values = APPLE_KEYS.map(key => descriptors[key].value), [fiscal, ordinal, transaction, settlement, appleId, sku, quantity, unitShare, extendedShare, currency, saleOrReturn] = values;
    const limits = [7, 0, 10, 10, 10, 128, 17, 25, 26, 3, 1];
    if (typeof ordinal !== "number" || !Number.isSafeInteger(ordinal) || ordinal < 1 || ordinal > 1000000 || values.some((value, index) => index !== 1 && (typeof value !== "string" || value.length < 1 || value.length > limits[index]))) throw Error();
    if (!/^[0-9]{4}-(0[1-9]|1[0-2])$/.test(fiscal) || !/^[0-9]{10}$/.test(appleId) || !/^[A-Za-z0-9._-]{1,128}$/.test(sku)) throw Error();
    const expectedSku = APPLE_PAIRS[appleId], registeredSku = Object.values(APPLE_PAIRS).includes(sku);
    if (expectedSku === undefined && !registeredSku) return null;
    if (expectedSku !== sku) throw Error();
    const isoDate = value => { const [month, day, year] = value.split("/"), date = new Date(`${year}-${month}-${day}T00:00:00.000Z`); if (!Number.isFinite(date.getTime()) || date.toISOString().slice(0, 10) !== `${year}-${month}-${day}`) throw Error(); return `${year}-${month}-${day}`; };
    const transactionDate = isoDate(transaction), settlementDate = isoDate(settlement);
    if (transactionDate > settlementDate || !/^-?[1-9][0-9]{0,15}$/.test(quantity) || !/^(?:0|[1-9][0-9]{0,15})(?:\.[0-9]{1,8})?$/.test(unitShare) || !/^-?(?:0|[1-9][0-9]{0,15})(?:\.[0-9]{1,8})?$/.test(extendedShare) || !/^[A-Z]{3}$/.test(currency) || !/^[SR]$/.test(saleOrReturn)) throw Error();
    const [unitWhole, unitFraction = ""] = unitShare.split("."), extendedNegative = extendedShare.startsWith("-"), unsignedExtended = extendedNegative ? extendedShare.slice(1) : extendedShare, [extendedWhole, extendedFraction = ""] = unsignedExtended.split("."), unitNumerator = BigInt(unitWhole + unitFraction), extendedNumerator = BigInt(extendedWhole + extendedFraction) * (extendedNegative ? -1n : 1n), signedQuantity = BigInt(quantity);
    if (unitNumerator <= 0n || (saleOrReturn === "S" ? signedQuantity <= 0n || extendedNumerator <= 0n : signedQuantity >= 0n || extendedNumerator >= 0n) || unitNumerator * signedQuantity * 10n ** BigInt(extendedFraction.length) !== extendedNumerator * 10n ** BigInt(unitFraction.length)) throw Error();
    const sourceEventId = `apple_finance_detail:${crypto.createHash("sha256").update(["apple_finance_detail", ...values].join("|")).digest("hex").slice(0, 24)}`, amount = Object.freeze({ decimal: extendedShare, currency });
    return Object.freeze({ schema_version: 1, financial_unit_id: "anicca_ios", source_ledger: "apple_finance_detail", source_event_id: sourceEventId, channel_id: "apple_app_store_anicca", fiscal_month: fiscal, transaction_date: transactionDate, settlement_date: settlementDate, receipt_kind: saleOrReturn === "S" ? "sale" : "return", quantity, unit_partner_share_decimal: unitShare, amount, recognition_status: "apple_finance_reported_partner_share", payout_status: "unknown", bank_landed_status: "unknown", evidence_status: "apple_finance_detail" });
  } catch {
    throw new Error("cfo_anicca_ios_earning_invalid:apple_finance_row");
  }
}

function freeze(value, seen = new WeakSet()) {
  if (value === null || typeof value !== "object" || seen.has(value)) return value;
  seen.add(value);
  Reflect.ownKeys(value).forEach(key => {
    const descriptor = Object.getOwnPropertyDescriptor(value, key);
    if (descriptor && Object.prototype.hasOwnProperty.call(descriptor, "value")) freeze(descriptor.value, seen);
  });
  return Object.freeze(value);
}

function decimalParts(value) {
  const negative = value.startsWith("-");
  const unsigned = negative ? value.slice(1) : value;
  const [whole, fraction = ""] = unsigned.split(".");
  return { negative, whole, fraction };
}

function addDecimal(total, value) {
  const left = decimalParts(total), right = decimalParts(value);
  const scale = Math.max(left.fraction.length, right.fraction.length);
  const leftNumerator = BigInt(left.whole + left.fraction.padEnd(scale, "0")) * (left.negative ? -1n : 1n);
  const rightNumerator = BigInt(right.whole + right.fraction.padEnd(scale, "0")) * (right.negative ? -1n : 1n);
  const numerator = leftNumerator + rightNumerator;
  if (numerator === 0n) return "0";
  const negative = numerator < 0n;
  const unsigned = (negative ? -numerator : numerator).toString().padStart(scale + 1, "0");
  const whole = scale === 0 ? unsigned : unsigned.slice(0, -scale);
  const fraction = scale === 0 ? "" : unsigned.slice(-scale).replace(/0+$/, "");
  return `${negative ? "-" : ""}${whole}${fraction ? `.${fraction}` : ""}`;
}

function aggregateAppleRows(rows) {
  const totals = new Map();
  for (const row of rows) {
    const currency = row.amount.currency;
    const existing = totals.get(currency) || { currency, row_count: 0, amount_decimal: "0" };
    existing.row_count += 1;
    existing.amount_decimal = addDecimal(existing.amount_decimal, row.amount.decimal);
    totals.set(currency, existing);
  }
  return [...totals.values()].sort((left, right) => left.currency < right.currency ? -1 : left.currency > right.currency ? 1 : 0);
}

function aggregateRevenueCatReceipts(receipts) {
  const totals = new Map();
  for (const receipt of receipts) {
    if (receipt === null || typeof receipt !== "object" || Array.isArray(receipt) || isProxy(receipt) || Object.getPrototypeOf(receipt) !== Object.prototype) throw Error();
    const receiptDescriptors = Object.getOwnPropertyDescriptors(receipt);
    const receiptKeys = Reflect.ownKeys(receipt);
    if (receiptKeys.length !== REVENUECAT_KEYS.length || receiptKeys.some(key => typeof key !== "string" || !REVENUECAT_KEYS.includes(key))) throw Error();
    for (const key of REVENUECAT_KEYS) {
      const descriptor = receiptDescriptors[key];
      if (!descriptor || !descriptor.enumerable || !Object.prototype.hasOwnProperty.call(descriptor, "value") || Object.prototype.hasOwnProperty.call(descriptor, "get") || Object.prototype.hasOwnProperty.call(descriptor, "set")) throw Error();
    }
    if (receipt.schema_version !== 1 || receipt.financial_unit_id !== "anicca_ios" || receipt.source_ledger !== "revenuecat_subscription_events" || typeof receipt.source_event_id !== "string" || !/^revenuecat_subscription:[0-9a-f]{24}$/.test(receipt.source_event_id) || receipt.channel_id !== "apple_app_store_anicca" || typeof receipt.occurred_at !== "string" || !/^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3}Z$/.test(receipt.occurred_at) || receipt.receipt_kind !== "initial_purchase" && receipt.receipt_kind !== "renewal" || receipt.recognition_status !== "provider_reported_gross" || receipt.cash_status !== "unknown" || receipt.apple_payout_status !== "unavailable" || receipt.refund_coverage !== "unknown" || receipt.evidence_status !== "provider_reported") throw Error();
    const occurredAt = new Date(receipt.occurred_at);
    if (!Number.isFinite(occurredAt.getTime()) || occurredAt.toISOString() !== receipt.occurred_at) throw Error();
    const amount = receiptDescriptors.amount.value;
    if (amount === null || typeof amount !== "object" || Array.isArray(amount) || isProxy(amount) || Object.getPrototypeOf(amount) !== Object.prototype) throw Error();
    const amountDescriptors = Object.getOwnPropertyDescriptors(amount);
    const amountKeys = Reflect.ownKeys(amount);
    if (amountKeys.length !== REVENUECAT_AMOUNT_KEYS.length || amountKeys.some(key => typeof key !== "string" || !REVENUECAT_AMOUNT_KEYS.includes(key))) throw Error();
    for (const key of ["decimal", "currency"]) {
      const descriptor = amountDescriptors[key];
      if (!descriptor || !descriptor.enumerable || !Object.prototype.hasOwnProperty.call(descriptor, "value") || Object.prototype.hasOwnProperty.call(descriptor, "get") || Object.prototype.hasOwnProperty.call(descriptor, "set")) throw Error();
    }
    const decimal = amountDescriptors.decimal.value, currency = amountDescriptors.currency.value;
    if (typeof decimal !== "string" || decimal.length < 1 || decimal.length > 32 || !/^(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$/.test(decimal) || /^0(?:\.0*)?$/.test(decimal) || typeof currency !== "string" || !/^[A-Z]{3}$/.test(currency)) throw Error();
    const existing = totals.get(currency) || { currency, receipt_count: 0, amount_decimal: "0" };
    existing.receipt_count += 1;
    existing.amount_decimal = addDecimal(existing.amount_decimal, decimal);
    totals.set(currency, existing);
  }
  return [...totals.values()].sort((left, right) => left.currency < right.currency ? -1 : left.currency > right.currency ? 1 : 0);
}

function splitReportLines(raw) {
  if (typeof raw !== "string" || raw.length === 0 || raw.includes("\0")) throw Error();
  const lines = raw.split("\n");
  if (lines[lines.length - 1] === "") lines.pop();
  if (lines.length === 0 || lines.some(line => line.endsWith("\r\r") || (line.includes("\r") && !line.endsWith("\r")))) throw Error();
  return lines.map(line => line.endsWith("\r") ? line.slice(0, -1) : line);
}

function parseReportMetadata(lines) {
  const metadata = {};
  for (let index = 0; index < REPORT_METADATA.length; index += 1) {
    const line = lines[index];
    if (typeof line !== "string" || line.length === 0) throw Error();
    const fields = line.split("\t");
    if (fields.length !== 2 || fields[0] !== REPORT_METADATA[index][0] || !REPORT_METADATA[index][1].test(fields[1])) throw Error();
    metadata[fields[0]] = fields[1];
  }
  return metadata;
}

function parseReportHeader(line) {
  if (typeof line !== "string" || line.length === 0) throw Error();
  const headers = line.split("\t");
  if (headers.length < REPORT_HEADERS.length || headers.some(header => header.length === 0)) throw Error();
  for (const required of REPORT_HEADERS) {
    const matches = headers.reduce((count, header) => count + (header === required ? 1 : 0), 0);
    if (matches !== 1) throw Error();
  }
  return { headers, indexes: Object.fromEntries(REPORT_HEADERS.map(required => [required, headers.indexOf(required)])) };
}

function parseReportDate(value) {
  if (typeof value !== "string" || !/^(0[1-9]|1[0-2])\/(0[1-9]|[12][0-9]|3[01])\/[0-9]{4}$/.test(value)) throw Error();
  const [month, day, year] = value.split("/");
  const date = new Date(`${year}-${month}-${day}T00:00:00.000Z`);
  if (!Number.isFinite(date.getTime()) || date.toISOString().slice(0, 10) !== `${year}-${month}-${day}`) throw Error();
  return `${year}-${month}-${day}`;
}

function parseFooter(lines) {
  const values = {};
  for (let index = 0; index < REPORT_FOOTERS.length; index += 1) {
    const fields = lines[index].split("\t");
    if (fields.length !== 2 || fields[0] !== REPORT_FOOTERS[index] || fields[1].length === 0) throw Error();
    values[fields[0]] = fields[1];
  }
  if (!/^(0|[1-9][0-9]*)$/.test(values.Total_Rows) || !/^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$/.test(values.Total_Amount) || !/^-?(?:0|[1-9][0-9]*)$/.test(values.Total_Units)) throw Error();
  const rowCount = Number(values.Total_Rows);
  if (!Number.isSafeInteger(rowCount) || rowCount < 1) throw Error();
  return { rowCount };
}

function parseAniccaIosAppleFinanceReport(raw, options = {}) {
  try {
    if (options === null || typeof options !== "object" || Array.isArray(options) || isProxy(options) || Object.getPrototypeOf(options) !== Object.prototype) throw Error();
    const optionDescriptors = Object.getOwnPropertyDescriptors(options);
    if (Object.keys(optionDescriptors).some(key => Object.prototype.hasOwnProperty.call(optionDescriptors[key], "get") || Object.prototype.hasOwnProperty.call(optionDescriptors[key], "set"))) throw Error();
    const revenueCatReceipts = Object.prototype.hasOwnProperty.call(optionDescriptors, "revenueCatReceipts") ? optionDescriptors.revenueCatReceipts.value : null;
    const lines = splitReportLines(raw);
    if (lines.length < REPORT_METADATA.length + 1 + 1 + REPORT_FOOTERS.length) throw Error();
    const metadata = parseReportMetadata(lines);
    const { headers, indexes } = parseReportHeader(lines[REPORT_METADATA.length]);
    const footerStart = lines.length - REPORT_FOOTERS.length;
    if (footerStart <= REPORT_METADATA.length) throw Error();
    const footer = parseFooter(lines.slice(footerStart));
    const dataLines = lines.slice(REPORT_METADATA.length + 1, footerStart);
    if (dataLines.length < 1 || dataLines.length !== footer.rowCount || dataLines.some(line => line.length === 0)) throw Error();
    const rows = [];
    for (let index = 0; index < dataLines.length; index += 1) {
      const fields = dataLines[index].split("\t");
      if (fields.length !== headers.length || fields.some(field => field.includes("\r"))) throw Error();
      const startDate = parseReportDate(fields[indexes["Start Date"]]);
      const endDate = parseReportDate(fields[indexes["End Date"]]);
      if (startDate > endDate) throw Error();
      const row = {
        fiscal_month: metadata.fiscal_month,
        row_ordinal: index + 1,
        transaction_date: fields[indexes["Transaction Date"]],
        settlement_date: fields[indexes["Settlement Date"]],
        apple_identifier: fields[indexes["Apple Identifier"]],
        sku: fields[indexes.SKU],
        quantity: fields[indexes.Quantity],
        partner_share_decimal: fields[indexes["Partner Share"]],
        extended_partner_share_decimal: fields[indexes["Extended Partner Share"]],
        currency: fields[indexes["Partner Share Currency"]],
        sale_or_return: fields[indexes["Sale or Return"]],
      };
      const normalized = normalizeAniccaIosAppleFinanceRow(row);
      if (normalized !== null) rows.push(normalized);
    }
    let revenuecatCoverageStatus = "unavailable";
    let revenuecatGrossTotals = null;
    let reconciliationStatus = "revenuecat_unavailable";
    if (revenueCatReceipts !== null && revenueCatReceipts !== undefined) {
      if (!Array.isArray(revenueCatReceipts) || Object.getPrototypeOf(revenueCatReceipts) !== Array.prototype || isProxy(revenueCatReceipts)) throw Error();
      const arrayDescriptors = Object.getOwnPropertyDescriptors(revenueCatReceipts);
      const lengthDescriptor = arrayDescriptors.length;
      if (!lengthDescriptor || !Object.prototype.hasOwnProperty.call(lengthDescriptor, "value") || lengthDescriptor.enumerable || !Number.isSafeInteger(lengthDescriptor.value) || lengthDescriptor.value < 0 || Object.keys(arrayDescriptors).some(key => key !== "length" && (!/^(0|[1-9][0-9]*)$/.test(key) || Number(key) >= lengthDescriptor.value))) throw Error();
      for (let index = 0; index < revenueCatReceipts.length; index += 1) {
        const descriptor = arrayDescriptors[String(index)];
        if (!descriptor || !descriptor.enumerable || !Object.prototype.hasOwnProperty.call(descriptor, "value") || Object.prototype.hasOwnProperty.call(descriptor, "get") || Object.prototype.hasOwnProperty.call(descriptor, "set")) throw Error();
      }
      revenuecatCoverageStatus = "observed_empty";
      revenuecatGrossTotals = aggregateRevenueCatReceipts(revenueCatReceipts);
      if (revenueCatReceipts.length > 0) revenuecatCoverageStatus = "provider_reported";
      reconciliationStatus = "gross_vs_partner_share_separate";
    }
    return freeze({
      schema_version: 1,
      financial_unit_id: "anicca_ios",
      source_ledger: "apple_finance_detail",
      fiscal_month: metadata.fiscal_month,
      report_status: metadata.report_status,
      boundary: { metadata_line_count: 3, header_verified: true, data_row_count: dataLines.length, footer_line_count: 3, footer_row_count: footer.rowCount },
      apple_partner_share_totals: aggregateAppleRows(rows),
      revenuecat_coverage_status: revenuecatCoverageStatus,
      revenuecat_gross_totals: revenuecatGrossTotals,
      reconciliation_status: reconciliationStatus,
      payout_status: "unknown",
      bank_landed_status: "unknown",
      evidence_status: "apple_finance_detail_complete",
    });
  } catch {
    throw new Error("cfo_anicca_ios_earning_invalid:finance_report");
  }
}

const BUSINESS_FACT_TOP_KEYS = ["earning", "token_usage", "direct_api_cost"];
const BUSINESS_EARNING_KEYS = ["status", "fiscal_month", "apple_partner_share_totals", "revenuecat_coverage_status", "revenuecat_gross_totals", "reconciliation_status", "payout_status", "bank_landed_status"];
const BUSINESS_TOKEN_KEYS = ["status", "event_count", "total_tokens", "coverage_exceptions"];
const BUSINESS_DIRECT_KEYS = ["status", "event_count", "estimated_usd"];
const BUSINESS_APPLE_TOTAL_KEYS = ["currency", "row_count", "amount_decimal"];
const BUSINESS_RC_TOTAL_KEYS = ["currency", "receipt_count", "amount_decimal"];
const BUSINESS_TOKEN_EXCEPTIONS = new Set(["missing_usage", "runner_identity_collision", "unattributed_usage"]);

function businessDataObject(value, allowedKeys) {
  if (value === null || typeof value !== "object" || Array.isArray(value) || isProxy(value) || Object.getPrototypeOf(value) !== Object.prototype) throw Error();
  const keys = Reflect.ownKeys(value), descriptors = Object.getOwnPropertyDescriptors(value);
  if (keys.length !== allowedKeys.length || keys.some(key => typeof key !== "string" || !allowedKeys.includes(key))) throw Error();
  for (const key of allowedKeys) {
    const descriptor = descriptors[key];
    if (!descriptor || !descriptor.enumerable || !Object.prototype.hasOwnProperty.call(descriptor, "value") || Object.prototype.hasOwnProperty.call(descriptor, "get") || Object.prototype.hasOwnProperty.call(descriptor, "set")) throw Error();
  }
  return descriptors;
}

function businessDenseArray(value) {
  if (!Array.isArray(value) || isProxy(value) || Object.getPrototypeOf(value) !== Array.prototype) throw Error();
  const keys = Reflect.ownKeys(value), descriptors = Object.getOwnPropertyDescriptors(value), length = value.length;
  const lengthDescriptor = descriptors.length;
  if (!lengthDescriptor || !Object.prototype.hasOwnProperty.call(lengthDescriptor, "value") || lengthDescriptor.enumerable || !Number.isSafeInteger(length) || length < 0 || keys.length !== length + 1 || keys.some(key => key !== "length" && (typeof key !== "string" || !/^(0|[1-9][0-9]*)$/.test(key) || Number(key) >= length))) throw Error();
  for (let index = 0; index < length; index += 1) {
    const descriptor = descriptors[String(index)];
    if (!descriptor || !descriptor.enumerable || !Object.prototype.hasOwnProperty.call(descriptor, "value") || Object.prototype.hasOwnProperty.call(descriptor, "get") || Object.prototype.hasOwnProperty.call(descriptor, "set")) throw Error();
  }
}

function businessSafeInteger(value, nullable = false) {
  if (nullable && value === null) return;
  if (!Number.isSafeInteger(value) || value < 0) throw Error();
}

function businessDecimal(value, signed = false, maxLength = 32) {
  const pattern = signed ? /^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$/ : /^(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$/;
  if (typeof value !== "string" || value.length < 1 || value.length > maxLength || !pattern.test(value) || (signed && /^-0(?:\.0*)?$/.test(value))) throw Error();
}

function businessAggregateDecimal(value, signed = false) {
  businessDecimal(value, signed, 128);
}

function businessCurrency(value) {
  if (typeof value !== "string" || !/^[A-Z]{3}$/.test(value)) throw Error();
}

function businessTotals(value, kind) {
  if (value === null) throw Error();
  businessDenseArray(value);
  const keys = kind === "apple" ? BUSINESS_APPLE_TOTAL_KEYS : BUSINESS_RC_TOTAL_KEYS;
  let previousCurrency = null;
  const totals = [];
  for (const item of value) {
    businessDataObject(item, keys);
    businessCurrency(item.currency);
    if (previousCurrency !== null && previousCurrency >= item.currency) throw Error();
    previousCurrency = item.currency;
    if (kind === "apple") {
      businessSafeInteger(item.row_count);
      if (item.row_count < 1) throw Error();
      businessAggregateDecimal(item.amount_decimal, true);
    } else {
      businessSafeInteger(item.receipt_count);
      if (item.receipt_count < 1) throw Error();
      businessAggregateDecimal(item.amount_decimal, false);
      if (/^0(?:\.0*)?$/.test(item.amount_decimal)) throw Error();
    }
    totals.push({ currency: item.currency, [kind === "apple" ? "row_count" : "receipt_count"]: kind === "apple" ? item.row_count : item.receipt_count, amount_decimal: item.amount_decimal });
  }
  return totals;
}

function composeAniccaIosBusinessFact(input) {
  try {
    businessDataObject(input, BUSINESS_FACT_TOP_KEYS);
    const earning = input.earning, tokenUsage = input.token_usage, directApiCost = input.direct_api_cost;
    businessDataObject(earning, BUSINESS_EARNING_KEYS);
    if (earning.status !== "complete" && earning.status !== "unavailable") throw Error();
    if (earning.status === "complete") {
      if (typeof earning.fiscal_month !== "string" || !/^[0-9]{4}-(0[1-9]|1[0-2])$/.test(earning.fiscal_month)) throw Error();
      if (earning.apple_partner_share_totals === null) throw Error();
      businessTotals(earning.apple_partner_share_totals, "apple");
    } else if (earning.fiscal_month !== null || earning.apple_partner_share_totals !== null) throw Error();
    if (!["unavailable", "observed_empty", "provider_reported"].includes(earning.revenuecat_coverage_status)) throw Error();
    if (earning.revenuecat_coverage_status === "unavailable") {
      if (earning.revenuecat_gross_totals !== null) throw Error();
    } else if (earning.revenuecat_coverage_status === "observed_empty") {
      if (!Array.isArray(earning.revenuecat_gross_totals)) throw Error();
      businessDenseArray(earning.revenuecat_gross_totals);
      if (earning.revenuecat_gross_totals.length !== 0) throw Error();
    } else {
      if (!Array.isArray(earning.revenuecat_gross_totals) || earning.revenuecat_gross_totals.length === 0) throw Error();
      businessTotals(earning.revenuecat_gross_totals, "revenuecat");
    }
    const expectedReconciliation = earning.revenuecat_coverage_status === "unavailable" ? "revenuecat_unavailable" : "gross_vs_partner_share_separate";
    if (earning.reconciliation_status !== expectedReconciliation || earning.payout_status !== "unknown" || earning.bank_landed_status !== "unknown") throw Error();
    businessDataObject(tokenUsage, BUSINESS_TOKEN_KEYS);
    if (!["covered", "partial", "unavailable"].includes(tokenUsage.status)) throw Error();
    if (tokenUsage.status === "unavailable") {
      if (tokenUsage.event_count !== null || tokenUsage.total_tokens !== null) throw Error();
    } else {
      businessSafeInteger(tokenUsage.event_count);
      businessSafeInteger(tokenUsage.total_tokens);
    }
    businessDenseArray(tokenUsage.coverage_exceptions);
    if (tokenUsage.status !== "partial" && tokenUsage.coverage_exceptions.length !== 0) throw Error();
    let previousException = null;
    const tokenExceptions = [];
    for (const exception of tokenUsage.coverage_exceptions) {
      if (typeof exception !== "string" || !BUSINESS_TOKEN_EXCEPTIONS.has(exception) || (previousException !== null && previousException >= exception)) throw Error();
      previousException = exception;
      tokenExceptions.push(exception);
    }
    businessDataObject(directApiCost, BUSINESS_DIRECT_KEYS);
    if (!["covered", "partial", "unavailable"].includes(directApiCost.status)) throw Error();
    if (directApiCost.status === "unavailable") {
      if (directApiCost.event_count !== null || directApiCost.estimated_usd !== null) throw Error();
    } else {
      businessSafeInteger(directApiCost.event_count);
      businessDecimal(directApiCost.estimated_usd, false);
    }
    const appleTotals = earning.apple_partner_share_totals === null ? null : businessTotals(earning.apple_partner_share_totals, "apple");
    const revenueCatTotals = earning.revenuecat_gross_totals === null ? null : businessTotals(earning.revenuecat_gross_totals, "revenuecat");
    const exceptions = ["apple_payout_unknown", "bank_landed_unknown", "capital_unknown", "human_cost_unknown", "profit_disabled_until_reconciliation"];
    if (earning.status === "unavailable") exceptions.push("apple_report_unavailable");
    if (earning.revenuecat_coverage_status === "unavailable") exceptions.push("revenuecat_unavailable");
    if (directApiCost.status === "partial") exceptions.push("direct_api_cost_partial");
    if (directApiCost.status === "unavailable") exceptions.push("direct_api_cost_unavailable");
    if (tokenUsage.status === "partial") exceptions.push("token_usage_partial");
    if (tokenUsage.status === "unavailable") exceptions.push("token_usage_unavailable");
    exceptions.push(...tokenExceptions);
    exceptions.sort();
    const result = {
      schema_version: 1,
      financial_unit_id: "anicca_ios",
      period: { fiscal_month: earning.fiscal_month },
      status: "partial",
      revenue: {
        apple_partner_share: { coverage_status: earning.status === "complete" ? "complete" : "unavailable", totals: appleTotals },
        revenuecat_gross: { coverage_status: earning.revenuecat_coverage_status, totals: revenueCatTotals },
        reconciliation_status: earning.reconciliation_status,
        payout_status: earning.payout_status,
        bank_landed_status: earning.bank_landed_status,
      },
      cost: {
        direct_api: { coverage_status: directApiCost.status, event_count: directApiCost.event_count, estimated_usd: directApiCost.estimated_usd, evidence_status: directApiCost.status === "unavailable" ? "unavailable" : "locally_estimated" },
        token_usage: { coverage_status: tokenUsage.status, event_count: tokenUsage.event_count, total_tokens: tokenUsage.total_tokens, evidence_status: tokenUsage.status === "unavailable" ? "unavailable" : "runtime_reported_subtotal" },
        human: { coverage_status: "unknown", amount: null },
      },
      capital: { coverage_status: "unknown", amount: null },
      profit: null,
      roi: null,
      coverage_exceptions: exceptions,
    };
    return freeze(result);
  } catch {
    throw new Error("cfo_anicca_ios_earning_invalid:business_fact");
  }
}

module.exports = { normalizeAniccaIosRevenueCatEvent, normalizeAniccaIosAppleFinanceRow, parseAniccaIosAppleFinanceReport, composeAniccaIosBusinessFact };
