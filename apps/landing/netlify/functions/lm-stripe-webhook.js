// lm-stripe-webhook.js — Stripe webhook for Life Manager (/lm) subscriptions ($20/mo, no trial).
// On checkout.session.completed → the session's client_reference_id is the lm_users uid (the /lm pay
// button appends ?client_reference_id=<uid> to the payment link) → set lm_users.paid=true. On
// customer.subscription.deleted → flip paid=false. Stripe signature is verified manually (no SDK):
// signed_payload = "<t>.<rawBody>", HMAC-SHA256 with STRIPE_LM_WEBHOOK_SECRET, compared to the v1 sig.
const crypto = require("crypto");
const WH_SECRET = process.env.STRIPE_LM_WEBHOOK_SECRET || "";
const STRIPE_SECRET = process.env.STRIPE_SECRET_KEY || "";
const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;

function verifyStripe(rawBody, sigHeader) {
  if (!WH_SECRET || !sigHeader) return false;
  const parts = Object.fromEntries(sigHeader.split(",").map((kv) => kv.split("=")));
  const t = parts.t, v1 = parts.v1;
  if (!t || !v1) return false;
  // Reject replays older than 5 minutes.
  if (Math.abs(Date.now() / 1000 - Number(t)) > 300) return false;
  const expected = crypto.createHmac("sha256", WH_SECRET).update(`${t}.${rawBody}`).digest("hex");
  const a = Buffer.from(v1), b = Buffer.from(expected);
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}

async function setPaid(uid, paid) {
  if (!SUPABASE_URL || !SUPABASE_KEY || !uid) return;
  await fetch(`${SUPABASE_URL}/rest/v1/lm_users?uid=eq.${encodeURIComponent(uid)}`, {
    method: "PATCH",
    headers: { apikey: SUPABASE_KEY, Authorization: `Bearer ${SUPABASE_KEY}`, "Content-Type": "application/json", Prefer: "return=minimal" },
    body: JSON.stringify({ paid, updated_at: new Date().toISOString() }),
  }).catch(() => {});
}

// For subscription.deleted we only have the customer/subscription id, not the uid → look up the uid
// via the original checkout session's client_reference_id.
async function uidForSubscription(subId) {
  if (!STRIPE_SECRET || !subId) return null;
  const r = await fetch(`https://api.stripe.com/v1/checkout/sessions?subscription=${encodeURIComponent(subId)}&limit=1`, {
    headers: { Authorization: `Bearer ${STRIPE_SECRET}` },
  });
  const j = await r.json().catch(() => ({}));
  const s = (j.data || [])[0];
  return s ? s.client_reference_id : null;
}

exports.handler = async (event) => {
  if (event.httpMethod !== "POST") return { statusCode: 405, body: "method not allowed" };
  const raw = event.body || "";
  if (!verifyStripe(raw, event.headers["stripe-signature"] || event.headers["Stripe-Signature"])) {
    return { statusCode: 400, body: "bad signature" };
  }
  let evt;
  try { evt = JSON.parse(raw); } catch { return { statusCode: 400, body: "bad json" }; }

  try {
    if (evt.type === "checkout.session.completed") {
      const uid = evt.data.object.client_reference_id;
      if (uid) await setPaid(uid, true);
    } else if (evt.type === "customer.subscription.deleted") {
      const uid = await uidForSubscription(evt.data.object.id);
      if (uid) await setPaid(uid, false);
    }
  } catch (e) {
    return { statusCode: 502, body: String(e) };
  }
  return { statusCode: 200, body: JSON.stringify({ received: true }) };
};
