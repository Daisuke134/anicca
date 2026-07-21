// LM-33b: authenticated, read-only JSON model for the Life Manager panel.
"use strict";

const { cookieValue, sessionUid } = require("./panel-auth.js");
const { interpretCalendarEvent } = require("./calendar-interpreter.js");
const { getCalendar } = require("./transport/index.js");
const { lockedDiscoveryGates } = require("./feature-discovery.js");
const { DISCOVERY_STRINGS } = require("./i18n.js");

const ENDPOINTS = new Set(["timeline", "scores", "ledger", "gates", "settings"]);
const CALL_MINUTES_BEFORE = Object.freeze([10, 5]);

function headers(key) {
  return { apikey: key, Authorization: `Bearer ${key}` };
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
    const body = await response.json().catch(() => ({}));
    if (optional && (response.status === 404 || body.code === "PGRST205" || body.code === "42P01")) {
      return { rows: [], missing: true };
    }
    throw new Error(`panel ${table} read failed (${response.status})`);
  }
  const rows = await response.json().catch(() => []);
  return { rows: Array.isArray(rows) ? rows : [], missing: false };
}

async function readUser(uid, select, opts) {
  const { rows } = await readRows("lm_users", { uid: `eq.${uid}`, select, limit: "1" }, opts);
  return rows[0] || null;
}

function finite(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : 0;
}

function rounded(value) {
  return Number(value.toFixed(12));
}

async function timeline(uid, opts) {
  const timeZone = configuredTimeZone(opts.timeZone);
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
  return {
    call_language: user && user.call_language || null,
    call_schedule: {
      time_zone: configuredTimeZone(opts.timeZone),
      minutes_before: [...CALL_MINUTES_BEFORE],
      wake_policy: user && user.wake_policy || "travel-only",
    },
    connections: {
      calendar: Boolean(user && user.calendar_provider),
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

async function handlePanelApiRequest(req, res, opts = {}) {
  const path = new URL(req.url || "/", "http://panel.local").pathname;
  const endpoint = path.startsWith("/api/panel/") ? path.slice("/api/panel/".length) : "";
  if (!ENDPOINTS.has(endpoint)) {
    sendJson(res, 404, { error: "not_found" });
    return;
  }

  const session = cookieValue(req.headers.cookie, "lm_panel_session");
  const nowMs = opts.nowMs == null ? Date.now() : opts.nowMs;
  const resolveSession = opts.sessionUidImpl || sessionUid;
  const uid = await resolveSession(session, {
    supaUrl: opts.supaUrl,
    supaKey: opts.supaKey,
    fetchImpl: opts.fetchImpl,
    now: () => new Date(nowMs),
  });
  if (!uid) {
    sendJson(res, 401, { error: "unauthorized" });
    return;
  }
  if (req.method !== "GET") {
    sendJson(res, 405, { error: "method_not_allowed" }, { Allow: "GET" });
    return;
  }

  const readers = { timeline, scores, ledger, gates, settings };
  sendJson(res, 200, await readers[endpoint](uid, { ...opts, nowMs }));
}

module.exports = {
  CALL_MINUTES_BEFORE,
  todayBounds,
  aggregateCosts,
  handlePanelApiRequest,
};
