// chain-reader.js has no real-RPC tests (same precedent as the original Base-only reader — enrich.test.js
// exercises the money math via mocks). This covers the deterministic "unconfigured" fallback path (no RPC
// URL / no ids => every accessor throws, never a fake number) for all three chains, plus Solana's declared
// native-token decimals (9, NOT 18 — the bug this file's comment warns enrich.js about).
const { test } = require("node:test");
const assert = require("node:assert");
const { makeBaseReader, makeSolanaReader, makePolygonReader } = require("../chain-reader");

test("makeBaseReader with no ids never touches the network and every accessor throws", async () => {
  const r = await makeBaseReader([]);
  assert.throws(() => r.ethUsdPrice());
  assert.throws(() => r.usdcBalanceAtomic("0xaaa"));
  assert.throws(() => r.nativeBalanceWei("0xaaa"));
  assert.throws(() => r.externalInflowsUsd("0xaaa", 0, new Set()));
});

test("makeSolanaReader with no ids never touches the network; declares nativeDecimals=9", async () => {
  const r = await makeSolanaReader([]);
  assert.throws(() => r.ethUsdPrice());
  assert.throws(() => r.usdcBalanceAtomic("SoL1"));
  assert.throws(() => r.nativeBalanceWei("SoL1"));
  assert.throws(() => r.externalInflowsUsd()); // not implemented — always unverified by design
  assert.strictEqual(r.nativeDecimals(), 9);
});

test("makePolygonReader with no ids never touches the network; native contribution is always 0", async () => {
  const r = await makePolygonReader([]);
  assert.throws(() => r.usdcBalanceAtomic("0xpoly"));
  assert.strictEqual(r.nativeBalanceWei("0xpoly"), 0n); // MATIC dust never counted, never throws
  assert.strictEqual(r.ethUsdPrice(), 0); // harmless since native is always 0
});
