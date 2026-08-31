"use strict";

const { recordEarnLoopRevenue } = require("./earnings-runtime.js");

const SOLANA_ADDRESS_RE = /^[1-9A-HJ-NP-Za-km-z]{32,44}$/;
const SOLANA_SIGNATURE_RE = /^[1-9A-HJ-NP-Za-km-z]{87,88}$/;
const LAMPORTS_PER_SOL = 1_000_000_000n;
const USD_MICROS = 1_000_000n;

function fail(message) {
  throw new Error(message);
}

function field(invoice, key) {
  return invoice?.[key] ?? invoice?.metadata?.[key] ?? null;
}

function decimalToAtomic(value, decimals, label) {
  const raw = String(value == null ? "" : value).trim();
  const match = /^(\d+)(?:\.(\d+))?$/.exec(raw);
  if (!match) fail(`${label} must be a non-negative decimal`);
  const fraction = match[2] || "";
  if (fraction.length > decimals) fail(`${label} has more than ${decimals} decimals`);
  return (BigInt(match[1]) * (10n ** BigInt(decimals))) +
    BigInt((fraction + "0".repeat(decimals)).slice(0, decimals));
}

function invoiceSignature(invoice) {
  const signature = String(field(invoice, "merchant_tx_hash") || "").trim();
  if (!SOLANA_SIGNATURE_RE.test(signature)) fail("paid invoice has no valid Solana merchant_tx_hash");
  return signature;
}

function accountKeyString(value) {
  if (typeof value === "string") return value;
  return String(value?.pubkey || "");
}

function assertInvoiceMatches(delivery, invoice) {
  if (String(invoice?.status || "").toLowerCase() !== "paid") fail("uGig invoice is not paid");
  if (invoice?.application_id !== delivery.application_id) fail("uGig invoice application does not match delivery");
  if (String(invoice?.currency || "").toUpperCase() !== "USD") fail("uGig invoice currency must be USD");
  if (decimalToAtomic(invoice?.amount_usd ?? invoice?.amount, 6, "invoice amount") !==
      decimalToAtomic(delivery.amount_usd, 6, "delivery amount")) {
    fail("uGig invoice amount does not match delivery");
  }
  const receiverCurrency = String(
    field(invoice, "receiver_payment_currency") ||
    field(invoice, "payment_currency") ||
    "",
  ).toLowerCase();
  if (receiverCurrency !== "sol") {
    fail("uGig invoice receiver payment currency must be SOL");
  }
  const settlementChain = String(field(invoice, "settlement_chain") || "").toLowerCase();
  if (!["sol", "solana"].includes(settlementChain)) fail("uGig invoice settlement chain must be Solana");
  const recipient = String(
    invoice?.merchant_wallet_address ??
    invoice?.payment_wallet_address ??
    invoice?.wallet_address ??
    invoice?.metadata?.merchant_wallet_address ??
    delivery.merchant_wallet_address ??
    "",
  ).trim();
  if (!SOLANA_ADDRESS_RE.test(recipient) || recipient !== delivery.merchant_wallet_address) {
    fail("uGig invoice recipient does not match delivery wallet");
  }
  const paidAt = new Date(String(field(invoice, "paid_at") || ""));
  if (!Number.isFinite(paidAt.getTime())) fail("paid invoice has no valid paid_at");
  return { recipient, paidAt: paidAt.toISOString() };
}

async function verifyUgigSolanaInvoice(delivery, invoice, options = {}) {
  if (!delivery || !invoice) fail("delivery and invoice are required");
  if (typeof options.rpcCall !== "function") fail("a Solana RPC caller is required");
  const { recipient, paidAt } = assertInvoiceMatches(delivery, invoice);
  const signature = invoiceSignature(invoice);
  const expectedLamports = decimalToAtomic(field(invoice, "amount_crypto"), 9, "amount_crypto");
  if (expectedLamports <= 0n) fail("amount_crypto must be positive");

  const statusResponse = await options.rpcCall(
    "getSignatureStatuses",
    [[signature], { searchTransactionHistory: true }],
  );
  const status = statusResponse?.value?.[0];
  if (!status || status.err != null || status.confirmationStatus !== "finalized") {
    fail("Solana payout is not finalized");
  }

  const transaction = await options.rpcCall("getTransaction", [
    signature,
    { commitment: "finalized", maxSupportedTransactionVersion: 0 },
  ]);
  if (!transaction || transaction.meta?.err != null) fail("Solana payout transaction failed or is unavailable");
  if (!transaction.transaction?.signatures?.includes(signature)) fail("Solana transaction signature does not match invoice");

  const keys = (transaction.transaction?.message?.accountKeys || []).map(accountKeyString);
  const recipientIndex = keys.indexOf(recipient);
  if (recipientIndex < 0) fail("Solana payout recipient is absent from transaction");
  const payer = keys[0];
  const owned = new Set((options.ownedWalletAddresses || [recipient]).map(String));
  if (!payer || payer === recipient || owned.has(payer)) fail("Solana payout is self-funded or has no external payer");

  const pre = transaction.meta?.preBalances?.[recipientIndex];
  const post = transaction.meta?.postBalances?.[recipientIndex];
  if (!Number.isSafeInteger(pre) || !Number.isSafeInteger(post) || post <= pre) {
    fail("Solana payout did not increase the recipient balance");
  }
  const receivedLamports = BigInt(post) - BigInt(pre);
  if (receivedLamports < expectedLamports) fail("Solana payout is underpaid");

  return Object.freeze({
    signature,
    recipient,
    payer,
    slot: transaction.slot,
    block_time: Number.isInteger(transaction.blockTime)
      ? new Date(transaction.blockTime * 1000).toISOString()
      : null,
    paid_at: paidAt,
    received_lamports: receivedLamports.toString(),
    expected_lamports: expectedLamports.toString(),
    finalized: true,
  });
}

function ugigSolanaLedgerEntry(delivery, invoice, proof) {
  if (!proof?.finalized) fail("a finalized Solana proof is required");
  const invoiceId = String(invoice?.id || invoice?.invoice_id || "").trim();
  if (!invoiceId) fail("paid invoice id is required");
  const usdMicros = decimalToAtomic(delivery.amount_usd, 6, "delivery amount");
  if (usdMicros <= 0n || usdMicros > BigInt(Number.MAX_SAFE_INTEGER) * USD_MICROS) {
    fail("delivery amount is outside the supported range");
  }
  return {
    entry_key: `ugig:invoice:${invoiceId}:merchant-payout`,
    wallet_address: proof.recipient,
    kind: "financial_external_income",
    amount_atomic: usdMicros.toString(),
    amount_decimals: 6,
    currency: "USD",
    occurred_at: proof.paid_at,
    tx_hash: proof.signature,
    source: "ugig_work",
    meta: {
      chain: "solana:mainnet",
      finalized: true,
      gig_id: delivery.gig_id,
      application_id: delivery.application_id,
      invoice_id: invoiceId,
      payer: proof.payer,
      slot: proof.slot,
      block_time: proof.block_time,
      received_lamports: proof.received_lamports,
      expected_lamports: proof.expected_lamports,
      external: true,
    },
  };
}

async function processUgigPaidInvoice(delivery, invoice, options = {}) {
  const proof = await verifyUgigSolanaInvoice(delivery, invoice, options);
  const entry = ugigSolanaLedgerEntry(delivery, invoice, proof);
  const recordEntry = options.recordEntry || recordEarnLoopRevenue;
  return recordEntry(entry, options);
}

module.exports = {
  verifyUgigSolanaInvoice,
  ugigSolanaLedgerEntry,
  processUgigPaidInvoice,
  decimalToAtomic,
};
