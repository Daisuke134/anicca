#!/usr/bin/env node
import { promises as fs } from "node:fs";
import path from "node:path";
import { resolveEarnLedgerPath } from "../_shared/lib/ledger.mjs";
import { verifyEvmReceipt } from "../_shared/lib/verify-tx.mjs";
import { reconcileLedger, reconcileRevenueReceipts, verifyLedgerRow } from "./lib/money-truth.mjs";

const defaultLedger = resolveEarnLedgerPath().path;
const [ledgerArg, correctionArg, candidateArg, journalArg] = process.argv.slice(2);
const ledgerPath = ledgerArg || defaultLedger;
const correctionPath = correctionArg || path.join(path.dirname(ledgerPath), "receipt-reconciliations.jsonl");
const candidatePath = candidateArg || path.join(path.dirname(ledgerPath), "revenue-receipts.inbox.jsonl");
const journalPath = journalArg || path.join(path.dirname(ledgerPath), "revenue-receipts.jsonl");

async function readCandidateJsonl(file) {
  try {
    const raw = await fs.readFile(file, "utf8");
    const rows = [];
    for (const [index, line] of raw.split("\n").entries()) {
      if (!line.trim()) continue;
      try { rows.push(JSON.parse(line)); }
      catch { throw new Error(`reconcile-receipts: corrupt candidate JSONL at line ${index + 1}`); }
    }
    return rows;
  } catch (error) {
    if (error?.code === "ENOENT") return [];
    throw error;
  }
}

try {
  const candidates = await readCandidateJsonl(candidatePath);
  const receiptResult = await reconcileRevenueReceipts({ journalPath, receipts: candidates });
  const ledgerResult = await reconcileLedger({
    ledgerPath,
    correctionPath,
    verifyReceipt: (_tx, row) => verifyLedgerRow(row, verifyEvmReceipt),
  });
  process.stdout.write(`${JSON.stringify({
    ledgerPath,
    correctionPath,
    candidatePath,
    journalPath,
    receipt_candidates_seen: candidates.length,
    receipt_accepted: receiptResult.accepted,
    receipt_duplicates: receiptResult.duplicates,
    receipt_locked: receiptResult.locked === true,
    ...ledgerResult,
  })}\n`);
} catch (error) {
  process.stderr.write(`reconcile-receipts: ${error?.message || error}\n`);
  process.exitCode = 1;
}
