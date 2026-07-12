// net-worth-augment.js — wraps a base per-chain reader with per-ROW overrides for net worth and
// revenue, for the specific known ids that have extra wallet legs configured in
// dashboard-wallet-legs.js (claude-p, Franklin — see that file's header for why).
//
// Contract (enrich.js relies on this): `netWorthUsd(id)` / `revenueMoUsd(id)` return `undefined` for
// any id that has NO override configured — enrich.js then falls back to its normal
// usdcBalanceAtomic/nativeBalanceWei/ethUsdPrice or externalInflowsUsd path for that row. This is
// deliberately PER-ROW, not per-reader: attaching an override function to the shared reader object
// must never change behaviour for every OTHER row that reader also serves (e.g. the rest of the
// "agents at arms" leaderboard, which has no configured legs and must keep using Transfer-log
// earnings exactly as before).
//
// Everything is precomputed up front (this factory is async) so the returned accessors stay
// synchronous, matching every other reader factory in this codebase (chain-reader.js,
// chain-reader-solana.js). One leg/account failing to read degrades gracefully — see
// net-worth-lib.fetchNetWorth's own per-leg fail-soft behaviour; a revenue override that fails to
// fetch is simply left out of the cache, so that row's enrich falls back to its default earnings path.
const { fetchNetWorth } = require('./net-worth-lib');
const { fetchRealizedPnlUsd } = require('./polymarket-revenue-reader');
const { fetchPortfolioValueUsd } = require('./polymarket-value-reader');
const { normalizeId, legsFor, polymarketAccountFor, polymarketRevenueEnabledFor } = require('./dashboard-wallet-legs');

/**
 * Precompute the override caches for every row that has configured legs/a Polymarket account.
 * Async (does the actual chain/API reads); the returned accessor bundle is synchronous, so it can be
 * attached to as many per-chain readers as `enrichOnChain` needs (base, solana, ...) WITHOUT
 * re-fetching — the overrides are id-keyed, not chain-keyed.
 *
 * @param {Array<{id:string}>} rows telemetry rows to precompute overrides for.
 * @param {{fetchImpl?:Function, rpc?:object, hlInfoUrl?:string, polymarketActivityUrl?:Function|string}} [opts]
 * @returns {Promise<{netWorthUsd:Function, revenueMoUsd:Function, revenueTodayUsd:Function, errors:Array}>}
 */
async function computeDashboardOverrides(rows, opts = {}) {
  const fetchImpl = opts.fetchImpl || globalThis.fetch;
  const netWorthCache = new Map();
  const revenueCache = new Map();
  const errors = [];

  const seen = new Set();
  for (const row of rows) {
    const key = normalizeId(row.id);
    if (seen.has(key)) continue;
    seen.add(key);

    const legs = legsFor(row.id);
    const pmAccount = polymarketAccountFor(row.id);
    if (legs.length || pmAccount) {
      // net worth = plain chain legs (Base/Polygon/Solana/Hyperliquid) PLUS the Polymarket account's
      // mark-to-market portfolio value (idle cash + every open position — see polymarket-value-reader.js;
      // NOT double-counted, `legs` deliberately excludes a plain balanceOf read of the PM deposit wallet).
      let total = 0;
      let anyOk = false;
      const legErrors = [];
      if (legs.length) {
        try {
          const result = await fetchNetWorth(legs, { fetchImpl, rpc: opts.rpc, hlInfoUrl: opts.hlInfoUrl });
          total += result.total_usd;
          anyOk = true;
          if (result.errors.length) legErrors.push(...result.errors);
        } catch (e) {
          legErrors.push({ error: String(e.message || e) });
        }
      }
      if (pmAccount) {
        try {
          const valueUrl = typeof opts.polymarketValueUrl === "function"
            ? opts.polymarketValueUrl(pmAccount)
            : opts.polymarketValueUrl;
          total += await fetchPortfolioValueUsd(pmAccount, fetchImpl, { valueUrl });
          anyOk = true;
        } catch (e) {
          legErrors.push({ error: String(e.message || e), leg: "polymarket-value" });
        }
      }
      if (anyOk) netWorthCache.set(key, Math.round(total * 1e6) / 1e6);
      // else: leave uncached -> netWorthUsd(id) returns undefined -> enrich falls back to the base reader
      if (legErrors.length) errors.push({ id: row.id, kind: "net_worth", errors: legErrors });
    }

    if (pmAccount && polymarketRevenueEnabledFor(row.id)) {
      try {
        const activityUrl = typeof opts.polymarketActivityUrl === "function"
          ? opts.polymarketActivityUrl(pmAccount)
          : opts.polymarketActivityUrl;
        const pnl = await fetchRealizedPnlUsd(pmAccount, fetchImpl, { activityUrl });
        revenueCache.set(key, pnl);
      } catch (e) {
        errors.push({ id: row.id, kind: "revenue", errors: [{ error: String(e.message || e) }] });
        // leave uncached -> revenueMoUsd(id) returns undefined -> enrich falls back to externalInflowsUsd
      }
    }
  }

  return {
    netWorthUsd: (id) => netWorthCache.get(normalizeId(id)),
    revenueMoUsd: (id) => revenueCache.get(normalizeId(id)),
    // A row whose revenueMoUsd is overridden has no reliable "today" figure from this source
    // (Polymarket activity is not bucketed by day here); report 0 rather than guessing — enrich
    // clamps revenue_today_usd <= revenue_mo_usd regardless.
    revenueTodayUsd: (id) => (revenueCache.has(normalizeId(id)) ? 0 : undefined),
    errors,
  };
}

/** Merge a precomputed override bundle onto a base per-chain reader (sync, no I/O). */
function withDashboardOverrides(baseReader, overrides) {
  return {
    ...baseReader,
    netWorthUsd: overrides.netWorthUsd,
    revenueMoUsd: overrides.revenueMoUsd,
    revenueTodayUsd: overrides.revenueTodayUsd,
  };
}

/**
 * Convenience one-shot for the single-reader case: compute the overrides for `rows` and merge them
 * onto `baseReader` in one call.
 * @param {object} baseReader flat reader (same shape enrichOnChain's back-compat single-reader call expects).
 * @param {Array<{id:string}>} rows
 * @param {object} [opts] see computeDashboardOverrides
 * @returns {Promise<object>} a NEW reader object: every property of baseReader, plus the overrides.
 */
async function augmentDashboardReader(baseReader, rows, opts = {}) {
  const overrides = await computeDashboardOverrides(rows, opts);
  return withDashboardOverrides(baseReader, overrides);
}

module.exports = { augmentDashboardReader, computeDashboardOverrides, withDashboardOverrides };
