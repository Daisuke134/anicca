// Hand-rolled validator (matches repo style — fashion webhook validates inline; zod is not a dep).
// Returns { ok:true, payload } or { ok:false, reason:"schema" }.
function validate(o) {
  if (o === null || typeof o !== "object") return { ok: false, reason: "schema" };
  if (typeof o.id !== "string" || !/^0x[a-fA-F0-9]{40}$/.test(o.id)) return { ok: false, reason: "schema" };
  if (!Number.isInteger(o.ts) || o.ts <= 0) return { ok: false, reason: "schema" };
  for (const k of ["host", "geo", "model_live"]) {
    if (typeof o[k] !== "string" || o[k].length === 0) return { ok: false, reason: "schema" };
  }
  if (o.model_tier !== "frontier" && o.model_tier !== "free") return { ok: false, reason: "schema" };
  if (typeof o.net_worth_usd !== "number" || o.net_worth_usd < 0) return { ok: false, reason: "schema" };
  if (typeof o.revenue_mo_usd !== "number") return { ok: false, reason: "schema" };
  if (typeof o.burn_day_usd !== "number" || o.burn_day_usd < 0) return { ok: false, reason: "schema" };
  if (!Number.isInteger(o.runway_days) || o.runway_days < 0) return { ok: false, reason: "schema" };
  if (!["alive", "critical", "dead"].includes(o.status)) return { ok: false, reason: "schema" };
  // Additive optional fields (agents-at-arms leaderboard) — validated only when present (back-compat).
  if (o.tags !== undefined) {
    if (!Array.isArray(o.tags) || o.tags.some((t) => typeof t !== "string")) return { ok: false, reason: "schema" };
  }
  if (o.revenue_today_usd !== undefined) {
    if (typeof o.revenue_today_usd !== "number" || o.revenue_today_usd < 0 || o.revenue_today_usd > o.revenue_mo_usd) return { ok: false, reason: "schema" };
  }
  if (o.revenue_by_source !== undefined) {
    const s = o.revenue_by_source;
    if (typeof s !== "object" || s === null || Array.isArray(s) || Object.values(s).some((v) => typeof v !== "number" || v < 0)) return { ok: false, reason: "schema" };
  }
  if (o.log_feed !== undefined) {
    if (!Array.isArray(o.log_feed) || o.log_feed.some((x) => !x || typeof x.ts !== "number" || typeof x.line !== "string")) return { ok: false, reason: "schema" };
  }
  return { ok: true, payload: o };
}
module.exports = { validate };
