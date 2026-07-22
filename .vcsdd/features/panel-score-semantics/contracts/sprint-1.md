---
sprintNumber: 1
feature: panel-score-semantics
scope: "Outcome-derived DAILY, PHYSICAL, MENTAL, and FINANCIAL score semantics, one authenticated snapshot RPC, additive append-only storage, closed UI rendering, deterministic evaluation, and independent readback oracle"
negotiationRound: 1
status: approved
criteria:
  - id: CRIT-001
    dimension: spec_fidelity
    description: The pure score core implements the four exact outcome-derived organ formulas and closed envelopes without using activity counters
    weight: 0.2
    passThreshold: npm run test:panel-score exits 0 and panel-score-semantics.test.js proves all four organ formulas, immutable-revision winner rules, privacy-safe references, closed status/value/numerator/denominator/period/reason/components/source_outcome_ids fields, and no lm_wake_log or lm_api_cost input enters panel-score-semantics.js
    beadId: BEAD-041
  - id: CRIT-002
    dimension: spec_fidelity
    description: The authenticated score endpoint performs one bounded source-outcome snapshot request and fails closed for unavailable or overflowing storage
    weight: 0.15
    passThreshold: panel-api-score-semantics.test.js passes and proves exactly one POST to /rest/v1/rpc/lm_panel_score_outcome_snapshot whose body has only p_uid bound to the authenticated session plus p_periods with daily physical mental financial start_at and end_at, while missing or malformed storage maps to HTTP 503 source_table_unavailable and overflow maps to HTTP 503 source_outcome_limit
    beadId: BEAD-042
  - id: CRIT-003
    dimension: implementation_correctness
    description: The additive PostgreSQL ledger and functions enforce immutable idempotent revisions, append-only storage, tenant boundaries, role denial, statement snapshots, and complete-or-overflow bounds
    weight: 0.2
    passThreshold: npm run test:panel-score:postgres exits 0 with roles=3 snapshot_sessions=2 complete_rows=20000 overflow_rows=20001 and its real PostgreSQL assertions prove non-zero UUID revision keys, exact retry success, mismatched retry conflict, fresh-key same-status correction and status re-entry, UPDATE and DELETE denial, internal uid organ and half-open period filters, SECURITY INVOKER with fixed search_path, PUBLIC anon authenticated denial, service_role success, and no partial rows on overflow
    beadId: BEAD-043
  - id: CRIT-004
    dimension: edge_case_coverage
    description: The fixed matrix covers every required success partial zero boundary dedup failure and invalid-data case and an independent oracle reaches the same outputs
    weight: 0.15
    passThreshold: npm run eval:score reports exactly 27/27 including the six named failure UI and captured-snapshot contract cases, scripts/independent-panel-score-readback.test.js matches all 21 literal period and score cases, and the oracle imports none of panel-score-semantics.js panel-api.js or panel-ui.js
    beadId: BEAD-044
  - id: CRIT-005
    dimension: implementation_correctness
    description: The panel presents four readable score cards from the closed API model and rejects malformed models without fabricated scores
    weight: 0.1
    passThreshold: panel-ui.test.js passes the PANEL-8g tests and proves DAILY PHYSICAL MENTAL FINANCIAL cards render measured insufficient_data and invalid_data states with value or exact visible insufficiency, ratio, period, reason, components, and source count, while a missing or malformed organ throws a load error and renders neither NaN nor raw JSON
    beadId: BEAD-045
  - id: CRIT-006
    dimension: structural_integrity
    description: Score derivation remains isolated in a deterministic pure core and the effectful API UI persistence and independent-oracle boundaries remain explicit
    weight: 0.05
    passThreshold: A source read confirms panel-score-semantics.js reads no environment clock filesystem database network or random value, panel-api.js performs the only score-source RPC and no mutation or provider call on GET scores, panel-ui.js only validates and renders the supplied model, and the independent oracle shares no production scorer import
    beadId: BEAD-046
  - id: CRIT-007
    dimension: verification_readiness
    description: Target tests, focused tenant and panel regressions, the complete Life Call regression suite, and all deterministic eval suites are freshly green after refactor
    weight: 0.1
    passThreshold: The adversary independently runs npm test and npm run eval from apps/life-call and both exit 0, with the score suite reporting 14/14 and all evals reporting calendar 21/21 late 12/12 context 12/12 and score 27/27, with zero skipped or todo score tests
    beadId: BEAD-047
  - id: CRIT-008
    dimension: verification_readiness
    description: VCSDD traceability is complete and the six named proof obligations have executable artifact paths ready for Phase 5 hardening
    weight: 0.05
    passThreshold: validateChainCompleteness returns valid true with no warnings, every TEST-001 through TEST-016 bead is green and linked to an implemented artifact, and state.json contains required pending obligations PROP-001 through PROP-006 at the exact proof-harness paths declared in verification-architecture.md
    beadId: BEAD-048
---

## Scope

Sprint 1 implements REQ-001 through REQ-012 locally and prepares the independent readback required by REQ-013. Production deployment and the read-only authenticated L3 occur only after VCSDD convergence and merge to `main`.

Final product and verification artifacts reviewed by this contract:

- `apps/life-call/lib/panel-score-semantics.js`
- `apps/life-call/lib/panel-api.js`
- `apps/life-call/lib/panel-ui.js`
- `apps/life-call/migrations/2026-07-22-panel-score-outcomes.sql`
- `apps/life-call/eval/score-semantics-cases.json`
- `apps/life-call/eval/run-score-semantics-eval.js`
- `apps/life-call/scripts/independent-panel-score-readback.js`
- `apps/life-call/lib/panel-score-semantics.test.js`
- `apps/life-call/lib/panel-api-score-semantics.test.js`
- `apps/life-call/lib/panel-score-migration.test.js`
- `apps/life-call/lib/panel-ui.test.js`
- `apps/life-call/scripts/independent-panel-score-readback.test.js`
- `apps/life-call/test/postgres/panel-score-postgres.integration.sh`
- `apps/life-call/package.json`

The sprint does not synthesize historical outcomes from activity counters and does not add production writers for new outcomes. The ledger and append function are additive infrastructure; score reads remain read-only and fail closed when the source is not available.

## Phase 2c refactor

The refactor extracts repeated score-unavailability error construction in `panel-api.js` into one named helper. The score contract, response codes, snapshot call, pure formulas, storage schema, and rendering remain unchanged. Fresh post-refactor verification is recorded in `evidence/sprint-1-green-phase.log`.

## Contract review round 1 closure

- FIND-001: expanded the closed matrix from 19 to 27 cases. The added cases cover unknown kinds, absent/invalid MENTAL resolution timestamps, missing source storage, period-resolution failure, source overflow, malformed snapshot storage, malformed UI models, and captured-snapshot membership. The actual two-session database snapshot remains independently executable under CRIT-003.
- FIND-002: the API now validates the complete `rows_by_organ` envelope as exactly four arrays and maps malformed snapshots to `503 source_table_unavailable`.
- FIND-003: the UI now enforces the per-organ period-kind enum and canonical UUID audit-reference shape before rendering.

Fresh evidence after these fixes is 446/446 full regression, 27/27 score eval, 21/21 independent pure oracle cases, and real PostgreSQL PASS at the 20,000/20,001 boundary.
