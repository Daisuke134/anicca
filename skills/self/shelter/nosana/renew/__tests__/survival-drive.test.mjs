// node:test — survival-drive: pure runway math + threshold classification. No I/O.
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  DEFAULT_RUNWAY_WARNING_HOURS,
  DEFAULT_RUNWAY_CRITICAL_HOURS,
  computeRunwayHours,
  formatRunway,
  evaluateSurvivalSignal,
} from "../survival-drive.mjs";

test("computeRunwayHours divides balance by burn rate", () => {
  assert.equal(computeRunwayHours({ nosBalance: 2.4, nosPerHour: 0.1728 }), 2.4 / 0.1728);
});

test("computeRunwayHours: zero balance yields exactly zero runway, not an error", () => {
  assert.equal(computeRunwayHours({ nosBalance: 0, nosPerHour: 0.1728 }), 0);
});

test("computeRunwayHours fails closed on a non-positive nosPerHour — an unknown rate is never free forever", () => {
  assert.throws(() => computeRunwayHours({ nosBalance: 1, nosPerHour: 0 }), /positive finite number/);
  assert.throws(() => computeRunwayHours({ nosBalance: 1, nosPerHour: -1 }), /positive finite number/);
});

test("computeRunwayHours fails closed on a negative nosBalance", () => {
  assert.throws(() => computeRunwayHours({ nosBalance: -1, nosPerHour: 1 }), /non-negative finite number/);
});

test("formatRunway splits hours into days + remainder", () => {
  assert.deepEqual(formatRunway(50), { days: 2, hours: 2, totalHours: 50 });
  assert.deepEqual(formatRunway(0.5), { days: 0, hours: 0.5, totalHours: 0.5 });
});

test("formatRunway fails closed on a negative input", () => {
  assert.throws(() => formatRunway(-1), /non-negative finite number/);
});

test("evaluateSurvivalSignal: comfortable runway is nominal and does not promote earning", () => {
  const s = evaluateSurvivalSignal({ runwayHours: DEFAULT_RUNWAY_WARNING_HOURS + 1 });
  assert.equal(s.level, "nominal");
  assert.equal(s.promoteEarning, false);
});

test("evaluateSurvivalSignal: exactly at the warning threshold promotes earning (inclusive)", () => {
  const s = evaluateSurvivalSignal({ runwayHours: DEFAULT_RUNWAY_WARNING_HOURS });
  assert.equal(s.level, "warning");
  assert.equal(s.promoteEarning, true);
});

test("evaluateSurvivalSignal: exactly at the critical threshold is critical, not merely warning", () => {
  const s = evaluateSurvivalSignal({ runwayHours: DEFAULT_RUNWAY_CRITICAL_HOURS });
  assert.equal(s.level, "critical");
  assert.equal(s.promoteEarning, true);
});

test("evaluateSurvivalSignal: zero or negative runway is insolvent", () => {
  assert.equal(evaluateSurvivalSignal({ runwayHours: 0 }).level, "insolvent");
  assert.equal(evaluateSurvivalSignal({ runwayHours: -5 }).level, "insolvent");
  assert.equal(evaluateSurvivalSignal({ runwayHours: -5 }).promoteEarning, true);
});

test("evaluateSurvivalSignal: unknown/invalid runway promotes earning rather than assuming survival is fine (never throws)", () => {
  const s1 = evaluateSurvivalSignal({ runwayHours: NaN });
  const s2 = evaluateSurvivalSignal({ runwayHours: undefined });
  assert.equal(s1.level, "unknown");
  assert.equal(s1.promoteEarning, true);
  assert.equal(s2.level, "unknown");
  assert.equal(s2.promoteEarning, true);
});

test("evaluateSurvivalSignal honors custom thresholds", () => {
  const s = evaluateSurvivalSignal({ runwayHours: 10, warningHours: 20, criticalHours: 5 });
  assert.equal(s.level, "warning");
});
