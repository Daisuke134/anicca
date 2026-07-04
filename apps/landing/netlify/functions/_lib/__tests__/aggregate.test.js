const { test } = require("node:test");
const assert = require("node:assert");
const { aggregate } = require("../telemetry-aggregate");

const NOWTS = Math.floor(Date.now() / 1000);

// aggregate operates on ENRICHED rows (post enrichOnChain): money carries *_src provenance.
const rows = [
  // chain-verified, self-funded: revenue/30 (0.33) >= burn (0.10), alive
  { id: "0x1", ts: NOWTS, net_worth_usd: 100, revenue_mo_usd: 10, burn_day_usd: 0.1, runway_days: 30, status: "alive", host: "akash", model_tier: "frontier", net_worth_src: "chain", earn_src: "chain" },
  // chain-verified, NOT self-funded: revenue/30 (0.16) < burn (0.50), critical
  { id: "0x2", ts: NOWTS, net_worth_usd: 50, revenue_mo_usd: 5, burn_day_usd: 0.5, runway_days: 2, status: "critical", host: "do", model_tier: "free", net_worth_src: "chain", earn_src: "chain" },
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
test("a row with no ts (or an ancient ts) is excluded from liveness (FRESH_S)", () => {
  const noTs = [{ id: "0xold", net_worth_usd: 1, revenue_mo_usd: 1, burn_day_usd: 0, runway_days: 1, status: "alive", model_tier: "free", net_worth_src: "chain", earn_src: "chain" }];
  assert.strictEqual(aggregate(noTs).alive, 0);
  const ancient = [{ ...noTs[0], id: "0xancient", ts: NOWTS - 999999 }];
  assert.strictEqual(aggregate(ancient).alive, 0);
});

// ---- IMPL-FIND fixes: verified-only totals, self-funded gate, R2 ordering, R5 stale ----

test("R4: rows with absent OR unverified src are NOT summed (no self-reported money)", () => {
  const raw = [{ id: "0xr", ts: NOWTS, net_worth_usd: 999, revenue_mo_usd: 999, burn_day_usd: 0.1, runway_days: 1, status: "alive", model_tier: "free" }]; // no *_src
  assert.strictEqual(aggregate(raw).total_net_worth_usd, undefined);
  assert.strictEqual(aggregate(raw).earned_mo_usd, undefined);
  const unv = [{ ...raw[0], net_worth_src: "unverified", earn_src: "unverified" }];
  assert.strictEqual(aggregate(unv).total_net_worth_usd, undefined);
});
test("IMPL-002: an unverified-earnings row is NOT counted as self-funded", () => {
  const unv = [{ id: "0xu", ts: NOWTS, net_worth_usd: 0, revenue_mo_usd: 1000, burn_day_usd: 0.1, runway_days: 1, status: "alive", model_tier: "free", earn_src: "unverified", net_worth_src: "unverified" }];
  assert.strictEqual(aggregate(unv).self_funded_pct, 0); // huge self-reported revenue ignored
});
test("R2: verified earner out-ranks an unverified whale regardless of numbers", () => {
  const mixed = [
    { id: "0xwhale", ts: NOWTS, net_worth_usd: 9e9, revenue_mo_usd: 9e9, burn_day_usd: 0, runway_days: 1, status: "alive", model_tier: "free", earn_src: "unverified", net_worth_src: "unverified" },
    { id: "0xearner", ts: NOWTS, net_worth_usd: 1, revenue_mo_usd: 5, burn_day_usd: 0, runway_days: 1, status: "alive", model_tier: "free", earn_src: "chain", net_worth_src: "chain" },
  ];
  assert.strictEqual(aggregate(mixed).leaderboard[0].id, "0xearner");
});
test("R2: net_worth tiebreak when revenues equal and both chain", () => {
  const tie = [
    { id: "0xlow", ts: NOWTS, net_worth_usd: 10, revenue_mo_usd: 7, burn_day_usd: 0, runway_days: 1, status: "alive", model_tier: "free", earn_src: "chain", net_worth_src: "chain" },
    { id: "0xhigh", ts: NOWTS, net_worth_usd: 20, revenue_mo_usd: 7, burn_day_usd: 0, runway_days: 1, status: "alive", model_tier: "free", earn_src: "chain", net_worth_src: "chain" },
  ];
  assert.strictEqual(aggregate(tie).leaderboard[0].id, "0xhigh");
});
test("R5: status:dead is excluded entirely (liveness filter), not just flagged", () => {
  const t = Math.floor(Date.now() / 1000) - 100;
  const dead = [{ id: "0xa", ts: t, net_worth_usd: 1, revenue_mo_usd: 1, burn_day_usd: 0, runway_days: 1, status: "dead", model_tier: "free", earn_src: "chain", net_worth_src: "chain" }];
  assert.strictEqual(aggregate(dead, t * 1000 + 60_000).leaderboard.length, 0);
});
test("R5b: display-only stale flag flips at 300s while still within the FRESH_S liveness window", () => {
  const t = Math.floor(Date.now() / 1000);
  const row = [{ id: "0xa", ts: t, net_worth_usd: 1, revenue_mo_usd: 1, burn_day_usd: 0, runway_days: 1, status: "alive", model_tier: "free", earn_src: "chain", net_worth_src: "chain" }];
  const dFresh = aggregate(row, t * 1000 + 60_000); // 60s later
  assert.strictEqual(dFresh.leaderboard[0].stale, false);
  const dStale = aggregate(row, (t + 301) * 1000); // 301s later
  assert.strictEqual(dStale.leaderboard[0].stale, true);
});

test("R7: leaderboard elements carry is_ours (from OUR_INSTANCE_IDS)", () => {
  const rows = [
    { id: "0xa3cdd4ec6b94f01826aaf90a6d5538a2aa8c4c21", ts: NOWTS, net_worth_usd: 1, revenue_mo_usd: 1, burn_day_usd: 0, runway_days: 1, status: "alive", model_tier: "free", earn_src: "chain", net_worth_src: "chain" },
    { id: "0xstranger", ts: NOWTS, net_worth_usd: 1, revenue_mo_usd: 1, burn_day_usd: 0, runway_days: 1, status: "alive", model_tier: "free", earn_src: "chain", net_worth_src: "chain" },
  ];
  const d = aggregate(rows);
  const ours = d.leaderboard.find((x) => x.id.startsWith("0xa3cdd4"));
  const stranger = d.leaderboard.find((x) => x.id === "0xstranger");
  assert.strictEqual(ours.is_ours, true);
  assert.strictEqual(stranger.is_ours, false);
});
