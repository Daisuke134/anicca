// reconcile.mjs — at-most-once reconciliation for the Base burn transaction, PLUS polling the
// Solana destination balance for the cross-chain credit. Two distinct concerns, kept as two
// function pairs because they resolve two different questions on two different timescales:
//
//   1. "did my SEND of the burn (or approve) transaction actually happen?" — seconds. An RPC
//      hiccup on send is the normal transient failure mode here. Mirrors
//      funding/acquire-nos.mjs's pollForConfirmation + reconcileUnknownOutcome exactly, just
//      reading a Base tx receipt by its pre-computed (deterministic, see sign.mjs) hash instead of
//      a Solana signature status.
//   2. "has the bridged USDC actually arrived on Solana yet?" — minutes, possibly much longer,
//      since this build does not submit the CCTP destination-side finalize call itself (see
//      README's known gap). Per spec this is the NORMAL case, not an edge case, so
//      pollForDestinationCredit times out into an honest `awaiting-credit` outcome rather than a
//      failure — and NEVER triggers a re-send of anything.
//
// Every dependency below is injected and read-only; none of these functions has a "send"
// capability in its signature, so retrying a poll can never resend the burn — structurally, not
// just behaviorally, incapable of a duplicate spend (same property funding/acquire-nos.mjs's
// reconcileUnknownOutcome documents for its own domain).

/** Pure: classify one eth_getTransactionReceipt result. */
export function decideBaseReceiptOutcome(receipt) {
  if (!receipt) return { outcome: "not-found" };
  const status = receipt.status;
  if (status === "0x1" || status === 1) return { outcome: "confirmed", receipt };
  if (status === "0x0" || status === 0) return { outcome: "failed-onchain", receipt };
  return { outcome: "pending" };
}

/**
 * I/O (fully injected, no real network by default): poll getReceiptImpl until the tx lands, fails
 * on-chain, or timeoutMs elapses. Every dependency (receipt lookup, sleep, clock) is injected so
 * this is unit-testable with fake timers — no real waiting in tests.
 */
export async function pollForBaseReceipt({
  txHash,
  getReceiptImpl,
  sleepImpl,
  now = () => Date.now(),
  pollIntervalMs = 3000,
  timeoutMs = 120000,
}) {
  const start = now();
  // eslint-disable-next-line no-constant-condition
  while (true) {
    let receipt = null;
    try {
      receipt = await getReceiptImpl(txHash);
    } catch {
      receipt = null; // RPC hiccup — keep polling, never treat as failed or confirmed.
    }
    const decided = decideBaseReceiptOutcome(receipt);
    if (decided.outcome === "confirmed" || decided.outcome === "failed-onchain") return decided;
    if (now() - start >= timeoutMs) return { outcome: "timeout" };
    await sleepImpl(pollIntervalMs);
  }
}

/**
 * At-most-once reconciliation for a Base tx whose SEND outcome is unknown (RPC threw or timed out
 * on the send call itself, or pollForBaseReceipt above timed out). NEVER sends anything — every
 * dependency is read-only, so this function is structurally incapable of a duplicate broadcast.
 * Checks the known (pre-computed, deterministic — see sign.mjs) tx hash's receipt directly.
 * Idempotent: re-running this against the same real on-chain state returns the same verdict.
 */
export async function reconcileUnknownBurnOutcome({ txHash, getReceiptImpl }) {
  let receipt = null;
  try {
    receipt = await getReceiptImpl(txHash);
  } catch {
    receipt = null;
  }
  const decided = decideBaseReceiptOutcome(receipt);
  if (decided.outcome === "confirmed" || decided.outcome === "failed-onchain") {
    return { ...decided, source: "eth_getTransactionReceipt", retried: false };
  }
  return {
    outcome: "unknown-unresolved",
    source: "none",
    retried: false,
    reason: `tx ${txHash} outcome could not be confirmed via eth_getTransactionReceipt — refusing to blind-retry; reconcile manually (e.g. https://basescan.org/tx/${txHash}) before any further action`,
  };
}

/**
 * Poll the REAL Solana USDC balance at the destination address for the cross-chain credit — the
 * ultimate ground truth that the bridge actually delivered funds (spec: "it must poll for the
 * destination-side credit"). Bounded by timeoutMs; per spec "unknown is the normal case here, not
 * an edge case", so timing out is reported as `awaiting-credit`, NOT a failure — the burn already
 * happened (irreversibly, on Base) and this function has no send capability on either chain.
 *
 * @param {object} p
 * @param {() => Promise<number>} p.getSolanaUsdcBalanceImpl
 * @param {number} p.preBalance — USDC balance observed at the destination BEFORE the burn.
 * @param {number} p.minExpectedDelta — minimum balance increase that counts as "credited". Must be
 *   a positive number — a zero/negative threshold would treat "no change" as success.
 */
export async function pollForDestinationCredit({
  getSolanaUsdcBalanceImpl,
  preBalance,
  minExpectedDelta,
  sleepImpl,
  now = () => Date.now(),
  pollIntervalMs = 15000,
  timeoutMs = 3 * 60 * 1000,
}) {
  if (typeof minExpectedDelta !== "number" || !Number.isFinite(minExpectedDelta) || minExpectedDelta <= 0) {
    throw new Error("pollForDestinationCredit: minExpectedDelta must be a positive finite number (fail-closed — a zero threshold would treat no change as success)");
  }
  const start = now();
  // eslint-disable-next-line no-constant-condition
  while (true) {
    let balance = null;
    try {
      balance = await getSolanaUsdcBalanceImpl();
    } catch {
      balance = null;
    }
    if (typeof balance === "number" && typeof preBalance === "number") {
      const delta = balance - preBalance;
      if (delta >= minExpectedDelta) {
        return { outcome: "credited", delta, balance };
      }
    }
    if (now() - start >= timeoutMs) {
      return {
        outcome: "awaiting-credit",
        balance,
        reason:
          "destination-side USDC credit not yet observed within the poll window — this is the NORMAL case for this bridge (the CCTP destination-side finalize call is not submitted automatically by this build, see README's known gap), not a failure. The Base burn already happened (irreversible) and is never re-sent from here. Re-run this poll later, or complete the CCTP finalize step manually.",
      };
    }
    await sleepImpl(pollIntervalMs);
  }
}
