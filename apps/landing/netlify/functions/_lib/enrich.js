// enrichOnChain (VCSDD GREEN, extended for multi-chain 2026-07-05) — the ONLY chain caller. Overwrites
// self-asserted money with on-chain reads keyed on the wallet `id`; flags `unverified` on read failure.
// `readers` is a MAP keyed by chain ("base" | "solana" | "polygon"), each entry injected/mockable.
const { excludeSet } = require("./leaderboard-constants");

function monthStartTs(nowMs) {
  const d = new Date(nowMs);
  return Math.floor(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), 1) / 1000);
}
function utcMidnightTs(nowMs) {
  const d = new Date(nowMs);
  return Math.floor(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()) / 1000);
}

// rows: validated telemetry rows (each may carry `chain`, default "base"). readers: { base, solana,
// polygon } — each a { nativeBalanceWei, usdcBalanceAtomic, ethUsdPrice, externalInflowsUsd,
// nativeDecimals? }. nativeDecimals defaults to 18 (ETH/MATIC) when the reader doesn't declare one
// (Solana's reader declares 9, since SOL is NOT 18-decimal like the EVM chains — a plain hardcoded 1e18
// would silently under-report Solana net worth by 9 orders of magnitude). Returns new rows with
// net_worth_usd/revenue_* set from chain + *_src flags.
function enrichOnChain(rows, readers, nowMs = Date.now()) {
  const mStart = monthStartTs(nowMs);
  const midnight = utcMidnightTs(nowMs);
  return rows.map((row) => {
    const e = { ...row };
    const ex = excludeSet(row);
    // NO cross-chain fallback: a row explicitly on "polygon"/"solana" whose reader is missing must be
    // unverified, never silently re-checked against the wrong chain (a Polygon-only wallet read via the
    // Base reader would come back "verified" at a misleading $0 — exactly the claude-p bug this file's
    // multi-chain support exists to prevent). Only an ABSENT `chain` field defaults to "base".
    const reader = (readers || {})[row.chain || "base"];
    if (!reader) { e.net_worth_src = "unverified"; e.earn_src = "unverified"; return e; }
    const decimals = typeof reader.nativeDecimals === "function" ? reader.nativeDecimals() : 18;
    // net worth = on-chain stablecoin + native*price (dimensioned USD)
    try {
      const stable = Number(reader.usdcBalanceAtomic(row.id)) / 1e6;
      const native = Number(reader.nativeBalanceWei(row.id)) / Math.pow(10, decimals);
      const price = reader.ethUsdPrice();
      const nw = stable + native * price;
      if (!Number.isFinite(nw)) throw new Error("non-finite net worth"); // NaN price/balance ⇒ unverified, never trusted
      e.net_worth_usd = nw;
      e.net_worth_src = "chain";
    } catch {
      e.net_worth_src = "unverified";
    }
    // earnings = external inflows (exclude self/seed/our). today ⊆ month window, so clamp today ≤ mo
    // to hold the R9 invariant even against a quirky reader.
    try {
      const mo = reader.externalInflowsUsd(row.id, mStart, ex);
      const today = reader.externalInflowsUsd(row.id, midnight, ex);
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
