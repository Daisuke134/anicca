import { test } from "node:test";
import assert from "node:assert/strict";
import { buildOfframpOrder, offrampIdempotencyKey, submitOfframp, getOfframpStatus, mapOrderStatus, API_BASE } from "../crossmint-offramp.mjs";

test("buildOfframpOrder: referenceId REQUIRED (no idempotency collapse — FIND-002)", () => {
  assert.throws(() => buildOfframpOrder({ bankAccountId: "ba_1", amountUsdc: "5.00" }), /referenceId required/);
});

test("buildOfframpOrder: rejects zero / over-precision amount (FIND-003)", () => {
  assert.throws(() => buildOfframpOrder({ bankAccountId: "ba_1", amountUsdc: "0", referenceId: "r" }), /> 0/);
  assert.throws(() => buildOfframpOrder({ bankAccountId: "ba_1", amountUsdc: "1.1234567", referenceId: "r" }), /6 decimal/);
});

test("mapOrderStatus: failed/unknown never -> paid (FIND-006)", () => {
  assert.equal(mapOrderStatus("completed"), "paid");
  assert.equal(mapOrderStatus("failed"), "needs_review");
  assert.equal(mapOrderStatus("awaiting-payment"), "pending");
  assert.equal(mapOrderStatus(undefined), "pending");
});

test("getOfframpStatus: returns mapped {raw,status} (no raw-status misread)", async () => {
  const fetchImpl = async () => ({ ok: true, json: async () => ({ status: "failed" }) });
  const out = await getOfframpStatus("ord_1", { apiKey: "sk", fetchImpl });
  assert.equal(out.status, "needs_review");
  assert.equal(out.raw.status, "failed");
});

test("buildOfframpOrder: fiat:usd line item to a registered bankAccountId", () => {
  const o = buildOfframpOrder({ bankAccountId: "ba_123", amountUsdc: "19.87", referenceId: "u1" });
  assert.equal(o.recipient.bankAccountId, "ba_123");
  assert.deepEqual(o.lineItems, [{ currencyLocator: "fiat:usd", amount: "19.87" }]);
  assert.equal(o.metadata.referenceId, "u1");
});

test("buildOfframpOrder: rejects missing bankAccountId (CSE-registered gate)", () => {
  assert.throws(() => buildOfframpOrder({ amountUsdc: "10" }), /bankAccountId required/);
});

test("buildOfframpOrder: rejects non-decimal amount (no integer-cents footguns)", () => {
  assert.throws(() => buildOfframpOrder({ bankAccountId: "ba_1", amountUsdc: "ten", referenceId: "r" }), /decimal string/);
});

test("offrampIdempotencyKey: deterministic on the payment-defining inputs", () => {
  const a = { bankAccountId: "ba_1", amountUsdc: "19.87", referenceId: "u1" };
  assert.equal(offrampIdempotencyKey(a), offrampIdempotencyKey({ ...a }));
  assert.notEqual(offrampIdempotencyKey(a), offrampIdempotencyKey({ ...a, amountUsdc: "19.88" }));
});

test("submitOfframp: posts to the orders endpoint with x-api-key + idempotency header", async () => {
  let captured = null;
  const fetchImpl = async (url, opts) => { captured = { url, opts }; return { ok: true, json: async () => ({ orderId: "ord_1" }) }; };
  const order = buildOfframpOrder({ bankAccountId: "ba_1", amountUsdc: "5.00", referenceId: "r1" });
  const res = await submitOfframp(order, { apiKey: "sk_test", fetchImpl });
  assert.equal(res.orderId, "ord_1");
  assert.equal(captured.url, `${API_BASE}/api/2022-06-09/orders`);
  assert.equal(captured.opts.headers["x-api-key"], "sk_test");
  assert.ok(captured.opts.headers["x-idempotency-key"].startsWith("anicca-offramp-ba_1-5.00-r1"));
});

test("submitOfframp: throws on non-ok with the upstream error body (no silent false-ok)", async () => {
  const fetchImpl = async () => ({ ok: false, status: 422, text: async () => "invalid bankAccountId" });
  const order = buildOfframpOrder({ bankAccountId: "ba_x", amountUsdc: "5.00", referenceId: "rx" });
  await assert.rejects(submitOfframp(order, { apiKey: "sk", fetchImpl }), /422: invalid bankAccountId/);
});

test("submitOfframp: requires apiKey", async () => {
  await assert.rejects(submitOfframp({}, {}), /CROSSMINT_API_KEY required/);
});
