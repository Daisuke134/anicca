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

// A cadence the detector actually fires on: 40±6-day haircut rhythm over FIVE visits (four gaps:
// 40/34/46/40 → median 40, MAD 3), last visit 70 days ago (70 > 1.5 × 40). Five visits, not three:
// CADENCE-1 requires ≥3 gaps plus a dispersion bound before a gap set counts as a cadence at all,
// so a three-visit fixture would now shape observe_only and never reach the 11b chain. The salon
// location repeats so care-anchors sees a usual provider, and a still more frequent office location
// exists so the work anchor derives from real workplace repetition (WORK_MIN_OCCURRENCES).
const HAIRCUT_DAYS_AGO = [230, 190, 156, 110, 70];
function overdueHaircutHistory() {
  const office = (n) => ({ id: `of${n}`, summary: "チーム定例", location: "オフィス東京", startMs: NOW - n * 7 * DAY_MS, start: { dateTime: new Date(NOW - n * 7 * DAY_MS).toISOString() } });
  const haircut = (daysAgo, i) => ({ id: `hc${i + 1}`, summary: "散髪", location: "サロンA 新宿", startMs: NOW - daysAgo * DAY_MS, start: { dateTime: new Date(NOW - daysAgo * DAY_MS).toISOString() } });
  return [
    ...HAIRCUT_DAYS_AGO.map(haircut),
    office(1), office(2), office(3), office(4), office(5), office(6),
  ];
}

// The bimodal burst that produced the first production scan row (clinic, 9-day "cadence", 50 days
// overdue) — gaps 47.0 / 5.7 / 8.5 / 419 / 3.2 days. Real detection, honest arithmetic, not a
// cadence: CADENCE-1 shapes it observe_only.
function burstClinicHistory() {
  const gapDays = [47.02, 5.75, 8.52, 419.0, 3.25];
  const offsets = [0];
  for (const gap of gapDays) offsets.push(offsets[offsets.length - 1] + gap);
  const span = offsets[offsets.length - 1];
  return offsets.map((o, i) => {
    const ms = NOW - (span - o + 58) * DAY_MS;
    return { id: `cl${i}`, summary: "クリニック", location: "内科クリニック新宿", startMs: ms, start: { dateTime: new Date(ms).toISOString() } };
  });
}

function checkupHistory(careType, summary, dates) {
  return dates.map((date, i) => {
    const startMs = Date.parse(`${date}T09:00:00+09:00`);
    return {
      id: `${careType}-${i}`,
      summary,
      location: "新宿検診センター",
      startMs,
      start: { dateTime: new Date(startMs).toISOString() },
    };
  });
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

test("history fetch window: the scan delegates to the 10-year events.js default at nowMs", async () => {
  const supa = fakeSupa();
  let seen = null;
  await careUserOnce(USER, NOW, baseDeps(supa, {
    fetchCalendarHistory: async (uid, opts) => { seen = { uid, opts }; return []; },
  }));
  assert.equal(seen.uid, USER.uid);
  assert.equal(seen.opts.nowMs, NOW);
  assert.equal(seen.opts.historyMs, undefined, "undefined delegates to the tested 10-year default");
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

test("actionable gastric checkup cadence reaches the existing 11b chain with its specific category", async () => {
  const supa = fakeSupa();
  let searched = null;
  const result = await careUserOnce(USER, NOW, baseDeps(supa, {
    fetchCalendarHistory: async () => checkupHistory(
      "gastric_screening",
      "胃がん検診",
      ["2020-01-01", "2021-01-01", "2022-01-01", "2023-01-01"],
    ),
    searchCareCandidates: async (args) => {
      searched = args.category;
      return { definitions: [], shortfallReason: "no bookable provider in anchors" };
    },
  }));
  assert.equal(result.status, "detected");
  assert.equal(result.category, "gastric_screening");
  assert.equal(searched, "gastric_screening");
  assert.equal(supa.calls.posts[0].detections[0].care_type, "gastric_screening");
  assert.equal(supa.calls.posts[0].detections[0].observe_only, false);
  assert.equal(supa.calls.patches[0].body.chain.category, "gastric_screening");
});

test("brain-dock with only two gaps is recorded observe-only and never spends on search", async () => {
  const supa = fakeSupa();
  let searches = 0;
  const result = await careUserOnce(USER, NOW, baseDeps(supa, {
    fetchCalendarHistory: async () => checkupHistory(
      "brain_dock",
      "脳ドック",
      ["2020-01-01", "2021-01-01", "2022-01-01"],
    ),
    searchCareCandidates: async () => {
      searches += 1;
      return { definitions: [], shortfallReason: null };
    },
  }));
  assert.equal(result.status, "observed");
  assert.deepEqual(result.observeOnly, ["brain_dock"]);
  assert.equal(searches, 0);
  const [detection] = supa.calls.posts[0].detections;
  assert.equal(detection.care_type, "brain_dock");
  assert.equal(detection.observe_only, true);
  assert.equal(detection.decision_reason, "insufficient-gaps");
  assert.equal(supa.calls.patches.length, 0);
});

// ── CADENCE-1 (spec §10 row CADENCE-1) ────────────────────────────────────────────────────────
// The first production scan detected clinic / 9-day cadence / 50 days overdue from a bimodal
// burst. The row was honest; acting on it would not have been. An observe-only detection must
// still land on the append-only scan row (so the log never hides what was seen) while the 11b
// chain — anchors, the paid Places search, evaluation — is not run at all.
test("observe-only detection: the burst lands on the scan row and the 11b chain never runs", async () => {
  const supa = fakeSupa();
  let searches = 0; let evaluations = 0;
  const result = await careUserOnce(USER, NOW, baseDeps(supa, {
    fetchCalendarHistory: async () => burstClinicHistory(),
    mapsKey: "maps-key",
    searchCareCandidates: async () => { searches += 1; return { definitions: [], shortfallReason: null }; },
    evaluateCareCandidates: async () => { evaluations += 1; return { schema_version: 1, candidates: [], selected_provider_id: null }; },
  }));
  assert.equal(result.status, "observed", "seen, recorded, not acted on");
  assert.deepEqual(result.observeOnly, ["clinic"]);
  // the detection survives on the row, with its honest numbers AND its refusal
  assert.equal(supa.calls.posts.length, 1);
  const [detection] = supa.calls.posts[0].detections;
  assert.equal(detection.care_type, "clinic");
  assert.equal(detection.personal_interval_days, 9, "the honest median survives on the row");
  // 58 days since the last visit − the 9-day median. (The exact production 50 is pinned against the
  // verbatim event timestamps in care-classification-real-history.test.js; this fixture rebuilds the
  // gaps from the measured day-lengths, so it lands one rounding step away.)
  assert.equal(detection.overdue_days, 49);
  assert.equal(detection.observe_only, true);
  assert.equal(detection.decision_reason, "cadence-unstable");
  // and nothing downstream ran — no anchors, no paid Places call, no chain PATCH
  assert.equal(searches, 0, "an unstable cadence must never spend on a Places search");
  assert.equal(evaluations, 0);
  assert.equal(supa.calls.patches.length, 0, "no chain result to persist");
});

test("a mix of one actionable and one observe-only detection chains only the actionable one", async () => {
  const supa = fakeSupa();
  let searchedCategory = null;
  const result = await careUserOnce(USER, NOW, baseDeps(supa, {
    fetchCalendarHistory: async () => [...burstClinicHistory(), ...overdueHaircutHistory()],
    searchCareCandidates: async (args) => { searchedCategory = args.category; return { definitions: [], shortfallReason: null }; },
  }));
  assert.equal(result.status, "detected");
  assert.equal(result.category, "haircut");
  assert.equal(searchedCategory, "haircut", "the chain binds to the ACTIONABLE detection, never the observed one");
  const detections = supa.calls.posts[0].detections;
  assert.deepEqual(
    Object.fromEntries(detections.map((d) => [d.care_type, d.observe_only])),
    { clinic: true, haircut: false },
    "both are on the row; only one is actionable",
  );
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

test("checkup titles classify into specific gastric, colorectal, and brain categories before generic clinic", () => {
  const sources = classifyCareHistory([
    { id: "g1", summary: "胃がん検診", startMs: 1 },
    { id: "g2", summary: "胃内視鏡 さくらクリニック", startMs: 2 },
    { id: "c1", summary: "大腸がん検診", startMs: 3 },
    { id: "c2", summary: "大腸内視鏡 さくらクリニック", startMs: 4 },
    { id: "b1", summary: "脳ドック", startMs: 5 },
    { id: "b2", summary: "Brain screening", startMs: 6 },
    { id: "n1", summary: "頭部MRIの研究MTG", startMs: 7 },
    { id: "n2", summary: "胃にやさしいランチ", startMs: 8 },
  ]);
  const byType = Object.fromEntries(sources.map((s) => [s.careType, s.events.map((e) => e.id)]));
  assert.deepEqual(byType, {
    gastric_screening: ["g1", "g2"],
    colorectal_screening: ["c1", "c2"],
    brain_dock: ["b1", "b2"],
  });
});

// 11c/11d gave this module a Telegram/calendar/browser surface, so the old source-grep purity check
// ("no send path appears in the file at all") is superseded — it would now forbid the very wiring
// §10 rows 11c/11d call for. The invariant it was PROTECTING is unchanged and is now asserted the
// stronger, behavioural way, both here (gate absent ⇒ nothing happens) and across
// lib/care-booking-wiring.test.js. What survives as a source check is the one rule no gate may ever
// unlock: §9.5 forbids the AI from phoning a provider.
test("gate absent: no send path, no calendar write, no browser session can run", async () => {
  const supa = fakeSupa();
  let sends = 0;
  let calendarWrites = 0;
  let steelCalls = 0;
  const result = await careUserOnce(USER, NOW, baseDeps(supa, {
    fetchCalendarHistory: async () => overdueHaircutHistory(),
    searchCareCandidates: async () => ({ definitions: [{}], shortfallReason: null }),
    evaluateCareCandidates: async () => ({
      schema_version: 1,
      selected_provider_id: "p-web",
      candidates: [{ provider_id: "p-web", public_name: "サロンA", reservation_route: "web", reservation_url: "https://x/reserve" }],
    }),
    bookingEnabled: false,
    sendMessage: async () => { sends += 1; return { ok: true, result: { message_id: 1 } }; },
    calendar: { createEvent: async () => { calendarWrites += 1; return { successful: true }; } },
    cdp: { createSession: async () => { steelCalls += 1; throw new Error("must never be reached"); } },
  }));
  assert.equal(result.status, "detected");
  assert.equal(result.bookingOutcome, undefined);
  assert.equal(sends, 0);
  assert.equal(calendarWrites, 0);
  assert.equal(steelCalls, 0);
});

test("§9.5: no gate unlocks a phone call to a provider", () => {
  const src = fs.readFileSync(path.join(__dirname, "care-daily-runtime.js"), "utf8");
  assert.doesNotMatch(src, /placeCall|telnyx|outboundCall/i, "the AI never phones a provider (§9.5)");
});
