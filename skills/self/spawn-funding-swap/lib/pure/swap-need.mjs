// spawn-funding-swap pure core — REQ-001, REQ-006, REQ-011. computeSwapNeed / usdEquivalentOf / capUsd.
// Pure, deterministic, no filesystem/subprocess/network-module/fetch imports permitted here
// (PROP-017's structural import-boundary guard).
import { SWAP_MAX_USD } from "./constants.mjs";

/**
 * computeSwapNeed — REQ-001: how much AKT (if any) must be acquired. Never over-buys at or above the
 * threshold boundary; never negative.
 * @param {number} current - current AKT balance (decimal float, already run through fromBaseUnits)
 * @param {number} threshold - target AKT balance
 * @returns {number} the AKT shortfall, clamped to 0 when current >= threshold
 */
export function computeSwapNeed(current, threshold) {
  return Math.max(0, threshold - current);
}

/**
 * usdEquivalentOf — REQ-011: pure conversion of an AKT shortfall into its USD equivalent, given a price
 * supplied by the effectful PriceOracle. Fails closed (throws) for a non-positive/non-finite price —
 * NEVER an unbounded/NaN/negative pass-through (PROP-018).
 * @param {number} needAkt
 * @param {number} aktUsdPrice
 * @returns {number}
 */
export function usdEquivalentOf(needAkt, aktUsdPrice) {
  if (!Number.isFinite(aktUsdPrice) || aktUsdPrice <= 0) {
    throw new Error(`usdEquivalentOf: aktUsdPrice must be a finite positive number, got ${aktUsdPrice}`);
  }
  return needAkt * aktUsdPrice;
}

/**
 * capUsd — REQ-006: hard-clamp of the USD amount to spend to min(requestedUsd, SWAP_MAX_USD).
 * SWAP_MAX_USD is a literal constant in constants.mjs, NEVER read from process.env/CLI/genome/config —
 * this function itself never reads process.env, so a hostile override has zero effect (PROP-012).
 * Adversarial inputs (NaN, negative) resolve to an explicit fail-closed 0, never an unbounded pass-
 * through; Infinity caps at SWAP_MAX_USD (PROP-011).
 * @param {number} requestedUsd
 * @returns {number}
 */
export function capUsd(requestedUsd) {
  // NaN and negative values fail closed to 0 (never an unbounded/negative pass-through). Infinity is
  // NOT excluded here — it falls through to Math.min below, which correctly clamps it to SWAP_MAX_USD.
  if (Number.isNaN(requestedUsd) || requestedUsd < 0) return 0;
  return Math.min(requestedUsd, SWAP_MAX_USD);
}
