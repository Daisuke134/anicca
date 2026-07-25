// cost.mjs — pure NOS cost math for EXTENDING an existing Nosana job. Deliberately does NOT
// re-fetch the live market price list (market.mjs's fetchMarkets) the way a fresh deploy does: a
// running job's per-second NOS price is already LOCKED IN and readable directly off the job's own
// account (`price`) — that locked price, not a possibly-different current market rate, is what
// the on-chain extend instruction actually charges. Re-deriving it from the market list would add
// an unnecessary network call and a source of drift (the cheapest market can change between the
// job's original post and the moment it needs renewing).
//
// Verified live 2026-07-25 against real job FHAjMnM1q3p5c5qCeFRjZLYEo12FUBesFPW8zvG5heAC (GET
// https://dashboard.k8s.prd.nos.ci/api/jobs/FHAjMnM1q3p5c5qCeFRjZLYEo12FUBesFPW8zvG5heAC):
// price=48 (raw NOS units), timeout=900s, usdRewardPerHour=0.043702677. Cross-check: 48 * 3600 /
// 10**NOS_DECIMALS = 0.1728 NOS/hour; at a NOS/USD price of ~$0.254 that is ~$0.0439/hour —
// matches the job's own usdRewardPerHour (0.0437) to within normal price-feed drift, confirming
// `price` is NOS-per-second in the mint's raw (10**-6) smallest-unit representation.

import { NOS_DECIMALS } from "../funding/acquire-nos.mjs";

export { NOS_DECIMALS };

/**
 * Pure: NOS cost (human units) of extending a job by `additionalSeconds` at its own locked-in
 * `pricePerSecond` (raw units, read directly off the job account — see job-lookup.mjs). Fails
 * closed on any non-positive/non-finite input — an unknown price is never treated as free.
 */
export function estimateExtendCostNos({ pricePerSecond, additionalSeconds }) {
  for (const [key, value] of Object.entries({ pricePerSecond, additionalSeconds })) {
    if (typeof value !== "number" || !Number.isFinite(value) || value <= 0) {
      throw new Error(`estimateExtendCostNos: ${key} must be a positive finite number, got ${value}`);
    }
  }
  return (pricePerSecond * additionalSeconds) / 10 ** NOS_DECIMALS;
}

/** Pure: USD-denominated cost for logging + spend-gate.mjs's USD-capped gate. Fails closed. */
export function estimateExtendCostUsd({ costNos, nosUsdPrice }) {
  for (const [key, value] of Object.entries({ costNos, nosUsdPrice })) {
    if (typeof value !== "number" || !Number.isFinite(value) || value <= 0) {
      throw new Error(`estimateExtendCostUsd: ${key} must be a positive finite number, got ${value}`);
    }
  }
  return costNos * nosUsdPrice;
}
