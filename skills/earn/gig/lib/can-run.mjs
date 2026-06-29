/**
 * can-run.mjs — D1 precondition gating for the earn/gig slot.
 *
 * gig is LABOR-based (no capital required), so a rail is available as soon as its
 * stored creds exist — this is the chicken-egg solution: a USDC-$0 instance still
 * earns via gig/labor, then capital slots (yield/hl_trade, separate slots) unlock.
 *
 * HARD INVARIANT (Dais 2026-06-29): every rail here is FULLY NO-HUMAN end-to-end —
 * onboarding, work, AND payout require zero human. A rail that needs human KYC / a
 * human's bank / any human input is DISQUALIFIED, because such a rail contradicts
 * "financially independent from humans". So:
 *   - Coconala = REMOVED (¥→human KYC'd bank = human loop).
 *   - abillio  = REMOVED (domain parked/dead, D2).
 * Only payout-to-own-wallet (USDC/crypto) rails qualify: laborx, dealwork (+x402 later).
 *
 * Pure: no I/O. The caller supplies the present cred-key names + brain + usdc balance.
 */

// rail -> the cred keys that must ALL be present for it to be usable.
// EVERY rail is no-human end-to-end with crypto/USDC payout to the OWN wallet.
const RAIL_CREDS = {
  laborx: ['LABORX_EMAIL', 'LABORX_PASSWORD'],   // login=stored creds, signup-captcha=CapSolver, payout=crypto→wallet
  dealwork: ['DEALWORK_API_KEY'],                // pure API, no captcha, payout=USDC escrow→wallet
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
