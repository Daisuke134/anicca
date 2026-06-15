// node:test — verify-tx: read a Base receipt status over JSON-RPC (injectable fetch).
import { test } from "node:test";
import assert from "node:assert/strict";
import { receiptStatus } from "../lib/verify-tx.mjs";

function fakeFetch(result) {
  return async () => ({ ok: true, json: async () => ({ jsonrpc: "2.0", id: 1, result }) });
}

const HASH_OK = "0xdead000000000000000000000000000000000000000000000000000000000001";
const HASH_REV = "0xdead000000000000000000000000000000000000000000000000000000000002";
const HASH_PEND = "0xdead000000000000000000000000000000000000000000000000000000000003";

test("returns '0x1' for a mined, successful tx", async () => {
  const s = await receiptStatus(HASH_OK, { fetchImpl: fakeFetch({ status: "0x1", transactionHash: HASH_OK }) });
  assert.equal(s, "0x1");
});

test("returns '0x0' for a reverted tx", async () => {
  const s = await receiptStatus(HASH_REV, { fetchImpl: fakeFetch({ status: "0x0" }) });
  assert.equal(s, "0x0");
});

test("returns null when the receipt is not yet available (pending/unknown tx)", async () => {
  const s = await receiptStatus(HASH_PEND, { fetchImpl: fakeFetch(null) });
  assert.equal(s, null);
});

test("throws on a non-tx-hash arg (guards the RPC URL)", async () => {
  await assert.rejects(() => receiptStatus("not-a-hash", { fetchImpl: fakeFetch({ status: "0x1" }) }));
});

test("sends eth_getTransactionReceipt with the tx hash", async () => {
  let body;
  const spy = async (_url, opts) => { body = JSON.parse(opts.body); return { ok: true, json: async () => ({ result: { status: "0x1" } }) }; };
  await receiptStatus("0xabc0000000000000000000000000000000000000000000000000000000000001", { fetchImpl: spy });
  assert.equal(body.method, "eth_getTransactionReceipt");
  assert.equal(body.params[0], "0xabc0000000000000000000000000000000000000000000000000000000000001");
});
