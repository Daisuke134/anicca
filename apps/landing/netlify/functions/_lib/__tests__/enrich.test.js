// VCSDD — agents-at-arms-leaderboard, extended 2026-07-05 for multi-chain (Solana + Polygon).
// Proves the no-fake core: on-chain enrichment (R3), earnings-rank (R2), totals-exclude (R4), and that
// enrichOnChain correctly ROUTES each row to its own chain's reader (never cross-contaminating chains).
const { test } = require("node:test");
const assert = require("node:assert");

const NOWTS = Math.floor(Date.now() / 1000);
const { enrichOnChain } = require("../enrich");
const { excludeSet, SEED_ADDRESSES, OUR_INSTANCE_IDS } = require("../leaderboard-constants");
const { aggregate } = require("../telemetry-aggregate");

// ---- deterministic mock reader (no real chain I/O) ----
// _bal: addr -> { usdcAtomic: bigint, wei: bigint }
// _inflows: addr -> [{ from, usd, ts }]
function mockReader({ bal = {}, inflows = {}, price = 3000, throwOn = null, decimals } = {}) {
  const norm = (a) => a.toLowerCase();
  const r = {
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
  if (decimals !== undefined) r.nativeDecimals = () => decimals;
  return r;
}

const baseRow = (over) => ({
  id: "0xaaa", ts: Math.floor(Date.now() / 1000), host: "akash", geo: "US",
  model_live: "glm-4.7", model_tier: "free", net_worth_usd: 0, revenue_mo_usd: 0,
  burn_day_usd: 0.1, runway_days: 10, status: "alive", ...over,
});

test("R3: net_worth_usd is dimensioned = usdc/1e6 + eth*price, src=chain", () => {
  const row = baseRow({ id: "0xaaa", net_worth_usd: 999999 /* self-asserted lie */ });
  const reader = mockReader({ bal: { "0xaaa": { usdcAtomic: 1_000000n, wei: 1_000000000000000000n } }, price: 3000 });
  const [e] = enrichOnChain([row], { base: reader });
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
  const [e] = enrichOnChain([row], { base: reader });
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
  const enriched = enrichOnChain(rows, { base: reader });
  const d = aggregate(enriched);
  assert.strictEqual(d.leaderboard[0].id, "0xearner"); // earner #1, not the whale
});

test("R3: reader failure => src=unverified and figure flagged (never trusted)", () => {
  const row = baseRow({ id: "0xaaa", net_worth_usd: 42 });
  const reader = mockReader({ throwOn: "usdc" });
  const [e] = enrichOnChain([row], { base: reader });
  assert.strictEqual(e.net_worth_src, "unverified");
});

test("R4: totals sum only chain-verified; all-unverified => undefined not 0", () => {
  const rows = [baseRow({ id: "0xaaa" }), baseRow({ id: "0xbbb" })];
  const reader = mockReader({ throwOn: "usdc" }); // both net worth unverified
  const enriched = enrichOnChain(rows, { base: reader });
  const d = aggregate(enriched);
  assert.strictEqual(d.total_net_worth_usd, undefined); // NOT 0
});

test("excludeSet(row) contains the row's own id + seed + our ids (per-row)", () => {
  const s = excludeSet({ id: "0xMe" });
  assert.ok(s.has("0xme"));
  for (const seed of SEED_ADDRESSES) assert.ok(s.has(seed.toLowerCase()));
  for (const our of OUR_INSTANCE_IDS) assert.ok(s.has(our.toLowerCase()));
});

test("edge-008: non-finite ethUsdPrice => net_worth_src unverified (never NaN trusted)", () => {
  const row = baseRow({ id: "0xaaa" });
  const reader = mockReader({ bal: { "0xaaa": { usdcAtomic: 1_000000n, wei: 1_000000000000000000n } }, price: NaN });
  const [e] = enrichOnChain([row], { base: reader });
  assert.strictEqual(e.net_worth_src, "unverified");
});

test("edge-007: revenue_today is clamped <= revenue_mo even if reader is inconsistent", () => {
  const row = baseRow({ id: "0xaaa" });
  let n = 0;
  const reader = {
    ethUsdPrice: () => 3000,
    usdcBalanceAtomic: () => 0n,
    nativeBalanceWei: () => 0n,
    externalInflowsUsd: () => (n++ === 0 ? 5 : 9),
  };
  const [e] = enrichOnChain([row], { base: reader });
  assert.ok(e.revenue_today_usd <= e.revenue_mo_usd, "today must be clamped to <= mo");
  assert.strictEqual(e.revenue_mo_usd, 5);
  assert.strictEqual(e.revenue_today_usd, 5);
});

test("IMPL2-001: a transfer from the REAL founder/treasury wallet is excluded (seed can't buy rank)", () => {
  const FOUNDER = "0x810f6d61f7606deee2657d3083e150a222bc29c5"; // hard-coded real treasury (not SEED_ADDRESSES[0])
  assert.ok(SEED_ADDRESSES.map((a) => a.toLowerCase()).includes(FOUNDER), "founder must be a configured seed");
  const row = baseRow({ id: "0xagent" });
  const reader = mockReader({
    inflows: { "0xagent": [
      { from: FOUNDER, usd: 1_000_000, ts: NOWTS },  // seed from founder — excluded
      { from: "0xrealcustomer", usd: 12, ts: NOWTS }, // real external — counts
    ] },
  });
  const [e] = enrichOnChain([row], { base: reader });
  assert.strictEqual(e.revenue_mo_usd, 12); // NOT 1,000,012
});

// ---- multi-chain routing (2026-07-05) ----

test("a row with chain:'solana' is routed to readers.solana, never readers.base", () => {
  const row = baseRow({ id: "SoLwAllet1111111111111111111111111111111111", chain: "solana" });
  const baseReader = mockReader({ throwOn: "usdc" }); // would fail if ever called
  const solReader = mockReader({ bal: { "solwallet1111111111111111111111111111111111": { usdcAtomic: 5_000000n, wei: 2_000000000n } }, price: 150, decimals: 9 });
  const [e] = enrichOnChain([row], { base: baseReader, solana: solReader });
  assert.strictEqual(e.net_worth_src, "chain");
  assert.strictEqual(e.net_worth_usd, 5 + 2 * 150); // 5 USDC + 2 SOL * $150 (9-decimal native, not 18)
});

test("a row with chain:'polygon' is routed to readers.polygon", () => {
  const row = baseRow({ id: "0xpoly", chain: "polygon" });
  const polyReader = mockReader({ bal: { "0xpoly": { usdcAtomic: 3_000000n, wei: 0n } }, price: 1 });
  const [e] = enrichOnChain([row], { base: mockReader({ throwOn: "usdc" }), polygon: polyReader });
  assert.strictEqual(e.net_worth_src, "chain");
  assert.strictEqual(e.net_worth_usd, 3);
});

test("a row with no chain field defaults to 'base' (back-compat)", () => {
  const row = baseRow({ id: "0xnochain" });
  delete row.chain;
  const baseReader = mockReader({ bal: { "0xnochain": { usdcAtomic: 9_000000n, wei: 0n } } });
  const [e] = enrichOnChain([row], { base: baseReader });
  assert.strictEqual(e.net_worth_usd, 9);
  assert.strictEqual(e.net_worth_src, "chain");
});

test("missing reader for a row's chain => unverified, never throws", () => {
  const row = baseRow({ id: "0xagent", chain: "polygon" });
  const [e] = enrichOnChain([row], { base: mockReader() }); // no polygon reader provided
  assert.strictEqual(e.net_worth_src, "unverified");
  assert.strictEqual(e.earn_src, "unverified");
});
