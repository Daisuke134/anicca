"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { createSupabaseMobileStore, createMemoryMobileStore } = require("../lib/mobile-store.js");
const { createSupabaseRouteStore } = require("../lib/route-cache.js");
const { legacyMobileRouteCacheKey, mobileRouteCacheKey } = require("../lib/mobile-utils.js");

function response(body, status = 200) {
  return { ok: status >= 200 && status < 300, status, json: async () => body, text: async () => JSON.stringify(body) };
}

test("Supabase mobile store scopes profile, outbox, and device operations to the server scope", async () => {
  const calls = [];
  const fetchImpl = async (input, init = {}) => {
    const url = new URL(String(input));
    calls.push({ url, init });
    if (url.pathname.endsWith("/lm_users")) return response([{ uid: "user-a", name: "A", home_address: "Tokyo" }]);
    if (url.pathname.endsWith("/lm_mobile_outbox")) return response([{ uid: "user-a", sequence: 1, id: "message:v1:1" }], init.method === "POST" ? 201 : 200);
    if (url.pathname.endsWith("/lm_mobile_devices")) return response([{ uid: "user-a", device_id: "device-a" }], init.method === "POST" ? 201 : 200);
    return response({}, 200);
  };
  const store = createSupabaseMobileStore({ supaUrl: "https://supa.example", supaKey: "service-key", fetchImpl });
  const scope = { uid: "user-a" };
  await store.readUser(scope);
  await store.patchUser(scope, { name: "A" });
  await store.appendOutbox(scope, { id: "message:v1:1", key: "chat.welcome", args: {} });
  await store.upsertDevice(scope, { token: "a".repeat(64), environment: "production", locale: "en", timezone: "UTC" });
  for (const call of calls) {
    if (call.url.pathname.endsWith("/lm_users") || call.url.pathname.endsWith("/lm_mobile_outbox") || call.url.pathname.endsWith("/lm_mobile_devices")) {
      assert.equal(call.init.method === "POST" ? JSON.parse(call.init.body).uid : call.url.searchParams.get("uid"), call.init.method === "POST" ? "user-a" : "eq.user-a");
      assert.doesNotMatch(call.url.toString(), /user-b/u);
    }
  }
});

test("memory store rejects a scope mismatch instead of permitting a client-selected tenant", async () => {
  const store = createMemoryMobileStore({ users: [{ uid: "user-a", name: "A" }, { uid: "user-b", name: "B" }] });
  assert.equal((await store.readUser({ uid: "user-a" })).name, "A");
  await assert.rejects(() => store.patchUser({ uid: "user-b" }, { name: "B" }, { expectedUid: "user-a" }), (error) => error.code === "scope_mismatch");
});

test("memory route cache accepts the authenticated scope and survives a same-process restart seam", async () => {
  const routeRequest = {
    eventId: "event-memory", eventDate: "2026-08-10", timezone: "Asia/Tokyo",
    origin: "Shibuya", destination: "Tokyo", direction: "outbound",
    arriveBy: "2026-08-10T09:00:00.000+09:00", departAt: null,
  };
  const route = { status: "route_ready", provider: "transit", timezone: "Asia/Tokyo", durationSeconds: 900 };
  const store = createMemoryMobileStore({ now: () => Date.parse("2026-08-10T08:10:00.000Z") });
  await store.writeRouteCache({ uid: "tenant-memory" }, routeRequest, route);
  const hit = await store.readRouteCache({ uid: "tenant-memory" }, routeRequest);
  assert.deepEqual(hit.value, route);
});

test("memory route cache never reuses one tenant's route for another tenant", async () => {
  const routeRequest = {
    eventId: "event-memory-isolation", eventDate: "2026-08-10", timezone: "Asia/Tokyo",
    origin: "Shibuya", destination: "Tokyo", direction: "outbound",
    arriveBy: "2026-08-10T09:00:00.000+09:00", departAt: null,
  };
  const store = createMemoryMobileStore({
    users: [{ uid: "tenant-a", name: "A" }, { uid: "tenant-b", name: "B" }],
    now: () => Date.parse("2026-08-10T08:10:00.000Z"),
  });
  const routeA = { status: "route_ready", provider: "transit", durationSeconds: 900 };
  const routeB = { status: "route_ready", provider: "transit", durationSeconds: 1200 };
  await store.writeRouteCache({ uid: "tenant-a" }, routeRequest, routeA);
  await store.writeRouteCache({ uid: "tenant-b" }, routeRequest, routeB);
  assert.deepEqual((await store.readRouteCache({ uid: "tenant-a" }, routeRequest)).value, routeA);
  assert.deepEqual((await store.readRouteCache({ uid: "tenant-b" }, routeRequest)).value, routeB);
});

test("Supabase mobile route cache persists the tenant-safe request digest and complete structured route", async () => {
  const calls = [];
  let persisted = null;
  const routeRequest = {
    eventId: "event-1", eventDate: "2026-08-10", timezone: "Asia/Tokyo",
    origin: "Shibuya", destination: "Tokyo", direction: "outbound",
    arriveBy: "2026-08-10T09:00:00.000+09:00", departAt: null,
  };
  const route = {
    status: "route_ready", provider: "transit", timezone: "Asia/Tokyo", durationSeconds: 900,
    accessWalkSecs: 60, egressWalkSecs: 120, fare: { currency: "JPY", amount: 220 }, steps: [{ trainType: "rapid", headsign: "Tokyo" }],
  };
  const fetchImpl = async (input, init = {}) => {
    const url = new URL(String(input));
    calls.push({ url, init });
    if (url.pathname.endsWith("/lm_route_cache") && init.method === "POST") {
      const next = JSON.parse(init.body);
      const wasEmpty = !persisted;
      persisted = { ...next, computed_at: "2026-08-10T08:10:00.000Z" };
      return response([persisted], wasEmpty ? 201 : 200);
    }
    if (url.pathname.endsWith("/lm_route_cache")) {
      return response(persisted ? [persisted] : []);
    }
    return response({}, 200);
  };
  const store = createSupabaseMobileStore({ supaUrl: "https://supa.example", supaKey: "service-key", fetchImpl });
  const scope = { uid: "tenant-a" };
  assert.equal(await store.readRouteCache(scope, routeRequest), null);
  const inserted = await store.writeRouteCache(scope, routeRequest, route);
  assert.deepEqual(inserted.value, route);
  const updatedRoute = { ...route, durationSeconds: 960, fare: { currency: "JPY", amount: 240 } };
  const updated = await store.writeRouteCache(scope, routeRequest, updatedRoute);
  assert.deepEqual(updated.value, updatedRoute);
  const hit = await store.readRouteCache(scope, routeRequest);
  assert.deepEqual(hit.value, updatedRoute);

  const writes = calls.filter((call) => call.init.method === "POST");
  assert.equal(writes.length, 2, "same request digest must update the existing cache row");
  const firstBody = JSON.parse(writes[0].init.body);
  const secondBody = JSON.parse(writes[1].init.body);
  assert.equal(firstBody.uid, "tenant-a");
  assert.match(firstBody.cache_key, /^v2:[0-9a-f]{64}$/u);
  assert.equal(firstBody.cache_key, secondBody.cache_key);
  assert.equal(firstBody.from_geo, routeRequest.origin);
  assert.equal(firstBody.to_geo, routeRequest.destination);
  assert.deepEqual(secondBody.route_result, updatedRoute);
  assert.equal(writes[0].url.searchParams.get("on_conflict"), "uid,cache_key");
  assert.equal(writes[1].url.searchParams.get("on_conflict"), "uid,cache_key");
});

test("Supabase mobile route store reads route_result and keeps route as a migration fallback", async () => {
  const routeRequest = {
    eventId: "event-fallback", eventDate: "2026-08-10", timezone: "Asia/Tokyo",
    origin: "Shibuya", destination: "Tokyo", direction: "outbound",
    arriveBy: "2026-08-10T09:00:00.000+09:00", departAt: null,
  };
  const legacyRoute = { status: "route_ready", provider: "transit", durationSeconds: 600 };
  let calls = 0;
  const store = createSupabaseMobileStore({
    supaUrl: "https://supa.example", supaKey: "service-key",
    fetchImpl: async (input) => {
      calls += 1;
      const url = new URL(String(input));
      assert.equal(url.searchParams.get("uid"), "eq.tenant-a");
      if (calls === 1) return response([{ route_result: legacyRoute, computed_at: "2026-08-10T08:10:00.000Z", ttl_secs: 600 }]);
      return response([{ route: legacyRoute, computed_at: "2026-08-10T08:10:00.000Z", ttl_secs: 600 }]);
    },
  });
  const hit = await store.readRouteCache({ uid: "tenant-a" }, routeRequest);
  assert.deepEqual(hit.value, legacyRoute);
  assert.equal(calls, 1, "the route-column fallback remains a read projection, not a second unscoped query");
});

test("Supabase mobile route store falls back to route when route_result is unavailable", async () => {
  const routeRequest = {
    eventId: "event-fallback-column", eventDate: "2026-08-10", timezone: "Asia/Tokyo",
    origin: "Shibuya", destination: "Tokyo", direction: "outbound",
    arriveBy: "2026-08-10T09:00:00.000+09:00", departAt: null,
  };
  const legacyRoute = { status: "route_ready", provider: "transit", durationSeconds: 600 };
  let calls = 0;
  const store = createSupabaseMobileStore({
    supaUrl: "https://supa.example", supaKey: "service-key",
    fetchImpl: async (input) => {
      calls += 1;
      const url = new URL(String(input));
      assert.equal(url.searchParams.get("uid"), "eq.tenant-a");
      if (calls === 1) return response({ code: "column_not_found" }, 400);
      return response([{ route: legacyRoute, computed_at: "2026-08-10T08:10:00.000Z", ttl_secs: 600 }]);
    },
  });
  const hit = await store.readRouteCache({ uid: "tenant-a" }, routeRequest);
  assert.deepEqual(hit.value, legacyRoute);
  assert.equal(calls, 2);
});

test("Supabase mobile route store reads a trigger-namespaced legacy route-only row", async () => {
  const routeRequest = {
    eventId: "event-legacy-trigger", eventDate: "2026-08-10", timezone: "Asia/Tokyo",
    origin: "Shibuya", destination: "Tokyo", direction: "outbound",
    arriveBy: "2026-08-10T09:00:00.000+09:00", departAt: null,
  };
  const scope = { uid: "tenant-a" };
  const legacyRoute = { status: "route_ready", provider: "transit", durationSeconds: 600 };
  const rawKey = mobileRouteCacheKey(scope, routeRequest);
  const triggerKey = legacyMobileRouteCacheKey(scope.uid, rawKey);
  const store = createSupabaseMobileStore({
    supaUrl: "https://supa.example", supaKey: "service-key",
    fetchImpl: async (input) => {
      const url = new URL(String(input));
      return response(decodeURIComponent(String(url.searchParams.get("cache_key") || "").replace(/^eq\./u, "")) === triggerKey
        ? [{ cache_key: triggerKey, route: legacyRoute, computed_at: "2026-08-10T08:10:00.000Z", ttl_secs: 600 }]
        : []);
    },
  });
  const hit = await store.readRouteCache(scope, routeRequest);
  assert.deepEqual(hit.value, legacyRoute);
});

test("mobile route cache legacy fields are derived from the request and provider result", async () => {
  const routeRequest = {
    eventId: "event-honest", eventDate: "2026-08-10", timezone: "Asia/Tokyo",
    origin: "Shibuya", destination: "Tokyo", direction: "outbound",
    arriveBy: "2026-08-10T09:00:00.000+09:00", departAt: null,
  };
  let body;
  const store = createSupabaseMobileStore({
    supaUrl: "https://supa.example", supaKey: "service-key",
    fetchImpl: async (_input, init = {}) => {
      if (init.method === "POST") body = JSON.parse(init.body);
      return response(body ? [body] : []);
    },
  });
  await store.writeRouteCache({ uid: "tenant-a" }, routeRequest, {
    status: "route_ready", provider: "transit", durationSeconds: 900,
  });
  assert.equal(body.from_geo, "Shibuya");
  assert.equal(body.to_geo, "Tokyo");
  assert.equal(body.time_bucket, Math.floor(Date.parse(routeRequest.arriveBy) / 600000));
  assert.equal(body.duration_secs, 900);
  assert.equal(body.provider, "transit");
  assert.deepEqual(body.route_result, { status: "route_ready", provider: "transit", durationSeconds: 900 });
  assert.equal(Object.hasOwn(body, "route"), false);
});

test("mobile route cache rejects a result without honest provider or duration", async () => {
  const request = {
    eventId: "event-invalid", eventDate: "2026-08-10", timezone: "Asia/Tokyo",
    origin: "Shibuya", destination: "Tokyo", direction: "outbound",
    arriveBy: "2026-08-10T09:00:00.000+09:00", departAt: null,
  };
  const store = createSupabaseMobileStore({
    supaUrl: "https://supa.example", supaKey: "service-key",
    fetchImpl: async () => response({}, 200),
  });
  await assert.rejects(
    () => store.writeRouteCache({ uid: "tenant-a" }, request, { status: "route_ready" }),
    (error) => error.code === "route_cache_write_failed" && error.retryable === true,
  );
});

test("provider adapter reads the mobile adapter's canonical route_result under the same tenant key", async () => {
  const routeRequest = {
    eventId: "event-cross-adapter", eventDate: "2026-08-10", timezone: "Asia/Tokyo",
    origin: "Shibuya", destination: "Tokyo", direction: "outbound",
    arriveBy: "2026-08-10T09:00:00.000+09:00", departAt: null,
  };
  const rows = new Map();
  const fetchImpl = async (input, init = {}) => {
    const url = new URL(String(input));
    if (init.method === "POST") {
      const body = JSON.parse(init.body);
      rows.set(`${body.uid}:${body.cache_key}`, body);
      return response([body], 201);
    }
    const uid = String(url.searchParams.get("uid") || "").replace(/^eq\./u, "");
    const cacheKey = String(url.searchParams.get("cache_key") || "").replace(/^eq\./u, "");
    const row = rows.get(`${uid}:${cacheKey}`);
    return response(row ? [row] : []);
  };
  const scope = { uid: "tenant-cross" };
  const mobile = createSupabaseMobileStore({ supaUrl: "https://supa.example", supaKey: "service", fetchImpl });
  const provider = createSupabaseRouteStore({ supaUrl: "https://supa.example", supaKey: "service", fetchImpl });
  const route = { status: "route_ready", provider: "transit", durationSeconds: 900 };
  await mobile.writeRouteCache(scope, routeRequest, route);
  const key = mobileRouteCacheKey(scope, routeRequest);
  const hit = await provider.get(key, scope);
  assert.deepEqual(hit.value, route);
  assert.equal(key, mobileRouteCacheKey({ uid: "another-tenant" }, routeRequest));
});

test("Supabase mobile route cache surfaces a write failure instead of claiming persistence", async () => {
  const routeRequest = {
    eventId: "event-failure", eventDate: "2026-08-10", timezone: "Asia/Tokyo",
    origin: "Shibuya", destination: "Tokyo", direction: "outbound",
    arriveBy: "2026-08-10T09:00:00.000+09:00", departAt: null,
  };
  const store = createSupabaseMobileStore({
    supaUrl: "https://supa.example", supaKey: "service-key",
    fetchImpl: async () => response({ code: "constraint_error" }, 409),
  });
  await assert.rejects(
    () => store.writeRouteCache({ uid: "tenant-a" }, routeRequest, { status: "route_ready", provider: "transit" }),
    (error) => error.code === "route_cache_write_failed" && error.status === 503 && error.retryable === true,
  );
});
