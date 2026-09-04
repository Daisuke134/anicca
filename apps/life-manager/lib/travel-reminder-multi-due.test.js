"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { travelReminderOnce } = require("./travel-reminder.js");

const NOW = Date.parse("2026-09-04T13:30:00+09:00");
const HOME = "東京都新宿区1-1-1";

function event(id, summary, location, startIso) {
  const startMs = Date.parse(startIso);
  return {
    id,
    summary,
    location,
    startIso,
    startMs,
    endMs: startMs + 60 * 60 * 1000,
  };
}

test("a later-start trip whose departure reminder is due is not blocked by an earlier-start trip that is not due", async () => {
  const earlierShortTrip = event(
    "earlier-short",
    "近場の予定",
    "近場",
    "2026-09-04T14:00:00+09:00",
  );
  const laterLongTrip = event(
    "later-long",
    "東京タワー",
    "東京タワー",
    "2026-09-04T14:20:00+09:00",
  );
  const claimed = [];
  const sent = [];

  const result = await travelReminderOnce({
    uid: "multi-due-user",
    telegram_chat_id: "multi-due-chat",
    notifications_enabled: true,
  }, NOW, {
    events: [earlierShortTrip, laterLongTrip],
    home: HOME,
    mapsKey: "maps",
    timezone: "Asia/Tokyo",
    telegramToken: "token",
    supaUrl: "https://supa.example",
    supaKey: "service-key",
    travelLogAssociation: false,
    directionsRoute: async (_origin, destination) => ({
      provider: "transit",
      durationSeconds: destination === "近場" ? 5 * 60 : 40 * 60,
      steps: [],
    }),
    claimTravel: async (_uid, eventKey, leg) => {
      assert.equal(leg, "telegram-t5");
      claimed.push(eventKey);
      return true;
    },
    sendMessage: async (_token, _chatId, text) => {
      sent.push(text);
      return { ok: true, result: { message_id: 910 } };
    },
    recordTravelTelegramReceipt: async () => ({ ok: true, matched: 1 }),
    log: () => {},
  });

  assert.equal(result.status, "sent");
  assert.deepEqual(claimed, [laterLongTrip.id]);
  assert.equal(sent.length, 1);
  assert.match(sent[0], /東京タワー/);
  assert.doesNotMatch(sent[0], /近場の予定/);
});

test("candidate route evaluations start concurrently so one slow route cannot consume the whole reminder deadline", async () => {
  const earlierShortTrip = event(
    "concurrent-earlier",
    "近場の予定",
    "近場",
    "2026-09-04T14:00:00+09:00",
  );
  const laterLongTrip = event(
    "concurrent-later",
    "東京タワー",
    "東京タワー",
    "2026-09-04T14:20:00+09:00",
  );
  let started = 0;
  let releaseRoutes;
  const routeBarrier = new Promise((resolve) => { releaseRoutes = resolve; });

  const run = travelReminderOnce({
    uid: "concurrent-user",
    telegram_chat_id: "concurrent-chat",
    notifications_enabled: true,
  }, NOW, {
    events: [earlierShortTrip, laterLongTrip],
    home: HOME,
    mapsKey: "maps",
    timezone: "Asia/Tokyo",
    telegramToken: "token",
    supaUrl: "https://supa.example",
    supaKey: "service-key",
    travelLogAssociation: false,
    directionsRoute: async (_origin, destination) => {
      started += 1;
      await routeBarrier;
      return {
        provider: "transit",
        durationSeconds: destination === "近場" ? 5 * 60 : 40 * 60,
        steps: [],
      };
    },
    claimTravel: async () => true,
    sendMessage: async () => ({ ok: true, result: { message_id: 911 } }),
    recordTravelTelegramReceipt: async () => ({ ok: true, matched: 1 }),
    log: () => {},
  });

  await new Promise((resolve) => setImmediate(resolve));
  const startedBeforeRelease = started;
  releaseRoutes();
  const result = await run;

  assert.equal(startedBeforeRelease, 2);
  assert.equal(result.status, "sent");
  assert.equal(result.eventKey, laterLongTrip.id);
});
