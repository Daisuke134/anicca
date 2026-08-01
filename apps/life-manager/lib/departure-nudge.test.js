"use strict";
// spec 2026-08-01-lm-daily-organ-design.md §5.2.1 + §5.2.2 (#2c).
//
// The ladder is a thing that must STOP. §5.2.1: 停止条件の無い連投は嫌がらせであって製品ではない — so the
// interesting assertions here are not "a message went out", they are "a message did NOT". D4 puts the
// stop and the permission in the SAME write: a rung is sendable only if the PATCH filtered on
// acked_at IS NULL AND last_level_min > <level> came back with a row. Reading the row and then
// deciding would re-open the race that two overlapping 60s ticks lose (the same reasoning that has
// claimWake betting on a unique constraint rather than a SELECT).
//
// Run: node --test lib/departure-nudge.test.js
const { test } = require("node:test");
const assert = require("node:assert");

const { claimNudgeLevel, ackNudge, buildNudgeMessage } = require("./departure-nudge.js");

const SUPA = { supaUrl: "https://supa.invalid", supaKey: "service-role-key" };
const UID = "lm_784ad279";
const EVENT_KEY = "lm_784ad279|2026-08-02T09:00:00+09:00";
const NOW = Date.parse("2026-08-02T07:40:00+09:00");

// Routes by HTTP verb, which is the whole shape of this module: PATCH = "may I", POST = "first rung".
function stubFetch({ patch, post }) {
  const calls = [];
  const fetchImpl = async (url, init = {}) => {
    calls.push({ url: String(url), init });
    const handler = init.method === "POST" ? post : patch;
    if (typeof handler !== "function") throw new Error(`unexpected ${init.method} to ${url}`);
    return handler(String(url), init);
  };
  return { fetchImpl, calls };
}

const rows = (list) => ({ ok: true, status: 200, json: async () => list });
const status = (code) => ({ ok: code >= 200 && code < 300, status: code, json: async () => [] });

test("the first rung inserts the row and is cleared to send", async () => {
  const { fetchImpl, calls } = stubFetch({
    patch: () => rows([]),          // no row yet — nothing to update
    post: () => status(201),        // so the ledger is opened here
  });
  const result = await claimNudgeLevel(UID, EVENT_KEY, 25, { ...SUPA, fetchImpl, nowMs: NOW });

  assert.equal(result.ok, true);
  assert.equal(result.claimed, true);
  const insert = calls.find((c) => c.init.method === "POST");
  assert.ok(insert, "the opening rung must INSERT");
  const body = JSON.parse(insert.init.body);
  assert.equal(body.uid, UID);
  assert.equal(body.event_key, EVENT_KEY);
  assert.equal(body.last_level_min, 25);
  // A plain insert, NOT merge-duplicates: the 409 is the interlock (see below), and resolving the
  // conflict away would silently overwrite a rung another tick already took.
  assert.doesNotMatch(String(insert.init.headers.Prefer || ""), /merge-duplicates/);
});

test("a later rung asks permission and stops in the same write it claims with", async () => {
  const { fetchImpl, calls } = stubFetch({
    patch: () => rows([{ uid: UID, event_key: EVENT_KEY, last_level_min: 10 }]),
    post: () => { throw new Error("must not INSERT when the PATCH already matched"); },
  });
  const result = await claimNudgeLevel(UID, EVENT_KEY, 10, { ...SUPA, fetchImpl, nowMs: NOW });

  assert.equal(result.claimed, true);
  const url = calls[0].url;
  assert.equal(calls[0].init.method, "PATCH");
  // D4: BOTH conditions ride on the one write. Either one alone is a different, broken product —
  // without the gt. the same rung repeats, without acked_at the [了解] does not stop anything.
  assert.match(url, /last_level_min=gt\.10/);
  assert.match(url, /acked_at=is\.null/);
  assert.match(url, new RegExp(`uid=eq\\.${UID}`));
  // The row count IS the answer, so the write has to ask for the rows back.
  assert.match(String(calls[0].init.headers.Prefer || ""), /return=representation/);
  assert.equal(JSON.parse(calls[0].init.body).last_level_min, 10);
});

test("a rung already sent is refused, because last_level_min only ever decreases", async () => {
  const { fetchImpl } = stubFetch({
    patch: () => rows([]),          // gt.25 does not match a row sitting at 25
    post: () => status(409),        // and the row exists, so the fallback insert conflicts
  });
  const result = await claimNudgeLevel(UID, EVENT_KEY, 25, { ...SUPA, fetchImpl, nowMs: NOW });

  assert.equal(result.ok, true);
  assert.equal(result.claimed, false);
});

test("an acknowledged event is refused at every remaining rung", async () => {
  const { fetchImpl } = stubFetch({
    patch: () => rows([]),          // acked_at is set, so the filter excludes the row
    post: () => status(409),
  });
  for (const level of [10, 5, 0, -3, -7]) {
    const result = await claimNudgeLevel(UID, EVENT_KEY, level, { ...SUPA, fetchImpl, nowMs: NOW });
    assert.equal(result.claimed, false, `level ${level} must stay silent after [了解]`);
  }
});

test("losing the opening rung to another tick is not a failure, just a no-send", async () => {
  const { fetchImpl } = stubFetch({
    patch: () => rows([]),
    post: () => status(409),        // the other tick's INSERT landed microseconds earlier
  });
  const result = await claimNudgeLevel(UID, EVENT_KEY, 25, { ...SUPA, fetchImpl, nowMs: NOW });

  assert.equal(result.ok, true);    // nothing broke — two ticks raced and one won, as designed
  assert.equal(result.claimed, false);
});

test("a write we could not confirm sends nothing and says so", async () => {
  const { fetchImpl, calls } = stubFetch({
    patch: () => status(500),
    post: () => { throw new Error("must not INSERT after an unresolved PATCH"); },
  });
  const result = await claimNudgeLevel(UID, EVENT_KEY, 10, { ...SUPA, fetchImpl, nowMs: NOW });

  assert.equal(result.ok, false);
  // The asymmetry that decides this: a nudge missed once is a nudge; a nudge sent twice is the
  // harassment §5.2.1 forbids. Not knowing whether the claim landed falls to the silent side.
  assert.equal(result.claimed, false);
  assert.equal(calls.filter((c) => c.init.method === "POST").length, 0);
});

test("the stop is a latch: a second tap cannot rewrite why the ladder ended", async () => {
  let taps = 0;
  const { fetchImpl, calls } = stubFetch({
    patch: () => (taps++ === 0
      ? rows([{ uid: UID, event_key: EVENT_KEY, ack_reason: "tap" }])
      : rows([])),                  // acked_at is no longer null, so the second tap matches nothing
  });

  const first = await ackNudge(UID, EVENT_KEY, "tap", { ...SUPA, fetchImpl, nowMs: NOW });
  assert.equal(first.ok, true);
  assert.equal(first.matched, 1);
  assert.match(calls[0].url, /acked_at=is\.null/);
  const body = JSON.parse(calls[0].init.body);
  assert.equal(body.ack_reason, "tap");
  assert.equal(body.acked_at, new Date(NOW).toISOString());

  const second = await ackNudge(UID, EVENT_KEY, "call_answered", { ...SUPA, fetchImpl, nowMs: NOW });
  assert.equal(second.ok, true);    // the write landed and correctly changed nothing
  assert.equal(second.matched, 0);
});

// ── the six rungs (§5.2.1 / §5.2.2「送る文」) ────────────────────────────────────────────────────

// 段ごとに文が変わり、T+7 以外には [了解] が付く（T+7 は梯子の終端 = spec §5.2.2 D6）。
// callback data は 'depart:ack:<startIso>' の形（D7。64 byte 上限があるので uid は載せない）。
test("each rung says something different and carries the acknowledge button", () => {
  const ev = { summary: "打合せ", startIso: "2026-08-02T09:00:00+09:00", location: "渋谷" };
  const at = (level) => buildNudgeMessage({ level, ev, departureIso: "2026-08-02T08:05:00+09:00", lang: "ja" });

  assert.match(at(25).text, /8:05/);
  assert.match(at(25).text, /25/);
  assert.notEqual(at(10).text, at(5).text);
  assert.match(at(0).text, /🚨/);
  assert.equal(
    at(0).extra.reply_markup.inline_keyboard[0][0].callback_data,
    "depart:ack:2026-08-02T09:00:00+09:00",
  );
  assert.equal(at(-7).extra, undefined);   // 終端に押すものは無い
});

test("english users get english", () => {
  const ev = { summary: "Standup", startIso: "2026-08-02T09:00:00+09:00", location: "Shibuya" };
  const m = buildNudgeMessage({ level: 0, ev, departureIso: "2026-08-02T08:05:00+09:00", lang: "en" });
  assert.match(m.text, /leave/i);
  assert.doesNotMatch(m.text, /[ぁ-んァ-ン一-龯]/);
});

test("the callback data stays inside Telegram's 64-byte limit", () => {
  const ev = { summary: "x".repeat(300), startIso: "2026-08-02T09:00:00+09:00", location: "y".repeat(300) };
  const m = buildNudgeMessage({ level: 25, ev, departureIso: "2026-08-02T08:05:00+09:00", lang: "ja" });
  const data = m.extra.reply_markup.inline_keyboard[0][0].callback_data;
  assert.equal(Buffer.byteLength(data, "utf8") <= 64, true, `callback_data is ${Buffer.byteLength(data, "utf8")} bytes`);
});

// The ladder's whole job is to move someone at a specific minute, so the LATE rungs have to say what
// being late now costs. T+3 is the first rung where the answer is no longer "you can still make it".
test("the overtime rungs name the arrival the user is now buying", () => {
  const ev = { summary: "打合せ", startIso: "2026-08-02T09:00:00+09:00", location: "渋谷" };
  const late = buildNudgeMessage({ level: -3, ev, departureIso: "2026-08-02T08:05:00+09:00", lang: "ja" });
  assert.match(late.text, /09:03/);          // 3 minutes past departure = 3 minutes past arrival
  assert.match(late.text, /3/);
  const lateEn = buildNudgeMessage({ level: -3, ev, departureIso: "2026-08-02T08:05:00+09:00", lang: "en" });
  assert.match(lateEn.text, /09:03/);
  assert.doesNotMatch(lateEn.text, /[ぁ-んァ-ン一-龯]/);
});

// sendMessage posts with parse_mode HTML, so a calendar entry someone else wrote is untrusted input.
test("an event title cannot inject markup into the message", () => {
  const ev = { summary: "<b>x</b>", startIso: "2026-08-02T09:00:00+09:00", location: "<i>y</i>" };
  const m = buildNudgeMessage({ level: 25, ev, departureIso: "2026-08-02T08:05:00+09:00", lang: "ja" });
  assert.doesNotMatch(m.text, /<b>|<i>/);
  assert.match(m.text, /&lt;b&gt;/);
});
