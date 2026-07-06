# Slot: `economy/gig` (status: live, 2026-07-07)

NOTE: not Foundation-pre-declared (no prior placeholder existed for this name) — added directly by the
builder per team-lead's P2.2 assignment (SPEC.md §3 P2 checklist items ②③⑤⑥), following the same
precedent as `self/spawn-child` and `self/coordinate`; flagged for Foundation review.

## Contract

- `lib/store.mjs` — pure gig lifecycle state machine (post→open→taken→delivered→paid|rejected).
  Fail-closed: `applyVerifyAndPay(verified:true)` REFUSES to mark `'paid'` without a real `payoutTx`.
- `lib/escrow.mjs` — pays through the P2.1 self-host x402-rs facilitator (127.0.0.1:8405), waits for
  on-chain confirmation before reporting success.
- `lib/identity.mjs` — ERC-8004 `register()`/`ownerOf()` direct calls against the live ChaosChain
  reference-implementation `IdentityRegistry` on Base Sepolia (`0xdc527768082c489e0ee228d24d3cfa290214f387`).
- `gig.mjs` — the 5 orchestration operations (`gigPost`, `gigList`, `gigTake`, `gigDeliver`,
  `gigVerifyAndPay`) + re-exports `registerIdentity`/`verifyIdentity`.
- `mcp-server.mjs` — MCP stdio server exposing all 7 as Franklin tools (wiring snippet in README, NOT
  applied to `~/.blockrun/mcp.json` from this worktree — witness step for the team lead).
- `state/gigs.json` — runtime board state (gitignored, matches `skills/*/*/state/` pattern already in
  `.gitignore`).

## E2E verified 2026-07-07 (real Base Sepolia tx, no mock)

Full internal loop: poster+taker ERC-8004 identity registered (agentId 8/9, both `ownerOf()`-verified
on-chain) → `gig_post` funds escrow (real settle) → `gig_take` → `gig_deliver` → `gig_verify_and_pay`
releases a REAL gasless payout to the taker (tx `0x17e4d4aa330ed5a4aaf3e5f5f926a4841c9a11958dfd1d7981de01ab04e32f6f`).
Balances after the run match the ledger exactly. Full evidence: README.md "E2E evidence" +
`.vcsdd/features/anicca-agent-economy/evidence/p2.2-gig-board.md` (anicca-project repo).

10/10 unit tests green (`__tests__/store.test.mjs`), including a genuine RED→GREEN check on the
fail-closed payout guard (temporarily removed it, the guarding test failed as expected, restored it,
green again).
