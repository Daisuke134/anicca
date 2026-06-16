// Life Manager (/lm) onboarding backend (spec28 P-lm-separate).
//   GET  ?action=google-start&return=<url>  -> begins Google login; redirects the browser to
//        Google consent (Composio managed OAuth identity primitive), callback assigns a stable uid.
//   GET  ?action=google-callback&...        -> Composio/Google redirect target; resolves the
//        connection to a uid and 302s back to <return>/lm?uid=<uid>.
//   POST ?action=save  {uid,name?,phone?}   -> upserts the lm_users row (name/phone).
// Identity = Composio Google connection (same verified app as calendar-connect.js). Supabase
// table lm_users is SEPARATE from the alarm subscriber_profiles so /lm and /install stay isolated.
const COMPOSIO_API = "https://backend.composio.dev/api/v3";
const COMPOSIO_KEY = process.env.COMPOSIO_API_KEY;
const GCAL_AUTH_CONFIG = process.env.COMPOSIO_GCAL_AUTH_CONFIG; // reuse the verified Google app
const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;

const json = (code, obj) => ({
  statusCode: code,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(obj),
});

async function upsertUser(row) {
  return fetch(`${SUPABASE_URL}/rest/v1/lm_users?on_conflict=uid`, {
    method: "POST",
    headers: {
      apikey: SUPABASE_KEY,
      Authorization: `Bearer ${SUPABASE_KEY}`,
      "Content-Type": "application/json",
      Prefer: "resolution=merge-duplicates,return=minimal",
    },
    body: JSON.stringify({ ...row, updated_at: new Date().toISOString() }),
  });
}

exports.handler = async (event) => {
  const q = event.queryStringParameters || {};
  const action = q.action;

  if (action === "google-start") {
    if (!COMPOSIO_KEY || !GCAL_AUTH_CONFIG) return { statusCode: 500, body: "missing composio config" };
    // Mint a stable uid for this onboarding session and start a Google (Composio) connection.
    const uid = "lm_" + (globalThis.crypto?.randomUUID?.() || Date.now().toString(36));
    const r = await fetch(`${COMPOSIO_API}/connected_accounts`, {
      method: "POST",
      headers: { "x-api-key": COMPOSIO_KEY, "Content-Type": "application/json" },
      body: JSON.stringify({ auth_config: { id: GCAL_AUTH_CONFIG }, connection: { user_id: uid } }),
    });
    const j = await r.json();
    const redirect = j.redirect_url || j.redirect_uri || j?.connectionData?.val?.redirectUrl;
    if (!redirect) return json(502, { error: "no redirect", detail: j });
    await upsertUser({ uid }).catch(() => {});
    const ret = q.return || "https://aniccaai.com/lm";
    // Append uid so the browser returns to /lm already logged-in (Composio redirects to its
    // configured callback; we forward uid via the state-bearing return URL).
    const dest = `${redirect}${redirect.includes("?") ? "&" : "?"}state=${encodeURIComponent(
      ret + (ret.includes("?") ? "&" : "?") + "uid=" + uid,
    )}`;
    return { statusCode: 302, headers: { Location: dest }, body: "" };
  }

  if (action === "google-callback") {
    const back = q.state || "https://aniccaai.com/lm";
    return { statusCode: 302, headers: { Location: back }, body: "" };
  }

  if (action === "save" && event.httpMethod === "POST") {
    if (!SUPABASE_URL || !SUPABASE_KEY) return json(500, { error: "missing supabase config" });
    let body;
    try { body = JSON.parse(event.body || "{}"); } catch { return json(400, { error: "bad json" }); }
    const { uid, name, phone } = body;
    if (!uid) return json(400, { error: "missing uid" });
    const row = { uid };
    if (typeof name === "string") row.name = name.slice(0, 120);
    if (typeof phone === "string") row.phone = phone.slice(0, 20);
    const r = await upsertUser(row);
    if (!r.ok) return json(502, { error: "save failed", status: r.status });
    return json(200, { ok: true });
  }

  return json(400, { error: "unknown action" });
};
