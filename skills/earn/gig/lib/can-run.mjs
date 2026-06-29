/**
 * can-run.mjs — D1 precondition gating for the earn/gig slot.
 *
 * gig is LABOR-based (no capital required), so a rail is available as soon as its
 * stored creds exist — this is the chicken-egg solution: a USDC-$0 instance still
 * earns via gig/labor, then capital slots (yield/hl_trade, separate slots) unlock.
 *
 * Coconala is CONDITIONAL (D3): only on a human-funded brain (claude-p) WITH creds,
 * because it settles to a human's KYC'd bank (¥→MUFG), never on-chain. A self-funded
 * (proxy) brain or a child instance never sees it.
 *
 * Only VERIFIED-LIVE rails are listed (D2): abillio is dropped (domain parked/dead).
 *
 * Pure: no I/O. The caller supplies the present cred-key names + brain + usdc balance.
 */

// rail -> the cred keys that must ALL be present for it to be usable
const RAIL_CREDS = {
  laborx: ['LABORX_EMAIL', 'LABORX_PASSWORD'],
  dealwork: ['DEALWORK_API_KEY'],
  coconala: ['COCONALA_EMAIL', 'COCONALA_PASSWORD'],
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
    if (rail === 'coconala' && brain !== 'claude-p') continue; // D3: human-funded only
    out.push(rail);
  }
  return out;
}

export { RAIL_CREDS };
