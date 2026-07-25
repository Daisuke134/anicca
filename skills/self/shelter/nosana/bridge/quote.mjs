// quote.mjs — pure cost/worth-it evaluator for bridging idle USDC from Base to Solana. No I/O:
// every number here must already be real/fetched by the caller. Fails closed (worthIt: false) on
// any missing/non-finite input rather than silently treating an unfetchable gas price or fee quote
// as free — spec: "an unfetchable quote or gas price is never treated as zero cost."

export const DEFAULT_MAX_COST_FRACTION = 0.05; // refuse to call it "worth it" above 5% total cost
export const WEI_PER_ETH = 1_000_000_000_000_000_000n;

function isFiniteNonNegative(n) {
  return typeof n === "number" && Number.isFinite(n) && n >= 0;
}

function refuse(reason) {
  return { worthIt: false, netReceivedUsdc: null, costUsd: null, costFraction: null, reason };
}

/**
 * Pure: evaluate whether bridging `amountUsdc` USDC from Base to Solana is worth it, given real
 * gas/price/fee inputs. Always returns a fully-populated verdict (never throws) so a caller can
 * always log `reason`, including on refusal.
 *
 * @param {object} p
 * @param {number} p.amountUsdc — USDC amount being bridged. Treated 1:1 with USD (the peg is close
 *   enough at single-digit-dollar scale that a live USDC/USD price feed would add a network call
 *   for no material change to the verdict — see this feature's report for the observed real peg).
 * @param {bigint} p.gasUnitsApprove — gas units for the approve() call (0n if the allowance is
 *   already sufficient and no approve is needed).
 * @param {bigint} p.gasUnitsBurn — gas units for the depositForBurn() call. Must be positive —
 *   there is always a burn.
 * @param {number} p.baseGasPriceWei — real current Base gas price, wei/gas.
 * @param {number} p.ethUsdPrice — real current ETH/USD price.
 * @param {number} [p.l1FeeUsd] — Base L1 data-posting fee in USD, if measured/estimated separately
 *   from baseGasPriceWei (defaults to 0 — Base's L1 fee is a separate line item from L2 gas price,
 *   see this feature's report for a real measured example; 0 is only safe when the caller has
 *   confirmed it is genuinely negligible for the calldata size in question, not when it is simply
 *   unmeasured).
 * @param {number} [p.bridgeFeeBps] — protocol fee in basis points (0 for CCTP Standard Transfer,
 *   verified live; pass the real fetched value for any other route — never hardcode a nonzero fee
 *   from memory, per Circle's own "fees can change" warning).
 * @param {number} [p.solanaGasUsd] — destination-side gas cost estimate, in USD (0 if this run
 *   submits no Solana-side transaction at all).
 * @param {number} [p.maxCostFraction] — worth-it threshold: total cost / amountUsdc must be <= this.
 * @returns {{worthIt: boolean, netReceivedUsdc: number|null, costUsd: number|null, costFraction: number|null, reason: string}}
 */
export function evaluateBridgeQuote({
  amountUsdc,
  gasUnitsApprove,
  gasUnitsBurn,
  baseGasPriceWei,
  ethUsdPrice,
  l1FeeUsd = 0,
  bridgeFeeBps = 0,
  solanaGasUsd = 0,
  maxCostFraction = DEFAULT_MAX_COST_FRACTION,
} = {}) {
  if (!isFiniteNonNegative(amountUsdc) || amountUsdc <= 0) {
    return refuse("amountUsdc must be a positive finite number");
  }
  if (typeof gasUnitsApprove !== "bigint" || gasUnitsApprove < 0n) {
    return refuse("gasUnitsApprove must be a non-negative bigint (fail-closed — an unknown gas estimate is never free)");
  }
  if (typeof gasUnitsBurn !== "bigint" || gasUnitsBurn <= 0n) {
    return refuse("gasUnitsBurn must be a positive bigint (fail-closed — an unknown gas estimate is never free)");
  }
  if (!isFiniteNonNegative(baseGasPriceWei) || baseGasPriceWei <= 0) {
    return refuse("baseGasPriceWei is unavailable (fail-closed — an unfetchable gas price is never treated as zero cost)");
  }
  if (!isFiniteNonNegative(ethUsdPrice) || ethUsdPrice <= 0) {
    return refuse("ethUsdPrice is unavailable (fail-closed — an unfetchable price is never treated as zero cost)");
  }
  if (!isFiniteNonNegative(l1FeeUsd)) {
    return refuse("l1FeeUsd must be a non-negative finite number");
  }
  if (!isFiniteNonNegative(bridgeFeeBps)) {
    return refuse("bridgeFeeBps is unavailable (fail-closed — an unfetchable fee quote is never treated as zero cost)");
  }
  if (!isFiniteNonNegative(solanaGasUsd)) {
    return refuse("solanaGasUsd must be a non-negative finite number");
  }
  if (!isFiniteNonNegative(maxCostFraction) || maxCostFraction <= 0) {
    return refuse("maxCostFraction must be a positive finite number");
  }

  const gasUnitsTotal = gasUnitsApprove + gasUnitsBurn;
  const gasCostWei = gasUnitsTotal * BigInt(Math.round(baseGasPriceWei));
  const gasCostEth = Number(gasCostWei) / Number(WEI_PER_ETH);
  const gasCostUsd = gasCostEth * ethUsdPrice + l1FeeUsd;
  const bridgeFeeUsd = amountUsdc * (bridgeFeeBps / 10000);
  const costUsd = gasCostUsd + bridgeFeeUsd + solanaGasUsd;
  const netReceivedUsdc = amountUsdc - costUsd;
  const costFraction = costUsd / amountUsdc;

  if (netReceivedUsdc <= 0) {
    return {
      worthIt: false,
      netReceivedUsdc,
      costUsd,
      costFraction,
      reason: `total cost $${costUsd.toFixed(4)} would consume the entire $${amountUsdc} transfer`,
    };
  }
  if (costFraction > maxCostFraction) {
    return {
      worthIt: false,
      netReceivedUsdc,
      costUsd,
      costFraction,
      reason: `total cost $${costUsd.toFixed(4)} is ${(costFraction * 100).toFixed(2)}% of the $${amountUsdc} transfer — above the ${(maxCostFraction * 100).toFixed(1)}% worth-it threshold`,
    };
  }
  return {
    worthIt: true,
    netReceivedUsdc,
    costUsd,
    costFraction,
    reason: `total cost $${costUsd.toFixed(4)} (${(costFraction * 100).toFixed(3)}% of $${amountUsdc}) is within the ${(maxCostFraction * 100).toFixed(1)}% worth-it threshold`,
  };
}
