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

module.exports = { normalizeLifeManagerEarningReceipt, collectLifeManagerStripeReceipts };
