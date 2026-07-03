// VCSDD sprint-2 RED — S11: render script writes ENRICHED leaderboard into served dashboard.json
// while preserving all existing top-level keys. FAILS until scripts/render-dashboard.mjs exports
// renderDashboard({ rows, reader, existing }) -> nextJson.
const { test } = require("node:test");
const assert = require("node:assert");
const path = require("node:path");
const fs = require("node:fs");

const SCRIPT = path.resolve(__dirname, "../../../../scripts/render-dashboard.mjs");
const NOW_S = Math.floor(Date.now() / 1000);

function baseRow(over) {
  return {
    id: "0xaaaa000000000000000000000000000000000001", ts: NOW_S, host: "akash", geo: "US",
    model_live: "glm-4.7", model_tier: "free", net_worth_usd: 0, revenue_mo_usd: 0,
    burn_day_usd: 0.1, runway_days: 10, status: "alive", ...over,
  };
}

function mockReader({ bal = {}, inflows = {}, price = 3000, throwOn = null } = {}) {
  const n = (a) => a.toLowerCase();
  return {
    ethUsdPrice: () => { if (throwOn === "price") throw new Error("no price"); return price; },
    usdcBalanceAtomic: (a) => { if (throwOn === "usdc") throw new Error("rpc down"); return (bal[n(a)]?.u) ?? 0n; },
    nativeBalanceWei: (a) => { if (throwOn === "native") throw new Error("rpc down"); return (bal[n(a)]?.w) ?? 0n; },
    externalInflowsUsd: (a, sinceTs, ex) => {
      if (throwOn === "inflows") throw new Error("rpc down");
      return (inflows[n(a)] ?? []).filter((x) => x.ts >= sinceTs && !ex.has(n(x.from))).reduce((s, x) => s + x.usd, 0);
    },
  };
}

test("S11: script file exists on disk", () => {
  assert.ok(fs.existsSync(SCRIPT), `render script must exist at ${SCRIPT}`);
});

test("S11.1: preserves existing top-level keys AND adds leaderboard[]", async () => {
  const { renderDashboard } = await import(SCRIPT);
  const existing = { mrr: { total_usd: 42 }, goals: { mrr_target: 1000 }, followers: { total: 100 } };
  const rows = [
    baseRow({ id: "0xa1", net_worth_usd: 999999 /* self-report lie */ }),
    baseRow({ id: "0xa2" }),
  ];
  const reader = mockReader({
    bal: { "0xa1": { u: 5_000000n, w: 0n }, "0xa2": { u: 12_000000n, w: 0n } },
    inflows: {
      "0xa2": [{ from: "0xcustomer", usd: 88, ts: NOW_S }],
    },
  });
  const next = await renderDashboard({ rows, reader, existing });
  assert.deepStrictEqual(next.mrr, existing.mrr);
  assert.deepStrictEqual(next.goals, existing.goals);
  assert.deepStrictEqual(next.followers, existing.followers);
  assert.ok(Array.isArray(next.leaderboard));
  assert.strictEqual(next.leaderboard.length, rows.length);
  // top ranked = the real earner, not the self-report liar
  assert.strictEqual(next.leaderboard[0].id, "0xa2");
});

test("S11.2: broken reader => every element carries earn_src=='unverified' / net_worth_src=='unverified' (no fabricated chain figures)", async () => {
  const { renderDashboard } = await import(SCRIPT);
  const rows = [baseRow({ id: "0xa1" }), baseRow({ id: "0xa2" })];
  const reader = mockReader({ throwOn: "usdc" }); // net worth broken
  // We want BOTH sides broken; also break inflows:
  const brokenBoth = { ...reader, externalInflowsUsd: () => { throw new Error("rpc down"); } };
  const next = await renderDashboard({ rows, reader: brokenBoth, existing: { mrr: {} } });
  for (const e of next.leaderboard) {
    assert.strictEqual(e.net_worth_src, "unverified", `net_worth_src must be unverified for ${e.id}`);
    assert.strictEqual(e.earn_src, "unverified", `earn_src must be unverified for ${e.id}`);
  }
});

test("S11.3: zero raw rows => leaderboard is [] and existing keys still preserved", async () => {
  const { renderDashboard } = await import(SCRIPT);
  const existing = { mrr: { total_usd: 7 }, goals: { mrr_target: 100 } };
  const next = await renderDashboard({ rows: [], reader: mockReader(), existing });
  assert.deepStrictEqual(next.mrr, existing.mrr);
  assert.deepStrictEqual(next.goals, existing.goals);
  assert.ok(Array.isArray(next.leaderboard));
  assert.strictEqual(next.leaderboard.length, 0);
});

test("S11.4: shouldRefuseCliWrite refuses on missing env / non-ok fetch / thrown fetch", async () => {
  const { shouldRefuseCliWrite } = await import(SCRIPT);
  assert.strictEqual(shouldRefuseCliWrite({ env: {} }).refuse, true, "missing url must refuse");
  assert.strictEqual(shouldRefuseCliWrite({ env: { SUPABASE_URL: "x" } }).refuse, true, "missing key must refuse");
  assert.strictEqual(shouldRefuseCliWrite({ env: { SUPABASE_URL: "x", SUPABASE_SERVICE_ROLE_KEY: "y" }, fetchOk: false }).refuse, true, "non-ok fetch must refuse");
  assert.strictEqual(shouldRefuseCliWrite({ env: { SUPABASE_URL: "x", SUPABASE_SERVICE_ROLE_KEY: "y" }, fetchThrew: true }).refuse, true, "thrown fetch must refuse");
  assert.strictEqual(shouldRefuseCliWrite({ env: { SUPABASE_URL: "x", SUPABASE_SERVICE_ROLE_KEY: "y" }, fetchOk: true }).refuse, false, "healthy path must NOT refuse");
});

test("S11.5: pre-migration row shape (all additive columns explicitly null) enriches and aggregates without throw; leaderboard length matches input rows", async () => {
  const { renderDashboard } = await import(SCRIPT);
  const preMigrationRow = {
    id: "0xa1", ts: NOW_S, host: "akash", geo: "US", model_live: "glm-4.7", model_tier: "free",
    net_worth_usd: 0, revenue_mo_usd: 0, burn_day_usd: 0.1, runway_days: 10, status: "alive",
    // pre-migration Supabase returns these as explicit nulls (or absent):
    tags: null, revenue_today_usd: null, revenue_by_source: null,
    net_worth_src: null, earn_src: null, last_heartbeat: null, log_feed: null,
  };
  const existing = { mrr: { total_usd: 1 } };
  const next = await renderDashboard({ rows: [preMigrationRow], reader: mockReader(), existing });
  assert.strictEqual(next.leaderboard.length, 1);
});

test("S2-IMPL-FIND-001: isDirectCliInvocation returns true for RELATIVE argv (the normal cron/GH-Action invocation) — not just when argv[1] happens to be absolute", async () => {
  const { isDirectCliInvocation } = await import(SCRIPT);
  const abs = path.resolve(SCRIPT); // absolute path to render-dashboard.mjs
  const rel = path.relative(process.cwd(), SCRIPT); // relative — the shape cron uses
  const importUrl = `file://${abs}`;
  assert.strictEqual(isDirectCliInvocation(["node", abs], importUrl), true, "absolute argv[1] must be direct");
  assert.strictEqual(isDirectCliInvocation(["node", rel], importUrl), true, "relative argv[1] (the cron shape) must ALSO be direct");
  assert.strictEqual(isDirectCliInvocation(["node", "some-other-script.mjs"], importUrl), false, "different script must NOT be direct");
  assert.strictEqual(isDirectCliInvocation(["node"], importUrl), false, "no argv[1] must NOT be direct");
});
