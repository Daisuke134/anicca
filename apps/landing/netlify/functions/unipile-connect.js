// unipile-connect.js — Life Manager (/lm): connect a user's GMAIL via Unipile hosted auth.
//
// Why Unipile (not Composio) for Gmail: Composio's managed Google app is NOT Google-verified for the
// RESTRICTED gmail scopes (gmail.modify), so its consent HARD-BLOCKS ("App is blocked") — proven in a
// real browser. Unipile owns a Google-VERIFIED app, so users connect Gmail (read+compose+send) with NO
// submission/CASA by us and no block. Calendar stays on Composio (calendar-connect.js).
//
// GET ?uid=<lm uid>&sig=<hmac>            -> if the user already has a Unipile Gmail account, {connected:true};
//   else mints a hosted-auth link (provider GOOGLE, name=uid) and returns { redirect_url }.
// GET ?uid=&sig=&check=1                  -> status-only poll: {connected:true|false} (never mints a link).
//
// On success Unipile redirects the browser to success_redirect_url AND calls notify_url
// (unipile-notify.js) with { name: uid, account_id } — that's where gmail_account_id gets stored.
const crypto = require("crypto");
const UNIPILE_DSN = process.env.UNIPILE_DSN;            // e.g. api35.unipile.com:16580
const UNIPILE_TOKEN = process.env.UNIPILE_TOKEN;
const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
const LM_UID_SECRET = process.env.LM_UID_SECRET || "";
const NOTIFY_SECRET = process.env.UNIPILE_NOTIFY_SECRET || "";
const BASE = "https://aniccaai.com";

function verifyUid(uid, sig) {
  if (!LM_UID_SECRET || !uid || !sig) return false;
  const expected = crypto.createHmac("sha256", LM_UID_SECRET).update(uid).digest("base64url");
  const a = Buffer.from(String(sig)), b = Buffer.from(expected);
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}
const json = (code, obj) => ({ statusCode: code, headers: { "Content-Type": "application/json" }, body: JSON.stringify(obj) });

async function alreadyConnected(uid) {
  // Source of truth = our row (set by unipile-notify). Also covers the poll.
  const r = await fetch(
    `${SUPABASE_URL}/rest/v1/lm_users?uid=eq.${encodeURIComponent(uid)}&select=gmail_account_id`,
    { headers: { apikey: SUPABASE_KEY, Authorization: `Bearer ${SUPABASE_KEY}` } });
  const d = await r.json().catch(() => []);
  return Array.isArray(d) && d[0] && !!d[0].gmail_account_id;
}

exports.handler = async (event) => {
  if (!UNIPILE_DSN || !UNIPILE_TOKEN) return json(500, { error: "missing unipile config" });
  const q = event.queryStringParameters || {};
  const uid = q.uid;
  if (!uid) return json(400, { error: "missing uid" });
  if (!verifyUid(uid, q.sig)) return json(403, { error: "bad uid signature" });

  try {
    if (await alreadyConnected(uid)) return json(200, { connected: true });
    if (q.check) return json(200, { connected: false });

    const expiresOn = new Date(Date.now() + 60 * 60 * 1000).toISOString(); // 1h link TTL
    const r = await fetch(`https://${UNIPILE_DSN}/api/v1/hosted/accounts/link`, {
      method: "POST",
      headers: { "X-API-KEY": UNIPILE_TOKEN, "Content-Type": "application/json" },
      body: JSON.stringify({
        type: "create",
        // Gmail ONLY (Dais 2026-06-22): "connect Gmail" must be a single clean action — no provider
        // picker / IMAP / Outlook. The product's mail layer is Gmail. Users connect a real Gmail account.
        // (We tried offering OUTLOOK/MAIL/IMAP so a Google account WITHOUT a Gmail mailbox could connect,
        // but the multi-provider wizard is worse UX; the right answer is: use a real Gmail.)
        providers: ["GOOGLE"],
        api_url: `https://${UNIPILE_DSN}`,
        expiresOn,
        name: uid, // Unipile echoes this to notify_url so we can match the account to the user
        // notify_url carries a shared secret so the webhook can reject unauthenticated callers
        // (account-takeover defense — see unipile-notify.js). Plus a provenance check there.
        notify_url: `${BASE}/.netlify/functions/unipile-notify?s=${encodeURIComponent(NOTIFY_SECRET)}`,
        success_redirect_url: `${BASE}/lm?gmail=connected`,
        failure_redirect_url: `${BASE}/lm?gmail=error`,
      }),
    });
    const j = await r.json().catch(() => ({}));
    const url = j.url || j.link;
    if (!url) return json(502, { error: "no unipile link", detail: j });
    return json(200, { redirect_url: url });
  } catch (e) {
    return json(502, { error: String(e) });
  }
};
