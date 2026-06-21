/**
 * context.mjs — Pure: assembleContext(opts) → context object
 *
 * REQ-001: Wake context assembly — wallet address, balance, recent ledger lines,
 * genesis prompt. No I/O performed here; all data passed in as arguments.
 */

/**
 * @typedef {object} WakeContext
 * @property {string} walletAddress
 * @property {number} balanceUsdc
 * @property {string} tier
 * @property {string} model
 * @property {object[]} recentLedgerLines - last 20 lines from ledger
 * @property {string} genesisPrompt - contents of $ANICCA_HOME/identity/genesis.md
 * @property {string} wakeId - ULID for this wake
 * @property {number} ts - unix timestamp
 */

/**
 * Assemble the wake context from pre-loaded data.
 *
 * @param {object} opts
 * @returns {WakeContext}
 */
export function assembleContext({ walletAddress, balanceUsdc, tier, model, recentLedgerLines, genesisPrompt, wakeId, ts, activeSkillSlots, skillCatalog, positionsSummary }) {
  return {
    walletAddress: walletAddress || 'unknown',
    balanceUsdc: typeof balanceUsdc === 'number' ? balanceUsdc : 0,
    // PATCH 3: surface deployed positions (yield/HL/etc) so the model can DECIDE a strategy from its
    // actual portfolio, not default. Empty string when the bootstrap didn't read positions.
    positionsSummary: typeof positionsSummary === 'string' ? positionsSummary : '',
    tier: tier || 'broke',
    model: model || 'free/gpt-oss-120b',
    recentLedgerLines: Array.isArray(recentLedgerLines) ? recentLedgerLines.slice(-20) : [],
    genesisPrompt: genesisPrompt || '',
    wakeId: wakeId || '',
    ts: ts || Math.floor(Date.now() / 1000),
    // spec 25 O1: the live skill slots the LLM may pick + their summaries
    activeSkillSlots: Array.isArray(activeSkillSlots) ? activeSkillSlots : [],
    skillCatalog: skillCatalog && typeof skillCatalog === 'object' ? skillCatalog : {},
  };
}
