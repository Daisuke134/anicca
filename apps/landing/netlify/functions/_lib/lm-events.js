// _lib/lm-events.js — read a Life Manager user's upcoming Google Calendar events through their
// Composio managed-OAuth connection (the SAME path /lm's calendar-connect.js sets up:
// Composio user_id === the lm_users uid). Mirrors the proven Python reader in
// apps/alarm-backend/scheduler/saas_lateness.py::fetch_composio_events, in JS for the Netlify
// cloud wake scheduler (life-call). No per-user Google API token needed — Composio holds it.
//
// Contract:
//   fetchUpcomingEvents(uid, { nowMs?, horizonH=18, apiKey? }) -> Promise<Event[]>
//     Event = { summary: string, location: string|null, startMs: number, startIso: string }
//     - timed events only (all-day date-only events are skipped — no leave time to compute)
//     - filtered to [now, now+horizonH], sorted ascending by start
//     - [] on: no API key, connection not ACTIVE, Composio error, or no qualifying events
//   fetchNextEvent(uid, opts) -> Promise<Event|null>  (the soonest upcoming timed event)
"use strict";

const COMPOSIO_EXEC =
  "https://backend.composio.dev/api/v3/tools/execute/GOOGLECALENDAR_EVENTS_LIST";

function isoZ(ms) {
  return new Date(ms).toISOString().replace(/\.\d{3}Z$/, "Z");
}

async function fetchUpcomingEvents(uid, opts = {}) {
  const apiKey = opts.apiKey || process.env.COMPOSIO_API_KEY;
  if (!apiKey || !uid) return [];
  const nowMs = opts.nowMs || Date.now();
  const horizonH = opts.horizonH || 18;
  const horizonMs = nowMs + horizonH * 3600 * 1000;

  const body = JSON.stringify({
    user_id: uid,
    arguments: {
      calendarId: "primary",
      singleEvents: true,
      orderBy: "startTime",
      timeMin: isoZ(nowMs),
      timeMax: isoZ(horizonMs),
    },
  });

  let j;
  try {
    const r = await fetch(COMPOSIO_EXEC, {
      method: "POST",
      headers: { "x-api-key": apiKey, "Content-Type": "application/json" },
      body,
    });
    j = await r.json();
  } catch {
    return []; // network error — caller treats as "no events this tick"
  }
  if (!j || !j.successful) return []; // not connected / Composio error

  const data = j.data || {};
  const items = data.items || data.events || [];
  const out = [];
  for (const e of items) {
    const raw = (e.start || {}).dateTime; // timed events only; date-only (all-day) skipped
    if (!raw) continue;
    const startMs = Date.parse(raw);
    if (Number.isNaN(startMs)) continue;
    if (startMs < nowMs || startMs > horizonMs) continue;
    out.push({
      summary: e.summary || "予定",
      location: e.location || null,
      startMs,
      startIso: raw,
    });
  }
  out.sort((a, b) => a.startMs - b.startMs);
  return out;
}

async function fetchNextEvent(uid, opts = {}) {
  const events = await fetchUpcomingEvents(uid, opts);
  return events.length ? events[0] : null;
}

module.exports = { fetchUpcomingEvents, fetchNextEvent };
