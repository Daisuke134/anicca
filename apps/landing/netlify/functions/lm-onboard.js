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
const crypto = require("crypto");
const LM_UID_SECRET = process.env.LM_UID_SECRET || "";
const ALLOWED_HOSTS = new Set(["aniccaai.com", "www.aniccaai.com", "localhost", "127.0.0.1"]);

// Sign/verify the server-minted uid so later calls can't forge identity (IDOR fix).
function signUid(uid) {
  return crypto.createHmac("sha256", LM_UID_SECRET).update(uid).digest("base64url");
}
function verifyUid(uid, sig) {
  if (!LM_UID_SECRET || !uid || !sig) return false;
  const expected = signUid(uid);
  const a = Buffer.from(String(sig));
  const b = Buffer.from(expected);
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}
function signCalendarGrant(uid, purpose, exp, nonce = "") {
  return crypto.createHmac("sha256", LM_UID_SECRET)
    .update(`${uid}\ncalendar-connect:${purpose}\n${exp}\n${nonce}`)
    .digest("base64url");
}
function calendarGrants(uid, nowSeconds = Math.floor(Date.now() / 1000)) {
  const exp = nowSeconds + 5 * 60;
  const nonce = crypto.randomBytes(18).toString("base64url");
  return {
    oauth: { purpose: "oauth", exp, nonce, sig: signCalendarGrant(uid, "oauth", exp, nonce) },
    status: { purpose: "status", exp, nonce: "", sig: signCalendarGrant(uid, "status", exp, "") },
  };
}
// Allow redirects to our own hosts ONLY; emit a normalized URL with userinfo cleared and any
// caller-supplied uid/sig stripped (defeats userinfo-confusion open redirect + session fixation).
function safeReturn(url) {
  try {
    const u = new URL(String(url));
    if ((u.protocol === "https:" || u.protocol === "http:") && ALLOWED_HOSTS.has(u.hostname)) {
      u.username = "";
      u.password = "";
      u.searchParams.delete("uid");
      u.searchParams.delete("sig");
      return u.toString();
    }
  } catch {}
  return "https://aniccaai.com/lm";
}

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

async function readUser(uid) {
  const select = "uid,name,calendar_provider,phone,paid,tg_onboard_stage,call_language";
  const result = await fetch(
    `${SUPABASE_URL}/rest/v1/lm_users?uid=eq.${encodeURIComponent(uid)}&select=${select}&limit=1`,
    { headers: { apikey: SUPABASE_KEY, Authorization: `Bearer ${SUPABASE_KEY}` } },
  );
  if (!result.ok) return { ok: false, row: null };
  const rows = await result.json().catch(() => null);
  if (!Array.isArray(rows)) return { ok: false, row: null };
  return { ok: true, row: rows[0] || null };
}

function onboardingState(row) {
  const current = row || {};
  const name = typeof current.name === "string" && current.name.trim() ? current.name : null;
  const calendarConnected = current.calendar_provider === "composio_gcal";
  const phone = typeof current.phone === "string" && current.phone.trim() ? current.phone : null;
  const paid = current.paid === true;
  const contextComplete = current.tg_onboard_stage === "done";
  const callLanguage = current.call_language === "ja" || current.call_language === "en"
    ? current.call_language : null;
  const step = !name ? "name" : !calendarConnected ? "connect" : !phone ? "phone" : !paid ? "pay" : "dashboard";
  return { name, calendarConnected, contextComplete, phone, paid, callLanguage, step };
}

exports.handler = async (event) => {
  const q = event.queryStringParameters || {};
  const action = q.action;

  if (action === "google-start") {
    if (!COMPOSIO_KEY || !GCAL_AUTH_CONFIG) return { statusCode: 500, body: "missing composio config" };
    if (!LM_UID_SECRET) return json(500, { error: "missing LM_UID_SECRET" });
    // Mint a stable uid for this onboarding session and start a Google (Composio) connection.
    const uid = "lm_" + (globalThis.crypto?.randomUUID?.() || Date.now().toString(36));
    const sig = signUid(uid);
    const r = await fetch(`${COMPOSIO_API}/connected_accounts`, {
      method: "POST",
      headers: { "x-api-key": COMPOSIO_KEY, "Content-Type": "application/json" },
      body: JSON.stringify({ auth_config: { id: GCAL_AUTH_CONFIG }, connection: { user_id: uid } }),
    });
    const j = await r.json();
    const redirect = j.redirect_url || j.redirect_uri || j?.connectionData?.val?.redirectUrl;
    if (!redirect) return json(502, { error: "no redirect", detail: j });
    await upsertUser({ uid }).catch(() => {});
    // safeReturn strips any caller-supplied uid/sig so the server-minted pair is the only one.
    const ret = safeReturn(q.return || "https://aniccaai.com/lm");
    const retWithId = ret + (ret.includes("?") ? "&" : "?") + "uid=" + uid + "&sig=" + encodeURIComponent(sig);
    const dest = `${redirect}${redirect.includes("?") ? "&" : "?"}state=${encodeURIComponent(retWithId)}`;
    return { statusCode: 302, headers: { Location: dest }, body: "" };
  }

  if (action === "google-callback") {
    const back = safeReturn(q.state || "https://aniccaai.com/lm");
    return { statusCode: 302, headers: { Location: back }, body: "" };
  }

  if (action === "exchange" && event.httpMethod === "POST") {
    // Verify a Supabase access token (Supabase Auth is the login), derive a stable uid from the
    // Supabase user id, sign it. The backend keeps its uid+sig contract; the uid is now anchored
    // to the real Supabase user — Composio is only the post-login gcal/gmail data connection.
    if (!SUPABASE_URL || !SUPABASE_KEY) return json(500, { error: "missing supabase config" });
    if (!LM_UID_SECRET) return json(500, { error: "missing LM_UID_SECRET" });
    let xb;
    try { xb = JSON.parse(event.body || "{}"); } catch { return json(400, { error: "bad json" }); }
    const token = xb.access_token || "";
    if (!token) return json(400, { error: "missing access_token" });
    const ur = await fetch(`${SUPABASE_URL}/auth/v1/user`, {
      headers: { Authorization: `Bearer ${token}`, apikey: SUPABASE_KEY },
    });
    if (!ur.ok) return json(401, { error: "invalid session" });
    const u = await ur.json().catch(() => null);
    if (!u || !u.id) return json(401, { error: "invalid session" });
    const uid = "lm_" + u.id; // deterministic per Supabase user
    const existing = await readUser(uid).catch(() => ({ ok: false, row: null }));
    if (!existing.ok) return json(502, { error: "onboarding state unavailable" });
    if (!existing.row) {
      const saved = await upsertUser({ uid }).catch(() => null);
      if (!saved || !saved.ok) return json(502, { error: "onboarding state save failed" });
    }
    return json(200, {
      uid, sig: signUid(uid), onboarding: onboardingState(existing.row),
      calendarConnect: calendarGrants(uid),
    });
  }

  if (action === "save" && event.httpMethod === "POST") {
    if (!SUPABASE_URL || !SUPABASE_KEY) return json(500, { error: "missing supabase config" });
    let body;
    try { body = JSON.parse(event.body || "{}"); } catch { return json(400, { error: "bad json" }); }
    const { uid, sig, name, phone, call_language } = body;
    if (!uid) return json(400, { error: "missing uid" });
    if (!verifyUid(uid, sig)) return json(403, { error: "bad uid signature" });
    const row = { uid };
    if (typeof name === "string") row.name = name.slice(0, 120);
    if (typeof phone === "string") row.phone = phone.slice(0, 20);
    // Call language the user picked on /lm (overrides the phone-country default; en/ja only).
    if (call_language === "en" || call_language === "ja") row.call_language = call_language;
    const r = await upsertUser(row);
    if (!r.ok) return json(502, { error: "save failed", status: r.status });
    return json(200, { ok: true });
  }

  if (action === "telegram-link" && event.httpMethod === "POST") {
    // The Telegram /start deep-link sends the user to /lm?tg=<chat_id>; once they're authenticated
    // (uid+sig), the page calls this to bind their Telegram chat to their lm_users row so the cloud
    // loops can message them on Telegram. HMAC-gated so nobody can bind a stranger's chat.
    if (!SUPABASE_URL || !SUPABASE_KEY) return json(500, { error: "missing supabase config" });
    let body;
    try { body = JSON.parse(event.body || "{}"); } catch { return json(400, { error: "bad json" }); }
    const { uid, sig, tg, name } = body;
    if (!uid) return json(400, { error: "missing uid" });
    if (!verifyUid(uid, sig)) return json(403, { error: "bad uid signature" });
    if (!/^\d{1,20}$/.test(String(tg || ""))) return json(400, { error: "bad tg id" });
    // The Telegram bot collects the name in-chat and carries it in the deep link (?name=) — persist it
    // here so the two channels share one row. Don't overwrite an existing name with an empty one.
    const row = { uid, telegram_chat_id: String(tg) };
    if (typeof name === "string" && name.trim()) row.name = name.trim().slice(0, 120);
    const r = await upsertUser(row);
    if (!r.ok) return json(502, { error: "save failed", status: r.status });
    return json(200, { ok: true });
  }

  return json(400, { error: "unknown action" });
};
