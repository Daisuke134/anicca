# VCSDD Phase-1c Spec-Review Verdict — trading-polymarket-spawn (iteration 2, re-review)

- **feature**: trading-polymarket-spawn
- **mode**: lean
- **iteration**: 2
- **reviewType**: spec (Phase 1c gate)
- **reviewing**: round-2 fix (commit 0ada823) claiming to resolve iteration-1's 13 findings
- **overallVerdict**: **FAIL**
- **timestamp**: 2026-07-01

Fresh-context, disk-only re-review. The round-2 edits genuinely fixed the wallet-isolation,
riskGate-purity, yield-sweep, spawn-TOCTOU, and most medium findings. But one critical iteration-1
finding (child brain on its own port — FIND-004) is **still open** because the spec's port-split
mechanism is contradicted by the real `clawrouter` launch, and the round-2 edits introduced four
new defects (under-bound on-chain settlement match, autonomous-child real-earn dead-end, an
unverified KYC guard, and a duplicate spawn subsystem). overallVerdict = FAIL (any dimension FAIL).

## Per-dimension verdicts

| Dimension | Verdict | Findings |
|-----------|---------|----------|
| Spec Fidelity | **FAIL** | FIND-014, FIND-015 |
| Edge Case Coverage | **FAIL** | FIND-016 |
| Implementation Correctness | **FAIL** | FIND-014 |
| Structural Integrity | **FAIL** | FIND-018 |
| Verification Readiness | **FAIL** | FIND-014, FIND-015, FIND-017 |

## Iteration-1 finding disposition (verified against the REAL runtime)

| # | Claim | Verdict | Evidence checked |
|---|-------|---------|------------------|
| FIND-001 | Wallet isolation via `HOME=$CHILD_HOME` | **RESOLVED** | `proxy.mjs:9`, `execute-yield.mjs:54`, `hl.py:44` (`expanduser ~`), `anicca-daemon.sh:53-54` all read `$HOME/.automaton/wallet.json`; REQ-S5(b) (spec.md:333) launches child with `HOME=$CHILD_HOME` → the whole child tree resolves the child wallet. Mechanism is real. |
| FIND-002 | INV-7 earn gate (skeleton REQ-G2 can't verify on-chain) | **RESOLVED (structurally) → see FIND-015** | REQ-T8 (spec.md:206-209) drops REQ-G2 and adds `settle-verify.py` with Polygon `eth_getLogs`. The G2 mismatch is gone, BUT the new gate is under-bound (FIND-015). |
| FIND-003 | `riskGate` purity contradiction | **RESOLVED** | Signature now `riskGate(risk_state, position_usdc, current_balance, edge, config)` in both Purity Boundary (spec.md:35) and Pure Core (verification-architecture.md:18); REQ-T4 (spec.md:108,130) passes `current_balance`/`edge` as explicit args; PROP-T6/T11 updated. All table predicates reference only params. Genuinely pure. |
| FIND-004 | Child shares parent `:8402` brain on parent wallet | **STILL OPEN → FIND-014** | Wallet half fixed via HOME. Brain-on-own-port half is FALSE: `anicca-daemon.sh:55` launches `clawrouter` with no port; line 50 comment = ":8402-only (no port split)". `COMPUTE_PROXY_PORT` is honored by `proxy.mjs:13`, not by the `clawrouter` the daemon actually runs. |
| FIND-005 | REQ-R5 wrong module + fail-open | **RESOLVED** | REQ-R5 (spec.md:443) correctly names `execute-yield.mjs`; surplus math confirmed at `execute-yield.mjs:103` (`surplus = liquid - BigInt(RESERVE)`). Fail behavior now fail-SAFE: reserved.json absent + slot live → deploy $0 (spec.md:452,458). |
| FIND-006 | Spawn double-seed TOCTOU | **RESOLVED** | REQ-S2(a-pre) (spec.md:276) adds `flock -n` on `spawn.lock` spanning read-of-snapshot through the "initiated" append; concurrent contender aborts `spawn_lock_held`; the durable "initiated" row + rate-cap then blocks sequential retries. PROP-S14 added. |
| FIND-007 | Kalshi KYC reroute = J8 violation | **RESOLVED (with gaps FIND-016/017)** | REQ-T10 (spec.md:236) now bans Kalshi for real stakes, names Hyperliquid as the only no-KYC fallback, provisions all venues fail-closed. Residual: autonomous dead-end (FIND-016) + the kyc_required guard has no PROP (FIND-017). |
| FIND-008 | `market_p` mid vs ask | **RESOLVED** | REQ-T5 (spec.md:142) = mid `(best_bid+best_ask)/2`, consistent with REQ-T3 (spec.md:92). |
| FIND-009 | Adversary PASS file path undefined | **RESOLVED** | REQ-T6 (spec.md:168) fixes path `$ANICCA_HOME/loops/earn-pm-trade/adversary-pass.json` + schema. |
| FIND-010 | Entry-only kill-switch, no perp SL | **RESOLVED** | REQ-T7 (spec.md:186) dispatches Hyperliquid to `hl.py` and MUST pass `--sl`/`--tp`; matches `hl.py` SL/TP design. |
| FIND-011 | `wallet.json` falsely attributed to ensure-solana | **RESOLVED** | REQ-R2 (spec.md:418) + REQ-S2(b)(c) (spec.md:278-279): ensure-solana writes only `solana.json` (confirmed `ensure-solana-wallet.mjs:12`); EVM key via viem `generatePrivateKey`. |
| FIND-012 | `pm.py` deps never installed | **RESOLVED** | REQ-S3(c) (spec.md:298) + NFR-1 (spec.md:466) install from `requirements.txt`. |
| FIND-013 | `pm.py` duplicates `hl.py` Hyperliquid | **RESOLVED** | REQ-T7 (spec.md:190): `pm.py` = Polymarket+Kalshi CLOBs only; Hyperliquid → existing `hl.py`. |

## NEW findings introduced / surfaced by the round-2 edits

| # | Dim | Sev | One-line |
|---|-----|-----|----------|
| FIND-014 | impl_correctness | critical | REQ-S5 same-host `CHILD_PORT` brain is infeasible: `clawrouter` is :8402-only (`anicca-daemon.sh:50,55`); child brain collides on :8402 and never listens on `$CHILD_PORT` → child inference dead. (reopens FIND-004) |
| FIND-015 | spec_fidelity | high | `settle-verify.py` Polygon `eth_getLogs` (spec.md:207) matches ANY incoming USDC ≥ entry_cost to our wallet — no `from`=settlement-contract / per-market amount binding → tithe/top-up/other-market payout = faked earn. INV-7 not enforced. |
| FIND-016 | edge_case | medium | Fail-closed `jurisdiction_ok_for_real:false` for all venues + no operator on an autonomous child (spec.md:241) → child can never real-stake → REQ-T8/REQ-S8/PROP-E2E-2 unreachable. |
| FIND-017 | verification_readiness | medium | The kyc_required belt-and-suspenders guard (spec.md:246) has no proof obligation; PROP-T14/15/16 test only `jurisdiction_ok_for_real`, and `kyc_required` is not in `jurisdictionVenueFilter`'s signature. |
| FIND-018 | structural_integrity | medium | Group S re-invents the existing tested `skills/self/spawn/` (decideSpawn / child-spec / ledger / gen-wallet / droplet-isolated provisioning) with parallel un-referenced constructs; same duplication anti-pattern as FIND-013. |

## Money-safety / hunt summary (re-verified)

| Hunt target | Result |
|-------------|--------|
| (a) real stake lost/swept/double-spent; kill-switch correct | IMPROVED — sweep (FIND-005) and double-seed (FIND-006) now fixed; perp SL via hl.py (FIND-010) fixed |
| (b) hidden human-in-the-loop | PARTIAL — Kalshi KYC banned (good), but autonomous child has no way to enable any real venue (FIND-016) |
| (c) faked-earn / INV-7 | **FAIL** — settle-verify accepts any incoming USDC ≥ entry_cost to our wallet, not bound to the market (FIND-015) |
| (d) spawn loop spending parent funds unsafely | **FAIL** — child brain can't run on its own port (FIND-014); same-host model collides on :8402 |
| (e) geoblock enforced for real stakes | IMPROVED — fail-closed provisioning; but flag flip undefined for autonomous instances (FIND-016) and guard unverified (FIND-017) |
| (f) false claims about the runtime | **FAIL** — REQ-S5's "ClawRouter on $CHILD_PORT" contradicts `anicca-daemon.sh:50` (FIND-014) |

## convergenceSignals

- findingCount (still-open + new): 5 (FIND-014 critical, FIND-015 high, FIND-016/017/018 medium)
- iteration-1 findings resolved: 12 of 13 (FIND-001,002,003,005,006,007,008,009,010,011,012,013)
- iteration-1 findings still open: 1 (FIND-004 → FIND-014)
- allFindingsVerifiedAgainstRuntime: true
