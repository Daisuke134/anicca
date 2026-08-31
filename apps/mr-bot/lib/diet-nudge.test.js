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
  DIET_NUDGE_COOLDOWN_DAYS,
  DIET_LUNCH_KEYWORDS,
  resetDietNudgeState,
} = require("./diet-nudge.js");
const { DIET_STRINGS } = require("./i18n.js");

// The per-day venue memo is module state on purpose — it is what bounds the Places spend on a day
// whose claim keeps failing. Tests share a process, so each one starts from an empty memo.
test.beforeEach(() => resetDietNudgeState());

const JST = 9;
const NOW = Date.parse("2026-07-27T02:30:00Z"); // 11:30 JST — inside the pre-lunch window
const DAY = 86400000;
const SUPA = { supaUrl: "https://db.example", supaKey: "service" };
const USER = { uid: "u-diet", telegram_chat_id: "100", notifications_enabled: true, home_address: "東京都新宿区" };
const TODAY = "2026-07-27";

function localDayOf(ms) {
  return new Date(ms + JST * 3600000).toISOString().slice(0, 10);
}

function answers(list, startMs = NOW - DAY) {
  return list.map((answer, index) => ({ answer, atMs: startMs - index * DAY }));
}

function input(overrides = {}) {
  return { nowMs: NOW, tzOffsetH: JST, answers: [], lastNudgeDay: null, ...overrides };
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
    answers: answers(["fast", "fast", "men", "teishoku"]), lastNudgeDay: TODAY,
  }));
  assert.equal(verdict.decision, "suppress");
  assert.equal(verdict.reason, "already-nudged-today");
});

test("the daily cap is checked before the evidence, so a spent day reports the cap", () => {
  assert.equal(evaluateDietNudge(input({ answers: [], lastNudgeDay: TODAY })).reason, "already-nudged-today");
});

// ── the cadence: a WEEK between nudges, not a day ─────────────────────────────────────────────────

test("after a nudge the organ is quiet for a week — three sermons a week is still a sermon", () => {
  assert.equal(DIET_NUDGE_COOLDOWN_DAYS, 7);
  const firing = answers(["fast", "fast", "men", "teishoku"]);
  // The evidence still fires; only the calendar stops it.
  const day6 = evaluateDietNudge(input({ answers: firing, lastNudgeDay: "2026-07-22" })); // 5 days ago
  assert.equal(day6.decision, "suppress");
  assert.equal(day6.reason, "nudge-cooldown");
  assert.equal(evaluateDietNudge(input({ answers: firing, lastNudgeDay: "2026-07-21" })).reason, "nudge-cooldown",
    "six days is not a week");
  assert.equal(evaluateDietNudge(input({ answers: firing, lastNudgeDay: "2026-07-20" })).decision, "send",
    "exactly seven days later the organ may speak again");
});

test("bad input throws instead of silently deciding to send", () => {
  assert.throws(() => evaluateDietNudge(null), /input must be an object/);
  assert.throws(() => evaluateDietNudge(input({ answers: "lots" })), /answers must be an array/);
  assert.throws(() => evaluateDietNudge(input({ tzOffsetH: null })), /tzOffsetH/);
  assert.throws(() => evaluateDietNudge(input({ answers: [{ answer: "pizza", atMs: NOW }] })), /unknown diet answer/);
  assert.throws(() => evaluateDietNudge(input({ lastNudgeDay: "yesterday" })), /lastNudgeDay/);
});

// ── the copy: fact + one option, never a verdict ──────────────────────────────────────────────────

test("the message states the count and names one place — no adjective about the food", () => {
  const text = buildNudgeMessage({ sampleCount: 6, fastCount: 4, venue: { name: "まいどおおきに食堂", address: "渋谷区道玄坂1-2-3", anchor: "work" } });
  assert.ok(text.includes("6"));
  assert.ok(text.includes("4"));
  assert.ok(text.includes("まいどおおきに食堂"));
  assert.ok(text.includes("渋谷区道玄坂1-2-3"));
  assert.equal(text, DIET_STRINGS.ja.lunchNudge.withVenue
    .replace("{sampleCount}", "6").replace("{fastCount}", "4")
    .replace("{venueName}", "まいどおおきに食堂").replace("{venueAddress}", "渋谷区道玄坂1-2-3"));
});

test("「職場の近く」 is claimed ONLY when the shop was found near an actual work anchor", () => {
  const fromHome = buildNudgeMessage({ sampleCount: 4, fastCount: 2, venue: { name: "定食屋", address: "新宿区1-1", anchor: "home" } });
  assert.ok(!fromHome.includes("職場"), `a home-anchored hit must not be sold as near their office: ${fromHome}`);
  assert.equal(fromHome, DIET_STRINGS.ja.lunchNudge.withVenueNearby
    .replace("{sampleCount}", "4").replace("{fastCount}", "2")
    .replace("{venueName}", "定食屋").replace("{venueAddress}", "新宿区1-1"));
  // An unlabelled venue is treated as the weaker claim, never the stronger one.
  assert.ok(!buildNudgeMessage({ sampleCount: 4, fastCount: 2, venue: { name: "定食屋", address: "新宿区1-1" } }).includes("職場"));
  assert.ok(buildNudgeMessage({ sampleCount: 4, fastCount: 2, venue: { name: "定食屋", address: "新宿区1-1", anchor: "work" } }).includes("職場"));
});

test("a venue name containing $& is printed literally — replace() must not re-expand it", () => {
  const text = buildNudgeMessage({
    sampleCount: 4, fastCount: 2,
    venue: { name: "$& 食堂 $'", address: "$`区1-2-3", anchor: "work" },
  });
  assert.ok(text.includes("$& 食堂 $'"), `the shop's real name must survive: ${text}`);
  assert.ok(text.includes("$`区1-2-3"), text);
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
  assert.deepEqual(venue, { name: "大戸屋 渋谷店", address: "渋谷区道玄坂1-2-3", anchor: "work" });
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
  assert.equal(venue.anchor, "home", "the fallback must SAY it fell back — the copy depends on it");
  assert.ok(locations.every((l) => l === "35.69,139.7"));
});

test("a location that is a link or a bare room label is never geocoded", async () => {
  const queries = [];
  const fetchImpl = async (target) => {
    queries.push(new URL(String(target)).searchParams.get("query"));
    return response(200, { status: "ZERO_RESULTS", results: [] });
  };
  for (const junk of ["https://zoom.us/j/93412", "http://meet.google.com/abc-defg-hij", "3F", "会議室"]) {
    assert.equal(await findLunchAlternative({
      anchors: { home: null, work: junk, usualProviders: [] }, apiKey: "k", fetchImpl,
    }), null);
  }
  assert.deepEqual(queries, [], `a video-call link is not a place, got ${JSON.stringify(queries)}`);
});

test("an unusable work location falls through to home rather than poisoning the search", async () => {
  const fetchImpl = async (target) => {
    const url = new URL(String(target));
    if (url.searchParams.get("query") === "東京都新宿区") {
      return response(200, { status: "OK", results: [{ geometry: { location: { lat: 35.69, lng: 139.7 } } }] });
    }
    return response(200, { status: "OK", results: [{ place_id: "p", name: "定食屋", formatted_address: "新宿区1-1" }] });
  };
  const venue = await findLunchAlternative({
    anchors: { home: "東京都新宿区", work: "https://zoom.us/j/93412", usualProviders: [] }, apiKey: "k", fetchImpl,
  });
  assert.equal(venue.anchor, "home", "a Zoom link is not a workplace, so no work proximity may be claimed");
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
      // Both reads are keyed on `day` — the column the (uid, day DESC) index actually serves.
      const dayFilter = String(url.searchParams.get("day") || "");
      const dayEq = dayFilter.startsWith("eq.") ? dayFilter.slice(3) : "";
      const dayFrom = dayFilter.startsWith("gte.") ? dayFilter.slice(4) : "";
      const matched = store.filter((r) =>
        (!kind || r.kind === kind) && (!dayEq || r.day === dayEq) && (!dayFrom || String(r.day) >= dayFrom));
      matched.sort((a, b) => String(b.day).localeCompare(String(a.day)));
      const limit = Number(url.searchParams.get("limit"));
      return response(200, Number.isFinite(limit) && limit > 0 ? matched.slice(0, limit) : matched);
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
    findLunchAlternative: async () => ({ name: "大戸屋 渋谷店", address: "渋谷区道玄坂1-2-3", anchor: "work" }),
    ...overrides,
  };
}

test("no resolvable timezone means no nudge at all — a sermon at 3am is the worst version of this", async () => {
  const db = supabase(FIRING_ROWS);
  const sent = [];
  const outcome = await dietNudgeOnce(USER, NOW, { ...nudgeDeps(db, sent), tzOffsetH: undefined });
  assert.equal(outcome.status, "skipped");
  assert.equal(outcome.reason, "no-timezone");
  assert.equal(sent.length, 0);
  assert.equal(db.inserts.length, 0);
});

test("the user's OWN zone drives the pre-lunch window", async () => {
  const nyUser = { ...USER, call_time_zone: "America/New_York" };
  const rows = ["fast", "fast", "men", "teishoku"].map((answer, i) => {
    const at = Date.parse("2026-07-27T15:30:00Z") - (i + 1) * DAY; // 11:30 EDT on the 27th
    return {
      uid: "u-diet", kind: "answer", answer,
      day: new Date(at - 4 * 3600000).toISOString().slice(0, 10),
      answered_at: new Date(at).toISOString(),
    };
  });
  const sent = [];
  const outcome = await dietNudgeOnce(nyUser, Date.parse("2026-07-27T15:30:00Z"), {
    ...nudgeDeps(supabase(rows), sent), tzOffsetH: undefined,
  });
  assert.equal(outcome.status, "nudged");
  assert.equal(sent.length, 1);
});

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
  // The anchor is part of the record: the row must show which claim the message was allowed to make.
  assert.deepEqual(nudgeRow.venue, { name: "大戸屋 渋谷店", address: "渋谷区道玄坂1-2-3", anchor: "work" });
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

test("a venue resolver that throws SYNCHRONOUSLY still degrades to the honest message", async () => {
  // `.catch()` on a call that threw before returning a promise never runs — the wrap is the fix.
  const db = supabase(FIRING_ROWS);
  const sent = [];
  const outcome = await dietNudgeOnce(USER, NOW, nudgeDeps(db, sent, {
    findLunchAlternative: () => { throw new Error("sync boom"); },
  }));
  assert.equal(outcome.status, "nudged");
  assert.equal(sent[0].text, DIET_STRINGS.ja.lunchNudge.withoutVenue
    .replace("{sampleCount}", "4").replace("{fastCount}", "2"));
});

test("a day whose claim keeps failing costs ONE Places resolution, not one per tick", async () => {
  // The window is 30 minutes of 60s ticks. Without a memo, a Supabase insert outage buys ~93 Places
  // calls for a single user on a single day — the incident bills us for the incident.
  const db = supabase(FIRING_ROWS);
  const brokenClaim = async (target, init = {}) => {
    if (String(init.method || "GET").toUpperCase() === "POST") return response(500, { message: "insert down" });
    return db.fetchImpl(target, init);
  };
  let placesResolutions = 0;
  const sent = [];
  for (let tick = 0; tick <= 15; tick += 1) {
    await dietNudgeOnce(USER, NOW + tick * 60000, nudgeDeps({ fetchImpl: brokenClaim }, sent, {
      findLunchAlternative: async () => { placesResolutions += 1; return { name: "大戸屋", address: "渋谷区1-1", anchor: "work" }; },
    })).catch(() => {});
  }
  assert.equal(placesResolutions, 1, `16 failing ticks must not buy 16 Places bills, got ${placesResolutions}`);
  assert.equal(sent.length, 0, "nothing was claimed, so nothing was sent");
});

test("4-of-6 fast every day for two weeks produces TWO nudges, on day 1 and day 8", async () => {
  const start = Date.parse("2026-07-01T02:30:00Z"); // 11:30 JST
  // A steady, unambiguously firing history already on file: 2 of every 3 lunches are fast food.
  const rows = [];
  for (let back = 1; back <= 14; back += 1) {
    const at = start - back * DAY;
    rows.push({
      uid: "u-diet", kind: "answer", answer: back % 3 === 0 ? "teishoku" : "fast",
      day: localDayOf(at), answered_at: new Date(at).toISOString(),
    });
  }
  const db = supabase(rows);
  const sent = [];
  const nudgedOn = [];
  for (let dayIndex = 0; dayIndex < 14; dayIndex += 1) {
    const outcome = await dietNudgeOnce(USER, start + dayIndex * DAY, nudgeDeps(db, sent));
    if (outcome.status === "nudged") nudgedOn.push(dayIndex + 1);
  }
  assert.deepEqual(nudgedOn, [1, 8],
    `the 14-day evidence barely moves at 3 asks/week — weekly cadence is the anti-sermon bound, got ${JSON.stringify(nudgedOn)}`);
  assert.equal(sent.length, 2);
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
