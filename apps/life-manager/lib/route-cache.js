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
const q = (n) => {
  const value = Number(n);
  return Number.isFinite(value) ? Math.round(value * 1e4) / 1e4 : null;
};

function coordinateLongitude(geo) {
  return geo && (geo.lon == null ? geo.lng : geo.lon);
}

function contextValue(context, keys) {
  for (const key of keys) {
    if (context && context[key] != null && context[key] !== "") return String(context[key]);
  }
  return "";
}

function normalizeContext(context = {}) {
  const source = context && typeof context === "object" ? context : {};
  return {
    provider: contextValue(source, ["provider"]),
    mode: contextValue(source, ["mode"]),
    anchorType: contextValue(source, ["anchorType"]),
    timezone: contextValue(source, ["timezone"]),
    serviceDate: contextValue(source, ["serviceDate"]),
  };
}

function resolveBucketAndContext(bucket, context) {
  // Keep the explicit scope object available for cache-key inspection while retaining the original
  // positional `(uid, from, to, bucket, provider)` API.
  if (bucket && typeof bucket === "object" && !Array.isArray(bucket)) {
    const merged = { ...bucket, ...(context && typeof context === "object" ? context : {}) };
    const normalized = normalizeContext(merged);
    const value = merged.timeBucket == null ? merged.bucket : merged.timeBucket;
    return { bucket: value == null ? "" : String(value), context: normalized };
  }
  return { bucket: bucket == null ? "" : String(bucket), context: normalizeContext(context) };
}

function cacheKey(uid, fromGeo, toGeo, bucket, context = {}) {
  const resolved = resolveBucketAndContext(bucket, context);
  // JSON avoids delimiter collisions and leaves every scope component explicit. In particular,
  // provider/mode and anchor direction must never share a route result accidentally.
  return JSON.stringify([
    uid == null ? "" : String(uid),
    q(fromGeo && fromGeo.lat), q(coordinateLongitude(fromGeo)),
    q(toGeo && toGeo.lat), q(coordinateLongitude(toGeo)),
    resolved.context.provider,
    resolved.context.mode,
    resolved.context.timezone,
    resolved.context.serviceDate,
    resolved.context.anchorType,
    resolved.bucket,
  ]);
}

// makeRouteCache({ store: Map-like {get,set}, ttlMs, now }) → { getOrCompute }.
// INVARIANT: the provider is called at most once per scoped route key within ttlMs.
function makeRouteCache({ store = new Map(), ttlMs = BUCKET_MS, now = Date.now } = {}) {
  const inFlight = new Map();
  async function getOrCompute(uid, fromGeo, toGeo, bucket, provider, context = {}) {
    const key = cacheKey(uid, fromGeo, toGeo, bucket, context);
    const t = now();
    const hit = store && typeof store.get === "function" ? store.get(key) : null;
    if (hit && Number.isFinite(hit.computedAt) && t - hit.computedAt < ttlMs) return hit.value;
    if (inFlight.has(key)) return inFlight.get(key);
    const run = (async () => {
      const value = await provider();
      const computedAt = now();
      if (value != null && store && typeof store.set === "function") store.set(key, { value, computedAt });
      return value;
    })();
    inFlight.set(key, run);
    try {
      return await run;
    } finally {
      inFlight.delete(key);
    }
  }
  return { getOrCompute };
}

module.exports = { timeBucket, cacheKey, makeRouteCache, BUCKET_MS };
