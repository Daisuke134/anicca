// life-travel.js — Netlify function for B-travel (spec27 WF-B B-travel).
//
// Triggered by POST from Anicca's heartbeat (schedule-derived trigger, spec27 §2 patch).
// Reads the user's primary GCal, calls Google Maps Directions for travel time,
// and inserts "[Travel] <event>" blocks before any event that is missing one.
//
// Pattern mirrors telemetry.js — handler validates env, delegates to pure logic.
//
// Auth: accepts GOOGLE_CALENDAR_TOKEN (static short-lived) OR
//       GOOGLE_REFRESH_TOKEN + GOOGLE_CLIENT_ID + GOOGLE_CLIENT_SECRET
//       (auto-refreshed via OAuth2 endpoint — see _lib/gcal-token.js).

const { detectMissingTravelBlocks, buildTravelBlock } = require("./_lib/travel-logic");
const { getAccessToken } = require("./_lib/gcal-token");

// ── GCal REST helpers ──────────────────────────────────────────────────────────

/**
 * Fetch today's events from a Google Calendar using the REST API.
 */
async function listTodayEvents(calendarId, token) {
  const now = new Date();
  const timeMin = new Date(now.getFullYear(), now.getMonth(), now.getDate()).toISOString();
  const timeMax = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1).toISOString();

  const url =
    `https://www.googleapis.com/calendar/v3/calendars/${encodeURIComponent(calendarId)}/events` +
    `?timeMin=${encodeURIComponent(timeMin)}&timeMax=${encodeURIComponent(timeMax)}` +
    `&singleEvents=true&orderBy=startTime&maxResults=50`;

  const r = await fetch(url, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!r.ok) throw new Error(`GCal list ${r.status}: ${await r.text()}`);
  const body = await r.json();
  return body.items || [];
}

/**
 * Insert a single event into the calendar.
 */
async function insertEvent(calendarId, eventBody, token) {
  const url = `https://www.googleapis.com/calendar/v3/calendars/${encodeURIComponent(calendarId)}/events`;
  const r = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(eventBody),
  });
  if (!r.ok) throw new Error(`GCal insert ${r.status}: ${await r.text()}`);
  return r.json();
}

// ── Google Maps Directions helper ─────────────────────────────────────────────

/**
 * Returns travel duration in seconds from `origin` to `destination`.
 * Falls back to DEFAULT_TRAVEL_SEC if the Maps API is unavailable or
 * the destination has no address.
 */
const DEFAULT_TRAVEL_SEC = 20 * 60; // 20 minutes default

async function getTravelDuration(origin, destination, mapsKey) {
  if (!destination || !mapsKey) return DEFAULT_TRAVEL_SEC;

  const url =
    `https://maps.googleapis.com/maps/api/directions/json` +
    `?origin=${encodeURIComponent(origin)}&destination=${encodeURIComponent(destination)}` +
    `&mode=transit&key=${encodeURIComponent(mapsKey)}`;

  try {
    const r = await fetch(url);
    if (!r.ok) return DEFAULT_TRAVEL_SEC;
    const body = await r.json();
    const leg = body?.routes?.[0]?.legs?.[0];
    return leg?.duration?.value || DEFAULT_TRAVEL_SEC;
  } catch {
    return DEFAULT_TRAVEL_SEC;
  }
}

// ── Handler ────────────────────────────────────────────────────────────────────

exports.handler = async (event) => {
  // Only POST (triggered by heartbeat)
  if (event.httpMethod !== "POST") return { statusCode: 405, body: "method not allowed" };

  let token;
  try {
    token = await getAccessToken();
  } catch (err) {
    return { statusCode: 500, body: `auth_error: ${err.message}` };
  }

  const mapsKey = process.env.GOOGLE_MAPS_API_KEY;
  const origin = process.env.HOME_ADDRESS || "Tokyo, Japan";
  const calendarId = process.env.GCAL_ID || "primary";

  let events;
  try {
    events = await listTodayEvents(calendarId, token);
  } catch (err) {
    return { statusCode: 502, body: `gcal_list_error: ${err.message}` };
  }

  const missing = detectMissingTravelBlocks(events);
  const inserted = [];

  for (const ev of missing) {
    // Parse start time
    const startMs = new Date(ev.start.dateTime).getTime();
    const startSec = Math.round(startMs / 1000);

    // Get travel duration from Maps API (or default 20 min)
    const destination = ev.location || null;
    const durationSec = await getTravelDuration(origin, destination, mapsKey);

    // Build the travel block resource
    const { calendarId: _cid, ...eventBody } = buildTravelBlock({
      calendarId,
      eventTitle: ev.summary,
      eventStart: startSec,
      durationSec,
    });

    try {
      const created = await insertEvent(calendarId, eventBody, token);
      inserted.push({ id: created.id, for: ev.summary, durationMin: Math.round(durationSec / 60) });
    } catch (err) {
      // Log and continue — partial success is better than hard failure
      inserted.push({ error: err.message, for: ev.summary });
    }
  }

  return {
    statusCode: 200,
    body: JSON.stringify({
      ok: true,
      checked: events.length,
      inserted,
    }),
  };
};
