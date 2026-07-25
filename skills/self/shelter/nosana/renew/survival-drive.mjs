// survival-drive.mjs — the "how long can Franklin live" calculation (S3 of "agent financial
// independence"). Pure: given the wallet's real NOS balance and the current NOS/hour rent, compute
// remaining runway, and classify it against configured thresholds into a signal that earning work
// OUGHT to be promoted to top priority once runway gets short. Wiring that signal into an actual
// earn-lane priority system is explicitly OUT OF SCOPE here — this module only ever produces the
// signal; nothing in this file (or anywhere in renew/) schedules, triggers, or promotes earning
// work. bin/citizen-rent only logs the signal.
//
// The "fail closed" direction here is the OPPOSITE of spend-gate.mjs's money-safety fail-closed
// (which means "refuse to spend on uncertain data"). For a SURVIVAL SIGNAL, the safe direction is
// to over-warn: unknown/invalid runway data must never be read as "survival is fine" just because
// it could not be computed.

export const DEFAULT_RUNWAY_WARNING_HOURS = 48; // 2 days
export const DEFAULT_RUNWAY_CRITICAL_HOURS = 6;

/**
 * Pure: hours of runway left at the current burn rate. Fails closed (throws) on a non-finite or
 * non-positive nosPerHour (an unknown rent rate is never treated as "free forever") and on a
 * negative/non-finite nosBalance. A zero balance correctly yields zero runway, not an error.
 */
export function computeRunwayHours({ nosBalance, nosPerHour }) {
  if (typeof nosBalance !== "number" || !Number.isFinite(nosBalance) || nosBalance < 0) {
    throw new Error(`computeRunwayHours: nosBalance must be a non-negative finite number, got ${nosBalance}`);
  }
  if (typeof nosPerHour !== "number" || !Number.isFinite(nosPerHour) || nosPerHour <= 0) {
    throw new Error(`computeRunwayHours: nosPerHour must be a positive finite number, got ${nosPerHour}`);
  }
  return nosBalance / nosPerHour;
}

/** Pure: split total runway hours into whole days + remainder hours for human-readable logging. */
export function formatRunway(totalHours) {
  if (typeof totalHours !== "number" || !Number.isFinite(totalHours) || totalHours < 0) {
    throw new Error(`formatRunway: totalHours must be a non-negative finite number, got ${totalHours}`);
  }
  const days = Math.floor(totalHours / 24);
  const hours = totalHours - days * 24;
  return { days, hours, totalHours };
}

/**
 * Pure: classify runway into a level + a promoteEarning signal. Never throws — an executor that
 * cannot even classify a bad runway number must still emit SOMETHING actionable (level "unknown",
 * promoteEarning true) rather than produce no signal at all.
 */
export function evaluateSurvivalSignal({
  runwayHours,
  warningHours = DEFAULT_RUNWAY_WARNING_HOURS,
  criticalHours = DEFAULT_RUNWAY_CRITICAL_HOURS,
}) {
  if (typeof runwayHours !== "number" || !Number.isFinite(runwayHours)) {
    return {
      level: "unknown",
      promoteEarning: true,
      reason: "runway could not be computed — treating it as dangerous rather than assuming survival is fine",
    };
  }
  if (runwayHours <= 0) {
    return { level: "insolvent", promoteEarning: true, reason: `runway is exhausted (${runwayHours.toFixed(2)}h)` };
  }
  if (runwayHours <= criticalHours) {
    return {
      level: "critical",
      promoteEarning: true,
      reason: `runway ${runwayHours.toFixed(2)}h is at or below the critical threshold ${criticalHours}h`,
    };
  }
  if (runwayHours <= warningHours) {
    return {
      level: "warning",
      promoteEarning: true,
      reason: `runway ${runwayHours.toFixed(2)}h is at or below the warning threshold ${warningHours}h`,
    };
  }
  return {
    level: "nominal",
    promoteEarning: false,
    reason: `runway ${runwayHours.toFixed(2)}h is above the warning threshold ${warningHours}h`,
  };
}
