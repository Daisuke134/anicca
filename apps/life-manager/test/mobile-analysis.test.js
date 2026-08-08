"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { analyzeNextEvent } = require("../lib/mobile-analysis.js");
const { createMemoryMobileStore } = require("../lib/mobile-store.js");

function baseStore(overrides = {}) {
  return createMemoryMobileStore({ users: [{ uid: "user-a", name: "A", home_address: "Shibuya", phone: null, paid: false, product_locale: "en", calendar_provider: "composio_gcal", gmail_account_id: "account-a", calendar_composio_user_id: "owner-a", ...overrides }] });
}

const event = { id: "event-1", summary: "Meeting", location: "Roppongi", startIso: "2026-08-08T03:00:00.000Z", endIso: "2026-08-08T04:00:00.000Z", timezone: "Asia/Tokyo", startMs: Date.parse("2026-08-08T03:00:00.000Z") };

test("phone null and paid false still reach direct Calendar analysis and append one route message", async () => {
  const store = baseStore();
  const travelCalls = [];
  const result = await analyzeNextEvent({ uid: "user-a", productLocale: "en" }, {}, {
    store, serverSecret: "test-travel-secret", workerId: "analysis-worker-1",
    fetchUpcomingEvents: async () => [event],
    computeMobileRoute: async () => ({ status: "route_ready", provider: "transit", eventId: event.id, timezone: event.timezone, origin: { displayNames: { en: "Shibuya", ja: "渋谷" } }, destination: { displayNames: { en: "Roppongi", ja: "六本木" } }, leaveAt: "2026-08-08T02:30:00.000Z", arriveAt: "2026-08-08T02:57:00.000Z", durationSeconds: 1620, bufferSeconds: 180, transferCount: 0, fare: null, geometry: null, steps: [] }),
    ensureMobileTravelBlock: async (input, deps) => {
      assert.deepEqual(store._outbox.get("user-a").map((row) => row.key), ["chat.route_ready"]);
      travelCalls.push({ input, deps });
      return { status: "created", providerEventId: "lmaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", verifiedAt: "2026-08-08T02:31:00.000Z" };
    },
  });
  assert.equal(result.status, "route_ready");
  const rows = store._outbox.get("user-a");
  assert.equal(rows.length, 2);
  assert.deepEqual(rows.map((row) => row.key), ["chat.route_ready", "chat.travel_block_confirmed"]);
  assert.equal(travelCalls.length, 1);
  assert.equal(travelCalls[0].input.uid, "user-a");
  assert.equal(travelCalls[0].input.sourceEventId, event.id);
  assert.equal(travelCalls[0].input.eventKey, event.id);
  assert.equal(travelCalls[0].input.leg, "go");
  assert.equal(travelCalls[0].input.calendarId, "primary");
  assert.equal(travelCalls[0].input.connectedAccountId, "account-a");
  assert.equal(travelCalls[0].input.composioUserId, "owner-a");
  assert.equal(travelCalls[0].input.payload.start.dateTime, "2026-08-08T02:30:00.000Z");
  assert.equal(travelCalls[0].input.payload.end.dateTime, event.startIso);
  assert.equal(travelCalls[0].input.payload.timezone, event.timezone);
  assert.match(travelCalls[0].input.payload.summary, /^\[Travel\]/u);
  assert.equal(travelCalls[0].deps.serverSecret, "test-travel-secret");
  assert.equal(result.nextCursor, "cursor:v1:c2VxOjE6djE");
});

test("route analysis emits one terminal localized failure receipt and never a confirmed receipt", async () => {
  const failures = ["provider_write_failed", "provider_readback_failed", "claim_pending", "budget_denied", "analysis_conflict", "provider_collision"];
  for (const reason of failures) {
    const store = baseStore();
    const result = await analyzeNextEvent({ uid: "user-a", productLocale: "en" }, { analysisId: `analysis-${reason}` }, {
      store,
      fetchUpcomingEvents: async () => [event],
      computeMobileRoute: async () => ({ status: "route_ready", provider: "transit", eventId: event.id, timezone: event.timezone, origin: { displayNames: { en: "Shibuya", ja: "渋谷" } }, destination: { displayNames: { en: "Roppongi", ja: "六本木" } }, leaveAt: "2026-08-08T02:30:00.000Z", arriveAt: "2026-08-08T02:57:00.000Z", durationSeconds: 1620, bufferSeconds: 180, steps: [] }),
      ensureMobileTravelBlock: async () => ({ status: reason, errorCode: reason }),
    });
    const rows = store._outbox.get("user-a");
    assert.deepEqual(rows.map((row) => row.key), ["chat.route_ready", "chat.travel_block_not_added"]);
    assert.equal(result.status, "route_ready");
    assert.equal(rows.some((row) => row.key === "chat.travel_block_confirmed"), false, reason);
    assert.equal(rows[1].args.reason, reason);
  }
});

test("the travel receipt is stable across analysis keys while route messages remain ordered", async () => {
  const store = baseStore();
  const travelCalls = [];
  const deps = {
    store,
    fetchUpcomingEvents: async () => [event],
    computeMobileRoute: async () => ({ status: "route_ready", provider: "transit", eventId: event.id, timezone: event.timezone, origin: { displayNames: { en: "Shibuya", ja: "渋谷" } }, destination: { displayNames: { en: "Roppongi", ja: "六本木" } }, leaveAt: "2026-08-08T02:30:00.000Z", arriveAt: "2026-08-08T02:57:00.000Z", durationSeconds: 1620, bufferSeconds: 180, steps: [] }),
    ensureMobileTravelBlock: async (input) => {
      travelCalls.push(input.analysisKey);
      return { status: travelCalls.length === 1 ? "created" : "existing", providerEventId: "lmaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", verifiedAt: "2026-08-08T02:31:00.000Z" };
    },
  };
  const first = await analyzeNextEvent({ uid: "user-a", productLocale: "en" }, { analysisId: "analysis-one" }, deps);
  const replay = await analyzeNextEvent({ uid: "user-a", productLocale: "en" }, { analysisId: "analysis-one" }, deps);
  const second = await analyzeNextEvent({ uid: "user-a", productLocale: "en" }, { analysisId: "analysis-two" }, deps);
  const rows = store._outbox.get("user-a");
  const receipts = rows.filter((row) => row.key === "chat.travel_block_confirmed");
  assert.equal(first.message.key, undefined);
  assert.equal(replay.message.id, first.message.id);
  assert.equal(second.message.id === first.message.id, false);
  assert.equal(receipts.length, 1);
  assert.equal(new Set(receipts.map((row) => row.id)).size, 1);
  assert.deepEqual(rows.map((row) => row.sequence), [1, 2, 3]);
  assert.deepEqual(travelCalls, ["analysis-one", "analysis-one", "analysis-two"]);
});

test("a failed travel attempt remains visible while provider recovery appends one stable confirmation", async () => {
  const store = baseStore();
  let attempts = 0;
  const deps = {
    store,
    fetchUpcomingEvents: async () => [event],
    computeMobileRoute: async () => ({
      status: "route_ready", provider: "transit", eventId: event.id, timezone: event.timezone,
      origin: { displayNames: { en: "Shibuya", ja: "渋谷" } },
      destination: { displayNames: { en: "Roppongi", ja: "六本木" } },
      leaveAt: "2026-08-08T02:30:00.000Z", arriveAt: "2026-08-08T02:57:00.000Z",
      durationSeconds: 1620, bufferSeconds: 180, steps: [],
    }),
    ensureMobileTravelBlock: async () => {
      attempts += 1;
      return attempts === 1
        ? { status: "provider_readback_failed", errorCode: "provider_readback_failed" }
        : { status: "created", providerEventId: "lmaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", verifiedAt: "2026-08-08T02:31:00.000Z" };
    },
  };

  await analyzeNextEvent({ uid: "user-a", productLocale: "en" }, { analysisId: "analysis-failed" }, deps);
  await analyzeNextEvent({ uid: "user-a", productLocale: "en" }, { analysisId: "analysis-recovered" }, deps);
  await analyzeNextEvent({ uid: "user-a", productLocale: "en" }, { analysisId: "analysis-recovered-again" }, deps);

  const rows = store._outbox.get("user-a");
  assert.deepEqual(rows.map((row) => row.key), [
    "chat.route_ready", "chat.travel_block_not_added",
    "chat.route_ready", "chat.travel_block_confirmed",
    "chat.route_ready",
  ]);
  const failures = rows.filter((row) => row.key === "chat.travel_block_not_added");
  const confirmations = rows.filter((row) => row.key === "chat.travel_block_confirmed");
  assert.equal(failures.length, 1);
  assert.equal(confirmations.length, 1);
  assert.notEqual(failures[0].id, confirmations[0].id);
  assert.deepEqual(rows.map((row) => row.sequence), [1, 2, 3, 4, 5]);
});

test("unknown travel provider errors keep an explicit unknown reason", async () => {
  const store = baseStore();
  await analyzeNextEvent({ uid: "user-a", productLocale: "en" }, { analysisId: "analysis-unknown-provider" }, {
    store,
    fetchUpcomingEvents: async () => [event],
    computeMobileRoute: async () => ({
      status: "route_ready", provider: "transit", eventId: event.id, timezone: event.timezone,
      origin: { displayNames: { en: "Shibuya", ja: "渋谷" } },
      destination: { displayNames: { en: "Roppongi", ja: "六本木" } },
      leaveAt: "2026-08-08T02:30:00.000Z", arriveAt: "2026-08-08T02:57:00.000Z",
      durationSeconds: 1620, bufferSeconds: 180, steps: [],
    }),
    ensureMobileTravelBlock: async () => ({ status: "provider exploded", errorCode: "provider exploded" }),
  });
  const failure = store._outbox.get("user-a").find((row) => row.key === "chat.travel_block_not_added");
  assert.ok(failure);
  assert.equal(failure.args.reason, "provider_unknown");
});

test("travel receipt projection is locale-switchable and does not expose provider authority", async () => {
  const store = baseStore();
  await analyzeNextEvent({ uid: "user-a", productLocale: "en" }, { analysisId: "locale-analysis" }, {
    store,
    fetchUpcomingEvents: async () => [event],
    computeMobileRoute: async () => ({ status: "route_ready", provider: "transit", eventId: event.id, timezone: event.timezone, origin: { displayNames: { en: "Shibuya", ja: "渋谷" } }, destination: { displayNames: { en: "Roppongi", ja: "六本木" } }, leaveAt: "2026-08-08T02:30:00.000Z", arriveAt: "2026-08-08T02:57:00.000Z", durationSeconds: 1620, bufferSeconds: 180, steps: [] }),
    ensureMobileTravelBlock: async () => ({ status: "existing", providerEventId: "lmaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", verifiedAt: "2026-08-08T02:31:00.000Z", marker: "secret-marker", claimToken: "secret-claim", connectedAccountId: "secret-account", composioUserId: "secret-owner", idempotencyKey: "secret-idempotency" }),
  });
  const en = await require("../lib/mobile-outbox.js").listMobileMessages({ uid: "user-a", productLocale: "en" }, null, { store });
  const ja = await require("../lib/mobile-outbox.js").listMobileMessages({ uid: "user-a", productLocale: "ja" }, null, { store });
  const enReceipt = en.messages.find((message) => message.semanticKey === "chat.travel_block_confirmed");
  const jaReceipt = ja.messages.find((message) => message.semanticKey === "chat.travel_block_confirmed");
  assert.ok(enReceipt);
  assert.ok(jaReceipt);
  assert.match(enReceipt.text, /Travel/u);
  assert.match(jaReceipt.text, /カレンダー/u);
  assert.doesNotMatch(jaReceipt.text, /Travel|verified|primary/u);
  assert.equal(JSON.stringify(enReceipt).includes("secret-"), false);
  assert.equal(JSON.stringify(jaReceipt).includes("secret-"), false);
  assert.equal(en.messages.length, ja.messages.length);
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
  assert.equal(disconnectedResult.message.type, "question");
  assert.equal(reads, 0);

  const missingName = baseStore({ name: null });
  const nameResult = await analyzeNextEvent({ uid: "user-a", productLocale: "en" }, { analysisId: "name-required" }, {
    store: missingName,
    fetchUpcomingEvents: async () => { reads++; return [event]; },
  });
  assert.equal(nameResult.status, "needs_information");
  assert.equal(nameResult.message.type, "question");
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
  assert.equal(store._outbox.get("user-a").length, 2);
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
