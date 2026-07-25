// node:test — quote.mjs: pure worth-it evaluator. No I/O anywhere in this file.
import { test } from "node:test";
import assert from "node:assert/strict";
import { evaluateBridgeQuote, DEFAULT_MAX_COST_FRACTION } from "../quote.mjs";

// Real numbers observed 2026-07-25 (see this feature's report): Base gas price ~6,000,000 wei/gas,
// ETH/USD ~$1856.68, approve ~68,000 gas units (measured 56,240 + margin), burn ~220,000 gas units
// (bounded by a real comparable measurement — see bridge.mjs's header).
function realShapedArgs(overrides = {}) {
  return {
    amountUsdc: 10,
    gasUnitsApprove: 68000n,
    gasUnitsBurn: 220000n,
    baseGasPriceWei: 6_000_000,
    ethUsdPrice: 1856.68,
    bridgeFeeBps: 0,
    solanaGasUsd: 0,
    ...overrides,
  };
}

test("evaluateBridgeQuote: real Base-gas-price shape is WORTH IT with a tiny cost fraction", () => {
  const q = evaluateBridgeQuote(realShapedArgs());
  assert.equal(q.worthIt, true);
  assert.ok(q.costUsd < 0.01, `expected costUsd well under 1 cent, got ${q.costUsd}`);
  assert.ok(q.costFraction < 0.001, `expected costFraction << 0.1%, got ${q.costFraction}`);
  assert.ok(q.netReceivedUsdc > 9.99);
});

test("evaluateBridgeQuote: skipping approve (allowance already sufficient) lowers cost further", () => {
  const withApprove = evaluateBridgeQuote(realShapedArgs());
  const withoutApprove = evaluateBridgeQuote(realShapedArgs({ gasUnitsApprove: 0n }));
  assert.ok(withoutApprove.costUsd < withApprove.costUsd);
});

test("evaluateBridgeQuote: fails closed on a missing/non-finite gas price (never treated as zero cost)", () => {
  const q1 = evaluateBridgeQuote(realShapedArgs({ baseGasPriceWei: null }));
  assert.equal(q1.worthIt, false);
  assert.match(q1.reason, /baseGasPriceWei is unavailable/);
  const q2 = evaluateBridgeQuote(realShapedArgs({ baseGasPriceWei: NaN }));
  assert.equal(q2.worthIt, false);
  const q3 = evaluateBridgeQuote(realShapedArgs({ baseGasPriceWei: 0 }));
  assert.equal(q3.worthIt, false);
});

test("evaluateBridgeQuote: fails closed on a missing/non-finite ETH/USD price", () => {
  const q = evaluateBridgeQuote(realShapedArgs({ ethUsdPrice: undefined }));
  assert.equal(q.worthIt, false);
  assert.match(q.reason, /ethUsdPrice is unavailable/);
});

test("evaluateBridgeQuote: bridgeFeeBps genuinely defaults to 0 (CCTP Standard Transfer's real verified rate) when omitted — but an explicitly INVALID value (not simply omitted) still fails closed rather than being silently coerced to free", () => {
  // Omitting the param entirely is a deliberate, documented default (0 bps == CCTP Standard
  // Transfer's real verified fee) — this is NOT the "unfetchable quote" case the spec warns about.
  const omitted = evaluateBridgeQuote({ amountUsdc: 10, gasUnitsApprove: 68000n, gasUnitsBurn: 220000n, baseGasPriceWei: 6_000_000, ethUsdPrice: 1856.68 });
  assert.equal(omitted.worthIt, true);

  // An explicitly invalid fetched value (NaN/negative) — e.g. a fee-quote fetch that returned
  // garbage — must still fail closed, never silently treated as 0/free.
  const invalid = evaluateBridgeQuote(realShapedArgs({ bridgeFeeBps: NaN }));
  assert.equal(invalid.worthIt, false);
  assert.match(invalid.reason, /bridgeFeeBps is unavailable/);
  const negative = evaluateBridgeQuote(realShapedArgs({ bridgeFeeBps: -1 }));
  assert.equal(negative.worthIt, false);
});

test("evaluateBridgeQuote: fails closed on a non-positive gasUnitsBurn (there is always a burn)", () => {
  const q1 = evaluateBridgeQuote(realShapedArgs({ gasUnitsBurn: 0n }));
  assert.equal(q1.worthIt, false);
  const q2 = evaluateBridgeQuote(realShapedArgs({ gasUnitsBurn: 100 })); // not a bigint
  assert.equal(q2.worthIt, false);
  assert.match(q2.reason, /gasUnitsBurn must be a positive bigint/);
});

test("evaluateBridgeQuote: fails closed on a non-positive amountUsdc", () => {
  assert.equal(evaluateBridgeQuote(realShapedArgs({ amountUsdc: 0 })).worthIt, false);
  assert.equal(evaluateBridgeQuote(realShapedArgs({ amountUsdc: -5 })).worthIt, false);
});

test("evaluateBridgeQuote: a large fixed-fee route (aggregator shape, bridgeFeeBps modeling a flat cut) is refused once cost exceeds the threshold", () => {
  // Real observed 2026-07-25: an LI.FI-quoted aggregator route (mayanMCTP) for $10 Base->Solana
  // returned toAmount 8.48 out of 10 in — a ~15% loss, modeled here via a large bridgeFeeBps.
  const q = evaluateBridgeQuote(realShapedArgs({ bridgeFeeBps: 1500 })); // 15%
  assert.equal(q.worthIt, false);
  assert.match(q.reason, /above the .*worth-it threshold/);
});

test("evaluateBridgeQuote: a moderate aggregator fee (~0.4%, real LI.FI/NEAR-Intents shape) still passes the default 5% threshold", () => {
  const q = evaluateBridgeQuote(realShapedArgs({ bridgeFeeBps: 40 })); // 0.4%
  assert.equal(q.worthIt, true);
});

test("evaluateBridgeQuote: cost consuming the entire transfer is refused even under the fraction threshold check", () => {
  const q = evaluateBridgeQuote(realShapedArgs({ amountUsdc: 0.0001, bridgeFeeBps: 0 }));
  assert.equal(q.worthIt, false);
});

test("evaluateBridgeQuote: default worth-it threshold is documented as 5%", () => {
  assert.equal(DEFAULT_MAX_COST_FRACTION, 0.05);
});

test("evaluateBridgeQuote: refuses on a missing/invalid maxCostFraction rather than silently defaulting", () => {
  const q = evaluateBridgeQuote(realShapedArgs({ maxCostFraction: 0 }));
  assert.equal(q.worthIt, false);
  assert.match(q.reason, /maxCostFraction must be a positive finite number/);
});

test("evaluateBridgeQuote: never throws — always returns a fully-populated object", () => {
  const q = evaluateBridgeQuote({});
  assert.equal(typeof q.worthIt, "boolean");
  assert.equal(typeof q.reason, "string");
});
