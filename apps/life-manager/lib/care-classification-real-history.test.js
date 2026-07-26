// care-classification-real-history.test.js — the production scan row (lm_care_scan_log id=1,
// scanned_at 2026-07-26T11:57:30.605Z) reported history_event_count=10 and one clinic detection at
// personal_interval_days=9 / overdue_days=50, and it was suspected of being an artifact of a
// truncated calendar read (10 looks exactly like a page cap). It is not. Replaying the SAME uid's
// full 703-event 18-month history through fetchCalendarHistory reproduces that row bit-for-bit, and
// the ten care visits below are the real, verbatim event titles and start times behind it.
//
// This file pins them so the meaning of that number can never drift silently again:
//   - history_event_count is NOT "how many calendar events were read" — it is receipt.real_event_count,
//     the count of CARE-CLASSIFIED past visits (6 clinic + 3 haircut + 1 dental = 10 of 703).
//   - the 9-day "personal cadence" is a genuine median of the user's own clinic gaps, not a fetch
//     artifact — and it is genuinely a median over a bimodal history (three visits inside ten weeks
//     in 2025, then a 14-month silence, then two visits in one week in 2026).
//
// ⚠️ PIN DELIBERATELY UPDATED by CADENCE-1 (spec §10 row CADENCE-1). The arithmetic below is
// UNCHANGED — same 10 care visits, same 6 clinic ids, same 9-day median, same 50 overdue days —
// because none of it was ever wrong. What changed is the MEANING the runtime assigns to it: a
// median over gaps of 3.2 / 5.7 / 8.5 / 47 / 419 days is a burst, not a cadence, so "50 days
// overdue against 9" is not a comparison anyone may act on. The detection is therefore now shaped
// observe_only:true / decision_reason:"cadence-unstable" — still recorded on the scan row (the log
// stays honest about what was seen), but no 11b chain, no booking. Booking off this row would have
// been the real false positive; this pin is what stops that regressing back in.
// Run: node --test lib/care-classification-real-history.test.js
"use strict";
const { test } = require("node:test");
const assert = require("node:assert");
const { classifyCareHistory } = require("./care-daily-runtime.js");
const { detectCalendarCare } = require("./care-detector-runtime.js");
const { judgeCadenceStability } = require("./care-detector.js");

// Verbatim from the live Google Calendar of uid lm_784ad279… (read 2026-07-26 via Composio,
// GOOGLECALENDAR_EVENTS_LIST, 703 events over 548 days). Only these ten carry a care keyword.
const REAL_CARE_EVENTS = [
  { id: "0iqiic09kb0jbsh68bjq20sfj4", summary: "Clinic ふじみの", start: { dateTime: "2025-01-31T13:30:00+09:00" } },
  { id: "1aj6pfm4hcnng4njftaka6h564", summary: "散髪", start: { dateTime: "2025-02-26T12:00:00+09:00" } },
  { id: "v3u4q3vaoa55dir2926617hb1k", summary: "健康診断新宿", start: { dateTime: "2025-03-19T14:00:00+09:00" } },
  { id: "89ll4pq50l499alj2njcosqdhc", summary: "カズクリニックへ行く", start: { dateTime: "2025-03-25T08:04:24+09:00" } },
  { id: "sg08fnoe37loddogdp4ov8ub8s", summary: "【CLINICS】医社）燈心会 ライトメンタルクリニックで診察", start: { dateTime: "2025-04-02T20:30:00+09:00" } },
  { id: "es1sdeqqfur98puufji3jv9qvg", summary: "散髪", start: { dateTime: "2025-10-18T18:30:00+09:00" } },
  { id: "3rojvqgmtlp7u48lasd9ioklfc", summary: "[NAIST] 健康診断", start: { date: "2026-05-26" } },
  { id: "cuk8nfea61qiaiib0kkra682is", summary: "🏥 NAIST 健康診断（未受診者枠）ミレニアムホール", start: { dateTime: "2026-05-29T15:00:00+09:00" } },
  { id: "bnimal495ek8cu5e8r2eimfhs8", summary: "四谷歯科 受診（伊藤先生）", start: { dateTime: "2026-06-13T08:00:00+09:00" } },
  { id: "2nfhjqrt4okn1gkoj7k7f74v8g", summary: "💇 [CONFIRMED] Rein 散髪 (カット 30分 ¥2900)", start: { dateTime: "2026-06-21T11:00:00+09:00" } },
];

// The 703-event history also holds ordinary events. They must classify as care for NOTHING —
// noise in, silence out — otherwise real_event_count stops meaning "care visits".
const REAL_NON_CARE_EVENTS = [
  { id: "n1", summary: "お祭り　ちゃむ　家の裏", start: { dateTime: "2026-07-26T16:30:00+09:00" } },
  { id: "n2", summary: "Anicca E2E talk test (Dais admits)", start: { dateTime: "2026-05-29T02:18:07+09:00" } },
  { id: "n3", summary: "Train to 新大阪", start: { dateTime: "2025-02-03T19:17:00+09:00" } },
  { id: "n4", summary: "", start: { date: "2025-01-28" } },
];

const PROD_SCAN_MS = Date.parse("2026-07-26T11:57:30.605Z"); // lm_care_scan_log id=1 scanned_at
const events = [...REAL_CARE_EVENTS, ...REAL_NON_CARE_EVENTS]
  .map((e) => ({ ...e, startMs: Date.parse(e.start.dateTime || e.start.date) }));

test("real titles → the three care types, and nothing else classifies as care", () => {
  const sources = classifyCareHistory(events);
  const byType = Object.fromEntries(sources.map((s) => [s.careType, s.events.map((e) => e.id).sort()]));
  assert.deepEqual(Object.keys(byType).sort(), ["clinic", "dental", "haircut"]);
  assert.equal(byType.clinic.length, 6, "健康診断 / クリニック / Clinic all fold into clinic");
  assert.equal(byType.haircut.length, 3);
  assert.equal(byType.dental.length, 1);
  const classified = new Set(sources.flatMap((s) => s.events.map((e) => e.id)));
  for (const noise of REAL_NON_CARE_EVENTS) {
    assert.ok(!classified.has(noise.id), `${noise.summary || "(untitled)"} is not a care visit`);
  }
});

test("history_event_count=10 is the CARE-visit count, not the calendar page size", () => {
  const receipt = detectCalendarCare({ nowMs: PROD_SCAN_MS, intents: [], sources: classifyCareHistory(events) });
  // 10 = 6 + 3 + 1, out of 703 events read. The production row's history_event_count is exactly
  // this field, so "10 of 703" was never evidence of a truncated fetch.
  assert.equal(receipt.real_event_count, 10);
});

test("the production detection reproduces exactly from the real events — 9-day cadence, 50 days overdue, but OBSERVE-ONLY", () => {
  const receipt = detectCalendarCare({ nowMs: PROD_SCAN_MS, intents: [], sources: classifyCareHistory(events) });
  assert.deepEqual(receipt.candidates, [{
    care_type: "clinic",
    reason: "personal-cadence-overdue",
    personal_interval_days: 9,
    overdue_days: 50,
    // CADENCE-1: the numbers are unchanged and correct; the verdict on them is not.
    observe_only: true,
    decision_reason: "cadence-unstable",
    source_provider_ids: [
      "0iqiic09kb0jbsh68bjq20sfj4",
      "3rojvqgmtlp7u48lasd9ioklfc",
      "89ll4pq50l499alj2njcosqdhc",
      "cuk8nfea61qiaiib0kkra682is",
      "sg08fnoe37loddogdp4ov8ub8s",
      "v3u4q3vaoa55dir2926617hb1k",
    ],
  }]);
});

test("the 9 days is the true median of the user's own clinic gaps — bimodal, but not fabricated", () => {
  const clinic = classifyCareHistory(events).find((s) => s.careType === "clinic").events
    .map((e) => e.startMs).sort((a, b) => a - b);
  const gapDays = clinic.slice(1).map((t, i) => (t - clinic[i]) / 86400000);
  const sorted = [...gapDays].sort((a, b) => a - b);
  assert.equal(gapDays.length, 5);
  assert.equal(Math.round(sorted[2]), 9, "median gap — three 2025 visits in ten weeks, then 14 months, then two in a week");
  assert.ok(sorted[0] < 6 && sorted[4] > 400, "the distribution really is bimodal, so the median is a weak cadence claim");
  // 58 days since the last visit vs a 9-day median: over the 1.5x OVERDUE_FACTOR either way.
  assert.ok((PROD_SCAN_MS - clinic[clinic.length - 1]) / 86400000 > 58);
  // CADENCE-1: the guard reads exactly these gaps and refuses to call them a cadence.
  const gapsMs = clinic.slice(1).map((t, i) => t - clinic[i]);
  assert.deepEqual(judgeCadenceStability(gapsMs), { decision: "observe", reason: "cadence-unstable" });
  const m = sorted[2] * 86400000;
  const mad = [...gapsMs.map((g) => Math.abs(g - m))].sort((a, b) => a - b)[2];
  assert.ok(mad > 0.5 * m, "MAD exceeds half the median — the dispersion clause fails");
  assert.ok(sorted[4] * 86400000 > 2.5 * m, "the 419-day gap is far outside the 2.5×median band");
});

test("the observe-only detection carries the honest numbers AND the refusal to act on them", () => {
  const receipt = detectCalendarCare({ nowMs: PROD_SCAN_MS, intents: [], sources: classifyCareHistory(events) });
  const [clinic] = receipt.candidates;
  assert.equal(clinic.personal_interval_days, 9, "the arithmetic is untouched");
  assert.equal(clinic.overdue_days, 50);
  assert.equal(clinic.observe_only, true, "…and it is not something to book against");
  assert.equal(clinic.decision_reason, "cadence-unstable");
});

test("haircut and dental stay silent — one and two visits are not a cadence", () => {
  const receipt = detectCalendarCare({ nowMs: PROD_SCAN_MS, intents: [], sources: classifyCareHistory(events) });
  assert.deepEqual(receipt.candidates.map((c) => c.care_type), ["clinic"]);
});
