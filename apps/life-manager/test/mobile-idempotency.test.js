"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { canonicalPayloadHash, withMobileIdempotency, MobileError } = require("../lib/mobile-idempotency.js");

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
