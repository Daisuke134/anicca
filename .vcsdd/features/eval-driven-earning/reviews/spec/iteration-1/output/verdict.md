# VCSDD Phase 1c Spec-Review Verdict — eval-driven-earning (iteration 1, lean)

**OVERALL VERDICT: FAIL**

Fresh-context adversary, disk-only. 13 findings (6 critical, 4 high, 3 medium). All 5 dimensions FAIL.

## Dimension verdicts

| dimension | verdict | findings |
|---|---|---|
| spec_fidelity | FAIL | FIND-001, FIND-002, FIND-003, FIND-010 |
| edge_case_coverage | FAIL | FIND-002, FIND-011 |
| implementation_correctness | FAIL | FIND-004, FIND-005, FIND-009, FIND-011 |
| structural_integrity | FAIL | FIND-007, FIND-012, FIND-013 |
| verification_readiness | FAIL | FIND-006, FIND-008 |

## Targeted hunt results (per manifest questions)

- **(a) Integrate skeleton REQ-B/B4/H — double-count / contradictory kill?** BROKEN. FIND-003: REQ-S5 calls a `survival-bankruptcy` self-recover reason that has NO Group J handler, and falsely claims it invokes REQ-B4 (which is triggered inside loop-roi.sh, not via self-recover). Two contradictory kill criteria (cost_jpy>5x earned_jpy from first_seen vs net_usdc<0 from loss_start) both target `loop.disabled`.
- **(b) Purity — clock/grace injected not read?** netWorth/isSolvent are genuinely pure and inject now_ts/grace correctly. But decideActivity is NOT purely realizable: FIND-006 (rolling-100-wake novelty quota requires file/history a pure fn cannot see) and FIND-005 (no explore/exploit decision rule; no-random contract blocks the quota policy).
- **(c) Can the judge override a VERIFIABLE check?** Spec text forbids it (REQ-EV3), but FIND-008: the guarantee is tested only against an unspecified `rubricEval`, and the pure `rubricScore` signature has no verifiable-check input, so Verifier's Law is not tied to any specified symbol.
- **(d) calibrationDrift on insufficient data fail-closed?** YES for the <min_pairs and zero-variance cases (PROP-E4/E7 return sufficient_data=False / pearson_r=None, no raise). BUT FIND-012: the window_secs semantics are unimplementable (no timestamps passed) and dropped in 1b.
- **(e) Curation/radar hidden human-touch / real money on un-curated skill / wallet-secret import?** J8 and NFR-ED6/anti-slop-7 keep human-touch and wallet-key out. However FIND-010: bootstrap grandfathers `trading-polymarket` (real wallet rail) into the menu with admitted_at_ts=null and it becomes exploit-eligible without ever passing Group CU. FIND-009: the curation sandbox mocks all payouts, so the 'earns via verifiable payout endpoint' criterion is unverifiable — the money-protection is illusory.
- **(f) income = INV-7 on-chain USDC only, un-fakeable?** NO. FIND-001: INV-7 is undefined in the skeleton. FIND-002: income_usdc = cumulative_usdc_earned zeroes out every JPY-settling MVP slot (Coconala/Amazon), forcing permanent insolvency and killing the best earners.
- **(g) Explore/exploit provably retires losers + doubles down winners?** Greedy-max double-down is provable, but FIND-013: the convergence-required proof test asserts 10/10 exploit selection, contradicting the mandatory ~10% explore quota — the test proves the wrong thing.

## Additional correctness defect

- FIND-004: cost_usdc formula in REQ-S1(d) is dimensionally wrong (USD divided again by FX ~ 150x error) and its acceptance number is arithmetically wrong; it disagrees with the REQ-S2(b) path for the same quantity.
- FIND-007: pure-function signatures (rubricScore, calibrationDrift, updateBanditArm) drift between the 1a and 1b documents.
- FIND-011: updateBanditArm alpha cap is contradictory (REQ-M2(a) uncapped vs EDGE-M2a capped at 1.0).

## Gate outcome

Spec is NOT ready for Phase 2. Route criticals FIND-001..006, FIND-009, FIND-010 back to Phase 1a; FIND-007/012/013 to Phase 1b. Re-review required after revision (lean: <=3 rounds).
