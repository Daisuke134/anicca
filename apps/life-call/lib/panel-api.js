// LM-33b: authenticated, read-only JSON model for the Life Manager panel.
"use strict";

const { cookieValue, csrfToken, panelScopeCookie, sessionScope, sessionUid } = require("./panel-auth.js");
const { buildControlCenter, claimCalendarOAuthState, executeUserCommand, validateCommand } = require("./user-command.js");
const { interpretCalendarEvent } = require("./calendar-interpreter.js");
const { getCalendar } = require("./transport/index.js");
const { lockedDiscoveryGates } = require("./feature-discovery.js");
const { DISCOVERY_STRINGS } = require("./i18n.js");

const ENDPOINTS = new Set(["timeline", "scores", "ledger", "gates", "settings"]);
const CALL_MINUTES_BEFORE = Object.freeze([10, 5]);

function headers(key) {
  return { apikey: key, Authorization: `Bearer ${key}` };
}

async function jsonOr(response, fallback) {
  try { return await response.json(); } catch { return fallback; }
}

function configuredTimeZone(value) {
  const candidate = String(value || "Asia/Tokyo");
  try {
    new Intl.DateTimeFormat("en", { timeZone: candidate }).format(0);
    return candidate;
  } catch {
    return "UTC";
  }
}

function zonedParts(ms, timeZone) {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone, year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23",
  }).formatToParts(new Date(ms));
  return Object.fromEntries(parts.filter((part) => part.type !== "literal").map((part) => [part.type, part.value]));
}

function dateKey(ms, timeZone) {
  const part = zonedParts(ms, timeZone);
  return `${part.year}-${part.month}-${part.day}`;
}

function zonedMidnightMs(key, timeZone) {
  const [year, month, day] = key.split("-").map(Number);
  const wallUtc = Date.UTC(year, month - 1, day);
  let instant = wallUtc;
  for (let pass = 0; pass < 2; pass++) {
    const part = zonedParts(instant, timeZone);
    const represented = Date.UTC(
      Number(part.year), Number(part.month) - 1, Number(part.day),
      Number(part.hour), Number(part.minute), Number(part.second),
    );
    instant = wallUtc - (represented - instant);
  }
  return instant;
}

function todayBounds(nowMs, timeZone) {
  const key = dateKey(nowMs, timeZone);
  const startMs = zonedMidnightMs(key, timeZone);
  const tomorrowKey = dateKey(startMs + 36 * 60 * 60 * 1000, timeZone);
  return { key, startMs, endMs: zonedMidnightMs(tomorrowKey, timeZone) };
}

async function readRows(table, params, opts = {}, optional = false) {
  if (!opts.supaUrl || !opts.supaKey) throw new Error("panel database is not configured");
  const url = new URL(`${String(opts.supaUrl).replace(/\/$/, "")}/rest/v1/${table}`);
  for (const [name, value] of Object.entries(params || {})) url.searchParams.set(name, value);
  const response = await (opts.fetchImpl || fetch)(url.toString(), { headers: headers(opts.supaKey) });
  if (!response.ok) {
    const body = await jsonOr(response, {});
    if (optional && (response.status === 404 || body.code === "PGRST205" || body.code === "42P01")) {
      return { rows: [], missing: true };
    }
    throw new Error(`panel ${table} read failed (${response.status})`);
  }
  const rows = await jsonOr(response, []);
  return { rows: Array.isArray(rows) ? rows : [], missing: false };
}

async function readUser(uid, select, opts) {
  const { rows } = await readRows("lm_users", { uid: `eq.${uid}`, select, limit: "1" }, opts);
  return rows[0] || null;
}

async function readPanelPreferences(uid, opts) {
  const { rows } = await readRows("lm_panel_preferences", { uid: `eq.${uid}`, select: "call_time_zone,call_enabled,notifications_enabled,daily_automation_enabled", limit: "1" }, opts, true);
  return rows[0] || {};
}

function finite(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : 0;
}

function rounded(value) {
  return Number(value.toFixed(12));
}

async function timeline(uid, opts) {
  const preferences = await readPanelPreferences(uid, opts);
  const timeZone = configuredTimeZone(preferences.call_time_zone || opts.timeZone);
  const nowMs = opts.nowMs == null ? Date.now() : opts.nowMs;
  const bounds = todayBounds(nowMs, timeZone);
  const user = await readUser(uid, "gmail_account_id", opts);
  const calendar = opts.calendar || getCalendar({
    apiKey: opts.composioKey || process.env.COMPOSIO_API_KEY,
    gmailAccountId: user && user.gmail_account_id,
  });
  const rawEvents = await calendar.listEventsRaw(uid, {
    timeMin: new Date(bounds.startMs).toISOString(),
    timeMax: new Date(bounds.endMs).toISOString(),
  });
  const sorted = (Array.isArray(rawEvents) ? rawEvents : []).slice().sort((left, right) => {
    const leftMs = Date.parse((left.start || {}).dateTime || (left.start || {}).date || "");
    const rightMs = Date.parse((right.start || {}).dateTime || (right.start || {}).date || "");
    return leftMs - rightMs;
  });
  const events = sorted.map((event, index) => ({
    id: event.id || "",
    summary: event.summary || "予定",
    start_at: (event.start || {}).dateTime || (event.start || {}).date || null,
    end_at: (event.end || {}).dateTime || (event.end || {}).date || null,
    location: event.location || null,
    interpretation: interpretCalendarEvent(event, {
      now: new Date(nowMs).toISOString(), timeZone,
      previousEvent: index > 0 ? sorted[index - 1] : null,
    }),
  }));
  const { rows: calls } = await readRows("lm_wake_log", {
    uid: `eq.${uid}`,
    called_at: `gte.${new Date(bounds.startMs).toISOString()}`,
    and: `(called_at.lt.${new Date(bounds.endMs).toISOString()})`,
    select: "event_key,called_at,answered_at",
    order: "called_at.asc",
  }, opts);
  return {
    date: bounds.key,
    timezone: timeZone,
    events,
    calls: calls.map((row) => ({
      event_key: row.event_key,
      called_at: row.called_at,
      answered_at: row.answered_at || null,
    })),
  };
}

async function scores(uid, opts) {
  const nowMs = opts.nowMs == null ? Date.now() : opts.nowMs;
  const { rows: calls } = await readRows("lm_wake_log", {
    uid: `eq.${uid}`,
    called_at: `gte.${new Date(nowMs - 7 * 86400000).toISOString()}`,
    and: `(called_at.lte.${new Date(nowMs).toISOString()})`,
    select: "called_at,answered_at",
  }, opts);
  const answered = calls.filter((row) => row.answered_at).length;
  const { rows: financialRows } = await readRows("lm_financial_ledger", {
    uid: `eq.${uid}`, select: "id", limit: "1",
  }, opts, true);
  return { organs: {
    daily: {
      score: calls.length ? Math.round(answered / calls.length * 100) : null,
      no_data: calls.length === 0,
      calls: calls.length,
      answered,
      window_days: 7,
    },
    physical: { score: null, no_data: true, unimplemented: true, missed_visits: 0 },
    financial: {
      score: financialRows.length ? 100 : null,
      no_data: financialRows.length === 0,
      ledger_entries: financialRows.length,
    },
  } };
}

function aggregateCosts(rows) {
  const result = { no_data: rows.length === 0, entries: rows.length, total_est_usd: 0, by_kind: {} };
  for (const row of rows) {
    const kind = String(row.kind || "unknown");
    const item = result.by_kind[kind] || { entries: 0, quantity: 0, est_usd: 0 };
    item.entries += 1;
    item.quantity += finite(row.quantity);
    item.est_usd += finite(row.est_usd);
    result.total_est_usd += finite(row.est_usd);
    result.by_kind[kind] = item;
  }
  result.total_est_usd = rounded(result.total_est_usd);
  for (const item of Object.values(result.by_kind)) {
    item.quantity = rounded(item.quantity);
    item.est_usd = rounded(item.est_usd);
  }
  return result;
}

async function ledger(uid, opts) {
  const { rows: costs } = await readRows("lm_api_cost", {
    uid: `eq.${uid}`, select: "ts,kind,quantity,unit,est_usd,meta", order: "ts.desc",
  }, opts);
  const financial = await readRows("lm_financial_ledger", {
    uid: `eq.${uid}`, select: "*", order: "ts.desc",
  }, opts, true);
  return {
    api_cost: aggregateCosts(costs),
    financial: { no_data: financial.rows.length === 0, entries: financial.rows },
  };
}

async function gates(uid, opts) {
  const nowMs = opts.nowMs == null ? Date.now() : opts.nowMs;
  const user = await readUser(uid, "payout_destination", opts);
  const { rows: locations } = await readRows("lm_user_locations", {
    uid: `eq.${uid}`, select: "uid,observed_at,expires_at", limit: "1",
  }, opts);
  const location = locations[0] || null;
  const locked = new Set(lockedDiscoveryGates({
    location,
    payoutDestination: user && user.payout_destination,
  }, nowMs));
  return { gates: [
    {
      id: "location",
      unlocked: !locked.has("location"),
      unlock_method: DISCOVERY_STRINGS.ja.location.text,
    },
    {
      id: "payout",
      unlocked: !locked.has("payout"),
      unlock_method: DISCOVERY_STRINGS.ja.payout.text,
    },
  ] };
}

async function settings(uid, opts) {
  const user = await readUser(uid,
    "call_language,wake_policy,calendar_provider,gmail_account_id,telegram_chat_id", opts);
  const preferences = await readPanelPreferences(uid, opts);
  let calendar = false;
  try { calendar = opts.scope ? await composioCalendarStatus(opts.scope, { ...opts, composioKey: opts.composioKey || process.env.COMPOSIO_API_KEY }) === "ACTIVE" : false; } catch { calendar = false; }
  return {
    call_language: user && user.call_language || null,
    call_schedule: {
      time_zone: configuredTimeZone(preferences.call_time_zone || opts.timeZone),
      minutes_before: [...CALL_MINUTES_BEFORE],
      wake_policy: user && user.wake_policy || "travel-only",
    },
    connections: {
      calendar,
      gmail: Boolean(user && user.gmail_account_id),
      telegram: Boolean(user && user.telegram_chat_id),
    },
  };
}

function sendJson(res, status, body, extraHeaders = {}) {
  res.writeHead(status, {
    "content-type": "application/json; charset=utf-8",
    "cache-control": "no-store",
    "x-content-type-options": "nosniff",
    ...extraHeaders,
  });
  res.end(JSON.stringify(body));
}

async function readJson(req) {
  return new Promise((resolve, reject) => {
    let raw = "", settled = false;
    const noop = () => {};
    const cleanup = () => { req.removeListener("data", onData); req.removeListener("end", onEnd); req.removeListener("error", onError); req.on("error", noop); };
    const fail = error => { if (settled) return; settled = true; raw = ""; cleanup(); reject(error); };
    const onData = chunk => { if (settled) return; raw += chunk; if (Buffer.byteLength(raw) > 32 * 1024) fail(Object.assign(new Error("body_too_large"), { status: 413 })); };
    const onEnd = () => { if (settled) return; settled = true; cleanup(); try { resolve(JSON.parse(raw || "{}")); } catch { reject(Object.assign(new Error("invalid_json"), { status: 400 })); } };
    const onError = error => fail(error);
    req.on("data", onData); req.on("end", onEnd); req.on("error", onError);
  });
}

function timingEqual(left, right) {
  const a = Buffer.from(String(left || "")), b = Buffer.from(String(right || ""));
  return a.length === b.length && a.length > 0 && require("node:crypto").timingSafeEqual(a, b);
}

function createSupabaseCommandStore(opts = {}) {
  const base = String(opts.supaUrl || "").replace(/\/$/, "");
  const fetchImpl = opts.fetchImpl || fetch;
  async function rows(table, query) {
    const response = await fetchImpl(`${base}/rest/v1/${table}?${query}`, { headers: headers(opts.supaKey) });
    if (!response.ok) throw new Error("panel_store_read_failed");
    const body = await jsonOr(response, []); return Array.isArray(body) ? body : [];
  }
  async function patch(table, scope, body) {
    const response = await fetchImpl(`${base}/rest/v1/${table}?uid=eq.${encodeURIComponent(scope.uid)}`, { method: "PATCH", headers: { ...headers(opts.supaKey), "content-type": "application/json", Prefer: "return=representation" }, body: JSON.stringify({ ...body, updated_at: new Date().toISOString() }) });
    if (!response.ok) throw new Error("panel_store_write_failed");
    const result = await jsonOr(response, []); return result[0] || body;
  }
  return {
    async assertCurrentScope(scope) { return Boolean((await rows("lm_users", new URLSearchParams({ uid: `eq.${scope.uid}`, telegram_chat_id: `eq.${scope.chatId}`, select: "uid", limit: "1" })))[0]); },
    async readUser(scope) { return (await rows("lm_users", new URLSearchParams({ uid: `eq.${scope.uid}`, telegram_chat_id: `eq.${scope.chatId}`, select: "uid,name,telegram_chat_id,phone,call_language,wake_policy,calendar_provider,gmail_account_id,payout_destination", limit: "1" })))[0] || null; },
    async readPreferences(scope) { return (await rows("lm_panel_preferences", new URLSearchParams({ uid: `eq.${scope.uid}`, select: "call_enabled,notifications_enabled,daily_automation_enabled,delegation_enabled,call_time_zone", limit: "1" })))[0] || {}; },
    async readLocation(scope) { return (await rows("lm_user_locations", new URLSearchParams({ uid: `eq.${scope.uid}`, select: "observed_at,expires_at", limit: "1" })))[0] || null; },
    async readReceipt(scope, key) { const row = (await rows("lm_panel_command_receipts", new URLSearchParams({ uid: `eq.${scope.uid}`, chat_id: `eq.${scope.chatId}`, idempotency_key: `eq.${key}`, select: "request_hash,status,result", limit: "1" })))[0]; return row ? { requestHash: row.request_hash, status: row.status, result: row.result } : null; },
    async claimReceipt(scope, key, value) { const response = await fetchImpl(`${base}/rest/v1/lm_panel_command_receipts`, { method: "POST", headers: { ...headers(opts.supaKey), "content-type": "application/json", Prefer: "return=minimal" }, body: JSON.stringify({ uid: scope.uid, chat_id: scope.chatId, idempotency_key: key, request_hash: value.requestHash, command_type: value.commandType, status: value.status }) }); if (response.status === 409) return false; if (!response.ok) throw new Error("panel_receipt_failed"); return true; },
    async finishReceipt(scope, key, value) { const response = await fetchImpl(`${base}/rest/v1/lm_panel_command_receipts?uid=eq.${encodeURIComponent(scope.uid)}&chat_id=eq.${encodeURIComponent(scope.chatId)}&idempotency_key=eq.${encodeURIComponent(key)}`, { method: "PATCH", headers: { ...headers(opts.supaKey), "content-type": "application/json", Prefer: "return=minimal" }, body: JSON.stringify({ status: value.status, result: value.result, updated_at: new Date().toISOString() }) }); if (!response.ok) throw new Error("panel_receipt_failed"); },
    async patchPreferences(scope, body) { const existing = await this.readPreferences(scope); if (!Object.keys(existing).length) { const response = await fetchImpl(`${base}/rest/v1/lm_panel_preferences`, { method: "POST", headers: { ...headers(opts.supaKey), "content-type": "application/json", Prefer: "resolution=merge-duplicates,return=representation" }, body: JSON.stringify({ uid: scope.uid, ...body }) }); if (!response.ok) throw new Error("panel_store_write_failed"); const result = await jsonOr(response, []); return result[0] || { ...existing, ...body }; } return patch("lm_panel_preferences", scope, body); },
    async patchUser(scope, body) { return patch("lm_users", scope, body); },
    async mutatePreferences(scope, body) { const response = await fetchImpl(`${base}/rest/v1/rpc/mutate_lm_panel_preferences`, { method: "POST", headers: { ...headers(opts.supaKey), "content-type": "application/json" }, body: JSON.stringify({ p_uid: scope.uid, p_chat_id: scope.chatId, p_patch: body }) }); if (!response.ok) throw new Error("scope_mismatch"); return jsonOr(response, body); },
    async mutateUser(scope, body) { const response = await fetchImpl(`${base}/rest/v1/rpc/mutate_lm_panel_user`, { method: "POST", headers: { ...headers(opts.supaKey), "content-type": "application/json" }, body: JSON.stringify({ p_uid: scope.uid, p_chat_id: scope.chatId, p_patch: body }) }); if (!response.ok) throw new Error("scope_mismatch"); return jsonOr(response, body); },
    async createOAuthState(scope, state) { const response = await fetchImpl(`${base}/rest/v1/lm_panel_oauth_states`, { method: "POST", headers: { ...headers(opts.supaKey), "content-type": "application/json", Prefer: "return=minimal" }, body: JSON.stringify({ state_hash: state.stateHash, uid: scope.uid, chat_id: scope.chatId, provider: state.provider, expires_at: state.expiresAt }) }); if (!response.ok) throw new Error("oauth_state_failed"); },
    async claimOAuthState(scope, stateHash) { const response = await fetchImpl(`${base}/rest/v1/rpc/claim_lm_panel_oauth_state`, { method: "POST", headers: { ...headers(opts.supaKey), "content-type": "application/json" }, body: JSON.stringify({ p_state_hash: stateHash, p_uid: scope.uid, p_chat_id: scope.chatId }) }); if (!response.ok) throw new Error("oauth_state_failed"); return jsonOr(response, false); },
  };
}

async function handlePanelOAuthCallback(req, res, opts = {}) {
  if (req.method !== "GET") { sendJson(res, 405, { error: "method_not_allowed" }, { Allow: "GET" }); return; }
  const session = cookieValue(req.headers.cookie, "__Host-lm_panel_session") || cookieValue(req.headers.cookie, "lm_panel_session");
  const scope = await (opts.sessionScopeImpl || sessionScope)(session, opts);
  if (!scope) { res.writeHead(401, { "content-type": "text/plain", "cache-control": "no-store" }); res.end("unauthorized"); return; }
  const renewedCookie = panelScopeCookie(scope);
  if (renewedCookie && typeof res.setHeader === "function") res.setHeader("Set-Cookie", renewedCookie);
  const state = new URL(req.url || "/", "http://panel.local").searchParams.get("state");
  const store = opts.commandStore || createSupabaseCommandStore(opts);
  if (store.assertCurrentScope && !await store.assertCurrentScope(scope)) { res.writeHead(401, { "content-type": "text/plain", "cache-control": "no-store" }); res.end("unauthorized"); return; }
  const claimed = await claimCalendarOAuthState(scope, state, { store });
  let verified = false;
  if (claimed) { try { verified = await composioCalendarStatus(scope, opts) === "ACTIVE"; } catch { verified = false; } }
  res.writeHead(verified ? 303 : 403, { ...(verified ? { Location: "/panel" } : {}), "cache-control": "no-store", "referrer-policy": "no-referrer" });
  res.end(verified ? "" : "calendar connection not verified");
}

function exactCalendarAccount(scope, item) {
  const owner = item && (item.user_id || item.userId || item.connection?.user_id);
  const toolkit = item && (item.toolkit_slug || item.toolkit?.slug || item.toolkit?.slug_name);
  return Boolean(item && item.id && String(owner) === String(scope.uid) && toolkit === "googlecalendar");
}

function sameEnabledCalendarAccount(item, id) {
  return Boolean(item && item.id === id && item.status === "ACTIVE" && item.is_disabled !== true && item.enabled === true);
}

function sameDisabledCalendarAccount(item, id) {
  return Boolean(item && item.id === id && item.status !== "ACTIVE" && item.is_disabled === true && item.enabled === false);
}

async function composioCalendarStatus(scope, opts = {}) {
  if (!opts.composioKey) return "INACTIVE";
  const response = await (opts.fetchImpl || fetch)(`https://backend.composio.dev/api/v3/connected_accounts?user_ids=${encodeURIComponent(scope.uid)}&toolkit_slugs=googlecalendar`, { headers: { "x-api-key": opts.composioKey } });
  if (!response.ok) throw new Error("provider_failed");
  const body = await jsonOr(response, {});
  const items = Array.isArray(body.items) ? body.items : [];
  if (items.length > 1) throw new Error("provider_ambiguous");
  if (items.length === 0) return "MISSING";
  if (!exactCalendarAccount(scope, items[0])) throw new Error("provider_ownership");
  return items[0].status === "ACTIVE" && items[0].is_disabled !== true && items[0].enabled !== false ? "ACTIVE" : "DISABLED";
}

async function composioCalendarAccounts(scope, opts = {}) {
  if (!opts.composioKey) throw new Error("provider_unavailable");
  const url = `https://backend.composio.dev/api/v3/connected_accounts?user_ids=${encodeURIComponent(scope.uid)}&toolkit_slugs=googlecalendar`;
  const response = await (opts.fetchImpl || fetch)(url, { headers: { "x-api-key": opts.composioKey } });
  if (!response.ok) throw new Error("provider_failed");
  const body = await jsonOr(response, {});
  const items = Array.isArray(body.items) ? body.items : [];
  if (items.some(item => !exactCalendarAccount(scope, item))) throw new Error("provider_ownership");
  return items;
}

async function composioCalendarDisconnect(scope, opts = {}) {
  const accounts = await composioCalendarAccounts(scope, opts);
  if (accounts.length === 0) return { provider: "calendar", state: "action_required" };
  if (accounts.length !== 1 || !accounts[0].id) throw new Error("provider_ambiguous");
  const account = accounts[0];
  if (account.status !== "ACTIVE" || account.is_disabled === true || account.enabled === false) return { provider: "calendar", state: "action_required" };
  const response = await (opts.fetchImpl || fetch)(`https://backend.composio.dev/api/v3/connected_accounts/${encodeURIComponent(account.id)}/status`, {
    method: "PATCH",
    headers: { "x-api-key": opts.composioKey, "content-type": "application/json" },
    body: JSON.stringify({ enabled: false }),
  });
  if (!response.ok) throw new Error("provider_failed");
  const readback = await composioCalendarAccounts(scope, opts);
  if (readback.length !== 1 || !sameDisabledCalendarAccount(readback[0], account.id)) {
    const rollback = await (opts.fetchImpl || fetch)(`https://backend.composio.dev/api/v3/connected_accounts/${encodeURIComponent(account.id)}/status`, { method: "PATCH", headers: { "x-api-key": opts.composioKey, "content-type": "application/json" }, body: JSON.stringify({ enabled: true }) });
    if (!rollback.ok) throw new Error("provider_rollback_failed");
    const restored = await composioCalendarAccounts(scope, opts);
    if (restored.length !== 1 || !sameEnabledCalendarAccount(restored[0], account.id)) throw new Error("provider_rollback_failed");
    throw new Error("provider_readback_failed");
  }
  return { provider: "calendar", state: "action_required" };
}

async function composioCalendarStart(scope, opts = {}) {
  const accounts = await composioCalendarAccounts(scope, opts);
  if (accounts.length === 0) return null;
  if (accounts.length !== 1 || !accounts[0].id) throw new Error("provider_ambiguous");
  const account = accounts[0];
  if (account.status === "ACTIVE" && account.is_disabled !== true && account.enabled !== false) return { provider: "calendar", state: "connected" };
  const response = await (opts.fetchImpl || fetch)(`https://backend.composio.dev/api/v3/connected_accounts/${encodeURIComponent(account.id)}/status`, {
    method: "PATCH",
    headers: { "x-api-key": opts.composioKey, "content-type": "application/json" },
    body: JSON.stringify({ enabled: true }),
  });
  if (!response.ok) throw new Error("provider_failed");
  const readback = await composioCalendarAccounts(scope, opts);
  if (readback.length !== 1 || !sameEnabledCalendarAccount(readback[0], account.id)) throw new Error("provider_readback_failed");
  return { provider: "calendar", state: "connected" };
}

async function handlePanelApiRequest(req, res, opts = {}) {
  const path = new URL(req.url || "/", "http://panel.local").pathname;
  const endpoint = path.startsWith("/api/panel/") ? path.slice("/api/panel/".length) : "";
  if (!ENDPOINTS.has(endpoint) && endpoint !== "control-center" && endpoint !== "commands") {
    sendJson(res, 404, { error: "not_found" });
    return;
  }

  const session = cookieValue(req.headers.cookie, "__Host-lm_panel_session") || cookieValue(req.headers.cookie, "lm_panel_session");
  const nowMs = opts.nowMs == null ? Date.now() : opts.nowMs;
  let scope;
  if (opts.sessionScopeImpl) scope = await opts.sessionScopeImpl(session, opts);
  else if (opts.sessionUidImpl) { const uid = await opts.sessionUidImpl(session, opts); scope = uid ? { uid, chatId: String(opts.sessionChatId || "legacy") } : null; }
  else scope = await sessionScope(session, {
    supaUrl: opts.supaUrl,
    supaKey: opts.supaKey,
    fetchImpl: opts.fetchImpl,
    now: () => new Date(nowMs),
  });
  if (!scope) {
    sendJson(res, 401, { error: "unauthorized" });
    return;
  }
  const renewedCookie = panelScopeCookie(scope);
  if (renewedCookie && typeof res.setHeader === "function") res.setHeader("Set-Cookie", renewedCookie);
  const commandStore = opts.commandStore || createSupabaseCommandStore(opts);
  if (!opts.sessionScopeImpl && !await commandStore.assertCurrentScope(scope)) {
    sendJson(res, 401, { error: "unauthorized" });
    return;
  }
  if (endpoint === "commands") {
    if (req.method !== "POST") { sendJson(res, 405, { error: "method_not_allowed" }, { Allow: "POST" }); return; }
    if (!/^application\/json(?:;|$)/i.test(String(req.headers["content-type"] || ""))) { sendJson(res, 415, { error: "json_required" }); return; }
    const expectedOrigin = String(opts.panelOrigin || opts.panelBaseUrl || "").replace(/\/$/, "");
    if (!expectedOrigin || String(req.headers.origin || "") !== expectedOrigin) { sendJson(res, 403, { error: "origin_rejected" }); return; }
    const expectedCsrf = scope.csrf || csrfToken(session);
    if (!timingEqual(req.headers["x-lm-csrf"], expectedCsrf)) { sendJson(res, 403, { error: "csrf_rejected" }); return; }
    const key = String(req.headers["idempotency-key"] || "");
    if (!/^[A-Za-z0-9._:-]{8,128}$/.test(key)) { sendJson(res, 400, { error: "idempotency_required" }); return; }
    try {
      const command = validateCommand(await readJson(req));
      const execute = opts.executeCommandImpl || executeUserCommand;
      const store = commandStore;
      const providerOpts = { ...opts, composioKey: opts.composioKey || process.env.COMPOSIO_API_KEY };
      const result = await execute(scope, command, { ...providerOpts, store, idempotencyKey: key, composioAuthConfig: opts.composioAuthConfig || process.env.COMPOSIO_GCAL_AUTH_CONFIG, startCalendarConnection: opts.startCalendarConnection || ((value) => composioCalendarStart(value, providerOpts)), disconnectCalendar: opts.disconnectCalendar || ((value) => composioCalendarDisconnect(value, providerOpts)) });
      sendJson(res, 200, result);
    } catch (error) { sendJson(res, error.status || 502, { error: error.message === "invalid_action" ? "invalid_action" : "command_failed" }); }
    return;
  }
  if (req.method !== "GET") {
    sendJson(res, 405, { error: "method_not_allowed" }, { Allow: "GET" });
    return;
  }

  if (endpoint === "control-center") {
    const store = commandStore;
    const model = await (opts.buildControlCenterImpl || buildControlCenter)(scope, { ...opts, store, nowMs, calendarStatus: opts.calendarStatus || ((value) => composioCalendarStatus(value, { ...opts, composioKey: opts.composioKey || process.env.COMPOSIO_API_KEY })) });
    sendJson(res, 200, { ...model, csrf: scope.csrf || csrfToken(session) }); return;
  }
  const readers = { timeline, scores, ledger, gates, settings };
  sendJson(res, 200, await readers[endpoint](scope.uid, { ...opts, nowMs, scope }));
}

module.exports = {
  CALL_MINUTES_BEFORE,
  todayBounds,
  aggregateCosts,
  createSupabaseCommandStore, readJson, composioCalendarStatus,
  composioCalendarDisconnect,
  composioCalendarStart,
  handlePanelOAuthCallback,
  handlePanelApiRequest,
};
