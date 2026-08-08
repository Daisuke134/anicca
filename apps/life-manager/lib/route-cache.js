// lib/route-cache.js — durable route-result cache. The Map used by the original
// implementation is retained as a read-through optimization only; production
// callers inject the Supabase store below.
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

function canonicalGeo(geo) {
  if (!geo) return null;
  const lat = q(geo.lat);
  const lon = q(coordinateLongitude(geo));
  if (lat == null || lon == null) return null;
  return `${lat},${lon}`;
}

function contextValue(context, keys, fallback = "") {
  for (const key of keys) {
    if (context && context[key] != null && context[key] !== "") return String(context[key]);
  }
  return fallback;
}

function normalizeContext(context = {}) {
  const direction = context.direction || (context.departureMode ? "return" : "outbound");
  return {
    eventAnchor: contextValue(context, ["eventAnchor", "anchor", "event_at"]),
    timezone: contextValue(context, ["timezone", "tz"]),
    direction: String(direction || ""),
    provider: contextValue(context, ["provider"]),
    routeMode: contextValue(context, ["routeMode", "mode"]),
  };
}

function resolveBucketAndContext(bucket, context) {
  if (bucket && typeof bucket === "object" && !Array.isArray(bucket)) {
    const next = normalizeContext(bucket);
    const value = bucket.timeBucket == null
      ? (bucket.eventAnchor ? timeBucket(Date.parse(bucket.eventAnchor)) : "")
      : bucket.timeBucket;
    return { bucket: value, context: next };
  }
  return { bucket, context: normalizeContext(context) };
}

function cacheKey(uid, fromGeo, toGeo, bucket, context = {}) {
  const resolved = resolveBucketAndContext(bucket, context);
  return JSON.stringify([
    q(fromGeo && fromGeo.lat), q(coordinateLongitude(fromGeo)),
    q(toGeo && toGeo.lat), q(coordinateLongitude(toGeo)),
    resolved.bucket == null ? "" : String(resolved.bucket),
    resolved.context.eventAnchor,
    resolved.context.timezone,
    resolved.context.direction,
    resolved.context.provider,
    resolved.context.routeMode,
  ]);
}

function isRecord(value) {
  return Boolean(value && typeof value === "object" && Object.prototype.hasOwnProperty.call(value, "value"));
}

function recordComputedAt(record) {
  if (!record) return null;
  const raw = record.computedAt == null ? record.computed_at : record.computedAt;
  const n = typeof raw === "number" ? raw : Date.parse(raw);
  return Number.isFinite(n) ? n : null;
}

function routeRecord(value, computedAt, context, ttlMs, { uid, fromGeo, toGeo, timeBucket: bucket } = {}) {
  return {
    value,
    computedAt,
    ttlMs,
    uid: uid == null ? null : String(uid),
    fromGeo: fromGeo == null ? null : { lat: q(fromGeo.lat), lon: q(coordinateLongitude(fromGeo)) },
    toGeo: toGeo == null ? null : { lat: q(toGeo.lat), lon: q(coordinateLongitude(toGeo)) },
    timeBucket: bucket == null ? null : Number(bucket),
    provider: context.provider || null,
    eventAnchor: context.eventAnchor || null,
    timezone: context.timezone || null,
    direction: context.direction || null,
    routeMode: context.routeMode || null,
  };
}

function routeValueFromRow(row) {
  if (!row || typeof row !== "object") return null;
  const value = row.route_result == null
    ? (row.route == null ? row.value : row.route)
    : row.route_result;
  if (value == null) return null;
  return {
    value,
    computedAt: row.computed_at || row.computedAt,
    ttlMs: row.ttl_secs == null ? undefined : Number(row.ttl_secs) * 1000,
    uid: row.uid == null ? null : String(row.uid),
    fromGeo: row.from_geo || null,
    toGeo: row.to_geo || null,
    timeBucket: row.time_bucket == null ? null : Number(row.time_bucket),
    provider: row.provider || null,
    eventAnchor: row.event_anchor || row.eventAnchor || null,
    timezone: row.timezone || null,
    direction: row.direction || null,
    routeMode: row.route_mode || row.routeMode || null,
  };
}

function authHeaders(key, extra) {
  return Object.assign({ apikey: key, Authorization: `Bearer ${key}` }, extra || {});
}

// The route fingerprint intentionally remains tenant-independent so the
// durable store can use the explicit (uid, cache_key) conflict identity. The
// process-local maps need the same tenant boundary even before persistence.
function scopedProcessKey(uid, fingerprint) {
  return `${uid == null ? "" : String(uid)}\u0000${fingerprint}`;
}

// Store rows by an opaque canonical key. The migration adds cache_key so the
// complete context key is durable instead of relying on the old shared geo
// identity. All writes use Supabase upsert semantics (one winner per key).
function createSupabaseRouteStore({ supaUrl, supaKey, fetchImpl = globalThis.fetch, table = "lm_route_cache" } = {}) {
  const baseUrl = String(supaUrl || "").replace(/\/$/u, "");
  const path = `${baseUrl}/rest/v1/${encodeURIComponent(table)}`;
  async function get(key, scope = {}) {
    const uid = scope && scope.uid != null ? String(scope.uid) : "";
    if (!baseUrl || !supaKey || typeof fetchImpl !== "function" || !key || !uid) return null;
    try {
      const query = `${path}?uid=eq.${encodeURIComponent(uid)}&cache_key=eq.${encodeURIComponent(key)}&select=*&limit=1`;
      const response = await fetchImpl(query, { headers: authHeaders(supaKey) });
      if (!response || !response.ok) return null;
      const rows = await response.json();
      return routeValueFromRow(Array.isArray(rows) ? rows[0] : null);
    } catch {
      return null;
    }
  }
  async function set(key, record, scope = {}) {
    const scopedUid = scope && scope.uid != null ? String(scope.uid) : "";
    const recordUid = record && record.uid != null ? String(record.uid) : "";
    const uid = scopedUid || recordUid;
    if (!baseUrl || !supaKey || typeof fetchImpl !== "function" || !key || !record || record.value == null || !uid || (scopedUid && recordUid && scopedUid !== recordUid)) return false;
    const value = record.value;
    const duration = value.durationSeconds == null
      ? (value.durationSecs == null ? null : value.durationSecs)
      : value.durationSeconds;
    const computedDate = record.computedAt == null ? new Date() : new Date(record.computedAt);
    if (!Number.isFinite(computedDate.getTime())) return false;
    const computedAt = computedDate.toISOString();
    const provider = record.provider || value.provider;
    const body = {
      cache_key: key,
      uid,
      from_geo: canonicalGeo(record.fromGeo),
      to_geo: canonicalGeo(record.toGeo),
      time_bucket: record.timeBucket == null ? null : Number(record.timeBucket),
      provider: provider == null ? null : String(provider),
      duration_secs: duration == null ? null : Number(duration),
      geometry: value.geometry == null ? null : value.geometry,
      route_result: value,
      computed_at: computedAt,
      ttl_secs: Math.max(1, Math.round((record.ttlMs == null ? BUCKET_MS : record.ttlMs) / 1000)),
      event_anchor: record.eventAnchor || null,
      timezone: record.timezone || null,
      direction: record.direction || null,
      route_mode: record.routeMode || null,
    };
    if (!body.uid || !body.from_geo || !body.to_geo || !Number.isFinite(body.time_bucket) || !Number.isFinite(body.duration_secs) || !body.provider) {
      return false;
    }
    try {
      const response = await fetchImpl(`${path}?on_conflict=uid%2Ccache_key`, {
        method: "POST",
        headers: authHeaders(supaKey, {
          "Content-Type": "application/json",
          Prefer: "resolution=merge-duplicates,return=minimal",
        }),
        body: JSON.stringify(body),
      });
      return Boolean(response && response.ok);
    } catch {
      return false;
    }
  }
  return { get, set };
}

function durableStoreKey(store, key, uid) {
  // The default/injected process-local Map has no second-argument scope
  // contract, so namespace its physical key as well as the read-through maps.
  return store instanceof Map ? scopedProcessKey(uid, key) : key;
}

function readStore(store, key, uid) {
  return store && typeof store.get === "function" ? Promise.resolve(store.get(durableStoreKey(store, key, uid), { uid })) : Promise.resolve(null);
}

function writeStore(store, key, value, uid) {
  if (!store || typeof store.set !== "function") return Promise.resolve(false);
  return Promise.resolve(store.set(durableStoreKey(store, key, uid), value, { uid }));
}

// makeRouteCache({ store: Map-like {get,set}, ttlMs, now }) → { getOrCompute }.
// INVARIANT: provider is called at most once per canonical key in this process;
// a durable store makes the completed value survive process restarts.
function makeRouteCache({ store = new Map(), ttlMs = BUCKET_MS, now = Date.now } = {}) {
  const inFlight = new Map();
  const readThrough = new Map();

  async function getOrCompute(uid, fromGeo, toGeo, bucket, provider, context = {}) {
    let compute = provider;
    let metadata = context;
    if (typeof bucket === "function") {
      // Defensive support for a compact `(uid, from, to, provider, context)` call.
      compute = bucket;
      bucket = timeBucket(now());
      metadata = provider || {};
    }
    if (typeof compute !== "function") throw new TypeError("route cache provider must be a function");
    const resolved = resolveBucketAndContext(bucket, metadata);
    const key = cacheKey(uid, fromGeo, toGeo, resolved.bucket, resolved.context);
    const processKey = scopedProcessKey(uid, key);
    const t = Number(now());
    const isFresh = (record) => {
      const computedAt = recordComputedAt(record);
      if (computedAt == null || t - computedAt < 0) return false;
      const effectiveTtl = Number(record && record.ttlMs);
      return t - computedAt < (Number.isFinite(effectiveTtl) ? effectiveTtl : ttlMs);
    };
    const localHit = readThrough.get(processKey);
    if (localHit && isFresh(localHit)) return localHit.value;
    const durableHit = await readStore(store, key, uid);
    if (durableHit && isFresh(durableHit)) {
      readThrough.set(processKey, durableHit);
      return durableHit.value;
    }
    if (inFlight.has(processKey)) return inFlight.get(processKey);
    const pending = (async () => {
      // A concurrent caller can have populated the durable store between the
      // initial read and this claim, so re-read before spending on the provider.
      const secondHit = await readStore(store, key, uid);
      if (secondHit && isFresh(secondHit)) {
        readThrough.set(processKey, secondHit);
        return secondHit.value;
      }
      const value = await compute();
      if (value == null) return value;
      const record = routeRecord(value, Number(now()), resolved.context, ttlMs, {
        uid,
        fromGeo,
        toGeo,
        timeBucket: resolved.bucket,
      });
      readThrough.set(processKey, record);
      const persisted = await writeStore(store, key, record, uid);
      if (!persisted) {
        readThrough.delete(processKey);
        throw new Error("durable route cache write failed");
      }
      return value;
    })();
    inFlight.set(processKey, pending);
    try {
      return await pending;
    } finally {
      inFlight.delete(processKey);
    }
  }
  return { getOrCompute };
}

module.exports = {
  timeBucket,
  cacheKey,
  makeRouteCache,
  createSupabaseRouteStore,
  normalizeContext,
  BUCKET_MS,
};
