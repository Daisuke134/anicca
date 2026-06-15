const { test } = require("node:test");
const assert = require("node:assert");
const { aggregate } = require("../telemetry-aggregate");

const rows = [
  // self-funded: revenue/30 (0.33) >= burn (0.10), alive
  { id: "0x1", net_worth_usd: 100, revenue_mo_usd: 10, burn_day_usd: 0.1, runway_days: 30, status: "alive", host: "akash", model_tier: "frontier" },
  // NOT self-funded: revenue/30 (0.16) < burn (0.50), critical
  { id: "0x2", net_worth_usd: 50, revenue_mo_usd: 5, burn_day_usd: 0.5, runway_days: 2, status: "critical", host: "do", model_tier: "free" },
];

test("computes totals + leaderboard (net worth desc)", () => {
  const d = aggregate(rows);
  assert.strictEqual(d.total_net_worth_usd, 150);
  assert.strictEqual(d.alive, 2);
  assert.strictEqual(d.leaderboard[0].id, "0x1");
});
test("self_funded_pct = % whose monthly revenue covers daily burn AND not dead (NOT a model proxy)", () => {
  assert.strictEqual(aggregate(rows).self_funded_pct, 50); // only 0x1 covers its burn
});
test("frontier_pct is reported separately (frontier is NOT self-funding)", () => {
  assert.strictEqual(aggregate(rows).frontier_pct, 50);
});
test("handles empty rows without div-by-zero", () => {
  const d = aggregate([]);
  assert.strictEqual(d.self_funded_pct, 0);
  assert.strictEqual(d.frontier_pct, 0);
  assert.strictEqual(d.alive, 0);
  assert.strictEqual(d.total_net_worth_usd, 0);
});
