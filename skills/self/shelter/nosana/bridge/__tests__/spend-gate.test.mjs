// node:test — bridge/spend-gate.mjs: pure cap + ETH-for-future-gas gate. No I/O anywhere here.
import { test } from "node:test";
import assert from "node:assert/strict";
import { evaluateBridgeGate, DEFAULT_MAX_BRIDGE_USD, DEFAULT_FUTURE_GAS_RESERVE_WEI } from "../spend-gate.mjs";

function realShapedArgs(overrides = {}) {
  return {
    amountUsdc: 10,
    ethBalanceWei: 8_860_000_000_000n, // real measured founder-wallet balance, 0.00000886 ETH
    gasCostWeiEstimate: 1_728_000_000_000n, // (68000+220000) gas * 6,000,000 wei/gas
    nowTs: 1_800_000_000,
    ...overrides,
  };
}

test("evaluateBridgeGate: documented defaults", () => {
  assert.equal(DEFAULT_MAX_BRIDGE_USD, 15);
  assert.equal(DEFAULT_FUTURE_GAS_RESERVE_WEI, 2_000_000_000_000n);
});

test("evaluateBridgeGate: allows a real-shaped $10 bridge within cap and leaving ETH for a future tx", () => {
  const gate = evaluateBridgeGate(realShapedArgs());
  assert.equal(gate.allowed, true);
});

test("evaluateBridgeGate: refuses an amount over the explicit per-bridge cap", () => {
  const gate = evaluateBridgeGate(realShapedArgs({ amountUsdc: 20 }));
  assert.equal(gate.allowed, false);
  assert.match(gate.reason, /exceeds per-job cap/); // reused checkSpendCaps wording, see file header
});

test("evaluateBridgeGate: refuses when daily cap would be exceeded (reused checkSpendCaps semantics)", () => {
  const history = [{ ts: 1_800_000_000 - 100, amountUsd: 8, status: "sent", txHash: "0xabc" }];
  const gate = evaluateBridgeGate(realShapedArgs({ config: { dailyUsdCap: 12 }, history }));
  assert.equal(gate.allowed, false);
  assert.match(gate.reason, /daily cap/);
});

test("evaluateBridgeGate: refuses when gas cost exceeds the ETH balance entirely (cannot even afford it)", () => {
  const gate = evaluateBridgeGate(realShapedArgs({ ethBalanceWei: 1_000n, gasCostWeiEstimate: 1_728_000_000_000n }));
  assert.equal(gate.allowed, false);
  assert.match(gate.reason, /cannot even afford this bridge/);
});

test("evaluateBridgeGate: refuses when the bridge would leave the wallet below the future-gas reserve", () => {
  // Balance just barely covers this tx's gas but leaves nothing for a future one.
  const ethBalanceWei = 1_728_000_000_000n + 500_000_000_000n; // reserve default is 2e12
  const gate = evaluateBridgeGate(realShapedArgs({ ethBalanceWei }));
  assert.equal(gate.allowed, false);
  assert.match(gate.reason, /reserved for a future transaction/);
});

test("evaluateBridgeGate: fails closed on a missing/non-bigint ethBalanceWei", () => {
  const g1 = evaluateBridgeGate(realShapedArgs({ ethBalanceWei: undefined }));
  assert.equal(g1.allowed, false);
  assert.match(g1.reason, /ethBalanceWei is unavailable/);
  const g2 = evaluateBridgeGate(realShapedArgs({ ethBalanceWei: 123 })); // number, not bigint
  assert.equal(g2.allowed, false);
});

test("evaluateBridgeGate: fails closed on a missing/non-positive gasCostWeiEstimate (never free)", () => {
  const g1 = evaluateBridgeGate(realShapedArgs({ gasCostWeiEstimate: undefined }));
  assert.equal(g1.allowed, false);
  assert.match(g1.reason, /gasCostWeiEstimate is unavailable/);
  const g2 = evaluateBridgeGate(realShapedArgs({ gasCostWeiEstimate: 0n }));
  assert.equal(g2.allowed, false);
});

test("evaluateBridgeGate: fails closed on a non-positive amountUsdc", () => {
  assert.equal(evaluateBridgeGate(realShapedArgs({ amountUsdc: 0 })).allowed, false);
  assert.equal(evaluateBridgeGate(realShapedArgs({ amountUsdc: -1 })).allowed, false);
});

test("evaluateBridgeGate: fails closed on a missing/non-finite nowTs", () => {
  const gate = evaluateBridgeGate(realShapedArgs({ nowTs: undefined }));
  assert.equal(gate.allowed, false);
  assert.match(gate.reason, /nowTs must be a finite number/);
});
