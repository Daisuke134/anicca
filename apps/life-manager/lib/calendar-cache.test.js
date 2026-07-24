"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const { makeCachedCalendar } = require("./calendar-cache.js");

const WINDOW = {
  timeMin: "2026-07-18T09:00:20.000Z",
  timeMax: "2026-07-18T10:00:40.000Z",
  maxResults: 50,
};

function fakeCalendar() {
  const calls = { list: 0, create: 0, patch: 0 };
  const inner = {
    kind: "fake",
    ready: () => true,
    async listEventsRaw(uid, input) {
      calls.list += 1;
      return [{ uid, input, call: calls.list }];
    },
    async createEvent(uid, input) {
      calls.create += 1;
      return { successful: true, uid, input };
    },
    async patchEvent(uid, input) {
      calls.patch += 1;
      return { successful: true, uid, input };
    },
  };
  return { inner, calls };
}

test("same uid and minute-rounded window is fetched once within TTL", async () => {
  const { inner, calls } = fakeCalendar();
  const calendar = makeCachedCalendar(inner, { now: () => 1_000, ttlMs: 300_000 });

  const first = await calendar.listEventsRaw("u1", WINDOW);
  const second = await calendar.listEventsRaw("u1", {
    ...WINDOW,
    timeMin: "2026-07-18T09:00:50.000Z",
    timeMax: "2026-07-18T10:00:59.000Z",
  });

  assert.equal(calls.list, 1);
  assert.strictEqual(second, first);
});

test("expired entry is fetched again", async () => {
  let now = 1_000;
  const { inner, calls } = fakeCalendar();
  const calendar = makeCachedCalendar(inner, { now: () => now, ttlMs: 300_000 });

  await calendar.listEventsRaw("u1", WINDOW);
  now += 300_000;
  await calendar.listEventsRaw("u1", WINDOW);

  assert.equal(calls.list, 2);
});

test("createEvent invalidates every cached window for that uid", async () => {
  const { inner, calls } = fakeCalendar();
  const calendar = makeCachedCalendar(inner, { now: () => 1_000 });

  await calendar.listEventsRaw("u1", WINDOW);
  await calendar.listEventsRaw("u1", {
    ...WINDOW,
    timeMin: "2026-07-18T12:00:00.000Z",
    timeMax: "2026-07-18T13:00:00.000Z",
  });
  await calendar.createEvent("u1", { summary: "new event" });
  await calendar.listEventsRaw("u1", WINDOW);

  assert.equal(calls.create, 1);
  assert.equal(calls.list, 3);
});

test("patchEvent invalidates that uid without invalidating another uid", async () => {
  const { inner, calls } = fakeCalendar();
  const calendar = makeCachedCalendar(inner, { now: () => 1_000 });

  await calendar.listEventsRaw("u1", WINDOW);
  await calendar.listEventsRaw("u2", WINDOW);
  await calendar.patchEvent("u1", { event_id: "e1", summary: "changed" });
  await calendar.listEventsRaw("u1", WINDOW);
  await calendar.listEventsRaw("u2", WINDOW);

  assert.equal(calls.patch, 1);
  assert.equal(calls.list, 3);
});

test("different uids use different cache keys", async () => {
  const { inner, calls } = fakeCalendar();
  const calendar = makeCachedCalendar(inner, { now: () => 1_000 });

  await calendar.listEventsRaw("u1", WINDOW);
  await calendar.listEventsRaw("u2", WINDOW);

  assert.equal(calls.list, 2);
});

test("an empty inner result remains an empty array", async () => {
  const inner = {
    async listEventsRaw() { return []; },
    async createEvent() { return { successful: true }; },
    async patchEvent() { return { successful: true }; },
  };
  const calendar = makeCachedCalendar(inner, { now: () => 1_000 });

  assert.deepEqual(await calendar.listEventsRaw("u1", WINDOW), []);
});

test("getCalendar shares the cached wrapper unless LM_CAL_CACHE=off", () => {
  const beforeCache = process.env.LM_CAL_CACHE;
  const beforeTransport = process.env.LIFE_TRANSPORT;
  delete process.env.LIFE_TRANSPORT;
  delete process.env.LM_CAL_CACHE;
  try {
    const { getCalendar } = require("./transport/index.js");
    const first = getCalendar({ kind: "composio", apiKey: "calendar-cache-wiring-test" });
    const second = getCalendar({ kind: "composio", apiKey: "calendar-cache-wiring-test" });
    assert.strictEqual(second, first);

    process.env.LM_CAL_CACHE = "off";
    const rawFirst = getCalendar({ kind: "composio", apiKey: "calendar-cache-wiring-test" });
    const rawSecond = getCalendar({ kind: "composio", apiKey: "calendar-cache-wiring-test" });
    assert.notStrictEqual(rawSecond, rawFirst);
  } finally {
    if (beforeCache == null) delete process.env.LM_CAL_CACHE;
    else process.env.LM_CAL_CACHE = beforeCache;
    if (beforeTransport == null) delete process.env.LIFE_TRANSPORT;
    else process.env.LIFE_TRANSPORT = beforeTransport;
  }
});
