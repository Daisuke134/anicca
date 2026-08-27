"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { fetchUpcomingEvents } = require("./events.js");

const {
  T5_MS,
  CATCH_UP_MS,
  isReminderDue,
  nextReminderEvent,
  resolveReminderOrigin,
  resolveReminderDestination,
  computeDepartureMs,
  computeReminderDueAt,
  formatTravelReminder,
  travelReminderOnce,
} = require("./travel-reminder.js");

const NOW = Date.parse("2026-08-28T04:00:00.000Z"); // 13:00 JST
const START = Date.parse("2026-08-28T05:00:00.000Z"); // 14:00 JST
const END = START + 60 * 60 * 1000;
const HOME = "東京都新宿区1-1-1";

function event(overrides = {}) {
  return {
    id: "event-1",
    summary: "打ち合わせ",
    location: "渋谷",
    startMs: START,
    startIso: "2026-08-28T14:00:00+09:00",
    endMs: END,
    ...overrides,
  };
}

function routeFixture(overrides = {}) {
  return {
    provider: "transit",
    departureAt: "2026-08-28T13:20:00+09:00",
    arrivalAt: "2026-08-28T14:00:00+09:00",
    durationSeconds: 2400,
    accessWalkSeconds: 300,
    egressWalkSeconds: 0,
    transferCount: 1,
    fare: { currency: "JPY", ticket: null, ic: 209 },
    steps: [
      {
        kind: "transit", mode: "subway", service: "丸ノ内線", trainType: null, headsign: "荻窪行",
        from: { name: "東京駅", platform: "2番線" }, to: { name: "新宿駅", platform: null },
        departAt: "2026-08-28T13:20:00+09:00", arriveAt: "2026-08-28T13:40:00+09:00",
      },
      {
        kind: "transit", mode: "rail", service: "JR線", trainType: null, headsign: null,
        from: { name: "新宿駅", platform: null }, to: { name: "渋谷駅", platform: null },
        departAt: "2026-08-28T13:46:00+09:00", arriveAt: "2026-08-28T13:55:00+09:00",
      },
    ],
    availability: { platform: true, fare: true, stationExit: false },
    ...overrides,
  };
}

test("T-5 physical event uses computed departure and non-travel uses event start", () => {
  const physical = event();
  const route = { durationSeconds: 30 * 60 };
  const departure = computeDepartureMs(physical, route, { bufferMin: 5 });
  assert.equal(departure, START - 35 * 60 * 1000);
  assert.equal(computeReminderDueAt(physical, { departureMs: departure }), START - 40 * 60 * 1000);

  const online = event({ id: "online", location: "", online: true });
  assert.equal(computeDepartureMs(online, null), START);
  assert.equal(computeReminderDueAt(online, { departureMs: START }), START - T5_MS);
});

test("T-5 due window includes threshold and 15-minute catch-up, but not early/late ticks", () => {
  const dueAt = START - T5_MS;
  assert.equal(isReminderDue(dueAt - 1, dueAt), false);
  assert.equal(isReminderDue(dueAt, dueAt), true);
  assert.equal(isReminderDue(dueAt + CATCH_UP_MS, dueAt), true);
  assert.equal(isReminderDue(dueAt + CATCH_UP_MS + 1, dueAt), false);
});

test("next event is the first timed non-helper event and eligibility is independent of call settings", () => {
  const helper = event({ id: "travel", summary: "[Travel] helper", startMs: START - 30 * 60 * 1000 });
  const first = event({ id: "first", startMs: START + 5 * 60 * 1000 });
  const later = event({ id: "later", startMs: START + 20 * 60 * 1000 });
  assert.equal(nextReminderEvent([later, helper, first], NOW).id, "first");
  assert.equal(nextReminderEvent([event({ startMs: NOW - 10 * 60 * 1000 - 1 })], NOW), null);
});

test("origin precedence is fresh live location, previous venue within 90m, then home", () => {
  const previous = event({ id: "previous", summary: "前の予定", location: "東京駅", startMs: START - 2 * 60 * 60 * 1000, endMs: START - 30 * 60 * 1000 });
  const current = event();
  const fresh = { latitude: 35.681, longitude: 139.767, observedAtMs: NOW - 1000, expiresAtMs: NOW + 10 * 60 * 1000 };
  assert.deepEqual(resolveReminderOrigin(current, { events: [previous, current], liveLocation: fresh, home: HOME, nowMs: NOW }), {
    kind: "live", value: "geo:35.681,139.767",
  });

  const expired = { ...fresh, expiresAtMs: NOW };
  assert.deepEqual(resolveReminderOrigin(current, { events: [previous, current], liveLocation: expired, home: HOME, nowMs: NOW }), {
    kind: "previous", value: "東京駅",
  });
  const far = { ...previous, endMs: START - 2 * 60 * 60 * 1000 };
  assert.deepEqual(resolveReminderOrigin(current, { events: [far, current], home: HOME, nowMs: NOW }), {
    kind: "home", value: HOME,
  });
  assert.equal(resolveReminderOrigin(current, { events: [far, current], home: "", nowMs: NOW }), null);
});

test("resolved destination uses the latest adjacent outbound Travel location only", () => {
  const current = event({ id: "target", location: "渋谷" });
  const older = { id: "travel-old", summary: "[Travel] 🚆 home→old", location: "旧住所", startMs: START - 50 * 60000, endMs: START - 60000 };
  const latest = { id: "travel-latest", summary: "🚆 移動 home→complete", location: "東京都渋谷区神南1-1-1", startMs: START - 40 * 60000, endMs: START + 30000 };
  assert.equal(resolveReminderDestination(current, { events: [older, latest, current] }), latest.location);

  const returnBlock = { summary: "[Travel] 🚆 return", location: "帰宅住所", startMs: START + 30000, endMs: START + 30000 };
  const pending = { summary: "[PENDING] helper", location: "保留住所", startMs: START - 10 * 60000, endMs: START };
  const unrelated = { summary: "[Travel] 🚆 unrelated", location: "遠い住所", startMs: START - 30 * 600000, endMs: START - 30 * 600000 };
  const empty = { summary: "[Travel] 🚆 empty", location: "", startMs: START - 5 * 60000, endMs: START };
  assert.equal(resolveReminderDestination(current, { events: [returnBlock, pending, unrelated, empty, current] }), current.location);
});

test("travel reminder routes through resolved destination while displaying the original event location", async () => {
  const destination = "東京都渋谷区神南1-1-1";
  const current = event({ id: "target-route", location: "渋谷", startMs: NOW + 3 * T5_MS, endMs: NOW + 63 * 60000 });
  const outbound = { id: "travel-route", summary: "[Travel] 🚆 home→resolved", location: destination, startMs: current.startMs - 40 * 60000, endMs: current.startMs - 30000 };
  const seen = [], sent = [];
  const result = await travelReminderOnce({ uid: "u-destination", telegram_chat_id: "chat-destination", notifications_enabled: true }, NOW, {
    events: [outbound, current], home: HOME, mapsKey: "maps", timezone: "Asia/Tokyo", telegramToken: "token", supaUrl: "supa", supaKey: "key",
    directionsRoute: async (_origin, to) => { seen.push(to); return { durationSeconds: 5 * 60 }; },
    claimTravel: async () => true,
    sendMessage: async (_token, _chat, text) => { sent.push(text); return { ok: true, result: { message_id: 709 } }; },
  });
  assert.equal(result.status, "sent");
  assert.deepEqual(seen, [destination]);
  assert.match(sent[0], /目的地: 渋谷/);
  assert.doesNotMatch(sent[0], new RegExp(destination));
});

test("formatter emits the canonical ordered Japanese route shape and only provider facts", () => {
  const text = formatTravelReminder(event(), routeFixture(), {
    departureMs: Date.parse("2026-08-28T04:15:00.000Z"),
    timezone: "Asia/Tokyo",
  });
  assert.equal(text, [
    "🚆 次は 14:00「打ち合わせ」",
    "13:15 出発 → 14:00 到着予定",
    "目的地: 渋谷",
    "",
    "13:20 東京駅 2番線",
    "丸ノ内線・荻窪行 → 13:40 新宿駅",
    "13:46 新宿駅からJR線 → 13:55 渋谷駅",
    "徒歩 5分 / 乗換 1回 / IC 209円",
    "",
    "※ 出口番号は経路元が返した場合だけ表示します。運行情報が変わることがあります。",
  ].join("\n"));
  assert.doesNotMatch(text, /出口\d|best|混雑|車両/);

  const withoutOptional = formatTravelReminder(event(), routeFixture({
    transferCount: null,
    fare: null,
    accessWalkSeconds: null,
    egressWalkSeconds: null,
    steps: routeFixture().steps.map((step) => ({ ...step, from: { ...step.from, platform: null } })),
  }), { departureMs: Date.parse("2026-08-28T04:15:00.000Z"), timezone: "Asia/Tokyo" });
  assert.doesNotMatch(withoutOptional, /番線|乗換|円/);
});

test("route failure sends event-only fallback with an explicit unavailable sentence", () => {
  const text = formatTravelReminder(event(), null, {
    departureMs: Date.parse("2026-08-28T04:15:00.000Z"),
    timezone: "Asia/Tokyo",
  });
  assert.match(text, /次は 14:00「打ち合わせ」/);
  assert.match(text, /13:15 出発/);
  assert.match(text, /目的地: 渋谷/);
  assert.match(text, /経路を取得できませんでした/);
  assert.doesNotMatch(text, /丸ノ内線|209円/);

  const locationless = formatTravelReminder(event({ location: "", online: true }), null, {
    departureMs: START, timezone: "Asia/Tokyo",
  });
  assert.doesNotMatch(locationless, /目的地:/);
});

test("formatter escapes Calendar/provider text for Telegram HTML", () => {
  const text = formatTravelReminder(event({ summary: "<b>会議</b> &確認", location: "<渋谷> &出口" }), routeFixture({
    steps: [{
      ...routeFixture().steps[0],
      from: { name: "<東京駅>", platform: "<2番線>" },
      to: { name: "新宿 &駅", platform: null },
      service: "<丸ノ内線>", headsign: "荻窪 &行",
    }],
  }), { departureMs: Date.parse("2026-08-28T04:15:00.000Z"), timezone: "Asia/Tokyo" });
  assert.match(text, /&lt;b&gt;会議&lt;\/b&gt; &amp;確認/);
  assert.match(text, /目的地: &lt;渋谷&gt; &amp;出口/);
  assert.match(text, /&lt;東京駅&gt; &lt;2番線&gt;/);
  assert.doesNotMatch(text, /<b>|<渋谷>|<丸ノ内線>/);
});

test("travelReminderOnce claims telegram-t5 before send, suppresses duplicate, and releases failures", async () => {
  const calls = [];
  const dueEvent = event({ startMs: NOW + 3 * T5_MS, startIso: "2026-08-28T13:15:00+09:00" });
  const deps = {
    events: [dueEvent], home: HOME, mapsKey: "maps", timezone: "Asia/Tokyo",
    directionsRoute: async () => ({ ...routeFixture(), durationSeconds: 5 * 60 }),
    claimTravel: async (...args) => { calls.push(["claim", ...args]); return true; },
    unclaimTravel: async (...args) => { calls.push(["release", ...args]); },
    sendMessage: async (...args) => { calls.push(["send", ...args]); return { ok: true, result: { message_id: 701 } }; },
    telegramToken: "token", supaUrl: "supa", supaKey: "key", log: (line) => calls.push(["log", line]),
  };
  const first = await travelReminderOnce({ uid: "u-123456789012345", telegram_chat_id: "chat-1", notifications_enabled: true }, NOW, deps);
  assert.equal(first.status, "sent");
  assert.equal(calls.findIndex((x) => x[0] === "claim") < calls.findIndex((x) => x[0] === "send"), true);
  assert.equal(calls.find((x) => x[0] === "claim")[3], "telegram-t5");
  assert.equal(first.telegramMessageId, 701);
  assert.match(calls.find((x) => x[0] === "log")[1], /uid=u-123456789/);
  assert.doesNotMatch(calls.find((x) => x[0] === "log")[1], /打ち合わせ|渋谷|\+81|@/);

  const duplicate = await travelReminderOnce({ uid: "u-123456789012345", telegram_chat_id: "chat-1", notifications_enabled: true }, NOW, {
    ...deps,
    claimTravel: async () => false,
    sendMessage: async () => { throw new Error("duplicate must not send"); },
  });
  assert.equal(duplicate.status, "suppressed");

  const failedCalls = [];
  const failed = await travelReminderOnce({ uid: "u-123456789012345", telegram_chat_id: "chat-1", notifications_enabled: true }, NOW, {
    ...deps,
    claimTravel: async (...args) => { failedCalls.push(["claim", ...args]); return true; },
    unclaimTravel: async (...args) => { failedCalls.push(["release", ...args]); },
    sendMessage: async () => ({ ok: false, status: 500 }),
  });
  assert.equal(failed.status, "send_failed");
  assert.equal(failedCalls.some((x) => x[0] === "release" && x[3] === "telegram-t5"), true);

  const missingIdCalls = [];
  const missingId = await travelReminderOnce({ uid: "u-123456789012345", telegram_chat_id: "chat-1", notifications_enabled: true }, NOW, {
    ...deps,
    claimTravel: async (...args) => { missingIdCalls.push(["claim", ...args]); return true; },
    unclaimTravel: async (...args) => { missingIdCalls.push(["release", ...args]); },
    sendMessage: async () => ({ ok: true, result: {} }),
  });
  assert.equal(missingId.status, "send_failed");
  assert.equal(missingIdCalls.some((x) => x[0] === "release"), true);
});

test("travelReminderOnce sends an event-only reminder when origin is unavailable and does not invent a route", async () => {
  const sent = [];
  const online = event({ id: "online", location: "", online: true, startMs: NOW + T5_MS, startIso: "2026-08-28T13:05:00+09:00" });
  const result = await travelReminderOnce({ uid: "u-online", telegram_chat_id: "chat-online", notifications_enabled: true }, NOW, {
    events: [online],
    directionsRoute: async () => { throw new Error("online must not route"); },
    claimTravel: async () => true,
    sendMessage: async (_token, _chat, text) => { sent.push(text); return { ok: true, result: { message_id: 702 } }; },
    telegramToken: "token", supaUrl: "supa", supaKey: "key",
  });
  assert.equal(result.status, "sent");
  assert.match(sent[0], /次は/);
  assert.doesNotMatch(sent[0], /経路を取得できませんでした/);
});

test("travelReminderOnce does not send before threshold", async () => {
  let sends = 0;
  const dueEvent = event({ id: "early", startMs: NOW + 15 * T5_MS, startIso: "2026-08-28T14:15:00+09:00" });
  const result = await travelReminderOnce({ uid: "u-early", telegram_chat_id: "chat-early", notifications_enabled: true }, NOW, {
    events: [dueEvent], home: HOME,
    directionsRoute: async () => ({ durationSeconds: 5 * 60 }),
    claimTravel: async () => true,
    sendMessage: async () => { sends += 1; return { ok: true, result: { message_id: 703 } }; },
    telegramToken: "token", supaUrl: "supa", supaKey: "key",
  });
  assert.equal(result.status, "suppressed");
  assert.equal(sends, 0);
});

test("travelReminderOnce fails closed without Supabase and performs no route, claim, or send", async () => {
  let routes = 0;
  let claims = 0;
  let sends = 0;
  const online = event({ id: "no-supa", location: "https://meet.example/room", online: true, startMs: NOW + T5_MS });
  const result = await travelReminderOnce({ uid: "u-no-supa", telegram_chat_id: "chat-no-supa", notifications_enabled: true }, NOW, {
    events: [online], home: HOME, telegramToken: "token",
    directionsRoute: async () => { routes += 1; return null; },
    claimTravel: async () => { claims += 1; return true; },
    sendMessage: async () => { sends += 1; return { ok: true, result: { message_id: 704 } }; },
  });
  assert.equal(result.status, "skipped");
  assert.equal(routes, 0);
  assert.equal(claims, 0);
  assert.equal(sends, 0);
});

test("online event reminder catches up from start+1m through start+10m, but not later", async () => {
  const sent = [];
  const eventAt = (offsetMs, id) => event({ id, location: "https://meet.example/room", online: true, startMs: NOW - offsetMs });
  const deps = {
    home: HOME, supaUrl: "supa", supaKey: "key", telegramToken: "token",
    claimTravel: async () => true,
    sendMessage: async (_token, _chat, text) => { sent.push(text); return { ok: true, result: { message_id: 705 + sent.length } }; },
  };
  const one = await travelReminderOnce({ uid: "u-online-1", telegram_chat_id: "chat", notifications_enabled: true }, NOW, {
    ...deps, events: [eventAt(60 * 1000, "online-1")],
  });
  assert.equal(one.status, "sent");
  const boundary = await travelReminderOnce({ uid: "u-online-10", telegram_chat_id: "chat", notifications_enabled: true }, NOW, {
    ...deps, events: [eventAt(10 * 60 * 1000, "online-10")],
  });
  assert.equal(boundary.status, "sent");
  const late = await travelReminderOnce({ uid: "u-online-late", telegram_chat_id: "chat", notifications_enabled: true }, NOW, {
    ...deps, events: [eventAt(10 * 60 * 1000 + 1, "online-late")],
  });
  assert.equal(late.status, "suppressed");
  assert.equal(sent.length, 2);
  assert.doesNotMatch(sent[0], /目的地:|経路を取得できませんでした/);
});

test("Calendar URL online event reaches the reminder at event-start T-5 without routing", async () => {
  const onlineStart = new Date(NOW - 60 * 1000).toISOString();
  const calendar = { async listEventsRaw() {
    return [{ id: "calendar-online", summary: "配信", location: "https://meet.example/room",
      start: { dateTime: onlineStart }, end: { dateTime: new Date(NOW + 30 * 60 * 1000).toISOString() } }];
  } };
  const events = await fetchUpcomingEvents("u-calendar-online", {
    nowMs: NOW, horizonH: 1, lookbackMs: 10 * 60 * 1000, calendar,
  });
  let routes = 0;
  const sent = [];
  const result = await travelReminderOnce({ uid: "u-calendar-online", telegram_chat_id: "chat", notifications_enabled: true }, NOW, {
    events, home: HOME, supaUrl: "supa", supaKey: "key", telegramToken: "token",
    directionsRoute: async () => { routes += 1; return null; }, claimTravel: async () => true,
    sendMessage: async (_token, _chat, text) => { sent.push(text); return { ok: true, result: { message_id: 708 } }; },
  });
  assert.equal(events[0].online, true);
  assert.equal(result.status, "sent");
  assert.equal(routes, 0);
  assert.match(sent[0], /次は/);
});
