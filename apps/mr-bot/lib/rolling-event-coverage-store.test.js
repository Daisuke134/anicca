"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const { buildRollingEventCoverage, isVerifiedRollingEventCoverage } = require("./rolling-event-coverage.js");
const { createRollingEventCoverageStore } = require("./rolling-event-coverage-store.js");

function snapshot() {
  return buildRollingEventCoverage({
    tenantId: "dais-local",
    timeZone: "Asia/Tokyo",
    now: "2026-08-01T16:00:00.000Z",
    resolvedDays: [],
  });
}

test("only an in-process verified coverage snapshot can reach the store", async () => {
  const store = createRollingEventCoverageStore({ async connect() { throw new Error("must not connect"); } });
  await assert.rejects(store.save(structuredClone(snapshot())), /rolling coverage snapshot invalid/i);
});

test("store inserts one tenant-bound snapshot with one client and returns the verified object", async () => {
  const value = snapshot();
  const calls = [];
  let released = 0;
  const store = createRollingEventCoverageStore({ async connect() { return {
    async query(sql, params = []) {
      calls.push({ sql, params });
      if (/INSERT INTO public\.lm_event_coverage_snapshots/.test(sql)) return { rows: [{ ...value }] };
      return { rows: [] };
    },
    release() { released += 1; },
  }; } });
  assert.equal(await store.save(value), value);
  assert.match(calls[0].sql, /BEGIN/);
  assert.match(calls[1].sql, /ON CONFLICT \(coverage_snapshot_id\) DO NOTHING/);
  assert.equal(calls[1].params[1], "dais-local");
  assert.match(calls.at(-1).sql, /COMMIT/);
  assert.equal(released, 1);
});

test("exact retry is idempotent while content collision rolls back", async () => {
  const value = snapshot();
  for (const collision of [false, true]) {
    const calls = [];
    const store = createRollingEventCoverageStore({ async connect() { return {
      async query(sql) {
        calls.push(sql);
        if (/INSERT INTO public\.lm_event_coverage_snapshots/.test(sql)) return { rows: [] };
        if (/FROM public\.lm_event_coverage_snapshots/.test(sql)) {
          return { rows: [{ ...value, counts: collision ? { ...value.counts, open: 20, covered_new: 1 } : { ...value.counts } }] };
        }
        return { rows: [] };
      }, release() {},
    }; } });
    if (collision) {
      await assert.rejects(store.save(value), /rolling coverage store unavailable/i);
      assert.match(calls.at(-1), /ROLLBACK/);
    } else {
      assert.equal(await store.save(value), value);
      assert.match(calls.at(-1), /COMMIT/);
    }
  }
});

test("store rehydrates one tenant-bound reference into a freshly verified snapshot", async () => {
  const value = snapshot();
  const hash = value.coverage_snapshot_id.replace("event-coverage:", "");
  const calls = [];
  let released = 0;
  const store = createRollingEventCoverageStore({ async connect() { return {
    async query(sql, params) { calls.push({ sql, params }); return { rows: [{ ...value }] }; },
    release() { released += 1; },
  }; } });
  const restored = await store.read(`event-coverage://dais-local/${hash}`);
  assert.equal(restored.coverage_snapshot_id, value.coverage_snapshot_id);
  assert.equal(isVerifiedRollingEventCoverage(restored), true);
  assert.notEqual(restored, value);
  assert.deepEqual(calls[0].params, [value.coverage_snapshot_id, "dais-local"]);
  assert.equal(released, 1);
  await assert.rejects(store.read(`event-coverage://other/${hash}`), /rolling coverage store unavailable/i);
  await assert.rejects(store.read("event-coverage://dais-local/not-a-hash"), /rolling coverage snapshot invalid/i);
});

test("migration upgrades 28-day counts without rewriting the historical migration", () => {
  const historical = fs.readFileSync(path.join(__dirname, "../migrations/2026-08-02-lm-event-coverage-snapshots.sql"), "utf8");
  const sql = fs.readFileSync(path.join(__dirname, "../migrations/2026-08-27-lm-event-coverage-horizon-28.sql"), "utf8");
  for (const required of [
    "lm_event_coverage_snapshots",
    "pg_constraint",
    "pg_get_constraintdef",
    "definition ~ .*>=",
    "definition ~ .*<=",
    "DROP CONSTRAINT",
    "NOT VALID",
    "CONSTRAINT lm_event_coverage_horizon_days_28_check",
    "CONSTRAINT lm_event_coverage_days_length_28_check",
    "CONSTRAINT lm_event_coverage_window_end_28_check",
    "CONSTRAINT lm_event_coverage_open_count_28_check",
    "CONSTRAINT lm_event_coverage_covered_existing_count_28_check",
    "CONSTRAINT lm_event_coverage_covered_new_count_28_check",
    "CONSTRAINT lm_event_coverage_unavailable_count_28_check",
    "CONSTRAINT lm_event_coverage_counts_sum_28_check",
    "horizon_days = 28",
    "window_start_date \\+ 27",
    "jsonb_array_length\\(days\\) = 28",
    "open_count \\+ covered_existing_count \\+ covered_new_count \\+ unavailable_count = 28",
  ]) assert.match(sql, new RegExp(required, "i"));
  for (const count of ["open_count", "covered_existing_count", "covered_new_count", "unavailable_count"]) {
    assert.match(sql, new RegExp(`definition ~ '${count}\\.\\*>=\\.\\*0\\.\\*${count}\\.\\*<=\\.\\*21'`, "i"));
  }
  assert.doesNotMatch(sql, /email|phone|password|cookie|guest_key|event_title|location|attendee/i);
  assert.match(historical, /horizon_days = 21/i);
  assert.doesNotMatch(historical, /horizon_days = 28|jsonb_array_length\\(days\\) = 28/i);
  assert.match(historical, /lm_event_coverage_current|immutable|ENABLE ROW LEVEL SECURITY/i);
  assert.doesNotMatch(sql, /DROP\s+(?:TABLE|VIEW)|DISABLE\s+ROW LEVEL SECURITY/i);
});
