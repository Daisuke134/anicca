// polymarket-revenue-reader.js — realized P&L for a Polymarket account, straight from Polymarket's
// own public activity API (https://data-api.polymarket.com/activity). This is the SAME definition
// Polymarket itself uses to settle a market: a REDEEM is real cash paid out for a winning position;
// a BUY is real cash spent opening a position. realized P&L = sum(REDEEM.usdcSize) − sum(BUY.usdcSize).
//
// Why this replaces the old Base-Transfer-log "earnings" heuristic for a Polymarket trader: money
// moving INTO the trading wallet (a deposit/bridge/top-up) is not itself a profit, and money moving
// OUT (a redemption paid to the same proxy wallet) was previously invisible to a Base-only Transfer
// scan (Polymarket settles on Polygon, not Base) — so neither side of the real economics was measured
// correctly. The activity feed is the ground truth Polymarket itself trades against.
//
// SELL trades are deliberately NOT netted in here: a SELL that closes a position before resolution
// realizes P&L too, but distinguishing an opening BUY from a closing SELL's cost basis needs
// matching, which the trader's own ledger (skills/earn/polymarket-trade/SKILL.md) already does more
// carefully. This reader only counts the two unambiguous cash events (REDEEM in, BUY out) so it can
// never overstate profit from an in-flight (not yet resolved) position.
const DEFAULT_ACTIVITY_URL = (address, limit) =>
  `https://data-api.polymarket.com/activity?user=${address}&limit=${limit}`;

/**
 * @param {string} address Polymarket proxy/deposit wallet (public, no key needed — read-only API).
 * @param {Function} fetchImpl injectable fetch (tests never hit the network).
 * @param {{activityUrl?:string, limit?:number}} [opts]
 * @returns {Promise<number>} realized P&L in USD = sum(REDEEM.usdcSize) − sum(BUY.usdcSize).
 *   Throws on a non-ok response or malformed body — callers must treat a throw as "unverified",
 *   never silently reporting a guessed/zero revenue as if it were chain-verified.
 */
async function fetchRealizedPnlUsd(address, fetchImpl, opts = {}) {
  const limit = opts.limit || 500;
  const url = opts.activityUrl || DEFAULT_ACTIVITY_URL(address, limit);
  const res = await fetchImpl(url, { method: 'GET' });
  if (!res.ok) throw new Error(`polymarket activity ${res.status}`);
  const list = await res.json();
  if (!Array.isArray(list)) throw new Error('polymarket activity: not an array');

  let redeemed = 0;
  let bought = 0;
  for (const a of list) {
    if (!a || typeof a !== 'object') continue;
    const size = Number(a.usdcSize);
    if (!Number.isFinite(size)) continue;
    if (a.type === 'REDEEM') redeemed += size;
    else if (a.type === 'TRADE' && a.side === 'BUY') bought += size;
  }
  const pnl = redeemed - bought;
  if (!Number.isFinite(pnl)) throw new Error('polymarket activity: non-finite pnl');
  return Math.round(pnl * 1e6) / 1e6;
}

module.exports = { fetchRealizedPnlUsd, DEFAULT_ACTIVITY_URL };
