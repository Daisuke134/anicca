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
  depositLanded also rejects surplus<=0 and moved<=0 (no trivial pass).
- One-time reconcile (CORRECTED per adversary 2026-06-22): cost-basis = PRINCIPAL (what was deposited),
  NOT current value — do NOT overwrite it with on-chain value (that would zero all unrealised P&L). The
  ONLY action is to DROP keys whose on-chain position is zero/dust (no real position): drop `morpho`
  (on-chain = 4 wei dust ≈ $0 vs a phantom $1 basis). KEEP aave/moonwell/fluid/bluechip principal — they
  have real on-chain positions. beefy has no cost-basis key and on-chain 0 → correctly absent.
- Evidence committed to disk: `state/cost-basis-onchain-proof.json` — balanceOf via CONSENSUS across
  multiple RPCs (a single RPC is unreliable: it intermittently returns 0x/garbage — proven 2026-06-22,
  llamarpc flipped morpho/fluid). Consensus (3-4 working RPCs): morpho=4 wei, beefy=0, aave/moonwell/
  fluid/bluechip > 0.

## Verify (4-D done)
- test passes (the phantom case returns false), execute-yield records delta-gated basis, cost-basis.json
  matches on-chain (see CORRECTION below — moonwell dropped, morpho kept), committed+pushed, synced to
  ~/.anicca. Adversary gate (vcsdd-adversary) reviews from disk before done.


## CORRECTION 2026-06-22 (adversary round 2) — the phantom was MOONWELL, not morpho
Via name(): morpho field = Steakhouse Prime (0xbeef…, a Morpho vault) = 0.971 sh ≈ $1 REAL; moonwell field =
Moonwell mUSDC (0xEdc817…) = 4 wei dust ≈ $0. So cost-basis MOONWELL $1 was the phantom (drop it); MORPHO $1
is a real Steakhouse position (KEEP it). The first reconciliation had these backwards (mislabeled proof file
misled even the adversary). Corrected: cost-basis = {aave, morpho, fluid, bluechip}; moonwell dropped. The
vars M/V in telemetry-poster are non-mnemonic (M=Moonwell, V=Morpho) — commented now. revenueBySource
extracted to lib/revenue.mjs with tests proving no +$1/−$1 phantom pair either way.
