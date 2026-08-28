#!/usr/bin/env node
"use strict";

const fs = require("node:fs");
const path = require("node:path");
const { readAccounts, readTransactions } = require("../lib/moneytree-local-adapter.js");
const { summarizeTransactions } = require("../lib/financial-ledger.js");
const { sendMessage } = require("../lib/telegram.js");

function ymd(date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

function renderSection(label, rows) {
  const total = summarizeTransactions(rows);
  return `${label}: 収入 ¥${total.income_jpy.toLocaleString("ja-JP")} / 支出 ¥${total.spending_jpy.toLocaleString("ja-JP")} / 差引 ¥${total.net_jpy.toLocaleString("ja-JP")}`;
}

async function main() {
  const now = new Date();
  const monthStart = new Date(now.getFullYear(), now.getMonth(), 1);
  const weekStart = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 6);
  weekStart.setHours(0, 0, 0, 0);
  const today = ymd(now);
  const [accounts, transactions] = await Promise.all([
    readAccounts(),
    readTransactions({ startDate: ymd(monthStart), endDate: today }),
  ]);
  const cash = accounts.reduce((sum, row) => sum + row.balance_jpy, 0);
  const daily = transactions.filter((row) => String(row.occurred_at).slice(0, 10) === today);
  const weekly = transactions.filter((row) => new Date(row.occurred_at) >= weekStart);
  const message = [
    "CFO · 実データ",
    `確認済み資産: ¥${cash.toLocaleString("ja-JP")}`,
    "負債: 未接続",
    renderSection("今日", daily),
    renderSection("7日", weekly),
    renderSection("今月", transactions),
    "出所: Moneytree read-only",
  ].join("\n");
  if (!process.argv.includes("--send")) return process.stdout.write(message);
  const credentialPath = path.join(process.env.HOME, ".local/share/anicca/credentials.json");
  const credential = JSON.parse(fs.readFileSync(credentialPath, "utf8")).credentials
    .find((row) => row.service === "telegram-life-manager");
  if (!credential?.bot_token || !credential?.chat_id) throw new Error("Life Manager Telegram credential is unavailable");
  const sent = await sendMessage(credential.bot_token, String(credential.chat_id), `Codex::: ${message}`);
  if (!sent?.ok || !Number.isInteger(sent.result?.message_id)) throw new Error("Life Manager Telegram send failed");
  process.stdout.write(`${JSON.stringify({ sent: true, message_id: sent.result.message_id })}\n`);
}

main().catch((error) => {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 1;
});
