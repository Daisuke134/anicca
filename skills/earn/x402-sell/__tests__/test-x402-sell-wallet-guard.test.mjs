// test-x402-sell-wallet-guard.test.mjs — Test for missing-wallet guard in x402_sell
import test from "node:test";
import assert from "node:assert/strict";
import { evaluateHalt } from "../../../_shared/lib/earn-guard.mjs";

test("x402_sell slot missing-wallet guard: empty or missing wallet returns missing-wallet halt", () => {
  const lines = [
    { wallet: "0x123", source: "x402_sell", earn_usdc: 10, cost_usdc: 0, net_usdc: 10 }
  ];

  // Test with undefined wallet
  const resUndefined = evaluateHalt(lines, { wallet: undefined, source: "x402_sell" });
  assert.equal(resUndefined.halt, true);
  assert.equal(resUndefined.reason, "missing-wallet");

  // Test with empty string wallet
  const resEmpty = evaluateHalt(lines, { wallet: "", source: "x402_sell" });
  assert.equal(resEmpty.halt, true);
  assert.equal(resEmpty.reason, "missing-wallet");

  // Test with whitespace wallet
  const resSpace = evaluateHalt(lines, { wallet: "   ", source: "x402_sell" });
  assert.equal(resSpace.halt, true);
  assert.equal(resSpace.reason, "missing-wallet");
});

test("x402_sell slot with valid wallet passes earn-guard check when cumulative net is non-negative", () => {
  const lines = [
    { wallet: "0x123", source: "x402_sell", earn_usdc: 10, cost_usdc: 0, net_usdc: 10 }
  ];

  const resValid = evaluateHalt(lines, { wallet: "0x123", source: "x402_sell" });
  assert.equal(resValid.halt, false);
  assert.equal(resValid.reason, null);
});
