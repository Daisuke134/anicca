// lib/travel.js — cloud travel-time auto-fill. For a user, look at today→+7d of located events and
// insert a "[Travel]" block before each one so the wake call fires before they must LEAVE. Ports
// travel/travel_fill.py to the Railway service: Google Directions for the leave time, Composio for the
// gcal read + write. Origin priority: previous event's location (back-to-back) → the user's home.
// Idempotent: never inserts a second [Travel] for an event that already has one.
"use strict";

const { getCalendar } = require("./transport/index.js");

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
function isOnlineLocation(loc) {
  // A URL / video-call link / phone-only "location" is NOT a place to travel to — routing it
  // wastes a Directions call (always null) and must never block-spam. meet/zoom/teams/webex + any
  // http(s)/tel scheme. Source: real Dais calendar had "https://meet.google.com/…" as a location.
  return /^(https?:\/\/|tel:)/i.test(loc) ||
    /\b(meet\.google\.|zoom\.us|teams\.microsoft\.|webex\.|whereby\.com|\bonline\b)/i.test(loc);
}

function travelDecision(ev, prev, home) {
  const norm = (s) => (s || "").replace(/\s+/g, "").toLowerCase();
  if (!ev || isTravel(ev.summary) || !((ev.location || "").trim())) {
    return { insert: false, origin: null, reason: "helper-or-no-location" };
  }
  if (isOnlineLocation(ev.location.trim())) {
    return { insert: false, origin: null, reason: "online" };
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

async function listEvents7d(uid, apiKey, nowMs, calendar) {
  const cal = calendar || getCalendar({ apiKey });
  const items = await cal.listEventsRaw(uid, {
    timeMin: new Date(nowMs).toISOString().replace(/\.\d{3}Z$/, "Z"),
    timeMax: new Date(nowMs + 7 * 86400 * 1000).toISOString().replace(/\.\d{3}Z$/, "Z"),
  });
  return items.map((e) => ({
    summary: e.summary || "",
    location: e.location || "",
    startMs: Date.parse((e.start || {}).dateTime || ""),
    endMs: Date.parse((e.end || {}).dateTime || ""),
  })).filter((e) => Number.isFinite(e.startMs));
}

// ── #71 Routes API helpers (pure, unit-tested in travel-routes.test.js) ──────────────────────────
// DRIVE now uses Routes API computeRoutes with TRAFFIC_AWARE_OPTIMAL — REAL traffic, so the old ×1.4
// fudge is GONE. TRANSIT stays on legacy Directions: VERIFIED 2026-06-21 that Routes API TRANSIT
// returns no routes for our key/region (empty {} even between major stations), while legacy transit
// works. departureTime ≈ event start so we get the traffic the user will actually hit (never-late bias).
function parseDurationSeconds(s) {
  const m = /^(\d+)s$/.exec(String(s || "").trim());
  return m ? Number(m[1]) : null;
}
function minutesFromSeconds(sec) {
  if (!Number.isFinite(sec)) return null;
  return Math.max(5, Math.round(sec / 60));
}
function buildDriveBody(src, dst, departIso) {
  return {
    origin: { address: src }, destination: { address: dst },
    travelMode: "DRIVE", routingPreference: "TRAFFIC_AWARE_OPTIMAL", departureTime: departIso,
  };
}
function clampDepartIso(departAtMs, nowMs) {
  // Routes API rejects a departureTime in the past → floor to now+60s.
  const ms = Math.max(Number(departAtMs) || 0, (Number(nowMs) || 0) + 60000);
  return new Date(ms).toISOString().replace(/\.\d{3}Z$/, "Z");
}

async function routesDriveMinutes(src, dst, mapsKey, departAtMs, nowMs) {
  const body = JSON.stringify(buildDriveBody(src, dst, clampDepartIso(departAtMs, nowMs)));
  try {
    const r = await fetch("https://routes.googleapis.com/directions/v2:computeRoutes", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": mapsKey,
        "X-Goog-FieldMask": "routes.duration",
      },
      body,
    });
    if (!r.ok) return null;
    const j = await r.json();
    const sec = parseDurationSeconds((((j.routes || [])[0]) || {}).duration);
    return sec == null ? null : minutesFromSeconds(sec);
  } catch { return null; }
}

async function legacyTransitMinutes(src, dst, mapsKey, arriveByMs, nowMs = Date.now()) {
  const p = new URLSearchParams({ origin: src, destination: dst, mode: "transit", key: mapsKey });
  // NEVER-LATE: anchor transit to the EVENT, not "now". Future event → arrival_time = event start, so
  // the train time reflects the schedule the user will actually ride. Past/missing → fall back to now.
  if (Number.isFinite(arriveByMs) && arriveByMs > nowMs) p.set("arrival_time", String(Math.floor(arriveByMs / 1000)));
  else p.set("departure_time", "now");
  try {
    const r = await fetch(`https://maps.googleapis.com/maps/api/directions/json?${p}`);
    const j = await r.json();
    if (j.status !== "OK" || !j.routes || !j.routes[0] || !j.routes[0].legs || !j.routes[0].legs[0]) return null;
    return minutesFromSeconds(j.routes[0].legs[0].duration.value);
  } catch { return null; }
}

// Query BOTH transit (anchored to event start) and traffic-aware drive, then take the LARGER —
// never-late bias: we don't yet know the user's mode, so assume the slower so we never under-estimate.
// departAtMs ≈ event start. Returns null only if neither mode resolves (caller then asks). floor 5 min.
// TODO(#69/#70): per-user travel_mode preference → trust the chosen mode instead of max().
async function directionsMinutes(src, dst, mapsKey, departAtMs = Date.now(), nowMs = Date.now()) {
  if (!mapsKey || !src || !dst) return null;
  const [transit, drive] = await Promise.all([
    legacyTransitMinutes(src, dst, mapsKey, departAtMs, nowMs),
    routesDriveMinutes(src, dst, mapsKey, departAtMs, nowMs),
  ]);
  const cands = [transit, drive].filter((n) => n != null);
  return cands.length ? Math.max(...cands) : null;
}

async function createTravelBlock(uid, apiKey, leaveMs, arriveMs, fromName, toName, dstAddr, calendar) {
  const cal = calendar || getCalendar({ apiKey });
  const hours = Math.floor((arriveMs - leaveMs) / 3600000);
  const minutes = Math.round(((arriveMs - leaveMs) % 3600000) / 60000);
  const j = await cal.createEvent(uid, {
    summary: `[Travel] 🚆 ${shortName(fromName)}→${shortName(toName)}`,
    start_datetime: isoNaiveUTC(leaveMs),
    event_duration_hour: hours, event_duration_minutes: Math.min(59, minutes),
    calendar_id: "primary", timezone: "UTC", location: dstAddr,
    description: "Auto-inserted by Anicca Life Manager — adjust if the route is wrong.",
  });
  return !!(j && j.successful);
}

// Returns { inserted, checked, skipped }. home = lm_users.home_address (may be null → first-of-day
// located events are skipped this run and should be handled by the ask-loop separately).
async function fillTravel(uid, { apiKey, mapsKey, home, nowMs = Date.now(), bufferMin = 5, calendar } = {}) {
  const cal = calendar || getCalendar({ apiKey });
  const events = await listEvents7d(uid, apiKey, nowMs, cal);
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
    const mins = await directionsMinutes(origin, ev.location, mapsKey, ev.startMs, nowMs);
    if (mins == null) { skipped++; continue; }
    const arriveMs = ev.startMs;
    const leaveMs = arriveMs - (mins + bufferMin) * 60000;
    if (leaveMs < nowMs) { skipped++; continue; } // already past the leave time
    if (await createTravelBlock(uid, apiKey, leaveMs, arriveMs, origin, ev.location, ev.location)) inserted++;
    else skipped++;
  }
  return { inserted, checked, skipped };
}

module.exports = {
  fillTravel, directionsMinutes, isTravel, travelDecision, isOnlineLocation,
  // #71 pure helpers (unit-tested)
  parseDurationSeconds, minutesFromSeconds, buildDriveBody, clampDepartIso,
};
