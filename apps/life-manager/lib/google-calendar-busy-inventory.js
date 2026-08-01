"use strict";

const { createHash } = require("node:crypto");

const DATE = /^\d{4}-\d{2}-\d{2}$/;
const VERIFIED = new WeakSet();

function invalid() { throw new Error("Google Calendar busy inventory invalid"); }
function unavailable() { throw new Error("Google Calendar busy inventory unavailable"); }

function exactInstant(value) {
  const text = String(value == null ? "" : value).trim();
  const ms = Date.parse(text);
  if (!Number.isFinite(ms) || !/[zZ]|[+-]\d\d:\d\d$/.test(text)) invalid();
  return new Date(ms).toISOString();
}

function dateKey(value) {
  const text = String(value == null ? "" : value).trim();
  if (!DATE.test(text) || new Date(`${text}T00:00:00Z`).toISOString().slice(0, 10) !== text) invalid();
  return text;
}

function safeIdentifier(value) {
  const text = String(value == null ? "" : value).trim();
  if (!text || text.length > 1_024 || /[\x00-\x1f\x7f]/.test(text)) invalid();
  return text;
}

function validTimeZone(value) {
  const timeZone = String(value == null ? "" : value).trim();
  try { new Intl.DateTimeFormat("en", { timeZone }).format(0); } catch { invalid(); }
  return timeZone;
}

function digest(value) {
  return createHash("sha256").update(String(value), "utf8").digest("hex");
}

function stableJson(value) {
  if (Array.isArray(value)) return `[${value.map(stableJson).join(",")}]`;
  if (value && typeof value === "object") {
    return `{${Object.keys(value).sort().map((key) => (
      `${JSON.stringify(key)}:${stableJson(value[key])}`
    )).join(",")}}`;
  }
  return JSON.stringify(value);
}

function normalizeBusyEvent(event, calendars, seen) {
  if (!event || typeof event !== "object" || Array.isArray(event)) invalid();
  const calendarId = safeIdentifier(event.CalendarID ?? event.calendarId ?? event.calendar_id);
  const eventId = safeIdentifier(event.id);
  if (!calendars.has(calendarId)) invalid();
  const identity = `${calendarId}\n${eventId}`;
  if (seen.has(identity)) invalid();
  seen.add(identity);
  if (String(event.status || "").toLowerCase() === "cancelled") return null;
  if (String(event.transparency || "").toLowerCase() === "transparent") return null;
  const calendarRef = `calendar-evidence://google/calendar/${digest(calendarId)}`;
  const eventRef = `calendar-evidence://google/event/${digest(identity)}`;
  if (event.start && event.end && event.start.dateTime != null && event.end.dateTime != null) {
    const startAt = exactInstant(event.start.dateTime);
    const endAt = exactInstant(event.end.dateTime);
    if (Date.parse(endAt) <= Date.parse(startAt)) invalid();
    return Object.freeze({
      kind: "timed",
      calendar_ref: calendarRef,
      event_ref: eventRef,
      start_at: startAt,
      end_at: endAt,
    });
  }
  if (event.start && event.end && event.start.date != null && event.end.date != null) {
    const startDate = dateKey(event.start.date);
    const endDate = dateKey(event.end.date);
    if (endDate <= startDate) invalid();
    return Object.freeze({
      kind: "all_day",
      calendar_ref: calendarRef,
      event_ref: eventRef,
      start_date: startDate,
      end_date: endDate,
    });
  }
  invalid();
}

async function inspectGoogleCalendarBusyInventory(options = {}) {
  const calendar = options.calendar;
  if (
    !calendar
    || typeof calendar.listCalendarsRaw !== "function"
    || typeof calendar.listAllEventsRaw !== "function"
  ) invalid();
  const timeMin = exactInstant(options.timeMin);
  const timeMax = exactInstant(options.timeMax);
  const observedAt = exactInstant(options.now);
  const timeZone = validTimeZone(options.timeZone);
  if (Date.parse(timeMax) <= Date.parse(timeMin)) invalid();
  let rawCalendars;
  let rawEvents;
  try {
    rawCalendars = await calendar.listCalendarsRaw({ strict: true });
    rawEvents = await calendar.listAllEventsRaw("dais-local", {
      timeMin: options.timeMin,
      timeMax: options.timeMax,
      maxResults: 2500,
      strict: true,
    });
  } catch { unavailable(); }
  if (!Array.isArray(rawCalendars) || !Array.isArray(rawEvents)) invalid();
  const calendars = new Set();
  for (const item of rawCalendars) {
    if (!item || typeof item !== "object" || Array.isArray(item)) invalid();
    const id = safeIdentifier(item.id);
    if (calendars.has(id)) invalid();
    calendars.add(id);
  }
  const seen = new Set();
  const busyIntervals = [];
  for (const event of rawEvents) {
    const interval = normalizeBusyEvent(event, calendars, seen);
    if (interval) busyIntervals.push(interval);
  }
  const core = {
    provider: "google-calendar",
    transport: "gog",
    time_zone: timeZone,
    time_min: timeMin,
    time_max: timeMax,
    observed_at: observedAt,
    calendar_count: calendars.size,
    source_event_count: rawEvents.length,
    busy_event_count: busyIntervals.length,
    excluded_event_count: rawEvents.length - busyIntervals.length,
    busy_intervals: Object.freeze(busyIntervals),
  };
  const snapshot = Object.freeze({
    busy_inventory_id: `google-calendar-busy-inventory:${digest(stableJson(core))}`,
    ...core,
  });
  VERIFIED.add(snapshot);
  return snapshot;
}

function isVerifiedGoogleCalendarBusyInventory(value) {
  return Boolean(value && typeof value === "object" && VERIFIED.has(value));
}

module.exports = {
  inspectGoogleCalendarBusyInventory,
  isVerifiedGoogleCalendarBusyInventory,
};
