// spawn-funding-swap pure core — REQ-003. checkSourceFunded: exact bigint-vs-bigint funding
// precondition (the live current blocker). Pure, deterministic, no I/O (PROP-017's structural
// import-boundary guard).

/**
 * checkSourceFunded — REQ-003: verifies the source wallet holds >= requiredBaseUnits of Base USDC AND
 * >= minGasWei of native Base gas. Exact bigint-vs-bigint comparisons (>=) on both dimensions — never a
 * float-equivalent comparison (the FIND-001/FIND-002 wrong-unit defect class this guards against).
 * @param {bigint} baseUsdcBalance
 * @param {bigint} baseGasBalance
 * @param {bigint} requiredBaseUnits
 * @param {bigint} minGasWei
 * @returns {boolean}
 */
export function checkSourceFunded(baseUsdcBalance, baseGasBalance, requiredBaseUnits, minGasWei) {
  return baseUsdcBalance >= requiredBaseUnits && baseGasBalance >= minGasWei;
}
