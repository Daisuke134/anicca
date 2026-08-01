#!/usr/bin/env node
"use strict";

const { Client } = require("pg");
const { latestCompletedTokyoReflectionWeek } = require("../lib/funder-weekly-reflection.js");
const { appendFunderWeeklyReflection } = require("../lib/funder-weekly-reflection-store.js");
const { collectFunderWeeklyReflectionSnapshot } = require("../lib/funder-weekly-reflection-snapshot.js");
const {
  runFunderWeeklyReflection,
  requestGeminiFunderReflection,
} = require("../lib/funder-weekly-reflection-runtime.js");

function arg(name) {
  const index = process.argv.indexOf(name);
  return index >= 0 ? String(process.argv[index + 1] || "").trim() : "";
}

async function main() {
  const tenantId = arg("--tenant");
  const connectionString = String(process.env.DATABASE_URL || "").trim();
  const reflectedAt = arg("--at") || new Date().toISOString();
  const force = process.argv.includes("--force");
  const candidateIds = arg("--candidate-ids").split(",").map((value) => value.trim()).filter(Boolean);
  const pgFields = ["PGHOST", "PGPORT", "PGUSER", "PGPASSWORD", "PGDATABASE"];
  const discrete = pgFields.every((key) => String(process.env[key] || "").trim());
  if (!tenantId || (!connectionString && !discrete)) {
    throw new Error("database configuration and --tenant are required");
  }
  const client = new Client(connectionString ? { connectionString } : {
    host: process.env.PGHOST,
    port: Number(process.env.PGPORT),
    user: process.env.PGUSER,
    password: process.env.PGPASSWORD,
    database: process.env.PGDATABASE,
  });
  await client.connect();
  try {
    const week = latestCompletedTokyoReflectionWeek(reflectedAt);
    const latest = await client.query(`
      SELECT week_key::text FROM public.lm_funder_weekly_reflection_ledger
      WHERE tenant_id=$1 ORDER BY week_key DESC LIMIT 1
    `, [tenantId]);
    const output = await runFunderWeeklyReflection({
      tenantId,
      reflectedAt,
      latestWeekKey: latest.rows[0] ? latest.rows[0].week_key : null,
      force,
      ...(candidateIds.length ? { candidateIds } : {}),
    }, {
      collectSnapshot: (request) => collectFunderWeeklyReflectionSnapshot(request, {
        query: client.query.bind(client),
      }),
      judge: (snapshot) => requestGeminiFunderReflection(snapshot, {
        apiKey: process.env.GEMINI_API_KEY,
      }),
      append: (value) => appendFunderWeeklyReflection(value, {
        query: client.query.bind(client),
      }),
    });
    process.stdout.write(`${JSON.stringify({ ...output, cutoff_at: output.week_end || week.week_end })}\n`);
  } finally {
    await client.end();
  }
}

if (require.main === module) {
  main().catch((error) => {
    process.stderr.write(`[funder-weekly-reflection] ${error.message}\n`);
    process.exitCode = 1;
  });
}
