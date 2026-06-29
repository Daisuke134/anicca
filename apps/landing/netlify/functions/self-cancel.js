// Cloud Anicca self-cancels its subscription once its OWN wallet ≥ AUTO_CANCEL_USDC.
// POST { sub_id, token } where token = base64url(HMAC-SHA256(SELF_CANCEL_MASTER_SECRET, sub_id)).
// The token is PER-INSTANCE: derived from THIS sub_id and SCP'd into the instance's /opt/anicca.env
// at spawn (the MASTER secret never leaves the server). A leaked token can only cancel its OWN sub_id
// (the HMAC is bound to sub_id), so the blast radius is one instance. Cancels the Stripe sub + marks
// the owner self_funded so the deleted-webhook keeps the droplet. (P-auto-cancel.)
const crypto = require("crypto");
const stripe = require("stripe");
const owners = require("./_lib/owners-store");

function expectedToken(sub_id, master) {
  return crypto.createHmac("sha256", master).update(String(sub_id)).digest("base64url");
}

exports.handler = async (event, deps = {}) => {
  if (event.httpMethod !== "POST") return { statusCode: 405, body: "method not allowed" };
  const MASTER = process.env.SELF_CANCEL_MASTER_SECRET;
  const STRIPE_SECRET = process.env.STRIPE_SECRET_KEY;
  const SUPA_URL = process.env.SUPABASE_URL,
    SUPA_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!MASTER || !STRIPE_SECRET || !SUPA_URL || !SUPA_KEY) return { statusCode: 500, body: "missing env" };
  let body;
  try {
    body = JSON.parse(event.body || "{}");
  } catch {
    return { statusCode: 400, body: "bad json" };
  }
  const { sub_id, token } = body;
  if (!sub_id || !token) return { statusCode: 400, body: "missing sub_id/token" };
  const exp = expectedToken(sub_id, MASTER);
  const a = Buffer.from(String(token)),
    b = Buffer.from(exp);
  if (a.length !== b.length || !crypto.timingSafeEqual(a, b)) return { statusCode: 403, body: "bad token" };
  const _owners = deps.owners || owners;
  const stripeClient = deps.stripeClient || stripe(STRIPE_SECRET);
  const cfg = { url: SUPA_URL, key: SUPA_KEY };
  try {
    // mark FIRST so a racing customer.subscription.deleted sees self_funded and keeps the droplet.
    await _owners.markSelfFunded(sub_id, cfg);
    try {
      await stripeClient.subscriptions.cancel(sub_id); // ctx7 /stripe/stripe-node: v13+ .cancel (was .del)
    } catch (e) {
      // idempotent: an already-cancelled / missing sub is success (the instance may retry).
      const code = e && (e.code || (e.raw && e.raw.code));
      if (code === "resource_missing" || /cancel/i.test((e && e.message) || "")) {
        return { statusCode: 200, body: JSON.stringify({ ok: true, already: sub_id }) };
      }
      throw e; // real failure → 500 → the instance retries (markSelfFunded already idempotently set)
    }
    return { statusCode: 200, body: JSON.stringify({ ok: true, self_funded: sub_id }) };
  } catch (err) {
    console.error("self-cancel error:", err);
    return { statusCode: 500, body: `self-cancel error: ${err.message}` };
  }
};

module.exports.expectedToken = expectedToken;
