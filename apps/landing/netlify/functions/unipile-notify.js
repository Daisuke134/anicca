// unipile-notify.js — Unipile hosted-auth webhook. After a user completes the Google consent, Unipile
// POSTs here with the connected account_id and the `name` we set at link creation (= the lm_users uid).
// We persist gmail_account_id so unipile-connect's poll flips to {connected:true}.
//
// SECURITY (account-takeover fix): this endpoint is UNauthenticated by default, so a stranger could POST
// {name: victim_uid, account_id: theirs} and rebind any user's mailbox. Two gates close that:
//   1) Shared secret: the notify_url carries ?s=<UNIPILE_NOTIFY_SECRET> known only to us + Unipile;
//      reject (403) on mismatch (timing-safe). Stops all unauthenticated callers.
//   2) Provenance check: the account_id MUST exist in OUR Unipile workspace (GET it with our token);
//      an attacker can't create an account there without our token. Reject (403) if it isn't ours.
// Only after both gates do we write gmail_account_id.
const crypto = require("crypto");
const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
const UNIPILE_DSN = process.env.UNIPILE_DSN;
const UNIPILE_TOKEN = process.env.UNIPILE_TOKEN;
const NOTIFY_SECRET = process.env.UNIPILE_NOTIFY_SECRET || "";
const json = (code, obj) => ({ statusCode: code, headers: { "Content-Type": "application/json" }, body: JSON.stringify(obj) });

function secretOk(got) {
  if (!NOTIFY_SECRET || !got) return false;
  const a = Buffer.from(String(got)), b = Buffer.from(NOTIFY_SECRET);
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}

// The account_id must be a real account in OUR Unipile workspace (auth'd by our token).
async function accountIsOurs(accountId) {
  try {
    const r = await fetch(`https://${UNIPILE_DSN}/api/v1/accounts/${encodeURIComponent(accountId)}`, {
      headers: { "X-API-KEY": UNIPILE_TOKEN, accept: "application/json" },
    });
    if (!r.ok) return false;
    const a = await r.json().catch(() => ({}));
    return !!(a && (a.id === accountId));
  } catch { return false; }
}

exports.handler = async (event) => {
  if (event.httpMethod !== "POST") return json(405, { error: "method not allowed" });
  // Gate 1: shared secret in the query string.
  const q = event.queryStringParameters || {};
  if (!secretOk(q.s)) return json(403, { error: "bad secret" });

  let p;
  try { p = JSON.parse(event.body || "{}"); } catch { return json(400, { error: "bad json" }); }
  const uid = p.name || p.identifier;                 // set to the lm uid at link creation
  const accountId = p.account_id || p.account || p.id;
  const status = p.status || "";
  if (!uid || !accountId) return json(200, { ok: true, skipped: "missing name/account_id" });
  if (status && !/SUCCESS|CREATED|OK/i.test(status)) return json(200, { ok: true, skipped: status });
  // Reject anything that isn't a uid we mint (lm_…) so a forged name can't touch other tables/rows.
  if (!/^lm_[A-Za-z0-9_-]+$/.test(uid)) return json(400, { error: "bad uid format" });

  // Gate 2: provenance — the account must live in our Unipile workspace.
  if (!(await accountIsOurs(accountId))) return json(403, { error: "account not in workspace" });

  if (!SUPABASE_URL || !SUPABASE_KEY) return json(500, { error: "missing supabase" });
  const r = await fetch(`${SUPABASE_URL}/rest/v1/lm_users?uid=eq.${encodeURIComponent(uid)}`, {
    method: "PATCH",
    headers: { apikey: SUPABASE_KEY, Authorization: `Bearer ${SUPABASE_KEY}`, "Content-Type": "application/json", Prefer: "return=minimal" },
    body: JSON.stringify({ gmail_account_id: accountId, gmail_provider: "unipile", updated_at: new Date().toISOString() }),
  });
  if (!r.ok) return json(502, { error: "supabase patch failed", status: r.status });
  return json(200, { ok: true });
};
