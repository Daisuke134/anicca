// economy/gig/gig.mjs — SPEC.md §3 P2.2 orchestration: the 5 gig-board operations, combining the pure
// state machine (lib/store.mjs) with the real facilitator settle (lib/escrow.mjs), ERC-8004 identity
// checks (lib/identity.mjs), a per-gig file lock (lib/lock.mjs), and fs persistence (lib/persist.mjs).
// This is what mcp-server.mjs exposes to Franklin and what scripts/e2e-testnet.mjs drives directly.
//
// SECURITY FIXES (adversary round 1, real live drains -- see
// .vcsdd/features/anicca-agent-economy/evidence/p2.2-security-fixes.md):
//   FINDING 1 (no poster auth): gigVerifyAndPay used to accept `verified` from ANY caller with no proof
//     they were the poster -- an attacker who merely took+delivered a gig could call
//     verify_and_pay(true) on themselves and drain the escrow (real tx 0x78111fa...). FIXED: the caller
//     must now supply `posterPrivateKey`; we derive its address (same primitive gig_post already uses
//     to establish the poster's identity) and REFUSE unless it equals gig.poster.
//   FINDING 2 (double-pay race): concurrent verify_and_pay(true) calls on ONE gig both read 'delivered'
//     before either wrote back, both settled a real payout (tx 0xd0af29c3 + 0x6573886b), and the JSON
//     ledger only recorded one (last-write-wins) -- the escrow was drained twice. FIXED: the entire
//     load -> decide -> settle -> save sequence for gigTake/gigDeliver/gigVerifyAndPay now runs inside
//     withGigLock(gigId) -- a concurrent call for the SAME gig is rejected immediately (fail-closed,
//     never queued), so at most one call ever reaches a real settle.
//   FINDING 3 (ERC-8004 decorative): identity registration worked but nothing in the gig lifecycle ever
//     checked it. FIXED: gigPost requires `posterAgentId` (verified against the poster's own derived
//     address); gigTake requires `takerAgentId` (verified against takerAddress); gigVerifyAndPay
//     RE-verifies the taker's identity at payout time (not just at take time) before releasing funds.
//
// Escrow model (documented limitation, see README): GIG_ESCROW_PRIVATE_KEY is a custody keypair the
// gig-board process holds -- not a Solidity escrow contract. Fail-closed release is enforced in
// lib/store.mjs (applyVerifyAndPay refuses to mark 'paid' without a real payoutTx) and here (payout is
// only attempted when: caller proved poster identity, gig is 'delivered', taker identity re-verified,
// and `verified` is exactly `true`).
//
// Dependency injection: `pay` and `verifyIdentityFn` default to the REAL network implementations
// (lib/escrow.mjs, lib/identity.mjs) for production/E2E use. Tests override them with fast, deterministic
// fakes to exercise the orchestration logic (auth, locking, identity gating) without touching the
// network or real testnet funds -- the fakes replace EXTERNAL I/O only, never our own decision logic.
import { privateKeyToAccount } from "viem/accounts";
import { payViaFacilitator } from "./lib/escrow.mjs";
import { verifyIdentity as verifyIdentityReal } from "./lib/identity.mjs";
import * as store from "./lib/store.mjs";
import { loadState, saveState } from "./lib/persist.mjs";
import { withGigLock } from "./lib/lock.mjs";

const DEFAULT_STATE_PATH = new URL("./state/gigs.json", import.meta.url).pathname;
const FACILITATOR_URL = process.env.GIG_FACILITATOR_URL || "http://127.0.0.1:8405";
const POST_LOCK_KEY = "_post"; // guards the shared nextId counter against concurrent gig_post calls

function escrowAddress() {
  return process.env.GIG_ESCROW_ADDRESS || null;
}
function escrowPrivateKey() {
  return process.env.GIG_ESCROW_PRIVATE_KEY || null;
}

/**
 * gigPost — poster funds escrow NOW (real on-chain settle, poster -> escrow) then the gig is recorded
 * OPEN. Requires `posterAgentId`: a valid ERC-8004 identity owned by the poster's own derived address
 * (finding 3). Fail-closed: if identity verification OR the escrow-funding settle fails, NO gig is
 * created. Wrapped in the shared "_post" lock so concurrent posts can't race the nextId counter.
 */
export async function gigPost({
  posterPrivateKey,
  posterAgentId,
  taskSpec,
  bountyUsdcBase,
  statePath = DEFAULT_STATE_PATH,
  pay = payViaFacilitator,
  verifyIdentityFn = verifyIdentityReal,
}) {
  const escrow = escrowAddress();
  if (!escrow) return { ok: false, reason: "GIG_ESCROW_ADDRESS not configured" };
  if (!Number.isInteger(bountyUsdcBase) || bountyUsdcBase <= 0) {
    return { ok: false, reason: `bountyUsdcBase must be a positive integer (USDC base units), got ${bountyUsdcBase}` };
  }
  if (!posterAgentId) return { ok: false, reason: "posterAgentId required (ERC-8004 identity, fail-closed)" };
  const posterAddress = privateKeyToAccount(posterPrivateKey).address;
  const idCheck = await verifyIdentityFn({ agentId: posterAgentId, expectedAddress: posterAddress });
  if (!idCheck.ok || !idCheck.valid) {
    return { ok: false, reason: `poster ERC-8004 identity invalid for agentId ${posterAgentId}: ${idCheck.reason || "ownerOf mismatch"}` };
  }
  return withGigLock(statePath, POST_LOCK_KEY, async () => {
    const fund = await pay({ privateKey: posterPrivateKey, to: escrow, amountBase: bountyUsdcBase, facilitatorUrl: FACILITATOR_URL });
    if (!fund.ok) return { ok: false, stage: "escrow-fund", ...fund };
    const state = await loadState(statePath);
    const { gig, state: next } = store.applyPost(state, {
      poster: posterAddress,
      posterAgentId,
      taskSpec,
      bountyUsdcBase,
      escrowAddress: escrow,
      postTx: fund.tx,
    });
    await saveState(statePath, next);
    return { ok: true, gig };
  });
}

export async function gigList({ status, statePath = DEFAULT_STATE_PATH } = {}) {
  const state = await loadState(statePath);
  return { ok: true, gigs: store.listGigs(state, { status }) };
}

/**
 * gigTake — claim an OPEN gig. Requires `takerAgentId`: a valid ERC-8004 identity owned by
 * `takerAddress` (finding 3). Wrapped in the per-gigId lock (finding 2) so two concurrent takes for the
 * same gig can't both succeed.
 */
export async function gigTake({ gigId, takerAddress, takerAgentId, statePath = DEFAULT_STATE_PATH, verifyIdentityFn = verifyIdentityReal }) {
  if (!takerAgentId) return { ok: false, reason: "takerAgentId required (ERC-8004 identity, fail-closed)" };
  const idCheck = await verifyIdentityFn({ agentId: takerAgentId, expectedAddress: takerAddress });
  if (!idCheck.ok || !idCheck.valid) {
    return { ok: false, reason: `taker ERC-8004 identity invalid for agentId ${takerAgentId}: ${idCheck.reason || "ownerOf mismatch"}` };
  }
  return withGigLock(statePath, gigId, async () => {
    const state = await loadState(statePath);
    const result = store.applyTake(state, gigId, takerAddress, takerAgentId);
    if (!result.ok) return result;
    await saveState(statePath, result.state);
    return { ok: true, gig: result.gig };
  });
}

export async function gigDeliver({ gigId, deliverable, statePath = DEFAULT_STATE_PATH }) {
  return withGigLock(statePath, gigId, async () => {
    const state = await loadState(statePath);
    const result = store.applyDeliver(state, gigId, deliverable);
    if (!result.ok) return result;
    await saveState(statePath, result.state);
    return { ok: true, gig: result.gig };
  });
}

/**
 * gigVerifyAndPay — the ONLY function that can move money out of escrow.
 *
 * AUTH (finding 1): the caller must supply `posterPrivateKey`; its derived address must equal
 * gig.poster or the call is rejected outright -- a taker, an attacker, or anyone else can never verify
 * their own delivery.
 * LOCK (finding 2): the entire load -> decide -> settle -> save sequence runs inside
 * withGigLock(gigId); a concurrent call for the same gig is rejected immediately, never queued, so at
 * most one call ever reaches a real settle.
 * IDENTITY (finding 3): before releasing funds, the taker's ERC-8004 identity is RE-verified (not just
 * trusted from take-time) -- if it's no longer valid, no payout.
 *
 * `verified !== true` (poster rejects) moves the gig to REJECTED, no payout, no exceptions.
 * `verified === true` triggers a REAL on-chain settle (escrow -> taker); the gig is only marked 'paid'
 * if that settle actually succeeds (a failed settle leaves the gig 'delivered' so it can be retried).
 */
export async function gigVerifyAndPay({
  gigId,
  verified,
  posterPrivateKey,
  statePath = DEFAULT_STATE_PATH,
  pay = payViaFacilitator,
  verifyIdentityFn = verifyIdentityReal,
}) {
  return withGigLock(statePath, gigId, async () => {
    const state = await loadState(statePath);
    const gig = store.getGig(state, gigId);
    if (!gig) return { ok: false, reason: `no such gig ${gigId}` };
    if (gig.status !== store.STATUS.DELIVERED) {
      return { ok: false, reason: `gig ${gigId} is '${gig.status}', not 'delivered' -- cannot verify/pay yet` };
    }

    // FINDING 1: only the real poster (proven by deriving the address from their own private key,
    // the same primitive gig_post uses to establish identity) may verify/pay this gig.
    if (!posterPrivateKey) {
      return { ok: false, reason: "posterPrivateKey required -- only the gig's poster can verify/pay (fail-closed)" };
    }
    const callerAddress = privateKeyToAccount(posterPrivateKey).address;
    if (callerAddress.toLowerCase() !== gig.poster.toLowerCase()) {
      return { ok: false, reason: `caller ${callerAddress} is not the poster of gig ${gigId} (${gig.poster}) -- rejected, fail-closed` };
    }

    if (verified !== true) {
      const result = store.applyVerifyAndPay(state, gigId, { verified: false });
      await saveState(statePath, result.state);
      return { ok: true, gig: result.gig, paid: false, reason: "poster rejected -- no payout (fail-closed)" };
    }

    // FINDING 3: re-verify the taker's identity at payout time, not just at take time.
    const idCheck = await verifyIdentityFn({ agentId: gig.takerAgentId, expectedAddress: gig.taker });
    if (!idCheck.ok || !idCheck.valid) {
      return { ok: false, reason: `taker ERC-8004 identity invalid at payout time for agentId ${gig.takerAgentId}: ${idCheck.reason || "ownerOf mismatch"}` };
    }

    const escrowKey = escrowPrivateKey();
    if (!escrowKey) return { ok: false, reason: "GIG_ESCROW_PRIVATE_KEY not configured -- cannot release escrow" };
    const payout = await pay({ privateKey: escrowKey, to: gig.taker, amountBase: gig.bountyUsdcBase, facilitatorUrl: FACILITATOR_URL });
    if (!payout.ok) {
      // fail-closed: gig stays 'delivered' (not marked paid) so verify_and_pay can be retried later.
      return { ok: false, stage: "escrow-release", gig, ...payout };
    }
    const result = store.applyVerifyAndPay(state, gigId, { verified: true, payoutTx: payout.tx });
    await saveState(statePath, result.state);
    return { ok: true, gig: result.gig, paid: true, tx: payout.tx };
  });
}

export { registerIdentity, verifyIdentity } from "./lib/identity.mjs";
