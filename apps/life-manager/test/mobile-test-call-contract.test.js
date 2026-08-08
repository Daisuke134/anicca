"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { requestMobileCall } = require("../lib/mobile-call.js");
const { createMemoryMobileStore } = require("../lib/mobile-store.js");

function store(overrides = {}) {
  return createMemoryMobileStore({ users: [{ uid: "user-a", phone: "+819012345678", calls_enabled: true, call_language: "ja", product_locale: "en", ...overrides }] });
}

test("call requires confirmation, valid phone, and explicit enablement", async () => {
  const fake = async () => ({ ok: true, ccid: "call-1" });
  await assert.rejects(() => requestMobileCall({ uid: "user-a" }, { confirmed: false, idempotencyKey: "key-1" }, { store: store(), placeCall: fake }), (error) => error.code === "call_confirmation_required");
  await assert.rejects(() => requestMobileCall({ uid: "user-a" }, { confirmed: true, idempotencyKey: "key-1" }, { store: store({ phone: null }), placeCall: fake }), (error) => error.code === "phone_required");
  await assert.rejects(() => requestMobileCall({ uid: "user-a" }, { confirmed: true, idempotencyKey: "key-1" }, { store: store({ calls_enabled: false }), placeCall: fake }), (error) => error.code === "calls_disabled");
  await assert.rejects(() => requestMobileCall({ uid: "user-a" }, { confirmed: true, idempotencyKey: "key-1" }, { store: store({ phone: "0901234" }), placeCall: fake }), (error) => error.code === "invalid_phone");
});

test("call claim is durable before provider invocation and cooldown/daily limits are returned honestly", async () => {
  const db = store();
  let calls = 0;
  const deps = { store: db, now: () => Date.parse("2026-08-08T00:00:00.000Z"), placeCall: async (input) => { calls++; assert.equal(input.to, "+819012345678"); return { ok: true, ccid: "call-1" }; } };
  const first = await requestMobileCall({ uid: "user-a", productLocale: "en" }, { confirmed: true, idempotencyKey: "key-1" }, deps);
  assert.equal(first.status, "placed");
  assert.equal(calls, 1);
  await assert.rejects(() => requestMobileCall({ uid: "user-a", productLocale: "en" }, { confirmed: true, idempotencyKey: "key-2" }, deps), (error) => error.code === "call_rate_limited");
  assert.equal(calls, 1);
});

test("call claims enforce a global daily cap in addition to the tenant cooldown", async () => {
  const db = createMemoryMobileStore({
    callDailyGlobalLimit: 1,
    users: [
      { uid: "user-a", phone: "+819012345678", calls_enabled: true, product_locale: "en" },
      { uid: "user-b", phone: "+819012345679", calls_enabled: true, product_locale: "en" },
    ],
  });
  const deps = { store: db, now: () => Date.parse("2026-08-08T00:00:00.000Z"), placeCall: async () => ({ ok: true, ccid: "call" }) };
  await requestMobileCall({ uid: "user-a" }, { confirmed: true, idempotencyKey: "global-a" }, deps);
  await assert.rejects(() => requestMobileCall({ uid: "user-b" }, { confirmed: true, idempotencyKey: "global-b" }, deps), (error) => error.code === "call_rate_limited");
});

test("concurrent tenants consume one atomic global day slot", async () => {
  const db = createMemoryMobileStore({
    callDailyGlobalLimit: 1,
    users: [
      { uid: "user-a", phone: "+819012345678", calls_enabled: true, product_locale: "en" },
      { uid: "user-b", phone: "+819012345679", calls_enabled: true, product_locale: "en" },
    ],
  });
  const deps = { store: db, now: () => Date.parse("2026-08-08T00:00:00.000Z"), placeCall: async () => ({ ok: true, ccid: "call" }) };
  const outcomes = await Promise.allSettled([
    requestMobileCall({ uid: "user-a" }, { confirmed: true, idempotencyKey: "atomic-a" }, deps),
    requestMobileCall({ uid: "user-b" }, { confirmed: true, idempotencyKey: "atomic-b" }, deps),
  ]);
  assert.equal(outcomes.filter((item) => item.status === "fulfilled").length, 1);
  assert.equal(outcomes.filter((item) => item.status === "rejected" && item.reason.code === "call_rate_limited").length, 1);
});

test("call day guards use the UTC day for offset timestamps", async () => {
  const db = createMemoryMobileStore({
    callDailyGlobalLimit: 1,
    users: [
      { uid: "user-a", phone: "+819012345678", calls_enabled: true, product_locale: "en" },
      { uid: "user-b", phone: "+819012345679", calls_enabled: true, product_locale: "en" },
    ],
  });
  let current = "2026-08-08T00:30:00+02:00";
  const deps = { store: db, now: () => Date.parse(current), placeCall: async () => ({ ok: true, ccid: "call" }) };
  await requestMobileCall({ uid: "user-a" }, { confirmed: true, idempotencyKey: "utc-day-a" }, deps);
  current = "2026-08-08T00:00:00Z";
  await requestMobileCall({ uid: "user-b" }, { confirmed: true, idempotencyKey: "utc-day-b" }, deps);
});
