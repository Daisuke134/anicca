const { test, beforeEach, afterEach } = require("node:test");
const assert = require("node:assert");

// We import the handler after setting env vars
let origFetch;

const SAMPLE_ROWS = [
  {
    id: "0xaaa1",
    net_worth_usd: 120.5,
    revenue_mo_usd: 30,
    burn_day_usd: 0.5,
    runway_days: 241,
    status: "alive",
    host: "akash",
    model_tier: "frontier",
    wallet_addr: "0xaaa1000000000000000000000000000000000001",
  },
  {
    id: "0xbbb2",
    net_worth_usd: 50,
    revenue_mo_usd: 0,
    burn_day_usd: 0.2,
    runway_days: 250,
    status: "alive",
    host: "do",
    model_tier: "free",
    wallet_addr: null,
  },
  {
    id: "0xccc3",
    net_worth_usd: 10,
    revenue_mo_usd: 0,
    burn_day_usd: 0,
    runway_days: 0,
    status: "dead",
    host: "do",
    model_tier: "free",
    wallet_addr: null,
  },
];

beforeEach(() => {
  process.env.SUPABASE_URL = "https://test.supabase.co";
  process.env.SUPABASE_SERVICE_ROLE_KEY = "test-key";
  origFetch = global.fetch;
  // Mock Supabase GET request returning sample rows
  global.fetch = async (url) => {
    if (typeof url === "string" && url.includes("/rest/v1/instances")) {
      return { ok: true, json: async () => SAMPLE_ROWS };
    }
    return { ok: false, status: 500, json: async () => ({}) };
  };
});

afterEach(() => {
  global.fetch = origFetch;
});

test("GET returns 200 with aggregated data", async () => {
  const { handler } = require("../../dashboard-sync");
  const res = await handler({ httpMethod: "GET", headers: {} });
  assert.strictEqual(res.statusCode, 200);

  const body = JSON.parse(res.body);
  // 2 alive (dead excluded from alive count)
  assert.strictEqual(body.alive, 2);
  // total_net_worth = 120.5 + 50 + 10 = 180.5
  assert.strictEqual(body.total_net_worth_usd, 180.5);
  // earned_mo = 30 + 0 + 0 = 30
  assert.strictEqual(body.earned_mo_usd, 30);
  // leaderboard sorted by net_worth desc: 0xaaa1 first
  assert.strictEqual(body.leaderboard[0].id, "0xaaa1");
  assert.ok(body.updated_at, "updated_at should be present");
  // Content-Type header
  assert.ok(res.headers["Content-Type"].includes("application/json"));
  // Cache-Control present
  assert.ok(res.headers["Cache-Control"]);
});

test("GET returns 200 with self_funded_pct", async () => {
  const { handler } = require("../../dashboard-sync");
  const res = await handler({ httpMethod: "GET", headers: {} });
  const body = JSON.parse(res.body);
  // Only 0xaaa1 has revenue/30 (1) >= burn (0.5) and is not dead → 1/3 = 33%
  assert.strictEqual(body.self_funded_pct, 33);
});

test("GET returns 200 with frontier_pct", async () => {
  const { handler } = require("../../dashboard-sync");
  const res = await handler({ httpMethod: "GET", headers: {} });
  const body = JSON.parse(res.body);
  // 1 of 3 rows has model_tier "frontier" → 33%
  assert.strictEqual(body.frontier_pct, 33);
});

test("returns 500 when SUPABASE_URL env is missing", async () => {
  delete process.env.SUPABASE_URL;
  // Force re-require by deleting cached module
  delete require.cache[require.resolve("../../dashboard-sync")];
  const { handler } = require("../../dashboard-sync");
  const res = await handler({ httpMethod: "GET", headers: {} });
  assert.strictEqual(res.statusCode, 500);
  // Restore
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
  const res = await handler({ httpMethod: "GET", headers: {} });
  assert.strictEqual(res.statusCode, 200);
  const body = JSON.parse(res.body);
  assert.strictEqual(body.alive, 0);
  assert.strictEqual(body.total_net_worth_usd, 0);
  assert.strictEqual(body.self_funded_pct, 0);
});
