// LM-33a: Telegram /panel one-time token and browser session helpers.
"use strict";

const crypto = require("crypto");
const { renderPanelPage } = require("./panel-ui.js");

const PANEL_TOKEN_TTL_MS = 5 * 60 * 1000;
const PANEL_SESSION_TTL_MS = 24 * 60 * 60 * 1000;
const PANEL_SESSION_ROTATE_MS = 12 * 60 * 60 * 1000;
const PANEL_SESSION_IDLE_MS = 30 * 24 * 60 * 60 * 1000;
const PANEL_COOKIE = "__Host-lm_panel_session";
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
  const sent = await sender(
    opts.token,
    chatId,
    "Open your Anicca Life Manager dashboard. The button expires in 5 minutes and works once.",
    { reply_markup: { inline_keyboard: [[{ text: "Open dashboard", url: result.url }]] } },
  );
  if (sent && sent.ok === false && opts.clickableFallback !== false) {
    await sender(opts.token, chatId, `<a href="${result.url}">Open dashboard</a> (expires in 5 minutes; works once)`);
  }
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
      expires_at: new Date(now.getTime() + PANEL_SESSION_IDLE_MS).toISOString(),
      idle_expires_at: new Date(now.getTime() + PANEL_SESSION_IDLE_MS).toISOString(),
      absolute_expires_at: null,
    }),
  });
  if (!response.ok) throw new Error(`panel session insert failed (${response.status})`);
  return session;
}

function panelSessionCookie(value, maxAge = PANEL_SESSION_IDLE_MS / 1000) {
  return `${PANEL_COOKIE}=${value}; Max-Age=${maxAge}; Path=/; HttpOnly; Secure; SameSite=Lax`;
}

function clearPanelCookies() {
  return [`${PANEL_COOKIE}=; Max-Age=0; Path=/; HttpOnly; Secure; SameSite=Lax`, "lm_panel_session=; Max-Age=0; Path=/; HttpOnly; Secure; SameSite=Lax"];
}

async function panelRpc(name, body, opts) {
  const response = await (opts.fetchImpl || fetch)(`${String(opts.supaUrl).replace(/\/$/, "")}/rest/v1/rpc/${name}`, {
    method: "POST", headers: supabaseHeaders(opts.supaKey), body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error(`panel session rpc failed (${response.status})`);
  return response.json().catch(() => null);
}

async function resolvePanelSession(session, opts = {}) {
  if (!OPAQUE_TOKEN_RE.test(String(session || ""))) return null;
  const randomBytes = opts.randomBytes || crypto.randomBytes;
  const candidateSeed = sha256(randomBytes(32).toString("base64url"));
  const rotationSecret = String(opts.sessionRotationSecret || process.env.LM_PANEL_SESSION_ROTATION_SECRET || opts.supaKey || "");
  if (!rotationSecret) return null;
  const deriveChild = (seed) => crypto.createHmac("sha256", rotationSecret).update(`lm-panel-session:v1:${session}:${seed}`).digest("base64url");
  const child = deriveChild(candidateSeed);
  const rows = await panelRpc("resolve_lm_panel_session", { p_session_hash: sha256(session), p_child_hash: sha256(child), p_child_seed: candidateSeed }, opts);
  const row = Array.isArray(rows) ? rows[0] : rows;
  if (!row || !row.uid || !row.chat_id) return null;
  let replacement = null;
  if (row.rotated) {
    if (row.accepted_child_seed) {
      replacement = deriveChild(String(row.accepted_child_seed));
      if (row.accepted_child_hash && sha256(replacement) !== row.accepted_child_hash) return null;
    } else {
      replacement = child;
    }
  }
  const csrf = row.family_id ? sha256(`${row.family_id}:panel-family-csrf`) : csrfToken(replacement || session);
  const scope = { uid: String(row.uid), chatId: String(row.chat_id), replacement, csrf };
  const cookieMaxAge = Number(row.cookie_max_age);
  if (Number.isInteger(cookieMaxAge) && cookieMaxAge > 0) {
    scope.cookieValue = replacement || session;
    scope.cookieMaxAge = cookieMaxAge;
  }
  return scope;
}

function panelScopeCookie(scope) {
  if (!scope) return "";
  if (scope.cookieValue && scope.cookieMaxAge) return panelSessionCookie(scope.cookieValue, scope.cookieMaxAge);
  return scope.replacement ? panelSessionCookie(scope.replacement) : "";
}

async function revokePanelSession(session, opts = {}) {
  if (!OPAQUE_TOKEN_RE.test(String(session || ""))) return false;
  return Boolean(await panelRpc("revoke_lm_panel_session", { p_session_hash: sha256(session) }, opts));
}

async function revokePanelSessionsForTenant(scope, opts = {}) {
  return Boolean(await panelRpc("revoke_lm_panel_sessions_for_tenant", { p_uid: String(scope.uid), p_chat_id: String(scope.chatId) }, opts));
}

function cookieValue(header, name) {
  for (const part of String(header || "").split(";")) {
    const index = part.indexOf("=");
    if (index === -1 || part.slice(0, index).trim() !== name) continue;
    return part.slice(index + 1).trim();
  }
  return "";
}

async function sessionScope(session, opts = {}) {
  return resolvePanelSession(session, opts);
}

async function sessionUid(session, opts = {}) {
  const scope = await sessionScope(session, opts);
  return scope && scope.uid;
}

function csrfToken(session) {
  return OPAQUE_TOKEN_RE.test(String(session || "")) ? sha256(`${session}:panel-csrf`) : "";
}

function renderInvalidPanelLink(botUsername) {
  const username = /^[A-Za-z0-9_]{5,32}$/.test(String(botUsername || "")) ? botUsername : "LifeManagerBotbot";
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="referrer" content="no-referrer"><title>Dashboard link expired</title><style>body{margin:0;min-height:100vh;display:grid;place-items:center;background:#f3efe5;color:#122238;font-family:Avenir,"Hiragino Sans",sans-serif}.card{width:min(32rem,calc(100% - 40px));border:1px solid #9d9484;background:#fbf8f0;padding:32px;box-shadow:0 24px 70px rgba(38,35,30,.12)}h1{font-family:"Iowan Old Style",serif;font-weight:500}a{display:inline-flex;min-height:44px;align-items:center;margin-top:12px;padding:0 18px;background:#122238;color:white;text-decoration:none}</style></head><body><main class="card"><h1>This dashboard link is no longer available.</h1><p>For your security, each link works once and expires after five minutes.</p><a href="https://t.me/${username}?start=panel">Get a new dashboard link</a></main></body></html>`;
}

async function handlePanelRequest(req, res, opts = {}) {
  const pathname = new URL(req.url || "/panel", "http://panel.local").pathname;
  if (pathname === "/panel/logout") {
    const session = cookieValue(req.headers.cookie, PANEL_COOKIE) || cookieValue(req.headers.cookie, "lm_panel_session");
    const expectedOrigin = String(opts.panelOrigin || opts.panelBaseUrl || "").replace(/\/$/, "");
    if (req.method !== "POST") { res.writeHead(405, { Allow: "POST", "cache-control": "no-store" }); res.end(); return; }
    if (!expectedOrigin || String(req.headers.origin || "") !== expectedOrigin) { res.writeHead(403, { Allow: "POST", "cache-control": "no-store" }); res.end(); return; }
    const scope = await sessionScope(session, opts);
    if (!scope || !timingEqual(req.headers["x-lm-csrf"], scope.csrf || csrfToken(session))) { res.writeHead(403, { Allow: "POST", "cache-control": "no-store" }); res.end(); return; }
    await revokePanelSession(session, opts);
    res.writeHead(303, { Location: "/panel", "Set-Cookie": clearPanelCookies(), "cache-control": "no-store" }); res.end(); return;
  }
  if (req.method !== "GET") {
    res.writeHead(405, { Allow: "GET" });
    res.end("method not allowed");
    return;
  }
  const query = new URL(req.url || "/panel", "http://panel.local").searchParams;
  const token = query.get("t");
  if (!token) {
    const session = cookieValue(req.headers.cookie, PANEL_COOKIE) || cookieValue(req.headers.cookie, "lm_panel_session");
    const scope = await sessionScope(session, opts);
    if (!scope) {
      res.writeHead(200, { "content-type": "text/html; charset=utf-8", "cache-control": "no-store", "referrer-policy": "no-referrer" });
      res.end(renderInvalidPanelLink(opts.botUsername || process.env.LM_TELEGRAM_BOT_USERNAME));
      return;
    }
    res.writeHead(200, {
      "content-type": "text/html; charset=utf-8",
      "cache-control": "no-store",
      "x-content-type-options": "nosniff",
      ...(panelScopeCookie(scope) ? { "Set-Cookie": panelScopeCookie(scope) } : {}),
    });
    res.end(renderPanelPage({ csrf: scope.csrf }));
    return;
  }

  const claimed = await claimPanelToken(token, opts);
  if (!claimed) {
    res.writeHead(403, { "content-type": "text/html; charset=utf-8", "cache-control": "no-store", "referrer-policy": "no-referrer", "x-content-type-options": "nosniff" });
    res.end(renderInvalidPanelLink(opts.botUsername || process.env.LM_TELEGRAM_BOT_USERNAME));
    return;
  }
  const session = await createPanelSession({ uid: claimed.uid, chatId: claimed.chat_id }, opts);
  res.writeHead(303, {
    Location: "/panel",
    "Set-Cookie": panelSessionCookie(session),
    "Cache-Control": "no-store",
    "Referrer-Policy": "no-referrer",
  });
  res.end();
}

function timingEqual(left, right) {
  const a = Buffer.from(String(left || "")), b = Buffer.from(String(right || ""));
  return a.length > 0 && a.length === b.length && crypto.timingSafeEqual(a, b);
}

module.exports = {
  PANEL_TOKEN_TTL_MS,
  PANEL_SESSION_TTL_MS,
  PANEL_SESSION_ROTATE_MS,
  PANEL_SESSION_IDLE_MS,
  sha256,
  createPanelToken,
  sendPanelLink,
  claimPanelToken,
  createPanelSession,
  panelSessionCookie,
  panelScopeCookie,
  clearPanelCookies,
  resolvePanelSession,
  revokePanelSession,
  revokePanelSessionsForTenant,
  cookieValue,
  csrfToken,
  sessionScope,
  sessionUid,
  handlePanelRequest,
};
