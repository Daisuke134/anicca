// Aggregate live, on-chain-ENRICHED anicca telemetry for the dashboard (R12, 2026-07-05: never serve
// raw self-reported rankings — dashboard-sync.js runs enrichOnChain over the rows before calling this,
// so every row here already carries net_worth_src/earn_src = "chain" | "unverified").
//
// LIVENESS FILTER (Dais 2026-06-18: "fake mf everywhere — VERIFY"): an instance only counts
// as live if it posted within FRESH_S. A real anicca posts telemetry every wake (the loop +
// report skill heartbeat), so anything older than this window is a stale/abandoned/test row and
// is excluded from the total, the count, and the leaderboard. This is why old Hardhat/test ids
// (host "test"/"do", hours old) no longer inflate the numbers — only genuinely-alive agents show.
const { OUR_INSTANCE_IDS } = require("./leaderboard-constants");
const OUR = new Set(OUR_INSTANCE_IDS.map((a) => String(a).toLowerCase()));
const FRESH_S = Number(process.env.TELEMETRY_FRESH_S || 1800); // 30 min default
const STALE_DISPLAY_S = 300; // display-only "stale" flag — matches lib/dashboard-core.mjs's client-side STALE_SECS

function isVerified(src) { return src === "chain"; }

// rank by chain-VERIFIED earnings first (R2: un-buyable rank) — a self-reported/unverified row can
// never outrank a verified earner, no matter how large its self-asserted number is.
function rankCmp(a, b) {
  const av = a.earn_src === "chain";
  const bv = b.earn_src === "chain";
  if (av !== bv) return av ? -1 : 1;
  if (av && bv && b.revenue_mo_usd !== a.revenue_mo_usd) return b.revenue_mo_usd - a.revenue_mo_usd;
  if (a.net_worth_src === "chain" && b.net_worth_src === "chain" && b.net_worth_usd !== a.net_worth_usd) {
    return b.net_worth_usd - a.net_worth_usd;
  }
  return String(a.id).localeCompare(String(b.id));
}

// sums ONLY chain-verified figures — non-empty-but-nothing-verified => undefined, never a fake 0.
function sumVerified(rows, valueKey, srcKey) {
  if (rows.length === 0) return 0;
  const counted = rows.filter((r) => isVerified(r[srcKey]));
  if (counted.length === 0) return undefined;
  const sum = counted.reduce((s, r) => s + (r[valueKey] || 0), 0);
  return Number.isFinite(sum) ? sum : undefined;
}

function aggregate(rows, nowMs) {
  const now = nowMs ?? Date.now();
  const nowSec = Math.floor(now / 1000);
  const live = (Array.isArray(rows) ? rows : []).filter(
    (r) => r && typeof r.ts === "number" && nowSec - r.ts <= FRESH_S && r.status !== "dead"
  );
  const total_net_worth_usd = sumVerified(live, "net_worth_usd", "net_worth_src");
  const earned_mo_usd = sumVerified(live, "revenue_mo_usd", "earn_src");
  // "earned today" = chain-verified inflows since midnight (enrichOnChain's revenue_today_usd), NOT the
  // self-reported daily_revenue_usd snapshot-diff field — R12 applies here too.
  const earned_today_usd = sumVerified(live, "revenue_today_usd", "earn_src");
  const alive = live.length;
  // self-funded = CHAIN-VERIFIED monthly revenue covers daily burn (real economic test, never a
  // self-reported/model-tier proxy).
  const selfFunded = live.filter(
    (r) => r.earn_src === "chain" && r.revenue_mo_usd / 30 >= (r.burn_day_usd || 0)
  ).length;
  const frontier = live.filter((r) => r.model_tier === "frontier").length;
  const self_funded_pct = live.length ? Math.round((selfFunded / live.length) * 100) : 0;
  const frontier_pct = live.length ? Math.round((frontier / live.length) * 100) : 0;
  const leaderboard = live
    .map((r) => ({ ...r, stale: r.ts ? nowSec - r.ts > STALE_DISPLAY_S : false, is_ours: OUR.has(String(r.id).toLowerCase()) }))
    .sort(rankCmp);
  return { total_net_worth_usd, earned_mo_usd, earned_today_usd, alive, self_funded_pct, frontier_pct, leaderboard, updated_at: new Date(now).toISOString() };
}
module.exports = { aggregate };
