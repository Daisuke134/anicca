"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

const {
  buildRollingEventCoverage,
  isVerifiedRollingEventCoverage,
} = require("./rolling-event-coverage.js");

const BASE = Object.freeze({
  tenantId: "dais-local",
  timeZone: "Asia/Tokyo",
  now: "2026-08-01T16:00:00.000Z",
  resolvedDays: [],
});

test("JST snapshot contains today through local day plus 20 exactly once", () => {
  const snapshot = buildRollingEventCoverage(BASE);
  assert.equal(snapshot.window_start_date, "2026-08-02");
  assert.equal(snapshot.window_end_date, "2026-08-22");
  assert.equal(snapshot.horizon_days, 21);
  assert.equal(snapshot.days.length, 21);
  assert.equal(new Set(snapshot.days.map((day) => day.date)).size, 21);
  assert.deepEqual(snapshot.days[0], { date: "2026-08-02", status: "open", evidence_refs: [] });
  assert.deepEqual(snapshot.days.at(-1), { date: "2026-08-22", status: "open", evidence_refs: [] });
  assert.deepEqual(snapshot.counts, { open: 21, covered_existing: 0, covered_new: 0, unavailable: 0 });
  assert.match(snapshot.coverage_snapshot_id, /^event-coverage:[0-9a-f]{64}$/);
  assert.equal(Object.isFrozen(snapshot), true);
  assert.equal(isVerifiedRollingEventCoverage(snapshot), true);
  assert.equal(isVerifiedRollingEventCoverage(structuredClone(snapshot)), false);
});

test("New York DST boundary still produces 21 consecutive local calendar dates", () => {
  const snapshot = buildRollingEventCoverage({
    ...BASE,
    timeZone: "America/New_York",
    now: "2026-03-08T04:30:00.000Z",
  });
  assert.equal(snapshot.window_start_date, "2026-03-07");
  assert.equal(snapshot.window_end_date, "2026-03-27");
  assert.equal(snapshot.days.length, 21);
  assert.deepEqual(snapshot.days.slice(0, 4).map((day) => day.date), [
    "2026-03-07", "2026-03-08", "2026-03-09", "2026-03-10",
  ]);
});

test("the next local day drops yesterday and appends one new open day", () => {
  const first = buildRollingEventCoverage(BASE);
  const next = buildRollingEventCoverage({ ...BASE, now: "2026-08-02T16:00:00.000Z" });
  assert.equal(next.window_start_date, "2026-08-03");
  assert.equal(next.window_end_date, "2026-08-23");
  assert.equal(next.days.some((day) => day.date === "2026-08-02"), false);
  assert.deepEqual(next.days.at(-1), { date: "2026-08-23", status: "open", evidence_refs: [] });
  assert.notEqual(first.coverage_snapshot_id, next.coverage_snapshot_id);
});

test("only supplied evidence resolves days and counts remain exact", () => {
  const resolvedDays = [
    { date: "2026-08-02", status: "covered_existing", evidence_refs: ["evidence://coverage/existing/" + "a".repeat(64)] },
    { date: "2026-08-03", status: "covered_new", evidence_refs: ["provider-receipt://coverage/new/" + "b".repeat(64)] },
    { date: "2026-08-04", status: "unavailable", evidence_refs: ["evidence://coverage/conflict/" + "c".repeat(64)] },
  ];
  const snapshot = buildRollingEventCoverage({ ...BASE, resolvedDays });
  assert.deepEqual(snapshot.days.slice(0, 4), [
    resolvedDays[0], resolvedDays[1], resolvedDays[2],
    { date: "2026-08-05", status: "open", evidence_refs: [] },
  ]);
  assert.deepEqual(snapshot.counts, { open: 18, covered_existing: 1, covered_new: 1, unavailable: 1 });
  assert.doesNotMatch(JSON.stringify(snapshot), /@|password|cookie|guest.?key/i);
});

test("invalid timezone, duplicate or out-of-window resolution, open claims, missing evidence, and secrets fail closed", () => {
  const valid = { date: "2026-08-02", status: "covered_new", evidence_refs: ["evidence://coverage/new/" + "d".repeat(64)] };
  const cases = [
    { ...BASE, timeZone: "Mars/Olympus" },
    { ...BASE, resolvedDays: [valid, { ...valid, status: "unavailable" }] },
    { ...BASE, resolvedDays: [{ ...valid, date: "2026-08-23" }] },
    { ...BASE, resolvedDays: [{ ...valid, status: "open" }] },
    { ...BASE, resolvedDays: [{ ...valid, evidence_refs: [] }] },
    { ...BASE, resolvedDays: [{ ...valid, evidence_refs: ["evidence://person@example.com/secret"] }] },
  ];
  for (const input of cases) assert.throws(() => buildRollingEventCoverage(input), /rolling event coverage invalid/i);
});
