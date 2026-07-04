// economy/ubi/ubi.js — Channel B (colony spec §5.2/§5.3): surplus -> humans (contribute) and
// broke-instance mutual aid (distributeAI). PURE decision functions only.
//
// HARD RULE #0: this module computes WHETHER and HOW MUCH to distribute from real inputs
// (deterministic arithmetic) — it never decides on its own that a number is "notable" and it never
// executes a transfer itself. The judgment call ("is $0.20 realized profit real, should we share it")
// stays where it belongs (an agent, or a human reading the plan); the ACTUAL send is a SEPARATE,
// already-built, explicit tool (skills/ubi/execute-ubi.py) invoked only after this gate says yes.
// Fail-closed everywhere: any missing/invalid/non-positive input means NO distribution — never guess.
//
// "realized profit" is NOT invented here — it is skills/earn/lib/revenue.mjs's already-tested
// revenueBySource(...).total (unrealised mark-to-market P&L + realised cash earnings), the exact
// figure telemetry-poster.mjs already reports as the instance's honest P&L (spec §25: "automaton
// realised net +$0.2013/2849 wakes"). No parallel "profit" definition is created.

export const DEFAULT_CONTRIBUTE_CONFIG = {
  contributePct: 0.10,        // §8: a modest, sustainable slice of realized surplus, not all of it
  contributeThresholdUsd: 1,  // below this the gas/complexity isn't worth it -> no-op, not a fake payout
  reserveUsd: 5,              // never let a contribution push the sender below its own compute buffer
};

/**
 * contribute — how much (if any) of THIS instance's realized profit should flow to the human UBI pool.
 * @param {number} totalRealizedProfitUsd - revenueBySource(...).total for this instance, USD
 * @param {number} liquidBalanceUsd - this instance's current liquid USDC, USD
 * @param {object} [config] - overrides for DEFAULT_CONTRIBUTE_CONFIG
 * @returns {{amount_usd: number, reason: string}}
 */
export function contribute(totalRealizedProfitUsd, liquidBalanceUsd, config = {}) {
  const cfg = { ...DEFAULT_CONTRIBUTE_CONFIG, ...config };
  if (!Number.isFinite(totalRealizedProfitUsd) || totalRealizedProfitUsd <= 0) {
    return { amount_usd: 0, reason: `no realized profit (${totalRealizedProfitUsd})` };
  }
  if (totalRealizedProfitUsd < cfg.contributeThresholdUsd) {
    return {
      amount_usd: 0,
      reason: `realized profit $${totalRealizedProfitUsd} below threshold $${cfg.contributeThresholdUsd}`,
    };
  }
  const raw = +(totalRealizedProfitUsd * cfg.contributePct).toFixed(6);
  if (!Number.isFinite(liquidBalanceUsd)) {
    return { amount_usd: 0, reason: 'liquid balance unknown — fail closed' };
  }
  if (liquidBalanceUsd - raw < cfg.reserveUsd) {
    return {
      amount_usd: 0,
      reason: `would breach reserve (liquid=$${liquidBalanceUsd}, reserve=$${cfg.reserveUsd})`,
    };
  }
  return {
    amount_usd: raw,
    reason: `${cfg.contributePct * 100}% of $${totalRealizedProfitUsd} realized profit`,
  };
}

export const DEFAULT_GOJO_CONFIG = {
  giftCeilingUsd: 5,   // REQ-DRAIN fixed ceiling
  giftPct: 0.25,       // REQ-DRAIN: 25% of surplus-above-reserve
  rateLimitHours: 24,  // REQ-DRAIN: <=1 gift/24h per recipient
};

/**
 * distributeAI — gojo mutual aid gate (REQ-DRAIN, spec §5.2/§5.3 INV-KEEP-ALIVE): should THIS surplus
 * instance send a rescue gift to `recipientWallet`, and how much. Registry-signed recipients only, one
 * gift per 24h per recipient, capped at min($5, 25% of the sender's surplus ABOVE ITS OWN reserve) —
 * so a rescue never starves the sender (never causing a "zero active strategies" self-heal violation
 * for the SENDER, mirroring the skip-floor invariant on the money side, not just the strategy side).
 * @param {string} recipientWallet
 * @param {number} senderSurplusAboveReserveUsd - sender's surplus AFTER its own reserve is already subtracted
 * @param {string[]} registrySignedWallets - addresses proven to be real colony members (not a bare list)
 * @param {Array<{to:string, ts:number}>} recentGifts - this sender's own recent gift history (ms epoch)
 * @param {object} [config] - overrides for DEFAULT_GOJO_CONFIG
 * @returns {{amount_usd: number, reason: string}}
 */
export function distributeAI(recipientWallet, senderSurplusAboveReserveUsd, registrySignedWallets, recentGifts, config = {}) {
  const cfg = { ...DEFAULT_GOJO_CONFIG, ...config };
  if (!Array.isArray(registrySignedWallets) || !registrySignedWallets.includes(recipientWallet)) {
    return { amount_usd: 0, reason: `recipient ${recipientWallet} not in the signed colony registry` };
  }
  const now = Date.now();
  const windowMs = cfg.rateLimitHours * 3600 * 1000;
  const alreadyGiftedRecently = (recentGifts || []).some(
    (g) => g && g.to === recipientWallet && Number.isFinite(g.ts) && now - g.ts < windowMs
  );
  if (alreadyGiftedRecently) {
    return { amount_usd: 0, reason: `rate-limited: already gifted ${recipientWallet} within ${cfg.rateLimitHours}h` };
  }
  if (!Number.isFinite(senderSurplusAboveReserveUsd) || senderSurplusAboveReserveUsd <= 0) {
    return { amount_usd: 0, reason: 'sender has no surplus above its own reserve' };
  }
  const amount = Math.min(cfg.giftCeilingUsd, +(senderSurplusAboveReserveUsd * cfg.giftPct).toFixed(6));
  return {
    amount_usd: amount,
    reason: `min($${cfg.giftCeilingUsd}, ${cfg.giftPct * 100}% of $${senderSurplusAboveReserveUsd} surplus-above-reserve)`,
  };
}
