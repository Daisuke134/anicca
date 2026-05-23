// Anicca Alarm — subscriber profile read/save for the /alarm/setup dashboard.
// GET  ?session_id=cs_...  -> resolve Stripe session -> ensure subscriber_profiles row
//                            -> return { token, phone, wake_time, ics_url, home_address, stakeholders, locoUrl }
// POST { token, ics_url?, home_address?, home_lat?, home_lon?, wake_time?, stakeholders? }
//                            -> update that subscriber's row (authed by owntracks_token)
const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
const STRIPE_KEY = process.env.STRIPE_SECRET_KEY;

async function supa(method, path, body, extraHeaders) {
  const r = await fetch(`${SUPABASE_URL}/rest/v1/${path}`, {
    method,
    headers: {
      apikey: SUPABASE_KEY, Authorization: `Bearer ${SUPABASE_KEY}`,
      "Content-Type": "application/json", ...(extraHeaders || {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const txt = await r.text();
  try { return { ok: r.ok, data: JSON.parse(txt) }; } catch { return { ok: r.ok, data: txt }; }
}

function locoUrl(origin, token) {
  return `${origin}/.netlify/functions/loco-ingest?token=${token}`;
}

exports.handler = async (event) => {
  if (!SUPABASE_URL || !SUPABASE_KEY) return { statusCode: 500, body: "missing config" };
  const ORIGIN = (event.headers && (event.headers.origin || event.headers.Origin)) || "https://aniccaai.com";

  if (event.httpMethod === "GET") {
    const sid = (event.queryStringParameters || {}).session_id;
    if (!sid || !STRIPE_KEY) return { statusCode: 400, body: "missing session_id" };
    // resolve phone from the Stripe checkout session
    const sr = await fetch(`https://api.stripe.com/v1/checkout/sessions/${sid}`, {
      headers: { Authorization: `Bearer ${STRIPE_KEY}` },
    });
    const session = await sr.json();
    if (session.error) return { statusCode: 400, body: "invalid session" };
    const phone = session.metadata?.phone || session.customer_details?.phone;
    const wakeTime = session.metadata?.wakeTime || "07:00";
    if (!phone) return { statusCode: 400, body: "no phone on session" };
    // ensure a row exists (webhook may not have fired yet)
    await supa("POST", "subscriber_profiles?on_conflict=phone",
      { phone, wake_time: wakeTime, stripe_customer: session.customer, stripe_subscription: session.subscription, status: "active" },
      { Prefer: "resolution=merge-duplicates,return=minimal" });
    const { data } = await supa("GET",
      `subscriber_profiles?phone=eq.${encodeURIComponent(phone)}&select=owntracks_token,phone,wake_time,ics_url,home_address,stakeholders`);
    const row = Array.isArray(data) && data[0] ? data[0] : {};
    return {
      statusCode: 200, headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...row, locoUrl: row.owntracks_token ? locoUrl(ORIGIN, row.owntracks_token) : null }),
    };
  }

  if (event.httpMethod === "POST") {
    let b; try { b = JSON.parse(event.body || "{}"); } catch { return { statusCode: 400, body: "bad json" }; }
    if (!b.token) return { statusCode: 401, body: "missing token" };
    const patch = { updated_at: new Date().toISOString() };
    for (const k of ["ics_url", "home_address", "home_lat", "home_lon", "wake_time", "stakeholders"]) {
      if (b[k] !== undefined) patch[k] = b[k];
    }
    const { ok } = await supa("PATCH",
      `subscriber_profiles?owntracks_token=eq.${encodeURIComponent(b.token)}`, patch, { Prefer: "return=minimal" });
    return { statusCode: ok ? 200 : 500, headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ok }) };
  }

  return { statusCode: 405, body: "method not allowed" };
};
