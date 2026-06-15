function aggregate(rows) {
  const total_net_worth_usd = rows.reduce((s, r) => s + r.net_worth_usd, 0);
  const earned_mo_usd = rows.reduce((s, r) => s + r.revenue_mo_usd, 0);
  const alive = rows.filter((r) => r.status !== "dead").length;
  // self-funded = monthly revenue covers daily burn AND not dead (real economic test, NOT a model proxy)
  const selfFunded = rows.filter((r) => r.status !== "dead" && r.revenue_mo_usd / 30 >= r.burn_day_usd).length;
  const frontier = rows.filter((r) => r.model_tier === "frontier").length;
  const self_funded_pct = rows.length ? Math.round((selfFunded / rows.length) * 100) : 0;
  const frontier_pct = rows.length ? Math.round((frontier / rows.length) * 100) : 0;
  const leaderboard = [...rows].sort((a, b) => b.net_worth_usd - a.net_worth_usd);
  return { total_net_worth_usd, earned_mo_usd, alive, self_funded_pct, frontier_pct, leaderboard, updated_at: new Date().toISOString() };
}
module.exports = { aggregate };
