import { test } from "node:test";
import assert from "node:assert/strict";
import { buildOfframpOrder, offrampIdempotencyKey, submitOfframp, API_BASE } from "../crossmint-offramp.mjs";

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
  assert.throws(() => buildOfframpOrder({ bankAccountId: "ba_1", amountUsdc: "ten" }), /decimal string/);
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
  const order = buildOfframpOrder({ bankAccountId: "ba_x", amountUsdc: "5.00" });
  await assert.rejects(submitOfframp(order, { apiKey: "sk", fetchImpl }), /422: invalid bankAccountId/);
});

test("submitOfframp: requires apiKey", async () => {
  await assert.rejects(submitOfframp({}, {}), /CROSSMINT_API_KEY required/);
});
