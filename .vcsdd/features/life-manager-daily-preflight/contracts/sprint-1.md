---
sprintNumber: 1
feature: life-manager-daily-preflight
scope: Complete CORE-a/8d closed preflight plus narrow method-2 receipt precision correction
criteria:
  - id: CRIT-001
    dimension: spec_fidelity
    description: All requirements, including legal strict Phase 1c gate semantics, are implemented without unsupported production or process claims.
    weight: 0.25
    passThreshold: PASS iff every REQ-001..018 has a linked PROP and admissible evidence, Phase 1c is represented as currentPhase=1c with an adversary verdict and humanApproved=false until explicit approval, and transition to 2a is rejected unless adversaryVerdict=PASS and humanApproved=true.
  - id: CRIT-002
    dimension: edge_case_coverage
    description: Minute intervals, exact timestamps, timezone offsets, impossible dates, freshness edges, and malformed bounds are deterministically covered.
    weight: 0.20
    passThreshold: All declared temporal boundary cases pass, including the fixed ten-assertion boundary audit, with no skipped required case.
  - id: CRIT-003
    dimension: implementation_correctness
    description: Exact correlation, polling boundaries, call/deadline bounds, and one-shot budgets remain fail-closed in production behavior.
    weight: 0.20
    passThreshold: PASS iff Telegram reply attempts are exactly bounded at 6 with 2000 ms delays, webhook attempts at 3 with 2000 ms delays, email attempts at 6 with 3000 ms delays, attempt 7/4/7 never occurs, every provider call is bounded at 15000 ms, collector deadlines are 179000/120000/179000 ms, timeout after send produces TG=1 email=1 phone=0 with no duplicate send, and the exact focused/full/eval/boundary commands meet their declared exits and counts.
  - id: CRIT-004
    dimension: structural_integrity
    description: Production provenance is fixed and test injection cannot enter production collectors, transports, receipt bounds, or CLI proof inputs.
    weight: 0.15
    passThreshold: Static and executable purity checks find zero production injection paths and zero accidental real-provider fallback from tests.
  - id: CRIT-005
    dimension: verification_readiness
    description: Evidence uses the closed typed final schema, is reproducible from a bound snapshot, and preserves historical artifacts.
    weight: 0.20
    passThreshold: PASS iff the canonical 9/9 success artifact is accepted, all 36 declared schema-negative/failure-separation cases are rejected, no forbidden field/class or nested unknown key is serializable, every exact command writes the declared evidence path with the declared exit/count, each changed production module independently has at least 90.00% lines and 90.00% functions, all VCSDD/schema/traceability/diff checks exit 0, safe secret/PII match counts are zero, and both historical JSON hashes/modes remain exact.
negotiationRound: 0
status: draft
---

# Sprint 1 Contract Draft

This is a strict-mode draft prepared before Phase 1c. It is not human/orchestrator approved and has no contract-review verdict. Phase 2 may not start from this draft.

## Traceability

### CRIT-001

Links: REQ-001–REQ-018; PROP-001, PROP-005, PROP-010, PROP-012. Binary gate correction is carried by REQ-018 → PROP-010 → CRIT-001.

### CRIT-002

Links: REQ-007–REQ-010, REQ-017; PROP-002, PROP-003, PROP-004.

### CRIT-003

Links: REQ-003–REQ-006, REQ-014–REQ-017; PROP-005, PROP-006, PROP-011, PROP-012. Numeric polling and deadline boundaries are carried by REQ-006 → PROP-006 → CRIT-003.

### CRIT-004

Links: REQ-011, REQ-012, REQ-017; PROP-008.

### CRIT-005

Links: REQ-002, REQ-013, REQ-015, REQ-016, REQ-018; PROP-007, PROP-009, PROP-010. Closed schema is carried by REQ-013 → PROP-007 → CRIT-005; process state is also carried by REQ-018 → PROP-010 → CRIT-005.

## Artifact scope

- Production/source/tests to be adjudicated in Phase 2: the exact correction diff `f6129abb5..58846034b` under `apps/life-call/`.
- Process artifacts: this feature directory, excluding modification of the two historical evidence JSON files.
- Canonical status: `docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md` row 8d and §10.0.

## Required review condition

A fresh artifact-only Phase 1c reviewer must evaluate the behavioral spec and verification architecture. Explicit strict-mode human/orchestrator approval must follow a fresh adversary PASS before Phase 2a. This draft must not be changed to `approved` in this corrective order.
