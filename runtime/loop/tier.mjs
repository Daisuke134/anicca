/**
 * tier.mjs — Pure: selectTier(balanceUsdc, env) → { tier, model }
 *
 * REQ-002: Survival-tier model selection based on USDC balance.
 * No I/O. Deterministic. Formally verifiable.
 *
 * PROP-001: selectTier(0)       → { tier: 'broke',  model: ANICCA_FREE_MODEL   }
 * PROP-002: selectTier(0..1.00) → { tier: 'lean',   model: ANICCA_LEAN_MODEL   }
 * PROP-003: selectTier(>1.00)   → { tier: 'funded', model: ANICCA_FUNDED_MODEL }
 * PROP-004: NaN / Infinity / -Infinity / negative → { tier: 'broke', ... }
 */

const DEFAULT_FREE_MODEL   = 'free/gpt-oss-120b';    // ClawRouter free path = verified $0 (no x402 per call)
const DEFAULT_LEAN_MODEL   = 'free/gpt-oss-120b';
const DEFAULT_FUNDED_MODEL = 'free/gpt-oss-120b';    // cost-free even when funded — no x402 compute burn
const DEFAULT_LEAN_THRESHOLD = 1.00;

/**
 * @param {number} balanceUsdc - USDC balance (may be NaN, Infinity, negative)
 * @param {object} env - key-value map (subset of process.env)
 * @returns {{ tier: 'broke'|'lean'|'funded', model: string }}
 */
export function selectTier(balanceUsdc, env) {
  const freeModel   = (env && env.ANICCA_FREE_MODEL)   || DEFAULT_FREE_MODEL;
  const leanModel   = (env && env.ANICCA_LEAN_MODEL)   || DEFAULT_LEAN_MODEL;
  const fundedModel = (env && env.ANICCA_FUNDED_MODEL) || DEFAULT_FUNDED_MODEL;
  const threshold   = parseFloat((env && env.LEAN_TIER_THRESHOLD) || DEFAULT_LEAN_THRESHOLD);
  const effectiveThreshold = Number.isFinite(threshold) ? threshold : DEFAULT_LEAN_THRESHOLD;

  // Non-finite or negative balance → broke (PROP-004)
  if (!Number.isFinite(balanceUsdc) || balanceUsdc < 0) {
    return { tier: 'broke', model: freeModel };
  }

  if (balanceUsdc === 0) {
    return { tier: 'broke', model: freeModel };
  }

  if (balanceUsdc <= effectiveThreshold) {
    return { tier: 'lean', model: leanModel };
  }

  return { tier: 'funded', model: fundedModel };
}
