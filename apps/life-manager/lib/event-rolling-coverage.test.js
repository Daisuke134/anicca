"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const { buildRollingEventCoverage } = require("./event-rolling-coverage.js");

const BEFORE_MIDNIGHT = "2026-08-01T14:59:59.000Z";
const AFTER_MIDNIGHT = "2026-08-01T15:00:00.000Z";

test("Tokyoの今日から20日後までexact 21日を毎回生成する", () => {
  const before = buildRollingEventCoverage({ tenantId: "dais-local", now: BEFORE_MIDNIGHT, observations: [] });
  assert.equal(before.window_start, "2026-08-01");
  assert.equal(before.window_end, "2026-08-21");
  assert.equal(before.days.length, 21);
  assert.equal(before.open_count, 21);
  assert.equal(before.complete, false);

  const after = buildRollingEventCoverage({ tenantId: "dais-local", now: AFTER_MIDNIGHT, observations: [] });
  assert.equal(after.window_start, "2026-08-02");
  assert.equal(after.window_end, "2026-08-22");
  assert.equal(after.days.some(({ date }) => date === "2026-08-01"), false);
  assert.equal(after.days.at(-1).date, "2026-08-22");
});

test("current証拠だけを3 statusへ置き、残りをopenへ導出する", () => {
  const actual = buildRollingEventCoverage({
    tenantId: "dais-local", now: AFTER_MIDNIGHT,
    observations: [
      { date: "2026-08-02", status: "covered_existing", evidence_ref: "calendar-event://tokyo/existing" },
      { date: "2026-08-03", status: "covered_new", evidence_ref: "provider-receipt://luma/new" },
      { date: "2026-08-04", status: "unavailable", evidence_ref: "calendar-conflict://all-calendars/day" },
      { date: "2026-09-01", status: "covered_existing", evidence_ref: "calendar-event://outside/window" },
    ],
  });
  assert.deepEqual(actual.counts, { covered_existing: 1, covered_new: 1, unavailable: 1, open: 18 });
  assert.deepEqual(actual.days.slice(0, 4).map(({ status }) => status), [
    "covered_existing", "covered_new", "unavailable", "open",
  ]);
  assert.equal(actual.days[3].evidence_ref, null);
});

test("cancel後にobservationが消えれば次回runで自動的にopenへ戻る", () => {
  const covered = buildRollingEventCoverage({ tenantId: "dais-local", now: AFTER_MIDNIGHT, observations: [
    { date: "2026-08-05", status: "covered_existing", evidence_ref: "calendar-event://tokyo/will-cancel" },
  ] });
  const recalculated = buildRollingEventCoverage({ tenantId: "dais-local", now: AFTER_MIDNIGHT, observations: [] });
  assert.equal(covered.days.find(({ date }) => date === "2026-08-05").status, "covered_existing");
  assert.equal(recalculated.days.find(({ date }) => date === "2026-08-05").status, "open");
});

test("21日すべてにcurrent evidenceがある時だけcompleteになる", () => {
  const empty = buildRollingEventCoverage({ tenantId: "dais-local", now: "2026-12-20T00:00:00Z", observations: [] });
  const observations = empty.days.map(({ date }, index) => ({
    date,
    status: index % 3 === 0 ? "covered_existing" : index % 3 === 1 ? "covered_new" : "unavailable",
    evidence_ref: `coverage-proof://day/${date}`,
  }));
  const complete = buildRollingEventCoverage({ tenantId: "dais-local", now: "2026-12-20T00:00:00Z", observations });
  assert.equal(complete.days.length, 21);
  assert.equal(complete.open_count, 0);
  assert.equal(complete.complete, true);
  assert.equal(complete.window_end, "2027-01-09");
});

test("explicit open、重複日、未知status、証拠なし、暗黙nowを拒否する", () => {
  const base = { tenantId: "dais-local", now: AFTER_MIDNIGHT };
  assert.throws(() => buildRollingEventCoverage({ ...base, observations: [{ date: "2026-08-02", status: "open", evidence_ref: "proof://x/y" }] }), /observation/i);
  assert.throws(() => buildRollingEventCoverage({ ...base, observations: [
    { date: "2026-08-02", status: "covered_new", evidence_ref: "proof://x/a" },
    { date: "2026-08-02", status: "covered_new", evidence_ref: "proof://x/b" },
  ] }), /duplicate/i);
  assert.throws(() => buildRollingEventCoverage({ ...base, observations: [{ date: "2026-08-02", status: "done", evidence_ref: "proof://x/y" }] }), /observation/i);
  assert.throws(() => buildRollingEventCoverage({ ...base, observations: [{ date: "2026-08-02", status: "covered_new" }] }), /evidence/i);
  assert.throws(() => buildRollingEventCoverage({ tenantId: "dais-local", observations: [] }), /now/i);
});
