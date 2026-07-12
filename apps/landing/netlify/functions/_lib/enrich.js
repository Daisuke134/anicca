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

// Sprint-6 S6.5: `readers` is either ONE flat reader object (back-compat — used for every row,
// the original single-chain call style) OR a { base, solana, ... } map dispatched per row.chain
// (default 'base'). Duck-typed: a flat reader has usdcBalanceAtomic as an own function.
function readerFor(readers, chain) {
  if (typeof readers.usdcBalanceAtomic === "function") return readers; // flat reader, back-compat
  return readers[chain]; // may be undefined -> caller's try/catch marks unverified
}

// rows: validated telemetry rows. reader: { nativeBalanceWei, usdcBalanceAtomic, ethUsdPrice,
// externalInflowsUsd } OR a per-chain map of such readers. Returns new rows with
// net_worth_usd/revenue_* set from chain + *_src flags.
function enrichOnChain(rows, readers, nowMs = Date.now()) {
  const mStart = monthStartTs(nowMs);
  const midnight = utcMidnightTs(nowMs);
  return rows.map((row) => {
    const e = { ...row };
    const ex = excludeSet(row);
    const reader = readerFor(readers, row.chain || "base");
    if (!reader) { e.net_worth_src = "unverified"; e.earn_src = "unverified"; return e; }
    // net worth = on-chain USDC + native*price (dimensioned USD), UNLESS the reader exposes a
    // per-row netWorthUsd(id) override (Sprint-7: multi-chain/multi-venue instances — see
    // net-worth-augment.js). The override is per-ROW: it returns undefined for any id it has no
    // data for, so every other row sharing this reader keeps the exact old usdc+native computation.
    try {
      const override = typeof reader.netWorthUsd === "function" ? reader.netWorthUsd(row.id) : undefined;
      let nw;
      if (override !== undefined && override !== null) {
        nw = Number(override);
      } else {
        const usdc = Number(reader.usdcBalanceAtomic(row.id)) / 1e6;
        const eth = Number(reader.nativeBalanceWei(row.id)) / 1e18;
        const price = reader.ethUsdPrice();
        nw = usdc + eth * price;
      }
      if (!Number.isFinite(nw)) throw new Error("non-finite net worth"); // NaN price/balance ⇒ unverified, never trusted
      e.net_worth_usd = nw;
      e.net_worth_src = "chain";
    } catch {
      e.net_worth_src = "unverified";
    }
    // earnings = external inflows (exclude self/seed/our), UNLESS the reader exposes a per-row
    // revenueMoUsd(id) override (e.g. Polymarket realized P&L — REDEEM minus BUY — for an instance
    // whose real earnings a Transfer-log scan cannot see/cannot correctly classify). Same per-ROW
    // contract as netWorthUsd above. today ⊆ month window, so clamp today ≤ mo either way.
    try {
      const moOverride = typeof reader.revenueMoUsd === "function" ? reader.revenueMoUsd(row.id) : undefined;
      let mo, today;
      if (moOverride !== undefined && moOverride !== null) {
        mo = Number(moOverride);
        const todayOverride = typeof reader.revenueTodayUsd === "function" ? reader.revenueTodayUsd(row.id) : undefined;
        today = todayOverride !== undefined && todayOverride !== null ? Number(todayOverride) : mo;
      } else {
        mo = reader.externalInflowsUsd(row.id, mStart, ex);
        today = reader.externalInflowsUsd(row.id, midnight, ex);
      }
      if (!Number.isFinite(mo) || !Number.isFinite(today)) throw new Error("non-finite earnings");
      e.revenue_mo_usd = mo;
      e.revenue_today_usd = Math.min(today, mo);
      e.earn_src = "chain";
    } catch {
      e.earn_src = "unverified";
    }
    return e;
  });
}

module.exports = { enrichOnChain, monthStartTs, utcMidnightTs };
