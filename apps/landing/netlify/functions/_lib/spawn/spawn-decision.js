// effectiveDecision: the runner-level wrapper over the pure balance/rate/cap gate (spawn-gate.js).
// The gate alone is authoritative for AUTONOMOUS wakes — a broke parent NEVER spawns itself broke.
// A founder-authorized FIRST birth (force=true) may override ONLY the low_balance reason, so the colony's
// first child can be born to prove the pipeline LIVE end-to-end. The rate-limit and concurrency cap STILL
// bind even under force (you can never exceed maxChildren or spawn faster than the rate limit), so force
// can produce at most the single first child, never a runaway colony.
const { decideSpawn } = require("./spawn-gate.js");

function effectiveDecision({ balanceUsdc, children = [], now = Date.now(), force = false, minBalance = 20, maxChildren = 1, rateLimitDays = 14 } = {}) {
  const base = decideSpawn({ balanceUsdc, children, now, minBalance, maxChildren, rateLimitDays });
  if (base.eligible) return base;
  if (force && base.reason === "low_balance") {
    // re-run the gate with the balance constraint relaxed; if rate-limit/cap would still block, honor that.
    const relaxed = decideSpawn({ balanceUsdc: minBalance, children, now, minBalance, maxChildren, rateLimitDays });
    if (relaxed.eligible) return { eligible: true, reason: "forced_genesis_birth" };
    return relaxed; // rate_limited or max_children — force does not override these
  }
  return base;
}

module.exports = { effectiveDecision };
