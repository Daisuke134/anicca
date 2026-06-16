// composio-gmail — deliver Anicca's wake/daily report into the user's OWN Gmail inbox
// via Composio's managed Gmail connection (the same /connected_accounts OAuth the web's
// gmail-connect.js sets up). No per-user OAuth app, no hardcoded secrets.
//
// Architecture (Dais 2026-06-16): ALL Anicca service connections go through Composio.
// The user connects their Gmail once (web one-click consent → ACTIVE connected account
// keyed by user_id). This module then SENDS a report into that mailbox via the v3 tools
// execute endpoint:  POST /api/v3/tools/execute/GMAIL_SEND_EMAIL  (x-api-key header).
//
// HONESTY (HARD 0.24): the executor makes a REAL Composio API call. Nothing is faked.
// Callers gate the real send behind their own flags; this module never simulates success.
//
// Docs (ctx7 /websites/docs-composio_vercel_app):
//   - POST /api/v3/tools/execute/{tool_slug}  (reference/api-reference/tools/postToolsExecuteByToolSlug)
//   - GMAIL_SEND_EMAIL args: to|recipient_email, cc, bcc, subject, body, is_html (toolkits/gmail)
//   - request body: { user_id, connected_account_id?, arguments: {...} } (api-reference execute curl)

const COMPOSIO_API = process.env.COMPOSIO_API_BASE || "https://backend.composio.dev/api/v3";
const GMAIL_SEND_SLUG = "GMAIL_SEND_EMAIL";
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

// buildGmailSend — pure: turn a high-level report into the exact Composio execute payload.
// Returns { slug, body } where body is what POSTs to /tools/execute/<slug>. No I/O, no env.
export function buildGmailSend({ to, subject, body, userId, connectedAccountId, isHtml = false } = {}) {
  if (typeof to !== "string" || !EMAIL_RE.test(to.trim())) {
    throw new Error(`composio-gmail: invalid recipient: ${to}`);
  }
  if (typeof subject !== "string" || subject.length === 0) {
    throw new Error("composio-gmail: subject required");
  }
  if (typeof body !== "string" || body.length === 0) {
    throw new Error("composio-gmail: body required");
  }
  if (typeof userId !== "string" || userId.length === 0) {
    throw new Error("composio-gmail: userId required (the Composio connection owner)");
  }
  const payload = {
    user_id: userId,
    arguments: {
      recipient_email: to.trim(),
      subject,
      body,
      is_html: Boolean(isHtml),
    },
  };
  if (connectedAccountId) payload.connected_account_id = connectedAccountId;
  return { slug: GMAIL_SEND_SLUG, body: payload };
}

// hasGmailConnection — does this user_id already have an ACTIVE Composio Gmail account?
// Mirrors gmail-connect.js idempotency check. Returns { connected, connectedAccountId|null }.
export async function hasGmailConnection({ userId, apiKey, opts = {} } = {}) {
  const fetchImpl = opts.fetchImpl || globalThis.fetch;
  if (!apiKey) throw new Error("composio-gmail: COMPOSIO_API_KEY required");
  if (!userId) throw new Error("composio-gmail: userId required");
  const url = `${COMPOSIO_API}/connected_accounts?user_ids=${encodeURIComponent(userId)}&toolkit_slugs=gmail`;
  const res = await fetchImpl(url, { headers: { "x-api-key": apiKey } });
  if (!res.ok) throw new Error(`composio-gmail: connected_accounts ${res.status}`);
  const j = await res.json();
  const active = (j.items || []).find((i) => i.status === "ACTIVE");
  return { connected: Boolean(active), connectedAccountId: active ? active.id : null };
}

// sendGmail — REAL send. Builds the payload (buildGmailSend) and POSTs to the execute endpoint.
// Throws on transport error OR when Composio reports successful:false. Never fakes success.
export async function sendGmail({ to, subject, body, userId, connectedAccountId, isHtml, apiKey, opts = {} } = {}) {
  const fetchImpl = opts.fetchImpl || globalThis.fetch;
  if (!apiKey) throw new Error("composio-gmail: COMPOSIO_API_KEY required");
  const { slug, body: payload } = buildGmailSend({ to, subject, body, userId, connectedAccountId, isHtml });
  const res = await fetchImpl(`${COMPOSIO_API}/tools/execute/${slug}`, {
    method: "POST",
    headers: { "x-api-key": apiKey, "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const text = await res.text();
  let j;
  try {
    j = JSON.parse(text);
  } catch {
    throw new Error(`composio-gmail: non-JSON response ${res.status}: ${text.slice(0, 200)}`);
  }
  if (!res.ok) throw new Error(`composio-gmail: execute ${res.status}: ${text.slice(0, 200)}`);
  if (j.successful === false) {
    throw new Error(`composio-gmail: send failed: ${j.error || JSON.stringify(j).slice(0, 200)}`);
  }
  return { successful: true, data: j.data };
}
