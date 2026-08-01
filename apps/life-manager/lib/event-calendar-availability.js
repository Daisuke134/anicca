"use strict";

const EVENT_REF = /^[a-z][a-z0-9+.-]*:\/\/[^\s]{3,500}$/i;

function instant(value, label) {
  const milliseconds = Date.parse(String(value || ""));
  if (!Number.isFinite(milliseconds)) throw new Error(`event calendar ${label} invalid`);
  return milliseconds;
}

function minutes(value) {
  return Number.isInteger(value) && value >= 0 && value <= 360 ? value : null;
}

function mergeIntervals(intervals) {
  const sorted = intervals.slice().sort((left, right) => left.start_ms - right.start_ms || left.end_ms - right.end_ms);
  const merged = [];
  for (const interval of sorted) {
    const last = merged.at(-1);
    if (last && interval.start_ms <= last.end_ms) {
      last.end_ms = Math.max(last.end_ms, interval.end_ms);
    } else {
      merged.push({ ...interval });
    }
  }
  return merged;
}

function evaluateEventCalendarAvailability(input = {}) {
  const windowStart = instant(input.window_start, "window");
  const windowEnd = instant(input.window_end, "window");
  if (windowEnd <= windowStart) throw new Error("event calendar window invalid");
  const calendars = input.freebusy && input.freebusy.calendars;
  if (!calendars || typeof calendars !== "object" || Array.isArray(calendars)) {
    throw new Error("event calendar freebusy incomplete");
  }
  const entries = Object.entries(calendars);
  if (entries.length < 1) throw new Error("event calendar freebusy incomplete");
  const busy = [];
  for (const [calendarId, value] of entries) {
    if (!calendarId || !value || typeof value !== "object" || Array.isArray(value) || (Array.isArray(value.errors) && value.errors.length > 0)) {
      throw new Error("event calendar freebusy incomplete");
    }
    if (value.busy != null && !Array.isArray(value.busy)) throw new Error("event calendar busy invalid");
    for (const interval of value.busy || []) {
      const startMs = instant(interval && interval.start, "busy");
      const endMs = instant(interval && interval.end, "busy");
      if (endMs <= startMs) throw new Error("event calendar busy invalid");
      if (endMs <= windowStart || startMs >= windowEnd) continue;
      busy.push({ start_ms: Math.max(startMs, windowStart), end_ms: Math.min(endMs, windowEnd) });
    }
  }
  const merged = mergeIntervals(busy);
  if (!Array.isArray(input.candidates)) throw new Error("event calendar candidates invalid");
  const eligible = [];
  const conflicts = [];
  const seen = new Set();
  for (const candidate of input.candidates) {
    const eventRef = String(candidate && candidate.event_ref || "").trim();
    const startMs = instant(candidate && candidate.start_at, "candidate");
    const endMs = instant(candidate && candidate.end_at, "candidate");
    const before = minutes(candidate && candidate.travel_before_minutes);
    const after = minutes(candidate && candidate.travel_after_minutes);
    if (!EVENT_REF.test(eventRef) || seen.has(eventRef) || endMs <= startMs || before == null || after == null) {
      throw new Error("event calendar candidate invalid");
    }
    seen.add(eventRef);
    const occupiedStart = startMs - before * 60_000;
    const occupiedEnd = endMs + after * 60_000;
    if (occupiedStart < windowStart || occupiedEnd > windowEnd) {
      conflicts.push(Object.freeze({ event_ref: eventRef, reason: "outside_window" }));
      continue;
    }
    const collision = merged.find((interval) => occupiedStart < interval.end_ms && occupiedEnd > interval.start_ms);
    if (collision) {
      conflicts.push(Object.freeze({
        event_ref: eventRef,
        reason: "busy_conflict",
        busy_start: new Date(collision.start_ms).toISOString(),
        busy_end: new Date(collision.end_ms).toISOString(),
      }));
      continue;
    }
    eligible.push(eventRef);
  }
  return Object.freeze({
    schema_version: 1,
    window_start: new Date(windowStart).toISOString(),
    window_end: new Date(windowEnd).toISOString(),
    calendar_count: entries.length,
    busy_interval_count: busy.length,
    merged_busy_intervals: Object.freeze(merged.map((interval) => Object.freeze({
      start: new Date(interval.start_ms).toISOString(),
      end: new Date(interval.end_ms).toISOString(),
    }))),
    eligible_event_refs: Object.freeze(eligible),
    conflicts: Object.freeze(conflicts),
  });
}

module.exports = { evaluateEventCalendarAvailability };
