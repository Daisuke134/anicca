const { test } = require("node:test");
const assert = require("node:assert");
const { decideSpawn } = require("../spawn-gate");

const DAY = 86400 * 1000;
const now = 1781600000000;

test("broke parent never spawns (low_balance first)", () => {
  const d = decideSpawn({ balanceUsdc: 5, children: [], now });
  assert.equal(d.eligible, false);
  assert.equal(d.reason, "low_balance");
});

test("balance gate beats every other condition", () => {
  // even with a recent child AND over cap, low balance is the reported reason (own survival first)
  const children = [{ spawned_ms: now - DAY }, { spawned_ms: now - 2 * DAY }];
  const d = decideSpawn({ balanceUsdc: 0, children, now });
  assert.equal(d.reason, "low_balance");
});

test("rate-limited: a child spawned within 14 days blocks", () => {
  const children = [{ spawned_ms: now - 3 * DAY }];
  const d = decideSpawn({ balanceUsdc: 100, children, now, maxChildren: 5 });
  assert.equal(d.eligible, false);
  assert.equal(d.reason, "rate_limited");
});

test("cap: at maxChildren blocks even if old enough", () => {
  const children = [{ spawned_ms: now - 30 * DAY }];
  const d = decideSpawn({ balanceUsdc: 100, children, now, maxChildren: 1 });
  assert.equal(d.eligible, false);
  assert.equal(d.reason, "max_children");
});

test("eligible: funded, no recent child, under cap", () => {
  const d = decideSpawn({ balanceUsdc: 50, children: [], now });
  assert.equal(d.eligible, true);
  assert.equal(d.reason, "eligible");
});

test("eligible with old child under a higher cap", () => {
  const children = [{ spawned_ms: now - 20 * DAY }];
  const d = decideSpawn({ balanceUsdc: 50, children, now, maxChildren: 3 });
  assert.equal(d.eligible, true);
});

test("default minBalance is 20", () => {
  assert.equal(decideSpawn({ balanceUsdc: 19.99, children: [], now }).eligible, false);
  assert.equal(decideSpawn({ balanceUsdc: 20, children: [], now }).eligible, true);
});
