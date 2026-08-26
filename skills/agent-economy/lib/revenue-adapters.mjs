// Provider-owned revenue readback adapters.
//
// These adapters are deliberately boring: a lane owns its provider API/browser readback and
// passes the resulting, secret-free projection here.  A row is revenue only when the projection
// contains a terminal settlement state, an explicit payer/recipient, exact signed money fields,
// and provider/chain proof.  Everything else is a durable rejection candidate.  The adapters do
// not execute a provider action and do not infer a payout from an offer, view, draft, submission,
// or payout request.

import { createHash } from "node:crypto";
import { appendFile, mkdir, readFile } from "node:fs/promises";
import { dirname } from "node:path";

import {
  normalizeRevenueReceipt,
  RevenueReceiptValidationError,
} from "./revenue-receipt.mjs";
import { reconcileRevenueReceipts } from "./money-truth.mjs";

export const REVENUE_REJECTION_SCHEMA_VERSION = 1;
export const REVENUE_REJECTION_KIND = "revenue_rejection";

const TERMINAL = new Set([
  "settled", "paid", "received", "completed", "refunded", "charged_back", "chargeback", "reversed",
]);
const STATUS_ALIASES = new Map([
  ["0x1", "settled"], ["success", "settled"], ["succeeded", "settled"],
  ["検収", "settled"], ["検収完了", "settled"], ["支払", "paid"], ["支払完了", "paid"],
  ["awarded", "paid"], ["award", "paid"], ["verified_received", "received"],
  ["refunded", "refunded"], ["refund_succeeded", "refunded"],
]);
const EXPECTED_ASSET = new Map([
  ["coconala", "JPY"], ["lancers", "JPY"], ["taskmarket", "USDC"], ["x402", "USDC"], ["stripe", "USD"],
]);
const NESTED_KEYS = ["settlement", "settlement_readback", "provider_readback", "payout", "payment", "award", "finance"];

const asObject = (value) => value && typeof value === "object" && !Array.isArray(value) ? value : null;
const asText = (value) => (typeof value === "string" || typeof value === "number") && String(value).trim() ? String(value).trim() : null;

function directOrNested(input, keys) {
  const object = asObject(input);
  if (!object) return undefined;
  for (const key of keys) {
    if (object[key] !== undefined && object[key] !== null) return object[key];
  }
  for (const nestedKey of NESTED_KEYS) {
    const nested = asObject(object[nestedKey]);
    if (!nested) continue;
    for (const key of keys) {
      if (nested[key] !== undefined && nested[key] !== null) return nested[key];
    }
  }
  return undefined;
}

function sourceId(provider, row) {
  const explicit = directOrNested(row, [
    "source_record_id", "sourceRecordId", "idempotency_key", "idempotencyKey", "requestId", "request_id",
    "proposal_id", "proposalId", "taskId", "task_id", "submissionId", "submission_id", "external_receipt_id",
    "externalReceiptId", "provider_receipt_id", "providerReceiptId", "payout_receipt_id", "payment_receipt_id",
    "transaction", "tx_hash", "txHash", "id",
  ]);
  if (asText(explicit)) return asText(explicit);
  const identity = {
    provider,
    amount: directOrNested(row, ["gross", "gross_amount", "amount", "jpy", "amount_atomic", "gross_atomic"]),
    occurred_at: directOrNested(row, ["occurred_at", "occurredAt", "ts", "timestamp"]),
  };
  return createHash("sha256").update(JSON.stringify(identity), "utf8").digest("hex");
}

function rejection(provider, row, reason, code = "MISSING_SETTLEMENT_PROOF", options = {}) {
  const id = sourceId(provider, row);
  const rejectionKey = `revenue-rejection:v1:${createHash("sha256")
    .update(JSON.stringify({ provider, source_record_id: id, code, reason }), "utf8")
    .digest("hex")}`;
  const observedAt = directOrNested(row, ["occurred_at", "occurredAt", "ts", "timestamp"])
    ?? options.observedAt ?? new Date().toISOString();
  return Object.freeze({
    schema_version: REVENUE_REJECTION_SCHEMA_VERSION,
    kind: REVENUE_REJECTION_KIND,
    provider,
    source_record_id: id,
    rejection_key: rejectionKey,
    code,
    reason,
    observed_at: normalizeObservedAt(observedAt),
  });
}

function normalizedProvider(provider) {
  const value = String(provider || "").trim().toLowerCase().replace(/[ _]+/g, "-");
  if (value === "writer" || value === "writer-stripe" || value === "stripe-writer") return "stripe";
  if (value === "x402-sell" || value === "x402-seller") return "x402";
  if (value === "task-market" || value === "task_market") return "taskmarket";
  return value;
}

function normalizeObservedAt(value) {
  const date = new Date(typeof value === "number" ? (value > 1e12 ? value : value * 1000) : String(value));
  if (!Number.isFinite(date.getTime())) return new Date(0).toISOString();
  return date.toISOString();
}

function terminalState(row, keys = ["terminal_state", "terminalState", "settlement_state", "settlementStatus", "status"]) {
  const raw = directOrNested(row, keys);
  if (raw === true) return "settled";
  const text = asText(raw);
  if (!text) throw new AdapterFailure("NON_TERMINAL", "terminal settlement state is missing");
  const state = text.toLowerCase().replace(/[ -]+/g, "_");
  const mapped = STATUS_ALIASES.get(state) || STATUS_ALIASES.get(text) || state;
  if (!TERMINAL.has(mapped)) throw new AdapterFailure("NON_TERMINAL", `settlement state ${JSON.stringify(text)} is not terminal`);
  return mapped;
}

function assetFor(row, provider, options = {}) {
  const raw = directOrNested(row, ["asset", "currency", "currency_code", "currencyCode", "token"])
    ?? options.asset ?? EXPECTED_ASSET.get(provider);
  const asset = asText(raw)?.toUpperCase();
  if (!asset || !/^[A-Z][A-Z0-9]{2,9}$/.test(asset)) throw new AdapterFailure("MALFORMED_CURRENCY", "currency/asset is malformed");
  const expected = options.expectedAsset ?? EXPECTED_ASSET.get(provider);
  if (expected && asset !== String(expected).toUpperCase()) {
    throw new AdapterFailure("MALFORMED_CURRENCY", `currency ${asset} is not the ${expected} lane asset`);
  }
  return asset;
}

function decimalText(value, field, { allowNegative = false } = {}) {
  if (typeof value === "number") {
    if (!Number.isFinite(value)) throw new AdapterFailure("MALFORMED_AMOUNT", `${field} is not finite`);
    value = String(value);
  } else if (typeof value === "bigint") {
    value = value.toString();
  } else if (typeof value === "string") {
    value = value.trim().replace(/^\$/, "");
  } else {
    throw new AdapterFailure("MALFORMED_AMOUNT", `${field} is missing or malformed`);
  }
  const pattern = allowNegative ? /^-?\d+(?:\.\d+)?$/ : /^\d+(?:\.\d+)?$/;
  if (!pattern.test(value)) throw new AdapterFailure("MALFORMED_AMOUNT", `${field} is not a decimal amount`);
  return value;
}

function atomicToDecimal(value, field, decimals = 6) {
  const raw = decimalText(value, field);
  if (!/^\d+$/.test(raw)) throw new AdapterFailure("MALFORMED_AMOUNT", `${field} must be an integer atomic amount`);
  const scale = Number(decimals);
  if (!Number.isSafeInteger(scale) || scale < 0 || scale > 18) throw new AdapterFailure("MALFORMED_AMOUNT", "asset decimals are invalid");
  const digits = raw.padStart(scale + 1, "0");
  if (scale === 0) return digits;
  const split = digits.length - scale;
  return `${digits.slice(0, split)}.${digits.slice(split)}`.replace(/\.0+$/, "").replace(/(\.\d*?)0+$/, "$1");
}

function moneyValue(row, keys, atomicKeys = [], options = {}) {
  const atomic = directOrNested(row, atomicKeys);
  if (atomic !== undefined) return atomicToDecimal(atomic, keys[0], options.decimals ?? directOrNested(row, ["decimals", "asset_decimals", "assetDecimals"]) ?? 6);
  const value = directOrNested(row, keys);
  if (value && typeof value === "object" && !Array.isArray(value)) {
    return decimalText(value.amount ?? value.value, keys[0]);
  }
  return decimalText(value, keys[0]);
}

function optionalMoney(row, keys, atomicKeys = [], options = {}) {
  const value = directOrNested(row, atomicKeys.length ? [...atomicKeys, ...keys] : keys);
  if (value === undefined || value === null || value === "") return "0";
  return moneyValue(row, keys, atomicKeys, options);
}

function identity(row, options = {}) {
  const payer = asText(directOrNested(row, ["payer", "external_payer", "externalPayer", "buyer_id", "buyerId", "customer_id", "customerId", "buyer", "client_id", "clientId"]))
    ?? asText(options.payer);
  const recipient = asText(directOrNested(row, ["recipient", "recipient_id", "recipientId", "pay_to", "payTo", "payout_account", "payoutAccount", "account_id", "accountId", "wallet"]))
    ?? asText(options.recipient ?? options.accountIdentity);
  if (!payer) throw new AdapterFailure("MISSING_IDENTITY", "external payer is missing");
  if (!recipient) throw new AdapterFailure("MISSING_IDENTITY", "configured recipient/account identity is missing");
  if (payer.toLowerCase() === recipient.toLowerCase()) throw new AdapterFailure("SELF_PAYMENT", "payer and recipient are the same identity");
  const selfPayers = options.selfPayers ?? options.selfWallets ?? [];
  const values = Array.isArray(selfPayers) ? selfPayers : [selfPayers];
  if (values.some((item) => asText(item)?.toLowerCase() === payer.toLowerCase())) {
    throw new AdapterFailure("SELF_PAYMENT", "payer is an instance-controlled identity");
  }
  return { payer, recipient };
}

function providerProof(row, labels = {}) {
  const raw = directOrNested(row, ["proof", "chain_provider_proof", "chainProviderProof", "provider_proof", "providerProof", "settlement_proof", "settlementProof"]);
  const object = asObject(raw);
  const verified = object?.verified === true
    || directOrNested(row, labels.verificationKeys || ["verified", "proof_verified", "proofVerified", "settlement_verified", "settlementVerified", "provider_proof_verified", "providerProofVerified"]) === true;
  const providerId = asText(object && directOrNested(object, ["provider_receipt_id", "providerReceiptId", "receipt_id", "receiptId"]))
    ?? asText(directOrNested(row, labels.providerKeys || ["provider_receipt_id", "providerReceiptId", "receipt_id", "receiptId", "payout_receipt_id", "payment_receipt_id", "award_receipt_id", "settlement_receipt_id"]));
  if (providerId) {
    if (!verified) throw new AdapterFailure("UNVERIFIED_SETTLEMENT_PROOF", "provider receipt id is not explicitly verified");
    return { provider_receipt_id: providerId, verified: true };
  }
  const txHash = asText(object ? directOrNested(object, ["tx_hash", "txHash", "transaction_hash", "transactionHash"]) : undefined)
    ?? asText(directOrNested(row, labels.txKeys || ["tx_hash", "txHash", "transaction_hash", "transactionHash", "transaction"]));
  const chainId = (object ? directOrNested(object, ["chain_id", "chainId", "network"]) : undefined)
    ?? directOrNested(row, labels.chainKeys || ["chain_id", "chainId", "network"]);
  const logIndex = (object ? directOrNested(object, ["log_index", "logIndex"]) : undefined)
    ?? directOrNested(row, labels.logKeys || ["log_index", "logIndex"]);
  if (txHash || chainId !== undefined || logIndex !== undefined) {
    if (!verified || !txHash || chainId === undefined || logIndex === undefined) {
      throw new AdapterFailure("MISSING_SETTLEMENT_PROOF", "chain settlement proof requires verified tx, chain, and log index");
    }
    return { chain_id: chainId, tx_hash: txHash, log_index: logIndex, verified: true };
  }
  throw new AdapterFailure("MISSING_SETTLEMENT_PROOF", "provider/chain settlement proof is absent");
}

function buildReceipt(provider, row, options, config) {
  const asset = assetFor(row, provider, options);
  const { payer, recipient } = identity(row, options);
  const gross = moneyValue(row, config.grossKeys, config.grossAtomicKeys, { decimals: config.decimals ?? options.decimals });
  const fee = config.feeKeys ? optionalMoney(row, config.feeKeys, config.feeAtomicKeys || [], { decimals: config.decimals ?? options.decimals }) : "0";
  const refund = config.refundKeys ? optionalMoney(row, config.refundKeys, config.refundAtomicKeys || [], { decimals: config.decimals ?? options.decimals }) : "0";
  const proof = providerProof(row, config.proof || {});
  const terminal_state = terminalState(row, config.statusKeys);
  const occurred_at = directOrNested(row, ["occurred_at", "occurredAt", "timestamp", "ts", "created_at", "createdAt"]);
  if (occurred_at === undefined || occurred_at === null) throw new AdapterFailure("MISSING_TIMESTAMP", "settlement timestamp is missing");
  const receipt = normalizeRevenueReceipt({
    provider, payer, recipient, gross, fee, refund, asset, proof, terminal_state, occurred_at,
  }, { selfPayers: options.selfPayers ?? options.selfWallets });
  const expectedPayout = directOrNested(row, config.netKeys || []);
  if (expectedPayout !== undefined && expectedPayout !== null) {
    const payout = decimalText(expectedPayout, "payout/net");
    if (Number(payout) !== Number(receipt.signed_net)) throw new AdapterFailure("ARITHMETIC_MISMATCH", "provider payout does not equal signed net");
  }
  return receipt;
}

class AdapterFailure extends Error {
  constructor(code, message) {
    super(message);
    this.name = "AdapterFailure";
    this.code = code;
  }
}

function adaptOne(providerInput, row, options, config) {
  const provider = normalizedProvider(providerInput);
  try {
    if (!asObject(row)) throw new AdapterFailure("MALFORMED_SOURCE", "provider row must be an object");
    return { ok: true, receipt: buildReceipt(provider, row, options, config) };
  } catch (error) {
    const code = error instanceof RevenueReceiptValidationError ? error.code : error?.code || "REJECTED";
    const reason = error instanceof RevenueReceiptValidationError ? error.message.replace(/^revenue-receipt\s+[^:]+:\s*/, "") : String(error?.message || error);
    return { ok: false, rejection: rejection(provider, row, reason, code, options) };
  }
}

export function adaptCoconala(row, options = {}) {
  const nestedPayout = asObject(row?.payout);
  const input = nestedPayout ? { ...row, ...nestedPayout } : row;
  const status = directOrNested(input, ["payout_status", "payoutState", "settlement_state", "status"]);
  if (status && ["pending", "requested", "申請済み", "in_transit"].includes(String(status).toLowerCase())) {
    return { ok: false, rejection: rejection("coconala", row, "payout is pending or only requested", "PENDING_SETTLEMENT", options) };
  }
  if (row?.net_of_fee === true && directOrNested(row, ["gross_jpy", "gross_amount_jpy", "gross_amount", "gross"]) === undefined) {
    return { ok: false, rejection: rejection("coconala", row, "Coconala source exposes net-only sale without gross/fee settlement", "NET_ONLY_SOURCE", options) };
  }
  return adaptOne("coconala", input, options, {
    grossKeys: ["gross_jpy", "gross_amount_jpy", "gross_amount", "gross", "amount_jpy", "amount"],
    feeKeys: ["fee_jpy", "fee_amount_jpy", "fee_amount", "fee", "platform_fee_jpy"],
    refundKeys: ["refund_jpy", "refund_amount_jpy", "refund_amount", "refund"],
    netKeys: ["payout_jpy", "payout_amount_jpy", "payout_amount", "net_jpy", "net_amount"],
    statusKeys: ["payout_status", "payoutState", "terminal_state", "settlement_state", "status"],
    proof: {
      providerKeys: ["payout_receipt_id", "payoutReceiptId", "provider_receipt_id", "providerReceiptId", "settlement_receipt_id"],
      verificationKeys: ["payout_proof_verified", "payoutProofVerified", "settlement_verified", "settlementVerified", "proof_verified", "verified"],
    },
  });
}

export function adaptLancers(row, options = {}) {
  if (row?.source_complete === false || row?.finance?.source_complete === false) {
    return { ok: false, rejection: rejection("lancers", row, "Lancers finance readback is incomplete", "FINANCE_READBACK_INCOMPLETE", options) };
  }
  return adaptOne("lancers", row, options, {
    grossKeys: ["gross_jpy", "gross_amount_jpy", "gross_amount", "gross", "amount_jpy", "amount"],
    feeKeys: ["fee_jpy", "fee_amount_jpy", "fee_amount", "fee", "platform_fee_jpy"],
    refundKeys: ["refund_jpy", "refund_amount_jpy", "refund_amount", "refund"],
    netKeys: ["payout_jpy", "payout_amount_jpy", "payout_amount", "net_jpy", "net_amount"],
    statusKeys: ["payment_status", "payout_status", "terminal_state", "settlement_state", "status"],
    proof: {
      providerKeys: ["payment_receipt_id", "paymentReceiptId", "payout_receipt_id", "payoutReceiptId", "provider_receipt_id", "providerReceiptId", "settlement_receipt_id"],
      verificationKeys: ["payment_proof_verified", "paymentProofVerified", "payout_proof_verified", "payoutProofVerified", "settlement_verified", "settlementVerified", "proof_verified", "verified"],
    },
  });
}

export function adaptTaskMarket(row, options = {}) {
  const status = directOrNested(row, ["award_status", "awardStatus", "payout_status", "payoutStatus", "terminal_state", "status"]);
  if (!status || ["submitted", "accepted", "pending", "processing", "open"].includes(String(status).toLowerCase())) {
    return { ok: false, rejection: rejection("taskmarket", row, "TaskMarket award is not a terminal payout", "PENDING_SETTLEMENT", options) };
  }
  return adaptOne("taskmarket", row, options, {
    grossKeys: ["gross", "gross_usdc", "award_amount", "award_amount_usdc", "payout_amount", "settled_amount"],
    grossAtomicKeys: ["gross_atomic", "award_amount_atomic", "payout_amount_atomic", "settled_amount_atomic"],
    feeKeys: ["fee", "fee_usdc", "fee_amount"],
    feeAtomicKeys: ["fee_atomic", "fee_amount_atomic"],
    refundKeys: ["refund", "refund_usdc", "refund_amount"],
    refundAtomicKeys: ["refund_atomic", "refund_amount_atomic"],
    statusKeys: ["award_status", "awardStatus", "payout_status", "payoutStatus", "terminal_state", "status"],
    proof: {
      providerKeys: ["award_receipt_id", "awardReceiptId", "payout_receipt_id", "payoutReceiptId", "settlement_receipt_id", "settlementReceiptId", "provider_receipt_id", "providerReceiptId"],
      verificationKeys: ["award_proof_verified", "awardProofVerified", "payout_proof_verified", "payoutProofVerified", "settlement_verified", "settlementVerified", "proof_verified", "verified"],
    },
  });
}

export function adaptX402(row, options = {}) {
  const nested = asObject(row?.payment_response) || asObject(row?.paymentResponse);
  const input = nested ? { ...row, ...nested } : row;
  if (input?.settled !== true && input?.success !== true) {
    return { ok: false, rejection: rejection("x402", row, "x402 payment did not have success:true terminal readback", "PENDING_SETTLEMENT", options) };
  }
  return adaptOne("x402", input, options, {
    grossKeys: ["settled_amount", "settledAmount", "amount", "gross", "payment_amount"],
    grossAtomicKeys: ["settled_amount_atomic", "settledAmountAtomic", "amount_atomic", "amountAtomic"],
    feeKeys: ["fee", "fee_amount"],
    refundKeys: ["refund", "refund_amount"],
    statusKeys: ["terminal_state", "settlement_state", "status", "settled", "success"],
    proof: {
      providerKeys: ["provider_receipt_id", "providerReceiptId", "settlement_receipt_id", "settlementReceiptId"],
      txKeys: ["tx_hash", "txHash", "transaction_hash", "transactionHash", "transaction"],
      chainKeys: ["chain_id", "chainId", "network"],
      logKeys: ["log_index", "logIndex"],
      verificationKeys: ["settlement_verified", "settlementVerified", "proof_verified", "proofVerified", "verified"],
    },
  });
}

function writerRows(value) {
  if (Array.isArray(value)) return value;
  if (asObject(value)) {
    if (Array.isArray(value.rows)) return value.rows;
    return [value];
  }
  return [];
}

function writerProof(row, keys) {
  const candidate = asText(directOrNested(row, ["provider_receipt_id", "providerReceiptId"]));
  if (candidate) return providerProof({ ...row, provider_receipt_id: candidate }, {
    providerKeys: ["provider_receipt_id"], verificationKeys: keys,
  });
  // The shipped Stripe observer names the immutable object id and dashboard URL but predates the
  // explicit proof_verified marker.  Those two fields are an official readback boundary; enrich a
  // copy only (never the outbox) so current rows remain consumable without trusting free-form IDs.
  const externalId = asText(directOrNested(row, ["external_receipt_id", "externalReceiptId"]));
  const sourceUrl = asText(directOrNested(row, ["source_url", "sourceUrl"]));
  if (externalId && row?.test === false && /^https:\/\/dashboard\.stripe\.com\//.test(sourceUrl || "")) {
    return providerProof({ ...row, provider_receipt_id: externalId, proof_verified: true }, {
      providerKeys: ["provider_receipt_id"], verificationKeys: ["proof_verified", ...keys],
    });
  }
  return providerProof(row, { providerKeys: ["external_receipt_id", "externalReceiptId"], verificationKeys: keys });
}

export function adaptWriterStripe(value, options = {}) {
  const rows = writerRows(value);
  const accepted = [];
  const rejected = [];
  const moneyRows = rows.filter((row) => row?.receipt_type === "money" || row?.type === "money");
  const feeRows = rows.filter((row) => row?.receipt_type === "fee" || row?.type === "fee");
  const refundRows = rows.filter((row) => row?.receipt_type === "refund" || row?.type === "refund");
  const feeFor = (money) => feeRows.find((fee) => String(fee?.money_external_receipt_id || fee?.moneyExternalReceiptId || "") === String(money?.external_receipt_id || money?.externalReceiptId || ""));
  const lineageMatches = (a, b) => String(a?.money_external_receipt_id || a?.moneyExternalReceiptId || a?.external_receipt_id || a?.externalReceiptId || "") === String(b?.external_receipt_id || b?.externalReceiptId || "")
    || (a?.artifact_id && b?.artifact_id && a.artifact_id === b.artifact_id && a?.run_id === b?.run_id);

  for (const money of moneyRows) {
    const rejectRow = (reason, code) => rejected.push(rejection("stripe", money, reason, code, options));
    if (money?.test === true || money?.livemode === false || String(money?.status || "").toLowerCase() === "test") {
      rejectRow("Stripe test-mode money is not external revenue", "TEST_RECEIPT");
      continue;
    }
    if (!TERMINAL.has(STATUS_ALIASES.get(String(money?.status || "").toLowerCase()) || String(money?.status || "").toLowerCase())) {
      rejectRow("Stripe money is pending or lacks a terminal received state", "PENDING_SETTLEMENT");
      continue;
    }
    const fee = feeFor(money);
    const feeStatus = String(fee?.status || "").toLowerCase();
    if (!fee || fee?.test === true || fee?.livemode === false || (feeStatus !== "verified" && !TERMINAL.has(STATUS_ALIASES.get(feeStatus) || feeStatus))) {
      rejectRow("Stripe money is not joined to a verified balance-transaction fee readback", "FEE_READBACK_UNJOINED");
      continue;
    }
    try {
      const asset = assetFor(money, "stripe", { ...options, asset: money.currency });
      if (fee.currency !== undefined && String(fee.currency).toUpperCase() !== asset) {
        throw new AdapterFailure("MALFORMED_CURRENCY", "Stripe fee currency does not match money currency");
      }
      const { payer, recipient } = identity(money, options);
      const gross = moneyValue(money, ["amount", "gross", "gross_amount"]);
      const feeAmount = moneyValue(fee, ["amount", "fee", "fee_amount"]);
      const proof = writerProof(money, ["proof_verified", "proofVerified", "provider_proof_verified", "providerProofVerified"]);
      // The fee row is part of the signed-net proof; a fee amount without its own official
      // balance-transaction identity is not enough to authorize the net contribution.
      writerProof(fee, ["proof_verified", "proofVerified", "provider_proof_verified", "providerProofVerified"]);
      const occurred_at = directOrNested(money, ["occurred_at", "occurredAt", "ts", "timestamp"]);
      const state = terminalState(money, ["terminal_state", "terminalState", "status"]);
      if (occurred_at === undefined || occurred_at === null) throw new AdapterFailure("MISSING_TIMESTAMP", "Stripe money timestamp is missing");
      const receipt = normalizeRevenueReceipt({ provider: "stripe", payer, recipient, gross, fee: feeAmount, refund: "0", asset, proof, terminal_state: state, occurred_at }, { selfPayers: options.selfPayers ?? options.selfWallets });
      const reportedNet = directOrNested(money, ["signed_net", "signedNet", "net", "net_amount", "netAmount"]);
      if (reportedNet !== undefined && reportedNet !== null
        && Number(decimalText(reportedNet, "net", { allowNegative: true })) !== Number(receipt.signed_net)) {
        throw new AdapterFailure("ARITHMETIC_MISMATCH", "Stripe net does not equal money minus fee");
      }
      accepted.push({ receipt, source_row: money });
    } catch (error) {
      const code = error instanceof RevenueReceiptValidationError ? error.code : error?.code || "REJECTED";
      const reason = error instanceof RevenueReceiptValidationError ? error.message.replace(/^revenue-receipt\s+[^:]+:\s*/, "") : String(error?.message || error);
      rejectRow(reason, code);
    }
  }

  for (const refund of refundRows) {
    const rejectRow = (reason, code) => rejected.push(rejection("stripe", refund, reason, code, options));
    if (refund?.test === true || refund?.livemode === false || String(refund?.status || "").toLowerCase() !== "refunded") {
      rejectRow("Stripe refund is not a terminal live refund", "PENDING_SETTLEMENT");
      continue;
    }
    const money = moneyRows.find((candidate) => lineageMatches(refund, candidate));
    if (!money) {
      rejectRow("Stripe refund is not joined to a known money receipt", "REFUND_READBACK_UNJOINED");
      continue;
    }
    try {
      const asset = assetFor(refund, "stripe", { ...options, asset: refund.currency || money.currency });
      if (money.currency !== undefined && String(money.currency).toUpperCase() !== asset) {
        throw new AdapterFailure("MALFORMED_CURRENCY", "Stripe refund currency does not match money currency");
      }
      const { payer, recipient } = identity(money, options);
      const proof = writerProof(refund, ["proof_verified", "proofVerified", "provider_proof_verified", "providerProofVerified"]);
      const occurred_at = directOrNested(refund, ["occurred_at", "occurredAt", "ts", "timestamp"]);
      if (occurred_at === undefined || occurred_at === null) throw new AdapterFailure("MISSING_TIMESTAMP", "Stripe refund timestamp is missing");
      const receipt = normalizeRevenueReceipt({ provider: "stripe", payer, recipient, gross: "0", fee: "0", refund: moneyValue(refund, ["amount", "refund", "refund_amount"]), asset, proof, terminal_state: "refunded", occurred_at }, { selfPayers: options.selfPayers ?? options.selfWallets });
      accepted.push({ receipt, source_row: refund });
    } catch (error) {
      const code = error instanceof RevenueReceiptValidationError ? error.code : error?.code || "REJECTED";
      const reason = error instanceof RevenueReceiptValidationError ? error.message.replace(/^revenue-receipt\s+[^:]+:\s*/, "") : String(error?.message || error);
      rejectRow(reason, code);
    }
  }
  return { accepted, rejected };
}

export function adaptRevenueRow(provider, row, options = {}) {
  const normalized = normalizedProvider(provider);
  if (normalized === "coconala") return adaptCoconala(row, options);
  if (normalized === "lancers") return adaptLancers(row, options);
  if (normalized === "taskmarket") return adaptTaskMarket(row, options);
  if (normalized === "x402") return adaptX402(row, options);
  if (normalized === "stripe") return adaptWriterStripe(row, options);
  return { ok: false, rejection: rejection(normalized || "unknown", row, "revenue provider adapter is unknown", "UNKNOWN_PROVIDER", options) };
}

export const adaptCoconalaRevenue = adaptCoconala;
export const adaptLancersRevenue = adaptLancers;
export const adaptTaskMarketRevenue = adaptTaskMarket;
export const adaptX402Revenue = adaptX402;
export const adaptWriterRevenue = adaptWriterStripe;

async function readJsonl(file) {
  try {
    const raw = await readFile(file, "utf8");
    const rows = [];
    for (const [index, line] of raw.split("\n").entries()) {
      if (!line.trim()) continue;
      try { rows.push(JSON.parse(line)); } catch { throw new Error(`revenue-adapters: corrupt rejection JSONL at line ${index + 1}`); }
    }
    return rows;
  } catch (error) {
    if (error?.code === "ENOENT") return [];
    throw error;
  }
}

async function persistRejections(file, rows) {
  if (!file || rows.length === 0) return { persisted: 0, duplicates: 0 };
  const existing = await readJsonl(file);
  const seen = new Set(existing.map((row) => row?.rejection_key).filter(Boolean));
  const fresh = [];
  let duplicates = 0;
  for (const row of rows) {
    if (seen.has(row.rejection_key)) { duplicates += 1; continue; }
    seen.add(row.rejection_key);
    fresh.push(row);
  }
  if (fresh.length) {
    await mkdir(dirname(file), { recursive: true, mode: 0o700 });
    await appendFile(file, fresh.map((row) => JSON.stringify(row)).join("\n") + "\n", { mode: 0o600 });
  }
  return { persisted: fresh.length, duplicates };
}

/** Adapt source rows and project only accepted receipts into the shared append-only journal. */
export async function projectRevenueReceipts({ journalPath, rejectionPath, provider, rows, options = {}, nowTs, selfPayers, selfWallets } = {}) {
  if (!journalPath) throw new TypeError("journalPath is required");
  if (!Array.isArray(rows)) throw new TypeError("rows must be an array");
  const adapterOptions = { ...options };
  if (selfPayers !== undefined) adapterOptions.selfPayers = selfPayers;
  if (selfWallets !== undefined) adapterOptions.selfWallets = selfWallets;
  const normalized = normalizedProvider(provider);
  const batch = normalized === "stripe"
    ? adaptWriterStripe(rows, adapterOptions)
    : rows.reduce((result, row) => {
      const outcome = adaptRevenueRow(normalized, row, adapterOptions);
      if (outcome.ok) result.accepted.push({ receipt: outcome.receipt, source_row: row });
      else result.rejected.push(outcome.rejection);
      return result;
    }, { accepted: [], rejected: [] });
  const rejectionResult = await persistRejections(rejectionPath || `${journalPath}.rejections.jsonl`, batch.rejected);
  const receiptResult = await reconcileRevenueReceipts({
    journalPath,
    receipts: batch.accepted.map((item) => item.receipt),
    nowTs,
    selfPayers: adapterOptions.selfPayers ?? adapterOptions.selfWallets ?? [],
  });
  return {
    accepted: receiptResult.accepted,
    duplicates: receiptResult.duplicates,
    rejected: batch.rejected.length,
    rejection_persisted: rejectionResult.persisted,
    rejection_duplicates: rejectionResult.duplicates,
    rows: receiptResult.rows,
    rejections: batch.rejected,
    summary: receiptResult.summary,
  };
}

export const projectRevenue = projectRevenueReceipts;
