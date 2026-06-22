// revenue.mjs — PURE per-source revenue (P&L) computation, extracted from telemetry-poster.mjs so it is
// unit-testable without the daemon's side effects (telemetry-poster auto-runs post() on import).
//
// revenue per source = current on-chain value − cost basis (mark-to-market P&L), PLUS realised cash
// earnings (x402 sales / hl closes). Liquid is idle cash, not a stream → excluded. Negative = losing.
// A venue with value≈0 AND cost≈0 is hidden (never really used). This is what guarantees a phantom
// cost-basis key (e.g. a dropped morpho with on-chain dust) does NOT show a fake profit/loss cell.

export const YIELD_VENUES = ["aave", "morpho", "moonwell", "beefy", "fluid", "bluechip"];

// @param nw     netWorth() breakdown: { aave, morpho, moonwell, beefy, fluid, bluechip, ... } in USD
// @param basis  cost-basis (principal deposited) per venue, USD
// @param earnBySource realised cash earnings per source (x402/hl/token), USD
export function revenueBySource(nw, basis, earnBySource) {
  const out = {};
  for (const v of YIELD_VENUES) {
    const value = Number(nw[v] || 0), cost = Number((basis || {})[v] || 0);
    if (value < 1e-4 && cost < 1e-4) continue; // never used (or fully reconciled away) → hide
    out[v] = +(value - cost).toFixed(6);       // unrealised P&L (can be negative)
  }
  for (const [s, amt] of Object.entries(earnBySource || {})) { // realised cash earnings
    if (Math.abs(amt) < 1e-9) continue;
    out[s] = +((out[s] || 0) + amt).toFixed(6);
  }
  const total = +Object.values(out).reduce((a, b) => a + b, 0).toFixed(6);
  return { bySource: out, total };
}
