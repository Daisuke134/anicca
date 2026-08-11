"use strict";

const crypto = require("node:crypto");
const { isProxy } = require("node:util").types;
const KEYS = ["provider_event_id", "event_type", "environment", "store", "product_id", "price_decimal", "currency", "purchased_at_ms"];
const APPLE_KEYS = ["fiscal_month", "row_ordinal", "transaction_date", "settlement_date", "apple_identifier", "sku", "quantity", "partner_share_decimal", "extended_partner_share_decimal", "currency", "sale_or_return"];
const APPLE_PAIRS = Object.freeze({ "6755129214": "anicca-ios-001", "6755320744": "ai.anicca.app.ios.annual", "6755320627": "ai.anicca.app.ios.monthly", "6762049696": "ai.anicca.app.ios.yearly.b", "6769264298": "ai.anicca.app.ios.monthly.b", "6762049888": "ai.anicca.app.ios.weekly.b", "6762320930": "ai.anicca.app.ios.yearly.retention", "6758591116": "Anicca" });

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

module.exports = { normalizeAniccaIosRevenueCatEvent, normalizeAniccaIosAppleFinanceRow };
