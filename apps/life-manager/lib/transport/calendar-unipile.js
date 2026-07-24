// lib/transport/calendar-unipile.js — CLOUD calendar transport via Unipile v1.
// API schema: https://developer.unipile.com/reference/calendarscontroller_listcalendareventsbycalendar.md
"use strict";

const RESPONSE_STATUS = {
  yes: "accepted",
  no: "declined",
  maybe: "tentative",
  noreply: "needsAction",
};

function mapDate(value) {
  if (!value || typeof value !== "object") return {};
  if (value.date_time) {
    const out = { dateTime: value.date_time };
    if (value.time_zone) out.timeZone = value.time_zone;
    return out;
  }
  return value.date ? { date: value.date } : {};
}

function mapAttendee(attendee) {
  const out = { email: attendee.email };
  if (attendee.display_name) out.displayName = attendee.display_name;
  if (attendee.comment) out.comment = attendee.comment;
  if (attendee.is_organizer != null) out.organizer = attendee.is_organizer;
  if (attendee.is_optional != null) out.optional = attendee.is_optional;
  if (attendee.is_resource != null) out.resource = attendee.is_resource;
  if (RESPONSE_STATUS[attendee.response_status]) out.responseStatus = RESPONSE_STATUS[attendee.response_status];
  return out;
}

function mapEvent(event) {
  const out = {
    id: event.id,
    summary: event.title || "",
    description: event.body || "",
    location: event.location || "",
    start: mapDate(event.start),
    end: mapDate(event.end),
  };
  if (Array.isArray(event.attendees)) out.attendees = event.attendees.map(mapAttendee);
  if (event.organizer) {
    out.organizer = { email: event.organizer.email };
    if (event.organizer.display_name) out.organizer.displayName = event.organizer.display_name;
  }
  if (event.is_cancelled != null) out.status = event.is_cancelled ? "cancelled" : "confirmed";
  return out;
}

function makeUnipileCalendar({ accountId, token, dsn } = {}) {
  const base = dsn ? `https://${dsn}` : "";
  const headers = { "X-API-KEY": token, "Content-Type": "application/json", accept: "application/json" };
  let primaryCalendarId;

  async function requestJson(url, init = {}) {
    const response = await fetch(url, { ...init, headers: { ...headers, ...(init.headers || {}) } });
    if (!response.ok) throw new Error(`Unipile calendar HTTP ${response.status || "error"}`);
    return response.json();
  }

  async function getPrimaryCalendarId() {
    if (primaryCalendarId) return primaryCalendarId;
    const query = new URLSearchParams({ account_id: accountId });
    const body = await requestJson(`${base}/api/v1/calendars?${query}`);
    const calendars = Array.isArray(body && body.data) ? body.data : [];
    const primary = calendars.find((calendar) => calendar && calendar.is_default === true)
      || (calendars.length === 1 ? calendars[0] : null);
    if (!primary || !primary.id) throw new Error("Unipile primary calendar not found");
    primaryCalendarId = primary.id;
    return primaryCalendarId;
  }

  return {
    kind: "unipile",
    ready: () => !!(accountId && token && dsn),

    async listEventsRaw(_uid, { timeMin, timeMax, maxResults } = {}) {
      if (!accountId || !token || !dsn) return [];
      try {
        const calendarId = await getPrimaryCalendarId();
        const query = new URLSearchParams({ account_id: accountId });
        if (timeMin) query.set("start", timeMin);
        if (timeMax) query.set("end", timeMax);
        if (maxResults) query.set("limit", String(maxResults));
        const body = await requestJson(`${base}/api/v1/calendars/${encodeURIComponent(calendarId)}/events?${query}`);
        return (Array.isArray(body && body.data) ? body.data : []).map(mapEvent);
      } catch {
        return [];
      }
    },

    async createEvent(_uid, args = {}) {
      if (!accountId || !token || !dsn) return { successful: false };
      try {
        const startMs = Date.parse(/(?:Z|[+-]\d\d:\d\d)$/.test(args.start_datetime || "")
          ? args.start_datetime : `${args.start_datetime || ""}Z`);
        if (!Number.isFinite(startMs)) return { successful: false };
        const durationMs = ((Number(args.event_duration_hour) || 0) * 60 +
          (Number(args.event_duration_minutes) || 0)) * 60_000;
        const calendarId = await getPrimaryCalendarId();
        const query = new URLSearchParams({ account_id: accountId });
        const body = {
          title: args.summary || "予定",
          attendees: [],
          start: { date_time: new Date(startMs).toISOString(), time_zone: args.timezone || "UTC" },
          end: { date_time: new Date(startMs + durationMs).toISOString(), time_zone: args.timezone || "UTC" },
        };
        if (args.description != null) body.body = args.description;
        if (args.location != null) body.location = args.location;
        await requestJson(`${base}/api/v1/calendars/${encodeURIComponent(calendarId)}/events?${query}`, {
          method: "POST", body: JSON.stringify(body),
        });
        return { successful: true };
      } catch {
        return { successful: false };
      }
    },

    async patchEvent(_uid, args = {}) {
      if (!accountId || !token || !dsn || !args.event_id) return { successful: false };
      try {
        const calendarId = await getPrimaryCalendarId();
        const query = new URLSearchParams({ account_id: accountId });
        const body = {};
        if (args.location != null) body.location = args.location;
        if (args.summary != null) body.title = args.summary;
        if (args.description != null) body.body = args.description;
        await requestJson(`${base}/api/v1/calendars/${encodeURIComponent(calendarId)}/events/${encodeURIComponent(args.event_id)}?${query}`, {
          method: "PATCH", body: JSON.stringify(body),
        });
        return { successful: true };
      } catch {
        return { successful: false };
      }
    },
  };
}

module.exports = { makeUnipileCalendar, mapEvent };
