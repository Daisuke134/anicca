"use strict";

const crypto = require("node:crypto");
const { isProxy } = require("node:util").types;
const KEYS = ["provider_event_id", "event_type", "environment", "store", "product_id", "price_decimal", "currency", "purchased_at_ms"];

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

module.exports = { normalizeAniccaIosRevenueCatEvent };
