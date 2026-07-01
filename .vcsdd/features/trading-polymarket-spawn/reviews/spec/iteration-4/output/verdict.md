# VCSDD Phase-1c Spec-Review Verdict — trading-polymarket-spawn (iteration 4, TRADING-ONLY after scope split)

- **feature**: trading-polymarket-spawn
- **mode**: lean
- **iteration**: 4
- **reviewType**: spec (Phase 1c gate)
- **scope**: TRADING ONLY (Group T + Group R); Group S (spawn) deferred to `spawn-child-earn`
- **reviewing**: scope-split + FIND-022/FIND-023 targeted fixes (note basedOn commit 81ce8e3)
- **overallVerdict**: **FAIL**
- **timestamp**: 2026-07-01

Fresh-context, disk-only review against the REAL `~/anicca` runtime. The three primary objectives of
this iteration LARGELY succeeded: FIND-022's settlement formula is corrected, FIND-023's vestigial args
are gone, and spawn is structurally carved out into `out-of-scope.jsonl`. BUT the FIND-022 fix is
**incompletely wired** — the new load-bearing input `filled_size` is consumed by the settlement gate yet
never written by the only requirement that creates a position row (FIND-024). Two further correctness/
definition gaps (FIND-026 PnL terms undefined, FIND-027 mid-vs-execution price) and one dangling spawn
reference (FIND-025) remain. overallVerdict = FAIL (any dimension FAIL).

## Per-dimension verdicts

| Dimension | Verdict | Findings |
|-----------|---------|----------|
| Spec Fidelity | **FAIL** | FIND-024, FIND-026 |
| Edge Case Coverage | PASS | (EDGE-T1..T7 + EDGE-R1/R2 + boundary fixtures RG-07/08, KF-03/04/05 + fail-closed defaults verified) |
| Implementation Correctness | **FAIL** | FIND-027 |
| Structural Integrity | **FAIL** | FIND-025 |
| Verification Readiness | **FAIL** | FIND-024 |

## Objective-by-objective disposition (this iteration's stated goals)

| Goal | Result | Evidence checked |
|------|--------|------------------|
| **(1) FIND-022 RESOLVED** — settle predicate `gross_payout = shares_held × $1`, `shares_held = filled_size/entry_price`, `settlement_price` removed, PROP-T26 deterministic | **PARTIAL** | The FORMULA is fixed: REQ-T8(b) cond-2 (behavioral-spec.md:209) uses `gross_payout_usdc = shares_held × $1.00`, `shares_held = filled_size/entry_price`, ±1 raw unit; explicitly states `settlement_price` is NOT valid. PROP-T26 (verification-architecture.md:74) now asserts `amount = round(filled_size/entry_price * 1e6) ±1`. `settlement_price` is gone everywhere (0 grep hits). BUT the predicate's input `filled_size` is never persisted (FIND-024), and `entry_price` is defined as the order-book MID rather than the execution price (FIND-027) — so PROP-T26 is not actually deterministically checkable against a real fill. The dimensional correction is right; the wiring is not complete. |
| **(2) FIND-023 RESOLVED** — `jurisdictionVenueFilter` is 2-arg everywhere | **RESOLVED** | 2-arg `jurisdictionVenueFilter(jurisdiction_ok_for_real, kyc_required)` is consistent across Pure Core (behavioral-spec.md:36; verification-architecture.md:21), REQ-T10 body (behavioral-spec.md:240), and all five call-sites PROP-T14/T14b/T15/T15b/T16 (verification-architecture.md:54-58). Grep confirms no surviving 4-arg `jurisdiction, venue, ...` form. Vestigial string args removed. |
| **(3) Spawn fully removed from active spec** | **MOSTLY** | Group S replaced by a DEFERRED marker (behavioral-spec.md:254-256); PROP-S/SE/INT-T10-13/16/E2E-2 replaced by deferred comments (verification-architecture.md:68,76,109,133,149,162); spawn params/NFRs/edge-cases removed; `out-of-scope.jsonl` preserves all REQ-S1..S9, PROP-S1..S14, INT tests, NFRs, edge cases, and FIND-014/016/019/020/021 verbatim. ONE stray reference survives: REQ-R4 (behavioral-spec.md:289) still names `spawn-log.jsonl` and `tithe-log.jsonl` (FIND-025). `colony`/sibling refs in REQ-R3 (behavioral-spec.md:278,285) are in-scope cross-instance dedup, not spawn — correctly retained. |

## Earlier-resolved trading fixes — re-confirmed intact

| # | Concern | Status | Evidence |
|---|---------|--------|----------|
| FIND-001/002/003/005 | (earn-slot wiring / tier / registry plumbing, iter-1/2) | INTACT | `isEarnSlot("earn/pm-trade")` true via `startsWith("earn/")` (earn-slot.mjs:11); `earnSkillRelPath` → `"earn/pm-trade/run.sh"` (earn-slot.mjs:30-33); `selectTier` present (tier.mjs:28). REQ-T1/PROP-T24/T25/PROP-R1 consistent. |
| FIND-007 | single-level earn slot (one slash only) | INTACT | earn-slot.mjs:29 comment + `earnSkillRelPath` single-slash contract; REQ-T1 declares only `earn/pm-trade`. |
| FIND-015 | settle-verify accepted any inbound USDC ≥ entry_cost | INTACT | REQ-T8(b) 3-condition predicate (from-allowlist + exact gross_payout + condition_id) at behavioral-spec.md:207-211; PROP-T26b (verification-architecture.md:75) rejects non-allowlist `from` even when amount ≥ entry_cost. Anti-fake-earn direction sound. |
| FIND-017 | `kyc_required` not in filter signature | INTACT | `kyc_required` is an explicit param; PROP-T14b/T15b prove the veto + absent-key fail-closed (default True→False); INT-T7 tests all three branches. |

Runtime claims spot-checked and TRUE: `proxy.mjs:9` resolves `(process.env.HOME) + "/.automaton/wallet.json"`
(REQ-R1); `hl.py` exposes `open/close` with `--sl/--tp` (hl.py:16-17,143) and reads
`~/.automaton/wallet.json` (hl.py:44) (REQ-T7b); `execute-yield.mjs:103` computes `surplus = liquid - RESERVE`
with `RESERVE = COMPUTE_RESERVE_USDC || "5"` (execute-yield.mjs:43) (REQ-R5) — and REQ-R5 correctly frames
the `reserved.json` logic as a modification to BE MADE (no false runtime claim).

## NEW findings (this iteration)

| # | Dim | Sev | One-line |
|---|-----|-----|----------|
| FIND-024 | spec_fidelity / verification_readiness | high | REQ-T7(c) write-list (behavioral-spec.md:187) omits `filled_size`, but the settlement gate REQ-T8(b):209 + schema:45 + PROP-T26 (verification-architecture.md:74) all REQUIRE it. The sole input to the FIND-022 predicate is never produced → settlement reads an undefined field → PROP-T26 has no guaranteed input. FIND-022 fix incompletely wired. |
| FIND-025 | structural_integrity | low | REQ-R4 (behavioral-spec.md:289) still references deferred-feature artifacts `spawn-log.jsonl` and `tithe-log.jsonl`; no in-scope requirement creates either. Dangling spawn/tithe ref the scope-split missed. |
| FIND-026 | spec_fidelity | low | REQ-T8(a) (behavioral-spec.md:205) `realized_pnl_usdc = settlement_amount − entry_cost` — both terms undefined in Tracked Quantities; PnL / cumulative / daily_loss rest on unbound quantities. |
| FIND-027 | implementation_correctness / verification_readiness | medium | `entry_price` is defined as the order-book MID (behavioral-spec.md:45) but `shares_held = filled_size/entry_price` needs the AVERAGE EXECUTION price; with only ±1 raw-unit tolerance the settlement predicate fail-closed REJECTS a real winning redemption (suppresses genuine earn) and makes PROP-T26's deterministic assertion unsatisfiable by an actual fill. |

## Money-safety / hunt summary (TRADING-only)

| Hunt target | Result |
|-------------|--------|
| (c) faked-earn / INV-7 | DIRECTION SOUND — 3-condition predicate + PROP-T26b reject misattributed transfers. BUT predicate input `filled_size` not persisted (FIND-024) and uses mid not execution price (FIND-027) → gate either KeyErrors or fail-closed rejects real wins. Not implementation-ready. |
| (e) geoblock for real stakes | RESOLVED for trading — KYC veto proven (PROP-T14b/T15b/INT-T7); Kalshi excluded; fail-closed defaults (jurisdiction absent→false, kyc absent→true). |
| trading-stake DeFi sweep (REQ-R5) | SOUND framing — `execute-yield.mjs:103` math correctly referenced; reserved.json modification well-specified; 3 cases + boundary in PROP-R5/INT-T21. |
| paper-mode bypass | SOUND — PROP-T18/T19/T20 + fail-closed adversary-pass.json gate. |
| (f) false runtime claims | NONE found in trading scope — proxy.mjs/hl.py/execute-yield.mjs claims verified true. (Spawn false-claims FIND-019/020/021 correctly deferred to `out-of-scope.jsonl`.) |

## convergenceSignals

- findingCount: 4 (FIND-024 high, FIND-027 medium, FIND-025 low, FIND-026 low)
- iteration-3 trading findings resolved: FIND-022 (formula; wiring incomplete → FIND-024/027), FIND-023 (fully resolved)
- spawn deferral: structurally complete except one dangling ref (FIND-025); `out-of-scope.jsonl` preserves all Group S content + FIND-014/016/019/020/021
- allClaimsVerifiedAgainstRuntime: true
- duplicateFindings: []
- rootCause: the FIND-022 settlement rewrite added `filled_size`/`shares_held` to the READ side (REQ-T8/PROP-T26) without updating the WRITE side (REQ-T7(c)) or re-basing `entry_price` from mid to execution price, and left REQ-T8(a)'s PnL terms unbound. Close the loop: (1) add `filled_size` to REQ-T7(c)'s recorded fields, (2) redefine `entry_price`/`shares_held` from the realized fill (avg execution price or shares directly), (3) bind `settlement_amount`/`entry_cost`, (4) delete the spawn-log/tithe-log clause from REQ-R4. These are small, surgical edits — one more iteration should converge the trading spec.
