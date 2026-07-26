"use strict";
// H4 ORG-precepts — the weekly mirror (spec §10 NEXT HORIZON row H4 ③).
//
// This is the leg that can do real harm, so the tests are about what it must NOT do as much as what
// it does: never on a Tuesday, never twice in a week, never on one data point, never outside the
// user's own budget, and never claiming a context the calendar does not actually show.
// Run: node --test lib/precepts-mirror.test.js

const test = require("node:test");
const assert = require("node:assert/strict");
const {
  MIRROR_MIN_ANSWERS, MIRROR_WINDOW_DAYS, MIRROR_COOLDOWN_DAYS, MIRROR_SEND_TRIGGER, BUSY_MIN_EVENTS, BUSY_TAIL_MS,
  countAnswers, detectPreceptsPattern, evaluatePreceptsMirror, buildMirrorMessage,
  resetPreceptsMirrorState, preceptsMirrorOnce,
} = require("./precepts-mirror.js");
const { preceptsUserOnce, resetPreceptsRuntimeState } = require("./precepts-runtime.js");
const { PRECEPTS_STRINGS } = require("./i18n.js");

test.beforeEach(() => { resetPreceptsMirrorState(); resetPreceptsRuntimeState(); });

const JST = 9;
// 2026-07-26 is a SUNDAY. 23:10 JST on it is 14:10Z; the 23:30 bedtime target is 14:30Z.
const SUNDAY_NIGHT = Date.parse("2026-07-26T14:10:00Z");
const SUNDAY_SLEEP = Date.parse("2026-07-26T14:30:00Z");
const MONDAY_NIGHT = Date.parse("2026-07-27T14:10:00Z");
const MONDAY_SLEEP = Date.parse("2026-07-27T14:30:00Z");
const SUPA = { supaUrl: "https://db.example", supaKey: "service" };
const USER = { uid: "u-precepts", telegram_chat_id: "100", notifications_enabled: true };

// Two Thursdays inside the four-week evidence window: 2026-07-23 and 2026-07-16.
const THU_23 = Date.parse("2026-07-23T14:10:00Z"); // 23:10 JST Thursday
const TUE_21 = Date.parse("2026-07-21T14:10:00Z"); // 23:10 JST Tuesday

// A row as readPreceptsAnswers hands it over: the CARRIED day (the evening the question was about)
// plus the instant the tap actually happened. The two are resolved with the SAME offset in
// production, so the fixture takes one too rather than hard-coding JST into a New York week.
function answer(answerValue, atMs, offsetH = JST) {
  return { answer: answerValue, atMs, day: new Date(atMs + offsetH * 3600000).toISOString().slice(0, 10) };
}

// ── the pattern rule ──────────────────────────────────────────────────────────────────────────────

test("one occurrence is never a pattern, and a calm stretch is never a pattern at all", () => {
  assert.deepEqual(detectPreceptsPattern({ answers: [answer("harsh", THU_23)], tzOffsetH: JST }), { kind: "none" });
  assert.deepEqual(detectPreceptsPattern({
    answers: [answer("calm", THU_23), answer("calm", THU_23 - 7 * 86400000)], tzOffsetH: JST,
  }), { kind: "none" }, "「なし・穏やかだった」 is counted, but 'you were calm on Thursdays' is not a context");
});

test("two of the same answer on the same weekday is a weekday pattern", () => {
  const pattern = detectPreceptsPattern({
    answers: [answer("harsh", THU_23), answer("harsh", THU_23 - 7 * 86400000)], tzOffsetH: JST,
  });
  assert.deepEqual(pattern, { kind: "weekday", answer: "harsh", count: 2, weekday: 4 });
});

test("the weekday is the USER's — a New York week is not a Tokyo week", () => {
  // 2026-07-24T02:00Z is Friday 11:00 JST and Thursday 22:00 EDT.
  const instants = [Date.parse("2026-07-24T02:00:00Z"), Date.parse("2026-07-17T02:00:00Z")];
  const tokyo = detectPreceptsPattern({ answers: instants.map((ms) => answer("harsh", ms, JST)), tzOffsetH: JST });
  const newYork = detectPreceptsPattern({ answers: instants.map((ms) => answer("harsh", ms, -4)), tzOffsetH: -4 });
  assert.equal(tokyo.weekday, 5, "Friday in Tokyo");
  assert.equal(newYork.weekday, 4, "Thursday in New York");
});

test("the weekday comes from the CARRIED day, so a 00:20 tap is not reported as the next weekday", () => {
  // The bedtime question ships ≤30 min before sleep, so answers routinely land after local midnight.
  // The row is keyed to the evening it describes; reading the weekday off answered_at instead would
  // tell a user their Thursdays were hard when what the calendar shows is Fridays.
  const thursdayNights = ["2026-07-23", "2026-07-16"];
  const answers = thursdayNights.map((day) => ({
    answer: "harsh",
    // 00:20 JST the NEXT morning: a Friday instant carrying a Thursday night.
    atMs: Date.parse(`${day}T15:20:00Z`),
    day,
  }));
  const pattern = detectPreceptsPattern({ answers, tzOffsetH: JST });
  assert.equal(pattern.weekday, 4, `Thursday, the night described — got ${pattern.weekday}`);
  // And a sample with no carried day still falls back to the instant, unchanged.
  assert.equal(detectPreceptsPattern({
    answers: thursdayNights.map((day) => ({ answer: "harsh", atMs: Date.parse(`${day}T15:20:00Z`) })),
    tzOffsetH: JST,
  }).weekday, 5, "with nothing carried, the instant is all there is");
});

test("two answers on different weekdays, with no busy days, is no pattern — facts only", () => {
  assert.deepEqual(detectPreceptsPattern({
    answers: [answer("harsh", THU_23), answer("harsh", TUE_21)], tzOffsetH: JST,
  }), { kind: "none" });
});

test("a day with three or more events, ending within the tail, makes an answer 'busy'", () => {
  assert.equal(BUSY_MIN_EVENTS, 3);
  const busyDay = (nightMs) => {
    const dayStart = nightMs - 10 * 3600000; // ~13:10 JST
    return [0, 1, 2].map((i) => ({
      startMs: dayStart + i * 3600000, endMs: dayStart + i * 3600000 + 3600000,
    }));
  };
  const answers = [answer("harsh", THU_23), answer("harsh", TUE_21)];
  const events = [...busyDay(THU_23), ...busyDay(TUE_21)];
  assert.deepEqual(detectPreceptsPattern({ answers, events, tzOffsetH: JST }),
    { kind: "busy", answer: "harsh", count: 2, weekday: null });
});

test("two events is not a block, and a block that finished before the tail does not count", () => {
  const nearlyBusy = [0, 1].map((i) => ({ startMs: THU_23 - 10 * 3600000 + i * 3600000, endMs: THU_23 - 9 * 3600000 + i * 3600000 }));
  assert.equal(detectPreceptsPattern({
    answers: [answer("harsh", THU_23), answer("harsh", TUE_21)], events: nearlyBusy, tzOffsetH: JST,
  }).kind, "none", "two events is not the three the sentence claims");

  // Three events, but they all ended before dawn of the same local day — well outside the tail.
  const earlyBlock = [0, 1, 2].map((i) => ({
    startMs: THU_23 - 21 * 3600000 + i * 1800000, endMs: THU_23 - 20 * 3600000 + i * 1800000,
  }));
  assert.equal(detectPreceptsPattern({
    answers: [answer("harsh", THU_23), answer("harsh", TUE_21)], events: earlyBlock, tzOffsetH: JST,
  }).kind, "none", "a busy morning is not the context of a 23:10 tap");
  assert.equal(BUSY_TAIL_MS, 8 * 3600000);
});

test("the same weekday AND a busy block on every one of those days is the combined pattern", () => {
  const busyDay = (nightMs) => [0, 1, 2].map((i) => ({
    startMs: nightMs - 10 * 3600000 + i * 3600000, endMs: nightMs - 9 * 3600000 + i * 3600000,
  }));
  const thursdays = [THU_23, THU_23 - 7 * 86400000];
  assert.deepEqual(detectPreceptsPattern({
    answers: thursdays.map((ms) => answer("harsh", ms)),
    events: thursdays.flatMap(busyDay),
    tzOffsetH: JST,
  }), { kind: "weekday_busy", answer: "harsh", count: 2, weekday: 4 });
});

test("the subject is the single most frequent non-calm answer, ties broken deterministically", () => {
  // One 'lie' and two 'harsh' → harsh is the subject; the lone lie cannot dilute it.
  const pattern = detectPreceptsPattern({
    answers: [answer("lie", TUE_21), answer("harsh", THU_23), answer("harsh", THU_23 - 7 * 86400000)],
    tzOffsetH: JST,
  });
  assert.equal(pattern.answer, "harsh");
  // A 1-1 tie has no subject with two occurrences, so there is no pattern to name.
  assert.equal(detectPreceptsPattern({
    answers: [answer("lie", TUE_21), answer("harsh", THU_23)], tzOffsetH: JST,
  }).kind, "none");
});

test("the same evidence always produces the same pattern — the rule is deterministic", () => {
  const answers = [answer("harsh", THU_23), answer("harsh", THU_23 - 7 * 86400000), answer("lie", TUE_21)];
  assert.deepEqual(
    detectPreceptsPattern({ answers, tzOffsetH: JST }),
    detectPreceptsPattern({ answers: [...answers].reverse(), tzOffsetH: JST }),
  );
});

// ── the message ───────────────────────────────────────────────────────────────────────────────────

test("counts are counts of taps the user made, in the fixed order, zeros omitted", () => {
  assert.deepEqual(countAnswers([answer("harsh", THU_23), answer("calm", TUE_21), answer("harsh", TUE_21)]), [
    { answer: "harsh", count: 2 }, { answer: "calm", count: 1 },
  ]);
});

test("no pattern → facts and nothing else", () => {
  const text = buildMirrorMessage({ counts: [{ answer: "harsh", count: 2 }], pattern: { kind: "none" } });
  assert.equal(text, "🌙 最近4週間の記録です。「きつく当たった」が2回。");
});

test("a pattern is stated as a fact, and the combined one is the spec's own sentence", () => {
  const counts = [{ answer: "harsh", count: 2 }];
  assert.equal(
    buildMirrorMessage({ counts, pattern: { kind: "weekday", answer: "harsh", count: 2, weekday: 4 } }),
    "🌙 最近4週間の記録です。「きつく当たった」が2回。2回とも木曜でした。",
  );
  assert.equal(
    buildMirrorMessage({ counts, pattern: { kind: "weekday_busy", answer: "harsh", count: 2, weekday: 4 } }),
    "🌙 最近4週間の記録です。「きつく当たった」が2回。2回とも予定が3件以上あった木曜の後でした。",
  );
  assert.equal(
    buildMirrorMessage({ counts, pattern: { kind: "busy", answer: "harsh", count: 2, weekday: null } }),
    "🌙 最近4週間の記録です。「きつく当たった」が2回。2回とも予定が3件以上あった日の後でした。",
  );
});

test("several answer kinds are joined, calm included — the week, not a highlight reel", () => {
  const text = buildMirrorMessage({
    counts: [{ answer: "harsh", count: 2 }, { answer: "calm", count: 3 }], pattern: { kind: "none" },
  });
  assert.equal(text, "🌙 最近4週間の記録です。「きつく当たった」が2回、「なし・穏やかだった」が3回。");
});

test("a label containing a replace-magic sequence is not re-expanded", () => {
  // Labels come from the Dais-editable copy; `$&` in a template's SUBSTITUTION is a live footgun.
  const text = buildMirrorMessage({ counts: [{ answer: "harsh", count: "$&" }], pattern: { kind: "none" } });
  assert.ok(text.includes("$&"), text);
  assert.ok(!text.includes("{count}"), text);
});

// ── the pure gate ─────────────────────────────────────────────────────────────────────────────────

function mirrorInput(overrides = {}) {
  return {
    nowMs: SUNDAY_NIGHT,
    tzOffsetH: JST,
    sleepTargetMs: SUNDAY_SLEEP,
    sentTodayCount: 0,
    lastMentalSentMs: null,
    answers: [answer("harsh", THU_23), answer("calm", TUE_21)],
    lastMirrorDay: null,
    events: [],
    location: { state: "unknown" },
    ...overrides,
  };
}

test("on a Sunday night in the window, with two answers, the mirror is due", () => {
  const verdict = evaluatePreceptsMirror(mirrorInput());
  assert.equal(verdict.decision, "send");
  assert.equal(verdict.answerCount, 2);
});

test("never on any other night of the week", () => {
  assert.equal(evaluatePreceptsMirror(mirrorInput({
    nowMs: MONDAY_NIGHT, sleepTargetMs: MONDAY_SLEEP,
  })).reason, "not-sunday");
});

test("Sunday is detected in the USER's week, not in UTC", () => {
  // Monday 11:00 JST is Sunday 22:00 in New York; only one of the two users is mirrored.
  const instant = Date.parse("2026-07-27T02:00:00Z");
  assert.equal(evaluatePreceptsMirror(mirrorInput({
    nowMs: instant, tzOffsetH: JST, sleepTargetMs: instant + 600000,
  })).reason, "not-sunday");
  assert.equal(evaluatePreceptsMirror(mirrorInput({
    nowMs: instant, tzOffsetH: -4, sleepTargetMs: instant + 600000,
  })).decision, "send");
});

test("one answer is a spotlight, not a mirror", () => {
  assert.equal(MIRROR_MIN_ANSWERS, 2);
  const verdict = evaluatePreceptsMirror(mirrorInput({ answers: [answer("harsh", THU_23)] }));
  assert.equal(verdict.reason, "not-enough-answers");
  assert.equal(verdict.answerCount, 1);
});

test("the evidence window is four weeks, and answers older than it do not count", () => {
  // The spec row's own example (2 occurrences, all on the same weekday) is impossible inside seven
  // days when the question is asked weekly — see the module header. The window that makes the
  // message producible is the one the copy names, and nothing outside it counts.
  assert.equal(MIRROR_WINDOW_DAYS, 28);
  const stale = [answer("harsh", SUNDAY_NIGHT - 29 * 86400000), answer("calm", SUNDAY_NIGHT - 30 * 86400000)];
  assert.equal(evaluatePreceptsMirror(mirrorInput({ answers: stale })).reason, "not-enough-answers");
  const inWindow = [answer("harsh", SUNDAY_NIGHT - 27 * 86400000), answer("calm", SUNDAY_NIGHT - 20 * 86400000)];
  assert.equal(evaluatePreceptsMirror(mirrorInput({ answers: inWindow })).decision, "send");
  // And the copy states the window it actually counted over — 「今週は」 over 28 days is a small lie.
  for (const template of Object.values(PRECEPTS_STRINGS.ja.weeklyMirror)) {
    assert.ok(!String(template).includes("今週"), template);
  }
});

test("the weekly cadence and the same-day guard both come from the last mirror row", () => {
  assert.equal(MIRROR_COOLDOWN_DAYS, 7);
  assert.equal(evaluatePreceptsMirror(mirrorInput({ lastMirrorDay: "2026-07-26" })).reason, "already-mirrored-today");
  assert.equal(evaluatePreceptsMirror(mirrorInput({ lastMirrorDay: "2026-07-22" })).reason, "mirror-cooldown");
  assert.equal(evaluatePreceptsMirror(mirrorInput({ lastMirrorDay: "2026-07-19" })).decision, "send");
});

test("the mirror lives inside MENTAL's budget too (H4 ⑤)", () => {
  assert.equal(evaluatePreceptsMirror(mirrorInput({ sentTodayCount: 3 })).reason, "mental-daily-cap-reached");
  assert.equal(evaluatePreceptsMirror(mirrorInput({
    lastMentalSentMs: SUNDAY_NIGHT - 60 * 60000,
  })).reason, "too-soon-after-mental-send");
});

test("outside the bedtime window, mid-event, and moving all suppress", () => {
  assert.equal(evaluatePreceptsMirror(mirrorInput({ nowMs: SUNDAY_SLEEP - 31 * 60000 })).reason, "outside-bedtime-window");
  assert.equal(evaluatePreceptsMirror(mirrorInput({ nowMs: SUNDAY_SLEEP + 1 })).reason, "outside-bedtime-window");
  assert.equal(evaluatePreceptsMirror(mirrorInput({
    events: [{ startMs: SUNDAY_NIGHT - 600000, endMs: SUNDAY_NIGHT + 600000 }],
  })).reason, "mid-event");
  assert.equal(evaluatePreceptsMirror(mirrorInput({ location: { state: "moving" } })).reason, "user-moving");
});

test("the schema is closed and malformed input is refused rather than coerced", () => {
  assert.throws(() => evaluatePreceptsMirror({ ...mirrorInput(), surprise: 1 }), /unknown key/);
  assert.throws(() => evaluatePreceptsMirror(mirrorInput({ answers: [{ answer: "rage", atMs: 1 }] })), /unknown precepts answer/);
  assert.throws(() => evaluatePreceptsMirror(mirrorInput({ lastMirrorDay: "sunday" })), /lastMirrorDay/);
});

// ── the production leg ────────────────────────────────────────────────────────────────────────────

function response(status, body) {
  return { ok: status >= 200 && status < 300, status, json: async () => body, text: async () => JSON.stringify(body) };
}

function supabase(rows = [], mentalRows = []) {
  const inserts = [];
  const mentalInserts = [];
  const store = [...rows];
  const mental = [...mentalRows];
  const fetchImpl = async (input, init = {}) => {
    const url = new URL(String(input));
    const method = String(init.method || "GET").toUpperCase();
    if (url.pathname.endsWith("/lm_mental_send_log")) {
      if (method === "GET") return response(200, mental);
      const body = JSON.parse(init.body || "{}");
      mentalInserts.push(body);
      return response(201, {});
    }
    if (!url.pathname.endsWith("/lm_precepts_log")) return response(200, []);
    if (method === "GET") {
      const kind = String(url.searchParams.get("kind") || "").replace(/^eq\./, "");
      const dayFilter = String(url.searchParams.get("day") || "");
      const dayFrom = dayFilter.startsWith("gte.") ? dayFilter.slice(4) : "";
      return response(200, store.filter((r) => (!kind || r.kind === kind) && (!dayFrom || String(r.day) >= dayFrom)));
    }
    const body = JSON.parse(init.body || "{}");
    if (store.some((r) => r.uid === body.uid && r.day === body.day && r.kind === body.kind)) {
      return response(409, { code: "23505", message: "duplicate key" });
    }
    store.push(body);
    inserts.push(body);
    return response(201, {});
  };
  return { fetchImpl, inserts, mentalInserts, store };
}

function telegram() {
  const sent = [];
  return {
    sent,
    sendMessage: async (_token, chatId, text) => {
      sent.push({ chatId: String(chatId), text });
      return { ok: true, result: { message_id: 900 + sent.length } };
    },
  };
}

const ANSWER_ROWS = [
  { uid: "u-precepts", day: "2026-07-23", kind: "answer", answer: "harsh", answered_at: new Date(THU_23).toISOString() },
  { uid: "u-precepts", day: "2026-07-21", kind: "answer", answer: "calm", answered_at: new Date(TUE_21).toISOString() },
];

function mirrorDeps(db, tg, overrides = {}) {
  return {
    ...SUPA,
    fetchImpl: db.fetchImpl,
    telegramToken: "tok",
    sendMessage: tg.sendMessage,
    tzOffsetH: JST,
    sleepTargetMs: SUNDAY_SLEEP,
    events: [],
    getLocationState: async () => "unknown",
    fetchHistory: async () => [],
    ...overrides,
  };
}

test("a Sunday night with two answers sends ONE message and records a mirror row", async () => {
  const db = supabase(ANSWER_ROWS);
  const tg = telegram();
  const outcome = await preceptsMirrorOnce(USER, SUNDAY_NIGHT, mirrorDeps(db, tg));
  assert.equal(outcome.status, "mirrored");
  assert.equal(outcome.pattern, "none");
  assert.equal(tg.sent.length, 1);
  assert.equal(tg.sent[0].text, "🌙 最近4週間の記録です。「きつく当たった」が1回、「なし・穏やかだった」が1回。");
  const row = db.inserts.find((r) => r.kind === "mirror");
  assert.deepEqual({ uid: row.uid, day: row.day, kind: row.kind, pattern: row.pattern },
    { uid: "u-precepts", day: "2026-07-26", kind: "mirror", pattern: null });
});

test("the mirror spends one of MENTAL's three, under its own trigger token", async () => {
  const db = supabase(ANSWER_ROWS);
  const outcome = await preceptsMirrorOnce(USER, SUNDAY_NIGHT, mirrorDeps(db, telegram()));
  assert.equal(outcome.budgeted, true);
  assert.equal(db.mentalInserts.length, 1);
  assert.equal(db.mentalInserts[0].trigger, MIRROR_SEND_TRIGGER);
  assert.equal(db.mentalInserts[0].trigger, "precepts_mirror");
});

test("a mirror whose budget row is LOST says so, and stands the whole organ down for the day", async () => {
  const db = supabase(ANSWER_ROWS);
  const tg = telegram();
  const outcome = await preceptsMirrorOnce(USER, SUNDAY_NIGHT, mirrorDeps(db, tg, {
    recordMentalSend: async () => false,
  }));
  assert.equal(outcome.status, "mirrored");
  assert.equal(outcome.budgeted, false, "the outcome must not imply a cap row that never landed");

  // Fail closed ACROSS the legs: the question and the mirror spend the same three, so a cap that
  // stopped counting must stop BOTH. (The mirror's own claim would have stopped the mirror anyway;
  // the question is the leg that would otherwise keep spending an unaudited budget.)
  let reads = 0;
  const counted = { fetchImpl: async (...args) => { reads += 1; return db.fetchImpl(...args); } };
  const question = await preceptsUserOnce(USER, SUNDAY_NIGHT + 60000, {
    ...SUPA,
    fetchImpl: counted.fetchImpl,
    telegramToken: "tok",
    sendMessage: tg.sendMessage,
    tzOffsetH: JST,
    sleepTargetMs: SUNDAY_SLEEP + 60000,
    events: [],
    getLocationState: async () => "unknown",
  });
  assert.equal(question.reason, "budget-unrecorded");
  assert.equal(reads, 0, "a stood-down organ must not even read");
});

test("the day is CLAIMED before the message is sent, so 30 ticks cannot mean 30 mirrors", async () => {
  const db = supabase(ANSWER_ROWS);
  const tg = telegram();
  await preceptsMirrorOnce(USER, SUNDAY_NIGHT, mirrorDeps(db, tg));
  const again = await preceptsMirrorOnce(USER, SUNDAY_NIGHT + 60000, mirrorDeps(supabase(db.store), tg, {
    sleepTargetMs: SUNDAY_SLEEP + 60000,
  }));
  assert.equal(again.reason, "already-mirrored-today");
  assert.equal(tg.sent.length, 1);
});

test("the calendar history is pulled ONCE per user per day, not once per tick", async () => {
  const db = supabase(ANSWER_ROWS);
  let pulls = 0;
  const failingClaim = {
    fetchImpl: async (input, init = {}) => {
      if (String(init.method || "GET").toUpperCase() === "POST" && String(input).includes("lm_precepts_log")) {
        return response(409, { code: "23505", message: "duplicate key" });
      }
      return db.fetchImpl(input, init);
    },
  };
  for (let tick = 0; tick < 10; tick += 1) {
    await preceptsMirrorOnce(USER, SUNDAY_NIGHT + tick * 60000, mirrorDeps(failingClaim, telegram(), {
      sleepTargetMs: SUNDAY_SLEEP + tick * 60000,
      fetchHistory: async () => { pulls += 1; return []; },
    }));
  }
  assert.equal(pulls, 1, `an 8-day calendar read per tick is 10 reads for one message, got ${pulls}`);
});

test("the busy tail measures the REAL end when the calendar has one, and says so when it does not", async () => {
  // A long block: starts 10h before the tap, ends 2h before it. Measured, it is inside the 8h tail.
  // The start+1h assumption would put its end 9h before the tap and silently rule the day out — so
  // this pair is the difference between reading the calendar and guessing at it.
  const thursdays = [THU_23, THU_23 - 7 * 86400000];
  const rows = thursdays.map((ms) => ({
    uid: "u-precepts", day: new Date(ms + JST * 3600000).toISOString().slice(0, 10),
    kind: "answer", answer: "harsh", answered_at: new Date(ms).toISOString(),
  }));
  const longBlocks = thursdays.flatMap((ms) => [
    { startMs: ms - 12 * 3600000, endMs: ms - 11 * 3600000 },
    { startMs: ms - 11 * 3600000, endMs: ms - 10 * 3600000 },
    { startMs: ms - 10 * 3600000, endMs: ms - 2 * 3600000 },
  ]);
  const measured = await preceptsMirrorOnce(USER, SUNDAY_NIGHT, mirrorDeps(supabase(rows), telegram(), {
    fetchHistory: async () => longBlocks,
  }));
  assert.equal(measured.pattern, "weekday_busy", "the measured end is inside the tail");

  // The SAME calendar with the ends missing (all-day rows, or a provider that gave none) falls back
  // to start+1h — a documented assumption, and one that refuses the pattern rather than inventing it.
  resetPreceptsMirrorState();
  const assumed = await preceptsMirrorOnce(USER, SUNDAY_NIGHT, mirrorDeps(supabase(rows), telegram(), {
    fetchHistory: async () => longBlocks.map(({ startMs }) => ({ startMs, endMs: null })),
  }));
  assert.equal(assumed.pattern, "weekday", "with no measured end we name the weekday and claim no context");
});

test("a calendar we cannot read costs the CONTEXT, never the message", async () => {
  const db = supabase(ANSWER_ROWS);
  const tg = telegram();
  const outcome = await preceptsMirrorOnce(USER, SUNDAY_NIGHT, mirrorDeps(db, tg, {
    fetchHistory: async () => { throw new Error("composio down"); },
  }));
  assert.equal(outcome.status, "mirrored");
  assert.equal(outcome.pattern, "none", "we do not claim a context we could not check");
  assert.equal(tg.sent.length, 1);
});

test("a real weekday+busy week produces the spec's sentence and stores the SHAPE, not the calendar", async () => {
  const thursdays = [THU_23, THU_23 - 7 * 86400000];
  const rows = thursdays.map((ms) => ({
    uid: "u-precepts", day: new Date(ms + JST * 3600000).toISOString().slice(0, 10),
    kind: "answer", answer: "harsh", answered_at: new Date(ms).toISOString(),
  }));
  const db = supabase(rows);
  const tg = telegram();
  const events = thursdays.flatMap((ms) => [0, 1, 2].map((i) => ({
    startMs: ms - 10 * 3600000 + i * 3600000, endMs: ms - 9 * 3600000 + i * 3600000, summary: "定例MTG",
  })));
  const outcome = await preceptsMirrorOnce(USER, SUNDAY_NIGHT, mirrorDeps(db, tg, {
    fetchHistory: async () => events,
  }));
  assert.equal(outcome.pattern, "weekday_busy");
  assert.equal(tg.sent[0].text, "🌙 最近4週間の記録です。「きつく当たった」が2回。2回とも予定が3件以上あった木曜の後でした。");
  const row = db.inserts.find((r) => r.kind === "mirror");
  assert.deepEqual(row.pattern, { kind: "weekday_busy", answer: "harsh", count: 2, weekday: 4 });
  assert.ok(!JSON.stringify(row).includes("定例MTG"), "no event content may reach the ledger");
});

test("six nights a week the mirror costs nothing — Supabase is never touched", async () => {
  let reads = 0;
  const fetchImpl = async () => { reads += 1; return response(200, []); };
  const outcome = await preceptsMirrorOnce(USER, MONDAY_NIGHT, mirrorDeps({ fetchImpl }, telegram(), {
    sleepTargetMs: MONDAY_SLEEP,
  }));
  assert.equal(outcome.reason, "not-sunday");
  assert.equal(reads, 0);
});

test("an unreadable ledger is a silence, not an assumed week", async () => {
  const fetchImpl = async () => response(500, { message: "down" });
  const tg = telegram();
  const outcome = await preceptsMirrorOnce(USER, SUNDAY_NIGHT, mirrorDeps({ fetchImpl }, tg));
  assert.equal(outcome.reason, "ledger-unreadable");
  assert.equal(tg.sent.length, 0);
});

test("a notifications-off user, an unresolvable zone, and a missing chat all yield silence", async () => {
  const db = supabase(ANSWER_ROWS);
  const tg = telegram();
  assert.equal((await preceptsMirrorOnce({ ...USER, notifications_enabled: false }, SUNDAY_NIGHT, mirrorDeps(db, tg))).status, "skipped");
  assert.equal((await preceptsMirrorOnce({ uid: "x" }, SUNDAY_NIGHT, mirrorDeps(db, tg))).status, "skipped");
  const blind = await preceptsMirrorOnce(USER, SUNDAY_NIGHT, {
    ...mirrorDeps(db, tg), tzOffsetH: undefined, sleepTargetMs: undefined,
  });
  assert.equal(blind.reason, "no-timezone");
  assert.equal(tg.sent.length + db.inserts.length, 0);
});

test("a Telegram failure is reported honestly and never spends the budget", async () => {
  const db = supabase(ANSWER_ROWS);
  const outcome = await preceptsMirrorOnce(USER, SUNDAY_NIGHT, mirrorDeps(db, telegram(), {
    sendMessage: async () => ({ ok: false }),
  }));
  assert.equal(outcome.status, "send_failed");
  assert.equal(db.mentalInserts.length, 0);
});

test("the mirror never scores, never preaches and never asks anything", () => {
  const patterns = [
    { kind: "none" },
    { kind: "weekday", answer: "harsh", count: 2, weekday: 4 },
    { kind: "busy", answer: "lie", count: 2, weekday: null },
    { kind: "weekday_busy", answer: "time", count: 3, weekday: 1 },
  ];
  for (const pattern of patterns) {
    const text = buildMirrorMessage({
      counts: [{ answer: "harsh", count: 2 }, { answer: "calm", count: 1 }], pattern,
    });
    assert.ok(!/[?？]/.test(text), text);
    for (const word of ["戒", "罪", "業", "点数", "評価", "スコア", "しましょう", "べき", "おすすめ"]) {
      assert.ok(!text.includes(word), `「${word}」 in: ${text}`);
    }
    assert.ok(text.startsWith("🌙"), text);
    assert.equal((text.match(/\p{Extended_Pictographic}/gu) || []).length, 1, text);
  }
  // The copy the messages are built from is the same Dais-editable table the tests read.
  assert.ok(PRECEPTS_STRINGS.ja.weeklyMirror.facts.includes("{counts}"));
});
