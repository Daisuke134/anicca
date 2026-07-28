#!/usr/bin/env node
"use strict";

const { readFile } = require("node:fs/promises");
const { handoffTaskMarketAwards } = require("../lib/taskmarket-award-handoff.js");

const MAX_LEDGER_BYTES = 64_000;

function parseArgs(argv) {
  const parsed = {
    ledgerResultPath: null,
    workerAddress: null,
    destination: null,
    apiUrl: null,
    rpcUrl: null,
  };
  for (let index = 0; index < argv.length; index += 1) {
    const key = argv[index];
    const value = argv[index + 1];
    if (!value) throw new Error(`unknown or incomplete argument ${key}`);
    if (key === "--ledger-result") parsed.ledgerResultPath = argv[++index];
    else if (key === "--worker") parsed.workerAddress = argv[++index];
    else if (key === "--destination") parsed.destination = argv[++index];
    else if (key === "--api") parsed.apiUrl = argv[++index];
    else if (key === "--rpc") parsed.rpcUrl = argv[++index];
    else throw new Error(`unknown or incomplete argument ${key}`);
  }
  return parsed;
}

async function readLedgerResult(path) {
  const bytes = await readFile(String(path || ""));
  if (bytes.length > MAX_LEDGER_BYTES) throw new Error("ledger result exceeds bounded size");
  try {
    return JSON.parse(bytes.toString("utf8"));
  } catch {
    throw new Error("ledger result is not JSON");
  }
}

async function main(deps = {}, argv = process.argv.slice(2)) {
  const parsed = parseArgs(argv);
  const ledgerResult = deps.ledgerResult || await readLedgerResult(parsed.ledgerResultPath);
  const result = await handoffTaskMarketAwards({
    ledgerResult,
    workerAddress: parsed.workerAddress || deps.workerAddress || process.env.TASKMARKET_WORKER_ADDRESS,
    destination: parsed.destination || deps.destination || process.env.LIFE_MANAGER_AGENT_WALLET_ADDRESS,
    apiUrl: parsed.apiUrl || deps.apiUrl || process.env.TASKMARKET_API_URL,
    rpcUrl: parsed.rpcUrl || deps.rpcUrl || process.env.BASE_RPC_URL,
  }, deps);
  (deps.writeOutput || ((text) => process.stdout.write(text)))(`${JSON.stringify(result)}\n`);
  return result;
}

if (require.main === module) {
  main().catch(() => {
    process.stderr.write('{"ok":false,"error":"taskmarket_award_handoff_failed"}\n');
    process.exitCode = 1;
  });
}

module.exports = {
  MAX_LEDGER_BYTES,
  parseArgs,
  readLedgerResult,
  main,
};
