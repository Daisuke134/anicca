"use strict";

const { getCalendar } = require("./transport/index.js");
const { interpretCalendarEvent } = require("./calendar-interpreter.js");

function isoZ(ms) {
  return new Date(ms).toISOString().replace(/\.\d{3}Z$/u, "Z");
}

function providerTimezone(event) {
  const start = event && event.start;
  const end = event && event.end;
  return (event && (event.timezone || event.timeZone))
    || (start && (start.timeZone || start.timezone))
    || (end && (end.timeZone || end.timezone))
    || null;
}

async function fetchMobileUpcomingEvents(uid, options = {}) {
  if (!uid) return [];
  const nowMs = Number.isFinite(options.nowMs) ? options.nowMs : Date.now();
  const horizonH = Number.isFinite(options.horizonH) ? options.horizonH : 18;
  const composioUserId = options.composioUserId || options.calendarComposioUserId || uid;
  const connectedAccountId = options.connectedAccountId || options.gmailAccountId || null;
  const calendar = options.calendar || getCalendar({
    apiKey: options.apiKey,
    gmailAccountId: connectedAccountId,
    composioUserId,
    connectedAccountId,
  });
  const items = await calendar.listEventsRaw(uid, {
    timeMin: isoZ(nowMs), timeMax: isoZ(nowMs + horizonH * 3600 * 1000),
    connectedAccountId,
  });
  const output = [];
  for (const event of Array.isArray(items) ? items : []) {
    if (interpretCalendarEvent(event).decision === "no_call") continue;
    const startIso = event && event.start && event.start.dateTime;
    if (!startIso) continue;
    const startMs = Date.parse(startIso);
    if (!Number.isFinite(startMs) || startMs < nowMs || startMs > nowMs + horizonH * 3600 * 1000) continue;
    const endIso = event && event.end && event.end.dateTime;
    const endMs = endIso && Number.isFinite(Date.parse(endIso)) ? Date.parse(endIso) : null;
    output.push({
      id: event.id || "", summary: event.summary || "予定", location: event.location || null,
      attendees: Array.isArray(event.attendees) ? event.attendees : [],
      startMs, startIso, endMs, endIso: endIso || null, timezone: providerTimezone(event),
    });
  }
  output.sort((a, b) => a.startMs - b.startMs);
  return output;
}

module.exports = { fetchMobileUpcomingEvents, providerTimezone };
