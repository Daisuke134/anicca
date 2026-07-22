---
sprintNumber: 3
feature: panel-score-semantics
scope: "Close fresh implementation-review FIND-004/FIND-005: a safe-integer financial ratio must render when the canonical server core reports it, without weakening the closed score payload validation."
negotiationRound: 0
status: approved
criteria:
  - id: CRIT-013
    dimension: implementation_correctness
    description: The score core and score-card validator use one integer-safe half-up ratio implementation for measured safe integers
    weight: 0.55
    passThreshold: `roundedScoreValue` is the sole score-ratio rounding implementation in `panel-score-semantics.js`; both core aggregation paths and `panel-ui.js` use it, preserving clamp 0..100 and rejecting mismatched values instead of weakening closed payload validation
    beadId: BEAD-061
  - id: CRIT-014
    dimension: edge_case_coverage
    description: The renderer has a real boundary regression for the canonical safe-integer financial ratio
    weight: 0.30
    passThreshold: The UI test first fails against float `Math.round`, then passes using `numerator=945755921642804`, `denominator=9007199253740991`, and canonical value `10`; normal small ratios and contradictory models remain covered
    beadId: BEAD-062
  - id: CRIT-015
    dimension: verification_readiness
    description: The correction preserves the endpoint, full regression, eval, and real PostgreSQL evidence
    weight: 0.15
    passThreshold: Fresh commands show focused panel score plus UI tests pass 27/27, `npm test` exits 0, `npm run eval` reports 21/21 plus 12/12 plus 12/12 plus 27/27, and `npm run test:panel-score:postgres` passes roles=3 snapshot_sessions=2 complete_rows=20000 overflow_rows=20001
    beadId: BEAD-063
---

## Scope

Sprint 3 changes only the shared integer-safe rounding helper, its core call sites, the renderer validator call site, and the boundary regression test required by FIND-004/FIND-005. It does not change score formulas, source-outcome selection, endpoint auth/query behavior, migration schema, PostgreSQL privileges, or the score-card model.
