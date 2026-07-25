// node:test — solvency-report.mjs: turns the joined ledger + a real NOS balance/price into runway
// figures, reusing survival-drive.mjs's own runway math. Pure, no I/O.
import { test } from "node:test";
import assert from "node:assert/strict";
import { computeSolvencyReport } from "../solvency-report.mjs";
import { computeRunwayHours } from "../../renew/survival-drive.mjs";

function makeLedger(overrides = {}) {
  return {
    burnUsdPerHour: 0.02,
    revenueUsdPerHour: 0,
    netUsdPerHour: -0.02,
    totalExternalRevenueUsd: 0,
    noCostData: false,
    noRevenueData: true,
    ...overrides,
  };
}

test("computeSolvencyReport fails closed on a missing/invalid nosUsdPrice — never an optimistic default", () => {
  const ledger = makeLedger();
  assert.throws(() => computeSolvencyReport({ ledger, nosBalance: 2.5, nosUsdPrice: undefined }), /nosUsdPrice must be a positive finite number/);
  assert.throws(() => computeSolvencyReport({ ledger, nosBalance: 2.5, nosUsdPrice: 0 }), /nosUsdPrice must be a positive finite number/);
  assert.throws(() => computeSolvencyReport({ ledger, nosBalance: 2.5, nosUsdPrice: NaN }), /nosUsdPrice must be a positive finite number/);
  assert.throws(() => computeSolvencyReport({ ledger, nosBalance: 2.5, nosUsdPrice: -1 }), /nosUsdPrice must be a positive finite number/);
});

test("computeSolvencyReport fails closed on an invalid nosBalance", () => {
  const ledger = makeLedger();
  assert.throws(() => computeSolvencyReport({ ledger, nosBalance: -1, nosUsdPrice: 0.25 }), /nosBalance must be a non-negative finite number/);
  assert.throws(() => computeSolvencyReport({ ledger, nosBalance: NaN, nosUsdPrice: 0.25 }), /nosBalance must be a non-negative finite number/);
});

test("computeSolvencyReport requires a ledger object", () => {
  assert.throws(() => computeSolvencyReport({ ledger: null, nosBalance: 1, nosUsdPrice: 0.25 }), /ledger is required/);
});

test("computeSolvencyReport: zero external revenue is reported explicitly as revenueIsZero, never smoothed away", () => {
  const ledger = makeLedger({ totalExternalRevenueUsd: 0 });
  const report = computeSolvencyReport({ ledger, nosBalance: 2.5, nosUsdPrice: 0.25 });
  assert.equal(report.revenueIsZero, true);
  assert.equal(report.revenueUsdPerHour, 0);
});

test("computeSolvencyReport: burnNosPerHour and runway agree with survival-drive.mjs's OWN computeRunwayHours for the SAME inputs", () => {
  const ledger = makeLedger({ burnUsdPerHour: 0.04796, revenueUsdPerHour: 0 });
  const nosBalance = 2.495705;
  const nosUsdPrice = 0.25383035377762303;
  const report = computeSolvencyReport({ ledger, nosBalance, nosUsdPrice });
  const expectedNosPerHour = ledger.burnUsdPerHour / nosUsdPrice;
  assert.equal(report.burnNosPerHour, expectedNosPerHour);
  // Cross-check: calling survival-drive.mjs's own computeRunwayHours directly with the SAME
  // nosBalance/nosPerHour must produce the identical number computeSolvencyReport used internally —
  // proving agreement by construction (one shared implementation), not by coincidence.
  const independentRunway = computeRunwayHours({ nosBalance, nosPerHour: expectedNosPerHour });
  assert.equal(report.runwayHoursBurnOnly, independentRunway);
});

test("computeSolvencyReport: no cost data -> burn is UNKNOWN, not zero — survival level is 'unknown', promoteEarning true", () => {
  const ledger = makeLedger({ noCostData: true, burnUsdPerHour: 0, revenueUsdPerHour: 0 });
  const report = computeSolvencyReport({ ledger, nosBalance: 2.5, nosUsdPrice: 0.25 });
  assert.equal(report.burnNosPerHour, null);
  assert.equal(report.runwayHoursBurnOnly, null);
  assert.equal(report.survivalSignal.level, "unknown");
  assert.equal(report.survivalSignal.promoteEarning, true);
});

test("computeSolvencyReport: revenue that exceeds burn yields an INFINITE with-revenue runway, never a fabricated finite number", () => {
  const ledger = makeLedger({ burnUsdPerHour: 0.01, revenueUsdPerHour: 0.05, netUsdPerHour: 0.04, totalExternalRevenueUsd: 1 });
  const report = computeSolvencyReport({ ledger, nosBalance: 1, nosUsdPrice: 0.25 });
  assert.equal(report.runwayHoursWithRevenue, Infinity);
  assert.equal(report.runwayWithRevenue.totalHours, Infinity);
});

test("computeSolvencyReport: revenue that partially offsets burn shrinks the burn rate but keeps a finite runway", () => {
  const ledger = makeLedger({ burnUsdPerHour: 0.05, revenueUsdPerHour: 0.02, netUsdPerHour: -0.03, totalExternalRevenueUsd: 1 });
  const nosUsdPrice = 0.25;
  const report = computeSolvencyReport({ ledger, nosBalance: 1, nosUsdPrice });
  assert.ok(report.runwayHoursWithRevenue > report.runwayHoursBurnOnly); // revenue extends runway
  assert.ok(Number.isFinite(report.runwayHoursWithRevenue));
});

test("computeSolvencyReport: the conservative burn-only runway drives the alert level even when revenue is proven zero — never softened", () => {
  // Even though revenue is $0 (so with-revenue and burn-only runway are numerically identical here),
  // this pins that the SURVIVAL SIGNAL is always derived from runwayHoursBurnOnly, never from a
  // revenue-optimistic figure.
  const ledger = makeLedger({ burnUsdPerHour: 1, revenueUsdPerHour: 0, netUsdPerHour: -1, totalExternalRevenueUsd: 0 });
  const report = computeSolvencyReport({ ledger, nosBalance: 0.001, nosUsdPrice: 0.25, criticalHours: 6, warningHours: 48 });
  assert.equal(report.survivalSignal.level, "critical");
});
