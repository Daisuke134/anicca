export const MONEY_TRUTH_RECONCILE_INTERVAL_MS = 15 * 60 * 1000;

/** Pure cadence gate for the optional resident receipt reconciler. */
export function shouldReconcile({
  enabled,
  lastRunMs,
  nowMs,
  intervalMs = MONEY_TRUTH_RECONCILE_INTERVAL_MS,
} = {}) {
  if (enabled !== "1") return false;
  if (!Number.isFinite(Number(nowMs)) || !Number.isFinite(Number(intervalMs)) || Number(intervalMs) <= 0) return false;
  if (!Number.isFinite(Number(lastRunMs)) || Number(lastRunMs) <= 0) return true;
  return Number(nowMs) - Number(lastRunMs) >= Number(intervalMs);
}

