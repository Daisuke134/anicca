"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  cleanFinancialReportJobs,
  parseArgs,
} = require("./financial-report-cleanup-jobs.js");

// Real refs measured from the local stack litter (poll-time buckets) versus
// cadence-anchored refs the fixed enqueue writes.
const LITTER_REF = "financial-report://dais-local/daily/2026-07-30T04%3A30%3A00.000Z";
const LITTER_WEEKLY_REF = "financial-report://dais-local/weekly/2026-07-30T04%3A30%3A00.000Z";
const CADENCE_REF = "financial-report://dais-local/daily/2026-07-30T11%3A00%3A00.000Z";
const CADENCE_WEEKLY_REF = "financial-report://dais-local/weekly/2026-08-02T11%3A05%3A00.000Z";

function row(overrides = {}) {
  return {
    job_id: "financial-report:aaaa",
    status: "queued",
    attempt: 0,
    created_at: "2026-07-30T04:32:25.607Z",
    report_ref: LITTER_REF,
    receipt_count: "0",
    ...overrides,
  };
}

test("arguments require the clean command and a tenant, and default to dry run", () => {
  assert.throws(() => parseArgs([]), /usage/i);
  assert.throws(() => parseArgs(["clean"]), /--tenant is required/);
  assert.throws(() => parseArgs(["clean", "--tenant", "t", "--bogus", "x"]), /invalid/i);
  assert.equal(parseArgs(["clean", "--tenant", "dais-local"]).apply, false);
  assert.equal(parseArgs(["clean", "--tenant", "dais-local", "--apply"]).apply, true);
});

test("a dry run prints the plan and deletes nothing", async () => {
  const calls = [];
  let output = "";
  const report = await cleanFinancialReportJobs(["clean", "--tenant", "dais-local"], {
    query: async (sql, params) => {
      calls.push({ sql, params });
      return {
        rows: [
          row(),
          row({ job_id: "financial-report:bbbb", report_ref: LITTER_WEEKLY_REF }),
          row({ job_id: "financial-report:cccc", report_ref: CADENCE_REF }),
        ],
      };
    },
    stdout: { write(text) { output += text; } },
    env: { LM_FINANCIAL_REPORT_TIME_ZONE: "Asia/Tokyo" },
  });

  assert.equal(calls.length, 1);
  assert.match(calls[0].sql, /FROM public\.lm_runtime_jobs/);
  assert.match(calls[0].sql, /status = 'queued'/);
  assert.match(calls[0].sql, /attempt = 0/);
  assert.match(calls[0].sql, /lease_owner IS NULL/);
  assert.deepEqual(calls[0].params, ["dais-local", "report.financial.telegram"]);
  assert.equal(report.mode, "dry-run");
  assert.equal(report.scanned, 3);
  assert.equal(report.would_delete, 2);
  assert.equal(report.deleted, 0);
  assert.deepEqual(report.delete_plan.map((entry) => entry.job_id), [
    "financial-report:aaaa",
    "financial-report:bbbb",
  ]);
  assert.deepEqual(report.delete_plan[0], {
    job_id: "financial-report:aaaa",
    report_kind: "daily",
    report_instant: "2026-07-30T04:30:00.000Z",
    created_at: "2026-07-30T04:32:25.607Z",
    reason: "off_cadence_instant",
  });
  assert.deepEqual(report.kept_rows, [{
    job_id: "financial-report:cccc",
    report_kind: "daily",
    report_instant: "2026-07-30T11:00:00.000Z",
    reason: "cadence_slot",
  }]);
  assert.equal(JSON.parse(output).mode, "dry-run");
});

test("cadence-anchored jobs are never deletion candidates", async () => {
  const report = await cleanFinancialReportJobs(["clean", "--tenant", "dais-local", "--apply"], {
    query: async () => ({
      rows: [
        row({ job_id: "financial-report:dddd", report_ref: CADENCE_REF }),
        row({ job_id: "financial-report:eeee", report_ref: CADENCE_WEEKLY_REF }),
      ],
    }),
    stdout: { write() {} },
  });
  assert.equal(report.would_delete, 0);
  assert.equal(report.deleted, 0);
  assert.deepEqual(report.kept_rows.map((entry) => entry.reason), ["cadence_slot", "cadence_slot"]);
});

test("a row that already produced a receipt or has an unreadable ref is kept", async () => {
  const report = await cleanFinancialReportJobs(["clean", "--tenant", "dais-local", "--apply"], {
    query: async () => ({
      rows: [
        row({ job_id: "financial-report:ffff", receipt_count: "1" }),
        row({ job_id: "financial-report:gggg", report_ref: "not-a-ref" }),
        row({ job_id: "financial-report:hhhh", report_ref: null }),
      ],
    }),
    stdout: { write() {} },
  });
  assert.equal(report.would_delete, 0);
  assert.deepEqual(report.kept_rows.map((entry) => entry.reason), [
    "receipt_present",
    "unparseable_ref",
    "unparseable_ref",
  ]);
});

test("apply deletes only the scanned off-cadence ids and re-asserts the guard in SQL", async () => {
  const calls = [];
  const report = await cleanFinancialReportJobs(["clean", "--tenant", "dais-local", "--apply"], {
    query: async (sql, params) => {
      calls.push({ sql, params });
      if (calls.length === 1) {
        return {
          rows: [
            row(),
            row({ job_id: "financial-report:bbbb", report_ref: LITTER_WEEKLY_REF }),
            row({ job_id: "financial-report:cccc", report_ref: CADENCE_REF }),
          ],
        };
      }
      // One candidate was claimed between scan and delete: the SQL guard drops it.
      return { rows: [{ job_id: "financial-report:aaaa" }] };
    },
    stdout: { write() {} },
  });

  assert.equal(calls.length, 2);
  assert.match(calls[1].sql, /^\s*DELETE FROM public\.lm_runtime_jobs/);
  assert.match(calls[1].sql, /NOT EXISTS/);
  assert.match(calls[1].sql, /status = 'queued'/);
  assert.deepEqual(calls[1].params, [
    "dais-local",
    "report.financial.telegram",
    ["financial-report:aaaa", "financial-report:bbbb"],
  ]);
  assert.equal(report.mode, "apply");
  assert.equal(report.would_delete, 2);
  assert.equal(report.deleted, 1);
  assert.deepEqual(report.deleted_job_ids, ["financial-report:aaaa"]);
});

test("an empty scan issues no delete at all", async () => {
  const calls = [];
  const report = await cleanFinancialReportJobs(["clean", "--tenant", "dais-local", "--apply"], {
    query: async (sql, params) => {
      calls.push({ sql, params });
      return { rows: [] };
    },
    stdout: { write() {} },
  });
  assert.equal(calls.length, 1);
  assert.equal(report.deleted, 0);
});

test("an unavailable store fails loudly", async () => {
  await assert.rejects(
    () => cleanFinancialReportJobs(["clean", "--tenant", "dais-local"], { stdout: { write() {} } }),
    /durable store is unavailable/,
  );
});
