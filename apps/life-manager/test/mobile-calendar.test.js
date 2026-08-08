"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { fetchMobileUpcomingEvents } = require("../lib/mobile-calendar.js");

test("mobile Calendar reader preserves the provider IANA timezone instead of inventing UTC", async () => {
  const events = await fetchMobileUpcomingEvents("user-a", {
    nowMs: Date.parse("2026-08-07T17:00:00.000Z"),
    horizonH: 18,
    calendar: {
      async listEventsRaw() {
        return [{
          id: "event-a", summary: "Meeting", location: "Tokyo",
          start: { dateTime: "2026-08-08T03:00:00+09:00", timeZone: "Asia/Tokyo" },
          end: { dateTime: "2026-08-08T04:00:00+09:00", timeZone: "Asia/Tokyo" },
        }];
      },
    },
  });
  assert.equal(events[0].timezone, "Asia/Tokyo");
  assert.equal(events[0].startIso, "2026-08-08T03:00:00+09:00");
});

test("mobile Calendar reader reports an unknown provider timezone as null", async () => {
  const events = await fetchMobileUpcomingEvents("user-a", {
    nowMs: Date.parse("2026-08-08T00:00:00.000Z"), horizonH: 18,
    calendar: { async listEventsRaw() { return [{ id: "event-b", location: "Tokyo", start: { dateTime: "2026-08-08T03:00:00Z" } }]; } },
  });
  assert.equal(events[0].timezone, null);
});
