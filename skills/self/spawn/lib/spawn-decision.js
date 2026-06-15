// Pure spawn gate (no I/O). Decides whether a parent Anicca may birth a child this wake.
// Order: balance (own survival first) -> rate-limit -> concurrency cap.
// Returns { eligible:boolean, reason:"ok"|"low_balance"|"rate_limited"|"max_children" }.
const DAY_MS = 86400000;

function decideSpawn({
  balanceUsdc,
  children = [],
  nowMs = Date.now(),
  minBalanceUsdc = 20,
  rateLimitDays = 14,
  maxChildren = 1,
} = {}) {
  // Survival first: must be a real finite number >= threshold. "20"/NaN/negative => dormant.
  if (typeof balanceUsdc !== "number" || !Number.isFinite(balanceUsdc) || balanceUsdc < minBalanceUsdc) {
    return { eligible: false, reason: "low_balance" };
  }

  const windowStart = nowMs - rateLimitDays * DAY_MS;
  const spawnedRecently = children.some(
    (c) => typeof c.spawned_ms === "number" && Number.isFinite(c.spawned_ms) && c.spawned_ms >= windowStart
  );
  if (spawnedRecently) {
    return { eligible: false, reason: "rate_limited" };
  }

  if (children.length >= maxChildren) {
    return { eligible: false, reason: "max_children" };
  }

  return { eligible: true, reason: "ok" };
}

module.exports = { decideSpawn, DAY_MS };
