const PERIODS_PER_YEAR_8H = (365 * 24) / 8;
const CACHE_TTL_MS = 60_000;

let cache = { timestamp: 0, rows: [], errors: [] };

export function baseSymbol(raw) {
  const symbol = String(raw || '').toUpperCase().trim();
  return symbol.replace(/(USDT|USDC|USD)$/, '') || symbol;
}

export function toFundingRate8h(nativeRate, intervalHours) {
  const hours = Number(intervalHours) > 0 ? Number(intervalHours) : 8;
  return Number(nativeRate) * (8 / hours);
}

export function annualizedBps(fundingRate8h) {
  return Number(fundingRate8h) * PERIODS_PER_YEAR_8H * 10_000;
}

function round(value, decimals) {
  const factor = 10 ** decimals;
  return Math.round(Number(value) * factor) / factor;
}

export function normalizeBinance(premiumIndex, fundingInfo = []) {
  const intervalBySymbol = new Map(
    (fundingInfo || []).map(item => [item.symbol, Number(item.fundingIntervalHours)]),
  );
  return (premiumIndex || [])
    .filter(item => item?.symbol && item.lastFundingRate != null && item.markPrice != null)
    .map(item => {
      const intervalHours = intervalBySymbol.get(item.symbol) || 8;
      const native = Number(item.lastFundingRate);
      return {
        exchange: 'binance',
        symbol: item.symbol,
        baseSymbol: baseSymbol(item.symbol),
        fundingRateNative: native,
        fundingIntervalHoursNative: intervalHours,
        fundingRate8h: toFundingRate8h(native, intervalHours),
        nextFundingTime: Number(item.nextFundingTime),
        markPrice: Number(item.markPrice),
      };
    })
    .filter(item => Number.isFinite(item.fundingRate8h) && Number.isFinite(item.markPrice));
}

export function normalizeBybit(tickers) {
  return (tickers || [])
    .filter(item => item?.symbol && item.fundingRate !== '' && item.fundingRate != null && item.markPrice)
    .map(item => {
      const intervalHours = Number(item.fundingIntervalHour) || 8;
      const native = Number(item.fundingRate);
      return {
        exchange: 'bybit',
        symbol: item.symbol,
        baseSymbol: baseSymbol(item.symbol),
        fundingRateNative: native,
        fundingIntervalHoursNative: intervalHours,
        fundingRate8h: toFundingRate8h(native, intervalHours),
        nextFundingTime: Number(item.nextFundingTime),
        markPrice: Number(item.markPrice),
      };
    })
    .filter(item => Number.isFinite(item.fundingRate8h) && Number.isFinite(item.markPrice));
}

export function normalizeHyperliquid(universe, contexts, now = Date.now()) {
  const nextFundingTime = Math.ceil(now / 3_600_000) * 3_600_000;
  const rows = [];
  for (let index = 0; index < (universe || []).length; index += 1) {
    const market = universe[index];
    const context = (contexts || [])[index];
    if (!market || !context || market.isDelisted) continue;
    const native = Number(context.funding);
    const markPrice = Number(context.markPx);
    if (!Number.isFinite(native) || !Number.isFinite(markPrice)) continue;
    rows.push({
      exchange: 'hyperliquid',
      symbol: market.name,
      baseSymbol: baseSymbol(market.name),
      fundingRateNative: native,
      fundingIntervalHoursNative: 1,
      fundingRate8h: toFundingRate8h(native, 1),
      nextFundingTime,
      markPrice,
    });
  }
  return rows;
}

export function computeDivergence(rows, topN = 20) {
  const bySymbol = new Map();
  for (const row of rows || []) {
    if (!bySymbol.has(row.baseSymbol)) bySymbol.set(row.baseSymbol, []);
    bySymbol.get(row.baseSymbol).push(row);
  }
  const divergence = [];
  for (const [symbol, group] of bySymbol) {
    if (new Set(group.map(item => item.exchange)).size < 2) continue;
    const sorted = [...group].sort(
      (a, b) => annualizedBps(b.fundingRate8h) - annualizedBps(a.fundingRate8h),
    );
    const high = sorted[0];
    const low = sorted.at(-1);
    const highBps = annualizedBps(high.fundingRate8h);
    const lowBps = annualizedBps(low.fundingRate8h);
    divergence.push({
      symbol,
      divergenceBps: round(highBps - lowBps, 2),
      short: { exchange: high.exchange, annualizedBps: round(highBps, 2) },
      long: { exchange: low.exchange, annualizedBps: round(lowBps, 2) },
    });
  }
  return divergence.sort((a, b) => b.divergenceBps - a.divergenceBps).slice(0, topN);
}

export function buildFundingRatesResponse(rows, { symbol, errors = [] } = {}) {
  const wanted = symbol ? baseSymbol(symbol) : null;
  const filtered = wanted ? (rows || []).filter(row => row.baseSymbol === wanted) : (rows || []);
  return {
    rates: filtered.slice(0, 1_000).map(row => ({
      symbol: row.symbol,
      exchange: row.exchange,
      baseSymbol: row.baseSymbol,
      fundingRate8h: round(row.fundingRate8h, 8),
      fundingRateNative: row.fundingRateNative,
      fundingIntervalHoursNative: row.fundingIntervalHoursNative,
      normalization: 'fundingRate8h = fundingRateNative * (8 / fundingIntervalHoursNative)',
      annualizedBps: round(annualizedBps(row.fundingRate8h), 2),
      nextFundingTime: row.nextFundingTime,
      markPrice: row.markPrice,
    })),
    divergenceTop20: computeDivergence(filtered, 20),
    exchanges: [...new Set((rows || []).map(row => row.exchange))],
    degraded: errors.length > 0,
    errors,
    generatedAt: new Date().toISOString(),
  };
}

async function fetchJson(fetchImpl, url, options, timeoutMs) {
  const response = await fetchImpl(url, {
    ...options,
    signal: AbortSignal.timeout(timeoutMs),
  });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

export async function fetchAllRows({
  fetchImpl = fetch,
  timeoutMs = 5_000,
} = {}) {
  const calls = [
    Promise.all([
      fetchJson(fetchImpl, 'https://fapi.binance.com/fapi/v1/premiumIndex', {}, timeoutMs),
      fetchJson(fetchImpl, 'https://fapi.binance.com/fapi/v1/fundingInfo', {}, timeoutMs),
    ]).then(([premium, info]) => normalizeBinance(premium, info)),
    fetchJson(fetchImpl, 'https://api.bybit.com/v5/market/tickers?category=linear', {}, timeoutMs)
      .then(body => {
        if (body.retCode !== 0) throw new Error(`retCode ${body.retCode}`);
        return normalizeBybit(body.result?.list);
      }),
    fetchJson(fetchImpl, 'https://api.hyperliquid.xyz/info', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ type: 'metaAndAssetCtxs' }),
    }, timeoutMs).then(body => normalizeHyperliquid(body?.[0]?.universe, body?.[1])),
  ];
  const settled = await Promise.allSettled(calls);
  const names = ['binance', 'bybit', 'hyperliquid'];
  const rows = [];
  const errors = [];
  settled.forEach((result, index) => {
    if (result.status === 'fulfilled') rows.push(...result.value);
    else errors.push({ exchange: names[index], error: String(result.reason?.message || 'failed').slice(0, 120) });
  });
  if (rows.length === 0) throw new Error('all funding-rate upstreams failed');
  return { rows, errors };
}

export async function getFundingRatesCached({
  now = Date.now(),
  ttlMs = CACHE_TTL_MS,
  fetchImpl = fetch,
} = {}) {
  if (cache.rows.length > 0 && now - cache.timestamp < ttlMs) return cache;
  const fresh = await fetchAllRows({ fetchImpl });
  cache = { timestamp: now, ...fresh };
  return cache;
}

export function resetFundingRatesCacheForTests() {
  cache = { timestamp: 0, rows: [], errors: [] };
}
