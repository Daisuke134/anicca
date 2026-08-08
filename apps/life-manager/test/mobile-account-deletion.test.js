"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { deleteMobileAccount } = require("../lib/mobile-account.js");
const { createMemoryMobileStore } = require("../lib/mobile-store.js");

test("account deletion requires confirmation and returns a durable provider cleanup receipt", async () => {
  const store = createMemoryMobileStore({ users: [{ uid: "user-a", name: "A" }, { uid: "user-b", name: "B" }] });
  const calls = [];
  const result = await deleteMobileAccount({ uid: "user-a" }, { confirmed: true, operationId: "delete-1" }, {
    store, disconnectCalendar: async (scope) => { calls.push(["calendar", scope.uid]); return { state: "disconnected" }; },
  });
  assert.equal(result.status, "completed");
  assert.equal(result.operationId, "delete-1");
  assert.deepEqual(calls, [["calendar", "user-a"]]);
  assert.equal(store._users.has("user-a"), false);
  assert.equal(store._users.has("user-b"), true);
  await assert.rejects(() => deleteMobileAccount({ uid: "user-b" }, { confirmed: false }, { store }), (error) => error.code === "deletion_confirmation_required");
});

test("unknown provider cleanup never claims deletion completed and does not cascade account data", async () => {
  const store = createMemoryMobileStore({ users: [{ uid: "user-a" }] });
  await assert.rejects(() => deleteMobileAccount({ uid: "user-a" }, { confirmed: true, operationId: "delete-2" }, { store, disconnectCalendar: async () => undefined }), (error) => error.code === "deletion_incomplete");
  assert.equal(store._users.has("user-a"), true);
  assert.equal([...store._deletionReceipts.values()][0].status, "incomplete");
});

test("database cascade failure leaves an incomplete durable receipt", async () => {
  const receipts = [];
  const store = {
    async revokeAllSessions() {},
    async deleteAccount() { throw new Error("database unavailable"); },
    async writeDeletionReceipt(_scope, receipt) { receipts.push(receipt); return receipt; },
  };
  await assert.rejects(() => deleteMobileAccount({ uid: "user-a" }, { confirmed: true, operationId: "delete-db" }, {
    store, disconnectCalendar: async () => ({ state: "disconnected" }),
  }), (error) => error.code === "deletion_incomplete");
  assert.equal(receipts[0].status, "incomplete");
});

test("account deletion removes tenant idempotency receipts with the account cascade", async () => {
  const store = createMemoryMobileStore({ users: [{ uid: "user-a" }] });
  await store.claimIdempotency({ uid: "user-a" }, "delete-key", { requestHash: "hash", status: "pending" });
  await deleteMobileAccount({ uid: "user-a" }, { confirmed: true, operationId: "delete-receipts" }, {
    store, disconnectCalendar: async () => ({ state: "disconnected" }),
  });
  assert.equal(store._idempotency.size, 0);
});

test("router deletion can preserve its current idempotency receipt for replay", async () => {
  const store = createMemoryMobileStore({ users: [{ uid: "user-a" }] });
  await store.claimIdempotency({ uid: "user-a" }, "delete-key", { requestHash: "hash", status: "pending" });
  await store.claimIdempotency({ uid: "user-a" }, "other-key", { requestHash: "hash", status: "pending" });
  await deleteMobileAccount({ uid: "user-a" }, { confirmed: true, operationId: "delete-replay", idempotencyKey: "delete-key" }, {
    store, disconnectCalendar: async () => ({ state: "disconnected" }),
  });
  assert.equal(store._idempotency.has("user-a:delete-key"), true);
  assert.equal(store._idempotency.has("user-a:other-key"), false);
});

test("already-disabled provider cleanup is a completed disconnect", async () => {
  const store = createMemoryMobileStore({ users: [{ uid: "user-a" }] });
  const result = await deleteMobileAccount({ uid: "user-a" }, { confirmed: true, operationId: "delete-disabled" }, {
    store, disconnectCalendar: async () => ({ provider: "calendar", state: "action_required" }),
  });
  assert.equal(result.status, "completed");
  assert.equal(result.providerCleanup[0].status, "disconnected");
});

test("provider cleanup is resumable and precedes atomic terminal session revocation", async () => {
  const order = [];
  let attempts = 0;
  const receipts = new Map();
  const store = {
    async readDeletionReceipt(_scope, operationId) { return receipts.get(operationId) || null; },
    async writeDeletionReceipt(_scope, receipt) { receipts.set(receipt.operationId, { ...receipt }); return receipt; },
    async revokeAllSessions() { order.push("revoke"); },
    async finalizeAccountDeletion() { order.push("finalize"); return { operationId: "delete-resume", status: "completed", completedAt: "2026-08-08T00:00:00.000Z", providerCleanup: [{ provider: "calendar", status: "disconnected" }] }; },
  };
  await assert.rejects(() => deleteMobileAccount({ uid: "user-a" }, { confirmed: true, operationId: "delete-resume", idempotencyKey: "delete-capability-1" }, {
    store, disconnectCalendar: async () => { attempts++; return undefined; },
  }), (error) => error.code === "deletion_incomplete");
  assert.deepEqual(order, []);
  await deleteMobileAccount({ uid: "user-a" }, { confirmed: true, operationId: "delete-resume", idempotencyKey: "delete-capability-1" }, {
    store, disconnectCalendar: async () => { attempts++; return { state: "disconnected" }; },
  });
  assert.deepEqual(order, ["finalize"]);
  assert.equal(attempts, 2);
  assert.match(receipts.get("delete-resume").capabilityHash, /^[0-9a-f]{64}$/u);
  assert.equal(JSON.stringify(receipts).includes("delete-capability-1"), false);
});
