# Verification Report

## Proof Obligations

- PROP-001 — proved. `node .vcsdd/features/panel-score-semantics/verification/proof-harnesses/ratio-invariants.js` passed: bounded_pairs=66049, non_financial_evaluations=198147, boundary_pairs=12, generated_pairs=10000, seed=0x51c0a7e1. This run includes the prior 23/40 rounding regression case via the bounded pair domain.
- PROP-002 — proved. `dedup-invariants.js` passed: seed=0x8A17C0DE, row_sets=500, cases=12000, shuffles_per_set=21, fixed_fixtures=4, typed_pairs=35.
- PROP-003 — proved. `period-invariants.js` passed: period_cases=6, inclusion_cases=4, invalid_clock_cases=1, with half-open `[start,end)` inclusion.
- PROP-004 — proved. `tenant-query-invariants.js` passed: endpoint_cases=5, exact_snapshot_rpc_calls=1, forged_tenant_rows_excluded=1, denied_methods=3, overflow_fail_closed=1. Real PostgreSQL support passed separately below.
- PROP-005 — proved. `migration-invariants.js` passed: static_checks=53; `npm run test:panel-score:postgres` passed with roles=3, snapshot_sessions=2, complete_rows=20000, overflow_rows=20001.
- PROP-006 — proved. `render-linkage-invariants.js` passed: organs=4, linkage_cases=4, exact_winner_ref_sets=4, raw_identifier_leaks=0, contradictory_models_rejected=1.

Captured raw outputs are in `verification/hardening-results/`, SHA-256 recorded by the final release evidence. Focused regression passed 14/14; full Life Call regression exited 0; deterministic evals passed calendar 21/21, late 12/12, context/onboarding/discovery 12/12, and score semantics 27/27.

## Summary

All six required Tier-1 proof obligations are proved by fresh deterministic runs after entering Phase 5. The real PostgreSQL harness confirms the privileged RPC contract, service-only access, statement snapshot, complete 20,000-row response, and 20,001-row fail-closed overflow. No required proof is skipped.

### Final Phase 5 rerun

After Sprint 4's emitted-browser renderer correction, all required proof harnesses were rerun in this Phase 5: PROP-001 66049 pairs/198147 non-financial evaluations/10000 generated, PROP-002 12000 permutation cases, PROP-003 6 period plus 4 inclusion cases, PROP-004 endpoint tenant/RPC cases, PROP-005 53 migration checks, and PROP-006 four-organ linkage. Fresh focused tests passed 14/14 plus UI 14/14; full regression exited 0; evals passed 21/21, 12/12, 12/12, and 27/27; real PostgreSQL passed roles=3, snapshot_sessions=2, complete_rows=20000, overflow_rows=20001. Raw outputs are `verification/hardening-results/final-*.log`.
