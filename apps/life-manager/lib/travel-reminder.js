// Claimed T-5 event/travel Telegram reminder.
"use strict";

const crypto = require("node:crypto");
const { directionsRoute, claimTravel, unclaimTravel } = require("./travel.js");
const { isHelperBlock } = require("./wake-filter.js");
const { sendMessage } = require("./telegram.js");

const T5_MS = 5 * 60 * 1000;
const CATCH_UP_MS = 15 * 60 * 1000;
const REMINDER_LOOKBACK_MS = CATCH_UP_MS - T5_MS;
const PREVIOUS_EVENT_WINDOW_MS = 90 * 60 * 1000;
const DEFAULT_TIMEZONE = "Asia/Tokyo";

function toMs(value) {
  if (value instanceof Date) value = value.getTime();
  if (typeof value === "number") return Number.isFinite(value) ? value : null;
  if (typeof value === "string" && value.trim()) {
    const ms = Date.parse(value);
    return Number.isFinite(ms) ? ms : null;
  }
  return null;
}
function startMs(event) { return toMs(event && event.startMs); }
function endMs(event) { return toMs(event && event.endMs); }
function helper(event) { return Boolean(event && isHelperBlock(event.summary || "")); }
function physical(event) {
  const online = event && (event.online === true || event.isOnline === true);
  return Boolean(event && String(event.location || "").trim() && !online);
}

function travelHelper(event) {
  const summary = String(event && event.summary || "");
  return summary.startsWith("[Travel]") || summary.includes("🚆 移動");
}

function normalizeLocation(value) {
  return String(value || "").normalize("NFKC").replace(/[－ー‐‑–—]/g, "-").replace(/\s+/g, "").toLowerCase();
}

// A Travel block's end-window adjacency is not enough on its own: the same block can also fall in
// ANOTHER nearby timed event's [start-2min, start+1min] window (e.g. two back-to-back events with a
// single travel leg between them). If it matches more than one event's window, which one it belongs
// to is genuinely ambiguous, so fail closed to the event's own location rather than misattribute it.
function matchesOtherEventWindow(candidateEnd, events, event, candidate) {
  return events.some((other) => {
    if (!other || other === event || other === candidate) return false;
    if (other.id && (other.id === event.id || (candidate.id && other.id === candidate.id))) return false;
    if (helper(other)) return false;
    const otherStart = startMs(other);
    return otherStart !== null && candidateEnd >= otherStart - 2 * 60000 && candidateEnd <= otherStart + 60000;
  });
}

function resolveReminderDestination(event, { events = [], home } = {}) {
  const fallback = String(event && event.location || "").trim();
  const normalizedHome = normalizeLocation(home);
  const start = startMs(event), end = endMs(event);
  const list = Array.isArray(events) ? events : [];
  const matches = [];
  for (const candidate of list) {
    if (!candidate || candidate === event || (candidate.id && candidate.id === event.id) || !travelHelper(candidate)) continue;
    const candidateStart = startMs(candidate), candidateEnd = endMs(candidate);
    const location = String(candidate.location || "").trim();
    if (!location || (normalizedHome && normalizeLocation(location) === normalizedHome) || start === null || candidateStart === null || candidateEnd === null) continue;
    if (candidateEnd < start - 2 * 60000 || candidateEnd > start + 60000 || candidateStart > start || (end !== null && candidateStart >= end)) continue;
    if (matchesOtherEventWindow(candidateEnd, list, event, candidate)) continue;
    matches.push({ start: candidateStart, location });
  }
  return matches.length === 1 ? matches[0].location : fallback;
}

function nextReminderEvent(events, nowMs = Date.now()) {
  const now = toMs(nowMs);
  if (now === null) return null;
  return (Array.isArray(events) ? events : [])
    .filter((event) => startMs(event) !== null && startMs(event) >= now - REMINDER_LOOKBACK_MS && !helper(event))
    .sort((a, b) => startMs(a) - startMs(b))[0] || null;
}

function freshLive(location, nowMs) {
  if (!location || typeof location !== "object") return null;
  const lat = Number(location.latitude);
  const lon = Number(location.longitude);
  const observed = toMs(location.observedAtMs ?? location.observed_at);
  const expires = toMs(location.expiresAtMs ?? location.expires_at);
  const now = toMs(nowMs);
  if (!Number.isFinite(lat) || !Number.isFinite(lon) || observed === null || expires === null || now === null) return null;
  return expires > now && observed <= now ? { lat, lon } : null;
}

function resolveReminderOrigin(event, { events = [], liveLocation, home, nowMs = Date.now() } = {}) {
  const live = freshLive(liveLocation, nowMs);
  if (live) return { kind: "live", value: `geo:${live.lat},${live.lon}` };
  const start = startMs(event);
  let previous = null;
  for (const candidate of Array.isArray(events) ? events : []) {
    if (!candidate || candidate === event || (candidate.id && candidate.id === event.id) || helper(candidate)) continue;
    const location = String(candidate.location || "").trim();
    const end = endMs(candidate);
    if (!location || start === null || end === null || end > start || start - end > PREVIOUS_EVENT_WINDOW_MS) continue;
    if (!previous || end > previous.end) previous = { end, location };
  }
  if (previous) return { kind: "previous", value: previous.location };
  const address = String(home || "").trim();
  return address ? { kind: "home", value: address } : null;
}

function routeDuration(route) {
  const seconds = Number(route && route.durationSeconds);
  return Number.isFinite(seconds) && seconds >= 0 ? seconds : null;
}

function computeDepartureMs(event, route, { bufferMin = 5 } = {}) {
  const start = startMs(event);
  if (start === null || !physical(event)) return start;
  const duration = routeDuration(route);
  if (duration === null) return start;
  const buffer = Number(bufferMin);
  return start - duration * 1000 - (Number.isFinite(buffer) && buffer >= 0 ? buffer : 5) * 60000;
}

function computeReminderDueAt(event, { departureMs, route, bufferMin = 5 } = {}) {
  const departure = toMs(departureMs) ?? computeDepartureMs(event, route, { bufferMin });
  return departure === null ? null : departure - T5_MS;
}

function isReminderDue(nowMs, dueAt) {
  const now = toMs(nowMs);
  const due = toMs(dueAt);
  return now !== null && due !== null && now >= due && now <= due + CATCH_UP_MS;
}

function escapeHtml(value) {
  return String(value == null ? "" : value).replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/\"/g, "&quot;").replace(/'/g, "&#39;");
}

function timezone(value) {
  const zone = String(value || "").trim() || DEFAULT_TIMEZONE;
  try { new Intl.DateTimeFormat("en", { timeZone: zone }).format(0); return zone; }
  catch { return DEFAULT_TIMEZONE; }
}
function timeText(value, zone) {
  const ms = toMs(value);
  return ms === null ? null : new Intl.DateTimeFormat("ja-JP", {
    timeZone: timezone(zone), hour: "2-digit", minute: "2-digit", hourCycle: "h23",
  }).format(new Date(ms));
}
function stopText(stop) {
  if (!stop || typeof stop !== "object" || !String(stop.name || "").trim()) return null;
  const platform = String(stop.platform || "").trim();
  return escapeHtml(String(stop.name).trim()) + (platform ? ` ${escapeHtml(platform)}` : "");
}
function stepText(step, transitIndex, zone) {
  if (!step || step.kind === "walk" || step.mode === "walk") return null;
  const from = stopText(step.from), to = stopText(step.to);
  const depart = timeText(step.departAt, zone), arrive = timeText(step.arriveAt, zone);
  if (!from || !to || !depart || !arrive) return null;
  const service = [step.service, step.trainType, step.headsign].filter((v) => v != null && String(v).trim())
    .map((v) => escapeHtml(String(v).trim())).join("・");
  if (!service) return `${depart} ${from} → ${arrive} ${to}`;
  return transitIndex === 0 ? `${depart} ${from}\n${service} → ${arrive} ${to}`
    : `${depart} ${from}から${service} → ${arrive} ${to}`;
}
function walkText(route) {
  const values = [route && route.accessWalkSeconds, route && route.egressWalkSeconds]
    .filter((v) => v !== null && v !== undefined && v !== "").map(Number).filter(Number.isFinite);
  if (!values.length && Array.isArray(route && route.steps)) {
    for (const step of route.steps) {
      if (!step || (step.kind !== "walk" && step.mode !== "walk")) continue;
      const from = toMs(step.departAt), to = toMs(step.arriveAt);
      if (from !== null && to !== null && to >= from) values.push((to - from) / 1000);
    }
  }
  return values.length ? `徒歩 ${Math.max(0, Math.round(values.reduce((a, b) => a + b, 0) / 60))}分` : null;
}
function fareText(fare) {
  if (!fare || typeof fare !== "object") return null;
  const currency = String(fare.currency || "").trim().toUpperCase();
  const suffix = currency === "JPY" || !currency ? "円" : ` ${escapeHtml(currency)}`;
  const ic = fare.ic === null || fare.ic === undefined || fare.ic === "" ? null : Number(fare.ic);
  const ticket = fare.ticket === null || fare.ticket === undefined || fare.ticket === "" ? null : Number(fare.ticket);
  if (Number.isFinite(ic)) return `IC ${escapeHtml(ic)}${suffix}`;
  if (Number.isFinite(ticket)) return `切符 ${escapeHtml(ticket)}${suffix}`;
  return null;
}

function formatTravelReminder(event, route, { departureMs, timezone: zone = DEFAULT_TIMEZONE, routeAttempted } = {}) {
  const start = startMs(event);
  if (start === null) return "";
  const departure = toMs(departureMs) ?? computeDepartureMs(event, route);
  const lines = [`🚆 次は ${timeText(start, zone)}「${escapeHtml(event.summary || "予定")}」`];
  if (departure !== null) lines.push(`${timeText(departure, zone)} 出発 → ${timeText(start, zone)} 到着予定`);
  const destination = physical(event) ? String(event.location || "").trim() : "";
  if (destination) lines.push(`目的地: ${escapeHtml(destination)}`);
  const attempted = routeAttempted === undefined ? physical(event) : routeAttempted === true;
  if (!route) return attempted ? lines.concat("", "経路を取得できませんでした。").join("\n") : lines.join("\n");
  const rendered = [], steps = Array.isArray(route.steps) ? route.steps : [];
  let index = 0;
  for (const step of steps) {
    const text = stepText(step, index, zone);
    if (text) { rendered.push(text); index += 1; }
  }
  if (rendered.length) lines.push("", ...rendered);
  const facts = [walkText(route)];
  const transfers = route.transferCount === null || route.transferCount === undefined || route.transferCount === ""
    ? null : Number(route.transferCount);
  if (Number.isFinite(transfers)) facts.push(`乗換 ${transfers}回`);
  facts.push(fareText(route.fare));
  const present = facts.filter(Boolean);
  if (present.length) lines.push(present.join(" / "));
  lines.push("", "※ 出口番号は経路元が返した場合だけ表示します。運行情報が変わることがあります。");
  return lines.join("\n");
}

function eventKey(event) {
  return String(event.id || `${startMs(event) === null ? "unknown" : startMs(event)}:${event.summary || ""}`);
}

async function travelReminderOnce(user, nowMs = Date.now(), deps = {}) {
  const now = toMs(nowMs), chatId = String(user && user.telegram_chat_id || "").trim();
  if (!user || !user.uid || !chatId || user.notifications_enabled === false || now === null) return { status: "skipped" };
  const token = deps.telegramToken !== undefined ? deps.telegramToken : process.env.LM_TELEGRAM_BOT_TOKEN;
  if (!token) return { status: "skipped", reason: "telegram-unconfigured" };
  const supaUrl = deps.supaUrl !== undefined ? deps.supaUrl : process.env.SUPABASE_URL;
  const supaKey = deps.supaKey !== undefined ? deps.supaKey : process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!supaUrl || !supaKey) return { status: "skipped", reason: "travel-ledger-unconfigured" };
  const events = Array.isArray(deps.events) ? deps.events : [];
  const event = nextReminderEvent(events, now);
  if (!event) return { status: "suppressed", reason: "no-event" };
  const home = deps.home !== undefined ? deps.home : user.home_address;
  const origin = resolveReminderOrigin(event, {
    events, liveLocation: deps.liveLocation,
    home, nowMs: now,
  });
  const routeAttempted = physical(event) && Boolean(origin);
  const destination = resolveReminderDestination(event, { events, home });
  let route = null;
  if (routeAttempted) {
    try {
      route = await (deps.directionsRoute || directionsRoute)(origin.value, destination, deps.mapsKey,
        startMs(event), now, false, { uid: user.uid, timezone: deps.timezone || user.call_time_zone });
    } catch { route = null; }
  }
  const departureMs = computeDepartureMs(event, route, { bufferMin: deps.bufferMin });
  const dueAt = computeReminderDueAt(event, { departureMs });
  if (!isReminderDue(now, dueAt)) return { status: "suppressed", reason: "not-due", dueAt };
  const key = eventKey(event);
  let claimed = false;
  try { claimed = await (deps.claimTravel || claimTravel)(user.uid, key, "telegram-t5", supaUrl, supaKey); }
  catch { return { status: "suppressed", reason: "claim-failed" }; }
  if (!claimed) return { status: "suppressed", reason: "duplicate" };
  let response = null;
  try { response = await (deps.sendMessage || sendMessage)(token, chatId, formatTravelReminder(event, route, {
    departureMs, timezone: deps.timezone || user.call_time_zone || DEFAULT_TIMEZONE, routeAttempted,
  })); } catch { /* release below */ }
  const status = Number(response && response.status);
  const ok = Boolean(response && response.ok === true && (!Number.isFinite(status) || status >= 200 && status < 300));
  const messageId = response && response.result && response.result.message_id;
  if (!ok || messageId === null || messageId === undefined || messageId === "") {
    try { await (deps.unclaimTravel || unclaimTravel)(user.uid, key, "telegram-t5", supaUrl, supaKey); } catch { /* retry next tick */ }
    return { status: "send_failed", eventKey: key };
  }
  const provider = route && route.provider ? String(route.provider) : "none";
  (deps.log || console.log)(`[travel-reminder] uid=${String(user.uid).slice(0, 12)} event_key_hash=${crypto.createHash("sha256").update(key).digest("hex")} provider=${provider} tg_message_id=${messageId}`);
  return { status: "sent", eventKey: key, provider, telegramMessageId: messageId };
}

module.exports = {
  T5_MS, CATCH_UP_MS, isReminderDue, nextReminderEvent, resolveReminderOrigin,
  resolveReminderDestination, computeDepartureMs, computeReminderDueAt, formatTravelReminder, travelReminderOnce, escapeHtml,
};
