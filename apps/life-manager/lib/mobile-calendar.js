"use strict";

const { getCalendar } = require("./transport/index.js");
const { interpretCalendarEvent } = require("./calendar-interpreter.js");

const MOBILE_TRAVEL_MARKER = /^lm_travel_v1_[0-9a-f]{64}$/u;
const LEGACY_WEB_TRAVEL_DESCRIPTION = "Auto-inserted by Life Manager — adjust if the route is wrong.";

function privateTravelMarker(event) {
  const modern = event && event.extendedProperties && event.extendedProperties.private;
  const legacy = event && event.extended_properties && event.extended_properties.private;
  const values = modern && typeof modern === "object" ? modern : legacy;
  if (!values || typeof values !== "object") return null;
  return values.lm_travel_block || values.life_manager_travel_block || values.lmTravelBlock || null;
}

function isGeneratedTravelBlock(event) {
  const marker = privateTravelMarker(event);
  // A marker is authoritative. If a provider returns an invalid value under our
  // private key, fail closed and do not reinterpret a user title as a legacy block.
  if (marker !== null) return typeof marker === "string" && MOBILE_TRAVEL_MARKER.test(marker);
  return String(event && event.summary || "").startsWith("[Travel]")
    && String(event && event.description || "") === LEGACY_WEB_TRAVEL_DESCRIPTION;
}

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
  // `uid` is the stable Life Manager tenant key. Provider execution must use the
  // Composio provisional owner persisted during OAuth, paired with the exact
  // connected account, or Composio can resolve a different owner/account.
  const items = await calendar.listEventsRaw(composioUserId, {
    timeMin: isoZ(nowMs), timeMax: isoZ(nowMs + horizonH * 3600 * 1000),
    connectedAccountId,
  });
  const output = [];
  for (const event of Array.isArray(items) ? items : []) {
    if (isGeneratedTravelBlock(event)) continue;
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
