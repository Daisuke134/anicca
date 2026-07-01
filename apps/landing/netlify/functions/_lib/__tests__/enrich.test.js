// VCSDD Phase 2a RED — agents-at-arms-leaderboard.
// Proves the no-fake core: on-chain enrichment (R3), earnings-rank (R2), totals-exclude (R4).
// FAILS until GREEN implements ../enrich.js and ../leaderboard-constants.js and extends aggregate.
const { test } = require("node:test");
const assert = require("node:assert");

const NOWTS = Math.floor(Date.now() / 1000);
const { enrichOnChain } = require("../enrich");
const { excludeSet, SEED_ADDRESSES, OUR_INSTANCE_IDS } = require("../leaderboard-constants");
const { aggregate } = require("../telemetry-aggregate");

// ---- deterministic mock reader (no real chain I/O) ----
// _bal: addr -> { usdcAtomic: bigint, wei: bigint }
// _inflows: addr -> [{ from, usd, ts }]
function mockReader({ bal = {}, inflows = {}, price = 3000, throwOn = null } = {}) {
  const norm = (a) => a.toLowerCase();
  return {
    ethUsdPrice: () => price,
    usdcBalanceAtomic: (a) => {
      if (throwOn === "usdc") throw new Error("rpc down");
      return (bal[norm(a)]?.usdcAtomic) ?? 0n;
    },
    nativeBalanceWei: (a) => {
      if (throwOn === "native") throw new Error("rpc down");
      return (bal[norm(a)]?.wei) ?? 0n;
    },
    externalInflowsUsd: (a, sinceTs, exSet) => {
      if (throwOn === "inflows") throw new Error("rpc down");
      const list = inflows[norm(a)] ?? [];
      return list
        .filter((x) => x.ts >= sinceTs && !exSet.has(norm(x.from)))
        .reduce((s, x) => s + x.usd, 0);
    },
  };
}

const baseRow = (over) => ({
  id: "0xaaa", ts: Math.floor(Date.now() / 1000), host: "akash", geo: "US",
  model_live: "glm-4.7", model_tier: "free", net_worth_usd: 0, revenue_mo_usd: 0,
  burn_day_usd: 0.1, runway_days: 10, status: "alive", ...over,
});

test("R3: net_worth_usd is dimensioned = usdc/1e6 + eth*price, src=chain", () => {
  const row = baseRow({ id: "0xaaa", net_worth_usd: 999999 /* self-asserted lie */ });
  const reader = mockReader({ bal: { "0xaaa": { usdcAtomic: 1_000000n, wei: 1_000000000000000000n } }, price: 3000 });
  const [e] = enrichOnChain([row], reader);
  assert.strictEqual(e.net_worth_usd, 1 + 3000); // 1 USDC + 1 ETH*3000, NOT the self-asserted 999999
  assert.strictEqual(e.net_worth_src, "chain");
});

test("R3 anti-buy: inflows from own id or a SEED address do NOT count as revenue", () => {
  const seed = SEED_ADDRESSES[0] || "0xseed";
  const row = baseRow({ id: "0xaaa" });
  const reader = mockReader({
    inflows: { "0xaaa": [
      { from: "0xaaa", usd: 5000, ts: NOWTS },      // self-transfer — excluded
      { from: seed, usd: 5000, ts: NOWTS },          // seed money — excluded
      { from: "0xcustomer", usd: 7, ts: NOWTS },     // real external earning — counts
    ] },
  });
  const [e] = enrichOnChain([row], reader);
  assert.strictEqual(e.revenue_mo_usd, 7);       // only the external $7, not 10007
  assert.strictEqual(e.earn_src, "chain");
});

test("R3 anti-buy end-to-end: a self/seed-funded whale does NOT out-rank a real earner", () => {
  const rows = [
    baseRow({ id: "0xwhale" }),   // only self/seed inflows
    baseRow({ id: "0xearner" }),  // real external inflow
  ];
  const reader = mockReader({
    inflows: {
      "0xwhale": [{ from: "0xwhale", usd: 1_000_000, ts: NOWTS }],
      "0xearner": [{ from: "0xcustomer", usd: 50, ts: NOWTS }],
    },
  });
  const enriched = enrichOnChain(rows, reader);
  const d = aggregate(enriched);
  assert.strictEqual(d.leaderboard[0].id, "0xearner"); // earner #1, not the whale
});

test("R3: reader failure => src=unverified and figure flagged (never trusted)", () => {
  const row = baseRow({ id: "0xaaa", net_worth_usd: 42 });
  const reader = mockReader({ throwOn: "usdc" });
  const [e] = enrichOnChain([row], reader);
  assert.strictEqual(e.net_worth_src, "unverified");
});

test("R4: totals sum only chain-verified; all-unverified => undefined not 0", () => {
  const rows = [baseRow({ id: "0xaaa" }), baseRow({ id: "0xbbb" })];
  const reader = mockReader({ throwOn: "usdc" }); // both net worth unverified
  const enriched = enrichOnChain(rows, reader);
  const d = aggregate(enriched);
  assert.strictEqual(d.total_net_worth_usd, undefined); // NOT 0
});

test("excludeSet(row) contains the row's own id + seed + our ids (per-row)", () => {
  const s = excludeSet({ id: "0xMe" });
  assert.ok(s.has("0xme"));
  for (const seed of SEED_ADDRESSES) assert.ok(s.has(seed.toLowerCase()));
  for (const our of OUR_INSTANCE_IDS) assert.ok(s.has(our.toLowerCase()));
});
