const test = require("node:test");
const assert = require("node:assert/strict");
const { computeSpawnGate } = require("../akt-cost-gate");

test("ready: balance strictly above threshold", () => {
  const g = computeSpawnGate({ balanceAkt: 30, costAkt: 25, bufferAkt: 1 });
  assert.equal(g.ready, true);
  assert.equal(g.reason, "ready");
  assert.equal(g.thresholdAkt, 26);
  assert.equal(g.shortfallAkt, 0);
});

test("ready: balance exactly AT threshold (boundary, inclusive)", () => {
  const g = computeSpawnGate({ balanceAkt: 26, costAkt: 25, bufferAkt: 1 });
  assert.equal(g.ready, true);
  assert.equal(g.shortfallAkt, 0);
});

test("NOT-YET: balance one unit below threshold (boundary)", () => {
  const g = computeSpawnGate({ balanceAkt: 25.999999, costAkt: 25, bufferAkt: 1 });
  assert.equal(g.ready, false);
  assert.equal(g.reason, "insufficient_akt");
  assert.equal(g.thresholdAkt, 26);
  // shortfall must be the exact, correctly-rounded gap — not a placeholder.
  assert.equal(g.shortfallAkt, 0.000001);
});

test("NOT-YET: real spec numbers (2026-07-05) — 1.8575 AKT vs 25+1 threshold", () => {
  const g = computeSpawnGate({ balanceAkt: 1.8575, costAkt: 25, bufferAkt: 1 });
  assert.equal(g.ready, false);
  assert.equal(g.reason, "insufficient_akt");
  assert.equal(g.thresholdAkt, 26);
  assert.equal(g.shortfallAkt, 24.1425);
});

test("NOT-YET: zero balance", () => {
  const g = computeSpawnGate({ balanceAkt: 0, costAkt: 25, bufferAkt: 1 });
  assert.equal(g.ready, false);
  assert.equal(g.shortfallAkt, 26);
});

test("no buffer defaults to 0 (threshold == cost)", () => {
  const g = computeSpawnGate({ balanceAkt: 25, costAkt: 25 });
  assert.equal(g.ready, true);
  assert.equal(g.thresholdAkt, 25);
});

test("invalid: balance is NaN", () => {
  const g = computeSpawnGate({ balanceAkt: NaN, costAkt: 25, bufferAkt: 1 });
  assert.equal(g.ready, false);
  assert.equal(g.reason, "invalid_balance");
  assert.equal(g.thresholdAkt, null);
});

test("invalid: balance is negative", () => {
  const g = computeSpawnGate({ balanceAkt: -5, costAkt: 25, bufferAkt: 1 });
  assert.equal(g.ready, false);
  assert.equal(g.reason, "invalid_balance");
});

test("invalid: balance missing (undefined)", () => {
  const g = computeSpawnGate({ costAkt: 25, bufferAkt: 1 });
  assert.equal(g.ready, false);
  assert.equal(g.reason, "invalid_balance");
});

test("invalid: cost is NaN", () => {
  const g = computeSpawnGate({ balanceAkt: 100, costAkt: NaN, bufferAkt: 1 });
  assert.equal(g.ready, false);
  assert.equal(g.reason, "invalid_cost");
});

test("invalid: cost is negative", () => {
  const g = computeSpawnGate({ balanceAkt: 100, costAkt: -1, bufferAkt: 1 });
  assert.equal(g.ready, false);
  assert.equal(g.reason, "invalid_cost");
});

test("negative bufferAkt is ignored (treated as 0), not subtracted", () => {
  const g = computeSpawnGate({ balanceAkt: 25, costAkt: 25, bufferAkt: -10 });
  assert.equal(g.ready, true);
  assert.equal(g.thresholdAkt, 25);
});

test("large balance still reports ready + zero shortfall", () => {
  const g = computeSpawnGate({ balanceAkt: 1000, costAkt: 25, bufferAkt: 1 });
  assert.equal(g.ready, true);
  assert.equal(g.shortfallAkt, 0);
});
