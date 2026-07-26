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

const { getCalendar } = require("./transport/index.js");
const { interpretCalendarEvent } = require("./calendar-interpreter.js");

function isoZ(ms) {
  return new Date(ms).toISOString().replace(/\.\d{3}Z$/, "Z");
}

async function fetchUpcomingEvents(uid, opts = {}) {
  if (!uid) return [];
  const nowMs = opts.nowMs || Date.now();
  const horizonH = opts.horizonH || 18;
  const horizonMs = nowMs + horizonH * 3600 * 1000;
  // 12c: the MENTAL trough trigger needs events that ALREADY ENDED (within TROUGH_AFTER_MS). A
  // timeMin=now window can never return one, which made between_events unreachable in production.
  // lookbackMs (default 0) widens the window backwards for that one caller; every other caller
  // keeps the strict-future contract unchanged.
  const lookbackMs = Number.isFinite(opts.lookbackMs) && opts.lookbackMs > 0 ? opts.lookbackMs : 0;

  // #74: calendar reads go through the transport adapter (composio cloud / gog local). Tests inject
  // their own via opts.calendar; production builds the env-selected one.
  const calendar = opts.calendar || getCalendar({ apiKey: opts.apiKey, gmailAccountId: opts.gmailAccountId });
  const items = await calendar.listEventsRaw(uid, { timeMin: isoZ(nowMs - lookbackMs), timeMax: isoZ(horizonMs) });
  const out = [];
  for (const e of items) {
    if (interpretCalendarEvent(e).decision === "no_call") continue;
    const raw = (e.start || {}).dateTime; // timed events only; date-only (all-day) skipped
    if (!raw) continue;
    const startMs = Date.parse(raw);
    if (Number.isNaN(startMs)) continue;
    if (startMs > horizonMs) continue;
    if (lookbackMs === 0) {
      if (startMs < nowMs) continue;
    } else {
      // keep an event iff it ends strictly after (nowMs - lookbackMs). Google's own timeMin
      // filter works on end time, so this mirrors the API contract for the widened window. A
      // malformed end.dateTime parses to NaN and falls back to the 1-hour default rather than
      // silently skipping the end-time check.
      const parsedEnd = (e.end || {}).dateTime ? Date.parse((e.end || {}).dateTime) : NaN;
      const endForFilter = Number.isFinite(parsedEnd) ? parsedEnd : startMs + 3600000;
      if (endForFilter <= nowMs - lookbackMs) continue;
    }
    const endRaw = (e.end || {}).dateTime;       // for the leave-time anchor (#69): match a [Travel]
    const endMs = endRaw ? Date.parse(endRaw) : NaN; // block whose endMs === a later event's startMs
    out.push({
      id: e.id || "",
      summary: e.summary || "予定",
      location: e.location || null,
      attendees: Array.isArray(e.attendees) ? e.attendees : [],
      startMs,
      startIso: raw,
      endMs: Number.isNaN(endMs) ? null : endMs,
      endIso: endRaw || null,
    });
  }
  out.sort((a, b) => a.startMs - b.startMs);
  return out;
}

async function fetchNextEvent(uid, opts = {}) {
  const events = await fetchUpcomingEvents(uid, opts);
  return events.length ? events[0] : null;
}

// 11a runtime: care detection needs the user's OWN visit HISTORY. fetchUpcomingEvents is
// future-only by contract (and rightly so — every wake/late consumer depends on it), which is the
// same unreachable-rule disease 12c had: the one thing the care detector needs (past visits) is the
// one thing that fetch can never return. This is a dedicated history read with its own contract
// (mirrors the lookbackMs precedent above rather than stretching it to 18 months):
//   - window = [now - historyMs, now], default ~18 months
//   - all-day (date-only) events are KEPT — a barber visit logged all-day is still a visit
//   - no interpretCalendarEvent filter — "no_call" is a call decision, not a history decision
//   - the raw `start` object survives so detectCalendarCare can parse dateTime/date itself
//   - STRICT reads: a transport/API failure PROPAGATES (throws) instead of returning []. The wake
//     path's swallow-to-[] is load-bearing there, but here the caller (careUserOnce) persists an
//     append-only once-per-day claim — "the read failed" must never look like "empty calendar",
//     or a single API blip freezes a fabricated empty scan for the whole day.
//   - CHUNKED window: one 548-day call with orderBy=startTime ascending + maxResults 2500 truncates
//     the RECENT end on busy calendars — exactly the events that hold the last-visit dates — turning
//     stale visits into false overdues. The transport wrapper exposes no pageToken, so the window is
//     split into ≤3 contiguous ~183-day chunks (each safely under 2500 for any human calendar) and
//     merged, deduped by id (a chunk-boundary event can appear in two chunks).
const CARE_HISTORY_MS = 548 * 86400000; // ~18 months
const HISTORY_CHUNK_MS = 183 * 86400000; // ~6 months per chunk

async function fetchCalendarHistory(uid, opts = {}) {
  if (!uid) return [];
  const nowMs = opts.nowMs || Date.now();
  const historyMs = Number.isFinite(opts.historyMs) && opts.historyMs > 0 ? opts.historyMs : CARE_HISTORY_MS;
  const calendar = opts.calendar || getCalendar({ apiKey: opts.apiKey, gmailAccountId: opts.gmailAccountId });
  const chunkCount = Math.min(3, Math.max(1, Math.ceil(historyMs / HISTORY_CHUNK_MS)));
  const chunkMs = Math.ceil(historyMs / chunkCount);
  const items = [];
  for (let i = 0; i < chunkCount; i += 1) {
    const chunkStart = nowMs - historyMs + i * chunkMs;
    const chunkEnd = Math.min(nowMs, chunkStart + chunkMs);
    const chunk = await calendar.listEventsRaw(uid, {
      timeMin: isoZ(chunkStart), timeMax: isoZ(chunkEnd), maxResults: 2500, strict: true,
    });
    for (const e of chunk || []) items.push(e);
  }
  const seen = new Set();
  const out = [];
  for (const e of items) {
    const id = e && typeof e.id === "string" ? e.id : "";
    if (!id || seen.has(id)) continue;
    seen.add(id);
    const raw = (e.start || {}).dateTime || (e.start || {}).date;
    const startMs = raw ? Date.parse(raw) : NaN;
    if (!Number.isFinite(startMs) || startMs > nowMs) continue; // history holds only real past visits
    out.push({ id, summary: e.summary || "", location: e.location || null, startMs, start: e.start });
  }
  out.sort((a, b) => a.startMs - b.startMs);
  return out;
}

module.exports = { fetchUpcomingEvents, fetchNextEvent, fetchCalendarHistory, CARE_HISTORY_MS };
