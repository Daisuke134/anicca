/**
 * funding-rates.mjs — cross-exchange perp funding-rate primitive sold over x402 (serve.mjs mounts it
 * at GET /funding-rates). Deterministic fetch+arithmetic only, no LLM in the serving path, free
 * public upstreams (Binance/Bybit/Hyperliquid), $0 marginal cost per INV-UNIT-ECON.
 *
 * Buyer = automated trading bots polling every few seconds (measured: ottoai's funding-rate product
 * sees ~93.5% bot traffic at ~7s/poll). Upstream perp funding changes continuously (mark price every
 * tick, funding rate every settlement), satisfying INV-REPEAT — this is not a static/cacheable-forever
 * product. A 60s in-memory cache (see getFundingRatesCached) protects the free upstreams from being
 * hit on every buyer poll while still serving fresh-enough data.
 *
 * Normalization: each exchange pays funding on its own native interval (Binance/Bybit: mostly 8h but
 * some symbols 1h/2h/4h — see /fapi/v1/fundingInfo and the per-ticker fundingIntervalHour field;
 * Hyperliquid: always 1h, docs: https://hyperliquid.gitbook.io/hyperliquid-docs/trading/funding —
 * "funding is paid every hour at one eighth of the computed [8h] rate"). To compare rates across
 * venues we rebase every native rate to an 8h-equivalent: fundingRate8h = native * (8 / intervalHours).
 * Verified empirically 2026-07-17 (curl): Binance premiumIndex has no interval field (defaults to 8h
 * unless listed in fundingInfo); Bybit's /v5/market/tickers ALREADY includes fundingIntervalHour per
 * row (no second call needed); Hyperliquid's metaAndAssetCtxs "funding" field is the hourly-paid rate
 * (cross-checked against POST {"type":"predictedFundings"} which reports the same value for HlPerp).
 *
 * Cross-exchange divergence = the arbitrage signal: for a symbol listed on 2+ exchanges, the spread
 * between the highest and lowest annualized funding rate. A market-neutral trader shorts the high-rate
 * venue (collects funding) and longs the low-rate venue (pays less / collects if negative).
 */

// ---- symbol normalization --------------------------------------------------
// Binance/Bybit perp symbols are "<BASE>USDT"/"<BASE>USDC"; Hyperliquid uses the bare base asset name
// (e.g. "BTC"). One canonical key per underlying asset lets divergence match across venues.
export function baseSymbol(raw) {
  const s = String(raw).toUpperCase().trim();
  const stripped = s.replace(/(USDT|USDC|USD)$/, "");
  return stripped || s;
}

// ---- 8h-equivalent + annualized bps ----------------------------------------
const PERIODS_PER_YEAR_8H = (365 * 24) / 8; // 1095 settlements/yr at an 8h cadence

export function toFundingRate8h(nativeRate, intervalHours) {
  const h = Number(intervalHours) > 0 ? Number(intervalHours) : 8;
  return Number(nativeRate) * (8 / h);
}

export function annualizedBps(fundingRate8h) {
  return Number(fundingRate8h) * PERIODS_PER_YEAR_8H * 10_000;
}

function round(n, decimals) {
  const f = 10 ** decimals;
  return Math.round(Number(n) * f) / f;
}

// ---- per-exchange normalizers (pure: raw upstream JSON -> canonical rows) --
// Every row: { exchange, symbol, baseSymbol, fundingRateNative, fundingIntervalHoursNative,
//              fundingRate8h, nextFundingTime (ms epoch), markPrice }

export function normalizeBinance(premiumIndex, fundingInfo = []) {
  const intervalBySymbol = new Map(
    (fundingInfo || []).map((f) => [f.symbol, Number(f.fundingIntervalHours)]),
  );
  return (premiumIndex || [])
    .filter((p) => p && p.symbol && p.lastFundingRate != null && p.markPrice != null)
    .map((p) => {
      // symbols absent from /fapi/v1/fundingInfo use Binance's default 8h interval (verified: that
      // endpoint only lists symbols with a NON-default interval, e.g. LPTUSDT=4h, TRBUSDT=4h).
      const intervalHours = intervalBySymbol.get(p.symbol) || 8;
      const native = Number(p.lastFundingRate);
      return {
        exchange: "binance", symbol: p.symbol, baseSymbol: baseSymbol(p.symbol),
        fundingRateNative: native, fundingIntervalHoursNative: intervalHours,
        fundingRate8h: toFundingRate8h(native, intervalHours),
        nextFundingTime: Number(p.nextFundingTime), markPrice: Number(p.markPrice),
      };
    });
}

export function normalizeBybit(tickers) {
  return (tickers || [])
    .filter((t) => t && t.symbol && t.fundingRate !== "" && t.fundingRate != null && t.markPrice)
    .map((t) => {
      const intervalHours = Number(t.fundingIntervalHour) || 8;
      const native = Number(t.fundingRate);
      return {
        exchange: "bybit", symbol: t.symbol, baseSymbol: baseSymbol(t.symbol),
        fundingRateNative: native, fundingIntervalHoursNative: intervalHours,
        fundingRate8h: toFundingRate8h(native, intervalHours),
        nextFundingTime: Number(t.nextFundingTime), markPrice: Number(t.markPrice),
      };
    });
}

export function normalizeHyperliquid(universe, ctxs, now = Date.now()) {
  // Hyperliquid pays funding every hour on the hour (docs, verified above) but metaAndAssetCtxs does
  // not return the next settlement timestamp, so it is computed deterministically from `now`.
  const nextFundingTime = Math.ceil(now / 3_600_000) * 3_600_000;
  const rows = [];
  for (let i = 0; i < (universe || []).length; i++) {
    const u = universe[i], ctx = (ctxs || [])[i];
    if (!u || !ctx || u.isDelisted) continue;
    const native = Number(ctx.funding);
    const markPrice = Number(ctx.markPx);
    if (!Number.isFinite(native) || !Number.isFinite(markPrice)) continue;
    rows.push({
      exchange: "hyperliquid", symbol: u.name, baseSymbol: baseSymbol(u.name),
      fundingRateNative: native, fundingIntervalHoursNative: 1,
      fundingRate8h: toFundingRate8h(native, 1),
      nextFundingTime, markPrice,
    });
  }
  return rows;
}

// ---- cross-exchange divergence (the arbitrage signal) ----------------------
export function computeDivergence(rows, topN = 20) {
  const bySymbol = new Map();
  for (const r of rows || []) {
    if (!bySymbol.has(r.baseSymbol)) bySymbol.set(r.baseSymbol, []);
    bySymbol.get(r.baseSymbol).push(r);
  }
  const out = [];
  for (const [symbol, group] of bySymbol) {
    if (group.length < 2) continue; // divergence needs >=2 exchanges quoting the same asset
    let high = group[0], low = group[0];
    let highBps = annualizedBps(high.fundingRate8h), lowBps = annualizedBps(low.fundingRate8h);
    for (const g of group) {
      const bps = annualizedBps(g.fundingRate8h);
      if (bps > highBps) { high = g; highBps = bps; }
      if (bps < lowBps) { low = g; lowBps = bps; }
    }
    if (high.exchange === low.exchange) continue; // only one distinct exchange had data
    out.push({
      symbol,
      divergenceBps: round(highBps - lowBps, 2),
      short: { exchange: high.exchange, annualizedBps: round(highBps, 2) }, // collects funding
      long: { exchange: low.exchange, annualizedBps: round(lowBps, 2) },    // pays less / collects if negative
    });
  }
  out.sort((a, b) => b.divergenceBps - a.divergenceBps);
  return out.slice(0, topN);
}

// ---- response assembly (pure: rows -> the JSON the buyer receives) --------
export function buildFundingRatesResponse(rows, { symbol, errors = [] } = {}) {
  const want = symbol ? baseSymbol(symbol) : null;
  const filtered = want ? (rows || []).filter((r) => r.baseSymbol === want) : (rows || []);
  const rates = filtered.map((r) => ({
    symbol: r.symbol, exchange: r.exchange, baseSymbol: r.baseSymbol,
    fundingRate8h: round(r.fundingRate8h, 8),
    fundingRateNative: r.fundingRateNative, fundingIntervalHoursNative: r.fundingIntervalHoursNative,
    normalization: "fundingRate8h = fundingRateNative * (8 / fundingIntervalHoursNative)",
    annualizedBps: round(annualizedBps(r.fundingRate8h), 2),
    nextFundingTime: r.nextFundingTime, markPrice: r.markPrice,
  }));
  return {
    rates,
    divergenceTop20: computeDivergence(filtered, 20),
    exchanges: [...new Set((rows || []).map((r) => r.exchange))],
    degraded: (errors || []).length > 0,
    errors: errors || [],
    generatedAt: new Date().toISOString(),
  };
}

// ---- network fetch (I/O; not unit-tested — normalizers/divergence above are the tested pure core) --
async function fetchJson(url, opts, timeoutMs) {
  const resp = await fetch(url, { ...opts, signal: AbortSignal.timeout(timeoutMs) });
  if (!resp.ok) throw new Error(`HTTP ${resp.status} from ${url}`);
  return resp.json();
}

async function fetchBinanceRaw(timeoutMs) {
  const [premiumIndex, fundingInfo] = await Promise.all([
    fetchJson("https://fapi.binance.com/fapi/v1/premiumIndex", {}, timeoutMs),
    fetchJson("https://fapi.binance.com/fapi/v1/fundingInfo", {}, timeoutMs),
  ]);
  return normalizeBinance(premiumIndex, fundingInfo);
}

async function fetchBybitRaw(timeoutMs) {
  const body = await fetchJson("https://api.bybit.com/v5/market/tickers?category=linear", {}, timeoutMs);
  if (body.retCode !== 0) throw new Error(`bybit retCode ${body.retCode}: ${body.retMsg}`);
  return normalizeBybit(body.result?.list);
}

async function fetchHyperliquidRaw(timeoutMs) {
  const body = await fetchJson("https://api.hyperliquid.xyz/info", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ type: "metaAndAssetCtxs" }),
  }, timeoutMs);
  return normalizeHyperliquid(body?.[0]?.universe, body?.[1]);
}

const UPSTREAM_TIMEOUT_MS = 5_000;

// Degrades: if one exchange fails the other(s) still serve; only throws when ALL fail.
export async function fetchAllRows({ timeoutMs = UPSTREAM_TIMEOUT_MS } = {}) {
  const [bin, byb, hl] = await Promise.allSettled([
    fetchBinanceRaw(timeoutMs), fetchBybitRaw(timeoutMs), fetchHyperliquidRaw(timeoutMs),
  ]);
  const rows = [], errors = [];
  for (const [name, result] of [["binance", bin], ["bybit", byb], ["hyperliquid", hl]]) {
    if (result.status === "fulfilled") rows.push(...result.value);
    else errors.push({ exchange: name, error: String(result.reason?.message || result.reason).slice(0, 200) });
  }
  if (rows.length === 0) {
    throw new Error(`all upstream exchanges failed: ${errors.map((e) => `${e.exchange}: ${e.error}`).join("; ")}`);
  }
  return { rows, errors };
}

// 60s in-memory cache: upstream is hit at most once/min regardless of buyer poll frequency (measured
// buyer behavior: ~7s/poll bots — see file header). Module-level state is fine here: one process = one
// seller instance (per-instance x402 seller processes, cf. serve.mjs PAYTO gating).
const CACHE_TTL_MS = 60_000;
let cache = { ts: 0, rows: [], errors: [] };

export async function getFundingRatesCached({ now = Date.now(), ttlMs = CACHE_TTL_MS } = {}) {
  if (cache.rows.length && now - cache.ts < ttlMs) return cache;
  const { rows, errors } = await fetchAllRows();
  cache = { ts: now, rows, errors };
  return cache;
}

// test-only escape hatch: reset the module-level cache between unit tests.
export function _resetCacheForTests() {
  cache = { ts: 0, rows: [], errors: [] };
}
