// node:test — revenue.mjs: USD external-revenue math over already-classified rows. Pure, no I/O.
import { test } from "node:test";
import assert from "node:assert/strict";
import { sumExternalRevenueUsd, computeRevenueRateUsdPerHour } from "../revenue.mjs";
import { classifyRevenueRows, buildSelfWalletSet } from "../self-pay.mjs";

test("sumExternalRevenueUsd: zero revenue events — the honest zero, not a division fudge", () => {
  const summary = sumExternalRevenueUsd([], { windowStart: 0, windowEnd: 10 });
  assert.equal(summary.totalExternalRevenueUsd, 0);
  assert.equal(summary.totalEventCount, 0);
  assert.equal(summary.externalEventCount, 0);
});

test("sumExternalRevenueUsd separates self-pay from external and never mixes the totals — INV-7", () => {
  const set = buildSelfWalletSet();
  const rows = classifyRevenueRows(
    [
      { ts: 1, amountUsd: 0.70, from: "0x3eccad24794ca298d25378e9902a251322ea8749" }, // self-pay
      { ts: 2, amountUsd: 5.00, from: "0x000000000000000000000000000000deadbeef" }, // external
    ],
    set,
  );
  const summary = sumExternalRevenueUsd(rows, { windowStart: 0, windowEnd: 10 });
  assert.equal(summary.totalExternalRevenueUsd, 5.0);
  assert.equal(summary.totalSelfPayUsd, 0.70);
  assert.equal(summary.externalEventCount, 1);
  assert.equal(summary.totalEventCount, 2);
});

test("REGRESSION: the real ground-truth scenario — every observed inflow is self-pay, external revenue is exactly $0", () => {
  const set = buildSelfWalletSet({ solanaSelfWallets: ["F5SYUC4f5QULbEgSYb1DFCBfi74AnWE3ZaXAhqXwhZ5T"] });
  const rows = classifyRevenueRows(
    [{ ts: 1784956420.145, amountUsd: 0.7011866549524, from: "F5SYUC4f5QULbEgSYb1DFCBfi74AnWE3ZaXAhqXwhZ5T" }],
    set,
  );
  const summary = sumExternalRevenueUsd(rows, { windowStart: 0, windowEnd: 1784971215 });
  assert.equal(summary.totalExternalRevenueUsd, 0);
  assert.ok(summary.totalSelfPayUsd > 0); // it WAS an inflow, just correctly excluded
});

test("sumExternalRevenueUsd fails closed on an invalid amountUsd on an in-window row", () => {
  const rows = [{ ts: 1, amountUsd: NaN, from: "0xabc", external: true }];
  assert.throws(() => sumExternalRevenueUsd(rows, { windowStart: 0, windowEnd: 10 }), /invalid amountUsd/);
});

test("computeRevenueRateUsdPerHour flags noData when there were no revenue events at all", () => {
  const rate = computeRevenueRateUsdPerHour({ totalExternalRevenueUsd: 0, totalEventCount: 0, windowStart: 0, windowEnd: 3600 });
  assert.equal(rate.revenueUsdPerHour, 0);
  assert.equal(rate.noData, true);
});

test("computeRevenueRateUsdPerHour computes a real nonzero rate when external revenue exists", () => {
  const rate = computeRevenueRateUsdPerHour({ totalExternalRevenueUsd: 10, totalEventCount: 2, windowStart: 0, windowEnd: 3600 * 5 });
  assert.equal(rate.revenueUsdPerHour, 2);
  assert.equal(rate.noData, false);
});

test("computeRevenueRateUsdPerHour fails closed on an invalid totalExternalRevenueUsd", () => {
  assert.throws(
    () => computeRevenueRateUsdPerHour({ totalExternalRevenueUsd: -1, totalEventCount: 1, windowStart: 0, windowEnd: 10 }),
    /must be a non-negative finite number/,
  );
});
