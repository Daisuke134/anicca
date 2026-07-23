# Iteration-1 Finding Resolution

This builder record does not alter, replace, or constitute an adversary verdict. The original `output/verdict.json` and `output/findings/FIND-001.json` through `FIND-004.json` remain authoritative and unchanged. A fresh reviewer must adjudicate iteration 2.

## FIND-001 — accepted; routed to Phase 1a

Original finding: “REQ-018 makes the installed strict Phase 1c workflow impossible: it requires state to remain at 1b until both adversary review and later human approval pass, while the atomic workflow must transition 1b to 1c before recording the adversary gate. PROP-010 and the final review checklist repeat the incompatible requirement that no 1c verdict exist. Correct REQ-018, PROP-010, and the final checklist so Phase 1c means currentPhase=1c with an adversary verdict recorded, sprintCount=0, draft contract unapproved, humanApproved=false, and no transition to 2a.”

Resolution: accepted without modification. Corrected locations:

- `specs/behavioral-spec.md#req-018--process-gate-honesty`
- `specs/verification-architecture.md#prop-010--process-state-honesty-tier-2-required`
- `specs/verification-architecture.md#final-phase-1-checklist`
- `contracts/sprint-1.md#crit-001`
- `contracts/sprint-1.md#crit-005`
- `state.json` (`1c/FAIL → 1a → 1b`, iteration-1 gate retained, `humanApproved=false`)

## FIND-002 — security concern accepted; literal remedy modified

Original finding: “The final evidence allowlist is broader than the required hashes-and-booleans boundary: REQ-013 permits classifications, counts, and timestamps in serialized reports and errors. Narrow the final production evidence schema to sanitized booleans and one-way hash references only, and keep any timing arithmetic or failure classification transient or in a separately defined non-final diagnostic channel that cannot enter the final artifact.”

Adjudication: accept the security/purity concern, but replace the literal “booleans and hashes only” remedy with the orchestrator-approved closed typed success schema needed to prove fixed dependency identity/status, 9/9 counts, and freshness. Only fixed schema/version/dependency/status enums, booleans, bounded counts, UTC freshness timestamps, and one-way `sha256:` references are legal. A separate closed non-final failure enum cannot enter a success artifact.

Corrected locations:

- `specs/behavioral-spec.md#req-013--sanitized-evidence`
- `specs/verification-architecture.md#purity-boundary-map`
- `specs/verification-architecture.md#prop-007--closed-final-schema-and-security-closure-tier-2-required`
- `specs/verification-architecture.md#exact-phase-2-command-matrix`
- `contracts/sprint-1.md#crit-005`

## FIND-003 — accepted; routed to Phase 1b

Original finding: “Controlled readback is called bounded but no numeric timeout, maximum poll count, or closed deadline is specified for Telegram backlog or email inbox polling. This leaves acceptance and side-effect failure behavior non-binary and cannot prove that a post-send failure terminates without retry. Define exact per-provider deadlines and/or maximum poll counts, with boundary tests for the final allowed poll and the first disallowed poll.”

Resolution: accepted. Corrected locations:

- `specs/behavioral-spec.md#req-006--one-shot-side-effect-limits`
- `specs/verification-architecture.md#prop-006--poll-boundaries-one-shot-budgets-and-no-phone-tier-1-required`
- `specs/verification-architecture.md#exact-phase-2-command-matrix`
- `contracts/sprint-1.md#crit-003`

The record distinguishes current implementation (reply `6×`, webhook `3×`, inbox `6×`; delays `2000/2000/3000 ms`; sidecar `15000 ms`; gog `30000 ms`) from required future RED work (all calls `15000 ms`; Telegram/email/parallel hard deadlines `179000/120000/179000 ms`).

## FIND-004 — accepted; routed to Phase 1b

Original finding: “The verification plan names command classes but does not specify exact executable commands or concrete output paths, and it delegates coverage to a threshold that the draft contract never declares. Therefore CRIT-003 and CRIT-005 cannot be adjudicated reproducibly or as binary PASS/FAIL. Add exact commands, expected exits/counts, evidence paths, source-snapshot binding, and numeric line/function coverage thresholds for every L1, L2, boundary, security, purity, and process obligation.”

Resolution: accepted. Corrected locations:

- `specs/verification-architecture.md#exact-phase-2-command-matrix`
- `specs/verification-architecture.md#coverage-acceptance`
- `specs/verification-architecture.md#redgreen-evidence-contract-for-phase-2`
- `contracts/sprint-1.md#crit-003`
- `contracts/sprint-1.md#crit-005`

Coverage is binary per changed production module at `>=90.00%` lines and `>=90.00%` functions, with include-filtered commands and machine-readable V8 JSON paths; no combined average is accepted.
