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
  deleteLiveLocation,
  claimLateEvent,
  processLocationLateNotice,
  markAnswered,
  recordAmdResult,
  applyAmdDetection,
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

test("deleteLiveLocation removes exactly the named tenant's row and reports the honest count", async () => {
  // A fake store that honours the PostgREST uid filter: deleting u1 must leave u2's fix untouched.
  const store = new Map([
    ["u1", { uid: "u1", ...LIVE }],
    ["u2", { uid: "u2", latitude: 1.5, longitude: 2.5, observed_at: LIVE.observed_at, expires_at: LIVE.expires_at }],
  ]);
  const fetchImpl = async (url, init = {}) => {
    const parsed = new URL(url);
    assert.equal(parsed.pathname, "/rest/v1/lm_user_locations");
    assert.equal(String(init.method || "GET").toUpperCase(), "DELETE");
    assert.match(init.headers.Prefer, /return=representation/, "the delete must read back what it removed");
    const uid = String(parsed.searchParams.get("uid") || "").replace(/^eq\./, "");
    assert.ok(uid, "an unfiltered DELETE would wipe every tenant — the uid filter is mandatory");
    const removed = store.has(uid) ? [store.get(uid)] : [];
    store.delete(uid);
    return { ok: true, status: 200, json: async () => removed };
  };
  const opts = { supaUrl: "https://db.test", supaKey: "k", fetchImpl };
  assert.deepEqual(await deleteLiveLocation("u1", opts), { deleted: 1 });
  assert.equal(store.has("u1"), false, "u1's row is gone");
  assert.deepEqual(store.get("u2"), { uid: "u2", latitude: 1.5, longitude: 2.5, observed_at: LIVE.observed_at, expires_at: LIVE.expires_at },
    "the other tenant's location is untouched");
  assert.deepEqual(await deleteLiveLocation("u1", opts), { deleted: 0 }, "a second delete honestly reports zero rows");
});

test("deleteLiveLocation refuses to guess: missing config or a failed request returns null, never a count", async () => {
  assert.equal(await deleteLiveLocation("u1", { supaKey: "k", fetchImpl: async () => { throw new Error("unreachable"); } }), null);
  assert.equal(await deleteLiveLocation("", { supaUrl: "https://db.test", supaKey: "k", fetchImpl: async () => { throw new Error("unreachable"); } }), null);
  assert.equal(await deleteLiveLocation("u1", {
    supaUrl: "https://db.test", supaKey: "k",
    fetchImpl: async () => ({ ok: false, status: 500, json: async () => [] }),
  }), null);
  assert.equal(await deleteLiveLocation("u1", {
    supaUrl: "https://db.test", supaKey: "k",
    fetchImpl: async () => { throw new Error("network down"); },
  }), null);
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

// Found in production on 2026-07-25: an all-day meeting with a location was claimed at 09:31 JST and
// runs until 18:00, so every later event that day was unreachable — the finder takes only the FIRST
// event with a location, and a failed claim returned immediately instead of considering the next one.
test("a deduplicated leading event does not suppress the next event's late notice", async () => {
  const leading = { ...EVENT, id: "already-claimed" };
  const next = { ...EVENT, id: "still-actionable" };
  const claimed = new Set(["already-claimed"]);
  const notified = [];
  const messages = [];
  const deps = {
    routeMinutes: async () => 43,
    claimEvent: async (_uid, key) => { if (claimed.has(key)) return false; claimed.add(key); return true; },
    sendLateNotice: async (_uid, event) => { notified.push(event.id); return { sent: true, id: "resend-1" }; },
    sendMessage: async (_token, _chat, text) => { messages.push(text); return { ok: true }; },
  };

  const result = await processLocationLateNotice({
    user: { uid: "u1", telegram_chat_id: "7" }, location: LIVE,
    events: [leading, next], nowMs: NOW, telegramToken: "tg",
  }, deps);

  assert.equal(result.sent, true);
  assert.deepEqual(notified, ["still-actionable"], "the notice must be about the event we could claim");
  assert.equal(messages.length, 1);
});

test("when every candidate is already claimed the run stays deduplicated and silent", async () => {
  let mailCalls = 0;
  const messages = [];
  const deps = {
    routeMinutes: async () => 43,
    claimEvent: async () => false,
    sendLateNotice: async () => { mailCalls++; return { sent: true }; },
    sendMessage: async (_token, _chat, text) => { messages.push(text); return { ok: true }; },
  };

  const result = await processLocationLateNotice({
    user: { uid: "u1", telegram_chat_id: "7" }, location: LIVE,
    events: [{ ...EVENT, id: "a" }, { ...EVENT, id: "b" }], nowMs: NOW, telegramToken: "tg",
  }, deps);

  assert.deepEqual(result, { decision: "late", deduped: true });
  assert.equal(mailCalls, 0);
  assert.deepEqual(messages, []);
});

// The journey's Telegram leg was unauditable: the send result was discarded, so nothing downstream
// could name the message that was actually delivered. Carry the id the provider returns.
test("the delivered Telegram message id is carried on the result", async () => {
  const deps = {
    routeMinutes: async () => 43,
    claimEvent: async () => true,
    sendLateNotice: async () => ({ sent: true, id: "resend-1" }),
    sendMessage: async () => ({ ok: true, result: { message_id: 4242 } }),
  };
  const result = await processLocationLateNotice({
    user: { uid: "u1", telegram_chat_id: "7" }, location: LIVE,
    events: [EVENT], nowMs: NOW, telegramToken: "tg",
  }, deps);
  assert.equal(result.sent, true);
  assert.equal(result.telegramMessageId, 4242);
});

test("a Telegram send that returns no id leaves the field absent rather than inventing one", async () => {
  const deps = {
    routeMinutes: async () => 43,
    claimEvent: async () => true,
    sendLateNotice: async () => ({ sent: true, id: "resend-1" }),
    sendMessage: async () => ({ ok: false }),
  };
  const result = await processLocationLateNotice({
    user: { uid: "u1", telegram_chat_id: "7" }, location: LIVE,
    events: [EVENT], nowMs: NOW, telegramToken: "tg",
  }, deps);
  assert.equal(result.sent, true);
  assert.equal("telegramMessageId" in result, false);
});

// ---------------------------------------------------------------------------
// spec 2026-08-01-lm-daily-organ-design.md §1.3 + §3 row 2 — AMD detection telemetry.
//
// Measured over every Telnyx call event correlated to lm_wake_log: human → answered_at set, 10/10;
// machine/not_sure → null, 33/33. The recording path is healthy; the TABLE is the defect. Four
// different realities ("a person answered", "rang unanswered", "voicemail", "the webhook never
// arrived") collapse into one reading, so a rotated Telnyx signing key would make every call fail
// silently forever with nothing anywhere recording it. These tests pin the column that separates
// them, and pin that a PATCH matching zero rows is not the same value as a PATCH that never landed.
// ---------------------------------------------------------------------------

const SUPA = { supaUrl: "https://supa.invalid", supaKey: "service-role-key" };

function stubFetch(handler) {
  const calls = [];
  const fetchImpl = async (url, init) => {
    calls.push({ url: String(url), init: init || {}, body: JSON.parse((init || {}).body || "null") });
    return handler(String(url), init || {});
  };
  return { fetchImpl, calls };
}

const patchedRows = (rows) => async () => ({ ok: true, status: 200, json: async () => rows });

test("AMD human writes both the raw result and answered_at", async () => {
  const { fetchImpl, calls } = stubFetch(patchedRows([{ event_key: "k" }]));
  const out = await applyAmdDetection("lm_u", "k", {
    result: "human", nowMs: Date.parse("2026-08-01T00:10:00Z"), ...SUPA, fetchImpl,
  });

  assert.equal(out.result, "human");
  assert.equal(out.amd.ok, true);
  assert.equal(out.amd.matched, 1);
  assert.equal(out.answered.ok, true);
  assert.equal(out.answered.matched, 1);

  const amdWrite = calls.find((c) => c.body && "amd_result" in c.body);
  const answeredWrite = calls.find((c) => c.body && "answered_at" in c.body);
  assert.ok(amdWrite, "the raw AMD result must be persisted");
  assert.ok(answeredWrite, "a human detection must still set answered_at");
  assert.equal(amdWrite.body.amd_result, "human");
  assert.equal(answeredWrite.body.answered_at, "2026-08-01T00:10:00.000Z");
  // The amd_result write must NOT inherit the answered_at=is.null latch: a detection arriving after
  // a row is already answered would otherwise be dropped, i.e. unrecorded again.
  assert.doesNotMatch(amdWrite.url, /answered_at=is\.null/);
  assert.match(answeredWrite.url, /answered_at=is\.null/);
});

test("AMD machine records the voicemail as itself and never sets answered_at", async () => {
  const { fetchImpl, calls } = stubFetch(patchedRows([{ event_key: "k" }]));
  const out = await applyAmdDetection("lm_u", "k", { result: "machine", ...SUPA, fetchImpl });

  assert.equal(out.amd.ok, true);
  assert.equal(out.amd.matched, 1);
  assert.equal(out.answered, null, "no answered_at write may be attempted for a machine");
  assert.equal(calls.length, 1);
  assert.equal(calls[0].body.amd_result, "machine");
  assert.equal("answered_at" in calls[0].body, false);
  assert.equal(calls.some((c) => /answered_at=is\.null/.test(c.url)), false);
});

test("AMD not_sure is recorded as itself, not folded into machine or dropped", async () => {
  const { fetchImpl, calls } = stubFetch(patchedRows([{ event_key: "k" }]));
  const out = await applyAmdDetection("lm_u", "k", { result: "not_sure", ...SUPA, fetchImpl });

  assert.equal(out.amd.matched, 1);
  assert.equal(out.answered, null);
  assert.equal(calls.length, 1);
  assert.equal(calls[0].body.amd_result, "not_sure");
  assert.equal("answered_at" in calls[0].body, false);
});

// The defect §1.3 names outright: markAnswered returned false for "matched zero rows" AND for "the
// request never landed", so a rotated signing key looked exactly like a user who did not pick up.
test("a PATCH matching zero rows is distinguishable from a PATCH whose request failed", async () => {
  const zeroRows = await markAnswered("lm_u", "k", {
    ...SUPA, fetchImpl: async () => ({ ok: true, status: 200, json: async () => [] }),
  });
  assert.deepEqual(
    { ok: zeroRows.ok, matched: zeroRows.matched },
    { ok: true, matched: 0 },
    "the write reached Supabase and correctly matched nothing",
  );

  const httpFail = await markAnswered("lm_u", "k", {
    ...SUPA, fetchImpl: async () => ({ ok: false, status: 503, json: async () => ({}) }),
  });
  assert.equal(httpFail.ok, false, "a 5xx is a failure to record, not a zero match");
  assert.equal(httpFail.matched, 0);
  assert.ok(httpFail.error, "the failure must name itself");

  const thrown = await markAnswered("lm_u", "k", {
    ...SUPA, fetchImpl: async () => { throw new Error("ECONNRESET"); },
  });
  assert.equal(thrown.ok, false);
  assert.ok(thrown.error);

  // Same contract on the amd_result write, or the new column inherits the old blindness.
  const amdZero = await recordAmdResult("lm_u", "k", {
    result: "machine", ...SUPA, fetchImpl: async () => ({ ok: true, status: 200, json: async () => [] }),
  });
  assert.deepEqual({ ok: amdZero.ok, matched: amdZero.matched }, { ok: true, matched: 0 });
  const amdFail = await recordAmdResult("lm_u", "k", {
    result: "machine", ...SUPA, fetchImpl: async () => ({ ok: false, status: 403, json: async () => ({}) }),
  });
  assert.equal(amdFail.ok, false);
  assert.equal(amdFail.matched, 0);
});

// server.js:816 (the media bridge, LM_AMD=off fallback) calls markAnswered with no new options.
// It must keep issuing exactly the one latched answered_at PATCH it always did.
test("the media bridge caller still issues one latched answered_at PATCH and nothing else", async () => {
  const { fetchImpl, calls } = stubFetch(patchedRows([{ event_key: "k" }]));
  const out = await markAnswered("lm_u", "k", { ...SUPA, nowMs: Date.parse("2026-08-01T00:10:00Z"), fetchImpl });

  assert.equal(out.matched, 1);
  assert.equal(calls.length, 1);
  assert.equal(calls[0].init.method, "PATCH");
  assert.match(calls[0].url, /\/rest\/v1\/lm_wake_log\?/);
  assert.match(calls[0].url, /answered_at=is\.null/);
  assert.deepEqual(calls[0].body, { answered_at: "2026-08-01T00:10:00.000Z" });
});

// `answered: null` is reserved for "not a human, so not attempted". A human we could not correlate
// must report a FAILED write, not the same null — otherwise an undecodable client_state reads as a
// deliberate skip, which is exactly the ambiguity this change exists to remove.
test("a detection with no wake identifiers writes nothing and says so", async () => {
  const explode = async () => { throw new Error("must not be called"); };
  const out = await applyAmdDetection("", "", { result: "human", ...SUPA, fetchImpl: explode });
  assert.equal(out.amd.ok, false);
  assert.equal(out.amd.error, "missing_args");
  assert.equal(out.answered.ok, false);
  assert.equal(out.answered.error, "missing_args");
});
