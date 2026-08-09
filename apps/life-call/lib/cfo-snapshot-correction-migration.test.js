"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { test } = require("node:test");

const migrationPath = path.join(__dirname, "..", "migrations", "2026-08-09-cfo-snapshot-corrections.sql");
const baseMigrationPath = path.join(__dirname, "..", "migrations", "2026-08-09-cfo-daily-snapshots.sql");

function functionBody(sql, signature) {
  const start = sql.indexOf(signature);
  const end = sql.indexOf("\nREVOKE ALL ON FUNCTION", start);
  assert.ok(start >= 0 && end > start, `${signature} must be defined and closed`);
  return sql.slice(start, end);
}

function rpcSecurityBody(sql, functionName) {
  return functionBody(sql, `CREATE OR REPLACE FUNCTION public.${functionName}`);
}

function projectionKeys(body) {
  const projections = [...body.matchAll(/jsonb_build_object\(([\s\S]*?)\)\s*;/gi)].map((match) => match[1]);
  assert.equal(projections.length, 1, "RPC must use one closed receipt projection");
  return [...projections[0].matchAll(/'([a-z_]+)'\s*,/gi)].map((match) => match[1]);
}

test("CFO correction migration locks positive contiguous revisions without changing old rows", () => {
  const sql = fs.readFileSync(migrationPath, "utf8");
  const baseSql = fs.readFileSync(baseMigrationPath, "utf8");
  const revisionRpc = functionBody(sql, "CREATE OR REPLACE FUNCTION public.lm_append_cfo_daily_snapshot_revision");
  const legacyRpc = functionBody(sql, "CREATE OR REPLACE FUNCTION public.lm_append_cfo_daily_snapshot(");

  [
    /ALTER TABLE public\.lm_cfo_daily_snapshots\s+ADD COLUMN IF NOT EXISTS supersedes_revision integer/i,
    /DROP CONSTRAINT IF EXISTS lm_cfo_daily_snapshots_revision_check/i,
    /DROP CONSTRAINT IF EXISTS lm_cfo_daily_snapshots_owner_date_run_unique/i,
    /ADD CONSTRAINT \S*revision_positive\s+CHECK \(revision > 0\)/i,
    /ADD CONSTRAINT \S*predecessor_contract\s+CHECK[\s\S]*supersedes_revision IS NULL/i,
    /UNIQUE \(uid, reporting_date, run_id, revision\)/i,
    /DROP CONSTRAINT IF EXISTS lm_cfo_daily_snapshots_owner_date_run_unique/i,
    /FOREIGN KEY \(uid, reporting_date, run_id, supersedes_revision\)[\s\S]*REFERENCES public\.lm_cfo_daily_snapshots \(uid, reporting_date, run_id, revision\)/i,
    /revision = 1[\s\S]*supersedes_revision IS NULL/i,
    /revision > 1[\s\S]*supersedes_revision = revision - 1/i,
    /BEFORE UPDATE OR DELETE ON public\.lm_cfo_daily_snapshots/i,
    /SET search_path\s*=\s*public,\s*pg_temp/i,
    /REVOKE UPDATE, DELETE ON TABLE public\.lm_cfo_daily_snapshots FROM service_role/i,
    /GRANT SELECT, INSERT ON TABLE public\.lm_cfo_daily_snapshots TO service_role/i,
  ].forEach((pattern) => assert.match(sql, pattern));
  assert.match(baseSql, /UNIQUE\s*\(uid,\s*reporting_date,\s*revision\)/i);

  assert.match(revisionRpc, /p_revision\s+IS NULL OR p_revision <= 0/i);
  assert.match(revisionRpc, /p_supersedes_revision\s+IS DISTINCT FROM p_revision - 1/i);
  assert.match(revisionRpc, /FOR UPDATE/i);
  assert.match(revisionRpc, /same_run|predecessor.*run|run_id.*p_run_id/i);
  assert.match(revisionRpc, /ON CONFLICT DO NOTHING/i);
  assert.match(revisionRpc, /IS DISTINCT FROM p_report_payload/i);
  assert.match(revisionRpc, /IS DISTINCT FROM p_source_bundle/i);
  assert.doesNotMatch(revisionRpc, /\bUPDATE\s+\S+\s+SET\b|\bDELETE\s+FROM\b/i);
  assert.deepEqual(projectionKeys(revisionRpc), [
    "public_ref", "reporting_date", "run_id", "revision", "supersedes_revision", "created_at",
  ]);
  assert.doesNotMatch(revisionRpc.match(/jsonb_build_object\(([\s\S]*?)\)\s*;/i)[1], /\buid\b/i);

  assert.match(legacyRpc, /revision\s*=\s*1/i);
  assert.match(legacyRpc, /ON CONFLICT DO NOTHING/i);
  assert.deepEqual(projectionKeys(legacyRpc), [
    "public_ref", "reporting_date", "run_id", "revision", "supersedes_revision", "created_at",
  ]);
});

test("CFO correction RPCs are private, fixed-path, append-only interfaces", () => {
  const sql = fs.readFileSync(migrationPath, "utf8");
  const rpcs = [
    {
      name: "lm_append_cfo_daily_snapshot",
      signature: "lm_append_cfo_daily_snapshot(text, date, uuid, jsonb, jsonb)",
    },
    {
      name: "lm_append_cfo_daily_snapshot_revision",
      signature: "lm_append_cfo_daily_snapshot_revision(text, date, uuid, integer, integer, jsonb, jsonb)",
    },
  ];
  rpcs.forEach(({ name, signature }) => {
    const body = rpcSecurityBody(sql, name);
    assert.match(body, /SECURITY DEFINER/i);
    assert.match(body, /SET search_path\s*=\s*pg_catalog,\s*public/i);
    assert.doesNotMatch(body, /SECURITY INVOKER/i);
    const escaped = signature.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    assert.match(sql, new RegExp(`REVOKE ALL ON FUNCTION public\\.${escaped} FROM PUBLIC, anon, authenticated`, "i"));
    assert.match(sql, new RegExp(`GRANT EXECUTE ON FUNCTION public\\.${escaped} TO service_role`, "i"));
  });
  assert.doesNotMatch(sql, /GRANT EXECUTE ON FUNCTION public\.lm_append_cfo_daily_snapshot(?:_revision)?[^;]*\b(?:anon|authenticated|PUBLIC)\b/i);
  assert.doesNotMatch(sql, /CREATE TABLE|DROP TABLE|TRUNCATE|DELETE FROM|UPDATE public\.lm_cfo_daily_snapshots/i);
});
