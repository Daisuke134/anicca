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
