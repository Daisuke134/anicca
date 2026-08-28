"use strict";

function normalizeTransaction(row) {
  return {
    ...row,
    merchant: String(row.merchant || "").trim().replace(/\s+/g, " "),
    category: String(row.category || "未分類").trim() || "未分類",
  };
}

function summarizeTransactions(transactions) {
  let incomeJpy = 0;
  let spendingJpy = 0;
  let excludedTransferRows = 0;
  for (const row of transactions) {
    if (row.transfer_id) {
      excludedTransferRows += 1;
      continue;
    }
    if (row.amount_jpy > 0) incomeJpy += row.amount_jpy;
    if (row.amount_jpy < 0) spendingJpy += Math.abs(row.amount_jpy);
  }
  return { income_jpy: incomeJpy, spending_jpy: spendingJpy, net_jpy: incomeJpy - spendingJpy, excluded_transfer_rows: excludedTransferRows };
}

function detectSubscriptions(transactions) {
  const groups = new Map();
  for (const input of transactions) {
    const row = normalizeTransaction(input);
    if (row.transfer_id || row.amount_jpy >= 0 || !row.merchant || !row.occurred_at) continue;
    const amount = Math.abs(row.amount_jpy);
    const key = `${row.merchant}\u0000${amount}`;
    const group = groups.get(key) || { merchant: row.merchant, amount_jpy: amount, months: new Set() };
    group.months.add(String(row.occurred_at).slice(0, 7));
    groups.set(key, group);
  }
  return [...groups.values()]
    .filter((group) => group.months.size >= 2)
    .map((group) => ({ merchant: group.merchant, amount_jpy: group.amount_jpy, months: [...group.months].sort(), usage_status: "unknown" }));
}

module.exports = { detectSubscriptions, normalizeTransaction, summarizeTransactions };
