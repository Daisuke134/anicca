// shelter-burn.mjs — pure USD burn-rate math over the CORRECTION-AWARE shelter cost ledger view.
// Callers MUST pass rows already read via shelter-cost-ledger.js's readShelterCostEntriesResolved
// (never the raw readShelterCostEntries) — this module does no I/O and does not know how to resolve
// corrections itself, so passing raw rows here would double-count a corrected row (its jobAddress
// would be wrong, but worse, a correction ROW ITSELF has no settledLeaseCostUsd field: summed
// naively it contributes NaN/undefined, silently corrupting the total). sumResolvedShelterCostUsd
// defends against exactly that by refusing (fail-closed) rather than coercing a missing amount to 0.

import { filterRowsByWindow, computeWindowHours } from "./ledger-window.mjs";

/**
 * Pure: total settled shelter lease cost (USD) from already-resolved rows, restricted to
 * [windowStart, windowEnd]. Fails closed (throws) if any in-window row lacks a finite,
 * non-negative `settledLeaseCostUsd` — a malformed row must never be silently treated as $0 cost
 * (that would understate burn and could tell survival-drive everything is fine when it is not).
 * A resolved correction row is never passed to this function in the first place (see this module's
 * header) — this guard is a second, defensive line, not the primary mechanism.
 */
export function sumResolvedShelterCostUsd(resolvedRows, { windowStart, windowEnd }) {
  const inWindow = filterRowsByWindow(resolvedRows, { windowStart, windowEnd });
  let total = 0;
  for (const row of inWindow) {
    const amount = row && Number(row.settledLeaseCostUsd);
    if (!Number.isFinite(amount) || amount < 0) {
      throw new Error(
        `sumResolvedShelterCostUsd: row at ts=${row && row.ts} has an invalid settledLeaseCostUsd (${row && row.settledLeaseCostUsd}) — fail-closed, refusing to treat as $0`,
      );
    }
    total += amount;
  }
  return { totalCostUsd: total, eventCount: inWindow.length, windowStart, windowEnd };
}

/**
 * Pure: USD/hour burn rate from an already-computed window total. Fails closed on a non-positive
 * windowHours (computeWindowHours already throws on that; this re-checks defensively since callers
 * may pass windowHours from elsewhere) and is honest about eventCount === 0 via the caller checking
 * `noData` on the returned object — a real $0 in a real window is a different fact from "we have no
 * cost data for this window at all", and the two must never be conflated into the same "$0/hr".
 */
export function computeBurnRateUsdPerHour({ totalCostUsd, eventCount, windowStart, windowEnd }) {
  if (typeof totalCostUsd !== "number" || !Number.isFinite(totalCostUsd) || totalCostUsd < 0) {
    throw new Error(`computeBurnRateUsdPerHour: totalCostUsd must be a non-negative finite number, got ${totalCostUsd}`);
  }
  const windowHours = computeWindowHours({ windowStart, windowEnd });
  return {
    burnUsdPerHour: totalCostUsd / windowHours,
    windowHours,
    noData: !eventCount || eventCount === 0,
  };
}
