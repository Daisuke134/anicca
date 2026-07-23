---
sprintNumber: 2
feature: panel-score-semantics
scope: "Close sprint-1 findings by rejecting fractional minor units at both append and storage boundaries, asserting invalid revision and amount inputs in real PostgreSQL, and rejecting non-canonical or non-closed score-card models"
negotiationRound: 1
status: approved
criteria:
  - id: CRIT-009
    dimension: implementation_correctness
    description: The outcome ledger preserves integer minor-unit semantics without PostgreSQL scale coercion and rejects invalid amounts before persistence
    weight: 0.35
    passThreshold: The real PostgreSQL harness proves lm_append_score_outcome rejects amount_minor 1.5 with zero rows persisted, a direct service_role INSERT of amount_minor 1.5 fails the table constraint with zero rows persisted, amount_minor is stored as unbounded numeric guarded by amount_minor equals trunc amount_minor and the JavaScript safe-integer bounds, and exact valid retries remain idempotent
    beadId: BEAD-057
  - id: CRIT-010
    dimension: edge_case_coverage
    description: The executable PostgreSQL contract covers both zero revision keys and fractional minor units at the real database boundary
    weight: 0.25
    passThreshold: npm run test:panel-score:postgres exits 0 and its source plus fresh output prove a zero UUID revision_key is rejected, fractional amount input through the append function is rejected, fractional direct storage insertion is rejected, each rejected input leaves zero matching rows, and the existing roles 3 snapshot_sessions 2 complete_rows 20000 overflow_rows 20001 assertions still pass
    beadId: BEAD-058
  - id: CRIT-011
    dimension: implementation_correctness
    description: The score-card renderer accepts only the exact four-organ closed model with canonical UTC millisecond timestamps
    weight: 0.25
    passThreshold: panel-ui.test.js passes and proves a valid four-organ payload renders exactly four cards while numeric timestamps, non-canonical or impossible ISO timestamps, missing organs, extra organs, extra outer fields, malformed period kinds, contradictory ratios, duplicate references, and incomplete components throw invalid score payload
    beadId: BEAD-059
  - id: CRIT-012
    dimension: verification_readiness
    description: The corrective changes retain complete deterministic regression and traceability evidence
    weight: 0.15
    passThreshold: Fresh commands from apps/life-call show npm test exits 0 with panel score 14/14, npm run eval reports calendar 21/21 late 12/12 context 12/12 score 27/27, npm run test:panel-score:postgres exits 0, validateChainCompleteness returns valid true with no warnings, TEST-017 through TEST-019 are green, IMPL-006 and IMPL-007 are implemented, and FIND-001 through FIND-003 beads are resolved
    beadId: BEAD-060
---

## Scope

Sprint 2 is limited to the three findings from the sprint-1 implementation review. It changes the additive outcome migration, the real PostgreSQL harness, the score-card validator, and the validator tests. The four score formulas, snapshot RPC, fixed matrix, independent oracle, API response model, and production rollout scope remain unchanged.

Reviewed corrective artifacts:

- `apps/life-call/migrations/2026-07-22-panel-score-outcomes.sql`
- `apps/life-call/test/postgres/panel-score-postgres.integration.sh`
- `apps/life-call/lib/panel-ui.js`
- `apps/life-call/lib/panel-ui.test.js`
- `.vcsdd/features/panel-score-semantics/evidence/sprint-2-red-phase.log`
- `.vcsdd/features/panel-score-semantics/evidence/sprint-2-green-phase.log`

The sprint does not modify outcome formulas, introduce outcome writers, synthesize outcomes from activity counters, or broaden browser/database privileges.
