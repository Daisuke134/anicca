// solvency-ledger.mjs — THE deterministic join: revenue events + shelter cost events, over one
// shared window, into a single view of what came in and what went out. This is a temporal join, not
// a row-to-row match: a shelter lease renewal and a revenue payment are independent real-world
// events on different chains (Solana job rent vs. wherever a sale eventually settles) with no
// natural 1:1 correspondence, so this deliberately does NOT invent a synthetic key to pair them up.
// What it DOES do is keep every row's own real identifying fields intact (a cost row's `jobAddress`,
// a revenue row's `from`/`txSignature`) so the combined ledger is fully traceable back to its source
// — "join" here means "merge two real, already-classified streams into one chronologically ordered,
// window-scoped view with correct running totals", not "correlate transaction A with transaction B".
//
// Callers MUST pass:
//   - costRowsResolved: shelter-cost-ledger.js's readShelterCostEntriesResolved(...) output (never
//     the raw reader — see shelter-burn.mjs's header for why a raw correction row would corrupt the
//     sum).
//   - revenueRowsClassified: self-pay.mjs's classifyRevenueRows(...) output (never unclassified rows
//     — this module trusts the `external` flag it's given rather than re-deriving it, so classifying
//     is a separate, independently-testable step).

import { sumResolvedShelterCostUsd, computeBurnRateUsdPerHour } from "./shelter-burn.mjs";
import { sumExternalRevenueUsd, computeRevenueRateUsdPerHour } from "./revenue.mjs";
import { filterRowsByWindow } from "./ledger-window.mjs";

/**
 * Pure: build the joined solvency ledger for [windowStart, windowEnd] — a chronological list of
 * every cost and revenue event in the window (each tagged with its own real fields, `type`, and
 * signed `amountUsd`: negative for cost, positive for external revenue, self-pay rows kept but
 * tagged `excluded: true` and NOT signed into the running total) plus the aggregate totals both
 * sides need.
 */
export function buildSolvencyLedger({ costRowsResolved, revenueRowsClassified, windowStart, windowEnd }) {
  const costInWindow = filterRowsByWindow(costRowsResolved, { windowStart, windowEnd });
  const revenueInWindow = filterRowsByWindow(revenueRowsClassified, { windowStart, windowEnd });

  const costSummary = sumResolvedShelterCostUsd(costRowsResolved, { windowStart, windowEnd });
  const burn = computeBurnRateUsdPerHour(costSummary);
  const revenueSummary = sumExternalRevenueUsd(revenueRowsClassified, { windowStart, windowEnd });
  const revenueRate = computeRevenueRateUsdPerHour(revenueSummary);

  const events = [
    ...costInWindow.map((row) => ({
      type: "cost",
      ts: row.ts,
      amountUsd: -Number(row.settledLeaseCostUsd),
      jobAddress: row.jobAddress || null,
      corrected: row.corrected === true,
    })),
    ...revenueInWindow.map((row) => ({
      type: "revenue",
      ts: row.ts,
      amountUsd: row.external ? Number(row.amountUsd) : 0,
      rawAmountUsd: Number(row.amountUsd),
      from: row.from || null,
      txSignature: row.txSignature || null,
      external: Boolean(row.external),
      excluded: !row.external,
      classification: row.classification || null,
    })),
  ].sort((a, b) => a.ts - b.ts);

  return {
    windowStart,
    windowEnd,
    events,
    totalCostUsd: costSummary.totalCostUsd,
    totalExternalRevenueUsd: revenueSummary.totalExternalRevenueUsd,
    totalSelfPayUsd: revenueSummary.totalSelfPayUsd,
    netUsd: revenueSummary.totalExternalRevenueUsd - costSummary.totalCostUsd,
    burnUsdPerHour: burn.burnUsdPerHour,
    revenueUsdPerHour: revenueRate.revenueUsdPerHour,
    netUsdPerHour: revenueRate.revenueUsdPerHour - burn.burnUsdPerHour,
    windowHours: burn.windowHours,
    costEventCount: costSummary.eventCount,
    revenueEventCount: revenueSummary.totalEventCount,
    externalRevenueEventCount: revenueSummary.externalEventCount,
    noCostData: burn.noData,
    noRevenueData: revenueRate.noData,
  };
}
