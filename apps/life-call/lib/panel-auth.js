// LM-33a: Telegram /panel one-time token and browser session helpers.
"use strict";

const crypto = require("crypto");

const PANEL_TOKEN_TTL_MS = 5 * 60 * 1000;
const PANEL_SESSION_TTL_MS = 24 * 60 * 60 * 1000;
const OPAQUE_TOKEN_RE = /^[A-Za-z0-9_-]{43}$/;

function sha256(value) {
  return crypto.createHash("sha256").update(String(value)).digest("hex");
}

function supabaseHeaders(supaKey, prefer) {
  return {
    apikey: supaKey,
    Authorization: `Bearer ${supaKey}`,
    "Content-Type": "application/json",
    ...(prefer ? { Prefer: prefer } : {}),
  };
}

async function createPanelToken({ uid, chatId }, opts = {}) {
  const randomBytes = opts.randomBytes || crypto.randomBytes;
  const now = opts.now ? opts.now() : new Date();
  const token = randomBytes(32).toString("base64url");
  const row = {
    token_hash: sha256(token),
    uid,
    chat_id: String(chatId),
    expires_at: new Date(now.getTime() + PANEL_TOKEN_TTL_MS).toISOString(),
  };
  const response = await (opts.fetchImpl || fetch)(`${opts.supaUrl}/rest/v1/lm_panel_tokens`, {
    method: "POST",
    headers: supabaseHeaders(opts.supaKey, "return=minimal"),
    body: JSON.stringify(row),
  });
  if (!response.ok) throw new Error(`panel token insert failed (${response.status})`);
  const base = String(opts.panelBaseUrl || "").replace(/\/$/, "");
  return { token, url: `${base}/panel?t=${encodeURIComponent(token)}` };
}

async function sendPanelLink({ uid, chatId }, opts = {}) {
  const result = await createPanelToken({ uid, chatId }, opts);
  const sender = opts.sendMessage || require("./telegram.js").sendMessage;
  await sender(
    opts.token,
    chatId,
    `Open your Anicca Life Manager panel (this link expires in 5 minutes and works once):\n${result.url}`,
  );
  return result;
}

async function claimPanelToken(token, opts = {}) {
  if (!OPAQUE_TOKEN_RE.test(String(token || ""))) return null;
  const response = await (opts.fetchImpl || fetch)(`${opts.supaUrl}/rest/v1/rpc/claim_lm_panel_token`, {
    method: "POST",
    headers: supabaseHeaders(opts.supaKey),
    body: JSON.stringify({ p_token_hash: sha256(token) }),
  });
  if (!response.ok) throw new Error(`panel token claim failed (${response.status})`);
  const rows = await response.json().catch(() => []);
  return Array.isArray(rows) && rows[0] ? rows[0] : null;
}

async function createPanelSession({ uid, chatId }, opts = {}) {
  const randomBytes = opts.randomBytes || crypto.randomBytes;
  const now = opts.now ? opts.now() : new Date();
  const session = randomBytes(32).toString("base64url");
  const response = await (opts.fetchImpl || fetch)(`${opts.supaUrl}/rest/v1/lm_panel_sessions`, {
    method: "POST",
    headers: supabaseHeaders(opts.supaKey, "return=minimal"),
    body: JSON.stringify({
      session_hash: sha256(session),
      uid,
      chat_id: String(chatId),
      expires_at: new Date(now.getTime() + PANEL_SESSION_TTL_MS).toISOString(),
    }),
  });
  if (!response.ok) throw new Error(`panel session insert failed (${response.status})`);
  return session;
}

function cookieValue(header, name) {
  for (const part of String(header || "").split(";")) {
    const index = part.indexOf("=");
    if (index === -1 || part.slice(0, index).trim() !== name) continue;
    return part.slice(index + 1).trim();
  }
  return "";
}

async function sessionUid(session, opts = {}) {
  if (!OPAQUE_TOKEN_RE.test(String(session || ""))) return null;
  const now = opts.now ? opts.now() : new Date();
  const query = new URLSearchParams({
    session_hash: `eq.${sha256(session)}`,
    expires_at: `gt.${now.toISOString()}`,
    select: "uid",
    limit: "1",
  });
  const response = await (opts.fetchImpl || fetch)(`${opts.supaUrl}/rest/v1/lm_panel_sessions?${query}`, {
    headers: supabaseHeaders(opts.supaKey),
  });
  if (!response.ok) throw new Error(`panel session lookup failed (${response.status})`);
  const rows = await response.json().catch(() => []);
  return Array.isArray(rows) && rows[0] && rows[0].uid ? String(rows[0].uid) : null;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[character]);
}

async function handlePanelRequest(req, res, opts = {}) {
  if (req.method !== "GET") {
    res.writeHead(405, { Allow: "GET" });
    res.end("method not allowed");
    return;
  }
  const query = new URL(req.url || "/panel", "http://panel.local").searchParams;
  const token = query.get("t");
  if (!token) {
    const session = cookieValue(req.headers.cookie, "lm_panel_session");
    const uid = await sessionUid(session, opts);
    if (!uid) {
      res.writeHead(401, { "content-type": "text/plain; charset=utf-8", "cache-control": "no-store" });
      res.end("unauthorized");
      return;
    }
    res.writeHead(200, {
      "content-type": "text/html; charset=utf-8",
      "cache-control": "no-store",
      "x-content-type-options": "nosniff",
    });
    res.end(`<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Anicca Life Manager</title></head><body><main><h1>Anicca Life Manager</h1><p>${escapeHtml(uid)}</p></main></body></html>`);
    return;
  }

  const claimed = await claimPanelToken(token, opts);
  if (!claimed) {
    res.writeHead(403, { "content-type": "text/plain; charset=utf-8", "cache-control": "no-store" });
    res.end("forbidden");
    return;
  }
  const session = await createPanelSession({ uid: claimed.uid, chatId: claimed.chat_id }, opts);
  res.writeHead(303, {
    Location: "/panel",
    "Set-Cookie": `lm_panel_session=${session}; Max-Age=86400; Path=/panel; HttpOnly; Secure; SameSite=Lax`,
    "Cache-Control": "no-store",
    "Referrer-Policy": "no-referrer",
  });
  res.end();
}

module.exports = {
  PANEL_TOKEN_TTL_MS,
  PANEL_SESSION_TTL_MS,
  sha256,
  createPanelToken,
  sendPanelLink,
  claimPanelToken,
  createPanelSession,
  cookieValue,
  sessionUid,
  handlePanelRequest,
};
