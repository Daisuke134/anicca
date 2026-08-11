"use strict";

const PREFIX = "cfo_life_manager_earning_invalid:";
const INTERNAL = new WeakSet();
const CHANNELS = Object.freeze({ taskmarket_work: "taskmarket_life_manager", ugig_work: "ugig_life_manager" });
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const RECEIPT = /^(?:0x[0-9a-fA-F]{64}|[1-9A-HJ-NP-Za-km-z]{87,88})$/;
const MAX_ATOMIC = 90071992547409910000n;

function fail(reason) { const error = new Error(`${PREFIX}${reason}`); INTERNAL.add(error); throw error; }
function plain(value) { return value !== null && typeof value === "object" && !Array.isArray(value) && Object.getPrototypeOf(value) === Object.prototype; }
function data(value) {
  if (!plain(value)) fail("invalid_input");
  for (const key of Reflect.ownKeys(value)) {
    const descriptor = Object.getOwnPropertyDescriptor(value, key);
    if (!descriptor || !Object.prototype.hasOwnProperty.call(descriptor, "value")) fail("invalid_input");
  }
}
function amount(value) {
  if (typeof value === "number") {
    if (!Number.isSafeInteger(value) || value <= 0) fail("amount");
    return String(value);
  }
  if (typeof value !== "string" || !/^[1-9][0-9]*$/.test(value)) fail("amount");
  try { const atomic = BigInt(value); if (atomic <= 0n || atomic > MAX_ATOMIC) fail("amount"); } catch { fail("amount"); }
  return value;
}
function normalizeLifeManagerEarningReceipt(input) {
  try {
    data(input); data(input.meta);
    if (input.kind !== "financial_external_income") fail("kind");
    if (!Object.prototype.hasOwnProperty.call(CHANNELS, input.source)) fail("source");
    if (input.meta.finalized !== true) fail("not_finalized");
    if (input.meta.external !== true) fail("not_external");
    if (typeof input.public_ref !== "string" || !UUID.test(input.public_ref)) fail("public_ref");
    if (typeof input.tx_hash !== "string" || !RECEIPT.test(input.tx_hash)) fail("receipt");
    const atomic = input.amount_minor === null && amount(input.amount_atomic);
    if (input.amount_minor !== null) fail("amount");
    if (!Number.isInteger(input.amount_decimals) || input.amount_decimals < 0 || input.amount_decimals > 6) fail("amount");
    if (input.currency !== "USD") fail("currency");
    if (typeof input.occurred_at !== "string") fail("occurred_at");
    const date = new Date(input.occurred_at);
    if (!Number.isFinite(date.getTime())) fail("occurred_at");
    const result = { schema_version: 1, financial_unit_id: "life_manager_saas", source_ledger: "lm_agent_earnings", source_event_id: `lm_agent_earnings:${input.public_ref}`, channel_id: CHANNELS[input.source], occurred_at: date.toISOString(), amount: { atomic, decimals: input.amount_decimals, currency: input.currency }, landed_cash_status: "confirmed_agent_wallet", evidence_status: "onchain_finalized_external_settlement" };
    Object.freeze(result.amount);
    return Object.freeze(result);
  } catch (error) {
    if (INTERNAL.has(error)) throw error;
    fail("invalid_input");
  }
}

async function collectLifeManagerStripeReceipts(options) {
  try {
    data(options);
    const { stripeKey, paymentLinkUrl, fetchImpl } = options;
    if (Reflect.ownKeys(options).sort().join(",") !== "fetchImpl,paymentLinkUrl,stripeKey" || typeof stripeKey !== "string" || !/^sk_live_[A-Za-z0-9]+$/.test(stripeKey) || typeof paymentLinkUrl !== "string" || !/^https:\/\/buy\.stripe\.com\/[^/?#]+$/.test(paymentLinkUrl) || typeof fetchImpl !== "function") fail("stripe_options");
    const seen = new Set();
    async function list(path, query) {
      const out = [];
      let cursor;
      for (let page = 0; page < 100; page++) {
        const url = new URL(`https://api.stripe.com/v1/${path}`);
        url.searchParams.set("limit", "100"); if (query) for (const [k, v] of Object.entries(query)) url.searchParams.set(k, v); if (cursor) url.searchParams.set("starting_after", cursor);
        let response, body;
        try { response = await fetchImpl(url.toString(), { method: "GET", headers: { Authorization: `Bearer ${stripeKey}` } }); body = await response.json(); } catch { fail("stripe_network"); }
        if (!response || !response.ok || !plain(body) || !Array.isArray(body.data) || typeof body.has_more !== "boolean") fail("stripe_response");
        for (const item of body.data) { if (!plain(item) || typeof item.id !== "string" || !/^[A-Za-z0-9_]+$/.test(item.id) || seen.has(`${path}:${item.id}`)) fail("stripe_item"); seen.add(`${path}:${item.id}`); out.push(item); }
        if (!body.has_more) return out;
        const last = body.data[body.data.length - 1]; if (!last || typeof last.id !== "string" || !last.id) fail("stripe_pagination"); cursor = last.id;
      }
      fail("stripe_pagination");
    }
    const paymentLinks = await list("payment_links");
    const matching = paymentLinks.filter(link => link.url === paymentLinkUrl && link.livemode === true && link.active === true);
    if (matching.length !== 1) fail("stripe_canonical_link");
    const linkId = matching[0].id;
    const sessions = await list("checkout/sessions", { payment_link: linkId });
    const receipts = []; let zero = 0;
    for (const session of sessions) {
      if (!["paid", "unpaid", "no_payment_required"].includes(session.payment_status) || !["complete", "open", "expired"].includes(session.status)) fail("stripe_status");
      if (session.payment_link !== linkId || session.livemode !== true) fail("stripe_session_link");
      if (session.payment_status !== "paid") continue;
      if (session.status !== "complete" || !Number.isInteger(session.created) || session.created < 0 || !Number.isSafeInteger(session.amount_total) || session.amount_total < 0 || typeof session.currency !== "string" || !/^[a-z]{3}$/.test(session.currency)) fail("stripe_paid");
      if (session.amount_total === 0) { zero++; continue; }
      receipts.push(Object.freeze({ source_event_id: `stripe_checkout:${session.id}`, occurred_at: new Date(session.created * 1000).toISOString(), amount: Object.freeze({ minor: String(session.amount_total), currency: session.currency.toUpperCase() }), recognition_status: "gross_inflow_unreconciled", landed_cash_status: "confirmed_stripe_balance", bank_landed_status: "unknown", evidence_status: "provider_reported" }));
    }
    receipts.sort((a, b) => a.occurred_at.localeCompare(b.occurred_at) || a.source_event_id.localeCompare(b.source_event_id));
    const result = { schema_version: 1, financial_unit_id: "life_manager_saas", channel_id: "stripe_life_manager", status: "covered", receipt_count: receipts.length, zero_value_paid_count: zero, reversal_coverage_status: "unknown", receipts: Object.freeze(receipts), evidence_status: "provider_reported" };
    return Object.freeze(result);
  } catch (error) { if (INTERNAL.has(error)) throw error; fail("stripe_invalid_input"); }
}

const COVERAGE = Object.freeze(["period_start", "period_end", "earning_ledger", "stripe", "direct_api_cost", "token_usage", "shared_subscription"]), EARNING = Object.freeze(["status", "receipt_count"]), STRIPE = Object.freeze(["schema_version", "financial_unit_id", "channel_id", "status", "receipt_count", "zero_value_paid_count", "reversal_coverage_status", "receipts", "evidence_status"]), RECEIPT_KEYS = Object.freeze(["source_event_id", "occurred_at", "amount", "recognition_status", "landed_cash_status", "bank_landed_status", "evidence_status"]), AMOUNT_KEYS = Object.freeze(["minor", "currency"]), DIRECT = Object.freeze(["status", "event_count", "estimated_usd"]), TOKEN = Object.freeze(["status", "event_count", "total_tokens", "coverage_exceptions"]), SHARED = Object.freeze(["status", "amount_minor", "currency"]), OFFSET = 9 * 60 * 60 * 1000, TOKEN_EXCEPTIONS = new Set(["missing_usage", "runner_identity_collision", "unattributed_usage"]);
function exact(value, keys) { data(value); const actual = Reflect.ownKeys(value); if (actual.length !== keys.length || keys.some(key => !Object.prototype.hasOwnProperty.call(value, key))) fail("business_coverage"); }
function dense(value) { if (!Array.isArray(value) || Object.getPrototypeOf(value) !== Array.prototype || Reflect.ownKeys(value).length !== value.length + 1) fail("business_coverage"); const length = Object.getOwnPropertyDescriptor(value, "length"); if (!length || !Object.prototype.hasOwnProperty.call(length, "value")) fail("business_coverage"); for (let index = 0; index < value.length; index++) { const descriptor = Object.getOwnPropertyDescriptor(value, String(index)); if (!descriptor || !Object.prototype.hasOwnProperty.call(descriptor, "value")) fail("business_coverage"); } }
function safeCount(value) { if (!Number.isSafeInteger(value) || value < 0) fail("business_coverage"); }
function canonicalUtc(value) { if (typeof value !== "string") fail("business_coverage"); const date = new Date(value); if (!Number.isFinite(date.getTime()) || date.toISOString() !== value) fail("business_coverage"); return date; }
function uppercaseCurrency(value) { if (typeof value !== "string" || !/^[A-Z]{3}$/.test(value)) fail("business_coverage"); }
function deepFreeze(value) { if (value && typeof value === "object" && !Object.isFrozen(value)) { for (const child of Object.values(value)) deepFreeze(child); Object.freeze(value); } return value; }
function composeLifeManagerBusinessCoverage(input) {
  try {
    exact(input, COVERAGE); const start = canonicalUtc(input.period_start); canonicalUtc(input.period_end); const shifted = new Date(start.getTime() + OFFSET); if (shifted.getUTCDay() === undefined || shifted.getUTCDate() !== 1 || shifted.getUTCHours() !== 0 || shifted.getUTCMinutes() !== 0 || shifted.getUTCSeconds() !== 0 || shifted.getUTCMilliseconds() !== 0) fail("business_coverage"); const next = new Date(0); next.setUTCFullYear(shifted.getUTCFullYear(), shifted.getUTCMonth() + 1, 1); next.setUTCHours(0, 0, 0, 0); if (new Date(next.getTime() - OFFSET).toISOString() !== input.period_end) fail("business_coverage");
    exact(input.earning_ledger, EARNING); if (input.earning_ledger.status !== "covered") fail("business_coverage"); safeCount(input.earning_ledger.receipt_count);
    exact(input.stripe, STRIPE); if (input.stripe.schema_version !== 1 || input.stripe.financial_unit_id !== "life_manager_saas" || input.stripe.channel_id !== "stripe_life_manager" || input.stripe.status !== "covered" || !["unknown", "covered"].includes(input.stripe.reversal_coverage_status)) fail("business_coverage"); safeCount(input.stripe.receipt_count); safeCount(input.stripe.zero_value_paid_count); dense(input.stripe.receipts); if (input.stripe.receipts.length !== input.stripe.receipt_count) fail("business_coverage");
    for (const receipt of input.stripe.receipts) { exact(receipt, RECEIPT_KEYS); exact(receipt.amount, AMOUNT_KEYS); if (typeof receipt.source_event_id !== "string" || !/^stripe_checkout:[A-Za-z0-9_]+$/.test(receipt.source_event_id)) fail("business_coverage"); canonicalUtc(receipt.occurred_at); if (typeof receipt.amount.minor !== "string" || !/^[1-9][0-9]*$/.test(receipt.amount.minor)) fail("business_coverage"); uppercaseCurrency(receipt.amount.currency); if (receipt.recognition_status !== "gross_inflow_unreconciled" || receipt.landed_cash_status !== "confirmed_stripe_balance" || receipt.bank_landed_status !== "unknown" || receipt.evidence_status !== "provider_reported") fail("business_coverage"); }
    exact(input.direct_api_cost, DIRECT); if (!["covered", "partial"].includes(input.direct_api_cost.status)) fail("business_coverage"); safeCount(input.direct_api_cost.event_count); if (typeof input.direct_api_cost.estimated_usd !== "string" || !/^(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$/.test(input.direct_api_cost.estimated_usd)) fail("business_coverage");
    exact(input.token_usage, TOKEN); if (!["covered", "partial"].includes(input.token_usage.status)) fail("business_coverage"); safeCount(input.token_usage.event_count); safeCount(input.token_usage.total_tokens); dense(input.token_usage.coverage_exceptions); for (let index = 0; index < input.token_usage.coverage_exceptions.length; index++) { const exception = input.token_usage.coverage_exceptions[index]; if (!TOKEN_EXCEPTIONS.has(exception) || (index && input.token_usage.coverage_exceptions[index - 1] >= exception)) fail("business_coverage"); }
    exact(input.shared_subscription, SHARED); if (input.shared_subscription.status !== "confirmed_shared_unallocated" || typeof input.shared_subscription.amount_minor !== "string" || !/^[1-9][0-9]*$/.test(input.shared_subscription.amount_minor) || input.shared_subscription.currency !== "USD") fail("business_coverage");
    const periodStripeReceipts = input.stripe.receipts.filter(receipt => receipt.occurred_at >= input.period_start && receipt.occurred_at < input.period_end), totalReceipts = input.earning_ledger.receipt_count + periodStripeReceipts.length, hasStripeReceipts = periodStripeReceipts.length > 0, exceptions = ["capital_unknown", "human_cost_unknown", "shared_subscription_unallocated"]; if (input.direct_api_cost.status !== "covered") exceptions.push("direct_api_cost_partial"); if (input.token_usage.status !== "covered") exceptions.push("token_usage_partial"); exceptions.push(...input.token_usage.coverage_exceptions); if (hasStripeReceipts && input.stripe.reversal_coverage_status !== "covered") exceptions.push("stripe_reversal_unknown"); exceptions.sort(); const noReceipts = totalReceipts === 0;
    const result = { schema_version: 1, financial_unit_id: "life_manager_saas", period: { start: input.period_start, end: input.period_end, time_zone: "Asia/Tokyo" }, status: exceptions.length === 0 ? "complete" : "partial", revenue: { coverage_status: "covered_registered_channels", gross_receipt_count: totalReceipts, reversal_coverage_status: noReceipts ? "not_applicable_no_receipts" : hasStripeReceipts ? input.stripe.reversal_coverage_status : "not_applicable_no_stripe_receipts", landed_cash_coverage_status: noReceipts ? "not_applicable_no_receipts" : hasStripeReceipts ? "partial" : "confirmed_agent_wallet" }, cost: { direct_api: { coverage_status: input.direct_api_cost.status, event_count: input.direct_api_cost.event_count, estimated_usd: input.direct_api_cost.estimated_usd, evidence_status: "locally_estimated" }, token_usage: { coverage_status: input.token_usage.status, event_count: input.token_usage.event_count, total_tokens: input.token_usage.total_tokens, evidence_status: "runtime_reported_subtotal" }, shared_subscription: { coverage_status: input.shared_subscription.status, observed_amount: { minor: input.shared_subscription.amount_minor, currency: input.shared_subscription.currency }, allocated_amount: null }, human: { coverage_status: "unknown", amount: null } }, capital: { coverage_status: "unknown", amount: null }, profit: null, roi: null, coverage_exceptions: exceptions };
    return deepFreeze(result);
  } catch (error) { if (INTERNAL.has(error)) throw error; fail("business_coverage"); }
}

module.exports = { normalizeLifeManagerEarningReceipt, collectLifeManagerStripeReceipts, composeLifeManagerBusinessCoverage };
