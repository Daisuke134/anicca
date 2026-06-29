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
  // Optional fleet-identity fields (backward compatible: absent is OK; if present must be a known enum).
  for (const [k, allowed] of [["funding", ["human", "self"]], ["env", ["local", "cloud"]], ["brain", ["claude-p", "proxy"]]]) {
    if (o[k] !== undefined && !allowed.includes(o[k])) return { ok: false, reason: "schema" };
  }
  return { ok: true, payload: o };
}
module.exports = { validate };
