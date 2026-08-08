"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { createSupabaseMobileStore, createMemoryMobileStore } = require("../lib/mobile-store.js");

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
  assert.match(firstBody.cache_key, /^[0-9a-f]{64}$/u);
  assert.equal(firstBody.cache_key, secondBody.cache_key);
  assert.equal(firstBody.from_geo, `mobile:${firstBody.cache_key}`);
  assert.deepEqual(secondBody.route, updatedRoute);
  assert.equal(writes[0].url.searchParams.get("on_conflict"), "uid,cache_key");
  assert.equal(writes[1].url.searchParams.get("on_conflict"), "uid,cache_key");
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
