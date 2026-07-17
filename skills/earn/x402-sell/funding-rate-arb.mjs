/**
 * funding-rate-arb.mjs — pairwise cross-exchange funding-rate arbitrage signal, built on top of
 * funding-rates.mjs (serve-v2.mjs mounts it at GET /funding-rate-arb). No new upstream calls: reuses
 * the SAME cached rows funding-rates.mjs already fetches (getFundingRatesCached, 60s TTL) — pure
 * arithmetic on top, $0 marginal cost per INV-UNIT-ECON, no LLM in the serving path.
 *
 * Why this is a DISTINCT product from /funding-rates (not just the same data twice): /funding-rates'
 * own divergenceTop20 (computeDivergence in funding-rates.mjs) picks only the single highest-vs-lowest
 * exchange PAIR per symbol. A symbol quoted on all 3 exchanges (binance/bybit/hyperliquid) has 3
 * distinct tradeable pairs (binance-bybit, binance-hyperliquid, bybit-hyperliquid) — a bot running a
 * market-neutral funding-collection strategy on a SPECIFIC venue pair (e.g. it only has API keys for
 * bybit+hyperliquid) needs the bybit-hyperliquid spread even when binance-hyperliquid is bigger.
 * /funding-rate-arb enumerates every distinct exchange pair per symbol, not just the extreme one.
 */

function round(n, decimals) {
  const f = 10 ** decimals;
  return Math.round(Number(n) * f) / f;
}

// ---- pairwise arb computation (pure: rows -> arb opportunities) ------------
// rows: output of funding-rates.mjs's fetchAllRows/getFundingRatesCached ({ exchange, baseSymbol,
// fundingRate8h, markPrice, ... }). annualizedBpsFn injected to avoid a second computation path
// diverging from funding-rates.mjs's own annualization (single source of truth for the bps formula).
export function computeArbPairs(rows, annualizedBpsFn, { symbol, topN = 20 } = {}) {
  const want = symbol ? String(symbol).toUpperCase().trim() : null;
  const bySymbol = new Map();
  for (const r of rows || []) {
    if (want && r.baseSymbol !== want) continue;
    if (!bySymbol.has(r.baseSymbol)) bySymbol.set(r.baseSymbol, []);
    bySymbol.get(r.baseSymbol).push(r);
  }
  const out = [];
  for (const [sym, group] of bySymbol) {
    // one row per exchange per symbol expected; if an exchange lists a symbol twice (shouldn't
    // happen upstream) just take each row as its own quote — pairs still enumerate correctly.
    for (let i = 0; i < group.length; i++) {
      for (let j = i + 1; j < group.length; j++) {
        const a = group[i], b = group[j];
        if (a.exchange === b.exchange) continue; // need two DISTINCT venues to trade the spread
        const aBps = annualizedBpsFn(a.fundingRate8h);
        const bBps = annualizedBpsFn(b.fundingRate8h);
        const high = aBps >= bBps ? a : b, low = aBps >= bBps ? b : a;
        const highBps = Math.max(aBps, bBps), lowBps = Math.min(aBps, bBps);
        out.push({
          symbol: sym,
          divergenceBps: round(highBps - lowBps, 2),
          // market-neutral pair trade: short the high-funding venue (collects funding), long the
          // low-funding venue (pays less funding / collects if negative) — same convention as
          // funding-rates.mjs's computeDivergence.
          short: { exchange: high.exchange, annualizedBps: round(highBps, 2), markPrice: high.markPrice },
          long: { exchange: low.exchange, annualizedBps: round(lowBps, 2), markPrice: low.markPrice },
        });
      }
    }
  }
  out.sort((x, y) => y.divergenceBps - x.divergenceBps);
  return want ? out : out.slice(0, topN);
}

export function buildFundingRateArbResponse(rows, annualizedBpsFn, { symbol, errors = [] } = {}) {
  const pairs = computeArbPairs(rows, annualizedBpsFn, { symbol, topN: 20 });
  return {
    symbol: symbol ? String(symbol).toUpperCase().trim() : null,
    pairs,
    pairCount: pairs.length,
    note: "short = higher annualized funding venue (collects funding); long = lower venue (pays less / collects if negative). divergenceBps = short.annualizedBps - long.annualizedBps.",
    degraded: (errors || []).length > 0,
    errors: errors || [],
    generatedAt: new Date().toISOString(),
  };
}
