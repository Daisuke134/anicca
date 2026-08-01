#!/usr/bin/env node
"use strict";

const fs = require("node:fs");
const { Client } = require("pg");
const { makeFunderGogThreadReader } = require("../lib/funder-gog-thread-reader.js");
const { syncFunderThreadResults, loadFunderSubmissionReceipt } = require("../lib/funder-thread-result-sync.js");
const { appendOutboundResult } = require("../lib/outbound-result-store.js");

function arg(name, fallback = "") {
  const index = process.argv.indexOf(name);
  return index >= 0 ? String(process.argv[index + 1] || "") : fallback;
}

function privateJson(pathname) {
  if (!pathname) return {};
  const stat = fs.statSync(pathname);
  if ((stat.mode & 0o077) !== 0) throw new Error("judgment file must be mode 0600");
  const value = JSON.parse(fs.readFileSync(pathname, "utf8"));
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error("judgment file must be an object keyed by Gmail message ID");
  }
  return value;
}

async function main() {
  const databaseUrl = String(process.env.DATABASE_URL || "");
  const tenantId = arg("--tenant", "dais-local");
  const sourceId = arg("--source");
  const account = arg("--account", process.env.GOG_ACCOUNT || "");
  if (!databaseUrl || !tenantId || !sourceId || !account) {
    throw new Error("DATABASE_URL, tenant, exact source, and account are required");
  }
  const client = new Client({ connectionString: databaseUrl });
  await client.connect();
  try {
    const receipt = await loadFunderSubmissionReceipt({
      tenantId, sourceId, query: (sql, params) => client.query(sql, params),
    });
    const result = await syncFunderThreadResults({
      submissionReceipt: receipt, ownerEmail: account,
      reader: makeFunderGogThreadReader({ account }),
      judgments: privateJson(arg("--judgments")),
      append: (entry) => appendOutboundResult(entry, {
        query: (sql, params) => client.query(sql, params),
      }),
    });
    process.stdout.write(JSON.stringify(result) + "\n");
  } finally {
    await client.end();
  }
}

main().catch((error) => {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 1;
});
