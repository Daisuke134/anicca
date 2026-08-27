// refill.mjs — S19: when Base revenue should become Solana rent.
//
// The agent earns USDC on Base (x402 settles there) and spends NOS + SOL on Solana (Nosana
// lease) plus USDC on Base (frontier inference, Modal boxes). Revenue therefore piles up on the
// wrong chain from the shelter's point of view — a wallet can be rich in USDC and homeless at
// the same time. This module is the pure "should we move money, and how much" decision behind
// that hop; skills/self/shelter/nosana/funding/acquire-nos.mjs already owns the real SOL->NOS
// swap and this feature's bridge leg reuses the relay.link flow proven in
// bridge-base-to-solana.mjs (apps/x402-agents/scripts) — neither is reimplemented here.
//
// THREE wallets, not two — this is the fix for a real routing bug (S19 v1 shipped without it).
// The Solana side is TWO wallets, not one (S8, sub-wallet.mjs): a treasury (Franklin's own
// canonical key, resolve-identity.mjs's resolveSolanaSecret) and a capped SPENDER sub-wallet
// (sub-wallet.mjs's ensureSubWallet) that is the ONLY key nosana lease payments ever sign with.
// v1 measured "is Solana stocked" against the treasury and stopped there — a treasury full of NOS
// changes nothing about whether the agent has a home, because the treasury cannot pay rent; only
// the sub-wallet can, and it was never topped up. So this module now targets the SUB-WALLET's
// balance for "do we need to act at all", and adds a third leg: after the bridge+swap refill the
// treasury, sub-wallet.mjs's own capped, gated fundSubWallet moves a bounded slice of that onward
// to the actual spender. Bridging/swapping is skipped entirely when the treasury already holds
// enough to cover the sub-wallet's shortfall on its own — that money is already on the right
// chain, so paying a bridge fee to move it again would be pure waste.
//
// Kept free of network calls, key reads, and process.env on purpose: every number it needs
// arrives as an argument, so it can be exercised exhaustively without ever touching a wallet. The
// thin executor (bin/citizen-refill) is what reads real balances and injects real rails.

import { DEFAULT_NOS_CAP as SUBWALLET_NOS_CAP, DEFAULT_SOL_CAP as SUBWALLET_SOL_CAP } from "../sub-wallet.mjs";

// Top the SPENDER up to its own cap, not past it — sub-wallet.mjs's caps ARE the security
// boundary (a leaked cloud key loses at most the cap), and its own funding gate flatly refuses
// any request that would push the sub-wallet over cap rather than clamping it down. Importing the
// literal constants (not copying the numbers) means this target can never drift out of sync with
// what the gate will actually allow.
export const DEFAULT_SUBWALLET_TARGET_NOS = SUBWALLET_NOS_CAP;
export const DEFAULT_SUBWALLET_TARGET_SOL = SUBWALLET_SOL_CAP;

// relay.link (and the destination-chain landing fee) take a real cut of a bridge; below this
// floor, a "successful" transfer would arrive smaller than what it cost to send.
export const DEFAULT_MIN_BRIDGE_USD = 0.5;

// Base is not just a source of NOS money — it is where the agent pays for frontier inference and
// Modal boxes directly. Bridging it down to zero to feed Solana just relocates the starvation
// from one chain to the other, so this much always stays behind regardless of how short Solana is.
export const DEFAULT_KEEP_ON_BASE_USD = 1.0;

// One pass never moves more than this, no matter how large the shortfall or the Base balance
// looks — a bad quote, a bad price read, or a bug in this function can only cost one bounded
// pass, not the whole treasury. Extra passes are always available on the next tick.
export const DEFAULT_MAX_PASS_USD = 25;

function isFiniteNumber(v) {
  return typeof v === "number" && Number.isFinite(v);
}

/**
 * Pure: should we move money toward the wallet that actually pays rent (the sub-wallet), and how?
 *
 * Balances are REQUIRED, not defaulted — a caller that forgets to pass one gets a refusal, not a
 * silent "assume it's fine" (same fail-closed shape as renew.mjs's evaluateRenewal).
 *
 * Decision order:
 *   1. Is the SUB-WALLET (the spender) short of NOS and/or SOL against its own cap? If not, done —
 *      bridging/swapping/topping-up money the spender does not need would just burn fees.
 *   2. Does the TREASURY already hold enough to cover that shortfall directly? If so, skip the
 *      bridge and the swap entirely — the money is already on Solana, so route it straight to the
 *      sub-wallet (`topUpNos`/`topUpSol`, `bridgeUsd: 0`, `swapNeeded: false`).
 *   3. Otherwise bring in outside money: bridge Base USDC (bounded, see the DEFAULT_* comments
 *      above), and swap it for NOS ONLY if NOS specifically is what the treasury cannot already
 *      cover (`swapNeeded`) — a pure SOL shortfall lands as native SOL from the bridge itself and
 *      never needs a swap at all (see executeRefill's doc comment).
 *
 * @returns {{act: boolean, bridgeUsd: number, swapNeeded: boolean, topUpNos: number, topUpSol: number, reason: string}}
 */
export function planRefill({
  subNosBalance,
  subSolBalance,
  ownerNosBalance,
  ownerSolBalance,
  baseUsdc,
  targetSubNos = DEFAULT_SUBWALLET_TARGET_NOS,
  targetSubSol = DEFAULT_SUBWALLET_TARGET_SOL,
  minBridgeUsd = DEFAULT_MIN_BRIDGE_USD,
  keepOnBaseUsd = DEFAULT_KEEP_ON_BASE_USD,
  maxPassUsd = DEFAULT_MAX_PASS_USD,
} = {}) {
  const inputs = { subNosBalance, subSolBalance, ownerNosBalance, ownerSolBalance, baseUsdc };
  for (const [key, value] of Object.entries(inputs)) {
    if (!isFiniteNumber(value)) {
      return {
        act: false,
        bridgeUsd: 0,
        swapNeeded: false,
        topUpNos: 0,
        topUpSol: 0,
        reason: `refusing to plan without a real ${key} number (fail-closed)`,
      };
    }
  }

  const topUpNos = Math.max(0, targetSubNos - subNosBalance);
  const topUpSol = Math.max(0, targetSubSol - subSolBalance);

  if (topUpNos === 0 && topUpSol === 0) {
    return {
      act: false,
      bridgeUsd: 0,
      swapNeeded: false,
      topUpNos: 0,
      topUpSol: 0,
      reason: `the wallet that actually pays rent is stocked: ${subNosBalance} NOS >= ${targetSubNos}, ${subSolBalance} SOL >= ${targetSubSol} — nothing to do`,
    };
  }

  const ownerCoversNos = ownerNosBalance >= topUpNos;
  const ownerCoversSol = ownerSolBalance >= topUpSol;

  if (ownerCoversNos && ownerCoversSol) {
    return {
      act: true,
      bridgeUsd: 0,
      swapNeeded: false,
      topUpNos,
      topUpSol,
      reason:
        `treasury already holds enough (${ownerNosBalance} NOS, ${ownerSolBalance} SOL) to cover the ` +
        `shelter wallet's shortfall (${topUpNos.toFixed(6)} NOS, ${topUpSol.toFixed(6)} SOL) directly — ` +
        `skipping the bridge and the swap, topping up straight from the treasury`,
    };
  }

  // Some (or all) of the shortfall needs money that has not reached Solana yet. NOS specifically
  // only needs manufacturing (a swap) when the treasury does not already hold enough of it — a
  // pure SOL gap is filled directly by the bridge itself (see executeRefill's doc comment).
  const swapNeeded = topUpNos > 0 && !ownerCoversNos;

  // What Base can spare without touching its own working capital, then bounded to one pass. The
  // exact USD->NOS conversion is deliberately NOT computed here — acquire-nos.mjs already prices
  // that for real against a live Jupiter quote once the bridged SOL has landed; this module only
  // decides how large a pass is worth attempting.
  const availableUsd = Math.max(0, baseUsdc - keepOnBaseUsd);
  const bridgeUsd = Math.min(availableUsd, maxPassUsd);

  if (bridgeUsd < minBridgeUsd) {
    return {
      act: false,
      bridgeUsd: 0,
      swapNeeded: false,
      topUpNos,
      topUpSol,
      reason:
        `available bridge $${availableUsd.toFixed(2)} (after keeping $${keepOnBaseUsd} on Base) is too small ` +
        `to be worth its fees — need at least $${minBridgeUsd}, and the treasury alone cannot cover the ` +
        `shelter wallet's shortfall (${topUpNos.toFixed(6)} NOS, ${topUpSol.toFixed(6)} SOL)`,
    };
  }

  const legs = [swapNeeded && "swap to NOS", "top up the shelter wallet"].filter(Boolean).join(", then ");
  return {
    act: true,
    bridgeUsd,
    swapNeeded,
    topUpNos,
    topUpSol,
    reason:
      `bridging $${bridgeUsd.toFixed(2)} from Base, then ${legs} — treasury alone cannot cover the shelter ` +
      `wallet's shortfall (needs ${topUpNos.toFixed(6)} NOS, ${topUpSol.toFixed(6)} SOL)`,
  };
}

/**
 * Carry out a decided plan: bridge Base USDC to the treasury (Solana), then — only if the plan
 * says NOS must be manufactured — swap the landed SOL into NOS, then — always last — move the
 * shortfall on to the sub-wallet that actually pays rent. Every rail is injected; this function
 * never touches the network itself. bin/citizen-refill supplies the real bridge (relay.link,
 * mirroring bridge-base-to-solana.mjs), the real swap (acquire-nos.mjs's acquireNos, run against
 * the treasury identity), and the real top-up (sub-wallet.mjs's fundSubWallet, which applies its
 * own caps/floors — this function never reimplements that gate).
 *
 * Ordering is bridge -> swap -> top-up, and each leg runs ONLY if the leg before it succeeded (or
 * was not needed at all, per the plan). Money that never arrived cannot be moved onward: a failed
 * bridge means there is nothing new for the swap to work with, and a failed swap means the top-up
 * would be sending NOS that was never actually acquired. A leg the plan marked unnecessary
 * (bridgeUsd 0, swapNeeded false) is simply skipped rather than treated as a failure — e.g. when
 * the treasury already covers the shortfall, execution goes straight to the top-up.
 */
export async function executeRefill({ plan, bridge, swapToNos, topUpSubWallet }) {
  if (!plan || plan.act !== true) {
    return { ok: true, skipped: true, reason: (plan && plan.reason) || "no plan to act on" };
  }

  let bridgeResult = null;
  if (plan.bridgeUsd > 0) {
    bridgeResult = await bridge(plan.bridgeUsd);
    if (!bridgeResult || bridgeResult.ok !== true) {
      return {
        ok: false,
        skipped: false,
        reason: `bridge failed: ${(bridgeResult && bridgeResult.reason) || "unknown"}`,
        bridge: bridgeResult,
        swap: null,
        topUp: null,
      };
    }
  }

  let swapResult = null;
  if (plan.swapNeeded) {
    swapResult = await swapToNos();
    // acquireNos returns a reconciled settlement as {posted:true, signature, nosReceived};
    // it does not use an `ok` field. A signature alone is not enough unless the rail also says it
    // posted, while an unreadable shape is indeterminate because funds may already have moved.
    const swapped = swapResult && (
      swapResult.ok
      ?? (
        swapResult.posted === true
        && typeof swapResult.signature === "string"
        && swapResult.signature.length > 0
      )
    );
    if (swapped !== true) {
      const indeterminate = Boolean(swapResult)
        && swapResult.ok === undefined
        && swapResult.posted === undefined;
      return {
        ok: false,
        indeterminate,
        skipped: false,
        reason: indeterminate
          ? "swap result is unreadable — the swap MAY have gone through. Check the chain before retrying; do not swap blind."
          : `swap failed: ${(swapResult && swapResult.reason) || "no reason given"}`,
        bridge: bridgeResult,
        swap: swapResult,
        topUp: null,
      };
    }
  }

  let topUpResult = null;
  if (plan.topUpNos > 0 || plan.topUpSol > 0) {
    topUpResult = await topUpSubWallet({ nos: plan.topUpNos, sol: plan.topUpSol });
    // Rails report success under different names. Read both, and treat "neither field is present"
    // as INDETERMINATE rather than as failure: this call may already have moved money, and a
    // caller told "failed" will retry and send it twice. Measured 2026-07-27 — tx aYGEcC5k landed
    // 0.473 NOS on-chain while this branch reported `top-up failed: unknown`, because the rail
    // returns `sent` and this read `ok`.
    const moved = topUpResult && (topUpResult.ok ?? topUpResult.sent);
    if (moved !== true) {
      const indeterminate = Boolean(topUpResult) && topUpResult.ok === undefined && topUpResult.sent === undefined;
      return {
        ok: false,
        indeterminate,
        skipped: false,
        reason: indeterminate
          ? "top-up result is unreadable — the transfer MAY have gone through. Check the chain before retrying; do not re-send blind."
          : `top-up refused: ${(topUpResult && (topUpResult.reason || (topUpResult.gate && topUpResult.gate.reason))) || "no reason given"}`,
        bridge: bridgeResult,
        swap: swapResult,
        topUp: topUpResult,
      };
    }
  }

  return { ok: true, skipped: false, bridge: bridgeResult, swap: swapResult, topUp: topUpResult };
}
