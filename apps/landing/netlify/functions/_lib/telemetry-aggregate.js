// aggregate — PURE function of (already enrich-on-chained) rows. No chain/network I/O here.
// Leaderboard ranks by VERIFIED external earnings; totals count only chain-verified figures.

function isVerified(src) {
  return src !== "unverified"; // 'chain' or absent (back-compat raw rows) count; only explicit 'unverified' excluded
}

// verified-earnings first (revenue desc, net_worth tiebreak when both chain), then id asc.
function rankCmp(a, b) {
  const av = a.earn_src === "chain";
  const bv = b.earn_src === "chain";
  if (av !== bv) return av ? -1 : 1; // chain-verified earners rank above everyone else
  if (av && bv) {
    if (b.revenue_mo_usd !== a.revenue_mo_usd) return b.revenue_mo_usd - a.revenue_mo_usd;
    if (a.net_worth_src === "chain" && b.net_worth_src === "chain" && b.net_worth_usd !== a.net_worth_usd) {
      return b.net_worth_usd - a.net_worth_usd;
    }
  }
  return String(a.id).localeCompare(String(b.id)); // deterministic id asc
}

function sumVerified(rows, valueKey, srcKey) {
  if (rows.length === 0) return 0; // empty set → 0 (back-compat)
  const counted = rows.filter((r) => isVerified(r[srcKey]));
  if (counted.length === 0) return undefined; // non-empty but nothing verified → undefined, never fake 0
  return counted.reduce((s, r) => s + (r[valueKey] || 0), 0);
}

function aggregate(rows) {
  const nowSec = Math.floor(Date.now() / 1000);
  const total_net_worth_usd = sumVerified(rows, "net_worth_usd", "net_worth_src");
  const earned_mo_usd = sumVerified(rows, "revenue_mo_usd", "earn_src");
  const alive = rows.filter((r) => r.status !== "dead").length;
  // self-funded = monthly revenue covers daily burn AND not dead (real economic test, NOT a model proxy)
  const selfFunded = rows.filter((r) => r.status !== "dead" && r.revenue_mo_usd / 30 >= r.burn_day_usd).length;
  const frontier = rows.filter((r) => r.model_tier === "frontier").length;
  const self_funded_pct = rows.length ? Math.round((selfFunded / rows.length) * 100) : 0;
  const frontier_pct = rows.length ? Math.round((frontier / rows.length) * 100) : 0;
  const leaderboard = rows
    .map((r) => ({ ...r, stale: r.ts ? nowSec - r.ts > 600 : false }))
    .sort(rankCmp);
  return { total_net_worth_usd, earned_mo_usd, alive, self_funded_pct, frontier_pct, leaderboard, updated_at: new Date().toISOString() };
}

module.exports = { aggregate };
