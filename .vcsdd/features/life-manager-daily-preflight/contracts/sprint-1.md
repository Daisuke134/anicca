---
sprintNumber: 1
feature: life-manager-daily-preflight
scope: Complete CORE-a/8d closed preflight plus narrow method-2 receipt precision correction
criteria:
  - id: CRIT-001
    dimension: spec_fidelity
    description: All nine dependencies and every fail-closed correlation, freshness, sanitation, side-effect, and historical immutability requirement are satisfied.
    weight: 0.25
    passThreshold: Every linked REQ has direct test or proof evidence with no contradiction or unsupported production claim.
  - id: CRIT-002
    dimension: edge_case_coverage
    description: Minute intervals, exact timestamps, timezone offsets, impossible dates, freshness edges, and malformed bounds are deterministically covered.
    weight: 0.20
    passThreshold: All declared temporal boundary cases pass, including the fixed ten-assertion boundary audit, with no skipped required case.
  - id: CRIT-003
    dimension: implementation_correctness
    description: Exact nonce, provider, owned-recipient, same-run receipt correlation and one-shot budgets remain fail-closed in production behavior.
    weight: 0.20
    passThreshold: Focused, full, eval, and boundary commands all pass from the contracted source snapshot with exact exits and counts.
  - id: CRIT-004
    dimension: structural_integrity
    description: Production provenance is fixed and test injection cannot enter production collectors, transports, receipt bounds, or CLI proof inputs.
    weight: 0.15
    passThreshold: Static and executable purity checks find zero production injection paths and zero accidental real-provider fallback from tests.
  - id: CRIT-005
    dimension: verification_readiness
    description: Evidence is fresh, sanitized, schema-valid, traceable, and preserves historical artifacts while respecting the controlled effect budget.
    weight: 0.20
    passThreshold: VCSDD evidence markers and freshness pass; security and artifact review find zero unsafe data or unauthorized changes.
negotiationRound: 0
status: draft
---

# Sprint 1 Contract Draft

This is a strict-mode draft prepared before Phase 1c. It is not human/orchestrator approved and has no contract-review verdict. Phase 2 may not start from this draft.

## Traceability

### CRIT-001

Links: REQ-001–REQ-018; PROP-001, PROP-005, PROP-010, PROP-012.

### CRIT-002

Links: REQ-007–REQ-010, REQ-017; PROP-002, PROP-003, PROP-004.

### CRIT-003

Links: REQ-003–REQ-006, REQ-014–REQ-017; PROP-005, PROP-006, PROP-011, PROP-012.

### CRIT-004

Links: REQ-011, REQ-012, REQ-017; PROP-008.

### CRIT-005

Links: REQ-002, REQ-013, REQ-015, REQ-016, REQ-018; PROP-007, PROP-009, PROP-010.

## Artifact scope

- Production/source/tests to be adjudicated in Phase 2: the exact correction diff `f6129abb5..58846034b` under `apps/life-call/`.
- Process artifacts: this feature directory, excluding modification of the two historical evidence JSON files.
- Canonical status: `docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md` row 8d and §10.0.

## Required review condition

A fresh artifact-only Phase 1c reviewer must evaluate the behavioral spec and verification architecture. Explicit strict-mode human/orchestrator approval must follow a fresh adversary PASS before Phase 2a. This draft must not be changed to `approved` in this corrective order.
