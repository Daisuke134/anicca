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
export function assembleContext({ walletAddress, balanceUsdc, tier, model, recentLedgerLines, genesisPrompt, wakeId, ts }) {
  return {
    walletAddress: walletAddress || 'unknown',
    balanceUsdc: typeof balanceUsdc === 'number' ? balanceUsdc : 0,
    tier: tier || 'broke',
    model: model || 'nvidia/deepseek-v4-flash',
    recentLedgerLines: Array.isArray(recentLedgerLines) ? recentLedgerLines.slice(-20) : [],
    genesisPrompt: genesisPrompt || '',
    wakeId: wakeId || '',
    ts: ts || Math.floor(Date.now() / 1000),
  };
}
