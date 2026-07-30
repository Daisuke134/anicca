#!/usr/bin/env node
// honne-ja-shadow-status.js — seven-cycle Honne JA shadow gate reader.
//
// Read-only: prints how many CONSECUTIVE successful shadow generation receipts
// the durable store holds for the Honne JA slice, as n/7 with timestamps. It
// never enqueues, executes, or mutates anything; it is the evidence reader for
// the spec §13 seven-expected-run cutover gate (which stays unclaimed until it
// reads 7/7).
"use strict";

const { honneJaShadowStatus } = require("../lib/honne-ja-shadow-runtime.js");

const DEFAULTS = { product: "honne-ai", format: "reelclaw", locale: "ja" };
const ALLOWED = new Set(["tenant", "product", "format", "locale"]);

function parseArgs(argv) {
  if (argv[0] !== "status") {
    throw new Error(
      "usage: honne-ja-shadow-status.js status --tenant <id> [--product <id>] [--format <id>] [--locale <locale>]",
    );
  }
  const values = { ...DEFAULTS };
  for (let index = 1; index < argv.length; index += 2) {
    const flag = String(argv[index] || "");
    const value = argv[index + 1];
    const name = flag.slice(2);
    if (
      !/^--[a-z-]+$/.test(flag)
      || !value
      || String(value).startsWith("--")
      || !ALLOWED.has(name)
    ) {
      throw new Error("honne JA shadow status arguments are invalid");
    }
    values[name] = String(value).trim();
  }
  if (!values.tenant) throw new Error("--tenant is required");
  return values;
}

const HISTORY_SQL = `
  SELECT r.outcome, r.receipt, r.created_at
  FROM public.lm_runtime_job_receipts r
  JOIN public.lm_runtime_jobs j
    ON j.job_id = r.job_id
    AND j.tenant_id = r.tenant_id
  WHERE j.tenant_id = $1
    AND j.capability = 'marketing.video.generate'
    AND j.input_refs->>'product_ref' = $2
    AND j.input_refs->>'format_ref' = $3
    AND j.input_refs->>'locale_ref' = $4
  ORDER BY r.created_at ASC
  LIMIT 500
`;

async function readHonneJaShadowStatus(argv, deps = {}) {
  const args = parseArgs(argv);
  if (typeof deps.query !== "function") {
    throw new Error("honne JA shadow status store is unavailable");
  }
  const result = await deps.query(HISTORY_SQL, [
    args.tenant,
    `product://${args.product}`,
    `format://${args.format}`,
    `locale://${args.locale}`,
  ]);
  const status = honneJaShadowStatus(result.rows.map((row) => ({
    outcome: row.outcome,
    receipt: row.receipt,
    created_at: row.created_at instanceof Date
      ? row.created_at.toISOString()
      : row.created_at,
  })));
  (deps.stdout || process.stdout).write(`${JSON.stringify({
    tenant_id: args.tenant,
    product_id: args.product,
    format_id: args.format,
    locale: args.locale,
    cycles: status.display,
    consecutive: status.consecutive,
    expected: status.expected,
    gate_met: status.gate_met,
    receipts: status.receipts,
  })}\n`);
  return status;
}

async function main() {
  const { Pool } = require("pg");
  const connectionString = String(process.env.LM_RUNTIME_DATABASE_URL || "").trim();
  if (!connectionString) throw new Error("LM_RUNTIME_DATABASE_URL is required");
  const pool = new Pool({ connectionString, max: 1 });
  try {
    await readHonneJaShadowStatus(process.argv.slice(2), {
      query: pool.query.bind(pool),
    });
  } finally {
    await pool.end();
  }
}

if (require.main === module) {
  main().catch((error) => {
    process.stderr.write(`${error.message}\n`);
    process.exitCode = 1;
  });
}

module.exports = {
  parseArgs,
  readHonneJaShadowStatus,
};
