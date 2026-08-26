// money-truth.mjs — append-only receipt reconciliation for the agent-economy policy.
//
// The earn ledger is intentionally immutable. A provider/RPC can return no receipt at the moment
// a pass records its result, then the same transaction can be finalized later. This module keeps
// the original row untouched and joins a retryable {tx,status} sidecar onto it.

import { promises as fs } from "node:fs";
import path from "node:path";
import { randomUUID } from "node:crypto";
import {
  RevenueReceiptValidationError,
  canonicalRevenueReceiptKey,
  isNormalizedRevenueReceipt,
  normalizeRevenueReceipt,
  REVENUE_RECEIPT_SCHEMA_VERSION,
} from "./revenue-receipt.mjs";

const SWAP_SOURCES = new Set(["swap", "swap-eth-usdc", "swap-usdc-eth"]);
const INTERNAL_SOURCES = new Set(["reconcile", "receipt-reconcile"]);

const finitePositive = (value) => Number.isFinite(Number(value)) && Number(value) > 0;
const finiteNumber = (value) => Number.isFinite(Number(value));
const NORMALIZED_ASSETS = new Set(["USDC", "USD"]);
const VERIFIED_TERMINAL_STATES = new Set([
  "settled", "paid", "received", "completed", "refunded", "charged_back", "chargeback", "reversed",
]);

/** Return the stable proof identity for a ledger row, or null for narrations. */
export function receiptKey(row) {
  if (!row || typeof row !== "object") return null;
  if (typeof row.tx === "string" && row.tx.length > 0) return row.tx;
  if (typeof row.sig === "string" && row.sig.length > 0) return `sig:${row.sig}`;
  if (row.chain === "hyperliquid" && row.fill_tid != null) return `hyperliquid:${row.fill_tid}`;
  return null;
}

function isReceiptRetryCandidate(row) {
  return Boolean(
    row &&
    row.external === true &&
    finitePositive(row.net_usdc) &&
    typeof row.tx === "string" &&
    row.tx.length > 0
  );
}

/**
 * Retry only delayed EVM receipts. Failures are represented as status:null and remain retryable.
 * Duplicate transaction hashes are fetched once and returned once, preserving first-seen order.
 */
export async function reconcilePendingReceipts(rows, verifyReceipt) {
  if (typeof verifyReceipt !== "function") throw new TypeError("verifyReceipt must be a function");
  const seen = new Set();
  const corrections = [];
  for (const row of Array.isArray(rows) ? rows : []) {
    if (!isReceiptRetryCandidate(row)) continue;
    const tx = String(row.tx).toLowerCase();
    if (seen.has(tx)) continue;
    seen.add(tx);
    let status = null;
    try {
      const result = await verifyReceipt(tx, row);
      const evidence = sanitizeEvidence(result);
      status = result?.verified === true && evidence
        && (result.status === "0x1" || result.status === "0x0") ? result.status : null;
      if (result?.verified === true && evidence && status !== null) {
        const correction = { tx, status, verified: true, evidence };
        corrections.push(correction);
        continue;
      }
    } catch {
      status = null;
    }
    corrections.push({ tx, status });
  }
  return corrections;
}

async function readJsonl(file) {
  try {
    const raw = await fs.readFile(file, "utf8");
    const rows = [];
    for (const [index, line] of raw.split("\n").entries()) {
      if (!line.trim()) continue;
      try {
        rows.push(JSON.parse(line));
      } catch {
        throw new Error(`money-truth: corrupt JSONL at line ${index + 1}`);
      }
    }
    return rows;
  } catch (error) {
    if (error?.code === "ENOENT") return [];
    throw error;
  }
}

function journalLockPath(file) {
  return `${file}.lock`;
}

function processAlive(pid) {
  try { process.kill(pid, 0); return true; } catch { return false; }
}

async function acquireJournalLock(file) {
  const lockPath = journalLockPath(file);
  const owner = `${process.pid}:${randomUUID()}`;
  try {
    await fs.mkdir(lockPath);
  } catch (error) {
    if (error?.code !== "EEXIST") throw error;
    let stale = false;
    try {
      const value = JSON.parse(await fs.readFile(path.join(lockPath, "owner"), "utf8"));
      stale = !Number.isInteger(value?.pid) || !processAlive(value.pid);
    } catch {
      // A just-created lock may not have its owner file visible yet.  Treat an unreadable owner as
      // held (fail closed) rather than deleting a concurrent writer's lock and racing the append.
      stale = false;
    }
    if (!stale) return null;
    await fs.rm(lockPath, { recursive: true, force: true });
    try { await fs.mkdir(lockPath); } catch (retryError) {
      if (retryError?.code === "EEXIST") return null;
      throw retryError;
    }
  }
  await fs.writeFile(path.join(lockPath, "owner"), JSON.stringify({ pid: process.pid, owner }), "utf8");
  return { lockPath, owner };
}

async function releaseJournalLock(lock) {
  if (!lock) return;
  try {
    const value = JSON.parse(await fs.readFile(path.join(lock.lockPath, "owner"), "utf8"));
    if (value?.owner !== lock.owner) return;
  } catch {
    return;
  }
  await fs.rm(lock.lockPath, { recursive: true, force: true }).catch(() => {});
}

async function withJournalLock(file, work) {
  await fs.mkdir(path.dirname(file), { recursive: true });
  const lock = await acquireJournalLock(file);
  if (!lock) return { locked: true };
  try { return await work(); } finally { await releaseJournalLock(lock); }
}

function sanitizeEvidence(value) {
  if (!value || typeof value !== "object") return undefined;
  const source = value.evidence && typeof value.evidence === "object"
    ? value.evidence
    : value.transfer && typeof value.transfer === "object"
      ? { ...value, ...value.transfer }
      : value;
  const allowed = ["chain_id", "tx_hash", "contract", "payer", "recipient", "amount_atomic", "log_index", "provider_receipt_id"];
  const evidence = {};
  for (const key of allowed) {
    if (source[key] !== undefined && source[key] !== null
      && (typeof source[key] === "string" || typeof source[key] === "number")) evidence[key] = source[key];
  }
  return Object.keys(evidence).length > 0 ? evidence : undefined;
}

/** Build and verify one ledger row's complete EVM transfer tuple through the shared strict verifier. */
export async function verifyLedgerRow(row, verifyEvmReceipt) {
  if (!row || typeof row !== "object" || typeof verifyEvmReceipt !== "function") {
    return { verified: false, reason: "missing_transfer_proof" };
  }
  const proof = row.proof || row.chain_provider_proof;
  const txHash = proof?.tx_hash || proof?.transaction_hash || row.tx;
  const chainId = proof?.chain_id || row.chain_id;
  const contract = proof?.contract || row.contract || row.asset_contract;
  const recipient = row.recipient || row.wallet;
  const payer = row.payer || row.from;
  const amountAtomic = row.amount_atomic || row.expected_amount_atomic;
  const logIndex = proof?.log_index;
  if (proof?.verified !== true || !txHash || !chainId || !contract || !recipient || !payer
    || amountAtomic == null || logIndex == null) {
    return { verified: false, reason: "missing_transfer_proof" };
  }
  return verifyEvmReceipt({
    tx_hash: txHash,
    expected_chain_id: chainId,
    expected_contract: contract,
    expected_recipient: recipient,
    expected_payer: payer,
    expected_amount_atomic: amountAtomic,
    expected_log_index: logIndex,
  });
}

/**
 * Reconcile a real ledger against an append-only receipt sidecar. Null/error results are not
 * persisted, which keeps them retryable on the next wake; terminal 0x1/0x0 results are idempotent.
 */
export async function reconcileLedger({ ledgerPath, correctionPath, fetchReceipt, verifyReceipt, nowTs } = {}) {
  if (!ledgerPath || !correctionPath) throw new TypeError("ledgerPath and correctionPath are required");
  const verifier = verifyReceipt || fetchReceipt;
  if (typeof verifier !== "function") throw new TypeError("verifyReceipt must be a function");
  const result = await withJournalLock(correctionPath, async () => {
    const [rows, stored] = await Promise.all([readJsonl(ledgerPath), readJsonl(correctionPath)]);
    const known = new Map(
      stored.filter((c) => c && c.verified === true && typeof c.tx === "string" && (c.status === "0x1" || c.status === "0x0"))
        .map((c) => [c.tx.toLowerCase(), c])
    );
    const pendingRows = rows.filter((row) => row?.tx && !known.has(String(row.tx).toLowerCase()));
    const attempted = await reconcilePendingReceipts(pendingRows, verifier);
    const durable = attempted.filter((correction) => correction.verified === true
      && correction.status !== null && !known.has(String(correction.tx).toLowerCase()));
    if (durable.length > 0) {
      await fs.mkdir(path.dirname(correctionPath), { recursive: true });
      await fs.appendFile(
        correctionPath,
        durable.map((correction) => JSON.stringify({ ts: nowTs ?? Math.floor(Date.now() / 1000), ...correction })).join("\n") + "\n",
        "utf8",
      );
    }
    const corrections = [...stored, ...durable];
    return {
      attempted_receipts: attempted.length,
      persisted_corrections: durable.length,
      summary: summarizeRealizedRevenue(rows, corrections),
    };
  });
  if (result?.locked) return { attempted_receipts: 0, persisted_corrections: 0, locked: true };
  return result;
}

function receiptInRow(row) {
  const candidate = row && typeof row === "object" && row.schema_version === REVENUE_RECEIPT_SCHEMA_VERSION && row.kind === "revenue_receipt"
    ? row : row && typeof row === "object" && row.receipt && row.receipt.schema_version === REVENUE_RECEIPT_SCHEMA_VERSION
      && row.receipt.kind === "revenue_receipt" ? row.receipt : null;
  if (candidate) {
    try { return normalizeRevenueReceipt(candidate); } catch { return null; }
  }
  return null;
}

function receiptIsVerifiedExternal(receipt, row = receipt, selfPayers = []) {
  if (!receipt || !isNormalizedRevenueReceipt(receipt)) return false;
  if (!VERIFIED_TERMINAL_STATES.has(String(receipt.terminal_state).toLowerCase())) return false;
  if (!NORMALIZED_ASSETS.has(String(receipt.asset).toUpperCase())) return false;
  const payer = String(receipt.payer || "").toLowerCase();
  const recipient = String(receipt.recipient || "").toLowerCase();
  if (!payer || !recipient || payer === recipient) return false;
  const selfSet = new Set((Array.isArray(selfPayers) ? selfPayers : [selfPayers])
    .filter((value) => value !== undefined && value !== null)
    .map((value) => String(value).trim().toLowerCase()));
  if (selfSet.has(payer)) return false;
  if (row && row.external === false) return false;
  return finiteNumber(receipt.signed_net);
}

/**
 * Append normalized RevenueReceipt rows to a canonical JSONL journal.  Input is normalized as a
 * complete batch before any write, so one malformed receipt cannot leave a partial contribution.
 * Existing rows and duplicate items are keyed only by the canonical receipt id; a replay therefore
 * reports duplicates and appends no additional value.
 */
export async function reconcileRevenueReceipts({ journalPath, receipts, nowTs, selfPayers = [], selfWallets } = {}) {
  if (!journalPath) throw new TypeError("journalPath is required");
  if (!Array.isArray(receipts)) throw new TypeError("receipts must be an array");
  const walletsProvided = Array.isArray(selfWallets) ? selfWallets.length > 0 : selfWallets !== undefined && selfWallets !== null && selfWallets !== "";
  const payers = Array.isArray(selfPayers) && selfPayers.length === 0 && walletsProvided
    ? selfWallets
    : (selfPayers !== undefined && selfPayers !== null && selfPayers !== "" ? selfPayers : (selfWallets ?? []));
  const result = await withJournalLock(journalPath, async () => {
    const existing = await readJsonl(journalPath);
    for (const row of existing) {
      if (row?.kind !== "revenue_receipt") continue;
      if (row.schema_version !== REVENUE_RECEIPT_SCHEMA_VERSION) {
        throw new RevenueReceiptValidationError("UNSUPPORTED_VERSION", "journal contains an unsupported receipt version", "schema_version");
      }
      // Validate all stored canonical rows before deciding whether a new candidate is a duplicate.
      // A malformed/forged old row must never be silently bypassed by writing a v2 copy.
      normalizeRevenueReceipt(row);
    }
    const known = new Set(existing.map((row) => isNormalizedRevenueReceipt(row) ? row.idempotency_key : null).filter(Boolean));
    const seen = new Set();
    const normalized = [];
    let duplicates = 0;
    for (const candidate of receipts) {
      // Always run the normalizer, even for an object carrying schema_version/kind.  A caller cannot
      // smuggle a modified signed_net or idempotency marker past the arithmetic/proof checks.
      const receipt = normalizeRevenueReceipt(candidate, { selfPayers: payers });
      if (String(receipt.payer).toLowerCase() === String(receipt.recipient).toLowerCase()) {
        throw new RevenueReceiptValidationError("SELF_PAYMENT", "payer is an instance-controlled wallet", "payer");
      }
      const key = canonicalRevenueReceiptKey(receipt);
      if (known.has(key) || seen.has(key)) {
        duplicates += 1;
        continue;
      }
      seen.add(key);
      normalized.push(receipt);
    }
    if (normalized.length > 0) {
      await fs.mkdir(path.dirname(journalPath), { recursive: true });
      await fs.appendFile(
        journalPath,
        normalized.map((receipt) => JSON.stringify(receipt)).join("\n") + "\n",
        "utf8",
      );
    }
    const allRows = [...existing, ...normalized];
    return {
      accepted: normalized.length,
      duplicates,
      rejected: 0,
      rows: normalized,
      summary: summarizeRealizedRevenue(allRows, [], { selfPayers: payers }),
      ...(nowTs == null ? {} : { ts: nowTs }),
    };
  });
  if (result?.locked) return { accepted: 0, duplicates: 0, rejected: 0, rows: [], locked: true };
  return result;
}

function correctionStatus(row, correctionsByKey) {
  const key = receiptKey(row);
  if (!key) return null;
  const correction = correctionsByKey.get(key);
  return correction ? correction.status : row.status;
}

function correctionForRow(row, correctionsByKey) {
  const key = receiptKey(row);
  return key ? correctionsByKey.get(key) : null;
}

function isExplicitlyExcluded(row) {
  const source = String(row?.source || "");
  return row?.test === true || SWAP_SOURCES.has(source) || INTERNAL_SOURCES.has(source);
}

function isVerifiedExternal(row, correctionsByKey) {
  if (isExplicitlyExcluded(row) || row?.external !== true || !finitePositive(row?.net_usdc)) return false;
  if (row.tx) {
    const correction = correctionForRow(row, correctionsByKey);
    return correction?.verified === true && correction.status === "0x1";
  }
  if (row.sig) return row.confirmed === true;
  return row.chain === "hyperliquid" && row.fill_tid != null && row.confirmed === true;
}

/** Summarize only externally verified realized net; unverified claims remain visible but zeroed. */
export function summarizeRealizedRevenue(rows, corrections = [], options = {}) {
  const correctionsByKey = new Map(
    (Array.isArray(corrections) ? corrections : [])
      .filter((c) => c && typeof c.tx === "string" && c.tx.length > 0)
      .map((c) => [c.tx, c])
  );
  let externalNet = 0;
  let verifiedExternalRows = 0;
  let unverifiedExternalRows = 0;
  let excludedRows = 0;
  const inputRows = Array.isArray(rows) ? rows : [];
  const normalizedCorrectionRows = (Array.isArray(corrections) ? corrections : [])
    .filter((correction) => isNormalizedRevenueReceipt(correction))
    .filter((correction) => !inputRows.some((row) => receiptInRow(row)?.idempotency_key === correction.idempotency_key));
  const allRows = [...inputRows, ...normalizedCorrectionRows];
  const canonicalTxs = new Set(allRows.map((row) => receiptInRow(row)?.proof?.tx_hash?.toLowerCase()).filter(Boolean));
  for (const row of allRows) {
    const normalized = receiptInRow(row);
    if (normalized) {
      if (receiptIsVerifiedExternal(normalized, row, options.selfPayers ?? options.selfWallets ?? [])) {
        externalNet += Number(normalized.signed_net);
        verifiedExternalRows += 1;
      } else if (String(normalized.payer || "").toLowerCase() === String(normalized.recipient || "").toLowerCase()
        || !VERIFIED_TERMINAL_STATES.has(String(normalized.terminal_state).toLowerCase())) {
        excludedRows += 1;
      } else {
        unverifiedExternalRows += 1;
      }
    } else if (row?.tx && canonicalTxs.has(String(row.tx).toLowerCase())) {
      // A legacy row without its log tuple is ambiguous once the canonical v2 receipt covers the
      // same transaction.  Exclude it rather than risking a second contribution.
      excludedRows += 1;
    } else if (isExplicitlyExcluded(row) || row?.external !== true || !finitePositive(row?.net_usdc)) {
      excludedRows += 1;
    } else if (isVerifiedExternal(row, correctionsByKey)) {
      const correction = correctionForRow(row, correctionsByKey);
      const correctedValue = correction && (correction.signed_net ?? correction.signedNet ?? correction.net_usdc ?? correction.net);
      const correctedNet = correctedValue === undefined || correctedValue === null
        ? Number(row.net_usdc) : Number(correctedValue);
      if (Number.isFinite(correctedNet)) externalNet += correctedNet;
      verifiedExternalRows += 1;
    } else {
      unverifiedExternalRows += 1;
    }
  }
  return {
    external_net_usdc: Math.round(externalNet * 1e6) / 1e6,
    verified_external_rows: verifiedExternalRows,
    unverified_external_rows: unverifiedExternalRows,
    excluded_rows: excludedRows,
  };
}
