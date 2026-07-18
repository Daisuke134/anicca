"use strict";

const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const {
  parseWakeEventKey,
  t0EventKey,
  shouldSendT0,
  shouldFallback,
  lateToken,
  lateQuestion,
  parseLateCallback,
  runningLateText,
  processWakeRows,
  deliverLateNotice,
  handleLateCallback,
  pendingT0Keys,
  listWakeRows,
  claimPrompt,
  markAnswered,
  claimNotified,
} = require("./late-notice.js");

const START = "2026-07-18T09:00:00+09:00";
const T5 = `u1|${START}|5`;
const T0 = `u1|${START}|0`;

test("event-key helpers preserve uid/start and convert only the wake level to T-0", () => {
  assert.deepEqual(parseWakeEventKey(T5), { uid: "u1", startIso: START, level: 5 });
  assert.equal(t0EventKey(T5), T0);
  assert.equal(parseWakeEventKey("bad"), null);
  assert.equal(t0EventKey("bad"), null);
});

test("T-0 is eligible only after event start when the T-5 call was answered and no T-0 row exists", () => {
  const row = { uid: "u1", event_key: T5, answered_at: "2026-07-18T08:55:30+09:00" };
  assert.equal(shouldSendT0(row, Date.parse(START), false), true);
  assert.equal(shouldSendT0(row, Date.parse(START) - 1, false), false);
  assert.equal(shouldSendT0({ ...row, answered_at: null }, Date.parse(START), false), false);
  assert.equal(shouldSendT0(row, Date.parse(START), true), false);
  assert.equal(shouldSendT0({ ...row, event_key: T0 }, Date.parse(START), false), false);
});

test("10-minute fallback uses only persisted called/answered/notified values and includes the boundary", () => {
  const row = { event_key: T0, called_at: "2026-07-18T09:00:00Z", answered_at: null, notified_late_at: null };
  assert.equal(shouldFallback(row, Date.parse("2026-07-18T09:09:59.999Z")), false);
  assert.equal(shouldFallback(row, Date.parse("2026-07-18T09:10:00Z")), true);
  assert.equal(shouldFallback({ ...row, answered_at: "2026-07-18T09:01:00Z" }, Date.parse("2026-07-18T09:10:00Z")), false);
  assert.equal(shouldFallback({ ...row, notified_late_at: "2026-07-18T09:02:00Z" }, Date.parse("2026-07-18T09:10:00Z")), false);
  assert.equal(shouldFallback({ ...row, called_at: "invalid" }, Date.parse("2026-07-18T09:10:00Z")), false);
});

test("late callback token is short, opaque, deterministic, and bound to the event key", () => {
  const a = lateToken(T0, "secret");
  assert.match(a, /^[A-Za-z0-9_-]{22}$/);
  assert.equal(a, lateToken(T0, "secret"));
  assert.notEqual(a, lateToken(T0.replace("|0", "|5"), "secret"));
  assert.notEqual(a, lateToken(T0, "other-secret"));
});

test("question and parser use the adjudicated late:ok/still callback schema", () => {
  const q = lateQuestion("Standup", "abcdefghijklmnopqrstuv");
  assert.match(q.text, /Standup/);
  assert.deepEqual(q.extra.reply_markup.inline_keyboard[0], [
    { text: "出た", callback_data: "late:ok:abcdefghijklmnopqrstuv" },
    { text: "まだ", callback_data: "late:still:abcdefghijklmnopqrstuv" },
  ]);
  assert.deepEqual(parseLateCallback("late:still:abcdefghijklmnopqrstuv"), { action: "still", token: "abcdefghijklmnopqrstuv" });
  assert.equal(parseLateCallback("late:nope:abcdefghijklmnopqrstuv"), null);
  assert.equal(parseLateCallback("ask:yes:e:r"), null);
  assert.equal(runningLateText("Standup"), "running late to Standup");
  assert.equal(runningLateText(""), "running late to the event");
});

test("processWakeRows atomically claims one T-0 prompt and drives fallback only for due DB rows", async () => {
  const sent = [], delivered = [], claimed = [];
  const rows = [
    { uid: "u1", event_key: T5, answered_at: "2026-07-18T08:56:00+09:00", called_at: "2026-07-18T08:55:00+09:00", notified_late_at: null },
    { uid: "u1", event_key: `u1|2026-07-18T07:00:00+09:00|0`, answered_at: null, called_at: "2026-07-17T22:00:00Z", notified_late_at: null },
  ];
  await processWakeRows({ user: { uid: "u1", telegram_chat_id: "7" }, rows, nowMs: Date.parse(START), secret: "s" }, {
    claimPrompt: async (uid, key) => { claimed.push([uid, key]); return true; },
    releasePrompt: async () => { throw new Error("must not release successful send"); },
    summaryFor: async (_uid, startIso) => startIso === START ? "Standup" : "Breakfast",
    sendQuestion: async (_chat, question) => { sent.push(question); return { ok: true }; },
    deliver: async (input) => { delivered.push(input); return { notified: true }; },
  });
  assert.deepEqual(claimed, [["u1", T0]]);
  assert.equal(sent.length, 1);
  assert.match(sent[0].text, /Standup/);
  assert.equal(delivered.length, 1);
  assert.equal(delivered[0].eventKey, "u1|2026-07-18T07:00:00+09:00|0");
  assert.equal(delivered[0].summary, "Breakfast");
});

test("failed T-0 Telegram send releases the atomic prompt claim for a later tick", async () => {
  const released = [];
  await processWakeRows({
    user: { uid: "u1", telegram_chat_id: "7" },
    rows: [{ uid: "u1", event_key: T5, answered_at: "yes", called_at: "x", notified_late_at: null }],
    nowMs: Date.parse(START), secret: "s",
  }, {
    claimPrompt: async () => true,
    releasePrompt: async (...args) => released.push(args),
    summaryFor: async () => "Standup",
    sendQuestion: async () => ({ ok: false }),
    deliver: async () => { throw new Error("not due"); },
  });
  assert.deepEqual(released, [["u1", T0]]);
});

test("deliverLateNotice claims before I/O, dedups parallel/replayed attempts, and marks no-destination terminal", async () => {
  let claimed = false, mailCalls = 0;
  const tg = [];
  const deps = {
    claimNotified: async () => { if (claimed) return false; claimed = true; return true; },
    sendLateNotice: async (_uid, text) => { mailCalls++; assert.equal(text, "running late to Standup"); return { sent: false }; },
    sendMessage: async (...args) => { tg.push(args); return { ok: true }; },
  };
  const input = { uid: "u1", eventKey: T0, summary: "Standup", chatId: "7", token: "tg", noticeOpts: {} };
  assert.deepEqual(await Promise.all([deliverLateNotice(input, deps), deliverLateNotice(input, deps)]), [
    { notified: true, sent: false, reason: "no_destination" },
    { notified: false, deduped: true },
  ]);
  assert.equal(mailCalls, 1);
  assert.equal(tg.length, 1, "no destination produces exactly one Telegram message");
});

test("late callbacks resolve only the uid's matching T-0 token; ok answers, still delivers once", async () => {
  const token = lateToken(T0, "s");
  const marked = [], delivered = [];
  const base = {
    uid: "u1", chatId: "7", data: `late:ok:${token}`, secret: "s",
    rows: [{ uid: "u1", event_key: T0, called_at: "now", answered_at: null, notified_late_at: null }],
  };
  const deps = {
    markAnswered: async (...args) => { marked.push(args); return true; },
    summaryFor: async () => "Standup",
    deliver: async (input) => { delivered.push(input); return { notified: true }; },
  };
  assert.deepEqual(await handleLateCallback(base, deps), { ok: true, action: "ok" });
  assert.deepEqual(marked, [["u1", T0]]);
  assert.equal(delivered.length, 0);

  assert.deepEqual(await handleLateCallback({ ...base, data: `late:still:${token}` }, deps), { ok: true, action: "still", notified: true });
  assert.equal(delivered.length, 1);
  assert.equal(delivered[0].summary, "Standup");
});

test("any message answers only pending T-0 rows sent within the fallback window", () => {
  const now = Date.parse("2026-07-18T09:05:00Z");
  assert.deepEqual(pendingT0Keys([
    { event_key: T0, called_at: "2026-07-18T09:00:00Z", answered_at: null, notified_late_at: null },
    { event_key: "u1|2026-07-18T08:00:00Z|0", called_at: "2026-07-18T08:00:00Z", answered_at: null, notified_late_at: null },
    { event_key: "u1|2026-07-18T09:01:00Z|0", called_at: "2026-07-18T09:01:00Z", answered_at: "yes", notified_late_at: null },
    { event_key: T5, called_at: "2026-07-18T09:00:00Z", answered_at: null, notified_late_at: null },
  ], now), [T0]);
});

test("Supabase helpers keep dedup/response claims atomic and are fully fetch-injected", async () => {
  const calls = [];
  const replies = [
    { ok: true, status: 200, json: async () => [{ uid: "u1", event_key: T0 }] },
    { ok: true, status: 201, json: async () => [] },
    { ok: true, status: 200, json: async () => [{ event_key: T0 }] },
    { ok: true, status: 200, json: async () => [{ event_key: T0 }] },
  ];
  const fetchImpl = async (url, init = {}) => { calls.push({ url, init }); return replies.shift(); };
  const opts = { supaUrl: "https://db.test", supaKey: "k", fetchImpl, nowMs: Date.parse("2026-07-18T09:10:00Z") };
  assert.equal((await listWakeRows("u1", opts)).length, 1);
  assert.equal(await claimPrompt("u1", T0, opts), true);
  assert.equal(await markAnswered("u1", T0, opts), true);
  assert.equal(await claimNotified("u1", T0, { requireUnanswered: true }, opts), true);
  assert.equal(calls[1].init.method, "POST");
  assert.deepEqual(JSON.parse(calls[1].init.body), { uid: "u1", event_key: T0 });
  assert.match(calls[2].url, /answered_at=is\.null/);
  assert.equal(calls[2].init.method, "PATCH");
  assert.match(calls[3].url, /notified_late_at=is\.null/);
  assert.match(calls[3].url, /answered_at=is\.null/);
  assert.equal(calls[3].init.headers.Prefer, "return=representation");
});

test("migration adds exactly the two LM-5 columns idempotently", () => {
  const sql = fs.readFileSync(path.join(__dirname, "../migrations/2026-07-18-lm-wake-log-late-notice.sql"), "utf8");
  assert.match(sql, /ADD COLUMN IF NOT EXISTS answered_at timestamptz/);
  assert.match(sql, /ADD COLUMN IF NOT EXISTS notified_late_at timestamptz/);
  assert.equal((sql.match(/ADD COLUMN IF NOT EXISTS/g) || []).length, 2);
});
