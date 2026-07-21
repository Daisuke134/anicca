// Fail-closed, read-only readiness audit for the production DAILY runtime.
// Every adapter returns curated evidence only; raw provider bodies, credentials and PII never enter reports.
"use strict";

const crypto = require("node:crypto");
const { LIVE_MODEL } = require("./call-logic.js");
const { GATE_ORDER, discoveryMessage } = require("./feature-discovery.js");

const DEPENDENCY_NAMES = Object.freeze([
  "health",
  "telegram",
  "calendar",
  "call",
  "location",
  "email",
  "discovery",
  "gemini",
  "maps",
]);

const REQUIRED_TELEGRAM_UPDATES = Object.freeze(["message", "edited_message", "callback_query"]);
const TELNYX_BASE = "https://api.telnyx.com/v2";
const COMPOSIO_EXEC = "https://backend.composio.dev/api/v3/tools/execute/GOOGLECALENDAR_EVENTS_LIST";
const RESEND_DOMAINS = "https://api.resend.com/domains";
const TIMEOUT = Symbol("preflight-timeout");

class PreflightFailure extends Error {
  constructor(classification, evidence = {}) {
    super(classification);
    this.classification = classification;
    this.evidence = evidence;
  }
}

function fail(classification, evidence) {
  throw new PreflightFailure(classification, evidence);
}

function requireEnv(env, names) {
  const missing = names.filter((name) => !String(env[name] || "").trim());
  if (missing.length) fail("configuration", { configured: false, missing_count: missing.length });
}

function secretValues(env) {
  return Object.entries(env || {})
    .filter(([name, value]) => /(?:KEY|TOKEN|SECRET|PHONE_NUMBER|CONNECTION_ID)$/i.test(name) && String(value || "").length >= 4)
    .map(([, value]) => String(value));
}

function sanitizeEvidence(value, secrets = [], key = "") {
  if (/(?:secret|token|api.?key|authorization|phone|email|address|latitude|longitude|chat.?id|\buid\b|raw|body)/i.test(key)) {
    return "[REDACTED]";
  }
  if (Array.isArray(value)) return value.map((item) => sanitizeEvidence(item, secrets));
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.entries(value).map(([childKey, childValue]) => [
      childKey,
      sanitizeEvidence(childValue, secrets, childKey),
    ]));
  }
  if (typeof value !== "string") return value;
  let safe = value
    .replace(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi, "[REDACTED_EMAIL]")
    .replace(/\+\d[\d ()-]{7,}\d/g, "[REDACTED_NUMBER]")
    .replace(/Bearer\s+\S+/gi, "Bearer [REDACTED]");
  for (const secret of secrets) safe = safe.split(secret).join("[REDACTED]");
  return safe.slice(0, 200);
}

async function requestJson(fetchImpl, url, options, signal) {
  const response = await fetchImpl(url, { ...(options || {}), signal });
  if (!response || !response.ok) fail("http_error", { http_status: Number(response && response.status) || 0 });
  try {
    return await response.json();
  } catch {
    fail("invalid_response", { json: false });
  }
}

function hashedRef(value) {
  return crypto.createHash("sha256").update(String(value || "")).digest("hex").slice(0, 12);
}

function healthBase(env) {
  if (env.LIFE_CALL_HEALTH_URL) return String(env.LIFE_CALL_HEALTH_URL).replace(/\/health\/?$/, "");
  if (env.RAILWAY_PUBLIC_DOMAIN) return `https://${String(env.RAILWAY_PUBLIC_DOMAIN).replace(/^https?:\/\//, "")}`;
  if (env.PUBLIC_WSS) return String(env.PUBLIC_WSS).replace(/^wss:/, "https:").replace(/^ws:/, "http:").replace(/\/$/, "");
  return String(env.PUBLIC_BASE || "").replace(/\/$/, "");
}

function supabaseHeaders(env) {
  return {
    apikey: env.SUPABASE_SERVICE_ROLE_KEY,
    Authorization: `Bearer ${env.SUPABASE_SERVICE_ROLE_KEY}`,
  };
}

async function currentComposioUser(env, fetchImpl, signal) {
  requireEnv(env, ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"]);
  const url = `${env.SUPABASE_URL}/rest/v1/lm_users?paid=is.true&calendar_provider=eq.composio_gcal&select=uid&limit=1`;
  const rows = await requestJson(fetchImpl, url, { headers: supabaseHeaders(env) }, signal);
  const user = Array.isArray(rows) && rows[0];
  if (!user || !user.uid) fail("state_unavailable", { current_user: false });
  return user;
}

async function healthCheck(env, fetchImpl, signal) {
  const base = healthBase(env);
  if (!base) fail("configuration", { configured: false });
  const body = await requestJson(fetchImpl, `${base}/health`, {}, signal);
  if (!body || body.ok !== true || body.service !== "life-call") fail("unhealthy", { healthy: false });
  return { ok: true, evidence: { service: "life-call", healthy: true, build: String(body.build || "unreported") } };
}

async function telegramCheck(env, fetchImpl, signal) {
  requireEnv(env, ["LM_TELEGRAM_BOT_TOKEN", "LM_TELEGRAM_WEBHOOK_SECRET"]);
  const token = env.LM_TELEGRAM_BOT_TOKEN;
  const body = await requestJson(fetchImpl, `https://api.telegram.org/bot${token}/getWebhookInfo`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: "{}",
  }, signal);
  const info = body && body.result;
  const allowed = Array.isArray(info && info.allowed_updates) ? info.allowed_updates : [];
  let webhookHost = "";
  try { webhookHost = new URL(info && info.url).hostname; } catch {}
  const pending = Number(info && info.pending_update_count);
  const missingUpdates = REQUIRED_TELEGRAM_UPDATES.filter((name) => !allowed.includes(name));
  if (body.ok !== true || !webhookHost || !Number.isFinite(pending) || pending !== 0 ||
      info.last_error_message || info.last_error_date || missingUpdates.length) {
    fail("webhook_not_ready", {
      webhook_configured: Boolean(webhookHost),
      pending_updates: Number.isFinite(pending) ? pending : -1,
      last_error: Boolean(info && (info.last_error_message || info.last_error_date)),
      missing_update_count: missingUpdates.length,
    });
  }
  return {
    ok: true,
    evidence: {
      webhook_host: webhookHost,
      pending_updates: pending,
      last_error: false,
      allowed_updates: [...allowed].sort(),
      webhook_auth_configured: true,
    },
  };
}

async function calendarCheck(env, fetchImpl, signal, nowMs) {
  requireEnv(env, ["COMPOSIO_API_KEY"]);
  const user = await currentComposioUser(env, fetchImpl, signal);
  const body = await requestJson(fetchImpl, COMPOSIO_EXEC, {
    method: "POST",
    headers: { "x-api-key": env.COMPOSIO_API_KEY, "Content-Type": "application/json" },
    body: JSON.stringify({
      user_id: user.uid,
      arguments: {
        calendarId: "primary",
        singleEvents: true,
        orderBy: "startTime",
        timeMin: new Date(nowMs).toISOString(),
        timeMax: new Date(nowMs + 24 * 60 * 60 * 1000).toISOString(),
        maxResults: 1,
      },
    }),
  }, signal);
  const items = body && body.data && (body.data.items || body.data.events);
  if (body.successful !== true || !Array.isArray(items)) fail("calendar_read_failed", { authenticated_read: false });
  return {
    ok: true,
    evidence: { transport: "composio", authenticated_read: true, item_count: items.length, user_ref: hashedRef(user.uid) },
  };
}

async function callCheck(env, fetchImpl, signal) {
  requireEnv(env, ["TELNYX_API_KEY", "TELNYX_PHONE_NUMBER", "TELNYX_CONNECTION_ID"]);
  const headers = { Authorization: `Bearer ${env.TELNYX_API_KEY}` };
  const balanceBody = await requestJson(fetchImpl, `${TELNYX_BASE}/balance`, { headers }, signal);
  const balance = Number(balanceBody && balanceBody.data && balanceBody.data.balance);
  if (!Number.isFinite(balance) || balance < 0.5) fail("balance_not_ready", { minimum_met: false });

  const digits = String(env.TELNYX_PHONE_NUMBER).replace(/\D/g, "");
  const numberBody = await requestJson(fetchImpl,
    `${TELNYX_BASE}/phone_numbers?filter%5Bphone_number%5D=${encodeURIComponent(digits)}&page%5Bsize%5D=10`,
    { headers }, signal);
  const assigned = Array.isArray(numberBody && numberBody.data)
    ? numberBody.data.find((item) => String(item.phone_number || "").replace(/\D/g, "") === digits)
    : null;
  if (!assigned || assigned.status !== "active") fail("number_not_ready", { number_assigned: Boolean(assigned), active: false });

  const appBody = await requestJson(fetchImpl,
    `${TELNYX_BASE}/call_control_applications/${encodeURIComponent(env.TELNYX_CONNECTION_ID)}`,
    { headers }, signal);
  const app = appBody && appBody.data;
  const profileConfigured = Boolean(app && app.outbound && app.outbound.outbound_voice_profile_id);
  if (!app || app.id !== env.TELNYX_CONNECTION_ID || app.active !== true || !profileConfigured) {
    fail("call_control_not_ready", { active: Boolean(app && app.active), outbound_profile_configured: profileConfigured });
  }
  return {
    ok: true,
    evidence: {
      auth_balance: true,
      minimum_balance_met: true,
      currency: String((balanceBody.data && balanceBody.data.currency) || "unknown"),
      number_assigned: true,
      number_status: "active",
      call_control_active: true,
      outbound_profile_configured: true,
      webhook_configured: Boolean(app.webhook_event_url),
      dial_attempted: false,
    },
  };
}

async function locationCheck(env, fetchImpl, signal, nowMs) {
  const user = await currentComposioUser(env, fetchImpl, signal);
  const url = `${env.SUPABASE_URL}/rest/v1/lm_user_locations?uid=eq.${encodeURIComponent(user.uid)}` +
    "&select=observed_at,expires_at&limit=1";
  const rows = await requestJson(fetchImpl, url, { headers: supabaseHeaders(env) }, signal);
  if (!Array.isArray(rows)) fail("location_read_failed", { schema_read: false });
  const row = rows[0] || null;
  const expiresAt = Date.parse(row && row.expires_at);
  const state = !row ? "absent" : Number.isFinite(expiresAt) && expiresAt > nowMs ? "fresh" : "expired";
  return {
    ok: true,
    evidence: { schema_read: true, current_user_state: state, row_present: Boolean(row), user_ref: hashedRef(user.uid), write_attempted: false },
  };
}

function fromDomain(value) {
  const match = /@([^>\s]+)>?\s*$/.exec(String(value || ""));
  return match ? match[1].toLowerCase() : "";
}

async function emailCheck(env, fetchImpl, signal) {
  requireEnv(env, ["RESEND_API_KEY", "LM_MAIL_FROM"]);
  const domain = fromDomain(env.LM_MAIL_FROM);
  if (!domain) fail("from_not_ready", { from_domain_configured: false });
  const body = await requestJson(fetchImpl, RESEND_DOMAINS, {
    headers: { Authorization: `Bearer ${env.RESEND_API_KEY}` },
  }, signal);
  const domains = Array.isArray(body && body.data) ? body.data : [];
  const record = domains.find((item) => String(item.name || "").toLowerCase() === domain);
  if (!record || record.status !== "verified") fail("domain_not_ready", { from_domain: domain, verified: false });
  return {
    ok: true,
    evidence: { auth: true, from_domain: domain, domain_status: "verified", send_attempted: false },
  };
}

async function discoveryCheck(env, fetchImpl, signal, nowMs) {
  requireEnv(env, ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "LM_TELEGRAM_BOT_TOKEN"]);
  const config = discoveryMessage("location");
  const callback = config && config.extra && config.extra.reply_markup && config.extra.reply_markup.inline_keyboard;
  if (!GATE_ORDER.includes("location") || !Array.isArray(callback)) fail("discovery_config", { config_ready: false });
  const select = "uid,telegram_chat_id,last_discovery_at,last_discovery_gate,payout_destination";
  const url = `${env.SUPABASE_URL}/rest/v1/lm_users?telegram_chat_id=not.is.null&select=${select}&limit=1`;
  const rows = await requestJson(fetchImpl, url, { headers: supabaseHeaders(env) }, signal);
  const user = Array.isArray(rows) && rows[0];
  if (!user || !user.uid || !user.telegram_chat_id) fail("discovery_state", { eligible_user: false });
  const lastMs = Date.parse(user.last_discovery_at);
  const due = !Number.isFinite(lastMs) || lastMs <= nowMs - 7 * 24 * 60 * 60 * 1000;
  return {
    ok: true,
    evidence: {
      bot_configured: true,
      state_schema_read: true,
      eligible_user: true,
      user_ref: hashedRef(user.uid),
      last_discovery_state: Number.isFinite(lastMs) ? "set" : "never",
      current_due_state: due ? "due" : "throttled",
      last_gate: GATE_ORDER.includes(user.last_discovery_gate) ? user.last_discovery_gate : "none",
      notification_attempted: false,
    },
  };
}

async function geminiCheck(env, fetchImpl, signal) {
  requireEnv(env, ["GEMINI_API_KEY"]);
  const body = await requestJson(fetchImpl,
    `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(LIVE_MODEL)}`,
    { headers: { "x-goog-api-key": env.GEMINI_API_KEY } }, signal);
  const methods = Array.isArray(body && body.supportedGenerationMethods) ? body.supportedGenerationMethods : [];
  if (!String(body && body.name || "").endsWith(LIVE_MODEL) || !methods.includes("bidiGenerateContent")) {
    fail("model_not_ready", { model_available: false, bidi_supported: methods.includes("bidiGenerateContent") });
  }
  return {
    ok: true,
    evidence: { model: LIVE_MODEL, model_available: true, bidi_supported: true, generation_attempted: false },
  };
}

async function mapsCheck(env, fetchImpl, signal, nowMs) {
  const key = env.LIFE_MAPS_KEY || env.GOOGLE_API_KEY;
  if (!key) fail("configuration", { configured: false });
  const routesBody = await requestJson(fetchImpl, "https://routes.googleapis.com/directions/v2:computeRoutes", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Goog-Api-Key": key, "X-Goog-FieldMask": "routes.duration" },
    body: JSON.stringify({
      origin: { location: { latLng: { latitude: 35.681236, longitude: 139.767125 } } },
      destination: { location: { latLng: { latitude: 35.628471, longitude: 139.73876 } } },
      travelMode: "DRIVE",
      routingPreference: "TRAFFIC_AWARE_OPTIMAL",
      departureTime: new Date(nowMs + 60_000).toISOString(),
    }),
  }, signal);
  const routeDuration = routesBody && routesBody.routes && routesBody.routes[0] && routesBody.routes[0].duration;
  if (!routeDuration) fail("routes_not_ready", { routes_api: false });

  const params = new URLSearchParams({
    origin: "35.681236,139.767125",
    destination: "35.628471,139.738760",
    mode: "transit",
    departure_time: "now",
    key,
  });
  const legacyBody = await requestJson(fetchImpl,
    `https://maps.googleapis.com/maps/api/directions/json?${params.toString()}`, {}, signal);
  const leg = legacyBody && legacyBody.routes && legacyBody.routes[0] && legacyBody.routes[0].legs && legacyBody.routes[0].legs[0];
  if (legacyBody.status !== "OK" || !leg) fail("directions_not_ready", { directions_api: false });
  return {
    ok: true,
    evidence: { routes_api: true, directions_api: true, drive_duration_reported: true, transit_duration_reported: true, write_attempted: false },
  };
}

function createDependencyChecks({ env = process.env, fetchImpl = fetch, nowMs = Date.now() } = {}) {
  const secrets = secretValues(env);
  return [
    { name: "health", run: ({ signal }) => healthCheck(env, fetchImpl, signal) },
    { name: "telegram", run: ({ signal }) => telegramCheck(env, fetchImpl, signal) },
    { name: "calendar", run: ({ signal }) => calendarCheck(env, fetchImpl, signal, nowMs) },
    { name: "call", run: ({ signal }) => callCheck(env, fetchImpl, signal) },
    { name: "location", run: ({ signal }) => locationCheck(env, fetchImpl, signal, nowMs) },
    { name: "email", run: ({ signal }) => emailCheck(env, fetchImpl, signal) },
    { name: "discovery", run: ({ signal }) => discoveryCheck(env, fetchImpl, signal, nowMs) },
    { name: "gemini", run: ({ signal }) => geminiCheck(env, fetchImpl, signal) },
    { name: "maps", run: ({ signal }) => mapsCheck(env, fetchImpl, signal, nowMs) },
  ].map((check) => ({ ...check, secrets }));
}

async function runOne(check, timeoutMs, now) {
  const startedAt = now();
  const controller = new AbortController();
  let timer;
  try {
    const result = await Promise.race([
      Promise.resolve().then(() => check.run({ signal: controller.signal })),
      new Promise((_, reject) => {
        timer = setTimeout(() => {
          controller.abort();
          reject(TIMEOUT);
        }, timeoutMs);
      }),
    ]);
    if (!result || result.ok !== true || !result.evidence || Array.isArray(result.evidence) ||
        typeof result.evidence !== "object" || Object.keys(result.evidence).length === 0) {
      const explicit = result && result.ok === false;
      return {
        dependency: check.name,
        status: "fail",
        latencyMs: Math.max(0, now() - startedAt),
        evidence: sanitizeEvidence(explicit && result.evidence && Object.keys(result.evidence).length
          ? result.evidence : { reason: explicit ? "dependency_error" : "invalid_result" }, check.secrets),
        failureClass: explicit ? String(result.failureClass || "dependency_error") : "invalid_result",
      };
    }
    return {
      dependency: check.name,
      status: "pass",
      latencyMs: Math.max(0, now() - startedAt),
      evidence: sanitizeEvidence(result.evidence, check.secrets),
      failureClass: null,
    };
  } catch (error) {
    const timedOut = error === TIMEOUT;
    const classification = timedOut ? "timeout"
      : error instanceof PreflightFailure ? error.classification : "dependency_error";
    const evidence = error instanceof PreflightFailure && error.evidence && Object.keys(error.evidence).length
      ? error.evidence : { reason: classification };
    return {
      dependency: check.name,
      status: timedOut ? "timeout" : "fail",
      latencyMs: Math.max(0, now() - startedAt),
      evidence: sanitizeEvidence(evidence, check.secrets),
      failureClass: classification,
    };
  } finally {
    clearTimeout(timer);
  }
}

async function runPreflight({ checks, timeoutMs = 15000, now = Date.now } = {}) {
  if (!Array.isArray(checks) || checks.length === 0) throw new Error("preflight checks required");
  const dependencies = await Promise.all(checks.map((check) => runOne(check, timeoutMs, now)));
  const passed = dependencies.filter((item) => item.status === "pass").length;
  const failed = dependencies.filter((item) => item.status === "fail").length;
  const timedOut = dependencies.filter((item) => item.status === "timeout").length;
  const exitCode = passed === dependencies.length ? 0 : 1;
  return {
    schemaVersion: 1,
    kind: "life-call-daily-preflight",
    generatedAt: new Date(now()).toISOString(),
    timeoutMs,
    overallStatus: exitCode === 0 ? "pass" : "fail",
    exitCode,
    summary: { required: dependencies.length, passed, failed, timedOut },
    dependencies,
  };
}

module.exports = {
  DEPENDENCY_NAMES,
  createDependencyChecks,
  runPreflight,
  sanitizeEvidence,
};
