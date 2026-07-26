"use strict";
// H4 ORG-precepts — the production leg: ask the question, record the tap.
//
// Four failure modes these tests exist to make impossible:
//   1. The 60s tick sees the bedtime window for 30 consecutive minutes. Without a durable claim the
//      user gets 30 identical questions. The claim is the INSERT, and it happens BEFORE the send.
//   2. A precepts question that does NOT spend one of MENTAL's three (H4 ⑤). Two organs each keeping
//      politely to three a day is six a day, and the user only has one evening.
//   3. A tap that writes to somebody else's row. This is the most private ledger the product holds.
//   4. An unreadable ledger read as an empty one, which is how a weekly question becomes a nightly
//      one during an incident.
// Run: node --test lib/precepts-runtime.test.js

const test = require("node:test");
const assert = require("node:assert/strict");
const {
  preceptsUserOnce, handlePreceptsCallback, readPreceptsAskState, resetPreceptsRuntimeState,
  PRECEPTS_CALLBACK, PRECEPTS_SEND_TRIGGER,
} = require("./precepts-runtime.js");
const { PRECEPTS_STRINGS } = require("./i18n.js");

test.beforeEach(() => resetPreceptsRuntimeState());

const JST = 9;
const NIGHT = Date.parse("2026-07-27T14:10:00Z");  // 23:10 JST, 20 min before a 23:30 bedtime
const SLEEP = Date.parse("2026-07-27T14:30:00Z");
const SUPA = { supaUrl: "https://db.example", supaKey: "service" };
const USER = { uid: "u-precepts", telegram_chat_id: "100", notifications_enabled: true };
const ROW = { uid: "u-precepts", telegram_chat_id: "100" };

function response(status, body) {
  return { ok: status >= 200 && status < 300, status, json: async () => body, text: async () => JSON.stringify(body) };
}

// A tiny Supabase double covering BOTH tables this organ touches: lm_precepts_log (GET by kind/day,
// POST that 409s on a duplicate (uid, day, kind) exactly the way the unique index does) and
// lm_mental_send_log (the shared budget).
function supabase(rows = [], mentalRows = []) {
  const inserts = [];
  const mentalInserts = [];
  const store = [...rows];
  const mental = [...mentalRows];
  const fetchImpl = async (input, init = {}) => {
    const url = new URL(String(input));
    const method = String(init.method || "GET").toUpperCase();
    if (url.pathname.endsWith("/lm_mental_send_log")) {
      if (method === "GET") {
        const since = String(url.searchParams.get("sent_at") || "").replace(/^gte\./, "");
        return response(200, mental.filter((r) => !since || r.sent_at >= since));
      }
      const body = JSON.parse(init.body || "{}");
      mental.push({ ...body, sent_at: new Date(NIGHT).toISOString() });
      mentalInserts.push(body);
      return response(201, {});
    }
    if (!url.pathname.endsWith("/lm_precepts_log")) return response(200, []);
    if (method === "GET") {
      const kind = String(url.searchParams.get("kind") || "").replace(/^eq\./, "");
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
  return { fetchImpl, inserts, mentalInserts, store, mental };
}

function telegram() {
  const sent = [];
  const edits = [];
  return {
    sent,
    edits,
    sendMessage: async (_token, chatId, text, extra) => {
      sent.push({ chatId: String(chatId), text, extra });
      return { ok: true, result: { message_id: 800 + sent.length } };
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
    sleepTargetMs: SLEEP,
    events: [],
    getLocationState: async () => "unknown",
    ...overrides,
  };
}

// ── whose clock, and the silence at the end of the chain ──────────────────────────────────────────

test("a user whose timezone we cannot resolve is left ALONE, and warned about once per boot", async () => {
  const db = supabase();
  const tg = telegram();
  const logs = [];
  const blind = { ...deps(db, tg), tzOffsetH: undefined, sleepTargetMs: undefined, log: (l) => logs.push(l) };
  const outcome = await preceptsUserOnce(USER, NIGHT, blind);
  assert.equal(outcome.status, "skipped");
  assert.equal(outcome.reason, "no-timezone");
  assert.equal(db.inserts.length + tg.sent.length, 0, "no read, no claim, no message");
  await preceptsUserOnce(USER, NIGHT + 60000, blind);
  await preceptsUserOnce(USER, NIGHT + 120000, blind);
  assert.equal(logs.length, 1, `once per boot, got ${JSON.stringify(logs)}`);
});

test("the bedtime window belongs to the USER's clock, resolved from their own row zone", async () => {
  const nyUser = { ...USER, call_time_zone: "America/New_York" };
  const bare = (nowMs) => preceptsUserOnce(nyUser, nowMs, {
    ...deps(supabase(), telegram()), tzOffsetH: undefined, sleepTargetMs: undefined,
  });
  // 23:10 EDT on 2026-07-27 is 03:10Z on the 28th; 23:10 JST is 14:10Z on the 27th.
  const asked = await bare(Date.parse("2026-07-28T03:10:00Z"));
  assert.equal(asked.status, "asked");
  assert.equal(asked.day, "2026-07-27");
  const quiet = await bare(NIGHT);
  assert.equal(quiet.reason, "outside-bedtime-window", "JST bedtime is 10:10 in New York");
});

// ── asking ────────────────────────────────────────────────────────────────────────────────────────

test("in the window with a clean history, the question is sent once and the ask is recorded", async () => {
  const db = supabase();
  const tg = telegram();
  const outcome = await preceptsUserOnce(USER, NIGHT, deps(db, tg));
  assert.equal(outcome.status, "asked");
  assert.equal(tg.sent.length, 1);
  assert.equal(tg.sent[0].text, PRECEPTS_STRINGS.ja.nightQuestion.text);
  assert.equal(tg.sent[0].extra.reply_markup.inline_keyboard.flat().length, 5);
  assert.deepEqual(
    { uid: db.inserts[0].uid, day: db.inserts[0].day, kind: db.inserts[0].kind },
    { uid: "u-precepts", day: "2026-07-27", kind: "ask" },
  );
  assert.equal(db.inserts[0].answer, undefined, "an ask row carries no answer");
});

test("every button carries the night it was asked, so a tap can never be filed against another", async () => {
  const db = supabase();
  const tg = telegram();
  await preceptsUserOnce(USER, NIGHT, deps(db, tg));
  assert.deepEqual(tg.sent[0].extra.reply_markup.inline_keyboard.flat().map((b) => b.callback_data), [
    "precepts:answer:lie:2026-07-27", "precepts:answer:harsh:2026-07-27",
    "precepts:answer:time:2026-07-27", "precepts:answer:impulse:2026-07-27",
    "precepts:answer:calm:2026-07-27",
  ]);
});

test("the night is CLAIMED before the message is sent", async () => {
  const db = supabase();
  const tg = telegram();
  const order = [];
  const watched = async (input, init) => {
    if (String(init && init.method).toUpperCase() === "POST" && String(input).includes("lm_precepts_log")) {
      order.push("claim");
    }
    return db.fetchImpl(input, init);
  };
  const watchedTg = { ...tg, sendMessage: async (...args) => { order.push("send"); return tg.sendMessage(...args); } };
  await preceptsUserOnce(USER, NIGHT, deps({ fetchImpl: watched }, watchedTg));
  assert.deepEqual(order, ["claim", "send"], "a send that precedes the claim is a send that can repeat");
});

test("two ticks that RACE — both reading an empty history — still send only one question", async () => {
  const db = supabase();
  const tg = telegram();
  const blindToOwnWrites = async (input, init = {}) => {
    if (String(init.method || "GET").toUpperCase() === "GET") return response(200, []);
    return db.fetchImpl(input, init);
  };
  const first = await preceptsUserOnce(USER, NIGHT, deps({ fetchImpl: blindToOwnWrites }, tg));
  const second = await preceptsUserOnce(USER, NIGHT + 1000, deps({ fetchImpl: blindToOwnWrites }, tg));
  assert.equal(first.status, "asked");
  assert.equal(second.status, "already_asked");
  assert.equal(tg.sent.length, 1, "the racing tick must not send");
});

test("a later tick in the same window is stopped by TWO bounds it reads back, and reports the tighter", async () => {
  const db = supabase();
  const tg = telegram();
  await preceptsUserOnce(USER, NIGHT, deps(db, tg));
  const again = await preceptsUserOnce(USER, NIGHT + 60000, deps(db, tg));
  assert.equal(again.status, "suppressed");
  // The question it just sent is now a MENTAL send, so the 2h spacing binds before the 7-day one —
  // the shared budget is doing real work here, not just being written to.
  assert.equal(again.reason, "too-soon-after-mental-send");
  assert.equal(tg.sent.length, 1, "no second question");

  // And with the MENTAL log clear (a lost budget row), the weekly spacing still stops it on its own.
  const forgetful = supabase(db.store);
  const later = await preceptsUserOnce(USER, NIGHT + 3 * 3600000, deps(forgetful, tg, {
    sleepTargetMs: SLEEP + 3 * 3600000,
  }));
  assert.equal(later.reason, "weekly-spacing");
});

test("outside the window nothing is claimed, nothing is sent, and Supabase is never touched", async () => {
  let reads = 0;
  const fetchImpl = async () => { reads += 1; return response(200, []); };
  const outcome = await preceptsUserOnce(USER, Date.parse("2026-07-27T10:00:00Z"), deps({ fetchImpl }, telegram()));
  assert.equal(outcome.status, "suppressed");
  assert.equal(outcome.reason, "outside-bedtime-window");
  assert.equal(reads, 0, "23½ of every 24 hours the organ must cost nothing at all");
});

test("last week's ask is read from the LEDGER, not from memory", async () => {
  const lastNight = [{
    uid: "u-precepts", day: "2026-07-26", kind: "ask",
    asked_at: "2026-07-26T14:10:00Z", created_at: "2026-07-26T14:10:00Z",
  }];
  const tooSoon = await preceptsUserOnce(USER, NIGHT, deps(supabase(lastNight), telegram()));
  assert.equal(tooSoon.reason, "weekly-spacing");

  const eightDaysAgo = [{
    uid: "u-precepts", day: "2026-07-19", kind: "ask",
    asked_at: "2026-07-19T14:10:00Z", created_at: "2026-07-19T14:10:00Z",
  }];
  const due = await preceptsUserOnce(USER, NIGHT, deps(supabase(eightDaysAgo), telegram()));
  assert.equal(due.status, "asked");
});

test("readPreceptsAskState counts only ask rows inside the trailing 7 days", async () => {
  const db = supabase([
    { uid: "u-precepts", day: "2026-07-25", kind: "ask", asked_at: "2026-07-25T14:10:00Z" },
    { uid: "u-precepts", day: "2026-07-25", kind: "answer", answer: "harsh", answered_at: "2026-07-25T14:12:00Z" },
    { uid: "u-precepts", day: "2026-07-01", kind: "ask", asked_at: "2026-07-01T14:10:00Z" },
  ]);
  const state = await readPreceptsAskState("u-precepts", NIGHT, SUPA, db.fetchImpl, JST);
  assert.equal(state.askedThisWeek, 1, "the answer row and the 26-day-old ask are not asks-this-week");
  assert.equal(state.lastAskMs, Date.parse("2026-07-25T14:10:00Z"));
});

test("the lookup itself throws — an unreadable history is never handed back as 'never asked'", async () => {
  const fetchImpl = async () => response(500, { message: "boom" });
  await assert.rejects(() => readPreceptsAskState("u", NIGHT, SUPA, fetchImpl, JST), /precepts ask state/i);
});

test("a transient read failure is logged ONCE per user per day, not once per 60s tick", async () => {
  const fetchImpl = async () => response(500, { message: "boom" });
  const tg = telegram();
  const logs = [];
  const flaky = { ...deps({ fetchImpl }, tg), log: (line) => logs.push(line) };
  for (let tick = 0; tick < 20; tick += 1) {
    const outcome = await preceptsUserOnce(USER, NIGHT + tick * 60000, {
      ...flaky, sleepTargetMs: SLEEP + tick * 60000,
    });
    assert.equal(outcome.reason, "ledger-unreadable", "an outage must never look like a clean history");
  }
  assert.equal(logs.length, 1, `20 ticks inside one window must print one line, got ${logs.length}`);
  assert.equal(tg.sent.length, 0);
  const nextDay = NIGHT + 86400000;
  await preceptsUserOnce(USER, nextDay, { ...flaky, sleepTargetMs: SLEEP + 86400000 });
  assert.equal(logs.length, 2, "a new day is a new incident and says so");
});

test("an unreadable MENTAL budget is a silence, never an assumed-empty budget", async () => {
  // The precepts leg reads lm_mental_send_log STRICTLY (unlike MENTAL itself): spending a cap it
  // cannot see is worse than saying nothing.
  const db = supabase();
  const partiallyBlind = async (input, init) => {
    if (String(input).includes("lm_mental_send_log")) return response(500, { message: "down" });
    return db.fetchImpl(input, init);
  };
  const tg = telegram();
  const outcome = await preceptsUserOnce(USER, NIGHT, deps({ fetchImpl: partiallyBlind }, tg));
  assert.equal(outcome.reason, "ledger-unreadable");
  assert.equal(db.inserts.length + tg.sent.length, 0);
});

// ── the shared MENTAL budget (H4 ⑤) ───────────────────────────────────────────────────────────────

test("a day with 3 MENTAL sends gets NO precepts question — the cap is shared, not doubled", async () => {
  const threeSends = [
    { uid: "u-precepts", trigger: "pre_event", sent_at: "2026-07-27T09:00:00Z" },
    { uid: "u-precepts", trigger: "between_events", sent_at: "2026-07-27T11:00:00Z" },
    { uid: "u-precepts", trigger: "pre_sleep", sent_at: "2026-07-27T11:30:00Z" },
  ];
  const db = supabase([], threeSends);
  const tg = telegram();
  const outcome = await preceptsUserOnce(USER, NIGHT, deps(db, tg));
  assert.equal(outcome.status, "suppressed");
  assert.equal(outcome.reason, "mental-daily-cap-reached");
  assert.equal(db.inserts.length + tg.sent.length, 0, "no claim, no question");
});

test("a MENTAL send inside the last 2 hours suppresses the question", async () => {
  const recent = [{ uid: "u-precepts", trigger: "pre_sleep", sent_at: new Date(NIGHT - 3600000).toISOString() }];
  const outcome = await preceptsUserOnce(USER, NIGHT, deps(supabase([], recent), telegram()));
  assert.equal(outcome.reason, "too-soon-after-mental-send");

  const old = [{ uid: "u-precepts", trigger: "pre_sleep", sent_at: new Date(NIGHT - 3 * 3600000).toISOString() }];
  assert.equal((await preceptsUserOnce(USER, NIGHT, deps(supabase([], old), telegram()))).status, "asked");
});

test("a delivered question SPENDS one of MENTAL's three, recorded under its own trigger", async () => {
  const db = supabase();
  const tg = telegram();
  const outcome = await preceptsUserOnce(USER, NIGHT, deps(db, tg));
  assert.equal(outcome.status, "asked");
  assert.equal(outcome.budgeted, true);
  assert.equal(db.mentalInserts.length, 1);
  assert.equal(db.mentalInserts[0].uid, "u-precepts");
  assert.equal(db.mentalInserts[0].trigger, PRECEPTS_SEND_TRIGGER);
  assert.equal(db.mentalInserts[0].trigger, "precepts",
    "the ledger says what was actually sent — recording a question as 'pre_sleep' would be a lie");
  assert.equal(String(db.mentalInserts[0].telegram_message_id), String(outcome.telegramMessageId));
});

test("a question that never reached anyone does NOT spend the budget", async () => {
  const db = supabase();
  const outcome = await preceptsUserOnce(USER, NIGHT, deps(db, telegram(), {
    sendMessage: async () => ({ ok: false }),
  }));
  assert.equal(outcome.status, "send_failed");
  assert.equal(db.mentalInserts.length, 0, "a row for an undelivered message would suppress a real one later");
});

// ── the ordinary refusals ─────────────────────────────────────────────────────────────────────────

test("mid-event and moving suppress the ask in production too, with no Supabase write", async () => {
  const db = supabase();
  const tg = telegram();
  const midEvent = await preceptsUserOnce(USER, NIGHT, deps(db, tg, {
    events: [{ startMs: NIGHT - 600000, endMs: NIGHT + 600000 }],
  }));
  assert.equal(midEvent.reason, "mid-event");
  const moving = await preceptsUserOnce(USER, NIGHT, deps(db, tg, { getLocationState: async () => "moving" }));
  assert.equal(moving.reason, "user-moving");
  assert.equal(db.inserts.length + tg.sent.length, 0);
});

test("a user with notifications off, no chat, or no Supabase is skipped without any I/O", async () => {
  const db = supabase();
  const tg = telegram();
  for (const u of [{ ...USER, notifications_enabled: false }, { uid: "x" }, null]) {
    assert.equal((await preceptsUserOnce(u, NIGHT, deps(db, tg))).status, "skipped");
  }
  assert.equal((await preceptsUserOnce(USER, NIGHT, { ...deps(db, tg), supaUrl: "" })).status, "skipped");
  assert.equal(db.inserts.length + tg.sent.length, 0);
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
    messageText: PRECEPTS_STRINGS.ja.nightQuestion.text,
    fetchImpl: db.fetchImpl,
    nowMs: NIGHT + 600000,
    tzOffsetH: JST,
    sendMessage: tg.sendMessage,
    reflectAnswer: tg.reflectAnswer,
    ...overrides,
  };
}

test("the callback pattern accepts exactly the five answers, each carrying its ask day", () => {
  for (const answer of ["lie", "harsh", "time", "impulse", "calm"]) {
    assert.ok(PRECEPTS_CALLBACK.test(`precepts:answer:${answer}:2026-07-27`));
  }
  assert.ok(!PRECEPTS_CALLBACK.test("precepts:answer:anger:2026-07-27"));
  assert.ok(!PRECEPTS_CALLBACK.test("precepts:answer:harsh:extra"));
  assert.ok(!PRECEPTS_CALLBACK.test("precepts:answer:harsh"), "a dayless tap cannot be filed against a night");
});

test("a tap persists the choice and answers VISIBLY by editing the question (CB-1 ①)", async () => {
  const db = supabase();
  const tg = telegram();
  const outcome = await handlePreceptsCallback("precepts:answer:harsh:2026-07-27", callbackOpts(db, tg));
  assert.equal(outcome.ok, true);
  assert.deepEqual(
    { uid: db.inserts[0].uid, day: db.inserts[0].day, kind: db.inserts[0].kind, answer: db.inserts[0].answer },
    { uid: "u-precepts", day: "2026-07-27", kind: "answer", answer: "harsh" },
  );
  assert.ok(db.inserts[0].answered_at);
  assert.equal(tg.edits.length, 1);
  assert.equal(tg.edits[0].label, PRECEPTS_STRINGS.ja.nightQuestion.harshButton);
  assert.equal(tg.edits[0].messageText, PRECEPTS_STRINGS.ja.nightQuestion.text);
});

test("no thank-you is sent — the edit IS the response (§10.0-15 ①)", async () => {
  const db = supabase();
  const tg = telegram();
  await handlePreceptsCallback("precepts:answer:calm:2026-07-27", callbackOpts(db, tg));
  assert.equal(tg.sent.length, 0, `a tap must not spawn a second message, got ${JSON.stringify(tg.sent)}`);
});

test("the answer is filed under the day the QUESTION carried; a stale night is refused VISIBLY", async () => {
  const db = supabase();
  const tg = telegram();
  const outcome = await handlePreceptsCallback("precepts:answer:harsh:2026-07-20", callbackOpts(db, tg));
  assert.equal(outcome.ok, false);
  assert.equal(outcome.reason, "expired");
  assert.equal(db.inserts.length, 0, "a week-old question must never write tonight's row");
  assert.equal(tg.edits.length, 1, "the dead keyboard is stripped");
  assert.equal(tg.edits[0].label, "", "stripping a keyboard must not claim a choice");
  assert.equal(tg.sent[0].text, PRECEPTS_STRINGS.ja.nightQuestion.expired);
});

test("a tap after local midnight still belongs to the evening it was asked about", async () => {
  const db = supabase();
  const tg = telegram();
  // 00:20 JST on the 28th: the question's own day has ended, so the tap expires rather than being
  // silently re-filed as the 28th — a night nobody was asked about.
  const outcome = await handlePreceptsCallback("precepts:answer:harsh:2026-07-27", callbackOpts(db, tg, {
    nowMs: Date.parse("2026-07-27T15:20:00Z"),
  }));
  assert.equal(outcome.reason, "expired");
  assert.equal(db.inserts.length, 0);
});

test("a second tap gets a visible 'already recorded' reply naming what is ON FILE", async () => {
  const db = supabase();
  const tg = telegram();
  await handlePreceptsCallback("precepts:answer:time:2026-07-27", callbackOpts(db, tg));
  const outcome = await handlePreceptsCallback("precepts:answer:calm:2026-07-27", callbackOpts(db, tg));
  assert.equal(outcome.reason, "already_answered");
  assert.equal(db.inserts.length, 1, "the unique index is the guard; no second row");
  assert.equal(tg.sent.length, 1);
  assert.equal(tg.sent[0].text,
    PRECEPTS_STRINGS.ja.nightQuestion.alreadyAnswered.replace("{choice}", PRECEPTS_STRINGS.ja.nightQuestion.timeButton),
    "the reply names what was ALREADY recorded, not what was just tapped");
});

test("cross-tenant taps are refused: a stranger's actor id writes nothing", async () => {
  const db = supabase();
  const tg = telegram();
  const outcome = await handlePreceptsCallback("precepts:answer:harsh:2026-07-27", callbackOpts(db, tg, { actorId: "999" }));
  assert.equal(outcome.reason, "scope_mismatch");
  assert.equal(db.inserts.length + tg.edits.length, 0);
});

test("a row that does not name this chat is refused even when the actor matches", async () => {
  const db = supabase();
  const outcome = await handlePreceptsCallback("precepts:answer:harsh:2026-07-27", callbackOpts(db, telegram(), {
    row: { uid: "someone-else", telegram_chat_id: "555" },
  }));
  assert.equal(outcome.reason, "row_chat_mismatch");
  assert.equal(db.inserts.length, 0);
});

test("an unlinked chat is refused rather than writing an orphan row", async () => {
  const db = supabase();
  const outcome = await handlePreceptsCallback("precepts:answer:harsh:2026-07-27", callbackOpts(db, telegram(), { row: null }));
  assert.equal(outcome.reason, "unlinked");
  assert.equal(db.inserts.length, 0);
});

test("callbacks that are not ours are ignored, not guessed at", async () => {
  assert.deepEqual(await handlePreceptsCallback("diet:answer:fast:2026-07-27", callbackOpts(supabase(), telegram())), { ignored: true });
  assert.deepEqual(await handlePreceptsCallback("precepts:answer:anger:2026-07-27", callbackOpts(supabase(), telegram())), { ignored: true });
});

test("a persist failure is never dressed up as a recorded answer", async () => {
  const db = { fetchImpl: async () => response(500, { message: "down" }) };
  const tg = telegram();
  const outcome = await handlePreceptsCallback("precepts:answer:harsh:2026-07-27", callbackOpts(db, tg));
  assert.equal(outcome.reason, "persist_failed");
  assert.equal(tg.edits.length, 0, "nothing was recorded, so nothing is shown as recorded");
});

test("the tap does NOT spend the MENTAL budget — only messages WE send do", async () => {
  const db = supabase();
  await handlePreceptsCallback("precepts:answer:harsh:2026-07-27", callbackOpts(db, telegram()));
  assert.equal(db.mentalInserts.length, 0, "the user's own tap is not an unsolicited message");
});
