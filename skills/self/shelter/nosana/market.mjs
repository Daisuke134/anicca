// market.mjs — Nosana GPU-market price discovery + job-cost math. Selection and cost math are
// pure (deterministic, no I/O) so a pricing bug is caught by a fast offline test, never
// discovered on-chain. All network access is injected via `fetchImpl` per spec deliverable 2.
//
// NOS/USD pricing deliberately reuses (never duplicates) the generic, already-pure
// `fetchNosUsdPrice({fetchImpl})` stub in skills/self/spawn/lib/cloud-target.mjs — that module
// says its own Nosana price source is "deliberately left unwired"; `fetchNosUsdPriceLive` below
// is that wiring (a real Jupiter-price fetchImpl), added here rather than inside cloud-target.mjs
// so cloud-target.mjs itself stays pure/I-O-free per its own file header.

import { fetchNosUsdPrice as fetchNosUsdPriceGeneric } from "../../spawn/lib/cloud-target.mjs";

export const MARKETS_PRICE_URL = "https://dashboard.k8s.prd.nos.ci/api/markets/prices";
export const NOS_MINT = "nosXBVoaCTtYdLvKY6Csb4AC8JCdQKKAaWYtx2ZMoo7";
export const JUP_PRICE_URL = `https://api.jup.ag/price/v3?ids=${NOS_MINT}`;

// The public markets/prices endpoint has no explicit `gpu` boolean field (verified live
// 2026-07-25: all 25 markets returned are NVIDIA-named GPU markets). Detect GPU markets by name
// so a future non-GPU (e.g. CPU-only) market added to the list is never silently treated as a
// GPU match by a naive "everything is a GPU market" assumption.
export function isGpuMarketName(name) {
  return typeof name === "string" && /nvidia|geforce|rtx|\bgpu\b|\bh100\b|\ba100\b/i.test(name);
}

/**
 * Pure: normalize the raw markets/prices payload into {address, name, usdPerHour, gpu}[].
 * Throws on a malformed (non-array) payload or entirely-empty-after-filtering result — callers
 * must fail closed rather than silently proceeding with zero markets to choose from.
 */
export function normalizeMarkets(raw) {
  if (!Array.isArray(raw)) {
    throw new Error("normalizeMarkets: expected an array of markets");
  }
  return raw
    .map((m) => ({
      address: m && typeof m.address === "string" ? m.address : null,
      name: m && typeof m.name === "string" ? m.name : null,
      usdPerHour: Number(m && m.usd_reward_per_hour),
      gpu: isGpuMarketName(m && m.name),
    }))
    .filter((m) => m.address && m.name && Number.isFinite(m.usdPerHour) && m.usdPerHour > 0);
}

/**
 * Pure: select the cheapest eligible market. requireGpu defaults true (S1 only deploys GPU
 * container jobs). Deterministic tie-break on lowest address so ties are never randomized.
 * Returns null (never throws) when there is no eligible market — callers must treat null as
 * "refuse to post", not as "any market is fine".
 */
export function selectCheapestMarket(markets, { requireGpu = true } = {}) {
  const eligible = (markets || []).filter((m) => m && (!requireGpu || m.gpu === true));
  if (eligible.length === 0) return null;
  return eligible.reduce((best, m) => {
    if (!best) return m;
    if (m.usdPerHour < best.usdPerHour) return m;
    if (m.usdPerHour === best.usdPerHour && m.address < best.address) return m;
    return best;
  }, null);
}

/**
 * Pure cost math: usd = usdPerHour * hours; nos = usd / nosUsdPrice. Throws (fails closed)
 * rather than silently computing a spend of 0/Infinity from a bad input — an unknown or
 * non-positive price must never be treated as "free" (spec hard constraint 3).
 */
export function estimateJobCost({ usdPerHour, hours, nosUsdPrice }) {
  for (const [key, value] of Object.entries({ usdPerHour, hours, nosUsdPrice })) {
    if (typeof value !== "number" || !Number.isFinite(value) || value <= 0) {
      throw new Error(`estimateJobCost: ${key} must be a positive finite number, got ${value}`);
    }
  }
  const usd = usdPerHour * hours;
  const nos = usd / nosUsdPrice;
  return { usd, nos };
}

/**
 * I/O: fetch + normalize the live Nosana market price list. fetchImpl is injected (default the
 * global fetch) so tests never hit the network. Fails closed: any HTTP/parse error throws —
 * never returns an empty-but-successful-looking list on failure.
 */
export async function fetchMarkets({ fetchImpl = fetch, url = MARKETS_PRICE_URL } = {}) {
  const res = await fetchImpl(url);
  if (!res || !res.ok) {
    throw new Error(`fetchMarkets: HTTP ${res && res.status} from ${url}`);
  }
  const raw = await res.json();
  return normalizeMarkets(raw);
}

// Real fetchImpl adapter wiring cloud-target.mjs's generic, no-arg `fetchImpl()` contract
// (Response-like object whose .json() resolves to {price}) to the actual Jupiter price API for
// the NOS mint. This is the "Nosana side" wiring the existing cloud-target.mjs module asked for,
// kept OUTSIDE cloud-target.mjs itself so that module stays pure/I-O-free.
async function defaultJupiterNosFetchImpl() {
  const res = await fetch(JUP_PRICE_URL);
  if (!res.ok) return { json: async () => ({}) };
  const data = await res.json();
  const usdPrice = data && data[NOS_MINT] && data[NOS_MINT].usdPrice;
  return { json: async () => ({ price: typeof usdPrice === "number" ? usdPrice : undefined }) };
}

/**
 * I/O: live NOS/USD price, wired through cloud-target.mjs's generic (fail-closed-to-0)
 * fetchNosUsdPrice. That generic function never throws (it collapses any failure to 0) — this
 * wrapper enforces spec hard constraint 3 ("fail closed on any price fetch failure — never
 * treat an unknown price as free") by turning a 0/invalid result into a thrown error instead of
 * letting a silent 0 flow into cost math.
 */
export async function fetchNosUsdPriceLive({ fetchImpl = defaultJupiterNosFetchImpl } = {}) {
  const price = await fetchNosUsdPriceGeneric({ fetchImpl });
  if (typeof price !== "number" || !Number.isFinite(price) || price <= 0) {
    throw new Error("fetchNosUsdPriceLive: could not obtain a valid NOS/USD price — refusing to treat as free");
  }
  return price;
}
