/**
 * catalog-gate.mjs — Pure: filterCatalog(...) → string[]
 *
 * anicca-agent-economy REQ-201/202/203: a bookkeeping-only catalog eligibility gate that hides
 * capital-risking earn slots from a broke instance's tool menu until it clears a reserve floor
 * (`BOOTSTRAP_RESERVE_USDC`), except when the instance already holds an open position in that slot
 * (the FIND-003 close/withdraw carve-out). Directly analogous to the existing `tier.mjs::selectTier` --
 * deterministic set arithmetic over already-fetched bookkeeping inputs, no I/O, no ranking/preference
 * logic (REQ-203). See specs/behavioral-spec.md and specs/verification-architecture.md
 * (.vcsdd/features/anicca-agent-economy/) for the full requirement text.
 */

// REQ-201's documented default: mirrors the exact `Number(process.env.X) || N` fallback idiom already
// used for COMPUTE_RESERVE_USDC in context.mjs. Standing invariant: this MUST be >= COMPUTE_RESERVE_USDC's
// own default (5) -- see PROP-201c.
export const DEFAULT_BOOTSTRAP_RESERVE_USDC = Number(process.env.BOOTSTRAP_RESERVE_USDC) || 20;

/**
 * Resolve the effective reserve threshold: use the caller-supplied value only if it is a finite,
 * non-negative number; otherwise fall back to the documented default. This is what keeps the gate from
 * ever being silently disabled by a misconfigured/unset/negative/non-finite threshold (REQ-201 edge case).
 *
 * @param {number} reserveThresholdUsdc
 * @returns {number}
 */
function effectiveThreshold(reserveThresholdUsdc) {
  return Number.isFinite(reserveThresholdUsdc) && reserveThresholdUsdc >= 0
    ? reserveThresholdUsdc
    : DEFAULT_BOOTSTRAP_RESERVE_USDC;
}

/**
 * Is the given balance below the given (already-resolved) threshold? A non-finite or otherwise invalid
 * balance is treated as below-threshold (fail-closed), mirroring tier.mjs's own NaN/Infinity/negative
 * handling (REQ-201 edge case).
 *
 * @param {number} balanceUsdc
 * @param {number} threshold
 * @returns {boolean}
 */
function isBelowThreshold(balanceUsdc, threshold) {
  return !Number.isFinite(balanceUsdc) || balanceUsdc < threshold;
}

/**
 * filterCatalog — REQ-201/202/203's pure eligibility gate.
 *
 * @param {object} opts
 * @param {number} opts.balanceUsdc - the instance's current realized liquid USDC balance
 * @param {string[]} opts.allSlotNames - every currently-live skill slot name
 * @param {(slotName: string) => (string|undefined)} opts.riskTagOf - "safe" | "capital" | undefined
 *   (untagged) per slot; anything other than exactly "safe" is treated as capital-risking (fail-closed
 *   default for untagged slots -- REQ-201 edge case)
 * @param {(slotName: string) => boolean} opts.alwaysAvailableOf - maintainer override: true survives
 *   filtering unconditionally, regardless of riskTagOf (REQ-201's FIND-002 fix)
 * @param {(slotName: string) => boolean} opts.hasOpenRiskPositionOf - already-RESOLVED, synchronous
 *   per-slot bookkeeping fact: does the instance currently hold an open position in this slot? (REQ-201's
 *   FIND-003 open-position carve-out)
 * @param {number} opts.reserveThresholdUsdc - the configured BOOTSTRAP_RESERVE_USDC value (may be
 *   unset/non-finite/negative -- falls back to DEFAULT_BOOTSTRAP_RESERVE_USDC)
 * @returns {string[]} a plain array of eligible slot names, no score/rank/preference attached (REQ-203)
 */
export function filterCatalog({
  balanceUsdc,
  allSlotNames,
  riskTagOf,
  alwaysAvailableOf,
  hasOpenRiskPositionOf,
  reserveThresholdUsdc,
}) {
  const slots = Array.isArray(allSlotNames) ? allSlotNames : [];
  const threshold = effectiveThreshold(reserveThresholdUsdc);

  // balanceUsdc may be a number (one balance for every slot — the original behaviour, and what
  // every existing caller and test passes) or a function (name) => number, letting the caller gate
  // each slot on the money THAT slot can actually spend.
  //
  // Why the function form exists (measured 2026-07-12): the gate read only Base USDC. claude-p held
  // $1.95 there — five cents under the $2 reserve — so every capital-risking slot was hidden and its
  // brain had nothing left to pick but `narrate` (235 of its last 300 wakes). Meanwhile it held $5.18
  // of pUSD inside its Polymarket deposit wallet: money that buys Polymarket shares and nothing else,
  // i.e. exactly the currency the polymarket slot spends. The instance was forbidden from trading on
  // the only venue its money could be spent at. Franklin, on the identical code with $6.48 of Base
  // USDC, cleared the same gate and traded polymarket 120 times. Same code, opposite outcome, and the
  // whole difference was which pocket the gate happened to look in.
  //
  // The gate stays honest either way: it never counts money a slot cannot draw on.
  const balanceFor = (name) =>
    typeof balanceUsdc === "function" ? balanceUsdc(name) : balanceUsdc;

  return slots.filter((name) => {
    // REQ-202: at or above threshold, a slot is never removed (equality counts as at-or-above).
    if (!isBelowThreshold(balanceFor(name), threshold)) return true;
    // FIND-002: alwaysAvailable overrides the risk tag entirely, checked BEFORE the risk tag itself, so
    // a pathological all-risky-tagged registry can never hide these maintainer-designated utility slots.
    if (typeof alwaysAvailableOf === "function" && alwaysAvailableOf(name) === true) return true;
    // Only an EXPLICIT "safe" tag exempts a slot from the gate -- anything else (an explicit "capital"
    // tag, or no tag at all) is treated as capital-risking (fail-closed default for untagged slots).
    if (typeof riskTagOf === "function" && riskTagOf(name) === "safe") return true;
    // FIND-003: a capital-risking slot with a currently-open position stays visible so it can be
    // closed/withdrawn -- being below the bootstrap reserve only ever blocks OPENING new risk, never
    // closing existing exposure.
    return typeof hasOpenRiskPositionOf === "function" && hasOpenRiskPositionOf(name) === true;
  });
}

/**
 * hasOpenRiskPositionOfYield — REQ-201's `yield` carve-out mechanism: a synchronous read of the EXACT
 * same ledger-scan expression `runtime/loop/index.mjs` already performs, every wake, to populate
 * `ctx.positionsSummary` -- genuinely no new I/O, no new query. Zero-argument-shape surprises: any
 * non-array input is treated as an empty ledger (no open position), never throws.
 *
 * @param {object[]} recentLedger - recent ledger lines (each `{ source, tx, ... }`)
 * @returns {boolean}
 */
export function hasOpenRiskPositionOfYield(recentLedger) {
  const ledger = Array.isArray(recentLedger) ? recentLedger : [];
  const match = ledger
    .slice()
    .reverse()
    .find((l) => String((l && l.source) || "").startsWith("yield") && l && l.tx);
  return Boolean(match);
}

/**
 * hasOpenRiskPositionOfHlTrade — REQ-201's `hl_trade` carve-out mechanism: a NEW, lazy Hyperliquid
 * position query. Lazy: `queryFn` is invoked ONLY when `balanceUsdc` is below the (resolved)
 * `reserveThresholdUsdc` for the current wake -- at/above threshold this resolves `false` without ever
 * calling `queryFn` (the carve-out is irrelevant above threshold, since nothing is being excluded there).
 * Fail-OPEN (deliberately the opposite direction from every other fail-closed default in this gate, see
 * behavioral-spec.md REQ-201): if `queryFn` rejects, times out, or the endpoint is unreachable, this
 * resolves `true` (assume a position MAY be open) rather than `false` -- wrongly hiding `hl_trade` from
 * an instance that actually needs it to close a real position is the unbounded-harm failure mode; wrongly
 * showing it for one extra wake when no position exists is the bounded, low-cost one.
 *
 * @param {object} opts
 * @param {number} opts.balanceUsdc
 * @param {number} opts.reserveThresholdUsdc
 * @param {() => Promise<{open_positions?: object[]}>} opts.queryFn - production: wired to `hl.py
 *   account`'s real output; tests inject a fake
 * @returns {Promise<boolean>}
 */
export async function hasOpenRiskPositionOfHlTrade({ balanceUsdc, reserveThresholdUsdc, queryFn }) {
  const threshold = effectiveThreshold(reserveThresholdUsdc);
  if (!isBelowThreshold(balanceUsdc, threshold)) return false; // never queried at/above threshold
  try {
    const result = await queryFn();
    const positions = result && Array.isArray(result.open_positions) ? result.open_positions : [];
    return positions.length > 0;
  } catch {
    return true; // fail-open, deliberately opposite direction from this gate's other fail-closed defaults
  }
}
