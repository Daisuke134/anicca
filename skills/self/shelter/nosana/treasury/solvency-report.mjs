// solvency-report.mjs — turns the joined solvency ledger (solvency-ledger.mjs) plus a real NOS
// balance and a real NOS/USD price into the two numbers survival-drive.mjs actually wants: a burn
// rate in NOS/hour and a runway in hours. Deliberately REUSES survival-drive.mjs's own
// computeRunwayHours/evaluateSurvivalSignal/formatRunway rather than re-deriving runway math a
// second time — this is what makes "does my runway agree with survival-drive's" true by
// construction whenever the two are fed the same nosBalance/nosPerHour, instead of two independent
// implementations that might quietly drift apart.
//
// Fail-closed rule for THIS module specifically: nosUsdPrice is required and must be a positive
// finite number — a missing/invalid price is refused (thrown), never defaulted to some historical
// value or silently treated as "so cheap it's free". Same for nosBalance. This mirrors
// funding/acquire-nos.mjs's fetchMintUsdPrice, which already refuses to return an invalid price;
// this module refuses to CONSUME one.

import { computeRunwayHours, evaluateSurvivalSignal, formatRunway, DEFAULT_RUNWAY_WARNING_HOURS, DEFAULT_RUNWAY_CRITICAL_HOURS } from "../renew/survival-drive.mjs";

function requirePositiveFinite(name, value) {
  if (typeof value !== "number" || !Number.isFinite(value) || value <= 0) {
    throw new Error(`computeSolvencyReport: ${name} must be a positive finite number, got ${value} — fail-closed, refusing to guess`);
  }
}

/**
 * Pure: the full solvency report. `ledger` is solvency-ledger.mjs's buildSolvencyLedger(...) output.
 *
 * Two runway figures are always both computed, never just one, so a caller can never accidentally
 * present an optimistic revenue-adjusted number as if it were the conservative one:
 *   - runwayHoursBurnOnly: ignores revenue entirely — "how long do we last if nothing more comes
 *     in". This is the number survival-drive-style alerting (evaluateSurvivalSignal) is run
 *     against — deliberately conservative: proven-zero or unproven revenue must never soften the
 *     alert level (spec: "must be explicit when revenue is zero rather than dividing by it and
 *     emitting nonsense").
 *   - runwayHoursWithRevenue: nets revenue against burn. `Infinity` (never a thrown error, never a
 *     fabricated large-but-finite number) when revenue-per-hour already covers or exceeds burn —
 *     computeRunwayHours itself refuses a non-positive nosPerHour, so a non-positive NET burn is
 *     handled here explicitly rather than forced through that guard.
 *
 * When the ledger has no cost data at all (`ledger.noCostData`), the burn rate is UNKNOWN, not
 * zero — burnNosPerHour/runwayHoursBurnOnly are `null` and the survival level comes back "unknown"
 * (survival-drive.mjs's own fail-closed direction: an unknown burn rate is never read as "safe").
 */
export function computeSolvencyReport({
  ledger,
  nosBalance,
  nosUsdPrice,
  warningHours = DEFAULT_RUNWAY_WARNING_HOURS,
  criticalHours = DEFAULT_RUNWAY_CRITICAL_HOURS,
}) {
  if (!ledger || typeof ledger !== "object") {
    throw new Error("computeSolvencyReport: ledger is required");
  }
  requirePositiveFinite("nosUsdPrice", nosUsdPrice);
  if (typeof nosBalance !== "number" || !Number.isFinite(nosBalance) || nosBalance < 0) {
    throw new Error(`computeSolvencyReport: nosBalance must be a non-negative finite number, got ${nosBalance} — fail-closed`);
  }

  let burnNosPerHour = null;
  let runwayHoursBurnOnly = null;
  let survivalSignal;
  if (ledger.noCostData) {
    survivalSignal = {
      level: "unknown",
      promoteEarning: true,
      reason: "no shelter-cost ledger data in this window — burn rate is unknown, not zero (fail-closed)",
    };
  } else {
    burnNosPerHour = ledger.burnUsdPerHour / nosUsdPrice;
    runwayHoursBurnOnly = computeRunwayHours({ nosBalance, nosPerHour: burnNosPerHour });
    survivalSignal = evaluateSurvivalSignal({ runwayHours: runwayHoursBurnOnly, warningHours, criticalHours });
  }

  let runwayHoursWithRevenue = null;
  let netNosPerHour = null;
  if (burnNosPerHour !== null) {
    netNosPerHour = (ledger.burnUsdPerHour - ledger.revenueUsdPerHour) / nosUsdPrice;
    runwayHoursWithRevenue = netNosPerHour > 0 ? computeRunwayHours({ nosBalance, nosPerHour: netNosPerHour }) : Infinity;
  }

  return {
    nosBalance,
    nosUsdPrice,
    burnUsdPerHour: ledger.burnUsdPerHour,
    revenueUsdPerHour: ledger.revenueUsdPerHour,
    netUsdPerHour: ledger.netUsdPerHour,
    burnNosPerHour,
    netNosPerHour,
    runwayHoursBurnOnly,
    runwayBurnOnly: runwayHoursBurnOnly === null ? null : formatRunway(runwayHoursBurnOnly),
    runwayHoursWithRevenue,
    runwayWithRevenue:
      runwayHoursWithRevenue === null || runwayHoursWithRevenue === Infinity
        ? runwayHoursWithRevenue === Infinity
          ? { days: Infinity, hours: Infinity, totalHours: Infinity }
          : null
        : formatRunway(runwayHoursWithRevenue),
    survivalSignal,
    revenueIsZero: ledger.totalExternalRevenueUsd === 0,
    noCostData: Boolean(ledger.noCostData),
    noRevenueData: Boolean(ledger.noRevenueData),
  };
}
