// VCSDD spawn-funding-swap Phase 2a (RED). REQ-012 — the single toBaseUnits/fromBaseUnits base-unit
// conversion choke point. Written against lib/pure/base-units.mjs and lib/pure/constants.mjs, which do
// NOT exist yet — every test below MUST fail at module-load time (MODULE_NOT_FOUND) until Phase 2b.
import { test } from "node:test";
import assert from "node:assert/strict";
import fc from "fast-check";
import { toBaseUnits, fromBaseUnits } from "../pure/base-units.mjs";
import { USDC_DECIMALS_BASE, AKT_DECIMALS, SWAP_MAX_USD } from "../pure/constants.mjs";

// PROP-022(a)
test("PROP-022(a): toBaseUnits(15.0, 6) === 15000000n (fixed fixture)", () => {
  assert.equal(toBaseUnits(15.0, 6), 15000000n);
});

// PROP-022(b)
test("PROP-022(b): toBaseUnits floors (never rounds up) — 15.0000009 -> 15000000n, not 15000001n (a naive Math.round implementation MUST fail this)", () => {
  assert.equal(toBaseUnits(15.0000009, 6), 15000000n);
});

// PROP-022(c)
test("PROP-022(c): toBaseUnits(SWAP_MAX_USD, USDC_DECIMALS_BASE) is the exact upper-bound bigint PROP-019 asserts against", () => {
  const result = toBaseUnits(SWAP_MAX_USD, USDC_DECIMALS_BASE);
  assert.equal(typeof result, "bigint");
  assert.equal(result, BigInt(Math.floor(SWAP_MAX_USD * 10 ** USDC_DECIMALS_BASE)));
});

// PROP-022(e)
test("PROP-022(e): wrong-decimals fixture — toBaseUnits(15.0, 0) and toBaseUnits(15.0, 18) both FAIL exact equality against the correctly-scaled 15000000n expectation (10^6x-class unit-error detector)", () => {
  assert.notEqual(toBaseUnits(15.0, 0), 15000000n);
  assert.notEqual(toBaseUnits(15.0, 18), 15000000n);
});

// PROP-022(d)
test("PROP-022(d): adversarial amountFloat (NaN/negative/Infinity) throws — fail closed, never coerces to 0n or silently truncates", () => {
  for (const bad of [NaN, -1, -0.0001, Infinity, -Infinity]) {
    assert.throws(() => toBaseUnits(bad, USDC_DECIMALS_BASE), Error, `expected throw for amountFloat=${bad}`);
  }
});

test("PROP-022(d): missing/non-integer/negative decimals throws — no implicit default is ever used", () => {
  assert.throws(() => toBaseUnits(15.0, undefined), Error);
  assert.throws(() => toBaseUnits(15.0, 6.5), Error);
  assert.throws(() => toBaseUnits(15.0, -1), Error);
});

test("PROP-022(d): Number.MAX_SAFE_INTEGER overflow guard throws instead of silently mis-scaling", () => {
  // amountFloat whose intermediate amountFloat * 10^decimals comfortably exceeds MAX_SAFE_INTEGER.
  const overflowing = Number.MAX_SAFE_INTEGER / 10 ** USDC_DECIMALS_BASE + 1_000_000;
  assert.throws(() => toBaseUnits(overflowing, USDC_DECIMALS_BASE), Error);
});

// PROP-022 (property tier)
test("PROP-022 (property): toBaseUnits floors — never rounds up — for arbitrary non-negative amounts with excess sub-base-unit precision", () => {
  fc.assert(
    fc.property(fc.integer({ min: 0, max: 10_000_000 }), fc.integer({ min: 0, max: 999 }), (wholeMicros, extraSubMicroPrecision) => {
      const decimals = 6;
      // amount already has decimals-precision (wholeMicros / 10^6) plus EXTRA sub-micro precision beyond
      // that (extraSubMicroPrecision / 10^9, bounded to [0, 999] so extraSubMicroPrecision/10^9 always
      // stays STRICTLY below one whole micro-unit [1e-6] and can therefore never carry into wholeMicros'
      // integer portion by construction — extraSubMicroPrecision up to 999_999 previously let this extra
      // term reach ~0.001, up to 1000x a whole micro-unit, which would correctly push floor(amount*1e6)
      // past wholeMicros for large draws; that was a test-fixture defect, not an impl defect, since no
      // correct floor-based toBaseUnits could satisfy `result === wholeMicros` against such an input), so
      // a naive round-based implementation would sometimes bump the integer up by 1 relative to the
      // correct floor.
      const amount = wholeMicros / 10 ** decimals + extraSubMicroPrecision / 10 ** 9;
      const result = toBaseUnits(amount, decimals);
      assert.equal(result, BigInt(wholeMicros), "must floor to the whole-micro-unit portion only, never round up into the extra precision");
    }),
    { numRuns: 300 }
  );
});

// PROP-023
test("PROP-023: fromBaseUnits(1850000n, 6) === 1.85 (fixed fixture feeding computeSwapNeed's `current` input)", () => {
  assert.equal(fromBaseUnits(1850000n, 6), 1.85);
});

test("PROP-023: fromBaseUnits throws on negative bigint input (impossible on-chain balance) rather than returning a negative float", () => {
  assert.throws(() => fromBaseUnits(-1n, 6), Error);
});

test("PROP-023: fromBaseUnits throws on missing/non-integer/negative decimals", () => {
  assert.throws(() => fromBaseUnits(100n, undefined), Error);
  assert.throws(() => fromBaseUnits(100n, 1.5), Error);
  assert.throws(() => fromBaseUnits(100n, -2), Error);
});

// PROP-022/PROP-023 round-trip (property tier)
test("PROP-022/PROP-023 (property): fromBaseUnits(toBaseUnits(x, decimals), decimals) === x for representative fixture floats with no more than `decimals` fractional digits", () => {
  fc.assert(
    fc.property(fc.integer({ min: 0, max: 1_000_000_000 }), (microUnits) => {
      const decimals = AKT_DECIMALS;
      const x = microUnits / 10 ** decimals;
      const roundTripped = fromBaseUnits(toBaseUnits(x, decimals), decimals);
      assert.ok(Math.abs(roundTripped - x) < 1e-9, `round-trip mismatch: ${roundTripped} !== ${x}`);
    }),
    { numRuns: 300 }
  );
});
