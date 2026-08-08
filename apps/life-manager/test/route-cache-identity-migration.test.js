"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const SQL = fs.readFileSync(path.join(__dirname, "../migrations/2026-08-08-lm-route-cache-identity.sql"), "utf8");

test("route cache follow-up migration is additive and does not delete legacy rows", () => {
  assert.match(SQL, /ALTER TABLE public\.lm_route_cache[\s\S]*ADD COLUMN IF NOT EXISTS route_result jsonb/);
  assert.match(SQL, /UPDATE public\.lm_route_cache[\s\S]*SET route_result\s*=\s*route[\s\S]*WHERE route_result IS NULL[\s\S]*route IS NOT NULL/);
  assert.doesNotMatch(SQL, /\b(?:DELETE|TRUNCATE)\s+FROM\s+public\.lm_route_cache\b/i);
  assert.doesNotMatch(SQL, /DROP\s+TABLE\s+public\.lm_route_cache/i);
});

test("route cache follow-up drops old global identities and creates exact tenant key", () => {
  assert.match(SQL, /DROP INDEX IF EXISTS public\.lm_route_cache_cache_key_idx/);
  assert.match(SQL, /DROP INDEX IF EXISTS public\.lm_route_cache_mobile_key_unique/);
  assert.match(SQL, /CREATE UNIQUE INDEX IF NOT EXISTS lm_route_cache_uid_cache_key_unique[\s\S]*ON public\.lm_route_cache \(uid, cache_key\);/);
  assert.doesNotMatch(SQL, /CREATE UNIQUE INDEX[^;]*ON public\.lm_route_cache \(cache_key\)/);
  assert.doesNotMatch(SQL, /WHERE\s+cache_key\s+IS\s+NOT\s+NULL/i);
});

test("route cache follow-up is safe after either original migration order", () => {
  assert.match(SQL, /CREATE TABLE IF NOT EXISTS public\.lm_route_cache/);
  assert.match(SQL, /ADD COLUMN IF NOT EXISTS cache_key text/);
  assert.match(SQL, /ADD COLUMN IF NOT EXISTS route jsonb/);
  assert.match(SQL, /NOT VALID/);
  assert.match(SQL, /VALIDATE CONSTRAINT/);
  assert.doesNotMatch(SQL, /SET\s+NOT\s+NULL/i);
});
