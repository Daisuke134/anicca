// lib/route-cache.test.js — C3 RED. lm_route_cache: <=1 provider call per (uid, from, to, time-bucket);
// a moved event (changed start → new bucket) recomputes; stale-beyond-TTL recomputes. Pure logic with an
// injected store (Map) + a call-counting provider. NO network.
"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const { cacheKey, timeBucket, makeRouteCache } = require("./route-cache.js"); // missing → RED

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

test("cacheKey: provider, endpoints, mode, anchor type, timezone/service date, and time bucket are scoped", () => {
  const base = {
    timezone: "Asia/Tokyo",
    serviceDate: "20260827",
    anchorType: "arrival",
    provider: "transit",
    mode: "transit",
  };
  const key = cacheKey("tenant-a", G(35.68, 139.76), G(35.69, 139.70), 42, base);
  assert.notEqual(key, cacheKey("tenant-b", G(35.68, 139.76), G(35.69, 139.70), 42, base));
  assert.notEqual(key, cacheKey("tenant-a", G(35.6801, 139.76), G(35.69, 139.70), 42, base));
  assert.notEqual(key, cacheKey("tenant-a", G(35.68, 139.76), G(35.6901, 139.70), 42, base));
  assert.notEqual(key, cacheKey("tenant-a", G(35.68, 139.76), G(35.69, 139.70), 42, { ...base, provider: "google" }));
  assert.notEqual(key, cacheKey("tenant-a", G(35.68, 139.76), G(35.69, 139.70), 42, { ...base, mode: "drive" }));
  assert.notEqual(key, cacheKey("tenant-a", G(35.68, 139.76), G(35.69, 139.70), 42, { ...base, anchorType: "departure" }));
  assert.notEqual(key, cacheKey("tenant-a", G(35.68, 139.76), G(35.69, 139.70), 42, { ...base, timezone: "America/New_York" }));
  assert.notEqual(key, cacheKey("tenant-a", G(35.68, 139.76), G(35.69, 139.70), 42, { ...base, serviceDate: "20260828" }));
  assert.notEqual(key, cacheKey("tenant-a", G(35.68, 139.76), G(35.69, 139.70), 43, base));
});

test("getOrCompute: provider-scoped contexts do not share a cached route", async () => {
  let calls = 0;
  const provider = async () => { calls++; return { durationSeconds: 600 }; };
  const cache = makeRouteCache({ store: new Map(), ttlMs: 10 * 60_000, now: () => 1000 });
  const args = ["tenant-a", G(35.68, 139.76), G(35.69, 139.70), 42];
  await cache.getOrCompute(...args, provider, { provider: "transit", mode: "transit", timezone: "Asia/Tokyo", serviceDate: "20260827", anchorType: "arrival" });
  await cache.getOrCompute(...args, provider, { provider: "google", mode: "drive", timezone: "Asia/Tokyo", serviceDate: "20260827", anchorType: "arrival" });
  assert.equal(calls, 2);
});

test("getOrCompute: a null route is retried, then the accepted route is cached", async () => {
  let calls = 0;
  const provider = async () => calls++ === 0 ? null : { durationSecs: 1029 };
  const cache = makeRouteCache({ store: new Map(), ttlMs: 10 * 60_000, now: () => 1000 });
  const args = ["u1", G(35.68, 139.76), G(35.69, 139.70), 100];

  assert.equal(await cache.getOrCompute(...args, provider), null);
  const route = await cache.getOrCompute(...args, provider);
  assert.deepEqual(route, { durationSecs: 1029 });
  assert.deepEqual(await cache.getOrCompute(...args, provider), route);
  assert.equal(calls, 2);
});

test("getOrCompute: concurrent null calls share in-flight work, then a later call retries", async () => {
  let calls = 0;
  let release;
  const gate = new Promise((resolve) => { release = resolve; });
  const provider = async () => {
    calls += 1;
    if (calls === 1) { await gate; return null; }
    return { durationSecs: 1029 };
  };
  const cache = makeRouteCache({ store: new Map(), ttlMs: 10 * 60_000, now: () => 1000 });
  const args = ["u1", G(35.68, 139.76), G(35.69, 139.70), 100];

  const first = cache.getOrCompute(...args, provider);
  const second = cache.getOrCompute(...args, provider);
  assert.equal(calls, 1);
  release();
  assert.deepEqual(await Promise.all([first, second]), [null, null]);
  assert.deepEqual(await cache.getOrCompute(...args, provider), { durationSecs: 1029 });
  assert.equal(calls, 2);
});

test("getOrCompute: an undefined route is not cached", async () => {
  let calls = 0;
  const provider = async () => calls++ === 0 ? undefined : { durationSecs: 1029 };
  const cache = makeRouteCache({ store: new Map(), ttlMs: 10 * 60_000, now: () => 1000 });
  const args = ["u1", G(35.68, 139.76), G(35.69, 139.70), 100];

  assert.equal(await cache.getOrCompute(...args, provider), undefined);
  assert.deepEqual(await cache.getOrCompute(...args, provider), { durationSecs: 1029 });
  assert.equal(calls, 2);
});
