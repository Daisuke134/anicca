"use strict";
const { test } = require("node:test");
const assert = require("node:assert");
const { contextEntries, backfillCalendarContext } = require("./context-graph.js");

const inferred = {
  home_area: "Shibuya", work_place: "Marunouchi",
  frequent_venue_1: "Shibuya Hikarie", frequent_venue_2: "Tokyo International Forum",
  typical_morning_start: "09:30",
};

test("contextEntries returns exactly the five required graph fields", () => {
  assert.deepEqual(contextEntries(inferred), [
    ["context:home_area", "Shibuya"], ["context:work_place", "Marunouchi"],
    ["context:frequent_venue_1", "Shibuya Hikarie"],
    ["context:frequent_venue_2", "Tokyo International Forum"],
    ["context:typical_morning_start", "09:30"],
  ]);
  assert.deepEqual(contextEntries({ ...inferred, work_place: "" }), []);
});

test("backfillCalendarContext reads the previous 60 days and upserts five memories", async () => {
  const nowMs = Date.parse("2026-07-18T00:00:00.000Z");
  let range;
  const writes = [];
  const count = await backfillCalendarContext("u1", {
    nowMs, geminiKey: "g", supaUrl: "s", supaKey: "k",
    calendar: { ready: () => true, listEventsRaw: async (_uid, input) => { range = input; return [{ summary: "Office", location: "Tokyo" }]; } },
    infer: async () => inferred,
    remember: async (uid, phrase, address) => { writes.push({ uid, phrase, address }); return true; },
    log: () => {},
  });
  assert.equal(range.timeMax, "2026-07-18T00:00:00.000Z");
  assert.equal(range.timeMin, "2026-05-19T00:00:00.000Z");
  assert.ok(range.maxResults >= 250);
  assert.equal(count, 5);
  assert.equal(writes.length, 5);
  assert.deepEqual(writes.map((x) => x.phrase), contextEntries(inferred).map(([key]) => key));
});

test("backfillCalendarContext logs and skips instead of crashing when inference is unavailable", async () => {
  const logs = [];
  const count = await backfillCalendarContext("u1", {
    geminiKey: "g", supaUrl: "s", supaKey: "k",
    calendar: { ready: () => true, listEventsRaw: async () => [{ summary: "x" }] },
    infer: async () => { throw new Error("offline"); },
    remember: async () => { throw new Error("must not write"); }, log: (line) => logs.push(line),
  });
  assert.equal(count, 0);
  assert.match(logs[0], /skipped/i);
});
