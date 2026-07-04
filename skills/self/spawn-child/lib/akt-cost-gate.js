// Pure Akash self-spawn READINESS gate (no I/O). This is NOT the "should we spawn" judgment — that
// stays with the calling agent (right-altitude prompt in SKILL.md: when to consider it, what to weigh).
// This is deterministic arithmetic only: does the current AKT balance cover the known cost of the
// funding+deploy sequence (ACT mint burn + gas reserve) plus a safety buffer?
//
// costAkt/bufferAkt come from config.json (spawn_cost_akt / buffer_akt), not hardcoded here — the
// caller reads config and passes numbers in. Threshold = costAkt + bufferAkt.
function computeSpawnGate({ balanceAkt, costAkt, bufferAkt = 0 } = {}) {
  if (typeof balanceAkt !== "number" || !Number.isFinite(balanceAkt) || balanceAkt < 0) {
    return { ready: false, reason: "invalid_balance", thresholdAkt: null, shortfallAkt: null };
  }
  if (typeof costAkt !== "number" || !Number.isFinite(costAkt) || costAkt < 0) {
    return { ready: false, reason: "invalid_cost", thresholdAkt: null, shortfallAkt: null };
  }
  const buffer = typeof bufferAkt === "number" && Number.isFinite(bufferAkt) && bufferAkt >= 0 ? bufferAkt : 0;
  const threshold = costAkt + buffer;

  if (balanceAkt >= threshold) {
    return { ready: true, reason: "ready", thresholdAkt: threshold, shortfallAkt: 0 };
  }
  // round to avoid float noise (e.g. 24.799999999999997 -> 24.8) while staying exact for the ledger.
  const shortfall = Math.round((threshold - balanceAkt) * 1e6) / 1e6;
  return { ready: false, reason: "insufficient_akt", thresholdAkt: threshold, shortfallAkt: shortfall };
}

module.exports = { computeSpawnGate };
