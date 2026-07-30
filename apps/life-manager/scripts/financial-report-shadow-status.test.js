"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  parseArgs,
  readFinancialReportShadowStatus,
} = require("./financial-report-shadow-status.js");

const SNAPSHOT_HASH = "a".repeat(64);
const CHAT_HASH = "c".repeat(64);
// Wednesday 2026-08-05 23:00 JST. Expected grid backward from here: daily 08-05,
// daily 08-04, daily 08-03, weekly 08-02, daily 08-02, daily 08-01, daily 07-31.
const NOW_MS = Date.parse("2026-08-05T14:00:00.000Z");
const GRID = Object.freeze([
  { kind: "daily", slot: "2026-07-31T11:00:00.000Z", period_key: "2026-07-31" },
  { kind: "daily", slot: "2026-08-01T11:00:00.000Z", period_key: "2026-08-01" },
  { kind: "daily", slot: "2026-08-02T11:00:00.000Z", period_key: "2026-08-02" },
  { kind: "weekly", slot: "2026-08-02T11:05:00.000Z", period_key: "2026-W31" },
  { kind: "daily", slot: "2026-08-03T11:00:00.000Z", period_key: "2026-08-03" },
  { kind: "daily", slot: "2026-08-04T11:00:00.000Z", period_key: "2026-08-04" },
  { kind: "daily", slot: "2026-08-05T11:00:00.000Z", period_key: "2026-08-05" },
]);

function shadowRow(entry, overrides = {}) {
  return {
    outcome: "completed",
    created_at: new Date(Date.parse(entry.slot) + 2000).toISOString(),
    receipt: {
      schema_version: 1,
      kind: "telegram_financial_report",
      status: "shadow_held",
      report_kind: entry.kind,
      period_key: entry.period_key,
      slot: entry.slot,
      chat_id_hash: CHAT_HASH,
      snapshot_hash: SNAPSHOT_HASH,
      held_at: new Date(Date.parse(entry.slot) + 1000).toISOString(),
      source_freshness: {
        report_cutoff_at: entry.slot,
        earnings_latest_at: null,
        costs_latest_at: null,
        balance_observed_at: entry.slot,
      },
      ...overrides,
    },
  };
}

function legacyRow(entry, overrides = {}) {
  return {
    report_kind: entry.kind,
    period_key: entry.period_key,
    snapshot_hash: SNAPSHOT_HASH,
    status: "sent",
    sent_at: new Date(Date.parse(entry.slot) + 3000).toISOString(),
    updated_at: new Date(Date.parse(entry.slot) + 3000).toISOString(),
    ...overrides,
  };
}

test("arguments require the status command, a tenant, and a known source", () => {
  assert.throws(() => parseArgs([]), /usage/i);
  assert.throws(() => parseArgs(["status"]), /--tenant is required/);
  assert.throws(() => parseArgs(["status", "--tenant", "t", "--bogus", "x"]), /invalid/i);
  assert.throws(() => parseArgs(["status", "--tenant", "t", "--source", "made-up"]), /shadow or legacy/);
  const args = parseArgs(["status", "--tenant", "dais-local"]);
  assert.equal(args.tenant, "dais-local");
  assert.equal(args.source, "shadow");
});

test("the shadow source is the gate truth and is scoped to the report capability", async () => {
  const calls = [];
  let output = "";
  const status = await readFinancialReportShadowStatus(["status", "--tenant", "dais-local"], {
    query: async (sql, params) => {
      calls.push({ sql, params });
      return { rows: GRID.slice(5).map((entry) => shadowRow(entry)) };
    },
    stdout: { write(text) { output += text; } },
    nowMs: NOW_MS,
    env: { LM_FINANCIAL_REPORT_TIME_ZONE: "Asia/Tokyo" },
  });

  assert.equal(calls.length, 1);
  assert.match(calls[0].sql, /lm_runtime_job_receipts/);
  assert.match(calls[0].sql, /ORDER BY r\.created_at ASC/);
  assert.deepEqual(calls[0].params, ["dais-local", "report.financial.telegram"]);
  assert.equal(status.consecutive, 2);
  const printed = JSON.parse(output);
  assert.equal(printed.source, "shadow");
  assert.equal(printed.gate_truth, "shadow");
  assert.equal(printed.runs, "2/7");
  assert.equal(printed.gate_met, false);
  assert.equal(printed.rows_read, 2);
  assert.deepEqual(printed.missed_runs, []);
  assert.equal(printed.receipts[0].period_key, "2026-08-04");
  assert.equal(printed.receipts[0].slot, "2026-08-04T11:00:00.000Z");
  assert.equal(printed.receipts[0].snapshot_hash, SNAPSHOT_HASH);
});

test("seven verified held runs read 7/7", async () => {
  let output = "";
  await readFinancialReportShadowStatus(["status", "--tenant", "dais-local"], {
    query: async () => ({ rows: GRID.map((entry) => shadowRow(entry)) }),
    stdout: { write(text) { output += text; } },
    nowMs: NOW_MS,
  });
  const printed = JSON.parse(output);
  assert.equal(printed.runs, "7/7");
  assert.equal(printed.gate_met, true);
  assert.deepEqual(printed.duplicate_runs, []);
});

test("a receipt that claims a real send is not a valid shadow run", async () => {
  let output = "";
  await readFinancialReportShadowStatus(["status", "--tenant", "dais-local"], {
    query: async () => ({
      rows: [
        shadowRow(GRID[5]),
        // Same shape, but with a message_id: a held report never has one.
        shadowRow(GRID[6], { message_id: 987 }),
      ],
    }),
    stdout: { write(text) { output += text; } },
    nowMs: NOW_MS,
  });
  assert.equal(JSON.parse(output).runs, "0/7");
});

test("a failed attempt row breaks the streak", async () => {
  let output = "";
  await readFinancialReportShadowStatus(["status", "--tenant", "dais-local"], {
    query: async () => ({
      rows: [
        shadowRow(GRID[4]),
        { outcome: "failed", created_at: "2026-08-04T11:00:02.000Z", receipt: { error_code: "CAPABILITY_EXECUTION_FAILED" } },
        shadowRow(GRID[6]),
      ],
    }),
    stdout: { write(text) { output += text; } },
    nowMs: NOW_MS,
  });
  assert.equal(JSON.parse(output).runs, "1/7");
});

test("an expected run with no receipt is reported missed", async () => {
  let output = "";
  await readFinancialReportShadowStatus(["status", "--tenant", "dais-local"], {
    query: async () => ({
      rows: GRID.filter((entry) => entry.kind !== "weekly").map((entry) => shadowRow(entry)),
    }),
    stdout: { write(text) { output += text; } },
    nowMs: NOW_MS,
  });
  const printed = JSON.parse(output);
  assert.equal(printed.runs, "3/7");
  assert.deepEqual(printed.missed_runs, [{
    report_kind: "weekly",
    slot: "2026-08-02T11:05:00.000Z",
    period_key: "2026-W31",
  }]);
});

test("an empty durable history reads 0/7 without failing", async () => {
  let output = "";
  await readFinancialReportShadowStatus(["status", "--tenant", "dais-local"], {
    query: async () => ({ rows: [] }),
    stdout: { write(text) { output += text; } },
    nowMs: NOW_MS,
  });
  const printed = JSON.parse(output);
  assert.equal(printed.runs, "0/7");
  assert.equal(printed.rows_read, 0);
  assert.deepEqual(printed.receipts, []);
});

test("an unavailable durable store fails loudly instead of reading 0/7", async () => {
  await assert.rejects(
    () => readFinancialReportShadowStatus(["status", "--tenant", "dais-local"], {
      stdout: { write() {} },
      nowMs: NOW_MS,
    }),
    /durable store is unavailable/,
  );
});

test("the legacy cross-check source reads the Supabase send ledger by period key", async () => {
  const requests = [];
  let output = "";
  await readFinancialReportShadowStatus(
    ["status", "--tenant", "lm_tenant", "--source", "legacy"],
    {
      env: {
        SUPABASE_URL: "https://example.supabase.co/",
        SUPABASE_SERVICE_ROLE_KEY: "service-role",
        LM_FINANCIAL_REPORT_TIME_ZONE: "Asia/Tokyo",
      },
      fetchImpl: async (url, init) => {
        requests.push({ url, init });
        return {
          ok: true,
          status: 200,
          json: async () => GRID.map((entry) => legacyRow(entry)),
        };
      },
      stdout: { write(text) { output += text; } },
      nowMs: NOW_MS,
    },
  );

  assert.equal(requests.length, 1);
  assert.match(requests[0].url, /^https:\/\/example\.supabase\.co\/rest\/v1\/lm_financial_report_receipts\?/);
  assert.match(requests[0].url, /uid=eq\.lm_tenant/);
  assert.doesNotMatch(requests[0].url, /service-role/);
  const printed = JSON.parse(output);
  assert.equal(printed.source, "legacy");
  assert.equal(printed.gate_truth, "shadow");
  assert.equal(printed.runs, "7/7");
  // A pending legacy row is not a completed run.
  assert.equal(printed.receipts.length, 7);
});

test("the legacy source refuses to report anything without credentials", async () => {
  await assert.rejects(
    () => readFinancialReportShadowStatus(
      ["status", "--tenant", "lm_tenant", "--source", "legacy"],
      { env: {}, stdout: { write() {} }, nowMs: NOW_MS },
    ),
    /SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required/,
  );
  await assert.rejects(
    () => readFinancialReportShadowStatus(
      ["status", "--tenant", "lm_tenant", "--source", "legacy"],
      {
        env: { SUPABASE_URL: "https://example.supabase.co", SUPABASE_SERVICE_ROLE_KEY: "k" },
        fetchImpl: async () => ({ ok: false, status: 503, json: async () => [] }),
        stdout: { write() {} },
        nowMs: NOW_MS,
      },
    ),
    /legacy ledger read failed \(503\)/,
  );
});

test("a pending legacy row breaks the streak instead of counting", async () => {
  let output = "";
  await readFinancialReportShadowStatus(
    ["status", "--tenant", "lm_tenant", "--source", "legacy"],
    {
      env: {
        SUPABASE_URL: "https://example.supabase.co",
        SUPABASE_SERVICE_ROLE_KEY: "service-role",
      },
      fetchImpl: async () => ({
        ok: true,
        status: 200,
        json: async () => [
          legacyRow(GRID[5]),
          legacyRow(GRID[6], { status: "pending", sent_at: null }),
        ],
      }),
      stdout: { write(text) { output += text; } },
      nowMs: NOW_MS,
    },
  );
  assert.equal(JSON.parse(output).runs, "0/7");
});
