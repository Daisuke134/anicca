# Impl Review Findings — self-improve-real-ledger (Phase 3, iteration 1)

Reviewer: fresh-context VCSDD adversary (Opus). File write blocked by harness guard; persisted
verbatim by orchestrator from the reviewer's report.

## F-1 — BLOCKING — data_realism_gap fed a wrong-unit input in production (REQ-RL11 broken)
promote_gate_run.py:239-241 passes assessment["combined_score"] (unitless Sharpe-like ratio,
0-10ish, capped 500) as mean_backtest_net_usd (a DOLLAR per-trade mean per REQ-RL11). With
sufficient=True the realism gate compares ratio-vs-dollars → fires essentially always (case (a)
nearly always true when combined_score>0; case (b) 3x-jump arbitrary) → promotion permanently
deadlocked or arbitrarily blocked; the gate looks wired to real data but is functionally
decorative through wrong typing. Correct field exists: assessment["mean_oos_net_usd"]
(evaluator.py:186/193/233, genuine dollar mean across 3 OOS windows). Fix must be None-safe
(mean_oos_net_usd is None for scope-guard-rejected/stage1-failed candidates and
compute_realized_gate is called unconditionally before the eligibility check → bare swap crashes
on float(None)). Nothing catches it today: PROP-RL-GATE4 tests the pure fn with hand-picked
floats; the schema test passes a literal; PROP-RL-LIVE2 (deferred to post-merge) is the only
end-to-end obligation. Required: field fix + None-safe default + a regression test exercising the
assess_candidate() → compute_realized_gate() seam with realistic differently-scaled values.
Anti-stub check (CRIT-004) itself: literally satisfied (all 3 sites genuinely call
compute_realized_gate; plumbing real) — the defect is wrong-typed input, judged BLOCKING under
spec_fidelity/implementation_correctness/verification_readiness.

## Independently re-executed evidence
worktree self-improve: 80 passed 1 failed (= documented EDGE-RL5b artifact, root cause confirmed);
hl-trade 41+1skip; ledger.test.mjs 12/12; ledger.test.js 9/9. is_confirmed/is_profitable vs
ledger.mjs::isProfitable verified semantically identical. last_promotion_ts fail-closed confirmed
live (git RC=128 → None).

## Minor (3, non-blocking)
1. schema test pairs tmp repo with real BASELINE_PATH — REQ-RL12 integration never exercised
   through compute_realized_gate (unit-tested in isolation only); suggest follow-up integration test.
2. window_end_ts computed via two independent time.time() calls (ms drift, immaterial).
3. PROP-RL-MIR1 documents a node -e cross-language check that doesn't exist as an executable test
   (manual read confirmed parity) — verification-method documentation gap.

Blocking: 1. Major: 0. Minor: 3. deploymentRecommendation: DO_NOT_DEPLOY.
