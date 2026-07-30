#!/usr/bin/env node
// financial-report-shadow-status.js — seven-run financial report shadow gate reader.
//
// Read-only: prints how many CONSECUTIVE EXPECTED financial report runs (daily
// 20:00 local, weekly Sunday 20:05 local — the cadence the legacy launchd owner
// `ai.anicca.life-manager-financial-report` acts on) hold exactly one verified
// receipt, as n/7 with timestamps, plus any expected run that was released with
// no receipt row (missed_runs) and any expected run with more than one row
// (duplicate_runs = gate violation). It never enqueues, executes, sends, or
// mutates anything; it is the evidence reader for the spec §13 seven-expected-run
// cutover gate (which stays unclaimed until it reads 7/7 with zero missed and
// zero duplicate effects).
//
// ★ GATE TRUTH = `--source shadow` (the default): DURABLE RUNTIME SHADOW
// RECEIPTS in `lm_runtime_job_receipts` for capability `report.financial.telegram`
// with receipt status `shadow_held`. Reason: the gate has to prove that THE LIFE
// MANAGER RUNTIME produced the report at every expected run. Shadow deliberately
// never writes the Supabase `lm_financial_report_receipts` table, because that
// table is the LEGACY sender's send ledger and a shadow-written row there would
// make the legacy owner see a duplicate and SKIP its real send. Rows in that
// table therefore prove that launchd sent — not that the runtime is ready.
//
// `--source legacy` reads that Supabase send ledger explicitly, as a cross-check
// that the legacy owner is still sending on the same cadence grid. It requires
// SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY and FAILS LOUDLY when they are
// absent: an unreadable source must never print 0/7 or 7/7.
"use strict";

const {
  EXPECTED_SHADOW_RUNS,
  SHADOW_HOLD_STATUS,
  financialReportShadowStatus,
} = require("../lib/financial-report-shadow-runtime.js");
const {
  financialReportSlotForPeriodKey,
} = require("../lib/financial-report-schedule.js");
const {
  CAPABILITY,
  verifyFinancialReportReceipt,
} = require("../lib/report-job-adapter.js");

const HASH = /^[0-9a-f]{64}$/;
const SOURCES = new Set(["shadow", "legacy"]);
const ALLOWED = new Set(["tenant", "source", "time-zone"]);

function parseArgs(argv) {
  if (argv[0] !== "status") {
    throw new Error(
      "usage: financial-report-shadow-status.js status --tenant <id> [--source shadow|legacy] [--time-zone <zone>]",
    );
  }
  const values = { source: "shadow" };
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
      throw new Error("financial report shadow status arguments are invalid");
    }
    values[name] = String(value).trim();
  }
  if (!values.tenant) throw new Error("--tenant is required");
  if (!SOURCES.has(values.source)) {
    throw new Error("--source must be shadow or legacy");
  }
  return values;
}

const HISTORY_SQL = `
  SELECT r.outcome, r.receipt, r.created_at
  FROM public.lm_runtime_job_receipts r
  JOIN public.lm_runtime_jobs j
    ON j.job_id = r.job_id
    AND j.tenant_id = r.tenant_id
  WHERE j.tenant_id = $1
    AND j.capability = $2
  ORDER BY r.created_at ASC
  LIMIT 500
`;

// Durable shadow receipts (GATE TRUTH). Every receipt row for the capability is
// read, not just the held ones: a failed attempt or a skipped run must still
// break the streak instead of being filtered into invisibility.
async function readShadowRuns(args, deps) {
  if (typeof deps.query !== "function") {
    throw new Error("financial report shadow status durable store is unavailable");
  }
  const result = await deps.query(HISTORY_SQL, [args.tenant, CAPABILITY]);
  return result.rows.map((row) => {
    const receipt = row.receipt || {};
    const verified = row.outcome === "completed"
      && receipt.status === SHADOW_HOLD_STATUS
      && verifyFinancialReportReceipt(receipt);
    return {
      report_kind: receipt.report_kind || null,
      period_key: receipt.period_key || null,
      slot: receipt.slot || null,
      snapshot_hash: receipt.snapshot_hash || null,
      recorded_at: row.created_at instanceof Date
        ? row.created_at.toISOString()
        : row.created_at,
      verified,
    };
  });
}

// The legacy sender's Supabase send ledger (CROSS-CHECK source). Rows carry only
// (report_kind, period_key), so each row is placed on the expected-run grid via
// its period key.
async function readLegacyRuns(args, deps) {
  const env = deps.env || process.env;
  const supaUrl = String(env.SUPABASE_URL || "").replace(/\/$/, "");
  const supaKey = String(env.SUPABASE_SERVICE_ROLE_KEY || "");
  if (!supaUrl || !supaKey) {
    throw new Error(
      "financial report shadow status cannot read the legacy send ledger: "
      + "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required. Refusing to "
      + "print a count it did not measure",
    );
  }
  const fetchImpl = deps.fetchImpl || globalThis.fetch;
  if (typeof fetchImpl !== "function") {
    throw new Error("financial report shadow status needs fetch");
  }
  const url = `${supaUrl}/rest/v1/lm_financial_report_receipts`
    + `?uid=eq.${encodeURIComponent(args.tenant)}`
    + "&select=report_kind,period_key,snapshot_hash,status,sent_at,updated_at"
    + "&order=updated_at.asc&limit=500";
  const response = await fetchImpl(url, {
    headers: {
      apikey: supaKey,
      Authorization: `Bearer ${supaKey}`,
      "Content-Type": "application/json",
    },
  });
  if (!response || response.ok !== true) {
    throw new Error(
      `financial report shadow status legacy ledger read failed (${
        response ? response.status : "no response"
      })`,
    );
  }
  const rows = await response.json();
  if (!Array.isArray(rows)) {
    throw new Error("financial report shadow status legacy ledger returned a non-array body");
  }
  const timeZone = args["time-zone"] || String(
    (deps.env || process.env).LM_FINANCIAL_REPORT_TIME_ZONE || "Asia/Tokyo",
  ).trim();
  return rows.map((row) => {
    let slot = null;
    try {
      slot = financialReportSlotForPeriodKey(row.report_kind, row.period_key, timeZone);
    } catch {
      slot = null;
    }
    return {
      report_kind: row.report_kind || null,
      period_key: row.period_key || null,
      slot,
      snapshot_hash: row.snapshot_hash || null,
      recorded_at: row.sent_at || row.updated_at || null,
      verified: row.status === "sent" && HASH.test(String(row.snapshot_hash || "")),
    };
  });
}

async function readFinancialReportShadowStatus(argv, deps = {}) {
  const args = parseArgs(argv);
  const env = deps.env || process.env;
  const timeZone = args["time-zone"]
    || String(env.LM_FINANCIAL_REPORT_TIME_ZONE || "Asia/Tokyo").trim();
  const runs = args.source === "legacy"
    ? await readLegacyRuns(args, deps)
    : await readShadowRuns(args, deps);
  const status = financialReportShadowStatus(runs, {
    nowMs: deps.nowMs == null ? Date.now() : deps.nowMs,
    timeZone,
    expected: EXPECTED_SHADOW_RUNS,
  });
  (deps.stdout || process.stdout).write(`${JSON.stringify({
    tenant_id: args.tenant,
    source: args.source,
    gate_truth: "shadow",
    time_zone: timeZone,
    cadence: "daily 20:00 local, weekly Sunday 20:05 local",
    runs: status.display,
    consecutive: status.consecutive,
    expected: status.expected,
    gate_met: status.gate_met,
    receipts: status.runs,
    missed_runs: status.missed_runs,
    duplicate_runs: status.duplicate_runs,
    rows_read: runs.length,
  })}\n`);
  return status;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.source === "legacy") {
    await readFinancialReportShadowStatus(process.argv.slice(2), {});
    return;
  }
  const { Pool } = require("pg");
  const connectionString = String(process.env.LM_RUNTIME_DATABASE_URL || "").trim();
  if (!connectionString) throw new Error("LM_RUNTIME_DATABASE_URL is required");
  const pool = new Pool({ connectionString, max: 1 });
  try {
    await readFinancialReportShadowStatus(process.argv.slice(2), {
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
  readFinancialReportShadowStatus,
};
