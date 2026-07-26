"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

const { runAftercare } = require("./care-aftercare.js");
const { PHYSICAL_STRINGS, formatCareBookingReport } = require("./i18n.js");

const USER = Object.freeze({ uid: "u1", name: "山田太郎", telegram_chat_id: 4242 });
const CANDIDATES = Object.freeze([
  Object.freeze({
    provider_id: "p1", public_name: "丸の内内科クリニック", official_url: "https://a.example.jp",
    reservation_route: "web", reservation_url: "https://a.example.jp/reserve", usual_provider: false,
  }),
  Object.freeze({
    provider_id: "p2", public_name: "大手町ファミリークリニック", official_url: "https://b.example.jp",
    reservation_route: "email", reservation_url: "mailto:b@example.jp", usual_provider: false,
  }),
  Object.freeze({
    provider_id: "p3", public_name: "東京駅前医院", official_url: "https://c.example.jp",
    reservation_route: "phone_only", reservation_url: null, usual_provider: false,
  }),
]);

function fakeDeps(overrides = {}) {
  const sent = [];
  const events = [];
  const records = [];
  return {
    sent, events, records,
    telegramToken: "tok",
    async sendMessage(token, chatId, text, extra) {
      sent.push({ token, chatId, text, extra });
      return { ok: true, result: { message_id: 900 + sent.length } };
    },
    calendar: {
      async createEvent(uid, args) { events.push({ uid, args }); return { successful: true }; },
    },
    async recordBooking(record) { records.push(record); return true; },
    ...overrides,
  };
}

test("a booked outcome sends the §9.11 事後報告 copy verbatim from i18n", async () => {
  const deps = fakeDeps();
  const result = await runAftercare({
    booking: {
      outcome: "booked",
      provider_id: "p1",
      booked_slot: "2026-08-06T18:00:00+09:00",
      confirmation: { number: "A1B2C3", booking_id: null, text: "ご予約を受け付けました。" },
    },
    candidate: CANDIDATES[0],
    candidates: CANDIDATES,
    careType: "clinic",
    sinceDays: 122,
    user: USER,
    deps,
  });

  assert.equal(result.status, "reported");
  assert.equal(deps.sent.length, 1);
  assert.equal(deps.sent[0].chatId, 4242);

  const expected = PHYSICAL_STRINGS.ja.booked
    .replace("{emoji}", PHYSICAL_STRINGS.ja.emoji.clinic)
    .replace("{careLabel}", PHYSICAL_STRINGS.ja.careLabels.clinic)
    .replace("{sinceLabel}", "4ヶ月")
    .replace("{providerName}", "丸の内内科クリニック")
    .replace("{slotLabel}", "木曜18:00");
  assert.equal(deps.sent[0].text, expected);
  assert.equal(result.message, expected);
});

test("the usual provider gets §9.11's いつものお店 shape", async () => {
  const deps = fakeDeps();
  await runAftercare({
    booking: {
      outcome: "booked", provider_id: "p1", booked_slot: "2026-08-08T11:00:00+09:00",
      confirmation: { number: "Z9", booking_id: null, text: "予約を受け付けました" },
    },
    candidate: { ...CANDIDATES[0], public_name: "いつもの床屋", usual_provider: true },
    candidates: CANDIDATES,
    careType: "haircut",
    sinceDays: 43,
    user: USER,
    deps,
  });
  const expected = PHYSICAL_STRINGS.ja.bookedUsual
    .replace("{emoji}", PHYSICAL_STRINGS.ja.emoji.haircut)
    .replace("{sinceLabel}", "6週間")
    .replace("{slotLabel}", "土曜11:00");
  assert.equal(deps.sent[0].text, expected);
});

test("a booked outcome writes the calendar event and records the booking on the scan row", async () => {
  const deps = fakeDeps();
  await runAftercare({
    booking: {
      outcome: "booked", provider_id: "p1", booked_slot: "2026-08-06T18:00:00+09:00",
      confirmation: { number: "A1B2C3", booking_id: null, text: "ご予約を受け付けました。" },
    },
    candidate: CANDIDATES[0], candidates: CANDIDATES, careType: "clinic", sinceDays: 122, user: USER, deps,
  });

  assert.equal(deps.events.length, 1, "exactly one calendar event");
  assert.equal(deps.events[0].uid, "u1");
  assert.equal(deps.events[0].args.summary, "丸の内内科クリニック");
  assert.equal(deps.events[0].args.start_datetime, "2026-08-06T09:00:00");
  assert.equal(deps.events[0].args.timezone, "UTC");

  assert.equal(deps.records.length, 1);
  assert.deepEqual(deps.records[0], {
    outcome: "booked",
    provider_id: "p1",
    booked_slot: "2026-08-06T18:00:00+09:00",
    confirmation: { number: "A1B2C3", booking_id: null, text: "ご予約を受け付けました。" },
    reason_code: null,
    telegram_message_id: 901,
    calendar_event_created: true,
  });
});

test("an honest failure presents the candidates and writes NO calendar event", async () => {
  const deps = fakeDeps();
  const result = await runAftercare({
    booking: {
      outcome: "honest_failure",
      provider_id: "p1",
      reason_code: "unmappable_required_field",
      reason: "予約フォームに私が読み取れない必須項目があります: 保険証番号",
    },
    candidate: CANDIDATES[0], candidates: CANDIDATES, careType: "clinic", sinceDays: 122, user: USER, deps,
  });

  assert.equal(result.status, "reported");
  assert.equal(deps.events.length, 0, "no calendar event for a booking that did not happen");
  assert.equal(deps.records[0].outcome, "honest_failure");
  assert.equal(deps.records[0].calendar_event_created, false);

  const text = deps.sent[0].text;
  assert.match(text, /丸の内内科クリニック/);
  assert.match(text, /大手町ファミリークリニック/);
  assert.match(text, /東京駅前医院/);
  assert.match(text, /保険証番号/, "says WHY booking failed");
  assert.equal(text, formatCareBookingReport({
    outcome: "honest_failure",
    careType: "clinic",
    reason: "予約フォームに私が読み取れない必須項目があります: 保険証番号",
    candidates: CANDIDATES,
  }));
});

test("a possibly-booked outcome is reported as unconfirmed, with no calendar event and no resend", async () => {
  const deps = fakeDeps();
  const result = await runAftercare({
    booking: {
      outcome: "possibly_booked",
      provider_id: "p1",
      booked_slot: "2026-08-06T18:00:00+09:00",
      reason_code: "no_confirmation_signal",
      reason: "送信は行いましたが完了の確認が取れませんでした",
    },
    candidate: CANDIDATES[0], candidates: CANDIDATES, careType: "clinic", sinceDays: 122, user: USER, deps,
  });

  assert.equal(result.status, "reported");
  assert.equal(deps.events.length, 0);
  assert.equal(deps.sent.length, 1);
  assert.match(deps.sent[0].text, /二重予約/);
  assert.equal(deps.records[0].outcome, "possibly_booked");
});

test("an unreachable user still gets the booking recorded", async () => {
  const deps = fakeDeps();
  const result = await runAftercare({
    booking: {
      outcome: "booked", provider_id: "p1", booked_slot: "2026-08-06T18:00:00+09:00",
      confirmation: { number: "A1B2C3", booking_id: null, text: "" },
    },
    candidate: CANDIDATES[0], candidates: CANDIDATES, careType: "clinic", sinceDays: 122,
    user: { uid: "u1", name: "山田太郎", telegram_chat_id: null },
    deps,
  });
  assert.equal(result.status, "unreachable");
  assert.equal(deps.sent.length, 0);
  assert.equal(deps.records.length, 1);
  assert.equal(deps.records[0].telegram_message_id, null);
});

test("a failed calendar write is recorded as failed rather than claimed as done", async () => {
  const deps = fakeDeps({
    calendar: { async createEvent() { return { successful: false }; } },
  });
  const result = await runAftercare({
    booking: {
      outcome: "booked", provider_id: "p1", booked_slot: "2026-08-06T18:00:00+09:00",
      confirmation: { number: "A1B2C3", booking_id: null, text: "" },
    },
    candidate: CANDIDATES[0], candidates: CANDIDATES, careType: "clinic", sinceDays: 122, user: USER, deps,
  });
  assert.equal(result.calendarEventCreated, false);
  assert.equal(deps.records[0].calendar_event_created, false);
});
