#!/usr/bin/env node
// Un-fakeable affiliate earn ledger (mirrors founder-loop INV-7 pattern).
// ONLY accepts rows that represent a REAL external Amazon Associates report row.
// Internal / test / manual / synthetic rows are REJECTED. Append-only JSONL.
//
// Usage:
//   node record-affiliate-earn.mjs --row '{"source":"amazon_report","amount_jpy":123,"report_date":"2026-06-30","order_items":2,"report_export_id":"abc123"}'
//   node record-affiliate-earn.mjs --sum            # total real earned JPY
//
// INVARIANTS (a row is recorded ONLY if ALL hold):
//   INV-1  source === "amazon_report"            (no test/manual/internal/synthetic)
//   INV-2  amount_jpy is a finite number > 0
//   INV-3  report_date matches YYYY-MM-DD
//   INV-4  report_export_id is a non-empty string (the Amazon report export ref = external proof)
//   INV-5  the ledger path resolves inside the affiliate earn dir (no path escape)
// A rejected row throws and writes NOTHING.

import { appendFileSync, readFileSync, existsSync, mkdirSync } from "node:fs";
import { homedir } from "node:os";
import { join, resolve } from "node:path";

const LEDGER_DIR = join(homedir(), ".smtm", "earn-loops", "affiliate");
const LEDGER = join(LEDGER_DIR, "earn-ledger.jsonl");

export function validateRow(row) {
  if (!row || typeof row !== "object") throw new Error("REJECT: row not an object");
  if (row.source !== "amazon_report")
    throw new Error(`REJECT INV-1: source must be "amazon_report" (got ${JSON.stringify(row.source)}) — internal/test/manual rows are not real earnings`);
  if (typeof row.amount_jpy !== "number" || !Number.isFinite(row.amount_jpy) || row.amount_jpy <= 0)
    throw new Error(`REJECT INV-2: amount_jpy must be a finite number > 0 (got ${JSON.stringify(row.amount_jpy)})`);
  if (typeof row.report_date !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(row.report_date))
    throw new Error(`REJECT INV-3: report_date must be YYYY-MM-DD (got ${JSON.stringify(row.report_date)})`);
  if (typeof row.report_export_id !== "string" || row.report_export_id.trim() === "")
    throw new Error("REJECT INV-4: report_export_id (external Amazon report proof) required");
  return true;
}

export function recordEarn(row, stampedAt) {
  validateRow(row);
  const safe = resolve(LEDGER);
  if (!safe.startsWith(resolve(LEDGER_DIR)))
    throw new Error("REJECT INV-5: ledger path escapes affiliate earn dir");
  if (!existsSync(LEDGER_DIR)) mkdirSync(LEDGER_DIR, { recursive: true });
  const entry = {
    source: "amazon_report",
    amount_jpy: row.amount_jpy,
    report_date: row.report_date,
    report_export_id: row.report_export_id,
    order_items: typeof row.order_items === "number" ? row.order_items : null,
    partner_tag: row.partner_tag || process.env.AMAZON_PARTNER_TAG || null,
    recorded_at: stampedAt || null,
  };
  appendFileSync(LEDGER, JSON.stringify(entry) + "\n", "utf8");
  return entry;
}

export function sumEarnedJpy() {
  if (!existsSync(LEDGER)) return 0;
  return readFileSync(LEDGER, "utf8")
    .split("\n")
    .filter(Boolean)
    .map((l) => JSON.parse(l))
    .filter((r) => r.source === "amazon_report" && typeof r.amount_jpy === "number")
    .reduce((a, r) => a + r.amount_jpy, 0);
}

// CLI
if (import.meta.url === `file://${process.argv[1]}`) {
  const args = process.argv.slice(2);
  if (args[0] === "--sum") {
    console.log(JSON.stringify({ total_jpy: sumEarnedJpy() }));
  } else if (args[0] === "--row") {
    try {
      const row = JSON.parse(args[1]);
      const stamp = new Date().toISOString();
      const e = recordEarn(row, stamp);
      console.log("RECORDED " + JSON.stringify(e));
    } catch (err) {
      console.error(String(err.message || err));
      process.exit(1);
    }
  } else {
    console.error("usage: --row '<json>' | --sum");
    process.exit(2);
  }
}
