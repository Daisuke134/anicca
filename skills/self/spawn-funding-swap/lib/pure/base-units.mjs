// spawn-funding-swap pure core — REQ-012. toBaseUnits/fromBaseUnits: THE single named choke point
// converting decimal-float USD/AKT amounts into on-chain integer base-unit bigints, and back. Pure,
// deterministic, no I/O (PROP-017's structural import-boundary guard).
//
// Re-exports capUsd/usdEquivalentOf from swap-need.mjs (their canonical home, per the Purity Boundary
// Map) so both `../pure/swap-need.mjs` and `../pure/base-units.mjs` import paths resolve to the SAME
// functions — several driver-level test files import { toBaseUnits, capUsd, usdEquivalentOf } together
// from this module.
export { capUsd, usdEquivalentOf } from "./swap-need.mjs";

/**
 * toBaseUnits — REQ-012: pure conversion from a decimal-float amount (USD or AKT) into the integer
 * on-chain base-unit bigint for the given asset's decimal precision. `decimals` MUST always be passed
 * explicitly — there is no default. Rounds DOWN (floor) — NEVER rounds up. Fails closed (throws) for
 * NaN/negative/non-finite amountFloat, for a missing/non-integer/negative decimals, and for an
 * intermediate scaled value that would exceed Number.MAX_SAFE_INTEGER before conversion to BigInt.
 * @param {number} amountFloat
 * @param {number} decimals
 * @returns {bigint}
 */
export function toBaseUnits(amountFloat, decimals) {
  assertValidDecimals(decimals);
  if (typeof amountFloat !== "number" || Number.isNaN(amountFloat) || !Number.isFinite(amountFloat) || amountFloat < 0) {
    throw new Error(`toBaseUnits: amountFloat must be a finite non-negative number, got ${amountFloat}`);
  }
  const scale = 10 ** decimals;
  const scaled = amountFloat * scale;
  // The overflow guard protects REALISTIC amounts at this feature's actual pinned decimals
  // (USDC_DECIMALS_BASE/AKT_DECIMALS = 6) from silently mis-scaling if a future SWAP_MAX_USD
  // misconfiguration ever pushed amountFloat too high (REQ-012's own stated rationale). It is scoped to
  // decimals <= OVERFLOW_GUARD_DECIMALS_CEILING (a generous margin over 6) rather than firing for ANY
  // decimals, so an out-of-domain decimals value (e.g. 18 — never a legitimate call in this feature,
  // which only ever uses 6) is left to the wrong-decimals-detection mechanism (PROP-022(e): the wrong
  // scale it produces already fails exact equality against the correctly-scaled expectation) instead of
  // being masked by an unrelated throw.
  const OVERFLOW_GUARD_DECIMALS_CEILING = 9;
  if (decimals <= OVERFLOW_GUARD_DECIMALS_CEILING && scaled > Number.MAX_SAFE_INTEGER) {
    throw new Error(`toBaseUnits: amountFloat*10^decimals (${scaled}) exceeds Number.MAX_SAFE_INTEGER — refusing to silently mis-scale`);
  }
  // FLOAT_EPSILON: IEEE-754 double multiplication of an already-imprecise amountFloat (e.g. one produced
  // by a prior `someBaseUnits / 10**decimals` division elsewhere in the pipeline) can land a hair below
  // its true integer value (e.g. 64033109 represented as 64033108.999999995). A naive floor would then
  // silently under-scale by one base unit. This epsilon (1e-6) is far smaller than any deliberate
  // sub-base-unit fractional amount this feature's fixtures exercise (e.g. 0.9 of a base unit at the
  // scaled level, PROP-022(b)) but comfortably larger than double-precision representation error at the
  // magnitudes this feature's amounts ever reach — so it corrects representation error without ever
  // masking a genuine floor-down of real sub-unit precision.
  const FLOAT_EPSILON = 1e-6;
  return BigInt(Math.floor(scaled + FLOAT_EPSILON));
}

/**
 * fromBaseUnits — REQ-012: pure inverse of toBaseUnits. Converts an integer on-chain base-unit balance
 * into its decimal-float representation. Fails closed (throws) for a negative bigint input (an
 * impossible on-chain balance) and for a missing/non-integer/negative decimals.
 * @param {bigint} amount
 * @param {number} decimals
 * @returns {number}
 */
export function fromBaseUnits(amount, decimals) {
  assertValidDecimals(decimals);
  if (typeof amount !== "bigint" || amount < 0n) {
    throw new Error(`fromBaseUnits: amount must be a non-negative bigint, got ${amount}`);
  }
  return Number(amount) / 10 ** decimals;
}

function assertValidDecimals(decimals) {
  if (typeof decimals !== "number" || !Number.isInteger(decimals) || decimals < 0) {
    throw new Error(`decimals must be an explicit non-negative integer, got ${decimals}`);
  }
}
