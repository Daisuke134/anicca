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
  // 0x/EVM addresses normalize lowercase; non-0x (solana) addresses are case-sensitive and must
  // NOT be lowercased (Sprint-6 S6.6) — check each with the chain-aware rule, not a blanket .toLowerCase().
  for (const seed of SEED_ADDRESSES) assert.ok(s.has(seed.startsWith("0x") ? seed.toLowerCase() : seed));
  for (const our of OUR_INSTANCE_IDS) assert.ok(s.has(our.startsWith("0x") ? our.toLowerCase() : our));
});

test("edge-008: non-finite ethUsdPrice => net_worth_src unverified (never NaN trusted)", () => {
  const row = baseRow({ id: "0xaaa" });
  const reader = mockReader({ bal: { "0xaaa": { usdcAtomic: 1_000000n, wei: 1_000000000000000000n } }, price: NaN });
  const [e] = enrichOnChain([row], reader);
  assert.strictEqual(e.net_worth_src, "unverified");
});

test("edge-007: revenue_today is clamped <= revenue_mo even if reader is inconsistent", () => {
  const row = baseRow({ id: "0xaaa" });
  // enrich calls externalInflowsUsd for MONTH first, then TODAY. Return mo=5 then today=9
  // (inconsistent, today>mo) — enrich must clamp today to mo. Call-order based = date-independent.
  let n = 0;
  const reader = {
    ethUsdPrice: () => 3000,
    usdcBalanceAtomic: () => 0n,
    nativeBalanceWei: () => 0n,
    externalInflowsUsd: () => (n++ === 0 ? 5 : 9),
  };
  const [e] = enrichOnChain([row], reader);
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
  const [e] = enrichOnChain([row], reader);
  assert.strictEqual(e.revenue_mo_usd, 12); // NOT 1,000,012
});

// Sprint-6 S6.5: enrichOnChain dispatches per-row on chain (default 'base'), a Solana row must
// never be read against the Base reader or vice versa. Single-reader call style (back-compat,
// every test above) must keep working unchanged.
test("S6.5: a mixed batch (1 base row, 1 solana row) enriches each against its OWN reader", () => {
  const baseRow_ = baseRow({ id: "0xaaa" }); // chain absent => base
  const solRow = baseRow({ id: "SoLwaLLetAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA1", chain: "solana" });
  const baseReader = mockReader({ bal: { "0xaaa": { usdcAtomic: 2_000000n, wei: 0n } }, price: 1 });
  const solanaReader = {
    ethUsdPrice: () => 999999, // deliberately absurd — if this leaks into the base row's math, the test catches it
    usdcBalanceAtomic: (a) => (a === "SoLwaLLetAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA1" ? 5_000000n : 0n),
    nativeBalanceWei: () => 0n,
    externalInflowsUsd: () => 0,
  };
  const enriched = enrichOnChain([baseRow_, solRow], { base: baseReader, solana: solanaReader });
  const eBase = enriched.find((r) => r.id === "0xaaa");
  const eSol = enriched.find((r) => r.chain === "solana");
  assert.strictEqual(eBase.net_worth_usd, 2); // 2 USDC * price=1, NOT touched by solana's price=999999
  assert.strictEqual(eSol.net_worth_usd, 5); // 5 USDC-equivalent, read from the solana reader
});

test("S6.5: a solana row with NO solana reader configured => unverified (never silently uses base)", () => {
  const solRow = baseRow({ id: "SoLwaLLetAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA1", chain: "solana" });
  const baseReader = mockReader({});
  const [e] = enrichOnChain([solRow], { base: baseReader }); // no 'solana' key at all
  assert.strictEqual(e.net_worth_src, "unverified");
  assert.strictEqual(e.earn_src, "unverified");
});

test("S6.5: single flat reader (no {base,solana} wrapper) still works for an all-base batch (regression)", () => {
  const row = baseRow({ id: "0xaaa" });
  const reader = mockReader({ bal: { "0xaaa": { usdcAtomic: 3_000000n, wei: 0n } }, price: 1 });
  const [e] = enrichOnChain([row], reader); // exact same call style as every test above
  assert.strictEqual(e.net_worth_usd, 3);
});

// Sprint-6 S6.6: excludeSet must be chain-aware — base58 (Solana) ids are case-sensitive, so
// lowercasing a Solana seed/instance id would make it fail to match the real address ever again.
test("S6.6: excludeSet does NOT lowercase a solana-format row id (case-sensitive base58)", () => {
  const mixedCaseId = "AJ99EemzNHpkdjpMJ9aXfLthvfQYkjSXUjYrQr3853MN";
  const s = excludeSet({ id: mixedCaseId, chain: "solana" });
  assert.ok(s.has(mixedCaseId), "must contain the EXACT case, not a lowercased corruption");
  assert.ok(!s.has(mixedCaseId.toLowerCase()) || mixedCaseId === mixedCaseId.toLowerCase());
});

test("S6.6: excludeSet still lowercases a base/EVM row id (regression, existing behavior)", () => {
  const s = excludeSet({ id: "0xABCDEF0000000000000000000000000000000dead" });
  assert.ok(s.has("0xabcdef0000000000000000000000000000000dead"));
});

test("S6.6: a solana seed/instance address correctly excludes a matching solana-chain inflow", () => {
  const SOLANA_FOUNDER = SEED_ADDRESSES.find((a) => !a.startsWith("0x"));
  assert.ok(SOLANA_FOUNDER, "at least one non-0x (solana) seed address must be configured");
  const row = baseRow({ id: "SoLwaLLetAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA1", chain: "solana" });
  const reader = {
    ethUsdPrice: () => 1, usdcBalanceAtomic: () => 0n, nativeBalanceWei: () => 0n,
    externalInflowsUsd: (a, sinceTs, exSet) => (exSet.has(SOLANA_FOUNDER) ? 0 : 999),
  };
  const [e] = enrichOnChain([row], { solana: reader });
  assert.strictEqual(e.revenue_mo_usd, 0); // the founder-seed inflow was excluded, not counted
});
