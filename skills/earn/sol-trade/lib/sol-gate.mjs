// sol-gate.mjs — SOL pre-gate: the pure engage-decision function (REQ-008), the dev-safety
// paper/live boundary (REQ-009), the free Jupiter Price v3 fetch wrapper (REQ-007), and the
// descriptive-only signal payload builder (REQ-010, HARD #0). franklin-sol-evolvable-edge.
//
// HARD #0 (unchanged, non-negotiable): this file NEVER decides which market/side to trade -- it
// only computes an ENGAGE/SKIP signal from observed market data + the current genome. Which
// market/side/size to trade remains franklin-trading's own internal model-debate judgment,
// exactly as today (REQ-010/REQ-018).
import fs from "node:fs";
import path from "node:path";

// NFR: MUST NOT exceed 8 seconds per mint.
export const DEFAULT_TIMEOUT_MS = 8000;

const DEFAULT_ENDPOINT = "https://lite-api.jup.ag/price/v3";

function readJsonSafe(filePath) {
  try {
    return JSON.parse(fs.readFileSync(filePath, "utf8"));
  } catch {
    return null;
  }
}

/**
 * isLiveEnabled(env) — REQ-009 (HARD dev-safety): only exactly "1" is live-enabled. Any other
 * value (unset, "true", "yes", "0", empty string, whitespace-padded "1") is treated identically
 * to unset -- fail closed to paper mode, never a loose truthy-string match. Pure over an injected
 * env object so tests never need to mutate process.env.
 */
export function isLiveEnabled(env = process.env) {
  return env.SOL_GATE_LIVE_ENABLE === "1";
}

/**
 * decideEngagement({ momentumPct, liquidityUsd, ageSec, genome, liveEnabled }) — REQ-008/009, the
 * single most safety-critical pure function in this feature. No I/O, no randomness, no wall-clock
 * read; the SAME function regardless of which genome (baseline or any mutant) is passed in
 * (REQ-018: evolution only ever produces new numeric KNOB VALUES consumed as data here, never new
 * code).
 *
 * momentum_component = min(5, (abs(momentumPct) / genome.SOL_GATE_MIN_MOMENTUM_PCT) * 5)
 * liquidity_component = min(5, (liquidityUsd / genome.SOL_GATE_MIN_LIQUIDITY_USD) * 5)
 * conviction = momentum_component + liquidity_component (range 0-10)
 * wouldEngage = abs(momentumPct) >= MIN_MOMENTUM_PCT AND liquidityUsd >= MIN_LIQUIDITY_USD AND
 *               conviction >= MIN_CONVICTION
 * engage = liveEnabled === true AND wouldEngage === true (REQ-009's paper-mode override; a
 *          belt-and-suspenders staleness re-check also defeats wouldEngage if ageSec exceeds the
 *          genome's own SOL_GATE_MAX_STALENESS_SEC, mirroring REQ-007's fetch-level cutoff).
 */
export function decideEngagement({ momentumPct, liquidityUsd, ageSec, genome, liveEnabled }) {
  const g = genome || {};
  const minMomentum = Number(g.SOL_GATE_MIN_MOMENTUM_PCT);
  const minLiquidity = Number(g.SOL_GATE_MIN_LIQUIDITY_USD);
  const minConviction = Number(g.SOL_GATE_MIN_CONVICTION);
  const maxStaleness = Number(g.SOL_GATE_MAX_STALENESS_SEC);

  const mp = Number(momentumPct);
  const lq = Number(liquidityUsd);
  const age = Number(ageSec);

  const genomeOk =
    Number.isFinite(minMomentum) && minMomentum > 0 && Number.isFinite(minLiquidity) && minLiquidity > 0 && Number.isFinite(minConviction);
  const inputsOk = Number.isFinite(mp) && Number.isFinite(lq);

  let momentumComponent = 0;
  let liquidityComponent = 0;
  let conviction = 0;
  let wouldEngage = false;

  if (genomeOk && inputsOk) {
    momentumComponent = Math.min(5, (Math.abs(mp) / minMomentum) * 5);
    liquidityComponent = Math.min(5, (lq / minLiquidity) * 5);
    conviction = momentumComponent + liquidityComponent;
    wouldEngage = Math.abs(mp) >= minMomentum && lq >= minLiquidity && conviction >= minConviction;
  }

  // Belt-and-suspenders staleness re-check (mirrors REQ-007's fetch-level cutoff at this, the
  // single choke point that actually decides engagement).
  if (Number.isFinite(maxStaleness) && Number.isFinite(age) && age > maxStaleness) {
    wouldEngage = false;
  }

  const engage = liveEnabled === true && wouldEngage === true;

  return { wouldEngage, conviction, momentumComponent, liquidityComponent, engage };
}

/**
 * fetchSolMarketSignal(mint, opts) — REQ-007. Fetches usdPrice/priceChange24h/liquidity from the
 * free, unauthenticated Jupiter Price v3 endpoint with a bounded timeout, caches the last
 * successful fetch (value + local wall-clock timestamp) per mint under this instance's own state
 * directory. NEVER throws to its caller; every failure path returns a typed "no signal" result
 * ({ok:false}) that decideEngagement treats as skip. A fresh successful fetch is ALWAYS preferred
 * over a cached snapshot, regardless of the cached snapshot's age. If a fresh fetch fails, falls
 * back to the last local cache ONLY IF its local fetch timestamp is no older than
 * SOL_GATE_MAX_STALENESS_SEC; otherwise (or on cold start) returns {ok:false} -- fail-closed to
 * "skip", never a guessed/zero value.
 *
 * @param {string} mint
 * @param {{fetchImpl?: typeof fetch, endpoint?: string, timeoutMs?: number, cacheDir?: string,
 *          maxStalenessSec?: number, nowMs?: () => number}} [opts]
 */
export async function fetchSolMarketSignal(mint, opts = {}) {
  const {
    fetchImpl = globalThis.fetch,
    endpoint = process.env.SOL_GATE_PRICE_ENDPOINT || DEFAULT_ENDPOINT,
    timeoutMs = Number(process.env.SOL_GATE_FETCH_TIMEOUT_MS || DEFAULT_TIMEOUT_MS),
    cacheDir,
    maxStalenessSec,
    nowMs = Date.now,
  } = opts;

  const boundedTimeoutMs = Math.min(DEFAULT_TIMEOUT_MS, Number.isFinite(timeoutMs) ? timeoutMs : DEFAULT_TIMEOUT_MS);
  const cachePath = cacheDir ? path.join(cacheDir, `${mint}.json`) : null;

  let fresh = null;
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), boundedTimeoutMs);
    const url = `${endpoint}?ids=${encodeURIComponent(mint)}`;
    let res;
    try {
      res = await fetchImpl(url, { signal: controller.signal });
    } finally {
      clearTimeout(timer);
    }
    if (res && res.ok) {
      const json = await res.json();
      const entry = json && json[mint];
      const usdPrice = Number(entry && entry.usdPrice);
      const priceChange24h = Number(entry && entry.priceChange24h);
      const liquidity = Number(entry && entry.liquidity);
      if (Number.isFinite(usdPrice) && Number.isFinite(priceChange24h) && Number.isFinite(liquidity)) {
        fresh = { usdPrice, priceChange24h, liquidity, fetchedAtMs: nowMs() };
      }
    }
  } catch {
    fresh = null;
  }

  if (fresh) {
    if (cachePath) {
      try {
        fs.mkdirSync(path.dirname(cachePath), { recursive: true });
        fs.writeFileSync(cachePath, JSON.stringify(fresh));
      } catch {
        // fail-soft: a cache write failure never blocks returning the fresh signal.
      }
    }
    return { ok: true, source: "live", usdPrice: fresh.usdPrice, priceChange24h: fresh.priceChange24h, liquidity: fresh.liquidity, ageSec: 0 };
  }

  if (cachePath) {
    const cached = readJsonSafe(cachePath);
    if (cached && Number.isFinite(cached.fetchedAtMs)) {
      const ageSec = (nowMs() - cached.fetchedAtMs) / 1000;
      if (Number.isFinite(maxStalenessSec) && ageSec <= maxStalenessSec) {
        return {
          ok: true,
          source: "cache",
          usdPrice: Number(cached.usdPrice),
          priceChange24h: Number(cached.priceChange24h),
          liquidity: Number(cached.liquidity),
          ageSec,
        };
      }
    }
  }

  return { ok: false, source: "none", reason: "no-signal" };
}

/**
 * describeSignal({ momentumPct, liquidityUsd, conviction, mint }) — REQ-010 (HARD #0). Builds the
 * ONLY payload the pre-gate is allowed to contribute to franklin-trading's invocation context: a
 * FIXED set of raw observed numeric/descriptive fields, NEVER a directive string containing a
 * side, an action verb, a size, or an instruction to trade.
 */
export function describeSignal({ momentumPct, liquidityUsd, conviction, mint }) {
  return {
    observedMomentumPct: Number(momentumPct),
    observedLiquidityUsd: Number(liquidityUsd),
    observedConviction: Number(conviction),
    observedMint: String(mint),
  };
}
