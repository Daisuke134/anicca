"use strict";
// H2 ORG-diet — the production leg: ask the question, record the tap.
//
// Two failure modes these tests exist to make impossible:
//   1. The 60s tick sees the lunch window for 120 consecutive minutes. Without a durable claim the
//      user gets 120 identical questions. The claim is the INSERT, and it happens BEFORE the send.
//   2. A tap that writes to somebody else's row. The diet ledger is small data, but it is still the
//      user's day — the same actorId===chatId + row-re-verify guard the payout intake uses applies.
// Run: node --test lib/diet-runtime.test.js

const test = require("node:test");
const assert = require("node:assert/strict");
const {
  dietUserOnce,
  handleDietCallback,
  readDietAskState,
  localDay,
  resolveDietTzOffsetH,
  resetDietRuntimeState,
  DIET_CALLBACK,
} = require("./diet-runtime.js");
const { DIET_STRINGS } = require("./i18n.js");

// The once-per-boot / once-per-day log latches are module state by design (that IS the fix for the
// per-tick log storm). Tests share a process, so each one starts from a clean latch.
test.beforeEach(() => resetDietRuntimeState());

const JST = 9;
const NOON_JST = Date.parse("2026-07-27T03:00:00Z"); // 12:00 JST
const SUPA = { supaUrl: "https://db.example", supaKey: "service" };
const USER = { uid: "u-diet", telegram_chat_id: "100", notifications_enabled: true };
const ROW = { uid: "u-diet", telegram_chat_id: "100" };

function response(status, body) {
  return { ok: status >= 200 && status < 300, status, json: async () => body, text: async () => JSON.stringify(body) };
}

// A tiny Supabase double: GETs answer from `rows`, POSTs land in `inserts` and 409 on a duplicate
// (uid, day, kind) exactly the way the unique index does in the database.
function supabase(rows = []) {
  const inserts = [];
  const store = [...rows];
  const fetchImpl = async (input, init = {}) => {
    const url = new URL(String(input));
    const method = String(init.method || "GET").toUpperCase();
    if (!url.pathname.endsWith("/lm_diet_log")) return response(200, []);
    if (method === "GET") {
      const kind = String(url.searchParams.get("kind") || "").replace(/^eq\./, "");
      // The reads are keyed on `day`, which is what the (uid, day DESC) index actually serves —
      // both an exact day (the answer lookup) and a trailing range (the weekly cap).
      const dayFilter = String(url.searchParams.get("day") || "");
      const dayEq = dayFilter.startsWith("eq.") ? dayFilter.slice(3) : "";
      const dayFrom = dayFilter.startsWith("gte.") ? dayFilter.slice(4) : "";
      return response(200, store.filter((r) =>
        (!kind || r.kind === kind) && (!dayEq || r.day === dayEq) && (!dayFrom || String(r.day) >= dayFrom)));
    }
    const body = JSON.parse(init.body || "{}");
    if (store.some((r) => r.uid === body.uid && r.day === body.day && r.kind === body.kind)) {
      return response(409, { code: "23505", message: "duplicate key" });
    }
    store.push(body);
    inserts.push(body);
    return response(201, {});
  };
  return { fetchImpl, inserts, store };
}

function telegram() {
  const sent = [];
  const edits = [];
  return {
    sent,
    edits,
    sendMessage: async (_token, chatId, text, extra) => {
      sent.push({ chatId: String(chatId), text, extra });
      return { ok: true, result: { message_id: 700 + sent.length } };
    },
    reflectAnswer: async (args) => { edits.push(args); return { ok: true }; },
  };
}

function deps(db, tg, overrides = {}) {
  return {
    ...SUPA,
    fetchImpl: db.fetchImpl,
    telegramToken: "tok",
    sendMessage: tg.sendMessage,
    tzOffsetH: JST,
    events: [],
    getLocationState: async () => "unknown",
    ...overrides,
  };
}

// ── the local day ─────────────────────────────────────────────────────────────────────────────────

test("the ledger day is the user's local day, not the UTC one", () => {
  // 2026-07-27 00:30 JST is still 2026-07-26 in UTC. Lunch is a local idea; the row must say so.
  assert.equal(localDay(Date.parse("2026-07-26T15:30:00Z"), JST), "2026-07-27");
  assert.equal(localDay(Date.parse("2026-07-26T15:30:00Z"), 0), "2026-07-26");
  assert.equal(localDay(NOON_JST, JST), "2026-07-27");
});

// ── whose clock? (the tz chain, and the silence at the end of it) ─────────────────────────────────

test("the chain is deps → the user row's own zone → env, and it reports which link answered", () => {
  const previous = process.env.LM_DIET_UTC_OFFSET_HOURS;
  delete process.env.LM_DIET_UTC_OFFSET_HOURS;
  try {
    assert.equal(resolveDietTzOffsetH({ tzOffsetH: -5 }, { call_time_zone: "Asia/Tokyo" }, NOON_JST), -5);
    assert.equal(resolveDietTzOffsetH({}, { call_time_zone: "Asia/Tokyo" }, NOON_JST), 9);
    assert.equal(resolveDietTzOffsetH({}, { call_time_zone: "America/New_York" }, NOON_JST), -4);
    assert.equal(resolveDietTzOffsetH({}, { call_time_zone: "Mars/Olympus" }, NOON_JST), null,
      "an unusable zone name is not silently 9");
    assert.equal(resolveDietTzOffsetH({}, {}, NOON_JST), null);
    process.env.LM_DIET_UTC_OFFSET_HOURS = "2";
    assert.equal(resolveDietTzOffsetH({}, {}, NOON_JST), 2);
  } finally {
    if (previous === undefined) delete process.env.LM_DIET_UTC_OFFSET_HOURS;
    else process.env.LM_DIET_UTC_OFFSET_HOURS = previous;
  }
});

test("a user whose timezone we cannot resolve is left ALONE — silence beats a question at 3am", async () => {
  const db = supabase();
  const tg = telegram();
  const logs = [];
  const blind = { ...deps(db, tg), tzOffsetH: undefined, log: (line) => logs.push(line) };
  const outcome = await dietUserOnce(USER, NOON_JST, blind);
  assert.equal(outcome.status, "skipped");
  assert.equal(outcome.reason, "no-timezone");
  assert.equal(db.inserts.length + tg.sent.length, 0, "no read, no claim, no message");
  // The 60s tick would otherwise print this line 1440 times a day, per user.
  await dietUserOnce(USER, NOON_JST + 60000, blind);
  await dietUserOnce(USER, NOON_JST + 120000, blind);
  assert.equal(logs.length, 1, `the missing-zone warning is once per boot, got ${JSON.stringify(logs)}`);
});

test("the window belongs to the USER's clock — a New York user is asked at New York noon", async () => {
  const nyUser = { ...USER, call_time_zone: "America/New_York" };
  const noonNewYork = Date.parse("2026-07-27T16:00:00Z"); // 12:00 EDT
  const asked = await dietUserOnce(nyUser, noonNewYork, { ...deps(supabase(), telegram()), tzOffsetH: undefined });
  assert.equal(asked.status, "asked");
  assert.equal(asked.day, "2026-07-27");
  const quiet = await dietUserOnce(nyUser, NOON_JST, { ...deps(supabase(), telegram()), tzOffsetH: undefined });
  assert.equal(quiet.reason, "outside-lunch-window", "JST noon is 23:00 in New York — nobody is asked then");
});

test("LM_DIET_UTC_OFFSET_HOURS is the last link before silence, not the first", async () => {
  const previous = process.env.LM_DIET_UTC_OFFSET_HOURS;
  process.env.LM_DIET_UTC_OFFSET_HOURS = "9";
  try {
    const outcome = await dietUserOnce(USER, NOON_JST, { ...deps(supabase(), telegram()), tzOffsetH: undefined });
    assert.equal(outcome.status, "asked");
  } finally {
    if (previous === undefined) delete process.env.LM_DIET_UTC_OFFSET_HOURS;
    else process.env.LM_DIET_UTC_OFFSET_HOURS = previous;
  }
});

// ── asking ────────────────────────────────────────────────────────────────────────────────────────

test("in the window with a clean history, the question is sent once and the ask is recorded", async () => {
  const db = supabase();
  const tg = telegram();
  const outcome = await dietUserOnce(USER, NOON_JST, deps(db, tg));
  assert.equal(outcome.status, "asked");
  assert.equal(tg.sent.length, 1);
  assert.equal(tg.sent[0].text, DIET_STRINGS.ja.lunchQuestion.text);
  assert.equal(tg.sent[0].extra.reply_markup.inline_keyboard.flat().length, 4);
  assert.equal(db.inserts.length, 1);
  assert.deepEqual(
    { uid: db.inserts[0].uid, day: db.inserts[0].day, kind: db.inserts[0].kind },
    { uid: "u-diet", day: "2026-07-27", kind: "ask" },
  );
  assert.equal(db.inserts[0].answer, undefined, "an ask row carries no answer");
});

test("every button carries the day it was asked, so a tap can never be filed against another day", async () => {
  const db = supabase();
  const tg = telegram();
  await dietUserOnce(USER, NOON_JST, deps(db, tg));
  assert.deepEqual(tg.sent[0].extra.reply_markup.inline_keyboard.flat().map((b) => b.callback_data), [
    "diet:answer:teishoku:2026-07-27", "diet:answer:men:2026-07-27",
    "diet:answer:fast:2026-07-27", "diet:answer:skip:2026-07-27",
  ]);
});

test("the day is CLAIMED before the message is sent", async () => {
  const db = supabase();
  const tg = telegram();
  const order = [];
  const watched = async (input, init) => {
    if (String(init && init.method).toUpperCase() === "POST") order.push("claim");
    return db.fetchImpl(input, init);
  };
  const watchedTg = { ...tg, sendMessage: async (...args) => { order.push("send"); return tg.sendMessage(...args); } };
  await dietUserOnce(USER, NOON_JST, deps({ fetchImpl: watched }, watchedTg));
  assert.deepEqual(order, ["claim", "send"], "a send that precedes the claim is a send that can repeat");
});

test("a later tick in the same window is stopped by the 48h spacing it reads back", async () => {
  const db = supabase();
  const tg = telegram();
  await dietUserOnce(USER, NOON_JST, deps(db, tg));
  const again = await dietUserOnce(USER, NOON_JST + 60000, deps(db, tg));
  assert.equal(again.status, "suppressed");
  assert.equal(again.reason, "too-soon-after-last");
  assert.equal(tg.sent.length, 1, "no second question");
});

test("two ticks that RACE — both reading an empty history — still send only one question", async () => {
  // The spacing check above is read-then-decide, so it cannot stop two ticks that read before
  // either wrote. The unique index can, and this is the only thing standing between the user and a
  // duplicate: the loser of the INSERT gets 409 and stops without sending.
  const db = supabase();
  const tg = telegram();
  const blindToOwnWrites = async (input, init = {}) => {
    if (String(init.method || "GET").toUpperCase() === "GET") return response(200, []);
    return db.fetchImpl(input, init);
  };
  const first = await dietUserOnce(USER, NOON_JST, deps({ fetchImpl: blindToOwnWrites }, tg));
  const second = await dietUserOnce(USER, NOON_JST + 1000, deps({ fetchImpl: blindToOwnWrites }, tg));
  assert.equal(first.status, "asked");
  assert.equal(second.status, "already_asked");
  assert.equal(tg.sent.length, 1, "the racing tick must not send");
  assert.equal(db.inserts.length, 1);
});

test("outside the window nothing is claimed and nothing is sent", async () => {
  const db = supabase();
  const tg = telegram();
  const outcome = await dietUserOnce(USER, Date.parse("2026-07-27T01:00:00Z"), deps(db, tg)); // 10:00 JST
  assert.equal(outcome.status, "suppressed");
  assert.equal(outcome.reason, "outside-lunch-window");
  assert.equal(db.inserts.length, 0);
  assert.equal(tg.sent.length, 0);
});

test("the weekly cap and the 48h spacing are read from the ledger, not from memory", async () => {
  const three = ["2026-07-21", "2026-07-23", "2026-07-25"].map((day) => ({
    uid: "u-diet", day, kind: "ask", asked_at: `${day}T03:00:00Z`, created_at: `${day}T03:00:00Z`,
  }));
  const capped = await dietUserOnce(USER, NOON_JST, deps(supabase(three), telegram()));
  assert.equal(capped.status, "suppressed");
  assert.equal(capped.reason, "weekly-cap-reached");

  const yesterday = [{
    uid: "u-diet", day: "2026-07-26", kind: "ask",
    asked_at: "2026-07-26T03:00:00Z", created_at: "2026-07-26T03:00:00Z",
  }];
  const tooSoon = await dietUserOnce(USER, NOON_JST, deps(supabase(yesterday), telegram()));
  assert.equal(tooSoon.reason, "too-soon-after-last");
});

test("readDietAskState counts only ask rows inside the trailing 7 days", async () => {
  const db = supabase([
    { uid: "u-diet", day: "2026-07-25", kind: "ask", asked_at: "2026-07-25T03:00:00Z", created_at: "2026-07-25T03:00:00Z" },
    { uid: "u-diet", day: "2026-07-25", kind: "answer", answer: "fast", created_at: "2026-07-25T04:00:00Z" },
    { uid: "u-diet", day: "2026-07-01", kind: "ask", asked_at: "2026-07-01T03:00:00Z", created_at: "2026-07-01T03:00:00Z" },
  ]);
  const state = await readDietAskState("u-diet", NOON_JST, SUPA, db.fetchImpl);
  assert.equal(state.askedThisWeek, 1, "the answer row and the 26-day-old ask are not asks-this-week");
  assert.equal(state.lastAskMs, Date.parse("2026-07-25T03:00:00Z"));
});

test("the lookup itself throws — an unreadable history is never handed back as 'never asked'", async () => {
  const fetchImpl = async () => response(500, { message: "boom" });
  await assert.rejects(() => readDietAskState("u-diet", NOON_JST, SUPA, fetchImpl), /diet ask state/i);
});

test("a transient read failure is logged ONCE per user per day, not once per 60s tick", async () => {
  const fetchImpl = async () => response(500, { message: "boom" });
  const tg = telegram();
  const logs = [];
  const flaky = { ...deps({ fetchImpl }, tg), log: (line) => logs.push(line) };
  for (let tick = 0; tick < 30; tick += 1) {
    const outcome = await dietUserOnce(USER, NOON_JST + tick * 60000, flaky);
    assert.equal(outcome.status, "suppressed");
    assert.equal(outcome.reason, "ledger-unreadable", "an outage must never look like a clean history");
  }
  assert.equal(logs.length, 1, `30 ticks inside one window must print one line, got ${logs.length}`);
  assert.equal(tg.sent.length, 0);
  // A new day is a new incident and says so.
  await dietUserOnce(USER, NOON_JST + 86400000, flaky);
  assert.equal(logs.length, 2);
});

test("the lunch window is checked BEFORE Supabase is touched at all", async () => {
  let reads = 0;
  const fetchImpl = async () => { reads += 1; return response(200, []); };
  const outcome = await dietUserOnce(USER, Date.parse("2026-07-27T01:00:00Z"), deps({ fetchImpl }, telegram()));
  assert.equal(outcome.reason, "outside-lunch-window");
  assert.equal(reads, 0, "23 of every 24 hours the organ must cost nothing at all");
});

test("mid-event and moving suppress the ask in production too, with no Supabase write", async () => {
  const db = supabase();
  const tg = telegram();
  const midEvent = await dietUserOnce(USER, NOON_JST, deps(db, tg, {
    events: [{ startMs: NOON_JST - 600000, endMs: NOON_JST + 600000 }],
  }));
  assert.equal(midEvent.reason, "mid-event");
  const moving = await dietUserOnce(USER, NOON_JST, deps(db, tg, { getLocationState: async () => "moving" }));
  assert.equal(moving.reason, "user-moving");
  assert.equal(db.inserts.length, 0);
  assert.equal(tg.sent.length, 0);
});

test("a user with notifications off, no chat, or no Supabase is skipped without any I/O", async () => {
  const db = supabase();
  const tg = telegram();
  for (const u of [{ ...USER, notifications_enabled: false }, { uid: "x" }, null]) {
    assert.equal((await dietUserOnce(u, NOON_JST, deps(db, tg))).status, "skipped");
  }
  assert.equal((await dietUserOnce(USER, NOON_JST, { ...deps(db, tg), supaUrl: "" })).status, "skipped");
  assert.equal(db.inserts.length + tg.sent.length, 0);
});

test("a Telegram failure is reported honestly, never as an ask that reached anyone", async () => {
  const db = supabase();
  const outcome = await dietUserOnce(USER, NOON_JST, deps(db, telegram(), {
    sendMessage: async () => ({ ok: false }),
  }));
  assert.equal(outcome.status, "send_failed");
});

// ── the tap ───────────────────────────────────────────────────────────────────────────────────────

function callbackOpts(db, tg, overrides = {}) {
  return {
    ...SUPA,
    row: ROW,
    chatId: "100",
    actorId: "100",
    token: "tok",
    messageId: "246",
    messageText: DIET_STRINGS.ja.lunchQuestion.text,
    fetchImpl: db.fetchImpl,
    nowMs: NOON_JST + 900000,
    tzOffsetH: JST,
    sendMessage: tg.sendMessage,
    reflectAnswer: tg.reflectAnswer,
    ...overrides,
  };
}

test("the callback pattern accepts exactly the four answers, each carrying its ask day", () => {
  for (const answer of ["teishoku", "men", "fast", "skip"]) {
    assert.ok(DIET_CALLBACK.test(`diet:answer:${answer}:2026-07-27`));
  }
  assert.ok(!DIET_CALLBACK.test("diet:answer:pizza:2026-07-27"));
  assert.ok(!DIET_CALLBACK.test("diet:answer:fast:extra"));
  assert.ok(!DIET_CALLBACK.test("diet:answer:fast"), "a dayless tap cannot be filed against a day");
});

test("the answer is filed under the day the QUESTION carried, not the day of the tap", async () => {
  const db = supabase();
  const tg = telegram();
  // Tapped at 00:20 JST on the 28th — nearly midnight, an hour after the question's own day ended.
  // The row still belongs to the 27th, because that is the lunch the user is answering about.
  const outcome = await handleDietCallback("diet:answer:fast:2026-07-27", callbackOpts(db, tg, {
    nowMs: Date.parse("2026-07-27T15:20:00Z"),
  }));
  assert.equal(outcome.ok, false, "a question from an earlier day has expired");
  assert.equal(outcome.reason, "expired");
  const sameDay = await handleDietCallback("diet:answer:fast:2026-07-27", callbackOpts(db, tg));
  assert.equal(sameDay.ok, true);
  assert.equal(db.inserts[0].day, "2026-07-27");
});

test("a stale-day tap is refused VISIBLY: the keyboard goes, the expiry is stated, no row is written", async () => {
  const db = supabase();
  const tg = telegram();
  const outcome = await handleDietCallback("diet:answer:fast:2026-07-20", callbackOpts(db, tg));
  assert.equal(outcome.ok, false);
  assert.equal(outcome.reason, "expired");
  assert.equal(db.inserts.length, 0, "a week-old question must never write today's lunch");
  assert.equal(tg.edits.length, 1, "the dead keyboard is stripped");
  assert.equal(tg.edits[0].label, "", "stripping a keyboard must not claim a choice");
  assert.equal(tg.sent.length, 1);
  assert.equal(tg.sent[0].text, DIET_STRINGS.ja.lunchQuestion.expired);
});

test("a tap persists the choice and answers VISIBLY by editing the question (CB-1 ①)", async () => {
  const db = supabase();
  const tg = telegram();
  const outcome = await handleDietCallback("diet:answer:fast:2026-07-27", callbackOpts(db, tg));
  assert.equal(outcome.ok, true);
  assert.equal(outcome.answer, "fast");
  assert.deepEqual(
    { uid: db.inserts[0].uid, day: db.inserts[0].day, kind: db.inserts[0].kind, answer: db.inserts[0].answer },
    { uid: "u-diet", day: "2026-07-27", kind: "answer", answer: "fast" },
  );
  assert.ok(db.inserts[0].answered_at, "the answer row records when it was answered");
  assert.equal(tg.edits.length, 1);
  assert.equal(tg.edits[0].messageId, "246");
  assert.equal(tg.edits[0].label, DIET_STRINGS.ja.lunchQuestion.fastButton);
  assert.equal(tg.edits[0].messageText, DIET_STRINGS.ja.lunchQuestion.text);
});

test("no thank-you is sent — the edit IS the response (§10.0-15 ①, no extra chatter)", async () => {
  const db = supabase();
  const tg = telegram();
  await handleDietCallback("diet:answer:teishoku:2026-07-27", callbackOpts(db, tg));
  assert.equal(tg.sent.length, 0, `a tap must not spawn a second message, got ${JSON.stringify(tg.sent)}`);
});

test("a second tap gets a visible 'already recorded' reply and never a duplicate row (§10.0-15 ③)", async () => {
  const db = supabase();
  const tg = telegram();
  await handleDietCallback("diet:answer:men:2026-07-27", callbackOpts(db, tg));
  const outcome = await handleDietCallback("diet:answer:fast:2026-07-27", callbackOpts(db, tg));
  assert.equal(outcome.ok, false);
  assert.equal(outcome.reason, "already_answered");
  assert.equal(db.inserts.length, 1, "the unique index is the guard; no second row");
  assert.equal(tg.sent.length, 1, "the second tap is answered visibly");
  assert.equal(tg.sent[0].text,
    DIET_STRINGS.ja.lunchQuestion.alreadyAnswered.replace("{choice}", DIET_STRINGS.ja.lunchQuestion.menButton),
    "the reply names what was ALREADY recorded, not what was just tapped");
});

test("cross-tenant taps are refused: a stranger's actor id writes nothing", async () => {
  const db = supabase();
  const tg = telegram();
  const outcome = await handleDietCallback("diet:answer:fast:2026-07-27", callbackOpts(db, tg, { actorId: "999" }));
  assert.equal(outcome.ok, false);
  assert.equal(outcome.reason, "scope_mismatch");
  assert.equal(db.inserts.length, 0);
  assert.equal(tg.edits.length, 0);
});

test("a row that does not name this chat is refused even when the actor matches", async () => {
  const db = supabase();
  const tg = telegram();
  const outcome = await handleDietCallback("diet:answer:fast:2026-07-27", callbackOpts(db, tg, {
    row: { uid: "someone-else", telegram_chat_id: "555" },
  }));
  assert.equal(outcome.ok, false);
  assert.equal(outcome.reason, "row_chat_mismatch");
  assert.equal(db.inserts.length, 0);
});

test("an unlinked chat (no row) is refused rather than writing an orphan row", async () => {
  const db = supabase();
  const outcome = await handleDietCallback("diet:answer:fast:2026-07-27", callbackOpts(db, telegram(), { row: null }));
  assert.equal(outcome.ok, false);
  assert.equal(outcome.reason, "unlinked");
  assert.equal(db.inserts.length, 0);
});

test("callbacks that are not ours are ignored, not guessed at", async () => {
  assert.deepEqual(await handleDietCallback("payout:answer:bank", callbackOpts(supabase(), telegram())), { ignored: true });
  assert.deepEqual(await handleDietCallback("diet:answer:sushi", callbackOpts(supabase(), telegram())), { ignored: true });
});

test("a persist failure is never dressed up as a recorded answer", async () => {
  const db = { fetchImpl: async () => response(500, { message: "down" }) };
  const tg = telegram();
  const outcome = await handleDietCallback("diet:answer:fast:2026-07-27", callbackOpts(db, tg));
  assert.equal(outcome.ok, false);
  assert.equal(outcome.reason, "persist_failed");
  assert.equal(tg.edits.length, 0, "nothing was recorded, so nothing is shown as recorded");
});
