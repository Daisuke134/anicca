// VCSDD R12 — the dashboard-sync endpoint must NOT serve raw self-reported rankings; it enriches every
// row on-chain (multi-chain, routed per-row by `chain`) before aggregating.
const { test, beforeEach, afterEach } = require("node:test");
const assert = require("node:assert");

let origFetch;
const NOWTS = Math.floor(Date.now() / 1000);

const SAMPLE_ROWS = [
  { id: "0xaaa1", ts: NOWTS, net_worth_usd: 120.5, revenue_mo_usd: 30, burn_day_usd: 0.5, runway_days: 241, status: "alive", host: "akash", model_tier: "frontier" },
  { id: "0xbbb2", ts: NOWTS, net_worth_usd: 50, revenue_mo_usd: 0, burn_day_usd: 0.2, runway_days: 250, status: "alive", host: "do", model_tier: "free" },
  { id: "0xccc3", ts: NOWTS, net_worth_usd: 10, revenue_mo_usd: 0, burn_day_usd: 0, runway_days: 0, status: "dead", host: "do", model_tier: "free" },
];

// deterministic mock reader — every id gets its OWN self-reported figures back as "chain-verified"
// (this test suite is about the wiring/plumbing, not the money math — that's enrich.test.js's job).
function passthroughReader(rows) {
  const byId = Object.fromEntries(rows.map((r) => [String(r.id).toLowerCase(), r]));
  const norm = (a) => String(a).toLowerCase();
  return {
    ethUsdPrice: () => 1,
    usdcBalanceAtomic: (a) => BigInt(Math.round((byId[norm(a)]?.net_worth_usd || 0) * 1e6)),
    nativeBalanceWei: () => 0n,
    externalInflowsUsd: (a) => byId[norm(a)]?.revenue_mo_usd || 0,
  };
}

beforeEach(() => {
  process.env.SUPABASE_URL = "https://test.supabase.co";
  process.env.SUPABASE_SERVICE_ROLE_KEY = "test-key";
  origFetch = global.fetch;
  global.fetch = async (url) => {
    if (typeof url === "string" && url.includes("/rest/v1/instances")) {
      return { ok: true, json: async () => SAMPLE_ROWS };
    }
    return { ok: false, status: 500, json: async () => ({}) };
  };
});
afterEach(() => { global.fetch = origFetch; });

test("GET returns 200 with enriched, chain-verified aggregated data", async () => {
  const { handler } = require("../../dashboard-sync");
  const deps = { readers: { base: passthroughReader(SAMPLE_ROWS) } };
  const res = await handler({ httpMethod: "GET", headers: {} }, {}, deps);
  assert.strictEqual(res.statusCode, 200);

  const body = JSON.parse(res.body);
  assert.strictEqual(body.alive, 2); // dead excluded
  assert.strictEqual(body.total_net_worth_usd, 170.5); // 120.5 + 50 (dead row excluded before enrichment even runs)
  assert.strictEqual(body.earned_mo_usd, 30);
  assert.strictEqual(body.leaderboard[0].id, "0xaaa1");
  assert.strictEqual(body.leaderboard[0].net_worth_src, "chain");
  assert.strictEqual(body.leaderboard[0].earn_src, "chain");
  assert.ok(body.updated_at, "updated_at should be present");
  assert.ok(res.headers["Content-Type"].includes("application/json"));
  assert.ok(res.headers["Cache-Control"]);
});

test("GET returns 200 with self_funded_pct (chain-verified gate)", async () => {
  const { handler } = require("../../dashboard-sync");
  const deps = { readers: { base: passthroughReader(SAMPLE_ROWS) } };
  const res = await handler({ httpMethod: "GET", headers: {} }, {}, deps);
  const body = JSON.parse(res.body);
  // among the 2 LIVE (non-dead) rows: only 0xaaa1 has revenue/30 (1) >= burn (0.5) → 1/2 = 50%
  assert.strictEqual(body.self_funded_pct, 50);
});

test("GET returns 200 with frontier_pct", async () => {
  const { handler } = require("../../dashboard-sync");
  const deps = { readers: { base: passthroughReader(SAMPLE_ROWS) } };
  const res = await handler({ httpMethod: "GET", headers: {} }, {}, deps);
  const body = JSON.parse(res.body);
  // 1 of 2 LIVE rows has model_tier "frontier" → 50%
  assert.strictEqual(body.frontier_pct, 50);
});

test("a reader failure => net_worth_src/earn_src unverified, row still served (never dropped)", async () => {
  const { handler } = require("../../dashboard-sync");
  const throwingReader = { ethUsdPrice: () => { throw new Error("rpc down"); }, usdcBalanceAtomic: () => { throw new Error("rpc down"); }, nativeBalanceWei: () => 0n, externalInflowsUsd: () => { throw new Error("rpc down"); } };
  const res = await handler({ httpMethod: "GET", headers: {} }, {}, { readers: { base: throwingReader } });
  const body = JSON.parse(res.body);
  assert.strictEqual(body.leaderboard[0].net_worth_src, "unverified");
  assert.strictEqual(body.leaderboard[0].earn_src, "unverified");
  assert.strictEqual(body.total_net_worth_usd, undefined); // never a fake summed total
});

test("a chain:'polygon-proxy' row (e.g. claude-p, signer != funds-holder) stays honestly unverified — NOT a false verified-$0", async () => {
  const { handler } = require("../../dashboard-sync");
  const proxyRow = { id: "0xsigner", ts: NOWTS, chain: "polygon-proxy", net_worth_usd: 0.24, revenue_mo_usd: 0, burn_day_usd: 0, runway_days: 999, status: "alive", host: "claude-p", model_tier: "frontier" };
  global.fetch = async (url) => (typeof url === "string" && url.includes("/rest/v1/instances")) ? { ok: true, json: async () => [proxyRow] } : { ok: false, status: 500 };
  // deliberately give it a WORKING base reader that would happily report a real (but wrong) $0 for
  // "0xsigner" — this proves the row is skipped by chain, not merely because no reader was passed at all.
  const passthrough = { ethUsdPrice: () => 1, usdcBalanceAtomic: () => 0n, nativeBalanceWei: () => 0n, externalInflowsUsd: () => 0 };
  const res = await handler({ httpMethod: "GET", headers: {} }, {}, { readers: { base: passthrough } });
  const body = JSON.parse(res.body);
  assert.strictEqual(body.leaderboard[0].net_worth_src, "unverified");
  assert.strictEqual(body.leaderboard[0].net_worth_usd, 0.24); // self-reported figure preserved, not overwritten with a false $0
});

test("returns 500 when SUPABASE_URL env is missing", async () => {
  delete process.env.SUPABASE_URL;
  delete require.cache[require.resolve("../../dashboard-sync")];
  const { handler } = require("../../dashboard-sync");
  const res = await handler({ httpMethod: "GET", headers: {} });
  assert.strictEqual(res.statusCode, 500);
  process.env.SUPABASE_URL = "https://test.supabase.co";
});

test("returns 502 when Supabase is unreachable", async () => {
  global.fetch = async () => ({ ok: false, status: 503 });
  delete require.cache[require.resolve("../../dashboard-sync")];
  const { handler } = require("../../dashboard-sync");
  const res = await handler({ httpMethod: "GET", headers: {} });
  assert.strictEqual(res.statusCode, 502);
});

test("handles empty instances table without crashing", async () => {
  global.fetch = async () => ({ ok: true, json: async () => [] });
  delete require.cache[require.resolve("../../dashboard-sync")];
  const { handler } = require("../../dashboard-sync");
  const res = await handler({ httpMethod: "GET", headers: {} }, {}, { readers: { base: passthroughReader([]) } });
  assert.strictEqual(res.statusCode, 200);
  const body = JSON.parse(res.body);
  assert.strictEqual(body.alive, 0);
  assert.strictEqual(body.total_net_worth_usd, 0);
  assert.strictEqual(body.self_funded_pct, 0);
});
