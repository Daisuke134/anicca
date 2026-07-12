// polymarket-value-reader.js — CURRENT mark-to-market portfolio value (idle cash + open positions) for
// a Polymarket account, from Polymarket's own public /value endpoint.
//
// Why this exists (2026-07-12 finding): a Polymarket trading wallet's real net worth is NOT its idle
// pUSD balanceOf() — most of an active trader's money sits in OPEN POSITIONS (ERC-1155 conditional
// tokens), which a plain ERC-20 balance read cannot see at all. Verified live: claude-p's PM deposit
// wallet (0x904B50d2e214Da947d83D6a2D32c4E3Ffc17Eb74) held only ~$0.18 of idle pUSD while
// data-api.polymarket.com/value reported ~$20.59 — the idle-cash-only reading undercounted this
// account's real net worth by >100x. /value is Polymarket's own mark-to-market of the account
// (cash + every open position at its current price), the same number the trader sees in its own UI.
const DEFAULT_VALUE_URL = (address) => `https://data-api.polymarket.com/value?user=${address}`;

/**
 * @param {string} address Polymarket proxy/deposit wallet (public, read-only).
 * @param {Function} fetchImpl injectable fetch.
 * @param {{valueUrl?:string}} [opts]
 * @returns {Promise<number>} current portfolio value in USD.
 *   Throws on a non-ok response or malformed body — never silently returns a guessed/zero value.
 */
async function fetchPortfolioValueUsd(address, fetchImpl, opts = {}) {
  const url = opts.valueUrl || DEFAULT_VALUE_URL(address);
  const res = await fetchImpl(url, { method: "GET" });
  if (!res.ok) throw new Error(`polymarket value ${res.status}`);
  const body = await res.json();
  // API returns [{ user, value }] for a single-address query.
  const entry = Array.isArray(body) ? body[0] : body;
  const v = Number(entry?.value);
  if (!Number.isFinite(v)) throw new Error("polymarket value: non-finite");
  return v;
}

module.exports = { fetchPortfolioValueUsd, DEFAULT_VALUE_URL };
