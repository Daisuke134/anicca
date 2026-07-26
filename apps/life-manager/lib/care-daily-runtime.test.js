// care-daily-runtime.test.js — 11a/11b runtime: the PHYSICAL organ scans BY ITSELF once per UTC day
// per user, records every scan (abstention included) durably in lm_care_scan_log, and on a real
// detection runs the 11b chain (anchors → candidate search → evaluation) in-process. No booking, no
// Telegram — 11c/11d own the side effects; this module's product is the self-executing
// detection+candidates record. Run: node --test lib/care-daily-runtime.test.js
"use strict";
const { test } = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const { careUserOnce, classifyCareHistory } = require("./care-daily-runtime.js");

const NOW = Date.parse("2026-07-26T00:00:00Z");
const DAY_MS = 86400000;
const USER = { uid: "u-care", home_address: "東京都新宿区1-1-1", gmail_account_id: null };

// A cadence the detector actually fires on: 40-day haircut rhythm, last visit 70 days ago
// (70 > 1.5 × 40). The salon location repeats so care-anchors sees a usual provider, and a more
// frequent office location exists so the work anchor derives from real workplace repetition
// (WORK_MIN_OCCURRENCES) instead of the salon visits.
function overdueHaircutHistory() {
  const office = (n) => ({ id: `of${n}`, summary: "チーム定例", location: "オフィス東京", startMs: NOW - n * 7 * DAY_MS, start: { dateTime: new Date(NOW - n * 7 * DAY_MS).toISOString() } });
  return [
    { id: "hc1", summary: "散髪", location: "サロンA 新宿", startMs: NOW - 150 * DAY_MS, start: { dateTime: new Date(NOW - 150 * DAY_MS).toISOString() } },
    { id: "hc2", summary: "散髪", location: "サロンA 新宿", startMs: NOW - 110 * DAY_MS, start: { dateTime: new Date(NOW - 110 * DAY_MS).toISOString() } },
    { id: "hc3", summary: "散髪", location: "サロンA 新宿", startMs: NOW - 70 * DAY_MS, start: { dateTime: new Date(NOW - 70 * DAY_MS).toISOString() } },
    office(1), office(2), office(3), office(4),
  ];
}

// Supabase double: GET returns existingRows, POST returns postStatus(+postBody), PATCH is recorded
// (patchOk=false simulates a failed chain persist).
function fakeSupa({ existingRows = [], postStatus = 201, postBody = "", patchOk = true } = {}) {
  const calls = { gets: [], posts: [], patches: [] };
  const fetchImpl = async (url, opts = {}) => {
    const method = (opts.method || "GET").toUpperCase();
    if (method === "GET") {
      calls.gets.push(url);
      return { ok: true, status: 200, json: async () => existingRows };
    }
    if (method === "POST") {
      calls.posts.push(JSON.parse(opts.body));
      return { ok: postStatus === 201, status: postStatus, json: async () => [], text: async () => postBody };
    }
    calls.patches.push({ url, body: JSON.parse(opts.body) });
    return { ok: patchOk, status: patchOk ? 204 : 500, json: async () => [] };
  };
  return { calls, fetchImpl };
}

function baseDeps(supa, overrides = {}) {
  return {
    supaUrl: "https://db.example",
    supaKey: "service",
    fetchImpl: supa.fetchImpl,
    fetchCalendarHistory: async () => [],
    searchCareCandidates: async () => ({ definitions: [], shortfallReason: "none" }),
    evaluateCareCandidates: async () => ({ schema_version: 1, candidates: [], selected_provider_id: null }),
    ...overrides,
  };
}

test("claim-once: a second tick the same UTC day does not scan again", async () => {
  const supa = fakeSupa({ existingRows: [{ id: 1 }] });
  let historyFetches = 0;
  const result = await careUserOnce(USER, NOW, baseDeps(supa, {
    fetchCalendarHistory: async () => { historyFetches += 1; return []; },
  }));
  assert.equal(result.status, "already_scanned");
  assert.equal(historyFetches, 0, "no calendar read when today's row already exists");
  assert.equal(supa.calls.posts.length, 0, "no second scan row");
});

test("insert race (409) means another tick claimed today — stop, no chain", async () => {
  const supa = fakeSupa({ postStatus: 409 });
  let chainRan = 0;
  const result = await careUserOnce(USER, NOW, baseDeps(supa, {
    fetchCalendarHistory: async () => overdueHaircutHistory(),
    searchCareCandidates: async () => { chainRan += 1; return { definitions: [], shortfallReason: null }; },
  }));
  assert.equal(result.status, "already_scanned");
  assert.equal(chainRan, 0, "the loser of the race must not run the 11b chain");
});

test("history fetch window: the scan reads ~18 months of history at nowMs", async () => {
  const supa = fakeSupa();
  let seen = null;
  await careUserOnce(USER, NOW, baseDeps(supa, {
    fetchCalendarHistory: async (uid, opts) => { seen = { uid, opts }; return []; },
  }));
  assert.equal(seen.uid, USER.uid);
  assert.equal(seen.opts.nowMs, NOW);
  assert.ok(!Number.isFinite(seen.opts.historyMs) || seen.opts.historyMs >= 540 * DAY_MS,
    "history window must cover ~18 months (or defer to the events.js default)");
});

test("abstention (the honest common case) records a scan row with empty detections", async () => {
  const supa = fakeSupa();
  const result = await careUserOnce(USER, NOW, baseDeps(supa, {
    // one haircut = a visit, not a cadence → detector must stay silent
    fetchCalendarHistory: async () => [overdueHaircutHistory()[0]],
  }));
  assert.equal(result.status, "abstained");
  assert.equal(supa.calls.posts.length, 1);
  const row = supa.calls.posts[0];
  assert.equal(row.uid, USER.uid);
  assert.equal(row.scan_day, "2026-07-26");
  assert.deepEqual(row.detections, []);
  assert.equal(row.history_event_count, 1);
  assert.equal(supa.calls.patches.length, 0, "no chain on abstention");
});

test("real detection: the 11b chain runs in-process and the full result lands on the scan row", async () => {
  const supa = fakeSupa();
  const definitions = [{ providerId: "p1", publicName: "サロンB", officialUrl: "https://salon-b.example/", proximityRank: 1, usualProvider: false }];
  const evaluated = {
    schema_version: 1,
    candidates: [{ provider_id: "p1", public_name: "サロンB", official_url: "https://salon-b.example/", proximity_rank: 1, usual_provider: false, reservation_route: "web", reservation_url: "https://salon-b.example/reserve" }],
    selected_provider_id: "p1",
  };
  let searchArgs = null;
  const result = await careUserOnce(USER, NOW, baseDeps(supa, {
    fetchCalendarHistory: async () => overdueHaircutHistory(),
    mapsKey: "maps-key",
    searchCareCandidates: async (args) => { searchArgs = args; return { definitions, shortfallReason: "only 1 of 3" }; },
    evaluateCareCandidates: async (defs) => { assert.deepEqual(defs, definitions); return evaluated; },
  }));
  assert.equal(result.status, "detected");
  assert.equal(result.category, "haircut");
  assert.equal(result.selectedProviderId, "p1");
  // detection row first (durable), chain result second (same row)
  assert.equal(supa.calls.posts.length, 1);
  assert.equal(supa.calls.posts[0].detections.length, 1);
  assert.equal(supa.calls.posts[0].detections[0].care_type, "haircut");
  // the search was bound to the detected category + the user's own anchors + injected key
  assert.equal(searchArgs.category, "haircut");
  assert.equal(searchArgs.apiKey, "maps-key");
  assert.equal(searchArgs.anchors.home, USER.home_address);
  assert.equal(searchArgs.anchors.work, "オフィス東京", "work anchor derives from the user's own repeated calendar locations");
  assert.deepEqual(searchArgs.anchors.usualProviders, [{ careType: "haircut", location: "サロンA 新宿" }]);
  // full persisted chain: category, anchors used (privacy-redacted), candidates, selection, shortfall
  assert.equal(supa.calls.patches.length, 1);
  const chain = supa.calls.patches[0].body.chain;
  assert.equal(chain.category, "haircut");
  assert.deepEqual(chain.anchors_used, { home: true, work: true, usual_provider_care_types: ["haircut"] });
  assert.deepEqual(chain.candidates, evaluated.candidates);
  assert.equal(chain.selected_provider_id, "p1");
  assert.equal(chain.shortfall_reason, "only 1 of 3");
  // 11b privacy rule: the raw home address never rides into the scan log
  assert.ok(!JSON.stringify(supa.calls.patches[0].body).includes(USER.home_address));
});

test("chain failure is isolated: a throwing candidate search cannot lose the detection row", async () => {
  const supa = fakeSupa();
  const result = await careUserOnce(USER, NOW, baseDeps(supa, {
    fetchCalendarHistory: async () => overdueHaircutHistory(),
    searchCareCandidates: async () => { throw new Error("places quota exhausted"); },
  }));
  assert.equal(result.status, "detected", "the detection itself still reports");
  assert.equal(result.chainError, "places quota exhausted");
  assert.equal(supa.calls.posts.length, 1, "detection row was written BEFORE the chain ran");
  assert.equal(supa.calls.posts[0].detections[0].care_type, "haircut");
  assert.equal(supa.calls.patches.length, 1);
  assert.equal(supa.calls.patches[0].body.chain_error, "places quota exhausted");
});

// 🔴 Finding 1: a failed history read must NOT claim the day. Freezing history_event_count=0 /
// detections=[] into the append-only lm_care_scan_log on an API failure poisons the claim — the day
// is permanently marked scanned with fabricated emptiness. Failure ≠ empty calendar.
test("history read failure → history_unavailable, NO claim row — the next tick retries", async () => {
  const supa = fakeSupa();
  const result = await careUserOnce(USER, NOW, baseDeps(supa, {
    fetchCalendarHistory: async () => { throw new Error("composio 502"); },
  }));
  assert.equal(result.status, "history_unavailable");
  assert.equal(supa.calls.posts.length, 0, "a failed read must never freeze count=0 into the log");
  assert.equal(supa.calls.patches.length, 0, "no chain either");
});

test("transport failure through the REAL history reader → history_unavailable (not a fake empty scan)", async () => {
  const supa = fakeSupa();
  const deps = baseDeps(supa, {
    calendar: { kind: "fake", ready: () => true, async listEventsRaw() { throw new Error("api down"); } },
  });
  delete deps.fetchCalendarHistory; // exercise the real events.js reader over a failing transport
  const result = await careUserOnce(USER, NOW, deps);
  assert.equal(result.status, "history_unavailable");
  assert.equal(supa.calls.posts.length, 0);
});

// A TRUNCATED history is the same class of lie as a failed one: the read "succeeded" but what came
// back is not the user's history, and lm_care_scan_log is append-only, so persisting it would freeze
// a fabricated cadence forever. Provable-incompleteness must land as history_unavailable too.
test("truncated history (full page, no cursor to follow) → history_unavailable, NO claim row", async () => {
  const supa = fakeSupa();
  const bulk = [];
  for (let i = 0; i < 2500; i += 1) {
    bulk.push({ id: `b${i}`, summary: "予定", start: { dateTime: new Date(NOW - (2500 - i) * 3600000).toISOString() } });
  }
  const deps = baseDeps(supa, {
    calendar: { kind: "fake", ready: () => true, async listEventsRaw() { return bulk; } },
  });
  delete deps.fetchCalendarHistory; // the real events.js reader must refuse to call this complete
  const result = await careUserOnce(USER, NOW, deps);
  assert.equal(result.status, "history_unavailable");
  assert.match(result.error, /truncat/i);
  assert.equal(supa.calls.posts.length, 0, "a provably-incomplete history must never claim the day");
});

// 🟡 Finding 2: only the duplicate-key race means "already scanned". A 500/503 from Supabase must
// surface as a throw (the scheduler's catch logs it) — otherwise real outages masquerade as dedup.
test("insert failure that is NOT the duplicate race throws — 500 is not 'already scanned'", async () => {
  const supa = fakeSupa({ postStatus: 500, postBody: "internal error" });
  await assert.rejects(
    () => careUserOnce(USER, NOW, baseDeps(supa, { fetchCalendarHistory: async () => overdueHaircutHistory() })),
    /500/,
  );
});

test("PostgREST duplicate-key body counts as the race loss even off the 409 status", async () => {
  const supa = fakeSupa({ postStatus: 400, postBody: JSON.stringify({ code: "23505", message: "duplicate key value violates unique constraint" }) });
  const result = await careUserOnce(USER, NOW, baseDeps(supa, { fetchCalendarHistory: async () => overdueHaircutHistory() }));
  assert.equal(result.status, "already_scanned");
});

// 🟡 Finding 3: the chain PATCH lands AFTER the Places spend already happened. A silent persist
// failure would burn the spend and hide the loss — it must be visible via the injectable logger.
test("chain persist failure is visible: failed PATCH logs chain-persist-failed", async () => {
  const supa = fakeSupa({ patchOk: false });
  const logs = [];
  const result = await careUserOnce(USER, NOW, baseDeps(supa, {
    fetchCalendarHistory: async () => overdueHaircutHistory(),
    logError: (...args) => logs.push(args.join(" ")),
  }));
  assert.equal(result.status, "detected", "the detection row itself already landed");
  assert.ok(
    logs.some((m) => m.includes("chain-persist-failed") && m.includes(USER.uid)),
    `expected a chain-persist-failed log naming the uid, got: ${JSON.stringify(logs)}`,
  );
});

test("missing Supabase config → honest skip, no throw", async () => {
  const result = await careUserOnce(USER, NOW, { supaUrl: "", supaKey: "", fetchImpl: async () => { throw new Error("must not fetch"); } });
  assert.equal(result.status, "skipped");
});

test("classifyCareHistory groups by care type on the user's own words; unrelated events pass through as anchors only", () => {
  const sources = classifyCareHistory([
    { id: "a", summary: "散髪", startMs: 1 },
    { id: "b", summary: "歯科検診", startMs: 2 },
    { id: "c", summary: "チームMTG", startMs: 3 },
    { id: "d", summary: "内科クリニック", startMs: 4 },
  ]);
  const byType = Object.fromEntries(sources.map((s) => [s.careType, s.events.map((e) => e.id)]));
  assert.deepEqual(byType, { haircut: ["a"], dental: ["b"], clinic: ["d"] });
});

test("this path has NO Telegram surface — 11c/11d own the side effects", () => {
  const src = fs.readFileSync(path.join(__dirname, "care-daily-runtime.js"), "utf8");
  assert.doesNotMatch(src, /telegram|sendMessage/i, "care runtime must not import or call any send path");
  assert.doesNotMatch(src, /placeCall|createEvent|care-booking/i, "no booking / calendar / call side effects in 11a/11b runtime");
});
