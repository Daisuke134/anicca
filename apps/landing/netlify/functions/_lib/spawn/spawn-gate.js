// Deterministic spawn gate (pure). spec27b. Order: balance -> rate-limit -> cap.
// A broke parent NEVER spawns whatever else is true (own survival first).
const DAY_MS = 86400 * 1000;

function decideSpawn({ balanceUsdc, children = [], now = Date.now(), minBalance = 20, maxChildren = 1, rateLimitDays = 14 } = {}) {
  if (!(Number(balanceUsdc) >= minBalance)) return { eligible: false, reason: "low_balance" };

  const recent = children.some((c) => {
    const ms = Number(c && c.spawned_ms);
    return Number.isFinite(ms) && now - ms < rateLimitDays * DAY_MS;
  });
  if (recent) return { eligible: false, reason: "rate_limited" };

  if (children.length >= maxChildren) return { eligible: false, reason: "max_children" };

  return { eligible: true, reason: "eligible" };
}

module.exports = { decideSpawn };
