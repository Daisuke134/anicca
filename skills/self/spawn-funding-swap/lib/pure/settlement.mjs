// spawn-funding-swap pure core — REQ-007. verifySettlement: the pure final on-chain settlement check.
// Pure, deterministic, no I/O (PROP-017's structural import-boundary guard).

/**
 * verifySettlement — REQ-007: accepts any postBalanceUakt - preBalanceUakt delta that is >=
 * quotedAmountOutUakt * (10000 - toleranceBps) / 10000, i.e. within toleranceBps basis points of the
 * route's quoted amount_out. All bigint math — no float-equivalent comparison.
 * @param {bigint} preBalanceUakt
 * @param {bigint} postBalanceUakt
 * @param {bigint} quotedAmountOutUakt
 * @param {number} toleranceBps
 * @returns {boolean}
 */
export function verifySettlement(preBalanceUakt, postBalanceUakt, quotedAmountOutUakt, toleranceBps) {
  const delta = postBalanceUakt - preBalanceUakt;
  const toleranceBpsBig = BigInt(toleranceBps);
  const minAcceptable = (quotedAmountOutUakt * (10_000n - toleranceBpsBig)) / 10_000n;
  return delta >= minAcceptable;
}
