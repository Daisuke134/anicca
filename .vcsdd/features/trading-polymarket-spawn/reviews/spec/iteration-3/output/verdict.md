# VCSDD Phase-1c Spec-Review Verdict — trading-polymarket-spawn (iteration 3, lean FINAL re-review)

- **feature**: trading-polymarket-spawn
- **mode**: lean
- **iteration**: 3
- **reviewType**: spec (Phase 1c gate)
- **reviewing**: round-3 fix (commit 059da3f) claiming to resolve iteration-2's FIND-014/015/016/017/018
- **overallVerdict**: **FAIL**
- **timestamp**: 2026-07-01

Fresh-context, disk-only re-review against the REAL `skills/self/spawn/` skill and runtime. Round-3
genuinely fixed the on-chain settlement under-binding (FIND-015), the KYC-veto signature (FIND-017),
and removed the duplicated spawn subsystem (FIND-018). BUT the Group-S "thin wrapper fully delegates to
`run.sh`" rewrite rests on **delegation claims that are false against the real `run.sh`**: it does NOT
perform the seed transfer, and it does NOT consume `ANICCA_VENUE_POLICY_PATH` / write the child
`menu.json`. So FIND-014's feasibility half and FIND-016 remain open, and three new defects surface.
overallVerdict = FAIL (any dimension FAIL).

## Per-dimension verdicts

| Dimension | Verdict | Findings |
|-----------|---------|----------|
| Spec Fidelity | **FAIL** | FIND-019, FIND-020 |
| Edge Case Coverage | **FAIL** | FIND-020 |
| Implementation Correctness | **FAIL** | FIND-019, FIND-021 |
| Structural Integrity | PASS | (FIND-018 reinvention removed; minor FIND-023 low, non-blocking) |
| Verification Readiness | **FAIL** | FIND-022 |

## Iteration-2 finding disposition (verified file:line against the REAL skill)

| # | iter-2 claim | Round-3 fix verdict | Evidence checked |
|---|--------------|---------------------|------------------|
| FIND-014 | Child brain infeasible same-host `:8402` (reopened FIND-004) | **STILL-OPEN** | Port half RESOLVED: child boots on a SEPARATE DO droplet (run.sh:135-162 provisions a droplet whose cloud-init runs clawrouter+automaton), so `:8402` is free — `anicca-daemon.sh:49-50` `:8402-only` no longer collides. BUT the delegation-feasibility half is FALSE: see FIND-019 (no seed transfer in run.sh), FIND-020 (no venue-policy ingestion), FIND-021 (run.sh's own gate uses maxChildren=1 / minBalance=20 / `.balance_usdc`, contradicting REQ-S1/S7). The "thin wrapper, 7 mechanics delegated" framing asserts capabilities run.sh lacks. |
| FIND-015 | settle-verify accepts any inbound USDC ≥ entry_cost (faked earn) | **RESOLVED** | REQ-T8(b) (behavioral-spec.md:207-211) now requires ALL THREE: `from` ∈ `POLYMARKET_SETTLEMENT_ADDRS` allowlist, amount = `gross_payout_usdc` (±1 raw unit), and `condition_id` present in the tx via `eth_getTransactionReceipt` PositionRedemption/PayoutRedemption. PROP-T26b (verification-architecture.md:91) explicitly rejects a non-allowlist `from` even when amount ≥ entry_cost (sibling tithe / top-up / wrong-market payout). The anti-fake-earn direction is sound. Caveat: the exact-amount formula is undefined (see FIND-022) — over-strict, but fail-closed. |
| FIND-016 | Autonomous child can never enable a real venue (no operator) | **STILL-OPEN** | The fix mechanism does not exist in the delegated skill: grep of `skills/self/spawn` = 0 hits for `ANICCA_VENUE_POLICY_PATH` and 0 hits for `menu.json`; run.sh:143 calls `cloud-init.sh "$CHILD_ID" "$CHILD_INBOX"` (no policy path). See FIND-020. |
| FIND-017 | `kyc_required` not in `jurisdictionVenueFilter` signature; unverified guard | **RESOLVED** | 4-arg signature `jurisdictionVenueFilter(jurisdiction, venue, jurisdiction_ok_for_real, kyc_required)` is consistent across behavioral-spec.md:35, verification-architecture.md:23, REQ-T10 (behavioral-spec.md:240). PROP-T14b (arch:59) tests the kyc veto (kalshi True/True→False); PROP-T15b (arch:61) tests absent-key fail-closed default True→False; INT-T7 (arch:159) tests all three branches. Minor vestigial-arg smell (FIND-023, low). |
| FIND-018 | Group S re-invents the tested `skills/self/spawn/` | **RESOLVED** | Group S is now a documented thin wrapper: Purity Boundary `spawnEligible` wraps `decideSpawn` from `skills/self/spawn/lib/spawn-decision.js`; `children` via `lib/ledger.js readChildren`; all `spawn-log.jsonl` references replaced by `state/children.jsonl`. The parallel reinvented constructs are gone. (Note: the delegation is now leaky/false rather than duplicated — tracked as FIND-019/020/021, a different defect class.) |

## NEW findings introduced / surfaced by round-3

| # | Dim | Sev | One-line |
|---|-----|-----|----------|
| FIND-019 | spec_fidelity | critical | REQ-S2 step 5 / REQ-S4 claim run.sh does the on-chain seed transfer and waits for confirmation; real run.sh only sets `SEED_USDC` (run.sh:118), stores it as ledger metadata (run.sh:129), and PRINTS a manual "Seed the child wallet with $X" (run.sh:196). SKILL.md:55 = manual post-step. False runtime claim → FIND-014 delegation infeasible. |
| FIND-020 | spec_fidelity / security_surface | high | REQ-T10/S2/S3/S5 claim run.sh consumes `ANICCA_VENUE_POLICY_PATH` and cloud-init writes child `menu.json` before install.sh; grep of `skills/self/spawn` = 0 hits for either, run.sh:143 passes only CHILD_ID+CHILD_INBOX to cloud-init. FIND-016 mechanism fictional. |
| FIND-021 | impl_correctness | medium | Double spawn gate: run.sh:61-66 re-runs `decideSpawn` with hardcoded defaults maxChildren=1 / minBalance=20 and reads balance from `$STATE_DIR/wallet.json .balance_usdc` (run.sh:48-51) — contradicting REQ-S1/S7 (spawn_hard_cap=5, treasury from RPC) and the automaton key-file wallet model → 2nd child refused / always dormant on real runtime. |
| FIND-022 | verification_readiness | medium | PROP-S11 tests a non-existent "seed transfer step 5" in run.sh; PROP-T26 / REQ-T8(b) cond-2 reference undefined `settlement_price` (`gross_payout = size × settlement_price` is dimensionally wrong for CTF binary redemption where payout = shares×$1, shares=size/entry_price) → real winning redemption rejected; obligation not deterministically checkable. |
| FIND-023 | structural_integrity | low | `jurisdictionVenueFilter`'s `jurisdiction`/`venue` params are vestigial (return depends only on the two booleans); name-vs-behavior mismatch. Non-blocking. |

## Money-safety / hunt summary (re-verified against real run.sh)

| Hunt target | Result |
|-------------|--------|
| (c) faked-earn / INV-7 | **RESOLVED** — 3-condition predicate (from-allowlist + exact gross_payout + condition_id) + PROP-T26b reject misattributed transfers. Over-strict amount formula (FIND-022) is fail-closed. |
| (d) spawn loop spending parent funds unsafely | **FAIL** — run.sh performs NO seed transfer (FIND-019); the spec asserts it does. Worse, the gate run.sh actually enforces (maxChildren=1, minBalance=20, `.balance_usdc`) diverges from REQ-S1/S7 (FIND-021). |
| (b) hidden human-in-the-loop | **FAIL** — autonomous child still cannot enable a real venue; the parent-policy delegation path does not exist in run.sh/cloud-init (FIND-020). Seeding is a manual operator step per SKILL.md:55/run.sh:196 (FIND-019). |
| (e) geoblock for real stakes | IMPROVED — KYC veto now in `jurisdictionVenueFilter` (FIND-017 resolved) and proven (PROP-T14b/T15b/INT-T7); but the flag-flip path for children is fictional (FIND-020). |
| (f) false claims about the runtime | **FAIL** — REQ-S2/S3/S4/S5 describe run.sh steps (seed transfer, venue-policy ingestion) that do not exist; run.sh's own gate is misdescribed (FIND-019/020/021). |
| port isolation (FIND-014 port half) | RESOLVED — separate droplet, child `:8402` free (run.sh:135-162). |

## convergenceSignals

- findingCount (still-open + new): 5 blocking (FIND-019 critical, FIND-020 high, FIND-021 medium, FIND-022 medium) + 1 low non-blocking (FIND-023)
- iteration-2 findings resolved: 3 of 5 (FIND-015, FIND-017, FIND-018)
- iteration-2 findings still open: 2 (FIND-014 → FIND-019/021; FIND-016 → FIND-020)
- allFindingsVerifiedAgainstRuntime: true
- rootCause: Group-S round-3 rewrite swapped "reinvented subsystem" for "delegate to existing skill" but asserts run.sh does seed transfer + venue-policy provisioning, which it does not — the spec must either (a) add those steps to the spawn skill and reference them honestly, or (b) move seed-transfer + venue-policy bootstrap into the `self/spawn-child` wrapper and stop claiming run.sh performs them.
