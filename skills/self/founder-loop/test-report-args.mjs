// test-report-args.mjs — RED (Phase 2a, feature claude-p-loop-verification).
// PROP-LV-007 / REQ-LV-018 — founder_report_args(prev_earn, total_earn, status) -> {result,
// earned_usdc, evidence}. Pure: deterministically builds the loop-report.sh 3rd/4th/5th args from
// STATE.md's two numbers + STATUS string. Does NOT call loop-report.sh itself (that wiring is a
// Tier2/3 concern inside founder-loop.sh) and does NOT touch record-earn.mjs (INV-H2 unchanged).
//
// report-args.mjs does not exist yet -> import fails -> RED.
import { test } from "node:test";
import assert from "node:assert/strict";
import { founderReportArgs } from "../founder-loop/report-args.mjs";

const WALLET = "0x810f6d61f7606deee2657d3083e150a222bc29c5";

test("founderReportArgs: prev=0, total=5.0 -> success, earned=5.0, evidence has increase+wallet", () => {
  const r = founderReportArgs(0, 5.0, "EARNING — real external USDC received; keep growing");
  assert.equal(r.result, "success");
  assert.equal(r.earned_usdc, 5.0);
  assert.match(r.evidence, /5(\.0)?/);
  assert.match(r.evidence, new RegExp(WALLET));
});

test("founderReportArgs: prev=5.0, total=5.0 (no increment) -> queue-empty, earned=0, evidence='none: <status>'", () => {
  const status = "NO realised external earn yet — bottleneck is DEMAND/LISTING/PRICING, not code";
  const r = founderReportArgs(5.0, 5.0, status);
  assert.equal(r.result, "queue-empty");
  assert.equal(r.earned_usdc, 0);
  assert.equal(r.evidence, `none: ${status}`);
});

test("founderReportArgs: total > prev by a fraction -> success, earned_usdc is the exact increment (not the total)", () => {
  const r = founderReportArgs(10.25, 12.75, "EARNING — real external USDC received; keep growing");
  assert.equal(r.result, "success");
  assert.equal(r.earned_usdc, 2.5);
});

test("founderReportArgs: total < prev (should not happen, defensive) -> earned_usdc clamped to 0, not negative", () => {
  const status = "LEDGER UNREADABLE — fail-safe; a real total cannot be summed, recompute before trusting";
  const r = founderReportArgs(10.0, 3.0, status);
  assert.equal(r.result, "queue-empty");
  assert.equal(r.earned_usdc, 0);
  assert.ok(r.earned_usdc >= 0, "earned_usdc must never go negative");
});
