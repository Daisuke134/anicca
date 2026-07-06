// economy/gig/gig.mjs — SPEC.md §3 P2.2 orchestration: the 5 gig-board operations, combining the pure
// state machine (lib/store.mjs) with the real facilitator settle (lib/escrow.mjs) and fs persistence
// (lib/persist.mjs). This is what mcp-server.mjs exposes to Franklin and what scripts/e2e-testnet.mjs
// drives directly for the real on-chain proof.
//
// Escrow model (documented limitation, see README): GIG_ESCROW_PRIVATE_KEY is a custody keypair the
// gig-board process holds -- not a Solidity escrow contract. Fail-closed release is enforced in
// lib/store.mjs (applyVerifyAndPay refuses to mark 'paid' without a real payoutTx) and here (payout is
// only ever attempted when the poster's `verified` argument is exactly `true`).
import { payViaFacilitator } from "./lib/escrow.mjs";
import * as store from "./lib/store.mjs";
import { loadState, saveState } from "./lib/persist.mjs";

const DEFAULT_STATE_PATH = new URL("./state/gigs.json", import.meta.url).pathname;
const FACILITATOR_URL = process.env.GIG_FACILITATOR_URL || "http://127.0.0.1:8405";

function escrowAddress() {
  return process.env.GIG_ESCROW_ADDRESS || null;
}
function escrowPrivateKey() {
  return process.env.GIG_ESCROW_PRIVATE_KEY || null;
}

/**
 * gigPost — poster funds escrow NOW (real on-chain settle, poster -> escrow) then the gig is recorded
 * OPEN. Fail-closed: if the escrow-funding settle fails, NO gig is created (never a gig with a fake/
 * unfunded bounty).
 */
export async function gigPost({ posterPrivateKey, posterAddress, taskSpec, bountyUsdcBase, statePath = DEFAULT_STATE_PATH }) {
  const escrow = escrowAddress();
  if (!escrow) return { ok: false, reason: "GIG_ESCROW_ADDRESS not configured" };
  if (!Number.isInteger(bountyUsdcBase) || bountyUsdcBase <= 0) {
    return { ok: false, reason: `bountyUsdcBase must be a positive integer (USDC base units), got ${bountyUsdcBase}` };
  }
  const fund = await payViaFacilitator({ privateKey: posterPrivateKey, to: escrow, amountBase: bountyUsdcBase, facilitatorUrl: FACILITATOR_URL });
  if (!fund.ok) return { ok: false, stage: "escrow-fund", ...fund };
  const state = await loadState(statePath);
  const { gig, state: next } = store.applyPost(state, {
    poster: posterAddress || fund.payerAddress,
    taskSpec,
    bountyUsdcBase,
    escrowAddress: escrow,
    postTx: fund.tx,
  });
  await saveState(statePath, next);
  return { ok: true, gig };
}

export async function gigList({ status, statePath = DEFAULT_STATE_PATH } = {}) {
  const state = await loadState(statePath);
  return { ok: true, gigs: store.listGigs(state, { status }) };
}

export async function gigTake({ gigId, takerAddress, statePath = DEFAULT_STATE_PATH }) {
  const state = await loadState(statePath);
  const result = store.applyTake(state, gigId, takerAddress);
  if (!result.ok) return result;
  await saveState(statePath, result.state);
  return { ok: true, gig: result.gig };
}

export async function gigDeliver({ gigId, deliverable, statePath = DEFAULT_STATE_PATH }) {
  const state = await loadState(statePath);
  const result = store.applyDeliver(state, gigId, deliverable);
  if (!result.ok) return result;
  await saveState(statePath, result.state);
  return { ok: true, gig: result.gig };
}

/**
 * gigVerifyAndPay — the ONLY function that can move money out of escrow. `verified !== true` (poster
 * rejects) moves the gig to REJECTED, no payout, no exceptions. `verified === true` triggers a REAL
 * on-chain settle (escrow -> taker) via the facilitator; the gig is only marked 'paid' if that settle
 * actually succeeds (fail-closed both ways: no verify -> no pay, and a failed settle -> still no pay,
 * gig stays 'delivered' so a retry can be attempted).
 */
export async function gigVerifyAndPay({ gigId, verified, statePath = DEFAULT_STATE_PATH }) {
  const state = await loadState(statePath);
  const gig = store.getGig(state, gigId);
  if (!gig) return { ok: false, reason: `no such gig ${gigId}` };
  if (gig.status !== store.STATUS.DELIVERED) {
    return { ok: false, reason: `gig ${gigId} is '${gig.status}', not 'delivered' -- cannot verify/pay yet` };
  }
  if (verified !== true) {
    const result = store.applyVerifyAndPay(state, gigId, { verified: false });
    await saveState(statePath, result.state);
    return { ok: true, gig: result.gig, paid: false, reason: "poster rejected -- no payout (fail-closed)" };
  }
  const escrowKey = escrowPrivateKey();
  if (!escrowKey) return { ok: false, reason: "GIG_ESCROW_PRIVATE_KEY not configured -- cannot release escrow" };
  const payout = await payViaFacilitator({ privateKey: escrowKey, to: gig.taker, amountBase: gig.bountyUsdcBase, facilitatorUrl: FACILITATOR_URL });
  if (!payout.ok) {
    // fail-closed: gig stays 'delivered' (not marked paid) so verify_and_pay can be retried later.
    return { ok: false, stage: "escrow-release", gig, ...payout };
  }
  const result = store.applyVerifyAndPay(state, gigId, { verified: true, payoutTx: payout.tx });
  await saveState(statePath, result.state);
  return { ok: true, gig: result.gig, paid: true, tx: payout.tx };
}

export { registerIdentity, verifyIdentity } from "./lib/identity.mjs";
