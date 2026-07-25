#!/usr/bin/env node
"use strict";
// FIN-c — generate the spec 9.11 monthly report for the agent wallet from measured inputs only.
//
//   node scripts/agent-earnings-report.js --month 2026-07 [--ledger <file.jsonl>]
//
// The balance always comes off the chain. The ledger comes from Supabase, or from a local append-only
// JSONL file while the migration is still unapplied in production. Nothing here has a default that
// stands in for a measurement: an RPC that will not answer, or a ledger we cannot read, aborts the
// report rather than printing a zero that looks the same as a real one.

const fs = require("node:fs");
const { rollUpMonth, formatMonthlyReport, usdMinorFromAtomic } = require("../lib/earnings-ledger.js");
const { readMonthRows } = require("../lib/earnings-runtime.js");

const AGENT_WALLET = process.env.AGENT_WALLET_ADDRESS || "0x477EeE969ccfdc0e959F38cE8B83e372FC0262ad";
const BASE_RPC = process.env.BASE_RPC_URL || "https://mainnet.base.org";
// Circle's canonical USDC on Base, six decimals.
const USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913";
const USDC_DECIMALS = 6;

function arg(name, fallback = null) {
  const index = process.argv.indexOf(`--${name}`);
  return index >= 0 && process.argv[index + 1] ? process.argv[index + 1] : fallback;
}

async function rpc(method, params) {
  const response = await fetch(BASE_RPC, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ jsonrpc: "2.0", id: 1, method, params }),
  });
  if (!response.ok) throw new Error(`Base RPC ${method} failed (${response.status})`);
  const body = await response.json();
  if (body.error) throw new Error(`Base RPC ${method} failed: ${body.error.message}`);
  return body.result;
}

// The report is denominated in dollars. USDC is the dollar leg and converts exactly; native ETH is
// not, and pricing it would mean inventing a rate. So a non-zero ETH balance stops the report and
// says why, instead of quietly reporting only part of the wallet.
async function readBalanceMinor() {
  const native = BigInt(await rpc("eth_getBalance", [AGENT_WALLET, "latest"]));
  const usdcRaw = await rpc("eth_call", [{
    to: USDC,
    data: `0x70a08231${AGENT_WALLET.slice(2).toLowerCase().padStart(64, "0")}`,
  }, "latest"]);
  if (native !== 0n) {
    throw new Error(`wallet holds ${native} wei of native ETH and this report has no price source for it`);
  }
  return usdMinorFromAtomic(BigInt(usdcRaw).toString(), USDC_DECIMALS);
}

function readLocalLedger(path) {
  return fs.readFileSync(path, "utf8").split("\n").filter((line) => line.trim()).map((line) => JSON.parse(line));
}

async function main() {
  const [year, month] = String(arg("month") || "").split("-").map(Number);
  if (!Number.isInteger(year) || !Number.isInteger(month)) throw new Error("--month YYYY-MM is required");
  const timezone = arg("timezone", process.env.LM_TIMEZONE || "Asia/Tokyo");
  const ledgerFile = arg("ledger");

  const rows = ledgerFile
    ? readLocalLedger(ledgerFile)
    : await readMonthRows({ year, month, timezone, walletAddress: AGENT_WALLET });

  const balanceMinor = await readBalanceMinor();
  const summary = rollUpMonth(rows, { year, month, timezone, walletAddress: AGENT_WALLET, balanceMinor });
  const text = formatMonthlyReport(summary, { cause: arg("cause"), plan: arg("plan") });

  process.stdout.write(`${JSON.stringify(summary, null, 2)}\n\n${text}\n`);
}

main().catch((error) => {
  process.stderr.write(`${error && error.message ? error.message : error}\n`);
  process.exitCode = 1;
});
