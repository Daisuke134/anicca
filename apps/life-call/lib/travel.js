// lib/travel.js — cloud travel-time auto-fill. For a user, look at today→+7d of located events and
// insert a "[Travel]" block before each one so the wake call fires before they must LEAVE. Ports
// travel/travel_fill.py to the Railway service: Google Directions for the leave time, Composio for the
// gcal read + write. Origin priority: previous event's location (back-to-back) → the user's home.
// Idempotent: never inserts a second [Travel] for an event that already has one.
"use strict";

const COMPOSIO = "https://backend.composio.dev/api/v3";

function isoNaiveUTC(ms) {
  // Timezone-agnostic: pass the UTC wall clock paired with timezone:"UTC" (set in createTravelBlock).
  // Google stores the correct ABSOLUTE instant and shows it in each user's own timezone — so this
  // works for a user in Tokyo, New York, or anywhere, with no hardcoded offset.
  return new Date(ms).toISOString().replace(/\.\d{3}Z$/, "").replace("Z", "");
}
function isTravel(summary) {
  const s = summary || "";
  return s.startsWith("[Travel]") || s.includes("🚆 移動");
}

// PURE travel decision (no network) — the single source of truth for "does this event need a
// [Travel] block, and from where". Unit-tested so the home→home guard can never silently regress.
// Returns { insert: boolean, origin: string|null, reason: string }.
function travelDecision(ev, prev, home) {
  const norm = (s) => (s || "").replace(/\s+/g, "").toLowerCase();
  if (!ev || isTravel(ev.summary) || !((ev.location || "").trim())) {
    return { insert: false, origin: null, reason: "helper-or-no-location" };
  }
  // Origin = previous event's location if it ends within [0,90] min before this one (back-to-back) AND
  // the previous event is a REAL event (not one of Anicca's own [Travel] helper blocks); else home.
  const gap = prev && prev.endMs ? ev.startMs - prev.endMs : Infinity;
  const origin = prev && prev.location && !isTravel(prev.summary) && gap >= 0 && gap <= 90 * 60000
    ? prev.location : home;
  if (!origin) return { insert: false, origin: null, reason: "no-origin" }; // home unknown → ask-loop handles it
  if (norm(origin) === norm(ev.location)) return { insert: false, origin, reason: "same-location" }; // home→home etc.
  return { insert: true, origin, reason: "travel-needed" };
}
function shortName(addr) {
  return (addr || "").split(/[,、]/)[0].slice(0, 18) || "?";
}

async function listEvents7d(uid, apiKey, nowMs) {
  const body = JSON.stringify({
    user_id: uid,
    arguments: {
      calendarId: "primary", singleEvents: true, orderBy: "startTime",
      timeMin: new Date(nowMs).toISOString().replace(/\.\d{3}Z$/, "Z"),
      timeMax: new Date(nowMs + 7 * 86400 * 1000).toISOString().replace(/\.\d{3}Z$/, "Z"),
    },
  });
  let j;
  try {
    const r = await fetch(`${COMPOSIO}/tools/execute/GOOGLECALENDAR_EVENTS_LIST`, {
      method: "POST", headers: { "x-api-key": apiKey, "Content-Type": "application/json" }, body });
    j = await r.json();
  } catch { return []; }
  if (!j || !j.successful) return [];
  const items = (j.data || {}).items || [];
  return items.map((e) => ({
    summary: e.summary || "",
    location: e.location || "",
    startMs: Date.parse((e.start || {}).dateTime || ""),
    endMs: Date.parse((e.end || {}).dateTime || ""),
  })).filter((e) => Number.isFinite(e.startMs));
}

async function directionsMinutes(src, dst, mapsKey) {
  if (!mapsKey || !src || !dst) return null;
  for (const mode of ["transit", "driving"]) {
    const p = new URLSearchParams({ origin: src, destination: dst, mode, key: mapsKey });
    if (mode === "transit") p.set("departure_time", "now");
    try {
      const r = await fetch(`https://maps.googleapis.com/maps/api/directions/json?${p}`);
      const j = await r.json();
      if (j.status !== "OK") continue;
      const sec = j.routes[0].legs[0].duration.value;
      let mins = Math.max(5, Math.round(sec / 60));
      if (mode === "driving") mins = Math.round(mins * 1.4);
      return mins;
    } catch { /* try next mode */ }
  }
  return null;
}

async function createTravelBlock(uid, apiKey, leaveMs, arriveMs, fromName, toName, dstAddr) {
  const hours = Math.floor((arriveMs - leaveMs) / 3600000);
  const minutes = Math.round(((arriveMs - leaveMs) % 3600000) / 60000);
  const body = JSON.stringify({
    user_id: uid,
    arguments: {
      summary: `[Travel] 🚆 ${shortName(fromName)}→${shortName(toName)}`,
      start_datetime: isoNaiveUTC(leaveMs),
      event_duration_hour: hours, event_duration_minutes: Math.min(59, minutes),
      calendar_id: "primary", timezone: "UTC", location: dstAddr,
      description: "Auto-inserted by Anicca Life Manager — adjust if the route is wrong.",
    },
  });
  try {
    const r = await fetch(`${COMPOSIO}/tools/execute/GOOGLECALENDAR_CREATE_EVENT`, {
      method: "POST", headers: { "x-api-key": apiKey, "Content-Type": "application/json" }, body });
    const j = await r.json();
    return !!j.successful;
  } catch { return false; }
}

// Returns { inserted, checked, skipped }. home = lm_users.home_address (may be null → first-of-day
// located events are skipped this run and should be handled by the ask-loop separately).
async function fillTravel(uid, { apiKey, mapsKey, home, nowMs = Date.now(), bufferMin = 5 } = {}) {
  const events = await listEvents7d(uid, apiKey, nowMs);
  let inserted = 0, checked = 0, skipped = 0;
  for (let i = 0; i < events.length; i++) {
    const ev = events[i];
    if (isTravel(ev.summary) || !ev.location) continue;
    checked++;
    // Single source of truth for the skip/insert decision (home→home, no-origin, etc.).
    const decision = travelDecision(ev, events[i - 1], home);
    if (!decision.insert) { skipped++; continue; }
    const origin = decision.origin;
    // Dedup: a [Travel] block already sitting in the gap right before this event?
    const dup = events.some((e) => isTravel(e.summary) && e.endMs && e.endMs <= ev.startMs && e.endMs > ev.startMs - 3 * 3600000);
    if (dup) { skipped++; continue; }
    const mins = await directionsMinutes(origin, ev.location, mapsKey);
    if (mins == null) { skipped++; continue; }
    const arriveMs = ev.startMs;
    const leaveMs = arriveMs - (mins + bufferMin) * 60000;
    if (leaveMs < nowMs) { skipped++; continue; } // already past the leave time
    if (await createTravelBlock(uid, apiKey, leaveMs, arriveMs, origin, ev.location, ev.location)) inserted++;
    else skipped++;
  }
  return { inserted, checked, skipped };
}

module.exports = { fillTravel, directionsMinutes, isTravel, travelDecision };
