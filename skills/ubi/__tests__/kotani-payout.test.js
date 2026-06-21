import { test } from "node:test";
import assert from "node:assert/strict";
import { buildOfframpRequest, mapOfframpStatus, submitOfframp, getOfframpStatus, kotaniIdempotencyKey, assertPayableAmount, API_BASE } from "../kotani-payout.mjs";

test("buildOfframpRequest: rejects zero / over-precision amount (FIND-003)", () => {
  const base = { referenceId: "u1", fiatCurrency: "KES", customerKey: "c", fiatWalletId: "w", senderAddress: "0x" };
  assert.throws(() => buildOfframpRequest({ ...base, cryptoAmount: "0" }), /> 0/);
  assert.throws(() => buildOfframpRequest({ ...base, cryptoAmount: "1.1234567" }), /6 decimal/);
});

test("kotaniIdempotencyKey: deterministic on referenceId, requires it", () => {
  assert.equal(kotaniIdempotencyKey("u1"), kotaniIdempotencyKey("u1"));
  assert.notEqual(kotaniIdempotencyKey("u1"), kotaniIdempotencyKey("u2"));
  assert.throws(() => kotaniIdempotencyKey(""), /referenceId required/);
});

test("submitOfframp: sends x-idempotency-key from referenceId (FIND-001 no double-send)", async () => {
  let captured = null;
  const fetchImpl = async (url, opts) => { captured = opts; return { ok: true, json: async () => ({ status: "PENDING" }) }; };
  const body = buildOfframpRequest({ referenceId: "u1", cryptoAmount: "5", fiatCurrency: "KES", customerKey: "c", fiatWalletId: "w", senderAddress: "0x" });
  await submitOfframp(body, { apiKey: "k", fetchImpl });
  assert.equal(captured.headers["x-idempotency-key"], "kotani-offramp-u1");
});

test("buildOfframpRequest: shapes the /api/v3/offramp body, own-wallet sender", () => {
  const r = buildOfframpRequest({ referenceId: "u1", cryptoAmount: "19.87", fiatCurrency: "KES", customerKey: "cust_1", fiatWalletId: "fw_1", senderAddress: "0xanicca" });
  assert.equal(r.referenceId, "u1");
  assert.equal(r.cryptoAmount, "19.87");
  assert.equal(r.fiatCurrency, "KES");
  assert.equal(r.customerKey, "cust_1");
  assert.equal(r.fiatWalletId, "fw_1");
  assert.equal(r.senderAddress, "0xanicca");
  assert.equal(r.usingIntegratedWallet, false);
});

test("buildOfframpRequest: rejects each missing required field + non-decimal amount", () => {
  const base = { referenceId: "u1", cryptoAmount: "1", fiatCurrency: "KES", customerKey: "c", fiatWalletId: "w", senderAddress: "0x" };
  assert.throws(() => buildOfframpRequest({ ...base, referenceId: "" }), /referenceId required/);
  assert.throws(() => buildOfframpRequest({ ...base, customerKey: "" }), /customerKey required/);
  assert.throws(() => buildOfframpRequest({ ...base, fiatWalletId: "" }), /fiatWalletId required/);
  assert.throws(() => buildOfframpRequest({ ...base, fiatCurrency: "" }), /fiatCurrency required/);
  assert.throws(() => buildOfframpRequest({ ...base, cryptoAmount: "lots" }), /decimal string/);
});

test("mapOfframpStatus: success->paid, failure->needs_review (never auto-resend), else pending", () => {
  assert.equal(mapOfframpStatus("SUCCESSFUL"), "paid");
  assert.equal(mapOfframpStatus("completed"), "paid");
  assert.equal(mapOfframpStatus("FAILED"), "needs_review");
  assert.equal(mapOfframpStatus("CANCELLED"), "needs_review");
  assert.equal(mapOfframpStatus("PENDING"), "pending");
  assert.equal(mapOfframpStatus(undefined), "pending"); // unknown never reads as paid
});

test("submitOfframp: POSTs to /api/v3/offramp with auth + body", async () => {
  let captured = null;
  const fetchImpl = async (url, opts) => { captured = { url, opts }; return { ok: true, json: async () => ({ referenceId: "u1", status: "PENDING" }) }; };
  const body = buildOfframpRequest({ referenceId: "u1", cryptoAmount: "5", fiatCurrency: "KES", customerKey: "c", fiatWalletId: "w", senderAddress: "0x" });
  const res = await submitOfframp(body, { apiKey: "k_test", fetchImpl });
  assert.equal(res.status, "PENDING");
  assert.equal(captured.url, `${API_BASE}/api/v3/offramp`);
  assert.match(captured.opts.headers.Authorization, /Bearer k_test/);
});

test("submitOfframp: throws on non-ok with upstream body (no silent false-ok on money)", async () => {
  const fetchImpl = async () => ({ ok: false, status: 400, text: async () => "bad customerKey" });
  const body = buildOfframpRequest({ referenceId: "u1", cryptoAmount: "5", fiatCurrency: "KES", customerKey: "c", fiatWalletId: "w", senderAddress: "0x" });
  await assert.rejects(submitOfframp(body, { apiKey: "k", fetchImpl }), /400: bad customerKey/);
});

test("submitOfframp: requires apiKey", async () => {
  await assert.rejects(submitOfframp({}, {}), /KOTANI_API_KEY required/);
});

test("getOfframpStatus: maps the polled status", async () => {
  const fetchImpl = async () => ({ ok: true, json: async () => ({ status: "SUCCESSFUL" }) });
  const out = await getOfframpStatus("u1", { apiKey: "k", fetchImpl });
  assert.equal(out.status, "paid");
});
