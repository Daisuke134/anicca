"use strict";

const { toChecksumAddress } = require("./agent-wallet.js");
const { normaliseEntry, usdMinorFromAtomic } = require("./earnings-ledger.js");
const { recordEarnLoopRevenue } = require("./earnings-runtime.js");

const ALLOWED_SOURCES = new Set(["x402-image", "the402", "clawmerchants"]);
const SOURCE_SALE_ID = /^[a-zA-Z0-9][a-zA-Z0-9._:-]{0,191}$/;
const OFFER_ID = /^[a-zA-Z0-9/][a-zA-Z0-9._:/-]{0,191}$/;
const WORK_ID = /^[a-zA-Z0-9][a-zA-Z0-9._:-]{0,127}$/;

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

function revenueLedgerEntry(input, options = {}, recipe = "sale", provenance = null) {
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
  let workMeta = {};
  if (recipe === "work") {
    if (input.source !== "the402") fail("x402 work revenue must come from The402");
    if (!provenance || typeof provenance !== "object") fail("work provenance is required");
    const settlementId = exactString(provenance.settlementId, "settlement provenance", WORK_ID);
    const jobId = provenance.jobId == null ? null : exactString(provenance.jobId, "job provenance", WORK_ID);
    const postingId = provenance.postingId == null
      ? null
      : exactString(provenance.postingId, "posting provenance", WORK_ID);
    if (!jobId && !postingId) fail("job or posting provenance is required");
    if (sourceSaleId !== `the402:${settlementId}`) fail("settlement provenance does not match source sale id");
    workMeta = {
      recipe: "work",
      settlement_id: settlementId,
      job_id: jobId,
      posting_id: postingId,
    };
  } else if (recipe !== "sale") {
    fail("unknown x402 revenue recipe");
  }

  const entry = normaliseEntry({
    entry_key: `x402:${tx}:income`,
    wallet_address: toChecksumAddress(payTo.slice(2)),
    kind: "financial_external_income",
    amount_minor: usdMinorFromAtomic(input.usdc_atomic, 6),
    currency: "USD",
    occurred_at: occurredAt.toISOString(),
    tx_hash: tx,
    source: recipe === "work" ? "x402_work" : "x402_sale",
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
      ...workMeta,
    },
  });
  return entry;
}

function saleLedgerEntry(input, options = {}) {
  return revenueLedgerEntry(input, options, "sale");
}

function workLedgerEntry(input, options = {}, provenance) {
  return revenueLedgerEntry(input, options, "work", provenance);
}

async function recordX402Sale(input, options = {}) {
  const entry = saleLedgerEntry(input, options);
  const recordEntry = options.recordEntry || recordEarnLoopRevenue;
  return recordEntry(entry);
}

async function recordX402Work(input, provenance, options = {}) {
  const entry = workLedgerEntry(input, options, provenance);
  const recordEntry = options.recordEntry || recordEarnLoopRevenue;
  return recordEntry(entry);
}

module.exports = {
  ALLOWED_SOURCES,
  saleLedgerEntry,
  workLedgerEntry,
  recordX402Sale,
  recordX402Work,
};
