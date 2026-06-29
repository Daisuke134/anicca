// Aggregate live anicca telemetry for the dashboard.
//
// LIVENESS FILTER (Dais 2026-06-18: "fake mf everywhere — VERIFY"): an instance only counts
// as live if it posted within FRESH_S. A real anicca posts telemetry every wake (the loop +
// report skill heartbeat), so anything older than this window is a stale/abandoned/test row and
// is excluded from the total, the count, and the leaderboard. This is why old Hardhat/test ids
// (host "test"/"do", hours old) no longer inflate the numbers — only genuinely-alive agents show.
const FRESH_S = Number(process.env.TELEMETRY_FRESH_S || 1800); // 30 min default

function aggregate(rows, nowS) {
  const now = nowS || Math.floor(Date.now() / 1000);
  const live = (Array.isArray(rows) ? rows : []).filter(
    (r) => r && typeof r.ts === "number" && now - r.ts <= FRESH_S && r.status !== "dead"
  );
  const total_net_worth_usd = live.reduce((s, r) => s + (r.net_worth_usd || 0), 0);
  const earned_mo_usd = live.reduce((s, r) => s + (r.revenue_mo_usd || 0), 0);
  // total revenue TODAY across all live agents (can be negative when the colony is losing money)
  const earned_today_usd = live.reduce((s, r) => s + (r.daily_revenue_usd || 0), 0);
  const alive = live.length;
  // self-funded = monthly revenue covers daily burn (real economic test, NOT a model proxy)
  const selfFunded = live.filter((r) => r.revenue_mo_usd / 30 >= (r.burn_day_usd || 0)).length;
  const frontier = live.filter((r) => r.model_tier === "frontier").length;
  const self_funded_pct = live.length ? Math.round((selfFunded / live.length) * 100) : 0;
  const frontier_pct = live.length ? Math.round((frontier / live.length) * 100) : 0;
  const leaderboard = [...live].sort((a, b) => b.net_worth_usd - a.net_worth_usd);
  return { total_net_worth_usd, earned_mo_usd, earned_today_usd, alive, self_funded_pct, frontier_pct, leaderboard, updated_at: new Date().toISOString() };
}
module.exports = { aggregate };
