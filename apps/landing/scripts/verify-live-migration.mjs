// Sprint-3 live-verify script. RUNS AGAINST PRODUCTION Supabase — no mocks.
// Requires: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_ACCESS_TOKEN
//
// Checks:
//   S3.2  every new column exists in information_schema.columns for `instances`
//   S3.2  idx_instances_tags_gin exists in pg_indexes
//   S3.3  row count (snapshotted for pre/post comparison in the evidence log)
//   S3.4  every existing row still passes the local telemetry-schema.validate contract
// Prints a JSON summary to stdout; exits 0 on all-green, 1 otherwise.

import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const { validate } = require("../netlify/functions/_lib/telemetry-schema");

const {
  SUPABASE_URL,
  SUPABASE_SERVICE_ROLE_KEY,
  SUPABASE_ACCESS_TOKEN,
} = process.env;

if (!SUPABASE_URL || !SUPABASE_SERVICE_ROLE_KEY || !SUPABASE_ACCESS_TOKEN) {
  console.error("[verify-live] missing env — need SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_ACCESS_TOKEN");
  process.exit(2);
}

const PROJECT_REF = new URL(SUPABASE_URL).host.split(".")[0];
const MGMT = `https://api.supabase.com/v1/projects/${PROJECT_REF}/database/query`;
const REST = `${SUPABASE_URL}/rest/v1`;

async function mgmtQuery(sql) {
  const r = await fetch(MGMT, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${SUPABASE_ACCESS_TOKEN}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ query: sql }),
  });
  const text = await r.text();
  if (!r.ok) throw new Error(`Management API ${r.status}: ${text}`);
  try { return JSON.parse(text); } catch { return text; }
}

async function restGet(pathAndQs) {
  const r = await fetch(`${REST}/${pathAndQs}`, {
    headers: {
      apikey: SUPABASE_SERVICE_ROLE_KEY,
      Authorization: `Bearer ${SUPABASE_SERVICE_ROLE_KEY}`,
    },
  });
  if (!r.ok) throw new Error(`PostgREST ${r.status}: ${await r.text()}`);
  return r.json();
}

const REQUIRED_COLUMNS = {
  tags:               { data_type: "ARRAY",             udt_name: "_text" },
  revenue_today_usd:  { data_type: "double precision" },
  revenue_by_source:  { data_type: "jsonb" },
  net_worth_src:      { data_type: "text" },
  earn_src:           { data_type: "text" },
  last_heartbeat:     { data_type: "timestamp with time zone" },
  log_feed:           { data_type: "jsonb" },
};

async function main() {
  const summary = { checks: [] };

  // S3.2 columns via information_schema
  const colsRes = await mgmtQuery(
    "select column_name, data_type, udt_name from information_schema.columns " +
    "where table_schema='public' and table_name='instances' order by column_name;"
  );
  const cols = colsRes || [];
  const colMap = Object.fromEntries(cols.map((c) => [c.column_name, c]));
  const missing = [];
  const mismatched = [];
  for (const [name, want] of Object.entries(REQUIRED_COLUMNS)) {
    const got = colMap[name];
    if (!got) { missing.push(name); continue; }
    if (got.data_type !== want.data_type) mismatched.push({ name, want: want.data_type, got: got.data_type });
    if (want.udt_name && got.udt_name !== want.udt_name) mismatched.push({ name, want_udt: want.udt_name, got_udt: got.udt_name });
  }
  const columnsCheckOk = missing.length === 0 && mismatched.length === 0;
  summary.checks.push({ id: "S3.2/columns", ok: columnsCheckOk, missing, mismatched, total_columns_seen: cols.length });

  // S3.2 GIN index on tags
  const idxRes = await mgmtQuery(
    "select indexname, indexdef from pg_indexes " +
    "where schemaname='public' and tablename='instances' and indexname='idx_instances_tags_gin';"
  );
  const indexOk = Array.isArray(idxRes) && idxRes.length === 1 && /USING\s+gin\s*\(\s*tags\s*\)/i.test(idxRes[0].indexdef || "");
  summary.checks.push({ id: "S3.2/index", ok: indexOk, matches: idxRes });

  // S3.3 row count
  const countRes = await mgmtQuery("select count(*)::bigint as n from public.instances;");
  const rowCount = Array.isArray(countRes) && countRes[0] ? Number(countRes[0].n) : null;
  summary.checks.push({ id: "S3.3/count", ok: Number.isFinite(rowCount), row_count: rowCount });

  // S3.4 fetch every row via PostgREST + local validate
  const rows = await restGet("instances?select=*");
  const badRows = [];
  for (const row of rows) {
    // pre-migration rows will have the additive columns as null — validate() must still accept them.
    // Coerce nulls -> undefined so the OPTIONAL-when-present contract matches Supabase's null shape.
    const cleaned = {};
    for (const [k, v] of Object.entries(row)) if (v !== null) cleaned[k] = v;
    const v = validate(cleaned);
    if (!v.ok) badRows.push({ id: row.id, reason: v.reason });
  }
  summary.checks.push({ id: "S3.4/back-compat-validate", ok: badRows.length === 0, checked: rows.length, bad_rows: badRows });

  summary.ok = summary.checks.every((c) => c.ok);
  console.log(JSON.stringify(summary, null, 2));
  process.exit(summary.ok ? 0 : 1);
}

main().catch((e) => { console.error("[verify-live] fatal:", e.message); process.exit(1); });
