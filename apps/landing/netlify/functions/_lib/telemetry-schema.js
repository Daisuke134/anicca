// Hand-rolled validator (matches repo style — fashion webhook validates inline; zod is not a dep).
// Returns { ok:true, payload } or { ok:false, reason:"schema" }.
const BASE_ID_RE = /^0x[a-fA-F0-9]{40}$/;
// Base58 alphabet excludes 0/O/I/l (Bitcoin/Solana convention) to avoid visual ambiguity.
const SOLANA_ID_RE = /^[1-9A-HJ-NP-Za-km-z]{32,44}$/;

function validate(o) {
  if (o === null || typeof o !== "object") return { ok: false, reason: "schema" };
  const chain = o.chain === undefined ? "base" : o.chain;
  // "polygon" = same EIP-191/secp256k1 signature scheme as "base" (chain-agnostic across EVM
  // networks — only the RPC target used for balance verification differs, see chain-reader.js).
  // "polygon-proxy" = signed by a DELEGATE identity that is deliberately NOT the funds-holding
  // address (e.g. a Polymarket ERC-1167 proxy wallet, which has no private key of its own and
  // cannot produce an EIP-191 signature — see claude-p, 2026-07-05). Same id-shape/signature rules
  // as "base", but dashboard-sync.js intentionally wires NO reader for it, so it is always
  // net_worth_src="unverified" until real EIP-1271 (proxy-signature) verification exists — honest,
  // never a false "chain"-verified figure for an address that was never actually checked.
  if (chain !== "base" && chain !== "solana" && chain !== "polygon" && chain !== "polygon-proxy") return { ok: false, reason: "schema" };
  if (typeof o.id !== "string") return { ok: false, reason: "schema" };
  if (chain === "solana") {
    if (!SOLANA_ID_RE.test(o.id)) return { ok: false, reason: "schema" };
  } else if (!BASE_ID_RE.test(o.id)) return { ok: false, reason: "schema" };
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
  // Additive optional fields (agents-at-arms leaderboard) — validated only when present (back-compat).
  if (o.tags !== undefined) {
    if (!Array.isArray(o.tags) || o.tags.some((t) => typeof t !== "string")) return { ok: false, reason: "schema" };
  }
  if (o.revenue_today_usd !== undefined) {
    if (typeof o.revenue_today_usd !== "number" || o.revenue_today_usd < 0 || o.revenue_today_usd > o.revenue_mo_usd) return { ok: false, reason: "schema" };
  }
  if (o.revenue_by_source !== undefined) {
    // Per-source PnL — can be NEGATIVE (loss / drawdown / mark-to-market). Only reject non-numbers /
    // non-finite values. Verified against live production 2026-07-04 (row 0xa3cd… had
    // bluechip:-0.433, aave:-0.005 — real losses). Sprint-1 tests were positive-only fixtures.
    const s = o.revenue_by_source;
    if (typeof s !== "object" || s === null || Array.isArray(s) || Object.values(s).some((v) => typeof v !== "number" || !Number.isFinite(v))) return { ok: false, reason: "schema" };
  }
  if (o.log_feed !== undefined) {
    if (!Array.isArray(o.log_feed) || o.log_feed.some((x) => !x || typeof x.ts !== "number" || typeof x.line !== "string")) return { ok: false, reason: "schema" };
  }
  return { ok: true, payload: o };
}
module.exports = { validate, BASE_ID_RE, SOLANA_ID_RE };
