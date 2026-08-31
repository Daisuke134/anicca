"use strict";
// 11a PHY-a contract: closed schemas + the two spec invariants — no fixed
// cycle imposed on anyone (no personal history → no detection, ever) and no
// medical diagnosis (the closed candidate schema has no field to carry one).
// The full decision matrix lives in eval/phy-cases.jsonl.

const test = require("node:test");
const assert = require("node:assert/strict");
const { validateInput, detectUnmetCare, judgeCadenceStability } = require("./care-detector.js");

const DAY = 86400000;
const NOW = 1753344000000;

function input(overrides = {}) {
  return { nowMs: NOW, visits: [], intents: [], ...overrides };
}

test("schema: closed input keys and visit shape", () => {
  assert.doesNotThrow(() => validateInput(input()));
  assert.throws(() => validateInput({ ...input(), extra: 1 }), /unknown key/);
  assert.throws(() => validateInput(input({ visits: [{ startMs: 1, careType: "dental", note: "x" }] })), /unknown key: visit/);
  assert.throws(() => validateInput(input({ visits: [{ startMs: 1, careType: "" }] })), /careType/);
});

test("no fixed cycle: zero and single-visit histories never flag, at any elapsed time", () => {
  for (const yearsAgo of [1, 2, 5]) {
    const single = detectUnmetCare(input({ visits: [{ startMs: NOW - yearsAgo * 365 * DAY, careType: "dental" }] }));
    assert.deepEqual(single.candidates, [], `single visit ${yearsAgo}y ago must not flag`);
  }
  assert.deepEqual(detectUnmetCare(input()).candidates, []);
});

test("no diagnosis: candidates carry only visit-gap observation fields", () => {
  const out = detectUnmetCare(input({ visits: [
    { startMs: NOW - 840 * DAY, careType: "dental" },
    { startMs: NOW - 660 * DAY, careType: "dental" },
    { startMs: NOW - 480 * DAY, careType: "dental" },
    { startMs: NOW - 300 * DAY, careType: "dental" },
  ] }));
  assert.equal(out.candidates.length, 1);
  // decision / decisionReason are the CADENCE-1 stability verdict, still pure visit-gap
  // arithmetic — no field here can carry a diagnosis.
  assert.deepEqual(Object.keys(out.candidates[0]).sort(), [
    "careType", "decision", "decisionReason", "lastVisitMs", "overdueDays",
    "personalIntervalDays", "reason",
  ]);
});

test("cadence is personal: identical elapsed time flags one user and not another", () => {
  // 4+ visits on both sides: CADENCE-1 requires at least 3 gaps before "overdue vs cadence"
  // is a meaningful claim, so the personal-cadence contrast is now measured at that width.
  const gapDays = 120;
  const shortCadence = detectUnmetCare(input({ visits: [
    { startMs: NOW - (gapDays + 135) * DAY, careType: "haircut" },
    { startMs: NOW - (gapDays + 90) * DAY, careType: "haircut" },
    { startMs: NOW - (gapDays + 45) * DAY, careType: "haircut" },
    { startMs: NOW - gapDays * DAY, careType: "haircut" },
  ] }));
  assert.equal(shortCadence.candidates.length, 1, "45-day-cadence user is overdue after 120 days");
  assert.equal(shortCadence.candidates[0].decision, "act");
  const longCadence = detectUnmetCare(input({ visits: [
    { startMs: NOW - (gapDays + 540) * DAY, careType: "haircut" },
    { startMs: NOW - (gapDays + 360) * DAY, careType: "haircut" },
    { startMs: NOW - (gapDays + 180) * DAY, careType: "haircut" },
    { startMs: NOW - gapDays * DAY, careType: "haircut" },
  ] }));
  assert.deepEqual(longCadence.candidates, [], "180-day-cadence user is fine after the same 120 days");
});

// ── CADENCE-1 (spec §10 row CADENCE-1) ────────────────────────────────────────────────────────
// The first production scan (2026-07-26) computed clinic personal_interval_days=9 from gaps of
// 3.2 / 5.7 / 8.5 / 47 / 419 days. The median is honest arithmetic over a BIMODAL BURST — three
// visits in ten weeks of 2025, fourteen months of silence, two visits in one week of 2026 — and
// "50 days overdue against a 9-day cadence" is a meaningless comparison. Booking on it would be
// the real false positive. A gap set is a cadence only when the gaps are mutually consistent
// enough that "overdue vs cadence" means something; otherwise the detection survives as an
// OBSERVATION (decision:"observe") and nothing downstream may act on it.

const REAL_CLINIC_GAP_DAYS = [47.02, 5.75, 8.52, 419.0, 3.25]; // measured, chronological

test("guard math: the real bimodal clinic history is NOT a cadence", () => {
  const verdict = judgeCadenceStability(REAL_CLINIC_GAP_DAYS.map((d) => d * DAY));
  assert.deepEqual(verdict, { decision: "observe", reason: "cadence-unstable" });
});

test("guard math: MAD ≤ 0.5×median OR every gap inside [0.4×m, 2.5×m] is a cadence", () => {
  // 40±6 day haircut rhythm: median 40, MAD 3 ≤ 20 — stable on both clauses.
  assert.deepEqual(
    judgeCadenceStability([40, 34, 46, 40].map((d) => d * DAY)),
    { decision: "act", reason: null },
  );
  // The OR really is a disjunction: gaps 10/10/35/35 → median 22.5, MAD 12.5 > 11.25 (dispersion
  // clause FAILS) but every gap sits inside [9, 56.25], so the band clause alone makes it a cadence.
  assert.deepEqual(
    judgeCadenceStability([10, 10, 35, 35].map((d) => d * DAY)),
    { decision: "act", reason: null },
  );
  // One gap outside 2.5×m AND a MAD over half the median → not a cadence.
  assert.deepEqual(
    judgeCadenceStability([10, 10, 60, 200].map((d) => d * DAY)),
    { decision: "observe", reason: "cadence-unstable" },
  );
});

test("guard math: fewer than 3 gaps (under 4 visits) is insufficient data, not a cadence", () => {
  assert.deepEqual(
    judgeCadenceStability([40, 40].map((d) => d * DAY)),
    { decision: "observe", reason: "insufficient-gaps" },
  );
  assert.equal(judgeCadenceStability([40 * DAY]).reason, "insufficient-gaps");
});

test("bimodal burst overdue → observed, never actionable", () => {
  // The production gap sequence replayed as visits: the detector still SEES it (the scan row
  // must stay honest about what was read) but marks it non-actionable.
  const starts = [0];
  for (const gap of REAL_CLINIC_GAP_DAYS) starts.push(starts[starts.length - 1] + gap * DAY);
  const last = starts[starts.length - 1];
  const out = detectUnmetCare(input({
    nowMs: NOW,
    visits: starts.map((offset) => ({ startMs: NOW - last + offset - 58 * DAY, careType: "clinic" })),
  }));
  assert.equal(out.candidates.length, 1, "the detection is recorded, not silently dropped");
  assert.equal(out.candidates[0].careType, "clinic");
  assert.equal(out.candidates[0].reason, "personal-cadence-overdue");
  assert.equal(out.candidates[0].decision, "observe");
  assert.equal(out.candidates[0].decisionReason, "cadence-unstable");
});

test("a stable 40±6-day cadence, overdue, stays fully actionable", () => {
  const out = detectUnmetCare(input({ visits: [
    { startMs: NOW - 230 * DAY, careType: "haircut" },
    { startMs: NOW - 190 * DAY, careType: "haircut" },
    { startMs: NOW - 156 * DAY, careType: "haircut" },
    { startMs: NOW - 110 * DAY, careType: "haircut" },
    { startMs: NOW - 70 * DAY, careType: "haircut" },
  ] }));
  assert.equal(out.candidates.length, 1);
  assert.equal(out.candidates[0].decision, "act");
  assert.equal(out.candidates[0].decisionReason, null);
  assert.equal(out.candidates[0].personalIntervalDays, 40);
});

test("three visits / two gaps overdue → observed as insufficient data", () => {
  const out = detectUnmetCare(input({ visits: [
    { startMs: NOW - 160 * DAY, careType: "dental" },
    { startMs: NOW - 130 * DAY, careType: "dental" },
    { startMs: NOW - 100 * DAY, careType: "dental" },
  ] }));
  assert.equal(out.candidates.length, 1);
  assert.equal(out.candidates[0].decision, "observe");
  assert.equal(out.candidates[0].decisionReason, "insufficient-gaps");
});

test("explicit-goal detections are unaffected by the cadence guard", () => {
  const out = detectUnmetCare(input({ intents: [{
    id: "g1", uid: "u-1", kind: "explicit_goal", statement: "歯医者を予約したい care:dental",
    provenance: { source: "user_message", evidence: "ev g1", observedAt: "2025-06-09T08:00:00.000Z" },
    confidenceTier: "explicit", confidence: 0.9, expiresAt: null, status: "active", supersedes: null,
  }] }));
  assert.equal(out.candidates.length, 1);
  assert.equal(out.candidates[0].reason, "explicit-goal-unmet");
  assert.equal(out.candidates[0].decision, "act", "the user asking for it IS the mandate — no cadence needed");
});
