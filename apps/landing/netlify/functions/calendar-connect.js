// Anicca Alarm — connect a subscriber's Google Calendar via Composio (managed OAuth).
// GET ?token=<owntracks_token>  -> creates a Composio connection for user_id=token
//   against the Google Calendar auth config, returns { redirect_url } for the
//   one-click Google consent. After consent, saas_lateness reads their events live.
// No ICS, no per-user OAuth app, no Google verification (Composio's app is verified).
const COMPOSIO_API = "https://backend.composio.dev/api/v3";
const COMPOSIO_KEY = process.env.COMPOSIO_API_KEY;
const GCAL_AUTH_CONFIG = process.env.COMPOSIO_GCAL_AUTH_CONFIG; // ac_FIvQ1FI9Dukl
const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
const LM_UID_SECRET = process.env.LM_UID_SECRET || "";
const crypto = require("crypto");

const json = (statusCode, value) => ({
  statusCode, headers: { "Content-Type": "application/json" }, body: JSON.stringify(value),
});

function verifyCalendarGrant(uid, query, expectedPurpose, nowSeconds = Math.floor(Date.now() / 1000)) {
  const purpose = String(query.purpose || "");
  const nonce = String(query.nonce || "");
  const exp = Number(query.exp);
  const sig = String(query.sig || "");
  if (!LM_UID_SECRET || !uid || purpose !== expectedPurpose || !Number.isInteger(exp) ||
      exp <= nowSeconds || exp > nowSeconds + 10 * 60 || !sig ||
      (purpose === "oauth" && !nonce) || (purpose === "status" && nonce)) return false;
  const canonical = `${uid}\ncalendar-connect:${purpose}\n${exp}\n${nonce}`;
  const expected = crypto.createHmac("sha256", LM_UID_SECRET).update(canonical).digest("base64url");
  const a = Buffer.from(sig);
  const b = Buffer.from(expected);
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}

async function claimOAuthNonce(uid, nonce, exp) {
  if (!SUPABASE_URL || !SUPABASE_KEY) return false;
  const nonceHash = crypto.createHash("sha256").update(nonce).digest("hex");
  const result = await fetch(`${SUPABASE_URL}/rest/v1/lm_calendar_connect_nonces`, {
    method: "POST",
    headers: {
      apikey: SUPABASE_KEY, Authorization: `Bearer ${SUPABASE_KEY}`,
      "Content-Type": "application/json", Prefer: "return=minimal",
    },
    body: JSON.stringify({
      uid, purpose: "oauth", nonce_hash: nonceHash,
      expires_at: new Date(exp * 1000).toISOString(),
    }),
  }).catch(() => null);
  return Boolean(result && result.status === 201);
}

async function supaGetTokenPhone(token) {
  const r = await fetch(
    `${SUPABASE_URL}/rest/v1/subscriber_profiles?owntracks_token=eq.${encodeURIComponent(token)}&select=phone`,
    { headers: { apikey: SUPABASE_KEY, Authorization: `Bearer ${SUPABASE_KEY}` } });
  const d = await r.json();
  return Array.isArray(d) && d[0] ? d[0].phone : null;
}

exports.handler = async (event) => {
  if (!COMPOSIO_KEY || !GCAL_AUTH_CONFIG) return { statusCode: 500, body: "missing composio config" };
  const qs = event.queryStringParameters || {};
  const token = qs.token;
  const uid = qs.uid;
  if (!token && !uid) return { statusCode: 400, body: "missing token or uid" };

  // Two callers, two stable ids:
  //   ?token=<owntracks_token> → Anicca Alarm (/install); Composio user_id = subscriber phone
  //     resolved from subscriber_profiles, and we mark that table.
  //   ?uid=<lm_user_id>        → Life Manager (/lm); Composio user_id = uid itself (the lm_users
  //     primary key), and we mark lm_users. No subscriber row exists for /lm users, so this branch
  //     must NOT go through subscriber_profiles (that path 404s for a raw uid).
  const isLm = !token && !!uid;
  if (isLm) {
    const expectedPurpose = qs.check ? "status" : "oauth";
    if (!verifyCalendarGrant(uid, qs, expectedPurpose)) return json(403, { error: "bad calendar signature" });
    if (expectedPurpose === "oauth" && !await claimOAuthNonce(uid, String(qs.nonce), Number(qs.exp))) {
      return json(403, { error: "calendar signature already used" });
    }
  }
  const userId = isLm ? uid : await supaGetTokenPhone(token);
  if (!userId) return { statusCode: 404, body: "subscriber not found" };

  // Marks the connecting/connected provider on whichever table owns this user.
  const markProvider = async () => {
    if (!SUPABASE_URL || !SUPABASE_KEY) return;
    const url = isLm
      ? `${SUPABASE_URL}/rest/v1/lm_users?uid=eq.${encodeURIComponent(uid)}`
      : `${SUPABASE_URL}/rest/v1/subscriber_profiles?owntracks_token=eq.${encodeURIComponent(token)}`;
    await fetch(url, {
      method: "PATCH",
      headers: { apikey: SUPABASE_KEY, Authorization: `Bearer ${SUPABASE_KEY}`, "Content-Type": "application/json", Prefer: "return=minimal" },
      body: JSON.stringify({ calendar_provider: "composio_gcal", updated_at: new Date().toISOString() }),
    }).catch(() => {});
  };

  try {
    // Idempotent: if this user already has an ACTIVE Google Calendar connection, done.
    const existing = await fetch(
      `${COMPOSIO_API}/connected_accounts?user_ids=${encodeURIComponent(userId)}&toolkit_slugs=googlecalendar`,
      { headers: { "x-api-key": COMPOSIO_KEY } });
    const ej = await existing.json();
    const active = (ej.items || []).find((i) => i.status === "ACTIVE");
    if (active) {
      await markProvider();
      return { statusCode: 200, headers: { "Content-Type": "application/json" }, body: JSON.stringify({ connected: true }) };
    }
    // Status-only poll (the new-tab connect UI polls with &check=1): never mint a fresh OAuth,
    // else each poll spawns a duplicate Composio connection. Just report not-yet-connected.
    if (qs.check) {
      return { statusCode: 200, headers: { "Content-Type": "application/json" }, body: JSON.stringify({ connected: false }) };
    }
    const r = await fetch(`${COMPOSIO_API}/connected_accounts`, {
      method: "POST",
      headers: { "x-api-key": COMPOSIO_KEY, "Content-Type": "application/json" },
      body: JSON.stringify({ auth_config: { id: GCAL_AUTH_CONFIG }, connection: { user_id: userId } }),
    });
    const j = await r.json();
    const redirect = j.redirect_url || j.redirect_uri || j?.connectionData?.val?.redirectUrl;
    if (!redirect) return { statusCode: 502, body: JSON.stringify({ error: "no redirect", detail: j }) };
    // Do NOT mark calendar_provider here — minting the OAuth is not the same as connecting. We mark it
    // ONLY when the connection is truly ACTIVE (the check=1 poll above detects consent + marks). This
    // keeps the Telegram bot's onboarding stage truthful — it never says "✅ Calendar connected!" until
    // the user has actually consented.
    return { statusCode: 200, headers: { "Content-Type": "application/json" }, body: JSON.stringify({ redirect_url: redirect }) };
  } catch (e) {
    return { statusCode: 502, body: JSON.stringify({ error: String(e) }) };
  }
};
