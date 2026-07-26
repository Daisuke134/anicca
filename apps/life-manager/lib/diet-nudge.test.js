"use strict";
// H2 ORG-diet — the intervention. This is the leg that can do real damage: an unsolicited message
// about what someone eats is a sermon unless it is (a) rare, (b) evidence-backed, and (c) carrying a
// concrete option instead of an opinion. The thresholds below ARE the product decision — 4 real
// samples, a 50% fast share, one message a day, in the 30 minutes before lunch is decided.
// Run: node --test lib/diet-nudge.test.js

const test = require("node:test");
const assert = require("node:assert/strict");
const {
  evaluateDietNudge,
  findLunchAlternative,
  dietNudgeOnce,
  buildNudgeMessage,
  DIET_NUDGE_MIN_SAMPLES,
  DIET_NUDGE_FAST_SHARE,
  DIET_NUDGE_WINDOW_DAYS,
  NUDGE_WINDOW_START_MIN,
  NUDGE_WINDOW_END_MIN,
  DIET_LUNCH_KEYWORDS,
} = require("./diet-nudge.js");
const { DIET_STRINGS } = require("./i18n.js");

const JST = 9;
const NOW = Date.parse("2026-07-27T02:30:00Z"); // 11:30 JST — inside the pre-lunch window
const DAY = 86400000;
const SUPA = { supaUrl: "https://db.example", supaKey: "service" };
const USER = { uid: "u-diet", telegram_chat_id: "100", notifications_enabled: true, home_address: "東京都新宿区" };

function answers(list, startMs = NOW - DAY) {
  return list.map((answer, index) => ({ answer, atMs: startMs - index * DAY }));
}

function input(overrides = {}) {
  return { nowMs: NOW, tzOffsetH: JST, answers: [], nudgedToday: false, ...overrides };
}

function response(status, body) {
  return { ok: status >= 200 && status < 300, status, json: async () => body, text: async () => JSON.stringify(body) };
}

// ── the thresholds ────────────────────────────────────────────────────────────────────────────────

test("the published thresholds are the ones the code uses", () => {
  assert.equal(DIET_NUDGE_MIN_SAMPLES, 4);
  assert.equal(DIET_NUDGE_FAST_SHARE, 0.5);
  assert.equal(DIET_NUDGE_WINDOW_DAYS, 14);
});

test("three samples is never enough, even at 100% fast", () => {
  const verdict = evaluateDietNudge(input({ answers: answers(["fast", "fast", "fast"]) }));
  assert.equal(verdict.decision, "suppress");
  assert.equal(verdict.reason, "not-enough-samples");
  assert.equal(verdict.sampleCount, 3);
});

test("four samples at exactly 50% fast crosses the line", () => {
  const verdict = evaluateDietNudge(input({ answers: answers(["fast", "fast", "men", "teishoku"]) }));
  assert.equal(verdict.decision, "send");
  assert.equal(verdict.sampleCount, 4);
  assert.equal(verdict.fastCount, 2);
  assert.equal(verdict.fastShare, 0.5);
});

test("four samples just under 50% stays silent", () => {
  const verdict = evaluateDietNudge(input({ answers: answers(["fast", "fast", "men", "teishoku", "teishoku"]) }));
  assert.equal(verdict.decision, "suppress");
  assert.equal(verdict.reason, "fast-share-below-threshold");
  assert.equal(verdict.fastShare, 0.4);
});

test("「食べてない」 counts as a real sample and is not fast food — skipping lunch dilutes the share", () => {
  // Deliberate: a day with no lunch is an observation we made, and it is honestly not fast food.
  // Counting it in the denominator makes the nudge HARDER to fire, which is the safe direction.
  const verdict = evaluateDietNudge(input({ answers: answers(["fast", "fast", "skip", "skip"]) }));
  assert.equal(verdict.sampleCount, 4);
  assert.equal(verdict.fastShare, 0.5);
  assert.equal(verdict.decision, "send");
});

test("answers older than 14 days are not evidence about now", () => {
  const stale = [
    { answer: "fast", atMs: NOW - 20 * DAY },
    { answer: "fast", atMs: NOW - 18 * DAY },
    { answer: "fast", atMs: NOW - 16 * DAY },
    { answer: "fast", atMs: NOW - 15 * DAY },
  ];
  const verdict = evaluateDietNudge(input({ answers: stale }));
  assert.equal(verdict.sampleCount, 0);
  assert.equal(verdict.reason, "not-enough-samples");
});

test("an answer exactly 14 days old is still inside the window", () => {
  const edge = ["fast", "fast", "men", "teishoku"].map((answer, i) => ({
    answer, atMs: NOW - (14 * DAY) + i,
  }));
  assert.equal(evaluateDietNudge(input({ answers: edge })).sampleCount, 4);
});

// ── the moment ────────────────────────────────────────────────────────────────────────────────────

test("the nudge window is 11:15-11:45 local — before lunch is decided, not after", () => {
  assert.equal(NUDGE_WINDOW_START_MIN, 11 * 60 + 15);
  assert.equal(NUDGE_WINDOW_END_MIN, 11 * 60 + 45);
  const firing = answers(["fast", "fast", "men", "teishoku"]);
  const at = (hhmm) => {
    const [h, m] = hhmm.split(":").map(Number);
    return Date.parse("2026-07-27T00:00:00Z") + (h - JST) * 3600000 + m * 60000;
  };
  assert.equal(evaluateDietNudge(input({ nowMs: at("11:15"), answers: firing })).decision, "send");
  assert.equal(evaluateDietNudge(input({ nowMs: at("11:45"), answers: firing })).decision, "send");
  assert.equal(evaluateDietNudge(input({ nowMs: at("11:14"), answers: firing })).reason, "outside-nudge-window");
  assert.equal(evaluateDietNudge(input({ nowMs: at("11:46"), answers: firing })).reason, "outside-nudge-window");
  // The window belongs to the user's clock, like the question's.
  assert.equal(evaluateDietNudge(input({ nowMs: at("11:30"), tzOffsetH: 0, answers: firing })).reason, "outside-nudge-window");
});

test("one nudge per day, maximum", () => {
  const verdict = evaluateDietNudge(input({
    answers: answers(["fast", "fast", "men", "teishoku"]), nudgedToday: true,
  }));
  assert.equal(verdict.decision, "suppress");
  assert.equal(verdict.reason, "already-nudged-today");
});

test("the daily cap is checked before the evidence, so a spent day reports the cap", () => {
  assert.equal(evaluateDietNudge(input({ answers: [], nudgedToday: true })).reason, "already-nudged-today");
});

test("bad input throws instead of silently deciding to send", () => {
  assert.throws(() => evaluateDietNudge(null), /input must be an object/);
  assert.throws(() => evaluateDietNudge(input({ answers: "lots" })), /answers must be an array/);
  assert.throws(() => evaluateDietNudge(input({ tzOffsetH: null })), /tzOffsetH/);
  assert.throws(() => evaluateDietNudge(input({ answers: [{ answer: "pizza", atMs: NOW }] })), /unknown diet answer/);
});

// ── the copy: fact + one option, never a verdict ──────────────────────────────────────────────────

test("the message states the count and names one place — no adjective about the food", () => {
  const text = buildNudgeMessage({ sampleCount: 6, fastCount: 4, venue: { name: "まいどおおきに食堂", address: "渋谷区道玄坂1-2-3" } });
  assert.ok(text.includes("6"));
  assert.ok(text.includes("4"));
  assert.ok(text.includes("まいどおおきに食堂"));
  assert.ok(text.includes("渋谷区道玄坂1-2-3"));
  assert.equal(text, DIET_STRINGS.ja.lunchNudge.withVenue
    .replace("{sampleCount}", "6").replace("{fastCount}", "4")
    .replace("{venueName}", "まいどおおきに食堂").replace("{venueAddress}", "渋谷区道玄坂1-2-3"));
});

test("with no venue found the message says so, rather than inventing one or staying quiet about it", () => {
  const text = buildNudgeMessage({ sampleCount: 5, fastCount: 3, venue: null });
  assert.equal(text, DIET_STRINGS.ja.lunchNudge.withoutVenue
    .replace("{sampleCount}", "5").replace("{fastCount}", "3"));
  assert.ok(!/\{/.test(text), "no unfilled placeholders may reach the user");
});

test("neither copy moralises, diagnoses, or asks for a reply (§9.11 + H2 ⑥)", () => {
  for (const text of Object.values(DIET_STRINGS.ja.lunchNudge)) {
    assert.doesNotMatch(text, /健康|カロリー|栄養|太|痩|ダイエット|controlled|体に悪|やめ|控え|改善|そろそろ.*見直/);
    assert.doesNotMatch(text, /[?？]/, "a nudge is one-directional — it never asks a question");
    assert.doesNotMatch(text, /返信|教えて|reply/);
    // §9.11: at most one emoji, at the head.
    const emoji = [...text].filter((c) => /\p{Extended_Pictographic}/u.test(c));
    assert.ok(emoji.length <= 1, `at most one emoji, got ${emoji.join("")}`);
    if (emoji.length === 1) assert.ok(text.startsWith(emoji[0]), "the emoji belongs at the head");
  }
});

// ── the venue lookup (Places, near the WORK anchor) ───────────────────────────────────────────────

test("the lookup searches the diet keywords around the work anchor and returns one real place", async () => {
  const queries = [];
  const fetchImpl = async (input) => {
    const url = new URL(String(input));
    const query = url.searchParams.get("query");
    queries.push({ query, location: url.searchParams.get("location") });
    if (query === "渋谷オフィス") {
      return response(200, { status: "OK", results: [{ geometry: { location: { lat: 35.658, lng: 139.701 } } }] });
    }
    return response(200, { status: "OK", results: [
      { place_id: "p1", name: "大戸屋 渋谷店", formatted_address: "渋谷区道玄坂1-2-3" },
    ] });
  };
  const venue = await findLunchAlternative({
    anchors: { home: "東京都新宿区", work: "渋谷オフィス", usualProviders: [] },
    apiKey: "k", fetchImpl,
  });
  assert.deepEqual(venue, { name: "大戸屋 渋谷店", address: "渋谷区道玄坂1-2-3" });
  assert.ok(queries.some((q) => DIET_LUNCH_KEYWORDS.includes(q.query)), `a diet keyword must be searched, got ${JSON.stringify(queries)}`);
  assert.ok(queries.filter((q) => q.location).every((q) => q.location === "35.658,139.701"),
    "the search is biased to the work anchor, not the user's home");
});

test("the keywords are the 定食/サラダ family the spec names", () => {
  assert.ok(DIET_LUNCH_KEYWORDS.includes("定食"));
  assert.ok(DIET_LUNCH_KEYWORDS.includes("サラダ"));
});

test("with no work anchor it falls back to home rather than searching the whole country", async () => {
  const locations = [];
  const fetchImpl = async (input) => {
    const url = new URL(String(input));
    if (url.searchParams.get("location")) locations.push(url.searchParams.get("location"));
    if (url.searchParams.get("query") === "東京都新宿区") {
      return response(200, { status: "OK", results: [{ geometry: { location: { lat: 35.69, lng: 139.7 } } }] });
    }
    return response(200, { status: "OK", results: [{ place_id: "p", name: "定食屋", formatted_address: "新宿区1-1" }] });
  };
  const venue = await findLunchAlternative({ anchors: { home: "東京都新宿区", work: null, usualProviders: [] }, apiKey: "k", fetchImpl });
  assert.equal(venue.name, "定食屋");
  assert.ok(locations.every((l) => l === "35.69,139.7"));
});

test("no anchor at all, no API key, or an empty Places result all yield null — never a guess", async () => {
  const empty = async () => response(200, { status: "ZERO_RESULTS", results: [] });
  assert.equal(await findLunchAlternative({ anchors: { home: null, work: null, usualProviders: [] }, apiKey: "k", fetchImpl: empty }), null);
  assert.equal(await findLunchAlternative({ anchors: { home: "東京", work: null, usualProviders: [] }, apiKey: "", fetchImpl: empty }), null);
  assert.equal(await findLunchAlternative({ anchors: { home: "東京", work: null, usualProviders: [] }, apiKey: "k", fetchImpl: empty }), null);
});

test("a Places transport failure yields null rather than throwing into the scheduler", async () => {
  const boom = async () => { throw new Error("network"); };
  assert.equal(await findLunchAlternative({ anchors: { home: "東京", work: null, usualProviders: [] }, apiKey: "k", fetchImpl: boom }), null);
});

// ── the production leg ────────────────────────────────────────────────────────────────────────────

function supabase(rows = []) {
  const inserts = [];
  const store = [...rows];
  const fetchImpl = async (input, init = {}) => {
    const url = new URL(String(input));
    const method = String(init.method || "GET").toUpperCase();
    if (!url.pathname.endsWith("/lm_diet_log")) return response(200, []);
    if (method === "GET") {
      const kind = String(url.searchParams.get("kind") || "").replace(/^eq\./, "");
      const day = String(url.searchParams.get("day") || "").replace(/^eq\./, "");
      return response(200, store.filter((r) => (!kind || r.kind === kind) && (!day || r.day === day)));
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

const FIRING_ROWS = ["fast", "fast", "men", "teishoku"].map((answer, i) => ({
  uid: "u-diet", kind: "answer", answer,
  day: new Date(NOW - (i + 1) * DAY).toISOString().slice(0, 10),
  answered_at: new Date(NOW - (i + 1) * DAY).toISOString(),
  created_at: new Date(NOW - (i + 1) * DAY).toISOString(),
}));

function nudgeDeps(db, sent, overrides = {}) {
  return {
    ...SUPA,
    fetchImpl: db.fetchImpl,
    telegramToken: "tok",
    sendMessage: async (_t, chatId, text) => { sent.push({ chatId: String(chatId), text }); return { ok: true, result: { message_id: 9 } }; },
    tzOffsetH: JST,
    calendarEvents: [],
    mapsKey: "k",
    findLunchAlternative: async () => ({ name: "大戸屋 渋谷店", address: "渋谷区道玄坂1-2-3" }),
    ...overrides,
  };
}

test("a firing history sends exactly one nudge and records it as a kind:nudge row", async () => {
  const db = supabase(FIRING_ROWS);
  const sent = [];
  const outcome = await dietNudgeOnce(USER, NOW, nudgeDeps(db, sent));
  assert.equal(outcome.status, "nudged");
  assert.equal(sent.length, 1);
  assert.ok(sent[0].text.includes("大戸屋 渋谷店"));
  const nudgeRow = db.inserts.find((r) => r.kind === "nudge");
  assert.ok(nudgeRow, `a nudge row must be written, got ${JSON.stringify(db.inserts)}`);
  assert.equal(nudgeRow.day, "2026-07-27");
  assert.equal(nudgeRow.answer, undefined, "a nudge row carries no answer");
  // The ledger is append-only, so the venue has to go in at insert time or never: a nudge row that
  // cannot say which shop it named is not an auditable record of what we told the user.
  assert.deepEqual(nudgeRow.venue, { name: "大戸屋 渋谷店", address: "渋谷区道玄坂1-2-3" });
});

test("the honest no-venue nudge records a null venue rather than omitting the fact", async () => {
  const db = supabase(FIRING_ROWS);
  await dietNudgeOnce(USER, NOW, nudgeDeps(db, [], { findLunchAlternative: async () => null }));
  assert.equal(db.inserts.find((r) => r.kind === "nudge").venue, null);
});

test("the nudge day is CLAIMED before the send — 30 ticks in the window send one message", async () => {
  const db = supabase(FIRING_ROWS);
  const sent = [];
  await dietNudgeOnce(USER, NOW, nudgeDeps(db, sent));
  const again = await dietNudgeOnce(USER, NOW + 60000, nudgeDeps(db, sent));
  assert.equal(again.status, "suppressed");
  assert.equal(again.reason, "already-nudged-today");
  assert.equal(sent.length, 1);
});

test("Places finding nothing still sends the honest message, minus the venue", async () => {
  const db = supabase(FIRING_ROWS);
  const sent = [];
  const outcome = await dietNudgeOnce(USER, NOW, nudgeDeps(db, sent, { findLunchAlternative: async () => null }));
  assert.equal(outcome.status, "nudged");
  assert.equal(sent[0].text, DIET_STRINGS.ja.lunchNudge.withoutVenue
    .replace("{sampleCount}", "4").replace("{fastCount}", "2"));
});

test("a Places crash does not lose the nudge — it degrades to the honest no-venue message", async () => {
  const db = supabase(FIRING_ROWS);
  const sent = [];
  const outcome = await dietNudgeOnce(USER, NOW, nudgeDeps(db, sent, {
    findLunchAlternative: async () => { throw new Error("places 500"); },
  }));
  assert.equal(outcome.status, "nudged");
  assert.equal(sent[0].text, DIET_STRINGS.ja.lunchNudge.withoutVenue
    .replace("{sampleCount}", "4").replace("{fastCount}", "2"));
});

test("a quiet history spends no Places call and sends nothing", async () => {
  const db = supabase(FIRING_ROWS.slice(0, 3));
  const sent = [];
  let placesCalls = 0;
  const outcome = await dietNudgeOnce(USER, NOW, nudgeDeps(db, sent, {
    findLunchAlternative: async () => { placesCalls += 1; return null; },
  }));
  assert.equal(outcome.reason, "not-enough-samples");
  assert.equal(placesCalls, 0, "the Places spend happens only for a nudge we are actually sending");
  assert.equal(sent.length, 0);
  assert.equal(db.inserts.length, 0);
});

test("notifications off, no chat, or no Supabase: skipped with no I/O", async () => {
  const db = supabase(FIRING_ROWS);
  const sent = [];
  for (const u of [{ ...USER, notifications_enabled: false }, { uid: "x" }, null]) {
    assert.equal((await dietNudgeOnce(u, NOW, nudgeDeps(db, sent))).status, "skipped");
  }
  assert.equal(sent.length, 0);
  assert.equal(db.inserts.length, 0);
});

test("a Telegram failure is reported as a failure, not as a delivered nudge", async () => {
  const db = supabase(FIRING_ROWS);
  const outcome = await dietNudgeOnce(USER, NOW, nudgeDeps(db, [], { sendMessage: async () => ({ ok: false }) }));
  assert.equal(outcome.status, "send_failed");
});
