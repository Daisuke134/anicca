// node:test — cost: pure extend-cost math, cross-checked against the real job fixture. No I/O.
import { test } from "node:test";
import assert from "node:assert/strict";
import { estimateExtendCostNos, estimateExtendCostUsd, NOS_DECIMALS } from "../cost.mjs";

test("NOS_DECIMALS is re-exported from acquire-nos.mjs (single source of truth, not redeclared)", () => {
  assert.equal(NOS_DECIMALS, 6);
});

test("estimateExtendCostNos matches the real job fixture's price for its own original duration", () => {
  // Real job FHAjMnM1q3p5c5qCeFRjZLYEo12FUBesFPW8zvG5heAC: price=48 (raw units/sec), timeout=900s.
  const costNos = estimateExtendCostNos({ pricePerSecond: 48, additionalSeconds: 900 });
  assert.ok(Math.abs(costNos - 0.0432) < 1e-9, `expected ~0.0432, got ${costNos}`);
});

test("estimateExtendCostNos scales linearly with additionalSeconds", () => {
  const oneMinute = estimateExtendCostNos({ pricePerSecond: 100, additionalSeconds: 60 });
  const twoMinutes = estimateExtendCostNos({ pricePerSecond: 100, additionalSeconds: 120 });
  assert.equal(twoMinutes, oneMinute * 2);
});

test("estimateExtendCostNos fails closed on a non-positive pricePerSecond — never treats an unknown price as free", () => {
  assert.throws(() => estimateExtendCostNos({ pricePerSecond: 0, additionalSeconds: 60 }), /positive finite number/);
  assert.throws(() => estimateExtendCostNos({ pricePerSecond: -5, additionalSeconds: 60 }), /positive finite number/);
  assert.throws(() => estimateExtendCostNos({ pricePerSecond: NaN, additionalSeconds: 60 }), /positive finite number/);
});

test("estimateExtendCostNos fails closed on a non-positive additionalSeconds", () => {
  assert.throws(() => estimateExtendCostNos({ pricePerSecond: 48, additionalSeconds: 0 }), /positive finite number/);
  assert.throws(() => estimateExtendCostNos({ pricePerSecond: 48, additionalSeconds: -900 }), /positive finite number/);
});

test("estimateExtendCostUsd multiplies costNos by nosUsdPrice", () => {
  assert.equal(estimateExtendCostUsd({ costNos: 0.0432, nosUsdPrice: 0.254 }), 0.0432 * 0.254);
});

test("estimateExtendCostUsd fails closed on a non-positive nosUsdPrice", () => {
  assert.throws(() => estimateExtendCostUsd({ costNos: 0.04, nosUsdPrice: 0 }), /positive finite number/);
  assert.throws(() => estimateExtendCostUsd({ costNos: 0.04, nosUsdPrice: -1 }), /positive finite number/);
});
