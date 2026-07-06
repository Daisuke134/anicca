# Slot: `economy/gig` (status: live, 2026-07-07, round-3 security fixes applied)

NOTE: not Foundation-pre-declared (no prior placeholder existed for this name) — added directly by the
builder per team-lead's P2.2 assignment (SPEC.md §3 P2 checklist items ②③⑤⑥), following the same
precedent as `self/spawn-child` and `self/coordinate`; flagged for Foundation review.

## Contract

- `lib/store.mjs` — pure gig lifecycle state machine (post→open→taken→delivered→paid|rejected).
  Fail-closed: `applyVerifyAndPay(verified:true)` REFUSES to mark `'paid'` without a real `payoutTx`.
  Records `posterAgentId`/`takerAgentId` (round 2).
- `lib/escrow.mjs` — pays through the P2.1 self-host x402-rs facilitator (127.0.0.1:8405), waits for
  on-chain confirmation before reporting success, retries transient `insufficient_funds` (round 2).
- `lib/identity.mjs` — ERC-8004 `register()`/`ownerOf()` direct calls against the live ChaosChain
  reference-implementation `IdentityRegistry` on Base Sepolia (`0xdc527768082c489e0ee228d24d3cfa290214f387`).
- `lib/lock.mjs` (round 2, NEW) — per-gigId POSIX-exclusive file lock; concurrent calls on the same gig
  are rejected fail-closed rather than racing. Round 3: heartbeats the lock's mtime while `fn()` runs so
  a live holder is never mistaken for a crashed one (staleMs/heartbeatMs injectable).
- `gig.mjs` — the 5 orchestration operations (`gigPost`, `gigList`, `gigTake`, `gigDeliver`,
  `gigVerifyAndPay`) + re-exports `registerIdentity`/`verifyIdentity`. Round 2: `gigVerifyAndPay` now
  requires `posterPrivateKey` (auth) and re-verifies taker ERC-8004 identity before paying;
  `gigPost`/`gigTake` require `posterAgentId`/`takerAgentId` (ERC-8004 gate); all mutating ops run
  inside `lib/lock.mjs`'s per-gigId lock. Round 3: new `applyAndSave()` is the only place that ever
  writes to disk — it always re-reads the board fresh under a global `"_board"` lock immediately
  before mutating, so a slow op on one gig can never clobber a concurrent save on an unrelated gig.
- `mcp-server.mjs` — MCP stdio server exposing all 7 as Franklin tools (wiring snippet in README, NOT
  applied to `~/.blockrun/mcp.json` from this worktree — witness step for the team lead). Tool schemas
  updated for the round-2 required params.
- `state/gigs.json` — runtime board state (gitignored, matches `skills/*/*/state/` pattern already in
  `.gitignore`). `state/locks/` (round 2) — per-gigId lock files, same gitignore pattern.

## E2E verified 2026-07-07 (real Base Sepolia tx, no mock)

Full internal loop: poster+taker ERC-8004 identity registered (agentId 8/9, both `ownerOf()`-verified
on-chain) → `gig_post` funds escrow (real settle) → `gig_take` → `gig_deliver` → `gig_verify_and_pay`
releases a REAL gasless payout to the taker (tx `0x17e4d4aa330ed5a4aaf3e5f5f926a4841c9a11958dfd1d7981de01ab04e32f6f`).
Balances after the run match the ledger exactly. Full evidence: README.md "E2E evidence" +
`.vcsdd/features/anicca-agent-economy/evidence/p2.2-gig-board.md` (anicca-project repo).

10/10 unit tests green (`__tests__/store.test.mjs`), including a genuine RED→GREEN check on the
fail-closed payout guard (temporarily removed it, the guarding test failed as expected, restored it,
green again).

## SECURITY ROUND 2 (2026-07-07): adversary drained the escrow live, twice — now fixed

A fresh-context adversary found 2 critical real drains (no poster auth on `verify_and_pay`; a
double-pay race from no per-gig locking) + 1 decorative-identity gap (ERC-8004 registered but never
checked in the lifecycle). All 3 fixed in `gig.mjs` + new `lib/lock.mjs`. 7 new orchestration-layer
tests (`__tests__/gig.test.mjs`), each finding's fix verified RED→GREEN by temporarily reverting it.
Real testnet re-proof: the taker's self-verify attack is REJECTED, and 2 concurrent real
`verify_and_pay(true)` calls pay out exactly once (tx
`0x5b34159acdf5e90b5575c77ee9bdfef76006d07c7f63b0d88106074fd2c7eeb4`), confirmed via full on-chain
`eth_getLogs` reconciliation of the escrow address (7 in / 7 out, net-zero, every transfer accounted
for including the adversary's own 3 drain txs). Full detail:
`.vcsdd/features/anicca-agent-economy/evidence/p2.2-security-fixes.md` (anicca-project repo) +
README.md "Security fixes, round 2".

## SECURITY ROUND 3 (2026-07-07): 2 residual concurrency gaps, not fund-theft but real data-loss

A second adversary pass confirmed all 3 round-2 fund-drain fixes hold, but found: (gap 1) `STALE_MS`
alone let a live-but-slow holder's lock be stolen after 30s (a real settle+retry measured 16.79s +
network on top), reopening the double-pay race under congestion; (gap 2) the per-gigId lock never
protected the shared `state/gigs.json` file itself — a slow op on gig X could silently revert a
concurrent `gig_take` on unrelated gig Y back to `'open'`. Both fixed (`lib/lock.mjs` heartbeat;
`gig.mjs`'s `applyAndSave` fresh-read-before-write under a global `"_board"` lock). 4 new tests
(`__tests__/lock.test.mjs` ×3, `__tests__/gig.test.mjs`'s `★GAP 2★` ×1), each verified RED→GREEN by
temporarily reverting the specific mechanism. Full suite 21/21. Re-ran the real testnet E2E (both
round-2 attack re-proofs) clean; on-chain reconciliation still nets out exactly. Full detail:
`.vcsdd/features/anicca-agent-economy/evidence/p2.2-security-fixes-round3.md` (anicca-project repo) +
README.md "Security fixes, round 3".
