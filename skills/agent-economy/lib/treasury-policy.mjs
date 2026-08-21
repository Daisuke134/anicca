// treasury-policy.mjs — pure money-safety policy shared by future signers and compute adapters.

const GRADUATION_MULTIPLIER = 1.5;
const MIN_RUNWAY_DAYS = 30;
const finite = (value) => Number.isFinite(Number(value));
const round = (value) => Math.round(Number(value) * 1e6) / 1e6;

/** Liquid funds that may be spent after reserve and already-committed liabilities. */
export function computeSpendable({ liquidUsdc, reserveUsdc, committedUsdc = 0 } = {}) {
  if (!finite(liquidUsdc) || !finite(reserveUsdc) || !finite(committedUsdc)) return 0;
  if (Number(liquidUsdc) < 0 || Number(reserveUsdc) < 0 || Number(committedUsdc) < 0) return 0;
  return round(Math.max(0, Number(liquidUsdc) - Number(reserveUsdc) - Number(committedUsdc)));
}

/** Authorize one proposed spend without signing or broadcasting it. */
export function authorizeSpend({
  amountUsdc,
  liquidUsdc,
  reserveUsdc,
  committedUsdc = 0,
  sessionSpentUsdc = 0,
  sessionCapUsdc,
} = {}) {
  if (!finite(amountUsdc) || Number(amountUsdc) <= 0
    || !finite(liquidUsdc) || Number(liquidUsdc) < 0
    || !finite(reserveUsdc) || Number(reserveUsdc) < 0
    || !finite(committedUsdc) || Number(committedUsdc) < 0
    || !finite(sessionSpentUsdc) || Number(sessionSpentUsdc) < 0
    || !finite(sessionCapUsdc) || Number(sessionCapUsdc) <= 0) {
    return { allowed: false, reason: "invalid-input" };
  }
  const spendableUsdc = computeSpendable({ liquidUsdc, reserveUsdc, committedUsdc });
  const sessionRemainingUsdc = round(Number(sessionCapUsdc) - Number(sessionSpentUsdc));
  if (Number(amountUsdc) > spendableUsdc + Number.EPSILON) {
    return { allowed: false, reason: "reserve-floor", spendableUsdc, sessionRemainingUsdc };
  }
  if (Number(amountUsdc) > sessionRemainingUsdc + Number.EPSILON) {
    return { allowed: false, reason: "session-cap", spendableUsdc, sessionRemainingUsdc };
  }
  return {
    allowed: true,
    reason: "ok",
    spendableUsdc,
    sessionRemainingUsdc: round(sessionRemainingUsdc - Number(amountUsdc)),
  };
}

/** Proposed graduation gate: external net covers compute+shelter with margin and no human fuel. */
export function graduationGate({
  externalRealizedNet30d,
  computeCost30d,
  shelterCost30d,
  liquidRunwayDays,
  humanPaidInference30d,
} = {}) {
  if (!finite(externalRealizedNet30d) || !finite(computeCost30d) || !finite(shelterCost30d)
    || !finite(liquidRunwayDays) || !finite(humanPaidInference30d)
    || Number(externalRealizedNet30d) < 0 || Number(computeCost30d) < 0
    || Number(shelterCost30d) < 0 || Number(liquidRunwayDays) < 0
    || Number(humanPaidInference30d) < 0) {
    return { eligible: false, reason: "invalid-input", coverage: null };
  }
  if (Number(humanPaidInference30d) > 0) {
    return { eligible: false, reason: "human-paid-inference", coverage: null };
  }
  const totalCost = Number(computeCost30d) + Number(shelterCost30d);
  if (totalCost <= 0) return { eligible: false, reason: "insufficient-cost-data", coverage: null };
  const coverage = round(Number(externalRealizedNet30d) / totalCost);
  if (Number(liquidRunwayDays) < MIN_RUNWAY_DAYS) {
    return { eligible: false, reason: "insufficient-runway", coverage };
  }
  if (coverage < GRADUATION_MULTIPLIER) {
    return { eligible: false, reason: "insufficient-coverage", coverage };
  }
  return { eligible: true, reason: "ok", coverage };
}

