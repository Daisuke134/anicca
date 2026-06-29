// Life Manager (/lm) — connect a user's Gmail via Composio (managed OAuth).
// GET ?uid=<lm_user_id> -> creates a Composio connection for user_id=uid against the
//   Gmail auth config, returns { redirect_url } for one-click Google consent, or
//   { connected:true } if an ACTIVE connection already exists. Mirrors calendar-connect.js
//   (the proven gcal connector) — same Composio v3 /connected_accounts flow, toolkit=gmail.
// No per-user OAuth app, no Google verification (Composio's app is verified).
const COMPOSIO_API = "https://backend.composio.dev/api/v3";
const COMPOSIO_KEY = process.env.COMPOSIO_API_KEY;
const GMAIL_AUTH_CONFIG = process.env.COMPOSIO_GMAIL_AUTH_CONFIG; // ac_… (Gmail auth config id)
const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
const crypto = require("crypto");
const LM_UID_SECRET = process.env.LM_UID_SECRET || "";
function verifyUid(uid, sig) {
  if (!LM_UID_SECRET || !uid || !sig) return false;
  const expected = crypto.createHmac("sha256", LM_UID_SECRET).update(uid).digest("base64url");
  const a = Buffer.from(String(sig));
  const b = Buffer.from(expected);
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}

exports.handler = async (event) => {
  if (!COMPOSIO_KEY || !GMAIL_AUTH_CONFIG) return { statusCode: 500, body: "missing composio config" };
  const q = event.queryStringParameters || {};
  const uid = q.uid;
  if (!uid) return { statusCode: 400, body: "missing uid" };
  if (!verifyUid(uid, q.sig)) return { statusCode: 403, body: "bad uid signature" };

  try {
    // Idempotent: if this user already has an ACTIVE Gmail connection, done.
    const existing = await fetch(
      `${COMPOSIO_API}/connected_accounts?user_ids=${encodeURIComponent(uid)}&toolkit_slugs=gmail`,
      { headers: { "x-api-key": COMPOSIO_KEY } });
    const ej = await existing.json();
    const active = (ej.items || []).find((i) => i.status === "ACTIVE");
    if (active) {
      await markProvider(uid);
      return { statusCode: 200, headers: { "Content-Type": "application/json" }, body: JSON.stringify({ connected: true }) };
    }
    // Status-only poll (the new-tab connect UI polls with &check=1): never mint a fresh OAuth.
    if (q.check) {
      return { statusCode: 200, headers: { "Content-Type": "application/json" }, body: JSON.stringify({ connected: false }) };
    }
    const r = await fetch(`${COMPOSIO_API}/connected_accounts`, {
      method: "POST",
      headers: { "x-api-key": COMPOSIO_KEY, "Content-Type": "application/json" },
      body: JSON.stringify({ auth_config: { id: GMAIL_AUTH_CONFIG }, connection: { user_id: uid } }),
    });
    const j = await r.json();
    const redirect = j.redirect_url || j.redirect_uri || j?.connectionData?.val?.redirectUrl;
    if (!redirect) return { statusCode: 502, body: JSON.stringify({ error: "no redirect", detail: j }) };
    await markProvider(uid);
    return { statusCode: 200, headers: { "Content-Type": "application/json" }, body: JSON.stringify({ redirect_url: redirect }) };
  } catch (e) {
    return { statusCode: 502, body: JSON.stringify({ error: String(e) }) };
  }
};

async function markProvider(uid) {
  if (!SUPABASE_URL || !SUPABASE_KEY) return;
  await fetch(`${SUPABASE_URL}/rest/v1/lm_users?uid=eq.${encodeURIComponent(uid)}`, {
    method: "PATCH",
    headers: {
      apikey: SUPABASE_KEY,
      Authorization: `Bearer ${SUPABASE_KEY}`,
      "Content-Type": "application/json",
      Prefer: "return=minimal",
    },
    body: JSON.stringify({ gmail_provider: "composio_gmail", updated_at: new Date().toISOString() }),
  }).catch(() => {});
}
