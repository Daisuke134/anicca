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
      return response([{ ...JSON.parse(init.body), computed_at: new Date().toISOString() }], 201);
    }
    if (url.pathname.endsWith("/lm_route_cache")) {
      return response([{ cache_key: url.searchParams.get("cache_key").slice(3), route, computed_at: new Date().toISOString(), ttl_secs: 600 }]);
    }
    return response({}, 200);
  };
  const store = createSupabaseMobileStore({ supaUrl: "https://supa.example", supaKey: "service-key", fetchImpl });
  const scope = { uid: "tenant-a" };
  const hit = await store.readRouteCache(scope, routeRequest);
  assert.deepEqual(hit.value, route);
  await store.writeRouteCache(scope, routeRequest, route);
  const write = calls.find((call) => call.init.method === "POST");
  const body = JSON.parse(write.init.body);
  assert.equal(body.uid, "tenant-a");
  assert.match(body.cache_key, /^[0-9a-f]{64}$/u);
  assert.equal(body.from_geo, `mobile:${body.cache_key}`);
  assert.deepEqual(body.route, route);
  assert.equal(write.url.searchParams.get("on_conflict"), "uid,cache_key");
});
