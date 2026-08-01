#!/usr/bin/env node
"use strict";

const path = require("node:path");
const os = require("node:os");
const { Client } = require("pg");
const {
  buildJobHunterConfirmationResult,
  verifyJobHunterConfirmationResultSource,
  makeJobHunterSqliteQuery,
  readJobHunterConfirmationReceipts,
} = require("../lib/job-hunter-outbound-result.js");
const { appendOutboundResult } = require("../lib/outbound-result-store.js");

function arg(name, fallback = "") {
  const index = process.argv.indexOf(name);
  return index >= 0 ? String(process.argv[index + 1] || "") : fallback;
}

async function main() {
  const databaseUrl = String(process.env.DATABASE_URL || "");
  const tenantId = arg("--tenant", "dais-local");
  const ledgerPath = path.resolve(arg("--ledger",
    path.join(os.homedir(), ".local/state/anicca/job-search/ledger.sqlite3")));
  if (!tenantId || !ledgerPath) {
    throw new Error("tenant and exact Job Hunter ledger are required");
  }
  const queryJobHunter = makeJobHunterSqliteQuery({ ledgerPath });
  const receipts = await readJobHunterConfirmationReceipts({ query: queryJobHunter });
  if (receipts.length === 0) {
    process.stdout.write(JSON.stringify({ schema_version: 1, organ: "job_hunter",
      source_count: 0, results: [] }) + "\n");
    return;
  }
  if (!databaseUrl) throw new Error("DATABASE_URL is required when Job Hunter has sources");
  const client = new Client({ connectionString: databaseUrl });
  await client.connect();
  try {
    const results = [];
    for (const receipt of receipts) {
      const entry = buildJobHunterConfirmationResult({ tenantId, sourceReceipt: receipt });
      const saved = await appendOutboundResult(entry, {
        query: (sql, params) => client.query(sql, params),
        verifyJobHunterSource: (candidate) =>
          verifyJobHunterConfirmationResultSource(candidate, { query: queryJobHunter }),
      });
      results.push({ result_id: entry.result_id,
        provider_message_id: entry.provider_message_id, inserted: saved.inserted === true });
    }
    process.stdout.write(JSON.stringify({ schema_version: 1, organ: "job_hunter",
      source_count: receipts.length, results }) + "\n");
  } finally {
    await client.end();
  }
}

main().catch((error) => {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 1;
});
