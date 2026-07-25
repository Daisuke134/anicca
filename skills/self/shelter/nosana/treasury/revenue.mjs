// revenue.mjs — pure USD external-revenue math over already-classified rows (self-pay.mjs's
// classifyRevenueRows output). Mirrors shelter-burn.mjs's shape deliberately: same window helpers,
// same {total*, eventCount, noData} result shape, so solvency-report.mjs can treat both sides
// symmetrically.

import { filterRowsByWindow, computeWindowHours } from "./ledger-window.mjs";

/**
 * Pure: total EXTERNAL revenue (USD) from already-classified rows, restricted to
 * [windowStart, windowEnd]. Self-pay rows (classified `external: false`) are counted separately as
 * `totalSelfPayUsd` — never added into `totalExternalRevenueUsd` (INV-7) — so the report can show
 * "here is what we correctly excluded" rather than silently dropping it with no trace. Fails closed
 * on a malformed amountUsd on an in-window row (never treated as $0).
 */
export function sumExternalRevenueUsd(classifiedRows, { windowStart, windowEnd }) {
  const inWindow = filterRowsByWindow(classifiedRows, { windowStart, windowEnd });
  let totalExternalRevenueUsd = 0;
  let totalSelfPayUsd = 0;
  let externalEventCount = 0;
  for (const row of inWindow) {
    const amount = row && Number(row.amountUsd);
    if (!Number.isFinite(amount) || amount < 0) {
      throw new Error(
        `sumExternalRevenueUsd: row at ts=${row && row.ts} has an invalid amountUsd (${row && row.amountUsd}) — fail-closed, refusing to treat as $0`,
      );
    }
    if (row.external) {
      totalExternalRevenueUsd += amount;
      externalEventCount += 1;
    } else {
      totalSelfPayUsd += amount;
    }
  }
  return {
    totalExternalRevenueUsd,
    totalSelfPayUsd,
    externalEventCount,
    totalEventCount: inWindow.length,
    windowStart,
    windowEnd,
  };
}

/** Pure: USD/hour external-revenue rate from an already-computed window total. Never fabricates a
 * nonzero rate: eventCount === 0 (no revenue events observed in the window at all, e.g. no revenue
 * ledger wired yet) yields `revenueUsdPerHour: 0, noData: true` — explicitly flagged rather than
 * silently identical to "we checked and confirmed zero income".
 */
export function computeRevenueRateUsdPerHour({ totalExternalRevenueUsd, totalEventCount, windowStart, windowEnd }) {
  if (typeof totalExternalRevenueUsd !== "number" || !Number.isFinite(totalExternalRevenueUsd) || totalExternalRevenueUsd < 0) {
    throw new Error(
      `computeRevenueRateUsdPerHour: totalExternalRevenueUsd must be a non-negative finite number, got ${totalExternalRevenueUsd}`,
    );
  }
  const windowHours = computeWindowHours({ windowStart, windowEnd });
  return {
    revenueUsdPerHour: totalExternalRevenueUsd / windowHours,
    windowHours,
    noData: !totalEventCount || totalEventCount === 0,
  };
}
