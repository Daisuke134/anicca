"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { test } = require("node:test");

const migrationPath = path.join(__dirname, "..", "migrations", "2026-08-09-cfo-daily-runs.sql");

function functionBody(sql, signature) {
  const start = sql.indexOf(signature);
  const end = sql.indexOf("\nREVOKE ALL ON FUNCTION", start);
  assert.ok(start >= 0 && end > start, `${signature} must have a closed definition`);
  return sql.slice(start, end);
}

test("CFO daily-run migration backfills immutable owner-local runs and links snapshots", () => {
  const sql = fs.readFileSync(migrationPath, "utf8");
  const tableStart = sql.indexOf("CREATE TABLE IF NOT EXISTS public.lm_cfo_daily_runs");
  const fkStart = sql.indexOf("FOREIGN KEY (uid, reporting_date, run_id)");
  const claim = functionBody(sql, "CREATE OR REPLACE FUNCTION public.lm_claim_cfo_daily_run");
  const helper = functionBody(sql, "CREATE OR REPLACE FUNCTION public.lm_cfo_owner_local_date");

  assert.ok(tableStart >= 0);
  assert.ok(sql.indexOf("RAISE EXCEPTION", 0) < tableStart, "invalid existing preferences abort before setup");
  assert.ok(fkStart > sql.indexOf("INSERT INTO public.lm_cfo_daily_runs"), "backfill precedes snapshot FK");
  [
    /public_ref\s+uuid\s+NOT NULL\s+DEFAULT\s+gen_random_uuid\(\)/i,
    /run_id\s+uuid\s+NOT NULL\s+DEFAULT\s+gen_random_uuid\(\).*00000000-0000-0000-0000-000000000000/is,
    /UNIQUE\s*\(uid,\s*reporting_date\)/i,
    /UNIQUE\s*\(uid,\s*reporting_date,\s*run_id\)/i,
    /time_zone_source\s+text\s+NOT NULL/i,
    /CHECK\s*\(time_zone_source\s+IN\s*\('migration_preference',\s*'owner_preference'\)\)/i,
    /pg_timezone_names/i,
    /migration_preference/i,
    /owner_preference/i,
    /ALTER TABLE public\.lm_cfo_daily_snapshots[\s\S]*FOREIGN KEY \(uid, reporting_date, run_id\)[\s\S]*REFERENCES public\.lm_cfo_daily_runs/i,
    /ENABLE ROW LEVEL SECURITY/i,
    /CREATE POLICY[^;]+TO service_role/is,
    /REVOKE ALL ON TABLE public\.lm_cfo_daily_runs FROM PUBLIC, anon, authenticated/i,
    /GRANT SELECT, INSERT ON TABLE public\.lm_cfo_daily_runs TO service_role/i,
    /REVOKE UPDATE, DELETE ON TABLE public\.lm_cfo_daily_runs FROM service_role/i,
    /BEFORE UPDATE OR DELETE/i,
    /SECURITY INVOKER/i,
    /SET search_path\s*=\s*public,\s*pg_temp/i,
  ].forEach((pattern) => assert.match(sql, pattern));

  assert.match(sql.slice(0, tableStart), /lm_cfo_daily_snapshots[\s\S]*lm_panel_preferences[\s\S]*pg_timezone_names[\s\S]*RAISE EXCEPTION/i);
  assert.match(claim, /FROM public\.lm_panel_preferences[\s\S]*pg_timezone_names[\s\S]*FOR UPDATE/i);
  assert.match(claim, /statement_timestamp\(\)\s+AT TIME ZONE\s+owner_time_zone/i);
  assert.match(claim, /ON CONFLICT DO NOTHING/i);
  assert.doesNotMatch(claim, /\bUPDATE\s+\S+\s+SET\b/i);
  assert.match(sql, /lm_claim_cfo_daily_run\(text\)/i);
  assert.match(sql, /REVOKE ALL ON FUNCTION public\.lm_claim_cfo_daily_run\(text\) FROM PUBLIC, anon, authenticated/i);
  assert.match(sql, /GRANT EXECUTE ON FUNCTION public\.lm_claim_cfo_daily_run\(text\) TO service_role/i);
  assert.match(sql, /REVOKE ALL ON FUNCTION public\.lm_cfo_owner_local_date\(text, timestamptz\) FROM PUBLIC, anon, authenticated, service_role/i);
  assert.doesNotMatch(sql, /GRANT EXECUTE ON FUNCTION public\.lm_cfo_owner_local_date\(text, timestamptz\)/i);
  assert.match(helper, /AT TIME ZONE/i);
});

test("daily-run claim receipt is a closed five-key public projection", () => {
  const sql = fs.readFileSync(migrationPath, "utf8");
  const claim = functionBody(sql, "CREATE OR REPLACE FUNCTION public.lm_claim_cfo_daily_run");
  const projections = [...claim.matchAll(/jsonb_build_object\(([\s\S]*?)\)\s*;/gi)].map((match) => match[1]);
  assert.equal(projections.length, 1, "insert and retry must use the same closed projection");
  for (const projection of projections) {
    assert.deepEqual(
      [...projection.matchAll(/'([a-z_]+)'\s*,/gi)].map((match) => match[1]),
      ["public_ref", "reporting_date", "run_id", "time_zone", "created_at"],
    );
    assert.doesNotMatch(projection, /\b(?:uid|id|time_zone_source|report_payload|source_bundle)\b/i);
  }
});
