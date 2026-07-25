// ledger-window.mjs — pure time-window helpers shared by the cost side and the revenue side of the
// solvency join, so both are always measured over the SAME window instead of two silently-different
// ranges producing a misleading net figure.

/**
 * Pure: rows whose `ts` falls in [windowStart, windowEnd] (inclusive both ends — a row landing
 * exactly on a boundary is real data, never dropped by an off-by-one). Rows with a missing/
 * non-finite `ts` are excluded (fail closed: an undatable row can never be silently assumed to be
 * "in" the window).
 */
export function filterRowsByWindow(rows, { windowStart, windowEnd }) {
  if (typeof windowStart !== "number" || !Number.isFinite(windowStart)) {
    throw new Error(`filterRowsByWindow: windowStart must be a finite number, got ${windowStart}`);
  }
  if (typeof windowEnd !== "number" || !Number.isFinite(windowEnd)) {
    throw new Error(`filterRowsByWindow: windowEnd must be a finite number, got ${windowEnd}`);
  }
  if (windowEnd < windowStart) {
    throw new Error(`filterRowsByWindow: windowEnd (${windowEnd}) is before windowStart (${windowStart})`);
  }
  return (rows || []).filter((r) => {
    const ts = r && Number(r.ts);
    return Number.isFinite(ts) && ts >= windowStart && ts <= windowEnd;
  });
}

/**
 * Pure: window length in hours. Fails closed (throws) on a non-positive result rather than letting
 * a caller silently divide by zero — a zero-width window can never yield a meaningful rate.
 */
export function computeWindowHours({ windowStart, windowEnd }) {
  if (typeof windowStart !== "number" || !Number.isFinite(windowStart)) {
    throw new Error(`computeWindowHours: windowStart must be a finite number, got ${windowStart}`);
  }
  if (typeof windowEnd !== "number" || !Number.isFinite(windowEnd)) {
    throw new Error(`computeWindowHours: windowEnd must be a finite number, got ${windowEnd}`);
  }
  const hours = (windowEnd - windowStart) / 3600;
  if (!(hours > 0)) {
    throw new Error(`computeWindowHours: window is not positive-width (${hours}h) — refusing to compute a rate over it`);
  }
  return hours;
}

/**
 * Pure: the default trailing window for an empirical (ledger-observed) rate — [earliest observed
 * `ts` across `rows`, nowTs]. Deliberately NOT a fixed "trailing 24h" default: if the ledger only
 * has, say, 4 hours of real history, dividing its real total cost by a hypothetical 24h window
 * would understate the true burn rate by pretending 20 hours of (nonexistent) zero-cost history
 * happened. Anchoring to the earliest real row means the denominator is always real elapsed time
 * the ledger actually covers. Returns `{windowStart: null, windowEnd: nowTs, hasData: false}` when
 * `rows` is empty — callers must treat `hasData: false` as "no empirical rate available", never
 * silently compute a rate over an empty/undefined window.
 */
export function defaultLedgerWindow(rows, nowTs) {
  if (typeof nowTs !== "number" || !Number.isFinite(nowTs)) {
    throw new Error(`defaultLedgerWindow: nowTs must be a finite number, got ${nowTs}`);
  }
  const timestamps = (rows || []).map((r) => r && Number(r.ts)).filter((t) => Number.isFinite(t));
  if (timestamps.length === 0) {
    return { windowStart: null, windowEnd: nowTs, hasData: false };
  }
  const windowStart = Math.min(...timestamps);
  // A window collapsing to zero width (the only row is dated exactly "now") is nudged back by one
  // second rather than thrown — this is a legitimate edge case (the very first event of all time),
  // not a caller error, and computeWindowHours' own >0 guard is the real backstop against misuse.
  return { windowStart: windowStart < nowTs ? windowStart : nowTs - 1, windowEnd: nowTs, hasData: true };
}
