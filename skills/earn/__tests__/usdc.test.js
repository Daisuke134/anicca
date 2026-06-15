// node:test — usdc: read a wallet's USDC balance over Base RPC (balanceOf) + delta.
import { test } from "node:test";
import assert from "node:assert/strict";
import { usdcBalance, delta } from "../lib/usdc.mjs";

function fakeFetch(hexResult) {
  return async () => ({ ok: true, json: async () => ({ result: hexResult }) });
}

test("usdcBalance parses a hex wei6 balance into human USDC (÷1e6)", async () => {
  // 0x4c4b40 = 5_000_000 base units = 5.000000 USDC
  const bal = await usdcBalance("0x1111111111111111111111111111111111111111", { fetchImpl: fakeFetch("0x4c4b40") });
  assert.equal(bal, 5);
});

test("usdcBalance returns 0 for an empty/zero result", async () => {
  const bal = await usdcBalance("0x1111111111111111111111111111111111111111", { fetchImpl: fakeFetch("0x0") });
  assert.equal(bal, 0);
});

test("usdcBalance rejects a non-address arg (guards the RPC call)", async () => {
  await assert.rejects(() => usdcBalance("nope", { fetchImpl: fakeFetch("0x0") }));
});

test("delta returns after - before (a positive profitable wake)", () => {
  assert.equal(delta(5.5, 5.0), 0.5);
  assert.equal(delta(5.0, 5.0), 0);
});

test("usdcBalance builds an eth_call to the USDC contract with balanceOf(address)", async () => {
  let body;
  const spy = async (_url, opts) => { body = JSON.parse(opts.body); return { ok: true, json: async () => ({ result: "0x0" }) }; };
  await usdcBalance("0x833589fcd6edb6e08f4c7c32d4f71b54bda02913", { fetchImpl: spy });
  assert.equal(body.method, "eth_call");
  // balanceOf selector 0x70a08231 + left-padded address
  assert.match(body.params[0].data, /^0x70a08231/);
  assert.ok(body.params[0].data.endsWith("833589fcd6edb6e08f4c7c32d4f71b54bda02913"));
});
