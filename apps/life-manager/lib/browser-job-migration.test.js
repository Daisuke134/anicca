"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const SQL = fs.readFileSync(path.join(
  __dirname,
  "../migrations/2026-07-28-lm-browser-jobs.sql",
), "utf8");
const UPGRADE_SQL = fs.readFileSync(path.join(
  __dirname,
  "../migrations/2026-07-28-lm-browser-jobs-principal-kind.sql",
), "utf8");
const AUTH_TRACE_SQL = fs.readFileSync(path.join(
  __dirname,
  "../migrations/2026-07-29-lm-browser-job-auth-trace.sql",
), "utf8");
const WORKROOM_PATH = path.join(__dirname, "../migrations/2026-08-31-lm-browser-job-workrooms.sql");
const WORKROOM_SQL = fs.existsSync(WORKROOM_PATH) ? fs.readFileSync(WORKROOM_PATH, "utf8") : "";

test("BROWSER-GEN-1 queue is tenant-bound, idempotent, and stores no raw prompt or credential", () => {
  assert.match(SQL, /CREATE TABLE IF NOT EXISTS public\.lm_browser_jobs/i);
  assert.match(SQL, /uid text NOT NULL/i);
  assert.match(SQL, /prompt_hash text NOT NULL/i);
  assert.match(SQL, /principal_kind text NOT NULL CHECK \(principal_kind IN \('none', 'agent_owned', 'user_provided'\)\)/i);
  assert.match(SQL, /requires_login = false AND principal_kind = 'none'[\s\S]*requires_login = true AND principal_kind IN \('agent_owned', 'user_provided'\)/i);
  assert.match(SQL, /UNIQUE \(uid, telegram_chat_id, telegram_message_id\)/i);
  assert.doesNotMatch(SQL, /\braw_prompt\b|\bpassword\b|\bcookie\b|\bauth_token\b/i);
  assert.doesNotMatch(SQL, /REFERENCES public\.lm_users/i, "the private Railway queue does not duplicate the Supabase user registry");
});

test("BROWSER-GEN-1 has closed terminal states and bounded trace/receipt JSON", () => {
  assert.match(SQL, /status IN \('queued', 'claimed', 'completed', 'possibly_completed', 'handoff_required', 'failed'\)/i);
  assert.match(SQL, /jsonb_array_length\(trace\) <= 100/i);
  assert.match(SQL, /octet_length\(trace::text\) <= 65536/i);
  assert.match(SQL, /octet_length\(receipt::text\) <= 16384/i);
});

test("claim is concurrency safe and only stale incomplete work can be reclaimed", () => {
  assert.match(SQL, /CREATE OR REPLACE FUNCTION public\.claim_lm_browser_job/i);
  assert.match(SQL, /FOR UPDATE SKIP LOCKED/i);
  assert.match(SQL, /status = 'queued'[\s\S]*status = 'claimed'[\s\S]*lease_expires_at <= clock_timestamp\(\)/i);
  assert.match(SQL, /SET status = 'claimed'/i);
});

test("trace and finish mutations are narrow functions inside the private Railway database", () => {
  for (const fn of ["claim_lm_browser_job", "append_lm_browser_job_trace", "finish_lm_browser_job"]) {
    assert.match(SQL, new RegExp(`CREATE OR REPLACE FUNCTION public\\.${fn}`, "i"));
  }
  assert.match(SQL, /SET search_path = public, pg_temp/i);
  assert.match(SQL, /'action_observed'/i);
  assert.match(SQL, /'evidence_sent'/i);
  assert.doesNotMatch(SQL, /\bTO service_role\b|\bFROM PUBLIC, anon\b/i);
});

test("trace RPC allowlist contains exactly the three auth lifecycle stages", () => {
  const authStages = [...SQL.matchAll(/'auth_context_[a-z_]+'/g)].map(([stage]) => stage);
  assert.deepEqual(authStages, [
    "'auth_context_loaded'",
    "'auth_context_saved'",
    "'auth_context_invalidated'",
  ]);
});

test("principal kind forward migration upgrades legacy browser jobs without changing historical login ownership", () => {
  assert.match(UPGRADE_SQL, /ALTER TABLE public\.lm_browser_jobs\s+ADD COLUMN IF NOT EXISTS principal_kind text/i);
  assert.match(UPGRADE_SQL, /WHEN requires_login THEN 'agent_owned'\s+ELSE 'none'/i);
  assert.match(UPGRADE_SQL, /WHERE principal_kind IS NULL/i);
  assert.match(UPGRADE_SQL, /ALTER COLUMN principal_kind SET NOT NULL/i);
  assert.match(UPGRADE_SQL, /principal_kind IN \('none', 'agent_owned', 'user_provided'\)/i);
  assert.match(UPGRADE_SQL, /requires_login = false AND principal_kind = 'none'[\s\S]*requires_login = true AND principal_kind IN \('agent_owned', 'user_provided'\)/i);
});

test("auth trace forward migration upgrades the production trace allowlist", () => {
  assert.match(AUTH_TRACE_SQL, /CREATE OR REPLACE FUNCTION public\.append_lm_browser_job_trace/i);
  const authStages = [...AUTH_TRACE_SQL.matchAll(/'auth_context_[a-z_]+'/g)].map(([stage]) => stage);
  assert.deepEqual(authStages, [
    "'auth_context_loaded'",
    "'auth_context_saved'",
    "'auth_context_invalidated'",
  ]);
  assert.match(AUTH_TRACE_SQL, /octet_length\(COALESCE\(p_meta, '\{\}'::jsonb\)::text\) > 8192/i);
  assert.match(AUTH_TRACE_SQL, /jsonb_array_length\(trace\) < 100/i);
});

test("workroom migration preserves Telegram rows and adds one tenant-bound effect identity", () => {
  assert.match(WORKROOM_SQL, /ADD COLUMN IF NOT EXISTS source_kind text/i);
  assert.match(WORKROOM_SQL, /ADD COLUMN IF NOT EXISTS source_ref text/i);
  assert.match(WORKROOM_SQL, /ADD COLUMN IF NOT EXISTS job_id text/i);
  assert.match(WORKROOM_SQL, /ADD COLUMN IF NOT EXISTS dispatch_id text/i);
  assert.match(WORKROOM_SQL, /ADD COLUMN IF NOT EXISTS effect_key text/i);
  assert.match(WORKROOM_SQL, /SET source_kind = 'telegram'/i);
  assert.match(WORKROOM_SQL, /SET source_ref = 'telegram-message:\/\/'/i);
  assert.match(WORKROOM_SQL, /ALTER COLUMN telegram_chat_id DROP NOT NULL/i);
  assert.match(WORKROOM_SQL, /source_kind IN \('telegram', 'panel', 'symphony'\)/i);
  assert.match(WORKROOM_SQL, /source_kind = 'telegram'[\s\S]*telegram_chat_id IS NOT NULL[\s\S]*source_kind IN \('panel', 'symphony'\)[\s\S]*telegram_chat_id IS NULL/i);
  assert.match(WORKROOM_SQL, /CREATE UNIQUE INDEX[\s\S]*\(uid, effect_key\)[\s\S]*WHERE effect_key IS NOT NULL/i);
  assert.doesNotMatch(WORKROOM_SQL, /\braw_prompt\b|\bpassword\b|\bcookie\b|\bauth_token\b/i);
});
