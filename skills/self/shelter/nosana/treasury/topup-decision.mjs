// topup-decision.mjs — should Franklin buy more NOS for the shelter RIGHT NOW, and how much?
// Deliberately reuses funding/acquire-nos.mjs's own cap primitives (resolveSpendLamports,
// DEFAULT_MAX_SPEND_SOL, DEFAULT_MAX_SPEND_FRACTION_OF_BALANCE, DEFAULT_SOL_FEE_FLOOR_SOL,
// LAMPORTS_PER_SOL) instead of re-deriving a second, divergent cap engine — the existing funding
// refill logic (acquire-nos.mjs) was built for keeping the TRADING wallet topped up; this module is
// the missing "should we, for the SHELTER specifically, and how much" decision that sits in front of
// it. It never signs or sends anything itself — it returns a decision; acquireNos (already fully
// gated on its own quote/slippage/price-impact/floor checks) is what actually executes, and only
// when the caller separately passes --live to it (see bin/citizen-solvency).
//
// {allowed, reason} return shape mirrors spend-gate.mjs/acquire-nos.mjs's evaluateFundingGate
// exactly — same fail-closed idiom, not a new one.

import {
  resolveSpendLamports,
  DEFAULT_MAX_SPEND_SOL,
  DEFAULT_MAX_SPEND_FRACTION_OF_BALANCE,
  DEFAULT_SOL_FEE_FLOOR_SOL,
  LAMPORTS_PER_SOL,
} from "../funding/acquire-nos.mjs";

export { DEFAULT_MAX_SPEND_SOL, DEFAULT_MAX_SPEND_FRACTION_OF_BALANCE, DEFAULT_SOL_FEE_FLOOR_SOL, LAMPORTS_PER_SOL };

// Survival levels (survival-drive.mjs's evaluateSurvivalSignal output) that warrant considering a
// top-up. "unknown" is included deliberately — survival-drive.mjs's own fail-closed rule treats an
// unclassifiable runway as dangerous, not fine, and this module inherits that same direction: an
// unknown burn rate is never a reason to skip checking whether more NOS is warranted.
const LEVELS_NEEDING_TOPUP = new Set(["warning", "critical", "insolvent", "unknown"]);

/**
 * Pure: the top-up decision. `solBalanceLamports` and `floorLamports`/`feeReserveLamports` are all
 * in lamports so this composes directly with resolveSpendLamports's own units.
 *
 * @param {{
 *   survivalLevel: string,
 *   solBalanceLamports: number,
 *   requestedSol?: number,
 *   maxFraction?: number,
 *   floorLamports?: number,
 *   feeReserveLamports?: number,
 * }} opts
 * @returns {{allowed: boolean, reason: string, recommendedSpendLamports: number, recommendedSpendSol: number}}
 */
export function decideShelterTopUp({
  survivalLevel,
  solBalanceLamports,
  requestedSol = DEFAULT_MAX_SPEND_SOL,
  maxFraction = DEFAULT_MAX_SPEND_FRACTION_OF_BALANCE,
  floorLamports = Math.floor(DEFAULT_SOL_FEE_FLOOR_SOL * LAMPORTS_PER_SOL),
  feeReserveLamports = 0,
}) {
  if (!LEVELS_NEEDING_TOPUP.has(survivalLevel)) {
    return {
      allowed: false,
      reason: `survival level "${survivalLevel}" does not need a top-up — runway is healthy`,
      recommendedSpendLamports: 0,
      recommendedSpendSol: 0,
    };
  }
  if (typeof solBalanceLamports !== "number" || !Number.isFinite(solBalanceLamports) || solBalanceLamports < 0) {
    return {
      allowed: false,
      reason: "solBalanceLamports is unavailable (fail-closed) — refusing to recommend a top-up without a real balance",
      recommendedSpendLamports: 0,
      recommendedSpendSol: 0,
    };
  }
  if (typeof floorLamports !== "number" || !Number.isFinite(floorLamports) || floorLamports < 0) {
    return {
      allowed: false,
      reason: "floorLamports is invalid (fail-closed)",
      recommendedSpendLamports: 0,
      recommendedSpendSol: 0,
    };
  }
  if (typeof feeReserveLamports !== "number" || !Number.isFinite(feeReserveLamports) || feeReserveLamports < 0) {
    return {
      allowed: false,
      reason: "feeReserveLamports is invalid (fail-closed)",
      recommendedSpendLamports: 0,
      recommendedSpendSol: 0,
    };
  }

  const { spendLamports } = resolveSpendLamports({ requestedSol, solBalanceLamports, maxFraction });
  const headroomLamports = solBalanceLamports - floorLamports - feeReserveLamports;
  const safeSpendLamports = Math.max(0, Math.min(spendLamports, headroomLamports));

  if (safeSpendLamports <= 0) {
    return {
      allowed: false,
      reason:
        `survival level "${survivalLevel}" needs a top-up, but SOL balance ${(solBalanceLamports / LAMPORTS_PER_SOL).toFixed(9)} ` +
        `leaves no safe headroom above the fee floor ${(floorLamports / LAMPORTS_PER_SOL).toFixed(9)} SOL (+ reserve ` +
        `${(feeReserveLamports / LAMPORTS_PER_SOL).toFixed(9)} SOL) — refusing to recommend a swap that would strand the wallet (fail-closed)`,
      recommendedSpendLamports: 0,
      recommendedSpendSol: 0,
    };
  }

  return {
    allowed: true,
    reason:
      `survival level "${survivalLevel}" — recommending a top-up swap of ${(safeSpendLamports / LAMPORTS_PER_SOL).toFixed(9)} SOL ` +
      `(within the ${(maxFraction * 100).toFixed(0)}%-of-balance cap and above the fee floor)`,
    recommendedSpendLamports: safeSpendLamports,
    recommendedSpendSol: safeSpendLamports / LAMPORTS_PER_SOL,
  };
}
