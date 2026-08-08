"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const SQL = fs.readFileSync(path.join(__dirname, "../migrations/2026-08-08-lm-mobile-v1.sql"), "utf8");
const OAUTH_SQL = fs.readFileSync(path.join(__dirname, "../migrations/2026-08-09-lm-mobile-calendar-oauth.sql"), "utf8");

test("mobile migration persists the Gate 3 tenant, replay, cursor, device, call, and deletion boundaries", () => {
  for (const table of [
    "lm_mobile_oauth_states", "lm_mobile_sessions", "lm_mobile_idempotency", "lm_mobile_analysis_states",
    "lm_mobile_outbox", "lm_mobile_questions", "lm_mobile_call_attempts", "lm_mobile_call_day_guards", "lm_mobile_devices", "lm_mobile_deletion_receipts",
    "lm_route_cache",
  ]) assert.match(SQL, new RegExp(`CREATE TABLE IF NOT EXISTS public\\.${table}\\b`));
  for (const fn of [
    "claim_lm_mobile_oauth_state", "claim_lm_mobile_idempotency", "complete_lm_mobile_idempotency",
    "rotate_lm_mobile_refresh", "consume_lm_mobile_question", "claim_lm_mobile_question", "complete_lm_mobile_question", "claim_lm_mobile_call", "delete_lm_mobile_account",
    "claim_lm_mobile_device", "finalize_lm_mobile_deletion",
  ]) assert.match(SQL, new RegExp(`CREATE OR REPLACE FUNCTION public\\.${fn}\\b`));
  assert.match(SQL, /product_locale[^\n]*text/);
  assert.match(SQL, /calls_enabled boolean/);
  assert.match(SQL, /ALTER COLUMN product_locale SET DEFAULT 'en'/);
  assert.match(SQL, /ALTER COLUMN calls_enabled SET DEFAULT false/);
  assert.match(SQL, /state_hash text PRIMARY KEY/);
  assert.match(SQL, /access_token_hash text NOT NULL UNIQUE/);
  assert.match(SQL, /refresh_token_hash text NOT NULL UNIQUE/);
  assert.match(SQL, /result_expires_at timestamptz/);
  assert.match(SQL, /sequence bigint GENERATED ALWAYS AS IDENTITY/);
  assert.match(SQL, /token text NOT NULL CHECK \(token ~ '\^\[0-9a-fA-F\]\{64\}\$'/);
  assert.match(SQL, /CREATE UNIQUE INDEX IF NOT EXISTS lm_mobile_devices_token_unique/);
  assert.match(SQL, /capability_hash text/);
  assert.match(SQL, /DROP INDEX IF EXISTS public\.lm_route_cache_mobile_key_unique/);
  assert.match(SQL, /CREATE UNIQUE INDEX IF NOT EXISTS lm_route_cache_mobile_key_unique[\s\S]*?ON public\.lm_route_cache \(uid, cache_key\);/);
  assert.doesNotMatch(SQL, /lm_route_cache_mobile_key_unique[\s\S]*?WHERE cache_key IS NOT NULL/);
  assert.match(SQL, /UPDATE public\.lm_mobile_sessions SET revoked_at/);
  assert.match(SQL, /status IN \('open', 'claimed', 'answered', 'stale'\)/);
  assert.match(SQL, /global_count integer NOT NULL DEFAULT 0/);
  assert.match(SQL, /global_count = global_count \+ 1/);
  assert.match(SQL, /global_count < 100/);
  assert.match(SQL, /claim_day := \(p_now AT TIME ZONE 'UTC'\)::date/);
  assert.match(SQL, /day = claim_day/);
  assert.match(SQL, /GREATEST\(guard\.global_count, EXCLUDED\.global_count\)/);
  assert.doesNotMatch(SQL, /SELECT count\(\*\)::integer INTO global_count/);
  assert.doesNotMatch(SQL, /pg_advisory_(?:lock|xact_lock|unlock)/i);
  assert.doesNotMatch(SQL, /raw_access_token|raw_refresh_token|raw_bearer/i);
});

test("follow-up OAuth migration keeps provider facts hashed and RPCs service-role-only", () => {
  assert.match(OAUTH_SQL, /ADD COLUMN IF NOT EXISTS composio_user_id text/);
  assert.match(OAUTH_SQL, /ADD COLUMN IF NOT EXISTS connected_account_id text/);
  assert.match(OAUTH_SQL, /CREATE TABLE IF NOT EXISTS public\.lm_mobile_calendar_connections/);
  assert.match(OAUTH_SQL, /provider_subject_hash text NOT NULL CHECK \(length\(provider_subject_hash\) = 64\)/);
  for (const signature of ["claim_lm_mobile_oauth_state_v2\\(text\\)", "link_lm_mobile_calendar_identity\\(text, text, text, text, text, text, text\\)"]) {
    assert.match(OAUTH_SQL, new RegExp(`REVOKE ALL ON FUNCTION public\\.${signature} FROM PUBLIC, anon, authenticated`));
    assert.match(OAUTH_SQL, new RegExp(`GRANT EXECUTE ON FUNCTION public\\.${signature} TO service_role`));
  }
  assert.doesNotMatch(OAUTH_SQL, /raw_provider_identity|provider_email|provider_subject(?!_hash)/i);
});
