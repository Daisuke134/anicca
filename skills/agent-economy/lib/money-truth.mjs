// money-truth.mjs — append-only receipt reconciliation for the agent-economy policy.
//
// The earn ledger is intentionally immutable. A provider/RPC can return no receipt at the moment
// a pass records its result, then the same transaction can be finalized later. This module keeps
// the original row untouched and joins a retryable {tx,status} sidecar onto it.

import { promises as fs } from "node:fs";
import path from "node:path";

const SWAP_SOURCES = new Set(["swap", "swap-eth-usdc", "swap-usdc-eth"]);
const INTERNAL_SOURCES = new Set(["reconcile", "receipt-reconcile"]);

const finitePositive = (value) => Number.isFinite(Number(value)) && Number(value) > 0;

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
    row.tx.length > 0 &&
    row.status !== "0x1"
  );
}

/**
 * Retry only delayed EVM receipts. Failures are represented as status:null and remain retryable.
 * Duplicate transaction hashes are fetched once and returned once, preserving first-seen order.
 */
export async function reconcilePendingReceipts(rows, fetchReceipt) {
  if (typeof fetchReceipt !== "function") throw new TypeError("fetchReceipt must be a function");
  const seen = new Set();
  const corrections = [];
  for (const row of Array.isArray(rows) ? rows : []) {
    if (!isReceiptRetryCandidate(row)) continue;
    const tx = row.tx;
    if (seen.has(tx)) continue;
    seen.add(tx);
    let status = null;
    try {
      const result = await fetchReceipt(tx);
      status = result === "0x1" || result === "0x0" ? result : null;
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
    return raw.split("\n").filter(Boolean).map((line) => {
      try { return JSON.parse(line); } catch { return null; }
    }).filter(Boolean);
  } catch (error) {
    if (error?.code === "ENOENT") return [];
    throw error;
  }
}

/**
 * Reconcile a real ledger against an append-only receipt sidecar. Null/error results are not
 * persisted, which keeps them retryable on the next wake; terminal 0x1/0x0 results are idempotent.
 */
export async function reconcileLedger({ ledgerPath, correctionPath, fetchReceipt, nowTs } = {}) {
  if (!ledgerPath || !correctionPath) throw new TypeError("ledgerPath and correctionPath are required");
  const [rows, stored] = await Promise.all([readJsonl(ledgerPath), readJsonl(correctionPath)]);
  const known = new Map(
    stored.filter((c) => c && typeof c.tx === "string" && (c.status === "0x1" || c.status === "0x0"))
      .map((c) => [c.tx, c])
  );
  const pendingRows = rows.filter((row) => row?.tx && !known.has(row.tx));
  const attempted = await reconcilePendingReceipts(pendingRows, fetchReceipt);
  const durable = attempted.filter((correction) => correction.status !== null && !known.has(correction.tx));
  if (durable.length > 0) {
    await fs.mkdir(path.dirname(correctionPath), { recursive: true });
    await fs.appendFile(
      correctionPath,
      durable.map((correction) => JSON.stringify({ ts: nowTs ?? Math.floor(Date.now() / 1000), ...correction })).join("\n") + "\n",
      "utf8"
    );
  }
  const corrections = [...stored, ...durable];
  return {
    attempted_receipts: attempted.length,
    persisted_corrections: durable.length,
    summary: summarizeRealizedRevenue(rows, corrections),
  };
}

function correctionStatus(row, correctionsByKey) {
  const key = receiptKey(row);
  if (!key) return null;
  const correction = correctionsByKey.get(key);
  return correction ? correction.status : row.status;
}

function isExplicitlyExcluded(row) {
  const source = String(row?.source || "");
  return row?.test === true || SWAP_SOURCES.has(source) || INTERNAL_SOURCES.has(source);
}

function isVerifiedExternal(row, correctionsByKey) {
  if (isExplicitlyExcluded(row) || row?.external !== true || !finitePositive(row?.net_usdc)) return false;
  if (row.tx) return correctionStatus(row, correctionsByKey) === "0x1";
  if (row.sig) return row.confirmed === true;
  return row.chain === "hyperliquid" && row.fill_tid != null && row.confirmed === true;
}

/** Summarize only externally verified realized net; unverified claims remain visible but zeroed. */
export function summarizeRealizedRevenue(rows, corrections = []) {
  const correctionsByKey = new Map(
    (Array.isArray(corrections) ? corrections : [])
      .filter((c) => c && typeof c.tx === "string" && c.tx.length > 0)
      .map((c) => [c.tx, c])
  );
  let externalNet = 0;
  let verifiedExternalRows = 0;
  let unverifiedExternalRows = 0;
  let excludedRows = 0;
  for (const row of Array.isArray(rows) ? rows : []) {
    if (isExplicitlyExcluded(row) || row?.external !== true || !finitePositive(row?.net_usdc)) {
      excludedRows += 1;
    } else if (isVerifiedExternal(row, correctionsByKey)) {
      externalNet += Number(row.net_usdc);
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
