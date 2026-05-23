// Anicca Alarm — Stripe Checkout (subscription) creator.
// POST { phone, wakeTime } -> { url } (Stripe-hosted checkout).
// phone + wakeTime ride along as subscription metadata so the success webhook
// can provision the user's daily wake-up call. No free trial.
exports.handler = async (event) => {
  if (event.httpMethod !== "POST") return { statusCode: 405, body: "method not allowed" };
  let body;
  try { body = JSON.parse(event.body || "{}"); } catch { return { statusCode: 400, body: "bad json" }; }

  const phone = String(body.phone || "").trim();
  const wakeTime = String(body.wakeTime || "07:00").trim();
  if (!/^\+?[0-9][0-9\s\-]{6,}$/.test(phone)) return { statusCode: 400, body: "invalid phone" };

  const STRIPE_KEY = process.env.STRIPE_SECRET_KEY;
  const PRICE = process.env.STRIPE_ALARM_PRICE_ID; // $9.99/mo recurring
  if (!STRIPE_KEY || !PRICE) return { statusCode: 500, body: "missing config" };

  const ORIGIN = (event.headers && (event.headers.origin || event.headers.Origin)) || "https://aniccaai.com";

  const params = new URLSearchParams();
  params.append("mode", "subscription");
  params.append("line_items[0][price]", PRICE);
  params.append("line_items[0][quantity]", "1");
  params.append("success_url", `${ORIGIN}/alarm/setup?session_id={CHECKOUT_SESSION_ID}`);
  params.append("cancel_url", `${ORIGIN}/alarm?canceled=1`);
  params.append("subscription_data[metadata][phone]", phone);
  params.append("subscription_data[metadata][wakeTime]", wakeTime);
  params.append("metadata[phone]", phone);
  params.append("metadata[wakeTime]", wakeTime);
  // collect their phone at checkout too (for receipts / verification)
  params.append("phone_number_collection[enabled]", "true");

  try {
    const r = await fetch("https://api.stripe.com/v1/checkout/sessions", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${STRIPE_KEY}`,
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: params.toString(),
    });
    const session = await r.json();
    if (session.error) return { statusCode: 500, body: JSON.stringify({ error: session.error.message }) };
    return {
      statusCode: 200,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: session.url }),
    };
  } catch (e) {
    return { statusCode: 500, body: JSON.stringify({ error: String(e) }) };
  }
};
