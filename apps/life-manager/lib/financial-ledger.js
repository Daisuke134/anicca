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

module.exports = { normalizeTransaction, summarizeTransactions };
