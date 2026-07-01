// enrichOnChain (VCSDD GREEN) — the ONLY chain caller. Overwrites self-asserted money with on-chain
// reads keyed on the wallet `id`; flags `unverified` on read failure. `reader` is injected (mockable).
const { excludeSet } = require("./leaderboard-constants");

function monthStartTs(nowMs) {
  const d = new Date(nowMs);
  return Math.floor(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), 1) / 1000);
}
function utcMidnightTs(nowMs) {
  const d = new Date(nowMs);
  return Math.floor(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()) / 1000);
}

// rows: validated telemetry rows. reader: { nativeBalanceWei, usdcBalanceAtomic, ethUsdPrice,
// externalInflowsUsd }. Returns new rows with net_worth_usd/revenue_* set from chain + *_src flags.
function enrichOnChain(rows, reader, nowMs = Date.now()) {
  const mStart = monthStartTs(nowMs);
  const midnight = utcMidnightTs(nowMs);
  return rows.map((row) => {
    const e = { ...row };
    const ex = excludeSet(row);
    // net worth = on-chain USDC + native*price (dimensioned USD)
    try {
      const usdc = Number(reader.usdcBalanceAtomic(row.id)) / 1e6;
      const eth = Number(reader.nativeBalanceWei(row.id)) / 1e18;
      e.net_worth_usd = usdc + eth * reader.ethUsdPrice();
      e.net_worth_src = "chain";
    } catch {
      e.net_worth_src = "unverified";
    }
    // earnings = external inflows (exclude self/seed/our)
    try {
      e.revenue_mo_usd = reader.externalInflowsUsd(row.id, mStart, ex);
      e.revenue_today_usd = reader.externalInflowsUsd(row.id, midnight, ex);
      e.earn_src = "chain";
    } catch {
      e.earn_src = "unverified";
    }
    return e;
  });
}

module.exports = { enrichOnChain, monthStartTs, utcMidnightTs };
