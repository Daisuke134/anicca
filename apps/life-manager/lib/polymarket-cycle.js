"use strict";

// Adapter between Polymarket's six-decimal cycle accounting and Life Manager's
// cent-denominated append-only ledger. Deployed capital and recovered principal
// stay in metadata; only the economic delta and fees become accounting rows.

const { normaliseEntry } = require("./earnings-ledger.js");
const { recordEarnLoopRevenue } = require("./earnings-runtime.js");

const MICRO_PER_CENT = 10000n;
const HASH = /^0x[0-9a-fA-F]{64}$/;
const SECRET_KEYS = new Set([
  "privatekey", "private_key", "mnemonic", "seed", "secretkey", "secret_key", "secret",
]);

function fail(message) {
  throw new Error(message);
}

function assertNoSecret(value, depth = 0) {
  if (depth > 8 || !value || typeof value !== "object") return;
  if (Array.isArray(value)) {
    for (const item of value) assertNoSecret(item, depth + 1);
    return;
  }
  for (const [key, nested] of Object.entries(value)) {
    if (SECRET_KEYS.has(String(key).toLowerCase())) {
      fail("a secret field can never enter Polymarket cycle evidence");
    }
    assertNoSecret(nested, depth + 1);
  }
}

function unsignedMicro(value, field) {
  if (typeof value !== "string") fail(`${field} money must be an exact decimal string`);
  const raw = value.trim();
  if (!/^\d+$/.test(raw)) fail(`${field} must be a non-negative integer in micro-USD`);
  return BigInt(raw);
}

function signedMicro(value, field) {
  if (typeof value !== "string") fail(`${field} money must be an exact decimal string`);
  const raw = value.trim();
  if (!/^-?\d+$/.test(raw)) fail(`${field} must be a signed integer in micro-USD`);
  return BigInt(raw);
}

function centString(micro, field) {
  if (micro % MICRO_PER_CENT !== 0n) {
    fail(`${field} is not an exact US cent and cannot enter the cent ledger`);
  }
  return (micro / MICRO_PER_CENT).toString();
}

function requireHash(value, field) {
  const raw = String(value == null ? "" : value).trim();
  if (!HASH.test(raw)) fail(`${field} is not a transaction hash`);
  return raw;
}

function cycleLedgerEntries(cycle) {
  if (!cycle || typeof cycle !== "object") fail("a Polymarket cycle must be an object");
  assertNoSecret(cycle);

  const condition = String(cycle.condition_id == null ? "" : cycle.condition_id).trim();
  if (!HASH.test(condition)) fail("condition_id is not a Polymarket condition hash");
  const expectedCycleId = `polymarket:${condition}`;
  if (cycle.cycle_id !== expectedCycleId) fail(`cycle_id must be ${expectedCycleId}`);
  if (cycle.receipt_status !== "0x1") fail("the redeem receipt must have status 0x1");
  const tradeTx = requireHash(cycle.trade_tx_hash, "trade_tx_hash");
  const redeemTx = requireHash(cycle.redeem_tx_hash, "redeem_tx_hash");

  const deployed = unsignedMicro(cycle.deployed_microusd, "deployed_microusd");
  const recovered = unsignedMicro(cycle.recovered_microusd, "recovered_microusd");
  const fee = unsignedMicro(cycle.fee_microusd, "fee_microusd");
  const realized = signedMicro(cycle.realized_pnl_microusd, "realized_pnl_microusd");
  const expectedRealized = recovered - deployed - fee;
  if (realized !== expectedRealized) {
    fail(`realized P&L formula mismatch: expected ${expectedRealized}, got ${realized}`);
  }

  const meta = {
    cycle_id: expectedCycleId,
    condition_id: condition,
    deployed_microusd: deployed.toString(),
    recovered_microusd: recovered.toString(),
    fee_microusd: fee.toString(),
    realized_pnl_microusd: realized.toString(),
    trade_tx_hash: tradeTx,
    redeem_tx_hash: redeemTx,
    receipt_status: cycle.receipt_status,
    evidence: cycle.evidence == null ? {} : cycle.evidence,
  };
  const shared = {
    wallet_address: cycle.wallet_address,
    currency: "USD",
    occurred_at: cycle.occurred_at,
    source: "polymarket_cycle",
    meta,
  };

  // Validate identity and evidence even when a perfectly flat, fee-free cycle
  // produces no accounting row.
  normaliseEntry({
    ...shared,
    entry_key: `${expectedCycleId}:validation`,
    kind: "financial_internal_move",
    amount_minor: "0",
    tx_hash: redeemTx,
  });

  const entries = [];
  const delta = recovered - deployed;
  if (delta > 0n) {
    entries.push(normaliseEntry({
      ...shared,
      entry_key: `${expectedCycleId}:income`,
      kind: "financial_external_income",
      amount_minor: centString(delta, "cycle income"),
      tx_hash: redeemTx,
    }));
  } else if (delta < 0n) {
    entries.push(normaliseEntry({
      ...shared,
      entry_key: `${expectedCycleId}:loss`,
      kind: "financial_realized_loss",
      amount_minor: centString(-delta, "cycle loss"),
      tx_hash: redeemTx,
    }));
  }
  if (fee > 0n) {
    entries.push(normaliseEntry({
      ...shared,
      entry_key: `${expectedCycleId}:fee`,
      kind: "financial_fee",
      amount_minor: centString(fee, "cycle fee"),
      tx_hash: tradeTx,
    }));
  }

  return Object.freeze(entries);
}

async function recordPolymarketCycle(cycle, opts = {}) {
  const entries = cycleLedgerEntries(cycle);
  const recordEntry = opts.recordEntry || recordEarnLoopRevenue;
  const recordOpts = opts.recordOpts || opts;
  if (typeof recordEntry !== "function") fail("recordEntry must be a function");
  const writes = [];
  for (const entry of entries) {
    writes.push(await recordEntry(entry, recordOpts));
  }
  return Object.freeze({
    ok: true,
    cycle_id: cycle.cycle_id,
    entries,
    writes: Object.freeze(writes),
  });
}

module.exports = { cycleLedgerEntries, recordPolymarketCycle };
