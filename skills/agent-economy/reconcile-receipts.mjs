#!/usr/bin/env node
import path from "node:path";
import { resolveEarnLedgerPath } from "../_shared/lib/ledger.mjs";
import { verifyEvmReceipt } from "../_shared/lib/verify-tx.mjs";
import { reconcileLedger, verifyLedgerRow } from "./lib/money-truth.mjs";

const defaultLedger = resolveEarnLedgerPath().path;
const ledgerPath = process.argv[2] || defaultLedger;
const correctionPath = process.argv[3] || path.join(path.dirname(ledgerPath), "receipt-reconciliations.jsonl");

try {
  const result = await reconcileLedger({
    ledgerPath,
    correctionPath,
    verifyReceipt: (_tx, row) => verifyLedgerRow(row, verifyEvmReceipt),
  });
  process.stdout.write(`${JSON.stringify({ ledgerPath, correctionPath, ...result })}\n`);
} catch (error) {
  process.stderr.write(`reconcile-receipts: ${error?.message || error}\n`);
  process.exitCode = 1;
}
