"use strict";

const { test } = require("node:test");
const assert = require("node:assert");
const { makeUnipileCalendar } = require("./calendar-unipile.js");
const { getCalendar } = require("./index.js");

function jsonResponse(body, ok = true) {
  return { ok, json: async () => body };
}

test("listEventsRaw maps Unipile events to Google Calendar shape", async () => {
  const original = global.fetch;
  const calls = [];
  global.fetch = async (url, init = {}) => {
    calls.push({ url: String(url), init });
    if (calls.length === 1) {
      return jsonResponse({ data: [
        { id: "cal-secondary", is_default: false },
        { id: "cal-primary", is_default: true },
      ] });
    }
    return jsonResponse({ data: [
      {
        id: "event-timed",
        title: "Dentist",
        body: "Bring insurance card",
        location: "Shibuya Clinic",
        start: { date_time: "2026-07-20T01:00:00.000Z", time_zone: "Asia/Tokyo" },
        end: { date_time: "2026-07-20T02:00:00.000Z", time_zone: "Asia/Tokyo" },
      },
      {
        id: "event-all-day",
        title: "Holiday",
        start: { date: "2026-07-21" },
        end: { date: "2026-07-22" },
      },
    ] });
  };

  try {
    const calendar = makeUnipileCalendar({ accountId: "acct-1", token: "token-1", dsn: "api.example:13111" });
    const events = await calendar.listEventsRaw("ignored-uid", {
      timeMin: "2026-07-20T00:00:00Z",
      timeMax: "2026-07-23T00:00:00Z",
      maxResults: 25,
    });

    assert.deepEqual(events, [
      {
        id: "event-timed",
        summary: "Dentist",
        description: "Bring insurance card",
        location: "Shibuya Clinic",
        start: { dateTime: "2026-07-20T01:00:00.000Z", timeZone: "Asia/Tokyo" },
        end: { dateTime: "2026-07-20T02:00:00.000Z", timeZone: "Asia/Tokyo" },
      },
      {
        id: "event-all-day",
        summary: "Holiday",
        description: "",
        location: "",
        start: { date: "2026-07-21" },
        end: { date: "2026-07-22" },
      },
    ]);

    const calendarsUrl = new URL(calls[0].url);
    assert.equal(calendarsUrl.pathname, "/api/v1/calendars");
    assert.equal(calendarsUrl.searchParams.get("account_id"), "acct-1");

    const eventsUrl = new URL(calls[1].url);
    assert.equal(eventsUrl.pathname, "/api/v1/calendars/cal-primary/events");
    assert.equal(eventsUrl.searchParams.get("account_id"), "acct-1");
    assert.equal(eventsUrl.searchParams.get("start"), "2026-07-20T00:00:00Z");
    assert.equal(eventsUrl.searchParams.get("end"), "2026-07-23T00:00:00Z");
    assert.equal(eventsUrl.searchParams.get("limit"), "25");
  } finally {
    global.fetch = original;
  }
});

test("patchEvent PATCHes the Unipile event URL with a partial location body", async () => {
  const original = global.fetch;
  const calls = [];
  global.fetch = async (url, init = {}) => {
    calls.push({ url: String(url), init });
    if (calls.length === 1) return jsonResponse({ data: [{ id: "calendar/a", is_default: true }] });
    return jsonResponse({ object: "CalendarEventPatched" });
  };

  try {
    const calendar = makeUnipileCalendar({ accountId: "acct-1", token: "token-1", dsn: "api.example:13111" });
    const result = await calendar.patchEvent("ignored-uid", {
      calendar_id: "primary",
      event_id: "event/9",
      location: "Tokyo Station",
    });

    assert.deepEqual(result, { successful: true });
    assert.equal(calls.length, 2);
    const patch = calls[1];
    const patchUrl = new URL(patch.url);
    assert.equal(patchUrl.pathname, "/api/v1/calendars/calendar%2Fa/events/event%2F9");
    assert.equal(patchUrl.searchParams.get("account_id"), "acct-1");
    assert.equal(patch.init.method, "PATCH");
    assert.deepEqual(JSON.parse(patch.init.body), { location: "Tokyo Station" });
    assert.equal(patch.init.headers["X-API-KEY"], "token-1");
  } finally {
    global.fetch = original;
  }
});

test("createEvent translates the existing Composio argument shape to Unipile v1", async () => {
  const original = global.fetch;
  const calls = [];
  global.fetch = async (url, init = {}) => {
    calls.push({ url: String(url), init });
    if (calls.length === 1) return jsonResponse({ data: [{ id: "cal-primary", is_default: true }] });
    return jsonResponse({ object: "CalendarEventCreated", event_id: "created-1" });
  };

  try {
    const calendar = makeUnipileCalendar({ accountId: "acct-1", token: "token-1", dsn: "api.example:13111" });
    const result = await calendar.createEvent("ignored-uid", {
      summary: "[Travel] Home→Office",
      description: "Auto-inserted",
      location: "Tokyo Office",
      start_datetime: "2026-07-20T01:00:00",
      event_duration_hour: 1,
      event_duration_minutes: 15,
      timezone: "UTC",
      calendar_id: "primary",
    });

    assert.deepEqual(result, { successful: true });
    const create = calls[1];
    assert.equal(create.init.method, "POST");
    assert.deepEqual(JSON.parse(create.init.body), {
      title: "[Travel] Home→Office",
      body: "Auto-inserted",
      location: "Tokyo Office",
      attendees: [],
      start: { date_time: "2026-07-20T01:00:00.000Z", time_zone: "UTC" },
      end: { date_time: "2026-07-20T02:15:00.000Z", time_zone: "UTC" },
    });
  } finally {
    global.fetch = original;
  }
});

test("getCalendar selects Unipile only via LIFE_CAL_TRANSPORT and fails loud on unknown values", () => {
  const previous = {
    life: process.env.LIFE_TRANSPORT,
    calendar: process.env.LIFE_CAL_TRANSPORT,
    cache: process.env.LM_CAL_CACHE,
  };
  process.env.LIFE_TRANSPORT = "composio";
  process.env.LM_CAL_CACHE = "off";
  try {
    delete process.env.LIFE_CAL_TRANSPORT;
    assert.equal(getCalendar({ apiKey: "composio-key" }).kind, "composio");

    process.env.LIFE_CAL_TRANSPORT = "unipile";
    assert.equal(getCalendar({ accountId: "acct-1", token: "token-1", dsn: "api.example:13111" }).kind, "unipile");
    assert.equal(getCalendar({
      gmailAccountId: "acct-1", unipileToken: "token-1", unipileDsn: "api.example:13111",
    }).ready(), true);

    process.env.LIFE_CAL_TRANSPORT = "typo";
    assert.throws(() => getCalendar({}), /Unknown LIFE_CAL_TRANSPORT/);
  } finally {
    if (previous.life == null) delete process.env.LIFE_TRANSPORT;
    else process.env.LIFE_TRANSPORT = previous.life;
    if (previous.calendar == null) delete process.env.LIFE_CAL_TRANSPORT;
    else process.env.LIFE_CAL_TRANSPORT = previous.calendar;
    if (previous.cache == null) delete process.env.LM_CAL_CACHE;
    else process.env.LM_CAL_CACHE = previous.cache;
  }
});
