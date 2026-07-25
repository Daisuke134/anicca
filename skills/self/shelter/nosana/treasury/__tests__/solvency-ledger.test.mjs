// node:test — solvency-ledger.mjs: the deterministic join of revenue + shelter-cost events over a
// shared window. Pure, no I/O. Uses the REAL 2026-07-25 correction row + realistic revenue rows.
import { test } from "node:test";
import assert from "node:assert/strict";
import { buildSolvencyLedger } from "../solvency-ledger.mjs";
import { resolveShelterCostEntries } from "../../../../spawn/lib/shelter-cost-ledger.js";
import { classifyRevenueRows, buildSelfWalletSet } from "../self-pay.mjs";

const REAL_RAW_COST_ROWS = [
  { ts: 1784956463.817, settledLeaseCostUsd: 0.01199, jobAddress: "F5SYUC4f5QULbEgSYb1DFCBfi74AnWE3ZaXAhqXwhZ5T" },
  { ts: 1784957544.282, correction: true, correctsTs: 1784956463.817, correctedField: "jobAddress", correctedJobAddress: "FHAjMnM1q3p5c5qCeFRjZLYEo12FUBesFPW8zvG5heAC", reason: "payer-wallet-as-jobAddress bug" },
  { ts: 1784961735.332, settledLeaseCostUsd: 0.01199, jobAddress: "CMZ4B2jvqx63ULMNQ4o1jjjrhRUnktQBHbtWWigFUHaS" },
];

test("buildSolvencyLedger joins cost + revenue events into one chronological view, preserving each row's own real fields", () => {
  const costRowsResolved = resolveShelterCostEntries(REAL_RAW_COST_ROWS);
  const selfWalletSet = buildSelfWalletSet({ solanaSelfWallets: ["F5SYUC4f5QULbEgSYb1DFCBfi74AnWE3ZaXAhqXwhZ5T"] });
  const revenueRowsClassified = classifyRevenueRows(
    [
      { ts: 1784956420, amountUsd: 0.70, from: "F5SYUC4f5QULbEgSYb1DFCBfi74AnWE3ZaXAhqXwhZ5T" }, // self-pay, inside the window
      { ts: 1784960000, amountUsd: 3.5, from: "0x000000000000000000000000000000deadbeef", txSignature: "sig123" }, // external, real
    ],
    selfWalletSet,
  );
  const ledger = buildSolvencyLedger({
    costRowsResolved,
    revenueRowsClassified,
    windowStart: 1784956000,
    windowEnd: 1784962000,
  });

  assert.equal(ledger.events.length, 4); // 2 cost rows + 2 revenue rows (1 self-pay, 1 external), all in window
  assert.deepEqual(
    ledger.events.map((e) => e.type),
    ["revenue", "cost", "revenue", "cost"], // chronological by ts
  );
  const costEvent = ledger.events.find((e) => e.ts === 1784956463.817);
  assert.equal(costEvent.jobAddress, "FHAjMnM1q3p5c5qCeFRjZLYEo12FUBesFPW8zvG5heAC"); // corrected address preserved
  assert.equal(costEvent.amountUsd, -0.01199); // cost is signed negative
  const externalRevenueEvent = ledger.events.find((e) => e.type === "revenue" && e.external);
  assert.equal(externalRevenueEvent.amountUsd, 3.5);
  assert.equal(externalRevenueEvent.txSignature, "sig123"); // real field preserved, no synthetic key invented
  const selfPayRevenueEvent = ledger.events.find((e) => e.type === "revenue" && !e.external);
  assert.equal(selfPayRevenueEvent.excluded, true);
  assert.equal(selfPayRevenueEvent.amountUsd, 0); // excluded from the signed total (INV-7)
  assert.equal(selfPayRevenueEvent.rawAmountUsd, 0.70); // but the real figure is retained for audit

  assert.ok(Math.abs(ledger.totalCostUsd - 0.02398) < 1e-9);
  assert.equal(ledger.totalExternalRevenueUsd, 3.5);
  assert.equal(ledger.totalSelfPayUsd, 0.70); // the self-pay inflow is visible, just correctly excluded from revenue
  assert.ok(Math.abs(ledger.netUsd - (3.5 - 0.02398)) < 1e-9);
  assert.equal(ledger.noCostData, false);
  assert.equal(ledger.noRevenueData, false);
});

test("buildSolvencyLedger: self-pay revenue in-window is EXCLUDED from netUsd but still visible in events, tagged excluded", () => {
  const costRowsResolved = [];
  const selfWalletSet = buildSelfWalletSet({ solanaSelfWallets: ["F5SYUC4f5QULbEgSYb1DFCBfi74AnWE3ZaXAhqXwhZ5T"] });
  const revenueRowsClassified = classifyRevenueRows(
    [{ ts: 100, amountUsd: 0.70, from: "F5SYUC4f5QULbEgSYb1DFCBfi74AnWE3ZaXAhqXwhZ5T" }],
    selfWalletSet,
  );
  const ledger = buildSolvencyLedger({ costRowsResolved, revenueRowsClassified, windowStart: 0, windowEnd: 200 });
  assert.equal(ledger.events.length, 1);
  assert.equal(ledger.events[0].excluded, true);
  assert.equal(ledger.events[0].amountUsd, 0); // never contributes to the signed total
  assert.equal(ledger.events[0].rawAmountUsd, 0.70); // but the real figure is retained for audit
  assert.equal(ledger.totalExternalRevenueUsd, 0);
  assert.equal(ledger.totalSelfPayUsd, 0.70);
});

test("buildSolvencyLedger: empty cost and revenue rows -> noCostData and noRevenueData both true, no throw", () => {
  const ledger = buildSolvencyLedger({ costRowsResolved: [], revenueRowsClassified: [], windowStart: 0, windowEnd: 3600 });
  assert.equal(ledger.noCostData, true);
  assert.equal(ledger.noRevenueData, true);
  assert.equal(ledger.totalCostUsd, 0);
  assert.equal(ledger.totalExternalRevenueUsd, 0);
  assert.equal(ledger.events.length, 0);
});
