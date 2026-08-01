#!/usr/bin/env node
"use strict";

const fs = require("node:fs");
const { Client } = require("pg");
const { buildDailyFunderDiscovery } = require("../lib/funder-program-discovery.js");
const { appendDailyFunderDiscovery } = require("../lib/funder-program-discovery-store.js");

function inputPath(argv) {
  const index = argv.indexOf("--input");
  if (index < 0 || !argv[index + 1] || argv.length !== index + 2) throw new Error("usage: record-funder-program-discovery --input <json>");
  return argv[index + 1];
}

async function main() {
  const file = inputPath(process.argv.slice(2));
  const raw = JSON.parse(fs.readFileSync(file, "utf8"));
  if (!process.env.DATABASE_URL) throw new Error("DATABASE_URL required");
  const client = new Client({ connectionString: process.env.DATABASE_URL });
  await client.connect();
  try {
    const current = await client.query(`
      SELECT DISTINCT ON (funder_id) funder_id, official_url, priority, discovery_facts_digest
      FROM public.lm_funder_registry_snapshots
      WHERE tenant_id=$1
      ORDER BY funder_id, observed_at DESC, recorded_at DESC`, [raw.tenantId]);
    const discovery = buildDailyFunderDiscovery({ ...raw, existingEntries: current.rows });
    const saved = await appendDailyFunderDiscovery(discovery, { query: client.query.bind(client) });
    process.stdout.write(`${JSON.stringify({
      discovery_run_id: saved.run.discovery_run_id,
      source_count: discovery.run.source_count,
      candidate_count: discovery.run.candidate_count,
      appended_count: saved.entries.filter(({ inserted }) => inserted).length,
    })}\n`);
  } finally {
    await client.end();
  }
}

main().catch((error) => {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 1;
});
