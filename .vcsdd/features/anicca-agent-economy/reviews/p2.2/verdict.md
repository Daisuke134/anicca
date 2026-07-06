# P2.2 gig-board — fresh-context adversary verdict (disk + live re-execution)

**date**: 2026-07-07 · **reviewer**: fresh Sonnet VCSDD adversary, zero builder context
**artifacts reviewed**: `~/anicca/.worktrees/agent-economy` @ `19ec3f8`, `skills/economy/gig/**`
**method**: read all source, ran the real unit tests, verified all 3 claimed tx hashes on-chain via
public RPC (read-only), then **actively attacked the live testnet deployment** (facilitator running at
127.0.0.1:8405, real base-sepolia contracts) using the project's own test credentials
(`~/.anicca-signing/{x402-facilitator,gig-board}/.env`). All reproductions below are real on-chain
transactions, not simulations — tx hashes included.

## Overall verdict: **FAIL** (critical fund-safety fail-open, confirmed live twice)

## Per-dimension

| dimension | verdict | evidence |
|---|---|---|
| **escrow-no-fail-open** | **FAIL (critical)** | Two independent, live, on-chain reproductions. See §1 and §2 below. |
| **custody-key-safe** | **FAIL** | Key itself is not committed (PASS on that narrow check), but the software gating the README claims compensates for the custody model does not exist for the one operation that matters. See §3. |
| **erc8004-real** | PASS | `register()`/`ownerOf()` are real, live, un-spoofable on-chain calls. See §4. |
| **mcp-tool-contracts** | **FAIL (critical)** | `gig_verify_and_pay`'s tool description ("Poster-only") is false — the implementation enforces no caller identity at all. See §1. |
| **e2e-reproduces** | PASS | All 3 claimed tx hashes are real, mined, successful (`status:"0x1"`) on Base Sepolia. The loop mechanically works exactly as documented. See §5. |
| **test-integrity** | **FAIL (coverage gap, not fabrication)** | The 10/10 tests are genuinely real (re-ran them myself, identical result) and the RED→GREEN guard demonstration is legitimate — but every test targets `lib/store.mjs` (pure functions) only. Zero tests exist for `gig.mjs`, which is where both critical vulnerabilities below actually live. "10/10 green" does not and cannot catch either bug. See §6. |

---

## §1. CRITICAL: `gig_verify_and_pay` has no poster authentication — anyone can self-verify and drain escrow to an address of their choosing

The brief asked: "can escrowed funds be released to a taker WITHOUT a genuine poster verify?" **Yes,
trivially, and I proved it live.**

`gig.mjs:77` (`gigVerifyAndPay`) and the MCP tool `gig_verify_and_pay`
(`mcp-server.mjs:79-93`) take only `{ gigId, verified }`. There is no poster private key, no signature,
no check against `gig.poster` anywhere in `gig.mjs`, `lib/store.mjs`, or `mcp-server.mjs`. The tool's own
description literally says *"Poster-only: approve or reject a delivered gig"* — that claim is false; the
code enforces nothing of the kind. Combined with `gig_take` also accepting an arbitrary
`takerAddress` string with no signature proof of control, **any caller with access to this MCP server
can steal any open gig's bounty**:

1. `gig_list` → find an open gig posted by someone else.
2. `gig_take(gigId, takerAddress = <attacker's own address>)` — no proof required.
3. `gig_deliver(gigId, deliverable = "garbage")` — no review gate.
4. `gig_verify_and_pay(gigId, verified: true)` — called by the **attacker**, not the poster.

**Live reproduction** (script:
`/private/tmp/claude-501/-Users-anicca-anicca-project/a5e7d2ee-7172-4857-8f3d-ba2edbb855fd/scratchpad/adversary-fail-open-test.mjs`,
run against the live facilitator + live ERC-8004 registry, real base-sepolia poster
`0xDE6CAF...9742`, freshly generated attacker address `0xC7D7deC0BE728D930D777aAec5afe114E197D8C1`
that had **never touched this system before**):

```
gig_post  (legit poster funds escrow)         tx 0x923f3595...43d7b88
gig_take  (ATTACKER claims it under own addr) ok, no auth check
gig_deliver (attacker submits garbage)        ok, no review gate
gig_verify_and_pay (ATTACKER calls it themselves, not poster) -> paid:true
  payout tx 0x78111fa62b82d9e94b2f7609cca40592e7cd824991c4a3667cf99b6572e68555
```

Confirmed on-chain independently (public RPC, `eth_getTransactionReceipt` → `status:"0x1"`, and
`balanceOf(attacker)` on the USDC contract): **the attacker address's on-chain USDC balance went from 0
to 1000 base units**, funds that came directly out of the gig-board's escrow, with zero involvement from
the real poster after the initial `gig_post`.

This is not a theoretical gap — it is the entire trust model of the escrow (§3 of the assignment: "was
this released without a genuine poster verify") failing open on the very first adversarial probe.

## §2. CRITICAL: no lock/compare-and-set around `gigVerifyAndPay` → concurrent calls double-pay the same gig from the same escrow

`gig.mjs:77-99` does `loadState()` (fresh `fs.readFile` + `JSON.parse`) → `payViaFacilitator()` (a
network round-trip that includes `publicClient.waitForTransactionReceipt()`, i.e. a real multi-second
wait for on-chain confirmation — the exact race window the builder's own evidence already flagged for
the *post→release* ordering) → `store.applyVerifyAndPay(state, ...)` using the **state object loaded
before the wait** → `saveState()` (full-file overwrite, last-write-wins, no version check). There is no
file lock, no atomic check-and-set, nothing serializing two calls against the same `gigId`.

**Live reproduction** (script: `.../scratchpad/double-pay-race-test.mjs`): posted a fresh gig (bounty
1000 base units), took + delivered it, then fired **two concurrent**
`gigVerifyAndPay({ gigId, verified: true })` calls via `Promise.all`. Both calls independently loaded the
same `'delivered'` state, both proceeded to a real settle, and **both succeeded with two distinct,
real, mined on-chain tx hashes**:

```
call A: paid:true tx 0xd0af29c3c0c119d62f32c48c3e63273db0344fb58fbc68962afd9c03ef59fc08
call B: paid:true tx 0x6573886bc22ac7a39ce9e22db0ed1864a5c32b83227563d3dcd8b794018f7e54
```

On-chain confirmation after the run: escrow balance went **2000 → 0** (fully drained), taker balance
increased by **2000** — a single 1000-unit bounty paid out **twice** for one piece of (fabricated) work.

A second, independent bug surfaced as a side effect: because `saveState` is a full-object overwrite and
one call's write clobbers the other's, the persisted `state/gigs.json` for this gig now records **only
one** `payoutTx` even though **two real on-chain transfers happened** — the off-chain ledger silently
diverges from on-chain reality after the very race the escrow model depends on for correctness. This
means the gig board's own bookkeeping cannot be trusted to reflect true payout history once any
concurrency occurs.

Both §1 and §2 are independently sufficient to drain the entire escrow; together they mean **the
custody-keypair escrow currently has zero effective access control on the release path** — worse than
the honestly-documented "no Solidity contract" limitation, because the README's compensating claim
("fail-closed release is enforced in software... in `gig.mjs`") is not true for either "who is allowed to
call verify" or "how many times can a payout happen."

## §3. Custody-key model

- **Key hygiene: PASS on its own terms.** `grep -rn "GIG_ESCROW_PRIVATE_KEY\s*="` across the tracked
  tree finds only the `0xREPLACE_ME` placeholder in `.env.example`. The real key lives at
  `~/.anicca-signing/gig-board/.env`, confirmed **not inside any git repository**
  (`git rev-parse --is-inside-work-tree` → "fatal: not a git repository"). `state/gigs.json` matches the
  existing `.gitignore` pattern `skills/*/*/state/`. No leak found.
- **Trust/centralization assessment: this is not merely an "upgrade later" limitation as framed in the
  README.** A single process holding a hot key that can move 100% of escrowed funds is an acceptable
  MVP trade-off **only if the software logic gating release is airtight**. It is not (§1, §2). The
  README's own honesty section undersells this: it frames the gap as "no Solidity escrow contract" when
  the actual, more urgent gap is "no authorization check of any kind on the one function that spends the
  custody key," which is a correctness bug, not a documented architecture trade-off.

## §4. ERC-8004 identity — real, but not wired into the gig trust flow

Re-ran independently:
- `registerIdentity()` against a fresh key with 0 ETH → correctly fails closed:
  `{"ok":false,"reason":"Execution reverted with reason: gas required exceeds allowance (0)."}` (real
  chain rejection, not swallowed).
- `verifyIdentity({agentId:'8', expectedAddress:<real owner>})` → `valid:true`.
- `verifyIdentity({agentId:'8', expectedAddress:<attacker address>})` (spoof attempt) → `valid:false`,
  returns the **real** owner address. Not spoofable — `ownerOf()` is a genuine on-chain read.

All three of the evidence doc's claimed identity/gig tx hashes were independently verified via public
RPC `eth_getTransactionReceipt` (not trusting the builder's log): agentId-8 register
(`0x5f6ef20a...bcc4e6b`), agentId-9 register (`0x7a76e308...459fe36`), and the `gig_post` escrow-fund
(`0xaceb134d...1e5ea44`) — all `status:"0x1"`, all with `Transfer`/`Registered` event logs matching the
claimed amounts/agentIds exactly. **erc8004-real: PASS**, this part of the evidence is genuine.

However: `gig.mjs`'s five gig operations (`gigPost`/`gigTake`/`gigDeliver`/`gigVerifyAndPay`) **never
call `verifyIdentity`**. Identity registration/verification exist as two disconnected tools sitting next
to the gig board, not as a gate inside it. SPEC.md §3 P2's verification bullet says "双方 ERC-8004
identity" as part of what's proven — technically both parties CAN register, but the gig lifecycle does
not require or check either party's identity at any step. Given §1's finding (anyone can `gig_take` any
gig under any address with zero identity proof), ERC-8004 currently provides no actual protection for
"見知らぬ agent 同士でも trade 可" (strangers can trade safely) — it's decorative relative to the gig
flow as shipped.

## §5. E2E reproduction

The original evidence's 3 tx hashes verified independently as real, mined, successful on Base Sepolia
(see §4). Ran `node --test __tests__/store.test.mjs` myself: 10/10 pass, identical to the claimed
result. The mechanical loop (post→take→deliver→verify_and_pay→gasless payout) genuinely works as
described — my own two adversarial scripts each completed the full loop successfully on the first try,
which is itself further proof the mechanics are real (not flaky, not mocked). **e2e-reproduces: PASS**
on the narrow "does the claimed evidence check out" question; the problem is what the loop *doesn't*
check (§1, §2), not whether it runs.

## §6. Test-integrity

The unit tests are real — I ran them and got the identical 10/10 result the evidence doc claims, and the
"remove the guard, watch it fail, restore it, watch it pass" RED→GREEN discipline described is a
legitimate way to prove a test isn't tautological. No fabrication found here.

But scope: `__tests__/store.test.mjs` imports only `../lib/store.mjs` — pure, in-memory, no fs, no
network, no auth. **`gig.mjs` (the orchestration layer, the only place a poster-authorization check or a
concurrency lock could ever live) has zero test coverage.** The "★core★ fail-closed" test the evidence
doc highlights only proves "you can't fabricate a `payoutTx` string out of thin air" — it says nothing
about "only the poster can trigger a payout" or "concurrent calls can't double-spend," which are exactly
the two ways this system actually fails. A green test suite created false confidence about the security
properties that matter most. **test-integrity: FAIL** (as a signal for "was this MVP actually verified
end-to-end for the properties that matter" — not as an accusation that the tests themselves are fake).

---

## What needs to happen before this can ship (even as an internal-only MVP)

1. `gig_verify_and_pay` MUST authenticate the caller as the actual poster (e.g. require the poster's
   private key to sign a message/authorization the same way `gig_post` already does via
   `payViaFacilitator`'s EIP-3009 signature — reuse that exact pattern instead of a bare boolean) before
   any payout is attempted. Zero exceptions.
2. `gigVerifyAndPay` (and ideally `gigTake`/`gigDeliver`) need a per-`gigId` lock (file lock, atomic
   rename-based compare-and-set, or an in-process mutex map keyed by `gigId`) so two concurrent calls
   against the same gig cannot both pass the `status === DELIVERED` check before either writes back.
3. Given #1 and #2 are both about "money can leave escrow," add orchestration-layer tests (not just
   `store.mjs` unit tests) that assert: (a) a non-poster caller cannot trigger payout, (b) two concurrent
   verify_and_pay calls on one gig cannot both succeed.
4. Either wire `verifyIdentity()` into `gigTake`/`gigVerifyAndPay` as an actual gate, or stop describing
   ERC-8004 as part of what "見知らぬ agent 同士でも trade 可" proves for this sub-task — right now it's
   two unconnected, correctly-working tools bolted next to a board that doesn't call them.

## Artifacts

- Reproduction scripts (kept for reference, not committed to any repo):
  `/private/tmp/claude-501/-Users-anicca-anicca-project/a5e7d2ee-7172-4857-8f3d-ba2edbb855fd/scratchpad/adversary-fail-open-test.mjs`
  `/private/tmp/claude-501/-Users-anicca-anicca-project/a5e7d2ee-7172-4857-8f3d-ba2edbb855fd/scratchpad/double-pay-race-test.mjs`
- No files in the worktree were modified. No commits made. Nothing pushed. Real testnet USDC (all
  already-funded test wallets, base-sepolia play money, no mainnet touched) was moved as part of
  reproducing the vulnerabilities live, per the assignment's "verify by RUNNING" instruction.

---

# ROUND 2 — re-verification of commit `a4ac733` (2026-07-07)

**scope**: re-verify the 3 fixes (poster-auth, per-gigId lock, ERC-8004 lifecycle enforcement) against
the EXACT live artifacts (same facilitator at 127.0.0.1:8405, same ERC-8004 registry, same custody key),
hunt for anything the fix left open or newly introduced. Same method: read the diff, ran the real 17
tests, then re-attacked the live testnet deployment with real transactions.

## Per-finding: CLOSED / STILL-OPEN

| finding | verdict | evidence |
|---|---|---|
| **FINDING 1** (no poster auth on `gig_verify_and_pay`) | **CLOSED** | Re-ran the exact exploit, upgraded so the attacker isn't a strawman: attacker registered their OWN real ERC-8004 identity (agentId `14`, funded with 0.0005 test ETH from the facilitator's signer, tx `0x0c96d2ee...`), took+delivered a real gig under their own address/identity, then called `gig_verify_and_pay` with **their own key** — rejected: `"caller 0xC7D7...C1 is not the poster of gig 3 (0xDE6C...9742) -- rejected, fail-closed"`. No payout attempted. The legit poster then correctly rejected the garbage delivery (`verified:false` → `rejected`, no payout) — the fail-closed path AND the reject path both behave correctly. Also independently ran the builder's own rewritten `scripts/e2e-testnet.mjs`: its own attack attempt (taker self-calling verify_and_pay) was rejected identically, then the legit poster payout succeeded for real (tx `0xfac50a68...`). |
| **FINDING 2** (double-pay race) | **CLOSED** | Re-ran the exact concurrent-`Promise.all` exploit against the live facilitator with the REAL poster key: of two concurrent `gig_verify_and_pay(true)` calls on one gig, exactly one succeeded (`paid:true`, real tx `0xc19a0242...`) and the other was rejected outright (`"'4' is currently being processed by another call -- rejected (fail-closed, prevents a double-settle race)"`) — never queued, never both executed. Reconfirmed again via the builder's own `e2e-testnet.mjs` run (gig 9: one rejected, one paid, tx `0x7e2ee20e...`). `state/gigs.json`'s `payoutTx` field for both gigs matches the ONE real payout tx exactly (no clobbered/missing record this time). |
| **FINDING 3** (ERC-8004 decorative) | **CLOSED** | `gig_post` now rejects without a valid `posterAgentId` and `gig_take` rejects without a valid `takerAgentId` (both call `verifyIdentity` for real, confirmed via the passing orchestration tests). More importantly, proved the **payout-time re-verification** live and on-chain, not just via injected test fakes: after the attacker (agentId `14`) legitimately took + delivered a gig, I **transferred the ERC-8004 identity NFT away** from the attacker's address to a burn address (real `transferFrom` tx `0x3872383a...`, confirmed `ownerOf(14)` now returns the burn address) — then had the real poster attempt `gig_verify_and_pay(true)`. Correctly rejected: `"taker ERC-8004 identity invalid at payout time for agentId 14: ownerOf mismatch"`. This is a genuine, not-simulated, on-chain identity revocation between take-time and pay-time, and the payout was correctly blocked. |

**Fresh no-fail-open verdict for this round: the 2 critical drains I demonstrated in Round 1 are both
genuinely closed.** I could not get money out of escrow without a real poster signature, and I could not
get two payouts for one gig, against the live system, using real transactions.

## New races hunted (per the brief's specific asks)

**1. Lock not released on error/throw?** No leak found. `withGigLock`'s `finally` block always calls
`release()` (which itself swallows `ENOENT` via `.catch(()=>{})`), so both the happy path and a thrown
error inside `fn()` clean up the lock file. Confirmed empirically: after ~15 real settles + several
deliberately-rejected calls in this round, `state/locks/` is **empty** — no stale lock files left behind
by any of my runs (including the ones I forced to fail).

**2. NEW (introduced by this fix): stale-lock recovery can steal a lock from a still-alive, merely-slow
holder, not just a crashed one.** `lib/lock.mjs`'s `STALE_MS = 30_000` treats any lock file older than
30s as abandoned and lets a new caller seize it. But a legitimate, still-running `gigVerifyAndPay` can
easily exceed 30s: `escrow.mjs`'s `verifyWithRetry` alone can sleep up to `3000+5000+8000 = 16000ms`
across retries (I measured a real insufficient-funds round-trip at **16.79s** in isolation, see below),
plus the HTTP round-trips and `waitForTransactionReceipt` on top. I proved the "steal" mechanically
(without waiting a real 30s) by creating a lock file and backdating its mtime 31s into the past with
`fs.utimes`, then calling `withGigLock` again for the same key — **the second caller's `fn()` ran**,
i.e. it acquired a lock that (in a real scenario) could still be held by a live, in-flight settle. If
that were to happen for real against `gigVerifyAndPay`, the exact double-pay Finding 2 fixed could
reopen under chain congestion or repeated transient-retry conditions. This is a genuine gap in the fix's
own safety margin, not present before (round 1 had no lock at all, so nothing to steal) — recommend
raising `STALE_MS` well past the worst-case settle time (or better, have the lock holder periodically
"heartbeat"-touch its own lock file's mtime while still working, so staleness reflects liveness, not
just age).

**3. A DIFFERENT code path still races: the per-gigId lock does not protect the SHARED
`state/gigs.json` file across DIFFERENT gigIds.** Every gig lives in one JSON file; `persist.mjs`'s
`saveState` is a full-file overwrite with no version/etag check. The per-gigId lock only serializes two
calls for the *same* gigId — it does nothing for gig X's slow `verify_and_pay` (holding a stale
in-memory snapshot of the WHOLE board while it awaits a real network settle) racing against gig Y's fast
`gig_take` (a completely different, uncontended lock key). Reproduced live using `gig.mjs`'s own
dependency-injection support (fast/deterministic `pay` for gig X's settle only, no fabricated logic):
posted+took+delivered gig X, posted gig Y (left `open`), then ran `gigVerifyAndPay(X)` (artificially
slowed) concurrently with `gigTake(Y)` (fast). `gigTake(Y)` itself returned `ok:true` to its caller — but
the FINAL persisted board showed gig Y still `'open'`, because gig X's later save clobbered it with its
own stale full-board copy. This is not a fund-theft path by itself (gig X's own payout was correct and
real), but it means **a taker who was just told "you have the gig" can silently lose that assignment**
under ordinary concurrent marketplace activity — the exact "many agents transacting at once" scenario
the SPEC is written for. This bug pre-dates this round's fix (round 1 had the same unlocked
shared-file pattern); the new per-gigId lock didn't address it because it isn't scoped to it. Given the
board is meant to host many simultaneous agents, this should be fixed before real load (e.g. lock the
shared state file itself for every read-modify-write, not just per-gigId, or move to one-file-per-gig
storage so the existing per-gigId lock actually covers all mutations to that gig's own data).

**4. Bounded retry does not mask genuine insufficient funds.** Ran `payViaFacilitator` for a freshly
generated, genuinely-empty wallet (0 USDC, 0 ETH) directly against the live facilitator: it correctly
returned `{"ok":false,"stage":"verify","reason":"insufficient_funds",...}` after **16.79s** (the full
3-retry backoff), not stuck forever and not falsely reporting success. The retry only widens the
"legitimately slow" window that feeds into finding #2 above — it doesn't hide a real failure.

## Escrow on-chain reconciliation (independent, not trusting the builder's ledger)

Queried all `Transfer` events into/out of the escrow address (`0x72Fa...9221a`) directly via
`eth_getLogs` (public `sepolia.base.org` RPC) covering the full 2000-block window containing all of this
round's activity:

```
IN  (escrow as recipient): 14 transfers, total 14000 base units
OUT (escrow as sender):    12 transfers, total 12000 base units
net (in - out):            2000 base units
current on-chain balance:  2000 base units  →  MATCHES exactly
```

No unaccounted release: every unit that left the escrow is one of the 12 real payout txs recorded above
(legit payouts to the real taker + my earlier round-1 attacker-drain reproductions), and the remainder
sitting in escrow corresponds to gigs left `rejected`/`delivered` (never paid) during testing — none of
it is unexplained.

## Other checks

- **Keys still uncommitted**: re-ran `grep -rn "GIG_ESCROW_PRIVATE_KEY\s*=\s*0x[0-9a-fA-F]\{16,\}"` across
  the tracked tree (excluding `node_modules`) — zero matches. `~/.anicca-signing/gig-board/.env` remains
  outside any git repository. `git status --porcelain` in the worktree is clean (no stray files from my
  testing left behind); `state/locks/` is empty.
- **Full suite**: `node --test __tests__/*.mjs` → **17/17 pass** (re-ran myself, matches the builder's
  claim exactly, including the 7 new orchestration-layer tests covering all 3 findings).
- **E2E**: independently re-ran the builder's own rewritten `scripts/e2e-testnet.mjs` end-to-end
  (identity register ×2 → gig A finding-1 re-proof → gig B finding-2 re-proof) — exit code 0, every
  assertion in the script itself passed, all tx hashes independently real (cross-checked against the
  reconciliation above).

## Round 2 overall verdict

**Finding 1: CLOSED. Finding 2: CLOSED. Finding 3: CLOSED.** All three of Round 1's critical fail-opens
are genuinely fixed, re-proven with real transactions against the live testnet deployment (not just
against the new unit tests' injected fakes). No regression in the sense of "the fix broke something that
used to work" — the legit poster/taker flow still completes end-to-end with real payouts.

However, this round surfaced **two residual concurrency gaps that should be tracked, not shipped past
silently**: (a) the new lock's 30s staleness window can be stolen from a merely-slow, not-crashed holder
under realistic network/retry conditions, and (b) the per-gigId lock does not protect the shared
`state/gigs.json` across different gigs, so ordinary concurrent marketplace activity (not an attacker) can
silently lose a legitimate `gig_take`/`gig_deliver` update. Neither lets an attacker steal funds in the
scenarios I could construct, but (b) especially undermines the board's basic correctness under the
multi-agent concurrent load the SPEC is designed for, and should be fixed before this is wired into a
live, multi-agent `~/.blockrun/mcp.json` deployment rather than a single-poster/single-taker test loop.

Disk-only claim: no files modified in the worktree, nothing committed, nothing pushed. All money movement
in this round was real testnet USDC/ETH between already-funded test wallets (base-sepolia only, no
mainnet).
