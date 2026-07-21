---
sprintNumber: 1
feature: life-manager-daily-preflight
scope: Complete CORE-a/8d closed preflight plus narrow method-2 receipt precision correction
criteria:
  - id: CRIT-001
    dimension: spec_fidelity
    description: All requirements, including legal strict Phase 1c gate semantics, are implemented without unsupported production or process claims.
    weight: 0.25
    passThreshold: >-
      PASS iff every REQ-001..018 reaches at least one PROP and CRIT, iteration-1/2 review outputs remain immutable, the fresh iteration-3 Phase 1c verdict is independently recorded with humanApproved=false until explicit approval, and transition to 2a is rejected unless iteration-3 adversaryVerdict=PASS and humanApproved=true.
  - id: CRIT-002
    dimension: edge_case_coverage
    description: Receipt intervals and every final dependency checkedAt/current-run correlation boundary are deterministically covered.
    weight: 0.20
    passThreshold: >-
      PASS iff the fixed receipt audit is 10/10 and the eight checkedAt cases pass: exact 900000 ms boundary accepted, and one-ms stale, one-ms future, malformed, non-finite, before-run-start, mixed-run, and fresh-only inputs rejected; raw correlation IDs are absent and runRef is the current-run one-way hash.
  - id: CRIT-003
    dimension: implementation_correctness
    description: Exact correlation, polling boundaries, call/deadline bounds, and one-shot budgets remain fail-closed in production behavior.
    weight: 0.20
    passThreshold: >-
      PASS iff Telegram reply attempts are exactly bounded at 6 with 2000 ms delays, webhook attempts at 3 with 2000 ms delays, email attempts at 6 with 3000 ms delays, attempt 7/4/7 never occurs, every provider call is bounded at 15000 ms, collector deadlines are 179000/120000/179000 ms, timeout after send produces no duplicate send and zero phone calls, and command results are baseline 51/51 plus new 63/63, full final 434/434, eval 33/33, temporal 18/18, and poll/deadline 12/12.
  - id: CRIT-004
    dimension: structural_integrity
    description: Production provenance is fixed and test injection cannot enter production collectors, transports, receipt bounds, or CLI proof inputs.
    weight: 0.15
    passThreshold: >-
      PASS iff immutable provenance 26/26 plus new purity 6/6 equals 32/32, with zero production injection paths, zero accidental real-provider fallback, current-run runRef derivation, no raw-correlation serialization, and atomic report/no-artifact-on-failure behavior.
  - id: CRIT-005
    dimension: verification_readiness
    description: Evidence uses the closed typed final schema, is reproducible from a bound snapshot, and preserves historical artifacts.
    weight: 0.20
    passThreshold: >-
      PASS iff final schema tests are exactly 45/45 (2 positive + 43 fail-closed negative), verifier contracts are 12/12, every command writes its declared snapshot-bound evidence with exact exit/count, every changed production module independently has at least 90.00% lines and functions, VCSDD state/runtime/gates, REQ-PROP-CRIT traceability, review/artifact schemas, safe ISO-aware secret/PII scan, git/diff/staged scope, and historical SHA-256+0600 checks all exit 0, and the separately authorized single L3 produces exactly one closed 9/9 TG=1/email=1/phone=0 same-run report or no artifact on failure.
negotiationRound: 0
status: draft
---

# Sprint 1 Contract Draft

This is a strict-mode draft prepared before Phase 1c. It is not human/orchestrator approved and has no contract-review verdict. Phase 2 may not start from this draft.

## Traceability

### CRIT-001

Links: REQ-001–REQ-018; PROP-001, PROP-005, PROP-010, PROP-012. FIND-005 current-run closure is carried by REQ-002/013 → PROP-001/007 → CRIT-001; iteration-2 routing and iteration-3 gate honesty are carried by REQ-018 → PROP-010 → CRIT-001.

### CRIT-002

Links: REQ-002, REQ-007–REQ-010, REQ-013, REQ-017; PROP-002, PROP-003, PROP-004, PROP-007. FIND-005 exact-limit/stale/future/malformed/mixed-run cases terminate here.

### CRIT-003

Links: REQ-003–REQ-006, REQ-014–REQ-017; PROP-005, PROP-006, PROP-011, PROP-012. FIND-006 immutable/new/final count arithmetic and numeric polling/deadline boundaries terminate here.

### CRIT-004

Links: REQ-011, REQ-012, REQ-017; PROP-008. FIND-006 exact purity/provenance and atomic output contracts terminate here.

### CRIT-005

Links: REQ-002, REQ-013, REQ-015, REQ-016, REQ-018; PROP-007, PROP-009, PROP-010, PROP-012. FIND-005 closed same-run schema and FIND-006 process/schema/scan/history/L3 matrix terminate here.

## Artifact scope

- Production/source/tests to be adjudicated in Phase 2: the exact correction diff `f6129abb5..58846034b` under `apps/life-call/`.
- Process artifacts: this feature directory, excluding modification of the two historical evidence JSON files.
- Canonical status: `docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md` row 8d and §10.0.

## Required review condition

A fresh artifact-only Phase 1c iteration-3 reviewer must independently evaluate the corrected behavioral spec and verification architecture. Explicit strict-mode human/orchestrator approval may follow only a fresh iteration-3 adversary PASS before Phase 2a. This draft remains `draft` in this corrective order.
