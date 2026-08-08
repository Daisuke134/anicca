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

test("route cache follow-up retains rolling identities and creates exact tenant key", () => {
  // The old provider still sends on_conflict=cache_key and old mobile instances
  // still send route-only rows while this migration rolls through the fleet.
  assert.doesNotMatch(SQL, /DROP INDEX IF EXISTS public\.lm_route_cache_cache_key_idx/);
  assert.doesNotMatch(SQL, /DROP INDEX IF EXISTS public\.lm_route_cache_mobile_key_unique/);
  assert.match(SQL, /CREATE UNIQUE INDEX IF NOT EXISTS lm_route_cache_cache_key_idx[\s\S]*ON public\.lm_route_cache \(cache_key\);/);
  assert.match(SQL, /CREATE UNIQUE INDEX IF NOT EXISTS lm_route_cache_uid_cache_key_unique[\s\S]*ON public\.lm_route_cache \(uid, cache_key\);/);
  assert.doesNotMatch(SQL, /WHERE\s+cache_key\s+IS\s+NOT\s+NULL/i);
});

test("route cache follow-up keeps old writer conflict targets during the rolling window", () => {
  assert.doesNotMatch(SQL, /DROP INDEX IF EXISTS public\.lm_route_cache_cache_key_idx/);
  assert.doesNotMatch(SQL, /DROP INDEX IF EXISTS public\.lm_route_cache_mobile_key_unique/);
  assert.match(SQL, /CREATE UNIQUE INDEX IF NOT EXISTS lm_route_cache_cache_key_idx[\s\S]*ON public\.lm_route_cache \(cache_key\);/);
  assert.match(SQL, /CREATE UNIQUE INDEX IF NOT EXISTS lm_route_cache_uid_cache_key_unique[\s\S]*ON public\.lm_route_cache \(uid, cache_key\);/);
  assert.match(SQL, /route_result IS NOT NULL[\s\S]*OR[\s\S]*route IS NOT NULL/);
});

test("migration contract simulates old provider and old mobile writes before cleanup", () => {
  const hasGlobalTarget = /CREATE UNIQUE INDEX IF NOT EXISTS lm_route_cache_cache_key_idx[\s\S]*ON public\.lm_route_cache \(cache_key\);/.test(SQL);
  const hasTenantTarget = /CREATE UNIQUE INDEX IF NOT EXISTS lm_route_cache_uid_cache_key_unique[\s\S]*ON public\.lm_route_cache \(uid, cache_key\);/.test(SQL);
  assert.equal(hasGlobalTarget, true, "old provider on_conflict=cache_key must still infer a unique target");
  assert.equal(hasTenantTarget, true, "new provider/mobile on_conflict=uid,cache_key must infer a target");

  const rows = [];
  const oldProviderWrite = (row) => {
    assert.equal(hasGlobalTarget, true);
    rows.push({ ...row, route_result: row.route_result || null });
  };
  const oldMobileWrite = (row) => {
    assert.equal(hasTenantTarget, true);
    assert.ok(row.route, "old mobile instances only send route");
    rows.push({ ...row, route_result: null });
  };
  oldProviderWrite({ uid: "tenant-a", cache_key: "legacy-provider-key", route_result: { durationSecs: 900 } });
  oldMobileWrite({ uid: "tenant-a", cache_key: "legacy-mobile-key", route: { durationSeconds: 1200 } });
  assert.equal(rows.length, 2, "both old writers remain accepted until cleanup");
  assert.deepEqual(rows[1].route, { durationSeconds: 1200 });
  assert.equal(rows[1].route_result, null, "backfill is additive; old route-only payload is not rejected");
});

test("route cache follow-up is safe after either original migration order", () => {
  assert.match(SQL, /CREATE TABLE IF NOT EXISTS public\.lm_route_cache/);
  assert.match(SQL, /ADD COLUMN IF NOT EXISTS cache_key text/);
  assert.match(SQL, /ADD COLUMN IF NOT EXISTS route jsonb/);
  assert.match(SQL, /NOT VALID/);
  assert.match(SQL, /VALIDATE CONSTRAINT/);
  assert.doesNotMatch(SQL, /SET\s+NOT\s+NULL/i);
});

test("rolling compatibility namespaces legacy and canonical keys before the global conflict target", () => {
  assert.match(SQL, /ADD COLUMN IF NOT EXISTS legacy_cache_key text/);
  assert.match(SQL, /CREATE OR REPLACE FUNCTION public\.lm_route_cache_namespace_legacy_mobile/);
  assert.match(SQL, /legacy-provider-v1/);
  assert.match(SQL, /legacy-mobile-v1/);
  assert.match(SQL, /CREATE TRIGGER lm_route_cache_namespace_legacy_mobile/);

  const fingerprint = "same-route-fingerprint";
  const canonicalKey = (uid) => `v2:${uid}:${fingerprint}`;
  const legacyProviderKey = (uid) => `legacy-provider-v1:${uid}:${fingerprint}`;
  const legacyMobileKey = (uid) => `legacy-mobile-v1:${uid}:${fingerprint}`;
  const storedKeys = [
    canonicalKey("tenant-a"), canonicalKey("tenant-b"),
    legacyProviderKey("tenant-a"), legacyProviderKey("tenant-b"),
    legacyMobileKey("tenant-a"), legacyMobileKey("tenant-b"),
  ];
  assert.equal(new Set(storedKeys).size, storedKeys.length,
    "the old global arbiter must not collapse equal route fingerprints across tenants");
});
