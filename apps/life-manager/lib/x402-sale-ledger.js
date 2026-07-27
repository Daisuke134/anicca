"use strict";

const { toChecksumAddress } = require("./agent-wallet.js");
const { normaliseEntry, usdMinorFromAtomic } = require("./earnings-ledger.js");
const { recordEarnLoopRevenue } = require("./earnings-runtime.js");

const ALLOWED_SOURCES = new Set(["x402-image", "the402", "clawmerchants"]);
const SOURCE_SALE_ID = /^[a-zA-Z0-9][a-zA-Z0-9._:-]{0,191}$/;
const OFFER_ID = /^[a-zA-Z0-9/][a-zA-Z0-9._:/-]{0,191}$/;

function fail(message) {
  throw new Error(message);
}

function address(value, label) {
  const raw = String(value == null ? "" : value).trim().toLowerCase();
  if (!/^0x[0-9a-f]{40}$/.test(raw)) fail(`${label} must be an EVM address`);
  return raw;
}

function transactionHash(value) {
  const raw = String(value == null ? "" : value).trim().toLowerCase();
  if (!/^0x[0-9a-f]{64}$/.test(raw)) fail("tx must be a transaction hash");
  return raw;
}

function exactString(value, label, pattern) {
  if (typeof value !== "string" || !pattern.test(value)) fail(`${label} is invalid`);
  return value;
}

function ownedBoundary(values) {
  const set = new Set((Array.isArray(values) ? values : []).map((value) => address(value, "owned payTo")));
  if (set.size === 0) fail("ownedPayTos must contain at least one owned payTo");
  return set;
}

function saleLedgerEntry(input, options = {}) {
  if (!input || typeof input !== "object") fail("a verified x402 sale must be an object");
  if (!ALLOWED_SOURCES.has(input.source)) fail("x402 sale source is not allowed");
  const sourceSaleId = exactString(input.source_sale_id, "source sale id", SOURCE_SALE_ID);
  const offerId = exactString(input.offer_id, "offer id", OFFER_ID);
  const tx = transactionHash(input.tx);
  const payer = address(input.from, "payer address");
  const receiver = address(input.to, "receiver address");
  const payTo = address(input.payTo, "payTo address");
  const ownedPayTos = ownedBoundary(options.ownedPayTos);
  const selfWallets = new Set((Array.isArray(options.selfWallets) ? options.selfWallets : [])
    .map((value) => address(value, "self wallet")));

  if (!ownedPayTos.has(payTo)) fail("payTo is not an owned wallet");
  if (receiver !== payTo) fail("receiver must match payTo");
  if (selfWallets.has(payer) || ownedPayTos.has(payer)) fail("payer is a self wallet");
  if (input.finalized !== true) fail("sale receipt must be finalized");
  if (input.status !== "success") fail("sale receipt must be successful");
  if (input.external !== true) fail("sale must be classified as external");
  if (!Number.isSafeInteger(input.block) || input.block < 0) fail("receipt block must be a non-negative safe integer");
  if (typeof input.usdc_atomic !== "string") fail("usdc_atomic must be an exact decimal string");
  if (!/^\d+$/.test(input.usdc_atomic) || BigInt(input.usdc_atomic) <= 0n) {
    fail("USDC atomic amount must be a positive integer string");
  }
  const occurredAt = new Date(input.observed_at);
  if (typeof input.observed_at !== "string" || Number.isNaN(occurredAt.getTime())) {
    fail("observed_at must be a timestamp");
  }

  const entry = normaliseEntry({
    entry_key: `x402:${tx}:income`,
    wallet_address: toChecksumAddress(payTo.slice(2)),
    kind: "financial_external_income",
    amount_minor: usdMinorFromAtomic(input.usdc_atomic, 6),
    currency: "USD",
    occurred_at: occurredAt.toISOString(),
    tx_hash: tx,
    source: "x402_sale",
    meta: {
      protocol: "x402",
      network: "eip155:8453",
      marketplace: input.source,
      source_sale_id: sourceSaleId,
      offer_id: offerId,
      receipt_block: input.block,
      payer,
      pay_to: payTo,
      usdc_atomic: input.usdc_atomic,
      finalized: true,
      external: true,
    },
  });
  return entry;
}

async function recordX402Sale(input, options = {}) {
  const entry = saleLedgerEntry(input, options);
  const recordEntry = options.recordEntry || recordEarnLoopRevenue;
  return recordEntry(entry);
}

module.exports = {
  ALLOWED_SOURCES,
  saleLedgerEntry,
  recordX402Sale,
};
