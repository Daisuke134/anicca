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
// SECURITY FIXES (adversary round 2, 2026-07-07 -- 2 residual concurrency gaps, not fund-theft but real
// data-loss bugs waiting to bite once automaton + Franklin are separate concurrent launchd loops):
//   GAP 1 (stale-lock steal): see lib/lock.mjs -- a live holder now heartbeats its lock so it's never
//     mistaken for a crashed one, however long its settle legitimately takes.
//   GAP 2 (cross-gig shared-state clobber): the per-gigId lock never protected the SHARED state file --
//     a slow operation on gig X would load a stale full-board snapshot, and its LATE save (after its
//     slow network step) would overwrite the ENTIRE file, silently reverting a concurrent gig_take on
//     an unrelated gig Y back to 'open'. FIXED: `applyAndSave()` below re-reads the board FRESH from
//     disk immediately before every mutation+save, inside a dedicated global "_board" lock -- so no
//     write can ever be computed from data older than the moment it's about to be persisted. The
//     (possibly slow) network step still only holds the per-gigId/"_post" lock; the board lock is held
//     only for the brief, local read-mutate-write, preserving throughput across unrelated gigs.
//
// anicca-agent-economy REQ-102 (Phase 2b, GREEN -- a genuine new finding from the Phase 2a RED evidence,
// see evidence/sprint-1-red-phase.log §2): extending GAP 2's 2-gigId scenario to THREE OR MORE distinct,
// FAST, concurrent gigIds reproducibly rejected one of them outright -- the shared "_board" lock is the
// SAME fail-closed, non-queueing primitive as the per-gigId locks, so two unrelated gigIds' board-lock
// acquisitions landing in the same instant made one lose with no retry, even though nothing about
// fund-safety required that rejection (only ONE gigId's lock -- the one actually being mutated -- needs
// to stay strictly fail-closed for fund-safety; REQ-103's double-pay/self-verify tests exercise THAT
// lock, never the shared board lock). FIX: `applyAndSave()` below retries its OWN acquisition of the
// "_board" lock with a short, bounded backoff -- safe specifically because the board lock's own critical
// section is brief (a local read-mutate-write; the slow network settle already completed before
// `applyAndSave` is ever called) and holds no funds-moving side effect of its own. This retry is added
// ONLY around the "_board" lock in `applyAndSave`; `withGigLock`'s general per-gigId/`"_post"` behavior
// (lib/lock.mjs) is untouched and remains fail-closed/non-queueing, preserving every REQ-103 invariant
// (a genuine SAME-gigId double-pay attempt must still be rejected outright, never retried into a second
// settle).
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
// `lockConfig` similarly defaults to lib/lock.mjs's production staleMs/heartbeatMs; tests inject tiny
// values so lock-contention/staleness scenarios run in milliseconds, not minutes.
import { privateKeyToAccount } from "viem/accounts";
import { payViaFacilitator } from "./lib/escrow.mjs";
import { verifyIdentity as verifyIdentityReal } from "./lib/identity.mjs";
import * as store from "./lib/store.mjs";
import { loadState, saveState } from "./lib/persist.mjs";
import { withGigLock } from "./lib/lock.mjs";

// GIG_STATE_PATH override: without it, DEFAULT_STATE_PATH resolves next to THIS module file, which is
// fine for a single-copy dev/testnet run but WRONG once automaton and Franklin each get their own
// separate on-disk copy of this skill (see WITNESS-RUNBOOK.md) -- two independent state/gigs.json files
// would mean each instance only ever sees gigs it posted itself, never a real marketplace. Both
// deployed copies must set GIG_STATE_PATH to the SAME shared path for cross-agent trades to work.
const DEFAULT_STATE_PATH = process.env.GIG_STATE_PATH || new URL("./state/gigs.json", import.meta.url).pathname;
const FACILITATOR_URL = process.env.GIG_FACILITATOR_URL || "http://127.0.0.1:8405";
const POST_LOCK_KEY = "_post"; // guards the shared nextId counter against concurrent gig_post calls
const BOARD_LOCK_KEY = "_board"; // guards the shared state file's actual read-mutate-write (GAP 2)
// REQ-102: bounded retry knobs for the shared "_board" lock ONLY (see the header comment above) -- brief
// enough that they never meaningfully delay a genuinely uncontended write, but wide enough to absorb two
// or three FAST, unrelated gigIds' board-lock acquisitions landing in the same instant.
const BOARD_LOCK_RETRY_ATTEMPTS = 40;
const BOARD_LOCK_RETRY_DELAY_MS = 5;
const BOARD_LOCK_CONTENDED_REASON = `'${BOARD_LOCK_KEY}' is currently being processed by another call`;

function escrowAddress() {
  return process.env.GIG_ESCROW_ADDRESS || null;
}
function escrowPrivateKey() {
  return process.env.GIG_ESCROW_PRIVATE_KEY || null;
}

/**
 * applyAndSave — the ONLY place that ever writes state to disk. Re-reads the board FRESH from disk
 * (never reusing an earlier, possibly-stale snapshot from before a slow network step), applies a pure
 * lib/store.mjs transition to that fresh read, and saves -- all inside the global "_board" lock, so a
 * concurrent write for a DIFFERENT gig can never be clobbered by this one (GAP 2). `mutateFn` is one of
 * lib/store.mjs's transition functions bound to its specific args; it returns lib/store.mjs's own
 * `{ok, state, gig}` / `{ok:false, reason}` shape, which callers pass straight back to their caller
 * on failure.
 */
async function applyAndSave(statePath, mutateFn, lockConfig) {
  for (let attempt = 0; attempt < BOARD_LOCK_RETRY_ATTEMPTS; attempt++) {
    const outcome = await withGigLock(
      statePath,
      BOARD_LOCK_KEY,
      async () => {
        const state = await loadState(statePath); // always the freshest on-disk state at write time
        const result = mutateFn(state);
        if (result.ok) await saveState(statePath, result.state);
        return result;
      },
      lockConfig
    );
    const lostBoardLockRace = outcome.ok === false && typeof outcome.reason === "string" && outcome.reason.startsWith(BOARD_LOCK_CONTENDED_REASON);
    if (!lostBoardLockRace) return outcome; // real success, OR a real business-logic/fund-safety rejection -- never retried
    // The shared board lock's own critical section is brief and safe to retry (see header comment) --
    // unlike a per-gigId lock loss, which must stay a real rejection for fund-safety.
    await new Promise((r) => setTimeout(r, BOARD_LOCK_RETRY_DELAY_MS));
  }
  return { ok: false, reason: `${BOARD_LOCK_CONTENDED_REASON} -- rejected after ${BOARD_LOCK_RETRY_ATTEMPTS} bounded retries (fail-closed)` };
}

/**
 * gigPost — poster funds escrow NOW (real on-chain settle, poster -> escrow) then the gig is recorded
 * OPEN. Requires `posterAgentId`: a valid ERC-8004 identity owned by the poster's own derived address
 * (finding 3). Fail-closed: if identity verification OR the escrow-funding settle fails, NO gig is
 * created. Wrapped in the shared "_post" lock so concurrent posts can't race each other's network step;
 * the actual write goes through applyAndSave's "_board" lock (GAP 2).
 */
export async function gigPost({
  posterPrivateKey,
  posterAgentId,
  taskSpec,
  bountyUsdcBase,
  statePath = DEFAULT_STATE_PATH,
  pay = payViaFacilitator,
  verifyIdentityFn = verifyIdentityReal,
  lockConfig = {},
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
  return withGigLock(
    statePath,
    POST_LOCK_KEY,
    async () => {
      const fund = await pay({ privateKey: posterPrivateKey, to: escrow, amountBase: bountyUsdcBase, facilitatorUrl: FACILITATOR_URL });
      if (!fund.ok) return { ok: false, stage: "escrow-fund", ...fund };
      const result = await applyAndSave(
        statePath,
        (state) =>
          store.applyPost(state, {
            poster: posterAddress,
            posterAgentId,
            taskSpec,
            bountyUsdcBase,
            escrowAddress: escrow,
            postTx: fund.tx,
          }),
        lockConfig
      );
      return result.ok ? { ok: true, gig: result.gig } : result;
    },
    lockConfig
  );
}

export async function gigList({ status, statePath = DEFAULT_STATE_PATH } = {}) {
  const state = await loadState(statePath);
  return { ok: true, gigs: store.listGigs(state, { status }) };
}

/**
 * gigTake — claim an OPEN gig. Requires `takerAgentId`: a valid ERC-8004 identity owned by
 * `takerAddress` (finding 3). Wrapped in the per-gigId lock (finding 2) so two concurrent takes for the
 * same gig can't both succeed; the actual write goes through applyAndSave's "_board" lock (GAP 2) so an
 * unrelated gig's concurrent write can never clobber this one.
 */
export async function gigTake({ gigId, takerAddress, takerAgentId, statePath = DEFAULT_STATE_PATH, verifyIdentityFn = verifyIdentityReal, lockConfig = {} }) {
  if (!takerAgentId) return { ok: false, reason: "takerAgentId required (ERC-8004 identity, fail-closed)" };
  const idCheck = await verifyIdentityFn({ agentId: takerAgentId, expectedAddress: takerAddress });
  if (!idCheck.ok || !idCheck.valid) {
    return { ok: false, reason: `taker ERC-8004 identity invalid for agentId ${takerAgentId}: ${idCheck.reason || "ownerOf mismatch"}` };
  }
  return withGigLock(
    statePath,
    gigId,
    async () => {
      const result = await applyAndSave(statePath, (state) => store.applyTake(state, gigId, takerAddress, takerAgentId), lockConfig);
      return result.ok ? { ok: true, gig: result.gig } : result;
    },
    lockConfig
  );
}

export async function gigDeliver({ gigId, deliverable, statePath = DEFAULT_STATE_PATH, lockConfig = {} }) {
  return withGigLock(
    statePath,
    gigId,
    async () => {
      const result = await applyAndSave(statePath, (state) => store.applyDeliver(state, gigId, deliverable), lockConfig);
      return result.ok ? { ok: true, gig: result.gig } : result;
    },
    lockConfig
  );
}

/**
 * gigVerifyAndPay — the ONLY function that can move money out of escrow.
 *
 * AUTH (finding 1): the caller must supply `posterPrivateKey`; its derived address must equal
 * gig.poster or the call is rejected outright -- a taker, an attacker, or anyone else can never verify
 * their own delivery.
 * LOCK (finding 2 / GAP 1): the entire load -> decide -> settle sequence runs inside
 * withGigLock(gigId), heartbeated so a live holder's settle -- however slow -- is never mistaken for a
 * crashed one and stolen out from under it; a concurrent call for the same gig is rejected immediately,
 * never queued, so at most one call ever reaches a real settle.
 * WRITE (GAP 2): the final state mutation goes through applyAndSave, which re-reads the board fresh
 * from disk under the global "_board" lock immediately before writing -- so this gig's (possibly slow)
 * settle can never clobber an unrelated gig's concurrent, already-persisted change.
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
  lockConfig = {},
}) {
  return withGigLock(
    statePath,
    gigId,
    async () => {
      // Pre-check snapshot: used only to fail fast (missing gig, wrong status, wrong caller) before
      // spending a network call. The AUTHORITATIVE check+write happens again, fresh, in applyAndSave --
      // store.mjs's own guards re-validate status there too, so a stale pre-check can never result in
      // an incorrect write (it can only cause an unnecessary network call to be attempted, which then
      // fails cleanly at the fresh-write stage).
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
        const result = await applyAndSave(statePath, (freshState) => store.applyVerifyAndPay(freshState, gigId, { verified: false }), lockConfig);
        if (!result.ok) return result;
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
      const result = await applyAndSave(
        statePath,
        (freshState) => store.applyVerifyAndPay(freshState, gigId, { verified: true, payoutTx: payout.tx }),
        lockConfig
      );
      if (!result.ok) return result;
      return { ok: true, gig: result.gig, paid: true, tx: payout.tx };
    },
    lockConfig
  );
}

export { registerIdentity, verifyIdentity } from "./lib/identity.mjs";
