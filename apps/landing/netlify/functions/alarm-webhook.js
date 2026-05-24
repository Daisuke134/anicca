// Anicca Alarm — Stripe webhook -> provision/cancel the daily wake-up call.
// On subscription checkout completion, store {phone, wakeTime, customer, subscription}
// into Supabase `alarm_subscribers`. On cancellation, mark canceled.
// The Mac-mini per-user scheduler reads this table and calls each subscriber daily.
const Stripe = require("stripe");

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;

async function supa(method, path, body) {
  const r = await fetch(`${SUPABASE_URL}/rest/v1/${path}`, {
    method,
    headers: {
      apikey: SUPABASE_KEY,
      Authorization: `Bearer ${SUPABASE_KEY}`,
      "Content-Type": "application/json",
      Prefer: "resolution=merge-duplicates,return=minimal",
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  return r.ok;
}

exports.handler = async (event) => {
  const STRIPE_KEY = process.env.STRIPE_SECRET_KEY;
  const WH_SECRET = process.env.STRIPE_ALARM_WEBHOOK_SECRET;
  if (!STRIPE_KEY || !WH_SECRET || !SUPABASE_URL || !SUPABASE_KEY) {
    return { statusCode: 500, body: "missing config" };
  }
  const stripe = Stripe(STRIPE_KEY);
  const sig = event.headers["stripe-signature"] || event.headers["Stripe-Signature"];

  let evt;
  try {
    const raw = event.isBase64Encoded ? Buffer.from(event.body, "base64") : event.body;
    evt = stripe.webhooks.constructEvent(raw, sig, WH_SECRET);
  } catch (e) {
    return { statusCode: 400, body: `bad signature: ${e.message}` };
  }

  try {
    if (evt.type === "checkout.session.completed") {
      const s = evt.data.object;
      const phone = s.metadata?.phone || s.customer_details?.phone;
      const wakeTime = s.metadata?.wakeTime || "07:00";
      if (phone) {
        // upsert into the unified subscriber_profiles (wake + never-late share one row)
        await supa("POST", "subscriber_profiles?on_conflict=phone", {
          phone, wake_time: wakeTime, name: s.metadata?.name || null, email: s.customer_details?.email || null,
          stripe_customer: s.customer, stripe_subscription: s.subscription,
          status: "active", updated_at: new Date().toISOString(),
        });
      }
    } else if (evt.type === "customer.subscription.deleted") {
      const sub = evt.data.object;
      await supa("PATCH", `subscriber_profiles?stripe_subscription=eq.${sub.id}`,
        { status: "canceled", updated_at: new Date().toISOString() });
    }
  } catch (e) {
    return { statusCode: 500, body: `handler error: ${e.message}` };
  }
  return { statusCode: 200, body: JSON.stringify({ received: true }) };
};
