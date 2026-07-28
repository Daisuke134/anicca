"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const SQL = fs.readFileSync(path.join(
  __dirname,
  "../migrations/2026-07-28-lm-browser-jobs.sql",
), "utf8");

test("BROWSER-GEN-1 queue is tenant-bound, idempotent, and stores no raw prompt or credential", () => {
  assert.match(SQL, /CREATE TABLE IF NOT EXISTS public\.lm_browser_jobs/i);
  assert.match(SQL, /uid text NOT NULL REFERENCES public\.lm_users\(uid\) ON DELETE CASCADE/i);
  assert.match(SQL, /prompt_hash text NOT NULL/i);
  assert.match(SQL, /UNIQUE \(uid, telegram_chat_id, telegram_message_id\)/i);
  assert.doesNotMatch(SQL, /\braw_prompt\b|\bpassword\b|\bcookie\b|\bauth_token\b/i);
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

test("trace and finish mutations are narrow security-definer RPCs restricted to service_role", () => {
  for (const fn of ["claim_lm_browser_job", "append_lm_browser_job_trace", "finish_lm_browser_job"]) {
    assert.match(SQL, new RegExp(`CREATE OR REPLACE FUNCTION public\\.${fn}`, "i"));
    assert.match(SQL, new RegExp(`REVOKE ALL ON FUNCTION public\\.${fn}[\\s\\S]*FROM PUBLIC, anon, authenticated`, "i"));
    assert.match(SQL, new RegExp(`GRANT EXECUTE ON FUNCTION public\\.${fn}[\\s\\S]*TO service_role`, "i"));
  }
  assert.match(SQL, /SECURITY DEFINER\s+SET search_path = public, pg_temp/i);
  assert.match(SQL, /ALTER TABLE public\.lm_browser_jobs ENABLE ROW LEVEL SECURITY/i);
  assert.match(SQL, /REVOKE ALL ON TABLE public\.lm_browser_jobs\s+FROM PUBLIC, anon, authenticated/i);
});

