#!/usr/bin/env node
"use strict";

const { runFinancialReport } = require("../lib/financial-report-runtime.js");
const { readUsdcBalance } = require("./run-agent-payout.js");

function parseArgs(argv) {
  const args = Array.isArray(argv) ? argv : [];
  const uidIndex = args.indexOf("--uid");
  const uid = uidIndex >= 0 ? String(args[uidIndex + 1] || "").trim() : "";
  if (!uid || uid.startsWith("--")) throw new Error("--uid <tenant-uid> is required");
  const forceIndex = args.indexOf("--force");
  let force = null;
  if (forceIndex >= 0) {
    force = String(args[forceIndex + 1] || "");
    if (!["daily", "weekly", "all"].includes(force)) {
      throw new Error("--force must be daily, weekly, or all");
    }
  }
  return { uid, force };
}

function publicResult(result) {
  const safe = {};
  for (const key of [
    "status",
    "reason",
    "report_kind",
    "period_key",
    "telegram_message_id",
    "snapshot_hash",
  ]) {
    if (result && Object.prototype.hasOwnProperty.call(result, key)) safe[key] = result[key];
  }
  return safe;
}

async function main(argv = process.argv.slice(2), env = process.env, deps = {}) {
  const { uid, force } = parseArgs(argv);
  const execute = deps.runReport || runFinancialReport;
  const balanceReader = deps.readBalance || readUsdcBalance;
  const fetchImpl = deps.fetchImpl || globalThis.fetch;
  const nowMs = deps.nowMs == null ? Date.now() : deps.nowMs;
  const runtimeDeps = {
    supaUrl: env.SUPABASE_URL,
    supaKey: env.SUPABASE_SERVICE_ROLE_KEY,
    telegramToken: env.LM_TELEGRAM_BOT_TOKEN,
    fetchImpl,
    readBalance: (walletAddress) => balanceReader(walletAddress, {
      rpcUrl: env.BASE_RPC_URL || "https://mainnet.base.org",
      fetchImpl,
    }),
  };
  const results = [];
  for (const kind of ["daily", "weekly"]) {
    try {
      results.push(await execute({
        uid,
        kind,
        nowMs,
        force: force === "all" || force === kind,
        reserveAtomic: env.LM_FINANCIAL_REPORT_RESERVE_USDC_ATOMIC
          || env.LM_PAYOUT_RESERVE_USDC_ATOMIC
          || undefined,
      }, runtimeDeps));
    } catch {
      results.push({
        status: "failed",
        reason: "report_failed",
        report_kind: kind,
      });
    }
  }
  const stdout = deps.stdout || process.stdout;
  stdout.write(`${JSON.stringify(results.map(publicResult))}\n`);
  return results;
}

if (require.main === module) {
  main().then((results) => {
    if (results.some((result) => result.status === "failed")) process.exitCode = 1;
  }).catch((error) => {
    process.stderr.write(`[financial-report] ${error && error.message ? error.message : "failed"}\n`);
    process.exitCode = 1;
  });
}

module.exports = { parseArgs, publicResult, main };
