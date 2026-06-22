# SPEC — #8 Fix phantom yield deposit + reconcile cost-basis to on-chain (VSDD, 2026-06-22)

## Problem (on-chain verified)
- `~/.anicca/skills/earn/state/cost-basis.json` claims `morpho: 1.00`, but on-chain morpho(0xEdc817)=0 → **phantom $1**.
- Root: a now-removed older code path recorded a "morpho" basis without the position landing. The CURRENT
  `execute-yield.mjs` only writes beefy/fluid/aave keys and records on `r.status==="success"`, so it does
  not create this key anymore — but `status==="success"` is NOT proof money moved (a tx can succeed yet
  deposit nothing if the venue is wrong/no-op), so the guard is not bulletproof.
- Honest note: Beefy USDC APY on Base is ~5.05% (NOT 56%); Fluid is currently HIGHER at 5.36%, so the
  auto "highest-APY" picker currently selects Fluid (which lands on-chain). "Beefy as default" = "auto
  best-APY stable yield as the hedge floor", already designed; the real defect is phantom accounting.

## Contract (invariants)
1. cost-basis.json MUST equal on-chain reality: every venue key maps to a position that actually exists
   on-chain; no key for a zero position. (Reconcile the existing file; remove phantom `morpho`.)
2. A deposit is recorded in cost-basis ONLY if it actually moved money: liquid USDC strictly decreased by
   ~the deposited amount (read-after-write), not merely `tx.status==="success"`.
3. recordDeposit basis = the USDC amount that actually left liquid (delta), not a blind `surplus`.
4. No-mock E2E: verified against real Base RPC reads (balanceOf before/after).

## RED (failing checks first)
- Unit: pure helper `depositLanded({statusOk, liqBefore, liqAfter, surplus})` →
  - status ok + liquid dropped ≥ 99% of surplus → true
  - status ok + liquid UNCHANGED (phantom) → **false**  ← current code records this (bug)
  - status not ok → false
- Reconciliation check: after fix, for every key in cost-basis.json there is a matching on-chain balance > 0
  (within tolerance); `morpho` is gone.

## GREEN (implementation)
- Add `export function depositLanded(...)` (pure) + wire main() to gate `recordDeposit` on it; when a
  deposit "succeeds" but money didn't move, DO NOT record + emit `{phantom:true}` in the output line.
- One-time reconcile: rewrite cost-basis.json (live ~/.anicca + mother ~/anicca) from on-chain balances
  (drop morpho; set moonwell/aave/fluid/bluechip to true values).

## Verify (4-D done)
- test passes (the phantom case returns false), execute-yield records delta-gated basis, cost-basis.json
  matches on-chain (morpho gone), committed+pushed, synced to ~/.anicca. Adversary gate (vcsdd-adversary)
  reviews from disk before done.
