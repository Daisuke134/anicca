const { verifyMessage } = require("ethers");
const nacl = require("tweetnacl");
const bs58 = require("bs58");
const { validate } = require("./telemetry-schema");

// CLIENT-SIDE format helper only. The verifier NEVER calls this on inbound data — it recovers the
// signer from the verbatim `message` bytes. Re-serializing would diverge across languages
// (JS JSON.stringify(5.0)==="5" but python json.dumps(5.0)==="5.0") and 401 every whole-number balance.
function canonicalMessage(p) {
  const m = {
    id: p.id, ts: p.ts, host: p.host, geo: p.geo, model_live: p.model_live,
    model_tier: p.model_tier, net_worth_usd: p.net_worth_usd, revenue_mo_usd: p.revenue_mo_usd,
    burn_day_usd: p.burn_day_usd, runway_days: p.runway_days, status: p.status,
  };
  // Additive leaderboard fields — appended ONLY when present so they are covered by the signature,
  // while base-only messages stay byte-identical (cross-language + back-compat preserved).
  if (p.chain !== undefined) m.chain = p.chain;
  if (p.tags !== undefined) m.tags = p.tags;
  if (p.revenue_today_usd !== undefined) m.revenue_today_usd = p.revenue_today_usd;
  if (p.revenue_by_source !== undefined) m.revenue_by_source = p.revenue_by_source;
  if (p.log_feed !== undefined) m.log_feed = p.log_feed;
  return JSON.stringify(m);
}

// Verifies the exact string the client signed. Parses it for schema + checks, but recovers the
// signer from `message` verbatim. ethers verifyMessage is synchronous in v6.
function verifyTelemetry(message, signature, ctx) {
  let raw;
  try { raw = JSON.parse(message); } catch { return { ok: false, reason: "bad_json" }; }
  const v = validate(raw);
  if (!v.ok) return v;
  const p = v.payload;
  if (p.ts > ctx.now + 5) return { ok: false, reason: "future" };
  if (ctx.now - p.ts > 60) return { ok: false, reason: "stale" };
  if (p.ts <= ctx.lastTs) return { ok: false, reason: "replay" };
  if (p.chain === "solana") {
    // ed25519 has no signature-recovery step (unlike ECDSA) — the claimed `id` IS the
    // verification key. base58 is case-sensitive: NEVER .toLowerCase()/.toUpperCase() here.
    let verified;
    try {
      const pub = bs58.decode(p.id);
      const sig = bs58.decode(signature);
      verified = nacl.sign.detached.verify(Buffer.from(message, "utf8"), sig, pub);
    } catch { return { ok: false, reason: "bad_signature" }; }
    if (!verified) return { ok: false, reason: "bad_signature" };
    return { ok: true, payload: p };
  }
  let signer;
  try { signer = verifyMessage(message, signature); } catch { return { ok: false, reason: "bad_signature" }; }
  if (signer.toLowerCase() !== p.id.toLowerCase()) return { ok: false, reason: "signer_mismatch" };
  return { ok: true, payload: p };
}

module.exports = { canonicalMessage, verifyTelemetry };
