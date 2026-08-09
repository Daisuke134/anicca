"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { test } = require("node:test");

const migrationPath = path.join(__dirname, "..", "migrations", "2026-08-09-cfo-daily-snapshots.sql");

test("CFO daily snapshot migration is append-only, private, and invariant-locked", () => {
  const sql = fs.readFileSync(migrationPath, "utf8");
  [
    /CREATE TABLE IF NOT EXISTS public\.lm_cfo_daily_snapshots/i,
    /public_ref\s+uuid\s+NOT NULL\s+DEFAULT\s+gen_random_uuid\(\)\s+UNIQUE/i,
    /uid\s+text\s+NOT NULL\s+REFERENCES\s+public\.lm_users\(uid\)/i,
    /UNIQUE\s*\(uid,\s*reporting_date,\s*revision\)/i,
    /UNIQUE\s*\(uid,\s*reporting_date,\s*run_id\)/i,
    /run_id\s+uuid\s+NOT NULL.*00000000-0000-0000-0000-000000000000/i,
    /jsonb_typeof\(report_payload\)\s*=\s*'object'/i,
    /jsonb_typeof\(source_bundle\)\s*=\s*'object'/i,
    /report_payload\s*->>\s*'reportingDate'.*=\s*reporting_date::text/i,
    /report_payload\s*->>\s*'revision'\s*=\s*revision::text/i,
    /report_payload\s*->>\s*'currency'.*=\s*'JPY'/i,
    /source_bundle\s*->\s*'source'\s*->>\s*'sourceId'.*=\s*'moneytree_mufg'/i,
    /source_bundle\s*->\s*'state'\s*->>\s*'sourceId'.*=\s*'moneytree_mufg'/i,
    /BEFORE UPDATE OR DELETE/i,
    /ENABLE ROW LEVEL SECURITY/i,
    /CREATE POLICY[^;]+FOR SELECT TO service_role/is,
    /CREATE POLICY[^;]+FOR INSERT TO service_role/is,
    /REVOKE ALL ON TABLE public\.lm_cfo_daily_snapshots FROM PUBLIC, anon, authenticated/i,
    /GRANT SELECT, INSERT ON TABLE public\.lm_cfo_daily_snapshots TO service_role/i,
    /REVOKE UPDATE, DELETE ON TABLE public\.lm_cfo_daily_snapshots FROM service_role/i,
    /SECURITY INVOKER/i,
    /SET search_path\s*=\s*public,\s*pg_temp/i,
    /ON CONFLICT DO NOTHING/i,
    /run_id_conflict/i,
    /reporting_date_conflict/i,
    /REVOKE ALL ON FUNCTION public\.lm_append_cfo_daily_snapshot\(text,\s*date,\s*uuid,\s*jsonb,\s*jsonb\) FROM PUBLIC, anon, authenticated/i,
    /GRANT EXECUTE ON FUNCTION public\.lm_append_cfo_daily_snapshot\(text,\s*date,\s*uuid,\s*jsonb,\s*jsonb\) TO service_role/i,
  ].forEach((pattern) => assert.match(sql, pattern));

  const start = sql.indexOf("CREATE OR REPLACE FUNCTION public.lm_append_cfo_daily_snapshot");
  const end = sql.indexOf("REVOKE ALL ON FUNCTION public.lm_append_cfo_daily_snapshot", start);
  assert.ok(start >= 0 && end > start);
  assert.doesNotMatch(sql.slice(start, end), /\bUPDATE\b/i);
});
