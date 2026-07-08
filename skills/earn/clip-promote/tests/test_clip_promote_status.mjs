// test_clip_promote_status.mjs — RED (Phase 2a, feature claude-p-loop-verification).
// PROP-LV-026 / REQ-LV-120 — clip_promote_status(payout_rows, today_jst_date) -> {"status": ...}.
// Cadence-Contract-independent status for clip-promote (campaign-dependent posting frequency,
// REQ-LV-100 explicitly excludes it from the 7-loop Cadence Contract). Looks ONLY at record-payout.mjs's
// status:"recorded" lines (task:"promote.fun clip payout") for a JST-today ts — never calls cadence_met.
//
// clip-promote-status.mjs does not exist yet -> import fails -> RED.
import { test } from "node:test";
import assert from "node:assert/strict";
import { clipPromoteStatus } from "../clip-promote-status.mjs";

// 2026-07-08T10:00:00+09:00 == 2026-07-08T01:00:00Z
const TODAY_JST = "2026-07-08";
const TS_TODAY_JST_MORNING = Math.floor(Date.UTC(2026, 6, 8, 1, 0, 0) / 1000);   // JST 10:00 on the 8th
const TS_YESTERDAY_JST = Math.floor(Date.UTC(2026, 6, 6, 20, 0, 0) / 1000);      // JST 05:00 on the 7th
// UTC-late-night edge: UTC 2026-07-08T16:00:00Z == JST 2026-07-09T01:00:00 (next JST day)
const TS_UTC_LATE_CROSSES_TO_NEXT_JST_DAY = Math.floor(Date.UTC(2026, 6, 8, 16, 0, 0) / 1000);

test("clipPromoteStatus: a recorded payout row today (JST) -> payout-today", () => {
  const rows = [{ status: "recorded", task: "promote.fun clip payout", ts: TS_TODAY_JST_MORNING, earn_usdc: 0.5 }];
  assert.deepEqual(clipPromoteStatus(rows, TODAY_JST), { status: "payout-today" });
});

test("clipPromoteStatus: no rows -> no-payout-today", () => {
  assert.deepEqual(clipPromoteStatus([], TODAY_JST), { status: "no-payout-today" });
});

test("clipPromoteStatus: only yesterday's row -> no-payout-today", () => {
  const rows = [{ status: "recorded", task: "promote.fun clip payout", ts: TS_YESTERDAY_JST, earn_usdc: 0.3 }];
  assert.deepEqual(clipPromoteStatus(rows, TODAY_JST), { status: "no-payout-today" });
});

test("clipPromoteStatus: non-recorded status (e.g. 'rejected'/'duplicate') rows are ignored", () => {
  const rows = [{ status: "duplicate", task: "promote.fun clip payout", ts: TS_TODAY_JST_MORNING, earn_usdc: 0 }];
  assert.deepEqual(clipPromoteStatus(rows, TODAY_JST), { status: "no-payout-today" });
});

test("clipPromoteStatus: JST day-boundary — a UTC-late ts that is actually JST-tomorrow does NOT count for today", () => {
  const rows = [{ status: "recorded", task: "promote.fun clip payout", ts: TS_UTC_LATE_CROSSES_TO_NEXT_JST_DAY, earn_usdc: 0.2 }];
  assert.deepEqual(clipPromoteStatus(rows, TODAY_JST), { status: "no-payout-today" });
  assert.deepEqual(clipPromoteStatus(rows, "2026-07-09"), { status: "payout-today" });
});

test("clipPromoteStatus: does NOT call cadence_met (campaign-dependent, no Cadence Contract) — mixed rows, only today's recorded row matters", () => {
  const rows = [
    { status: "recorded", task: "promote.fun clip payout", ts: TS_YESTERDAY_JST, earn_usdc: 0.1 },
    { status: "recorded", task: "promote.fun clip payout", ts: TS_TODAY_JST_MORNING, earn_usdc: 0.5 },
  ];
  assert.deepEqual(clipPromoteStatus(rows, TODAY_JST), { status: "payout-today" });
});
