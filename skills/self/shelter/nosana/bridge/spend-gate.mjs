// spend-gate.mjs — pure money-safety gate for bridging USDC from Base to Solana. Reuses the SAME
// per-transfer/daily/cumulative cap engine ../spend-gate.mjs already defines for Nosana job spend
// (`checkSpendCaps`) instead of re-expressing cap math a third time — that function is already
// generic over `{amountUsd, history, config, nowTs}` and does not know or care what the spend is
// for. This module adds the two checks specific to bridging:
//   1. a small explicit per-bridge cap (spec: "cap this at a small explicit amount"), applied via
//      checkSpendCaps's existing `perJobUsdCap` field (re-purposed here as a per-bridge cap — same
//      semantics: "this one transfer must not exceed X").
//   2. refusing anything that would leave the Base wallet's ETH balance unable to cover a FUTURE
//      transaction's gas (spec: "refuse anything that would leave the Base wallet unable to pay
//      gas for a future transaction"). This is deliberately distinct from
//      funding/acquire-nos.mjs's post-swap SOL floor: that one guards the SAME wallet's
//      native-token reserve on the SAME chain after a SOL-denominated swap; this one guards Base
//      ETH specifically, which the bridge spends only for gas (never for the USDC amount itself).

import { checkSpendCaps } from "../spend-gate.mjs";

// A bit above the ~$10 idle balance this feature exists to move — a deliberately small ceiling,
// not a blank check. Overridable by the caller (bin/citizen-bridge wires env NOSANA_BRIDGE_MAX_USD).
export const DEFAULT_MAX_BRIDGE_USD = 15;

// 0.000002 ETH — roughly 2x this feature's own real measured+estimated gas cost for one
// approve+depositForBurn pair at the Base gas price observed 2026-07-25 (see this feature's
// report). Kept as a hard floor so a bridge never leaves the wallet unable to pay for a second,
// unrelated future Base transaction.
export const DEFAULT_FUTURE_GAS_RESERVE_WEI = 2_000_000_000_000n;

function isFiniteNonNegativeNumber(n) {
  return typeof n === "number" && Number.isFinite(n) && n >= 0;
}

/**
 * Pure: the combined preflight gate the bridge orchestrator consults before any spend. Fails
 * closed on any missing/non-finite balance/estimate rather than treating "unknown" as "safe".
 *
 * @param {object} p
 * @param {number} p.amountUsdc
 * @param {bigint} p.ethBalanceWei — real current Base ETH balance.
 * @param {bigint} p.gasCostWeiEstimate — real estimated total gas cost (approve + burn) for THIS bridge.
 * @param {bigint} [p.futureGasReserveWei]
 * @param {Array}  [p.history] — prior bridge spend rows, shape `{ts, amountUsd, status, txHash}` —
 *   the exact shape checkSpendCaps already expects.
 * @param {object} [p.config] — `{perBridgeUsdCap, dailyUsdCap, cumulativeUsdCap}`, all optional.
 * @param {number} p.nowTs — epoch seconds.
 * @returns {{allowed: boolean, reason: string}}
 */
export function evaluateBridgeGate({
  amountUsdc,
  ethBalanceWei,
  gasCostWeiEstimate,
  futureGasReserveWei = DEFAULT_FUTURE_GAS_RESERVE_WEI,
  history = [],
  config = {},
  nowTs,
}) {
  if (!isFiniteNonNegativeNumber(amountUsdc) || amountUsdc <= 0) {
    return { allowed: false, reason: "amountUsdc must be a positive finite number" };
  }
  if (typeof nowTs !== "number" || !Number.isFinite(nowTs)) {
    return { allowed: false, reason: "nowTs must be a finite number (epoch seconds)" };
  }

  const effectiveConfig = {
    perJobUsdCap: config.perBridgeUsdCap ?? DEFAULT_MAX_BRIDGE_USD,
    dailyUsdCap: config.dailyUsdCap ?? null,
    cumulativeUsdCap: config.cumulativeUsdCap ?? null,
  };
  const capDecision = checkSpendCaps({ amountUsd: amountUsdc, history, config: effectiveConfig, nowTs });
  if (!capDecision.allowed) {
    return { allowed: false, reason: capDecision.reason };
  }

  if (typeof ethBalanceWei !== "bigint" || ethBalanceWei < 0n) {
    return { allowed: false, reason: "ethBalanceWei is unavailable (fail-closed)" };
  }
  if (typeof gasCostWeiEstimate !== "bigint" || gasCostWeiEstimate <= 0n) {
    return { allowed: false, reason: "gasCostWeiEstimate is unavailable (fail-closed — an unknown gas cost is never free)" };
  }
  if (typeof futureGasReserveWei !== "bigint" || futureGasReserveWei < 0n) {
    return { allowed: false, reason: "futureGasReserveWei must be a non-negative bigint" };
  }

  if (gasCostWeiEstimate > ethBalanceWei) {
    return {
      allowed: false,
      reason: `estimated gas cost ${gasCostWeiEstimate} wei exceeds the Base wallet's ETH balance ${ethBalanceWei} wei — cannot even afford this bridge`,
    };
  }

  const postGasWei = ethBalanceWei - gasCostWeiEstimate;
  if (postGasWei < futureGasReserveWei) {
    return {
      allowed: false,
      reason: `after this bridge's gas (${gasCostWeiEstimate} wei), the Base wallet would have ${postGasWei} wei left — below the ${futureGasReserveWei} wei reserved for a future transaction's gas`,
    };
  }

  return { allowed: true, reason: "within caps and leaves enough ETH for a future transaction's gas" };
}
