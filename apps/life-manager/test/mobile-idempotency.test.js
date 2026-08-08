"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { canonicalPayloadHash, withMobileIdempotency, MobileError } = require("../lib/mobile-idempotency.js");
const { createMemoryMobileStore } = require("../lib/mobile-store.js");

function deps() {
  const receipts = new Map();
  return {
    receipts,
    store: {
      async readIdempotency(scope, key) { return receipts.get(`${scope.uid}:${key}`) || null; },
      async claimIdempotency(scope, key, value) {
        const id = `${scope.uid}:${key}`;
        if (receipts.has(id)) return false;
        receipts.set(id, { requestHash: value.requestHash, status: "pending", result: null });
        return true;
      },
      async completeIdempotency(scope, key, value) { receipts.set(`${scope.uid}:${key}`, { ...receipts.get(`${scope.uid}:${key}`), ...value }); },
    },
  };
}

test("canonical payload hashing is stable across object key order", () => {
  assert.equal(canonicalPayloadHash({ b: 2, a: 1 }), canonicalPayloadHash({ a: 1, b: 2 }));
  assert.notEqual(canonicalPayloadHash({ a: 1 }), canonicalPayloadHash({ a: 2 }));
});

test("same key and payload executes once and replays the durable result", async () => {
  const d = deps();
  const scope = { uid: "user-a" };
  let calls = 0;
  const input = { scope, key: "request-1", payload: { a: 1 }, operation: async () => ({ receipt: "one" }) };
  assert.deepEqual(await withMobileIdempotency(input, d), { receipt: "one" });
  assert.deepEqual(await withMobileIdempotency(input, d), { receipt: "one" });
  calls += 0;
  assert.equal(d.receipts.size, 1);
});

test("same key with different payload returns 409 and performs no side effect", async () => {
  const d = deps();
  const scope = { uid: "user-a" };
  let sideEffects = 0;
  await withMobileIdempotency({ scope, key: "request-1", payload: { a: 1 }, operation: async () => { sideEffects++; return { ok: true }; } }, d);
  await assert.rejects(
    () => withMobileIdempotency({ scope, key: "request-1", payload: { a: 2 }, operation: async () => { sideEffects++; return { ok: true }; } }, d),
    (error) => error instanceof MobileError && error.status === 409 && error.code === "idempotency_conflict",
  );
  assert.equal(sideEffects, 1);
});

test("idempotency keys meet the durable receipt minimum length", async () => {
  await assert.rejects(() => withMobileIdempotency({
    scope: { uid: "user-a" }, key: "short", payload: {}, operation: async () => ({ ok: true }),
  }, deps()), (error) => error.code === "idempotency_required");
});

test("failed idempotent mutations replay structured details", async () => {
  const d = deps();
  const input = {
    scope: { uid: "user-a" }, key: "detail-1", payload: { call: true },
    operation: async () => { throw new MobileError("call_rate_limited", "Calls are temporarily rate-limited.", 429, true, { reason: "cooldown" }); },
  };
  await assert.rejects(() => withMobileIdempotency(input, d), (error) => error.details.reason === "cooldown");
  await assert.rejects(() => withMobileIdempotency(input, d), (error) => error.details.reason === "cooldown");
});

test("token-bearing idempotent results are encrypted per request and replay exactly without plaintext secrets", async () => {
  const store = createMemoryMobileStore({ users: [{ uid: "user-a" }] });
  const scope = { uid: "user-a" };
  const payload = { method: "POST", path: "/session/refresh", body: { refreshToken: "refresh-token:v1:secret" } };
  const expected = {
    accessToken: "access:v1:secret", refreshToken: "refresh:v1:next", tokenType: "Bearer",
    expiresAt: "2026-08-08T00:20:00.000Z", refreshExpiresAt: "2026-09-08T00:00:00.000Z",
  };
  const first = await withMobileIdempotency({ scope, key: "refresh-replay-1", payload, operation: async () => expected }, { store });
  const receipt = store._idempotency.get("user-a:refresh-replay-1");
  assert.deepEqual(first, expected);
  assert.equal(receipt.result.accessToken, undefined);
  assert.equal(receipt.result.refreshToken, undefined);
  assert.equal(receipt.result.kind, "encrypted_replay:v1");
  const replay = await withMobileIdempotency({ scope, key: "refresh-replay-1", payload, operation: async () => { throw new Error("must replay"); } }, { store });
  assert.deepEqual(replay, expected);
});

test("deletion capability details are not persisted in plaintext error receipts", async () => {
  const d = deps();
  const input = {
    scope: { uid: "user-a" }, key: "delete-error-1", payload: { confirmed: true },
    operation: async () => { throw new MobileError("deletion_incomplete", "retry", 502, true, { receipt: { deletionCapability: "capability-secret" } }); },
  };
  await assert.rejects(() => withMobileIdempotency(input, d));
  assert.equal(JSON.stringify([...d.receipts.values()]).includes("capability-secret"), false);
  await assert.rejects(() => withMobileIdempotency(input, d), (error) => error.details.receipt.deletionCapability === "capability-secret");
});
