// lib/route-cache.js — C3 (VCSDD life-manager-cost-connect-reliability): route-result cache so the 60s
// scheduler tick does NOT recompute a route it already has. This is a NEW store, distinct from
// lm_travel_log (which stays a dedup/claim ledger). In production the `store` is Supabase `lm_route_cache`
// (uid, from_geo, to_geo, time_bucket, provider, duration_secs, geometry, computed_at, ttl); here it is
// injected so the logic is pure + unit-testable.
"use strict";

const BUCKET_MS = 10 * 60_000; // coarse 10-min bucket: a moved event lands in a new bucket → recompute.

// Round a departure epoch (ms) down to a coarse bucket index.
function timeBucket(epochMs, bucketMs = BUCKET_MS) {
  return Math.floor(epochMs / bucketMs);
}

// Round a coordinate so trivially-different geos share a cache row (~11m at 4 dp is plenty for a route).
const q = (n) => Math.round(n * 1e4) / 1e4;

function cacheKey(uid, fromGeo, toGeo, bucket) {
  return [uid, q(fromGeo.lat), q(fromGeo.lon), q(toGeo.lat), q(toGeo.lon), bucket].join("|");
}

// makeRouteCache({ store: Map-like {get,set}, ttlMs, now }) → { getOrCompute }.
// INVARIANT: the provider is called at most once per (uid, from, to, bucket) within ttlMs.
function makeRouteCache({ store, ttlMs = BUCKET_MS, now = Date.now }) {
  async function getOrCompute(uid, fromGeo, toGeo, bucket, provider) {
    const key = cacheKey(uid, fromGeo, toGeo, bucket);
    const hit = store.get(key);
    const t = now();
    if (hit && t - hit.computedAt < ttlMs) return hit.value;
    const value = await provider();
    store.set(key, { value, computedAt: t });
    return value;
  }
  return { getOrCompute };
}

module.exports = { timeBucket, cacheKey, makeRouteCache, BUCKET_MS };
