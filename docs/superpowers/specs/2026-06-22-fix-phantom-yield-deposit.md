# SPEC — #8 Fix phantom yield deposit + reconcile cost-basis to on-chain (VSDD, 2026-06-22)

## ⭐ FINAL CONCLUSION (read this first — the sections below are the dated investigation trail)
There was **NO phantom**. The original "morpho=$0 on-chain" was a **decimals bug** (Moonwell mUSDC is 8-dec; it
was divided by 1e18 so $1 looked like dust). Verified via `decimals()`: aave=6, morpho/Steakhouse=18, moonwell/
mUSDC=8, fluid=6 → ALL of {aave, morpho, moonwell, fluid, bluechip} are REAL on-chain; only beefy=0 (no key).
**cost-basis.json is reverted to the original 5 keys — nothing dropped.** The DELIVERABLE that ships from #8 is
the defensive **read-after-write deposit guard** (`lib/deposit-guard.mjs`, gates recordDeposit on liquid actually
dropping, not just tx status) + `lib/revenue.mjs` extraction with phantom-sentinel tests. 21/21 green. The
investigation below (rounds 1-3) is kept verbatim as an honest record of the wrong turns the adversary caught.

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

## CORRECTION 2026-06-22 (adversary round 3, FIND-003) — THERE WAS NO PHANTOM; it was a decimals bug
The whole "morpho/moonwell phantom" premise was a units misread. Moonwell mUSDC is an **8-decimal cToken**;
my balanceOf read divided it by 1e18, so 43.66 mUSDC (≈$1 real, mint tx 0xa1a196 per earn-verification
2026-06-18) looked like 4.37e-9 "dust". Verified via decimals(): aave=6, morpho/Steakhouse=18, **moonwell/
mUSDC=8**, fluid=6. With correct decimals BOTH morpho(0xbeef Steakhouse, 0.971 sh) and moonwell(0xEdc817,
43.66 mUSDC) hold ~$1 REAL. Only beefy(0x83152e)=0 — and it has no cost-basis key, so already consistent.
ACTION: cost-basis fully REVERTED to the original {aave, moonwell, morpho, fluid, bluechip} — no key dropped.
What REMAINS valuable from #8 (kept): (1) deposit-guard read-after-write (prevents a FUTURE real phantom),
(2) revenueBySource extracted to lib/revenue.mjs + tests, (3) corrected proof with decimals, (4) M/V comment,
(5) SKILL.md test glob fix.
KNOWN LIMITATIONS (adversary, accepted): FIND-001 the morpho/moonwell basis keys have no current write path
(legacy positions from older code; VENUE_KEY only writes aave/fluid/beefy) — fine while they're static real
positions. FIND-004 depositLanded proves liquid dropped ~surplus, not that shares minted in the intended
venue — a reasonable proxy; strengthening to shares-delta is a future hardening (revenue-dashboard spec A).
