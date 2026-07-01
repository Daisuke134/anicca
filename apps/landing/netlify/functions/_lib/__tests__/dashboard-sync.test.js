// VCSDD R12 — the dashboard-sync endpoint must NOT serve raw self-reported rankings.
const { test, beforeEach, afterEach } = require("node:test");
const assert = require("node:assert");
const { handler } = require("../../dashboard-sync");

const NOWTS = Math.floor(Date.now() / 1000);
let origFetch;
beforeEach(() => {
  process.env.SUPABASE_URL = "https://x.supabase.co";
  process.env.SUPABASE_SERVICE_ROLE_KEY = "svc";
  origFetch = global.fetch;
  // Supabase returns RAW rows with self-asserted (lied) money.
  global.fetch = async () => ({
    ok: true,
    json: async () => [
      { id: "0xwhale", ts: NOWTS, host: "h", geo: "US", model_live: "m", model_tier: "free", net_worth_usd: 999999, revenue_mo_usd: 999999, burn_day_usd: 0, runway_days: 1, status: "alive" },
      { id: "0xearner", ts: NOWTS, host: "h", geo: "US", model_live: "m", model_tier: "free", net_worth_usd: 1, revenue_mo_usd: 1, burn_day_usd: 0, runway_days: 1, status: "alive" },
    ],
  });
});
afterEach(() => { global.fetch = origFetch; });

// injected mock reader: whale's inflows are all self-transfers (external 0); earner has a real customer.
function mockReader() {
  const norm = (a) => a.toLowerCase();
  const inflows = {
    "0xwhale": [{ from: "0xwhale", usd: 5_000_000 }], // self → excluded
    "0xearner": [{ from: "0xcustomer", usd: 50 }],    // external → counts
  };
  const bal = { "0xwhale": 0n, "0xearner": 0n };
  return {
    ethUsdPrice: () => 3000,
    usdcBalanceAtomic: (a) => bal[norm(a)] ?? 0n,
    nativeBalanceWei: () => 0n,
    externalInflowsUsd: (a, _s, exSet) => (inflows[norm(a)] ?? []).filter((x) => !exSet.has(norm(x.from))).reduce((s, x) => s + x.usd, 0),
  };
}

test("R12: dashboard-sync serves ENRICHED rankings, not raw self-reported", async () => {
  const res = await handler({}, {}, { reader: mockReader() });
  assert.strictEqual(res.statusCode, 200);
  const body = JSON.parse(res.body);
  // whale's self-asserted 999999 revenue must NOT win — external earnings rank the earner #1
  assert.strictEqual(body.leaderboard[0].id, "0xearner");
  const whale = body.leaderboard.find((x) => x.id === "0xwhale");
  assert.notStrictEqual(whale.revenue_mo_usd, 999999); // enriched (external=0), not the self-report
  assert.strictEqual(whale.revenue_mo_usd, 0);
  assert.strictEqual(whale.earn_src, "chain");
});
