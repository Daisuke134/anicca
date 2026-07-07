// VCSDD anicca-agent-spawn, Phase 2a (RED). REQ-306 selectCloudTarget (pure, deterministic,
// bookkeeping-only comparison) + the new AKT-USD/NOS-USD fail-closed price-fetch step.
// cloud-target.mjs does not exist yet — expected to fail at import time (module-not-found).
import { test } from "node:test";
import assert from "node:assert/strict";
import { selectCloudTarget, fetchAktUsdPrice, fetchNosUsdPrice } from "../cloud-target.mjs";

test("PROP-306a: lower normalized price wins when both providers are available", () => {
  assert.equal(selectCloudTarget({ nosanaAvailable: true, nosanaPriceUsd: 1, akashAvailable: true, akashPriceUsd: 2 }), "nosana");
  assert.equal(selectCloudTarget({ nosanaAvailable: true, nosanaPriceUsd: 3, akashAvailable: true, akashPriceUsd: 2 }), "akash");
});

test("PROP-306b: equal normalized prices, both available -> deterministic tie-breaker, always 'nosana', never randomized", () => {
  const args = { nosanaAvailable: true, nosanaPriceUsd: 5, akashAvailable: true, akashPriceUsd: 5 };
  assert.equal(selectCloudTarget(args), "nosana");
  assert.equal(selectCloudTarget(args), "nosana");
  assert.equal(selectCloudTarget(args), "nosana");
});

test("PROP-306c: exactly one provider unavailable -> the other is selected regardless of price", () => {
  assert.equal(selectCloudTarget({ nosanaAvailable: false, nosanaPriceUsd: 1, akashAvailable: true, akashPriceUsd: 999 }), "akash");
  assert.equal(selectCloudTarget({ nosanaAvailable: true, nosanaPriceUsd: 999, akashAvailable: false, akashPriceUsd: 1 }), "nosana");
});

test("PROP-306c: both providers unavailable -> 'none'", () => {
  assert.equal(selectCloudTarget({ nosanaAvailable: false, akashAvailable: false }), "none");
});

test("PROP-306d: selectCloudTarget performs zero I/O — synchronous, given already-fetched primitives only", () => {
  const result = selectCloudTarget({ nosanaAvailable: true, nosanaPriceUsd: 1, akashAvailable: true, akashPriceUsd: 2 });
  assert.equal(typeof result, "string");
  assert.ok(!(result instanceof Promise));
});

test("PROP-306e: the AKT-USD price-fetch step fails closed to 0 on a fetch error, never throws", async () => {
  const price = await fetchAktUsdPrice({
    fetchImpl: async () => {
      throw new Error("network down");
    },
  });
  assert.equal(price, 0);
});

test("PROP-306e: the AKT-USD price-fetch step fails closed to 0 on a non-finite parsed response", async () => {
  const price = await fetchAktUsdPrice({ fetchImpl: async () => ({ json: async () => ({ price: "not-a-number" }) }) });
  assert.equal(price, 0);
});

test("PROP-306e: the NOS-USD price-fetch step mirrors the identical fail-closed discipline", async () => {
  const price = await fetchNosUsdPrice({
    fetchImpl: async () => {
      throw new Error("down");
    },
  });
  assert.equal(price, 0);
});

test("REQ-306 EARS: normalized prices from a real, successful fetch are honored by selectCloudTarget end-to-end", async () => {
  const aktUsd = await fetchAktUsdPrice({ fetchImpl: async () => ({ json: async () => ({ price: 0.5 }) }) });
  assert.equal(aktUsd, 0.5);
  assert.equal(selectCloudTarget({ nosanaAvailable: true, nosanaPriceUsd: 0.4, akashAvailable: true, akashPriceUsd: aktUsd }), "nosana");
});
