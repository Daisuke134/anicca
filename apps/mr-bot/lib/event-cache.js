"use strict";
// lib/event-cache.js — spec 2026-08-01-lm-daily-organ-design.md §3.1 (method A).
//
// A hand-off between two timers in ONE process: the wake tick fetches the calendar and publishes
// here, the organ tick reads. It exists for one reason — lib/calendar-cache.js keys on a minute
// bucket derived from `now`, so two loops on different phases would each pay a real Composio call.
// Owning the fetch in one place keeps call volume exactly where it was before the split.
//
// Deliberately NOT durable: a restart simply means the first organ tick fetches once. Anything that
// must survive a restart belongs in Supabase, not here.

// The organ tick runs at most every 5 minutes, and the wake tick republishes every 60s, so entries
// are normally under a minute old. The TTL is the honesty boundary: past it, a reader must fetch
// rather than act on a calendar that may have changed.
const EVENT_CACHE_TTL_MS = Number(process.env.LM_EVENT_CACHE_TTL_MS) || 5 * 60_000;

const cache = new Map(); // uid -> { events, atMs }

function putEvents(uid, events, nowMs) {
  if (!uid) return;
  cache.set(String(uid), { events, atMs: nowMs == null ? Date.now() : nowMs });
}

// null means "you must fetch" — never confuse it with [] ("fetched, the user has no events").
function getEvents(uid, nowMs) {
  const entry = cache.get(String(uid || ""));
  if (!entry) return null;
  const now = nowMs == null ? Date.now() : nowMs;
  if (now - entry.atMs > EVENT_CACHE_TTL_MS) return null;
  return entry.events;
}

function clearEvents() {
  cache.clear();
}

module.exports = { putEvents, getEvents, clearEvents, EVENT_CACHE_TTL_MS };
