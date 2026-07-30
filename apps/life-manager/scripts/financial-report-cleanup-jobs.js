#!/usr/bin/env node
// financial-report-cleanup-jobs.js — remove OFF-CADENCE financial report job litter.
//
// WHY THIS EXISTS (measured, local stack 2026-07-30): the scheduler used to derive
// the report instant from POLL time (`Math.floor(Date.now()/pollMs)*pollMs`), so
// every 5-minute poll minted a new `report.financial.telegram` job. 14 distinct
// jobs accumulated between 04:32:25Z and 05:02:25Z (~576/day), all `queued` at
// `attempt = 0`, none of them executable: their instants were mid-afternoon local
// time, so the report would only ever answer `not_due`. The enqueue defect itself
// is fixed in `lib/report-job-adapter.js`; this script removes the rows the defect
// already wrote.
//
// SAFETY (this deletes production-shaped rows, so it is deliberately narrow):
//   * DRY RUN BY DEFAULT. Without `--apply` nothing is deleted and the exact
//     delete plan is printed.
//   * Only rows of capability `report.financial.telegram` for ONE tenant.
//   * Only rows that are still `queued` with `attempt = 0`, never leased, never
//     completed, and holding NO receipt row — i.e. rows that never ran and whose
//     deletion can therefore destroy no evidence.
//   * Only rows whose report instant is NOT an exact cadence slot (daily 20:00
//     local / weekly Sunday 20:05 local). A legitimate cadence-anchored job is
//     never a deletion candidate.
//   * The same predicate is re-asserted inside the DELETE statement, so a row
//     that gets claimed between the scan and the apply is not deleted.
"use strict";

const {
  isFinancialReportSlotInstant,
} = require("../lib/financial-report-schedule.js");
const {
  CAPABILITY,
  parseFinancialReportRef,
} = require("../lib/report-job-adapter.js");

const ALLOWED = new Set(["tenant", "time-zone"]);

function parseArgs(argv) {
  if (argv[0] !== "clean") {
    throw new Error(
      "usage: financial-report-cleanup-jobs.js clean --tenant <id> [--time-zone <zone>] [--apply]",
    );
  }
  const values = { apply: false };
  const positional = argv.slice(1).filter((value) => {
    if (value === "--apply") {
      values.apply = true;
      return false;
    }
    return true;
  });
  for (let index = 0; index < positional.length; index += 2) {
    const flag = String(positional[index] || "");
    const value = positional[index + 1];
    const name = flag.slice(2);
    if (
      !/^--[a-z-]+$/.test(flag)
      || !value
      || String(value).startsWith("--")
      || !ALLOWED.has(name)
    ) {
      throw new Error("financial report cleanup arguments are invalid");
    }
    values[name] = String(value).trim();
  }
  if (!values.tenant) throw new Error("--tenant is required");
  return values;
}

const SCAN_SQL = `
  SELECT j.job_id, j.status, j.attempt, j.created_at,
         j.input_refs->>'financial_report_ref' AS report_ref,
         (SELECT count(*) FROM public.lm_runtime_job_receipts r
           WHERE r.tenant_id = j.tenant_id AND r.job_id = j.job_id) AS receipt_count
  FROM public.lm_runtime_jobs j
  WHERE j.tenant_id = $1
    AND j.capability = $2
    AND j.status = 'queued'
    AND j.attempt = 0
    AND j.lease_owner IS NULL
    AND j.lease_expires_at IS NULL
    AND j.completed_at IS NULL
  ORDER BY j.created_at ASC
`;

const DELETE_SQL = `
  DELETE FROM public.lm_runtime_jobs j
  WHERE j.tenant_id = $1
    AND j.capability = $2
    AND j.job_id = ANY($3::text[])
    AND j.status = 'queued'
    AND j.attempt = 0
    AND j.lease_owner IS NULL
    AND j.lease_expires_at IS NULL
    AND j.completed_at IS NULL
    AND NOT EXISTS (
      SELECT 1 FROM public.lm_runtime_job_receipts r
      WHERE r.tenant_id = j.tenant_id AND r.job_id = j.job_id
    )
  RETURNING j.job_id
`;

function classify(row, timeZone) {
  const entry = {
    job_id: String(row.job_id),
    created_at: row.created_at instanceof Date ? row.created_at.toISOString() : row.created_at,
    report_ref: row.report_ref == null ? null : String(row.report_ref),
    receipt_count: Number(row.receipt_count || 0),
  };
  if (entry.receipt_count > 0) {
    return { ...entry, verdict: "keep", reason: "receipt_present" };
  }
  let parsed;
  try {
    parsed = parseFinancialReportRef(entry.report_ref);
  } catch {
    // An unparseable ref is not provably litter; never delete what is not understood.
    return { ...entry, verdict: "keep", reason: "unparseable_ref" };
  }
  const instant = new Date(parsed.nowMs).toISOString();
  if (isFinancialReportSlotInstant(parsed.kind, parsed.nowMs, timeZone)) {
    return {
      ...entry,
      report_kind: parsed.kind,
      report_instant: instant,
      verdict: "keep",
      reason: "cadence_slot",
    };
  }
  return {
    ...entry,
    report_kind: parsed.kind,
    report_instant: instant,
    verdict: "delete",
    reason: "off_cadence_instant",
  };
}

async function cleanFinancialReportJobs(argv, deps = {}) {
  const args = parseArgs(argv);
  if (typeof deps.query !== "function") {
    throw new Error("financial report cleanup durable store is unavailable");
  }
  const env = deps.env || process.env;
  const timeZone = args["time-zone"]
    || String(env.LM_FINANCIAL_REPORT_TIME_ZONE || "Asia/Tokyo").trim();
  const scanned = (await deps.query(SCAN_SQL, [args.tenant, CAPABILITY])).rows
    .map((row) => classify(row, timeZone));
  const candidates = scanned.filter((row) => row.verdict === "delete");
  const kept = scanned.filter((row) => row.verdict === "keep");

  let deleted = [];
  if (args.apply && candidates.length > 0) {
    deleted = (await deps.query(DELETE_SQL, [
      args.tenant,
      CAPABILITY,
      candidates.map((row) => row.job_id),
    ])).rows.map((row) => String(row.job_id));
  }

  const report = {
    mode: args.apply ? "apply" : "dry-run",
    tenant_id: args.tenant,
    capability: CAPABILITY,
    time_zone: timeZone,
    scanned: scanned.length,
    kept: kept.length,
    would_delete: candidates.length,
    deleted: deleted.length,
    // Always print WHAT would be (or was) deleted, never just a count.
    delete_plan: candidates.map((row) => ({
      job_id: row.job_id,
      report_kind: row.report_kind,
      report_instant: row.report_instant,
      created_at: row.created_at,
      reason: row.reason,
    })),
    deleted_job_ids: deleted,
    kept_rows: kept.map((row) => ({
      job_id: row.job_id,
      report_kind: row.report_kind || null,
      report_instant: row.report_instant || null,
      reason: row.reason,
    })),
  };
  (deps.stdout || process.stdout).write(`${JSON.stringify(report)}\n`);
  return report;
}

async function main() {
  const { Pool } = require("pg");
  const connectionString = String(process.env.LM_RUNTIME_DATABASE_URL || "").trim();
  if (!connectionString) throw new Error("LM_RUNTIME_DATABASE_URL is required");
  const pool = new Pool({ connectionString, max: 1 });
  try {
    await cleanFinancialReportJobs(process.argv.slice(2), {
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
  cleanFinancialReportJobs,
};
