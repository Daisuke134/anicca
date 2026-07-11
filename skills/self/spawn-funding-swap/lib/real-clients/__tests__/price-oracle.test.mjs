// VCSDD spawn-funding-swap Phase 2a (sprint-2, RED). PROP-036 — lib/real-clients/price-oracle.mjs.
// fetchImpl is always mocked (NFR-6). Written against a file that does NOT exist yet -- every test below
// MUST fail (module-not-found) until Phase 2b.
import { test } from "node:test";
import assert from "node:assert/strict";
import { createRealPriceOracle } from "../price-oracle.mjs";

test("PROP-036: getAktUsdPrice resolves the live-shaped CoinGecko response's akash-network.usd field", async () => {
  const oracle = createRealPriceOracle({ fetchImpl: async () => ({ ok: true, json: async () => ({ "akash-network": { usd: 0.606867 } }) }) });
  const price = await oracle.getAktUsdPrice();
  assert.equal(price, 0.606867);
  assert.equal(typeof price, "number");
});

test("PROP-036: getAktUsdPrice throws on a non-2xx HTTP response", async () => {
  const oracle = createRealPriceOracle({ fetchImpl: async () => ({ ok: false, status: 503 }) });
  await assert.rejects(() => oracle.getAktUsdPrice());
});

test("PROP-036: getAktUsdPrice throws when akash-network is missing from the response", async () => {
  const oracle = createRealPriceOracle({ fetchImpl: async () => ({ ok: true, json: async () => ({}) }) });
  await assert.rejects(() => oracle.getAktUsdPrice());
});

test("PROP-036: getAktUsdPrice throws when usd is zero (never returns a non-positive price)", async () => {
  const oracle = createRealPriceOracle({ fetchImpl: async () => ({ ok: true, json: async () => ({ "akash-network": { usd: 0 } }) }) });
  await assert.rejects(() => oracle.getAktUsdPrice());
});

test("PROP-036: getAktUsdPrice throws when usd is negative", async () => {
  const oracle = createRealPriceOracle({ fetchImpl: async () => ({ ok: true, json: async () => ({ "akash-network": { usd: -1 } }) }) });
  await assert.rejects(() => oracle.getAktUsdPrice());
});

test("PROP-036: getAktUsdPrice throws when usd is NaN/non-numeric", async () => {
  const oracle = createRealPriceOracle({ fetchImpl: async () => ({ ok: true, json: async () => ({ "akash-network": { usd: "not-a-number" } }) }) });
  await assert.rejects(() => oracle.getAktUsdPrice());
});

test("PROP-036: getAktUsdPrice throws when usd is Infinity", async () => {
  const oracle = createRealPriceOracle({ fetchImpl: async () => ({ ok: true, json: async () => ({ "akash-network": { usd: Infinity } }) }) });
  await assert.rejects(() => oracle.getAktUsdPrice());
});
