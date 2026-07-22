"use strict";

const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const {
  NO_DESTINATION_MESSAGE,
  evaluateLateArrival,
  formatLateSuccessMessage,
  upsertLiveLocation,
  getLiveLocation,
  claimLateEvent,
  processLocationLateNotice,
} = require("./late-notice.js");
const { sendLateNotice } = require("./notify.js");

const NOW = Date.parse("2026-07-21T09:45:00+09:00");
const EVENT = {
  id: "event-1", summary: "プロダクト定例", location: "渋谷ヒカリエ",
  startMs: Date.parse("2026-07-21T10:15:00+09:00"), startIso: "2026-07-21T10:15:00+09:00",
  attendees: [{ email: "guest@example.com" }],
};
const LIVE = {
  latitude: 35.681236, longitude: 139.767125,
  observed_at: "2026-07-21T00:44:00.000Z", expires_at: "2026-07-21T01:00:00.000Z",
};

test("location gate distinguishes missing, expired, on-time, and late", () => {
  assert.deepEqual(evaluateLateArrival({ nowMs: NOW, event: EVENT, travelMinutes: 35, location: null }), {
    decision: "location_missing",
  });
  assert.deepEqual(evaluateLateArrival({ nowMs: NOW, event: EVENT, travelMinutes: 35, location: { ...LIVE, expires_at: "2026-07-21T00:45:00.000Z" } }), {
    decision: "location_expired",
  });
  assert.deepEqual(evaluateLateArrival({ nowMs: NOW, event: EVENT, travelMinutes: 30, location: LIVE }), {
    decision: "on_time", arrivalMs: EVENT.startMs, lateMinutes: 0,
  });
  assert.deepEqual(evaluateLateArrival({ nowMs: NOW, event: EVENT, travelMinutes: 43, location: LIVE }), {
    decision: "late", arrivalMs: Date.parse("2026-07-21T10:28:00+09:00"), lateMinutes: 13,
  });
});

test("success copy follows spec table and rounds the notice ETA up to five minutes", () => {
  assert.equal(formatLateSuccessMessage(EVENT, Date.parse("2026-07-21T10:28:00+09:00"), 13),
    "📨 現在地から見て10:15に間に合わないため、先方に「15分ほど遅れます」とメールを送っておきました。次の電車なら10:28着です。");
});

test("location helpers upsert the latest live fix, enforce expiry, and atomically claim an event", async () => {
  const calls = [];
  const replies = [
    { ok: true, status: 201, json: async () => [] },
    { ok: true, status: 200, json: async () => [{ uid: "u1", ...LIVE }] },
    { ok: true, status: 201, json: async () => [] },
  ];
  const fetchImpl = async (url, init = {}) => { calls.push({ url, init }); return replies.shift(); };
  const opts = { supaUrl: "https://db.test", supaKey: "k", fetchImpl };
  assert.equal(await upsertLiveLocation("u1", {
    latitude: LIVE.latitude, longitude: LIVE.longitude,
    observedAtMs: Date.parse(LIVE.observed_at), expiresAtMs: Date.parse(LIVE.expires_at), messageId: "41",
  }, opts), true);
  assert.match(calls[0].url, /lm_user_locations\?on_conflict=uid/);
  assert.match(calls[0].init.headers.Prefer, /resolution=merge-duplicates/);
  assert.deepEqual(JSON.parse(calls[0].init.body), {
    uid: "u1", latitude: LIVE.latitude, longitude: LIVE.longitude,
    telegram_message_id: "41", source: "telegram_live_location",
    observed_at: LIVE.observed_at, expires_at: LIVE.expires_at,
  });
  assert.deepEqual(await getLiveLocation("u1", NOW, opts), { uid: "u1", ...LIVE });
  assert.equal(await claimLateEvent("u1", "event-1", opts), true);
  assert.match(calls[2].url, /lm_late_notice_log/);
  assert.deepEqual(JSON.parse(calls[2].init.body), { uid: "u1", event_key: "event-1" });
});

test("gate-closed and on-time decisions perform no claim, email, or Telegram I/O", async () => {
  let sideEffects = 0;
  const deps = {
    routeMinutes: async () => 30,
    claimEvent: async () => { sideEffects++; return true; },
    sendLateNotice: async () => { sideEffects++; return { sent: true }; },
    sendMessage: async () => { sideEffects++; },
  };
  assert.deepEqual(await processLocationLateNotice({ user: { uid: "u1" }, location: null, events: [EVENT], nowMs: NOW }, deps),
    { decision: "location_missing" });
  assert.deepEqual(await processLocationLateNotice({ user: { uid: "u1" }, location: LIVE, events: [EVENT], nowMs: NOW }, deps),
    { decision: "on_time", arrivalMs: EVENT.startMs, lateMinutes: 0 });
  assert.equal(sideEffects, 0);
});

test("late event with no external email is claimed once and reports the exact honest failure copy", async () => {
  let claimed = false, mailCalls = 0;
  const messages = [];
  const input = {
    user: { uid: "u1", telegram_chat_id: "7" }, location: LIVE,
    events: [{ ...EVENT, attendees: [] }], nowMs: NOW, telegramToken: "tg",
  };
  const deps = {
    routeMinutes: async () => 43,
    claimEvent: async () => { if (claimed) return false; claimed = true; return true; },
    sendLateNotice: async () => { mailCalls++; return { sent: false }; },
    sendMessage: async (_token, _chat, text) => { messages.push(text); return { ok: true }; },
  };
  assert.equal((await processLocationLateNotice(input, deps)).reason, "no_destination");
  assert.deepEqual(await processLocationLateNotice(input, deps), { decision: "late", deduped: true });
  assert.equal(mailCalls, 0);
  assert.deepEqual(messages, [NO_DESTINATION_MESSAGE]);
  assert.equal(NO_DESTINATION_MESSAGE, "⚠️ 先方の連絡先が見つからず、遅刻連絡は送れていません");
});

test("late event sends one Resend notice then the exact success report", async () => {
  const mail = [], messages = [];
  const result = await processLocationLateNotice({
    user: { uid: "u1", name: "Dais", email: "dais@example.com", telegram_chat_id: "7" },
    location: LIVE, events: [EVENT], nowMs: NOW, telegramToken: "tg", noticeOpts: { resendKey: "r" },
  }, {
    routeMinutes: async (origin, destination) => {
      assert.equal(origin, "35.681236,139.767125");
      assert.equal(destination, EVENT.location);
      return 43;
    },
    claimEvent: async (_uid, key) => { assert.equal(key, EVENT.id); return true; },
    sendLateNotice: async (...args) => { mail.push(args); return { sent: true, to: "guest@example.com" }; },
    sendMessage: async (_token, _chat, text) => { messages.push(text); return { ok: true }; },
  });
  assert.equal(result.sent, true);
  assert.equal(mail.length, 1);
  assert.equal(mail[0][0], "u1");
  assert.equal(mail[0][1].id, EVENT.id);
  assert.equal(mail[0][2].etaMinutes, 15);
  assert.deepEqual(messages, [
    "📨 現在地から見て10:15に間に合わないため、先方に「15分ほど遅れます」とメールを送っておきました。次の電車なら10:28着です。",
  ]);
});

test("structured notice reuses the Resend mail path and excludes self/organizer attendees", async () => {
  const calls = [];
  const result = await sendLateNotice("u1", {
    ...EVENT,
    attendees: [
      { email: "self@example.com", self: true },
      { email: "organizer@example.com", organizer: true },
      { email: "guest@example.com" },
    ],
  }, {
    userName: "Dais", userEmail: "dais@example.com", etaMinutes: 15, resendKey: "r",
    fetchImpl: async (url, init) => {
      calls.push({ url, body: JSON.parse(init.body) });
      return { ok: true, status: 200, json: async () => ({ id: "mail-1" }) };
    },
  });
  assert.equal(result.sent, true);
  assert.equal(calls.length, 1);
  assert.deepEqual(calls[0].body.to, ["guest@example.com"]);
  assert.match(calls[0].body.text, /Sent automatically by Life Manager on Dais's behalf/);
});

test("migration creates additive location and event-dedup tables", () => {
  const sql = fs.readFileSync(path.join(__dirname, "../migrations/2026-07-21-lm30-location-gate.sql"), "utf8");
  assert.match(sql, /CREATE TABLE IF NOT EXISTS lm_user_locations/);
  assert.match(sql, /expires_at timestamptz NOT NULL/);
  assert.match(sql, /CREATE TABLE IF NOT EXISTS lm_late_notice_log/);
  assert.match(sql, /PRIMARY KEY \(uid, event_key\)/);
});
