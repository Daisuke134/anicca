/**
 * can-run.mjs — D1 precondition gating for the earn/gig slot.
 *
 * gig is LABOR-based (no capital required), so a rail is available as soon as its
 * stored creds exist — this is the chicken-egg solution: a USDC-$0 instance still
 * earns via gig/labor, then capital slots (yield/hl_trade, separate slots) unlock.
 *
 * HARD INVARIANT (Dais 2026-06-29): every rail here is FULLY NO-HUMAN end-to-end AND
 * has ACTUAL action code (bid+deliver), not a pretended-live stub (D2 verified-live-only).
 *   - Coconala = REMOVED (¥→human KYC'd bank = human loop).
 *   - abillio  = REMOVED (domain parked/dead).
 *   - laborx   = NOT listed here yet: it is DETECT-only (apply/deliver = CDP browser, not
 *                written). Listing it before the action code exists would be the exact
 *                "pretended live" violation. Add it back ONLY when laborx apply/deliver lands.
 * Only dealwork (pure API, no-human, USDC escrow→own wallet) is action-complete today.
 *
 * Pure: no I/O. The caller supplies the present cred-key names + brain + usdc balance.
 */

// rail -> cred keys that must ALL be present. Only ACTION-COMPLETE no-human rails belong here.
const RAIL_CREDS = {
  dealwork: ['DEALWORK_API_KEY'],   // pure API, no captcha/human, bid+deliver wired, payout=USDC→own wallet
};

/**
 * @param {{creds: Set<string>, brain: string, usdc: number}} opts
 * @returns {string[]} available rail names (labor rails; never capital-only slots)
 */
export function availableRails({ creds, brain, usdc } = {}) {
  const have = creds instanceof Set ? creds : new Set(creds || []);
  const out = [];
  for (const [rail, keys] of Object.entries(RAIL_CREDS)) {
    if (!keys.every(k => have.has(k))) continue;        // need all creds for the rail
    out.push(rail);                                      // every rail here is no-human end-to-end
  }
  return out;
}

export { RAIL_CREDS };
