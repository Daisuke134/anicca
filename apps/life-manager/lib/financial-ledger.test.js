"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { detectSubscriptions, normalizeTransaction, summarizeTransactions } = require("./financial-ledger.js");

test("excludes both sides of an internal transfer", () => {
  assert.deepEqual(summarizeTransactions([
    { id: "t1", amount_jpy: -1000, transfer_id: "move-1" },
    { id: "t2", amount_jpy: 1000, transfer_id: "move-1" },
    { id: "income", amount_jpy: 500 },
    { id: "spend", amount_jpy: -200 },
  ]), { income_jpy: 500, spending_jpy: 200, net_jpy: 300, excluded_transfer_rows: 2 });
});

test("normalizes merchant whitespace and preserves provider category", () => {
  assert.deepEqual(normalizeTransaction({ id: "t1", merchant: "  Example   Store  ", category: "食費" }), {
    id: "t1", merchant: "Example Store", category: "食費",
  });
  assert.equal(normalizeTransaction({ id: "t2" }).category, "未分類");
});

test("detects recurring charges without claiming they are unused", () => {
  assert.deepEqual(detectSubscriptions([
    { merchant: "Service", amount_jpy: -980, occurred_at: "2026-01-10" },
    { merchant: "Service", amount_jpy: -980, occurred_at: "2026-02-10" },
    { merchant: "One-off", amount_jpy: -980, occurred_at: "2026-02-11" },
  ]), [{ merchant: "Service", amount_jpy: 980, months: ["2026-01", "2026-02"], usage_status: "unknown" }]);
});
