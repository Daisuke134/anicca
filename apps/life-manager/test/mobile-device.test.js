"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { upsertMobileDevice, removeMobileDevice } = require("../lib/mobile-device.js");
const { createMemoryMobileStore } = require("../lib/mobile-store.js");

test("APNs registration validates token, environment, locale, and timezone under tenant scope", async () => {
  const store = createMemoryMobileStore({ users: [{ uid: "user-a" }] });
  const token = "AB".repeat(32);
  const result = await upsertMobileDevice({ uid: "user-a" }, { token, environment: "production", locale: "ja", timezone: "Asia/Tokyo" }, { store, now: () => Date.parse("2026-08-08T00:00:00.000Z") });
  assert.match(result.deviceId, /^device:v1:/u);
  assert.equal(result.token, token.toLowerCase());
  assert.equal(result.lastSeenAt, "2026-08-08T00:00:00.000Z");
  await assert.rejects(() => upsertMobileDevice({ uid: "user-a" }, { token: "short", environment: "production", locale: "en", timezone: "UTC" }, { store }), (error) => error.code === "device_token_invalid");
  await assert.rejects(() => upsertMobileDevice({ uid: "user-a" }, { token, environment: "sandbox", locale: "en", timezone: "UTC" }, { store }), (error) => error.code === "device_environment_invalid");
});

test("device deletion is authenticated and idempotent", async () => {
  const store = createMemoryMobileStore({ users: [{ uid: "user-a" }] });
  const token = "aa".repeat(32);
  await upsertMobileDevice({ uid: "user-a" }, { token, environment: "development", locale: "en", timezone: "UTC" }, { store });
  assert.deepEqual(await removeMobileDevice({ uid: "user-a" }, { token }, { store }), { deleted: true });
  assert.deepEqual(await removeMobileDevice({ uid: "user-a" }, { token }, { store }), { deleted: true });
});
