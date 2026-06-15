const { test } = require("node:test");
const assert = require("node:assert");
const { decideSpawn } = require("../spawn-decision");

const DAY = 86400000;
const NOW = 1781450000000; // fixed ms

// Defaults: minBalanceUsdc=20, rateLimitDays=14, maxChildren=1
function base(over = {}) {
  return { balanceUsdc: 25, children: [], nowMs: NOW, ...over };
}

test("eligible when profitable, no recent spawn, under cap", () => {
  const r = decideSpawn(base());
  assert.strictEqual(r.eligible, true);
  assert.strictEqual(r.reason, "ok");
});

test("dormant when balance below threshold", () => {
  const r = decideSpawn(base({ balanceUsdc: 19.99 }));
  assert.strictEqual(r.eligible, false);
  assert.strictEqual(r.reason, "low_balance");
});

test("balance exactly at threshold is eligible (>=)", () => {
  const r = decideSpawn(base({ balanceUsdc: 20 }));
  assert.strictEqual(r.eligible, true);
});

test("rate limited when a child was spawned within the window", () => {
  const recent = { spawned_ms: NOW - 5 * DAY };
  const r = decideSpawn(base({ balanceUsdc: 100, children: [recent] }));
  assert.strictEqual(r.eligible, false);
  assert.strictEqual(r.reason, "rate_limited");
});

test("a child older than the window does not rate-limit, but maxChildren still caps", () => {
  const old = { spawned_ms: NOW - 30 * DAY };
  // one existing child already meets maxChildren=1 cap
  const r = decideSpawn(base({ balanceUsdc: 100, children: [old] }));
  assert.strictEqual(r.eligible, false);
  assert.strictEqual(r.reason, "max_children");
});

test("max_children blocks even when not rate-limited and rich (custom cap)", () => {
  const old1 = { spawned_ms: NOW - 30 * DAY };
  const old2 = { spawned_ms: NOW - 40 * DAY };
  const r = decideSpawn(base({ balanceUsdc: 1000, children: [old1, old2], maxChildren: 2 }));
  assert.strictEqual(r.eligible, false);
  assert.strictEqual(r.reason, "max_children");
});

test("higher cap allows another spawn once outside rate window", () => {
  const old = { spawned_ms: NOW - 30 * DAY };
  const r = decideSpawn(base({ balanceUsdc: 1000, children: [old], maxChildren: 5 }));
  assert.strictEqual(r.eligible, true);
});

test("balance is checked before rate-limit (low balance reason wins)", () => {
  const recent = { spawned_ms: NOW - 1 * DAY };
  const r = decideSpawn(base({ balanceUsdc: 1, children: [recent] }));
  assert.strictEqual(r.reason, "low_balance");
});

test("rejects non-numeric / negative balance", () => {
  assert.strictEqual(decideSpawn(base({ balanceUsdc: NaN })).reason, "low_balance");
  assert.strictEqual(decideSpawn(base({ balanceUsdc: -5 })).reason, "low_balance");
  assert.strictEqual(decideSpawn(base({ balanceUsdc: "20" })).reason, "low_balance");
});

test("children entries without spawned_ms are counted for the cap but never rate-limit", () => {
  // a malformed/legacy row (no timestamp) counts toward the cap so we never exceed maxChildren,
  // and is treated as outside the rate window (cannot prove it is recent).
  const r = decideSpawn(base({ balanceUsdc: 100, children: [{}], maxChildren: 1 }));
  assert.strictEqual(r.eligible, false);
  assert.strictEqual(r.reason, "max_children");
});
