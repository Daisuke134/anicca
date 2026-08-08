"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { analyzeNextEvent } = require("../lib/mobile-analysis.js");
const { createMemoryMobileStore } = require("../lib/mobile-store.js");

function baseStore(overrides = {}) {
  return createMemoryMobileStore({ users: [{ uid: "user-a", name: "A", home_address: "Shibuya", phone: null, paid: false, product_locale: "en", calendar_provider: "composio_gcal", gmail_account_id: "account-a", ...overrides }] });
}

const event = { id: "event-1", summary: "Meeting", location: "Roppongi", startIso: "2026-08-08T03:00:00.000Z", endIso: "2026-08-08T04:00:00.000Z", timezone: "Asia/Tokyo", startMs: Date.parse("2026-08-08T03:00:00.000Z") };

test("phone null and paid false still reach direct Calendar analysis and append one route message", async () => {
  const store = baseStore();
  const result = await analyzeNextEvent({ uid: "user-a", productLocale: "en" }, {}, {
    store, fetchUpcomingEvents: async () => [event], computeMobileRoute: async () => ({ status: "route_ready", provider: "transit", eventId: event.id, timezone: event.timezone, origin: { displayNames: { en: "Shibuya", ja: "渋谷" } }, destination: { displayNames: { en: "Roppongi", ja: "六本木" } }, leaveAt: "2026-08-08T02:30:00.000Z", arriveAt: "2026-08-08T02:57:00.000Z", durationSeconds: 1620, bufferSeconds: 180, transferCount: 0, fare: null, geometry: null, steps: [] }),
  });
  assert.equal(result.status, "route_ready");
  assert.equal(store._outbox.get("user-a").length, 1);
});

test("direct analysis exposes exactly the terminal state for no event, missing information, unavailable route, and provider failure", async () => {
  const cases = [
    { expected: "no_upcoming_event", events: [] },
    { expected: "needs_information", events: [{ ...event, location: null }] },
    { expected: "route_unavailable", events: [event], route: null },
    { expected: "failed", events: [event], error: new Error("provider") },
  ];
  for (const item of cases) {
    const store = baseStore(item.expected === "needs_information" ? { home_address: null } : {});
    const result = await analyzeNextEvent({ uid: "user-a", productLocale: "en" }, {}, {
      store, fetchUpcomingEvents: async () => item.events,
      computeMobileRoute: async () => { if (item.error) throw item.error; return item.route === null ? null : item.route; },
    });
    assert.equal(result.status, item.expected);
    assert.equal(store._outbox.get("user-a").length, 1);
  }
});

test("analysis does not read a disconnected calendar or bypass the required name", async () => {
  const disconnected = baseStore({ name: "A", calendar_provider: null, gmail_account_id: null });
  let reads = 0;
  const disconnectedResult = await analyzeNextEvent({ uid: "user-a", productLocale: "en" }, { analysisId: "calendar-required" }, {
    store: disconnected,
    fetchUpcomingEvents: async () => { reads++; return [event]; },
  });
  assert.equal(disconnectedResult.status, "needs_information");
  assert.equal(disconnectedResult.message.question.type, "calendar");
  assert.equal(reads, 0);

  const missingName = baseStore({ name: null });
  const nameResult = await analyzeNextEvent({ uid: "user-a", productLocale: "en" }, { analysisId: "name-required" }, {
    store: missingName,
    fetchUpcomingEvents: async () => { reads++; return [event]; },
  });
  assert.equal(nameResult.status, "needs_information");
  assert.equal(nameResult.message.question.type, "name");
  assert.equal(reads, 0);
});

test("replaying one analysis identifier keeps one durable terminal message", async () => {
  const store = baseStore();
  const deps = {
    store,
    fetchUpcomingEvents: async () => [event],
    computeMobileRoute: async () => ({
      status: "route_ready", provider: "transit", providerAttribution: "Transit API", eventId: event.id,
      timezone: event.timezone, origin: { displayNames: { en: "Shibuya", ja: "渋谷" } },
      destination: { displayNames: { en: "Roppongi", ja: "六本木" } }, leaveAt: event.startIso, arriveAt: event.endIso,
      bufferSeconds: 180, steps: [],
    }),
  };
  const one = await analyzeNextEvent({ uid: "user-a", productLocale: "en" }, { analysisId: "same-analysis" }, deps);
  const two = await analyzeNextEvent({ uid: "user-a", productLocale: "en" }, { analysisId: "same-analysis" }, deps);
  assert.equal(one.message.id, two.message.id);
  assert.equal(store._outbox.get("user-a").length, 1);
});

test("replaying a missing-information analysis keeps one open question", async () => {
  const store = baseStore({ home_address: null });
  const deps = { store, fetchUpcomingEvents: async () => [event] };
  const one = await analyzeNextEvent({ uid: "user-a", productLocale: "en" }, { analysisId: "same-question-analysis" }, deps);
  const two = await analyzeNextEvent({ uid: "user-a", productLocale: "en" }, { analysisId: "same-question-analysis" }, deps);
  assert.equal(one.message.id, two.message.id);
  assert.equal(store._outbox.get("user-a").length, 1);
  assert.equal(store._questions.size, 1);
});

test("unlocalizable provider navigation facts become a truthful route-unavailable terminal", async () => {
  const store = baseStore();
  const result = await analyzeNextEvent({ uid: "user-a", productLocale: "en" }, {}, {
    store,
    fetchUpcomingEvents: async () => [event],
    computeMobileRoute: async () => ({
      status: "route_ready", provider: "transit", eventId: event.id, timezone: event.timezone,
      origin: { displayNames: { ja: "未知駅" } }, destination: { displayNames: { ja: "未知目的地" } },
      leaveAt: event.startIso, arriveAt: event.endIso, steps: [],
    }),
  });
  assert.equal(result.status, "route_unavailable");
  assert.equal(result.message.route, null);
});
