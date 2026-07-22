---
sprintNumber: 4
feature: panel-score-semantics
scope: "Close fresh implementation-review FIND-006/FIND-007: serialize the existing shared integer-safe score helper into the actual renderPanelPage browser script and verify the emitted renderer."
negotiationRound: 0
status: approved
criteria:
  - id: CRIT-016
    dimension: implementation_correctness
    description: The inline panel renderer has every declared dependency for measured score validation
    weight: 0.55
    passThreshold: renderPanelPage serializes the existing `roundedScoreValue` function before `validScoreOrgan` and `renderScoreCards`; it does not duplicate or alter the integer-safe formula, and the module/browser paths therefore use the same helper
    beadId: BEAD-064
  - id: CRIT-017
    dimension: edge_case_coverage
    description: The real emitted browser score renderer is tested with the canonical safe-integer FINANCIAL model
    weight: 0.30
    passThreshold: panel-ui.test.js extracts the score script from renderPanelPage(), executes it in a Node VM, proves the core helper returns 10 for numerator=945755921642804 denominator=9007199253740991, and renders that closed model without ReferenceError while retaining malformed-model rejection coverage
    beadId: BEAD-065
  - id: CRIT-018
    dimension: verification_readiness
    description: The browser-path correction preserves all endpoint, regression, eval, and database contracts
    weight: 0.15
    passThreshold: Fresh commands show focused panel score plus UI tests pass 28/28, `npm test` exits 0, `npm run eval` reports 21/21 plus 12/12 plus 12/12 plus 27/27, and `npm run test:panel-score:postgres` passes roles=3 snapshot_sessions=2 complete_rows=20000 overflow_rows=20001
    beadId: BEAD-066
---

## Scope

Sprint 4 changes only browser serialization of the existing shared rounding helper and tests that execute the emitted browser score renderer. It does not alter score formulas, source outcomes, endpoint behavior, database migration, role access, or the closed score payload.
