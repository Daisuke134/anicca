// telemetry-msg.mjs — the SIGNED telemetry message shape, as a PURE side-effect-free builder so it can
// be unit-tested (key-safety + shape) WITHOUT importing the poster (which posts on import). The poster
// computes the values (net worth, revenue, log, identity) and calls this to produce the exact bytes it signs.
// This is the contract with the receiver (telemetry-verify/schema). Keep the key-set = the schema allowlist.

// The exact, fixed key-set of the signed message. The poster must never add a secret-bearing key.
export const MSG_KEYS = [
  "id", "ts", "host", "geo", "funding", "env", "brain", "model_live", "model_tier",
  "net_worth_usd", "daily_revenue_usd", "monthly_revenue_usd", "revenue_by_source",
  "revenue_mo_usd", "burn_day_usd", "runway_days", "status", "breakdown", "log",
];

// Returns { obj, msg } — obj is the message object, msg is JSON.stringify(obj) = the verbatim bytes to sign.
export function buildTelemetryMsg(p) {
  const obj = {
    id: String(p.id).toLowerCase(),
    ts: p.ts,
    host: p.host,
    geo: p.geo || "JP",
    funding: p.funding,
    env: p.env,
    brain: p.brain,
    model_live: p.model_live,
    model_tier: p.model_tier,
    net_worth_usd: p.net_worth_usd,
    daily_revenue_usd: p.daily_revenue_usd,
    monthly_revenue_usd: p.monthly_revenue_usd,
    revenue_by_source: p.revenue_by_source,
    revenue_mo_usd: p.monthly_revenue_usd, // back-compat: old field carries monthly revenue
    burn_day_usd: p.burn_day_usd,
    runway_days: p.runway_days ?? 999,
    status: p.status || "alive",
    breakdown: p.breakdown,
    log: p.log,
  };
  return { obj, msg: JSON.stringify(obj) };
}
