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

module.exports = { normalizeLifeManagerEarningReceipt };
