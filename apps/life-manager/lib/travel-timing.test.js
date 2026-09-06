"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");
const { computeDoorDepartureMs, computeT5ReminderMs } = require("./travel-timing.js");
const { resolveDeparture } = require("./wake-filter.js");
const { fillTravel } = require("./travel.js");

const MINUTE = 60 * 1000;
const START = Date.parse("2026-09-07T14:00:00+09:00");
const HOME = "新宿区南元町15-27";
const VENUE = "東京タワー";

function rawEvent({ id = "event-1", summary = "東京タワー", location = VENUE, start = START, end = START + 60 * MINUTE } = {}) {
  return {
    id,
    summary,
    location,
    start: { dateTime: new Date(start).toISOString() },
    end: { dateTime: new Date(end).toISOString() },
  };
}

function fakeCalendar(rows) {
  const created = [];
  return {
    created,
    async listEventsRaw() { return rows; },
    async createEvent(_uid, payload) {
      created.push(payload);
      return { successful: true };
    },
  };
}

test("shared timing keeps route seconds exact and applies the leave buffer once", () => {
  const route = { durationSeconds: 31 * 60 + 20 };
  const departure = computeDoorDepartureMs(START, route, { bufferMin: 5 });
  assert.equal(departure, START - (31 * 60 + 20) * 1000 - 5 * MINUTE);
  assert.equal(computeT5ReminderMs(departure), departure - 5 * MINUTE);
});

test("shared timing does not invent a physical departure when no structured route exists", () => {
  assert.equal(computeDoorDepartureMs(START, null, { bufferMin: 5 }), null);
  assert.equal(computeT5ReminderMs(null), null);
});

test("wake inline fallback uses the same structured-route second precision as Telegram", async () => {
  const ev = { id: "call-1", summary: "会議", location: VENUE, startMs: START, endMs: START + 60 * MINUTE };
  const route = { durationSeconds: 31 * 60 + 20 };
  let calls = 0;
  const departure = await resolveDeparture(ev, [ev], {
    home: HOME,
    mapsKey: "maps",
    nowMs: START - 2 * 60 * MINUTE,
    bufferMin: 5,
    routeFn: async (origin, destination, _key, anchorAtMs, _nowMs, departureMode) => {
      calls += 1;
      assert.equal(origin, HOME);
      assert.equal(destination, VENUE);
      assert.equal(anchorAtMs, START);
      assert.equal(departureMode, false);
      return route;
    },
    directionsFn: async () => { throw new Error("rounded-minute fallback must not own timing when structured route is available"); },
  });
  assert.equal(calls, 1);
  assert.equal(departure, computeDoorDepartureMs(START, route, { bufferMin: 5 }));
});

test("Calendar outbound Travel block starts at the same exact door departure as Telegram/calls", async () => {
  const cal = fakeCalendar([rawEvent()]);
  const route = { durationSeconds: 31 * 60 + 20 };
  let routeCalls = 0;
  const result = await fillTravel("timing-user", {
    apiKey: "calendar",
    mapsKey: "maps",
    home: HOME,
    timezone: "Asia/Tokyo",
    nowMs: START - 3 * 60 * MINUTE,
    bufferMin: 5,
    calendar: cal,
    _directionsRoute: async (_origin, _destination, _key, anchorAtMs, _nowMs, departureMode) => {
      routeCalls += 1;
      if (departureMode) return { durationSeconds: 20 * 60 };
      assert.equal(anchorAtMs, START);
      return route;
    },
    _directionsMinutes: async (_origin, _destination, _key, _anchorAtMs, _nowMs, departureMode) => {
      if (departureMode) return 20;
      throw new Error("Calendar must not round a structured outbound route before computing departure");
    },
  });

  assert.ok(routeCalls >= 1);
  assert.equal(result.inserted >= 1, true);
  const outbound = cal.created.find((row) => String(row.summary || "").includes("→東京タワー"));
  assert.ok(outbound, "outbound [Travel] block should be created");
  const expectedDeparture = computeDoorDepartureMs(START, route, { bufferMin: 5 });
  assert.equal(Date.parse(`${outbound.start_datetime}Z`), expectedDeparture);
  assert.equal(result.outboundReports[0].leaveMs, expectedDeparture);
});
