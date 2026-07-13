#!/usr/bin/env node
// Unit test for the un-fakeable affiliate ledger. No mocks — exercises validateRow directly.
import { validateRow } from "./record-affiliate-earn.mjs";

let pass = 0, fail = 0;
const ok = (name, fn, shouldThrow) => {
  let threw = false;
  try { fn(); } catch { threw = true; }
  const good = threw === shouldThrow;
  console.log(`${good ? "PASS" : "FAIL"}  ${name}`);
  good ? pass++ : fail++;
};

// REJECT: fake / test / internal sources
ok("reject source=test",        () => validateRow({ source: "test", amount_jpy: 100, report_date: "2026-06-30", report_export_id: "x" }), true);
ok("reject source=manual",      () => validateRow({ source: "manual", amount_jpy: 100, report_date: "2026-06-30", report_export_id: "x" }), true);
ok("reject missing source",     () => validateRow({ amount_jpy: 100, report_date: "2026-06-30", report_export_id: "x" }), true);
ok("reject amount<=0",          () => validateRow({ source: "amazon_report", amount_jpy: 0, report_date: "2026-06-30", report_export_id: "x" }), true);
ok("reject amount NaN",         () => validateRow({ source: "amazon_report", amount_jpy: "100", report_date: "2026-06-30", report_export_id: "x" }), true);
ok("reject bad date",           () => validateRow({ source: "amazon_report", amount_jpy: 100, report_date: "2026/06/30", report_export_id: "x" }), true);
ok("reject missing export_id",  () => validateRow({ source: "amazon_report", amount_jpy: 100, report_date: "2026-06-30" }), true);
// ACCEPT: a real-shaped Amazon report row
ok("accept real amazon_report", () => validateRow({ source: "amazon_report", amount_jpy: 123, report_date: "2026-06-30", report_export_id: "rep_abc123", order_items: 2 }), false);

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail === 0 ? 0 : 1);
