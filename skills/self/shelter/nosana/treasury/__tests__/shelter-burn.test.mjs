// node:test — shelter-burn.mjs: USD burn-rate math over the CORRECTION-AWARE ledger view. Pure, no
// I/O. Uses the REAL rows (and the REAL correction row) from today's live shelter-cost.jsonl
// (~/.hermes/state/shelter-cost.jsonl, 2026-07-25) to prove the no-double-count property against
// the actual incident data, not a synthetic stand-in.
import { test } from "node:test";
import assert from "node:assert/strict";
import { sumResolvedShelterCostUsd, computeBurnRateUsdPerHour } from "../shelter-burn.mjs";
import { resolveShelterCostEntries } from "../../../../spawn/lib/shelter-cost-ledger.js";

// Verbatim from ~/.hermes/state/shelter-cost.jsonl, read 2026-07-25 — the real CLI stdout-parsing
// incident: the first row recorded the PAYER WALLET address as jobAddress; the correction row fixes
// it to the real posted job's address without touching the original row (append-only).
const REAL_RAW_ROWS = [
  { ts: 1784956463.817, settledLeaseCostUsd: 0.01199, jobAddress: "F5SYUC4f5QULbEgSYb1DFCBfi74AnWE3ZaXAhqXwhZ5T" },
  {
    ts: 1784957544.282,
    correction: true,
    correctsTs: 1784956463.817,
    correctedField: "jobAddress",
    correctedJobAddress: "FHAjMnM1q3p5c5qCeFRjZLYEo12FUBesFPW8zvG5heAC",
    reason: "original row recorded the payer wallet address instead of the real posted job address",
  },
  { ts: 1784961735.332, settledLeaseCostUsd: 0.01199, jobAddress: "CMZ4B2jvqx63ULMNQ4o1jjjrhRUnktQBHbtWWigFUHaS" },
  { ts: 1784963806.997, settledLeaseCostUsd: 0.01199, jobAddress: "4JEk92draTopQVg3L6uw4U6GGpHBsofatuTaixW1hQYe" },
  { ts: 1784964765.77, settledLeaseCostUsd: 0.01199, jobAddress: "HaAxki9ZjZ5Kk3kPbELENrn1mHDaeq3pyLz48HHqCq5K" },
  { ts: 1784965497.943, settledLeaseCostUsd: 0.010743158532333123, jobAddress: "HaAxki9ZjZ5Kk3kPbELENrn1mHDaeq3pyLz48HHqCq5K" },
  { ts: 1784966427.288, settledLeaseCostUsd: 0.010811856598094603, jobAddress: "HaAxki9ZjZ5Kk3kPbELENrn1mHDaeq3pyLz48HHqCq5K" },
];
const REAL_TOTAL_USD = 0.01199 * 4 + 0.010743158532333123 + 0.010811856598094603;

test("sumResolvedShelterCostUsd against the REAL 2026-07-25 correction row: 6 rows resolve (correction excluded), total matches the real settled spend exactly", () => {
  const resolved = resolveShelterCostEntries(REAL_RAW_ROWS);
  assert.equal(resolved.length, 6); // the correction row itself never becomes a 7th spend row
  const summary = sumResolvedShelterCostUsd(resolved, { windowStart: 0, windowEnd: 1784966427.288 });
  assert.equal(summary.eventCount, 6);
  assert.ok(Math.abs(summary.totalCostUsd - REAL_TOTAL_USD) < 1e-9);
});

test("REGRESSION: summing the RAW (unresolved) rows would corrupt the total — proves resolveShelterCostEntries is load-bearing", () => {
  // The correction row has no settledLeaseCostUsd of its own; summing raw rows naively would
  // introduce a NaN. This test documents exactly why sumResolvedShelterCostUsd's own header insists
  // callers pass the RESOLVED view, never the raw one.
  const total = REAL_RAW_ROWS.reduce((s, r) => s + Number(r.settledLeaseCostUsd), 0);
  assert.ok(Number.isNaN(total));
});

test("sumResolvedShelterCostUsd restricts to the given window", () => {
  const resolved = resolveShelterCostEntries(REAL_RAW_ROWS);
  const summary = sumResolvedShelterCostUsd(resolved, { windowStart: 1784964000, windowEnd: 1784966427.288 });
  assert.equal(summary.eventCount, 3); // only the last 3 real rows fall in this window
});

test("sumResolvedShelterCostUsd fails closed on a row with a non-finite settledLeaseCostUsd", () => {
  const rows = [{ ts: 1, settledLeaseCostUsd: "not-a-number" }];
  assert.throws(() => sumResolvedShelterCostUsd(rows, { windowStart: 0, windowEnd: 10 }), /invalid settledLeaseCostUsd/);
});

test("sumResolvedShelterCostUsd fails closed on a negative settledLeaseCostUsd", () => {
  const rows = [{ ts: 1, settledLeaseCostUsd: -0.5 }];
  assert.throws(() => sumResolvedShelterCostUsd(rows, { windowStart: 0, windowEnd: 10 }), /invalid settledLeaseCostUsd/);
});

test("sumResolvedShelterCostUsd: an empty window (no rows) is a real, honest $0, with eventCount 0", () => {
  const summary = sumResolvedShelterCostUsd([], { windowStart: 0, windowEnd: 10 });
  assert.equal(summary.totalCostUsd, 0);
  assert.equal(summary.eventCount, 0);
});

test("computeBurnRateUsdPerHour divides the window total by the window's real hour-width", () => {
  const rate = computeBurnRateUsdPerHour({ totalCostUsd: 1, eventCount: 1, windowStart: 0, windowEnd: 3600 * 2 });
  assert.equal(rate.burnUsdPerHour, 0.5);
  assert.equal(rate.windowHours, 2);
  assert.equal(rate.noData, false);
});

test("computeBurnRateUsdPerHour flags noData when eventCount is 0 — a real $0 window is NOT the same fact as 'no data'", () => {
  const rate = computeBurnRateUsdPerHour({ totalCostUsd: 0, eventCount: 0, windowStart: 0, windowEnd: 3600 });
  assert.equal(rate.burnUsdPerHour, 0);
  assert.equal(rate.noData, true);
});

test("computeBurnRateUsdPerHour fails closed on an invalid totalCostUsd", () => {
  assert.throws(() => computeBurnRateUsdPerHour({ totalCostUsd: NaN, eventCount: 1, windowStart: 0, windowEnd: 10 }), /must be a non-negative finite number/);
});

test("using the REAL correction row end to end: burn rate over the real observed window", () => {
  const resolved = resolveShelterCostEntries(REAL_RAW_ROWS);
  const windowStart = Math.min(...resolved.map((r) => r.ts));
  const windowEnd = Math.max(...resolved.map((r) => r.ts));
  const summary = sumResolvedShelterCostUsd(resolved, { windowStart, windowEnd });
  const rate = computeBurnRateUsdPerHour(summary);
  // Real observed span 2026-07-25: ~2.77 hours across the real 6 resolved lease events.
  assert.ok(rate.windowHours > 2.7 && rate.windowHours < 2.8, `expected ~2.77h, got ${rate.windowHours}`);
  assert.ok(rate.burnUsdPerHour > 0);
});
