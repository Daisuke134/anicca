# Iteration 2 Resolution Record

This additive record does not modify or supersede the iteration-2 manifest, verdict, or finding JSON. The next reviewer independently decides iteration 3 from the corrected artifacts.

## Original findings and accepted adjudication

- `FIND-005` (`purity_boundary`, route `1a`) is accepted exactly. A dependency can enter a final report only from an internally aggregated observation whose non-serialized correlation equals the current report run correlation. `runRef` is the one-way SHA-256 reference of that current correlation; raw correlation IDs are never serialized. Every `checkedAt` is a finite, exact-round-trip `YYYY-MM-DDTHH:mm:ss.sssZ` value satisfying `max(generatedAt - 900000 ms, runStartedAt) <= checkedAt <= generatedAt`. Exact lower boundary passes; one-ms stale/future, before-run-start, malformed/non-finite, mixed-run, and fresh-only evidence fail closed.
- `FIND-006` (`proof_gap`, route `1b`) is accepted exactly. Mutable/baseline-only counts are replaced by immutable baseline plus exact new/final arithmetic; named commands, expected exits/counts/thresholds, snapshot binding, future evidence paths, helper RED-first contracts, process/security/traceability/history/schema/scope verification, and one separately authorized controlled-L3 command are fixed in the Phase 1b architecture and draft contract. Coverage independently requires lines and functions `>=90.00%` for the planned Phase 2 production modules `lib/daily-preflight.js`, `lib/daily-preflight-collectors.js`, and `lib/transport/mail-gog.js`, and for every additional production module actually changed during Phase 2; the future coverage verifier compares the Phase 2 production diff against the coverage table and fails for a missing module, combined-only average, sub-threshold lines, or sub-threshold functions.

## Corrected anchors

- Phase 1a: `specs/behavioral-spec.md` — REQ-002 and REQ-013 define current-run aggregation, strict UTC milliseconds, the closed freshness interval, hash-only `runRef`, raw-correlation exclusion, and all required boundary failures.
- Phase 1b: `specs/verification-architecture.md` — PROP-001 and PROP-007 carry FIND-005; PROP-006 through PROP-012 and the Exact Phase 2 command matrix carry FIND-006. Final schema arithmetic is `2 + 24 + 8 + 3 + 1 + 7 = 45`; new focused is `12 + 45 + 6 = 63`; full final is `371 + 63 = 434`.
- Draft grading: `contracts/sprint-1.md` — CRIT-001/002/005 cover FIND-005 and CRIT-003/004/005 cover FIND-006. Status remains `draft`.

## Route and stop

Installed atomic VCSDD state tooling records iteration-2 `1c/FAIL` routing to earliest Phase `1a`, preserving the FAIL gate, `humanApproved=false`, and `sprintCount=0`. After the Phase 1a correction, the legal `1a→1b` transition records the Phase 1b correction. Work stops at `currentPhase=1b`; no iteration-3 verdict, human approval, contract approval, Phase 2 evidence, or controlled provider execution is created.

The only next action is a fresh, artifact-only Phase 1c iteration-3 review. Its reviewer must independently determine PASS or FAIL.
