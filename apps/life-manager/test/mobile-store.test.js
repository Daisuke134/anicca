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
