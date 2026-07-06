// economy/gig/lib/store.mjs — SPEC.md §3 P2.2: pure state-transition functions for the gig board.
// No fs, no network, no private keys here -- unit-testable in complete isolation. gig.mjs is the ONLY
// caller that combines these transitions with real escrow settles (lib/escrow.mjs) + persistence
// (lib/persist.mjs), mirroring economy/ubi/ubi.js's split (pure decision vs. explicit execution).
//
// Lifecycle: open -> taken -> delivered -> paid | rejected. Every transition is a guarded, one-way
// door: you cannot take a gig that isn't open, deliver one that isn't taken, or verify/pay one that
// isn't delivered. Immutable: every function returns a NEW state object, never mutates its input
// (coding-style.md "Immutability (CRITICAL)").
//
// HARD RULE (spec §3 P2.2): escrow releases ONLY on verify. applyVerifyAndPay(verified:true) REFUSES
// to mark a gig 'paid' unless the caller already has a real payoutTx in hand (gig.mjs only calls this
// after lib/escrow.mjs's on-chain settle succeeds) -- this function never invents payment evidence.

const OPEN = "open";
const TAKEN = "taken";
const DELIVERED = "delivered";
const PAID = "paid";
const REJECTED = "rejected";

export const STATUS = { OPEN, TAKEN, DELIVERED, PAID, REJECTED };

export function emptyState() {
  return { nextId: 1, gigs: {} };
}

export function listGigs(state, { status } = {}) {
  const all = Object.values(state.gigs);
  return status ? all.filter((g) => g.status === status) : all;
}

export function getGig(state, gigId) {
  return state.gigs[gigId] || null;
}

/**
 * applyPost — create a new OPEN gig. Called by gig.mjs AFTER the poster's bounty has already been
 * settled into escrow on-chain (postTx is real evidence, not invented here).
 */
export function applyPost(state, { poster, taskSpec, bountyUsdcBase, escrowAddress, postTx }) {
  const id = String(state.nextId);
  const now = new Date().toISOString();
  const gig = {
    id,
    poster,
    taskSpec,
    bountyUsdcBase,
    escrowAddress,
    postTx,
    status: OPEN,
    taker: null,
    deliverable: null,
    verified: null,
    payoutTx: null,
    createdAt: now,
    updatedAt: now,
  };
  const next = { nextId: state.nextId + 1, gigs: { ...state.gigs, [id]: gig } };
  return { ok: true, state: next, gig };
}

export function applyTake(state, gigId, takerAddress) {
  const gig = state.gigs[gigId];
  if (!gig) return { ok: false, reason: `no such gig ${gigId}` };
  if (gig.status !== OPEN) {
    return { ok: false, reason: `gig ${gigId} is '${gig.status}', not 'open' -- cannot take` };
  }
  const updated = { ...gig, status: TAKEN, taker: takerAddress, updatedAt: new Date().toISOString() };
  const next = { ...state, gigs: { ...state.gigs, [gigId]: updated } };
  return { ok: true, state: next, gig: updated };
}

export function applyDeliver(state, gigId, deliverable) {
  const gig = state.gigs[gigId];
  if (!gig) return { ok: false, reason: `no such gig ${gigId}` };
  if (gig.status !== TAKEN) {
    return { ok: false, reason: `gig ${gigId} is '${gig.status}', not 'taken' -- cannot deliver` };
  }
  const updated = { ...gig, status: DELIVERED, deliverable, updatedAt: new Date().toISOString() };
  const next = { ...state, gigs: { ...state.gigs, [gigId]: updated } };
  return { ok: true, state: next, gig: updated };
}

/**
 * applyVerifyAndPay — the fail-closed gate. `verified:true` REQUIRES a non-empty `payoutTx` (proof an
 * on-chain escrow-release settle already happened) or this call is refused outright -- no state change,
 * no silent "paid" without evidence. `verified:false` moves the gig to REJECTED; no payoutTx is ever
 * recorded for a rejection.
 */
export function applyVerifyAndPay(state, gigId, { verified, payoutTx }) {
  const gig = state.gigs[gigId];
  if (!gig) return { ok: false, reason: `no such gig ${gigId}` };
  if (gig.status !== DELIVERED) {
    return { ok: false, reason: `gig ${gigId} is '${gig.status}', not 'delivered' -- cannot verify/pay yet` };
  }
  if (verified === true) {
    if (!payoutTx) {
      return {
        ok: false,
        reason: "verified=true requires a payoutTx -- refusing to mark paid without on-chain evidence (fail-closed)",
      };
    }
    const updated = { ...gig, status: PAID, verified: true, payoutTx, updatedAt: new Date().toISOString() };
    return { ok: true, state: { ...state, gigs: { ...state.gigs, [gigId]: updated } }, gig: updated };
  }
  const updated = { ...gig, status: REJECTED, verified: false, updatedAt: new Date().toISOString() };
  return { ok: true, state: { ...state, gigs: { ...state.gigs, [gigId]: updated } }, gig: updated };
}
