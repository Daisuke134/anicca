// lib/route-cache.test.js — C3 RED. lm_route_cache: <=1 provider call per (uid, from, to, time-bucket);
// a moved event (changed start → new bucket) recomputes; stale-beyond-TTL recomputes. Pure logic with an
// injected store (Map) + a call-counting provider. NO network.
"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const { cacheKey, timeBucket, makeRouteCache, createSupabaseRouteStore } = require("./route-cache.js");

const G = (lat, lon) => ({ lat, lon });

test("timeBucket: rounds a departure epoch to a coarse bucket (e.g. 10-min)", () => {
  const b1 = timeBucket(1_781_000_000_000);
  const b2 = timeBucket(1_781_000_000_000 + 60_000); // +1 min, same bucket
  const b3 = timeBucket(1_781_000_000_000 + 15 * 60_000); // +15 min, new bucket
  assert.equal(b1, b2);
  assert.notEqual(b1, b3);
});

test("cacheKey: stable for same (uid, from, to, bucket)", () => {
  const k1 = cacheKey("u1", G(35.68, 139.76), G(35.69, 139.70), 42);
  const k2 = cacheKey("u1", G(35.68, 139.76), G(35.69, 139.70), 42);
  assert.equal(k1, k2);
  assert.notEqual(k1, cacheKey("u1", G(35.68, 139.76), G(35.69, 139.70), 43));
});

test("getOrCompute: provider called at most ONCE per key within TTL", async () => {
  let calls = 0;
  const provider = async () => { calls++; return { durationSecs: 1029 }; };
  const cache = makeRouteCache({ store: new Map(), ttlMs: 10 * 60_000, now: () => 1000 });
  const args = ["u1", G(35.68, 139.76), G(35.69, 139.70), 100];
  const a = await cache.getOrCompute(...args, provider);
  const b = await cache.getOrCompute(...args, provider);
  assert.equal(a.durationSecs, 1029);
  assert.equal(b.durationSecs, 1029);
  assert.equal(calls, 1); // second hit is cached
});

test("getOrCompute: moved event (new bucket) recomputes", async () => {
  let calls = 0;
  const provider = async () => { calls++; return { durationSecs: 1029 }; };
  const cache = makeRouteCache({ store: new Map(), ttlMs: 10 * 60_000, now: () => 1000 });
  await cache.getOrCompute("u1", G(35.68, 139.76), G(35.69, 139.70), 100, provider);
  await cache.getOrCompute("u1", G(35.68, 139.76), G(35.69, 139.70), 101, provider); // different bucket
  assert.equal(calls, 2);
});

test("getOrCompute: stale beyond TTL recomputes", async () => {
  let calls = 0, t = 1000;
  const provider = async () => { calls++; return { durationSecs: 1029 }; };
  const cache = makeRouteCache({ store: new Map(), ttlMs: 10 * 60_000, now: () => t });
  await cache.getOrCompute("u1", G(35.68, 139.76), G(35.69, 139.70), 100, provider);
  t += 11 * 60_000; // TTL expired
  await cache.getOrCompute("u1", G(35.68, 139.76), G(35.69, 139.70), 100, provider);
  assert.equal(calls, 2);
});

test("cacheKey: coords within ~11m (4dp) COLLIDE; coords across the rounding boundary do NOT — FIND-002", () => {
  const a = cacheKey("u1", G(35.68000, 139.76000), G(35.69, 139.70), 5);
  const near = cacheKey("u1", G(35.680001, 139.760001), G(35.69, 139.70), 5); // < 1e-4 diff → same row
  const far = cacheKey("u1", G(35.6802, 139.76000), G(35.69, 139.70), 5); // > 1e-4 diff → different row
  assert.equal(a, near);
  assert.notEqual(a, far);
});

test("cacheKey: event anchor, timezone, direction, provider, and route mode are scoped", () => {
  const base = {
    eventAnchor: "2026-08-09T09:00:00+09:00",
    timezone: "Asia/Tokyo",
    direction: "outbound",
    provider: "transit",
    routeMode: "rail",
  };
  const key = cacheKey("u1", G(35.68, 139.76), G(35.69, 139.70), 42, base);
  for (const field of Object.keys(base)) {
    const changed = { ...base, [field]: `${base[field]}-changed` };
    assert.notEqual(key, cacheKey("u1", G(35.68, 139.76), G(35.69, 139.70), 42, changed), field);
  }
});

test("cacheKey: lng aliases normalize with lon and origin/destination remain directional", () => {
  const a = cacheKey("u1", { lat: 35.68, lon: 139.76 }, { lat: 35.69, lon: 139.70 }, 42);
  const b = cacheKey("u1", { lat: 35.68, lng: 139.76 }, { lat: 35.69, lng: 139.70 }, 42);
  const reversed = cacheKey("u1", { lat: 35.69, lon: 139.70 }, { lat: 35.68, lon: 139.76 }, 42);
  assert.equal(a, b);
  assert.notEqual(a, reversed);
});

test("getOrCompute: concurrent first writers spend once and a stale row recomputes", async () => {
  const rows = new Map();
  const cache = makeRouteCache({ store: rows, ttlMs: 600000, now: () => 1000 });
  let calls = 0;
  const provider = async () => {
    calls += 1;
    await new Promise((resolve) => setTimeout(resolve, 5));
    return { durationSecs: 900, provider: "transit" };
  };
  const args = ["u1", G(35.68, 139.76), G(35.69, 139.70), 42, provider, {
    eventAnchor: "2026-08-09T09:00:00+09:00", timezone: "Asia/Tokyo", provider: "transit", routeMode: "rail",
  }];
  const values = await Promise.all([cache.getOrCompute(...args), cache.getOrCompute(...args)]);
  assert.equal(calls, 1);
  assert.deepEqual(values[0], values[1]);
  assert.equal(rows.size, 1);
});

test("Supabase route store persists structured route result across cache instances", async () => {
  const rows = new Map();
  const calls = [];
  const fetchImpl = async (input, init = {}) => {
    const url = new URL(String(input));
    calls.push({ url, init });
    if (init.method === "POST") {
      const body = JSON.parse(init.body);
      rows.set(body.cache_key, body);
      return { ok: true, status: 201, json: async () => [] };
    }
    const keyExpr = url.searchParams.get("cache_key") || "";
    const row = rows.get(keyExpr.replace(/^eq\./u, ""));
    return { ok: true, status: 200, json: async () => (row ? [row] : []) };
  };
  const storeA = createSupabaseRouteStore({ supaUrl: "https://supa.invalid", supaKey: "service", fetchImpl });
  const storeB = createSupabaseRouteStore({ supaUrl: "https://supa.invalid", supaKey: "service", fetchImpl });
  const context = {
    eventAnchor: "2026-08-09T09:00:00+09:00", timezone: "Asia/Tokyo", direction: "outbound",
    provider: "transit", routeMode: "rail",
  };
  const cacheA = makeRouteCache({ store: storeA, ttlMs: 600000, now: () => 1000 });
  const cacheB = makeRouteCache({ store: storeB, ttlMs: 600000, now: () => 1000 });
  let callsA = 0;
  const value = { durationSecs: 900, steps: [{ mode: "rail", platform: null }] };
  const keyArgs = ["u1", G(35.68, 139.76), G(35.69, 139.70), 42, async () => { callsA += 1; return value; }, context];
  assert.deepEqual(await cacheA.getOrCompute(...keyArgs), value);
  let callsB = 0;
  const cached = await cacheB.getOrCompute("u1", G(35.68, 139.76), G(35.69, 139.70), 42, async () => { callsB += 1; return { durationSecs: 1 }; }, context);
  assert.deepEqual(cached, value);
  assert.equal(callsA, 1);
  assert.equal(callsB, 0);
  assert.equal(rows.size, 1);
  assert.equal(calls.filter((call) => call.init.method === "POST").length, 1);
});

test("Supabase route store writes every legacy NOT NULL route column and explicit cache conflict target", async () => {
  const requests = [];
  const fetchImpl = async (input, init = {}) => {
    requests.push({ url: new URL(String(input)), init });
    return { ok: true, status: 201, json: async () => [] };
  };
  const store = createSupabaseRouteStore({ supaUrl: "https://supa.invalid", supaKey: "service", fetchImpl });
  const cache = makeRouteCache({ store, ttlMs: 600000, now: () => 1000 });
  await cache.getOrCompute("u1", G(35.68, 139.76), G(35.69, 139.70), 42,
    async () => ({ durationSecs: 900, steps: [{ mode: "rail" }] }),
    { eventAnchor: "2026-08-09T09:00:00+09:00", timezone: "Asia/Tokyo", direction: "outbound", provider: "transit", routeMode: "rail" });
  const post = requests.find((request) => request.init.method === "POST");
  assert.ok(post, "durable cache write was attempted");
  const body = JSON.parse(post.init.body);
  assert.equal(body.uid, "u1");
  assert.equal(body.from_geo, "35.68,139.76");
  assert.equal(body.to_geo, "35.69,139.7");
  assert.equal(body.time_bucket, 42);
  assert.equal(body.duration_secs, 900);
  assert.match(post.url.search, /on_conflict=cache_key/);
});

test("route cache surfaces a failed durable write instead of silently claiming persistence", async () => {
  const store = { get: async () => null, set: async () => false };
  const cache = makeRouteCache({ store, ttlMs: 600000, now: () => 1000 });
  await assert.rejects(
    cache.getOrCompute("u1", G(35.68, 139.76), G(35.69, 139.70), 42, async () => ({ durationSecs: 900 })),
    /durable route cache write failed/
  );
});

test("two cache instances contend through the durable store and only one provider result wins", async () => {
  const rows = new Map();
  let writes = 0;
  const storeFactory = () => ({
    get: async (key) => rows.get(key) || null,
    set: async (key, record) => {
      writes += 1;
      if (!rows.has(key)) rows.set(key, record);
      return true;
    },
  });
  const cacheA = makeRouteCache({ store: storeFactory(), ttlMs: 600000, now: () => 1000 });
  const cacheB = makeRouteCache({ store: storeFactory(), ttlMs: 600000, now: () => 1000 });
  let providerCalls = 0;
  const provider = async () => { providerCalls += 1; await new Promise((r) => setTimeout(r, 5)); return { durationSecs: 900 }; };
  const args = ["u1", G(35.68, 139.76), G(35.69, 139.70), 42, provider];
  await Promise.all([cacheA.getOrCompute(...args), cacheB.getOrCompute(...args)]);
  assert.equal(writes, 2, "both writers may race but each must report durable success");
  assert.equal(rows.size, 1);
});

test("cache hits remain available when the caller marks provider work degraded", async () => {
  const store = new Map();
  const cache = makeRouteCache({ store, ttlMs: 600000, now: () => 1000 });
  const context = { provider: "transit", routeMode: "rail", allowCompute: true };
  await cache.getOrCompute("u1", G(35.68, 139.76), G(35.69, 139.70), 42, async () => ({ durationSecs: 900 }), context);
  let called = false;
  const value = await cache.getOrCompute("u1", G(35.68, 139.76), G(35.69, 139.70), 42, async () => { called = true; return null; }, { ...context, allowCompute: false });
  assert.equal(value.durationSecs, 900);
  assert.equal(called, false);
});
