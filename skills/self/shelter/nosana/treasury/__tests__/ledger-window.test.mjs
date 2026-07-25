// node:test — ledger-window.mjs: shared time-window helpers. Pure, no I/O.
import { test } from "node:test";
import assert from "node:assert/strict";
import { filterRowsByWindow, computeWindowHours, defaultLedgerWindow } from "../ledger-window.mjs";

test("filterRowsByWindow keeps rows on the boundary (inclusive both ends)", () => {
  const rows = [{ ts: 10 }, { ts: 20 }, { ts: 30 }];
  const kept = filterRowsByWindow(rows, { windowStart: 10, windowEnd: 20 });
  assert.deepEqual(kept.map((r) => r.ts), [10, 20]);
});

test("filterRowsByWindow excludes rows with a missing/non-finite ts (fail-closed)", () => {
  const rows = [{ ts: 10 }, { ts: NaN }, {}, { ts: 20 }];
  const kept = filterRowsByWindow(rows, { windowStart: 0, windowEnd: 100 });
  assert.equal(kept.length, 2);
});

test("filterRowsByWindow throws on a non-finite window boundary", () => {
  assert.throws(() => filterRowsByWindow([], { windowStart: NaN, windowEnd: 10 }), /windowStart must be a finite number/);
  assert.throws(() => filterRowsByWindow([], { windowStart: 0, windowEnd: undefined }), /windowEnd must be a finite number/);
});

test("filterRowsByWindow throws when windowEnd precedes windowStart", () => {
  assert.throws(() => filterRowsByWindow([], { windowStart: 10, windowEnd: 5 }), /windowEnd \(5\) is before windowStart \(10\)/);
});

test("computeWindowHours converts seconds to hours", () => {
  assert.equal(computeWindowHours({ windowStart: 0, windowEnd: 3600 }), 1);
  assert.equal(computeWindowHours({ windowStart: 1000, windowEnd: 1000 + 7200 }), 2);
});

test("computeWindowHours fails closed on a zero-or-negative-width window — never divide by zero silently", () => {
  assert.throws(() => computeWindowHours({ windowStart: 100, windowEnd: 100 }), /not positive-width/);
  assert.throws(() => computeWindowHours({ windowStart: 100, windowEnd: 50 }), /not positive-width/);
});

test("defaultLedgerWindow anchors to the earliest observed ts, not a fixed trailing window", () => {
  const rows = [{ ts: 1000 }, { ts: 500 }, { ts: 900 }];
  const window = defaultLedgerWindow(rows, 2000);
  assert.equal(window.windowStart, 500);
  assert.equal(window.windowEnd, 2000);
  assert.equal(window.hasData, true);
});

test("defaultLedgerWindow: empty rows -> hasData false, windowStart null (never a fabricated window)", () => {
  const window = defaultLedgerWindow([], 2000);
  assert.equal(window.hasData, false);
  assert.equal(window.windowStart, null);
  assert.equal(window.windowEnd, 2000);
});

test("defaultLedgerWindow: a single row dated exactly now is nudged back 1s rather than collapsing to zero width", () => {
  const window = defaultLedgerWindow([{ ts: 2000 }], 2000);
  assert.equal(window.windowStart, 1999);
  assert.equal(window.hasData, true);
});

test("defaultLedgerWindow throws on a non-finite nowTs", () => {
  assert.throws(() => defaultLedgerWindow([], NaN), /nowTs must be a finite number/);
});

test("defaultLedgerWindow ignores rows with a non-finite ts when finding the earliest", () => {
  const rows = [{ ts: NaN }, { ts: 700 }, {}];
  const window = defaultLedgerWindow(rows, 1000);
  assert.equal(window.windowStart, 700);
});
