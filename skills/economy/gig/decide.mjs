// economy/gig/decide.mjs — pure ELIGIBILITY gate for automaton's own participation in the P2.2 gig
// market each wake (colony spec SPEC.md §3 P2.2 / P4 agent-economy). Mirrors economy/ubi/ubi.js's split
// (pure decision vs. explicit execution): this module NEVER decides WHICH gig to take, WHAT task to
// post, WHAT bounty to offer, or WHAT the deliverable is — that is the calling model's own judgment,
// supplied via $ANICCA_ARGS exactly like every other args-driven earn strategy already in this repo
// (skills/earn/run.sh's hl-trade coin/side/size, skills/cook/run.sh's query). HARD RULE #0 (skills give
// TOOL + real data, not a hardcoded decision) — decideGigAction only answers the READINESS question a
// wake needs before it can even consider posting or taking: do I have spare capital right now
// (post-eligible), am I running low with real work actually available on the board (take-eligible), or
// is there nothing to do (idle)? run.sh then only executes an action the model explicitly asked for
// (via ANICCA_ARGS) AND that this gate independently agrees is eligible this wake — a stale or
// ineligible request degrades to a narrate line, it never forces a trade.
//
// Reserve/low thresholds mirror the already-established colony constants (economy/ubi/run.sh:
// RESERVE=$5.00, SURVIVAL_FLOOR=$0.50) so "surplus" and "broke" mean the same thing everywhere this
// instance reasons about its own balance.
export const DEFAULT_RESERVE_USDC = 5.0;
export const DEFAULT_LOW_USDC = 0.5;

/**
 * Pure: given REAL balance + a real open-gig board snapshot, which action class is this wake eligible
 * to attempt? Never throws; unresolvable/untrustworthy input fails closed to 'idle'.
 *
 * @param {object} input
 * @param {number} input.balanceUsdc - this instance's own on-chain USDC balance right now (gig-board chain)
 * @param {object[]} [input.openGigs] - gigList({status:'open'}) result, a real board snapshot
 * @param {number} [input.reserveUsdc] - surplus above this -> post-eligible
 * @param {number} [input.lowUsdc] - balance below this (with an open gig available) -> take-eligible
 * @returns {{action: 'post'|'take'|'idle', reason: string, surplusUsdc?: number, openGigCount?: number}}
 */
export function decideGigAction({
  balanceUsdc,
  openGigs = [],
  reserveUsdc = DEFAULT_RESERVE_USDC,
  lowUsdc = DEFAULT_LOW_USDC,
} = {}) {
  if (!Number.isFinite(balanceUsdc)) {
    return { action: "idle", reason: "balance unknown -- fail closed" };
  }
  if (!Number.isFinite(reserveUsdc) || !Number.isFinite(lowUsdc) || lowUsdc > reserveUsdc) {
    return { action: "idle", reason: "invalid reserve/low config -- fail closed" };
  }

  const surplusUsdc = +(balanceUsdc - reserveUsdc).toFixed(6);
  if (surplusUsdc > 0) {
    return {
      action: "post",
      reason: `surplus $${surplusUsdc} above reserve $${reserveUsdc} -- can afford a bounded gig`,
      surplusUsdc,
    };
  }

  if (balanceUsdc < lowUsdc) {
    const openGigCount = Array.isArray(openGigs) ? openGigs.length : 0;
    if (openGigCount > 0) {
      return {
        action: "take",
        reason: `balance $${balanceUsdc} below survival floor $${lowUsdc} and ${openGigCount} open gig(s) on the board -- worth trying to earn`,
        openGigCount,
      };
    }
    return {
      action: "idle",
      reason: `balance $${balanceUsdc} below survival floor $${lowUsdc} but no open gigs to take`,
    };
  }

  return {
    action: "idle",
    reason: `balance $${balanceUsdc} between floor $${lowUsdc} and reserve $${reserveUsdc} -- holding, nothing to do`,
  };
}
