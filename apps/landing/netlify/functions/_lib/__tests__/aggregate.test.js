const { test } = require("node:test");
const assert = require("node:assert");
const { aggregate } = require("../telemetry-aggregate");

// aggregate operates on ENRICHED rows (post enrichOnChain): money carries *_src provenance.
const rows = [
  // chain-verified, self-funded: revenue/30 (0.33) >= burn (0.10), alive
  { id: "0x1", net_worth_usd: 100, revenue_mo_usd: 10, burn_day_usd: 0.1, runway_days: 30, status: "alive", host: "akash", model_tier: "frontier", net_worth_src: "chain", earn_src: "chain" },
  // chain-verified, NOT self-funded: revenue/30 (0.16) < burn (0.50), critical
  { id: "0x2", net_worth_usd: 50, revenue_mo_usd: 5, burn_day_usd: 0.5, runway_days: 2, status: "critical", host: "do", model_tier: "free", net_worth_src: "chain", earn_src: "chain" },
];

test("R1/R4: totals (chain only) + leaderboard ranked by verified earnings desc", () => {
  const d = aggregate(rows);
  assert.strictEqual(d.total_net_worth_usd, 150);
  assert.strictEqual(d.earned_mo_usd, 15);
  assert.strictEqual(d.alive, 2);
  assert.strictEqual(d.leaderboard[0].id, "0x1"); // revenue 10 > 5
});
test("self_funded_pct counts only CHAIN-verified rows that cover burn", () => {
  assert.strictEqual(aggregate(rows).self_funded_pct, 50);
});
test("frontier_pct reported separately", () => {
  assert.strictEqual(aggregate(rows).frontier_pct, 50);
});
test("empty rows → totals 0, pcts 0, no div-by-zero", () => {
  const d = aggregate([]);
  assert.strictEqual(d.total_net_worth_usd, 0);
  assert.strictEqual(d.self_funded_pct, 0);
  assert.strictEqual(d.frontier_pct, 0);
  assert.strictEqual(d.alive, 0);
});

// ---- IMPL-FIND fixes: verified-only totals, self-funded gate, R2 ordering, R5 stale ----

test("R4: rows with absent OR unverified src are NOT summed (no self-reported money)", () => {
  const raw = [{ id: "0xr", net_worth_usd: 999, revenue_mo_usd: 999, burn_day_usd: 0.1, runway_days: 1, status: "alive", model_tier: "free" }]; // no *_src
  assert.strictEqual(aggregate(raw).total_net_worth_usd, undefined);
  assert.strictEqual(aggregate(raw).earned_mo_usd, undefined);
  const unv = [{ ...raw[0], net_worth_src: "unverified", earn_src: "unverified" }];
  assert.strictEqual(aggregate(unv).total_net_worth_usd, undefined);
});
test("IMPL-002: an unverified-earnings row is NOT counted as self-funded", () => {
  const unv = [{ id: "0xu", net_worth_usd: 0, revenue_mo_usd: 1000, burn_day_usd: 0.1, runway_days: 1, status: "alive", model_tier: "free", earn_src: "unverified", net_worth_src: "unverified" }];
  assert.strictEqual(aggregate(unv).self_funded_pct, 0); // huge self-reported revenue ignored
});
test("R2: verified earner out-ranks an unverified whale regardless of numbers", () => {
  const mixed = [
    { id: "0xwhale", net_worth_usd: 9e9, revenue_mo_usd: 9e9, burn_day_usd: 0, runway_days: 1, status: "alive", model_tier: "free", earn_src: "unverified", net_worth_src: "unverified" },
    { id: "0xearner", net_worth_usd: 1, revenue_mo_usd: 5, burn_day_usd: 0, runway_days: 1, status: "alive", model_tier: "free", earn_src: "chain", net_worth_src: "chain" },
  ];
  assert.strictEqual(aggregate(mixed).leaderboard[0].id, "0xearner");
});
test("R2: net_worth tiebreak when revenues equal and both chain", () => {
  const tie = [
    { id: "0xlow", net_worth_usd: 10, revenue_mo_usd: 7, burn_day_usd: 0, runway_days: 1, status: "alive", model_tier: "free", earn_src: "chain", net_worth_src: "chain" },
    { id: "0xhigh", net_worth_usd: 20, revenue_mo_usd: 7, burn_day_usd: 0, runway_days: 1, status: "alive", model_tier: "free", earn_src: "chain", net_worth_src: "chain" },
  ];
  assert.strictEqual(aggregate(tie).leaderboard[0].id, "0xhigh");
});
test("R5: stale derives from injected nowMs (pure/testable); status not mutated", () => {
  const t = 1_000_000; // seconds
  const fresh = [{ id: "0xa", ts: t, net_worth_usd: 1, revenue_mo_usd: 1, burn_day_usd: 0, runway_days: 1, status: "dead", model_tier: "free", earn_src: "chain", net_worth_src: "chain" }];
  const dFresh = aggregate(fresh, t * 1000 + 60_000); // 60s later
  assert.strictEqual(dFresh.leaderboard[0].stale, false);
  assert.strictEqual(dFresh.leaderboard[0].status, "dead"); // still visible, not mutated
  const dStale = aggregate(fresh, (t + 601) * 1000); // 601s later
  assert.strictEqual(dStale.leaderboard[0].stale, true);
});
