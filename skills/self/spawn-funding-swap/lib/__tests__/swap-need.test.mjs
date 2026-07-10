// VCSDD spawn-funding-swap Phase 2a (RED). REQ-001, REQ-006, REQ-011 — computeSwapNeed / usdEquivalentOf
// / capUsd, the pure need-computation and hard-cap chain. Written against lib/pure/swap-need.mjs and
// lib/pure/constants.mjs, which do NOT exist yet — every test below MUST fail at module-load time
// (MODULE_NOT_FOUND) until Phase 2b.
import { test } from "node:test";
import assert from "node:assert/strict";
import fc from "fast-check";
import { computeSwapNeed, usdEquivalentOf, capUsd } from "../pure/swap-need.mjs";
import { SWAP_MAX_USD } from "../pure/constants.mjs";

// PROP-001
test("PROP-001: computeSwapNeed(current, threshold) === 0 for current === threshold (exact boundary, never over-buy)", () => {
  assert.equal(computeSwapNeed(26, 26), 0);
});

test("PROP-001 (property): computeSwapNeed returns 0 for ALL current >= threshold; never negative for current < threshold", () => {
  fc.assert(
    fc.property(fc.double({ min: 0, max: 1_000_000, noNaN: true }), fc.double({ min: 0, max: 1_000_000, noNaN: true }), (current, threshold) => {
      const need = computeSwapNeed(current, threshold);
      assert.ok(need >= 0, "need must never be negative");
      if (current >= threshold) assert.equal(need, 0, "no over-buy at or above threshold");
      else assert.ok(Math.abs(need - (threshold - current)) < 1e-9, "shortfall must equal threshold - current below the boundary");
    }),
    { numRuns: 500 }
  );
});

// PROP-011
test("PROP-011: capUsd(x) === Math.min(x, SWAP_MAX_USD) for finite non-negative x", () => {
  fc.assert(
    fc.property(fc.double({ min: 0, max: 1_000_000, noNaN: true }), (x) => {
      assert.equal(capUsd(x), Math.min(x, SWAP_MAX_USD));
    }),
    { numRuns: 300 }
  );
});

test("PROP-011: capUsd resolves adversarial inputs (NaN, negative) to an explicit fail-closed 0, never an unbounded pass-through", () => {
  assert.equal(capUsd(NaN), 0);
  assert.equal(capUsd(-1), 0);
  assert.equal(capUsd(-1_000_000), 0);
});

test("PROP-011: capUsd(Infinity) caps at SWAP_MAX_USD, never returns Infinity", () => {
  assert.equal(capUsd(Infinity), SWAP_MAX_USD);
});

// PROP-012
test("PROP-012: capUsd output is bit-identical regardless of a hostile process.env.SWAP_MAX_USD / genome-style override", () => {
  const before = capUsd(999_999);
  const originalEnv = { ...process.env };
  try {
    process.env.SWAP_MAX_USD = "999999";
    process.env.SOL_TRADE_MAX_SPEND = "999999";
    process.env.GENOME_SWAP_MAX_USD_OVERRIDE = "999999";
    const after = capUsd(999_999);
    assert.equal(after, before, "capUsd must never read process.env — its cap is a literal constant");
    assert.equal(after, SWAP_MAX_USD, "the enforced cap itself must be unchanged by the hostile env");
  } finally {
    process.env = originalEnv;
  }
});

// PROP-018
test("PROP-018: usdEquivalentOf(needAkt, aktUsdPrice) === needAkt * aktUsdPrice for finite non-negative needAkt and finite positive aktUsdPrice", () => {
  fc.assert(
    fc.property(fc.double({ min: 0, max: 1_000_000, noNaN: true }), fc.double({ min: 1e-9, max: 1_000_000, noNaN: true }), (needAkt, aktUsdPrice) => {
      assert.ok(Math.abs(usdEquivalentOf(needAkt, aktUsdPrice) - needAkt * aktUsdPrice) < 1e-6);
    }),
    { numRuns: 500 }
  );
});

test("PROP-018: usdEquivalentOf throws (fail-closed) for aktUsdPrice <= 0, NaN, or Infinity", () => {
  for (const badPrice of [0, -1, NaN, Infinity]) {
    assert.throws(() => usdEquivalentOf(1.0, badPrice), Error, `expected throw for aktUsdPrice=${badPrice}`);
  }
});

test("PROP-018 (property, adversarial): usdEquivalentOf never returns an unbounded/NaN/negative value for any bad price — always throws instead", () => {
  const badPrices = fc.oneof(fc.constant(0), fc.constant(-1), fc.constant(NaN), fc.constant(Infinity), fc.constant(-Infinity), fc.double({ max: 0, noNaN: true }));
  fc.assert(
    fc.property(fc.double({ min: 0, max: 1_000_000, noNaN: true }), badPrices, (needAkt, aktUsdPrice) => {
      assert.throws(() => usdEquivalentOf(needAkt, aktUsdPrice), Error);
    }),
    { numRuns: 200 }
  );
});
